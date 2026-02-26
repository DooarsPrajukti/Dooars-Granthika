"""
members/views.py
────────────────
All views for the members app.
Every queryset is filtered by `owner=request.user` (multi-tenancy).

Photo serving
─────────────
Member photos are stored as binary blobs (BinaryField) in MySQL.
Use the `member_photo` view to serve them:
    <img src="{% url 'members:member_photo' member.pk %}">
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json

from .models import Member, Department, Course, AcademicYear, Semester, Transaction
from .forms import (
    MemberForm, DepartmentForm, CourseForm, AcademicYearForm, SemesterForm,
    StudentMemberForm, TeacherMemberForm, GeneralMemberForm,
)

# Map role string → role-specific form class
_ROLE_FORM_MAP = {
    "student": StudentMemberForm,
    "teacher": TeacherMemberForm,
    "general": GeneralMemberForm,
}

def _get_role_form(role):
    """Return the appropriate role form class, defaulting to StudentMemberForm."""
    return _ROLE_FORM_MAP.get(role, StudentMemberForm)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _owner_ctx(request):
    """Return the four lookup querysets that every list page needs."""
    return {
        "departments":   Department.objects.filter(owner=request.user),
        "courses":       Course.objects.filter(owner=request.user),
        "academic_years": AcademicYear.objects.filter(owner=request.user),
        "semesters":     Semester.objects.filter(owner=request.user),
    }


def _paginate(qs_or_list, request, per_page=20):
    paginator = Paginator(qs_or_list, per_page)
    page_obj  = paginator.get_page(request.GET.get("page"))
    return page_obj


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def members_dashboard(request):
    """High-level statistics dashboard – owner isolated."""
    members = Member.objects.filter(owner=request.user)

    total    = members.count()
    active   = members.filter(status="active").count()
    passout  = members.filter(status="passout").count()
    inactive = members.filter(status="inactive").count()

    def pct(n):
        return round(n / total * 100, 1) if total else 0

    stats = {
        "total_count":        total,
        "active_count":       active,
        "passout_count":      passout,
        "inactive_count":     inactive,
        "active_percentage":  pct(active),
        "passout_percentage": pct(passout),
        "inactive_percentage": pct(inactive),
    }

    recent_members = members.order_by("-created_at")[:10]

    departments = (
        Department.objects.filter(owner=request.user)
        .annotate(member_count=Count("members"))
        .filter(member_count__gt=0)
    )

    context = {
        **stats,
        "stats":             stats,
        "recent_members":    recent_members,
        "department_labels": json.dumps([d.name for d in departments]),
        "department_data":   json.dumps([d.member_count for d in departments]),
    }
    return render(request, "members/members_dashboard.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Member list views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def members_list(request):
    """All members with multi-field filtering."""
    members = Member.objects.filter(owner=request.user).select_related(
        "department", "course", "year", "semester"
    )

    status = request.GET.get("status")
    if status:
        members = members.filter(status=status)

    role = request.GET.get("role")
    if role:
        members = members.filter(role=role)

    dept = request.GET.get("department")
    if dept:
        members = members.filter(department_id=dept)

    course = request.GET.get("course")
    if course:
        members = members.filter(course_id=course)

    year = request.GET.get("year")
    if year:
        members = members.filter(year_id=year)

    semester = request.GET.get("semester")
    if semester:
        members = members.filter(semester_id=semester)

    search = request.GET.get("search", "").strip()
    if search:
        members = members.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(member_id__icontains=search)
            | Q(phone__icontains=search)
            | Q(roll_number__icontains=search)
        )

    page_obj = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "members/members_list.html", context)


@login_required
def members_active(request):
    """Active members only."""
    members = Member.objects.filter(
        owner=request.user, status="active"
    ).select_related("department", "course", "year", "semester")

    dept = request.GET.get("department")
    if dept:
        members = members.filter(department_id=dept)

    course = request.GET.get("course")
    if course:
        members = members.filter(course_id=course)

    year = request.GET.get("year")
    if year:
        members = members.filter(year_id=year)

    search = request.GET.get("search", "").strip()
    if search:
        members = members.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(member_id__icontains=search)
        )

    page_obj = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "members/members_active.html", context)


@login_required
def members_inactive(request):
    """Inactive members only."""
    members = Member.objects.filter(
        owner=request.user, status="inactive"
    ).select_related("department", "course", "year", "semester")

    dept = request.GET.get("department")
    if dept:
        members = members.filter(department_id=dept)

    reason = request.GET.get("reason")
    if reason:
        members = members.filter(inactive_reason__icontains=reason)

    year = request.GET.get("year")
    if year:
        members = members.filter(year_id=year)

    page_obj = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "members/members_inactive.html", context)


@login_required
def members_passout(request):
    """Pass-out members with clearance filter."""
    members = Member.objects.filter(
        owner=request.user, status="passout"
    ).select_related("department", "course", "year", "semester")

    dept = request.GET.get("department")
    if dept:
        members = members.filter(department_id=dept)

    passout_year = request.GET.get("passout_year")
    if passout_year:
        try:
            from django.db.models import F, ExpressionWrapper, IntegerField
            py = int(passout_year)
            members = members.annotate(
                computed_passout_year=ExpressionWrapper(
                    F("admission_year") + F("course__duration"),
                    output_field=IntegerField(),
                )
            ).filter(computed_passout_year=py)
        except (ValueError, TypeError):
            pass

    clearance = request.GET.get("clearance")
    if clearance:
        members = members.filter(clearance_status=clearance)

    page_obj = _paginate(members, request)

    # Build distinct passout years for the filter dropdown
    from django.db.models import F, ExpressionWrapper, IntegerField
    passout_years = (
        Member.objects.filter(owner=request.user, status="passout")
        .exclude(admission_year__isnull=True)
        .exclude(course__isnull=True)
        .annotate(
            passout_yr=ExpressionWrapper(
                F("admission_year") + F("course__duration"),
                output_field=IntegerField(),
            )
        )
        .values_list("passout_yr", flat=True)
        .distinct()
        .order_by("-passout_yr")
    )

    context = {
        **_owner_ctx(request),
        "members":       page_obj,
        "page_obj":      page_obj,
        "is_paginated":  page_obj.has_other_pages(),
        "passout_years": passout_years,
    }
    return render(request, "members/members_passout.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Member CRUD
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def member_detail(request, pk):
    """Member detail page."""
    member = get_object_or_404(Member, pk=pk, owner=request.user)
    transactions = Transaction.objects.filter(
        member=member, owner=request.user
    ).order_by("-issue_date")[:10]

    context = {
        "member":       member,
        "transactions": transactions,
    }
    return render(request, "members/member_detail.html", context)


@login_required
def member_add(request):
    """
    Add a new member.
    Uses the role-specific form (StudentMemberForm / TeacherMemberForm /
    GeneralMemberForm) so each role only validates and saves its relevant
    fields.  Supports select-or-create for Department, Course, AcademicYear,
    Semester.
    """
    if request.method == "POST":
        role      = request.POST.get("role", "student")
        FormClass = _get_role_form(role)
        form      = FormClass(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            member = form.save_with_create()
            messages.success(
                request, f"Member {member.full_name} added successfully!"
            )
            return redirect("members:member_detail", pk=member.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentMemberForm(user=request.user)

    context = {
        **_owner_ctx(request),
        "form": form,
    }
    return render(request, "members/member_add.html", context)


@login_required
def member_edit(request, pk):
    """
    Edit an existing member.
    The role-specific form is chosen based on the submitted role (POST) or the
    member's current role (GET), so each role only validates its own fields.
    """
    member = get_object_or_404(Member, pk=pk, owner=request.user)

    if request.method == "POST":
        role      = request.POST.get("role", member.role)
        FormClass = _get_role_form(role)
        form      = FormClass(
            request.POST, request.FILES, instance=member, user=request.user
        )
        if form.is_valid():
            member = form.save_with_create()
            messages.success(
                request, f"Member {member.full_name} updated successfully!"
            )
            return redirect("members:member_detail", pk=member.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        FormClass = _get_role_form(member.role)
        form = FormClass(instance=member, user=request.user)

    context = {
        **_owner_ctx(request),
        "form":   form,
        "member": member,
    }
    return render(request, "members/member_edit.html", context)


@login_required
def member_delete(request, pk):
    """Delete a member (POST only)."""
    member = get_object_or_404(Member, pk=pk, owner=request.user)

    if request.method == "POST":
        name = member.full_name
        member.delete()
        messages.success(request, f"Member {name} deleted successfully!")
        return redirect("members:members_list")

    return redirect("members:member_detail", pk=pk)


@login_required
def member_photo(request, pk):
    """
    Serve a member's photo stored as a binary blob in MySQL.

    BinaryField returns a memoryview in Python; we cast it to bytes before
    passing it to HttpResponse.

    Template usage:
        <img src="{% url 'members:member_photo' member.pk %}">
    """
    member = get_object_or_404(Member, pk=pk, owner=request.user)

    if not member.photo:
        return HttpResponse(status=404)

    return HttpResponse(
        bytes(member.photo),
        content_type=member.photo_mime_type or "image/jpeg",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Member actions
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def member_reactivate(request, pk):
    """Reactivate an inactive member."""
    if request.method == "POST":
        member = get_object_or_404(Member, pk=pk, owner=request.user)
        member.status        = "active"
        member.inactive_since  = None
        member.inactive_reason = None
        member.save()
        messages.success(
            request, f"Member {member.full_name} reactivated successfully!"
        )
        return redirect("members:member_detail", pk=pk)
    return redirect("members:members_inactive")


@login_required
def member_mark_cleared(request, pk):
    """Mark a member as cleared (only if truly no pending items)."""
    if request.method == "POST":
        member = get_object_or_404(Member, pk=pk, owner=request.user)

        pending_books = Transaction.objects.filter(
            member=member, owner=request.user, status__in=["issued", "overdue"]
        ).count()

        pending_fines = (
            Transaction.objects.filter(
                member=member, owner=request.user, fine_paid=False
            ).aggregate(total=Sum("fine_amount"))["total"]
            or 0
        )

        if pending_books == 0 and pending_fines == 0:
            member.clearance_status = "cleared"
            member.clearance_date   = timezone.now()
            member.cleared_by       = request.user
            member.save()
            messages.success(
                request, f"Member {member.full_name} marked as cleared!"
            )
        else:
            messages.error(
                request,
                f"Cannot clear member. Pending: {pending_books} book(s), "
                f"₹{pending_fines} in fines.",
            )
        return redirect("members:member_detail", pk=pk)

    return redirect("members:pending_clearance")


@login_required
def send_reminder(request, pk):
    """Send a reminder notification to the member (stub; wire up email/SMS here)."""
    if request.method == "POST":
        member = get_object_or_404(Member, pk=pk, owner=request.user)
        # TODO: integrate email / SMS service
        return JsonResponse(
            {"success": True, "message": f"Reminder sent to {member.full_name}"}
        )
    return JsonResponse({"success": False, "message": "Invalid request"})


# ──────────────────────────────────────────────────────────────────────────────
# Clearance views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def clearance_check(request):
    """
    Check clearance status by member-ID or phone number.
    POST → returns JSON (consumed by members.js frontend).
    GET  → renders the check page.
    """
    if request.method == "POST":
        query = (request.POST.get("member_id") or "").strip()
        try:
            member = (
                Member.objects.filter(owner=request.user)
                .filter(Q(member_id=query) | Q(phone=query))
                .first()
            )

            if not member:
                return JsonResponse({"success": False, "message": "Member not found"})

            pending_books = Transaction.objects.filter(
                member=member,
                owner=request.user,
                status__in=["issued", "overdue"],
            ).count()

            pending_fines = (
                Transaction.objects.filter(
                    member=member, owner=request.user, fine_paid=False
                ).aggregate(total=Sum("fine_amount"))["total"]
                or 0
            )

            payload = {
                "member_id":        member.member_id,
                "full_name":        member.full_name,
                "email":            member.email,
                "phone":            member.phone,
                "department":       member.department.name if member.department else None,
                "role":             member.get_role_display(),
                "status":           member.status,
                "clearance_status": member.clearance_status,
                "pending_books":    pending_books,
                "pending_fines":    float(pending_fines),
                "is_cleared":       pending_books == 0 and float(pending_fines) == 0,
                "clearance_date":   (
                    member.clearance_date.strftime("%d %b %Y")
                    if member.clearance_date else None
                ),
            }
            return JsonResponse({"success": True, "data": payload})

        except Exception as exc:
            return JsonResponse({"success": False, "message": str(exc)})

    return render(request, "members/clearance_check.html")


@login_required
def cleared_members(request):
    """Members who have been fully cleared."""
    members = Member.objects.filter(
        owner=request.user, clearance_status="cleared"
    ).select_related("department", "cleared_by")

    dept = request.GET.get("department")
    if dept:
        members = members.filter(department_id=dept)

    clearance_date = request.GET.get("clearance_date")
    now = timezone.now()
    if clearance_date == "today":
        members = members.filter(clearance_date__date=now.date())
    elif clearance_date == "week":
        members = members.filter(clearance_date__gte=now - timedelta(days=7))
    elif clearance_date == "month":
        members = members.filter(clearance_date__gte=now - timedelta(days=30))
    elif clearance_date == "year":
        members = members.filter(clearance_date__gte=now - timedelta(days=365))

    member_type = request.GET.get("member_type")
    if member_type:
        members = members.filter(status=member_type)

    page_obj = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "members/cleared_members.html", context)


@login_required
def pending_clearance(request):
    """Members with outstanding books or fines."""
    base_qs = Member.objects.filter(
        owner=request.user, clearance_status="pending"
    ).select_related("department")

    # Annotate pending data in Python (avoids complex ORM across tenant-scoped
    # Transaction rows)
    pending_members = []
    for member in base_qs:
        pending_books = Transaction.objects.filter(
            member=member, owner=request.user, status__in=["issued", "overdue"]
        ).count()

        pending_fines = (
            Transaction.objects.filter(
                member=member, owner=request.user, fine_paid=False
            ).aggregate(total=Sum("fine_amount"))["total"]
            or 0
        )

        lost_items = Transaction.objects.filter(
            member=member, owner=request.user, status="lost"
        ).count()

        if pending_books > 0 or float(pending_fines) > 0 or lost_items > 0:
            oldest = (
                Transaction.objects.filter(
                    member=member,
                    owner=request.user,
                    status__in=["issued", "overdue"],
                )
                .order_by("issue_date")
                .first()
            )
            member.pending_books    = pending_books
            member.total_fine       = pending_fines
            member.pending_damages  = 0
            member.pending_lost     = lost_items
            member.days_pending     = (
                (timezone.now().date() - oldest.issue_date.date()).days
                if oldest else 0
            )
            pending_members.append(member)

    # Department filter (post-annotation)
    dept_filter = request.GET.get("department")
    if dept_filter:
        pending_members = [
            m for m in pending_members if m.department_id == int(dept_filter)
        ]

    # Aggregate stats
    stats = {
        "unreturned_books": sum(m.pending_books for m in pending_members),
        "total_fines":      sum(float(m.total_fine) for m in pending_members),
        "overdue_books":    Transaction.objects.filter(
            owner=request.user, status="overdue"
        ).count(),
    }

    page_obj = _paginate(pending_members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "stats":        stats,
    }
    return render(request, "members/pending_clearance.html", context)


@login_required
def clearance_certificate(request, pk):
    """
    Generate a clearance certificate PDF.
    Requires reportlab (pip install reportlab) – stub provided as fallback.
    """
    member = get_object_or_404(
        Member, pk=pk, owner=request.user, clearance_status="cleared"
    )

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        import io

        buf = io.BytesIO()
        c   = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 100, "Library Clearance Certificate")

        c.setFont("Helvetica", 13)
        lines = [
            f"Member Name   : {member.full_name}",
            f"Member ID     : {member.member_id}",
            f"Department    : {member.department.name if member.department else 'N/A'}",
            f"Clearance Date: {member.clearance_date.strftime('%d %B %Y') if member.clearance_date else 'N/A'}",
            f"Cleared By    : {member.cleared_by.get_full_name() if member.cleared_by else 'System'}",
        ]
        y = height - 180
        for line in lines:
            c.drawString(80, y, line)
            y -= 30

        c.setFont("Helvetica-Oblique", 11)
        c.drawCentredString(
            width / 2, 150,
            "This certificate confirms that the above member has cleared all library obligations.",
        )
        c.save()
        buf.seek(0)

        response = HttpResponse(buf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="clearance_{member.member_id}.pdf"'
        )
        return response

    except ImportError:
        # Fallback: plain-text stub when reportlab is not installed
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="clearance_{member.member_id}.pdf"'
        )
        response.write(
            f"Clearance Certificate\n\nMember: {member.full_name}\n"
            f"ID: {member.member_id}\nStatus: Cleared\n".encode()
        )
        return response


# ──────────────────────────────────────────────────────────────────────────────
# Department / Course / AcademicYear / Semester management
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def department_list(request):
    """List / create departments."""
    departments = Department.objects.filter(owner=request.user)

    if request.method == "POST":
        form = DepartmentForm(request.POST, user=request.user)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.owner = request.user
            dept.save()
            messages.success(request, f"Department '{dept.name}' created.")
            return redirect("members:department_list")
    else:
        form = DepartmentForm(user=request.user)

    return render(
        request,
        "members/department_list.html",
        {"departments": departments, "form": form},
    )


@login_required
def department_delete(request, pk):
    if request.method == "POST":
        dept = get_object_or_404(Department, pk=pk, owner=request.user)
        dept.delete()
        messages.success(request, "Department deleted.")
    return redirect("members:department_list")


@login_required
def course_list(request):
    """List / create courses."""
    courses = Course.objects.filter(owner=request.user)

    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            messages.success(request, f"Course '{course.name}' created.")
            return redirect("members:course_list")
    else:
        form = CourseForm(user=request.user)

    return render(
        request,
        "members/course_list.html",
        {"courses": courses, "form": form},
    )


@login_required
def course_delete(request, pk):
    if request.method == "POST":
        course = get_object_or_404(Course, pk=pk, owner=request.user)
        course.delete()
        messages.success(request, "Course deleted.")
    return redirect("members:course_list")


@login_required
def academic_year_list(request):
    """List / create academic years."""
    years = AcademicYear.objects.filter(owner=request.user)

    if request.method == "POST":
        form = AcademicYearForm(request.POST, user=request.user)
        if form.is_valid():
            yr = form.save(commit=False)
            yr.owner = request.user
            yr.save()
            messages.success(request, f"Academic year '{yr.name}' created.")
            return redirect("members:academic_year_list")
    else:
        form = AcademicYearForm(user=request.user)

    return render(
        request,
        "members/academic_year_list.html",
        {"years": years, "form": form},
    )


@login_required
def academic_year_delete(request, pk):
    if request.method == "POST":
        yr = get_object_or_404(AcademicYear, pk=pk, owner=request.user)
        yr.delete()
        messages.success(request, "Academic year deleted.")
    return redirect("members:academic_year_list")


@login_required
def semester_list(request):
    """List / create semesters."""
    semesters = Semester.objects.filter(owner=request.user)

    if request.method == "POST":
        form = SemesterForm(request.POST, user=request.user)
        if form.is_valid():
            sem = form.save(commit=False)
            sem.owner = request.user
            sem.save()
            messages.success(request, f"Semester '{sem.name}' created.")
            return redirect("members:semester_list")
    else:
        form = SemesterForm(user=request.user)

    return render(
        request,
        "members/semester_list.html",
        {"semesters": semesters, "form": form},
    )


@login_required
def semester_delete(request, pk):
    if request.method == "POST":
        sem = get_object_or_404(Semester, pk=pk, owner=request.user)
        sem.delete()
        messages.success(request, "Semester deleted.")
    return redirect("members:semester_list")