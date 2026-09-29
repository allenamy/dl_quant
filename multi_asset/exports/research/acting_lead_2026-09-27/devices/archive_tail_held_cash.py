"""Preserve first run, schema correction, inputs, checks, and reproducible outputs."""
import hashlib,json,zipfile
from pathlib import Path
import numpy as np
old=Path('/dev/shm/tail_held_cash_20260929');new=Path(str(old)+'_seedfix')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=json.loads((new/'RESULT.json').read_text());b=json.loads((old/'RESULT.json').read_text())
assert a['tables']==b['tables']
p=np.load('/dev/shm/tail_risk_20260928/PREDICTIONS.npz',allow_pickle=False);off=p['off'];ii=np.searchsorted(p['anchors'],a['anchors'])
idx=np.concatenate([np.arange(off[i],off[i+1]) for i in ii])
comparison=dict(tables_identical=True,eligible_true_per_seed=p['eligible'][idx].sum(0).tolist(),selected_rows=len(idx),old_result_sha=sha(old/'RESULT.json'),new_result_sha=sha(new/'RESULT.json'),correction='eligible axis is seed, not tail; both selected seeds happen to be fully eligible; first run retained')
(new/'SCHEMA_CORRECTION.json').write_text(json.dumps(comparison,indent=2)+'\n')
for p,s in b['sources'].items():assert sha(p)==s,('initial_source_restoration',p)
for p,s in a['sources'].items():assert sha(p)==s,('corrected_source',p)
zpath=Path('/dev/shm/tail_held_cash_20260929_package.zip');members={}
dirs=[('initial_outputs',old),('outputs',new),('initial_sources',Path(str(old)+'_sources')),('sources',Path(str(new)+'_sources'))]
with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for prefix,d in dirs:
  for p in sorted(d.iterdir()):
   if p.is_file() and p.suffix in ('.npz','.json','.py','.txt','.log'):
    n=prefix+'/'+p.name;z.write(p,n);members[n]=dict(bytes=p.stat().st_size,sha256=sha(p))
 for p in (Path(str(old)+'.run.log'),Path(str(new)+'.run.log')):
  n='logs/'+p.name;z.write(p,n);members[n]=dict(bytes=p.stat().st_size,sha256=sha(p))
manifest=dict(path=str(zpath),sha256=sha(zpath),bytes=zpath.stat().st_size,members=members,limits=['Large parent inputs remain at pinned paths; no sources deleted','First schema interpretation retained as superseded; economic tables unchanged'])
Path('/dev/shm/tail_held_cash_20260929_package.ARCHIVE.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='members'}));print('members',len(members))
