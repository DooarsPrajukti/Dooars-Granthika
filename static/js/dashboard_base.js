/**
 * dashboard_base.js
 * Shared dashboard utilities loaded on EVERY page via dashboard_base.html.
 * Covers: mobile sidebar toggle, stat counter animation,
 *         custom tooltips, notification handler.
 *
 * Does NOT contain any page-specific logic (charts, quick actions, etc.).
 */

document.addEventListener('DOMContentLoaded', function () {
  initMobileSidebar();
  animateStats();
  initTooltips();
  initNotifications();
});

/* ============================================================
   1. Mobile Sidebar Toggle
   Creates a hamburger button on small screens (≤ 968 px)
   and wires up open/close behaviour.
   ============================================================ */
function initMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;

  if (window.innerWidth > 968) return;

  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'mobile-sidebar-toggle';
  toggleBtn.innerHTML = '☰';
  toggleBtn.setAttribute('aria-label', 'Toggle sidebar');
  toggleBtn.style.cssText = `
    position: fixed;
    top: 20px;
    left: 20px;
    z-index: 200;
    width: 44px;
    height: 44px;
    background: var(--ink-accent, #1a6fd4);
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 20px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(26,111,212,0.3);
    transition: opacity 0.2s;
  `;
  document.body.appendChild(toggleBtn);

  toggleBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside
  document.addEventListener('click', function (e) {
    if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

/* ============================================================
   2. Stat Counter Animation
   Animates .stat-value (admin cards) and .stat-body h3
   (members cards) from 0 to their final value on page load.
   ============================================================ */
function animateStats() {
  const statEls = document.querySelectorAll('.stat-value, .stat-body h3');

  statEls.forEach(function (el) {
    const raw        = el.textContent.trim().replace(/,/g, '');
    const finalValue = parseInt(raw, 10);
    if (isNaN(finalValue) || finalValue === 0) return;

    const steps     = 50;
    const stepTime  = Math.round(800 / steps); // ~800 ms total
    const increment = Math.ceil(finalValue / steps);
    let   current   = 0;

    const timer = setInterval(function () {
      current += increment;
      if (current >= finalValue) {
        el.textContent = finalValue.toLocaleString();
        clearInterval(timer);
      } else {
        el.textContent = current.toLocaleString();
      }
    }, stepTime);
  });
}

/* ============================================================
   3. Custom Tooltips
   Replaces native browser title tooltips with styled ones.
   Applies to any element with a [title] attribute.
   ============================================================ */
function initTooltips() {
  document.querySelectorAll('[title]').forEach(function (el) {
    let tooltip = null;

    el.addEventListener('mouseenter', function () {
      const title = this.getAttribute('title');
      if (!title) return;

      // Stash and remove native title so browser doesn't double-show
      this.dataset.titleBak = title;
      this.removeAttribute('title');

      tooltip = document.createElement('div');
      tooltip.className   = 'custom-tooltip';
      tooltip.textContent = title;
      tooltip.style.cssText = `
        position: fixed;
        background: var(--ink-dark, #0a1628);
        color: #e8f0f8;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
        z-index: 9999;
        pointer-events: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        opacity: 0;
        transition: opacity 0.15s ease;
      `;
      document.body.appendChild(tooltip);

      // Position after render so we have real dimensions
      requestAnimationFrame(function () {
        const rect = el.getBoundingClientRect();
        tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top  = (rect.top  - tooltip.offsetHeight - 8) + 'px';
        tooltip.style.opacity = '1';
      });
    });

    el.addEventListener('mouseleave', function () {
      // Restore native title
      if (this.dataset.titleBak) {
        this.setAttribute('title', this.dataset.titleBak);
        delete this.dataset.titleBak;
      }
      if (tooltip) {
        tooltip.remove();
        tooltip = null;
      }
    });
  });
}

/* ============================================================
   4. Notification Handler
   Wires up the bell icon button in the top bar.
   Replace the console.log with a real panel/dropdown later.
   ============================================================ */
function initNotifications() {
  const btn = document.querySelector('.btn-icon[title="Notifications"]');
  if (!btn) return;

  btn.addEventListener('click', function () {
    console.log('Notifications clicked');
    // TODO: open notification panel / dropdown
  });
}