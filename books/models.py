from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name        = "Category"
        verbose_name_plural = "Categories"
        ordering            = ["name"]

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

    title            = models.CharField(max_length=255)
    author           = models.CharField(max_length=255)
    isbn             = models.CharField(max_length=20, unique=True, verbose_name="ISBN")
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
    cover_image      = models.ImageField(upload_to="book_covers/", null=True, blank=True)
    description      = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Book"
        verbose_name_plural = "Books"

    def __str__(self):
        return f"{self.title} — {self.author}"

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