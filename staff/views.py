from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from .models import Staff, StaffStatus
from .forms import StaffForm
from accounts.utils import generate_random_password, generate_username
from core.email_service import send_account_credentials


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _save_photo(staff, request):
    """Read uploaded photo file and store binary + mime in the Staff instance."""
    photo_file = request.FILES.get('photo_upload')
    if photo_file:
        staff.photo      = photo_file.read()
        staff.photo_mime = photo_file.content_type  # e.g. 'image/jpeg'
        staff.save(update_fields=['photo', 'photo_mime'])


def _create_user_for_staff(staff):
    """
    Create a Django User for the given Staff instance.
    Returns (user, raw_password) so the password can be emailed.
    """
    raw_password = generate_random_password(length=10)

    username = generate_username(prefix='DG')
    while User.objects.filter(username=username).exists():
        username = generate_username(prefix='DG')

    user = User.objects.create_user(
        username=username,
        email=staff.email,
        password=raw_password,
        first_name=staff.first_name,
        last_name=staff.last_name,
    )
    staff.user = user
    staff.save(update_fields=['user'])
    return user, raw_password


# ──────────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────────

@login_required
def staff_list(request):
    qs = Staff.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(email__icontains=q)      |
            Q(role__icontains=q)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    role_filter = request.GET.get('role', '')
    if role_filter:
        qs = qs.filter(role=role_filter)

    context = {
        'staff_list':     qs,
        'total':          Staff.objects.count(),
        'active_count':   Staff.objects.filter(status=StaffStatus.ACTIVE).count(),
        'on_leave_count': Staff.objects.filter(status=StaffStatus.ON_LEAVE).count(),
        'inactive_count': Staff.objects.filter(status=StaffStatus.INACTIVE).count(),
        'search_query':   q,
        'status_filter':  status_filter,
        'role_filter':    role_filter,
        'status_choices': StaffStatus.choices,
        'role_choices':   Staff._meta.get_field('role').choices,
    }
    return render(request, 'staff/staff_list.html', context)


# ──────────────────────────────────────────────────────────────
# ADD
# ──────────────────────────────────────────────────────────────

@login_required
def staff_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            staff = form.save()

            # Save photo as BLOB
            _save_photo(staff, request)

            # Create Django user and email credentials
            try:
                user, raw_password = _create_user_for_staff(staff)
                email_sent = send_account_credentials(
                    email=staff.email,
                    password=raw_password,
                    Username=user.username,
                )
                if email_sent:
                    messages.success(
                        request,
                        f'{staff.full_name} added. Login credentials sent to {staff.email}.'
                    )
                else:
                    messages.warning(
                        request,
                        f'{staff.full_name} added but email failed. Username: {user.username}'
                    )
            except Exception as e:
                messages.warning(request, f'{staff.full_name} added but user creation failed: {e}')

            return redirect('staff:staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm()

    return render(request, 'staff/staff_form.html', {'form': form, 'action': 'Add'})


# ──────────────────────────────────────────────────────────────
# EDIT
# ──────────────────────────────────────────────────────────────

@login_required
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            staff = form.save()

            # Save new photo only if a new file was uploaded
            _save_photo(staff, request)

            # Sync changes to linked Django user
            if staff.user:
                staff.user.first_name = staff.first_name
                staff.user.last_name  = staff.last_name
                staff.user.email      = staff.email
                staff.user.save(update_fields=['first_name', 'last_name', 'email'])

            messages.success(request, f'{staff.full_name} updated successfully.')
            return redirect('staff:staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm(instance=staff)

    return render(request, 'staff/staff_form.html', {
        'form':   form,
        'action': 'Edit',
        'staff':  staff,
    })


# ──────────────────────────────────────────────────────────────
# DETAIL
# ──────────────────────────────────────────────────────────────

@login_required
def staff_detail(request, pk):
    staff = get_object_or_404(Staff.objects.select_related('user'), pk=pk)
    return render(request, 'staff/staff_detail.html', {'staff': staff})


# ──────────────────────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────────────────────

@login_required
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        name = staff.full_name
        linked_user = staff.user
        staff.delete()
        if linked_user:
            linked_user.delete()
        messages.success(request, f'{name} has been removed.')
    return redirect('staff:staff_list')


