import importlib.util,unittest,urllib.error
from pathlib import Path
class Response:
 def __init__(self,status=200,data=b'ok'):self.status=status;self.data=data;self.will_close=False
 def read(self,n):return self.data[:n]
class Conn:
 def __init__(self,rs):self.rs=list(rs);self.closed=False;self.requests=[]
 def request(self,*args):self.requests.append(args)
 def getresponse(self):return self.rs.pop(0)
 def close(self):self.closed=True
class Controls(unittest.TestCase):
 def setUp(self):
  p=Path(__file__).with_name('public_transport.py');self.assertTrue(p.exists(),'public transport missing');s=importlib.util.spec_from_file_location('pool',p);self.m=importlib.util.module_from_spec(s);s.loader.exec_module(self.m)
 def test_reuses_verified_host_connection(self):
  c=Conn([Response(),Response()]);calls=[];p=self.m.Reader(lambda:(calls.append(1) or c))
  self.assertEqual(p.read('https://data.binance.vision/a'),b'ok');self.assertEqual(p.read('https://data.binance.vision/b'),b'ok');self.assertEqual(len(calls),1)
 def test_not_found_is_explicit(self):
  p=self.m.Reader(lambda:Conn([Response(404)]))
  with self.assertRaises(urllib.error.HTTPError) as e:p.read('https://data.binance.vision/a')
  self.assertEqual(e.exception.code,404)
  e.exception.close()
 def test_size_bound_closes_connection(self):
  c=Conn([Response(data=b'x'*2000001)]);p=self.m.Reader(lambda:c)
  with self.assertRaises(ValueError):p.read('https://data.binance.vision/a')
  self.assertTrue(c.closed)
 def test_foreign_or_credential_url_refused(self):
  p=self.m.Reader(lambda: self.fail('must reject before connection'))
  for url in ['http://data.binance.vision/a','https://api.binance.com/a','https://x@data.binance.vision/a']:
   with self.assertRaises(ValueError):p.read(url)
if __name__=='__main__':unittest.main()
