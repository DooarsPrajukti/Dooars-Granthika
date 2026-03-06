"""
transactions/views.py

Tenant resolution:  request.user.library  (OneToOneField on accounts.Library)

books.Book and members.Member are scoped by  owner = FK(User) —
the library admin's User object.  We resolve this as  library.user.

Transaction / Fine / MissingBook are scoped by  library = FK(Library)
and queried via  Model.objects.for_library(library).

Overdue sync strategy
─────────────────────
A background daemon thread in fine_sync.py runs
Transaction.sync_overdue_for_library() for every library every
FINE_SYNC_INTERVAL seconds (default 60 s).

Views call _sync_overdue_if_stale(library) instead of the raw
sync method.  That helper is a no-op when the background thread
has already synced within the last STALE_THRESHOLD_SECONDS — so
page loads never wait for a slow bulk UPDATE in the hot path.
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
import time

from .forms import (
    AddPenaltyForm,
    IssueBookForm,
    MarkFinePaidForm,
    MarkLostForm,
    ReturnBookForm,
)
from finance.models import Fine
from .models import MissingBook, Transaction


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




def _get_borrow_limit(library, member=None):
    """
    Return the borrow limit for a member based on their role.
    Reads student_borrow_limit / teacher_borrow_limit from LibraryRuleSettings.
    Falls back to MemberSettings.borrow_limit, then 0 (unlimited).
    """
    role = getattr(member, "role", "") if member else ""

    # Primary: role-specific limits on LibraryRuleSettings
    try:
        rules = library.rules
        if role in ("teacher", "faculty", "staff"):
            limit = getattr(rules, "teacher_borrow_limit", None)
        else:
            # student / guest / other
            limit = getattr(rules, "student_borrow_limit", None)

        # Fall back to max_books_per_member if role-specific field is NULL
        if limit is None:
            limit = getattr(rules, "max_books_per_member", None)
        if limit is not None:
            return int(limit)
    except Exception:
        pass

    # Secondary: MemberSettings.borrow_limit
    try:
        from accounts.models import MemberSettings
        ms = MemberSettings.objects.get(library=library)
        limit = ms.borrow_limit
        if limit:
            return int(limit)
    except Exception:
        pass

    return 0  # 0 = no limit configured

# ── Throttled overdue sync ────────────────────────────────────────────────────
# Track the last time we ran a sync per library (library.pk → epoch float).
# This lives in process memory — resets on server restart, which is fine.
_last_sync: dict[int, float] = {}

# If the background thread hasn't run a sync within this many seconds since
# the last view-level sync, do a synchronous sync on the next page load.
# Keep this > FINE_SYNC_INTERVAL so the background thread almost always wins.
STALE_THRESHOLD_SECONDS: int = 90


def _sync_overdue_if_stale(library) -> None:
    """
    Run sync_overdue_for_library only when the last known sync is older
    than STALE_THRESHOLD_SECONDS.  The background thread normally keeps
    data fresh so this is a no-op on the vast majority of requests.
    """
    now = time.monotonic()
    last = _last_sync.get(library.pk, 0.0)
    if now - last >= STALE_THRESHOLD_SECONDS:
        Transaction.sync_overdue_for_library(library)
        _last_sync[library.pk] = now


# ─────────────────────────────────────────────────────────────────────────────
# 1. Transaction List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def transaction_list(request):
    library = _get_library_or_404(request)

    # Sync overdue status — background thread handles this every 60 s;
    # _sync_overdue_if_stale is a no-op when data is already fresh.
    _sync_overdue_if_stale(library)

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

    borrow_limit = _get_borrow_limit(library, txn.member)

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

    # Borrow limit — read role-specific limit from LibraryRuleSettings.
    # We don't know the member's role at page-load time, so use the
    # student limit as the conservative default for the policy card.
    # The per-member slot count is computed accurately after ID lookup.
    max_books_per_member = _get_borrow_limit(library)

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
        _limit = _get_borrow_limit(library, m)
        if _limit:
            m.slots_available = max(0, _limit - m.active_loans_count)
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
            book_copy  = cd.get("book_copy")
            issue_date = cd["issue_date"]

            due_date = issue_date + timedelta(days=borrowing_period)

            with db_transaction.atomic():
                txn = Transaction.objects.create(
                    library            = library,
                    member             = member,
                    book               = book,
                    book_copy          = book_copy,
                    issue_date         = issue_date,
                    due_date           = due_date,
                    loan_duration_days = borrowing_period,
                    fine_rate_per_day  = fine_rate_per_day,
                    status             = Transaction.STATUS_ISSUED,
                    issued_by          = request.user.get_full_name() or request.user.username,
                    notes              = cd.get("notes", ""),
                )

                # Mark the specific copy as issued
                if book_copy is not None:
                    book_copy.status = "issued"
                    book_copy.save(update_fields=["status"])
                else:
                    # Fallback: decrement available_copies on the Book directly
                    if hasattr(book, "available_copies"):
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

                # Mark the specific copy available again on return
                book = txn.book
                from books.models import BookCopy as _BookCopy
                try:
                    copy_to_return = txn.book_copy or (
                        _BookCopy.objects
                        .filter(book=book, status="issued")
                        .order_by("updated_at")
                        .first()
                    )
                    if copy_to_return:
                        copy_to_return.status = "available"
                        copy_to_return.save(update_fields=["status"])
                except Exception:
                    pass
                # Keep Book.available_copies in sync if that field exists
                if hasattr(book, "available_copies") and hasattr(book, "total_copies"):
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

    # Block renewal if this transaction has any unpaid fines
    unpaid_fines = txn.fines.filter(status=Fine.STATUS_UNPAID)
    if unpaid_fines.exists():
        total_due = unpaid_fines.aggregate(t=Sum("amount"))["t"]
        messages.error(
            request,
            f"Cannot renew — this loan has an outstanding fine of ₹{total_due}. "
            f"Please clear the fine before renewing."
        )
        return redirect("transactions:transaction_detail", pk=pk)

    # Also block if overdue fine exists as a computed property (not yet a saved Fine row)
    if txn.fine_amount > 0:
        messages.error(
            request,
            f"Cannot renew — this loan has an outstanding fine of ₹{txn.fine_amount}. "
            f"Please clear the fine before renewing."
        )
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
    _sync_overdue_if_stale(library)

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
# 18. Book Cover  (serves / redirects to the book cover image)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def book_cover_api(request, pk):
    """
    GET /transactions/api/book-cover/<pk>/
    Redirects to the book's cover image URL, or returns 404 if none.
    Used by <img src="..."> in the issue-book page.
    """
    from django.http import HttpResponseRedirect, HttpResponseNotFound
    from books.models import Book

    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return HttpResponseNotFound()

    for _field in ("cover", "cover_image", "cover_photo", "image",
                   "thumbnail", "book_cover", "photo"):
        _val = getattr(book, _field, None)
        if _val:
            try:
                if hasattr(_val, "name") and _val.name:
                    return HttpResponseRedirect(_val.url)
            except Exception:
                pass

    return HttpResponseNotFound()

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

    # Per-member borrow limit is role-specific; computed per member below.

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
            "borrow_limit": _get_borrow_limit(library, m),
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


# ─────────────────────────────────────────────────────────────────────────────
# 16. Member Lookup by exact member_id  (AJAX / JSON)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_lookup_api(request):
    """
    GET /transactions/api/member-lookup/?member_id=DGDGRST0326001
    Returns a single member's details or {"found": false}.
    Used by the issue-book page to preview the member after the field is filled.
    """
    library = _get_library_or_404(request)
    owner   = library.user

    from members.models import Member

    raw_id = request.GET.get("member_id", "").strip().upper()
    if not raw_id:
        return JsonResponse({"found": False, "error": "No member_id supplied."})

    try:
        member = Member.objects.get(member_id=raw_id, owner=owner)
    except Member.DoesNotExist:
        return JsonResponse({"found": False, "error": f'Member ID "{raw_id}" not found.'})

    # Active loan count + role-specific borrow limit
    borrow_limit = _get_borrow_limit(library, member)

    from django.db.models import Count, Sum, DecimalField as _DF
    active_loans = (
        Transaction.objects.for_library(library)
        .filter(member=member, status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE))
        .count()
    )
    from finance.models import Fine as _Fine
    total_due = (
        _Fine.objects.for_library(library)
        .filter(transaction__member=member, status=_Fine.STATUS_UNPAID)
        .aggregate(t=Sum("amount", output_field=_DF()))["t"]
        or Decimal("0.00")
    )

    slots = max(0, borrow_limit - active_loans) if borrow_limit else -1

    # Build photo URL — check if member actually has a photo file,
    # then return its absolute URL. Falls back to None so the JS
    # shows the initial-letter avatar instead of a broken image.
    photo_url = None
    # First try common ImageField names to see if a file is actually set
    for _field in ("photo", "profile_photo", "avatar", "profile_picture",
                   "image", "profile_image"):
        _val = getattr(member, _field, None)
        if _val:
            try:
                # Check the file actually has a name (not empty/default)
                if hasattr(_val, "name") and _val.name:
                    photo_url = request.build_absolute_uri(_val.url)
                    break
            except Exception:
                pass
    # If no direct field found, try the members:member_photo URL as fallback
    if not photo_url:
        try:
            from django.urls import reverse
            photo_url = request.build_absolute_uri(
                reverse("members:member_photo", args=[member.pk])
            )
        except Exception:
            pass

    return JsonResponse({
        "found":        True,
        "pk":           member.pk,
        "member_id":    member.member_id,
        "name":         f"{member.first_name} {member.last_name}".strip(),
        "role":         member.get_role_display() if hasattr(member, "get_role_display") else "",
        "email":        member.email or "",
        "status":       member.status,
        "active_loans": active_loans,
        "borrow_limit": borrow_limit,
        "slots":        slots,
        "total_due":    str(total_due),
        "photo_url":    photo_url,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 17. Book Lookup by exact book_id  (AJAX / JSON)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def book_lookup_api(request):
    """
    GET /transactions/api/book-lookup/?book_id=DGDGRBK0326001

    Looks up a BookCopy by its copy_id (books_bookcopy table), then returns
    details of the parent Book so the issue-book page can preview it.
    """
    import traceback

    try:
        library = _get_library_or_404(request)
        owner   = library.user

        from books.models import Book, BookCopy

        raw_id = request.GET.get("book_id", "").strip()
        if not raw_id:
            return JsonResponse({"found": False, "error": "No book_id supplied."})

        # ── Step 1: find the BookCopy row ─────────────────────────────
        try:
            copy = (
                BookCopy.objects
                .select_related("book")
                .get(copy_id=raw_id, book__owner=owner)
            )
        except BookCopy.DoesNotExist:
            return JsonResponse({"found": False, "error": f'Book copy ID "{raw_id}" not found.'})
        except Exception as e:
            return JsonResponse({"found": False, "error": f"[copy lookup] {type(e).__name__}: {e}"})

        # ── Step 2: get the parent Book ───────────────────────────────
        book = copy.book

        # ── Step 3: availability — count available copies for this book
        try:
            available_copies = (
                BookCopy.objects
                .filter(book=book, status="available")
                .count()
            )
            total_copies = BookCopy.objects.filter(book=book).count()
        except Exception:
            available_copies = getattr(book, "available_copies", 0) or 0
            total_copies     = getattr(book, "total_copies", available_copies) or available_copies

        # ── Step 4: category ─────────────────────────────────────────
        try:
            category_name = book.category.name if getattr(book, "category_id", None) else ""
        except Exception:
            category_name = ""

        # ── Step 5: cover image ──────────────────────────────────────
        # cover_image is a BLOB — served via book_cover_image view.
        cover_url = None
        try:
            if getattr(book, "cover_image", None):
                from django.urls import reverse as _reverse
                cover_url = request.build_absolute_uri(
                    _reverse("transactions:book_cover_image", args=[book.pk])
                )
        except Exception:
            pass

        return JsonResponse({
            "found":            True,
            "pk":               book.pk,
            "copy_pk":          copy.pk,
            "book_id":          raw_id,
            "title":            getattr(book, "title",  "") or "",
            "author":           getattr(book, "author", "") or "",
            "isbn":             getattr(book, "isbn",   "") or "",
            "available_copies": available_copies,
            "total_copies":     total_copies,
            "category":         category_name,
            "cover_url":        cover_url,
            "copy_status":      getattr(copy, "status",    ""),
            "copy_condition":   getattr(copy, "condition", ""),
        })

    except Exception as exc:
        err_detail = traceback.format_exc()
        import logging
        logging.getLogger("transactions.views").error(
            "book_lookup_api unexpected error: %s", err_detail
        )
        return JsonResponse(
            {"found": False, "error": f"Server error: {type(exc).__name__}: {exc}"},
            status=200,
        )

# ─────────────────────────────────────────────────────────────────────────────
# 18. Book Cover Image  — serves BLOB from books_book.cover_image
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def book_cover_image(request, pk):
    """
    GET /transactions/api/book-cover/<pk>/
    Streams books_book.cover_image (BLOB) as an HTTP image response.
    Falls back to 404 if no cover is stored.
    """
    from books.models import Book
    from django.http import HttpResponse, Http404

    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        raise Http404

    cover = getattr(book, "cover_image", None)
    if not cover:
        raise Http404

    # cover_image may be a BinaryField (bytes) or a FileField
    if isinstance(cover, (bytes, memoryview)):
        data      = bytes(cover)
        mime_type = getattr(book, "cover_mime_type", None) or "image/jpeg"
    else:
        # FileField / ImageField
        try:
            data      = cover.read()
            mime_type = getattr(book, "cover_mime_type", None) or "image/jpeg"
        except Exception:
            raise Http404

    if not data:
        raise Http404

    response = HttpResponse(data, content_type=mime_type)
    response["Cache-Control"] = "private, max-age=86400"
    return response