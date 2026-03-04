from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify
import uuid

from core.id_generator import generate_compact_id


class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)

    class Meta:
        verbose_name        = "Category"
        verbose_name_plural = "Categories"
        ordering            = ["name"]
        unique_together     = [("owner", "name")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Book(models.Model):
    LANGUAGE_CHOICES = [
        ("English",  "English"),
        ("Bengali",  "Bengali"),
        ("Hindi",    "Hindi"),
        ("Sanskrit", "Sanskrit"),
        ("Nepali",   "Nepali"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="books",
    )

    # ── Compact Random Book ID ─────────────────────────────────────────────
    book_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        blank=True,
        db_index=True,
        verbose_name="Book ID",
        help_text=(
            "Auto-generated compact random ID. "
            "Format: DG<LIB>BK<YY><8-digit-random>  e.g. DGDOOBK2648392071"
        ),
    )
    # Full year the book was catalogued (last 2 digits embedded in book_id;
    # full year stored here for filtering / reporting without string parsing).
    entry_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        editable=False,
        help_text="Full year the book was added (auto-set, do not override).",
    )
    # ── Internal UUID (two-step migration) ───────────────────────────────────
    # Step 1 migration: null=True, no default → Django adds column safely.
    # Step 2 migration (data migration): populate NULL rows with uuid.uuid4().
    # Step 3 migration: set null=False once all rows have a value.
    internal_uuid = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
        help_text="Internal immutable UUID — do not expose in public-facing UI.",
    )

    title            = models.CharField(max_length=255)
    author           = models.CharField(max_length=255)
    isbn             = models.CharField(max_length=20, verbose_name="ISBN")
    category         = models.ForeignKey(
                           Category,
                           on_delete=models.SET_NULL,
                           null=True, blank=True,
                           related_name="books",
                       )
    publisher        = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    language         = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, blank=True)
    edition          = models.CharField(max_length=50, blank=True)
    shelf_location   = models.CharField(max_length=50, blank=True)
    total_copies     = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    # ── Cover image stored as binary blob ─────────────────────────────
    cover_image      = models.BinaryField(null=True, blank=True)
    cover_mime_type  = models.CharField(max_length=50, blank=True,
                           default="image/jpeg",
                           help_text="MIME type of the stored cover image.")

    description      = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Book"
        verbose_name_plural = "Books"
        unique_together     = [("owner", "isbn")]

    def __str__(self):
        return f"{self.title} — {self.author}"

    def save(self, *args, **kwargs):
        # ── Auto-generate compact book_id on first save ────────────────────
        if not self.book_id:
            self.book_id = generate_compact_id(
                owner       = self.owner,
                module_code = "BK",
                model_class = Book,
                field_name  = "book_id",
            )
            from datetime import datetime
            self.entry_year = datetime.now().year
        super().save(*args, **kwargs)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def cover_image_b64(self):
        """
        Returns a data-URI string ready to drop into an <img src="…"> tag.
        Returns empty string if no cover is stored.
        """
        if self.cover_image:
            import base64
            data = base64.b64encode(bytes(self.cover_image)).decode("ascii")
            mime = self.cover_mime_type or "image/jpeg"
            return f"data:{mime};base64,{data}"
        return ""

    @property
    def issued_copies(self):
        """Copies currently out on loan (never negative)."""
        return max(0, self.total_copies - self.available_copies)

    @property
    def stock_status(self):
        """String tag matching the template badge logic."""
        if self.available_copies == 0:
            return "out-stock"
        if self.available_copies <= 3:
            return "low-stock"
        return "available"