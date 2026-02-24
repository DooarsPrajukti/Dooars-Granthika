from django.contrib import admin
from django.utils.html import format_html

from .models import Book, Category


# ─────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ("name", "slug", "book_count")
    search_fields       = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Books")
    def book_count(self, obj):
        return obj.books.count()


# ─────────────────────────────────────────────────────────────
# Book
# ─────────────────────────────────────────────────────────────

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "book_id",                                          # ← new
        "title", "author", "isbn", "category",
        "total_copies", "available_copies", "stock_badge",
        "shelf_location", "created_at",
    )
    list_filter         = ("category", "language")
    search_fields       = ("book_id", "title", "author", "isbn", "publisher")  # ← book_id searchable
    readonly_fields     = ("book_id", "created_at", "updated_at",              # ← book_id read-only
                           "issued_copies_display", "cover_preview")
    list_per_page       = 25
    date_hierarchy      = "created_at"
    ordering            = ("-created_at",)
    list_select_related = ("category",)

    fieldsets = (
        ("Identification", {
            "fields": ("book_id",),                         # ← shown at the top, read-only
        }),
        ("Basic Information", {
            "fields": (
                "title", "author", "isbn", "category",
                "publisher", "publication_year", "language", "edition",
            ),
        }),
        ("Stock & Location", {
            "fields": (
                "total_copies", "available_copies", "issued_copies_display",
                "shelf_location",
            ),
        }),
        ("Media & Description", {
            "fields": ("cover_image", "cover_preview", "description"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields":  ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Stock Status")
    def stock_badge(self, obj):
        colours = {
            "out-stock": ("#ef4444", "Out of Stock"),
            "low-stock": ("#f97316", "Low Stock"),
            "available": ("#22c55e", "Available"),
        }
        colour, label = colours.get(obj.stock_status, ("#6b7280", "Unknown"))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:99px;font-size:.75rem;font-weight:700;">{}</span>',
            colour, label,
        )

    @admin.display(description="Cover")
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:6px;" />',
                obj.cover_image_b64,
            )
        return "—"

    @admin.display(description="Issued Copies")
    def issued_copies_display(self, obj):
        return obj.issued_copies