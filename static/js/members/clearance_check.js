/**
 * members/clearance_check.js
 * ──────────────────────────
 * Intercepts the clearance-check form submit, sends it via postForm() (from
 * members.js) with the CSRF token attached, and renders the JSON response
 * inside #clearanceResult.
 *
 * Expected JSON shape from views.clearance_check:
 * {
 *   success: bool,
 *   message: string,          // only when success=false
 *   data: {
 *     member_id, full_name, email, phone, department,
 *     role, status, clearance_status,
 *     pending_books, pending_fines, is_cleared, clearance_date
 *   }
 * }
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  const form      = document.getElementById('clearanceCheckForm');
  const resultBox = document.getElementById('clearanceResult');
  const submitBtn = form?.querySelector('button[type="submit"]');

  if (!form || !resultBox) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Loading state
    if (submitBtn) {
      submitBtn.disabled  = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking…';
    }
    resultBox.innerHTML = '';

    postForm(form.action, new FormData(form))
      .then((resp) => {
        if (!resp.ok) throw new Error('Server error: ' + resp.status);
        return resp.json();
      })
      .then((data) => renderResult(data))
      .catch((err) => {
        resultBox.innerHTML =
          `<div class="result-not-found" style="color:#ef4444;padding:1rem;">
             <i class="fas fa-exclamation-circle"></i> Error: ${err.message}
           </div>`;
      })
      .finally(() => {
        if (submitBtn) {
          submitBtn.disabled  = false;
          submitBtn.innerHTML = '<i class="fas fa-search"></i> Check Status';
        }
      });
  });


  // ── Result renderer ─────────────────────────────────────────────────────────

  function renderResult(data) {
    if (!data.success) {
      resultBox.innerHTML =
        `<div class="result-not-found" style="
            display:flex;align-items:center;gap:.75rem;
            background:#fff;border:1px solid #e5e7eb;border-radius:12px;
            padding:1.5rem;color:#6b7280;font-size:1rem;margin-top:1rem;">
           <i class="fas fa-user-times" style="font-size:1.5rem;color:#ef4444"></i>
           <span>${data.message || 'Member not found.'}</span>
         </div>`;
      return;
    }

    const d           = data.data;
    const isCleared   = Boolean(d.is_cleared);
    const statusColor = isCleared ? '#10b981' : '#f59e0b';
    const statusIcon  = isCleared ? 'fa-check-circle' : 'fa-clock';
    const statusLabel = isCleared ? 'CLEARED' : 'PENDING';

    const pendingHtml = isCleared
      ? `<div class="result-row" style="color:#10b981;">
           <i class="fas fa-check-circle"></i>
           <strong>Cleared on:</strong> ${d.clearance_date || 'N/A'}
         </div>`
      : `<div class="result-row pending-details">
           <span><i class="fas fa-book" style="color:#ef4444"></i>
             <strong>Pending Books:</strong> ${d.pending_books}</span>
           <span style="margin:0 .5rem">|</span>
           <span><i class="fas fa-rupee-sign" style="color:#f59e0b"></i>
             <strong>Pending Fines:</strong> ₹${Number(d.pending_fines).toFixed(2)}</span>
         </div>`;

    resultBox.innerHTML = `
      <div class="result-card" style="
          background:#fff;border-radius:12px;padding:1.5rem;margin-top:1rem;
          box-shadow:0 2px 8px rgba(0,0,0,.08);
          border-left:5px solid ${statusColor};">

        <div class="result-header" style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;flex-wrap:wrap;gap:.75rem;">
          <div class="result-member-info">
            <h3 style="margin:0;font-size:1.25rem;font-weight:700;color:#1f2937;">${escHtml(d.full_name)}</h3>
            <span style="font-size:.85rem;color:#6b7280;font-family:monospace">${escHtml(d.member_id)}</span>
            &nbsp;
            <span style="font-size:.8rem;color:#9ca3af;">${escHtml(d.role || '')}</span>
          </div>
          <span style="
              background:${statusColor};color:white;padding:4px 16px;
              border-radius:20px;font-size:.85rem;font-weight:700;
              display:inline-flex;align-items:center;gap:.4rem;">
            <i class="fas ${statusIcon}"></i> ${statusLabel}
          </span>
        </div>

        <div class="result-details" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.5rem .75rem;">
          <div class="result-row"><strong>Email:</strong> ${escHtml(d.email || '—')}</div>
          <div class="result-row"><strong>Phone:</strong> ${escHtml(d.phone || '—')}</div>
          <div class="result-row"><strong>Department:</strong> ${escHtml(d.department || 'N/A')}</div>
          <div class="result-row"><strong>Member Status:</strong>
            <span class="status-badge ${escHtml(d.status)}" style="margin-left:.3rem">
              <i class="fas fa-circle"></i> ${escHtml(d.status)}
            </span>
          </div>
          ${pendingHtml}
        </div>

        ${!isCleared ? `
        <div style="margin-top:1.25rem;display:flex;gap:.75rem;flex-wrap:wrap;">
          <a href="/members/${escHtml(String(d.member_id))}" class="btn btn-secondary" style="font-size:.85rem;">
            <i class="fas fa-eye"></i> View Profile
          </a>
        </div>` : `
        <div style="margin-top:1.25rem;display:flex;gap:.75rem;flex-wrap:wrap;">
          <a href="/members/${escHtml(String(d.member_id))}" class="btn btn-secondary" style="font-size:.85rem;">
            <i class="fas fa-eye"></i> View Profile
          </a>
        </div>`}

      </div>`;
  }


  // ── Utility: escape HTML to prevent XSS in server data ──────────────────────

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

});
