/**
 * members/members_passout.js
 * ──────────────────────────
 * Pass-out members page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * members.js handles: search, table sort, filter reset.
 */

'use strict';

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

  // ── Highlight members with pending clearance ──────────────────────────────
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    const clearanceBadge = row.querySelector('.status-badge.pending');
    if (clearanceBadge) {
      row.style.borderLeft = '3px solid #f59e0b';
    }
  });

});
