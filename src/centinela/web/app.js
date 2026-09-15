const API = "/api/v1";
const $ = (id) => document.getElementById(id);
const scenarios = {
  legitimate:{amount:85000,type:"pago",channel:"app_movil",distance:2.1,velocity:0,failed:0,newBeneficiary:false,newDevice:false,vpn:false,ip:"CL",session:180},
  doubtful:{amount:1250000,type:"transferencia",channel:"app_movil",distance:3.2,velocity:1,failed:1,newBeneficiary:true,newDevice:false,vpn:false,ip:"CL",session:95},
  fraud:{amount:3900000,type:"transferencia",channel:"web",distance:640,velocity:3,failed:5,newBeneficiary:true,newDevice:true,vpn:true,ip:"BR",session:22}
};
let currentScenario = scenarios.legitimate;

document.querySelectorAll(".nav-item").forEach(button=>button.addEventListener("click",()=>{
  document.querySelectorAll(".nav-item,.view").forEach(x=>x.classList.remove("active"));
  button.classList.add("active"); $(button.dataset.view).classList.add("active");
  if(button.dataset.view==="analyst") loadCases();
  if(button.dataset.view==="supervisor") loadMetrics();
}));
document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>{
  document.querySelectorAll(".tab,.panel").forEach(x=>x.classList.remove("active"));
  button.classList.add("active"); $(button.dataset.panel).classList.add("active");
}));

function applyScenario(name){
  currentScenario=scenarios[name];
  $("amount").value=currentScenario.amount; $("txType").value=currentScenario.type; $("channel").value=currentScenario.channel;
  $("distance").value=currentScenario.distance; $("velocity").value=currentScenario.velocity; $("failedLogins").value=currentScenario.failed;
  $("newBeneficiary").checked=currentScenario.newBeneficiary; $("newDevice").checked=currentScenario.newDevice; $("vpn").checked=currentScenario.vpn;
}
document.querySelectorAll(".scenario").forEach(button=>button.addEventListener("click",()=>{
  document.querySelectorAll(".scenario").forEach(x=>x.classList.remove("active"));button.classList.add("active");applyScenario(button.dataset.scenario);
}));
applyScenario("legitimate");

async function request(path, options={}){
  const response=await fetch(API+path,options);
  if(!response.ok){let message="No pudimos completar la solicitud.";try{const data=await response.json();message=data.detail||message}catch{}throw new Error(message)}
  return response.json();
}
function toast(message){const el=$("toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),3000)}
function loading(target){target.className="result-card";target.innerHTML='<div class="spinner"></div><h3 style="text-align:center">Analizando…</h3><p style="text-align:center">Estamos verificando la información.</p>'}
function result(target,data){
  const map={aprobar:["success","✓","Operación aprobada"],validacion_adicional:["warning","!","Necesitamos confirmar"],bloquear:["danger","×","Operación en revisión"],autentico:["success","✓","Documento validado"],sospechoso:["warning","!","Necesitamos otra validación"],falso:["danger","×","Documento en revisión"]};
  const [tone,icon,title]=map[data.verdict]; target.className=`result-card ${tone}`;
  target.innerHTML=`<div class="result-icon">${icon}</div><p class="eyebrow">Resultado</p><h3>${title}</h3><p>${escapeHtml(data.explanation_customer)}</p><div class="result-meta"><span>Identificador de seguimiento</span><strong>${escapeHtml(data.trace_id.slice(0,14))}…</strong></div>`;
}
function escapeHtml(value){const d=document.createElement("div");d.textContent=String(value??"");return d.innerHTML}

$("transactionForm").addEventListener("submit",async event=>{
  event.preventDefault(); const button=event.submitter; button.disabled=true; loading($("transactionResult"));
  const now=new Date().toISOString(); const amount=Number($("amount").value);
  const payload={transaction_id:`TX-WEB-${Date.now()}`,timestamp:now,amount,currency:"CLP",channel:$("channel").value,type:$("txType").value,
    origin_account:{id:"ACC-DEMO",age_days:1450,avg_monthly_amount:900000,country:"CL"},destination_account:{id:"DEST-DEMO",bank:"Banco Demo",is_new_beneficiary:$("newBeneficiary").checked,country:"CL"},
    device:{id:"DEV-DEMO",is_new_device:$("newDevice").checked,os:"Web",ip_country:currentScenario.ip,vpn:$("vpn").checked},geo:{lat:-33.45,lon:-70.66,distance_from_home_km:Number($("distance").value)},
    behavior:{tx_last_hour:Number($("velocity").value),tx_last_24h:7,failed_logins_24h:Number($("failedLogins").value),session_seconds:currentScenario.session},customer_profile:{segment:"persona_natural",risk_tier:"medio"}};
  try{result($("transactionResult"),await request("/transactions/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}));}catch(error){showError($("transactionResult"),error.message)}finally{button.disabled=false}
});

const fileInput=$("documentFile"),dropzone=$("dropzone");
fileInput.addEventListener("change",()=>{$("fileName").textContent=fileInput.files[0]?.name||""});
["dragenter","dragover"].forEach(name=>dropzone.addEventListener(name,e=>{e.preventDefault();dropzone.classList.add("drag")}));
["dragleave","drop"].forEach(name=>dropzone.addEventListener(name,e=>{e.preventDefault();dropzone.classList.remove("drag")}));
dropzone.addEventListener("drop",e=>{fileInput.files=e.dataTransfer.files;$("fileName").textContent=fileInput.files[0]?.name||""});
$("documentForm").addEventListener("submit",async event=>{
  event.preventDefault();const button=event.submitter;button.disabled=true;loading($("documentResult"));
  const form=new FormData();form.append("file",fileInput.files[0]);if($("documentType").value)form.append("document_type",$("documentType").value);
  try{result($("documentResult"),await request("/documents/validate",{method:"POST",body:form}));}catch(error){showError($("documentResult"),error.message)}finally{button.disabled=false}
});
function showError(target,message){target.className="result-card danger";target.innerHTML=`<div class="result-icon">×</div><h3>No pudimos completar la evaluación</h3><p>${escapeHtml(message)}</p>`}

async function checkHealth(){try{const data=await request("/health");$("statusDot").className="dot online";$("statusText").textContent="API conectada";$("modeBadge").textContent=data.mock_mode?"Demo":"En vivo"}catch{$("statusDot").className="dot offline";$("statusText").textContent="API sin conexión";$("modeBadge").textContent="Error"}}

async function loadCases(){
  const target=$("casesTable");target.innerHTML='<div class="spinner"></div>';
  const query=new URLSearchParams();if($("caseProcess").value)query.set("process",$("caseProcess").value);if($("onlyReview").checked)query.set("requires_human_review","true");
  try{const cases=await request(`/cases?${query}`);if(!cases.length){target.className="table-empty";target.textContent="Aún no hay casos con estos filtros.";return}target.className="";target.innerHTML=`<table><thead><tr><th>Caso</th><th>Proceso</th><th>Decisión</th><th>Riesgo</th><th>Revisión</th><th>Fecha</th></tr></thead><tbody>${cases.map(c=>`<tr><td><strong>${escapeHtml(c.trace_id.slice(0,12))}…</strong></td><td>${c.process==="transaction"?"Transacción":"Documento"}</td><td><span class="badge ${c.verdict}">${escapeHtml(c.verdict.replaceAll("_"," "))}</span></td><td class="score">${Math.round(c.score*100)}%</td><td>${c.requires_human_review?"Sí":"No"}</td><td>${new Date(c.created_at).toLocaleString("es-CL")}</td></tr>`).join("")}</tbody></table>`}catch(error){target.className="table-empty";target.textContent=error.message}
}
$("refreshCases").addEventListener("click",loadCases);$("caseProcess").addEventListener("change",loadCases);$("onlyReview").addEventListener("change",loadCases);

function metricCard(label,value,note){return `<div class="card kpi"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`}
async function loadMetrics(){
  try{const m=await request("/metrics");$("kpis").innerHTML=metricCard("Eventos evaluados",m.total,"trazas registradas")+metricCard("Revisión humana",`${(m.human_review_rate*100).toFixed(1)}%`,"casos derivados")+metricCard("Latencia p95",`${m.latency_p95_ms.toFixed(1)} ms`,"modo actual")+metricCard("Costo acumulado",`US$ ${m.cost_usd.toFixed(4)}`,`US$ ${m.cost_per_event_usd.toFixed(6)} por evento`);renderBars(m.by_verdict);renderDonut(m.by_process,m.total)}catch(error){toast(error.message)}
}
function renderBars(data){const entries=Object.entries(data),max=Math.max(1,...entries.map(x=>x[1]));$("verdictChart").innerHTML=entries.length?entries.map(([name,value])=>`<div class="bar-row"><span>${escapeHtml(name.replaceAll("_"," "))}</span><div class="bar-track"><div class="bar-fill" style="width:${value/max*100}%"></div></div><strong>${value}</strong></div>`).join(""):'<p class="table-empty">Sin decisiones todavía.</p>'}
function renderDonut(data,total){const tx=data.transaction||0;const angle=total?tx/total*360:0;$("processChart").innerHTML=`<div class="donut" style="background:conic-gradient(var(--accent) 0 ${angle}deg,#b8e1e7 ${angle}deg 360deg)"><strong>${total}</strong></div>`}
$("refreshMetrics").addEventListener("click",loadMetrics);
checkHealth();
