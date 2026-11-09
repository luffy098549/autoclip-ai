"use strict";
document.addEventListener("DOMContentLoaded", async () => {
  const toggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      const open = sidebar.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    sidebar.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
      sidebar.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }));
  }

  if (document.querySelector("[data-stat]")) {
    const message = document.getElementById("summary-message");
    try {
      const response = await fetch("/api/summary", {headers: {"Accept": "application/json"}});
      if (!response.ok) throw new Error("Error HTTP " + response.status);
      const payload = await response.json();
      Object.entries(payload.counts || {}).forEach(([key, value]) => {
        const target = document.querySelector('[data-stat="' + key + '"]');
        if (target) target.textContent = Number(value).toLocaleString("es");
      });
      if (message) message.textContent = payload.message || "";
    } catch (error) {
      if (message) message.textContent = "No se pudo consultar la base de datos.";
    }
  }
});
