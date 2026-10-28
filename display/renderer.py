#!/usr/bin/env python3
"""Native SDL2-backed Pygame renderer, directly on KMS/DRM."""
import datetime, json, os, pathlib, time
import pygame
DATA=pathlib.Path(os.environ.get("INFOSCREEN_DATA_DIR","/var/lib/kufgem-infoscreen"))
pygame.init()
screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
fps=pygame.time.Clock()
layout={}
last_load=0.0
def color(s,default="#ffffff"):
 try:return pygame.Color(s)
 except (TypeError,ValueError):return pygame.Color(default)
def text(value,x,y,size,colour):
 font=pygame.font.Font(None,max(18,int(size)))
 surface=font.render(str(value)[:180],True,color(colour))
 screen.blit(surface,(int(x),int(y)))
def redraw():
 width,height=screen.get_size()
 screen.fill(color(layout.get("background","#101b2d"),"#101b2d"))
 text(layout.get("title","KUFGEM InfoScreen"),width*.04,height*.035,height*.045,"#77c6ff")
 for w in layout.get("widgets",[]):
  x=w["x"]*width/100;y=w["y"]*height/100
  typ=w["type"];ink=w.get("color","#ffffff")
  if typ=="clock":
   now=datetime.datetime.now()
   text(now.strftime("%H:%M:%S"),x,y,height*.135,ink)
   text(now.strftime("%d.%m.%Y"),x,y+height*.14,height*.05,ink)
  elif typ=="message":text(w.get("text",""),x,y,height*.07,ink)
  elif typ=="weather":text("Wetter · "+w.get("location","Kufstein"),x,y,height*.05,ink)
  elif typ=="departures":text("Bahn: Datenquelle noch nicht konfiguriert",x,y,height*.04,ink)
  elif typ=="traffic":text("Verkehr: Datenquelle noch nicht konfiguriert",x,y,height*.04,ink)
while True:
 for event in pygame.event.get():
  if event.type==pygame.QUIT:raise SystemExit
 if time.monotonic()-last_load>1:
  last_load=time.monotonic()
  try:
   candidate=json.loads((DATA/"layout.json").read_text(encoding="utf8"))
   if isinstance(candidate,dict) and isinstance(candidate.get("widgets"),list):layout=candidate
  except (OSError,ValueError):pass
 if not layout:
  layout={"title":"KUFGEM InfoScreen","background":"#101b2d","widgets":[{"type":"clock","x":6,"y":20,"color":"#ffffff"}]}
 redraw()
 pygame.display.flip()
 fps.tick(10)
