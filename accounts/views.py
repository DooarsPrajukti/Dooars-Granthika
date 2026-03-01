import base64
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
import json
from datetime import date, datetime, timedelta
# optional email service
try:
    import core.email_service as email_service
except Exception:
    email_service = None
import json
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from django.utils.timesince import timesince

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


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS  (add these as module-level functions)
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    """Return the Library for the logged-in admin or raise Http404."""
    try:
        return request.user.library   # OneToOne reverse on accounts.Library
    except Exception:
        raise Http404("No library associated with this account.")


def _first_of_month(ref_date, months_back=0):
    """
    Return the first day of the month that is `months_back` months before
    `ref_date`.  Works correctly across year boundaries.
    """
    m = ref_date.month - months_back
    y = ref_date.year
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _first_of_next_month(d):
    """Return the first day of the month following `d`."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def admin_dashboard(request):
    library = _get_library_or_404(request)
    owner   = library.user

    from accounts.models import Library
    from books.models import Book, Category
    from members.models import Member
    from transactions.models import Transaction

    today            = date.today()
    this_month_start = _first_of_month(today, months_back=0)
    last_month_start = _first_of_month(today, months_back=1)
    last_month_end   = this_month_start - timedelta(days=1)

    # ── Section 1 · Library Overview ─────────────────────────────────────────

    if request.user.is_superuser:
        total_libraries      = Library.objects.count()
        libraries_this_month = Library.objects.filter(created_at__date__gte=this_month_start).count()
        libraries_last_month = Library.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
        ).count()
    else:
        total_libraries      = 1
        libraries_this_month = 0
        libraries_last_month = 0
    libraries_change = libraries_this_month - libraries_last_month

    total_books  = Book.objects.filter(owner=owner).count()
    books_change = (
        Book.objects.filter(owner=owner, created_at__date__gte=this_month_start).count()
        - Book.objects.filter(
            owner=owner,
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
        ).count()
    )

    total_members  = Member.objects.filter(owner=owner, status="active").count()
    members_change = (
        Member.objects.filter(owner=owner, date_joined__gte=this_month_start).count()
        - Member.objects.filter(
            owner=owner,
            date_joined__gte=last_month_start,
            date_joined__lte=last_month_end,
        ).count()
    )

    base_txns           = Transaction.objects.for_library(library)
    active_transactions = base_txns.filter(
        status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE)
    ).count()
    transactions_change = (
        base_txns.filter(issue_date__gte=this_month_start).count()
        - base_txns.filter(
            issue_date__gte=last_month_start,
            issue_date__lte=last_month_end,
        ).count()
    )

    # ── Section 2 · Membership Statistics ────────────────────────────────────

    count_map = {
        row["status"]: row["cnt"]
        for row in Member.objects.filter(owner=owner)
            .values("status")
            .annotate(cnt=Count("id"))
    }
    active_count   = count_map.get("active",   0)
    passout_count  = count_map.get("passout",  0)
    inactive_count = count_map.get("inactive", 0)
    total_count    = active_count + passout_count + inactive_count

    def _pct(n):
        return round(n / total_count * 100, 1) if total_count else 0

    stats = {
        "active_count":        active_count,
        "passout_count":       passout_count,
        "inactive_count":      inactive_count,
        "total_count":         total_count,
        "active_percentage":   _pct(active_count),
        "passout_percentage":  _pct(passout_count),
        "inactive_percentage": _pct(inactive_count),
    }

    # ── Chart 1 · Monthly Loans (last 6 months) ───────────────────────────────
    # Build raw Python lists first so we can check if any data is non-zero.

    _loan_labels_raw = []
    _loan_data_raw   = []
    for i in range(5, -1, -1):
        ms  = _first_of_month(today, months_back=i)
        me  = _first_of_next_month(ms)
        cnt = base_txns.filter(issue_date__gte=ms, issue_date__lt=me).count()
        _loan_labels_raw.append(ms.strftime("%b %Y"))
        _loan_data_raw.append(cnt)

    # The template {% if monthly_loan_labels and monthly_loan_data %} must
    # receive values that are falsy when there is no real data.
    # We always have labels (month names), so gate on whether any loans exist.
    loans_have_data = any(v > 0 for v in _loan_data_raw)

    # ── Chart 2 · Books by Category ───────────────────────────────────────────

    cat_qs = (
        Category.objects
        .filter(owner=owner)
        .annotate(cnt=Count("books"))
        .filter(cnt__gt=0)
        .order_by("-cnt")[:8]
    )
    _cat_labels_raw = [c.name for c in cat_qs]
    _cat_data_raw   = [c.cnt  for c in cat_qs]
    categories_have_data = len(_cat_labels_raw) > 0

    # ── Chart 3 · New Members per day (last 7 days) ───────────────────────────

    day_count_map = {
        row["date_joined"]: row["cnt"]
        for row in Member.objects.filter(
            owner=owner,
            date_joined__gte=today - timedelta(days=6),
            date_joined__lte=today,
        ).values("date_joined").annotate(cnt=Count("id"))
    }
    _day_labels_raw = []
    _day_data_raw   = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        _day_labels_raw.append(d.strftime("%a"))
        _day_data_raw.append(day_count_map.get(d, 0))

    members_chart_have_data = any(v > 0 for v in _day_data_raw)

    # ── Chart 4 · Members by Department ──────────────────────────────────────

    dept_qs = (
        Member.objects
        .filter(owner=owner)
        .values("department__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    _dept_labels_raw = [row["department__name"] or "No Department" for row in dept_qs]
    _dept_data_raw   = [row["cnt"] for row in dept_qs]

    # ── Recent Activity Feed ──────────────────────────────────────────────────

    recent_activities = []

    for txn in base_txns.select_related("member", "book").order_by("-created_at")[:5]:
        if txn.status == Transaction.STATUS_RETURNED:
            icon, color, title = "undo-alt",           "green",  f"Book returned: {txn.book.title}"
        elif txn.status == Transaction.STATUS_OVERDUE:
            icon, color, title = "exclamation-triangle","red",   f"Overdue: {txn.book.title}"
        elif txn.status == Transaction.STATUS_LOST:
            icon, color, title = "times-circle",        "red",   f"Lost book: {txn.book.title}"
        else:
            icon, color, title = "book",                "blue",  f"Book issued: {txn.book.title}"
        recent_activities.append({
            "title":       title,
            "description": f"{txn.member.first_name} {txn.member.last_name}",
            "icon":        icon,
            "color":       color,
            "timestamp":   timesince(txn.created_at) + " ago",
        })

    for m in Member.objects.filter(owner=owner).order_by("-date_joined", "-id")[:3]:
        joined_dt  = datetime.combine(m.date_joined, datetime.min.time())
        role_label = m.get_role_display() if hasattr(m, "get_role_display") else ""
        recent_activities.append({
            "title":       f"New member: {m.first_name} {m.last_name}",
            "description": f"ID: {m.member_id}  {role_label}".strip(),
            "icon":        "user-plus",
            "color":       "purple",
            "timestamp":   timesince(joined_dt) + " ago",
        })

    recent_activities = recent_activities[:8]

    # ── Recent Members Table ──────────────────────────────────────────────────

    recent_members = (
        Member.objects
        .filter(owner=owner)
        .select_related("department")
        .order_by("-date_joined", "-id")[:5]
    )

    # ── UI Helpers ────────────────────────────────────────────────────────────

    library_logo_b64 = ""
    if library.library_logo and library.library_logo_mime:
        import base64
        raw = base64.b64encode(bytes(library.library_logo)).decode("ascii")
        library_logo_b64 = f"data:{library.library_logo_mime};base64,{raw}"

    notification_count = base_txns.filter(status=Transaction.STATUS_OVERDUE).count()

    # ── Build context ─────────────────────────────────────────────────────────
    #
    # The template's {% if monthly_loan_labels and monthly_loan_data %} check
    # needs the variables to be FALSY when there is no meaningful data.
    #
    # Strategy:
    #   • Pass the Python list as  monthly_loan_labels / monthly_loan_data
    #     so {% if %} evaluates the list (empty list = False).
    #   • The template then does  {{ monthly_loan_labels|safe }}  which on a
    #     Python list outputs its repr — NOT valid JSON.
    #
    # Fix: we pre-serialise to JSON and pass the JSON string, but we set the
    # variable to an EMPTY STRING (falsy) when there is no real data.
    # The template's |safe filter will output "" which becomes an empty JS
    # expression — so we must keep the {% else %}[]{% endif %} fallback intact.
    #
    # This is the cleanest way without touching the template at all.

    monthly_loan_labels = json.dumps(_loan_labels_raw)   if loans_have_data        else ""
    monthly_loan_data   = json.dumps(_loan_data_raw)     if loans_have_data        else ""
    category_labels     = json.dumps(_cat_labels_raw)    if categories_have_data   else ""
    category_data       = json.dumps(_cat_data_raw)      if categories_have_data   else ""
    member_day_labels   = json.dumps(_day_labels_raw)    if members_chart_have_data else ""
    member_day_data     = json.dumps(_day_data_raw)      if members_chart_have_data else ""

    # Department + status charts are always shown (they have inline fallback)
    department_labels = json.dumps(_dept_labels_raw)
    department_data   = json.dumps(_dept_data_raw)

    return render(request, "dashboards/admin_dashboard.html", {
        # Section 1
        "total_libraries":     total_libraries,
        "libraries_change":    libraries_change,
        "total_books":         total_books,
        "books_change":        books_change,
        "total_members":       total_members,
        "members_change":      members_change,
        "active_transactions": active_transactions,
        "transactions_change": transactions_change,
        # Section 2
        "stats": stats,
        # Charts — empty string when no data (falsy for {% if %} checks)
        "monthly_loan_labels": monthly_loan_labels,
        "monthly_loan_data":   monthly_loan_data,
        "category_labels":     category_labels,
        "category_data":       category_data,
        "member_day_labels":   member_day_labels,
        "member_day_data":     member_day_data,
        "department_labels":   department_labels,
        "department_data":     department_data,
        # Activity + table
        "recent_activities": recent_activities,
        "recent_members":    recent_members,
        # UI
        "library_logo_b64":   library_logo_b64,
        "notification_count": notification_count,
    })



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
                logo_file = request.FILES["library_logo"]
                library.library_logo      = logo_file.read()
                library.library_logo_mime = logo_file.content_type
            elif request.POST.get("remove_logo") == "1":
                library.library_logo      = None
                library.library_logo_mime = None

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

        # ── members ───────────────────────────────────────────────
        elif section == "members":
            member_cfg.student_borrow_limit     = _int(request.POST.get("student_borrow_limit"),     member_cfg.student_borrow_limit)
            member_cfg.teacher_borrow_limit     = _int(request.POST.get("teacher_borrow_limit"),     member_cfg.teacher_borrow_limit)
            member_cfg.membership_validity_days = _int(request.POST.get("membership_validity_days"), member_cfg.membership_validity_days)
            member_cfg.member_id_format         = request.POST.get("member_id_format", member_cfg.member_id_format).strip()
            member_cfg.allow_self_registration  = request.POST.get("allow_self_registration")  == "on"
            member_cfg.require_admin_approval   = request.POST.get("require_admin_approval")   == "on"
            member_cfg.enable_member_id_download= request.POST.get("enable_member_id_download")== "on"
            member_cfg.allow_profile_edit       = request.POST.get("allow_profile_edit")       == "on"
            member_cfg.save()
            messages.success(request, "Member settings saved.")

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

    # ── Build base64 logo data-URI for template ────────────────
    library_logo_b64 = None
    if library.library_logo:
        mime = library.library_logo_mime or "image/png"
        encoded = base64.b64encode(bytes(library.library_logo)).decode("utf-8")
        library_logo_b64 = f"data:{mime};base64,{encoded}"

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

        # Logo as base64 data-URI (blob from MySQL)
        "library_logo_b64":      library_logo_b64,

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




# def staff_dashboard(request):
#     return render(request, 'dashboards/staff_dashboard.html')