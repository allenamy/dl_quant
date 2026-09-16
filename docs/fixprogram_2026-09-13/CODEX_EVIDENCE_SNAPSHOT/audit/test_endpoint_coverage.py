import unittest
from fractions import Fraction
from types import SimpleNamespace
import numpy as np
import endpoint_coverage as e
import tempfile,zipfile,hashlib
from pathlib import Path

T=1735693200000
class EndpointControls(unittest.TestCase):
 def fixture(self,q=Fraction(2),mark=10.):
  self.assertTrue(hasattr(e,'EndpointFacts'),'independent endpoint gate must exist')
  f=dict(event_ms=np.array([T],dtype=np.int64),asset=np.array([0]),rate=np.array([.01]),mark=np.array([mark]))
  a=SimpleNamespace(halted=True,positions={'A':dict(instrument_id='A#1',active=True)},_q=lambda s:q)
  v=e.EndpointFacts(f,['A'],{'A#1':dict(symbol='A',start_ms=T-100,end_ms=T+100)},{}, {}, {})
  v.month_cache[('A','2025-01')]=True
  return v,a
 def test_fund_consumed_then_positive_or_negative_exit(self):
  for q in (Fraction(2),Fraction(-2)):
   v,a=self.fixture(q);self.assertEqual(v.check(a,T,1),1)
 def test_unconsumed_same_ms_funding_rejected(self):
  v,a=self.fixture()
  with self.assertRaisesRegex(ValueError,'same-ms funding'):v.check(a,T,0)
 def test_missing_held_endpoint_mark_rejected(self):
  v,a=self.fixture(mark=float('nan'))
  with self.assertRaisesRegex(ValueError,'endpoint rate/mark'):v.check(a,T,1)
 def test_flat_skips_missing_coverage_and_mark(self):
  v,a=self.fixture(Fraction(0),float('nan'));v.month_cache={}
  self.assertEqual(v.check(a,T,1),0)
 def test_missing_month_evidence_rejected(self):
  v,a=self.fixture();v.month_cache={}
  with self.assertRaisesRegex(ValueError,'month evidence'):v.check(a,T,1)
 def test_generation_endpoint_cannot_cross(self):
  v,a=self.fixture();v.segments['A#1']['end_ms']=T
  with self.assertRaisesRegex(ValueError,'generation endpoint'):v.check(a,T,1)
 def test_close_open_new_generation_flat(self):
  v,a=self.fixture(Fraction(0));a.positions['A']['instrument_id']='A#2';v.month_cache={}
  self.assertEqual(v.check(a,T,1),0)
 def test_month_source_omission_is_rejected(self):
  self.assertTrue(hasattr(e,'match_month'),'independent full-month match must exist')
  with self.assertRaisesRegex(ValueError,'month population'):e.match_month({T:.01},{})
  e.match_month({T:.01},{T:.01})
 def test_actual_zip_certificate_and_omitted_fact(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'controls') as root:
   p=Path(root)/'A-fundingRate-2025-01.zip';c=Path(str(p)+'.CHECKSUM')
   with zipfile.ZipFile(p,'w') as z:z.writestr('A-fundingRate-2025-01.csv','calc_time,funding_interval_hours,last_funding_rate\n'+str(T)+',8,0.01\n')
   c.write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
   v,a=self.fixture();v.month_cache={};v.descriptors={'A|2025-01':dict(kind='ORIGINAL_OFFICIAL_ZIP',archive=str(p),checksum=str(c))};v.pins={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (p,c)}
   self.assertEqual(v.check(a,T,1),1)
   v.month_cache={};v.f['rate'][0]=.02
   with self.assertRaisesRegex(ValueError,'month population'):v.check(a,T,1)
if __name__=='__main__':
 import sys
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]),unittest.defaultTestLoader.loadTestsFromName('test_current_dispatch')])
 raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
