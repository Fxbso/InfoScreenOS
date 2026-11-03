#!/usr/bin/env python3
"""Local dashboard API. Stdlib-only, no cloud dependencies."""
import copy, json, os, pathlib, secrets, tempfile, threading, base64, hashlib, hmac, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DATA = pathlib.Path(os.environ.get("INFOSCREEN_DATA_DIR", "/var/lib/kufgem-infoscreen"))
WEB = pathlib.Path(__file__).resolve().parents[1] / "dashboard" / "index.html"
PASSWORD_FILE = pathlib.Path(os.environ.get("INFOSCREEN_PASSWORD_FILE", "/etc/kufgem-infoscreen/password.json"))
SESSION_SECONDS = 7 * 24 * 3600
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()
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
def make_password_hash(password, salt=None):
 if salt is None: salt = secrets.token_bytes(16)
 key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 300000)
 return {"salt":salt.hex(), "hash":key.hex(), "iterations":300000}

def password_record():
 try: return json.loads(PASSWORD_FILE.read_text(encoding="utf-8"))
 except (OSError,ValueError): return None

def check_password(password):
 record=password_record()
 if not record: return False
 try:
  expected=bytes.fromhex(record["hash"])
  actual=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),
    bytes.fromhex(record["salt"]),int(record["iterations"]))
  return hmac.compare_digest(expected,actual)
 except (ValueError,KeyError,TypeError): return False

def session_signature(expires, record):
 # Changing the password invalidates every existing session.
 return hmac.new(bytes.fromhex(record["hash"]),str(expires).encode("ascii"),
                 hashlib.sha256).hexdigest()

def new_session():
 record=password_record()
 if not record: raise ValueError("Password not configured")
 expires=int(time.time())+SESSION_SECONDS
 return f"{expires}.{session_signature(expires,record)}"

def check_session(value):
 try:
  expires_str,signature=value.split(".",1)
  expires=int(expires_str)
  if expires<int(time.time()) or expires>int(time.time())+SESSION_SECONDS: return False
  record=password_record()
  return bool(record) and hmac.compare_digest(signature,session_signature(expires,record))
 except (ValueError,KeyError,TypeError,AttributeError): return False

def allow_login(address):
 now=time.monotonic()
 with LOGIN_LOCK:
  attempts=[t for t in LOGIN_ATTEMPTS.get(address,[]) if now-t<60]
  if len(attempts)>=6:
   LOGIN_ATTEMPTS[address]=attempts
   return False
  attempts.append(now)
  LOGIN_ATTEMPTS[address]=attempts
  return True

class Handler(BaseHTTPRequestHandler):
 def send_json(self,status,value,extra_headers=()):
  b=json.dumps(value).encode()
  self.send_response(status);self.send_header("Content-Type","application/json")
  for name,value in extra_headers: self.send_header(name,value)
  self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff")
  self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def authorized(self):
  cookie=self.headers.get("Cookie","")
  for part in cookie.split(";"):
   name,sep,value=part.strip().partition("=")
   if sep and name=="infoscreen_session": return check_session(value)
  return False
 def same_origin(self):
  # Require a custom header and reject cross-origin write attempts.
  if self.headers.get("X-InfoScreen-Request")!="1": return False
  origin=self.headers.get("Origin")
  if not origin: return True
  from urllib.parse import urlsplit
  parsed=urlsplit(origin)
  return parsed.scheme in ("http","https") and parsed.netloc==self.headers.get("Host")
 def read_json(self,max_size=4096):
  size=int(self.headers.get("Content-Length","0"))
  if size<2 or size>max_size: raise ValueError("Invalid payload size")
  return json.loads(self.rfile.read(size))
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
  if path=="/api/session": return self.send_json(200 if self.authorized() else 401,{"authenticated":self.authorized()})
  if path=="/app.js":
   b=(WEB.parent/"app.js").read_bytes()
   self.send_response(200);self.send_header("Content-Type","application/javascript; charset=utf-8")
   self.send_header("Cache-Control","no-cache");self.send_header("Content-Length",str(len(b)))
   self.end_headers();self.wfile.write(b);return
  if path=="/api/config":
   if not self.authorized():return self.send_json(401,{"error":"Unauthorized"})
   return self.send_json(200,load())
  if path not in ("/","/index.html"): return self.send_json(404,{"error":"Not found"})
  b=WEB.read_bytes()
  self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
  self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
  self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  path=urlsplit(self.path).path
  if path=="/api/login":
   if not self.same_origin():return self.send_json(403,{"error":"Forbidden"})
   if not allow_login(self.client_address[0]):return self.send_json(429,{"error":"Too many attempts"})
   try: value=self.read_json()
   except (ValueError,TypeError):return self.send_json(400,{"error":"Bad request"})
   if not isinstance(value,dict) or not isinstance(value.get("password"),str) or len(value["password"])>1024 or not check_password(value["password"]):
    return self.send_json(401,{"error":"Invalid password"})
   cookie="infoscreen_session="+new_session()+"; HttpOnly; SameSite=Strict; Path=/; Max-Age="+str(SESSION_SECONDS)
   return self.send_json(200,{"ok":True},(("Set-Cookie",cookie),))
  if path=="/api/logout":
   if not self.same_origin():return self.send_json(403,{"error":"Forbidden"})
   return self.send_json(200,{"ok":True},(("Set-Cookie","infoscreen_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"),))
  if path!="/api/background":return self.send_json(404,{"error":"Not found"})
  if not self.authorized():return self.send_json(401,{"error":"Unauthorized"})
  if not self.same_origin():return self.send_json(403,{"error":"Forbidden"})
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
  if not self.same_origin():return self.send_json(403,{"error":"Forbidden"})
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
