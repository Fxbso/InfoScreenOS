import copy, pathlib, tempfile, unittest
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
if __name__=="__main__":unittest.main()
