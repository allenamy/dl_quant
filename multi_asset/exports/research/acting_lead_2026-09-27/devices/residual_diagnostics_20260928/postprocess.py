"""One bounded consumer: decisions and reproducibility archive after true terminal."""
import hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
R=Path(sys.argv[1]);S=Path(str(R)+'_sources')
C=json.loads((S/'CONTRACT.json').read_text())
P=R/'POSTPROCESS_TERMINAL.json'

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def write(p,d):
 with open(p,'x') as f:json.dump(d,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())

rc=1;result={'source_sha256':sha(__file__),'device_commit':'recorded in launcher','production_changes':0}
try:
 while not (R/'TERMINAL.json').exists():
  if time.time()>C['deadline_epoch']+60:raise TimeoutError('batch terminal missing past deadline')
  time.sleep(5)
 t=json.loads((R/'TERMINAL.json').read_text())
 if t['rc']!=0:raise RuntimeError('upstream failed: '+str(t.get('error')))
 inp=R/'receipts/ECONOMIC_FULL_BOOK.json';out=R/'receipts/BOOK_DECISION.json'
 subprocess.run([sys.executable,'-B',str(HERE/'book_decision.py'),str(inp),str(out)],check=True,timeout=30)
 files=[]
 for base,prefix in [(R,'batch'),(S,'sources'),(HERE,'diagnostics')]:
  for p in sorted(base.rglob('*')):
   if p.is_symlink() or not p.is_file():continue
   if p.suffix in ('.json','.py','.log') or p.name=='model.npz':files.append((p,prefix+'/'+str(p.relative_to(base))))
 manifest={'files':[{'source_path':str(p),'archive_name':name,'bytes':p.stat().st_size,'sha256':sha(p)} for p,name in files],
  'large_artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(R.rglob('*.npz')) if p.is_file() and not p.is_symlink() and p.name!='model.npz'],
  'economic_sha256':sha(inp),'decision_sha256':sha(out),'prereg_commit':C['prereg_commit'],'source_commit':C['source_commit']}
 mp=R/'receipts/REVIEW_MANIFEST.json';write(mp,manifest)
 ap=R/'receipts/REVIEW_ARCHIVE.zip'
 with zipfile.ZipFile(ap,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for p,name in files:z.write(p,name)
  z.write(mp,'REVIEW_MANIFEST.json')
 result.update(status='POSTPROCESS_COMPLETE_NOT_RELEASE',archive_path=str(ap),archive_sha256=sha(ap),archive_bytes=ap.stat().st_size,files=len(files),large_artifacts=len(manifest['large_artifacts']),book_decision=json.loads(out.read_text())['status']);rc=0
except BaseException as e:result.update(status='POSTPROCESS_FAILED',error=repr(e))
finally:
 result.update(rc=rc,utc=time.strftime('%FT%TZ',time.gmtime()));write(P,result)
sys.exit(rc)
