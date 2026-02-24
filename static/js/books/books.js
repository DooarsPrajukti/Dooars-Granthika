/* ============================================================
   DOOARS GRANTHIKA — Books Module JS
   ============================================================ */

"use strict";

/* ── Animated Counter ── */
function animateCounter(el, target, duration) {
  duration = duration || 1400;
  var start = null;
  var step = function(ts) {
    if (!start) start = ts;
    var p = Math.min((ts - start) / duration, 1);
    el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
function initCounters() {
  var els = document.querySelectorAll("[data-count]");
  if (!els.length) return;
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        animateCounter(e.target, parseInt(e.target.dataset.count, 10));
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.4 });
  els.forEach(function(el) { io.observe(el); });
}

/* ── Progress Bars ── */
function initProgressBars() {
  var segs = document.querySelectorAll(".progress-segment[data-width]");
  if (!segs.length) return;
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        e.target.style.width = e.target.dataset.width + "%";
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });
  segs.forEach(function(s) { s.style.width = "0%"; io.observe(s); });
}

/* ── Live Search ── */
function initSearchFilter() {
  var inp  = document.getElementById("bookSearch");
  var rows = document.querySelectorAll(".books-table tbody tr");
  var noR  = document.getElementById("noResults");
  if (!inp || !rows.length) return;
  inp.addEventListener("input", function() {
    var q = inp.value.toLowerCase().trim();
    var v = 0;
    rows.forEach(function(r) {
      var m = !q || r.textContent.toLowerCase().includes(q);
      r.style.display = m ? "" : "none";
      if (m) v++;
    });
    if (noR) noR.style.display = v === 0 ? "block" : "none";
  });
}

/* ── Category Filter ── */
function initCategoryFilter() {
  var sel  = document.getElementById("categoryFilter");
  var rows = document.querySelectorAll(".books-table tbody tr");
  if (!sel || !rows.length) return;
  sel.addEventListener("change", function() {
    var v = sel.value.toLowerCase();
    rows.forEach(function(r) {
      if (!v) { r.style.display = ""; return; }
      var c = r.querySelector("[data-category]");
      r.style.display = (c && c.dataset.category.toLowerCase() === v) ? "" : "none";
    });
  });
}

/* ── Stock Filter ── */
function initStockFilter() {
  var sel  = document.getElementById("stockFilter");
  var rows = document.querySelectorAll(".books-table tbody tr");
  if (!sel || !rows.length) return;
  sel.addEventListener("change", function() {
    var v = sel.value;
    rows.forEach(function(r) {
      if (!v) { r.style.display = ""; return; }
      var b = r.querySelector(".badge");
      if (!b) return;
      var t = b.textContent.trim().toLowerCase();
      var m = (v === "available" && t.includes("available")) ||
              (v === "low-stock" && t.includes("low")) ||
              (v === "out-stock" && t.includes("out"));
      r.style.display = m ? "" : "none";
    });
  });
}

/* ── Table Sort ── */
function initTableSort() {
  var ths = document.querySelectorAll(".books-table thead th[data-sort]");
  ths.forEach(function(th) {
    th.addEventListener("click", function() {
      ths.forEach(function(h) { h.classList.remove("sorted"); });
      th.classList.add("sorted");
      var ic = th.querySelector(".sort-icon");
      if (ic) ic.textContent = ic.textContent === "▲" ? "▼" : "▲";
    });
  });
}

/* ── Row Hover ── */
function initRowHover() {
  document.querySelectorAll(".books-table tbody tr").forEach(function(r) {
    r.style.transition = "background .12s, transform .1s";
    r.addEventListener("mouseenter", function() { r.style.transform = "translateX(2px)"; });
    r.addEventListener("mouseleave", function() { r.style.transform = ""; });
  });
}

/* ── Staggered Entrance ── */
function initStagger() {
  document.querySelectorAll(".ani").forEach(function(c, i) {
    c.style.opacity = "0";
    c.style.transform = "translateY(14px)";
    c.style.transition = "opacity .34s ease " + (i * 0.05) + "s, transform .34s ease " + (i * 0.05) + "s";
    requestAnimationFrame(function() {
      c.style.opacity = "1";
      c.style.transform = "";
    });
  });
}

/* ── Form Validation ── */
function initFormValidation() {
  var form = document.getElementById("bookForm");
  if (!form) return;

  var totalEl     = document.getElementById("id_total_copies");
  var availEl     = document.getElementById("id_available_copies");
  var issuedHint  = document.getElementById("issuedCopiesHint");
  var issuedCount = document.getElementById("issuedCopiesCount");

  /* Keep available's max and the issued-copies hint in sync whenever
     either copies field changes. */
  function syncCopies() {
    if (!totalEl || !availEl) return;

    var total = parseInt(totalEl.value, 10);
    var avail = parseInt(availEl.value, 10);

    // Update the browser-enforced max so the up-arrow can't go past total
    if (!isNaN(total) && total >= 0) {
      availEl.max = total;
    } else {
      availEl.removeAttribute("max");
    }

    // Show issued-copies hint
    if (!isNaN(total) && !isNaN(avail) && total >= 0 && avail >= 0) {
      var issued = Math.max(0, total - avail);
      if (issuedCount) issuedCount.textContent = issued;
      if (issuedHint)  issuedHint.style.display = issued > 0 ? "block" : "none";
    } else {
      if (issuedHint) issuedHint.style.display = "none";
    }

    // Re-validate available if it was already marked invalid
    if (availEl.classList.contains("is-invalid")) validateCopies();
  }

  function validateCopies() {
    if (!totalEl || !availEl) return true;
    var total = parseInt(totalEl.value, 10);
    var avail = parseInt(availEl.value, 10);
    var ok = !isNaN(avail) && avail >= 0 && (isNaN(total) || avail <= total);
    availEl.classList.toggle("is-invalid", !ok);
    availEl.classList.toggle("is-valid",    ok);
    return ok;
  }

  if (totalEl) {
    totalEl.addEventListener("input", syncCopies);
    totalEl.addEventListener("change", syncCopies);
  }
  if (availEl) {
    availEl.addEventListener("input", syncCopies);
    availEl.addEventListener("change", syncCopies);
    availEl.addEventListener("blur", validateCopies);
  }

  // Run once on page load so the hint/max are set when editing an existing book
  syncCopies();

  var fields = form.querySelectorAll("[required]");
  fields.forEach(function(f) {
    f.addEventListener("blur",  function() { validate(f); });
    f.addEventListener("input", function() { if (f.classList.contains("is-invalid")) validate(f); });
  });

  form.addEventListener("submit", function(e) {
    var ok = true;
    fields.forEach(function(f) { if (!validate(f)) ok = false; });
    if (!validateCopies()) ok = false;

    if (!ok) {
      e.preventDefault();
      // Scroll to first error
      var first = form.querySelector(".is-invalid");
      if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    // Valid — show spinner and let the form submit normally (no fake delay)
    var btn = form.querySelector("[type=submit]");
    if (btn) {
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
      btn.disabled  = true;
    }
  });
}

function validate(f) {
  var v  = f.value.trim();
  var ok = v.length > 0;
  if (f.type === "number" && ok) {
    var num = parseFloat(v);
    ok = !isNaN(num) && num >= 0;
    // also honour the browser max attribute
    if (ok && f.max !== "" && !isNaN(parseFloat(f.max))) {
      ok = num <= parseFloat(f.max);
    }
  }
  f.classList.toggle("is-invalid", !ok);
  f.classList.toggle("is-valid",   ok);
  return ok;
}

/* ── Delete Animation ── */
function initDeleteAnim() {
  var c = document.querySelector(".delete-card");
  if (!c) return;
  c.style.opacity = "0";
  c.style.transform = "scale(.96) translateY(16px)";
  c.style.transition = "opacity .4s, transform .4s";
  requestAnimationFrame(function() { c.style.opacity = "1"; c.style.transform = ""; });
}

/* ── Refresh Button ── */
function initRefreshBtn() {
  var btn = document.getElementById("refreshBtn");
  if (!btn) return;
  btn.addEventListener("click", function() {
    var ic = btn.querySelector("i");
    ic.style.transition = "transform .6s ease";
    ic.style.transform = "rotate(360deg)";
    setTimeout(function() { ic.style.transform = ""; ic.style.transition = ""; }, 650);
  });
}

document.addEventListener("DOMContentLoaded", function() {
  initCounters();
  initProgressBars();
  initSearchFilter();
  initCategoryFilter();
  initStockFilter();
  initTableSort();
  initRowHover();
  initStagger();
  initFormValidation();
  initDeleteAnim();
  initRefreshBtn();
});