"""
finance/models.py

RazorpayPayment
    Tracks every Razorpay order created for a transactions.Fine.
    OneToOne with Fine — update_or_create in the view handles retries
    idempotently so no duplicate rows are ever created.

Add to transactions/models.py imports or keep here and import in views.
"""

from decimal import Decimal

from django.db import models

from transactions.models import Fine


class RazorpayPayment(models.Model):
    """
    Lifecycle:
        created  →  paid     (HMAC signature verified by callback or webhook)
        created  →  failed   (signature mismatch or payment.failed webhook)
    """

    STATUS_CREATED = "created"
    STATUS_PAID    = "paid"
    STATUS_FAILED  = "failed"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_PAID,    "Paid"),
        (STATUS_FAILED,  "Failed"),
    ]

    fine = models.OneToOneField(
        Fine,
        on_delete=models.CASCADE,
        related_name="razorpay_payment",
    )

    # Razorpay identifiers
    razorpay_order_id   = models.CharField(max_length=100, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True)

    # Amount stored in paise — never loses precision
    amount_paise = models.PositiveIntegerField(
        help_text="Amount in paise (100 paise = ₹1)"
    )
    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Razorpay Payment"
        verbose_name_plural = "Razorpay Payments"

    def __str__(self):
        return (
            f"RzPay {self.razorpay_order_id} [{self.status}] "
            f"₹{self.amount_paise / 100:.2f}"
        )

    @property
    def amount_rupees(self):
        return Decimal(self.amount_paise) / 100