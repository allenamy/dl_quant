"""Plan only missing jobs from the immutable 837 x 11 archive population."""
from pathlib import Path
import json,subprocess,os,time,sys
import download as D

def run():
 old=Path('/dev/shm/recent_public_prices_20260928_attempt2');src=Path(__file__).parent
 root=Path('/dev/shm/recent_public_prices_20260928_continue1')
 raw=(old/'MANIFEST.json').read_bytes();m=json.loads(raw);t=json.loads((old/'TERMINAL.json').read_text())
 cp=old.with_name(old.name+'_sources')/'CONTRACT.json';c=json.loads(cp.read_text())
 if t['rc']!=1 or t['status']!='PARTIAL_COLLECTION' or t['manifest_sha256']!=D.digest(raw) or m['contract_sha256']!=D.digest(cp.read_bytes()):raise ValueError('parent identity/status')
 expected={(s,d) for s in c['symbols'] for d in c['days']};actual=[(r['symbol'],r['day']) for r in m['results']]
 if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('parent population')
 pending=[]
 for r in m['results']:
  if r['status']=='VERIFIED_ARCHIVE':
   p=Path(r['file']);b=p.read_bytes();ch=Path(str(p)+'.CHECKSUM').read_bytes()
   if D.digest(b)!=r['sha256'] or D.digest(ch)!=r['checksum_sha256']:raise ValueError('preserved input drift')
   D.validate(b,ch.decode(),r['symbol'],r['day'])
  elif r['status']=='ARCHIVE_ABSENT':
   if r['http_status']!=404:raise ValueError('absence status')
  elif r['status'] in ('UNATTEMPTED_BUDGET','HTTP_ERROR','UNAVAILABLE'):pending.append({'symbol':r['symbol'],'day':r['day']})
  else:raise ValueError('unknown status')
 pending.sort(key=lambda r:(r['day'],r['symbol']),reverse=True)
 inv=src/'INVENTORY.json';D.write(inv,(json.dumps({'archive_requests':pending,'parent_manifest_sha256':D.digest(raw),'full_population':len(expected)},indent=2)+'\n').encode())
 contract={'root':str(root),'inventory':str(inv),'inventory_sha256':D.digest(inv.read_bytes()),'library_sha256':D.digest((src/'download.py').read_bytes()),'device_sha256':D.digest((src/'collect_label_proofs.py').read_bytes()),'additional_sources':{n:D.digest((src/n).read_bytes()) for n in ('collect_pooled.py','public_transport.py','resume_recent_archives.py')},'deadline_epoch':time.time()+900,'scope':'Only previously unattempted/unavailable jobs; static archives, 4 threads, same validators. Latest dates first. Not replay/training or production.'}
 cp=src/'CONTRACT.json';D.write(cp,(json.dumps(contract,indent=2)+'\n').encode())
 with open(src/'RUN.log','xb') as log:
  p=subprocess.Popen([sys.executable,str(src/'collect_pooled.py'),str(cp)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=src,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
 rec={'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'contract_sha256':D.digest(cp.read_bytes()),'pending_jobs':len(pending),'original_population':len(expected),'utc':time.strftime('%FT%TZ',time.gmtime()),'deadline_epoch':contract['deadline_epoch']}
 D.write(src/'LAUNCH.json',(json.dumps(rec,indent=2)+'\n').encode());print(json.dumps(rec))
if __name__=='__main__':run()
