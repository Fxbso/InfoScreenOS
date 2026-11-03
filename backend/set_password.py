#!/usr/bin/env python3
"""Change the local InfoScreen dashboard password (root only)."""
import getpass
import os
import pathlib
import secrets
import sys
import tempfile
import grp
from app import PASSWORD_FILE, make_password_hash

def main():
 if os.geteuid()!=0:
  sys.exit("Run with sudo.")
 if len(sys.argv)==2 and sys.argv[1]=="--generate":
  password=secrets.token_urlsafe(18)
 elif len(sys.argv)==1:
  password=getpass.getpass("Neues InfoScreen-Passwort (mind. 10 Zeichen): ")
  confirm=getpass.getpass("Passwort wiederholen: ")
  if password!=confirm: sys.exit("Passwörter stimmen nicht überein.")
  if len(password)<10: sys.exit("Mindestens 10 Zeichen verwenden.")
 else:
  sys.exit("Usage: sudo python3 /opt/kufgem-infoscreen/backend/set_password.py [--generate]")
 target=pathlib.Path(PASSWORD_FILE)
 target.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=target.parent,prefix=".password-")
 try:
  import json
  with os.fdopen(fd,"w") as out:
   json.dump(make_password_hash(password),out)
   out.flush()
   os.fsync(out.fileno())
  os.chown(tmp,0,grp.getgrnam("infoscreen").gr_gid)
  os.chmod(tmp,0o640)
  os.replace(tmp,target)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
 if len(sys.argv)==2:
  print("Einmaliges Startpasswort:",password)
 else:
  print("Passwort gespeichert. Bestehende Anmeldungen sind ab sofort ungültig.")

if __name__=="__main__":
 main()
