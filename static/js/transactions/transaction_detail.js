/* ============================================================
   transaction_detail.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Mark Fine as Paid ── */
  const markFinePaidBtn = document.getElementById('markFinePaidBtn');
  if (markFinePaidBtn) {
    markFinePaidBtn.addEventListener('click', function () {
      const txnId = this.dataset.id;
      if (!confirm('Confirm that the fine has been collected?')) return;

      this.disabled = true;
      this.innerHTML = '<svg viewBox="0 0 20 20" fill="none" style="width:15px;height:15px;animation:spin .6s linear infinite"><path d="M10 2a8 8 0 1 1-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Processing…';

      fetch(`/transactions/${txnId}/mark-fine-paid/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrf(),
          'Content-Type': 'application/json',
        },
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            showToast('Fine marked as paid successfully.', 'success');
            setTimeout(() => window.location.reload(), 1000);
          } else {
            showToast(data.error || 'Something went wrong.', 'error');
            this.disabled = false;
          }
        })
        .catch(() => {
          showToast('Network error. Please try again.', 'error');
          this.disabled = false;
        });
    });
  }

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

})();
