"""
transactions/urls.py
"""

from django.urls import path
from . import views

app_name = "transactions"

urlpatterns = [
    # ── Transaction list & detail ──────────────────────────────────────
    path("",                        views.transaction_list,   name="transaction_list"),
    path("<int:pk>/",               views.transaction_detail, name="transaction_detail"),

    # ── Issue / Return / Renew ─────────────────────────────────────────
    path("issue/",                  views.issue_book,         name="issue_book"),
    path("<int:pk>/return/",        views.return_book,        name="return_book"),
    path("<int:pk>/renew/",         views.renew_book,         name="renew_book"),

    # ── Overdue ────────────────────────────────────────────────────────
    path("overdue/",                views.overdue_list,       name="overdue_list"),

    # ── Fines ──────────────────────────────────────────────────────────
    path("fines/",                  views.fine_list,          name="fine_list"),
    path("fines/pay/",              views.mark_fine_paid,     name="mark_fine_paid"),
    path("fines/<int:pk>/waive/",   views.waive_fine,         name="waive_fine"),

    # ── Missing / Lost books ───────────────────────────────────────────
    path("missing/",                views.missing_books,      name="missing_books"),
    path("missing/mark-lost/",      views.mark_lost,          name="mark_lost"),
    path("missing/<int:pk>/recover/", views.mark_recovered,   name="mark_recovered"),
    path("missing/penalty/",        views.add_penalty,        name="add_penalty"),

    # ── AJAX search APIs (used by issue-book autocomplete) ─────────────
    path("api/members/",            views.member_search_api,  name="member_search_api"),
    path("api/books/",              views.book_search_api,    name="book_search_api"),
]