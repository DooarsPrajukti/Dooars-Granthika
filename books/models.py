from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify


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


def _generate_book_id(owner):
    """
    Generate a unique Book ID for the given owner.

    Format:  <PREFIX><NNN>
      PREFIX  — first 3 chars of the owner's library/username, uppercased.
      NNN     — zero-padded 3-digit serial, scoped per owner.

    The SELECT … FOR UPDATE lock on the last book row prevents duplicate
    serials under concurrent requests.
    """
    # Derive prefix from the owner's display name or username.
    # Prefer `library_name` if your User model exposes it; fall back to username.
    source = (
        getattr(owner, "library_name", None)
        or getattr(owner, "get_full_name", lambda: "")()
        or owner.username
    )
    prefix = source.replace(" ", "")[:3].upper() or "LIB"

    # Lock the most-recently-created book for this owner to get a safe serial.
    with transaction.atomic():
        last = (
            Book.objects.select_for_update()
            .filter(owner=owner, book_id__startswith=prefix)
            .order_by("-book_id")
            .first()
        )
        if last and last.book_id:
            try:
                last_serial = int(last.book_id[len(prefix):])
            except (ValueError, IndexError):
                last_serial = 0
        else:
            last_serial = 0

        new_serial = last_serial + 1
        return f"{prefix}{new_serial:03d}"


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

    # ── Auto-generated unique Book ID ─────────────────────────────────
    book_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        verbose_name="Book ID",
        help_text="Auto-generated. Format: <PREFIX><NNN> e.g. DOO001",
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
        # Generate book_id only once (on first save / creation).
        if not self.book_id:
            self.book_id = _generate_book_id(self.owner)
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