"use strict";
document.addEventListener("DOMContentLoaded",async()=>{
  const target=document.getElementById("integration-readiness");
  if(!target)return;
  function textRow(label,value){
    const p=document.createElement("p");
    const b=document.createElement("strong");
    b.textContent=label+": ";
    p.append(b,document.createTextNode(value));
    return p;
  }
  try{
    const response=await fetch("/api/integrations",{
      credentials:"same-origin",headers:{"Accept":"application/json"}
    });
    if(!response.ok)throw new Error("No se pudo consultar el estado de las cuentas");
    const d=await response.json();
    target.replaceChildren(
      textRow("YouTube", d.youtube.local_oauth_token_present?
        "Token local encontrado. Aún debes verificar su validez.":"OAuth pendiente"),
      textRow("TikTok", d.tiktok.account_access_token_configured?
        "Token configurado. Revisa permisos y auditoría.":"Permiso de cuenta pendiente"),
      textRow("Instagram", d.instagram.token_configured&&d.instagram.professional_account_configured?
        "Configuración básica presente. Verifica permisos.":"Cuenta profesional/OAuth pendiente"),
      textRow("Despliegue",d.deployment.read_only_demo?
        "Demostración de solo lectura":"Modo local/de desarrollo"),
      textRow("Publicación automática","Desactivada hasta completar pruebas y permisos")
    );
  }catch(err){target.textContent=err.message;}
});
