// LibNexa - Main JavaScript File
// Base functionality for all pages

document.addEventListener('DOMContentLoaded', function() {
  initializeNavigation();
  initializeButtonEffects();
  initializeMobileMenu();
  initializeScrollEffects();
});

/**
 * Initialize navigation functionality
 */
function initializeNavigation() {
  // Highlight active navigation link
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href !== '#' && href !== '') {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          const headerOffset = 80;
          const elementPosition = target.getBoundingClientRect().top;
          const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

          window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
          });
        }
      }
    });
  });
}

/**
 * Initialize button click effects
 */
function initializeButtonEffects() {
  const buttons = document.querySelectorAll('.btn');
  
  buttons.forEach(button => {
    button.addEventListener('click', function(e) {
      // Create ripple effect
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.add('ripple-effect');

      this.appendChild(ripple);

      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
}

/**
 * Initialize mobile menu toggle
 */
function initializeMobileMenu() {
  // Create mobile menu toggle button if it doesn't exist
  const header = document.querySelector('.main-header');
  const nav = document.querySelector('.main-nav');
  
  if (!header || !nav) return;

  // Check if mobile toggle already exists
  let mobileToggle = document.querySelector('.mobile-menu-toggle');
  
  if (!mobileToggle && window.innerWidth <= 768) {
    mobileToggle = document.createElement('button');
    mobileToggle.className = 'mobile-menu-toggle';
    mobileToggle.innerHTML = '☰';
    mobileToggle.setAttribute('aria-label', 'Toggle menu');
    
    const headerContainer = document.querySelector('.header-container');
    headerContainer.appendChild(mobileToggle);

    mobileToggle.addEventListener('click', function() {
      nav.classList.toggle('mobile-active');
      this.classList.toggle('active');
      this.innerHTML = this.classList.contains('active') ? '✕' : '☰';
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
      if (!header.contains(e.target)) {
        nav.classList.remove('mobile-active');
        mobileToggle.classList.remove('active');
        mobileToggle.innerHTML = '☰';
      }
    });

    // Close menu when clicking a link
    const navLinks = nav.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', function() {
        nav.classList.remove('mobile-active');
        mobileToggle.classList.remove('active');
        mobileToggle.innerHTML = '☰';
      });
    });
  }
}

/**
 * Initialize scroll effects
 */
function initializeScrollEffects() {
  const header = document.querySelector('.main-header');
  if (!header) return;

  let lastScroll = 0;
  
  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    // Add shadow on scroll
    if (currentScroll > 10) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    // Hide/show header on scroll (optional)
    if (currentScroll > lastScroll && currentScroll > 100) {
      // Scrolling down
      header.style.transform = 'translateY(-100%)';
    } else {
      // Scrolling up
      header.style.transform = 'translateY(0)';
    }

    lastScroll = currentScroll;
  });
}

/**
 * Show loading state on buttons
 */
function setButtonLoading(button, isLoading) {
  if (!button) return;

  if (isLoading) {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<span class="loading-spinner"></span> Loading...';
    button.style.opacity = '0.7';
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
    button.style.opacity = '1';
  }
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <span class="notification-icon">${getNotificationIcon(type)}</span>
    <span class="notification-message">${message}</span>
    <button class="notification-close" onclick="this.parentElement.remove()">✕</button>
  `;

  document.body.appendChild(notification);

  // Animate in
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);

  // Auto remove after 5 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 5000);
}

/**
 * Get notification icon based on type
 */
function getNotificationIcon(type) {
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  };
  return icons[type] || icons.info;
}

/**
 * Debounce function for performance
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function for performance
 */
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showNotification('Copied to clipboard!', 'success');
    return true;
  } catch (err) {
    console.error('Failed to copy:', err);
    showNotification('Failed to copy to clipboard', 'error');
    return false;
  }
}

/**
 * Format number with commas
 */
function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Add CSS for dynamic elements
 */
const dynamicStyles = document.createElement('style');
dynamicStyles.textContent = `
  /* Ripple Effect */
  .ripple-effect {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s ease-out;
    pointer-events: none;
  }
  
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
  
  /* Loading Spinner */
  .loading-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  /* Notification Toast */
  .notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 10000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
    max-width: 400px;
  }
  
  .notification.show {
    transform: translateX(0);
  }
  
  .notification-success {
    border-left: 4px solid #00c006;
  }
  
  .notification-error {
    border-left: 4px solid #ef0000;
  }
  
  .notification-warning {
    border-left: 4px solid #ff9800;
  }
  
  .notification-info {
    border-left: 4px solid #2c3e50;
  }
  
  .notification-icon {
    font-size: 1.5rem;
    font-weight: bold;
  }
  
  .notification-success .notification-icon {
    color: #00c006;
  }
  
  .notification-error .notification-icon {
    color: #ef0000;
  }
  
  .notification-warning .notification-icon {
    color: #ff9800;
  }
  
  .notification-info .notification-icon {
    color: #2c3e50;
  }
  
  .notification-message {
    flex: 1;
    color: #2c3e50;
  }
  
  .notification-close {
    background: none;
    border: none;
    font-size: 1.25rem;
    color: #4a5568;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background 0.2s;
  }
  
  .notification-close:hover {
    background: rgba(0, 0, 0, 0.05);
  }
  
  /* Mobile Menu Toggle */
  .mobile-menu-toggle {
    display: none;
    background: none;
    border: none;
    color: white;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.5rem;
    margin-left: auto;
  }
  
  /* Header Scrolled State */
  .main-header.scrolled {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }
  
  /* Mobile Styles */
  @media (max-width: 768px) {
    .mobile-menu-toggle {
      display: block;
    }
    
    .main-nav {
      position: fixed;
      top: 60px;
      left: 0;
      right: 0;
      background: #2c3e50;
      flex-direction: column;
      padding: 1rem;
      transform: translateX(-100%);
      transition: transform 0.3s ease;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    
    .main-nav.mobile-active {
      transform: translateX(0);
    }
    
    .main-nav .nav-link {
      padding: 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .notification {
      left: 10px;
      right: 10px;
      max-width: none;
    }
  }
`;
document.head.appendChild(dynamicStyles);

// Export functions for use in other scripts
window.LibNexa = {
  setButtonLoading,
  showNotification,
  debounce,
  throttle,
  isInViewport,
  copyToClipboard,
  formatNumber
};