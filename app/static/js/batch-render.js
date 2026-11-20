"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("batch-render-form");
  if (!form) return;
  const input = document.getElementById("batch-render-ids");
  const feedback = document.getElementById("batch-render-feedback");
  const check = document.getElementById("batch-render-check");
  const submit = form.querySelector('button[type="submit"]');
  let taskId = null;

  const report = message => { feedback.textContent = message; };
  async function jsonRequest(url, options = {}) {
    const response = await fetch(url, {credentials: "same-origin", ...options});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Solicitud rechazada");
    return payload;
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const raw = input.value.trim().split(",").map(value => value.trim());
    if (raw.length < 1 || raw.length > 5 ||
        raw.some(value => !/^[1-9][0-9]*$/.test(value) || !Number.isSafeInteger(Number(value))) ||
        new Set(raw.map(Number)).size !== raw.length) {
      report("Introduce entre 1 y 5 IDs positivos, únicos y separados por comas.");
      return;
    }
    submit.disabled = true;
    check.hidden = true;
    taskId = null;
    report("Enviando lote al worker…");
    try {
      const payload = await jsonRequest("/api/clips/render-batch", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({clip_ids: raw.map(Number)})
      });
      taskId = payload.task_id;
      report("Lote encolado. Usa Consultar estado para comprobar el resultado.");
      check.hidden = false;
    } catch (error) {
      report("No se pudo encolar: " + error.message);
    } finally {
      submit.disabled = false;
    }
  });

  check.addEventListener("click", async () => {
    if (!taskId) return;
    check.disabled = true;
    try {
      const payload = await jsonRequest("/api/jobs/" + encodeURIComponent(taskId));
      const result = payload.result;
      const summary = result && typeof result === "object"
        ? " · Procesados: " + (result.processed_clip_ids || []).length +
          " · Fallidos: " + (result.failed_clip_ids || []).length +
          " · Omitidos: " + (result.skipped_clip_ids || []).length
        : "";
      report("Estado: " + payload.state + summary);
    } catch (error) {
      report("No se pudo consultar el trabajo: " + error.message);
    } finally {
      check.disabled = false;
    }
  });
});
