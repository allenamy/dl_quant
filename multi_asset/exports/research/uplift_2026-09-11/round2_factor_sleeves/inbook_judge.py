"""In-book parity gate + paired blend delta with UTC-day block bootstrap (judge_v4 statistic)."""
import numpy as np, sys, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=np.load(A0p,allow_pickle=True); recA=A["d30_n2_c42_rec"]
Bz=np.load(R+"/out/IB2_PARITY.npz",allow_pickle=True); recB=Bz["rec"]
print("IB2_PARITY vs archived A0_dyn_s42 rec: BITWISE =", recA.tobytes()==recB.tobytes(),
      " maxabs %.3e"%np.nanmax(np.abs(recA-recB)))
RA=L.load(A0p); ts,gA=L.gser(RA)
def get(p):
    Rr=L.load(p); t,g=L.gser(Rr); assert np.array_equal(t,ts); return g
base=get(R+"/out/IB2_PARITY.npz")
for k,tag in ((1,"IB2_AMIRESID50"),(2,"IB2_AMIRESID25")):
    try: g=get(R+"/out/%s.npz"%tag)
    except Exception as e: print(tag,"missing",e); continue
    for wn in ("full22","frozen"):
        m=L.msk(ts,*L.W[wn]); d=(g-base)[m]
        lo,hi=L.boot(d,ts[m],k)
        print("%-16s %-7s paired D = %+0.4f  CI95 [%+0.4f, %+0.4f]  n=%d"%(tag,wn,np.nanmean(d),lo,hi,m.sum()))
    m=L.msk(ts,*L.W["full22"])
    print("%-16s level g_full %+0.4f  SR %+0.3f   (A0 %+0.4f / %+0.3f)"%(
       tag,np.nanmean(g[m]),L.sharpe(g[m]),np.nanmean(base[m]),L.sharpe(base[m])))
# standalone bootstrap for the sleeve itself (vs zero, not paired)
for tag,k in (("SL2_ORTH_AMIRESID__p",11),("SL2_ORTH_ASZSTAB__p",12),("SL2_ORTH_RESSKEW__m",13)):
    g=get(R+"/out/%s.npz"%tag)
    for wn in ("full22","frozen"):
        m=L.msk(ts,*L.W[wn]); lo,hi=L.boot(g[m],ts[m],k)
        print("%-24s %-7s level %+0.4f CI95 [%+0.4f, %+0.4f]"%(tag,wn,np.nanmean(g[m]),lo,hi))
