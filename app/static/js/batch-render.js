"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("batch-render-form");
  if (!form) return;
  const input = document.getElementById("batch-render-ids");
  const feedback = document.getElementById("batch-render-feedback");
  const check = document.getElementById("batch-render-check");
  const submit = form.querySelector('button[type="submit"]');
  let taskId = null;
  const refreshLibrary = () => {
    const refresh = document.getElementById("library-refresh");
    if (refresh) refresh.click();
  };

  const report = message => { feedback.textContent = message; };
  async function jsonRequest(url, options = {}) {
    const response = await fetch(url, {credentials: "same-origin", ...options});
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;
    if (!response.ok) {
      const message = payload && typeof payload.error === "string"
        ? payload.error : "Solicitud rechazada (HTTP " + response.status + ")";
      throw new Error(message);
    }
    if (!payload || typeof payload !== "object") {
      throw new Error("Respuesta inesperada del servidor");
    }
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
      if (typeof payload.task_id !== "string" || !/^[0-9a-f-]{36}$/i.test(payload.task_id)) {
        throw new Error("El servidor no devolvió un identificador de tarea válido");
      }
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
      if (typeof payload.state !== "string") throw new Error("Estado de trabajo inválido");
      const result = payload.result;
      const summary = result && typeof result === "object"
        ? " · Procesados: " + (Array.isArray(result.processed_clip_ids) ? result.processed_clip_ids.length : 0) +
          " · Fallidos: " + (Array.isArray(result.failed_clip_ids) ? result.failed_clip_ids.length : 0) +
          " · Omitidos: " + (Array.isArray(result.skipped_clip_ids) ? result.skipped_clip_ids.length : 0) +
          " · Sin autorización: " + (Array.isArray(result.unauthorized_clip_ids) ? result.unauthorized_clip_ids.length : 0)
        : "";
      report("Estado: " + payload.state + summary +
        (payload.state === "FAILURE" ? " · El worker informó un fallo." : ""));
      if (payload.state === "SUCCESS" || payload.state === "FAILURE" || payload.state === "REVOKED") {
        check.hidden = true;
        if (payload.state === "SUCCESS") refreshLibrary();
      }
    } catch (error) {
      report("No se pudo consultar el trabajo: " + error.message);
    } finally {
      check.disabled = false;
    }
  });
});
