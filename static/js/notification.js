/* =============================================================
   notifications.js  v3
   ─ NotifUtils    → shared helpers (timeAgo, api, icon, cookie)
   ─ NotifStore    → single data source, pub/sub, API calls
   ─ BadgeManager  → keeps ALL badge elements in sync
   ─ NotifModal    → topbar bell dropdown (NEW)
   ─ NotifPanel    → full-height slide-in drawer
   ─ NotifToast    → bottom-right popup toasts
   ─ NotifBoard    → full board page (window.NOTIF_BOARD = true)
   ─ NotifPoller   → 30-second background refresh
   ============================================================= */
'use strict';


/* ═══════════════════════════════════════════════════════════
   SHARED UTILITIES
═══════════════════════════════════════════════════════════ */
const NotifUtils = (() => {

  const TYPE_ICON = {
    info:    'fa-circle-info',
    success: 'fa-circle-check',
    warning: 'fa-triangle-exclamation',
    error:   'fa-circle-xmark',
    system:  'fa-gear',
    overdue: 'fa-clock',
    book:    'fa-book',
    return:  'fa-rotate-left',
    member:  'fa-user',
    fine:    'fa-coins',
  };

  function timeAgo(dateStr) {
    const diff  = Date.now() - new Date(dateStr).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(mins  / 60);
    const days  = Math.floor(hours / 24);
    if (mins  < 1)  return 'just now';
    if (mins  < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days  < 7)  return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return m ? decodeURIComponent(m[2]) : '';
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  function icon(type) { return TYPE_ICON[type] || 'fa-circle-info'; }

  async function api(url, method = 'GET', body = null) {
    const opts = {
      method,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken'),
      },
    };
    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (method === 'DELETE') return null;
    return res.json();
  }

  return { timeAgo, getCookie, sleep, icon, api };
})();


/* ═══════════════════════════════════════════════════════════
   STORE — single source of truth, pub/sub, all API calls
═══════════════════════════════════════════════════════════ */
const NotifStore = (() => {
  let _list      = [];
  let _listeners = [];
  let _seenIds   = new Set();

  function emit() { _listeners.forEach(fn => fn(_list)); }

  async function fetchAll() {
    try {
      const data = await NotifUtils.api('/api/notifications/');
      _list = Array.isArray(data) ? data : (data.results ?? []);
    } catch (e) {
      console.warn('[NotifStore] fetch failed', e);
    }
    emit();
    return _list;
  }

  async function markRead(id) {
    const n = _list.find(x => x.id === id);
    if (!n || n.read) return;
    n.read = true;
    emit();
    try { await NotifUtils.api(`/api/notifications/${id}/read/`, 'PATCH'); }
    catch (e) { console.warn(e); }
  }

  async function markAllRead() {
    _list.forEach(n => { n.read = true; });
    emit();
    try { await NotifUtils.api('/api/notifications/mark-all-read/', 'POST'); }
    catch (e) { console.warn(e); }
  }

  async function remove(id) {
    _list = _list.filter(n => n.id !== id);
    emit();
    try { await NotifUtils.api(`/api/notifications/${id}/`, 'DELETE'); }
    catch (e) { console.warn(e); }
  }

  async function clearAll() {
    _list = [];
    emit();
    try { await NotifUtils.api('/api/notifications/clear/', 'DELETE'); }
    catch (e) { console.warn(e); }
  }

  function getNew(list)    { return list.filter(n => !_seenIds.has(n.id)); }
  function markSeen(list)  { list.forEach(n => _seenIds.add(n.id)); }
  function subscribe(fn)   { _listeners.push(fn); }
  function getAll()        { return _list; }
  function getUnread()     { return _list.filter(n => !n.read).length; }

  return { fetch: fetchAll, markRead, markAllRead, remove, clearAll,
           subscribe, getAll, getUnread, getNew, markSeen };
})();


/* ═══════════════════════════════════════════════════════════
   BADGE MANAGER — keeps every badge element in sync
═══════════════════════════════════════════════════════════ */
const BadgeManager = (() => {
  function update(count) {
    // Targets: sidebar nav-badge, topbar bell badge, modal header badge,
    //          panel header badge, any custom .notification-badge
    document.querySelectorAll(
      '.notif-badge, .notif-modal-badge, .nav-badge, ' +
      '#topbarBadge, #notifUnreadCount, #notifModalBadge, .notification-badge'
    ).forEach(el => {
      el.textContent    = count > 99 ? '99+' : String(count);
      el.style.display  = count === 0 ? 'none' : 'inline-flex';
    });
  }
  return { update };
})();


/* ═══════════════════════════════════════════════════════════
   NOTIFICATION MODAL — topbar bell dropdown
═══════════════════════════════════════════════════════════ */
const NotifModal = (() => {
  const modal    = document.getElementById('notifModal');
  const backdrop = document.getElementById('notifModalBackdrop');
  const bodyEl   = document.getElementById('notifModalBody');
  const btnClose = document.getElementById('notifModalClose');
  const btnMark  = document.getElementById('notifModalMarkAll');
  const tabs     = document.querySelectorAll('[data-modal-tab]');
  const toggles  = document.querySelectorAll('.notif-modal-toggle');

  if (!modal) return { init() {}, open() {}, close() {}, toggle() {} };

  let isOpen    = false;
  let activeTab = 'all';
  const MAX     = 8;   // max items shown in dropdown

  /* ── filter ── */
  function filterList(list) {
    if (activeTab === 'unread')  return list.filter(n => !n.read);
    if (activeTab === 'overdue') return list.filter(n => n.type === 'overdue');
    return list;
  }

  /* ── build one item row ── */
  function makeItem(n) {
    const type = n.type || 'info';
    const el   = document.createElement('div');
    el.className  = `notif-modal__item notif-modal__item--${n.read ? 'read' : 'unread'}`;
    el.dataset.id = n.id;
    el.innerHTML  = `
      <div class="notif-modal__item-icon notif-modal__item-icon--${type}">
        <i class="fas ${NotifUtils.icon(type)}"></i>
      </div>
      <div class="notif-modal__item-body">
        <p class="notif-modal__item-title">${n.title}</p>
        ${n.description ? `<p class="notif-modal__item-desc">${n.description}</p>` : ''}
        <span class="notif-modal__item-time">${NotifUtils.timeAgo(n.created_at)}</span>
      </div>
      <button class="notif-modal__item-dismiss" title="Dismiss" aria-label="Dismiss">
        <i class="fas fa-xmark"></i>
      </button>`;

    /* mark read on body click */
    el.querySelector('.notif-modal__item-body').addEventListener('click', () => {
      NotifStore.markRead(n.id);
      el.classList.replace('notif-modal__item--unread', 'notif-modal__item--read');
    });

    /* dismiss */
    el.querySelector('.notif-modal__item-dismiss').addEventListener('click', async (e) => {
      e.stopPropagation();
      el.classList.add('is-dismissing');
      await NotifUtils.sleep(220);
      NotifStore.remove(n.id);
    });

    return el;
  }

  /* ── render list ── */
  function render(list) {
    const items = filterList(list).slice(0, MAX);
    if (!items.length) {
      bodyEl.innerHTML = `
        <div class="notif-modal__empty">
          <i class="fas fa-bell-slash"></i>
          <p>Nothing to show</p>
        </div>`;
      return;
    }
    bodyEl.innerHTML = '';
    const frag = document.createDocumentFragment();
    items.forEach((n, i) => {
      const el = makeItem(n);
      el.style.animationDelay = `${i * 25}ms`;
      frag.appendChild(el);
    });
    bodyEl.appendChild(frag);
  }

  /* ── open / close / toggle ── */
  function open() {
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    backdrop.classList.add('is-visible');
    toggles.forEach(t => t.setAttribute('aria-expanded', 'true'));
    isOpen = true;
    render(NotifStore.getAll());   // always fresh on open
  }

  function close() {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    backdrop.classList.remove('is-visible');
    toggles.forEach(t => t.setAttribute('aria-expanded', 'false'));
    isOpen = false;
  }

  function toggle() { isOpen ? close() : open(); }

  /* ── init ── */
  function init() {
    /* Bell / any .notif-modal-toggle clicks */
    toggles.forEach(t => t.addEventListener('click', e => {
      e.stopPropagation();
      toggle();
    }));

    btnClose?.addEventListener('click', close);
    backdrop?.addEventListener('click', close);
    btnMark?.addEventListener('click', () => NotifStore.markAllRead());

    /* Tab switching */
    tabs.forEach(t => t.addEventListener('click', () => {
      activeTab = t.dataset.modalTab;
      tabs.forEach(x => {
        x.classList.toggle('is-active', x === t);
        x.setAttribute('aria-selected', String(x === t));
      });
      render(NotifStore.getAll());
    }));

    /* Escape closes */
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) close(); });

    /* Clicking inside modal doesn't bubble to backdrop */
    modal.addEventListener('click', e => e.stopPropagation());

    /* Re-render & update badges whenever store changes */
    NotifStore.subscribe(list => {
      if (isOpen) render(list);
      BadgeManager.update(NotifStore.getUnread());
    });
  }

  return { init, open, close, toggle };
})();


/* ═══════════════════════════════════════════════════════════
   NOTIFICATION PANEL — full-height slide-in drawer
═══════════════════════════════════════════════════════════ */
const NotifPanel = (() => {
  const panel      = document.getElementById('notifPanel');
  const overlay    = document.getElementById('notifOverlay');
  const bodyEl     = document.getElementById('notifBody');
  const btnClose   = document.getElementById('notifClose');
  const btnMarkAll = document.getElementById('notifMarkAllRead');
  const btnRefresh = document.getElementById('notifRefresh');
  const tabs       = document.querySelectorAll('[data-tab]');

  if (!panel) return { init() {}, open() {}, close() {}, toggle() {} };

  let isOpen    = false;
  let activeTab = 'all';

  function filterList(list) {
    if (activeTab === 'unread')  return list.filter(n => !n.read);
    if (activeTab !== 'all')     return list.filter(n => n.type === activeTab);
    return list;
  }

  function makeItem(n) {
    const type = n.type || 'info';
    const el   = document.createElement('div');
    el.className  = `notif-item notif-item--${n.read ? 'read' : 'unread'} is-entering`;
    el.dataset.id = n.id;
    el.innerHTML  = `
      <div class="notif-item__dot"></div>
      <div class="notif-item__icon notif-item__icon--${type}">
        <i class="fas ${NotifUtils.icon(type)}"></i>
      </div>
      <div class="notif-item__body">
        <p class="notif-item__title">${n.title}</p>
        <p class="notif-item__desc">${n.description || ''}</p>
        <div class="notif-item__meta">
          <span class="notif-item__time">${NotifUtils.timeAgo(n.created_at)}</span>
          ${n.tag ? `<span class="notif-item__tag notif-item__tag--${n.tag}">${n.tag}</span>` : ''}
        </div>
      </div>
      <button class="notif-item__dismiss" title="Dismiss" aria-label="Dismiss">
        <i class="fas fa-xmark"></i>
      </button>`;

    el.querySelector('.notif-item__body').addEventListener('click', () => NotifStore.markRead(n.id));
    el.querySelector('.notif-item__dismiss').addEventListener('click', async e => {
      e.stopPropagation();
      el.classList.add('is-dismissing');
      await NotifUtils.sleep(280);
      NotifStore.remove(n.id);
    });
    return el;
  }

  function render(list) {
    const items = filterList(list);
    if (!items.length) {
      bodyEl.innerHTML = `
        <div class="notif-empty">
          <div class="notif-empty__icon"><i class="fas fa-bell-slash"></i></div>
          <p class="notif-empty__text">Nothing here</p>
          <p class="notif-empty__sub">No notifications in this category</p>
        </div>`;
      return;
    }
    bodyEl.innerHTML = '';
    const frag = document.createDocumentFragment();
    items.forEach(n => frag.appendChild(makeItem(n)));
    bodyEl.appendChild(frag);
  }

  function open() {
    panel.classList.add('is-open');
    overlay.classList.add('is-visible');
    panel.setAttribute('aria-hidden', 'false');
    isOpen = true;
  }

  function close() {
    panel.classList.remove('is-open');
    overlay.classList.remove('is-visible');
    panel.setAttribute('aria-hidden', 'true');
    isOpen = false;
  }

  function toggle() { isOpen ? close() : open(); }

  function init() {
    btnClose?.addEventListener('click', close);
    overlay?.addEventListener('click', close);
    btnMarkAll?.addEventListener('click', () => NotifStore.markAllRead());
    btnRefresh?.addEventListener('click', () => NotifStore.fetch());

    tabs.forEach(t => t.addEventListener('click', () => {
      activeTab = t.dataset.tab;
      tabs.forEach(x => {
        x.classList.toggle('is-active', x === t);
        x.setAttribute('aria-selected', String(x === t));
      });
      render(NotifStore.getAll());
    }));

    /* Any .notif-toggle in the page opens the panel */
    document.querySelectorAll('.notif-toggle').forEach(btn =>
      btn.addEventListener('click', toggle)
    );

    document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) close(); });

    NotifStore.subscribe(list => {
      render(list);
      BadgeManager.update(NotifStore.getUnread());
    });
  }

  return { init, open, close, toggle };
})();


/* ═══════════════════════════════════════════════════════════
   NOTIFICATION TOAST — bottom-right popup
═══════════════════════════════════════════════════════════ */
const NotifToast = (() => {
  const DURATION = 5000;

  /* Use existing container or create one */
  const container = (() => {
    let c = document.getElementById('toastContainer') ||
            document.querySelector('.nb-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.className = 'nb-toast-container';
      document.body.appendChild(c);
    }
    return c;
  })();

  const TYPE_ICON = {
    info:    'fa-circle-info',
    success: 'fa-circle-check',
    warning: 'fa-triangle-exclamation',
    error:   'fa-circle-xmark',
    system:  'fa-gear',
    overdue: 'fa-clock',
    book:    'fa-book',
    return:  'fa-rotate-left',
    member:  'fa-user',
    fine:    'fa-coins',
  };

  async function show(n, duration = DURATION) {
    const type  = n.type || 'info';
    const toast = document.createElement('div');
    toast.className = `nb-toast nb-toast--${type}`;
    toast.innerHTML = `
      <div class="nb-toast__icon">
        <i class="fas ${TYPE_ICON[type] || 'fa-circle-info'}"></i>
      </div>
      <div class="nb-toast__body">
        <p class="nb-toast__title">${n.title}</p>
        ${n.description ? `<p class="nb-toast__desc">${n.description}</p>` : ''}
      </div>
      <button class="nb-toast__close" title="Dismiss" aria-label="Dismiss">
        <i class="fas fa-xmark"></i>
      </button>
      <div class="nb-toast__progress" style="animation-duration:${duration}ms"></div>`;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('is-visible'));

    const dismiss = async () => {
      toast.classList.remove('is-visible');
      toast.classList.add('is-leaving');
      await NotifUtils.sleep(280);
      toast.remove();
    };

    toast.querySelector('.nb-toast__close').addEventListener('click', dismiss);
    const prog = toast.querySelector('.nb-toast__progress');
    toast.addEventListener('mouseenter', () => prog.style.animationPlayState = 'paused');
    toast.addEventListener('mouseleave', () => prog.style.animationPlayState = 'running');
    setTimeout(dismiss, duration);
  }

  return { show };
})();


/* ═══════════════════════════════════════════════════════════
   FULL BOARD — activates only when window.NOTIF_BOARD = true
═══════════════════════════════════════════════════════════ */
const NotifBoard = (() => {
  const PAGE_SIZE = 15;
  let currentPage  = 1;
  let activeFilter = 'all';
  let searchQuery  = '';
  let fullList     = [];

  function init() {
    if (!window.NOTIF_BOARD) return;

    const listEl   = document.getElementById('nbList');
    const emptyEl  = document.getElementById('nbEmpty');
    const searchEl = document.getElementById('nbSearch');
    const filters  = document.querySelectorAll('.nb-filter');
    const btnMark  = document.getElementById('nbMarkAllRead');
    const btnClear = document.getElementById('nbClearAll');
    const btnPrev  = document.getElementById('nbPrevPage');
    const btnNext  = document.getElementById('nbNextPage');
    const pageInfo = document.getElementById('nbPageInfo');

    if (!listEl) return;

    function getFiltered() {
      let data = fullList;
      if (activeFilter === 'unread')     data = data.filter(n => !n.read);
      else if (activeFilter !== 'all')   data = data.filter(n => n.type === activeFilter);
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        data = data.filter(n =>
          n.title.toLowerCase().includes(q) ||
          (n.description || '').toLowerCase().includes(q)
        );
      }
      return data;
    }

    function updateStats(data) {
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set('statTotal',   data.length);
      set('statUnread',  data.filter(n => !n.read).length);
      set('statOverdue', data.filter(n => n.type === 'overdue').length);
      set('statSystem',  data.filter(n => n.type === 'system').length);
    }

    function renderBoard(data) {
      const filtered   = getFiltered();
      const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
      if (currentPage > totalPages) currentPage = totalPages;

      const start = (currentPage - 1) * PAGE_SIZE;
      const page  = filtered.slice(start, start + PAGE_SIZE);

      listEl.innerHTML = '';
      updateStats(data);

      if (!page.length) {
        if (emptyEl) { listEl.appendChild(emptyEl); emptyEl.style.display = 'flex'; }
        if (btnPrev) btnPrev.disabled = true;
        if (btnNext) btnNext.disabled = true;
        if (pageInfo) pageInfo.textContent = 'Page 0 of 0';
        return;
      }

      if (emptyEl) emptyEl.style.display = 'none';
      const frag = document.createDocumentFragment();

      page.forEach(n => {
        const type = n.type || 'info';
        const item = document.createElement('div');
        item.className  = `nb-item nb-item--${n.read ? 'read' : 'unread'}`;
        item.dataset.id = n.id;
        item.innerHTML  = `
          <div class="nb-item__icon nb-item__icon--${type}">
            <i class="fas ${NotifUtils.icon(type)}"></i>
          </div>
          <div class="nb-item__body">
            <p class="nb-item__title">${n.title}</p>
            <p class="nb-item__desc">${n.description || ''}</p>
            <div class="nb-item__meta">
              <span class="nb-item__time">${NotifUtils.timeAgo(n.created_at)}</span>
              ${n.tag ? `<span class="nb-item__tag nb-item__tag--${n.tag}">${n.tag}</span>` : ''}
            </div>
          </div>
          <div class="nb-item__actions">
            ${!n.read
              ? `<button class="nb-item__btn nb-item__btn--read" title="Mark read" aria-label="Mark read">
                   <i class="fas fa-check"></i>
                 </button>`
              : ''}
            <button class="nb-item__btn nb-item__btn--delete" title="Delete" aria-label="Delete">
              <i class="fas fa-trash-can"></i>
            </button>
          </div>`;

        item.querySelector('.nb-item__btn--read')?.addEventListener('click', () => NotifStore.markRead(n.id));
        item.querySelector('.nb-item__btn--delete').addEventListener('click', async () => {
          item.classList.add('is-removing');
          await NotifUtils.sleep(260);
          NotifStore.remove(n.id);
        });
        item.querySelector('.nb-item__body').addEventListener('click', () => NotifStore.markRead(n.id));
        frag.appendChild(item);
      });

      listEl.appendChild(frag);

      if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
      if (btnPrev)  btnPrev.disabled = currentPage <= 1;
      if (btnNext)  btnNext.disabled = currentPage >= totalPages;
    }

    searchEl?.addEventListener('input', e => {
      searchQuery = e.target.value.trim();
      currentPage = 1;
      renderBoard(fullList);
    });

    filters.forEach(btn => btn.addEventListener('click', () => {
      activeFilter = btn.dataset.filter;
      filters.forEach(b => b.classList.toggle('is-active', b === btn));
      currentPage = 1;
      renderBoard(fullList);
    }));

    btnMark?.addEventListener('click', () => NotifStore.markAllRead());
    btnClear?.addEventListener('click', () => {
      if (confirm('Clear all notifications? This cannot be undone.')) NotifStore.clearAll();
    });
    btnPrev?.addEventListener('click', () => { currentPage--; renderBoard(fullList); });
    btnNext?.addEventListener('click', () => { currentPage++; renderBoard(fullList); });

    NotifStore.subscribe(list => { fullList = list; renderBoard(fullList); });
  }

  return { init };
})();


/* ═══════════════════════════════════════════════════════════
   POLLER — background refresh every 30 s, toasts for new items
═══════════════════════════════════════════════════════════ */
const NotifPoller = (() => {
  async function poll() {
    const fresh    = await NotifStore.fetch();
    const newItems = NotifStore.getNew(fresh);
    newItems.slice(0, 3).forEach(n => NotifToast.show(n));
    NotifStore.markSeen(fresh);
  }

  function init() {
    /* First load: seed seen IDs silently (no toasts) */
    NotifStore.fetch().then(list => NotifStore.markSeen(list));
    setInterval(poll, 30_000);
  }

  return { init };
})();


/* ═══════════════════════════════════════════════════════════
   AUTO-DISMISS DJANGO MESSAGES
═══════════════════════════════════════════════════════════ */
function initDjangoMessages() {
  document.querySelectorAll('.message').forEach((msg, i) => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.4s, transform 0.4s';
      msg.style.opacity    = '0';
      msg.style.transform  = 'translateX(20px)';
      setTimeout(() => msg.remove(), 400);
    }, 4000 + i * 600);
  });
}


/* ═══════════════════════════════════════════════════════════
   SIDEBAR TOGGLE (topbar hamburger for collapsed mode)
═══════════════════════════════════════════════════════════ */
function initSidebarToggle() {
  const btn     = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const main    = document.getElementById('mainContent');
  if (!btn || !sidebar) return;

  btn.addEventListener('click', () => {
    sidebar.classList.toggle('is-collapsed');
    main?.classList.toggle('sidebar-collapsed');
  });
}


/* ═══════════════════════════════════════════════════════════
   BOOT
═══════════════════════════════════════════════════════════ */
function boot() {
  NotifModal.init();        // topbar bell modal   — all pages
  NotifPanel.init();        // slide-in panel      — all pages
  NotifBoard.init();        // full board          — board page only
  NotifPoller.init();       // background polling  — all pages
  initDjangoMessages();     // auto-dismiss toasts
  initSidebarToggle();      // collapsible sidebar

  /* Global access for manual use e.g. NotifToast.show({...}) */
  window.NotifToast  = NotifToast;
  window.NotifStore  = NotifStore;
  window.NotifPanel  = NotifPanel;
  window.NotifModal  = NotifModal;
}

document.readyState === 'loading'
  ? document.addEventListener('DOMContentLoaded', boot)
  : boot();