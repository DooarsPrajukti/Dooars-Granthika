import base64
import json
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.timesince import timesince


# ==========================================================
# 🏠 ADMIN DASHBOARD
# ==========================================================
@login_required
def admin_dashboard(request):
    from accounts.models import Library, LibraryRuleSettings
    from books.models import Book, Category
    from members.models import Member
    from transactions.models import Transaction

    library = _get_library_or_404(request)

    rules_qs = LibraryRuleSettings.objects.filter(library=library).first()
    if rules_qs and not getattr(rules_qs, "is_setup_complete", False):
        return redirect("accounts:library_setup")

    owner = library.user
    today            = date.today()
    this_month_start = _first_of_month(today, months_back=0)
    last_month_start = _first_of_month(today, months_back=1)
    last_month_end   = this_month_start - timedelta(days=1)

    # ── Library count (superuser sees all) ───────────────────
    if request.user.is_superuser:
        total_libraries      = Library.objects.count()
        libraries_this_month = Library.objects.filter(
            created_at__date__gte=this_month_start
        ).count()
        libraries_last_month = Library.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
        ).count()
    else:
        total_libraries = 1
        libraries_this_month = libraries_last_month = 0
    libraries_change = libraries_this_month - libraries_last_month

    # ── Books ─────────────────────────────────────────────────
    total_books  = Book.objects.filter(owner=owner).count()
    books_change = (
        Book.objects.filter(owner=owner, created_at__date__gte=this_month_start).count()
        - Book.objects.filter(
            owner=owner,
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
        ).count()
    )

    # ── Members ───────────────────────────────────────────────
    total_members  = Member.objects.filter(owner=owner, status="active").count()
    members_change = (
        Member.objects.filter(owner=owner, date_joined__gte=this_month_start).count()
        - Member.objects.filter(
            owner=owner,
            date_joined__gte=last_month_start,
            date_joined__lte=last_month_end,
        ).count()
    )

    # ── Transactions ──────────────────────────────────────────
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

    # ── Member status breakdown ───────────────────────────────
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

    # ── Chart 1: Monthly Loans (last 6 months) ────────────────
    _loan_labels_raw, _loan_data_raw = [], []
    for i in range(5, -1, -1):
        ms  = _first_of_month(today, months_back=i)
        me  = _first_of_next_month(ms)
        cnt = base_txns.filter(issue_date__gte=ms, issue_date__lt=me).count()
        _loan_labels_raw.append(ms.strftime("%b %Y"))
        _loan_data_raw.append(cnt)
    loans_have_data = any(v > 0 for v in _loan_data_raw)

    # ── Chart 2: Books by Category ────────────────────────────
    cat_qs = (
        Category.objects
        .filter(owner=owner)
        .annotate(cnt=Count("books"))
        .filter(cnt__gt=0)
        .order_by("-cnt")[:8]
    )
    _cat_labels_raw      = [c.name for c in cat_qs]
    _cat_data_raw        = [c.cnt  for c in cat_qs]
    categories_have_data = len(_cat_labels_raw) > 0

    # ── Chart 3: New Members per day (last 7 days) ────────────
    day_count_map = {
        row["date_joined"]: row["cnt"]
        for row in Member.objects.filter(
            owner=owner,
            date_joined__gte=today - timedelta(days=6),
            date_joined__lte=today,
        ).values("date_joined").annotate(cnt=Count("id"))
    }
    _day_labels_raw, _day_data_raw = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        _day_labels_raw.append(d.strftime("%a"))
        _day_data_raw.append(day_count_map.get(d, 0))
    members_chart_have_data = any(v > 0 for v in _day_data_raw)

    # ── Chart 4: Members by Department ───────────────────────
    dept_qs = (
        Member.objects
        .filter(owner=owner)
        .values("department__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    _dept_labels_raw = [row["department__name"] or "No Department" for row in dept_qs]
    _dept_data_raw   = [row["cnt"] for row in dept_qs]

    # ── Recent Activity Feed ──────────────────────────────────
    recent_activities = []
    for txn in base_txns.select_related("member", "book").order_by("-created_at")[:5]:
        if txn.status == Transaction.STATUS_RETURNED:
            icon, color, title = "undo-alt",             "green",  f"Book returned: {txn.book.title}"
        elif txn.status == Transaction.STATUS_OVERDUE:
            icon, color, title = "exclamation-triangle",  "red",   f"Overdue: {txn.book.title}"
        elif txn.status == Transaction.STATUS_LOST:
            icon, color, title = "times-circle",          "red",   f"Lost book: {txn.book.title}"
        else:
            icon, color, title = "book",                  "blue",  f"Book issued: {txn.book.title}"
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

    recent_members = (
        Member.objects
        .filter(owner=owner)
        .select_related("department")
        .order_by("-date_joined", "-id")[:5]
    )

    # ── Library logo ──────────────────────────────────────────
    library_logo_b64 = ""
    if library.library_logo and library.library_logo_mime:
        raw = base64.b64encode(bytes(library.library_logo)).decode("ascii")
        library_logo_b64 = f"data:{library.library_logo_mime};base64,{raw}"

    notification_count = base_txns.filter(status=Transaction.STATUS_OVERDUE).count()

    return render(request, "dashboards/admin_dashboard.html", {
        "total_libraries":     total_libraries,
        "libraries_change":    libraries_change,
        "total_books":         total_books,
        "books_change":        books_change,
        "total_members":       total_members,
        "members_change":      members_change,
        "active_transactions": active_transactions,
        "transactions_change": transactions_change,
        "stats":               stats,
        "monthly_loan_labels": json.dumps(_loan_labels_raw) if loans_have_data         else "",
        "monthly_loan_data":   json.dumps(_loan_data_raw)   if loans_have_data         else "",
        "category_labels":     json.dumps(_cat_labels_raw)  if categories_have_data    else "",
        "category_data":       json.dumps(_cat_data_raw)    if categories_have_data    else "",
        "member_day_labels":   json.dumps(_day_labels_raw)  if members_chart_have_data else "",
        "member_day_data":     json.dumps(_day_data_raw)    if members_chart_have_data else "",
        "department_labels":   json.dumps(_dept_labels_raw),
        "department_data":     json.dumps(_dept_data_raw),
        "recent_activities":   recent_activities,
        "recent_members":      recent_members,
        "library_logo_b64":    library_logo_b64,
        "notification_count":  notification_count,
    })


# ==========================================================
# HELPERS
# ==========================================================

def _get_library_or_404(request):
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


def _first_of_month(ref_date, months_back=0):
    m, y = ref_date.month - months_back, ref_date.year
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _first_of_next_month(d):
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)