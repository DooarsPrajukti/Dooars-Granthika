/* ═══════════════════════════════════════════════════════════════════
   MEMBERS MODULE - JAVASCRIPT FUNCTIONALITY
   For: Dooars Granthika Library Management System
   ═══════════════════════════════════════════════════════════════════ */

// ───────────────────────────────────────────────────────────────────
// 1. UTILITY FUNCTIONS
// ─────────────────────────────────────────────────────────────────── 

const MembersUtils = {
  // Debounce function for search
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Show toast notification
  showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.messages-container') || this.createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `message message--${type}`;
    
    const iconMap = {
      'success': 'check-circle',
      'error': 'exclamation-circle',
      'warning': 'exclamation-triangle',
      'info': 'info-circle'
    };
    
    toast.innerHTML = `
      <i class="fas fa-${iconMap[type]}"></i>
      ${message}
      <button class="message-close" onclick="this.parentElement.remove()">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  },

  createToastContainer() {
    const container = document.createElement('div');
    container.className = 'messages-container';
    document.body.appendChild(container);
    return container;
  },

  // Format date
  formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
  },

  // Confirm action
  confirmAction(message) {
    return confirm(message);
  }
};

// ───────────────────────────────────────────────────────────────────
// 2. SEARCH & FILTER FUNCTIONALITY
// ───────────────────────────────────────────────────────────────────

class MembersSearch {
  constructor() {
    this.searchInput = document.getElementById('memberSearch');
    this.filterForm = document.getElementById('filterForm');
    this.init();
  }

  init() {
    if (this.searchInput) {
      this.searchInput.addEventListener('input', 
        MembersUtils.debounce((e) => this.handleSearch(e), 300)
      );
    }

    if (this.filterForm) {
      this.filterForm.addEventListener('submit', (e) => this.handleFilter(e));
    }

    // Reset filters
    const resetBtn = document.getElementById('resetFilters');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetFilters());
    }
  }

  handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    const tableRows = document.querySelectorAll('.members-table tbody tr');

    tableRows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(searchTerm) ? '' : 'none';
    });

    this.updateEmptyState();
  }

  handleFilter(e) {
    e.preventDefault();
    
    const formData = new FormData(this.filterForm);
    const params = new URLSearchParams(formData);
    
    // Redirect with query parameters
    window.location.href = `${window.location.pathname}?${params.toString()}`;
  }

  resetFilters() {
    if (this.filterForm) {
      this.filterForm.reset();
      window.location.href = window.location.pathname;
    }
  }

  updateEmptyState() {
    const tableRows = document.querySelectorAll('.members-table tbody tr');
    const visibleRows = Array.from(tableRows).filter(row => row.style.display !== 'none');
    
    let emptyState = document.querySelector('.empty-state-search');
    
    if (visibleRows.length === 0 && !emptyState) {
      emptyState = document.createElement('tr');
      emptyState.className = 'empty-state-search';
      emptyState.innerHTML = `
        <td colspan="100%" style="text-align: center; padding: 3rem;">
          <div class="empty-state-icon" style="display: inline-flex; width: 60px; height: 60px; margin-bottom: 1rem;">
            <i class="fas fa-search" style="font-size: 2rem; color: #9ca3af;"></i>
          </div>
          <p style="color: #6b7280; margin: 0;">No members found matching your search.</p>
        </td>
      `;
      document.querySelector('.members-table tbody').appendChild(emptyState);
    } else if (visibleRows.length > 0 && emptyState) {
      emptyState.remove();
    }
  }
}

// ───────────────────────────────────────────────────────────────────
// 3. FORM VALIDATION & SUBMISSION
// ───────────────────────────────────────────────────────────────────

class MemberForm {
  constructor() {
    this.form = document.getElementById('memberForm');
    this.init();
  }

  init() {
    if (!this.form) return;

    this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    
    // File input preview
    const photoInput = document.getElementById('memberPhoto');
    if (photoInput) {
      photoInput.addEventListener('change', (e) => this.handlePhotoPreview(e));
    }

    // Phone number formatting
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
      phoneInput.addEventListener('input', (e) => this.formatPhoneNumber(e));
    }

    // Email validation
    const emailInput = document.getElementById('email');
    if (emailInput) {
      emailInput.addEventListener('blur', (e) => this.validateEmail(e));
    }

    // Date validation (not future date)
    const dobInput = document.getElementById('dateOfBirth');
    if (dobInput) {
      dobInput.setAttribute('max', new Date().toISOString().split('T')[0]);
    }
  }

  handleSubmit(e) {
    if (!this.validateForm()) {
      e.preventDefault();
      MembersUtils.showToast('Please fill in all required fields correctly.', 'error');
      return false;
    }
    
    // Show loading state
    const submitBtn = this.form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }
  }

  validateForm() {
    const requiredFields = this.form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        this.showFieldError(field, 'This field is required');
        isValid = false;
      } else {
        this.clearFieldError(field);
      }
    });

    return isValid;
  }

  showFieldError(field, message) {
    field.classList.add('error');
    field.style.borderColor = '#ef4444';
    
    let errorMsg = field.parentElement.querySelector('.error-message');
    if (!errorMsg) {
      errorMsg = document.createElement('span');
      errorMsg.className = 'error-message';
      errorMsg.style.color = '#ef4444';
      errorMsg.style.fontSize = '0.875rem';
      errorMsg.style.marginTop = '0.25rem';
      field.parentElement.appendChild(errorMsg);
    }
    errorMsg.textContent = message;
  }

  clearFieldError(field) {
    field.classList.remove('error');
    field.style.borderColor = '';
    
    const errorMsg = field.parentElement.querySelector('.error-message');
    if (errorMsg) {
      errorMsg.remove();
    }
  }

  handlePhotoPreview(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      MembersUtils.showToast('Please select a valid image file.', 'error');
      e.target.value = '';
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      MembersUtils.showToast('Image size should be less than 5MB.', 'error');
      e.target.value = '';
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      let preview = document.getElementById('photoPreview');
      if (!preview) {
        preview = document.createElement('div');
        preview.id = 'photoPreview';
        preview.className = 'image-preview active';
        preview.innerHTML = '<img src="" alt="Preview" />';
        document.querySelector('.file-input-wrapper').appendChild(preview);
      }
      preview.querySelector('img').src = e.target.result;
      preview.classList.add('active');
    };
    reader.readAsDataURL(file);
  }

  formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length > 10) {
      value = value.slice(0, 10);
    }
    e.target.value = value;
  }

  validateEmail(e) {
    const email = e.target.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
      this.showFieldError(e.target, 'Please enter a valid email address');
    } else {
      this.clearFieldError(e.target);
    }
  }
}

// ───────────────────────────────────────────────────────────────────
// 4. DELETE CONFIRMATION
// ───────────────────────────────────────────────────────────────────

class MemberDelete {
  constructor() {
    this.init();
  }

  init() {
    document.addEventListener('click', (e) => {
      if (e.target.closest('.delete-member-btn')) {
        e.preventDefault();
        const btn = e.target.closest('.delete-member-btn');
        this.confirmDelete(btn);
      }
    });
  }

  confirmDelete(btn) {
    const memberName = btn.dataset.memberName || 'this member';
    const deleteUrl = btn.dataset.deleteUrl || btn.href;

    if (MembersUtils.confirmAction(`Are you sure you want to delete ${memberName}? This action cannot be undone.`)) {
      // Create and submit form
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = deleteUrl;
      
      // Add CSRF token
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      if (csrfToken) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrfmiddlewaretoken';
        input.value = csrfToken.value;
        form.appendChild(input);
      }
      
      document.body.appendChild(form);
      form.submit();
    }
  }
}

// ───────────────────────────────────────────────────────────────────
// 5. CLEARANCE CHECK
// ───────────────────────────────────────────────────────────────────

class ClearanceCheck {
  constructor() {
    this.form = document.getElementById('clearanceCheckForm');
    this.resultCard = document.getElementById('clearanceResult');
    this.init();
  }

  init() {
    if (!this.form) return;

    this.form.addEventListener('submit', (e) => this.handleCheck(e));
  }

  async handleCheck(e) {
    e.preventDefault();

    const formData = new FormData(this.form);
    const memberId = formData.get('member_id') || formData.get('member_phone');

    if (!memberId) {
      MembersUtils.showToast('Please enter Member ID or Phone Number', 'error');
      return;
    }

    // Show loading state
    const submitBtn = this.form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

    try {
      // Make AJAX request to check clearance
      const response = await fetch(this.form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        }
      });

      const data = await response.json();

      if (data.success) {
        this.displayResult(data.member);
      } else {
        MembersUtils.showToast(data.message || 'Member not found', 'error');
      }
    } catch (error) {
      console.error('Error:', error);
      MembersUtils.showToast('An error occurred. Please try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  }

  displayResult(member) {
    if (!this.resultCard) return;

    const isCleared = member.clearance_status === 'cleared';
    const iconClass = isCleared ? 'cleared' : 'pending';
    const statusText = isCleared ? 'Clearance Approved' : 'Pending Clearance';
    const statusMessage = isCleared 
      ? 'This member has no pending dues or issues.'
      : 'This member has pending items that need to be resolved.';

    let pendingItemsHtml = '';
    if (!isCleared && member.pending_items && member.pending_items.length > 0) {
      pendingItemsHtml = `
        <div class="pending-items">
          <h4><i class="fas fa-exclamation-triangle"></i> Pending Items:</h4>
          <ul>
            ${member.pending_items.map(item => `<li>${item}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    this.resultCard.innerHTML = `
      <div class="clearance-status">
        <div class="clearance-icon ${iconClass}">
          <i class="fas fa-${isCleared ? 'check' : 'clock'}"></i>
        </div>
        <h3>${statusText}</h3>
        <p>${statusMessage}</p>
      </div>
      
      <div class="clearance-details">
        <div class="clearance-info-grid">
          <div class="clearance-info-item">
            <span class="clearance-info-label">Member Name</span>
            <span class="clearance-info-value">${member.name}</span>
          </div>
          <div class="clearance-info-item">
            <span class="clearance-info-label">Member ID</span>
            <span class="clearance-info-value">${member.member_id}</span>
          </div>
          <div class="clearance-info-item">
            <span class="clearance-info-label">Department</span>
            <span class="clearance-info-value">${member.department || 'N/A'}</span>
          </div>
          <div class="clearance-info-item">
            <span class="clearance-info-label">Status</span>
            <span class="clearance-info-value">
              <span class="status-badge ${member.status}">${member.status}</span>
            </span>
          </div>
        </div>
        
        ${pendingItemsHtml}
        
        <div style="margin-top: 1.5rem; text-align: center;">
          <a href="/members/${member.id}/" class="btn btn-primary">
            <i class="fas fa-user"></i> View Full Profile
          </a>
        </div>
      </div>
    `;

    this.resultCard.classList.add('show');
    
    // Smooth scroll to result
    this.resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// ───────────────────────────────────────────────────────────────────
// 6. MODAL MANAGEMENT
// ───────────────────────────────────────────────────────────────────

class ModalManager {
  constructor() {
    this.init();
  }

  init() {
    // Modal triggers
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-modal-open]')) {
        const modalId = e.target.dataset.modalOpen;
        this.openModal(modalId);
      }

      if (e.target.matches('[data-modal-close]') || e.target.closest('[data-modal-close]')) {
        this.closeModal(e.target.closest('.modal-overlay'));
      }
    });

    // Close on overlay click
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-overlay')) {
        this.closeModal(e.target);
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal-overlay.active');
        if (openModal) {
          this.closeModal(openModal);
        }
      }
    });
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  closeModal(modal) {
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }
}

// ───────────────────────────────────────────────────────────────────
// 7. TABLE SORTING
// ───────────────────────────────────────────────────────────────────

class TableSort {
  constructor(tableId) {
    this.table = document.getElementById(tableId);
    this.init();
  }

  init() {
    if (!this.table) return;

    const headers = this.table.querySelectorAll('th[data-sortable]');
    headers.forEach(header => {
      header.style.cursor = 'pointer';
      header.addEventListener('click', () => this.sortTable(header));
    });
  }

  sortTable(header) {
    const column = header.cellIndex;
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const currentOrder = header.dataset.order || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    
    // Clear all sort indicators
    table.querySelectorAll('th').forEach(th => {
      th.dataset.order = '';
      const icon = th.querySelector('.sort-icon');
      if (icon) icon.remove();
    });
    
    // Add sort indicator
    header.dataset.order = newOrder;
    const icon = document.createElement('i');
    icon.className = `fas fa-sort-${newOrder === 'asc' ? 'up' : 'down'} sort-icon`;
    icon.style.marginLeft = '0.5rem';
    header.appendChild(icon);
    
    // Sort rows
    rows.sort((a, b) => {
      const aValue = a.cells[column].textContent.trim();
      const bValue = b.cells[column].textContent.trim();
      
      const aNum = parseFloat(aValue);
      const bNum = parseFloat(bValue);
      
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return newOrder === 'asc' ? aNum - bNum : bNum - aNum;
      }
      
      return newOrder === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    });
    
    // Reattach sorted rows
    rows.forEach(row => tbody.appendChild(row));
  }
}

// ───────────────────────────────────────────────────────────────────
// 8. BULK ACTIONS
// ───────────────────────────────────────────────────────────────────

class BulkActions {
  constructor() {
    this.selectedItems = new Set();
    this.init();
  }

  init() {
    // Select all checkbox
    const selectAll = document.getElementById('selectAllMembers');
    if (selectAll) {
      selectAll.addEventListener('change', (e) => this.handleSelectAll(e));
    }

    // Individual checkboxes
    document.addEventListener('change', (e) => {
      if (e.target.matches('.member-checkbox')) {
        this.handleCheckboxChange(e);
      }
    });

    // Bulk action buttons
    const bulkActionBtns = document.querySelectorAll('[data-bulk-action]');
    bulkActionBtns.forEach(btn => {
      btn.addEventListener('click', (e) => this.handleBulkAction(e));
    });
  }

  handleSelectAll(e) {
    const checkboxes = document.querySelectorAll('.member-checkbox');
    checkboxes.forEach(checkbox => {
      checkbox.checked = e.target.checked;
      if (e.target.checked) {
        this.selectedItems.add(checkbox.value);
      } else {
        this.selectedItems.delete(checkbox.value);
      }
    });
    this.updateBulkActionsUI();
  }

  handleCheckboxChange(e) {
    if (e.target.checked) {
      this.selectedItems.add(e.target.value);
    } else {
      this.selectedItems.delete(e.target.value);
    }
    this.updateBulkActionsUI();
  }

  updateBulkActionsUI() {
    const bulkActionsBar = document.getElementById('bulkActionsBar');
    const selectedCount = document.getElementById('selectedCount');
    
    if (bulkActionsBar) {
      bulkActionsBar.style.display = this.selectedItems.size > 0 ? 'flex' : 'none';
    }
    
    if (selectedCount) {
      selectedCount.textContent = this.selectedItems.size;
    }
  }

  handleBulkAction(e) {
    const action = e.target.closest('[data-bulk-action]').dataset.bulkAction;
    
    if (this.selectedItems.size === 0) {
      MembersUtils.showToast('Please select at least one member', 'warning');
      return;
    }

    const confirmMessage = `Are you sure you want to ${action} ${this.selectedItems.size} member(s)?`;
    
    if (MembersUtils.confirmAction(confirmMessage)) {
      // Submit form with selected IDs
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = `/members/bulk-${action}/`;
      
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      if (csrfToken) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrfmiddlewaretoken';
        input.value = csrfToken.value;
        form.appendChild(input);
      }
      
      this.selectedItems.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'member_ids';
        input.value = id;
        form.appendChild(input);
      });
      
      document.body.appendChild(form);
      form.submit();
    }
  }
}

// ───────────────────────────────────────────────────────────────────
// 9. INITIALIZATION
// ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Initialize all modules
  new MembersSearch();
  new MemberForm();
  new MemberDelete();
  new ClearanceCheck();
  new ModalManager();
  new TableSort('membersTable');
  new BulkActions();

  // Auto-hide messages after 5 seconds
  const messages = document.querySelectorAll('.message');
  messages.forEach(message => {
    setTimeout(() => {
      message.style.opacity = '0';
      setTimeout(() => message.remove(), 300);
    }, 5000);
  });

  console.log('Members module initialized successfully');
});

// Export for use in other modules if needed
window.MembersModule = {
  Utils: MembersUtils,
  Search: MembersSearch,
  Form: MemberForm,
  Delete: MemberDelete,
  Clearance: ClearanceCheck,
  Modal: ModalManager,
  TableSort: TableSort,
  BulkActions: BulkActions
};