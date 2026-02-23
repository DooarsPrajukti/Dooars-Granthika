from django import forms
from .models import Book, Category


class BookForm(forms.ModelForm):
    class Meta:
        model  = Book
        fields = [
            "title", "author", "isbn", "category",
            "publisher", "publication_year", "language", "edition",
            "total_copies", "available_copies", "shelf_location",
            "cover_image", "description",
        ]
        widgets = {
            "title":            forms.TextInput(attrs={"placeholder": "e.g. The Great Gatsby"}),
            "author":           forms.TextInput(attrs={"placeholder": "e.g. F. Scott Fitzgerald"}),
            "isbn":             forms.TextInput(attrs={"placeholder": "e.g. 978-0-7432-7356-5"}),
            "publisher":        forms.TextInput(attrs={"placeholder": "e.g. Penguin Books"}),
            "publication_year": forms.NumberInput(attrs={"placeholder": "e.g. 2020", "min": 1000, "max": 2099}),
            "edition":          forms.TextInput(attrs={"placeholder": "e.g. 3rd Edition"}),
            "shelf_location":   forms.TextInput(attrs={"placeholder": "e.g. A-12-F"}),
            "total_copies":     forms.NumberInput(attrs={"placeholder": "e.g. 10", "min": 0}),
            "available_copies": forms.NumberInput(attrs={"placeholder": "e.g. 7",  "min": 0}),
            "description":      forms.Textarea(attrs={
                                    "rows": 4,
                                    "placeholder": "A brief description of the book…",
                                }),
        }

    def clean(self):
        cleaned   = super().clean()
        total     = cleaned.get("total_copies")
        available = cleaned.get("available_copies")
        if total is not None and available is not None and available > total:
            self.add_error(
                "available_copies",
                "Available copies cannot exceed total copies.",
            )
        return cleaned