/**
 * members/member_add.js
 * ─────────────────────
 * Add-member page specific JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * Responsibilities:
 *   - Role card selection + dynamic section show/hide
 *   - Select-or-create mutual exclusivity (dept / course / year / semester)
 *   - Phone & email field validation
 *   - Photo drag-and-drop upload preview
 *   - Disable hidden department selects before submit
 *   - DOB max-date enforcement
 *   - Submit button loading state
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── helpers ──────────────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  function setName(el, name) { if (el) el.name = name; }


  // ═══════════════════════════════════════════════════════════════════════════
  // ROLE SWITCHING
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Show sections relevant to `role`, hide all others.
   * Also swaps the status <select> name so only the visible one POSTs,
   * and disables hidden department dropdowns.
   */
  function applyRole(role) {

    // Show/hide role-gated blocks
    document.querySelectorAll('.student-only').forEach(el => {
      el.style.display = (role === 'student') ? '' : 'none';
    });
    document.querySelectorAll('.teacher-only').forEach(el => {
      el.style.display = (role === 'teacher') ? '' : 'none';
    });
    document.querySelectorAll('.general-only').forEach(el => {
      el.style.display = (role === 'general') ? '' : 'none';
    });

    // Status select swap — only the visible one should POST name="status"
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

    // Disable hidden department selects so duplicate name="department" doesn't POST
    const deptStudent = $('department');
    const deptTeacher = $('department_teacher');
    const deptGeneral = $('orgDept');
    if (deptStudent) deptStudent.disabled = (role !== 'student');
    if (deptTeacher) deptTeacher.disabled = (role !== 'teacher');
    if (deptGeneral) deptGeneral.disabled = (role !== 'general');

    // Highlight the selected role card
    document.querySelectorAll('.role-option').forEach(opt => {
      opt.classList.toggle('selected', opt.dataset.role === role);
    });
  }

  // Wire role cards
  document.querySelectorAll('.role-option').forEach(label => {
    label.addEventListener('click', function () {
      const radio = this.querySelector('input[type="radio"]');
      if (radio) { radio.checked = true; applyRole(radio.value); }
    });
  });

  // Apply initial state (default: student)
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
  // PHOTO UPLOAD — drag-and-drop + file input + preview + remove
  // ═══════════════════════════════════════════════════════════════════════════

  const dropZone   = $('photoDropZone');
  const fileInput  = $('memberPhoto');
  const previewBox = $('photoPreviewBox');
  const previewImg = $('photoPreviewImg');
  const removeBtn  = $('photoRemoveBtn');

  function showPhotoPreview(file) {
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
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewBox.style.display = 'block';
      previewBox.classList.add('active');
    };
    reader.readAsDataURL(file);
  }

  fileInput?.addEventListener('change', () => showPhotoPreview(fileInput.files[0]));

  if (dropZone) {
    dropZone.addEventListener('dragover',  (e) => { e.preventDefault(); dropZone.style.borderColor = '#3b82f6'; });
    dropZone.addEventListener('dragleave', ()  => { dropZone.style.borderColor = ''; });
    dropZone.addEventListener('drop',      (e) => {
      e.preventDefault();
      dropZone.style.borderColor = '';
      const file = e.dataTransfer.files[0];
      if (file && fileInput) {
        // DataTransfer isn't assignable cross-browser via .files; use workaround
        try {
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
        } catch (_) { /* Safari fallback: preview only */ }
        showPhotoPreview(file);
      }
    });
  }

  removeBtn?.addEventListener('click', () => {
    if (fileInput) fileInput.value = '';
    if (previewImg) previewImg.src = '';
    if (previewBox) { previewBox.style.display = 'none'; previewBox.classList.remove('active'); }
  });


  // ═══════════════════════════════════════════════════════════════════════════
  // ADMISSION YEAR — sensible range
  // ═══════════════════════════════════════════════════════════════════════════

  const admYear = $('admissionYear');
  if (admYear) {
    const currentYear = new Date().getFullYear();
    admYear.setAttribute('min', '1990');
    admYear.setAttribute('max', String(currentYear));
    admYear.setAttribute('placeholder', `e.g. ${currentYear}`);
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

});


/* ── Pass institute_type to member_add.js so role switching stays correct ── */
window.INSTITUTE_TYPE = "{{ institute_type|escapejs }}";

(function () {
  /*
   * Role-based field visibility and label changes.
   * For private institutes: student-field / teacher fields are visible.
   * For non-private: only general-field is rendered (server-side).
   * This block handles JS-driven switching between student ↔ teacher
   * (only relevant for private institutes).
   */

  var IS_PRIVATE = (window.INSTITUTE_TYPE === 'private');

  var SECTION_TITLES = {
    student: "Academic Information",
    teacher: "Professional Information",
    general: "Additional Information",
  };

  var ROLE_LABELS = {
    "roll-label":  { student: "Roll Number",             teacher: "Employee ID",             general: "Government ID" },
    "spec-label":  { student: "Specialization / Subject", teacher: "Designation / Post",     general: "Occupation"    },
    "notes-label": { student: "Notes / Remarks",          teacher: "Notes / Remarks",         general: "Notes / Remarks" },
    "dept-star":   { student: "*",                        teacher: "*",                       general: ""              },
  };

  var ROLE_PLACEHOLDERS = {
    "rollNumber":     { student: "e.g. CS2024001",                  teacher: "e.g. EMP-2024-001",              general: "Aadhaar / Voter ID / PAN…"     },
    "specialization": { student: "e.g. Machine Learning, Finance…",  teacher: "e.g. Assistant Professor, HOD…", general: "e.g. Farmer, Govt. Teacher…"    },
  };

  function applyRole(role) {
    // Section heading
    var titleEl = document.getElementById("academicSectionTitle");
    if (titleEl) titleEl.textContent = SECTION_TITLES[role] || "Academic Information";

    // student-field blocks (course, year, semester, admission year)
    // Only exist in the DOM for private institutes
    document.querySelectorAll(".student-field").forEach(function (el) {
      el.style.display = (role === "student") ? "" : "none";
    });

    // Guardian phone wrapper — student only, only rendered for private
    var guardianWrapper = document.getElementById("guardian-phone-wrapper");
    if (guardianWrapper) guardianWrapper.style.display = (role === "student") ? "" : "none";

    // Dynamic labels
    Object.keys(ROLE_LABELS).forEach(function (id) {
      var el = document.getElementById(id);
      if (el && ROLE_LABELS[id][role] !== undefined) {
        el.textContent = ROLE_LABELS[id][role];
      }
    });

    // Dynamic placeholders
    Object.keys(ROLE_PLACEHOLDERS).forEach(function (id) {
      var el = document.getElementById(id);
      if (el && ROLE_PLACEHOLDERS[id][role]) {
        el.placeholder = ROLE_PLACEHOLDERS[id][role];
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Card click → highlight + apply
    document.querySelectorAll(".role-option").forEach(function (label) {
      label.addEventListener("click", function () {
        document.querySelectorAll(".role-option").forEach(function (l) {
          l.classList.remove("selected");
        });
        this.classList.add("selected");
        applyRole(this.dataset.role);
      });
    });

    // On page load — apply the already-checked role
    var checked = document.querySelector('input[name="role"]:checked');
    if (checked) applyRole(checked.value);
  });
})();