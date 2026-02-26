"""
members/models.py
─────────────────
Multi-tenant library member management models.

Each top-level entity (Department, Course, AcademicYear, Semester, Member,
Transaction) is scoped to a Django User ("owner") so multiple library
administrators can share one database instance without seeing each other's data.

Photo Storage Note:
    Member.photo is a BinaryField — the raw image bytes are stored directly
    in MySQL as a LONGBLOB column.  Member.photo_mime_type records the MIME
    type (e.g. "image/jpeg") so the photo can be served with the correct
    Content-Type header.

    Use the `member_photo` view to serve photos:
        <img src="{% url 'members:member_photo' member.pk %}">

    No MEDIA_ROOT / MEDIA_URL configuration is required for photos.
"""

import os
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# Validators (shared)
# ══════════════════════════════════════════════════════════════════════════════

_phone_validator = RegexValidator(
    regex=r"^\d{10}$",
    message="Phone number must be exactly 10 digits.",
)


# ══════════════════════════════════════════════════════════════════════════════
# Lookup / Reference Models
# ══════════════════════════════════════════════════════════════════════════════

class Department(models.Model):
    """
    Academic department — owner-scoped.
    Each owner (library admin) manages their own set of departments.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="departments",
        help_text="Library admin who owns this record.",
    )
    name = models.CharField(max_length=200, help_text="Full department name.")
    code = models.CharField(max_length=20, help_text="Short department code (e.g. CSE, MBA).")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "code")]
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    """
    Academic course — owner-scoped.
    Duration is stored in years (e.g. 3 for B.Tech, 2 for MBA).
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="courses",
        help_text="Library admin who owns this record.",
    )
    name = models.CharField(max_length=200, help_text="Full course name.")
    code = models.CharField(max_length=20, help_text="Short course code (e.g. BTECH, MBA).")
    duration = models.PositiveSmallIntegerField(
        default=3,
        help_text="Duration of the course in years.",
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "code")]
        ordering = ["name"]
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcademicYear(models.Model):
    """
    Flexible academic year label — owner-scoped.
    Examples: "1st Year", "2nd Year", "Final Year".
    Using a FK model instead of an integer so institutions can define
    their own labels (e.g. Foundation Year, Lateral Entry, etc.).
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="academic_years",
        help_text="Library admin who owns this record.",
    )
    name = models.CharField(
        max_length=100,
        help_text='Display label, e.g. "1st Year", "Final Year".',
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Sort order — lower value appears first.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "name")]
        ordering = ["order", "name"]
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"

    def __str__(self):
        return self.name


class Semester(models.Model):
    """
    Flexible semester label — owner-scoped.
    Examples: "Semester 1", "Odd Semester", "Spring 2025".
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="semesters",
        help_text="Library admin who owns this record.",
    )
    name = models.CharField(
        max_length=100,
        help_text='Display label, e.g. "Semester 1", "Spring 2025".',
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Sort order — lower value appears first.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "name")]
        ordering = ["order", "name"]
        verbose_name = "Semester"
        verbose_name_plural = "Semesters"

    def __str__(self):
        return self.name


# ══════════════════════════════════════════════════════════════════════════════
# Core Member Model
# ══════════════════════════════════════════════════════════════════════════════

class Member(models.Model):
    """
    Library member — owner-scoped (multi-tenant).

    Design decisions
    ────────────────
    • `owner`           – FK to User; every queryset MUST filter on this field.
    • `year`            – FK to AcademicYear (flexible labels, not integer choices).
    • `semester`        – FK to Semester (flexible labels).
    • `specialization`  – free-text optional subject/specialization field.
    • `academic_notes`  – free-text additional academic remarks.
    • `photo`           – BinaryField: stores raw image bytes as LONGBLOB in MySQL.
                          `photo_mime_type` stores the MIME type for serving.
                          Serve via the `member_photo` view.
    • `member_id`       – auto-generated on first save if not provided.
    • `inactive_since`  – automatically set/cleared via save() hook.
    """

    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher / Faculty"),
        ("general", "General Member"),
    ]

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("passout", "Pass Out"),
    ]

    CLEARANCE_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("cleared", "Cleared"),
    ]

    # ── Tenancy ──────────────────────────────────────────────────────────────
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="members",
        help_text="Library admin who owns this member record.",
    )

    # ── Role ─────────────────────────────────────────────────────────────────
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="student",
        help_text="Member role: Student, Teacher/Faculty, or General Member.",
        db_index=True,
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    member_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unique member ID per owner. Auto-generated if left blank.",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(help_text="Must be unique per owner.")

    # ── Contact ───────────────────────────────────────────────────────────────
    phone = models.CharField(
        validators=[_phone_validator],
        max_length=10,
        help_text="10-digit mobile number.",
    )
    alternate_phone = models.CharField(
        validators=[_phone_validator],
        max_length=10,
        blank=True,
        null=True,
        help_text="Optional alternate 10-digit number.",
    )
    guardian_phone = models.CharField(
        validators=[_phone_validator],
        max_length=10,
        blank=True,
        null=True,
        help_text="Parent/guardian 10-digit number.",
    )

    # ── Personal details ──────────────────────────────────────────────────────
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField(blank=True, null=True)

    # ── Cover image stored as binary blob ─────────────────────────────────────
    # MySQL stores this as LONGBLOB (up to 4 GB — more than enough for photos).
    # In Python, reading this field returns a `memoryview`; cast with bytes().
    # Serve via the `member_photo` view: {% url 'members:member_photo' member.pk %}
    photo           = models.BinaryField(null=True, blank=True)
    photo_mime_type = models.CharField(
        max_length=50,
        blank=True,
        default="image/jpeg",
        help_text="MIME type of the stored photo (e.g. image/jpeg, image/png).",
    )

    # ── Academic information ──────────────────────────────────────────────────
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text='Academic year (e.g. "1st Year", "Final Year").',
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text='Current semester (e.g. "Semester 3").',
    )
    roll_number = models.CharField(max_length=50, blank=True, null=True)
    admission_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Year of admission (e.g. 2022).",
    )
    specialization = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Specialization or elective subject (optional).",
    )
    academic_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional academic remarks or notes.",
    )

    # ── Library status ────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the member record was created.",
    )
    inactive_since = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Automatically set when status changes to 'inactive'.",
    )
    inactive_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for marking the member inactive.",
    )

    # ── Clearance ─────────────────────────────────────────────────────────────
    clearance_status = models.CharField(
        max_length=20,
        choices=CLEARANCE_STATUS_CHOICES,
        default="pending",
        help_text="Library clearance status (all books returned, dues cleared).",
    )
    clearance_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when clearance was granted.",
    )
    cleared_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_members",
        help_text="Staff member who granted clearance.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ─────────────────────────────────────────────────────────────────────────

    class Meta:
        unique_together = [
            ("owner", "member_id"),
            ("owner", "email"),
        ]
        ordering = ["-created_at"]
        verbose_name = "Member"
        verbose_name_plural = "Members"

    # ── String representation ─────────────────────────────────────────────────

    def __str__(self):
        return f"{self.full_name} ({self.member_id})"

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Return the member's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def books_issued_count(self) -> int:
        """Number of books currently issued or overdue to this member."""
        return self.transactions.filter(
            status__in=["issued", "overdue"],
            owner=self.owner,
        ).count()

    @property
    def total_transactions(self) -> int:
        """Lifetime total number of transactions for this member."""
        return self.transactions.filter(owner=self.owner).count()

    @property
    def age(self):
        """Member's age in years, or None if date_of_birth not set."""
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def passout_year(self):
        """
        Expected graduation year: admission_year + course.duration.
        Returns None if either value is missing.
        """
        if self.admission_year and self.course_id and self.course:
            return self.admission_year + self.course.duration
        return None

    # ── Save hook ─────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        # Auto-generate member_id on first save if not provided
        if not self.member_id:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            prefix_map = {
                "teacher": "TCH",
                "general": "GEN",
                "student": "STU",
            }
            prefix = prefix_map.get(self.role, "MEM")
            self.member_id = f"{prefix}-{self.owner_id}-{timestamp}"

        # Manage inactive_since timestamp automatically
        if self.status == "inactive":
            if not self.inactive_since:
                self.inactive_since = timezone.now()
        else:
            # Clear inactive metadata when re-activating
            self.inactive_since = None
            self.inactive_reason = None

        super().save(*args, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# Transaction Model
# ══════════════════════════════════════════════════════════════════════════════

class Transaction(models.Model):
    """
    Book issue / return transaction — owner-scoped.

    Lifecycle:  issued → (overdue auto-flagged on save) → returned | lost

    Fine calculation is intentionally left to the application layer so that
    fine rules (per-day rate, grace period, max cap) can be configured
    without schema changes.
    """

    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("returned", "Returned"),
        ("overdue", "Overdue"),
        ("lost", "Lost"),
    ]

    # ── Tenancy ──────────────────────────────────────────────────────────────
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="member_transactions",
        help_text="Library admin who owns this transaction.",
    )

    # ── Core details ──────────────────────────────────────────────────────────
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    book_title = models.CharField(max_length=500)
    book_author = models.CharField(max_length=500, blank=True, null=True)
    book_isbn = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="ISBN-10 or ISBN-13.",
    )
    book_accession_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Library accession / barcode number of the physical copy.",
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    issue_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the book was issued.",
    )
    due_date = models.DateField(help_text="Date by which the book must be returned.")
    return_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual return timestamp. Auto-set on save when status = 'returned'.",
    )

    # ── Status & fines ────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="issued",
    )
    fine_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Fine amount in local currency.",
    )
    fine_paid = models.BooleanField(
        default=False,
        help_text="True once the fine has been collected.",
    )
    fine_paid_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the fine was paid.",
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    issue_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Condition of the book at the time of issue, etc.",
    )
    return_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Condition of the book at the time of return, damage notes, etc.",
    )

    # ── Staff ─────────────────────────────────────────────────────────────────
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_transactions",
        help_text="Staff member who issued the book.",
    )
    returned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transactions",
        help_text="Staff member who received the returned book.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ─────────────────────────────────────────────────────────────────────────

    class Meta:
        ordering = ["-issue_date"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    # ── String representation ─────────────────────────────────────────────────

    def __str__(self):
        return f"{self.member.full_name} — {self.book_title} [{self.status}]"

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_overdue(self) -> bool:
        """True if the book is currently issued and past its due date."""
        if self.status in ("issued", "overdue"):
            return timezone.now().date() > self.due_date
        return False

    @property
    def days_overdue(self) -> int:
        """Number of days past the due date; 0 if not overdue."""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0

    @property
    def is_fine_pending(self) -> bool:
        """True if there is an unpaid fine on this transaction."""
        return self.fine_amount > 0 and not self.fine_paid

    # ── Save hook ─────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        # Auto-flag overdue books
        if self.status == "issued" and self.is_overdue:
            self.status = "overdue"

        # Auto-set return_date when marking as returned
        if self.status == "returned" and not self.return_date:
            self.return_date = timezone.now()

        # Auto-set fine_paid_date when fine is marked paid
        if self.fine_paid and not self.fine_paid_date:
            self.fine_paid_date = timezone.now()

        super().save(*args, **kwargs)