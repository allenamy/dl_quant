import csv,hashlib,io,json,unittest,zipfile
from download import validate, archive_url

class ArchiveTests(unittest.TestCase):
 def make(self, rows=None, name='BTCUSDT-5m-2026-09-26.csv'):
  r=rows or [['1790380800000','10','12','9','11','1','1790381099999','10','2','0.5','5','0']]
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:z.writestr(name,'\n'.join(','.join(x) for x in r))
  b=out.getvalue();return b,hashlib.sha256(b).hexdigest()+'  BTCUSDT-5m-2026-09-26.zip\n'
 def check(self,**kw):
  b,c=self.make(**kw);return validate(b,c,'BTCUSDT','2026-09-26')
 def test_unicode_exchange_symbol(self):
  self.assertIn('%E5%B8%81',archive_url('币安人生USDT','2026-09-26'))
 def test_path_component_reject(self):
  with self.assertRaises(ValueError):archive_url('../BTCUSDT','2026-09-26')
 def test_partial_is_visible(self):
  x=self.check();self.assertEqual(x['rows'],1);self.assertFalse(x['full_day'])
 def test_bad_hash(self):
  b,c=self.make()
  with self.assertRaises(ValueError):validate(b,c.replace(c[:64],'0'*64),'BTCUSDT','2026-09-26')
 def test_wrong_filename(self):
  b,c=self.make()
  with self.assertRaises(ValueError):validate(b,c.replace('BTCUSDT','ETHUSDT'),'BTCUSDT','2026-09-26')
 def test_zip_identity(self):
  with self.assertRaises(ValueError):self.check(name='different.csv')
 def test_nonfinite(self):
  with self.assertRaises(ValueError):self.check(rows=[['1790380800000','10','12','9','nan','1','1790381099999','10','2','0.5','5','0']])
 def test_time_grid(self):
  with self.assertRaises(ValueError):self.check(rows=[['1790380800001','10','12','9','11','1','1790381099999','10','2','0.5','5','0']])
 def test_duplicate(self):
  row=['1790380800000','10','12','9','11','1','1790381099999','10','2','0.5','5','0']
  with self.assertRaises(ValueError):self.check(rows=[row,row])
if __name__=='__main__':unittest.main()
