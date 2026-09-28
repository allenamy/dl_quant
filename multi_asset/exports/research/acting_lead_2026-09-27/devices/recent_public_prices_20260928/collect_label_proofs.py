"""Fetch only the exact archive pairs enumerated by a pinned label-gap inventory."""
from pathlib import Path
import concurrent.futures as cf
import datetime as dt,json,sys,time,urllib.error
import download as D

def main(contract):
 c=json.loads(Path(contract).read_text());p=Path(c['inventory']);b=p.read_bytes()
 if D.digest(b)!=c['inventory_sha256'] or D.digest(Path(D.__file__).read_bytes())!=c['library_sha256'] or D.digest(Path(__file__).read_bytes())!=c['device_sha256']:raise ValueError('source identity')
 inv=json.loads(b);jobs=[(r['symbol'],r['day']) for r in inv['archive_requests']]
 if len(jobs)!=len(set(jobs)):raise ValueError('duplicate request')
 for s,d in jobs:D.archive_url(s,d)
 root=Path(c['root']);root.mkdir(exist_ok=False);results=[]
 def one(sd):
  s,d=sd;url=D.archive_url(s,d);r={'symbol':s,'day':d,'url':url}
  if time.time()>c['deadline_epoch']:return dict(r,status='UNATTEMPTED_BUDGET')
  try:
   chk=D.read_url(url+'.CHECKSUM');raw=D.read_url(url);v=D.validate(raw,chk.decode(),s,d);p=root/'archives'/s/f'{s}-5m-{d}.zip';D.write(p,raw);D.write(Path(str(p)+'.CHECKSUM'),chk)
   return dict(r,status='VERIFIED_ARCHIVE',file=str(p),checksum_sha256=D.digest(chk),**v)
  except urllib.error.HTTPError as e:return dict(r,status='ARCHIVE_ABSENT' if e.code==404 else 'HTTP_ERROR',http_status=e.code)
  except Exception as e:return dict(r,status='UNAVAILABLE',error=repr(e))
 workers=c.get('workers',4)
 if type(workers)!=int or workers not in (4,8):raise ValueError('bounded static-download workers')
 with cf.ThreadPoolExecutor(max_workers=workers) as ex:
  for r in ex.map(one,jobs):
   results.append(r)
   if len(results)%25==0:print('processed',len(results),'/',len(jobs),flush=True)
 counts={k:sum(r['status']==k for r in results) for k in sorted({r['status'] for r in results})}
 x={'scope':'raw archive proofs only; no label, feature, model, or cash inputs rewritten','contract_sha256':D.digest(Path(contract).read_bytes()),'counts':counts,'results':results,'utc':dt.datetime.now(dt.timezone.utc).isoformat()};D.write(root/'MANIFEST.json',(json.dumps(x,indent=2)+'\n').encode())
 bad=sum(v for k,v in counts.items() if k not in ('VERIFIED_ARCHIVE','ARCHIVE_ABSENT'))
 D.write(root/'TERMINAL.json',(json.dumps({'rc':int(bool(bad)),'status':'COLLECTED_WITH_EXPLICIT_GAPS','counts':counts,'manifest_sha256':D.digest((root/'MANIFEST.json').read_bytes()),'utc':x['utc']},indent=2)+'\n').encode());print(counts,flush=True)
if __name__=='__main__':
 try:main(sys.argv[1])
 except BaseException as e:
  c=json.loads(Path(sys.argv[1]).read_text());r=Path(c['root']);r.mkdir(exist_ok=True)
  if not (r/'TERMINAL.json').exists():D.write(r/'TERMINAL.json',(json.dumps({'rc':1,'error':repr(e)})+'\n').encode())
  raise
