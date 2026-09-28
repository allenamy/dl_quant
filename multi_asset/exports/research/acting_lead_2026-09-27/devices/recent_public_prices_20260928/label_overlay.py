"""Isolated y4s overlay: retain every old finite value; restore proven NaNs only.

The executable revalidates official archives through label_proofs before use.
It never changes the source targets, features, or any in-flight model inputs.
"""
from pathlib import Path
import json,sys,hashlib,math
import numpy as np

def patch_labels(anchors,symbols,y,rows):
 a=np.asarray(anchors);s=np.asarray(symbols);y=np.asarray(y)
 if a.ndim!=1 or s.ndim!=1 or y.shape!=(len(a),len(s)) or y.dtype.kind!='f':raise ValueError('shape/dtype')
 if not np.isfinite(a).all() or not np.equal(a,np.floor(a)).all() or not np.equal(a%14400,0).all() or not np.all(np.diff(a)>0):raise ValueError('time axis')
 if len(set(map(str,s)))!=len(s):raise ValueError('symbol axis')
 ai={int(t):i for i,t in enumerate(a)};si={str(v):j for j,v in enumerate(s)};out=y.copy();seen=set();changed=[]
 for r in rows:
  t=r['anchor'];name=r['symbol']
  if type(t)!=int or t not in ai or name not in si:raise ValueError('label identity')
  key=(t,name)
  if key in seen:raise ValueError('duplicate label')
  seen.add(key);i,j=ai[t],si[name]
  if not np.isnan(y[i,j]):raise ValueError('source is not missing NaN')
  n=r['n_closes'];missing=r['missing_ts'];v=r['y4s']
  if r['status']=='UNAVAILABLE':
   if type(n)!=int or not 0<=n<49 or len(missing)!=49-n or v is not None:raise ValueError('unknown proof')
   continue
  if r['status']!='OBSERVED' or n!=49 or missing:raise ValueError('incomplete observed proof')
  if type(v) not in (int,float) or not math.isfinite(v) or v<=-1 or abs(v)>float(np.finfo(y.dtype).max):raise ValueError('invalid return')
  out[i,j]=v;changed.append((i,j))
 mask=np.zeros(y.shape,bool)
 for i,j in changed:mask[i,j]=True
 if out[~mask].tobytes()!=y[~mask].tobytes():raise ValueError('unapproved change')
 return out,changed

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(target,inventory,root,output):
 import label_proofs
 output=Path(output)
 if output.exists():raise ValueError('output must be new')
 inv=json.loads(Path(inventory).read_text());expected=inv['input_pins'].get(str(target))
 if not expected or sha(target)!=expected:raise ValueError('original target identity')
 output.mkdir(parents=True)
 label_proofs.run(inventory,Path(root),output/'REVALIDATED_PROOFS.json')
 proof=json.loads((output/'REVALIDATED_PROOFS.json').read_text())
 with np.load(target,allow_pickle=True) as t:
  a=t['E_ts'];s=t['symbols'];old=t['y4s'];new,changed=patch_labels(a,s,old,proof['rows'])
 # Only a y4s-specific overlay is exported, avoiding inconsistent other targets.
 with open(output/'Y4S_OVERLAY.npz','xb') as f:
  np.savez_compressed(f,E_ts=a,symbols=s,y4s=new,changed_rc=np.asarray(changed,dtype=np.int64).reshape(-1,2))
 with np.load(output/'Y4S_OVERLAY.npz',allow_pickle=True) as t:
  if t['y4s'].tobytes()!=new.tobytes() or not np.array_equal(t['E_ts'],a) or not np.array_equal(t['symbols'],s):raise ValueError('roundtrip')
 if sha(target)!=expected:raise ValueError('source changed during run')
 receipt={'status':'ISOLATED_LABEL_REPAIR_NOT_USED_FOR_TRAINING','original_targets':str(target),'original_sha256':expected,'overlay_sha256':sha(output/'Y4S_OVERLAY.npz'),'proofs_sha256':sha(output/'REVALIDATED_PROOFS.json'),'source_sha256':sha(__file__),'changed_nan_to_observed':len(changed),'old_finite_unchanged_bitwise':True,'axes_unchanged':True,'remaining_inventory_unknown':proof['n_still_unknown'],'limitations':['Only fixed latest-pool missing-label population repaired','No feature repair, retraining, evaluation or production change','Historical official archives are not a millisecond point-in-time availability certificate']}
 (output/'RECEIPT.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt))
if __name__=='__main__':run(*sys.argv[1:])
