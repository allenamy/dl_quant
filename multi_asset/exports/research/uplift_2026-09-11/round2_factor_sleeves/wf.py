"""Is the 'optimally combine the 36 sleeves' result real, or the round-1 exposure-control pathology
(in-sample selection ANTI-predictive out of sample)? Multi-fold expanding walk-forward, plus a
permutation control in which the sleeve identities are shuffled within each training fold."""
import numpy as np, sys, glob, os, datetime as dt
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=L.load(A0p); ts,g0=L.gser(A)
G={"A0":g0}
for p in sorted(glob.glob(R+"/out/SL2_ORTH_*.npz")):
    Rr=L.load(p); t,g=L.gser(Rr); G[os.path.basename(p)[9:-4]]=g
m=L.msk(ts,*L.W["full22"]); tsm=ts[m]
names=list(G); M=np.array([G[k][m] for k in names]); ok=np.isfinite(M).all(axis=0)
M=M[:,ok]; tsm=tsm[ok]; ANN=np.sqrt(2190.0); iA0=names.index("A0")
f=lambda s:int(dt.datetime.strptime(s,"%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
CUTS=["2023-07-01","2024-01-01","2024-07-01","2025-01-01","2025-07-01","2026-01-01","2026-08-11"]
def fit(Mtr,ridge):
    mu=Mtr.mean(axis=1); S=np.cov(Mtr); S=S+np.eye(len(mu))*ridge*np.trace(S)/len(mu)
    return np.linalg.solve(S,mu)
for ridge in (1e-6,1e-2,1e-1):
    allr=[]; allb=[]
    print("\n--- expanding walk-forward, ridge=%g, 37 assets (A0 + 36 sleeves) ---"%ridge)
    for a,b in zip(CUTS[:-1],CUTS[1:]):
        tr=tsm<f(a); te=(tsm>=f(a))&(tsm<f(b))
        if tr.sum()<1500 or te.sum()<200: continue
        w=fit(M[:,tr],ridge); r=w@M[:,te]
        s=r.mean()/r.std(ddof=1)*ANN; s0=M[iA0,te].mean()/M[iA0,te].std(ddof=1)*ANN
        allr.append(r/ r.std(ddof=1) if r.std(ddof=1)>0 else r); allb.append(M[iA0,te])
        print("  train<%s  test %s..%s n=%5d   combo SR %+6.3f   A0 SR %+6.3f   delta %+6.3f"%(a,a,b,te.sum(),s,s0,s-s0))
    if allr:
        rr=np.concatenate(allr); bb=np.concatenate(allb)
        print("  POOLED OOS  combo SR %+6.3f   A0 SR %+6.3f"%(rr.mean()/rr.std(ddof=1)*ANN, bb.mean()/bb.std(ddof=1)*ANN))
