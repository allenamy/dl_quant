import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time
R=json.load(open("/workspace/uplift_2026-09-11/trackC/eval_v4.json"))
ds=np.array([r["d_sharpe"] for r in R]); dd=np.array([r["dd_red"] for r in R])
dm=np.array([100*r["mean"]/r["base_mean"] for r in R]); bp=np.array([r["boot_p"] for r in R])
print("== FAMILY-LEVEL (all K=300 variants of the de-risk-when-quiet gross ladder) ==")
print("dSharpe    : min %+0.3f  p25 %+0.3f  med %+0.3f  p75 %+0.3f  max %+0.3f   frac>0 %.2f"%(ds.min(),np.percentile(ds,25),np.median(ds),np.percentile(ds,75),ds.max(),(ds>0).mean()))
print("maxDD red %%: min %+0.1f  p25 %+0.1f  med %+0.1f  p75 %+0.1f  max %+0.1f   frac>20%% %.2f"%(100*dd.min(),100*np.percentile(dd,25),100*np.median(dd),100*np.percentile(dd,75),100*dd.max(),(dd>0.20).mean()))
print("mean kept %%: min %5.1f  p25 %5.1f  med %5.1f  p75 %5.1f  max %5.1f   frac>=85%% %.2f"%(dm.min(),np.percentile(dm,25),np.median(dm),np.percentile(dm,75),dm.max(),(dm>=85).mean()))
print("boot_p<=0.10 count %d / %d  (expected by chance at alpha=0.10: %.0f)"%((bp<=0.10).sum(),len(bp),0.10*len(bp)))
print()
for s in ("bookvol","disp","sigfund","fundema","turn"):
    m=[r for r in R if r["src"]==s]; a=np.array([r["d_sharpe"] for r in m]); b=np.array([r["dd_red"] for r in m])
    print("  %-8s n=%3d  dSharpe med %+0.3f [%+0.3f,%+0.3f]   ddRed med %+0.1f%%   frac dS>0 %.2f"%(s,len(m),np.median(a),a.min(),a.max(),100*np.median(b),(a>0).mean()))
print()
print("== G4 CHECK (no year worse than baseline Sharpe - 0.50) for the 8 best by dSharpe ==")
R2=sorted(R,key=lambda r:-r["d_sharpe"])[:8]
for r in R2:
    bad=[(y,round(r["yr"][y][0]-r["base_yr"][y][0],2)) for y in r["yr"] if y in r["base_yr"] and r["yr"][y][0]-r["base_yr"][y][0] < -0.50]
    print("  %-9s ref%-3s th%.2f L%-3d  dSharpe %+0.3f  G4 %s  %s"%(r["src"],r["ref"],r["th"],r["L"],r["d_sharpe"],"FAIL" if bad else "pass",bad))
    print("      by-year Sharpe ctl/base:", {y:(r["yr"][y][0],r["base_yr"][y][0]) for y in sorted(r["yr"])})
