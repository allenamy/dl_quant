import numpy as np, sys, glob, os, datetime as dt
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=L.load(A0p); ts,g0=L.gser(A)
def get(p):
    Rr=L.load(p); t,g=L.gser(Rr); assert np.array_equal(t,ts); return g
ANN=np.sqrt(2190.0)
CAND={"AMIRESID__p":get(R+"/out/SL2_ORTH_AMIRESID__p.npz"),
      "ASZSTAB__p":get(R+"/out/SL2_ORTH_ASZSTAB__p.npz"),
      "RESSKEW__m":get(R+"/out/SL2_ORTH_RESSKEW__m.npz"),
      "R1_ORTH_amihud":get("/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_amihud_24h__p.npz")}
print("=== FIXED-WEIGHT (no fitting) combinations, full cycle 2022-01-31..2026-08-10 n=9918 ===")
m=L.msk(ts,*L.W["full22"])
def sr(x): 
    x=x[np.isfinite(x)]; return x.mean()/x.std(ddof=1)*ANN
def report(lbl,g):
    yb=L.years(ts,g); yp=sum(1 for k,v in yb.items() if v>0)
    print("  %-46s g %+0.4f  SR %+0.3f  yr+ %d/%d  %s"%(lbl,np.nanmean(g[m]),sr(g[m]),yp,len(yb),
        {str(k):round(v,1) for k,v in yb.items()}))
report("A0 alone",g0)
for k,v in CAND.items(): report(k+" alone",v)
for lbl,mix in (("A0 + AMIRESID (50/50 of unit-vol)",["AMIRESID__p"]),
                ("A0 + RESSKEW (50/50 of unit-vol)",["RESSKEW__m"]),
                ("A0 + AMIRESID + RESSKEW (equal unit-vol)",["AMIRESID__p","RESSKEW__m"]),
                ("A0 + all 3 candidates (equal unit-vol)",["AMIRESID__p","ASZSTAB__p","RESSKEW__m"])):
    xs=[g0]+[CAND[k] for k in mix]
    xs=[x/np.nanstd(x[m]) for x in xs]
    report(lbl,sum(xs)/len(xs))
print("\n=== per-year g (bps/anchor/gross, mean not sum) for the candidates ===")
import datetime as _dt
yr=np.array([_dt.datetime.fromtimestamp(t,_dt.timezone.utc).year for t in ts])
print("  %-18s"%"arm"+"".join("%9d"%y for y in sorted(set(yr[m]))))
for k,v in [("A0",g0)]+list(CAND.items()):
    print("  %-18s"%k+"".join("%+9.3f"%np.nanmean(v[m&(yr==y)]) for y in sorted(set(yr[m]))))
print("\n=== out-of-fit stress window 2026-08-11..2026-08-31 (n=121) ===")
mo=L.msk(ts,*L.W["oos"])
print("  n =",int(mo.sum()))
for k,v in [("A0",g0)]+list(CAND.items()):
    print("  %-18s g %+0.3f  SR %+0.3f"%(k,np.nanmean(v[mo]),sr(v[mo])))
