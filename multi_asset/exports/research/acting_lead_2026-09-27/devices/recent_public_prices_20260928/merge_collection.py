"""Close the original request population; collection integrity is not replay parity."""
from pathlib import Path
import json,sys,zipfile,collections,datetime
import download as D

ROOTS=[Path('/dev/shm/recent_public_prices_20260928_'+x) for x in ('attempt2','continue1','tail')]
def merge(out):
 allrows={};pins={};unresolved={'UNATTEMPTED_BUDGET','HTTP_ERROR','UNAVAILABLE'}
 for i,root in enumerate(ROOTS):
  cp=root.with_name(root.name+'_sources')/'CONTRACT.json';mp=root/'MANIFEST.json';tp=root/'TERMINAL.json'
  c=json.loads(cp.read_bytes());m=json.loads(mp.read_bytes());t=json.loads(tp.read_bytes())
  if m['contract_sha256']!=D.digest(cp.read_bytes()) or t['manifest_sha256']!=D.digest(mp.read_bytes()):raise ValueError('segment identity')
  if i==0:expected={(s,d) for s in c['symbols'] for d in c['days']}
  else:
   inv=Path(c['inventory']);raw=inv.read_bytes()
   if D.digest(raw)!=c['inventory_sha256']:raise ValueError('inventory identity')
   expected={(x['symbol'],x['day']) for x in json.loads(raw)['archive_requests']}
   if expected!={k for k,v in allrows.items() if v['status'] in unresolved}:raise ValueError('continuation shrinks or expands pending population')
   pins[str(inv)]=D.digest(raw)
  actual=[(x['symbol'],x['day']) for x in m['results']]
  if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('segment population')
  if collections.Counter(x['status'] for x in m['results'])!=collections.Counter(t['counts']):raise ValueError('terminal counts')
  for x in m['results']:
   if x['status']=='VERIFIED_ARCHIVE':
    p=Path(x['file']);raw=p.read_bytes();ch=Path(str(p)+'.CHECKSUM').read_bytes()
    if D.digest(raw)!=x['sha256'] or D.digest(ch)!=x['checksum_sha256']:raise ValueError('archive changed')
    proof=D.validate(raw,ch.decode(),x['symbol'],x['day'])
    for k,v in proof.items():
     if x[k]!=v:raise ValueError('record does not describe validated bytes')
   elif x['status']=='ARCHIVE_ABSENT':
    if x['http_status']!=404:raise ValueError('absence not 404')
   elif x['status'] not in unresolved:raise ValueError('unknown status')
   allrows[(x['symbol'],x['day'])]=x
  for p in (cp,mp,tp):pins[str(p)]=D.digest(p.read_bytes())
 rows=[allrows[k] for k in sorted(allrows)];counts=dict(collections.Counter(x['status'] for x in rows));byday={}
 for d in sorted({x['day'] for x in rows}):
  rr=[x for x in rows if x['day']==d];byday[d]=dict(collections.Counter(x['status'] for x in rr));byday[d]['partial_day_archives']=sum(x['status']=='VERIFIED_ARCHIVE' and not x['full_day'] for x in rr)
 result={'status':'REQUEST_POPULATION_CLOSED_WITH_EXPLICIT_ABSENCES' if not any(k in unresolved for k in counts) else 'PARTIAL','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':D.digest(Path(__file__).read_bytes()),'validator_sha256':D.digest(Path(D.__file__).read_bytes()),'n_requests':len(rows),'counts':counts,'by_day':byday,'receipt_pins':pins,'results':rows,'limits':['Archive integrity only; not production-channel parity','404 is not delisting proof; partial days stay partial','No model, feature or cash input changed']}
 D.write(Path(out),(json.dumps(result,indent=2)+'\n').encode());print({k:v for k,v in result.items() if k not in ('results','receipt_pins','by_day')})

def stream_archive(merged):
 mp=Path(merged);m=json.loads(mp.read_text());files=dict(m['receipt_pins']);files[str(mp)]=D.digest(mp.read_bytes());files[str(Path(__file__))]=D.digest(Path(__file__).read_bytes());files[str(Path(D.__file__))]=D.digest(Path(D.__file__).read_bytes())
 for r in m['results']:
  if r['status']=='VERIFIED_ARCHIVE':files[r['file']]=r['sha256'];files[r['file']+'.CHECKSUM']=r['checksum_sha256']
 manifest={}
 with zipfile.ZipFile(sys.stdout.buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for path,h in sorted(files.items()):
   p=Path(path);raw=p.read_bytes()
   if D.digest(raw)!=h:raise ValueError('archive input drift')
   name=str(p).removeprefix('/dev/shm/')
   if name in manifest:raise ValueError('archive duplicate name')
   z.writestr(name,raw);manifest[name]={'sha256':h,'bytes':len(raw)}
  z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':
 if sys.argv[1]=='merge':merge(sys.argv[2])
 elif sys.argv[1]=='archive':stream_archive(sys.argv[2])
 else:raise ValueError('mode')
