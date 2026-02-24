from django.contrib import admin
from django.utils.html import format_html
from .models import Staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display  = ('photo_thumb', 'full_name', 'role', 'status', 'email', 'phone_number', 'date_joined', 'has_account')
    list_filter   = ('role', 'status')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    ordering      = ('first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at', 'photo_thumb')

    fieldsets = (
        ('Personal', {
            'fields': ('photo', 'photo_thumb', 'first_name', 'last_name', 'email', 'phone_number', 'address')
        }),
        ('Employment', {
            'fields': ('role', 'status', 'date_joined', 'date_left', 'notes')
        }),
        ('Account', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def photo_thumb(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;" />', obj.photo.url)
        return format_html(
            '<div style="width:36px;height:36px;border-radius:50%;background:#2563eb;color:#fff;'
            'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">{}</div>',
            obj.initials
        )
    photo_thumb.short_description = ''

    def has_account(self, obj):
        if obj.user:
            return format_html('<span style="color:#16a34a;">✔ {}</span>', obj.user.username)
        return format_html('<span style="color:#9ca3af;">—</span>')
    has_account.short_description = 'Login Account'