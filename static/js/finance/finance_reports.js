const monthlyLabels = {{ monthly_labels|safe|default:'["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]' }};
const monthlyData   = {{ monthly_data|safe|default:'[0,0,0,0,0,0,0,0,0,0,0,0]' }};

new Chart(document.getElementById('monthlyChart'), {
  type: 'bar',
  data: {
    labels: monthlyLabels,
    datasets: [{
      label: 'Collections (₹)',
      data: monthlyData,
      backgroundColor: '#818cf8',
      borderRadius: 6,
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { callback: v => '₹' + v } },
      x: { grid: { display: false } }
    }
  }
});

new Chart(document.getElementById('methodChart'), {
  type: 'doughnut',
  data: {
    labels: ['Online', 'Cash'],
    datasets: [{
      data: [{{ online_amount|default:0 }}, {{ cash_amount|default:0 }}],
      backgroundColor: ['#4f46e5', '#f59e0b'],
      borderWidth: 0,
    }]
  },
  options: {
    responsive: true,
    cutout: '68%',
    plugins: {
      legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } }
    }
  }
});
