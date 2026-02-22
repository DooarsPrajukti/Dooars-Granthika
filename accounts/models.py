from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta


# ==========================================================
# 🏛 LIBRARY MODEL (CORE PROFILE)
# ==========================================================
class Library(models.Model):

    INSTITUTE_TYPE_CHOICES = [
        ("private", "Private Institution"),
        ("government_rural", "Government – Rural"),
        ("government_urban", "Government – Urban"),
    ]

    # 🔐 One Admin = One Library
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="library"
    )

    # 🆔 Auto Generated Code
    library_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        db_index=True
    )

    # 📷 Logo
    library_logo = models.ImageField(
        upload_to="library_logos/",
        blank=True,
        null=True
    )

    # 📚 Basic Information
    library_name = models.CharField(max_length=255)
    institute_name = models.CharField(max_length=255)

    institute_type = models.CharField(
        max_length=50,
        choices=INSTITUTE_TYPE_CHOICES,
        default="private"
    )

    institute_email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # 📍 Address
    address = models.TextField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    # 🕒 Time
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔥 Safe Auto Generate Code
    def save(self, *args, **kwargs):
        if not self.library_code:
            while True:
                random_part = get_random_string(4).upper()
                code = f"DG-{random_part}"
                if not Library.objects.filter(library_code=code).exists():
                    self.library_code = code
                    break
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.library_name} ({self.library_code})"


# ==========================================================
# 📚 LIBRARY RULE SETTINGS
# ==========================================================
class LibraryRuleSettings(models.Model):

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="rules"
    )

    late_fine = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    borrowing_period = models.PositiveIntegerField(
        default=14,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )

    max_books_per_member = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1)]
    )

    max_renewal_count = models.PositiveIntegerField(default=1)
    grace_period = models.PositiveIntegerField(default=0)

    lost_book_charge_formula = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Toggles
    auto_fine = models.BooleanField(default=True)
    allow_renewal = models.BooleanField(default=True)
    allow_partial_payment = models.BooleanField(default=False)
    auto_mark_lost = models.BooleanField(default=False)
    allow_advance_booking = models.BooleanField(default=False)

    def __str__(self):
        return f"Rules - {self.library.library_name}"


# ==========================================================
# 👥 MEMBER SETTINGS
# ==========================================================
class MemberSettings(models.Model):

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="member_settings"
    )

    student_borrow_limit = models.PositiveIntegerField(default=3)
    teacher_borrow_limit = models.PositiveIntegerField(default=5)
    membership_validity_days = models.PositiveIntegerField(default=365)

    member_id_format = models.CharField(
        max_length=50,
        default="MEM-{0001}"
    )

    allow_self_registration = models.BooleanField(default=False)
    require_admin_approval = models.BooleanField(default=True)
    enable_member_id_download = models.BooleanField(default=True)
    allow_profile_edit = models.BooleanField(default=True)

    def __str__(self):
        return f"Member Settings - {self.library.library_name}"


# ==========================================================
# 🔐 SECURITY SETTINGS
# ==========================================================
class SecuritySettings(models.Model):

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="security"
    )

    two_factor_auth = models.BooleanField(default=False)
    lock_after_failed_attempts = models.BooleanField(default=True)
    force_password_reset = models.BooleanField(default=False)
    login_email_notification = models.BooleanField(default=True)
    allow_multiple_device_login = models.BooleanField(default=True)

    failed_login_attempts_limit = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )

    def __str__(self):
        return f"Security - {self.library.library_name}"


# ==========================================================
# 🔔 NOTIFICATION SETTINGS
# ==========================================================
class NotificationSettings(models.Model):

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    email_overdue_reminder = models.BooleanField(default=True)
    sms_reminder = models.BooleanField(default=False)
    monthly_usage_report = models.BooleanField(default=True)
    weekly_database_backup = models.BooleanField(default=True)
    daily_activity_summary = models.BooleanField(default=False)

    def __str__(self):
        return f"Notifications - {self.library.library_name}"


# ==========================================================
# 🎨 APPEARANCE SETTINGS
# ==========================================================
class AppearanceSettings(models.Model):

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="appearance"
    )

    dark_mode = models.BooleanField(default=False)
    compact_view = models.BooleanField(default=False)
    dashboard_animation = models.BooleanField(default=True)
    show_welcome_message = models.BooleanField(default=True)

    primary_color = models.CharField(max_length=20, default="#2563eb")

    def __str__(self):
        return f"Appearance - {self.library.library_name}"


# ==========================================================
# 💳 SUBSCRIPTION MODEL (SAAS READY)
# ==========================================================
class Subscription(models.Model):

    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    ]

    library = models.OneToOneField(
        Library,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="basic"
    )

    start_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()

    is_active = models.BooleanField(default=True)

    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now().date() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.library.library_name} - {self.plan}"


# ==========================================================
# 🔁 AUTO CREATE DEFAULT SETTINGS
# ==========================================================
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Library)
def create_default_settings(sender, instance, created, **kwargs):
    if created:
        LibraryRuleSettings.objects.create(library=instance)
        MemberSettings.objects.create(library=instance)
        SecuritySettings.objects.create(library=instance)
        NotificationSettings.objects.create(library=instance)
        AppearanceSettings.objects.create(library=instance)
        Subscription.objects.create(
            library=instance,
            expiry_date=timezone.now().date() + timedelta(days=30)
        )