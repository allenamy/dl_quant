"""Round-2 book-layer reducer. g = net_ex/gross_total, bps per anchor per unit gross (judge_v4 statistic).
Windows: full = 2022-01-31..2026-08-31 (n=10039); full22 = ..2026-08-10 20Z (n=9918); frozen = 2025-03-01..
2026-08-10 (n=3168); oos = 2026-08-11..2026-08-31 (n=121). SE(annualised Sharpe)=sqrt(2190/N)."""
import numpy as np, sys, glob, os, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0=L.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz")
ts0,g0=L.gser(A0)
pats=sys.argv[1:] or [R+"/out/SL2_*.npz"]
rows=[]
for pat in pats:
  for p in sorted(glob.glob(pat)):
    R_=L.load(p); ts,g=L.gser(R_)
    assert np.array_equal(ts,ts0), p
    P=L.parts(R_)
    mf=L.msk(ts,*L.W["full22"]); mz=L.msk(ts,*L.W["frozen"]); m24=L.msk(ts,*L.W["y2024on"]); mo=L.msk(ts,*L.W["oos"])
    ok=np.isfinite(g)&np.isfinite(g0)&mf
    net=float(np.nanmean(P["net"][mf])); car=float(np.nanmean(P["carry"][mf]))
    yb=L.years(ts,g)
    rows.append(dict(name=os.path.basename(p)[:-4],
      g_full=float(np.nanmean(g[mf])), sr_full=L.sharpe(g[mf]),
      g_froz=float(np.nanmean(g[mz])), sr_froz=L.sharpe(g[mz]),
      g_24on=float(np.nanmean(g[m24])), sr_24on=L.sharpe(g[m24]),
      g_oos=float(np.nanmean(g[mo])),
      corr_A0=float(np.corrcoef(g[ok],g0[ok])[0,1]),
      carry_frac=car/net if net!=0 else float("nan"),
      pnl=float(np.nanmean(P["pnl"][mf])), carry=car, cost=float(np.nanmean(P["cost"][mf])),
      turn=float(np.nanmean(P["turn"][mf])),
      years={str(k):round(v,1) for k,v in yb.items()},
      ypos=sum(1 for k,v in yb.items() if v>0), ny=len(yb)))
rows.sort(key=lambda r:-r["sr_full"])
print("%-30s %8s %8s %8s %8s %8s %8s %7s %8s %6s"%("arm","g_full","SR_full","g_froz","SR_froz","g_24on","g_oos","corrA0","carry/net","yr+"))
for r in rows:
    print("%-30s %+8.3f %+8.3f %+8.3f %+8.3f %+8.3f %+8.2f %+7.3f %+8.2f %d/%d"%(
      r["name"],r["g_full"],r["sr_full"],r["g_froz"],r["sr_froz"],r["g_24on"],r["g_oos"],
      r["corr_A0"],r["carry_frac"],r["ypos"],r["ny"]))
json.dump(rows,open(R+"/judge2_out.json","w"),indent=1)
