# finance/models.py
# ─────────────────────────────────────────────────────────────────────────────
# Fine is the canonical fine model — lives here in the finance app.
# transactions.Fine has been removed; all fine logic lives here.
# ─────────────────────────────────────────────────────────────────────────────

import random
import time
from datetime import date
from decimal import Decimal

from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Fine ID generator
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_code(library) -> str:
    """
    Return the 2-character uppercase library code.
    Tries common field names; falls back to first 2 chars of library.name.
    """
    for field in ("code", "lib_code", "short_code", "abbreviation"):
        val = getattr(library, field, None)
        if val:
            return str(val).upper()[:2]
    name = getattr(library, "name", "") or ""
    return (name[:2].upper()) or "LB"


def generate_fine_id(library) -> str:
    """
    Build a fine transaction ID:
        DG<LIB>FN<MM><YY><RAND5>
    e.g.  DGGRFN032512345
      DG     — Dooars Granthika prefix
      GR     — 2-char library code
      FN     — fixed literal
      03     — month  (MM)
      25     — year   (YY)
      12345  — 5-digit random number (10000–99999)
    """
    today    = date.today()
    lib_code = _get_library_code(library)
    return f"DG{lib_code}FN{today.strftime('%m')}{today.strftime('%y')}{random.randint(10000, 99999)}"


# ─────────────────────────────────────────────────────────────────────────────
# Fine — canonical model (was transactions.Fine)
# ─────────────────────────────────────────────────────────────────────────────

class _FineQuerySet(models.QuerySet):
    def for_library(self, library):
        return self.filter(library=library)


class _FineManager(models.Manager):
    def get_queryset(self):
        return _FineQuerySet(self.model, using=self._db)

    def for_library(self, library):
        return self.get_queryset().for_library(library)


class Fine(models.Model):
    """
    One row per fine event per transaction, scoped to a Library tenant.

    Replaces transactions.Fine entirely — all fine-related logic lives
    in the finance app from this point on.
    """

    # ── Type constants ────────────────────────────────────────────────
    TYPE_OVERDUE = "overdue"
    TYPE_LOST    = "lost"
    TYPE_DAMAGE  = "damage"

    FINE_TYPE_CHOICES = [
        (TYPE_OVERDUE, "Overdue Fine"),
        (TYPE_LOST,    "Lost Book Penalty"),
        (TYPE_DAMAGE,  "Damage Charge"),
    ]

    # ── Status constants ──────────────────────────────────────────────
    STATUS_UNPAID = "unpaid"
    STATUS_PAID   = "paid"
    STATUS_WAIVED = "waived"

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID,   "Paid"),
        (STATUS_WAIVED, "Waived"),
    ]

    # ── Payment method constants ──────────────────────────────────────
    PAYMENT_METHOD_CHOICES = [
        ("cash",  "Cash"),
        ("upi",   "UPI"),
        ("card",  "Card"),
        ("other", "Other"),
    ]

    # ── Fine transaction ID  e.g. DGGRFN032512345 ────────────────────
    fine_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        db_index=True,
        help_text="Auto-generated on first save: DG<LIB>FN<MM><YY><RAND5>",
    )

    # ── Tenant scope ──────────────────────────────────────────────────
    library = models.ForeignKey(
        "accounts.Library",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="fines",
    )

    # ── Core relation ─────────────────────────────────────────────────
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="fines",          # txn.fines.all()  still works
    )

    # ── Fine details ──────────────────────────────────────────────────
    fine_type = models.CharField(max_length=20, choices=FINE_TYPE_CHOICES)
    amount    = models.DecimalField(max_digits=10, decimal_places=2)
    status    = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_UNPAID, db_index=True,
    )

    # ── Payment tracking ──────────────────────────────────────────────
    paid_date      = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True,
    )
    payment_ref = models.CharField(max_length=100, blank=True)

    # ── Audit ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = _FineManager()

    class Meta:
        app_label           = "finance"
        ordering            = ["-created_at"]
        verbose_name        = "Fine"
        verbose_name_plural = "Fines"
        indexes = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "fine_type"]),
        ]

    def __str__(self):
        return (
            f"Fine {self.fine_id or self.pk} "
            f"({self.get_fine_type_display()}) "
            f"₹{self.amount} [{self.get_status_display()}]"
        )

    # ── Auto-generate fine_id on first save ───────────────────────────
    def save(self, *args, **kwargs):
        if not self.fine_id:
            for _ in range(10):      # retry up to 10× on the rare collision
                candidate = generate_fine_id(self.library)
                if not Fine.objects.filter(fine_id=candidate).exists():
                    self.fine_id = candidate
                    break
            else:
                # Timestamp fallback — practically unreachable
                self.fine_id = f"DG{_get_library_code(self.library)}FN{int(time.time())}"
        super().save(*args, **kwargs)

    # ── Domain methods ────────────────────────────────────────────────
    def mark_paid(self, method="cash", ref=""):
        self.status         = self.STATUS_PAID
        self.paid_date      = date.today()
        self.payment_method = method
        self.payment_ref    = ref
        self.save(update_fields=[
            "status", "paid_date", "payment_method", "payment_ref", "updated_at",
        ])

    def waive(self):
        self.status = self.STATUS_WAIVED
        self.save(update_fields=["status", "updated_at"])

    @property
    def is_unpaid(self):
        return self.status == self.STATUS_UNPAID


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

class Payment(models.Model):
    """A payment record for a fine (cash or online)."""

    METHOD_CHOICES = [
        ("cash",   "Cash"),
        ("online", "Online"),
    ]
    STATUS_CHOICES = [
        ("success", "Success"),
        ("pending", "Pending"),
        ("failed",  "Failed"),
    ]

    fine   = models.ForeignKey(Fine, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="cash")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")

    receipt_number = models.CharField(max_length=80, blank=True, null=True)
    collected_by   = models.CharField(max_length=120, blank=True)

    gateway_order_id   = models.CharField(max_length=120, blank=True)
    gateway_payment_id = models.CharField(max_length=120, blank=True)
    gateway_signature  = models.CharField(max_length=255, blank=True)

    transaction_date = models.DateTimeField(default=timezone.now)
    created_at       = models.DateTimeField(auto_now_add=True)

    library = models.ForeignKey(
        "accounts.Library",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="finance_payments",
    )

    class Meta:
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"Payment #{self.pk} — ₹{self.amount} ({self.method}/{self.status})"


# ─────────────────────────────────────────────────────────────────────────────
# Expense
# ─────────────────────────────────────────────────────────────────────────────

class Expense(models.Model):
    """An operational expense recorded by library staff."""

    CATEGORY_CHOICES = [
        ("Books",       "Books"),
        ("Maintenance", "Maintenance"),
        ("Utilities",   "Utilities"),
        ("Salaries",    "Salaries"),
        ("Stationery",  "Stationery"),
        ("Technology",  "Technology"),
        ("Events",      "Events"),
        ("Other",       "Other"),
    ]

    date        = models.DateField(default=timezone.now)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    notes       = models.TextField(blank=True)
    recorded_by = models.CharField(max_length=120, blank=True)

    library = models.ForeignKey(
        "accounts.Library",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="expenses",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} — {self.description} (₹{self.amount})"