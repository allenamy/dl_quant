"""Diagnose the implausible walk-forward SR. Hypotheses:
 H1 the 36 arms are 18 sign-mirrored PAIRS; MV optimisation over near-collinear (+x,-x) pairs
    manufactures leverage from the device's own long/short asymmetry, not from market alpha.
 H2 the fitted weights imply absurd gross leverage, so the 'SR' is not implementable."""
import numpy as np, sys, glob, os, datetime as dt
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=L.load(A0p); ts,g0=L.gser(A); G={"A0":g0}
for p in sorted(glob.glob(R+"/out/SL2_ORTH_*.npz")):
    Rr=L.load(p); t,g=L.gser(Rr); G[os.path.basename(p)[9:-4]]=g
m=L.msk(ts,*L.W["full22"]); tsm=ts[m]
names=list(G); M=np.array([G[k][m] for k in names]); ok=np.isfinite(M).all(axis=0)
M=M[:,ok]; tsm=tsm[ok]; ANN=np.sqrt(2190.0); iA0=names.index("A0")
C=np.corrcoef(M)
print("=== H1: correlation between the __p and __m arm of the SAME feature ===")
fams=sorted({n[:-3] for n in names if n!="A0"})
for fm in fams:
    i=names.index(fm+"__p"); j=names.index(fm+"__m")
    print("  %-11s corr(p,m) = %+0.3f"%(fm,C[i,j]))
f=lambda s:int(dt.datetime.strptime(s,"%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
def fit(Mtr,ridge):
    mu=Mtr.mean(axis=1); S=np.cov(Mtr); S=S+np.eye(len(mu))*ridge*np.trace(S)/len(mu)
    return np.linalg.solve(S,mu)
print("\n=== H2: implied gross leverage of the fitted weights (A0 weight normalised to 1) ===")
tr=tsm<f("2025-01-01")
for ridge in (1e-6,1e-2,1e-1):
    w=fit(M[:,tr],ridge)
    print("  ridge=%-7g sum|w| = %10.1f   w_A0 = %8.3f   sum|w|/|w_A0| = %9.1f"%(
        ridge,np.abs(w).sum(),w[iA0],np.abs(w).sum()/max(abs(w[iA0]),1e-12)))
CUTS=["2023-07-01","2024-01-01","2024-07-01","2025-01-01","2025-07-01","2026-01-01","2026-08-11"]
def wfrun(idx,label,ridge=1e-2,cap=None):
    out=[];
    for a,b in zip(CUTS[:-1],CUTS[1:]):
        tr=tsm<f(a); te=(tsm>=f(a))&(tsm<f(b))
        if tr.sum()<1500 or te.sum()<200: continue
        w=fit(M[np.ix_(idx)][:,tr],ridge)
        if cap: w=w/np.abs(w).sum()*cap
        r=w@M[np.ix_(idx)][:,te]
        out.append(r/max(r.std(ddof=1),1e-12))
    rr=np.concatenate(out)
    print("  %-52s pooled OOS SR %+6.3f"%(label,rr.mean()/rr.std(ddof=1)*ANN))
print("\n=== restrict the asset set (ridge=1e-2) ===")
wfrun(list(range(len(names))),"all 37 (A0 + 18 features x 2 signs)")
pidx=[iA0]+[names.index(fm+"__p") for fm in fams]
wfrun(pidx,"A0 + the 18 __p arms only (no sign mirror)")
midx=[iA0]+[names.index(fm+"__m") for fm in fams]
wfrun(midx,"A0 + the 18 __m arms only (no sign mirror)")
cand=[iA0,names.index("AMIRESID__p"),names.index("ASZSTAB__p"),names.index("RESSKEW__m")]
wfrun(cand,"A0 + the 3 reported candidates only")
wfrun([iA0],"A0 alone")
