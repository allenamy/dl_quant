"""Inventory the already-certified label repair's affected folds, without training."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import sys,json,hashlib,time,datetime
import numpy as np
from label_contract import validate_overlay,needs_refit

NS=Path('/dev/shm/news2_2026-09-23');OLD=Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEW=Path('/dev/shm/f10_y4s_repair_20260928/Y4S_OVERLAY.npz')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def main(out):
 start=time.monotonic();H=Path(__file__).parent
 sys.path.insert(0,str(H));from adapt_contract import causal_windows,align_indices
 sys.path.insert(0,str(NS/'devices'));from f10_observability import span_admissible
 from news2_train_f10 import fold_specs
 pins={str(OLD):'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',str(NEW):'ea6e4b73876035ab6d5a94ca5049746a6ee1e18542ab6d180896e931a49ed81a',str(NS/'work/NEWS_FEATURES.npz'):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(NS/'work/legs.npz'):'9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',str(NS/'devices/f10_observability.py'):'c6399d7ae49482503209ce21916e38f1ad36fb7702c980eb5d0b67c5b9349dd1',str(NS/'devices/news2_train_f10.py'):'66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'}
 for p,h in pins.items():assert sha(p)==h,p
 with np.load(OLD,allow_pickle=True) as z:o={k:z[k] for k in ('E_ts','symbols','y4s')}
 with np.load(NEW,allow_pickle=True) as z:n={k:z[k] for k in ('E_ts','symbols','y4s')}
 assert np.array_equal(o['E_ts'],n['E_ts']) and np.array_equal(o['symbols'],n['symbols'])
 assert validate_overlay(o['y4s'],n['y4s'])==852
 with np.load(NS/'work/NEWS_FEATURES.npz') as z:F={k:z[k] for k in ('anchors','symbols','off','m')}
 with np.load(NS/'work/legs.npz') as z:ready=z['ready'];assert np.array_equal(z['E_ts'],F['anchors'])
 a=F['anchors'];sy=F['symbols'];assert np.array_equal(sy,o['symbols'])
 ix=np.array(align_indices(o['E_ts'].tolist(),a.tolist()));good=ix>=0;ys=[]
 for obj in (o,n):
  y=np.full((len(a),len(sy)),np.nan,np.float32);y[good]=obj['y4s'][ix[good]];ys.append(y)
 off=F['off'];m=F['m'];members=[m[off[i]:off[i+1]].astype(int) for i in range(len(a))];counts=np.diff(off)
 rows=[]
 for tag,begin,end in fold_specs(a):
  cutoff=int(a[np.flatnonzero((a>=begin)&(a<end))[0]])-60*14400;raw=causal_windows(a.tolist(),ready.tolist(),counts.tolist(),cutoff)
  accepted=[]
  for y in ys:accepted.append([s for s in raw if span_admissible(members,y,s,ready)[0]])
  orig=json.loads(Path(f'/dev/shm/f10_recent_adapt_20260928_attempt2/models/U_s42/{tag}/FOLD_RECEIPT.json').read_text())
  assert len(accepted[0])==orig['admission']['accepted_windows'] and cutoff==orig['admission']['cutoff']
  oldset={tuple(s) for s in accepted[0]};newset={tuple(s) for s in accepted[1]};assert oldset<=newset
  gained=[s for s in accepted[1] if tuple(s) not in oldset]
  rows.append({'fold':tag,'refit':needs_refit(*accepted),'cutoff':cutoff,'old':len(oldset),'new':len(newset),
    'gained_window_first_anchor':[int(a[s[0]]) for s in gained],
    'gained_window_label_end':[int(a[s[-1]]+14400) for s in gained],
    'old_latest_label_end':max(int(a[s[-1]]+14400) for s in accepted[0]),'new_latest_label_end':max(int(a[s[-1]]+14400) for s in accepted[1])})
 for p,h in pins.items():assert sha(p)==h,p
 result={'status':'ADMISSION_ONLY_NO_TRAINING_OR_PNL','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':pins,
  'source_sha256':sha(__file__),'helper_sha256':sha(H/'label_contract.py'),'rows':rows,'affected':[r['fold'] for r in rows if r['refit']],
  'seconds':time.monotonic()-start,'python':sys.executable,'numpy':np.__version__}
 with open(out,'x') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps({'affected':result['affected'],'seconds':result['seconds'],'rows':rows}))
if __name__=='__main__':main(sys.argv[1])
