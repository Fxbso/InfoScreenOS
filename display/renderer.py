#!/usr/bin/env python3
"""InfoScreen SDL2/Pygame fullscreen renderer for native X11 or KMS/DRM."""
import datetime, json, os, pathlib, socket, time, threading, sys
import pygame

DATA=pathlib.Path(os.environ.get("INFOSCREEN_DATA_DIR","/var/lib/kufgem-infoscreen"))
pygame.init()
screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
clock=pygame.time.Clock()
layout={}
background_image=None
background_mtime=None
last_load=0.0
weather_data={}
weather_lock=threading.Lock()
last_weather_request=0.0

def color(value,default="#ffffff"):
 try:return pygame.Color(value)
 except (ValueError,TypeError):return pygame.Color(default)

def write(text,x,y,size,ink,max_width=None):
 font=pygame.font.Font(None,max(16,int(size)))
 content=str(text)[:240]
 if max_width is None: content=content[:180]
 else:
  while content and font.size(content)[0]>max_width:content=content[:-1]
 surface=font.render(content,True,color(ink))
 screen.blit(surface,(int(x),int(y)))

def weather_worker():
 global weather_data
 try:
  sys.path.insert(0,"/opt/kufgem-infoscreen/backend")
  import app
  data=app.widget_data().get("widgets",{})
  with weather_lock:weather_data=data
 except Exception:pass

def widget_value(w):
 kind=w.get("type")
 source=w.get("source") or {}
 now=datetime.datetime.now()
 if kind=="clock":return now.strftime("%H:%M:%S")
 if kind=="date":return now.strftime("%A, %d.%m.%Y")
 if kind=="message":return w.get("text","")
 if kind=="hostname":return socket.gethostname()
 if kind=="uptime":
  try:
   seconds=int(float(pathlib.Path("/proc/uptime").read_text().split()[0]))
   return f"{seconds//86400} Tage · {(seconds%86400)//3600} Std."
  except (OSError,ValueError):return "–"
 if kind=="system":
  try:
   import shutil
   disk=shutil.disk_usage("/")
   return f"Freier Speicher: {disk.free//1073741824} GB"
  except OSError:return "Systemdaten nicht verfügbar"
 if kind=="divider":return "────────────────"
 if kind in ("weather","traffic","departures"):
  if source.get("provider")=="manual":return source.get("text","")
  if kind=="weather":
   with weather_lock: data=weather_data.get(w.get("id"),{})
   return data.get("text","Wetterdaten werden geladen …")
  return "Datenquelle nicht eingerichtet"
 return ""

def redraw():
 width,height=screen.get_size()
 screen.fill(color(layout.get("background","#101b2d"),"#101b2d"))
 if background_image is not None:
  screen.blit(pygame.transform.smoothscale(background_image,(width,height)),(0,0))
 shade=max(0,min(100,layout.get("overlayOpacity",12)))
 if shade:
  overlay=pygame.Surface((width,height),pygame.SRCALPHA)
  overlay.fill((0,0,0,int(255*shade/100)));screen.blit(overlay,(0,0))
 write(layout.get("title","KUFGEM InfoScreen"),width*.04,height*.025,height*.038,"#b7dfff")
 for w in layout.get("widgets",[]):
  try:
   x=int(w["x"]*width/100);y=int(w["y"]*height/100)
   ww=max(12,int(w["w"]*width/100));hh=max(12,int(w["h"]*height/100))
   ink=w.get("color","#ffffff")
   panel_opacity=max(0,min(100,w.get("panelOpacity",layout.get("widgetOpacity",78))))
   radius=int(max(0,min(100,w.get("radius",12)))*height/1080)
   panel=pygame.Surface((ww,hh),pygame.SRCALPHA)
   pygame.draw.rect(panel,(8,18,32,int(panel_opacity*255/100)),panel.get_rect(),border_radius=radius)
   screen.blit(panel,(x,y))
   padding=max(6,int(height*.014))
   title=w.get("title") or {"clock":"Uhr","date":"Datum","message":"Mitteilung","weather":"Wetter",
      "traffic":"Verkehr","departures":"Abfahrten","hostname":"Gerätename",
      "uptime":"Laufzeit","system":"Systemstatus","divider":"Trennlinie"}.get(w.get("type"),"")
   write(title,x+padding,y+padding,height*.022,ink,ww-padding*2)
   scale=max(.3,min(2,w.get("fontScale",50)/50))
   write(widget_value(w),x+padding,y+padding+height*.045,height*.045*scale,ink,ww-padding*2)
  except (KeyError,TypeError,ValueError):continue

while True:
 for event in pygame.event.get():
  if event.type==pygame.QUIT:raise SystemExit
 now=time.monotonic()
 if now-last_load>1:
  last_load=now
  pic=DATA/"background.img"
  try:
   mtime=pic.stat().st_mtime_ns
   if mtime!=background_mtime:
    background_image=pygame.image.load(str(pic)).convert()
    background_mtime=mtime
  except (OSError,pygame.error):
   background_image=None;background_mtime=None
  try:
   candidate=json.loads((DATA/"layout.json").read_text(encoding="utf-8"))
   if isinstance(candidate,dict) and isinstance(candidate.get("widgets"),list):layout=candidate
  except (OSError,ValueError):pass
 if now-last_weather_request>60:
  last_weather_request=now
  threading.Thread(target=weather_worker,daemon=True).start()
 if not layout:
  layout={"title":"KUFGEM InfoScreen","widgets":[{"type":"clock","x":6,"y":20,"w":40,"h":24}]}
 redraw()
 pygame.display.flip()
 clock.tick(10)
