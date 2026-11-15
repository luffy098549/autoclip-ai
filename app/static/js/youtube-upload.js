"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("youtube-upload-form");
  if (!form) return;
  const select = document.getElementById("youtube-upload-clip");
  const feedback = document.getElementById("youtube-upload-feedback");
  const history = document.getElementById("youtube-upload-history");
  const submit = document.getElementById("youtube-upload-submit");
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const make = (tag, value) => {
    const el = document.createElement(tag);
    if (value !== undefined) el.textContent = value;
    return el;
  };
  async function json(url, options = {}) {
    const response = await fetch(url, {credentials: "same-origin", ...options});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Error HTTP " + response.status);
    return payload;
  }
  async function refresh() {
    const [clips, uploads] = await Promise.all([
      json("/api/clips"), json("/api/integrations/youtube/uploads")
    ]);
    const previous = select.value;
    select.replaceChildren(new Option("Selecciona un clip listo", ""));
    const blocked = new Set((uploads.items || []).map(x => Number(x.clip_id)));
    (clips.items || []).filter(x => x.status === "ready" && !blocked.has(Number(x.id)))
      .forEach(x => select.add(new Option("Clip #" + x.id + " · " + (x.end - x.start).toFixed(1) + " s", x.id)));
    if ([...select.options].some(x => x.value === previous)) select.value = previous;
    history.replaceChildren();
    if (!(uploads.items || []).length) {
      history.append(make("p", "Aún no hay subidas registradas desde el Dashboard."));
    }
    (uploads.items || []).forEach(item => {
      const line = make("div");
      line.className = "data-item";
      line.append(make("strong", "Clip #" + item.clip_id + " · " + item.state));
      if (item.url) {
        const a = make("a", "Abrir en YouTube");
        a.href = item.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        line.append(a);
      }
      history.append(line);
    });
  }
  document.getElementById("youtube-upload-refresh").addEventListener("click", () => {
    refresh().catch(e => feedback.textContent = e.message);
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const clipId = Number(select.value);
    if (!clipId || !document.getElementById("youtube-upload-confirm").checked) return;
    if (!window.confirm("¿Enviar el clip #" + clipId + " a YouTube como PRIVADO? Esta acción no se puede deshacer desde AutoClip AI.")) return;
    submit.disabled = true;
    feedback.textContent = "Subiendo video privado. No cierres esta página ni repitas la solicitud…";
    try {
      const result = await json("/api/integrations/youtube/upload-private", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
        body: JSON.stringify({
          clip_id: clipId,
          title: document.getElementById("youtube-upload-title").value,
          description: document.getElementById("youtube-upload-description").value,
          made_for_kids: document.getElementById("youtube-upload-kids").value === "true",
          confirm_private: true
        })
      });
      feedback.replaceChildren(make("span", "Subida completada. Privacidad solicitada: privada. "));
      const link = make("a", "Ver video");
      link.href = result.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      feedback.append(link);
      form.reset();
      await refresh();
    } catch (e) {
      feedback.textContent = e.message + " No repitas la subida sin revisar el historial y YouTube Studio.";
      await refresh().catch(() => {});
    } finally {
      submit.disabled = false;
    }
  });
  refresh().catch(e => feedback.textContent = e.message);
});
