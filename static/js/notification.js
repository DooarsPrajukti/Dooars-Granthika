/* =============================================================
   notifications.js  v2
   ─ Slide-in panel  → works on EVERY page
   ─ Full board      → activated when window.NOTIF_BOARD = true
   ─ Popup toasts    → works on EVERY page (polled + push)
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
   STORE  (single source of truth for all notification data)
═══════════════════════════════════════════════════════════ */
const NotifStore = (() => {
  let _list      = [];
  let _listeners = [];
  let _seenIds   = new Set();

  function emit() { _listeners.forEach(fn => fn(_list)); }

  async function fetch() {
    try {
      _list = await NotifUtils.api('/api/notifications/');
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
    _list.forEach(n => n.read = true);
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

  /** Returns items newer than last fetch that we haven't seen */
  function getNew(list) {
    return list.filter(n => !_seenIds.has(n.id));
  }

  function markSeen(list) { list.forEach(n => _seenIds.add(n.id)); }

  function subscribe(fn) { _listeners.push(fn); }

  function getAll()    { return _list; }
  function getUnread() { return _list.filter(n => !n.read).length; }

  return { fetch, markRead, markAllRead, remove, clearAll, subscribe, getAll, getUnread, getNew, markSeen };
})();


/* ═══════════════════════════════════════════════════════════
   BADGE MANAGER  (topbar bell badges on all pages)
═══════════════════════════════════════════════════════════ */
const BadgeManager = (() => {
  function update(count) {
    document.querySelectorAll('.notif-badge, #topbarBadge, #notifUnreadCount').forEach(el => {
      el.textContent = count > 99 ? '99+' : count;
      el.style.display = count === 0 ? 'none' : 'inline-flex';
    });
  }
  return { update };
})();


/* ═══════════════════════════════════════════════════════════
   SLIDE-IN PANEL  (present on every page via dashboard_base)
═══════════════════════════════════════════════════════════ */
const NotifPanel = (() => {
  const panel      = document.getElementById('notifPanel');
  const overlay    = document.getElementById('notifOverlay');
  const body       = document.getElementById('notifBody');
  const btnClose   = document.getElementById('notifClose');
  const btnMarkAll = document.getElementById('notifMarkAllRead');
  const btnRefresh = document.getElementById('notifRefresh');
  const tabs       = document.querySelectorAll('.notif-tab');

  let isOpen    = false;
  let activeTab = 'all';

  if (!panel) return { init() {} };  // guard if panel not in DOM

  function filterList(list) {
    if (activeTab === 'all')    return list;
    if (activeTab === 'unread') return list.filter(n => !n.read);
    return list.filter(n => n.type === activeTab);
  }

  function renderItem(n) {
    const type = n.type || 'info';
    const el   = document.createElement('div');
    el.className = `notif-item notif-item--${n.read ? 'read' : 'unread'} is-entering`;
    el.dataset.id = n.id;
    el.innerHTML = `
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
      <button class="notif-item__dismiss" title="Dismiss"><i class="fas fa-xmark"></i></button>`;

    el.querySelector('.notif-item__body').addEventListener('click', () => NotifStore.markRead(n.id));
    el.querySelector('.notif-item__dismiss').addEventListener('click', async (e) => {
      e.stopPropagation();
      el.classList.add('is-dismissing');
      await NotifUtils.sleep(280);
      NotifStore.remove(n.id);
    });
    return el;
  }

  function render(list) {
    const filtered = filterList(list);
    if (!filtered.length) {
      body.innerHTML = `
        <div class="notif-empty">
          <div class="notif-empty__icon"><i class="fas fa-bell-slash"></i></div>
          <p class="notif-empty__text">Nothing here</p>
          <p class="notif-empty__sub">No notifications in this category</p>
        </div>`;
      return;
    }
    body.innerHTML = '';
    const frag = document.createDocumentFragment();
    filtered.forEach(n => frag.appendChild(renderItem(n)));
    body.appendChild(frag);
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
    btnMarkAll?.addEventListener('click', NotifStore.markAllRead);
    btnRefresh?.addEventListener('click', NotifStore.fetch);

    tabs.forEach(t => t.addEventListener('click', () => {
      activeTab = t.dataset.tab;
      tabs.forEach(x => { x.classList.toggle('is-active', x === t); x.setAttribute('aria-selected', x === t); });
      render(NotifStore.getAll());
    }));

    document.querySelectorAll('.notif-toggle').forEach(btn =>
      btn.addEventListener('click', toggle)
    );

    document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) close(); });

    NotifStore.subscribe((list) => {
      render(list);
      BadgeManager.update(NotifStore.getUnread());
    });
  }

  return { init, open, close, toggle };
})();


/* ═══════════════════════════════════════════════════════════
   TOAST POPUP  (works on every page)
═══════════════════════════════════════════════════════════ */
const NotifToast = (() => {
  const DURATION = 5000;  // ms before auto-dismiss

  let container = document.querySelector('.nb-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'nb-toast-container';
    document.body.appendChild(container);
  }

  const TYPE_ICON = {
    info:    'fa-circle-info',
    success: 'fa-circle-check',
    warning: 'fa-triangle-exclamation',
    error:   'fa-circle-xmark',
    system:  'fa-gear',
    overdue: 'fa-clock',
  };

  async function show(n, duration = DURATION) {
    const type = n.type || 'info';
    const toast = document.createElement('div');
    toast.className = `nb-toast nb-toast--${type}`;
    toast.innerHTML = `
      <div class="nb-toast__bar"></div>
      <div class="nb-toast__icon"><i class="fas ${TYPE_ICON[type] || 'fa-circle-info'}"></i></div>
      <div class="nb-toast__body">
        <p class="nb-toast__title">${n.title}</p>
        ${n.description ? `<p class="nb-toast__desc">${n.description}</p>` : ''}
      </div>
      <button class="nb-toast__close" title="Dismiss"><i class="fas fa-xmark"></i></button>
      <div class="nb-toast__progress" style="animation-duration:${duration}ms"></div>`;

    container.appendChild(toast);

    const dismiss = async () => {
      toast.classList.add('is-leaving');
      await NotifUtils.sleep(240);
      toast.remove();
    };

    toast.querySelector('.nb-toast__close').addEventListener('click', dismiss);
    toast.addEventListener('mouseenter', () => toast.querySelector('.nb-toast__progress').style.animationPlayState = 'paused');
    toast.addEventListener('mouseleave', () => toast.querySelector('.nb-toast__progress').style.animationPlayState = 'running');

    setTimeout(dismiss, duration);
  }

  return { show };
})();


/* ═══════════════════════════════════════════════════════════
   FULL BOARD  (only activates on notification_board page)
═══════════════════════════════════════════════════════════ */
const NotifBoard = (() => {
  const PAGE_SIZE = 15;
  let currentPage  = 1;
  let activeFilter = 'all';
  let searchQuery  = '';
  let fullList     = [];

  function init() {
    if (!window.NOTIF_BOARD) return;

    const list       = document.getElementById('nbList');
    const empty      = document.getElementById('nbEmpty');
    const search     = document.getElementById('nbSearch');
    const filters    = document.querySelectorAll('.nb-filter');
    const btnMark    = document.getElementById('nbMarkAllRead');
    const btnClear   = document.getElementById('nbClearAll');
    const btnPrev    = document.getElementById('nbPrevPage');
    const btnNext    = document.getElementById('nbNextPage');
    const pageInfo   = document.getElementById('nbPageInfo');

    if (!list) return;

    // ── Filter + Search + Paginate ──
    function getFiltered() {
      let data = fullList;
      if (activeFilter === 'unread') data = data.filter(n => !n.read);
      else if (activeFilter !== 'all') data = data.filter(n => n.type === activeFilter);
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
      document.getElementById('statTotal').textContent   = data.length;
      document.getElementById('statUnread').textContent  = data.filter(n => !n.read).length;
      document.getElementById('statOverdue').textContent = data.filter(n => n.type === 'overdue').length;
      document.getElementById('statSystem').textContent  = data.filter(n => n.type === 'system').length;
    }

    function renderBoard(data) {
      const filtered  = getFiltered();
      const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
      if (currentPage > totalPages) currentPage = totalPages;

      const start = (currentPage - 1) * PAGE_SIZE;
      const page  = filtered.slice(start, start + PAGE_SIZE);

      list.innerHTML = '';
      updateStats(data);

      if (!page.length) {
        list.appendChild(empty);
        empty.style.display = 'flex';
        btnPrev.disabled = true;
        btnNext.disabled = true;
        pageInfo.textContent = 'Page 0 of 0';
        return;
      }

      empty.style.display = 'none';
      const frag = document.createDocumentFragment();

      page.forEach(n => {
        const type = n.type || 'info';
        const item = document.createElement('div');
        item.className = `nb-item nb-item--${n.read ? 'read' : 'unread'}`;
        item.dataset.id = n.id;
        item.innerHTML = `
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
            ${!n.read ? `<button class="nb-item__btn nb-item__btn--read" title="Mark read" data-id="${n.id}"><i class="fas fa-check"></i></button>` : ''}
            <button class="nb-item__btn nb-item__btn--delete" title="Delete" data-id="${n.id}"><i class="fas fa-trash-can"></i></button>
          </div>`;

        // mark read
        item.querySelector('.nb-item__btn--read')?.addEventListener('click', () => NotifStore.markRead(n.id));

        // delete
        item.querySelector('.nb-item__btn--delete').addEventListener('click', async () => {
          item.classList.add('is-removing');
          await NotifUtils.sleep(260);
          NotifStore.remove(n.id);
        });

        // click row = mark read
        item.querySelector('.nb-item__body').addEventListener('click', () => NotifStore.markRead(n.id));

        frag.appendChild(item);
      });

      list.appendChild(frag);

      pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
      btnPrev.disabled = currentPage <= 1;
      btnNext.disabled = currentPage >= totalPages;
    }

    // ── Events ──
    search?.addEventListener('input', e => {
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

    btnMark?.addEventListener('click', NotifStore.markAllRead);
    btnClear?.addEventListener('click', () => {
      if (confirm('Clear all notifications? This cannot be undone.')) NotifStore.clearAll();
    });

    btnPrev?.addEventListener('click', () => { currentPage--; renderBoard(fullList); });
    btnNext?.addEventListener('click', () => { currentPage++; renderBoard(fullList); });

    // ── Subscribe to store ──
    NotifStore.subscribe(list => {
      fullList = list;
      renderBoard(fullList);
    });
  }

  return { init };
})();


/* ═══════════════════════════════════════════════════════════
   POLLER  (checks for new notifications every 30 s, shows toasts)
═══════════════════════════════════════════════════════════ */
const NotifPoller = (() => {
  async function poll() {
    const fresh = await NotifStore.fetch();
    const newItems = NotifStore.getNew(fresh);

    // Show toast for each new notification (max 3 at once to avoid spam)
    newItems.slice(0, 3).forEach(n => NotifToast.show(n));
    NotifStore.markSeen(fresh);
  }

  function init() {
    // On first load: seed seen IDs without toasting
    NotifStore.fetch().then(list => NotifStore.markSeen(list));
    // Then poll every 30 s
    setInterval(poll, 30_000);
  }

  return { init };
})();


/* ═══════════════════════════════════════════════════════════
   AUTO-DISMISS DJANGO TOASTS
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
   BOOT
═══════════════════════════════════════════════════════════ */
function boot() {
  NotifPanel.init();   // slide-in panel — all pages
  NotifBoard.init();   // full board    — board page only
  NotifPoller.init();  // polling + toasts — all pages
  initDjangoMessages();

  // Expose globally for manual use e.g. NotifToast.show({...})
  window.NotifToast = NotifToast;
  window.NotifStore = NotifStore;
  window.NotifPanel = NotifPanel;
}

document.readyState === 'loading'
  ? document.addEventListener('DOMContentLoaded', boot)
  : boot();
// ```

// ---

// ### 📁 File placement
// ```
// your_project/
// ├── templates/
// │   └── notifications/
// │       └── notification_board.html      ← full board page
// ├── static/
// │   ├── css/dashboards/
// │   │   ├── notification.css             ← unchanged (panel styles)
// │   │   └── notification_board.css       ← NEW (board + toast styles)
// │   └── js/
// │       └── notifications.js             ← NEW unified JS