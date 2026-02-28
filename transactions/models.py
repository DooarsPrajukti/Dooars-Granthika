"""
transactions/models.py

Multi-tenant SaaS — tenant = Library (from accounts.Library).

All three transaction models anchor to Library so every query can be
scoped with  Model.objects.for_library(library)  and never leak data
across tenants.

The Book and Member FKs still point to the existing models in the
books / members apps unchanged — no migration needed on those apps.
"""

from django.db import models
from datetime import date
from decimal import Decimal

from accounts.models import Library


# ─────────────────────────────────────────────────────────────────────────────
# Tenant isolation helpers
# ─────────────────────────────────────────────────────────────────────────────

class TenantQuerySet(models.QuerySet):
    def for_library(self, library):
        return self.filter(library=library)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_library(self, library):
        return self.get_queryset().for_library(library)


class TenantModelMixin(models.Model):
    """
    Abstract base — stamps every row with the owning Library.
    Always query via  Model.objects.for_library(lib)  to stay safe.
    """
    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(TenantModelMixin):
    """
    One row per borrowing event, scoped to a Library tenant.

    Fine maths live entirely in @property — no stored column can drift.
    fine_rate_per_day is snapshotted from LibraryRuleSettings.late_fine
    at the moment of issue so historic records are never mutated by
    rule changes.
    """

    STATUS_ISSUED   = "issued"
    STATUS_RETURNED = "returned"
    STATUS_OVERDUE  = "overdue"
    STATUS_LOST     = "lost"

    STATUS_CHOICES = [
        (STATUS_ISSUED,   "Issued"),
        (STATUS_RETURNED, "Returned"),
        (STATUS_OVERDUE,  "Overdue"),
        (STATUS_LOST,     "Lost"),
    ]

    CONDITION_GOOD    = "good"
    CONDITION_FAIR    = "fair"
    CONDITION_DAMAGED = "damaged"

    CONDITION_CHOICES = [
        (CONDITION_GOOD,    "Good"),
        (CONDITION_FAIR,    "Fair"),
        (CONDITION_DAMAGED, "Damaged"),
    ]

    # ── Relations ─────────────────────────────────────────────────────
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="issue_transactions",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="issue_transactions",
    )

    # ── Dates ─────────────────────────────────────────────────────────
    issue_date  = models.DateField()
    due_date    = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    lost_date   = models.DateField(null=True, blank=True)

    # ── Loan settings — snapshotted at issue time ─────────────────────
    loan_duration_days = models.PositiveIntegerField(default=14)
    fine_rate_per_day  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("2.00"),
        help_text="Copied from LibraryRuleSettings.late_fine at issue time.",
    )

    # ── Status & condition ────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_ISSUED, db_index=True,
    )
    return_condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, blank=True,
    )

    # ── Staff audit ───────────────────────────────────────────────────
    issued_by   = models.CharField(max_length=150, blank=True)
    returned_to = models.CharField(max_length=150, blank=True)

    # ── Copy info (snapshotted) ───────────────────────────────────────
    copy_number = models.CharField(max_length=20, blank=True)

    # ── Renewal ───────────────────────────────────────────────────────
    renewal_count = models.PositiveIntegerField(default=0)

    # ── Fine / payment ────────────────────────────────────────────────
    damage_charge  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
    )
    fine_paid      = models.BooleanField(default=False)
    fine_paid_date = models.DateField(null=True, blank=True)

    # ── Notes ─────────────────────────────────────────────────────────
    notes        = models.TextField(blank=True)
    return_notes = models.TextField(blank=True)

    # ── Audit ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "due_date"]),
            models.Index(fields=["library", "member"]),
        ]

    def __str__(self):
        return f"Txn #{self.pk} — {self.member} / {self.book}"

    # ── Computed properties ───────────────────────────────────────────

    @property
    def is_overdue(self):
        if self.status in (self.STATUS_RETURNED, self.STATUS_LOST):
            return False
        return date.today() > self.due_date

    @property
    def overdue_days(self):
        if self.status == self.STATUS_RETURNED and self.return_date:
            return max(0, (self.return_date - self.due_date).days)
        if not self.is_overdue:
            return 0
        return max(0, (date.today() - self.due_date).days)

    @property
    def overdue_fine(self):
        return Decimal(self.overdue_days) * self.fine_rate_per_day

    @property
    def fine_amount(self):
        return self.overdue_fine + self.damage_charge

    @property
    def days_borrowed(self):
        end = self.return_date or date.today()
        return max(0, (end - self.issue_date).days)

    @property
    def overdue_severity(self):
        d = self.overdue_days
        if d <= 7:
            return "mild"
        if d <= 30:
            return "moderate"
        return "severe"

    @classmethod
    def sync_overdue_for_library(cls, library):
        """Bulk-flip issued → overdue in one UPDATE. Call from a view or task."""
        cls.objects.for_library(library).filter(
            status=cls.STATUS_ISSUED,
            due_date__lt=date.today(),
        ).update(status=cls.STATUS_OVERDUE)


# ─────────────────────────────────────────────────────────────────────────────
# Fine
# ─────────────────────────────────────────────────────────────────────────────

class Fine(TenantModelMixin):
    """
    Explicit fine ledger row per transaction.
    library FK is denormalised (from TenantModelMixin) so
    Fine.objects.for_library(lib) never needs a JOIN through Transaction.
    """

    TYPE_OVERDUE = "overdue"
    TYPE_LOST    = "lost"
    TYPE_DAMAGE  = "damage"

    FINE_TYPE_CHOICES = [
        (TYPE_OVERDUE, "Overdue Fine"),
        (TYPE_LOST,    "Lost Book Penalty"),
        (TYPE_DAMAGE,  "Damage Charge"),
    ]

    STATUS_UNPAID = "unpaid"
    STATUS_PAID   = "paid"
    STATUS_WAIVED = "waived"

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID,   "Paid"),
        (STATUS_WAIVED, "Waived"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cash",  "Cash"),
        ("upi",   "UPI"),
        ("card",  "Card"),
        ("other", "Other"),
    ]

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    fine_type = models.CharField(max_length=20, choices=FINE_TYPE_CHOICES)
    amount    = models.DecimalField(max_digits=10, decimal_places=2)
    status    = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_UNPAID, db_index=True,
    )
    paid_date      = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True,
    )
    payment_ref    = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Fine"
        verbose_name_plural = "Fines"
        indexes = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "fine_type"]),
        ]

    def __str__(self):
        return f"Fine #{self.pk} ({self.fine_type}) ₹{self.amount} [{self.status}]"

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


# ─────────────────────────────────────────────────────────────────────────────
# MissingBook
# ─────────────────────────────────────────────────────────────────────────────

class MissingBook(TenantModelMixin):
    """
    Lifecycle tracker for books reported missing / lost / recovered.
    OneToOne with Transaction — no duplicate records per borrowing event.
    """

    STATUS_MISSING   = "missing"
    STATUS_LOST      = "lost"
    STATUS_RECOVERED = "recovered"

    STATUS_CHOICES = [
        (STATUS_MISSING,   "Missing"),
        (STATUS_LOST,      "Lost"),
        (STATUS_RECOVERED, "Recovered"),
    ]

    REASON_CHOICES = [
        ("lost",     "Book Lost"),
        ("damaged",  "Severely Damaged"),
        ("missing",  "Missing - Not Returned"),
        ("other",    "Other"),
    ]

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="missing_record",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="missing_book_records",
    )

    status        = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_MISSING,
    )
    reported_date = models.DateField(default=date.today)
    reason        = models.CharField(max_length=20, choices=REASON_CHOICES, blank=True)
    notes         = models.TextField(blank=True)

    penalty_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
    )
    penalty_paid   = models.BooleanField(default=False)
    penalty_reason = models.CharField(max_length=20, choices=REASON_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Missing Book"
        verbose_name_plural = "Missing Books"
        indexes = [
            models.Index(fields=["library", "status"]),
        ]

    def __str__(self):
        return f"Missing: {self.book.title} ({self.status})"