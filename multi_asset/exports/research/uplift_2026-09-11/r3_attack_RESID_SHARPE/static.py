"""Decompose RESID_SHARPE's score into a STATIC per-symbol tilt + a time-varying residual and run each
through the unmodified device. STATIC_EXP uses only information available before the fold (per-symbol mean
of the score over the PRIOR calendar year, applied to the whole next year) so it is causal."""
import numpy as np, os, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r3_attack_b9646")
from null import run, sym, pts, OFF, W, R2
import calendar
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
yrs=TG["yrs"].astype(int)[OFF:OFF+len(pts)]
P=np.load(R2+"/preds/RESID_SHARPE_s42.npy")[OFF:OFF+len(pts)]
# per-anchor z so the static mean is a pure cross-sectional tilt
Z=np.full_like(P,np.nan)
for i in range(P.shape[0]):
    v=P[i]; m=np.isfinite(v)
    if m.sum()>=10: Z[i,m]=(v[m]-v[m].mean())/(v[m].std()+1e-12)
S=np.full_like(P,np.nan); Rr=np.full_like(P,np.nan)
for y in (2023,2024,2025,2026):
    tr=(yrs==y-1); te=(yrs==y)
    if tr.sum()<50 or te.sum()<10: continue
    mu=np.nanmean(np.where(np.isfinite(Z[tr]),Z[tr],np.nan),axis=0)   # prior-year per-symbol mean
    S[te]=np.where(np.isfinite(Z[te]),mu[None,:],np.nan)
    Rr[te]=Z[te]-S[te]
fr=np.isfinite(Z)&np.isfinite(S)
print("share of score variance explained by the prior-year static tilt: %.4f"%(
    1-np.nanvar(Z[fr]-S[fr])/np.nanvar(Z[fr])))
jobs=[]
for nm,M in (("STATIC",S),("DYNRESID",Rr)):
    f=W+"/sig/%s.npz"%nm; np.savez(f,symbols=sym,ts=pts,mat=np.asarray(M,np.float32))
    jobs.append(("NULL_"+nm,f))
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as ex:
    for r in ex.map(lambda a: run(*a), jobs): print(r,flush=True)
print("STATIC_DONE")
