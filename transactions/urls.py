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

    # ── AJAX exact-ID lookup APIs (used by issue-book ID fields) ─────────
    path("api/member-lookup/",      views.member_lookup_api,  name="member_lookup_api"),
    path("api/book-lookup/",        views.book_lookup_api,    name="book_lookup_api"),

    # ── Book cover image (BLOB served as HTTP response) ───────────────
    path("api/book-cover/<int:pk>/", views.book_cover_image,  name="book_cover_image"),

]