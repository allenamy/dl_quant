"""Immutable public daily files + official SHA; no trading API or credentials.
Missing archives and partial days remain explicit. No zero fill or price inference.
"""
import concurrent.futures as cf
import csv,datetime as dt,hashlib,io,json,math,os,re,sys,time,urllib.request,urllib.error,urllib.parse,zipfile
from pathlib import Path
BASE='https://data.binance.vision/data/futures/um/daily/klines'
def archive_url(symbol, day):
 if not isinstance(symbol,str) or not symbol.isalnum():raise ValueError('symbol path component')
 if dt.date.fromisoformat(day).isoformat()!=day:raise ValueError('day')
 return f'{BASE}/{urllib.parse.quote(symbol,safe="")}/5m/{urllib.parse.quote(symbol+"-5m-"+day+".zip",safe="")}'
def digest(b):return hashlib.sha256(b).hexdigest()
def validate(raw, checksum, symbol, day):
 name=f'{symbol}-5m-{day}.zip';parts=checksum.split()
 if len(parts)!=2 or parts[1].lstrip('*')!=name or not re.fullmatch('[0-9a-f]{64}',parts[0]) or digest(raw)!=parts[0]:raise ValueError('checksum identity')
 start=int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp())*1000
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if z.namelist()!=[name[:-4]+'.csv'] or z.infolist()[0].file_size>1000000:raise ValueError('zip identity or size')
  rows=list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
 if rows and rows[0][0]=='open_time':rows=rows[1:]
 if not rows:raise ValueError('empty archive')
 times=[]
 for r in rows:
  if len(r)!=12:raise ValueError('schema')
  a=int(r[0]);b=int(r[6]);v=[float(x) for x in r]
  if not all(math.isfinite(x) for x in v):raise ValueError('nonfinite')
  if a<start or a>=start+86400000 or (a-start)%300000 or b!=a+299999:raise ValueError('timestamp')
  if min(v[1:5])<=0 or not (v[3]<=v[1]<=v[2] and v[3]<=v[4]<=v[2]):raise ValueError('OHLC')
  if any(v[i]<0 for i in (5,7,8,9,10)) or v[8]!=int(v[8]):raise ValueError('volume/count')
  times.append(a)
 if times!=sorted(set(times)):raise ValueError('duplicate/unordered')
 return {'rows':len(rows),'full_day':len(rows)==288,'first_open_ms':times[0],'last_open_ms':times[-1],
         'missing_bars':288-len(rows),'zero_volume_bars':sum(float(r[5])==0 for r in rows),'sha256':digest(raw),'bytes':len(raw)}
def write(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def read_url(url):
 with urllib.request.urlopen(url,timeout=12) as r:
  b=r.read(2000001)
  if len(b)>2000000:raise ValueError('response size')
  return b

def run(contract):
 C=json.loads(Path(contract).read_text());root=Path(C['root']);root.mkdir(exist_ok=False)
 if digest(Path(__file__).read_bytes())!=C['device_sha256']:raise ValueError('device drift')
 if len(C['symbols'])!=len(set(C['symbols'])) or any(not isinstance(s,str) or not s.isalnum() for s in C['symbols']):raise ValueError('symbols')
 results=[];jobs=[(s,d) for d in C['days'] for s in C['symbols']]
 def one(job):
  s,d=job;name=f'{s}-5m-{d}.zip';url=archive_url(s,d)
  rec={'symbol':s,'day':d,'url':url,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  if time.time()>C['deadline_epoch']:return dict(rec,status='UNATTEMPTED_BUDGET')
  try:
   chk=read_url(url+'.CHECKSUM');raw=read_url(url)
   v=validate(raw,chk.decode(),s,d);p=root/'archives'/s/name
   write(p,raw);write(Path(str(p)+'.CHECKSUM'),chk)
   return dict(rec,status='VERIFIED_ARCHIVE',file=str(p),checksum_sha256=digest(chk),**v)
  except urllib.error.HTTPError as e:return dict(rec,status='ARCHIVE_ABSENT' if e.code==404 else 'HTTP_ERROR',http_status=e.code)
  except Exception as e:return dict(rec,status='UNAVAILABLE',error=repr(e))
 with cf.ThreadPoolExecutor(max_workers=4) as ex:
  for x in ex.map(one,jobs):
   results.append(x)
   if len(results)%200==0:print('processed',len(results),'/',len(jobs),flush=True)
 counts={k:sum(x['status']==k for x in results) for k in sorted({x['status'] for x in results})}
 out={'schema':'public_recent_prices/1','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'contract_sha256':digest(Path(contract).read_bytes()),
      'source_sha256':digest(Path(__file__).read_bytes()),'counts':counts,'results':results,
      'scope':'archive integrity only;absent/partial remain unknown;not full replay or labels','python':sys.executable}
 write(root/'MANIFEST.json',(json.dumps(out,indent=2,allow_nan=False)+'\n').encode())
 bad=sum(v for k,v in counts.items() if k not in ('VERIFIED_ARCHIVE','ARCHIVE_ABSENT'))
 write(root/'TERMINAL.json',(json.dumps({'rc':1 if bad else 0,'status':'COLLECTION_WITH_EXPLICIT_GAPS' if not bad else 'PARTIAL_COLLECTION','counts':counts,'manifest_sha256':digest((root/'MANIFEST.json').read_bytes()),'utc':out['utc']},indent=2)+'\n').encode())
 print('FINISHED',counts,flush=True)
if __name__=='__main__':
 try:run(sys.argv[1])
 except BaseException as e:
  c=json.loads(Path(sys.argv[1]).read_text());root=Path(c['root']);root.mkdir(exist_ok=True)
  if not (root/'TERMINAL.json').exists():write(root/'TERMINAL.json',(json.dumps({'rc':1,'status':'FAILED','error':repr(e),'utc':dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+'\n').encode())
  raise
