/**
 * members/pending_clearance.js
 * ────────────────────────────
 * Pending clearance page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * Provides:
 *   - sendReminder(memberId)  — POST to /members/<id>/send-reminder/
 *   - markCleared(memberId)   — POST to /members/<id>/mark-cleared/
 *
 * Both use postAction() from members.js (CSRF token attached automatically).
 */

'use strict';

/**
 * Send a reminder notification to a member.
 * @param {number} memberId
 */
function sendReminder(memberId) {
  const url = `/members/${memberId}/send-reminder/`;
  const btn = document.querySelector(`[onclick="sendReminder(${memberId})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  postAction(url)
    .then((resp) => {
      if (!resp.ok) throw new Error('Server error ' + resp.status);
      return resp.json();
    })
    .then((data) => {
      showToast(data.message || 'Reminder sent!', 'success');
    })
    .catch((err) => {
      console.error('sendReminder error:', err);
      showToast('Failed to send reminder. Please try again.', 'error');
    })
    .finally(() => {
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-bell"></i>';
      }
    });
}

/**
 * Mark a member as cleared.
 * Reloads the page on success so they disappear from the pending list.
 * @param {number} memberId
 */
function markCleared(memberId) {
  if (!confirm('Mark this member as cleared?\nEnsure all books are returned and fines paid.')) return;

  const url = `/members/${memberId}/mark-cleared/`;
  const btn = document.querySelector(`[onclick="markCleared(${memberId})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  postAction(url)
    .then((resp) => {
      // View redirects to member_detail on success — treat redirect as OK
      if (resp.ok || resp.redirected) {
        showToast('Member marked as cleared!', 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        return resp.text().then((t) => {
          throw new Error(t || 'Server error ' + resp.status);
        });
      }
    })
    .catch((err) => {
      console.error('markCleared error:', err);
      showToast('Could not clear member — check pending items.', 'error');
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-check"></i>';
      }
    });
}

window.sendReminder = sendReminder;
window.markCleared  = markCleared;


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

  // ── Highlight high-priority pending rows ──────────────────────────────────
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    const daysEl = row.querySelector('.days-high');
    if (daysEl) row.style.background = '#fff7ed';
  });

});
