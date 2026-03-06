const labels = {{ chart_labels|safe|default:'["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]' }};
const incomeData  = {{ chart_income|safe|default:'[0,0,0,0,0,0,0,0,0,0,0,0]' }};
const expenseData = {{ chart_expenses|safe|default:'[0,0,0,0,0,0,0,0,0,0,0,0]' }};

new Chart(document.getElementById('plChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [
      {
        label: 'Income',
        data: incomeData,
        borderColor: '#16a34a',
        backgroundColor: 'rgba(22,163,74,.08)',
        fill: true,
        tension: .4,
        pointRadius: 4,
      },
      {
        label: 'Expenses',
        data: expenseData,
        borderColor: '#dc2626',
        backgroundColor: 'rgba(220,38,38,.06)',
        fill: true,
        tension: .4,
        pointRadius: 4,
      }
    ]
  },
  options: {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { beginAtZero: true, ticks: { callback: v => '₹' + v } },
      x: { grid: { display: false } }
    }
  }
});
