from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import (
    Library,
    LibraryRuleSettings,
    MemberSettings,
    SecuritySettings,
    NotificationSettings,
    AppearanceSettings,
)
from .utils import generate_random_password, generate_username

# optional email service
try:
    import core.email_service as email_service
except Exception:
    email_service = None


# ==========================================================
# 🔐 SIGN IN
# ==========================================================
def view_signin(request):

    if request.user.is_authenticated:
        return redirect("accounts:admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        if not username or not password:
            messages.error(request, "Please enter username and password.")
            return redirect("accounts:signin")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            if remember_me:
                request.session.set_expiry(timedelta(days=7))
            else:
                request.session.set_expiry(0)

            messages.success(request, "Login successful.")
            return redirect("accounts:admin_dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/sign_in.html")


# ==========================================================
# 🚪 LOGOUT
# ==========================================================
@login_required
def view_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("accounts:signin")


# ==========================================================
# 📝 REGISTER LIBRARY
# ==========================================================
def register_library(request):

    if request.method == "POST":
        try:
            with transaction.atomic():

                institute_email = request.POST.get("institute_email").lower()

                if User.objects.filter(email=institute_email).exists():
                    messages.error(request, "Email already exists.")
                    return redirect("accounts:signup")

                password = request.POST.get("admin_password")
                confirm_password = request.POST.get("admin_confirm_password")

                if password != confirm_password:
                    messages.error(request, "Passwords do not match.")
                    return redirect("accounts:signup")

                username = generate_username()
                while User.objects.filter(username=username).exists():
                    username = generate_username()

                user = User.objects.create_user(
                    username=username,
                    email=institute_email,
                    password=password,
                    first_name=request.POST.get("admin_full_name"),
                )

                Library.objects.create(
                    user=user,
                    library_name=request.POST.get("library_name"),
                    institute_name=request.POST.get("institute_name"),
                    institute_type=request.POST.get("institute_type"),
                    institute_email=institute_email,
                    phone_number=request.POST.get("phone_number"),
                    address=request.POST.get("address"),
                    district=request.POST.get("district"),
                    state=request.POST.get("state"),
                    country=request.POST.get("country"),
                )

                if email_service:
                    try:
                        email_service.send_account_credentials(
                            institute_email, password, username
                        )
                    except Exception:
                        pass

                messages.success(request, "Library registered successfully.")
                return redirect("accounts:signin")

        except Exception as e:
            print(e)
            messages.error(request, "Something went wrong.")
            return redirect("accounts:signup")

    return render(request, "accounts/sign_up.html")


# ==========================================================
# 🔑 FORGOT PASSWORD
# ==========================================================
def view_forget_password(request):

    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        user = User.objects.filter(email=email).first()

        if user:
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()

            lib = getattr(user, "library", None)

            if email_service:
                try:
                    email_service.send_password_reset_email(
                        user,
                        new_password,
                        lib.library_name if lib else "Library",
                        user.username,
                    )
                except Exception:
                    pass

        messages.success(request, "If this email exists, password sent.")
        return redirect("accounts:signin")

    return render(request, "accounts/forget_password.html")


# ==========================================================
# 🖥 ADMIN DASHBOARD
# ==========================================================
@login_required
def admin_dashboard(request):

    library = request.user.library

    return render(
        request,
        "dashboards/admin_dashboard.html",
        {"library": library},
    )


# ==========================================================
# ⚙️ SETTINGS PAGE
# ==========================================================
@login_required
def settings_view(request):

    # ── Fetch library ──────────────────────────────────────────────
    try:
        library = Library.objects.get(user=request.user)
    except Library.DoesNotExist:
        messages.error(request, "No library found for your account.")
        return redirect("accounts:admin_dashboard")

    # ── get_or_create — never throws RelatedObjectDoesNotExist ─────
    rules,         _ = LibraryRuleSettings.objects.get_or_create(library=library)
    member_cfg,    _ = MemberSettings.objects.get_or_create(library=library)
    security,      _ = SecuritySettings.objects.get_or_create(library=library)
    notifications, _ = NotificationSettings.objects.get_or_create(library=library)
    appearance,    _ = AppearanceSettings.objects.get_or_create(library=library)

    # ── POST ───────────────────────────────────────────────────────
    if request.method == "POST":
        section = request.POST.get("form_type", "").strip()

        # ── profile ────────────────────────────────────────────────
        if section == "profile":
            user            = request.user
            user.first_name = request.POST.get("first_name", user.first_name).strip()
            user.last_name  = request.POST.get("last_name",  user.last_name).strip()
            user.email      = request.POST.get("email",      user.email).strip()
            user.save()

            # Library fields
            library.library_name   = request.POST.get("library_name",   library.library_name).strip()
            library.institute_name = request.POST.get("institute_name", library.institute_name).strip()
            library.phone_number   = request.POST.get("phone_number",   library.phone_number or "").strip()
            library.address        = request.POST.get("address",        library.address).strip()

            if "library_logo" in request.FILES:
                library.library_logo = request.FILES["library_logo"]

            library.save()
            messages.success(request, "Profile updated successfully.")

        # ── security ───────────────────────────────────────────────
        elif section == "security":
            user       = request.user
            current_pw = request.POST.get("current_password", "")
            new_pw     = request.POST.get("new_password", "")
            confirm_pw = request.POST.get("confirm_password", "")

            if current_pw and new_pw and confirm_pw:
                if not user.check_password(current_pw):
                    messages.error(request, "Current password is incorrect.")
                elif new_pw != confirm_pw:
                    messages.error(request, "New passwords do not match.")
                elif len(new_pw) < 8:
                    messages.error(request, "Password must be at least 8 characters.")
                else:
                    user.set_password(new_pw)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password updated successfully.")
            else:
                messages.warning(request, "Please fill in all password fields.")

            # SecuritySettings fields
            security.two_factor_auth              = request.POST.get("two_factor_auth")              == "on"
            security.lock_after_failed_attempts   = request.POST.get("lock_after_failed_attempts")   == "on"
            security.force_password_reset         = request.POST.get("force_password_reset")         == "on"
            security.login_email_notification     = request.POST.get("login_email_notification")     == "on"
            security.allow_multiple_device_login  = request.POST.get("allow_multiple_device_login")  == "on"
            security.failed_login_attempts_limit  = _int(
                request.POST.get("failed_login_attempts_limit"),
                security.failed_login_attempts_limit,
            )
            security.save()

        # ── system ─────────────────────────────────────────────────
        elif section == "system":
            library.institute_email = request.POST.get("institute_email", library.institute_email).strip()
            library.phone_number    = request.POST.get("phone_number",    library.phone_number or "").strip()
            library.address         = request.POST.get("address",         library.address).strip()
            library.district        = request.POST.get("district",        library.district).strip()
            library.state           = request.POST.get("state",           library.state).strip()
            library.country         = request.POST.get("country",         library.country).strip()
            library.save()

            appearance.primary_color = request.POST.get("primary_color", appearance.primary_color).strip()
            appearance.save()

            messages.success(request, "System settings updated successfully.")

        # ── notifications ──────────────────────────────────────────
        elif section == "notifications":
            # Exact field names from NotificationSettings model
            notifications.email_overdue_reminder  = request.POST.get("email_overdue_reminder")  == "on"
            notifications.sms_reminder            = request.POST.get("sms_reminder")            == "on"
            notifications.monthly_usage_report    = request.POST.get("monthly_usage_report")    == "on"
            notifications.weekly_database_backup  = request.POST.get("weekly_database_backup")  == "on"
            notifications.daily_activity_summary  = request.POST.get("daily_activity_summary")  == "on"
            notifications.save()
            messages.success(request, "Notification preferences saved.")

        # ── fine & loans ───────────────────────────────────────────
        elif section == "fine":
            # Exact field names from LibraryRuleSettings model
            rules.max_books_per_member  = _int(request.POST.get("max_books_per_member"),  rules.max_books_per_member)
            rules.borrowing_period      = _int(request.POST.get("loan_period_days"),      rules.borrowing_period)
            rules.max_renewal_count     = _int(request.POST.get("renewal_limit"),         rules.max_renewal_count)
            rules.grace_period          = _int(request.POST.get("grace_period_days"),     rules.grace_period)
            rules.late_fine             = _dec(request.POST.get("fine_per_day"),          rules.late_fine)
            rules.auto_fine             = request.POST.get("auto_fine")             == "on"
            rules.allow_renewal         = request.POST.get("allow_renewal")         == "on"
            rules.allow_partial_payment = request.POST.get("allow_partial_payment") == "on"
            rules.auto_mark_lost        = request.POST.get("auto_mark_lost")        == "on"
            rules.allow_advance_booking = request.POST.get("allow_advance_booking") == "on"
            rules.save()
            messages.success(request, "Loan & fine settings saved.")

        else:
            messages.warning(request, f"Unknown settings section: '{section}'.")

        return redirect("accounts:settings")

    # ── GET: build context ─────────────────────────────────────────

    # Notification list — keys EXACTLY match model field names
    notification_list = [
        {
            "key":         "email_overdue_reminder",
            "label":       "Email Overdue Reminder",
            "description": "Send email reminders when a loan becomes overdue.",
            "enabled":     notifications.email_overdue_reminder,
        },
        {
            "key":         "sms_reminder",
            "label":       "SMS Reminders",
            "description": "Send SMS reminders for due and overdue books.",
            "enabled":     notifications.sms_reminder,
        },
        {
            "key":         "monthly_usage_report",
            "label":       "Monthly Usage Report",
            "description": "Receive a monthly summary report via email.",
            "enabled":     notifications.monthly_usage_report,
        },
        {
            "key":         "weekly_database_backup",
            "label":       "Weekly Database Backup",
            "description": "Get notified when weekly backup completes.",
            "enabled":     notifications.weekly_database_backup,
        },
        {
            "key":         "daily_activity_summary",
            "label":       "Daily Activity Summary",
            "description": "Receive a daily digest of library activity.",
            "enabled":     notifications.daily_activity_summary,
        },
    ]

    # system_settings proxy — template uses system_settings.<field>
    system_settings = _Proxy({
        "org_name":      library.library_name,
        "institute_name": library.institute_name,
        "org_email":     library.institute_email,
        "org_phone":     library.phone_number or "",
        "org_address":   library.address,
        "district":      library.district,
        "state":         library.state,
        "country":       library.country,
        "primary_color": appearance.primary_color,
    })

    # loan_settings proxy — template uses loan_settings.<field>
    loan_settings = _Proxy({
        "max_books_per_member": rules.max_books_per_member,
        "loan_period_days":     rules.borrowing_period,
        "renewal_limit":        rules.max_renewal_count,
        "grace_period_days":    rules.grace_period,
        "fine_per_day":         rules.late_fine,
        "max_fine":             0,   # no max_fine_amount field in model
        "waiver_percentage":    0,   # no waiver_percentage field in model
        # Toggles
        "auto_fine":             rules.auto_fine,
        "allow_renewal":         rules.allow_renewal,
        "allow_partial_payment": rules.allow_partial_payment,
        "auto_mark_lost":        rules.auto_mark_lost,
        "allow_advance_booking": rules.allow_advance_booking,
    })

    context = {
        # Raw instances
        "library":               library,
        "rules":                 rules,
        "member_cfg":            member_cfg,
        "security":              security,
        "notifications":         notifications,
        "appearance":            appearance,

        # Template-facing aliases
        "system_settings":       system_settings,
        "loan_settings":         loan_settings,
        "notification_settings": notification_list,

        # Active sessions — wire up your own queryset here if needed
        "active_sessions":       [],
    }

    return render(request, "accounts/settings.html", context)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _dec(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class _Proxy:
    """Dict → dot-accessible object for template context."""
    def __init__(self, data: dict):
        for k, v in data.items():
            setattr(self, k, v)
