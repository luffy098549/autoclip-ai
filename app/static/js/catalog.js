"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const get = async path => {
    const response = await fetch(path, {headers: {"Accept":"application/json"}});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Error al consultar");
    return result;
  };
  const send = async (path, body, multipart=false) => {
    const response = await fetch(path, {
      method: "POST",
      headers: multipart ? {"X-CSRFToken":csrf} : {"X-CSRFToken":csrf,"Content-Type":"application/json"},
      body: multipart ? body : JSON.stringify(body)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "No se pudo guardar");
    return result;
  };
  const message = (id, info, error=false) => {
    const el = document.getElementById(id);
    if (el) {el.textContent=info;el.className="form-feedback "+(error?"error":"ok");}
  };
  const addOption = (select, value, label) => {
    const el=document.createElement("option");el.value=String(value);el.textContent=label;select.append(el);
  };
  const drawList=(id,items,makeLabel)=>{
    const node=document.getElementById(id);
    if (!node) return;
    node.replaceChildren();
    if(!items.length){const p=document.createElement("p");p.className="muted";p.textContent="No hay registros todavía.";node.append(p);return;}
    items.forEach(item=>{
      const row=document.createElement("div");row.className="data-row";
      const name=document.createElement("b");name.textContent=makeLabel(item);
      const meta=document.createElement("span");meta.textContent="ID "+item.id;
      row.append(name,meta);node.append(row);
    });
  };
  async function loadStreamers(){
    const data=await get("/api/streamers");
    drawList("streamer-list",data.items,item=>item.name+" · "+item.platform+" / "+item.channel);
    const sel=document.getElementById("source-streamer");
    if(sel){sel.replaceChildren();addOption(sel,"","Sin canal asociado");data.items.forEach(item=>addOption(sel,item.id,item.name+" ("+item.platform+")"));}
  }
  async function loadClips(){
    const sources=await get("/api/sources");
    const clips=await get("/api/clips");
    drawList("source-list",sources.items,item=>item.name+" · "+item.rights);
    drawList("clip-list",clips.items,item=>"Fuente "+item.source_id+" · "+item.start+"–"+item.end+" s · "+item.status);
    const sel=document.getElementById("clip-source");
    if(sel){const previous=sel.value;sel.replaceChildren();addOption(sel,"","Selecciona una fuente");sources.items.forEach(item=>addOption(sel,item.id,"Fuente "+item.id+" · "+item.name));sel.value=previous;}
  }
  const streamer=document.getElementById("streamer-form");
  if(streamer){
    streamer.addEventListener("submit",async e=>{
      e.preventDefault();const form=new FormData(streamer);
      try{const result=await send("/api/streamers",Object.fromEntries(form.entries()));message("streamer-feedback",result.message);streamer.reset();await loadStreamers();}
      catch(err){message("streamer-feedback",err.message,true);}
    });
    loadStreamers().catch(err=>message("streamer-feedback",err.message,true));
  }
  const source=document.getElementById("source-form");
  if(source){
    source.addEventListener("submit",async e=>{
      e.preventDefault();message("source-feedback","Subiendo y validando archivo…");
      try{const result=await send("/api/sources",new FormData(source),true);message("source-feedback",result.message+" (ID "+result.id+")");source.reset();await loadClips();}
      catch(err){message("source-feedback",err.message,true);}
    });
    loadStreamers().catch(err=>message("source-feedback",err.message,true));
    loadClips().catch(err=>message("clip-feedback",err.message,true));
  }
  const clip=document.getElementById("clip-form");
  if(clip){
    clip.addEventListener("submit",async e=>{
      e.preventDefault();const form=new FormData(clip);
      try{const result=await send("/api/clips",Object.fromEntries(form.entries()));message("clip-feedback","Clip "+result.id+": "+result.status);await loadClips();}
      catch(err){message("clip-feedback",err.message,true);}
    });
  }
});
