"""king LGBM staleness direct test (PREREG_staleness_king_2026-09-11.md).
Row construction / keep cols / hyperparams copied verbatim from pod_export_bundle_v4.py L38-L52."""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
T0=time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]",*a,flush=True)
FEA=np.load("/workspace/data/wide_fea_v4.npy")
MT=np.load("/workspace/data/wide_fea_v4_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]
names=[str(n) for n in MT["names"]]
yrs=np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA=len(E_ts)
PINS=json.load(open("/workspace/live_pins.json"))
keep=[k for k,nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep]==PINS["keep_names"]
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    r=spearmanr(a[ok],b[ok]); return r.correlation if hasattr(r,"correlation") else r[0]
rows_X,rows_y,rows_a=[],[],[]
for i in range(nA):
    m=members[i]; yv=y4[i,m]; ok=np.isfinite(yv)
    if ok.sum()<50: continue
    rr=rankdata(yv[ok])/max(ok.sum()-1,1)-0.5
    rows_X.append(FEA[i,m[ok]][:,keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(),i,np.int32))
X=np.concatenate(rows_X); Y=np.concatenate(rows_y); A=np.concatenate(rows_a)
del rows_X,rows_y,rows_a,FEA
YRA=yrs[A]; TSA=E_ts[A]
log("rows",X.shape)
H0=int(time.mktime(time.struct_time((2026,7,1,0,0,0,0,0,0)))) if False else 1782864000  # placeholder
import calendar
H0=calendar.timegm((2026,7,1,0,0,0,0,0,0)); H1=calendar.timegm((2026,9,1,0,0,0,0,0,0))
R0=calendar.timegm((2024,7,1,0,0,0,0,0,0)); A1=calendar.timegm((2026,8,1,0,0,0,0,0,0))
te=(TSA>=H0)&(TSA<H1)
ARMS={"S_stale_lt2026": YRA<2026,
      "F_fresh_lt2026Jul": TSA<H0,
      "R_roll24m": (TSA>=R0)&(TSA<H0)}
res={}; preds={}
for nm,tr in ARMS.items():
    g=lgb.LGBMRegressor(n_estimators=400,learning_rate=0.05,num_leaves=63,
                        subsample=0.8,colsample_bytree=0.8,n_jobs=60,verbose=-1).fit(X[tr],Y[tr])
    pv=g.predict(X[te]); preds[nm]=pv
    log(nm,"n_train_rows",int(tr.sum()),"done")
a_te=A[te]; ua=np.unique(a_te)
ICS={nm:[] for nm in ARMS}; ANC=[]
for a in ua:
    sel=a_te==a; m=members[a]; okm=np.isfinite(y4[a,m]); yv=y4[a,m][okm]
    ANC.append(int(E_ts[a]))
    for nm in ARMS: ICS[nm].append(sp(preds[nm][sel],yv))
ANC=np.array(ANC); ICS={k:np.array(v) for k,v in ICS.items()}
day=np.array([int(t)//86400 for t in ANC])
def boot(d,day,n=2000,seed=20260911):
    rng=np.random.default_rng(seed); ud=np.unique(day)
    idx={u:np.nonzero(day==u)[0] for u in ud}
    out=np.empty(n)
    for b in range(n):
        pick=rng.choice(ud,len(ud),replace=True)
        ii=np.concatenate([idx[u] for u in pick]); out[b]=np.nanmean(d[ii])
    return out
out={"n_anchors_H":int(len(ANC)),"H":"2026-07-01..2026-08-31","n_days":int(len(np.unique(day)))}
for nm in ARMS:
    out[f"IC_{nm}"]=float(np.nanmean(ICS[nm]))
    out[f"n_train_rows_{nm}"]=int(ARMS[nm].sum())
for nm in ("F_fresh_lt2026Jul","R_roll24m"):
    d=ICS[nm]-ICS["S_stale_lt2026"]
    bs=boot(d,day)
    out[f"delta_{nm}_minus_S"]={"point":float(np.nanmean(d)),"ci95":[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],"P_gt0":float((bs>0).mean())}
    h2=ANC>=A1
    d2=d[h2]; bs2=boot(d2,day[h2])
    out[f"delta_{nm}_minus_S_H2Aug"]={"point":float(np.nanmean(d2)),"ci95":[float(np.percentile(bs2,2.5)),float(np.percentile(bs2,97.5))],"n":int(h2.sum())}
# monthly IC
import collections
mon=np.array([time.strftime("%Y-%m",time.gmtime(t)) for t in ANC])
out["monthly_IC"]={m:{nm:float(np.nanmean(ICS[nm][mon==m])) for nm in ARMS} for m in sorted(set(mon))}
out["lgbm_version"]=lgb.__version__
json.dump(out,open("/workspace/codex_research/uplift_stale_king.json","w"),indent=1)
np.savez("/workspace/codex_research/uplift_stale_king_ics.npz",anchors=ANC,**{f"ic_{k}":v for k,v in ICS.items()})
print(json.dumps(out,indent=1))
