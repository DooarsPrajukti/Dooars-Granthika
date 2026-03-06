"""
transactions/forms.py

All forms accept a `library` kwarg (the tenant Library instance).
IssueBookForm uses library.user as the `owner` when looking up books.Book
and members.Member, because those models are scoped by owner=FK(User)
rather than by library directly.
"""

from django import forms
from datetime import date
from decimal import Decimal

from finance.models import Fine
from .models import MissingBook, Transaction


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _active_loans_count(member, library):
    """
    Count active (issued + overdue) loans for a member within a library.

    Member has no active_loans_count property — we compute it from the
    Transaction table which is the single source of truth.
    """
    return Transaction.objects.for_library(library).filter(
        member=member,
        status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE),
    ).count()


# ─────────────────────────────────────────────────────────────────────────────
# Issue Book Form
# ─────────────────────────────────────────────────────────────────────────────

class IssueBookForm(forms.Form):
    """
    Accepts the human-readable library card ID and book accession ID.

    Fields posted by the form:
      member_id    — member.member_id  e.g. "DGDGRST0326001"
      book_copy_id — book.book_id      e.g. "BK-001"

    clean() resolves both to ORM objects and attaches them as
    cleaned_data["member"] and cleaned_data["book"].
    """

    member_id = forms.CharField(
        max_length=50,
        error_messages={"required": "Member ID is required."},
    )
    book_copy_id = forms.CharField(
        max_length=50,
        error_messages={"required": "Book Copy ID is required."},
    )
    issue_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    loan_duration = forms.IntegerField(
        initial=14,
        required=False,
        min_value=1,
        widget=forms.HiddenInput,
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )

    def __init__(self, *args, library=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._library = library
        self._owner   = library.user if library else None

    def _get_borrow_limit(self, member=None):
        """Role-specific borrow limit from LibraryRuleSettings."""
        role = getattr(member, "role", "") if member else ""
        try:
            rules = self._library.rules
            if role in ("teacher", "faculty", "staff"):
                limit = getattr(rules, "teacher_borrow_limit", None)
            else:
                limit = getattr(rules, "student_borrow_limit", None)
            if limit is None:
                limit = getattr(rules, "max_books_per_member", None)
            if limit is not None:
                return int(limit)
        except Exception:
            pass
        try:
            from accounts.models import MemberSettings
            ms = MemberSettings.objects.get(library=self._library)
            if ms.borrow_limit:
                return int(ms.borrow_limit)
        except Exception:
            pass
        return 0

    def clean_member_id(self):
        return self.cleaned_data["member_id"].strip().upper()

    def clean_book_copy_id(self):
        return self.cleaned_data["book_copy_id"].strip()

    def clean(self):
        cleaned = super().clean()

        from members.models import Member
        from books.models import Book

        raw_member_id   = cleaned.get("member_id", "")
        raw_book_copy_id = cleaned.get("book_copy_id", "")

        # ── Member: look up by library card ID (member.member_id) ─────────
        member = None
        if raw_member_id:
            try:
                member = Member.objects.get(
                    member_id=raw_member_id,
                    owner=self._owner,
                )
            except Member.DoesNotExist:
                self.add_error(
                    "member_id",
                    f'Member ID "{raw_member_id}" not found in this library.'
                )
            else:
                if member.status != "active":
                    self.add_error(
                        "member_id",
                        f"{member.first_name} {member.last_name} is not an active "
                        f"member (status: {member.get_status_display()}).",
                    )
                    member = None
                else:
                    active_loans = _active_loans_count(member, self._library)
                    borrow_limit = self._get_borrow_limit(member)

                    if borrow_limit and active_loans >= borrow_limit:
                        self.add_error(
                            "member_id",
                            f"{member.first_name} {member.last_name} has reached "
                            f"their borrowing limit ({borrow_limit} books).",
                        )
                        member = None

        if member:
            cleaned["member"] = member

        # ── Book: look up BookCopy by copy_id, then get parent Book ─────────
        book = None
        book_copy = None
        if raw_book_copy_id:
            from books.models import BookCopy
            try:
                book_copy = (
                    BookCopy.objects
                    .select_related("book")
                    .get(copy_id=raw_book_copy_id, book__owner=self._owner)
                )
            except BookCopy.DoesNotExist:
                self.add_error(
                    "book_copy_id",
                    f'Book copy ID "{raw_book_copy_id}" not found in this library.'
                )
            except Exception as exc:
                self.add_error(
                    "book_copy_id",
                    f'Book copy lookup error: {exc}'
                )
            else:
                book = book_copy.book
                # Check this specific copy is available
                copy_status = getattr(book_copy, "status", "available")
                if copy_status != "available":
                    self.add_error(
                        "book_copy_id",
                        f'Copy "{raw_book_copy_id}" of "{book.title}" is not available '
                        f'(status: {copy_status}).'
                    )
                    book = None
                    book_copy = None

        if book:
            cleaned["book"] = book
        if book_copy:
            cleaned["book_copy"] = book_copy

        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Return Book Form
# ─────────────────────────────────────────────────────────────────────────────

class ReturnBookForm(forms.Form):
    CONDITION_CHOICES = [
        ("good",    "Good"),
        ("fair",    "Fair"),
        ("damaged", "Damaged"),
    ]

    transaction_id = forms.IntegerField(widget=forms.HiddenInput)
    return_date    = forms.DateField(widget=forms.HiddenInput)
    condition      = forms.ChoiceField(choices=CONDITION_CHOICES, initial="good")
    damage_charge  = forms.DecimalField(
        required=False,
        min_value=Decimal("0.00"),
        decimal_places=2,
    )
    return_notes  = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )
    fine_paid_now = forms.BooleanField(required=False)

    def clean_damage_charge(self):
        return self.cleaned_data.get("damage_charge") or Decimal("0.00")

    def clean(self):
        cleaned = super().clean()
        try:
            txn = Transaction.objects.select_related("book", "member").get(
                pk=cleaned.get("transaction_id")
            )
        except Transaction.DoesNotExist:
            raise forms.ValidationError("Transaction not found.")

        if txn.status == Transaction.STATUS_RETURNED:
            raise forms.ValidationError("This book has already been returned.")

        cleaned["transaction"] = txn
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Mark Fine Paid Form
# ─────────────────────────────────────────────────────────────────────────────

class MarkFinePaidForm(forms.Form):
    fine_id        = forms.IntegerField()
    payment_method = forms.ChoiceField(
        choices=Fine.PAYMENT_METHOD_CHOICES,
        initial="cash",
    )
    payment_ref = forms.CharField(required=False, max_length=100)


# ─────────────────────────────────────────────────────────────────────────────
# Mark Lost Form
# ─────────────────────────────────────────────────────────────────────────────

class MarkLostForm(forms.Form):
    transaction_id = forms.IntegerField()
    notes          = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Add / Update Penalty Form
# ─────────────────────────────────────────────────────────────────────────────

class AddPenaltyForm(forms.Form):
    missing_id     = forms.IntegerField()
    penalty_amount = forms.DecimalField(
        min_value=Decimal("0.00"),
        decimal_places=2,
    )
    penalty_reason = forms.ChoiceField(choices=MissingBook.REASON_CHOICES)
    notes          = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )