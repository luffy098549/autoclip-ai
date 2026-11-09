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
    try {
      const status=await get("/api/status");
      if(status.youtube_metadata_enabled){
        document.querySelectorAll("#streamer-list .data-row").forEach((row,index)=>{
          const item=data.items[index];
          if(!item || item.platform!=="youtube")return;
          const btn=document.createElement("button");
          btn.type="button";btn.className="button ghost";btn.textContent="Sincronizar YouTube";
          btn.addEventListener("click",async()=>{
            btn.disabled=true;
            try{const result=await send("/api/streamers/"+item.id+"/sync",{});message("streamer-feedback",result.message+" · "+result.task_id);}
            catch(err){message("streamer-feedback",err.message,true);}
            finally{btn.disabled=false;}
          });
          row.append(btn);
        });
      }
      const videos=await get("/api/competitors/videos");
      drawList("competitor-list",videos.items,item=>item.title+" · "+item.views.toLocaleString("es")+" vistas · "+item.relative_views+"× vs. mediana del canal");
    }catch(err){message("streamer-feedback",err.message,true);}

    const sel=document.getElementById("source-streamer");
    if(sel){sel.replaceChildren();addOption(sel,"","Sin canal asociado");data.items.forEach(item=>addOption(sel,item.id,item.name+" ("+item.platform+")"));}
  }
  async function loadClips(){
    const sources=await get("/api/sources");
    const clips=await get("/api/clips");
    drawList("source-list",sources.items,item=>item.name+" · "+item.rights);
    document.querySelectorAll("#source-list .data-row").forEach((row,index)=>{
      const item=sources.items[index];
      if(!item)return;
      const button=document.createElement("button");
      button.type="button";button.className="button ghost";
      button.textContent="Transcripción";
      button.addEventListener("click",async()=>{
        const panel=document.getElementById("transcript-viewer");
        const output=document.getElementById("transcript-text");
        if(!panel||!output)return;
        panel.hidden=false;output.replaceChildren();
        try{
          const data=await get("/api/sources/"+item.id+"/transcript");
          if(!data.segments.length){
            const p=document.createElement("p");p.textContent="Esta fuente todavía no tiene transcripción.";output.append(p);
          }else data.segments.forEach(segment=>{
            const p=document.createElement("p");
            p.textContent=segment.start.toFixed(1)+"s – "+segment.end.toFixed(1)+"s · "+segment.text;
            output.append(p);
          });
        }catch(err){message("source-feedback",err.message,true);}
      });
      row.append(button);
    });
    try {
      const status=await get("/api/status");
      if(status.ai_detection_enabled){
        document.querySelectorAll("#source-list .data-row").forEach((row,index)=>{
          const item=sources.items[index];
          if(!item)return;
          const btn=document.createElement("button");
          btn.className="button ghost";
          btn.type="button";
          btn.textContent="Analizar con IA";
          btn.addEventListener("click",async()=>{
            btn.disabled=true;btn.textContent="Encolando…";
            try{
              const result=await send("/api/sources/"+item.id+"/analyze",{});
              message("source-feedback",result.message+" · ID de tarea: "+result.task_id);
            }catch(err){message("source-feedback",err.message,true);}
            finally{btn.disabled=false;btn.textContent="Analizar con IA";}
          });
          row.append(btn);
        });
      }
    } catch (e) { /* Other catalog operations remain available. */ }
    drawList("clip-list",clips.items,item=>"Fuente "+item.source_id+" · "+item.start+"–"+item.end+" s · "+item.status);
    document.querySelectorAll("#clip-list .data-row").forEach((row,index)=>{
      const item=clips.items[index];
      if(item && item.status==="ready"){
        const link=document.createElement("a");
        link.className="button ghost";
        link.href="/api/clips/"+item.id+"/download";
        link.textContent="Descargar MP4";
        row.append(link);
      }
      if(item && item.has_subtitles){
        const link=document.createElement("a");
        link.className="button ghost";
        link.href="/api/clips/"+item.id+"/subtitles";
        link.textContent="Descargar SRT";
        row.append(link);
      }
    });
    const sel=document.getElementById("clip-source");
    if(sel){const previous=sel.value;sel.replaceChildren();addOption(sel,"","Selecciona una fuente");sources.items.forEach(item=>addOption(sel,item.id,"Fuente "+item.id+" · "+item.name));sel.value=previous;}
  }
  async function loadAnalytics(){
    const clipData=await get("/api/clips");
    const data=await get("/api/analytics");
    const selector=document.getElementById("metric-clip");
    if(selector){const prev=selector.value;selector.replaceChildren();addOption(selector,"","Selecciona un clip");clipData.items.forEach(item=>addOption(selector,item.id,"Clip "+item.id+" · "+item.status));selector.value=prev;}
    const stats=document.getElementById("analytics-totals");
    if(stats) stats.textContent="Vistas registradas: "+data.summary.views.toLocaleString("es")+" · Likes: "+data.summary.likes.toLocaleString("es")+" · Compartidos: "+data.summary.shares.toLocaleString("es");
    drawList("analytics-list",data.items,item=>"Clip "+item.clip_id+" · "+item.platform+" · "+item.views.toLocaleString("es")+" vistas · "+item.engagement_percent+"% interacción");
    window.dispatchEvent(new CustomEvent("autoclip:analytics-updated"));
  }
  const analyticsForm=document.getElementById("metric-form");
  if(analyticsForm){
    analyticsForm.addEventListener("submit",async e=>{
      e.preventDefault();
      try{const result=await send("/api/analytics",Object.fromEntries(new FormData(analyticsForm).entries()));message("metric-feedback",result.message);await loadAnalytics();}
      catch(err){message("metric-feedback",err.message,true);}
    });
    loadAnalytics().catch(err=>message("metric-feedback",err.message,true));
  }
  document.getElementById("transcript-close")?.addEventListener("click",()=>{
    const p=document.getElementById("transcript-viewer");
    if(p)p.hidden=true;
  });
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
    window.setInterval(()=>{
      if(document.visibilityState==="visible")loadClips().catch(()=>{});
    },15000);
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
