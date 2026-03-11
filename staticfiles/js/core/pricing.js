// LibNexa - Pricing Page Animations

document.addEventListener('DOMContentLoaded', function() {
  initializePricingAnimations();
  initializePriceCounter();
  initializeFAQAnimations();
  initializeCardHoverEffects();
});

/**
 * Initialize pricing page animations
 */
function initializePricingAnimations() {
  // Add index to pricing cards for staggered animation
  const pricingCards = document.querySelectorAll('.pricing-card');
  pricingCards.forEach((card, index) => {
    card.style.setProperty('--card-index', index);
    
    // Add index to features within each card
    const features = card.querySelectorAll('.pricing-features li');
    features.forEach((feature, featureIndex) => {
      feature.style.setProperty('--feature-index', featureIndex);
    });
  });

  // Add index to FAQ items
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach((item, index) => {
    item.style.setProperty('--faq-index', index);
  });

  // Highlight featured card
  highlightFeaturedCard();
}

/**
 * Highlight featured card with special effects
 */
function highlightFeaturedCard() {
  const featuredCard = document.querySelector('.pricing-card.featured');
  if (!featuredCard) return;

  // Add glow effect
  setInterval(() => {
    featuredCard.style.transition = 'box-shadow 1s ease-in-out';
  }, 2000);
}

/**
 * Animate price numbers counting up
 */
function initializePriceCounter() {
  const prices = document.querySelectorAll('.price .amount');
  
  const observerOptions = {
    threshold: 0.5,
    rootMargin: '0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const priceElement = entry.target;
        const finalValue = priceElement.textContent.trim();
        
        // Check if it's "Custom" or a number
        if (finalValue.toLowerCase() === 'custom') {
          animateCustomText(priceElement);
        } else {
          const numericValue = parseInt(finalValue.replace(/[^0-9]/g, ''));
          if (!isNaN(numericValue)) {
            animatePrice(priceElement, 0, numericValue, 1500);
          }
        }
        
        observer.unobserve(priceElement);
      }
    });
  }, observerOptions);

  prices.forEach(price => observer.observe(price));
}

/**
 * Animate price counting
 */
function animatePrice(element, start, end, duration) {
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Easing function (easeOutQuart)
    const easeProgress = 1 - Math.pow(1 - progress, 4);
    
    const currentValue = Math.floor(start + (end - start) * easeProgress);
    element.textContent = currentValue.toLocaleString('en-IN');
    
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = end.toLocaleString('en-IN');
    }
  }
  
  requestAnimationFrame(update);
}

/**
 * Animate "Custom" text
 */
function animateCustomText(element) {
  const text = 'Custom';
  element.textContent = '';
  
  text.split('').forEach((char, index) => {
    setTimeout(() => {
      element.textContent += char;
    }, index * 100);
  });
}

/**
 * Initialize FAQ animations
 */
function initializeFAQAnimations() {
  const faqItems = document.querySelectorAll('.faq-item');
  
  faqItems.forEach(item => {
    // Add click-to-expand functionality
    item.addEventListener('click', function() {
      this.classList.toggle('expanded');
      
      // Smooth height transition
      const answer = this.querySelector('p');
      if (this.classList.contains('expanded')) {
        answer.style.maxHeight = answer.scrollHeight + 'px';
      } else {
        answer.style.maxHeight = null;
      }
    });

    // Hover effect
    item.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px)';
      this.style.borderLeftColor = '#00c006';
    });

    item.addEventListener('mouseleave', function() {
      if (!this.classList.contains('expanded')) {
        this.style.transform = 'translateY(0)';
        this.style.borderLeftColor = 'transparent';
      }
    });
  });
}

/**
 * Initialize card hover effects
 */
function initializeCardHoverEffects() {
  const cards = document.querySelectorAll('.pricing-card');
  
  cards.forEach(card => {
    // 3D tilt effect on mouse move
    card.addEventListener('mousemove', function(e) {
      if (window.innerWidth <= 768) return; // Disable on mobile

      const rect = this.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = (y - centerY) / 20;
      const rotateY = (centerX - x) / 20;
      
      this.style.transform = `
        perspective(1000px) 
        rotateX(${rotateX}deg) 
        rotateY(${rotateY}deg) 
        translateY(-15px) 
        scale(1.02)
      `;
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });

    // Button click animation
    const button = card.querySelector('.pricing-btn');
    if (button) {
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
    }
  });
}

/**
 * Add comparison tooltip
 */
function initializeComparisonTooltip() {
  const features = document.querySelectorAll('.pricing-features li');
  
  features.forEach(feature => {
    feature.addEventListener('mouseenter', function() {
      const featureText = this.textContent.trim();
      
      // Create tooltip (example)
      const tooltip = document.createElement('div');
      tooltip.className = 'feature-tooltip';
      tooltip.textContent = `Learn more about: ${featureText}`;
      tooltip.style.cssText = `
        position: absolute;
        background: #2c3e50;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease;
      `;
      
      this.appendChild(tooltip);
      setTimeout(() => {
        tooltip.style.opacity = '1';
      }, 10);
    });
    
    feature.addEventListener('mouseleave', function() {
      const tooltip = this.querySelector('.feature-tooltip');
      if (tooltip) {
        tooltip.remove();
      }
    });
  });
}

/**
 * Smooth scroll to pricing section from CTA
 */
function initializeSmoothScroll() {
  const ctaButton = document.querySelector('.cta-section .btn');
  if (ctaButton && ctaButton.getAttribute('href') === '#pricing') {
    ctaButton.addEventListener('click', function(e) {
      e.preventDefault();
      const pricingSection = document.querySelector('.pricing-section');
      if (pricingSection) {
        pricingSection.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  }
}

initializeSmoothScroll();

/**
 * Add sparkle effect to featured badge
 */
function addSparkleToBadge() {
  const badge = document.querySelector('.featured-badge');
  if (!badge) return;

  setInterval(() => {
    const sparkle = document.createElement('span');
    sparkle.textContent = '✨';
    sparkle.style.cssText = `
      position: absolute;
      top: 50%;
      left: ${Math.random() * 100}%;
      transform: translate(-50%, -50%);
      animation: sparkle 1s ease-out forwards;
      pointer-events: none;
    `;
    badge.appendChild(sparkle);
    
    setTimeout(() => sparkle.remove(), 1000);
  }, 2000);
}

// Add sparkle animation CSS
const style = document.createElement('style');
style.textContent = `
  @keyframes sparkle {
    0% {
      opacity: 1;
      transform: translate(-50%, -50%) scale(0);
    }
    50% {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
    }
    100% {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0) translateY(-20px);
    }
  }
  
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
`;
document.head.appendChild(style);

addSparkleToBadge();

/**
 * Plan comparison helper
 */
function highlightDifferences() {
  const cards = document.querySelectorAll('.pricing-card');
  
  cards.forEach(card => {
    card.addEventListener('click', function() {
      cards.forEach(c => c.classList.remove('comparing'));
      this.classList.add('comparing');
      
      // Highlight unique features
      const features = this.querySelectorAll('.pricing-features li');
      features.forEach(feature => {
        feature.style.backgroundColor = 'rgba(0, 192, 6, 0.05)';
        setTimeout(() => {
          feature.style.backgroundColor = '';
        }, 1000);
      });
    });
  });
}

highlightDifferences();