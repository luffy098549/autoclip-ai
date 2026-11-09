"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form=document.getElementById("plan-form");
  if(!form) return;
  const csrf=document.querySelector('meta[name="csrf-token"]')?.content || "";
  const clipSelect=document.getElementById("plan-clip");
  const list=document.getElementById("plan-list");
  const feedback=document.getElementById("plan-feedback");
  const say=(message,error=false)=>{
    feedback.textContent=message;
    feedback.className="form-feedback "+(error?"error":"ok");
  };
  async function json(url,options={}){
    const response=await fetch(url,{
      ...options, credentials:"same-origin",
      headers:{"Accept":"application/json",...(options.headers||{})}
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||"Error de conexión");
    return data;
  }
  function element(tag,text,className=""){
    const e=document.createElement(tag);
    e.textContent=text;
    if(className)e.className=className;
    return e;
  }
  async function loadClips(){
    const result=await json("/api/clips");
    clipSelect.replaceChildren();
    const empty=element("option","Selecciona un clip preparado");
    empty.value="";
    clipSelect.append(empty);
    result.items.filter(c=>c.status==="ready").forEach(c=>{
      const option=element("option","Clip #"+c.id+" · "+(c.end-c.start).toFixed(1)+" s");
      option.value=String(c.id);
      clipSelect.append(option);
    });
  }
  async function loadPlans(){
    const result=await json("/api/plans");
    list.replaceChildren();
    if(!result.items.length){
      list.append(element("p","Todavía no hay borradores.","muted"));
      return;
    }
    result.items.forEach(p=>{
      const row=element("div","","data-row plan-row");
      const copy=element("div","");
      const name={"youtube":"YouTube Shorts","tiktok":"TikTok","instagram":"Instagram Reels"}[p.platform]||p.platform;
      copy.append(element("b",name+" · Clip #"+p.clip_id),
                  element("small",p.scheduled_local.replace("T"," ")+" · Nueva York"));
      row.append(copy,element("span",p.state==="planned"?"Borrador":p.state));
      if(p.state==="planned"){
        const cancel=element("button","Cancelar","button ghost");
        cancel.type="button";
        cancel.addEventListener("click",async()=>{
          cancel.disabled=true;
          try{
            await json("/api/plans/"+p.id+"/cancel",{
              method:"POST",headers:{"X-CSRFToken":csrf}
            });
            say("Borrador cancelado");
            await loadPlans();
          }catch(err){say(err.message,true);cancel.disabled=false;}
        });
        row.append(cancel);
      }
      list.append(row);
    });
  }
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    try{
      const result=await json("/api/plans",{
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf},
        body:JSON.stringify(Object.fromEntries(new FormData(form).entries()))
      });
      say(result.message);
      await loadPlans();
    }catch(err){say(err.message,true);}
    finally{button.disabled=false;}
  });
  document.getElementById("plans-refresh")?.addEventListener("click",()=>{
    loadPlans().catch(err=>say(err.message,true));
  });
  loadClips().catch(err=>say("No se pudo cargar la biblioteca: "+err.message,true));
  loadPlans().catch(err=>say(err.message,true));
});
