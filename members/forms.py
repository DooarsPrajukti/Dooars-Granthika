"""
members/forms.py
────────────────
Forms for the members app.

Key features
────────────
• MemberForm  – handles select-or-create for Department, Course,
                AcademicYear and Semester; owner-scoped querysets.
• DepartmentForm, CourseForm, AcademicYearForm, SemesterForm – simple
  CRUD forms with owner-scoped uniqueness validation.
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Member, Department, Course, AcademicYear, Semester


# ──────────────────────────────────────────────────────────────────────────────
# Shared widget helpers
# ──────────────────────────────────────────────────────────────────────────────

def _text(placeholder="", **kw):
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder, **kw})


def _select(**kw):
    return forms.Select(attrs={"class": "form-control", **kw})


def _textarea(placeholder="", rows=3, **kw):
    return forms.Textarea(attrs={"class": "form-control", "rows": rows, "placeholder": placeholder, **kw})


def _number(placeholder="", **kw):
    return forms.NumberInput(attrs={"class": "form-control", "placeholder": placeholder, **kw})


# ──────────────────────────────────────────────────────────────────────────────
# MemberForm
# ──────────────────────────────────────────────────────────────────────────────

class MemberForm(forms.ModelForm):
    """
    Member create / edit form.

    Extra (non-model) fields
    ─────────────────────────
    new_department  – free-text; creates a Department on the fly if set.
    new_course      – free-text; creates a Course on the fly if set.
    new_year        – free-text; creates an AcademicYear on the fly if set.
    new_semester    – free-text; creates a Semester on the fly if set.
    photo_upload    – alias so the template can use a different field name
                      from the model's `photo`.

    These are processed in the view via `save_with_create()`.
    """

    # ── Extra "create" fields (optional) ─────────────────────────────────────
    new_department = forms.CharField(
        required=False,
        widget=_text("e.g. Computer Science"),
        label="Create new department",
    )
    new_course = forms.CharField(
        required=False,
        widget=_text("e.g. B.Sc. Honours"),
        label="Create new course",
    )
    new_year = forms.CharField(
        required=False,
        widget=_text("e.g. 3rd Year"),
        label="Create new academic year",
    )
    new_semester = forms.CharField(
        required=False,
        widget=_text("e.g. Semester 5"),
        label="Create new semester",
    )

    # ── Photo upload alias ────────────────────────────────────────────────────
    photo_upload = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Member photo",
    )

    class Meta:
        model = Member
        fields = [
            "first_name", "last_name", "email",
            "phone", "alternate_phone", "guardian_phone",
            "date_of_birth", "gender", "address",
            "department", "course", "year", "semester",
            "roll_number", "admission_year", "status",
            "specialization", "academic_notes",
        ]
        widgets = {
            "first_name": _text("Enter first name"),
            "last_name": _text("Enter last name"),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter email address"}),
            "phone": _text("10-digit number", maxlength="10"),
            "alternate_phone": _text("10-digit number", maxlength="10"),
            "guardian_phone": _text("10-digit number", maxlength="10"),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "gender": _select(),
            "address": _textarea("Enter address"),
            "department": _select(),
            "course": _select(),
            "year": _select(),
            "semester": _select(),
            "roll_number": _text("e.g. CS2024001"),
            "admission_year": _number("e.g. 2024", min="2000", max="2100"),
            "status": _select(),
            "specialization": _text("e.g. Machine Learning, Finance…"),
            "academic_notes": _textarea("Any additional academic information…", rows=2),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields["department"].queryset = (
                Department.objects.filter(owner=user).order_by("name")
            )
            self.fields["course"].queryset = (
                Course.objects.filter(owner=user).order_by("name")
            )
            self.fields["year"].queryset = (
                AcademicYear.objects.filter(owner=user).order_by("order", "name")
            )
            self.fields["semester"].queryset = (
                Semester.objects.filter(owner=user).order_by("order", "name")
            )
        else:
            for f in ("department", "course", "year", "semester"):
                self.fields[f].queryset = self.fields[f].queryset.none()

        # Make FK fields non-required at the form level; the view resolves
        # select-or-create before calling save().
        for f in ("department", "course", "year", "semester"):
            self.fields[f].required = False

    # ── Field-level validation ────────────────────────────────────────────────

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Member.objects.filter(owner=self.user, email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A member with this email already exists in your library."
            )
        return email

    def _validate_phone(self, field_name):
        phone = self.cleaned_data.get(field_name)
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_phone(self):
        return self._validate_phone("phone")

    def clean_alternate_phone(self):
        return self._validate_phone("alternate_phone")

    def clean_guardian_phone(self):
        return self._validate_phone("guardian_phone")

    def clean_photo_upload(self):
        photo = self.cleaned_data.get("photo_upload")
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise ValidationError("Photo size must be less than 5 MB.")
            valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if hasattr(photo, "content_type") and photo.content_type not in valid_types:
                raise ValidationError("Only JPG, PNG, GIF or WebP images are allowed.")
        return photo

    def clean(self):
        cleaned = super().clean()

        # Cross-field ownership check
        for field, Model in (
            ("department", Department),
            ("course", Course),
            ("year", AcademicYear),
            ("semester", Semester),
        ):
            obj = cleaned.get(field)
            if obj and self.user and obj.owner != self.user:
                raise ValidationError(f"Invalid {field} selection.")

        return cleaned

    # ── Convenience save helper ───────────────────────────────────────────────

    def save_with_create(self, commit=True):
        """
        Extended save that:
        1. Creates Department / Course / AcademicYear / Semester on the fly
           when the corresponding new_* field is filled and no FK was chosen.
        2. Maps photo_upload → member.photo.
        """
        if not self.user:
            raise ValueError("Cannot call save_with_create without a user.")

        member = super().save(commit=False)
        member.owner = self.user

        # ── Resolve Department ────────────────────────────────────────────────
        dept = self.cleaned_data.get("department")
        new_dept_name = (self.cleaned_data.get("new_department") or "").strip()
        if not dept and new_dept_name:
            dept, _ = Department.objects.get_or_create(
                owner=self.user,
                name__iexact=new_dept_name,
                defaults={
                    "name": new_dept_name,
                    "code": new_dept_name[:20].upper().replace(" ", "_"),
                },
            )
        member.department = dept

        # ── Resolve Course ────────────────────────────────────────────────────
        course = self.cleaned_data.get("course")
        new_course_name = (self.cleaned_data.get("new_course") or "").strip()
        if not course and new_course_name:
            course, _ = Course.objects.get_or_create(
                owner=self.user,
                name__iexact=new_course_name,
                defaults={
                    "name": new_course_name,
                    "code": new_course_name[:20].upper().replace(" ", "_"),
                    "duration": 3,
                },
            )
        member.course = course

        # ── Resolve AcademicYear ──────────────────────────────────────────────
        year = self.cleaned_data.get("year")
        new_year_name = (self.cleaned_data.get("new_year") or "").strip()
        if not year and new_year_name:
            year, _ = AcademicYear.objects.get_or_create(
                owner=self.user,
                name__iexact=new_year_name,
                defaults={"name": new_year_name},
            )
        member.year = year

        # ── Resolve Semester ──────────────────────────────────────────────────
        semester = self.cleaned_data.get("semester")
        new_semester_name = (self.cleaned_data.get("new_semester") or "").strip()
        if not semester and new_semester_name:
            semester, _ = Semester.objects.get_or_create(
                owner=self.user,
                name__iexact=new_semester_name,
                defaults={"name": new_semester_name},
            )
        member.semester = semester

        # ── Handle photo ──────────────────────────────────────────────────────
        photo = self.cleaned_data.get("photo_upload")
        if photo:
            member.photo = photo

        if commit:
            member.save()
        return member


# ──────────────────────────────────────────────────────────────────────────────
# Department form
# ──────────────────────────────────────────────────────────────────────────────

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description"]
        widgets = {
            "name": _text("Enter department name"),
            "code": _text("Enter department code"),
            "description": _textarea("Enter description (optional)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Department.objects.filter(owner=self.user, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A department with this code already exists in your library."
            )
        return code


# ──────────────────────────────────────────────────────────────────────────────
# Course form
# ──────────────────────────────────────────────────────────────────────────────

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "code", "duration", "description"]
        widgets = {
            "name": _text("Enter course name"),
            "code": _text("Enter course code"),
            "duration": _number("Duration in years", min="1", max="10"),
            "description": _textarea("Enter description (optional)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Course.objects.filter(owner=self.user, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A course with this code already exists in your library."
            )
        return code


# ──────────────────────────────────────────────────────────────────────────────
# AcademicYear form
# ──────────────────────────────────────────────────────────────────────────────

class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ["name", "order"]
        widgets = {
            "name": _text('e.g. "1st Year"'),
            "order": _number("Sort order (0 = first)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not self.user:
            raise ValidationError("User context required.")
        qs = AcademicYear.objects.filter(owner=self.user, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This academic year already exists.")
        return name


# ──────────────────────────────────────────────────────────────────────────────
# Semester form
# ──────────────────────────────────────────────────────────────────────────────

class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["name", "order"]
        widgets = {
            "name": _text('e.g. "Semester 1"'),
            "order": _number("Sort order (0 = first)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not self.user:
            raise ValidationError("User context required.")
        qs = Semester.objects.filter(owner=self.user, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This semester already exists.")
        return name