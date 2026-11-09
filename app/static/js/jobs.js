"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const list=document.getElementById("jobs-list");
  if(!list) return;
  const filter=document.getElementById("jobs-filter");
  const last=document.getElementById("jobs-last-refresh");
  let items=[];
  const category=(state)=>{
    if(state==="ready")return "ready";
    if(state==="processing")return "processing";
    if(state==="failed"||state==="rejected")return "failed";
    return "pending";
  };
  const labels={
    ready:"Listo",processing:"Procesando",failed:"Fallido",rejected:"Rechazado",
    queued:"En cola",awaiting_worker:"En espera",draft:"Borrador"
  };
  const element=(tag,text,cls="")=>{
    const e=document.createElement(tag);
    e.textContent=text;
    if(cls)e.className=cls;
    return e;
  };
  function render(){
    for(const status of ["ready","processing","pending","failed"]){
      const target=document.querySelector('[data-job-count="'+status+'"]');
      if(target)target.textContent=String(items.filter(item=>category(item.status)===status).length);
    }
    const active=filter.value;
    const visible=items.filter(item=>!active||category(item.status)===active);
    list.replaceChildren();
    if(!visible.length){
      list.append(element("p","No hay trabajos con ese estado.","muted"));
      return;
    }
    visible.forEach(item=>{
      const row=element("article","","job-row");
      const copy=element("div","","job-description");
      const title=element("strong","Clip #"+item.id);
      const details=element("small","Origen #"+item.source_id+" · "+
        (item.end-item.start).toFixed(1)+" s");
      copy.append(title,details);
      const badge=element("span",labels[item.status]||item.status,
                          "job-status "+category(item.status));
      row.append(copy,badge);
      if(item.status==="ready"){
        const link=element("a","Vista previa","button ghost");
        link.href="/clips";
        row.append(link);
      }
      list.append(row);
    });
  }
  async function reload(){
    const response=await fetch("/api/clips",{
      credentials:"same-origin",headers:{"Accept":"application/json"}
    });
    if(!response.ok)throw new Error("No se pudo consultar el worker");
    const data=await response.json();
    items=data.items||[];
    last.textContent="Actualizado: "+new Date().toLocaleTimeString("es");
    render();
  }
  const refresh=()=>reload().catch(err=>{last.textContent=err.message;});
  document.getElementById("jobs-refresh")?.addEventListener("click",refresh);
  filter.addEventListener("change",render);
  window.setInterval(()=>{
    if(document.visibilityState==="visible")refresh();
  },15000);
  refresh();
});
