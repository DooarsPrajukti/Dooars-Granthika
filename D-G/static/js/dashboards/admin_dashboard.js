/**
 * Admin Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {

  // Mobile sidebar toggle
  initMobileSidebar();

  // Stats counter animations
  animateStats();

  // Tooltips
  initTooltips();

  // Charts (data injected by Django via window.DASHBOARD_DATA)
  initCharts();

});

// ===========================
// Mobile Sidebar Toggle
// ===========================
function initMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');

  if (window.innerWidth <= 968) {
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'mobile-sidebar-toggle';
    toggleBtn.innerHTML = '☰';
    toggleBtn.style.cssText = `
      position: fixed;
      top: 20px;
      left: 20px;
      z-index: 200;
      width: 44px;
      height: 44px;
      background: var(--ink-accent);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 20px;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(26, 111, 212, 0.3);
    `;

    document.body.appendChild(toggleBtn);

    toggleBtn.addEventListener('click', function () {
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
  const statValues = document.querySelectorAll('.stat-value');

  statValues.forEach(stat => {
    const finalValue = parseInt(stat.textContent) || 0;
    if (finalValue === 0) return;

    let currentValue = 0;
    const increment = Math.ceil(finalValue / 50);
    const stepTime = 1000 / 50;

    const timer = setInterval(() => {
      currentValue += increment;
      if (currentValue >= finalValue) {
        stat.textContent = finalValue;
        clearInterval(timer);
      } else {
        stat.textContent = currentValue;
      }
    }, stepTime);
  });
}

// ===========================
// Tooltips
// ===========================
function initTooltips() {
  const tooltipElements = document.querySelectorAll('[title]');

  tooltipElements.forEach(el => {
    el.addEventListener('mouseenter', function () {
      const title = this.getAttribute('title');
      if (!title) return;

      const tooltip = document.createElement('div');
      tooltip.className = 'custom-tooltip';
      tooltip.textContent = title;
      tooltip.style.cssText = `
        position: absolute;
        background: var(--ink-dark);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
        z-index: 1000;
        pointer-events: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      `;

      document.body.appendChild(tooltip);

      const rect = this.getBoundingClientRect();
      tooltip.style.top  = (rect.top - tooltip.offsetHeight - 8 + window.scrollY) + 'px';
      tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + window.scrollX) + 'px';

      this._tooltip = tooltip;
    });

    el.addEventListener('mouseleave', function () {
      if (this._tooltip) {
        this._tooltip.remove();
        this._tooltip = null;
      }
    });
  });
}

// ===========================
// Charts
// ===========================
function initCharts() {

  // Guard: Chart.js must be loaded
  if (typeof Chart === 'undefined') return;

  const data = window.DASHBOARD_DATA || {};

  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.color = '#7a8fa9';

  const tooltipDefaults = {
    backgroundColor: '#0a1628',
    titleColor:      '#e8f0f8',
    bodyColor:       '#b8cee0',
    padding:         12,
    cornerRadius:    8,
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
            label: 'Loans',
            data: data.loansChart.data,
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
            x: { grid: { color: 'rgba(216,226,239,0.4)' }, border: { dash: [4, 4] } },
            y: { grid: { color: 'rgba(216,226,239,0.4)' }, border: { dash: [4, 4] }, beginAtZero: true, ticks: { precision: 0 } },
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
            backgroundColor: ['#1a6fd4', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#60b4ff'],
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
            y: { grid: { color: 'rgba(216,226,239,0.4)' }, border: { dash: [4, 4] }, beginAtZero: true, ticks: { precision: 0 } },
          }
        }
      });
    }
  }
}

// ===========================
// Quick Action Handlers
// ===========================
document.querySelectorAll('.action-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    const actionText = this.querySelector('.action-text').textContent;
    console.log('Action clicked:', actionText);
    // Wire up your action handlers here
  });
});

// ===========================
// Notification Click Handler
// ===========================
const notificationBtn = document.querySelector('.btn-icon[title="Notifications"]');
if (notificationBtn) {
  notificationBtn.addEventListener('click', function () {
    console.log('Notifications clicked');
    // Add notification panel logic here
  });
}