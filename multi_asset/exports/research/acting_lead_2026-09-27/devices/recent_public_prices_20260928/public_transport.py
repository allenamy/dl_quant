"""Thread-local persistent TLS for public static archives, without API access."""
import http.client,ssl,threading,urllib.parse,urllib.error

class Reader:
 def __init__(self,factory=None):
  self.local=threading.local();self.factory=factory or (lambda:http.client.HTTPSConnection('data.binance.vision',timeout=12,context=ssl.create_default_context()))
 def read(self,url):
  u=urllib.parse.urlsplit(url)
  if u.scheme!='https' or u.netloc!='data.binance.vision' or u.fragment:raise ValueError('public static archive host only')
  c=getattr(self.local,'conn',None)
  if c is None:c=self.factory();self.local.conn=c
  try:
   c.request('GET',u.path+('?' + u.query if u.query else ''))
   r=c.getresponse();b=r.read(2000001)
   if len(b)>2000000:raise ValueError('response size')
   if r.will_close:c.close();self.local.conn=None
   if r.status!=200:raise urllib.error.HTTPError(url,r.status,'public static status',None,None)
   return b
  except BaseException:
   c.close();self.local.conn=None;raise

reader=Reader()
