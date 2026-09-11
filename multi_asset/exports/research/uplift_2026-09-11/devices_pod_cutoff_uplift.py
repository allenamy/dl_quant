import numpy as np, time, json
DLW="/workspace/dlw_ext"
TG=np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4s=TG["y4s"]; nA,NW=y4s.shape
FE=np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
pa=FE["pair_a"].astype(np.int64)
ST=np.searchsorted(pa, np.arange(nA+1))
tr_idx=np.array([i for i in range(nA) if ST[i+1]-ST[i]>=50])
cut=int(len(tr_idx)*0.85); tr1,va1=tr_idx[:cut],tr_idx[cut:]
f=lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(t)))
out=dict(nA=nA, NW=NW, n_tr_idx=len(tr_idx), cut=cut,
  E_ts_first=f(E_ts[0]), E_ts_last=f(E_ts[-1]),
  tr_idx_first=f(E_ts[tr_idx[0]]), tr_idx_last=f(E_ts[tr_idx[-1]]),
  GRADIENT_last=f(E_ts[tr1[-1]]), VAL_first=f(E_ts[va1[0]]), VAL_last=f(E_ts[va1[-1]]),
  n_grad_anchors=len(tr1), n_val_anchors=len(va1))
# training-window starts actually used: starts = range(tr1[0]+BURN, tr1[-1]-WIN, STRIDE)
BURN,WIN,STRIDE=24,96,48
starts=list(range(int(tr1[0])+BURN,int(tr1[-1])-WIN,STRIDE))
out["n_train_spans"]=len(starts)
out["last_span_end_anchor"]=f(E_ts[min(starts[-1]+WIN, nA-1)])
# year histogram of gradient anchors
yrs=np.array([time.gmtime(int(t)).tm_year for t in E_ts])
import collections
out["grad_year_hist"]={int(k):int(v) for k,v in sorted(collections.Counter(yrs[tr1]).items())}
out["val_year_hist"]={int(k):int(v) for k,v in sorted(collections.Counter(yrs[va1]).items())}
print(json.dumps(out,indent=1))
