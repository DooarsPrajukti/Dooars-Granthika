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

from .models import Fine, MissingBook, Transaction


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
    member_id     = forms.IntegerField(widget=forms.HiddenInput)
    book_id       = forms.IntegerField(widget=forms.HiddenInput)
    issue_date    = forms.DateField(
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

        # loan_duration is a plain IntegerField — no choice rebuilding needed.
        # Any positive integer supplied by the view is valid.

    def clean(self):
        cleaned = super().clean()

        from members.models import Member
        from books.models import Book

        member_id = cleaned.get("member_id")
        book_id   = cleaned.get("book_id")

        # ── Member: scoped by owner (User), confirmed active ──────────────
        try:
            member = Member.objects.get(pk=member_id, owner=self._owner)
        except Member.DoesNotExist:
            raise forms.ValidationError(
                "Selected member not found in this library."
            )

        if member.status != "active":
            raise forms.ValidationError(
                f"{member.first_name} {member.last_name} is not an active member."
            )

        # Borrow limit comes from accounts.MemberSettings.borrow_limit.
        active_loans = _active_loans_count(member, self._library)
        try:
            from accounts.models import MemberSettings
            member_settings = MemberSettings.objects.get(library=self._library)
            borrow_limit    = int(member_settings.borrow_limit or 0)
        except Exception:
            borrow_limit = 0

        if borrow_limit and active_loans >= borrow_limit:
            raise forms.ValidationError(
                f"{member.first_name} {member.last_name} has reached their "
                f"borrowing limit ({borrow_limit} books)."
            )

        # ── Book: scoped by owner, must have copies available ─────────────
        try:
            book = Book.objects.get(pk=book_id, owner=self._owner)
        except Book.DoesNotExist:
            raise forms.ValidationError(
                "Selected book not found in this library."
            )

        if book.available_copies < 1:
            raise forms.ValidationError(
                f'"{book.title}" has no available copies right now.'
            )

        cleaned["member"] = member
        cleaned["book"]   = book
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