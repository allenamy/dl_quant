import numpy as np, glob, os.path as p
D = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/m0_fullhist_wf"
ref = np.load(p.join(D, "panel_ref.npz"), allow_pickle=True)
Y, CL = ref["Y"].astype(np.float64), ref["CL"].astype(bool)
ts = ref["ts"].astype(np.int64); day = ref["day"].astype(np.int64)
import datetime as dt
u = 1e9 if ts[0]>1e17 else (1e6 if ts[0]>1e14 else (1e3 if ts[0]>1e11 else 1.0))
yr = np.array([dt.datetime.utcfromtimestamp(int(t)/u).year for t in ts])
print("panel_ref: T=%d S=%d | CL frac=%.4f | date %s..%s" % (
    len(ts), Y.shape[1], CL.mean(),
    dt.datetime.utcfromtimestamp(int(ts[0])/u).strftime("%Y-%m-%d"),
    dt.datetime.utcfromtimestamp(int(ts[-1])/u).strftime("%Y-%m-%d")))
print("per-year panel rows:", {int(y): int((yr==y).sum()) for y in np.unique(yr)})
from scipy.stats import rankdata
def ric(f,y):
    rf=rankdata(f)-0.0; ry=rankdata(y); rf=rf-rf.mean(); ry=ry-ry.mean()
    d=np.sqrt((rf*rf).sum()*(ry*ry).sum()); return (rf*ry).sum()/d if d>1e-12 else np.nan
for f in sorted(glob.glob(p.join(D,"fold_*_preds.npz"))):
    z=np.load(f); pred=np.full(Y.shape,np.nan); pred[z["te_rows"]]=z["pred"][z["te_rows"]]
    te=z["te_rows"]; tey=yr[te]
    # which years does this fold's test cover?
    yrs={int(v):int((tey==v).sum()) for v in np.unique(tey)}
    # sigma ratio on te rows (clean) + IC on >=3600 CL
    ics=[]; sp=[]; sy=[]
    for t in te:
        v=CL[t]&np.isfinite(pred[t])&np.isfinite(Y[t])
        if v.sum()<5: continue
        fp=pred[t,v]; yv=Y[t,v]
        if np.std(fp)<1e-12 or np.std(yv)<1e-12: continue
        ics.append(ric(fp,yv)); sp.append(np.std(fp)); sy.append(np.std(yv))
    ics=np.array(ics)
    print("%s: te_rows=%d te-years=%s | >=3600CL rank-IC=%+.4f (IR %.1f, n_ts=%d) | sigma_hat/sigma_y=%.3f" % (
        p.basename(f), len(te), yrs, ics.mean(), ics.mean()/(ics.std()+1e-12), len(ics),
        np.mean(sp)/(np.mean(sy)+1e-12)))
# fund_ema_fullhist staged?
FE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/fund_ema_fullhist"
print("fund_ema_fullhist staged:", p.exists(p.join(FE,"panel_ref.npz")), "|", sorted([p.basename(x) for x in glob.glob(FE+"/*")]) if p.exists(FE) else "MISSING")
