from django.db import models
from django.contrib.auth.models import User


class StaffRole(models.TextChoices):
    LIBRARIAN  = 'librarian',  'Librarian'
    ASSISTANT  = 'assistant',  'Library Assistant'
    # CATALOGUER = 'cataloguer', 'Cataloguer'
    # ADMIN      = 'admin',      'Administrator'
    # VOLUNTEER  = 'volunteer',  'Volunteer'


class StaffStatus(models.TextChoices):
    ACTIVE   = 'active',   'Active'
    INACTIVE = 'inactive', 'Inactive'
    ON_LEAVE = 'on_leave', 'On Leave'


class Staff(models.Model):
    # ── Multi-tenant: which admin owns this staff member ──────
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='owned_staff',
        help_text='The superuser/admin who created this staff member.',
    )

    # ── Linked Django login account ───────────────────────────
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_profile',
    )

    # ── Portal access flag ────────────────────────────────────
    # 1 = staff can log in to the staff dashboard
    # 0 = login disabled (mirrors Django User.is_staff)
    is_staff_user = models.BooleanField(
        default=True,
        verbose_name='Portal Access',
        help_text='1 = can log in to staff dashboard  |  0 = access revoked.',
    )

    # ── Personal details ──────────────────────────────────────
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address      = models.TextField(blank=True)

    # Photo stored as BLOB in MySQL
    photo      = models.BinaryField(null=True, blank=True)
    photo_mime = models.CharField(max_length=50, blank=True)

    # ── Role & status ─────────────────────────────────────────
    role   = models.CharField(max_length=20, choices=StaffRole.choices,   default=StaffRole.LIBRARIAN)
    status = models.CharField(max_length=20, choices=StaffStatus.choices, default=StaffStatus.ACTIVE)

    # ── Employment ────────────────────────────────────────────
    date_joined = models.DateField()
    date_left   = models.DateField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['first_name', 'last_name']
        verbose_name        = 'Staff Member'
        verbose_name_plural = 'Staff Members'

    def __str__(self):
        return self.full_name

    # ── Properties ────────────────────────────────────────────

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def photo_b64(self):
        """Returns a base64 data URI for use directly in <img src=''>."""
        if self.photo:
            import base64
            data = base64.b64encode(bytes(self.photo)).decode('utf-8')
            mime = self.photo_mime or 'image/jpeg'
            return f"data:{mime};base64,{data}"
        return None

    # ── Helpers ───────────────────────────────────────────────

    def sync_portal_access(self):
        """
        Keep Django User.is_staff in sync with self.is_staff_user.
        1 → User.is_staff = True  (can access staff dashboard)
        0 → User.is_staff = False (access revoked)
        """
        if self.user:
            self.user.is_staff = self.is_staff_user
            self.user.save(update_fields=['is_staff'])