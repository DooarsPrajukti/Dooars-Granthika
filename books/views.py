"""
books/views.py
Dooars Granthika — Books module views.

URL names used in templates (must match urls.py exactly):
  books:book_list        books:book_detail     books:book_create
  books:book_update      books:book_delete     books:stock_dashboard
  books:export_books     books:export_books_excel  books:update_stock
  books:import_books_excel  books:download_import_template  books:book_cover

Context variables consumed by each template are noted above each view.
"""

import io
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BookForm
from .models import Book, Category

# ── How many available copies counts as "low stock"
LOW_STOCK_THRESHOLD = 3


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _user_books(user):
    """Base queryset scoped to the logged-in user."""
    return Book.objects.select_related("category").filter(owner=user)


def _user_categories(user):
    """Categories scoped to the logged-in user."""
    return Category.objects.filter(owner=user)


def _filter_books(qs, request):
    """
    Apply q / category / stock GET params to a Book queryset.
    Used identically by the list view and both export views so
    the exported data always matches what the user sees on screen.
    """
    q        = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    stock    = request.GET.get("stock", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q)    |
            Q(author__icontains=q)   |
            Q(isbn__icontains=q)     |
            Q(publisher__icontains=q)
        )
    if category:
        qs = qs.filter(category__slug=category)

    if stock == "available":
        qs = qs.filter(available_copies__gt=LOW_STOCK_THRESHOLD)
    elif stock == "low-stock":
        qs = qs.filter(
            available_copies__gt=0,
            available_copies__lte=LOW_STOCK_THRESHOLD,
        )
    elif stock == "out-stock":
        qs = qs.filter(available_copies=0)

    return qs


# ─────────────────────────────────────────────────────────────
# Book List
# book_list.html needs:
#   books, categories, page_obj, paginator
# ─────────────────────────────────────────────────────────────

@login_required
def book_list(request):
    qs = _user_books(request.user)
    qs = _filter_books(qs, request)

    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get("page"))

    return render(request, "books/book_list.html", {
        "books":      page_obj,
        "page_obj":   page_obj,
        "paginator":  paginator,
        "categories": _user_categories(request.user),
    })


# ─────────────────────────────────────────────────────────────
# Book Detail
# book_detail.html needs:  book
# ─────────────────────────────────────────────────────────────

@login_required
def book_detail(request, pk):
    book = get_object_or_404(_user_books(request.user), pk=pk)
    return render(request, "books/book_detail.html", {"book": book})


# ─────────────────────────────────────────────────────────────
# Book Create
# book_form.html needs:  form, categories, import_form, import_step
# ─────────────────────────────────────────────────────────────

@login_required
def book_create(request):
    from .forms import ExcelImportForm, parse_excel_rows

    form_type = request.POST.get("form_type", "manual") if request.method == "POST" else "manual"

    # ── Excel upload: parse & store preview in session ────────
    if request.method == "POST" and form_type == "import_upload":
        import_form = ExcelImportForm(request.POST, request.FILES)
        if import_form.is_valid():
            results = parse_excel_rows(import_form.cleaned_data["excel_file"], request.user)
            if not results:
                messages.error(request, "The file appears to be empty.")
            else:
                session_rows = []
                for r in results:
                    d = dict(r["data"])
                    cat = d.get("category")
                    d["category_pk"]       = cat.pk   if cat else None
                    d["category_name"]     = cat.name if cat else ""
                    d["_category_created"] = d.get("_category_created", False)
                    d.pop("category", None)
                    session_rows.append({
                        "row":    r["row"],
                        "data":   d,
                        "status": r["status"],
                        "errors": r["errors"],
                        "book_pk": r["book"].pk if r["book"] else None,
                    })
                request.session["import_preview"] = session_rows
                new_c = sum(1 for r in results if r["status"] == "new")
                dup_c = sum(1 for r in results if r["status"] == "duplicate")
                err_c = sum(1 for r in results if r["status"] == "error")
                return render(request, "books/book_form.html", {
                    "form":             BookForm(user=request.user),
                    "categories":       _user_categories(request.user),
                    "import_form":      import_form,
                    "import_step":      "preview",
                    "import_rows":      session_rows,
                    "import_new_count": new_c,
                    "import_dup_count": dup_c,
                    "import_err_count": err_c,
                })
        # Form invalid — re-render upload tab with errors
        return render(request, "books/book_form.html", {
            "form":        BookForm(user=request.user),
            "categories":  _user_categories(request.user),
            "import_form": import_form,
            "import_step": None,
        })

    # ── Excel confirm: bulk create / update ──────────────────
    if request.method == "POST" and form_type == "import_confirm":
        session_rows  = request.session.pop("import_preview", [])
        selected_rows = set(request.POST.getlist("selected_rows"))
        created = updated = skipped = 0

        for r in session_rows:
            if str(r["row"]) not in selected_rows or r["status"] == "error":
                skipped += 1
                continue
            d   = r["data"]
            cat = Category.objects.filter(pk=d.get("category_pk")).first() if d.get("category_pk") else None
            total = int(d.get("total_copies") or 1)
            defaults = {
                "title":            d.get("title", ""),
                "author":           d.get("author", ""),
                "category":         cat,
                "publisher":        d.get("publisher", ""),
                "publication_year": d.get("publication_year") or None,
                "language":         d.get("language", ""),
                "edition":          d.get("edition", ""),
                "shelf_location":   d.get("shelf_location", ""),
                "total_copies":     total,
                "available_copies": total,
                "description":      d.get("description", ""),
            }
            if r["status"] == "duplicate":
                Book.objects.filter(owner=request.user, isbn=d["isbn"]).update(**defaults)
                updated += 1
            else:
                Book.objects.create(owner=request.user, isbn=d["isbn"], **defaults)
                created += 1

        parts = []
        if created: parts.append(f"{created} book{'s' if created != 1 else ''} imported")
        if updated: parts.append(f"{updated} updated")
        if skipped: parts.append(f"{skipped} skipped")
        messages.success(request, " · ".join(parts) + ".")
        return redirect("books:book_list")

    # ── Manual entry POST ─────────────────────────────────────
    if request.method == "POST" and form_type == "manual":
        form = BookForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            book          = form.save(commit=False)
            book.owner    = request.user
            book.category = form.cleaned_data["category"]
            img = form.cleaned_data.get("cover_image")
            if img:
                book.cover_image     = img["data"]
                book.cover_mime_type = img["mime"]
            book.save()
            if hasattr(form, "_created_category"):
                messages.info(request, f'New category "{form._created_category}" was created.')
            elif hasattr(form, "_reused_category"):
                messages.info(request, f'Existing category "{form._reused_category}" was reused.')
            messages.success(request, f'"{book.title}" was added successfully.')
            return redirect("books:book_detail", pk=book.pk)
    else:
        form = BookForm(user=request.user)

    return render(request, "books/book_form.html", {
        "form":        form,
        "categories":  _user_categories(request.user),
        "import_form": ExcelImportForm(),
        "import_step": None,
    })


# ─────────────────────────────────────────────────────────────
# Book Update
# book_form.html needs:  form, categories
# ─────────────────────────────────────────────────────────────

@login_required
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk, owner=request.user)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book, user=request.user)
        if form.is_valid():
            updated          = form.save(commit=False)
            updated.category = form.cleaned_data["category"]
            img = form.cleaned_data.get("cover_image")
            if img:
                updated.cover_image     = img["data"]
                updated.cover_mime_type = img["mime"]
            else:
                updated.cover_image     = book.cover_image
                updated.cover_mime_type = book.cover_mime_type
            updated.save()
            if hasattr(form, "_created_category"):
                messages.info(request, f'New category "{form._created_category}" was created.')
            elif hasattr(form, "_reused_category"):
                messages.info(request, f'Existing category "{form._reused_category}" was reused.')
            messages.success(request, f'"{book.title}" was updated successfully.')
            return redirect("books:book_detail", pk=book.pk)
    else:
        form = BookForm(instance=book, user=request.user)

    return render(request, "books/book_form.html", {
        "form":       form,
        "categories": _user_categories(request.user),
    })


# ─────────────────────────────────────────────────────────────
# Book Delete
# book_delete.html needs:  book
# ─────────────────────────────────────────────────────────────

@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, owner=request.user)
    if request.method == "POST":
        title = book.title
        book.delete()
        messages.success(request, f"{title} was deleted.")
        return redirect("books:book_list")

    return render(request, "books/book_delete.html", {"book": book})


# ─────────────────────────────────────────────────────────────
# Stock Dashboard
# book_stock_dashboard.html needs:
#   total_books, available_books, low_stock_count, out_of_stock_count
#   available_pct, low_pct, out_pct
#   category_stats  (list of dicts: name, total, available, pct)
#   most_issued     (books with .issue_count attribute)
#   recent_books
#   low_stock_list, low_threshold
# ─────────────────────────────────────────────────────────────

@login_required
def stock_dashboard(request):
    all_books = _user_books(request.user)

    total_books        = all_books.count()
    low_stock_count    = all_books.filter(
                             available_copies__gt=0,
                             available_copies__lte=LOW_STOCK_THRESHOLD,
                         ).count()
    out_of_stock_count = all_books.filter(available_copies=0).count()
    available_books    = total_books - low_stock_count - out_of_stock_count

    def pct(n):
        return round(n / total_books * 100) if total_books else 0

    category_stats = []
    for cat in _user_categories(request.user):
        cat_qs    = all_books.filter(category=cat)
        total     = cat_qs.count()
        available = cat_qs.filter(available_copies__gt=0).count()
        category_stats.append({
            "name":      cat.name,
            "total":     total,
            "available": available,
            "pct":       round(available / total * 100) if total else 0,
        })

    most_issued_qs = all_books.order_by("available_copies")[:5]
    most_issued = []
    for b in most_issued_qs:
        b.issue_count = b.issued_copies
        most_issued.append(b)

    recent_books   = all_books.order_by("-created_at")[:5]
    low_stock_list = all_books.filter(
                         available_copies__gt=0,
                         available_copies__lte=LOW_STOCK_THRESHOLD,
                     ).order_by("available_copies")

    return render(request, "books/book_stock_dashboard.html", {
        "total_books":        total_books,
        "available_books":    available_books,
        "low_stock_count":    low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "available_pct":      pct(available_books),
        "low_pct":            pct(low_stock_count),
        "out_pct":            pct(out_of_stock_count),
        "category_stats":     category_stats,
        "most_issued":        most_issued,
        "recent_books":       recent_books,
        "low_stock_list":     low_stock_list,
        "low_threshold":      LOW_STOCK_THRESHOLD,
    })


# ─────────────────────────────────────────────────────────────
# Export preview page
# book_export.html needs:
#   preview_books, preview_more, total_count
#   total_copies_sum, available_copies_sum, issued_copies_sum
#   categories  (for filter strip)
# ─────────────────────────────────────────────────────────────

@login_required
def export_books(request):
    qs = _user_books(request.user)
    qs = _filter_books(qs, request)

    total_count   = qs.count()
    preview_limit = 8
    preview_books = list(qs[:preview_limit])
    preview_more  = max(0, total_count - preview_limit)

    agg = qs.aggregate(
        total_sum     = Sum("total_copies"),
        available_sum = Sum("available_copies"),
    )
    total_sum     = agg["total_sum"]     or 0
    available_sum = agg["available_sum"] or 0
    issued_sum    = total_sum - available_sum

    return render(request, "books/book_export.html", {
        "preview_books":        preview_books,
        "preview_more":         preview_more,
        "total_count":          total_count,
        "total_copies_sum":     total_sum,
        "available_copies_sum": available_sum,
        "issued_copies_sum":    issued_sum,
        "categories":           _user_categories(request.user),
    })


# ─────────────────────────────────────────────────────────────
# Excel download
# ─────────────────────────────────────────────────────────────

@login_required
def export_books_excel(request):
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        messages.error(request, "openpyxl is not installed. Run: pip install openpyxl")
        return redirect("books:export_books")

    qs = _user_books(request.user)
    qs = _filter_books(qs, request)

    HEADER_FILL  = PatternFill("solid", fgColor="0A1628")
    HEADER_FONT  = Font(color="FFFFFF", bold=True, size=9)
    TOTALS_FILL  = PatternFill("solid", fgColor="1E3A5F")
    TOTALS_FONT  = Font(color="FFFFFF", bold=True, size=9)
    GREEN_FILL   = PatternFill("solid", fgColor="DCFCE7")
    ORANGE_FILL  = PatternFill("solid", fgColor="FFF7ED")
    RED_FILL     = PatternFill("solid", fgColor="FEE2E2")
    CENTER       = Alignment(horizontal="center", vertical="center")
    THIN         = Side(style="thin", color="D1D5DB")
    BORDER       = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    wb = openpyxl.Workbook()

    # ── Sheet 1 : Book Catalogue ──────────────────────────────
    ws = wb.active
    ws.title = "Book Catalogue"

    headers    = [
        "#", "Title", "Author", "ISBN", "Category", "Publisher",
        "Language", "Edition", "Total Copies", "Available", "Issued",
        "Shelf Location", "Added On",
    ]
    col_widths = [4, 32, 22, 18, 16, 20, 11, 12, 12, 10, 8, 14, 12]

    ws.append(headers)
    ws.row_dimensions[1].height = 22
    for ci, (_, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=ci)
        cell.fill      = HEADER_FILL
        cell.font      = HEADER_FONT
        cell.alignment = CENTER
        cell.border    = BORDER
        ws.column_dimensions[get_column_letter(ci)].width = w

    ws.freeze_panes = "A2"

    for idx, book in enumerate(qs, 1):
        row_data = [
            idx,
            book.title,
            book.author,
            book.isbn,
            book.category.name if book.category else "",
            book.publisher,
            book.language,
            book.edition,
            book.total_copies,
            book.available_copies,
            book.issued_copies,
            book.shelf_location,
            book.created_at.strftime("%d/%m/%Y"),
        ]
        ws.append(row_data)
        r = ws.max_row

        avail_cell = ws.cell(row=r, column=10)
        if book.available_copies == 0:
            avail_cell.fill = RED_FILL
        elif book.available_copies <= LOW_STOCK_THRESHOLD:
            avail_cell.fill = ORANGE_FILL
        else:
            avail_cell.fill = GREEN_FILL

        for ci in range(1, len(headers) + 1):
            ws.cell(row=r, column=ci).border = BORDER

    last_data = ws.max_row

    ws.append(
        ["", "TOTALS", "", "", "", "", "", "",
         f"=SUM(I2:I{last_data})",
         f"=SUM(J2:J{last_data})",
         f"=SUM(K2:K{last_data})",
         "", ""]
    )
    for ci in range(1, len(headers) + 1):
        cell           = ws.cell(row=ws.max_row, column=ci)
        cell.fill      = TOTALS_FILL
        cell.font      = TOTALS_FONT
        cell.alignment = CENTER
        cell.border    = BORDER

    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last_data}"

    # ── Sheet 2 : Stock Summary ───────────────────────────────
    ws2 = wb.create_sheet("Stock Summary")
    s2_headers = ["Category", "Total Books", "Available", "Issued", "Out of Stock"]
    ws2.append(s2_headers)
    ws2.row_dimensions[1].height = 22
    for ci, w in enumerate([22, 14, 14, 14, 14], 1):
        cell = ws2.cell(row=1, column=ci)
        cell.fill      = HEADER_FILL
        cell.font      = HEADER_FONT
        cell.alignment = CENTER
        cell.border    = BORDER
        ws2.column_dimensions[get_column_letter(ci)].width = w
    ws2.freeze_panes = "A2"

    for cat in _user_categories(request.user):
        cat_qs    = qs.filter(category=cat)
        total     = cat_qs.count()
        agg       = cat_qs.aggregate(tc=Sum("total_copies"), ac=Sum("available_copies"))
        tc        = agg["tc"] or 0
        ac        = agg["ac"] or 0
        available = cat_qs.filter(available_copies__gt=0).count()
        out       = cat_qs.filter(available_copies=0).count()
        ws2.append([cat.name, total, available, tc - ac, out])
        r = ws2.max_row
        for ci in range(1, 6):
            ws2.cell(row=r, column=ci).border = BORDER

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"dooars_granthika_books_{date.today():%Y%m%d}.xlsx"
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ─────────────────────────────────────────────────────────────
# Stock bulk-upload
# ─────────────────────────────────────────────────────────────

@login_required
def update_stock(request):
    return render(request, "books/book_stock_update.html", {
        "categories": _user_categories(request.user),
    })


# ─────────────────────────────────────────────────────────────
# Cover image — serve blob stored in the DB
# ─────────────────────────────────────────────────────────────

@login_required
def book_cover(request, pk):
    """
    Serve the binary cover image stored as a BinaryField (BLOB) in the DB.
    Scoped to the current user's books. Returns 404 if no image is stored.

    Django's BinaryField returns a memoryview on MySQL/PostgreSQL.
    We must convert to bytes and check length — not truthiness — because
    a memoryview object is always truthy even when it wraps zero bytes.
    """
    from django.http import Http404, HttpResponse
    book = get_object_or_404(Book, pk=pk, owner=request.user)

    raw = book.cover_image
    if raw is None:
        raise Http404("No cover image.")

    image_bytes = bytes(raw)
    if not image_bytes:
        raise Http404("Cover image is empty.")

    mime = (book.cover_mime_type or "image/jpeg").strip() or "image/jpeg"
    response = HttpResponse(image_bytes, content_type=mime)
    # Allow browsers to cache the cover for 1 hour
    response["Cache-Control"] = "private, max-age=3600"
    return response


# ─────────────────────────────────────────────────────────────
# Excel Import — two-step: preview then confirm
# ─────────────────────────────────────────────────────────────
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Book, Category


@login_required
def import_books_excel(request):
    """
    GET  → show upload form
    POST (step=upload)   → parse file, store preview in session, show preview
    POST (step=confirm)  → read session data, bulk-create/update, redirect to list
    """
    from .forms import ExcelImportForm, parse_excel_rows

    step = request.POST.get("step", "upload")

    # ─────────────────────────────────────────────
    # STEP 1 → Upload & Preview
    # ─────────────────────────────────────────────
    if request.method == "POST" and step == "upload":
        form = ExcelImportForm(request.POST, request.FILES)

        if form.is_valid():
            results = parse_excel_rows(
                form.cleaned_data["excel_file"],
                request.user
            )

            if not results:
                messages.error(request, "The file appears to be empty.")
                return render(request, "books/book_import.html", {
                    "form": form,
                    "step": "upload"
                })

            session_rows = []

            for r in results:
                d = dict(r["data"])

                cat = d.get("category")
                d["category_pk"] = cat.pk if cat else None
                d["category_name"] = cat.name if cat else ""

                d.pop("category", None)
                d.pop("_category_created", None)

                session_rows.append({
                    "row": r["row"],
                    "data": d,
                    "status": r["status"],
                    "errors": r["errors"],
                    "book_pk": r["book"].pk if r["book"] else None,
                    "book_title": str(r["book"]) if r["book"] else "",
                })

            request.session["import_preview"] = session_rows

            return render(request, "books/book_import.html", {
                "step": "preview",
                "rows": session_rows,
                "new_count": sum(1 for r in results if r["status"] == "new"),
                "dup_count": sum(1 for r in results if r["status"] == "duplicate"),
                "err_count": sum(1 for r in results if r["status"] == "error"),
                "form": ExcelImportForm(),
            })

        return render(request, "books/book_import.html", {
            "form": form,
            "step": "upload"
        })

    # ─────────────────────────────────────────────
    # STEP 2 → Confirm & Save
    # ─────────────────────────────────────────────
    if request.method == "POST" and step == "confirm":

        session_rows = request.session.pop("import_preview", [])

        if not session_rows:
            messages.error(request, "Session expired. Please re-upload the file.")
            return redirect("books:import_books_excel")

        selected_rows = set(request.POST.getlist("selected_rows"))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for r in session_rows:

            if str(r["row"]) not in selected_rows or r["status"] == "error":
                skipped_count += 1
                continue

            d = r["data"]

            # ───────── SAFE TOTAL COPIES CONVERSION ─────────
            raw_total = d.get("total_copies")

            try:
                total = int(raw_total)
                if total < 1:
                    total = 1
            except (TypeError, ValueError):
                total = 1

            # DEBUG PRINT (REMOVE AFTER TESTING)
            print("Excel Total:", raw_total)
            print("Saving Total:", total)

            cat = None
            if d.get("category_pk"):
                cat = Category.objects.filter(pk=d["category_pk"]).first()

            defaults = {
                "title": d.get("title", ""),
                "author": d.get("author", ""),
                "category": cat,
                "publisher": d.get("publisher", ""),
                "publication_year": d.get("publication_year") or None,
                "language": d.get("language", ""),
                "edition": d.get("edition", ""),
                "shelf_location": d.get("shelf_location", ""),
                "total_copies": total,
                "available_copies": total,  # ALWAYS equal on import
                "description": d.get("description", ""),
            }

            if r["status"] == "duplicate":
                Book.objects.filter(
                    owner=request.user,
                    isbn=d["isbn"]
                ).update(**defaults)
                updated_count += 1
            else:
                Book.objects.create(
                    owner=request.user,
                    isbn=d["isbn"],
                    **defaults
                )
                created_count += 1

        parts = []
        if created_count:
            parts.append(f"{created_count} imported")
        if updated_count:
            parts.append(f"{updated_count} updated")
        if skipped_count:
            parts.append(f"{skipped_count} skipped")

        messages.success(request, " · ".join(parts) + ".")
        return redirect("books:book_list")

    # ─────────────────────────────────────────────
    # GET → Upload Page
    # ─────────────────────────────────────────────
    return render(request, "books/book_import.html", {
        "form": ExcelImportForm(),
        "step": "upload",
    })

# ─────────────────────────────────────────────────────────────
# Download blank import template
# ─────────────────────────────────────────────────────────────

@login_required
def download_import_template(request):
    """Serve a blank .xlsx template the user can fill in."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        messages.error(request, "openpyxl is not installed.")
        return redirect("books:import_books_excel")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Books"

    headers = [
        "Title", "Author", "ISBN", "Category", "Publisher",
        "Publication Year", "Language", "Edition",
        "Total Copies", "Available Copies", "Shelf Location", "Description",
    ]
    col_widths = [28, 22, 20, 18, 22, 16, 12, 14, 13, 16, 16, 36]

    HEADER_FILL = PatternFill("solid", fgColor="0A1628")
    HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
    CENTER      = Alignment(horizontal="center", vertical="center")

    ws.append(headers)
    ws.row_dimensions[1].height = 22
    for ci, w in enumerate(col_widths, 1):
        cell           = ws.cell(row=1, column=ci)
        cell.fill      = HEADER_FILL
        cell.font      = HEADER_FONT
        cell.alignment = CENTER
        ws.column_dimensions[get_column_letter(ci)].width = w

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = 'attachment; filename="book_import_template.xlsx"'
    return resp