/**
 * Admin Dashboard JavaScript
 * Handles: sidebar toggle, stat animations, tooltips, charts,
 *          quick-action clicks, notification panel.
 */

document.addEventListener('DOMContentLoaded', function () {

  initMobileSidebar();
  animateStats();
  initTooltips();
  initCharts();
  initQuickActions();
  initNotifications();

});

// ===========================
// Mobile Sidebar Toggle
// ===========================
function initMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;

  if (window.innerWidth <= 968) {
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'mobile-sidebar-toggle';
    toggleBtn.innerHTML   = '☰';
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

    document.addEventListener('click', function (e) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }
}

// ===========================
// Animate Stats on Load
// ===========================
function animateStats() {
  // Target both admin-style .stat-value and members-style h3 inside .stat-body
  const statEls = document.querySelectorAll('.stat-value, .stat-body h3');

  statEls.forEach(function (el) {
    const raw = el.textContent.trim().replace(/,/g, '');
    const finalValue = parseInt(raw, 10);
    if (isNaN(finalValue) || finalValue === 0) return;

    const steps     = 50;
    const stepTime  = Math.round(800 / steps);      // ~800 ms total
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

// ===========================
// Tooltips
// ===========================
function initTooltips() {
  document.querySelectorAll('[title]').forEach(function (el) {
    let tooltip = null;

    el.addEventListener('mouseenter', function () {
      const title = this.getAttribute('title');
      if (!title) return;

      // Temporarily clear title so the browser default doesn't double-show
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

      // Position after render so we have dimensions
      requestAnimationFrame(function () {
        const rect = el.getBoundingClientRect();
        tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top  = (rect.top  - tooltip.offsetHeight - 8) + 'px';
        tooltip.style.opacity = '1';
      });
    });

    el.addEventListener('mouseleave', function () {
      // Restore title
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

// ===========================
// Charts
// ===========================
function initCharts() {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded — skipping charts.');
    return;
  }

  const data = window.DASHBOARD_DATA || {};

  // Global defaults
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.color       = '#7a8fa9';

  const tooltipDefaults = {
    backgroundColor: '#0a1628',
    titleColor:      '#e8f0f8',
    bodyColor:       '#b8cee0',
    padding:         12,
    cornerRadius:    8,
    displayColors:   true,
  };

  // ── 1. Monthly Loans — Line Chart ────────────────────────────
  if (data.loansChart && data.loansChart.enabled) {
    const ctx = document.getElementById('loansChart');
    if (ctx) {
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.loansChart.labels,
          datasets: [{
            label:                'Loans',
            data:                 data.loansChart.data,
            borderColor:          '#1a6fd4',
            backgroundColor:      'rgba(26, 111, 212, 0.08)',
            borderWidth:          2.5,
            pointBackgroundColor: '#1a6fd4',
            pointRadius:          5,
            pointHoverRadius:     7,
            fill:                 true,
            tension:              0.4,
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend:  { display: false },
            tooltip: tooltipDefaults,
          },
          scales: {
            x: {
              grid:   { color: 'rgba(216,226,239,0.4)' },
              border: { dash: [4, 4] },
            },
            y: {
              grid:         { color: 'rgba(216,226,239,0.4)' },
              border:       { dash: [4, 4] },
              beginAtZero:  true,
              ticks:        { precision: 0 },
            },
          }
        }
      });
    }
  }

  // ── 2. Books by Category — Doughnut Chart ────────────────────
  if (data.categoryChart && data.categoryChart.enabled) {
    const ctx = document.getElementById('categoryChart');
    if (ctx) {
      new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: data.categoryChart.labels,
          datasets: [{
            data:            data.categoryChart.data,
            backgroundColor: ['#1a6fd4','#10b981','#8b5cf6','#f59e0b','#ef4444','#60b4ff','#f093fb','#30cfd0'],
            borderWidth:     2,
            borderColor:     '#ffffff',
            hoverOffset:     8,
          }]
        },
        options: {
          responsive: true,
          cutout: '68%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding:         16,
                usePointStyle:   true,
                pointStyleWidth: 10,
                font:            { size: 12 },
              }
            },
            tooltip: tooltipDefaults,
          }
        }
      });
    }
  }

  // ── 3. New Members — Bar Chart ───────────────────────────────
  if (data.membersChart && data.membersChart.enabled) {
    const ctx = document.getElementById('membersChart');
    if (ctx) {
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.membersChart.labels,
          datasets: [{
            label:                'New Members',
            data:                 data.membersChart.data,
            backgroundColor:      'rgba(96, 180, 255, 0.18)',
            borderColor:          '#60b4ff',
            borderWidth:          2,
            borderRadius:         6,
            hoverBackgroundColor: 'rgba(26, 111, 212, 0.25)',
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend:  { display: false },
            tooltip: tooltipDefaults,
          },
          scales: {
            x: { grid: { display: false } },
            y: {
              grid:        { color: 'rgba(216,226,239,0.4)' },
              border:      { dash: [4, 4] },
              beginAtZero: true,
              ticks:       { precision: 0 },
            },
          }
        }
      });
    }
  }
}

// ===========================
// Quick Action Handlers
// ===========================
function initQuickActions() {
  document.querySelectorAll('.action-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      // If the button is an <a> with a real href, let it navigate naturally.
      const href = this.getAttribute('href');
      if (href && href !== '#') return;

      // Fallback for placeholder buttons
      e.preventDefault();
      const labelEl = this.querySelector('.action-text');
      const label   = labelEl ? labelEl.textContent.trim() : 'Action';
      console.log('Quick action clicked:', label);
      // Wire up custom logic per action here, e.g.:
      // if (label === 'Generate Report') openReportModal();
    });
  });
}

// ===========================
// Notification Handler
// ===========================
function initNotifications() {
  const btn = document.querySelector('.btn-icon[title="Notifications"]');
  if (!btn) return;

  btn.addEventListener('click', function () {
    console.log('Notifications clicked');
    // Add notification panel / dropdown logic here
  });
}