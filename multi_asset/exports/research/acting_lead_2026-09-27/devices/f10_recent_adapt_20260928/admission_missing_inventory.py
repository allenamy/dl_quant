"""Enumerate every unknown possible-held label in the latest frozen training pool.
Inventory does not alter labels, admission, models, or evaluation.
"""
from pathlib import Path
import sys,json,hashlib,datetime as dt
import numpy as np
S=Path('/dev/shm/f10_recent_adapt_20260928_attempt2_sources');sys.path.insert(0,str(S))
from adapt_contract import causal_windows,align_indices

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def run(out):
 root=Path('/dev/shm/f10_recent_adapt_20260928_attempt2/models/R180_s42');r=json.loads((root/'202609/FOLD_RECEIPT.json').read_text());pins={**r['inputs'],**r['sources']}
 for p,h in pins.items():assert sha(p)==h,p
 ns=Path('/dev/shm/news2_2026-09-23');F=np.load(ns/'work/NEWS_FEATURES.npz');T=np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',allow_pickle=True);L=np.load(ns/'work/legs.npz')
 a=F['anchors'];sy=F['symbols'];off=F['off'];mm=F['m'];members=[mm[off[i]:off[i+1]].astype(int) for i in range(len(a))];ix=np.asarray(align_indices(T['E_ts'].tolist(),a.tolist()));y=np.full((len(a),len(sy)),np.nan,np.float32);ok=ix>=0;y[ok]=T['y4s'][ix[ok]]
 wins=causal_windows(a.tolist(),L['ready'].tolist(),np.diff(off).tolist(),r['admission']['cutoff']);missing={};bad_wins=0
 for wi,w in enumerate(wins):
  possible=np.zeros(len(sy),bool);badwin=False
  for i in w:
   possible[members[i]]=True;bad=np.flatnonzero(possible&~np.isfinite(y[i]));badwin|=bool(len(bad))
   for c in bad:
    key=(str(sy[c]),int(a[i]));missing.setdefault(key,[]).append(wi)
  bad_wins+=badwin
 assert bad_wins==r['admission']['raw_windows']-r['admission']['accepted_windows']
 jobs=set()
 for s,t in missing:
  # Close at E belongs to preceding bar; E+4h belongs to bar at E+4h-5m.
  for ts in (t-300,t+14400-300):jobs.add((s,dt.datetime.fromtimestamp(ts,dt.timezone.utc).date().isoformat()))
 rec={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'DATA_REQUEST_INVENTORY_NOT_LABEL_REPAIR','source_sha256':sha(__file__),'fold_receipt_sha256':sha(root/'202609/FOLD_RECEIPT.json'),'raw_windows':len(wins),'bad_windows':bad_wins,'missing_labels':[{'symbol':s,'anchor':t,'windows':v} for (s,t),v in sorted(missing.items())],'archive_requests':[{'symbol':s,'day':d} for s,d in sorted(jobs)],'input_pins':pins}
 with open(out,'x') as f:json.dump(rec,f,indent=2,allow_nan=False)
 print({'bad_windows':bad_wins,'missing_labels':len(missing),'symbols':sorted({s for s,t in missing}),'symbol_days':len(jobs)})
if __name__=='__main__':run(sys.argv[1])
