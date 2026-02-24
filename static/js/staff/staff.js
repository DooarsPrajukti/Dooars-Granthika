/* ============================================================
   staff.js  —  Dooars Granthika Staff Module
   Handles: delete modal, photo preview
   ============================================================ */

/* ── Delete Modal ─────────────────────────────────────────── */
function confirmDelete(name, url) {
  document.getElementById('modal-body-text').textContent =
    `Are you sure you want to remove ${name}? This action cannot be undone.`;
  document.getElementById('delete-form').action = url;
  document.getElementById('delete-modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('delete-modal').style.display = 'none';
}

const deleteModal = document.getElementById('delete-modal');
if (deleteModal) {
  deleteModal.addEventListener('click', function (e) {
    if (e.target === this) closeModal();
  });
}

/* ── Live Photo Preview ───────────────────────────────────── */
const photoUpload = document.getElementById('photo-upload');
if (photoUpload) {
  photoUpload.addEventListener('change', function () {
    const file = this.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
      let preview = document.getElementById('photo-preview');

      if (preview.tagName !== 'IMG') {
        const img = document.createElement('img');
        img.id        = 'photo-preview';
        img.className = 'avatar-img';
        img.alt       = 'Photo preview';
        preview.replaceWith(img);
        preview = img;
      }

      preview.src = e.target.result;
    };

    reader.readAsDataURL(file);
  });
}