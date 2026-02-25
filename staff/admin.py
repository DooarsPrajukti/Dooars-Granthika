from django.contrib import admin
from django.utils.html import format_html
from .models import Staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display  = (
        'photo_thumb', 'full_name', 'owner', 'role', 'status',
        'email', 'phone_number', 'date_joined',
        'portal_access', 'has_account',
    )
    list_filter   = ('role', 'status', 'is_staff_user', 'owner')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number', 'owner__username')
    ordering      = ('owner', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at', 'photo_thumb')

    fieldsets = (
        ('Tenant', {
            'fields': ('owner',),
        }),
        ('Personal', {
            'fields': ('photo', 'photo_thumb', 'first_name', 'last_name', 'email', 'phone_number', 'address'),
        }),
        ('Employment', {
            'fields': ('role', 'status', 'date_joined', 'date_left', 'notes'),
        }),
        ('Account & Access', {
            'fields': ('user', 'is_staff_user'),
            'description': 'is_staff_user = 1 → User.is_staff = True (dashboard access granted). '
                           'is_staff_user = 0 → User.is_staff = False (access revoked).',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def photo_thumb(self, obj):
        if obj.photo:
            import base64
            data = base64.b64encode(bytes(obj.photo)).decode('utf-8')
            mime = obj.photo_mime or 'image/jpeg'
            src  = f"data:{mime};base64,{data}"
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;" />',
                src,
            )
        return format_html(
            '<div style="width:36px;height:36px;border-radius:50%;background:#2563eb;color:#fff;'
            'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">{}</div>',
            obj.initials,
        )
    photo_thumb.short_description = ''

    def has_account(self, obj):
        if obj.user:
            return format_html('<span style="color:#16a34a;">✔ {}</span>', obj.user.username)
        return format_html('<span style="color:#9ca3af;">—</span>')
    has_account.short_description = 'Login Account'

    def portal_access(self, obj):
        if obj.is_staff_user:
            return format_html('<span style="color:#16a34a;font-weight:700;">1 ✔ Enabled</span>')
        return format_html('<span style="color:#ef4444;font-weight:700;">0 ✘ Revoked</span>')
    portal_access.short_description = 'Portal Access'