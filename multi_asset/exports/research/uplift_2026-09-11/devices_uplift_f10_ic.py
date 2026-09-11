"""Per-anchor score-layer IC of the DEPLOYED F10 (f10_live_s42_np.npz, sha 351ae26b…).
Serving math copied verbatim from pod_f10_np_export.py (clip -5..5, gelu=erf)."""
import numpy as np, time, json
from scipy.stats import spearmanr
from scipy.special import erf
W=np.load("/workspace/f8_ext/models/f10_live_s42_np.npz")
mu=W["mu"].astype(np.float64); sdv=W["sd_"].astype(np.float64)
TG=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4s=TG["y4s"]; nA=y4s.shape[0]
FE=np.load("/workspace/dlw_ext/data/dlw_fea82.npz",allow_pickle=True)
pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64)
F9=np.load("/workspace/f8_ext/data/f8_fea89.npz",allow_pickle=True)
XL=np.concatenate([FE["X"],F9["X"]],1).astype(np.float32); del FE,F9
ST=np.searchsorted(pa,np.arange(nA+1))
def gelu(x): return 0.5*x*(1+erf(x/np.sqrt(2)))
S=np.empty(XL.shape[0])
B=200000
for a in range(0,XL.shape[0],B):
    x=np.nan_to_num(np.clip((XL[a:a+B].astype(np.float64)-mu)/sdv,-5,5))
    h=gelu(x@W["w0"].T.astype(np.float64)+W["b0"].astype(np.float64))
    h=gelu(h@W["w1"].T.astype(np.float64)+W["b1"].astype(np.float64))
    S[a:a+B]=(h@W["w2"].T.astype(np.float64)+W["b2"].astype(np.float64)).squeeze(-1)
mon={}
for i in range(nA):
    a,b=int(ST[i]),int(ST[i+1])
    if b-a<50: continue
    y=y4s[i,ps[a:b]]
    ok=np.isfinite(y)
    if ok.sum()<30: continue
    r=spearmanr(S[a:b][ok],y[ok]).correlation
    if r==r: mon.setdefault(time.strftime("%Y-%m",time.gmtime(int(E_ts[i]))),[]).append(r)
out={k:[round(float(np.mean(v)),4),len(v)] for k,v in sorted(mon.items())}
json.dump(out,open("/workspace/codex_research/uplift_f10_monthly_ic.json","w"),indent=0)
print(json.dumps({k:v for k,v in out.items() if k>="2025-06"},indent=0))
import numpy as _n
yr={}
for k,(m,n) in out.items(): yr.setdefault(k[:4],[]).append((m,n))
print({y:round(float(_n.average([a for a,_ in v],weights=[b for _,b in v])),4) for y,v in yr.items()})
