"""
transactions/views.py

Tenant resolution:  request.user.library  (OneToOneField on accounts.Library)

books.Book and members.Member are scoped by  owner = FK(User) —
the library admin's User object.  We resolve this as  library.user.

Transaction / Fine / MissingBook are scoped by  library = FK(Library)
and queried via  Model.objects.for_library(library).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal

from .forms import (
    AddPenaltyForm,
    IssueBookForm,
    MarkFinePaidForm,
    MarkLostForm,
    ReturnBookForm,
)
from .models import Fine, MissingBook, Transaction


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    """
    Returns the Library for the logged-in user or raises Http404.
    Prevents accidental unscoped queries.
    """
    try:
        return request.user.library   # OneToOne related_name="library"
    except Exception:
        raise Http404("No library associated with this account.")


def _get_library_rules(library):
    """
    Safely fetch library.rules (LibraryRuleSettings).
    Returns the rules object, or None if not yet configured.
    """
    try:
        return library.rules
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Transaction List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def transaction_list(request):
    library = _get_library_or_404(request)

    # Sync overdue status on every list load (lightweight bulk UPDATE)
    Transaction.sync_overdue_for_library(library)

    qs = Transaction.objects.for_library(library).select_related("member", "book")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(member__first_name__icontains=q)
            | Q(member__last_name__icontains=q)
            | Q(book__title__icontains=q)
            | Q(pk__icontains=q)
        )

    status = request.GET.get("status", "").strip()
    if status:
        qs = qs.filter(status=status)

    date_from = request.GET.get("date_from", "")
    date_to   = request.GET.get("date_to", "")
    if date_from:
        qs = qs.filter(issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(issue_date__lte=date_to)

    base           = Transaction.objects.for_library(library)
    total_count    = base.count()
    issued_count   = base.filter(status=Transaction.STATUS_ISSUED).count()
    overdue_count  = base.filter(status=Transaction.STATUS_OVERDUE).count()
    returned_count = base.filter(status=Transaction.STATUS_RETURNED).count()
    lost_count     = base.filter(status=Transaction.STATUS_LOST).count()

    per_page     = int(request.GET.get("per_page", 25))
    paginator    = Paginator(qs.order_by("-created_at"), per_page)
    transactions = paginator.get_page(request.GET.get("page", 1))

    return render(request, "transactions/transaction_list.html", {
        "transactions":   transactions,
        "total_count":    total_count,
        "issued_count":   issued_count,
        "overdue_count":  overdue_count,
        "returned_count": returned_count,
        "lost_count":     lost_count,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2. Transaction Detail
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def transaction_detail(request, pk):
    library = _get_library_or_404(request)
    txn = get_object_or_404(
        Transaction.objects.for_library(library).select_related("member", "book"),
        pk=pk,
    )
    fines = txn.fines.all().order_by("-created_at")

    # Compute member stats not stored on the Member model
    member = txn.member
    active_loans_count = Transaction.objects.for_library(library).filter(
        member=member,
        status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE),
    ).count()

    outstanding_fine = (
        Fine.objects.for_library(library)
        .filter(transaction__member=member, status=Fine.STATUS_UNPAID)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )

    try:
        from accounts.models import MemberSettings
        member_settings = MemberSettings.objects.get(library=library)
        borrow_limit = int(member_settings.borrow_limit or 0)
    except Exception:
        borrow_limit = 0

    return render(request, "transactions/transaction_detail.html", {
        "transaction":        txn,
        "fines":              fines,
        "active_loans_count": active_loans_count,
        "borrow_limit":       borrow_limit,
        "outstanding_fine":   outstanding_fine,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 3. Issue Book
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def issue_book(request):
    library = _get_library_or_404(request)
    owner   = library.user
    rules   = _get_library_rules(library)

    from members.models import Member
    from books.models import Book

    # ─────────────────────────────────────────────
    # Validate Rules
    # ─────────────────────────────────────────────
    if not rules:
        messages.error(request, "Library rule settings not configured.")
        return redirect("transactions:transaction_list")

    borrowing_period  = int(rules.borrowing_period or 14)
    fine_rate_per_day = rules.late_fine or Decimal("0.00")
    max_renewal_count = rules.max_renewal_count or 0

    # Borrow limit comes from accounts.MemberSettings.borrow_limit,
    # not from library rules.
    try:
        from accounts.models import MemberSettings
        member_settings      = MemberSettings.objects.get(library=library)
        max_books_per_member = int(member_settings.borrow_limit or 0)
    except Exception:
        max_books_per_member = 0

    today = date.today()
    default_due_date = today + timedelta(days=borrowing_period)

    # ─────────────────────────────────────────────
    # Query scoped by owner (multi-tenant safe)
    # ─────────────────────────────────────────────
    # Annotate each member with their current active loan count.
    # Count() with a filter always returns an integer (0 when no rows match),
    # unlike Subquery which returns NULL for members with no loans yet.
    from django.db.models import Count, Sum, Q as _Q, DecimalField as _DF
    _members_qs = (
        Member.objects
        .filter(owner=owner, status="active")
        .annotate(active_loans_count=Count(
            "issue_transactions",
            filter=_Q(
                issue_transactions__library=library,
                issue_transactions__status__in=(
                    Transaction.STATUS_ISSUED,
                    Transaction.STATUS_OVERDUE,
                ),
            ),
        ))
        .order_by("first_name", "last_name")
    )

    # Bulk-fetch unpaid fine totals per member — one query, no N+1.
    _fine_totals = {
        row["transaction__member_id"]: row["total"]
        for row in Fine.objects.for_library(library)
        .filter(status=Fine.STATUS_UNPAID)
        .values("transaction__member_id")
        .annotate(total=Sum("amount", output_field=_DF()))
    }

    # Attach computed display fields as Python attributes.
    # slots_available counts DOWN from max → 0 as loans increase.
    # -1 signals "no limit configured" so the template can show ∞.
    members = []
    for m in _members_qs:
        if max_books_per_member:
            m.slots_available = max(0, max_books_per_member - m.active_loans_count)
        else:
            m.slots_available = -1   # unlimited — JS will show ∞
        m.total_due = _fine_totals.get(m.pk, Decimal("0.00"))
        members.append(m)

    books = (
        Book.objects
        .filter(owner=owner, available_copies__gt=0)
        .order_by("title")
    )

    # ─────────────────────────────────────────────
    # Handle POST
    # ─────────────────────────────────────────────
    if request.method == "POST":
        form = IssueBookForm(request.POST, library=library)

        if form.is_valid():
            cd         = form.cleaned_data
            member     = cd["member"]
            book       = cd["book"]
            issue_date = cd["issue_date"]

            due_date = issue_date + timedelta(days=borrowing_period)

            with db_transaction.atomic():
                txn = Transaction.objects.create(
                    library            = library,
                    member             = member,
                    book               = book,
                    issue_date         = issue_date,
                    due_date           = due_date,
                    loan_duration_days = borrowing_period,
                    fine_rate_per_day  = fine_rate_per_day,
                    status             = Transaction.STATUS_ISSUED,
                    issued_by          = request.user.get_full_name() or request.user.username,
                    notes              = cd.get("notes", ""),
                )

                book.available_copies = max(0, book.available_copies - 1)
                book.save(update_fields=["available_copies"])

            messages.success(
                request,
                f'"{book.title}" issued to {member.first_name} {member.last_name}. '
                f'Due: {due_date.strftime("%d %B %Y")}',
            )
            return redirect("transactions:transaction_detail", pk=txn.pk)

        else:
            # Surface form validation errors as page messages
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, e)

    else:
        form = IssueBookForm(library=library)

    # ─────────────────────────────────────────────
    # Render
    # ─────────────────────────────────────────────
    return render(request, "transactions/issue_book.html", {
        "form":                 form,
        "members":              members,
        "books":                books,
        "today":                today.isoformat(),
        "default_due_date":     default_due_date,
        "rules":                rules,
        "fine_rate_per_day":    fine_rate_per_day,
        "default_loan_days":    borrowing_period,
        "max_books_per_member": max_books_per_member,
        "max_renewal_count":    max_renewal_count,
    })

# ─────────────────────────────────────────────────────────────────────────────
# 4. Return Book
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def return_book(request, pk):
    library = _get_library_or_404(request)
    txn = get_object_or_404(
        Transaction.objects.for_library(library).select_related("member", "book"),
        pk=pk,
    )

    if txn.status == Transaction.STATUS_RETURNED:
        messages.info(request, "This book has already been returned.")
        return redirect("transactions:transaction_detail", pk=txn.pk)

    today = date.today()

    if request.method == "POST":
        form = ReturnBookForm(request.POST)
        if form.is_valid():
            cd            = form.cleaned_data
            damage_charge = cd.get("damage_charge") or Decimal("0.00")

            with db_transaction.atomic():
                txn.return_date      = today
                txn.return_condition = cd["condition"]
                txn.damage_charge    = damage_charge
                txn.return_notes     = cd.get("return_notes", "")
                txn.status           = Transaction.STATUS_RETURNED
                txn.returned_to      = request.user.get_full_name() or request.user.username

                if cd.get("fine_paid_now") and txn.fine_amount > 0:
                    txn.fine_paid      = True
                    txn.fine_paid_date = today

                txn.save()

                book = txn.book
                book.available_copies = min(book.total_copies, book.available_copies + 1)
                book.save(update_fields=["available_copies"])

                fine_status = Fine.STATUS_PAID if txn.fine_paid else Fine.STATUS_UNPAID
                fine_date   = today if txn.fine_paid else None

                if txn.overdue_fine > 0:
                    Fine.objects.create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_OVERDUE,
                        amount      = txn.overdue_fine,
                        status      = fine_status,
                        paid_date   = fine_date,
                    )
                if damage_charge > 0:
                    Fine.objects.create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_DAMAGE,
                        amount      = damage_charge,
                        status      = fine_status,
                        paid_date   = fine_date,
                    )

            messages.success(request, f'"{txn.book.title}" returned successfully.')
            return redirect("transactions:transaction_detail", pk=txn.pk)
    else:
        form = ReturnBookForm(initial={
            "transaction_id": txn.pk,
            "return_date":    today.isoformat(),
        })

    max_fine_display = Decimal("500.00")
    fine_pct = (
        min(100, int((txn.fine_amount / max_fine_display) * 100))
        if txn.fine_amount else 0
    )

    return render(request, "transactions/return_book.html", {
        "transaction": txn,
        "form":        form,
        "today":       today,
        "fine_pct":    fine_pct,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 5. Renew Book
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def renew_book(request, pk):
    """
    Extends the due date by the original loan_duration_days from today.
    Respects the library's max_renewal_count setting.
    POST only — no dedicated template needed; redirect back to detail.
    """
    if request.method != "POST":
        return redirect("transactions:transaction_detail", pk=pk)

    library = _get_library_or_404(request)
    txn = get_object_or_404(
        Transaction.objects.for_library(library),
        pk=pk,
    )

    if txn.status not in (Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE):
        messages.error(request, "Only active or overdue loans can be renewed.")
        return redirect("transactions:transaction_detail", pk=pk)

    rules        = _get_library_rules(library)
    max_renewals = getattr(rules, "max_renewal_count", 1)

    if txn.renewal_count >= max_renewals:
        messages.error(
            request,
            f"Maximum renewals ({max_renewals}) already reached for this loan."
        )
        return redirect("transactions:transaction_detail", pk=pk)

    new_due           = date.today() + timedelta(days=txn.loan_duration_days)
    txn.due_date      = new_due
    txn.renewal_count += 1
    txn.status        = Transaction.STATUS_ISSUED   # clear overdue flag
    txn.save(update_fields=["due_date", "renewal_count", "status", "updated_at"])

    messages.success(
        request,
        f'Loan renewed. New due date: {new_due.strftime("%d %B %Y")} '
        f'(renewal {txn.renewal_count}/{max_renewals}).',
    )
    return redirect("transactions:transaction_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Overdue List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def overdue_list(request):
    library = _get_library_or_404(request)
    Transaction.sync_overdue_for_library(library)

    qs = (
        Transaction.objects.for_library(library)
        .filter(status=Transaction.STATUS_OVERDUE)
        .select_related("member", "book")
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(member__first_name__icontains=q)
            | Q(member__last_name__icontains=q)
            | Q(book__title__icontains=q)
        )

    severity = request.GET.get("severity", "")
    today    = date.today()
    if severity == "mild":
        qs = qs.filter(due_date__gte=today - timedelta(days=7))
    elif severity == "moderate":
        qs = qs.filter(
            due_date__range=(today - timedelta(days=30), today - timedelta(days=8))
        )
    elif severity == "severe":
        qs = qs.filter(due_date__lt=today - timedelta(days=30))

    overdue_transactions = list(qs.order_by("due_date"))

    sort = request.GET.get("sort", "")
    if sort == "overdue_days":
        overdue_transactions.sort(key=lambda t: t.overdue_days)
    elif sort == "-fine_amount":
        overdue_transactions.sort(key=lambda t: t.fine_amount, reverse=True)
    else:
        # default: most overdue first (-overdue_days)
        overdue_transactions.sort(key=lambda t: t.overdue_days, reverse=True)
    total_fine = sum(t.fine_amount for t in overdue_transactions)

    return render(request, "transactions/overdue_list.html", {
        "overdue_transactions": overdue_transactions,
        "total_fine":           total_fine,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. Fine List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def fine_list(request):
    library = _get_library_or_404(request)
    qs = (
        Fine.objects.for_library(library)
        .select_related("transaction__member", "transaction__book")
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(transaction__member__first_name__icontains=q)
            | Q(transaction__member__last_name__icontains=q)
            | Q(transaction__pk__icontains=q)
        )

    status = request.GET.get("status", "").strip()
    if status in (Fine.STATUS_UNPAID, Fine.STATUS_PAID, Fine.STATUS_WAIVED):
        qs = qs.filter(status=status)

    fine_type = request.GET.get("type", "").strip()
    if fine_type in (Fine.TYPE_OVERDUE, Fine.TYPE_LOST, Fine.TYPE_DAMAGE):
        qs = qs.filter(fine_type=fine_type)

    date_from = request.GET.get("date_from", "")
    date_to   = request.GET.get("date_to", "")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    base = Fine.objects.for_library(library)

    def _agg(subqs):
        return subqs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    total_fine       = _agg(base)
    total_fine_count = base.count()
    unpaid_qs        = base.filter(status=Fine.STATUS_UNPAID)
    unpaid_fine      = _agg(unpaid_qs)
    unpaid_count     = unpaid_qs.count()
    paid_qs          = base.filter(status=Fine.STATUS_PAID)
    paid_fine        = _agg(paid_qs)
    paid_count       = paid_qs.count()
    waived_qs        = base.filter(status=Fine.STATUS_WAIVED)
    waived_fine      = _agg(waived_qs)
    waived_count     = waived_qs.count()

    paginator = Paginator(qs.order_by("-created_at"), 25)
    fines     = paginator.get_page(request.GET.get("page", 1))

    return render(request, "transactions/fine_list.html", {
        "fines":            fines,
        "total_fine":       total_fine,
        "total_fine_count": total_fine_count,
        "unpaid_fine":      unpaid_fine,
        "unpaid_count":     unpaid_count,
        "paid_fine":        paid_fine,
        "paid_count":       paid_count,
        "waived_fine":      waived_fine,
        "waived_count":     waived_count,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 8. Mark Fine Paid  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mark_fine_paid(request, pk=None):
    if request.method != "POST":
        return redirect("transactions:fine_list")

    library = _get_library_or_404(request)
    form    = MarkFinePaidForm(request.POST)

    if form.is_valid():
        cd   = form.cleaned_data
        fine = get_object_or_404(Fine.objects.for_library(library), pk=cd["fine_id"])
        if fine.status == Fine.STATUS_UNPAID:
            fine.mark_paid(
                method=cd["payment_method"],
                ref=cd.get("payment_ref", ""),
            )
            messages.success(request, f"Fine of ₹{fine.amount} marked as paid.")
        else:
            messages.warning(request, "Fine is already paid or waived.")
    else:
        messages.error(request, "Invalid form submission.")

    return redirect(request.POST.get("next") or reverse("transactions:fine_list"))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Waive Fine  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def waive_fine(request, pk):
    """Waive a single fine row. POST only."""
    if request.method != "POST":
        return redirect("transactions:fine_list")

    library = _get_library_or_404(request)
    fine    = get_object_or_404(Fine.objects.for_library(library), pk=pk)

    if fine.status == Fine.STATUS_UNPAID:
        fine.waive()
        messages.success(request, f"Fine of ₹{fine.amount} has been waived.")
    else:
        messages.warning(request, "Only unpaid fines can be waived.")

    return redirect(request.POST.get("next") or reverse("transactions:fine_list"))


# ─────────────────────────────────────────────────────────────────────────────
# 10. Missing / Lost Books
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def missing_books(request):
    library = _get_library_or_404(request)
    qs = (
        MissingBook.objects.for_library(library)
        .select_related("transaction__member", "book")
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(book__title__icontains=q)
            | Q(book__isbn__icontains=q)
            | Q(transaction__member__first_name__icontains=q)
            | Q(transaction__member__last_name__icontains=q)
        )

    status = request.GET.get("status", "").strip()
    if status in (
        MissingBook.STATUS_MISSING,
        MissingBook.STATUS_LOST,
        MissingBook.STATUS_RECOVERED,
    ):
        qs = qs.filter(status=status)

    penalty = request.GET.get("penalty", "").strip()
    if penalty == "pending":
        qs = qs.filter(penalty_amount__gt=0, penalty_paid=False)
    elif penalty == "paid":
        qs = qs.filter(penalty_paid=True)

    base            = MissingBook.objects.for_library(library)
    lost_count      = base.filter(status=MissingBook.STATUS_LOST).count()
    missing_count   = base.filter(status=MissingBook.STATUS_MISSING).count()
    recovered_count = base.filter(status=MissingBook.STATUS_RECOVERED).count()
    total_penalty   = base.aggregate(t=Sum("penalty_amount"))["t"] or Decimal("0.00")

    return render(request, "transactions/missing_books.html", {
        "missing_books":   qs.order_by("-created_at"),
        "lost_count":      lost_count,
        "missing_count":   missing_count,
        "recovered_count": recovered_count,
        "total_penalty":   total_penalty,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 11. Mark Lost  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mark_lost(request, pk=None):
    if request.method != "POST":
        return redirect("transactions:missing_books")

    library = _get_library_or_404(request)
    form    = MarkLostForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Invalid submission.")
        return redirect("transactions:missing_books")

    txn = get_object_or_404(
        Transaction.objects.for_library(library),
        pk=form.cleaned_data["transaction_id"],
    )

    if txn.status == Transaction.STATUS_RETURNED:
        messages.error(request, "Cannot mark a returned transaction as lost.")
        return redirect("transactions:missing_books")

    with db_transaction.atomic():
        txn.status    = Transaction.STATUS_LOST
        txn.lost_date = date.today()
        txn.notes     = form.cleaned_data.get("notes", "")
        txn.save(update_fields=["status", "lost_date", "notes", "updated_at"])

        # Reduce total_copies — one physical copy is permanently gone
        book = txn.book
        book.total_copies = max(0, book.total_copies - 1)
        # available_copies should not exceed total_copies after reduction
        book.available_copies = min(book.available_copies, book.total_copies)
        book.save(update_fields=["total_copies", "available_copies"])

        MissingBook.objects.update_or_create(
            transaction=txn,
            defaults={
                "library":       library,
                "book":          book,
                "status":        MissingBook.STATUS_LOST,
                "reported_date": date.today(),
                "notes":         form.cleaned_data.get("notes", ""),
            },
        )

    messages.success(request, f'"{txn.book.title}" marked as lost.')
    return redirect("transactions:missing_books")


# ─────────────────────────────────────────────────────────────────────────────
# 12. Mark Recovered  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def mark_recovered(request, pk):
    """
    Flip a MissingBook record to 'recovered'.
    Restores the book's total_copies and available_copies.
    POST only.
    """
    if request.method != "POST":
        return redirect("transactions:missing_books")

    library = _get_library_or_404(request)
    missing = get_object_or_404(
        MissingBook.objects.for_library(library).select_related("book"),
        pk=pk,
    )

    if missing.status == MissingBook.STATUS_RECOVERED:
        messages.info(request, "Book is already marked as recovered.")
        return redirect("transactions:missing_books")

    with db_transaction.atomic():
        missing.status = MissingBook.STATUS_RECOVERED
        missing.save(update_fields=["status", "updated_at"])

        book = missing.book
        book.total_copies     += 1
        book.available_copies += 1
        book.save(update_fields=["total_copies", "available_copies"])

    messages.success(request, f'"{missing.book.title}" marked as recovered.')
    return redirect("transactions:missing_books")


# ─────────────────────────────────────────────────────────────────────────────
# 13. Add / Update Penalty  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def add_penalty(request, pk=None):
    if request.method != "POST":
        return redirect("transactions:missing_books")

    library = _get_library_or_404(request)
    form    = AddPenaltyForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Invalid penalty form.")
        return redirect("transactions:missing_books")

    cd      = form.cleaned_data
    missing = get_object_or_404(
        MissingBook.objects.for_library(library),
        pk=cd["missing_id"],
    )

    missing.penalty_amount = cd["penalty_amount"]
    missing.penalty_reason = cd["penalty_reason"]
    if cd.get("notes"):
        missing.notes = cd["notes"]
    missing.save(update_fields=["penalty_amount", "penalty_reason", "notes", "updated_at"])

    Fine.objects.update_or_create(
        library     = library,
        transaction = missing.transaction,
        fine_type   = Fine.TYPE_LOST,
        defaults    = {"amount": cd["penalty_amount"], "status": Fine.STATUS_UNPAID},
    )

    messages.success(request, f"Penalty of ₹{cd['penalty_amount']} applied.")
    return redirect("transactions:missing_books")


# ─────────────────────────────────────────────────────────────────────────────
# 14. Member Search API  (AJAX / JSON)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_search_api(request):
    """
    GET /transactions/api/members/?q=...
    Returns JSON list of active members matching the query.
    Used by the issue-book page autocomplete.
    """
    library = _get_library_or_404(request)
    owner   = library.user

    from members.models import Member

    q = request.GET.get("q", "").strip()
    qs = Member.objects.filter(owner=owner, status="active")

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(member_id__icontains=q)
            | Q(email__icontains=q)
        )

    # Borrow limit comes from MemberSettings (same source as issue_book view)
    try:
        from accounts.models import MemberSettings
        member_settings = MemberSettings.objects.get(library=library)
        borrow_limit    = int(member_settings.borrow_limit or 0)
    except Exception:
        borrow_limit = 0

    members_list = list(qs.order_by("first_name", "last_name")[:20])

    # Bulk-fetch active loan counts in one query to avoid N+1.
    from django.db.models import Count
    active_counts = {
        row["member_id"]: row["cnt"]
        for row in Transaction.objects.for_library(library).filter(
            member__in=members_list,
            status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE),
        ).values("member_id").annotate(cnt=Count("id"))
    }

    results = [
        {
            "id":           m.pk,
            "name":         f"{m.first_name} {m.last_name}".strip(),
            "member_id":    m.member_id,
            "active_loans": active_counts.get(m.pk, 0),
            "borrow_limit": borrow_limit,
        }
        for m in members_list
    ]
    return JsonResponse({"results": results})


# ─────────────────────────────────────────────────────────────────────────────
# 15. Book Search API  (AJAX / JSON)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def book_search_api(request):
    """
    GET /transactions/api/books/?q=...
    Returns JSON list of available books matching the query.
    Used by the issue-book page autocomplete.
    """
    library = _get_library_or_404(request)
    owner   = library.user

    from books.models import Book

    q = request.GET.get("q", "").strip()
    qs = Book.objects.filter(owner=owner, available_copies__gt=0)

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(isbn__icontains=q)
            | Q(book_id__icontains=q)
        )

    results = [
        {
            "id":               b.pk,
            "title":            b.title,
            "author":           b.author,
            "isbn":             b.isbn,
            "book_id":          b.book_id,
            "available_copies": b.available_copies,
        }
        for b in qs.order_by("title")[:20]
    ]
    return JsonResponse({"results": results})