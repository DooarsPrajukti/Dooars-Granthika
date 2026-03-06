# finance/urls.py
# ─────────────────────────────────────────────────────────────────────────────
# All URL patterns for the finance app.
# Include in your project urls.py with:
#   path('finance/', include('finance.urls', namespace='finance')),
# ─────────────────────────────────────────────────────────────────────────────

from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [

    # ── Payment flow ──────────────────────────────────────────────────────────
    # Step 1: Show fine details + cash form (auto-detects from ?fine_id=)
    path(
        'process-payment/',
        views.process_payment,
        name='process_payment',
    ),

    # Step 2: Receive form POST, create Payment, mark fine paid, redirect back
    path(
        'cash-payment/',
        views.cash_payment,
        name='cash_payment',
    ),

    # Receipt view for a completed payment
    path(
        'receipt/<int:payment_id>/',
        views.payment_receipt,
        name='payment_receipt',
    ),

    # Legacy confirm-recovery page (redirects through cash_payment logic)
    path(
        'confirm-recovery/<int:fine_id>/',
        views.confirm_recovery,
        name='confirm_recovery',
    ),

    # ── Fine management ───────────────────────────────────────────────────────
    # Waive a fine (POST only) — used by the Waive button in transaction_detail
    path(
        'waive-fine/<int:fine_id>/',
        views.waive_fine,
        name='waive_fine',
    ),

    # ── Income ────────────────────────────────────────────────────────────────
    path(
        'income/',
        views.income_list,
        name='income_list',
    ),

    # ── Expenses ──────────────────────────────────────────────────────────────
    path(
        'expenses/',
        views.expense_list,
        name='expense_list',
    ),
    path(
        'expenses/add/',
        views.add_expense,
        name='add_expense',
    ),
    path(
        'expenses/<int:expense_id>/edit/',
        views.add_expense,          # same view, expense_id kwarg triggers edit mode
        name='edit_expense',
    ),
    path(
        'expenses/<int:expense_id>/delete/',
        views.delete_expense,
        name='delete_expense',
    ),

    # ── Reports ───────────────────────────────────────────────────────────────
    path(
        'reports/',
        views.finance_reports,
        name='finance_reports',
    ),
    path(
        'daily-collection/',
        views.daily_collection,
        name='daily_collection',
    ),
    path(
        'cash-book/',
        views.cash_book,
        name='cash_book',
    ),
    path(
        'profit-loss/',
        views.profit_loss,
        name='profit_loss',
    ),

    # ── Audit log ─────────────────────────────────────────────────────────────
    path(
        'audit/',
        views.audit_log,
        name='audit_log',
    ),
]