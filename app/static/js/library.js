"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const gallery=document.getElementById("clip-gallery");
  if(!gallery) return;
  const search=document.getElementById("library-search");
  const filter=document.getElementById("library-filter");
  const count=document.getElementById("library-count");
  let clips=[];
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
