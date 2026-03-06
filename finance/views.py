# finance/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from decimal import Decimal
from datetime import date

from .models import Fine, Payment, Expense


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


# ─────────────────────────────────────────────────────────────────────────────
# Process Payment  (shows fine details + cash form)
# Auto-selects member and total fine from ?fine_id= query param
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def process_payment(request):
    library = _get_library_or_404(request)

    fine_id   = request.GET.get("fine_id") or request.POST.get("fine_id")
    member_id = request.GET.get("member_id") or request.POST.get("member_id")

    fine             = None
    member           = None
    all_unpaid_fines = []
    total_fine       = Decimal("0.00")

    # ── Resolve by fine pk (most specific) ───────────────────────────────────
    if fine_id:
        fine = get_object_or_404(
            Fine.objects.for_library(library).select_related(
                "transaction__member", "transaction__book"
            ),
            pk=fine_id,
        )
        member = fine.transaction.member

    # ── Resolve by member_id (from dropdown when no fine_id given) ───────────
    elif member_id:
        from members.models import Member
        member = get_object_or_404(Member, pk=member_id, owner=library.user)

    # ── If we have a member, load all their unpaid fines ─────────────────────
    if member:
        all_unpaid_fines = (
            Fine.objects
            .for_library(library)
            .filter(
                transaction__member=member,
                status=Fine.STATUS_UNPAID,
            )
            .select_related("transaction__book")
            .order_by("-created_at")
        )
        total_fine = (
            all_unpaid_fines.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        )
        if not fine and all_unpaid_fines.exists():
            fine = all_unpaid_fines.first()

    # ── Build member list: members who have unpaid fines ─────────────────────
    from members.models import Member
    members_with_fines = (
        Member.objects
        .filter(
            owner=library.user,
            issue_transactions__library=library,
            issue_transactions__fines__status=Fine.STATUS_UNPAID,
        )
        .distinct()
        .order_by("first_name", "last_name")
    )

    return render(request, "finance/process_payment.html", {
        "fine":               fine,
        "member":             member,
        "all_unpaid_fines":   all_unpaid_fines,
        "total_fine":         total_fine,
        "fine_id":            fine.pk if fine else "",
        "member_id":          member.pk if member else "",
        "members_with_fines": members_with_fines,
        "payment_method_choices": Fine.PAYMENT_METHOD_CHOICES,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cash Payment  (POST — creates Payment, marks fine paid)
# All fine data is read directly from finance_fine table
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def cash_payment(request):
    if request.method != "POST":
        return redirect("finance:process_payment")

    library = _get_library_or_404(request)

    fine_id         = request.POST.get("fine_id")
    pay_all         = request.POST.get("pay_all") == "1"
    method          = request.POST.get("method", "cash")
    transaction_ref = request.POST.get("transaction_ref", "").strip()

    # ── Load the anchor fine (validates library scope) ────────────────────────
    fine = get_object_or_404(
        Fine.objects.for_library(library).select_related(
            "transaction__member", "transaction__book"
        ),
        pk=fine_id,
    )
    member = fine.transaction.member

    # ── Decide which fines to settle ─────────────────────────────────────────
    if pay_all:
        fines_to_pay = (
            Fine.objects
            .for_library(library)
            .filter(transaction__member=member, status=Fine.STATUS_UNPAID)
        )
    else:
        fines_to_pay = (
            Fine.objects
            .for_library(library)
            .filter(pk=fine.pk, status=Fine.STATUS_UNPAID)
        )

    total_amount = fines_to_pay.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    if total_amount == Decimal("0.00"):
        messages.warning(request, "No unpaid fines to collect.")
        return redirect("finance:process_payment")

    # ── Generate receipt number ───────────────────────────────────────────────
    today_str = timezone.now().strftime("%Y%m%d")
    last_payment = (
        Payment.objects
        .filter(receipt_number__startswith=f"RCP-{today_str}")
        .order_by("-receipt_number")
        .first()
    )
    try:
        last_seq = int(last_payment.receipt_number.split("-")[-1]) if last_payment else 0
    except (ValueError, AttributeError):
        last_seq = 0
    receipt_number = f"RCP-{today_str}-{last_seq + 1:04d}"

    # ── Create Payment record ─────────────────────────────────────────────────
    # fine FK on Payment links to the anchor fine (finance_fine.id)
    payment = Payment.objects.create(
        fine               = fine,                      # FK → finance_fine
        amount             = total_amount,
        method             = method,
        status             = "success",
        receipt_number     = receipt_number,
        collected_by       = request.user.get_full_name() or request.user.username,
        library            = library,
        transaction_date   = timezone.now(),
        gateway_order_id   = str(fine.transaction.pk),  # transactions_transaction.id
        gateway_payment_id = transaction_ref or receipt_number,
    )

    # ── Mark fines as paid in finance_fine ───────────────────────────────────
    today = date.today()
    fines_to_pay.update(
        status         = Fine.STATUS_PAID,
        paid_date      = today,
        payment_method = method,
        payment_ref    = transaction_ref or receipt_number,
    )

    # ── Also mark fine_paid flag on the parent transaction(s) ────────────────
    from transactions.models import Transaction
    txn_ids = list(fines_to_pay.values_list("transaction_id", flat=True))
    Transaction.objects.filter(pk__in=txn_ids).update(
        fine_paid      = True,
        fine_paid_date = today,
    )

    messages.success(
        request,
        f"₹{total_amount} collected from "
        f"{member.first_name} {member.last_name}. "
        f"Receipt: {receipt_number}",
    )
    return redirect("finance:payment_receipt", payment_id=payment.pk)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Receipt
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_receipt(request, payment_id):
    library = _get_library_or_404(request)
    payment = get_object_or_404(
        Payment.objects.select_related(
            "fine__transaction__member",
            "fine__transaction__book",
        ),
        pk=payment_id,
        library=library,
    )

    # Derive member and transaction from the fine FK (finance_fine → transactions_transaction)
    txn    = None
    member = None
    fines  = []

    if payment.fine:
        txn    = payment.fine.transaction
        member = txn.member if txn else None

        # All fines settled in the same payment session (same member, same paid_date,
        # same payment_ref)
        fines = (
            Fine.objects
            .for_library(library)
            .filter(
                transaction__member=member,
                paid_date=payment.fine.paid_date,
                payment_ref=payment.fine.payment_ref,
                status=Fine.STATUS_PAID,
            )
            .select_related("transaction__book")
        )

    return render(request, "finance/payment_receipt.html", {
        "payment":     payment,
        "transaction": txn,
        "member":      member,
        "fines":       fines,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Confirm Recovery  (legacy redirect)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def confirm_recovery(request, fine_id):
    from django.urls import reverse
    return redirect(reverse("finance:process_payment") + f"?fine_id={fine_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Waive Fine  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def waive_fine(request, fine_id):
    if request.method != "POST":
        return redirect("transactions:fine_list")

    library = _get_library_or_404(request)
    fine = get_object_or_404(
        Fine.objects.for_library(library).select_related("transaction__member"),
        pk=fine_id,
    )

    if fine.status == Fine.STATUS_UNPAID:
        fine.status    = Fine.STATUS_WAIVED
        fine.paid_date = date.today()
        fine.save(update_fields=["status", "paid_date", "updated_at"])
        messages.success(
            request,
            f"Fine of ₹{fine.amount} waived for "
            f"{fine.transaction.member.first_name} "
            f"{fine.transaction.member.last_name}.",
        )
    else:
        messages.warning(request, "Only unpaid fines can be waived.")

    return redirect(request.POST.get("next") or "transactions:fine_list")


# ─────────────────────────────────────────────────────────────────────────────
# Income List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def income_list(request):
    library = _get_library_or_404(request)
    payments = (
        Payment.objects
        .filter(library=library, status="success")
        .select_related(
            "fine__transaction__member",
            "fine__transaction__book",
        )
        .order_by("-transaction_date")
    )
    total_income = payments.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    return render(request, "finance/income_list.html", {
        "payments":     payments,
        "total_income": total_income,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Expense List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def expense_list(request):
    library  = _get_library_or_404(request)
    expenses = (
        Expense.objects
        .filter(library=library)
        .order_by("-date", "-created_at")
    )
    total_expense = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    return render(request, "finance/expense_list.html", {
        "expenses":      expenses,
        "total_expense": total_expense,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Add / Edit Expense
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def add_expense(request, expense_id=None):
    library = _get_library_or_404(request)
    expense = None

    if expense_id:
        expense = get_object_or_404(Expense, pk=expense_id, library=library)

    if request.method == "POST":
        amount      = request.POST.get("amount")
        description = request.POST.get("description", "").strip()
        category    = request.POST.get("category", "")
        notes       = request.POST.get("notes", "").strip()
        exp_date    = request.POST.get("date") or date.today()

        if not amount or not description:
            messages.error(request, "Amount and description are required.")
        else:
            if expense:
                expense.amount      = amount
                expense.description = description
                expense.category    = category
                expense.notes       = notes
                expense.date        = exp_date
                expense.save()
                messages.success(request, "Expense updated.")
            else:
                Expense.objects.create(
                    library     = library,
                    amount      = amount,
                    description = description,
                    category    = category,
                    notes       = notes,
                    date        = exp_date,
                    recorded_by = request.user.get_full_name() or request.user.username,
                )
                messages.success(request, "Expense recorded.")
            return redirect("finance:expense_list")

    return render(request, "finance/add_expense.html", {
        "expense":    expense,
        "today":      date.today().isoformat(),
        "categories": Expense.CATEGORY_CHOICES,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Delete Expense
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def delete_expense(request, expense_id):
    library = _get_library_or_404(request)
    expense = get_object_or_404(Expense, pk=expense_id, library=library)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
    return redirect("finance:expense_list")


# ─────────────────────────────────────────────────────────────────────────────
# Finance Reports
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def finance_reports(request):
    library       = _get_library_or_404(request)
    total_income  = Payment.objects.filter(library=library, status="success").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    total_expense = Expense.objects.filter(library=library).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    net           = total_income - total_expense
    return render(request, "finance/finance_reports.html", {
        "total_income":  total_income,
        "total_expense": total_expense,
        "net":           net,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Daily Collection
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def daily_collection(request):
    library     = _get_library_or_404(request)
    report_date = request.GET.get("date", date.today().isoformat())
    payments    = (
        Payment.objects
        .filter(library=library, status="success", transaction_date__date=report_date)
        .select_related(
            "fine__transaction__member",
            "fine__transaction__book",
        )
        .order_by("-transaction_date")
    )
    total = payments.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    return render(request, "finance/daily_collection.html", {
        "payments":    payments,
        "total":       total,
        "report_date": report_date,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cash Book
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def cash_book(request):
    library  = _get_library_or_404(request)
    payments = (
        Payment.objects
        .filter(library=library, status="success")
        .select_related("fine__transaction__member")
        .order_by("transaction_date")
    )
    expenses = Expense.objects.filter(library=library).order_by("date")
    return render(request, "finance/cash_book.html", {
        "payments": payments,
        "expenses": expenses,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Profit & Loss
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def profit_loss(request):
    library       = _get_library_or_404(request)
    total_income  = Payment.objects.filter(library=library, status="success").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    total_expense = Expense.objects.filter(library=library).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    return render(request, "finance/profit_loss.html", {
        "total_income":  total_income,
        "total_expense": total_expense,
        "net_profit":    total_income - total_expense,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def audit_log(request):
    library  = _get_library_or_404(request)
    payments = (
        Payment.objects
        .filter(library=library)
        .select_related(
            "fine__transaction__member",
            "fine__transaction__book",
        )
        .order_by("-created_at")[:200]
    )
    return render(request, "finance/audit_log.html", {"payments": payments})