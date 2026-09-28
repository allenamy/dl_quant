"""Bounded terminal consumer: no polling after deadline; archive all evidence."""
import json,sys,time,zipfile,os
from pathlib import Path
from cash_contract import sha,decide
R=Path(sys.argv[1]);S=Path(__file__).resolve().parent;C=json.loads((S/'CONTRACT.json').read_text())
rc=1;result={'source_sha256':sha(__file__)}
def write(p,x):
    with open(p,'x') as f:json.dump(x,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
try:
    while not (R/'TERMINAL.json').exists():
        if time.time()>C['deadline_epoch']+60:raise TimeoutError('missing terminal')
        time.sleep(5)
    terminal=json.loads((R/'TERMINAL.json').read_text())
    if terminal['rc']!=0:raise RuntimeError('upstream failed: '+str(terminal.get('error')))
    econ=R/'receipts/ECONOMIC_FULL_BOOK.json';d=decide(json.loads(econ.read_text()))
    d['economic_sha256']=sha(econ);write(R/'receipts/BOOK_DECISION.json',d)
    files=[]
    for root,prefix in ((R,'batch'),(S,'sources')):
        for p in sorted(root.rglob('*')):
            if p.is_file() and not p.is_symlink() and p.suffix in ('.py','.json','.log'):
                files.append((p,prefix+'/'+str(p.relative_to(root))))
    manifest={'files':[{'source_path':str(p),'archive_name':n,'bytes':p.stat().st_size,'sha256':sha(p)} for p,n in files],
        'large_artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(R.rglob('*.npz')) if p.is_file() and not p.is_symlink()]}
    write(R/'receipts/REVIEW_MANIFEST.json',manifest)
    ap=R/'receipts/REVIEW_ARCHIVE.zip'
    with zipfile.ZipFile(ap,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p,n in files:z.write(p,n)
        z.write(R/'receipts/REVIEW_MANIFEST.json','REVIEW_MANIFEST.json')
    result.update(status='POSTPROCESS_COMPLETE_NOT_RELEASE',archive_path=str(ap),archive_sha256=sha(ap),decision=d['status']);rc=0
except BaseException as e:result.update(status='FAILED',error=repr(e))
finally:
    result.update(rc=rc,utc=time.strftime('%FT%TZ',time.gmtime()))
    if R.exists():write(R/'POSTPROCESS_TERMINAL.json',result)
sys.exit(rc)
