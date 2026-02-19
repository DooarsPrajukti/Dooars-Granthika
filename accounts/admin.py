from django.contrib import admin
from .models import Library


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("library_name", "institute_email", "district", "state", "created_at")
    search_fields = ("library_name", "institute_email")
