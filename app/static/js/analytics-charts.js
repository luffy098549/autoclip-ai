"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const chart=document.getElementById("analytics-chart");
  const leaders=document.getElementById("analytics-leaders");
  if(!chart||!leaders)return;
  const totals={
    youtube:{name:"YouTube Shorts",views:0,engagement:0},
    tiktok:{name:"TikTok",views:0,engagement:0},
    instagram:{name:"Instagram Reels",views:0,engagement:0}
  };
  const element=(tag,text,cls="")=>{
    const node=document.createElement(tag);
    node.textContent=text;
    if(cls)node.className=cls;
    return node;
  };
  const number=n=>Math.round(Number(n)||0).toLocaleString("es");
  function updateSummary(data){
    const sum=data.summary||{};
    for(const key of ["views","likes","shares","tracked_clips"]){
      const e=document.querySelector('[data-metric-total="'+key+'"]');
      if(e)e.textContent=number(sum[key]);
    }
  }
  async function refresh(){
    const response=await fetch("/api/analytics",{
      credentials:"same-origin",headers:{"Accept":"application/json"}
    });
    if(!response.ok)throw new Error("No se pudieron consultar las estadísticas");
    const data=await response.json();
    updateSummary(data);
    const groups=Object.fromEntries(Object.entries(totals).map(([key,item])=>[
      key,{...item,views:0,engagement:0,interactions:0}
    ]));
    (data.items||[]).forEach(item=>{
      const group=groups[item.platform];
      if(group){
        group.views+=item.views;
        group.interactions+=item.likes+item.comments+item.shares;
      }
    });
    chart.replaceChildren();
    leaders.replaceChildren();
    if(!(data.items||[]).length){
      chart.append(element("p",
        "Aún no hay métricas verificadas. Registra estadísticas reales para ver los gráficos.",
        "muted"));
      leaders.append(element("p","Todavía no hay clips con resultados registrados.","muted"));
      return;
    }
    const peak=Math.max(1,...Object.values(groups).map(g=>g.views));
    for(const group of Object.values(groups)){
      const row=element("div",undefined,"analytics-bar-row");
      const top=element("div",undefined,"analytics-bar-heading");
      const engage=group.views?100*group.interactions/group.views:0;
      top.append(element("strong",group.name),
        element("span",number(group.views)+" vistas · "+engage.toFixed(2)+" % interacción"));
      const progress=document.createElement("progress");
      progress.max=peak;progress.value=group.views;
      progress.setAttribute("aria-label","Vistas de "+group.name);
      row.append(top,progress);
      chart.append(row);
    }
    const top=(data.items||[]).slice().sort((a,b)=>b.views-a.views).slice(0,5);
    top.forEach((item,index)=>{
      const line=element("div",undefined,"analytics-leader");
      line.append(
        element("b",String(index+1)+". Clip #"+item.clip_id),
        element("span",item.platform+" · "+number(item.views)+" vistas")
      );
      leaders.append(line);
    });
  }
  const run=()=>refresh().catch(error=>{
    chart.replaceChildren(element("p",error.message,"muted"));
  });
  window.addEventListener("autoclip:analytics-updated",run);
  document.getElementById("analytics-chart-refresh")?.addEventListener("click",run);
  run();
});
