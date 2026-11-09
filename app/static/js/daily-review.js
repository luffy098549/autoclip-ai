"use strict";
// Private, read-only daily clip review. Never schedules or publishes media.
document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("daily-review");
  if (!root) return;
  const status = document.getElementById("daily-review-status");
  const gallery = document.getElementById("daily-review-gallery");
  const refresh = document.getElementById("daily-review-refresh");
  const limit = document.getElementById("daily-review-limit");
  const empty = document.createElement("p");
  empty.className = "muted";

  async function load() {
    refresh.disabled = true;
    status.textContent = "Buscando los mejores clips autorizados…";
    gallery.replaceChildren();
    try {
      const response = await fetch("/api/review/daily?limit=" + encodeURIComponent(limit.value), {
        headers: {"Accept": "application/json"}, credentials: "same-origin", cache: "no-store"
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      status.textContent = data.count + " de " + data.target + " clips disponibles para revisión manual";
      if (!data.items.length) {
        empty.textContent = "Todavía no hay clips listos, puntuados y con derechos verificados.";
        gallery.append(empty);
        return;
      }
      for (const item of data.items) {
        const card = document.createElement("article");
        card.className = "daily-review-card";
        const heading = document.createElement("h3");
        heading.textContent = "Clip #" + item.clip_id + " · " + item.score.toFixed(1) + " puntos";
        const details = document.createElement("p");
        details.className = "muted";
        details.textContent = "Fuente #" + item.source_id + " · " + item.start.toFixed(1) + "–" + item.end.toFixed(1) + " s";
        const player = document.createElement("video");
        player.controls = true;
        player.preload = "none";
        player.playsInline = true;
        player.setAttribute("aria-label", "Vista previa del clip " + item.clip_id);
        player.src = item.preview_url;
        const download = document.createElement("a");
        download.className = "button ghost";
        download.href = item.download_url;
        download.textContent = "Descargar clip";
        card.append(heading, details, player, download);
        gallery.append(card);
      }
    } catch (error) {
      status.textContent = "No se pudo cargar la revisión diaria. Comprueba tu sesión y la base de datos.";
    } finally {
      refresh.disabled = false;
    }
  }
  refresh.addEventListener("click", load);
  limit.addEventListener("change", load);
  load();
});
