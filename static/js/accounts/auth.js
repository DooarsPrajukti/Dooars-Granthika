/**
 * Authentication JavaScript
 * Combined from login.html and register.html
 */

// ===========================
// Email validation regex
// ===========================
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ===========================
// Message Display Functions
// ===========================
function showMessage(message, type = "success") {
  const msgBox = document.getElementById("status-msg");
  if (msgBox) {
    msgBox.textContent = message;
    msgBox.className = `status ${type}`;
    
    // Auto-hide after 8 seconds for success messages
    if (type === "success") {
      setTimeout(() => {
        msgBox.textContent = "";
        msgBox.className = "status";
      }, 8000);
    } else {
      // Hide error messages after 5 seconds
      setTimeout(() => {
        msgBox.textContent = "";
        msgBox.className = "status";
      }, 5000);
    }
  }
}

// ===========================
// Login Function (for PyWebView)
// ===========================
async function login() {
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const savePasswordCheckbox = document.getElementById("savePassword");
  const loginBtn = document.getElementById("loginBtn");
  const btnText = loginBtn ? loginBtn.querySelector(".btn-text") : null;
  const spinner = loginBtn ? loginBtn.querySelector(".loading-spinner") : null;

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();
  const savePassword = savePasswordCheckbox ? savePasswordCheckbox.checked : false;

  if (!username || !password) {
    showMessage("⚠️ Please enter User ID and Password!", "warning");
    return;
  }

  if (btnText) btnText.textContent = "Logging in...";
  if (spinner) spinner.style.display = "inline-block";
  if (loginBtn) loginBtn.disabled = true;

  try {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.login) {
      const response = await window.pywebview.api.login(username, password, savePassword);

      if (response === true) {
        showMessage("✅ Login Successful!", "success");
      } else {
        showMessage("❌ Login Failed: " + response, "error");
      }
    } else {
      // Fallback for Django - submit form normally
      const form = document.getElementById("loginForm");
      if (form) {
        form.submit();
      }
    }
  } catch (error) {
    console.error("Error during login:", error);
    showMessage("❌ Login Error: " + error.message, "error");
  } finally {
    if (btnText) btnText.textContent = "Sign In";
    if (spinner) spinner.style.display = "none";
    if (loginBtn) loginBtn.disabled = false;
  }
}

// ===========================
// Field Validation for Register
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
  
  if (isValid) {
    group.classList.remove("error");
    group.classList.add("success");
  } else {
    group.classList.remove("success");
    group.classList.add("error");
  }
  
  return isValid;
}

// ===========================
// Validate Registration Form
// ===========================
function validateForm() {
  const fieldIds = [
    "libraryName", "instituteName", "instituteEmail", 
    "address", "district", "state", "country", 
    "latefine", "borrowingPeriod", "AlottedBooks"
  ];
  
  let isFormValid = true;
  
  fieldIds.forEach(fieldId => {
    if (!validateField(fieldId)) {
      isFormValid = false;
    }
  });
  
  return isFormValid;
}

// ===========================
// Register Function
// ===========================
async function register() {
  const registerBtn = document.getElementById("registerBtn");
  
  // Validate form first
  if (!validateForm()) {
    showMessage("⚠️ Please fix the errors above before submitting.", "error");
    return;
  }

  // Show loading state
  registerBtn.disabled = true;
  registerBtn.classList.add("loading");
  const btnText = registerBtn.querySelector(".btn-text");
  btnText.textContent = "Registering...";

  const data = {
    libraryName: document.getElementById("libraryName").value.trim(),
    instituteName: document.getElementById("instituteName").value.trim(),
    instituteEmail: document.getElementById("instituteEmail").value.trim(),
    address: document.getElementById("address").value.trim(),
    district: document.getElementById("district").value.trim(),
    state: document.getElementById("state").value.trim(),
    country: document.getElementById("country").value.trim(),
    latefine: document.getElementById("latefine").value.trim(),
    borrowingPeriod: document.getElementById("borrowingPeriod").value.trim(),
    AlottedBooks: document.getElementById("AlottedBooks").value.trim()
  };

  try {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.submit_registration) {
      const response = await window.pywebview.api.submit_registration(data);
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
        showMessage(`⚠️ Registration failed: ${response.message || 'Unknown error'}`, "error");
      }
    } else {
      // Fallback - submit form normally for Django
      const form = document.getElementById("registrationForm");
      if (form) {
        form.submit();
        return;
      }
    }
  } catch (error) {
    console.error("Error during registration:", error);
    showMessage("❌ Registration failed. Please try again.", "error");
  }

  resetButton();
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
// Clear Form Fields
// ===========================
function clearFields() {
  const fieldIds = [
    "libraryName", "instituteName", "instituteEmail", 
    "address", "district", "state", "country", 
    "latefine", "borrowingPeriod", "AlottedBooks"
  ];
  
  fieldIds.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    const group = document.getElementById(fieldId + "-group");
    if (field) {
      field.value = "";
    }
    if (group) {
      group.classList.remove("error", "success");
    }
  });
}

// ===========================
// Go Back Function (for PyWebView)
// ===========================
function goBack() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.go_back) {
    window.pywebview.api.go_back();
  } else {
    window.history.back();
  }
}

// ===========================
// Forgot Password Function (for PyWebView)
// ===========================
function ForgotPassword() {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.forget_password) {
    window.pywebview.api.forget_password();
  } else {
    // Fallback - will be handled by href in Django template
    console.log("Forgot password clicked");
  }
}

// ===========================
// Initialize on Page Load
// ===========================
document.addEventListener("DOMContentLoaded", function() {
  console.log("Auth script loaded");
  
  // ===========================
  // Login Form Handling
  // ===========================
  const loginBtn = document.getElementById("loginBtn");
  if (loginBtn && window.pywebview) {
    loginBtn.addEventListener("click", function(e) {
      e.preventDefault();
      login();
    });
  }

  // ===========================
  // Registration Form Handling
  // ===========================
  const fieldIds = [
    "libraryName", "instituteName", "instituteEmail", 
    "address", "district", "state", "country", 
    "latefine", "borrowingPeriod", "AlottedBooks"
  ];
  
  fieldIds.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (field) {
      field.addEventListener("blur", () => validateField(fieldId));
      field.addEventListener("input", () => {
        const group = document.getElementById(fieldId + "-group");
        if (group && group.classList.contains("error")) {
          validateField(fieldId);
        }
      });
    }
  });

  // Form submission for registration
  const registrationForm = document.getElementById("registrationForm");
  if (registrationForm) {
    registrationForm.addEventListener("submit", function(e) {
      e.preventDefault();
      register();
    });
  }

  // ===========================
  // Forgot Password Form Handling
  // ===========================
  const forgotForm = document.getElementById("forgotPasswordForm");
  const emailInput = document.getElementById("email");
  
  if (emailInput && forgotForm) {
    // Real-time email validation
    emailInput.addEventListener("input", function() {
      const email = this.value.trim();
      const hint = this.parentElement.nextElementSibling;
      
      if (!hint) return;
      
      if (email.length === 0) {
        this.style.borderColor = "var(--border)";
        hint.style.color = "var(--text-secondary)";
        hint.textContent = "Enter the email associated with your account";
      } else if (!emailRegex.test(email)) {
        this.style.borderColor = "var(--error)";
        hint.style.color = "var(--error)";
        hint.textContent = "Please enter a valid email address";
      } else {
        this.style.borderColor = "var(--success)";
        hint.style.color = "var(--success)";
        hint.textContent = "Email format is valid";
      }
    });
    
    // Form submit handler
    forgotForm.addEventListener("submit", function(e) {
      const email = emailInput.value.trim();
      
      if (!email || !emailRegex.test(email)) {
        e.preventDefault();
        showMessage("Please enter a valid email address", "error");
        return false;
      }
    });
  }
});