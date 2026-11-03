
const $=id=>document.getElementById(id);let config=null,selected=null;
function hdr(){return {"X-InfoScreen-Request":"1","Content-Type":"application/json"}}
const names={clock:"Uhr",date:"Datum",message:"Mitteilung",weather:"Wetter",traffic:"Verkehr",departures:"Abfahrten",hostname:"Gerätename",uptime:"Laufzeit",system:"Systemstatus",divider:"Trennlinie"};
const samples={clock:"14:32:08",date:"Dienstag, 3. November",message:"Willkommen bei KUFGEM",weather:"8 °C · Wolkig",traffic:"Keine aktuellen Meldungen",departures:"Abfahrten konfigurieren",hostname:"infoscreen-kufgem",uptime:"2 Tage, 4 Stunden",system:"RAM · Speicher · Netzwerk",divider:"─────────"};
let pending=null,editingWidgetId=null,tab="main",liveData={},realisticPreview=false,widgetCategory="all";
function make(tag,label,cls){const e=document.createElement(tag);if(label!==undefined)e.textContent=label;if(cls)e.className=cls;return e}
function switchTab(name){
 tab=name;
 clearContextMenu();
 $("studioLayout").hidden=name!=="main";
 $("explorerPanel").hidden=name!=="explorer";
 $("settingsPanel").hidden=name!=="settings";
 $("mainHeading").hidden=name!=="main";
 $("explorerHeading").hidden=name!=="explorer";
 $("settingsHeading").hidden=name!=="settings";
 for(const [key,id] of [["main","tabMain"],["explorer","tabExplorer"],["settings","tabSettings"]])$(id).classList.toggle("active",key===name);
 if(name==="settings")loadSystem();
 if(name==="explorer")renderExplorer();
}
function hasLiveContent(w){
 if(["weather","traffic","departures"].includes(w.type)){
  if(w.source?.provider==="manual")return Boolean((w.source.text||"").trim());
  if(w.type==="weather" && w.source?.provider==="open-meteo")return Boolean(liveData[w.id]?.ok && (liveData[w.id]?.text||"").trim());
  return false;
 }
 if(w.type==="message")return Boolean((w.text||"").trim());
 return true;
}
function content(w){if(w.type==="message")return w.text||samples.message;if(["traffic","departures"].includes(w.type))return w.source?.text||"Datenquelle nicht konfiguriert";if(w.type==="weather")return w.source?.provider==="manual"?(w.source.text||"Wetter"):liveData[w.id]?.text||"Wetterdaten laden …";if(w.type==="clock")return new Date().toLocaleTimeString("de-AT");if(w.type==="date")return new Date().toLocaleDateString("de-AT");return samples[w.type]||""}
function clearContextMenu(){
 const menu=$("widgetContextMenu");
 menu.hidden=true;
 menu.replaceChildren();
}
function highlightSelection(id){
 selected=id;
 for(const element of $("stage").querySelectorAll(".widget")){
  element.classList.toggle("active",element.dataset.widgetId===id);
 }
 renderEditor();
}
function deleteWidget(id){
 if(!config)return;
 const widget=config.widgets.find(w=>w.id===id);
 if(!widget)return;
 // Edits stay local until the user presses "Layout speichern".
 config.widgets=config.widgets.filter(w=>w.id!==id);
 if(selected===id)selected=null;
 clearContextMenu();render();
 $("feedback").textContent=(widget.title||names[widget.type]||"Widget")+" entfernt · zum Übernehmen Layout speichern.";
}
function duplicateWidget(id){
 const original=config?.widgets.find(w=>w.id===id);
 if(!original)return;
 const copy=JSON.parse(JSON.stringify(original));
 copy.id="w-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,7);
 copy.x=Math.min(100-copy.w,copy.x+3);
 copy.y=Math.min(100-copy.h,copy.y+3);
 config.widgets.push(copy);
 clearContextMenu();selected=copy.id;render();
 $("feedback").textContent="Widget dupliziert · zum Übernehmen Layout speichern.";
}
function openWidgetEditor(id){
 const original=config?.widgets.find(w=>w.id===id);
 if(!original)return;
 clearContextMenu();
 highlightSelection(id);
 editingWidgetId=id;
 pending=JSON.parse(JSON.stringify(original));
 $("wizardLayout").hidden=false;
 $("wizardTitle").textContent=(original.title||names[original.type])+" bearbeiten";
 $("wizardAdd").textContent="Änderungen übernehmen";
 updateWizardPreview();
 fields($("wizardFields"),pending);
}
function showWidgetContextMenu(event,id){
 event.preventDefault();
 event.stopPropagation();
 clearContextMenu();
 highlightSelection(id);
 const menu=$("widgetContextMenu");
 for(const [label,action,kind] of [
  ["✎  Bearbeiten",()=>openWidgetEditor(id),""],
  ["⧉  Duplizieren",()=>duplicateWidget(id),""],
  ["⌫  Löschen",()=>deleteWidget(id),"danger"]
 ]){
  const item=make("button",label,kind);
  item.type="button";item.onclick=action;
  menu.append(item);
 }
 menu.hidden=false;
 const rect=menu.getBoundingClientRect(),margin=8;
 menu.style.left=Math.max(margin,Math.min(event.clientX,window.innerWidth-rect.width-margin))+"px";
 menu.style.top=Math.max(margin,Math.min(event.clientY,window.innerHeight-rect.height-margin))+"px";
}
function isTextEditingTarget(target){
 return target instanceof Element && Boolean(target.closest("input,textarea,select,[contenteditable], [role='textbox']"));
}
function render(){if(!config)return;clearContextMenu();const stage=$("stage");stage.classList.toggle("livePreview",realisticPreview);stage.replaceChildren();stage.style.backgroundColor=config.background||"#101b2d";stage.style.backgroundImage="url('/api/background')";stage.style.backgroundSize="cover";stage.style.setProperty("--shade",(config.overlayOpacity??12)/100);$("title").value=config.title;$("background").value=config.background;$("overlayOpacity").value=config.overlayOpacity??12;$("widgetOpacity").value=config.widgetOpacity??78;
for(const w of config.widgets){if(realisticPreview&&!hasLiveContent(w))continue;const el=make("div",undefined,"widget"+(selected===w.id?" active":""));Object.assign(el.style,{left:w.x+"%",top:w.y+"%",width:w.w+"%",height:w.h+"%",color:w.color||"#fff",backgroundColor:"rgba(8,18,32,"+((w.panelOpacity??config.widgetOpacity??78)/100)+")",borderRadius:(w.radius??12)+"px",fontSize:(w.fontScale??50)/50+"rem"});el.dataset.widgetId=w.id;el.tabIndex=0;el.setAttribute("role","button");el.setAttribute("aria-label",(w.title||names[w.type])+" auswählen, Doppelklick zum Bearbeiten");el.title="Klick: auswählen · Doppelklick: bearbeiten · Rechtsklick: Aktionen";el.append(make("strong",w.title||names[w.type]||w.type),make("div",content(w),"previewContent"));el.addEventListener("dblclick",e=>{e.preventDefault();openWidgetEditor(w.id)});el.addEventListener("contextmenu",e=>showWidgetContextMenu(e,w.id));el.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();openWidgetEditor(w.id)}});el.onpointerdown=e=>{if(e.button!==0)return;clearContextMenu();highlightSelection(w.id);const ox=w.x,oy=w.y,sx=e.clientX,sy=e.clientY,rect=stage.getBoundingClientRect();el.setPointerCapture(e.pointerId);const move=ev=>{w.x=Math.round(Math.max(0,Math.min(100-w.w,ox+100*(ev.clientX-sx)/rect.width)));w.y=Math.round(Math.max(0,Math.min(100-w.h,oy+100*(ev.clientY-sy)/rect.height)));el.style.left=w.x+"%";el.style.top=w.y+"%"};el.addEventListener("pointermove",move);el.addEventListener("pointerup",()=>{el.removeEventListener("pointermove",move);render()},{once:true})};stage.append(el)}renderEditor()}
function field(box,label,value,type,change,options){box.append(make("label",label));const input=type==="select"?make("select"):make("input");if(type==="select"){for(const [val,name] of options){const opt=make("option",name);opt.value=val;input.append(opt)}}else{input.type=type;if(type==="range"){input.min=0;input.max=100}if(type==="number"){input.min=0;input.max=100}}input.value=value??"";input.addEventListener(type==="range"?"input":"change",()=>change(input.value));box.append(input)}
function fields(box,w){box.replaceChildren();for(const [key,label,type,def] of [["title","Überschrift","text",""],["x","Position X (%)","number",10],["y","Position Y (%)","number",20],["w","Breite (%)","number",40],["h","Höhe (%)","number",20],["color","Textfarbe","color","#ffffff"],["panelOpacity","Hilfsfläche im Editor (%)","range",78],["fontScale","Schriftgröße (%)","range",50],["radius","Eckenradius","range",12]])field(box,label,w[key]??def,type,v=>{w[key]=["number","range"].includes(type)?Math.max(key==="w"||key==="h"?1:0,Math.min(100,Number(v)||0)):v;if(!pending)render();else updateWizardPreview()});if(w.type==="message")field(box,"Text",w.text||"","text",v=>{w.text=v;if(!pending)render();else updateWizardPreview()});if(["weather","traffic","departures"].includes(w.type)){box.append(make("h4","Datenquelle"));const src=w.source??(w.source={provider:w.type==="weather"?"open-meteo":"manual",location:"Kufstein",interval:15,text:""});field(box,"Anbieter",src.provider,"select",v=>{src.provider=v;fields(box,w)},w.type==="weather"?[["open-meteo","Open-Meteo (Live)"],["manual","Manueller Text"]]:[["manual","Manuelle Meldung"],["none","Keine Quelle"]]);if(src.provider==="open-meteo"){field(box,"Ort",src.location||"Kufstein","text",v=>src.location=v);field(box,"Aktualisierungsintervall (Minuten)",src.interval||15,"number",v=>src.interval=Math.max(5,Math.min(120,Number(v)||15)));box.append(make("p","Open-Meteo überträgt den Ort an externe Server.","small"))}else if(src.provider==="manual")field(box,"Anzeigetext",src.text||"","text",v=>{src.text=v;if(!pending)render();else updateWizardPreview()});if(w.type!=="weather")box.append(make("p","Live-Verkehrs- und Zugdaten benötigen noch eine Anbieterintegration. Derzeit manuelle Quellen.","small"))}}
function renderEditor(){const box=$("editor");if(!config)return;const w=config.widgets.find(v=>v.id===selected);if(!w){box.replaceChildren(make("p","Widget auswählen und bearbeiten."));return}fields(box,w);const del=make("button","Widget entfernen","btn danger");del.onclick=()=>deleteWidget(w.id);box.append(del)}
const widgetMeta={
 clock:{category:"basics",icon:"◷",desc:"Klar lesbare Uhrzeit – automatisch aktuell."},
 date:{category:"basics",icon:"▦",desc:"Datum und Wochentag auf einen Blick."},
 message:{category:"basics",icon:"✎",desc:"Eigene Texte und wichtige Informationen."},
 weather:{category:"live",icon:"☀",desc:"Aktuelle Wetterdaten über Open-Meteo."},
 traffic:{category:"live",icon:"⇄",desc:"Verkehrsmeldungen – aktuell manuell."},
 departures:{category:"live",icon:"↗",desc:"Abfahrten – aktuell manuell."},
 hostname:{category:"device",icon:"▣",desc:"Gerätename des InfoScreen-Systems."},
 uptime:{category:"device",icon:"◴",desc:"Wie lange das Gerät bereits läuft."},
 system:{category:"device",icon:"▤",desc:"Lokale Systeminformationen."},
 divider:{category:"basics",icon:"━",desc:"Inhalte optisch voneinander trennen."}
};
function renderExplorer(){
 const catalog=$("widgetCatalog"),term=($("widgetSearch").value||"").trim().toLocaleLowerCase("de");
 catalog.replaceChildren();let count=0;
 for(const [type,title] of Object.entries(names)){
  const meta=widgetMeta[type],match=widgetCategory==="all"||meta.category===widgetCategory;
  if(!match||!(title+" "+meta.desc).toLocaleLowerCase("de").includes(term))continue;
  count++;
  const card=make("button",undefined,"widgetOption");
  card.type="button";card.setAttribute("aria-label",title+" hinzufügen");
  const head=make("div",undefined,"card-head"),icon=make("span",meta.icon,"card-icon"),tag=make("span",meta.category==="live"?"DATEN":"WIDGET","card-type");
  head.append(icon,tag);
  const preview=make("div",undefined,"widgetSample "+(type==="weather"?"weather-sample":type==="message"?"message-sample":type==="date"?"date-sample":meta.category==="device"?"system-sample":""));
  preview.append(make("strong",title),make("p",samples[type]));
  const foot=make("div",undefined,"card-footer");foot.append(make("strong",title),make("span","+","plus"));
  card.append(head,preview,foot);
  card.title=meta.desc;card.onclick=()=>openWizard(type);
  catalog.append(card);
 }
 $("widgetCount").textContent=count+" "+(count===1?"Widget":"Widgets")+" verfügbar";
 if(!count)catalog.append(make("p","Keine Widgets gefunden. Versuche einen anderen Suchbegriff.","small"));
}
function updateWizardPreview(){if(!pending)return;const preview=$("wizardPreview");preview.replaceChildren();const card=make("div",undefined,"widgetSample");card.style.background="rgba(8,18,32,"+((pending.panelOpacity??78)/100)+")";card.style.borderRadius=(pending.radius??12)+"px";card.style.color=pending.color||"#fff";card.append(make("strong",pending.title||names[pending.type]),make("p",pending.type==="message"?(pending.text||"Mitteilung"):pending.source?.provider==="manual"?(pending.source.text||samples[pending.type]):samples[pending.type]));preview.append(card)}
function openWizard(type){editingWidgetId=null;$("wizardAdd").textContent="+ Hinzufügen";pending={id:"w-"+Date.now(),type,x:10,y:20,w:40,h:20,color:"#ffffff",panelOpacity:78,fontScale:50,radius:12};if(type==="message")pending.text="Neue Mitteilung";if(type==="weather")pending.source={provider:"open-meteo",location:"Kufstein",interval:15};if(["traffic","departures"].includes(type))pending.source={provider:"manual",text:""};$("wizardLayout").hidden=false;$("wizardTitle").textContent=names[type]+" einrichten";updateWizardPreview();fields($("wizardFields"),pending)}
function closeWizard(){pending=null;editingWidgetId=null;$("wizardLayout").hidden=true;$("wizardAdd").textContent="+ Hinzufügen"}
$("wizardCancel").onclick=closeWizard;$("wizardAdd").onclick=()=>{
 if(!pending)return;
 const edit=editingWidgetId!==null;
 if(edit){
  const index=config.widgets.findIndex(w=>w.id===editingWidgetId);
  if(index<0){closeWizard();return}
  config.widgets[index]=pending;
 }else{
  config.widgets.push(pending);
 }
 selected=pending.id;
 realisticPreview=false;
 $("previewMode").textContent="Live-Vorschau ansehen";
 closeWizard();switchTab("main");render();
 $("feedback").textContent=edit?"Widget angepasst · zum Übernehmen Layout speichern.":"Widget hinzugefügt · zum Übernehmen Layout speichern.";
};
async function loadSystem(){const box=$("systemInfo");box.replaceChildren(make("p","Status wird geladen …"));try{const r=await fetch("/api/system");if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();box.replaceChildren();for(const [k,v] of [["Hostname",d.hostname],["Betriebssystem",d.platform],["IP-Adressen",d.network.addresses.join(", ")],["Adapter",d.network.interfaces.map(x=>x.name+" ("+x.state+")").join(", ")],["Laufzeit",Math.round(d.uptimeSeconds/3600)+" h"],["RAM",Math.round(d.memory.available/1048576)+" MB frei"],["Speicher",Math.round(d.disk.free/1073741824)+" GB frei"],["Software","Manuelle Aktualisierung"]]){const line=make("div",undefined,"systemline");line.append(make("span",k),document.createTextNode(v));box.append(line)}}catch(e){box.replaceChildren(make("p","Systemdaten nicht verfügbar: "+e.message))}}
async function refreshData(){try{const r=await fetch("/api/widget-data");if(r.ok){liveData=(await r.json()).widgets||{};if(config)render()}}catch(_){}}
async function loadConfig(){
 const r=await fetch("/api/config",{cache:"no-store"});
 if(!r.ok)throw Error(r.status===401?"Bitte anmelden":"API antwortet nicht ("+r.status+")");
 config=await r.json();
 renderExplorer();
 $("loginPanel").hidden=true;$("controls").hidden=false;$("status").textContent="Verbunden";switchTab(tab);render();refreshData();
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
 $("status").textContent="Anmeldung erforderlich";$("loginPanel").hidden=false;
 }catch(e){$("status").textContent="API nicht erreichbar";$("loginPanel").hidden=false}
})();
for(const [id,name] of [["tabMain","main"],["tabExplorer","explorer"],["tabSettings","settings"]])$(id).onclick=()=>switchTab(name);
$("widgetSearch").addEventListener("input",renderExplorer);
for(const button of $("widgetCategories").querySelectorAll("button")){
 button.onclick=()=>{
  widgetCategory=button.dataset.category;
  for(const other of $("widgetCategories").querySelectorAll("button"))other.classList.toggle("active",other===button);
  renderExplorer();
 };
}
$("wizardLayout").addEventListener("click",e=>{if(e.target===$("wizardLayout"))closeWizard()});
document.addEventListener("pointerdown",e=>{
 if(!$("widgetContextMenu").hidden&&!$("widgetContextMenu").contains(e.target))clearContextMenu();
});
$("stage").addEventListener("pointerdown",e=>{
 if(e.target===$("stage")){clearContextMenu();highlightSelection(null)}
});
document.addEventListener("keydown",e=>{
 if(!config||tab!=="main"||!$("wizardLayout").hidden||isTextEditingTarget(e.target))return;
 if((e.key==="Delete"||e.key==="Backspace")&&selected!==null){
  e.preventDefault();deleteWidget(selected);
 }
});
window.addEventListener("blur",clearContextMenu);
window.addEventListener("resize",clearContextMenu);

document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!$("wizardLayout").hidden)closeWizard()});
$("add").onclick=()=>switchTab("explorer");
$("previewMode").onclick=()=>{realisticPreview=!realisticPreview;$("previewMode").textContent=realisticPreview?"Bearbeitungsansicht anzeigen":"Live-Vorschau ansehen";render()};
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
