"""Prove potential replacements for missing training labels; never mutate inputs."""
from pathlib import Path
import csv,io,json,math,sys,zipfile
import download as D

def label_from_closes(prices, anchor):
 if type(anchor)!=int or anchor%14400:raise ValueError('anchor identity')
 ts=[anchor+300*k for k in range(49)];vals=[prices.get(t) for t in ts]
 for v in vals:
  if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<=0):raise ValueError('invalid raw close')
 missing=[t for t,v in zip(ts,vals) if v is None]
 return {'status':'UNAVAILABLE' if missing else 'OBSERVED','n_closes':49-len(missing),'missing_ts':missing,'y4s':None if missing else vals[-1]/vals[0]-1}

def run(inv_path,root,out):
 inv_raw=Path(inv_path).read_bytes();inv=json.loads(inv_raw);mf=root/'MANIFEST.json';raw=mf.read_bytes();m=json.loads(raw);t=json.loads((root/'TERMINAL.json').read_text());c=json.loads((root.with_name(root.name+'_sources')/'CONTRACT.json').read_text())
 if t['rc']!=0 or t['manifest_sha256']!=D.digest(raw) or m['contract_sha256']!=D.digest((root.with_name(root.name+'_sources')/'CONTRACT.json').read_bytes()) or c['inventory_sha256']!=D.digest(inv_raw):raise ValueError('receipt identity')
 expected={(r['symbol'],r['day']) for r in inv['archive_requests']};actual=[(r['symbol'],r['day']) for r in m['results']]
 if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('request population')
 prices={};proofs={}
 for r in m['results']:
  if r['status']!='VERIFIED_ARCHIVE':continue
  p=Path(r['file']);b=p.read_bytes();chk=Path(str(p)+'.CHECKSUM').read_bytes()
  if D.digest(b)!=r['sha256'] or D.digest(chk)!=r['checksum_sha256']:raise ValueError('archive drift')
  D.validate(b,chk.decode(),r['symbol'],r['day']);proofs[str(p)]=r['sha256']
  with zipfile.ZipFile(io.BytesIO(b)) as z:rows=list(csv.reader(z.read(z.namelist()[0]).decode().splitlines()))
  if rows[0][0]=='open_time':rows=rows[1:]
  dest=prices.setdefault(r['symbol'],{})
  for q in rows:
   when=(int(q[6])+1)//1000;v=float(q[4])
   if when in dest and dest[when]!=v:raise ValueError('conflicting observed close')
   dest[when]=v
 rows=[dict(r,**label_from_closes(prices.get(r['symbol'],{}),r['anchor'])) for r in inv['missing_labels']]
 windows={i:[] for i in range(inv['raw_windows'])}
 for r in rows:
  for wi in r['windows']:windows[wi].append(r)
 formerly_bad={i:rs for i,rs in windows.items() if rs};assert len(formerly_bad)==inv['bad_windows']
 recovered=[i for i,rs in formerly_bad.items() if all(r['status']=='OBSERVED' for r in rs)]
 result={'status':'PRICE_PROOFS_ONLY_NOT_APPLIED','scope':'counterfactual label availability;not retrained or book returns;archive availability not millisecond PIT certified','source_sha256':D.digest(Path(__file__).read_bytes()),'library_sha256':D.digest(Path(D.__file__).read_bytes()),'inventory_sha256':D.digest(inv_raw),'manifest_sha256':D.digest(raw),'archive_pins':proofs,'n_missing_original':len(rows),'n_observed_provable':sum(r['status']=='OBSERVED' for r in rows),'n_still_unknown':sum(r['status']!='OBSERVED' for r in rows),'formerly_rejected_windows':len(formerly_bad),'fully_priced_windows':recovered,'rows':rows}
 D.write(out,(json.dumps(result,indent=2,allow_nan=False)+'\n').encode());print({k:v for k,v in result.items() if k.startswith('n_') or k in ('formerly_rejected_windows','fully_priced_windows')})
if __name__=='__main__':run(sys.argv[1],Path(sys.argv[2]),Path(sys.argv[3]))
