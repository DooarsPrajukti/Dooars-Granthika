/**
 * admin_dashboard.js
 * Admin Dashboard — page-specific JavaScript.
 * Depends on: dashboard_base.js (loaded first via dashboard_base.html)
 *
 * Covers: Chart.js chart initialisation (loans, category, members,
 *         department, status) and quick-action button handlers.
 *
 * Expects window.DASHBOARD_DATA to be set inline by the Django template
 * before this script runs.
 */

document.addEventListener('DOMContentLoaded', function () {
  initCharts();
  initQuickActions();
});

/* ============================================================
   1. Charts
   Reads window.DASHBOARD_DATA injected by the Django template.
   Each chart is guarded — missing canvas or disabled data
   skips that chart gracefully.
   ============================================================ */
function initCharts() {
  if (typeof Chart === 'undefined') {
    console.warn('admin_dashboard.js: Chart.js not loaded — skipping charts.');
    return;
  }

  const data = window.DASHBOARD_DATA || {};

  // ── Global Chart.js defaults ──────────────────────────────
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

  // ── 1. Monthly Loans — Line Chart ────────────────────────
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
              grid:        { color: 'rgba(216,226,239,0.4)' },
              border:      { dash: [4, 4] },
              beginAtZero: true,
              ticks:       { precision: 0 },
            },
          },
        },
      });
    }
  }

  // ── 2. Books by Category — Doughnut Chart ─────────────────
  if (data.categoryChart && data.categoryChart.enabled) {
    const ctx = document.getElementById('categoryChart');
    if (ctx) {
      new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: data.categoryChart.labels,
          datasets: [{
            data: data.categoryChart.data,
            backgroundColor: [
              '#1a6fd4', '#10b981', '#8b5cf6', '#f59e0b',
              '#ef4444', '#60b4ff', '#f093fb', '#30cfd0',
            ],
            borderWidth:  2,
            borderColor:  '#ffffff',
            hoverOffset:  8,
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
              },
            },
            tooltip: tooltipDefaults,
          },
        },
      });
    }
  }

  // ── 3. New Members (last 7 days) — Bar Chart ──────────────
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
          },
        },
      });
    }
  }

  // ── 4. Members by Department — Doughnut Chart ─────────────
  // Data is provided inline by the template via window.DEPT_DATA
  const deptCtx = document.getElementById('departmentChart');
  if (deptCtx && window.DEPT_DATA) {
    new Chart(deptCtx, {
      type: 'doughnut',
      data: {
        labels: window.DEPT_DATA.labels,
        datasets: [{
          data: window.DEPT_DATA.values,
          backgroundColor: [
            '#667eea', '#764ba2', '#f093fb', '#4facfe',
            '#43e97b', '#fa709a', '#fee140', '#30cfd0',
          ],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { padding: 15, font: { size: 12 } },
          },
          tooltip: tooltipDefaults,
        },
      },
    });
  }

  // ── 5. Member Status Distribution — Pie Chart ─────────────
  // Data is provided inline by the template via window.STATUS_DATA
  const statusCtx = document.getElementById('statusChart');
  if (statusCtx && window.STATUS_DATA) {
    new Chart(statusCtx, {
      type: 'pie',
      data: {
        labels: ['Active', 'Pass Out', 'Inactive'],
        datasets: [{
          data: [
            window.STATUS_DATA.active,
            window.STATUS_DATA.passout,
            window.STATUS_DATA.inactive,
          ],
          backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { padding: 15, font: { size: 12 } },
          },
          tooltip: tooltipDefaults,
        },
      },
    });
  }
}

/* ============================================================
   2. Quick Action Button Handlers
   Lets <a href="#"> placeholder buttons wire up custom logic
   without interfering with real links.
   ============================================================ */
function initQuickActions() {
  document.querySelectorAll('.action-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      // Real href — let the browser navigate naturally
      const href = this.getAttribute('href');
      if (href && href !== '#') return;

      e.preventDefault();
      const labelEl = this.querySelector('.action-text');
      const label   = labelEl ? labelEl.textContent.trim() : 'Action';

      // Add per-action logic here, e.g.:
      // if (label === 'Generate Report') openReportModal();
      console.log('Quick action clicked:', label);
    });
  });
}