import hashlib,json,tempfile,unittest
from pathlib import Path
from control_binding import check_config_and_spec

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class ControlBindingTest(unittest.TestCase):
 def test_same_control_and_changed_config_or_spec(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'cfg';p.write_text('{"fee":2,"gross":2}')
   rec={'steps':{'run_config':{'base_config':str(p),'base_config_sha256':sha(p)}}}
   base={'price_meta':{'sha256':'a'},'universe':{'sha256':'b'},'window_first_anchor':'2023'}
   check_config_and_spec(rec,p,base,base)
   p.write_text('{"fee":3,"gross":2}')
   with self.assertRaises(ValueError):check_config_and_spec(rec,p,base,base)
   p.write_text('{"fee":2,"gross":2}')
   for bad in (dict(base,window_first_anchor='2024'),dict(base,universe={'sha256':'changed'})):
    with self.assertRaises(ValueError):check_config_and_spec(rec,p,base,bad)

if __name__=='__main__':unittest.main()
