/* ============================================================
   transaction_detail.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Toast Notification ── */
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      padding: '12px 20px',
      borderRadius: '10px',
      fontFamily: "'DM Sans', sans-serif",
      fontSize: '13.5px',
      fontWeight: '500',
      color: '#fff',
      background: type === 'success' ? '#16a34a' : type === 'error' ? '#b91c1c' : '#2563eb',
      boxShadow: '0 8px 24px rgba(15,34,64,.2)',
      zIndex: '9999',
      opacity: '0',
      transform: 'translateY(12px)',
      transition: 'opacity .2s ease, transform .2s ease',
    });
    document.body.appendChild(toast);
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    });
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      setTimeout(() => toast.remove(), 250);
    }, 3000);
  }

  /* ── CSRF helper ── */
  function getCsrf() {
    const meta = document.querySelector('[name=csrfmiddlewaretoken]');
    return meta ? meta.value : '';
  }

  /* ── Pay the Fine anchor links: confirm before navigating ── */
  document.querySelectorAll('.action-btn--pay, .btn--primary.btn--block').forEach(function (el) {
    // Only intercept <a> elements (not disabled)
    if (el.tagName !== 'A') return;
    if (el.getAttribute('aria-disabled') === 'true') return;

    el.addEventListener('click', function (e) {
      if (!confirm('Proceed to payment for this fine?')) {
        e.preventDefault();
      }
    });
  });

  /* ── Waive fine: confirm before submit ── */
  document.querySelectorAll('.action-btn--waive').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (!confirm('Are you sure you want to waive this fine? This cannot be undone.')) {
        e.preventDefault();
      }
    });
  });

  /* ── Print cleanup ── */
  window.addEventListener('beforeprint', () => {
    document.querySelectorAll('.page-header__actions, .info-card__link').forEach(el => {
      el.style.display = 'none';
    });
  });
  window.addEventListener('afterprint', () => {
    document.querySelectorAll('.page-header__actions, .info-card__link').forEach(el => {
      el.style.display = '';
    });
  });

  /* ── Animate timeline steps ── */
  const steps = document.querySelectorAll('.timeline-step');
  steps.forEach((step, i) => {
    step.style.opacity = '0';
    step.style.transform = 'translateX(-10px)';
    step.style.transition = `opacity .25s ease ${i * 120}ms, transform .25s ease ${i * 120}ms`;
    requestAnimationFrame(() => {
      step.style.opacity = '1';
      step.style.transform = 'translateX(0)';
    });
  });

  /* ── Animate info cards ── */
  const cards = document.querySelectorAll('.info-card, .timeline-card, .fine-card');
  cards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(14px)';
    card.style.transition = `opacity .3s ease ${i * 80}ms, transform .3s ease ${i * 80}ms`;
    requestAnimationFrame(() => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    });
  });

  /* ── Table row hover highlight ── */
  document.querySelectorAll('.table-row').forEach(row => {
    row.addEventListener('mouseenter', () => row.classList.add('table-row--hovered'));
    row.addEventListener('mouseleave', () => row.classList.remove('table-row--hovered'));
  });

})();