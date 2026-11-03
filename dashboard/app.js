
const $=id=>document.getElementById(id);let config=null,selected=null;
function hdr(){return {"X-InfoScreen-Request":"1","Content-Type":"application/json"}}
const names={clock:"Uhr",date:"Datum",message:"Mitteilung",weather:"Wetter",traffic:"Verkehr",departures:"Abfahrten",hostname:"Gerätename",uptime:"Laufzeit",system:"Systemstatus",divider:"Trennlinie"};
const samples={clock:"14:32:08",date:"Dienstag, 3. November",message:"Willkommen bei KUFGEM",weather:"8 °C · Wolkig",traffic:"Keine aktuellen Meldungen",departures:"Abfahrten konfigurieren",hostname:"infoscreen-kufgem",uptime:"2 Tage, 4 Stunden",system:"RAM · Speicher · Netzwerk",divider:"─────────"};
let pending=null,tab="main",liveData={};
function make(tag,label,cls){const e=document.createElement(tag);if(label!==undefined)e.textContent=label;if(cls)e.className=cls;return e}
function switchTab(name){tab=name;$("designPanel").hidden=name!=="main";$("explorerPanel").hidden=name!=="explorer";$("settingsPanel").hidden=name!=="settings";for(const [k,id] of [["main","tabMain"],["explorer","tabExplorer"],["settings","tabSettings"]])$(id).classList.toggle("active",k===name);if(name==="settings")loadSystem()}
function content(w){if(w.type==="message")return w.text||samples.message;if(["traffic","departures"].includes(w.type))return w.source?.text||"Datenquelle nicht konfiguriert";if(w.type==="weather")return w.source?.provider==="manual"?(w.source.text||"Wetter"):liveData[w.id]?.text||"Wetterdaten laden …";if(w.type==="clock")return new Date().toLocaleTimeString("de-AT");if(w.type==="date")return new Date().toLocaleDateString("de-AT");return samples[w.type]||""}
function render(){if(!config)return;const stage=$("stage");stage.replaceChildren();stage.style.backgroundColor=config.background||"#101b2d";stage.style.backgroundImage="url('/api/background')";stage.style.backgroundSize="cover";stage.style.setProperty("--shade",(config.overlayOpacity??12)/100);$("title").value=config.title;$("background").value=config.background;$("overlayOpacity").value=config.overlayOpacity??12;$("widgetOpacity").value=config.widgetOpacity??78;
for(const w of config.widgets){const el=make("div",undefined,"widget"+(selected===w.id?" active":""));Object.assign(el.style,{left:w.x+"%",top:w.y+"%",width:w.w+"%",height:w.h+"%",color:w.color||"#fff",backgroundColor:"rgba(8,18,32,"+((w.panelOpacity??config.widgetOpacity??78)/100)+")",borderRadius:(w.radius??12)+"px",fontSize:(w.fontScale??50)/50+"rem"});el.append(make("strong",w.title||names[w.type]||w.type),make("div",content(w),"previewContent"));el.onpointerdown=e=>{selected=w.id;renderEditor();const ox=w.x,oy=w.y,sx=e.clientX,sy=e.clientY,rect=stage.getBoundingClientRect();el.setPointerCapture(e.pointerId);const move=ev=>{w.x=Math.round(Math.max(0,Math.min(100-w.w,ox+100*(ev.clientX-sx)/rect.width)));w.y=Math.round(Math.max(0,Math.min(100-w.h,oy+100*(ev.clientY-sy)/rect.height)));el.style.left=w.x+"%";el.style.top=w.y+"%"};el.addEventListener("pointermove",move);el.addEventListener("pointerup",()=>{el.removeEventListener("pointermove",move);render()},{once:true})};stage.append(el)}renderEditor()}
function field(box,label,value,type,change,options){box.append(make("label",label));const input=type==="select"?make("select"):make("input");if(type==="select"){for(const [val,name] of options){const opt=make("option",name);opt.value=val;input.append(opt)}}else{input.type=type;if(type==="range"){input.min=0;input.max=100}if(type==="number"){input.min=0;input.max=100}}input.value=value??"";input.addEventListener(type==="range"?"input":"change",()=>change(input.value));box.append(input)}
function fields(box,w){box.replaceChildren();for(const [key,label,type,def] of [["title","Überschrift","text",""],["x","Position X (%)","number",10],["y","Position Y (%)","number",20],["w","Breite (%)","number",40],["h","Höhe (%)","number",20],["color","Textfarbe","color","#ffffff"],["panelOpacity","Karten-Deckkraft (%)","range",78],["fontScale","Schriftgröße (%)","range",50],["radius","Eckenradius","range",12]])field(box,label,w[key]??def,type,v=>{w[key]=["number","range"].includes(type)?Math.max(key==="w"||key==="h"?1:0,Math.min(100,Number(v)||0)):v;if(!pending)render()});if(w.type==="message")field(box,"Text",w.text||"","text",v=>{w.text=v;if(!pending)render()});if(["weather","traffic","departures"].includes(w.type)){box.append(make("h4","Datenquelle"));const src=w.source??(w.source={provider:w.type==="weather"?"open-meteo":"manual",location:"Kufstein",interval:15,text:""});field(box,"Anbieter",src.provider,"select",v=>{src.provider=v;fields(box,w)},w.type==="weather"?[["open-meteo","Open-Meteo (Live)"],["manual","Manueller Text"]]:[["manual","Manuelle Meldung"],["none","Keine Quelle"]]);if(src.provider==="open-meteo"){field(box,"Ort",src.location||"Kufstein","text",v=>src.location=v);field(box,"Aktualisierungsintervall (Minuten)",src.interval||15,"number",v=>src.interval=Math.max(5,Math.min(120,Number(v)||15)));box.append(make("p","Open-Meteo überträgt den Ort an externe Server.","small"))}else if(src.provider==="manual")field(box,"Anzeigetext",src.text||"","text",v=>{src.text=v;if(!pending)render()});if(w.type!=="weather")box.append(make("p","Live-Verkehrs- und Zugdaten benötigen noch eine Anbieterintegration. Derzeit manuelle Quellen.","small"))}}
function renderEditor(){const box=$("editor");if(!config)return;const w=config.widgets.find(v=>v.id===selected);if(!w){box.replaceChildren(make("p","Widget auswählen und bearbeiten."));return}fields(box,w);const del=make("button","Widget entfernen");del.onclick=()=>{config.widgets=config.widgets.filter(v=>v.id!==w.id);selected=null;render()};box.append(del)}
function renderExplorer(){const catalog=$("widgetCatalog");catalog.replaceChildren();for(const [type,title] of Object.entries(names)){const card=make("div",undefined,"widgetOption"),preview=make("div",undefined,"widgetSample");preview.append(make("strong",title),make("p",samples[type]));card.append(make("strong",title),preview);card.onclick=()=>openWizard(type);catalog.append(card)}}
function openWizard(type){pending={id:"w-"+Date.now(),type,x:10,y:20,w:40,h:20,color:"#ffffff",panelOpacity:78,fontScale:50,radius:12};if(type==="message")pending.text="Neue Mitteilung";if(type==="weather")pending.source={provider:"open-meteo",location:"Kufstein",interval:15};if(["traffic","departures"].includes(type))pending.source={provider:"manual",text:""};$("widgetCatalog").hidden=true;$("widgetWizard").hidden=false;$("wizardTitle").textContent=names[type]+" einrichten";const preview=$("wizardPreview"),card=make("div",undefined,"widgetSample");card.append(make("strong",names[type]),make("p",samples[type]));preview.replaceChildren(card);fields($("wizardFields"),pending)}
function closeWizard(){pending=null;$("widgetCatalog").hidden=false;$("widgetWizard").hidden=true}
$("wizardCancel").onclick=closeWizard;$("wizardAdd").onclick=()=>{if(!pending)return;config.widgets.push(pending);selected=pending.id;closeWizard();switchTab("main");render();$("feedback").textContent="Widget hinzugefügt. Zum Übernehmen Layout speichern."};
async function loadSystem(){const box=$("systemInfo");box.replaceChildren(make("p","Status wird geladen …"));try{const r=await fetch("/api/system");if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();box.replaceChildren();for(const [k,v] of [["Hostname",d.hostname],["Betriebssystem",d.platform],["IP-Adressen",d.network.addresses.join(", ")],["Adapter",d.network.interfaces.map(x=>x.name+" ("+x.state+")").join(", ")],["Laufzeit",Math.round(d.uptimeSeconds/3600)+" h"],["RAM",Math.round(d.memory.available/1048576)+" MB frei"],["Speicher",Math.round(d.disk.free/1073741824)+" GB frei"],["Software","Manuelle Aktualisierung"]])box.append(make("div",k+": "+v,"systemline"))}catch(e){box.replaceChildren(make("p","Systemdaten nicht verfügbar: "+e.message))}}
async function refreshData(){try{const r=await fetch("/api/widget-data");if(r.ok){liveData=(await r.json()).widgets||{};if(config)render()}}catch(_){}}
async function loadConfig(){
 const r=await fetch("/api/config",{cache:"no-store"});
 if(!r.ok)throw Error(r.status===401?"Bitte anmelden":"API antwortet nicht ("+r.status+")");
 config=await r.json();
 renderExplorer();
 $("loginPanel").hidden=true;$("controls").hidden=false;$("status").textContent="Verbunden";render();refreshData();
}
$("login").onclick=async()=>{
 $("status").textContent="Anmeldung läuft …";
 try{
  const password=$("password").value;
  const r=await fetch("/api/login",{method:"POST",headers:hdr(),body:JSON.stringify({password})});
  if(!r.ok)throw Error(r.status===401?"Passwort falsch":r.status===429?"Zu viele Versuche. Bitte später erneut versuchen.":"Anmeldung fehlgeschlagen ("+r.status+")");
  $("password").value="";
  await loadConfig();
 }catch(e){$("status").textContent="Nicht verbunden";$("feedbackLogin").textContent=e.message}
};
$("password").addEventListener("keydown",e=>{if(e.key==="Enter")$("login").click()});
$("logout").onclick=async()=>{
 await fetch("/api/logout",{method:"POST",headers:hdr()});
 location.reload();
};
(async()=>{
 try{const r=await fetch("/api/session",{cache:"no-store"});if(r.ok){await loadConfig();return}
 $("status").textContent="Anmeldung erforderlich";
 }catch(e){$("status").textContent="API nicht erreichbar"}
})();
for(const [id,name] of [["tabMain","main"],["tabExplorer","explorer"],["tabSettings","settings"]])$(id).onclick=()=>switchTab(name);
$("add").onclick=()=>switchTab("explorer");
$("title").onchange=e=>{config.title=e.target.value;render()};
$("background").oninput=e=>{config.background=e.target.value;render()};
$("overlayOpacity").oninput=e=>{config.overlayOpacity=Number(e.target.value);$("stage").style.setProperty("--shade",config.overlayOpacity/100)};
$("widgetOpacity").oninput=e=>{config.widgetOpacity=Number(e.target.value);render()};
$("reload").onclick=()=>loadConfig().catch(e=>$("feedback").textContent=e.message);
$("resetLayout").onclick=()=>{if(!confirm("Alle Widgets zurücksetzen?"))return;config.widgets=[{id:"clock",type:"clock",x:6,y:9,w:48,h:27,color:"#ffffff"},{id:"message",type:"message",x:6,y:55,w:82,h:20,color:"#ffffff",text:"Willkommen bei KUFGEM"}];selected=null;render()};
$("refreshSystem").onclick=loadSystem;
$("copyUpdate").onclick=()=>{const cmd="curl -fsSL https://raw.githubusercontent.com/Fxbso/InfoScreenOS/main/install-ubuntu.sh -o /tmp/infoscreen-install.sh && sudo bash /tmp/infoscreen-install.sh";if(navigator.clipboard?.writeText)navigator.clipboard.writeText(cmd).then(()=>$("copyUpdate").textContent="Kopiert");else prompt("Update-Befehl:",cmd)};
setInterval(()=>{if(config){render();refreshData()}},60000);
$("upload").onclick=async()=>{const file=$("image").files[0];if(!file)return;if(file.size>4*1024*1024){$("feedback").textContent="Bild ist zu groß (max. 4 MB).";return}try{const r=await fetch("/api/background",{method:"POST",headers:{"X-InfoScreen-Request":"1","Content-Type":file.type},body:file});if(!r.ok)throw Error(await r.text());$("stage").style.backgroundImage="url('/api/background?t="+Date.now()+"')";$("stage").style.backgroundSize="cover";$("feedback").textContent="Hintergrundbild übernommen."}catch(e){$("feedback").textContent="Upload fehlgeschlagen: "+e.message}};
$("save").onclick=async()=>{try{const r=await fetch("/api/config",{method:"PUT",headers:hdr(),body:JSON.stringify(config)});if(!r.ok)throw Error(await r.text());$("feedback").textContent="Gespeichert – Änderung wird auf HDMI angezeigt."}catch(e){$("feedback").textContent="Fehler: "+e.message}};
