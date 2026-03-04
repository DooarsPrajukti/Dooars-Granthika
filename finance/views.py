"""
finance/views.py

Tenant isolation: request.user.library (OneToOneField on accounts.Library).

────────────────────────────────────────────────────────────────────────
VIEWS
────────────────────────────────────────────────────────────────────────
  1.  finance_dashboard        GET  /finance/
  2.  finance_pay_fine         POST /finance/api/fine/<pk>/pay/
  3.  finance_waive_fine       POST /finance/api/fine/<pk>/waive/
  4.  finance_stats_api        GET  /finance/api/stats/
  5.  create_razorpay_order    POST /finance/fines/<fine_pk>/pay/create-order/
  6.  razorpay_callback        POST /finance/fines/<fine_pk>/pay/callback/
  7.  razorpay_webhook         POST /finance/razorpay/webhook/  (csrf_exempt)

────────────────────────────────────────────────────────────────────────
URL CONF — add to project urls.py
────────────────────────────────────────────────────────────────────────
  path("finance/", include("finance.urls", namespace="finance")),

────────────────────────────────────────────────────────────────────────
RAZORPAY SETUP
────────────────────────────────────────────────────────────────────────
  pip install razorpay

  # settings.py
  RAZORPAY_KEY_ID         = env("RAZORPAY_KEY_ID",         default="rzp_test_xxx")
  RAZORPAY_KEY_SECRET     = env("RAZORPAY_KEY_SECRET",     default="your_secret")
  RAZORPAY_CURRENCY       = "INR"
  RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")
"""

import hashlib
import hmac
import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from transactions.models import Fine, MissingBook, Transaction
from .models import RazorpayPayment

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


def _agg(qs):
    """Sum Fine.amount for a queryset; returns Decimal('0.00') when empty."""
    return (
        qs.aggregate(t=Sum("amount", output_field=DecimalField()))["t"]
        or Decimal("0.00")
    )


def _razorpay_client():
    """Lazily import razorpay so the app works even without the package installed."""
    import razorpay  # noqa: PLC0415
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _paise(amount_decimal):
    """Convert Decimal rupees to integer paise."""
    return int(amount_decimal * 100)


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """HMAC-SHA256: message = '{order_id}|{payment_id}', key = RAZORPAY_KEY_SECRET."""
    message   = f"{order_id}|{payment_id}"
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated, signature)


# ═════════════════════════════════════════════════════════════════════════════
# 1. Finance Dashboard
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def finance_dashboard(request):
    """
    GET /finance/
    Full KPI page — ledger, donut chart, bar chart, top defaulters.
    Template: finance/finance_dashboard.html
    """
    library = _get_library_or_404(request)
    Transaction.sync_overdue_for_library(library)

    base_fine   = Fine.objects.for_library(library)
    today       = date.today()
    month_start = today.replace(day=1)

    # KPI cards
    total_outstanding = _agg(base_fine.filter(status=Fine.STATUS_UNPAID))
    outstanding_count = base_fine.filter(status=Fine.STATUS_UNPAID).count()
    collected_month   = _agg(base_fine.filter(
                            status=Fine.STATUS_PAID,
                            paid_date__gte=month_start))
    waived_month      = _agg(base_fine.filter(
                            status=Fine.STATUS_WAIVED,
                            updated_at__date__gte=month_start))

    # Donut: unpaid fine breakdown by type
    overdue_amt = _agg(base_fine.filter(status=Fine.STATUS_UNPAID, fine_type=Fine.TYPE_OVERDUE))
    lost_amt    = _agg(base_fine.filter(status=Fine.STATUS_UNPAID, fine_type=Fine.TYPE_LOST))
    damage_amt  = _agg(base_fine.filter(status=Fine.STATUS_UNPAID, fine_type=Fine.TYPE_DAMAGE))

    # Hero chips
    overdue_txn_count = (Transaction.objects.for_library(library)
                         .filter(status=Transaction.STATUS_OVERDUE).count())
    lost_count        = (MissingBook.objects.for_library(library)
                         .filter(status=MissingBook.STATUS_LOST).count())

    # Status totals
    unpaid_total  = _agg(base_fine.filter(status=Fine.STATUS_UNPAID))
    paid_total    = _agg(base_fine.filter(status=Fine.STATUS_PAID))
    waived_total  = _agg(base_fine.filter(status=Fine.STATUS_WAIVED))
    unpaid_count  = base_fine.filter(status=Fine.STATUS_UNPAID).count()
    paid_count    = base_fine.filter(status=Fine.STATUS_PAID).count()
    waived_count  = base_fine.filter(status=Fine.STATUS_WAIVED).count()

    # Ledger (tab filter + search)
    tab      = request.GET.get("tab", "unpaid")
    fines_qs = base_fine.select_related("transaction__member", "transaction__book")
    if tab == "paid":
        fines_qs = fines_qs.filter(status=Fine.STATUS_PAID)
    elif tab == "waived":
        fines_qs = fines_qs.filter(status=Fine.STATUS_WAIVED)
    else:
        fines_qs = fines_qs.filter(status=Fine.STATUS_UNPAID)

    q = request.GET.get("q", "").strip()
    if q:
        fines_qs = fines_qs.filter(
            Q(transaction__member__first_name__icontains=q)
            | Q(transaction__member__last_name__icontains=q)
            | Q(transaction__book__title__icontains=q)
            | Q(transaction__pk__icontains=q)
        )
    fines_qs = fines_qs.order_by("-created_at")

    # Top defaulters
    defaulters = list(
        base_fine
        .filter(status=Fine.STATUS_UNPAID)
        .values(
            "transaction__member__pk",
            "transaction__member__first_name",
            "transaction__member__last_name",
            "transaction__member__member_id",
            "transaction__member__role",
        )
        .annotate(total_due=Sum("amount", output_field=DecimalField()))
        .order_by("-total_due")[:8]
    )

    # Monthly collections — last 6 months (bar chart)
    six_months_ago = today.replace(day=1) - timedelta(days=150)
    monthly_raw    = (
        base_fine
        .filter(status=Fine.STATUS_PAID, paid_date__gte=six_months_ago)
        .annotate(month=TruncMonth("paid_date"))
        .values("month")
        .annotate(total=Sum("amount", output_field=DecimalField()))
        .order_by("month")
    )
    monthly_data = [
        {
            "month": row["month"].strftime("%b"),
            "year":  row["month"].strftime("%Y"),
            "total": float(row["total"]),
        }
        for row in monthly_raw
    ]

    ytd_collected = _agg(base_fine.filter(
        status=Fine.STATUS_PAID,
        paid_date__year=today.year,
    ))

    return render(request, "finance/finance_dashboard.html", {
        "total_outstanding":  total_outstanding,
        "outstanding_count":  outstanding_count,
        "collected_month":    collected_month,
        "waived_month":       waived_month,
        "overdue_txn_count":  overdue_txn_count,
        "lost_count":         lost_count,
        "overdue_amt":        overdue_amt,
        "lost_amt":           lost_amt,
        "damage_amt":         damage_amt,
        "fines":              fines_qs,
        "tab":                tab,
        "q":                  q,
        "unpaid_total":       unpaid_total,
        "paid_total":         paid_total,
        "waived_total":       waived_total,
        "unpaid_count":       unpaid_count,
        "paid_count":         paid_count,
        "waived_count":       waived_count,
        "defaulters":         defaulters,
        "monthly_data_json":  json.dumps(monthly_data),
        "ytd_collected":      ytd_collected,
        "today":              today,
        "razorpay_key_id":    getattr(settings, "RAZORPAY_KEY_ID", ""),
    })


# ═════════════════════════════════════════════════════════════════════════════
# 2. Finance Pay Fine  (POST — JSON, AJAX)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def finance_pay_fine(request, pk):
    """
    POST /finance/api/fine/<pk>/pay/

    Body (JSON or form-encoded):
        { "payment_method": "cash|upi|card", "payment_ref": "..." }

    Response:
        { "ok": true, "message": "...", "fine_id": 42, "amount": "50.00", "method": "cash" }
    """
    library = _get_library_or_404(request)
    fine    = get_object_or_404(Fine.objects.for_library(library), pk=pk)

    if fine.status != Fine.STATUS_UNPAID:
        return JsonResponse(
            {"ok": False, "message": "Fine is already paid or waived."},
            status=400,
        )

    try:
        body   = json.loads(request.body)
        method = body.get("payment_method", "cash")
        ref    = body.get("payment_ref", "")
    except (json.JSONDecodeError, AttributeError):
        method = request.POST.get("payment_method", "cash")
        ref    = request.POST.get("payment_ref", "")

    fine.mark_paid(method=method, ref=ref)

    return JsonResponse({
        "ok":      True,
        "message": f"₹{fine.amount} marked as paid via {method.upper()}.",
        "fine_id": fine.pk,
        "amount":  str(fine.amount),
        "method":  method,
        "ref":     ref,
    })


# ═════════════════════════════════════════════════════════════════════════════
# 3. Finance Waive Fine  (POST — JSON, AJAX)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def finance_waive_fine(request, pk):
    """
    POST /finance/api/fine/<pk>/waive/

    Response:
        { "ok": true, "message": "...", "fine_id": 42 }
    """
    library = _get_library_or_404(request)
    fine    = get_object_or_404(Fine.objects.for_library(library), pk=pk)

    if fine.status != Fine.STATUS_UNPAID:
        return JsonResponse(
            {"ok": False, "message": "Only unpaid fines can be waived."},
            status=400,
        )

    fine.waive()

    return JsonResponse({
        "ok":      True,
        "message": f"₹{fine.amount} fine waived.",
        "fine_id": fine.pk,
    })


# ═════════════════════════════════════════════════════════════════════════════
# 4. Finance Stats API  (GET — JSON, live KPI refresh)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def finance_stats_api(request):
    """
    GET /finance/api/stats/

    Called by dashboard JS after every Pay / Waive to refresh KPI cards
    without a full page reload.
    """
    library     = _get_library_or_404(request)
    base_fine   = Fine.objects.for_library(library)
    today       = date.today()
    month_start = today.replace(day=1)

    return JsonResponse({
        "total_outstanding": str(_agg(base_fine.filter(status=Fine.STATUS_UNPAID))),
        "outstanding_count": base_fine.filter(status=Fine.STATUS_UNPAID).count(),
        "collected_month":   str(_agg(base_fine.filter(
                                  status=Fine.STATUS_PAID,
                                  paid_date__gte=month_start))),
        "waived_month":      str(_agg(base_fine.filter(
                                  status=Fine.STATUS_WAIVED,
                                  updated_at__date__gte=month_start))),
        "unpaid_count":      base_fine.filter(status=Fine.STATUS_UNPAID).count(),
        "paid_count":        base_fine.filter(status=Fine.STATUS_PAID).count(),
        "waived_count":      base_fine.filter(status=Fine.STATUS_WAIVED).count(),
    })


# ═════════════════════════════════════════════════════════════════════════════
# 5. Razorpay Create Order  (POST — JSON)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def create_razorpay_order(request, fine_pk):
    """
    POST /finance/fines/<fine_pk>/pay/create-order/

    Creates a Razorpay order and returns the payload the frontend passes
    directly to the Razorpay Checkout JS widget.
    """
    library = _get_library_or_404(request)
    fine    = get_object_or_404(Fine.objects.for_library(library), pk=fine_pk)

    if fine.status != Fine.STATUS_UNPAID:
        return JsonResponse(
            {"error": "This fine has already been paid or waived."},
            status=400,
        )

    member       = fine.transaction.member
    amount_paise = _paise(fine.amount)
    currency     = getattr(settings, "RAZORPAY_CURRENCY", "INR")

    try:
        client   = _razorpay_client()
        rz_order = client.order.create({
            "amount":   amount_paise,
            "currency": currency,
            "receipt":  f"fine_{fine.pk}",
            "notes": {
                "fine_id":    str(fine.pk),
                "library_id": str(library.pk),
                "member_id":  str(member.pk),
            },
        })
    except Exception as exc:
        logger.exception("Razorpay order creation failed for fine %s", fine.pk)
        return JsonResponse({"error": str(exc)}, status=502)

    # Upsert — retries are idempotent
    RazorpayPayment.objects.update_or_create(
        fine=fine,
        defaults={
            "razorpay_order_id":   rz_order["id"],
            "amount_paise":        amount_paise,
            "currency":            currency,
            "status":              RazorpayPayment.STATUS_CREATED,
            "razorpay_payment_id": "",
            "razorpay_signature":  "",
        },
    )

    return JsonResponse({
        "order_id":     rz_order["id"],
        "amount":       amount_paise,
        "currency":     currency,
        "key_id":       settings.RAZORPAY_KEY_ID,
        "fine_id":      fine.pk,
        "description":  f"Library fine – {fine.get_fine_type_display()}",
        "member_name":  f"{member.first_name} {member.last_name}",
        "member_email": getattr(member, "email", "") or "",
        "member_phone": getattr(member, "phone", "") or "",
    })


# ═════════════════════════════════════════════════════════════════════════════
# 6. Razorpay Callback  (POST — JSON, frontend sends after checkout)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def razorpay_callback(request, fine_pk):
    """
    POST /finance/fines/<fine_pk>/pay/callback/

    Body (JSON):
        { "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..." }
    """
    library = _get_library_or_404(request)
    fine    = get_object_or_404(Fine.objects.for_library(library), pk=fine_pk)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    order_id   = body.get("razorpay_order_id", "")
    payment_id = body.get("razorpay_payment_id", "")
    signature  = body.get("razorpay_signature", "")

    if not all([order_id, payment_id, signature]):
        return JsonResponse({"error": "Missing payment fields."}, status=400)

    if not _verify_razorpay_signature(order_id, payment_id, signature):
        logger.warning(
            "Razorpay signature mismatch fine=%s order=%s payment=%s",
            fine.pk, order_id, payment_id,
        )
        RazorpayPayment.objects.filter(
            fine=fine, razorpay_order_id=order_id
        ).update(
            status=RazorpayPayment.STATUS_FAILED,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )
        return JsonResponse({"error": "Payment verification failed."}, status=400)

    rz_pay = get_object_or_404(RazorpayPayment, fine=fine, razorpay_order_id=order_id)
    rz_pay.razorpay_payment_id = payment_id
    rz_pay.razorpay_signature  = signature
    rz_pay.status              = RazorpayPayment.STATUS_PAID
    rz_pay.save(update_fields=[
        "razorpay_payment_id", "razorpay_signature", "status", "updated_at",
    ])

    if fine.status == Fine.STATUS_UNPAID:
        fine.mark_paid(method="razorpay", ref=payment_id)

    logger.info("Fine %s paid via Razorpay payment %s", fine.pk, payment_id)
    return JsonResponse({"status": "ok", "payment_id": payment_id})


# ═════════════════════════════════════════════════════════════════════════════
# 7. Razorpay Webhook  (POST — csrf_exempt, server-to-server)
# ═════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    POST /finance/razorpay/webhook/

    Register in: Razorpay Dashboard → Settings → Webhooks
    Events handled: payment.captured, payment.failed
    """
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    received_sig   = request.headers.get("X-Razorpay-Signature", "")

    if webhook_secret:
        expected = hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, received_sig):
            logger.warning("Razorpay webhook signature mismatch")
            return JsonResponse({"error": "Invalid signature."}, status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Bad JSON."}, status=400)

    event = payload.get("event", "")

    if event == "payment.captured":
        entity     = payload["payload"]["payment"]["entity"]
        payment_id = entity["id"]
        order_id   = entity.get("order_id", "")
        fine_id    = entity.get("notes", {}).get("fine_id")

        if fine_id:
            try:
                rz_pay = RazorpayPayment.objects.select_related("fine").get(
                    razorpay_order_id=order_id
                )
                if rz_pay.fine.status == Fine.STATUS_UNPAID:
                    rz_pay.razorpay_payment_id = payment_id
                    rz_pay.status              = RazorpayPayment.STATUS_PAID
                    rz_pay.save(update_fields=[
                        "razorpay_payment_id", "status", "updated_at",
                    ])
                    rz_pay.fine.mark_paid(method="razorpay", ref=payment_id)
                    logger.info(
                        "Webhook: Fine %s paid via payment %s", fine_id, payment_id
                    )
            except RazorpayPayment.DoesNotExist:
                logger.warning("Webhook: No RazorpayPayment for order %s", order_id)

    elif event == "payment.failed":
        entity   = payload["payload"]["payment"]["entity"]
        order_id = entity.get("order_id", "")
        RazorpayPayment.objects.filter(razorpay_order_id=order_id).update(
            status=RazorpayPayment.STATUS_FAILED,
        )
        logger.info("Webhook: payment failed for order %s", order_id)

    return JsonResponse({"status": "ok"})