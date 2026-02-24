/* =============================================================
   staff_dashboard.js
   static/js/dashboard/staff_dashboard.js
   ============================================================= */

(function () {
  'use strict';

  function init() {
    const d = window.STAFF_DASHBOARD_DATA;
    if (!d) return;

    if (d.weeklyChart.enabled) {
      const canvas = document.getElementById('weeklyChart');
      if (!canvas) return;

      new Chart(canvas, {
        type: 'bar',
        data: {
          labels: d.weeklyChart.labels,
          datasets: [
            {
              label: 'Issued',
              data: d.weeklyChart.issued,
              backgroundColor: 'rgba(99,102,241,0.18)',
              borderColor: '#6366f1',
              borderWidth: 2,
              borderRadius: 6,
              borderSkipped: false,
            },
            {
              label: 'Returned',
              data: d.weeklyChart.returned,
              backgroundColor: 'rgba(34,197,94,0.15)',
              borderColor: '#22c55e',
              borderWidth: 2,
              borderRadius: 6,
              borderSkipped: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                font: { size: 11, family: "'Sora', sans-serif" },
                color: '#94a3b8',
                padding: 16,
                usePointStyle: true,
                pointStyleWidth: 8,
              },
            },
            tooltip: {
              backgroundColor: '#0f172a',
              titleColor: '#f1f5f9',
              bodyColor: '#94a3b8',
              borderColor: '#1e2538',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(0,0,0,0.04)' },
              ticks: { color: '#94a3b8', font: { size: 11 }, stepSize: 1 },
              border: { dash: [4, 4] },
            },
            x: {
              grid: { display: false },
              ticks: { color: '#94a3b8', font: { size: 11 } },
            },
          },
        },
      });
    }
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();
})();