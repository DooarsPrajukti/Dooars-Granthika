/**
 * members/member_edit.js
 * ──────────────────────
 * Edit-member page specific JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * Responsibilities:
 *   - Role card selection + dynamic section show/hide  (same logic as add)
 *   - Select-or-create mutual exclusivity
 *   - Phone & email field validation
 *   - Photo change preview
 *   - Disable hidden department selects before submit
 *   - DOB max-date enforcement
 *   - Submit button loading state
 *   - Delete member wiring
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── helpers ──────────────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  function setName(el, name) { if (el) el.name = name; }


  // ═══════════════════════════════════════════════════════════════════════════
  // ROLE SWITCHING  (mirrors member_add.js)
  // ═══════════════════════════════════════════════════════════════════════════

  function applyRole(role) {

    document.querySelectorAll('.student-only').forEach(el => {
      el.style.display = (role === 'student') ? '' : 'none';
    });
    document.querySelectorAll('.teacher-only').forEach(el => {
      el.style.display = (role === 'teacher') ? '' : 'none';
    });
    document.querySelectorAll('.general-only').forEach(el => {
      el.style.display = (role === 'general') ? '' : 'none';
    });

    // Status select swap
    const studentStatusWrap = $('status-student-wrapper');
    const otherStatusWrap   = $('status-other-wrapper');
    const studentSel = studentStatusWrap?.querySelector('select');
    const otherSel   = otherStatusWrap?.querySelector('select');

    if (role === 'student') {
      if (studentStatusWrap) studentStatusWrap.style.display = '';
      if (otherStatusWrap)   otherStatusWrap.style.display   = 'none';
      setName(studentSel, 'status');
      setName(otherSel,   '_status_disabled');
    } else {
      if (studentStatusWrap) studentStatusWrap.style.display = 'none';
      if (otherStatusWrap)   otherStatusWrap.style.display   = '';
      setName(otherSel,   'status');
      setName(studentSel, '_status_disabled');
    }

    // Disable hidden department dropdowns
    const deptStudent = $('department');
    const deptTeacher = $('department_teacher');
    const deptGeneral = $('orgDept');
    if (deptStudent) deptStudent.disabled = (role !== 'student');
    if (deptTeacher) deptTeacher.disabled = (role !== 'teacher');
    if (deptGeneral) deptGeneral.disabled = (role !== 'general');

    // Role card highlight
    document.querySelectorAll('.role-option').forEach(opt => {
      opt.classList.toggle('selected', opt.dataset.role === role);
    });
  }

  document.querySelectorAll('.role-option').forEach(label => {
    label.addEventListener('click', function () {
      const radio = this.querySelector('input[type="radio"]');
      if (radio) { radio.checked = true; applyRole(radio.value); }
    });
  });

  const checkedRadio = document.querySelector('input[name="role"]:checked');
  applyRole(checkedRadio ? checkedRadio.value : 'student');


  // ═══════════════════════════════════════════════════════════════════════════
  // SELECT-OR-CREATE
  // ═══════════════════════════════════════════════════════════════════════════

  initSelectOrCreate(); // from members.js


  // ═══════════════════════════════════════════════════════════════════════════
  // PHONE & EMAIL VALIDATION
  // ═══════════════════════════════════════════════════════════════════════════

  initPhoneValidation([
    { id: 'phone',          required: true  },
    { id: 'alternatePhone', required: false },
    { id: 'guardianPhone',  required: false },
  ]);

  initEmailValidation('email');


  // ═══════════════════════════════════════════════════════════════════════════
  // DOB — prevent future dates
  // ═══════════════════════════════════════════════════════════════════════════

  const dob = $('dateOfBirth');
  if (dob) dob.setAttribute('max', new Date().toISOString().split('T')[0]);


  // ═══════════════════════════════════════════════════════════════════════════
  // PHOTO — change preview for edit page
  // ═══════════════════════════════════════════════════════════════════════════

  const photoInput = $('memberPhoto');
  const previewDiv = $('photoPreview');

  if (photoInput && previewDiv) {
    photoInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (!file.type.startsWith('image/')) {
        showToast('Please select a valid image (JPG, PNG, GIF).', 'error');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        showToast('Image must be 5 MB or less.', 'error');
        return;
      }

      const reader = new FileReader();
      reader.onload = (evt) => {
        previewDiv.innerHTML = '';
        const img = document.createElement('img');
        img.src = evt.target.result;
        img.alt = 'New photo preview';
        previewDiv.appendChild(img);
        previewDiv.classList.add('active');
      };
      reader.readAsDataURL(file);
    });
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // ADMISSION YEAR — sensible range
  // ═══════════════════════════════════════════════════════════════════════════

  const admYear = $('admissionYear');
  if (admYear) {
    const currentYear = new Date().getFullYear();
    admYear.setAttribute('min', '1990');
    admYear.setAttribute('max', String(currentYear));
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // SUBMIT BUTTON — loading state
  // ═══════════════════════════════════════════════════════════════════════════

  const form      = $('memberForm');
  const submitBtn = $('submitBtn');

  form?.addEventListener('submit', () => {
    if (submitBtn) {
      submitBtn.disabled  = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
    }
  });


  // ═══════════════════════════════════════════════════════════════════════════
  // DELETE — inherited from members.js (initMemberDelete already called)
  // ═══════════════════════════════════════════════════════════════════════════
  // initMemberDelete() is called by members.js on DOMContentLoaded,
  // so .delete-member-btn already has its listener. Nothing extra needed here.

});
