import copy, pathlib, tempfile, unittest, json
from backend import app
class ConfigTest(unittest.TestCase):
 def test_defaults(self): self.assertEqual(app.validate(copy.deepcopy(app.DEFAULT))["widgets"][0]["type"],"clock")
 def test_rejects_bad_layout(self):
  d=copy.deepcopy(app.DEFAULT);d["widgets"][0]["x"]=-1
  with self.assertRaises(ValueError):app.validate(d)
 def test_persist(self):
  with tempfile.TemporaryDirectory() as p:
   old=app.DATA
   try:
    app.DATA=pathlib.Path(p)
    d=copy.deepcopy(app.DEFAULT);d["title"]="Updated"
    app.save(d)
    self.assertEqual(app.load()["title"],"Updated")
   finally:app.DATA=old
class PasswordAuthTest(unittest.TestCase):
 def test_password_hash_and_sessions(self):
  with tempfile.TemporaryDirectory() as tmp:
   previous=app.PASSWORD_FILE
   try:
    app.PASSWORD_FILE=pathlib.Path(tmp)/"password.json"
    record=app.make_password_hash("Test-Passwort-123")
    app.PASSWORD_FILE.write_text(json.dumps(record))
    self.assertTrue(app.check_password("Test-Passwort-123"))
    self.assertFalse(app.check_password("falsch"))
    cookie=app.new_session()
    self.assertTrue(app.check_session(cookie))
    self.assertFalse(app.check_session(cookie+"tampered"))
    app.PASSWORD_FILE.write_text(json.dumps(app.make_password_hash("Neues-Passwort-123")))
    self.assertFalse(app.check_session(cookie))
   finally:
    app.PASSWORD_FILE=previous

if __name__=="__main__":unittest.main()
