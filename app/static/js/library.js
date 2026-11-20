"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const gallery=document.getElementById("clip-gallery");
  if(!gallery) return;
  const search=document.getElementById("library-search");
  const filter=document.getElementById("library-filter");
  const count=document.getElementById("library-count");
  let clips=[];
  const selectedForBatch = new Set();
  let transferredSelection = "";
  const batchInput = document.getElementById("batch-render-ids");
  const batchFeedback = document.getElementById("batch-render-feedback");
  const eligible = new Set(["draft", "failed", "awaiting_worker"]);
  const selectionBar = document.createElement("div");
  selectionBar.className = "library-toolbar";
  const selectionStatus = document.createElement("span");
  selectionStatus.setAttribute("aria-live", "polite");
  const transferButton = document.createElement("button");
  transferButton.type = "button";
  transferButton.className = "button ghost";
  transferButton.textContent = "Enviar selección al formulario";
  selectionBar.append(selectionStatus, transferButton);
  if (batchInput) gallery.before(selectionBar);
  function invalidateTransferredSelection() {
    if (!batchInput || !transferredSelection) return;
    // A changed checkbox selection must never leave a stale batch ready to submit.
    if (batchInput.value === transferredSelection) {
      batchInput.value = "";
      if (batchFeedback) batchFeedback.textContent = "La selección cambió. Transfiere de nuevo los clips antes de procesar.";
    }
    transferredSelection = "";
  }
  function updateSelection() {
    selectionStatus.textContent = selectedForBatch.size + " de 5 clips seleccionados";
    transferButton.disabled = selectedForBatch.size === 0;
  }
  transferButton.addEventListener("click", () => {
    if (!batchInput || selectedForBatch.size === 0) return;
    batchInput.value = Array.from(selectedForBatch).join(", ");
    transferredSelection = batchInput.value;
    if (batchFeedback) batchFeedback.textContent = "Selección preparada. Confirma Procesar lote para encolarla.";
    batchInput.focus();
  });
  updateSelection();
  const statusLabels={
    ready:"Listo",failed:"Fallido",processing:"Procesando",
    awaiting_worker:"En espera",queued:"En cola",draft:"Borrador",
    rejected:"Rechazado"
  };

  function node(tag,text,cls){
    const e=document.createElement(tag);
    if(text!==undefined)e.textContent=text;
    if(cls)e.className=cls;
    return e;
  }

  function render(){
    const term=(search.value||"").trim().toLowerCase();
    const state=filter.value;
    const matching=clips.filter(c=>{
      return (!state||c.status===state)&&(
        !term||String(c.id).includes(term)||String(c.source_id).includes(term)
      );
    });
    for (const id of selectedForBatch) {
      if (!clips.some(c => c.id === id && eligible.has(c.status))) selectedForBatch.delete(id);
    }
    updateSelection();
    // Never submit IDs that became ineligible after a library refresh.
    if (batchInput && transferredSelection && batchInput.value === transferredSelection) {
      const validIds = new Set(Array.from(selectedForBatch).map(String));
      const transferredIds = transferredSelection.split(",").map(value => value.trim());
      if (transferredIds.some(id => !validIds.has(id))) {
        batchInput.value = "";
        transferredSelection = "";
        if (batchFeedback) batchFeedback.textContent = "La selección cambió. Vuelve a transferir los clips elegibles antes de procesar.";
      }
    }
    gallery.replaceChildren();
    count.textContent=matching.length+" clips mostrados";
    if(!matching.length){
      gallery.append(node("p","No hay clips que coincidan con los filtros.","muted"));
      return;
    }
    matching.forEach(item=>{
      const card=node("article",undefined,"clip-card");
      const top=node("div",undefined,"clip-media");
      if(item.status==="ready"){
        const video=node("video");
        video.src="/api/clips/"+item.id+"/preview";
        video.controls=true;
        video.preload="none";
        video.playsInline=true;
        video.setAttribute("aria-label","Vista previa de clip "+item.id);
        top.append(video);
      }else{
        top.append(node("div",statusLabels[item.status]||item.status,"clip-placeholder"));
      }
      const body=node("div",undefined,"clip-card-body");
      body.append(
        node("strong","Clip #"+item.id),
        node("span","Origen #"+item.source_id+" · "+
          (item.end-item.start).toFixed(1)+" segundos","clip-meta"),
        node("span",statusLabels[item.status]||item.status,"clip-state")
      );
      if(item.score!==null&&item.score!==undefined){
        body.append(node("span","Puntuación preliminar: "+item.score,"clip-meta"));
      }
      if(item.status==="ready"){
        const links=node("div",undefined,"clip-actions");
        const mp4=node("a","Descargar MP4","button");
        mp4.href="/api/clips/"+item.id+"/download";
        links.append(mp4);
        if(item.has_subtitles){
          const srt=node("a","Subtítulos SRT","button ghost");
          srt.href="/api/clips/"+item.id+"/subtitles";
          links.append(srt);
        }
        body.append(links);
      }
      if (batchInput && eligible.has(item.status)) {
        const label = node("label", undefined, "clip-meta");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedForBatch.has(item.id);
        checkbox.setAttribute("aria-label", "Seleccionar clip " + item.id + " para lote");
        checkbox.addEventListener("change", () => {
          if (checkbox.checked && selectedForBatch.size >= 5) {
            checkbox.checked = false;
            selectionStatus.textContent = "Máximo cinco clips por lote.";
            return;
          }
          if (checkbox.checked) selectedForBatch.add(item.id);
          else selectedForBatch.delete(item.id);
          invalidateTransferredSelection();
          updateSelection();
        });
        label.append(checkbox, document.createTextNode(" Seleccionar para lote"));
        body.append(label);
      }
      card.append(top,body);
      gallery.append(card);
    });
  }

  async function reload(){
    const response=await fetch("/api/clips",{credentials:"same-origin"});
    if(!response.ok)throw new Error("No se pudo cargar la biblioteca");
    const data=await response.json();
    clips=data.items||[];
    render();
  }
  search.addEventListener("input",render);
  filter.addEventListener("change",render);
  document.getElementById("library-refresh")?.addEventListener("click",()=>{
    reload().catch(err=>{count.textContent=err.message;});
  });
  reload().catch(err=>{count.textContent=err.message;});
});
