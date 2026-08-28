document.addEventListener("DOMContentLoaded", function () {
  // ---- Dark mode ----
  const root = document.documentElement;
  const toggle = document.getElementById("darkToggle");
  const saved = localStorage.getItem("sms-theme");
  if (saved) root.setAttribute("data-bs-theme", saved);

  function applyIcon() {
    if (!toggle) return;
    const isDark = root.getAttribute("data-bs-theme") === "dark";
    toggle.innerHTML = isDark
      ? '<i class="fa-solid fa-sun"></i>'
      : '<i class="fa-solid fa-moon"></i>';
  }
  applyIcon();

  if (toggle) {
    toggle.addEventListener("click", function () {
      const current = root.getAttribute("data-bs-theme");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      localStorage.setItem("sms-theme", next);
      applyIcon();
    });
  }

  // ---- Show / hide password ----
  document.querySelectorAll(".pw-toggle").forEach(function (icon) {
    icon.addEventListener("click", function () {
      const targetId = icon.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) return;
      if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
      } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
      }
    });
  });
});
