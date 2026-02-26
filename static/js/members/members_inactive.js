/**
 * members/members_inactive.js
 * ───────────────────────────
 * Inactive members page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * Provides:
 *   - reactivateMember(memberId) — POST to /members/<id>/reactivate/
 *
 * members.js handles: search, table sort, filter reset, delete.
 */

'use strict';

/**
 * Reactivate an inactive member.
 * Uses postAction() from members.js (attaches CSRF token automatically).
 * @param {number} memberId
 */
function reactivateMember(memberId) {
  if (!confirm('Reactivate this member? Their status will be changed to Active.')) return;

  const url = `/members/${memberId}/reactivate/`;
  const btn = document.querySelector(`[onclick="reactivateMember(${memberId})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  postAction(url)
    .then((resp) => {
      if (resp.ok || resp.redirected) {
        showToast('Member reactivated successfully!', 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        throw new Error('Server error ' + resp.status);
      }
    })
    .catch((err) => {
      console.error('reactivateMember error:', err);
      showToast('Failed to reactivate member. Please try again.', 'error');
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-redo"></i>';
      }
    });
}

window.reactivateMember = reactivateMember;


document.addEventListener('DOMContentLoaded', () => {

  // ── Row click → detail page ───────────────────────────────────────────────
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      if (e.target.closest('.table-actions')) return;
      const viewLink = row.querySelector('.action-icon.view');
      if (viewLink) window.location.href = viewLink.href;
    });
  });

});
