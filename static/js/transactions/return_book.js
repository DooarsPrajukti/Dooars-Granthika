/* ============================================================
   return_book.js
   ============================================================ */

(function () {
  'use strict';

  const CIRCUMFERENCE = 213.63; // 2π × r34

  /* ── DOM refs ── */
  const conditionOptions  = document.getElementById('conditionOptions');
  const damageChargeGroup = document.getElementById('damageChargeGroup');
  const damageChargeInput = document.getElementById('damageCharge');
  const totalFineDisplay  = document.getElementById('totalFineDisplay');
  const damageFineRow     = document.getElementById('damageFineRow');
  const damageFineDisplay = document.getElementById('damageFineDisplay');
  const fineConfirmPanel  = document.getElementById('fineConfirmPanel');
  const finePaidNow       = document.getElementById('finePaidNow');
  const returnForm        = document.getElementById('returnForm');
  const confirmBtn        = document.getElementById('confirmReturnBtn');

  /* Baseline overdue fine — read once from the DOM so damage additions stack on top */
  const baseFine = parseFloat(
    totalFineDisplay?.textContent?.replace('₹', '').trim() || '0'
  );

  /* ── Condition selector ── */
  if (conditionOptions) {
    conditionOptions.addEventListener('change', function (e) {
      if (e.target.type !== 'radio') return;
      const isDamaged = e.target.value === 'damaged';

      if (damageChargeGroup) {
        damageChargeGroup.hidden = !isDamaged;
      }

      if (!isDamaged && damageChargeInput) {
        damageChargeInput.value = '';
      }

      recalcTotal();
    });
  }

  /* ── Damage charge live recalc ── */
  if (damageChargeInput) {
    damageChargeInput.addEventListener('input', recalcTotal);
  }

  function recalcTotal() {
    const extra = Math.max(0, parseFloat(damageChargeInput?.value) || 0);
    const total = baseFine + extra;

    if (totalFineDisplay) {
      totalFineDisplay.textContent = `₹${total.toFixed(2)}`;
    }

    /* Show/hide damage row in fine breakdown */
    if (damageFineRow) {
      damageFineRow.style.display = extra > 0 ? '' : 'none';
    }
    if (damageFineDisplay) {
      damageFineDisplay.textContent = `₹${extra.toFixed(2)}`;
    }

    /* Update sidebar meter to reflect new total */
    animateMeter(total);
  }

  /* ── Fine meter ring animation ── */
  function animateMeter(overrideAmount) {
    const ring = document.querySelector('.fine-meter__ring');
    const fill = document.querySelector('.fine-meter__fill');
    if (!ring || !fill) return;

    /* Max represented amount for 100% fill — same as Python view: ₹500 */
    const MAX_FINE = 500;
    const amount = overrideAmount !== undefined
      ? overrideAmount
      : parseFloat(ring.dataset.pct || '0') * MAX_FINE / 100;

    const pct    = Math.min(100, (amount / MAX_FINE) * 100);
    const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;

    fill.style.transition     = 'stroke-dashoffset 0.6s ease';
    fill.style.strokeDashoffset = offset; // SVG attribute — no 'px' unit
  }

  /* Trigger initial animation after a short delay so CSS transition fires */
  setTimeout(() => animateMeter(), 200);

  /* ── Form submit guard ── */
  if (returnForm) {
    returnForm.addEventListener('submit', function (e) {
      const hasFine = fineConfirmPanel !== null;

      if (hasFine && !finePaidNow?.checked) {
        const proceed = confirm(
          'The fine has not been marked as collected. Continue without collecting the fine?'
        );
        if (!proceed) {
          e.preventDefault();
          return;
        }
      }

      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `
          <svg viewBox="0 0 20 20" fill="none"
               style="width:15px;height:15px;animation:spin .7s linear infinite;vertical-align:middle">
            <path d="M10 2a8 8 0 1 1-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg> Processing…`;
      }
    });
  }

})();