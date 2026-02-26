/**
 * members/members.js
 * ──────────────────
 * Shared utilities loaded on EVERY members page.
 *
 * Provides:
 *   - CSRF helpers:   getCsrfToken(), postJSON(), postForm(), postAction()
 *   - Toast:          showToast(message, type)
 *   - Table search:   live client-side row filter on #memberSearch → #membersTable
 *   - Filter reset:   #resetFilters button
 *   - Delete member:  .delete-member-btn data-delete-url / data-member-name
 *
 * All POST helpers attach X-CSRFToken automatically — never use raw fetch()
 * for state-changing requests.
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
// 1. CSRF HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Read Django's csrftoken cookie.
 * Falls back to the hidden {% csrf_token %} input if the cookie is absent.
 * @returns {string}
 */
function getCsrfToken() {
  const name = 'csrftoken';
  for (let c of document.cookie.split(';')) {
    c = c.trim();
    if (c.startsWith(name + '=')) {
      return decodeURIComponent(c.slice(name.length + 1));
    }
  }
  const el = document.querySelector('[name=csrfmiddlewaretoken]');
  return el ? el.value : '';
}

/**
 * POST JSON data. Attaches X-CSRFToken header automatically.
 * @param {string} url
 * @param {object} [body={}]
 * @returns {Promise<Response>}
 */
function postJSON(url, body = {}) {
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify(body),
  });
}

/**
 * POST a FormData object (supports file uploads).
 * Do NOT manually set Content-Type — browser sets multipart boundary.
 * @param {string}   url
 * @param {FormData} formData
 * @returns {Promise<Response>}
 */
function postForm(url, formData) {
  return fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData,
  });
}

/**
 * POST an empty body — for single-action endpoints (reactivate, mark-cleared, etc.)
 * @param {string} url
 * @returns {Promise<Response>}
 */
function postAction(url) {
  return postForm(url, new FormData());
}

window.getCsrfToken = getCsrfToken;
window.postJSON     = postJSON;
window.postForm     = postForm;
window.postAction   = postAction;


// ═══════════════════════════════════════════════════════════════════════════════
// 2. TOAST NOTIFICATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Display a brief toast at the top-right corner.
 * @param {string} message
 * @param {'success'|'error'|'info'|'warning'} [type='success']
 */
function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    Object.assign(container.style, {
      position: 'fixed', top: '1.5rem', right: '1.5rem',
      zIndex: '9999', display: 'flex', flexDirection: 'column', gap: '.5rem',
    });
    document.body.appendChild(container);
  }

  const palette = {
    success: '#10b981',
    error:   '#ef4444',
    info:    '#3b82f6',
    warning: '#f59e0b',
  };

  const toast = document.createElement('div');
  const icons = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
  Object.assign(toast.style, {
    background:    palette[type] || palette.info,
    color:         'white',
    padding:       '.75rem 1.25rem',
    borderRadius:  '8px',
    fontSize:      '.9rem',
    boxShadow:     '0 4px 12px rgba(0,0,0,.18)',
    opacity:       '0',
    transition:    'opacity .3s',
    maxWidth:      '340px',
    display:       'flex',
    alignItems:    'center',
    gap:           '.5rem',
  });
  toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i> ${message}`;
  container.appendChild(toast);

  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

window.showToast = showToast;


// ═══════════════════════════════════════════════════════════════════════════════
// 3. AUTO-DISMISS DJANGO FLASH MESSAGES
// ═══════════════════════════════════════════════════════════════════════════════

function autoDismissMessages() {
  document.querySelectorAll('.message').forEach((msg) => {
    setTimeout(() => {
      msg.style.transition = 'opacity .3s';
      msg.style.opacity = '0';
      setTimeout(() => msg.remove(), 300);
    }, 5000);
  });
}


// ═══════════════════════════════════════════════════════════════════════════════
// 4. CLIENT-SIDE TABLE SEARCH
// ═══════════════════════════════════════════════════════════════════════════════

function initTableSearch() {
  const searchInput = document.getElementById('memberSearch');
  const table       = document.getElementById('membersTable');
  if (!searchInput || !table) return;

  searchInput.addEventListener('input', function () {
    const q = this.value.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach((row) => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}


// ═══════════════════════════════════════════════════════════════════════════════
// 5. FILTER RESET
// ═══════════════════════════════════════════════════════════════════════════════

function initFilterReset() {
  const resetBtn = document.getElementById('resetFilters');
  if (!resetBtn) return;

  resetBtn.addEventListener('click', () => {
    const form = document.getElementById('filterForm');
    if (form) form.reset();
    window.location.href = window.location.pathname;
  });
}


// ═══════════════════════════════════════════════════════════════════════════════
// 6. TABLE COLUMN SORT (client-side, click column header)
// ═══════════════════════════════════════════════════════════════════════════════

function initTableSort(tableId) {
  const table = document.getElementById(tableId || 'membersTable');
  if (!table) return;

  table.querySelectorAll('th[data-sortable]').forEach((th, colIdx) => {
    th.style.cursor = 'pointer';
    th.dataset.dir  = 'asc';

    th.addEventListener('click', function () {
      const dir = this.dataset.dir === 'asc' ? 1 : -1;
      this.dataset.dir = dir === 1 ? 'desc' : 'asc';

      // Update sort icon
      table.querySelectorAll('th[data-sortable]').forEach((h) => {
        h.querySelector('.sort-icon')?.remove();
      });
      const icon = document.createElement('i');
      icon.className = `fas fa-sort-${dir === 1 ? 'up' : 'down'} sort-icon`;
      icon.style.marginLeft = '.4rem';
      this.appendChild(icon);

      const tbody = table.querySelector('tbody');
      const rows  = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {
        const aText = (a.cells[colIdx]?.textContent || '').trim().toLowerCase();
        const bText = (b.cells[colIdx]?.textContent || '').trim().toLowerCase();
        return aText < bText ? -dir : aText > bText ? dir : 0;
      });
      rows.forEach((r) => tbody.appendChild(r));
    });
  });
}

window.initTableSort = initTableSort;


// ═══════════════════════════════════════════════════════════════════════════════
// 7. DELETE MEMBER  (.delete-member-btn)
// ═══════════════════════════════════════════════════════════════════════════════

function initMemberDelete() {
  document.querySelectorAll('.delete-member-btn').forEach((btn) => {
    btn.addEventListener('click', function () {
      const name      = this.dataset.memberName || 'this member';
      const deleteUrl = this.dataset.deleteUrl;
      if (!deleteUrl) return;

      if (!confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) return;

      postAction(deleteUrl)
        .then((resp) => {
          if (resp.ok || resp.redirected) {
            showToast(`${name} deleted.`, 'success');
            setTimeout(() => { window.location.href = '/members/'; }, 800);
          } else {
            throw new Error('Server error ' + resp.status);
          }
        })
        .catch((err) => {
          console.error('Delete failed:', err);
          showToast('Delete failed. Please try again.', 'error');
        });
    });
  });
}

window.initMemberDelete = initMemberDelete;


// ═══════════════════════════════════════════════════════════════════════════════
// 8. SELECT-OR-CREATE  (dept / course / year / semester on add/edit forms)
//    When a "new_*" text input is filled, clear the corresponding select.
//    When the select changes, clear the "new_*" input.
// ═══════════════════════════════════════════════════════════════════════════════

function initSelectOrCreate() {
  const pairs = [
    { selectId: 'department',        newId: 'new_department'        },
    { selectId: 'department_teacher', newId: 'new_department_teacher' },
    { selectId: 'course',            newId: 'new_course'            },
    { selectId: 'year',              newId: 'new_year'              },
    { selectId: 'semester',          newId: 'new_semester'          },
  ];

  pairs.forEach(({ selectId, newId }) => {
    const sel   = document.getElementById(selectId);
    const input = document.getElementById(newId);
    if (!sel || !input) return;

    // Typing in the "create new" field → deselect dropdown
    input.addEventListener('input', () => {
      if (input.value.trim()) sel.value = '';
    });

    // Choosing from dropdown → clear the "create new" field
    sel.addEventListener('change', () => {
      if (sel.value) input.value = '';
    });
  });
}

window.initSelectOrCreate = initSelectOrCreate;


// ═══════════════════════════════════════════════════════════════════════════════
// 9. PHONE FIELD VALIDATION HELPER
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Wire digit-only filtering + 10-digit validation for phone inputs.
 * @param {Array<{id:string, required:boolean}>} fields
 */
function initPhoneValidation(fields) {
  fields.forEach(({ id, required }) => {
    const el = document.getElementById(id);
    if (!el) return;

    el.addEventListener('input', (e) => {
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10);
      e.target.setCustomValidity('');
      clearFieldError(e.target);
    });

    el.addEventListener('blur', (e) => {
      const v = e.target.value;
      if (v === '' && !required) { clearFieldError(e.target); return; }
      if (v.length > 0 && v.length !== 10) {
        setFieldError(e.target, 'Phone number must be exactly 10 digits.');
      } else {
        clearFieldError(e.target);
      }
    });

    el.addEventListener('invalid', (e) => {
      e.preventDefault();
      const v = e.target.value;
      setFieldError(e.target, v === '' && required
        ? 'This field is required.'
        : 'Phone number must be exactly 10 digits.');
    });
  });
}

window.initPhoneValidation = initPhoneValidation;


// ═══════════════════════════════════════════════════════════════════════════════
// 10. EMAIL VALIDATION HELPER
// ═══════════════════════════════════════════════════════════════════════════════

function initEmailValidation(inputId) {
  const el = document.getElementById(inputId || 'email');
  if (!el) return;

  el.addEventListener('blur', (e) => {
    const v = e.target.value.trim();
    if (v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
      setFieldError(e.target, 'Please enter a valid email address.');
    } else {
      clearFieldError(e.target);
    }
  });
}

window.initEmailValidation = initEmailValidation;


// ═══════════════════════════════════════════════════════════════════════════════
// 11. FIELD ERROR HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function setFieldError(input, message) {
  input.style.borderColor = '#ef4444';
  input.setCustomValidity(message);
  let errEl = input.closest('.form-group')?.querySelector('.error-message');
  if (!errEl) {
    errEl = document.createElement('span');
    errEl.className = 'error-message';
    input.closest('.form-group')?.appendChild(errEl);
  }
  errEl.textContent = message;
}

function clearFieldError(input) {
  input.style.borderColor = '';
  input.setCustomValidity('');
  const errEl = input.closest('.form-group')?.querySelector('.error-message');
  if (errEl) errEl.textContent = '';
}

window.setFieldError   = setFieldError;
window.clearFieldError = clearFieldError;


// ═══════════════════════════════════════════════════════════════════════════════
// 12. DOM READY — wire up shared behaviours present on every page
// ═══════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  autoDismissMessages();
  initTableSearch();
  initFilterReset();
  initTableSort();
  initMemberDelete();
});
