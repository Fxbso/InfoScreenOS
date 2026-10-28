#!/usr/bin/env python3
"""Local dashboard API. Stdlib-only, no cloud dependencies."""
import copy, json, os, pathlib, secrets, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DATA = pathlib.Path(os.environ.get("INFOSCREEN_DATA_DIR", "/var/lib/kufgem-infoscreen"))
WEB = pathlib.Path(__file__).resolve().parents[1] / "dashboard" / "index.html"
TOKEN_FILE = pathlib.Path(os.environ.get("INFOSCREEN_TOKEN_FILE", "/etc/kufgem-infoscreen/admin-token"))
LOCK=threading.RLock()
DEFAULT={"title":"KUFGEM InfoScreen","background":"#101b2d","widgets":[
 {"id":"clock","type":"clock","x":6,"y":9,"w":48,"h":27,"color":"#ffffff"},
 {"id":"message","type":"message","x":6,"y":56,"w":82,"h":22,"color":"#ffffff","text":"Willkommen bei KUFGEM"}]}
TYPES={"clock","message","weather","departures","traffic"}
def validate(v):
 if not isinstance(v,dict): raise ValueError("Expected object")
 for k,n in [("title",120),("background",120)]:
  if not isinstance(v.get(k),str) or len(v[k])>n: raise ValueError("Invalid "+k)
 ws=v.get("widgets")
 if not isinstance(ws,list) or len(ws)>32: raise ValueError("Invalid widgets")
 ids=set()
 for w in ws:
  if not isinstance(w,dict) or not isinstance(w.get("id"),str) or len(w["id"])>60 or w["id"] in ids: raise ValueError("Invalid widget id")
  ids.add(w["id"])
  if w.get("type") not in TYPES: raise ValueError("Invalid widget type")
  for k in ("x","y","w","h"):
   a=w.get(k)
   if isinstance(a,bool) or not isinstance(a,(float,int)) or not 0<=a<=100: raise ValueError("Invalid geometry")
  if w["w"]<1 or w["h"]<1: raise ValueError("Invalid size")
  for k in ("color","text","location"):
   if k in w and (not isinstance(w[k],str) or len(w[k])>300): raise ValueError("Invalid "+k)
 return v
def load():
 with LOCK:
  p=DATA/"layout.json"
  return validate(json.loads(p.read_text(encoding="utf8"))) if p.exists() else copy.deepcopy(DEFAULT)
def save(v):
 validate(v)
 with LOCK:
  DATA.mkdir(parents=True,exist_ok=True)
  fd,tmp=tempfile.mkstemp(dir=DATA,prefix=".layout-")
  try:
   with os.fdopen(fd,"w",encoding="utf8") as out:
    json.dump(v,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
   os.chmod(tmp,0o644)
   os.replace(tmp,DATA/"layout.json")
  finally:
   if os.path.exists(tmp): os.unlink(tmp)
def token():
 try: return TOKEN_FILE.read_text().strip()
 except OSError: return ""
class Handler(BaseHTTPRequestHandler):
 def send_json(self,status,value):
  b=json.dumps(value).encode()
  self.send_response(status);self.send_header("Content-Type","application/json")
  self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff")
  self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def authorized(self):
  expected=token()
  return bool(expected) and secrets.compare_digest(self.headers.get("Authorization",""),"Bearer "+expected)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=="/api/background":
   background=DATA/"background.img"
   if not background.exists():return self.send_json(404,{"error":"No background"})
   b=background.read_bytes()
   self.send_response(200)
   self.send_header("Content-Type","image/png" if b.startswith(b"\x89PNG") else "image/jpeg")
   self.send_header("Cache-Control","no-store")
   self.send_header("Content-Length",str(len(b)))
   self.end_headers();self.wfile.write(b);return
  if path=="/api/health": return self.send_json(200,{"ok":True})
  if path=="/api/config":
   if not self.authorized():return self.send_json(401,{"error":"Unauthorized"})
   return self.send_json(200,load())
  if path not in ("/","/index.html"): return self.send_json(404,{"error":"Not found"})
  b=WEB.read_bytes()
  self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
  self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
  self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  if urlsplit(self.path).path!="/api/background":return self.send_json(404,{"error":"Not found"})
  if not self.authorized():return self.send_json(401,{"error":"Unauthorized"})
  try:
   size=int(self.headers.get("Content-Length","0"))
   if size<8 or size>4*1024*1024:return self.send_json(413,{"error":"Image must be under 4 MB"})
   b=self.rfile.read(size)
   if not (b.startswith(b"\x89PNG\r\n\x1a\n") or b.startswith(b"\xff\xd8\xff")):return self.send_json(400,{"error":"Only PNG/JPEG allowed"})
   DATA.mkdir(parents=True,exist_ok=True)
   fd,name=tempfile.mkstemp(dir=DATA,prefix=".background-")
   try:
    with os.fdopen(fd,"wb") as out:out.write(b);out.flush();os.fsync(out.fileno())
    os.chmod(name,0o644)
    os.replace(name,DATA/"background.img")
   finally:
    if os.path.exists(name):os.unlink(name)
   return self.send_json(200,{"ok":True})
  except ValueError as e:return self.send_json(400,{"error":str(e)})
 def do_PUT(self):
  if urlsplit(self.path).path!="/api/config":return self.send_json(404,{"error":"Not found"})
  if not self.authorized():return self.send_json(401,{"error":"Unauthorized"})
  try:
   size=int(self.headers.get("Content-Length","0"))
   if size<2 or size>65536:return self.send_json(413,{"error":"Payload too large"})
   save(json.loads(self.rfile.read(size)))
   self.send_json(200,{"ok":True})
  except (ValueError,KeyError) as e:self.send_json(400,{"error":str(e)})
if __name__=="__main__":
 DATA.mkdir(parents=True,exist_ok=True)
 if not (DATA/"layout.json").exists(): save(copy.deepcopy(DEFAULT))
 host=os.environ.get("INFOSCREEN_HOST","0.0.0.0")
 ThreadingHTTPServer((host,int(os.environ.get("INFOSCREEN_PORT","8080"))),Handler).serve_forever()
