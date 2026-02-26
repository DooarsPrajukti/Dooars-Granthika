/**
 * members/member_detail.js
 * ────────────────────────
 * Member detail page specific JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * NOTE: sendReminder(), markCleared(), reactivateMember() are defined inline
 * in the member_detail.html template (they need Django URL tags).
 * This file handles UI concerns that don't need URL reversal.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── Delete member (wired by members.js, but we can add a toast override) ──
  // initMemberDelete() is already called by members.js on DOMContentLoaded.
  // No duplicate wiring needed.

  // ── Copy member ID to clipboard on click ─────────────────────────────────
  const memberIdEl = document.querySelector('.value-mono');
  if (memberIdEl) {
    memberIdEl.style.cursor = 'pointer';
    memberIdEl.title = 'Click to copy';
    memberIdEl.addEventListener('click', () => {
      const text = memberIdEl.textContent.trim();
      navigator.clipboard?.writeText(text)
        .then(() => showToast('Member ID copied!', 'info'))
        .catch(() => showToast('Could not copy.', 'error'));
    });
  }

  // ── Transaction table: highlight overdue rows ─────────────────────────────
  document.querySelectorAll('.members-table tbody tr').forEach((row) => {
    const statusBadge = row.querySelector('.status-badge');
    if (statusBadge && statusBadge.textContent.trim().toLowerCase().includes('overdue')) {
      row.style.background = '#fff7ed';
    }
  });

  // ── Smooth-scroll to transactions section ────────────────────────────────
  const txLink = document.querySelector('a[href="#transactions"]');
  if (txLink) {
    txLink.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelector('.members-table-container')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

});
