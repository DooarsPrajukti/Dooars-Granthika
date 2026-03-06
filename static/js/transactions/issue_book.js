/**
 * issue_book_id.js
 * Handles the member-ID and book-copy-ID input fields:
 *   - Debounced AJAX lookup on input (350 ms)
 *   - Inline preview card with name / stats / availability
 *   - Valid/invalid border colour + status icon
 *   - Updates the sidebar cards (reuses existing sidebar DOM)
 *   - Submit guard: disables button on submit
 *
 * Requires the following globals set by the template before this script loads:
 *   window.LIBRARY_RULES      — { defaultLoanDays, fineRatePerDay, maxBorrowLimit, maxRenewalCount }
 *   window.MEMBER_PHOTO_BASE  — base URL for member photos
 *   window.MEMBER_LOOKUP_URL  — URL for member lookup API
 *   window.BOOK_LOOKUP_URL    — URL for book lookup API
 */
(function () {
  'use strict';

  const DEBOUNCE_MS = 350;

  // ── DOM refs ─────────────────────────────────────────────────────
  const memberInput   = document.getElementById('memberIdInput');
  const memberStatus  = document.getElementById('memberIdStatus');
  const memberError   = document.getElementById('memberIdError');
  const memberRow     = memberInput?.closest('.id-field-input-row');
  const memberPreview = document.getElementById('memberPreview');

  const bookInput   = document.getElementById('bookCopyIdInput');
  const bookStatus  = document.getElementById('bookCopyIdStatus');
  const bookError   = document.getElementById('bookCopyIdError');
  const bookRow     = bookInput?.closest('.id-field-input-row');
  const bookPreview = document.getElementById('bookPreview');

  const submitBtn = document.getElementById('submitBtn');
  const form      = document.getElementById('issueBookForm');

  // ── State ────────────────────────────────────────────────────────
  let memberValid = false;
  let bookValid   = false;

  // ── Icons ────────────────────────────────────────────────────────
  const ICON_SPIN  = '<svg viewBox="0 0 20 20" fill="none" style="animation:spin 1s linear infinite"><path d="M10 3a7 7 0 1 1 0 14A7 7 0 0 1 10 3z" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" opacity=".3"/><path d="M10 3a7 7 0 0 1 7 7" stroke="#6366f1" stroke-width="2" stroke-linecap="round"/></svg><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
  const ICON_OK    = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" fill="#10b981"/><path d="M7 10l2 2 4-4" stroke="#fff" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_FAIL  = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" fill="#ef4444"/><path d="M8 8l4 4M12 8l-4 4" stroke="#fff" stroke-width="1.75" stroke-linecap="round"/></svg>';
  const ICON_BLANK = '';

  // ── Debounce helper ──────────────────────────────────────────────
  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  // ── Set field state ──────────────────────────────────────────────
  function setFieldState(row, statusEl, errorEl, state, errorMsg = '') {
    row.classList.toggle('is-valid',   state === 'ok');
    row.classList.toggle('is-invalid', state === 'error');
    statusEl.innerHTML = state === 'loading' ? ICON_SPIN
                       : state === 'ok'      ? ICON_OK
                       : state === 'error'   ? ICON_FAIL
                       : ICON_BLANK;
    if (errorEl) {
      errorEl.textContent = errorMsg;
      errorEl.classList.toggle('is-hidden', !errorMsg);
    }
  }

  // ── Member lookup ────────────────────────────────────────────────
  function lookupMember(rawVal) {
    const val = rawVal.trim().toUpperCase();
    if (!val) {
      memberValid = false;
      setFieldState(memberRow, memberStatus, memberError, 'idle');
      hideMemberPreview();
      syncSidebarMember(null);
      return;
    }

    setFieldState(memberRow, memberStatus, memberError, 'loading');

    fetch(`${window.MEMBER_LOOKUP_URL}?member_id=${encodeURIComponent(val)}`)
      .then(r => {
        if (!r.ok) {
          return r.text().then(t => { throw new Error(`Server ${r.status}: ${t.slice(0, 120)}`); });
        }
        return r.json();
      })
      .then(data => {
        if (data.found) {
          memberValid = true;
          setFieldState(memberRow, memberStatus, memberError, 'ok');
          showMemberPreview(data);
          syncSidebarMember(data);
        } else {
          memberValid = false;
          setFieldState(memberRow, memberStatus, memberError, 'error', data.error || 'Member not found.');
          hideMemberPreview();
          syncSidebarMember(null);
        }
      })
      .catch(err => {
        memberValid = false;
        setFieldState(memberRow, memberStatus, memberError, 'error', err.message || 'Lookup failed — check connection.');
        hideMemberPreview();
      });
  }

  function showMemberPreview(d) {
    if (!memberPreview) return;
    const initial  = (d.name || '?')[0].toUpperCase();
    const photo    = document.getElementById('memberPreviewPhoto');
    const initial_ = document.getElementById('memberPreviewInitial');
    if (photo && initial_) {
      initial_.textContent = initial;
      if (d.photo_url) {
        photo.onerror = () => {
          photo.style.display    = 'none';
          initial_.style.display = 'flex';
        };
        photo.src              = d.photo_url;
        photo.style.display    = 'block';
        initial_.style.display = 'none';
      } else {
        photo.style.display    = 'none';
        initial_.style.display = 'flex';
      }
    }
    document.getElementById('memberPreviewName').textContent  = d.name || '—';
    document.getElementById('memberPreviewMeta').textContent  = [d.role, d.member_id].filter(Boolean).join(' · ');
    document.getElementById('memberPreviewLoans').textContent = d.active_loans ?? '—';
    document.getElementById('memberPreviewSlots').textContent = d.slots === -1 ? '∞' : (d.slots ?? '—');
    const finesEl = document.getElementById('memberPreviewFines');
    const fine    = parseFloat(d.total_due || '0');
    finesEl.textContent = fine > 0 ? '₹' + fine.toFixed(2) : '₹0';
    finesEl.style.color = fine > 0 ? '#ef4444' : 'inherit';
    memberPreview.classList.remove('is-hidden');
  }

  function hideMemberPreview() {
    memberPreview?.classList.add('is-hidden');
  }

  // ── Sync sidebar member card ─────────────────────────────────────
  function syncSidebarMember(d) {
    const empty   = document.getElementById('sidebarMemberEmpty');
    const details = document.getElementById('sidebarMemberDetails');
    if (!empty || !details) return;
    if (!d) {
      empty.style.display = '';
      details.classList.add('is-hidden');
      return;
    }
    empty.style.display = 'none';
    details.classList.remove('is-hidden');

    const nameEl  = document.getElementById('sidebarMemberName');
    const typeEl  = document.getElementById('sidebarMemberType');
    const idEl    = document.getElementById('sidebarMemberId');
    const loansEl = document.getElementById('sidebarActiveLoans');
    const canEl   = document.getElementById('sidebarCanBorrow');
    const dueEl   = document.getElementById('sidebarTotalDue');
    const emailEl = document.getElementById('sidebarMemberEmail');

    if (nameEl)  nameEl.textContent  = d.name || '—';
    if (typeEl)  typeEl.textContent  = d.role || '—';
    if (idEl)    idEl.textContent    = d.member_id || '—';
    if (loansEl) loansEl.textContent = d.active_loans ?? '—';
    if (canEl)   canEl.textContent   = d.slots === -1 ? '∞' : (d.slots ?? '—');
    if (dueEl) {
      const fine = parseFloat(d.total_due || '0');
      dueEl.textContent = fine > 0 ? '₹' + fine.toFixed(2) : '₹0';
      dueEl.style.color = fine > 0 ? '#ef4444' : 'inherit';
    }
    if (emailEl) emailEl.textContent = d.email || '—';

    const photo   = document.getElementById('sidebarMemberPhoto');
    const initial = document.getElementById('sidebarMemberInitial');
    if (photo && initial) {
      initial.textContent = (d.name || '?')[0].toUpperCase();
      if (d.photo_url) {
        photo.onerror = () => {
          photo.style.display   = 'none';
          initial.style.display = 'flex';
        };
        photo.src             = d.photo_url;
        photo.style.display   = 'block';
        initial.style.display = 'none';
      } else {
        photo.style.display   = 'none';
        initial.style.display = 'flex';
      }
    }
  }

  // ── Book lookup ──────────────────────────────────────────────────
  function lookupBook(rawVal) {
    const val = rawVal.trim();
    if (!val) {
      bookValid = false;
      setFieldState(bookRow, bookStatus, bookError, 'idle');
      hideBookPreview();
      syncSidebarBook(null);
      return;
    }

    setFieldState(bookRow, bookStatus, bookError, 'loading');

    fetch(`${window.BOOK_LOOKUP_URL}?book_id=${encodeURIComponent(val)}`)
      .then(r => {
        if (!r.ok) {
          return r.text().then(t => { throw new Error(`Server ${r.status}: ${t.slice(0, 120)}`); });
        }
        return r.json();
      })
      .then(data => {
        if (data.found) {
          bookValid = true;
          setFieldState(bookRow, bookStatus, bookError, 'ok');
          showBookPreview(data);
          syncSidebarBook(data);
        } else {
          bookValid = false;
          setFieldState(bookRow, bookStatus, bookError, 'error', data.error || 'Book not found.');
          hideBookPreview();
          syncSidebarBook(null);
        }
      })
      .catch(err => {
        bookValid = false;
        setFieldState(bookRow, bookStatus, bookError, 'error', err.message || 'Lookup failed — check connection.');
        hideBookPreview();
      });
  }

  function _setBookCover(imgId, fallbackId, coverUrl) {
    const img      = document.getElementById(imgId);
    const fallback = document.getElementById(fallbackId);
    if (!img || !fallback) return;
    if (coverUrl) {
      img.onerror = () => {
        img.style.display      = 'none';
        fallback.style.display = '';
      };
      img.src              = coverUrl;
      img.style.display    = 'block';
      fallback.style.display = 'none';
    } else {
      img.style.display      = 'none';
      fallback.style.display = '';
    }
  }

  function showBookPreview(d) {
    if (!bookPreview) return;
    document.getElementById('bookPreviewTitle').textContent  = d.title  || '—';
    document.getElementById('bookPreviewAuthor').textContent = d.author || '—';
    document.getElementById('bookPreviewIsbn').textContent   = d.isbn   ? 'ISBN: ' + d.isbn : '';
    _setBookCover('bookPreviewCover', 'bookPreviewCoverFallback', d.cover_url);
    const badge = document.getElementById('bookPreviewAvailBadge');
    if (badge) {
      const avail = parseInt(d.available_copies, 10) || 0;
      badge.textContent = avail > 0
        ? avail + ' cop' + (avail === 1 ? 'y' : 'ies') + ' available'
        : 'No copies available';
      badge.className = 'avail-badge ' + (avail > 0 ? 'avail-badge--ok' : 'avail-badge--out');
    }
    bookPreview.classList.remove('is-hidden');
  }

  function hideBookPreview() {
    bookPreview?.classList.add('is-hidden');
  }

  // ── Sync sidebar book card ───────────────────────────────────────
  function syncSidebarBook(d) {
    const empty   = document.getElementById('sidebarBookEmpty');
    const details = document.getElementById('sidebarBookDetails');
    if (!empty || !details) return;
    if (!d) {
      empty.style.display = '';
      details.classList.add('is-hidden');
      return;
    }
    empty.style.display = 'none';
    details.classList.remove('is-hidden');

    const titleEl  = document.getElementById('sidebarBookTitle');
    const authorEl = document.getElementById('sidebarBookAuthor');
    const isbnEl   = document.getElementById('sidebarBookIsbn');
    const countEl  = document.getElementById('sidebarAvailCount');
    const fillEl   = document.getElementById('sidebarAvailFill');
    const warnEl   = document.getElementById('noCopiesWarning');
    const catEl    = document.getElementById('sidebarBookCategory');
    const catName  = document.getElementById('sidebarBookCategoryName');

    if (titleEl)  titleEl.textContent  = d.title  || '—';
    if (authorEl) authorEl.textContent = d.author || '—';
    if (isbnEl)   isbnEl.textContent   = d.isbn   ? 'ISBN ' + d.isbn : '';
    _setBookCover('sidebarBookCover', 'sidebarBookCoverFallback', d.cover_url);

    const avail = parseInt(d.available_copies, 10) || 0;
    const total = parseInt(d.total_copies, 10) || 1;
    if (countEl) countEl.textContent = avail + ' / ' + total;
    if (fillEl)  fillEl.style.width  = Math.round((avail / total) * 100) + '%';
    if (warnEl)  warnEl.classList.toggle('is-hidden', avail > 0);

    if (catEl && catName && d.category) {
      catName.textContent = d.category;
      catEl.classList.remove('is-hidden');
    } else if (catEl) {
      catEl.classList.add('is-hidden');
    }

    // Due date banner
    const rules  = window.LIBRARY_RULES || {};
    const banner = document.getElementById('sidebarDueBanner');
    const dueEl2 = document.getElementById('sidebarDueDate');
    const durEl  = document.getElementById('sidebarDuration');
    if (banner && dueEl2 && rules.defaultLoanDays) {
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + rules.defaultLoanDays);
      dueEl2.textContent = dueDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
      if (durEl) durEl.textContent = rules.defaultLoanDays + ' days';
      banner.classList.remove('is-hidden');
    }
  }

  // ── Wire inputs ──────────────────────────────────────────────────
  if (memberInput) {
    const debouncedMember = debounce(val => lookupMember(val), DEBOUNCE_MS);
    memberInput.addEventListener('input',  e => debouncedMember(e.target.value));
    memberInput.addEventListener('change', e => lookupMember(e.target.value));
    if (memberInput.value.trim()) lookupMember(memberInput.value);
  }

  if (bookInput) {
    const debouncedBook = debounce(val => lookupBook(val), DEBOUNCE_MS);
    bookInput.addEventListener('input',  e => debouncedBook(e.target.value));
    bookInput.addEventListener('change', e => lookupBook(e.target.value));
    if (bookInput.value.trim()) lookupBook(bookInput.value);
  }

  // ── Tab: member → book ───────────────────────────────────────────
  memberInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (memberInput.value.trim()) lookupMember(memberInput.value);
      if (e.key === 'Enter') { e.preventDefault(); bookInput?.focus(); }
    }
  });
  bookInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (bookInput.value.trim()) lookupBook(bookInput.value);
      setTimeout(() => { if (memberValid && bookValid) form?.submit(); }, 400);
    }
  });

  // ── Submit guard ─────────────────────────────────────────────────
  form?.addEventListener('submit', () => {
    if (submitBtn) {
      submitBtn.disabled  = true;
      submitBtn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" style="animation:spin 1s linear infinite;width:16px;height:16px"><path d="M10 3a7 7 0 0 1 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Issuing…';
    }
  });

})();