"use strict";
document.addEventListener("DOMContentLoaded",async()=>{
  const indicator=document.getElementById("system-health");
  if(!indicator) return;
  const set=(key,value)=>{
    const target=document.querySelector('[data-system="'+key+'"]');
    if(target)target.textContent=value;
  };
  const onOff=active=>active?"Configurado":"Desactivado";
  try{
    const res=await fetch("/api/system",{
      credentials:"same-origin",headers:{"Accept":"application/json"}
    });
    const state=await res.json();
    indicator.textContent=state.database?.connected ?
      "Conexión de base de datos comprobada" :
      (state.database?.message||"No se pudo comprobar la conexión");
    indicator.className="system-health "+(state.database?.connected?"ok":"error");
    set("database",(state.database?.engine||"Desconocida")+
      " · "+(state.database?.connected?"Conectada":"Sin conexión"));
    set("owner_login",onOff(state.owner_login_configured));
    set("storage",state.media_storage_available?"Carpeta disponible":"Carpeta no encontrada");
    set("processing",onOff(state.processing_enabled));
    set("ai",onOff(state.ai_enabled));
    set("auto_render",onOff(state.auto_render_enabled));
    set("monitoring",onOff(state.youtube_monitoring_enabled));
    set("publishing","Desactivada (por seguridad)");
    set("interval",state.interval_minutes+" minutos");
    set("limit",String(state.daily_limit));
    set("timezone",state.time_zone);
  }catch(error){
    indicator.textContent="No se pudo consultar el estado del sistema";
    indicator.className="system-health error";
  }
});
