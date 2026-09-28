"""Archive new LR evidence with hashes; large parent inputs remain separately archived."""
import hashlib,json,time,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
root=Path('/dev/shm/lr_recurrence_20260928');source=Path('/dev/shm/lr_recurrence_20260928_sources');inputs=Path('/dev/shm/lr_recurrence_20260928_inputs')
term=json.loads((root/'TERMINAL.json').read_text());verify=json.loads((root/'VERIFY.json').read_text())
assert term['rc']==0 and term['result_sha256']==sha(root/'RESULT.json')==verify['result_sha256']
files={}
for label,base in (('result',root),('source',source),('inputs',inputs)):
    for p in sorted(base.iterdir()):
        if p.is_file():files[label+'/'+p.name]=p
for name in ('lr_recurrence_20260928.run.log','lr_recurrence_20260928.LAUNCH.json','lr_recurrence_20260928_test_before.log','lr_recurrence_20260928_test_after.log'):
    files['logs/'+name]=Path('/dev/shm')/name
manifest={k:{'sha256':sha(p),'bytes':p.stat().st_size} for k,p in files.items()}
out=Path('/dev/shm/lr_recurrence_20260928.zip')
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
    for name,p in files.items():z.write(p,name)
    z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
receipt={'utc':time.strftime('%FT%TZ',time.gmtime()),'path':str(out),'sha256':sha(out),'bytes':out.stat().st_size,'members':len(files),'manifest':manifest,'parent_inputs':'C4/C5 and production archives remain pinned in RESULT inputs; not duplicated here'}
Path('/dev/shm/lr_recurrence_20260928.ARCHIVE.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='manifest'}))
