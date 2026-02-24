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
    # Django user account (created automatically on staff add)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff_profile'
    )

    # Personal details
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address      = models.TextField(blank=True)

    # Photo stored as BLOB in MySQL
    photo      = models.BinaryField(null=True, blank=True)
    photo_mime = models.CharField(max_length=50, blank=True)  # e.g. 'image/jpeg'

    # Role & status
    role   = models.CharField(max_length=20, choices=StaffRole.choices, default=StaffRole.LIBRARIAN)
    status = models.CharField(max_length=20, choices=StaffStatus.choices, default=StaffStatus.ACTIVE)

    # Employment
    date_joined = models.DateField()
    date_left   = models.DateField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'

    def __str__(self):
        return self.full_name

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