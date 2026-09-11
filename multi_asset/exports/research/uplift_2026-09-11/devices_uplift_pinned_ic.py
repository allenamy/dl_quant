import numpy as np, time, json
from scipy.stats import spearmanr
P=np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy") if __import__('os').path.exists("/workspace/shadow_bundle_v3/slow_pred_pinned.npy") else np.load("/workspace/shadow_bundle/slow_pred_pinned.npy")
M=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True)
E_ts=M["E_ts"].astype(np.int64); members=M["members"]; y4=M["y4"]
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    r=spearmanr(a[ok],b[ok]); return r.correlation if hasattr(r,"correlation") else r[0]
mon={}
for i in range(len(E_ts)):
    m=members[i]; okm=np.isfinite(y4[i,m])
    if okm.sum()<50: continue
    v=sp(P[i,m[okm]], y4[i,m][okm])
    if v==v: mon.setdefault(time.strftime("%Y-%m",time.gmtime(int(E_ts[i]))),[]).append(v)
out={k:(round(float(np.mean(v)),4),len(v)) for k,v in sorted(mon.items())}
print(json.dumps({k:v for k,v in out.items() if k>="2025-01"},indent=0))
yr={}
for k,(m,n) in out.items(): yr.setdefault(k[:4],[]).append((m,n))
print({y:round(float(np.average([a for a,_ in v],weights=[b for _,b in v])),4) for y,v in yr.items()})
