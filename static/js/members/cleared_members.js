/**
 * members/cleared_members.js
 * ──────────────────────────
 * Cleared members page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * Provides:
 *   - downloadClearanceCertificate(memberId) – triggers PDF download
 *   - Inline search + table sort (handled by members.js)
 */

'use strict';

/**
 * Download the clearance certificate PDF for a member.
 * The endpoint is a GET request — no CSRF token required.
 * @param {number} memberId
 */
function downloadClearanceCertificate(memberId) {
  const url = `/members/${memberId}/clearance-certificate/`;
  const btn = document.querySelector(`[onclick="downloadClearanceCertificate(${memberId})"]`);

  // Visual loading feedback
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  fetch(url, { method: 'GET' })
    .then((resp) => {
      if (!resp.ok) throw new Error(`Could not generate certificate (status ${resp.status}).`);
      return resp.blob();
    })
    .then((blob) => {
      // Detect content type — server sends application/pdf
      const mimeType = blob.type || 'application/pdf';
      const objectUrl = URL.createObjectURL(new Blob([blob], { type: mimeType }));
      const a = document.createElement('a');
      a.href     = objectUrl;
      a.download = `clearance_certificate_${memberId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
      showToast('Certificate downloaded!', 'success');
    })
    .catch((err) => {
      console.error('downloadClearanceCertificate error:', err);
      showToast('Failed to download certificate. Please try again.', 'error');
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-download"></i>';
      }
    });
}

window.downloadClearanceCertificate = downloadClearanceCertificate;


// ── Page initialisation ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Table search, sort, and filter reset are handled by members.js.
  // Nothing extra needed for this page.
});
