/**
 * Library Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
  console.log('Library dashboard loaded');

  // Mobile sidebar toggle
  initMobileSidebar();
  
  // Stats animations
  animateStats();
  
  // Initialize tooltips if needed
  initTooltips();
});

// ===========================
// Mobile Sidebar Toggle
// ===========================
function initMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');
  
  // Create mobile toggle button
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
    
    toggleBtn.addEventListener('click', function() {
      sidebar.classList.toggle('open');
    });
    
    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
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
    let currentValue = 0;
    const increment = Math.ceil(finalValue / 50);
    const duration = 1000;
    const stepTime = duration / 50;
    
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
    el.addEventListener('mouseenter', function() {
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
      tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
      tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
      
      this._tooltip = tooltip;
    });
    
    el.addEventListener('mouseleave', function() {
      if (this._tooltip) {
        this._tooltip.remove();
        this._tooltip = null;
      }
    });
  });
}

// ===========================
// Quick Action Handlers
// ===========================
const actionButtons = document.querySelectorAll('.action-btn');
actionButtons.forEach(btn => {
  btn.addEventListener('click', function() {
    const actionText = this.querySelector('.action-text').textContent;
    console.log('Action clicked:', actionText);
    // Add your action handlers here
  });
});

// ===========================
// Notification Click Handler
// ===========================
const notificationBtn = document.querySelector('.btn-icon[title="Notifications"]');
if (notificationBtn) {
  notificationBtn.addEventListener('click', function() {
    console.log('Notifications clicked');
    // Add notification panel logic here
  });
}