(() => {
  document.querySelectorAll("[data-admin-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.adminTab;
      document.querySelectorAll("[data-admin-tab]").forEach(b => b.classList.toggle("active", b === btn));
      document.querySelectorAll("[data-admin-panel]").forEach(panel => panel.classList.toggle("d-none", panel.dataset.adminPanel !== name));
    });
  });
  const input = document.getElementById("photoInput");
  const preview = document.getElementById("photoPreview");
  const placeholder = document.getElementById("photoPlaceholder");
  if (input && preview) {
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      preview.src = URL.createObjectURL(file);
      preview.classList.remove("d-none");
      if (placeholder) placeholder.classList.add("d-none");
    });
  }
})();