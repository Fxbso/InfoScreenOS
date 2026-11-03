
const $=id=>document.getElementById(id);let config=null,selected=null;
function hdr(){return {"X-InfoScreen-Request":"1","Content-Type":"application/json"}}
function render(){let stage=$("stage");stage.innerHTML="";stage.style.background=config.background;stage.style.backgroundImage="url(/api/background)";stage.style.backgroundSize="cover";$("title").value=config.title;$("background").value=/^#[0-9a-f]{6}$/i.test(config.background)?config.background:"#101b2d";
for(const w of config.widgets){let el=document.createElement("div");el.className="widget"+(selected===w.id?" active":"");Object.assign(el.style,{left:w.x+"%",top:w.y+"%",width:w.w+"%",height:w.h+"%",color:w.color||"#ffffff"});el.textContent=w.type==="message"?(w.text||"Mitteilung"):({"clock":"Uhr","weather":"Wetter","traffic":"Verkehr","departures":"Abfahrten"}[w.type]||w.type);
el.onpointerdown=e=>{selected=w.id;renderEditor();const ox=w.x,oy=w.y,sx=e.clientX,sy=e.clientY,rect=stage.getBoundingClientRect();el.setPointerCapture(e.pointerId);el.classList.add("active");for(const other of stage.children)if(other!==el)other.classList.remove("active");const move=ev=>{w.x=Math.round(Math.max(0,Math.min(100-w.w,ox+100*(ev.clientX-sx)/rect.width)));w.y=Math.round(Math.max(0,Math.min(100-w.h,oy+100*(ev.clientY-sy)/rect.height)));el.style.left=w.x+"%";el.style.top=w.y+"%";renderEditor()};el.addEventListener("pointermove",move);el.addEventListener("pointerup",()=>el.removeEventListener("pointermove",move),{once:true})};stage.append(el)}renderEditor()}
function renderEditor(){let box=$("editor");box.innerHTML="";let w=config.widgets.find(x=>x.id===selected);if(!w){box.textContent="Widget anklicken";return}for(const k of ["x","y","w","h","color",...(w.type==="message"?["text"]:[]),...(w.type==="weather"?["location"]:[])]){let label=document.createElement("label");label.textContent=k;let field=document.createElement("input");field.value=w[k]??"";field.type=["x","y","w","h"].includes(k)?"number":"text";field.onchange=()=>{w[k]=field.type==="number"?Math.max(k==="w"||k==="h"?1:0,Math.min(100,Number(field.value))):field.value;render()};box.append(label,field)}let remove=document.createElement("button");remove.textContent="Widget entfernen";remove.onclick=()=>{config.widgets=config.widgets.filter(x=>x.id!==w.id);selected=null;render()};box.append(remove)}
async function loadConfig(){
 const r=await fetch("/api/config",{cache:"no-store"});
 if(!r.ok)throw Error(r.status===401?"Bitte anmelden":"API antwortet nicht ("+r.status+")");
 config=await r.json();
 $("loginPanel").hidden=true;$("controls").hidden=false;$("status").textContent="Verbunden";render();
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
$("add").onclick=()=>{let type=$("kind").value;let w={id:"w-"+Date.now(),type,x:10,y:20,w:35,h:20,color:"#ffffff"};if(type==="message")w.text="Neue Mitteilung";if(type==="weather")w.location="Kufstein";config.widgets.push(w);selected=w.id;render()};
$("title").onchange=e=>config.title=e.target.value;$("background").oninput=e=>{config.background=e.target.value;$("stage").style.background=e.target.value};
$("upload").onclick=async()=>{const file=$("image").files[0];if(!file)return;if(file.size>4*1024*1024){$("feedback").textContent="Bild ist zu groß (max. 4 MB).";return}try{const r=await fetch("/api/background",{method:"POST",headers:{"X-InfoScreen-Request":"1","Content-Type":file.type},body:file});if(!r.ok)throw Error(await r.text());$("stage").style.backgroundImage="url('/api/background?t="+Date.now()+"')";$("stage").style.backgroundSize="cover";$("feedback").textContent="Hintergrundbild übernommen."}catch(e){$("feedback").textContent="Upload fehlgeschlagen: "+e.message}};
$("save").onclick=async()=>{try{const r=await fetch("/api/config",{method:"PUT",headers:hdr(),body:JSON.stringify(config)});if(!r.ok)throw Error(await r.text());$("feedback").textContent="Gespeichert – Änderung wird auf HDMI angezeigt."}catch(e){$("feedback").textContent="Fehler: "+e.message}};
