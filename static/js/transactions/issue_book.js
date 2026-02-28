/* ============================================================
   issue_book.js
   ============================================================ */

(function () {
  'use strict';

  const MAX_RESULTS = 3;

  /* ── State ── */
  let selectedMember = null;
  let selectedBook   = null;

  /* ── DOM refs ── */
  const memberSearch   = document.getElementById('memberSearch');
  const memberIdInput  = document.getElementById('memberId');
  const memberIdHidden = document.getElementById('memberIdHidden');
  const memberDropdown = document.getElementById('memberDropdown');

  const bookSearch     = document.getElementById('bookSearch');
  const bookIdInput    = document.getElementById('bookId');
  const bookIdHidden   = document.getElementById('bookIdHidden');
  const bookDropdown   = document.getElementById('bookDropdown');

  const issueDateInput = document.querySelector('input[name="issue_date"]');
  const loanDuration   = document.querySelector('input[name="loan_duration"]');
  const dueDateValue   = document.querySelector('.due-date-preview__date');

  /* ── Sidebar refs ── */
  const sidebarMemberEmpty   = document.getElementById('sidebarMemberEmpty');
  const sidebarMemberDetails = document.getElementById('sidebarMemberDetails');
  const sidebarBookEmpty     = document.getElementById('sidebarBookEmpty');
  const sidebarBookDetails   = document.getElementById('sidebarBookDetails');
  const sidebarDueBanner     = document.getElementById('sidebarDueBanner');
  const noCopiesWarn         = document.getElementById('noCopiesWarning');

  const submitBtn = document.getElementById('submitBtn');

  /* ─────────────── MEMBER SEARCH ─────────────── */
  const memberOptions = Array.from(memberIdInput.options).slice(1).map(o => ({
    id:        o.value,
    name:      o.dataset.name,
    memberId:  o.dataset.id,
    type:      o.dataset.type,
    active:    parseInt(o.dataset.active,    10) || 0,
    limit:     parseInt(o.dataset.limit,     10) || 0,
    canBorrow: parseInt(o.dataset.canBorrow, 10),
    totalDue:  parseFloat(o.dataset.totalDue) || 0,
    email:     o.dataset.email,
  }));

  memberSearch.addEventListener('input', function () {
    const q = this.value.toLowerCase().trim();
    if (!q) { closeDropdown(memberDropdown); return; }
    const filtered = memberOptions.filter(m =>
      m.name.toLowerCase().includes(q) || m.memberId.toLowerCase().includes(q)
    ).slice(0, MAX_RESULTS);
    renderMemberDropdown(filtered);
  });

  function renderMemberDropdown(items) {
    memberDropdown.innerHTML = '';

    if (!items.length) {
      memberDropdown.innerHTML =
        '<div class="dd-empty"><svg viewBox="0 0 20 20" fill="none" style="width:14px;height:14px"><circle cx="9" cy="9" r="5.5" stroke="currentColor" stroke-width="1.5"/><path d="M13.5 13.5l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg> No members found</div>';
    } else {
      const hdr = document.createElement('div');
      hdr.className = 'dd-header';
      hdr.innerHTML = '<span>Member</span><span>ID</span><span>Type</span><span>Slots</span>';
      memberDropdown.appendChild(hdr);

      items.forEach(m => {
        const slots      = m.limit ? m.canBorrow + '/' + m.limit : '∞';
        const slotsCls   = (m.limit && m.canBorrow === 0) ? 'dd-badge dd-badge--warn' : 'dd-badge dd-badge--ok';
        const row        = document.createElement('div');
        row.className    = 'dd-row';
        row.innerHTML    =
          '<div class="dd-cell dd-cell--name">' +
            '<span class="dd-avatar">' + escHtml(m.name.charAt(0).toUpperCase()) + '</span>' +
            '<span class="dd-name">'   + escHtml(m.name) + '</span>' +
          '</div>' +
          '<div class="dd-cell dd-cell--id">'  + escHtml(m.memberId) + '</div>' +
          '<div class="dd-cell dd-cell--type">' + escHtml(m.type)    + '</div>' +
          '<div class="dd-cell"><span class="' + slotsCls + '">' + slots + '</span></div>';
        row.addEventListener('click', () => selectMember(m));
        memberDropdown.appendChild(row);
      });
    }

    memberDropdown.classList.remove('is-hidden');
  }

  function selectMember(m) {
    selectedMember       = m;
    memberSearch.value   = m.name + ' (' + m.memberId + ')';
    memberIdHidden.value = m.id;
    closeDropdown(memberDropdown);

    document.getElementById('sidebarMemberAvatar').textContent = m.name.charAt(0).toUpperCase();
    document.getElementById('sidebarMemberName').textContent   = m.name;
    document.getElementById('sidebarMemberType').textContent   = m.type;
    document.getElementById('sidebarMemberId').textContent     = m.memberId;
    document.getElementById('sidebarActiveLoans').textContent  = m.active;
    document.getElementById('sidebarCanBorrow').textContent    = m.limit ? m.canBorrow + ' / ' + m.limit : '∞';
    document.getElementById('sidebarTotalDue').textContent     = m.totalDue > 0 ? '₹' + m.totalDue.toFixed(2) : '₹0';

    var emailEl = document.getElementById('sidebarMemberEmail');
    if (emailEl) emailEl.textContent = m.email || '';

    sidebarMemberEmpty.classList.add('is-hidden');
    sidebarMemberDetails.classList.remove('is-hidden');

    updateSubmitState();
    updateDueBanner();
  }

  /* ─────────────── BOOK SEARCH ─────────────── */
  const bookOptions = Array.from(bookIdInput.options).slice(1).map(o => ({
    id:        o.value,
    title:     o.dataset.title,
    author:    o.dataset.author,
    isbn:      o.dataset.isbn,
    available: parseInt(o.dataset.available, 10) || 0,
    total:     parseInt(o.dataset.total, 10) || 0,
    category:  o.dataset.category,
  }));

  bookSearch.addEventListener('input', function () {
    const q = this.value.toLowerCase().trim();
    if (!q) { closeDropdown(bookDropdown); return; }
    const filtered = bookOptions.filter(b =>
      b.title.toLowerCase().includes(q) ||
      b.author.toLowerCase().includes(q) ||
      b.isbn.toLowerCase().includes(q)
    ).slice(0, MAX_RESULTS);
    renderBookDropdown(filtered);
  });

  function renderBookDropdown(items) {
    bookDropdown.innerHTML = '';

    if (!items.length) {
      bookDropdown.innerHTML =
        '<div class="dd-empty"><svg viewBox="0 0 20 20" fill="none" style="width:14px;height:14px"><circle cx="9" cy="9" r="5.5" stroke="currentColor" stroke-width="1.5"/><path d="M13.5 13.5l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg> No books found</div>';
    } else {
      const hdr = document.createElement('div');
      hdr.className = 'dd-header';
      hdr.innerHTML = '<span>Title</span><span>Author</span><span>ISBN</span><span>Avail.</span>';
      bookDropdown.appendChild(hdr);

      items.forEach(b => {
        const availCls   = b.available > 0 ? 'dd-badge dd-badge--ok' : 'dd-badge dd-badge--warn';
        const availLabel = b.available > 0 ? b.available + '/' + b.total : 'None';
        const row        = document.createElement('div');
        row.className    = 'dd-row';
        row.innerHTML    =
          '<div class="dd-cell dd-cell--name">' +
            '<span class="dd-book-icon"><svg viewBox="0 0 16 20" fill="none" style="width:12px;height:15px"><rect x="1" y="1" width="14" height="18" rx="1.5" stroke="currentColor" stroke-width="1.2"/><path d="M4 6h8M4 9h8M4 12h5" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg></span>' +
            '<span class="dd-name">' + escHtml(b.title) + '</span>' +
          '</div>' +
          '<div class="dd-cell dd-cell--sub">'  + escHtml(b.author) + '</div>' +
          '<div class="dd-cell dd-cell--mono">' + escHtml(b.isbn)   + '</div>' +
          '<div class="dd-cell"><span class="' + availCls + '">' + availLabel + '</span></div>';
        row.addEventListener('click', () => selectBook(b));
        bookDropdown.appendChild(row);
      });
    }

    bookDropdown.classList.remove('is-hidden');
  }

  function selectBook(b) {
    selectedBook       = b;
    bookSearch.value   = b.title;
    bookIdHidden.value = b.id;
    closeDropdown(bookDropdown);

    var pct = b.total > 0 ? (b.available / b.total) * 100 : 0;

    document.getElementById('sidebarBookTitle').textContent  = b.title;
    document.getElementById('sidebarBookAuthor').textContent = b.author;
    document.getElementById('sidebarBookIsbn').textContent   = b.isbn;
    document.getElementById('sidebarAvailCount').textContent = b.available + ' / ' + b.total;
    document.getElementById('sidebarAvailFill').style.width  = pct + '%';

    var catWrap = document.getElementById('sidebarBookCategory');
    var catName = document.getElementById('sidebarBookCategoryName');
    if (b.category) {
      catName.textContent = b.category;
      catWrap.classList.remove('is-hidden');
    } else {
      catWrap.classList.add('is-hidden');
    }

    sidebarBookEmpty.classList.add('is-hidden');
    sidebarBookDetails.classList.remove('is-hidden');
    if (b.available > 0) { noCopiesWarn.classList.add('is-hidden'); } else { noCopiesWarn.classList.remove('is-hidden'); }

    updateSubmitState();
    updateDueBanner();
  }

  /* ─────────────── DUE DATE ─────────────── */
  function calcDueDate() {
    var raw  = issueDateInput ? issueDateInput.value : '';
    var d    = raw ? new Date(raw + 'T00:00:00') : new Date();
    var days = loanDuration
      ? parseInt(loanDuration.value, 10)
      : (window.LIBRARY_RULES && window.LIBRARY_RULES.defaultLoanDays) || 14;
    if (isNaN(d.getTime()) || isNaN(days)) return { label: '—', days: days };
    d.setDate(d.getDate() + days);
    return {
      label: d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
      days:  days,
    };
  }

  function updateDueBanner() {
    if (!selectedMember || !selectedBook) { sidebarDueBanner.classList.add('is-hidden'); return; }
    var res = calcDueDate();
    document.getElementById('sidebarDueDate').textContent  = res.label;
    document.getElementById('sidebarDuration').textContent = res.days + ' days';
    sidebarDueBanner.classList.remove('is-hidden');
    if (dueDateValue) dueDateValue.textContent = res.label;
  }

  if (dueDateValue) dueDateValue.textContent = calcDueDate().label;

  /* ─────────────── SUBMIT STATE ─────────────── */
  function updateSubmitState() {
    var canSubmit = !!selectedMember && !!selectedBook && selectedBook.available > 0;
    submitBtn.disabled      = !canSubmit;
    submitBtn.style.opacity = canSubmit ? '1' : '.55';
    submitBtn.style.cursor  = canSubmit ? 'pointer' : 'not-allowed';
  }

  /* ─────────────── OUTSIDE CLICK ─────────────── */
  document.addEventListener('click', function (e) {
    if (!e.target.closest('#memberSearch') && !e.target.closest('#memberDropdown')) closeDropdown(memberDropdown);
    if (!e.target.closest('#bookSearch')   && !e.target.closest('#bookDropdown'))   closeDropdown(bookDropdown);
  });

  function closeDropdown(el) { el.classList.add('is-hidden'); }

  /* ─────────────── FORM SUBMIT ─────────────── */
  document.getElementById('issueBookForm').addEventListener('submit', function (e) {
    if (!selectedMember || !selectedBook) {
      e.preventDefault(); showToast('Please select both a member and a book.', 'error'); return;
    }
    if (selectedBook.available <= 0) {
      e.preventDefault(); showToast('No copies available for this book.', 'error'); return;
    }
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" style="width:15px;height:15px;animation:spin .7s linear infinite"><path d="M10 2a8 8 0 1 1-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Issuing\u2026';
  });

  /* ─────────────── HELPERS ─────────────── */
  function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function showToast(msg, type) {
    type = type || 'info';
    var t = document.createElement('div');
    Object.assign(t.style, {
      position:'fixed', bottom:'24px', right:'24px', padding:'12px 20px',
      borderRadius:'10px', fontFamily:"'DM Sans',sans-serif", fontSize:'13.5px',
      fontWeight:'500', color:'#fff',
      background: type==='success'?'#16a34a': type==='error'?'#b91c1c':'#2563eb',
      boxShadow:'0 8px 24px rgba(15,34,64,.2)', zIndex:'9999',
      opacity:'0', transform:'translateY(12px)', transition:'opacity .2s ease, transform .2s ease',
    });
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(function(){ t.style.opacity='1'; t.style.transform='translateY(0)'; });
    setTimeout(function(){ t.style.opacity='0'; setTimeout(function(){ t.remove(); }, 250); }, 3500);
  }

})();