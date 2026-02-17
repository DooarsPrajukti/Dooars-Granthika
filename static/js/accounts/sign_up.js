/**
 * Sign Up / Registration Authentication
 */

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const FIELD_IDS = [
  "libraryName", "instituteName", "instituteEmail",
  "address", "district", "state", "country",
  "latefine", "borrowingPeriod", "AlottedBooks"
];

// ===========================
// Message Display
// ===========================
function showMessage(message, type = "success") {
  const msgBox = document.getElementById("status-msg");
  if (msgBox) {
    msgBox.textContent = message;
    msgBox.className = `status ${type}`;
    setTimeout(() => {
      msgBox.textContent = "";
      msgBox.className = "status";
    }, type === "success" ? 8000 : 5000);
  }
}

// ===========================
// Field Validation
// ===========================
function validateField(fieldId) {
  const field = document.getElementById(fieldId);
  const group = document.getElementById(fieldId + "-group");

  if (!field || !group) return true;

  const value = field.value.trim();
  let isValid = true;

  if (!value) {
    isValid = false;
  } else if (fieldId === "instituteEmail" && !emailRegex.test(value)) {
    isValid = false;
  } else if (fieldId === "latefine") {
    const num = parseFloat(value);
    isValid = !isNaN(num) && num >= 0;
  } else if (fieldId === "borrowingPeriod") {
    const num = parseInt(value);
    isValid = !isNaN(num) && num >= 1 && num <= 365;
  } else if (fieldId === "AlottedBooks") {
    const num = parseInt(value);
    isValid = !isNaN(num) && num >= 1 && num <= 50;
  }

  group.classList.toggle("error", !isValid);
  group.classList.toggle("success", isValid);

  return isValid;
}

// ===========================
// Validate Full Form
// ===========================
function validateForm() {
  return FIELD_IDS.every(id => validateField(id));
}

// ===========================
// Collect Form Data
// ===========================
function collectFormData() {
  return Object.fromEntries(
    FIELD_IDS.map(id => [id, document.getElementById(id)?.value.trim() ?? ""])
  );
}

// ===========================
// Clear Form Fields
// ===========================
function clearFields() {
  FIELD_IDS.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    const group = document.getElementById(fieldId + "-group");
    if (field) field.value = "";
    if (group) group.classList.remove("error", "success");
  });
}

// ===========================
// Reset Button State
// ===========================
function resetButton() {
  const registerBtn = document.getElementById("registerBtn");
  if (!registerBtn) return;
  const btnText = registerBtn.querySelector(".btn-text");
  registerBtn.disabled = false;
  registerBtn.classList.remove("loading");
  if (btnText) btnText.textContent = "Create Library Account";
}

// ===========================
// Register
// ===========================
async function register() {
  if (!validateForm()) {
    showMessage("⚠️ Please fix the errors above before submitting.", "error");
    return;
  }

  const registerBtn = document.getElementById("registerBtn");
  const btnText = registerBtn?.querySelector(".btn-text");

  if (registerBtn) registerBtn.disabled = true;
  if (registerBtn) registerBtn.classList.add("loading");
  if (btnText) btnText.textContent = "Registering...";

  try {
    if (window.pywebview?.api?.submit_registration) {
      const response = await window.pywebview.api.submit_registration(collectFormData());
      console.log("Registration response:", response);

      if (response.check_internet === false) {
        showMessage("⚠️ No internet connection. Please check your network settings.", "error");
      } else if (response.valid_email === false) {
        showMessage("⚠️ Invalid email structure.", "error");
      } else if (response.is_valid === false) {
        showMessage("⚠️ Invalid or duplicate email.", "error");
      } else if (response.Status === true) {
        showMessage("✅ Registration successful!\n\n📁 Check the Downloads folder for Excel templates.", "success");
        clearFields();
      } else {
        showMessage(`⚠️ Registration failed: ${response.message || "Unknown error"}`, "error");
      }
    } else {
      // Django fallback — submit form normally
      document.getElementById("registrationForm")?.submit();
      return;
    }
  } catch (error) {
    console.error("Registration error:", error);
    showMessage("❌ Registration failed. Please try again.", "error");
  }

  resetButton();
}

// ===========================
// Go Back (PyWebView)
// ===========================
function goBack() {
  if (window.pywebview?.api?.go_back) {
    window.pywebview.api.go_back();
  } else {
    window.history.back();
  }
}

// ===========================
// Init
// ===========================
document.addEventListener("DOMContentLoaded", function () {
  console.log("sign_up.js loaded");

  // Attach blur + live validation to all fields
  FIELD_IDS.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.addEventListener("blur", () => validateField(fieldId));
    field.addEventListener("input", () => {
      const group = document.getElementById(fieldId + "-group");
      if (group?.classList.contains("error")) validateField(fieldId);
    });
  });

  // Registration form submit
  document.getElementById("registrationForm")
    ?.addEventListener("submit", function (e) {
      e.preventDefault();
      register();
    });
});