"""F3 follow-up: (a) marginal contribution of TOP-k F3 features only (not all 43,
which overfit), (b) residualized univariate signal of each top feature beyond the
44 baseline. Uses the cached build. Confirms whether ANY book-dynamics mechanism
adds marginal alpha or whether it's all collinear with the existing 44.
"""
from __future__ import annotations
import json, os.path as pth, sys
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV, LinearRegression

REPO="/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0,REPO)
SYMS=["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink",
      "bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS=np.logspace(-2,4,13); EMB=1
FOLDS=[dict(tr=(0,250),te=(272,312)),dict(tr=(80,330),te=(352,392)),dict(tr=(160,410),te=(432,472))]
CACHE=pth.join(REPO,"multi_asset/exports/panel_cache")

z=np.load(pth.join(REPO,"multi_asset/exports/eda/_f3_built.npz"),allow_pickle=True)
feat=list(z["feat_names"])
data={s:dict(X44=z[f"{s}_X44"],y=z[f"{s}_y"],day=z[f"{s}_day"],
             clean=z[f"{s}_clean"].astype(bool),F3=z[f"{s}_F3"].astype(np.float64)) for s in SYMS}
alldays=np.unique(np.load(pth.join(CACHE,"bnfbtc.npz"))["day"]); uniq=alldays

def mad(x):
    x=x[np.isfinite(x)]; return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan
def folddays(f):
    n=uniq.shape[0]; te0,te1=f["te"]; tr0,tr1=f["tr"]
    if te0>=n: return None
    te1=min(te1,n); tri=np.arange(tr0,min(tr1,n)); tri=tri[tri<te0-EMB]
    return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())

def run(sym,cols):
    """cols=None -> baseline 44; else 44 + F3[:,cols]."""
    d=data[sym]
    X=d["X44"] if cols is None else np.concatenate([d["X44"],d["F3"][:,cols]],1)
    yh,yt,foldP=[],[],[]
    for f in FOLDS:
        r=folddays(f)
        if r is None: continue
        trd,ted=r; trm=np.isin(d["day"],list(trd)); tem=np.isin(d["day"],list(ted))&d["clean"]
        if trm.sum()<500 or tem.sum()<20: continue
        Xtr,ytr=X[trm],d["y"][trm]; Xte=X[tem]; yte=d["y"][tem]
        mu=Xtr.mean(0);sd=Xtr.std(0);sd=np.where(sd>1e-12,sd,1.0); sig=mad(ytr)
        if not np.isfinite(sig) or sig<=0: continue
        m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd,ytr/sig)
        p=m.predict((Xte-mu)/sd)*sig; yh.append(p); yt.append(yte)
        if len(p)>5: foldP.append(spearmanr(p,yte)[0])
    if not yh: return None
    yh=np.concatenate(yh);yt=np.concatenate(yt)
    return dict(P=float(pearsonr(yh,yt)[0]),S=float(spearmanr(yh,yt)[0]),foldS=foldP)

# ---- (a) TOP-k subsets ----
# strongest distinct mechanisms (avoid window-redundancy): spread-stress, add-imbalance,
# net-replenishment, OFI(5lvl), queue-imb-change. pick 1 per mechanism at its best window.
TOPSETS={
 "spread_only":["d_spread_300s"],
 "addimb_only":["addimb_300s"],
 "ofi_only":["ofi_300s"],
 "dOBI_only":["d_obi1_60s"],
 "netrepl_only":["netrepl_300s"],
 "best5_distinct":["d_spread_300s","addimb_300s","ofi_300s","d_obi1_60s","netrepl_300s"],
}
idx={n:feat.index(n) for n in feat}
print(f"{'set':16s} {'avgdP':>8s} {'avgdS':>8s} {'foldS+/-':>10s}",flush=True)
base={s:run(s,None) for s in SYMS}
res={}
for name,cols in TOPSETS.items():
    ci=[idx[c] for c in cols]
    dPs,dSs=[],[]; signs=[]
    for s in SYMS:
        b=base[s]; p=run(s,ci)
        if not(b and p): continue
        dPs.append(p["P"]-b["P"]); dSs.append(p["S"]-b["S"])
        for bf,pf in zip(b["foldS"],p["foldS"]): signs.append(pf-bf)
    sp=sum(1 for x in signs if x>0); sn=sum(1 for x in signs if x<0)
    res[name]=dict(avgdP=round(float(np.mean(dPs)),4),avgdS=round(float(np.mean(dSs)),4),
                   foldSpos=sp,foldSneg=sn)
    print(f"{name:16s} {np.mean(dPs):>+8.4f} {np.mean(dSs):>+8.4f}   +{sp}/-{sn}",flush=True)

# ---- (b) residualized univariate: signal of feature BEYOND the 44 baseline ----
# pool all assets' clean rows, per-asset MAD-normalize y, regress feature on X44
# (within-asset, leak-free is not the point here — this is a pooled descriptive
# measure of *incremental* linear info). Report Spearman of residual-feature vs y.
print("\nResidualized univariate (feature info beyond 44 baseline), pooled clean:",flush=True)
TOPF=["d_spread_300s","addimb_300s","ofi_300s","netrepl_300s","d_obi1_60s","replratio_300s"]
for fn in TOPF:
    j=idx[fn]; rs=[]
    for s in SYMS:
        d=data[s]; cl=d["clean"]
        X=d["X44"][cl]; f=d["F3"][cl,j]; y=d["y"][cl]
        m=np.isfinite(f)&np.isfinite(y)&np.all(np.isfinite(X),1)
        if m.sum()<300 or np.std(f[m])<1e-12: continue
        lr=LinearRegression().fit(X[m],f[m]); fr=f[m]-lr.predict(X[m])  # feature residual
        if np.std(fr)<1e-12: continue
        rs.append(spearmanr(fr,y[m])[0])
    raw=[]
    for s in SYMS:
        d=data[s];cl=d["clean"];f=d["F3"][cl,j];y=d["y"][cl];mm=np.isfinite(f)&np.isfinite(y)
        if mm.sum()>=300 and np.std(f[mm])>1e-12: raw.append(spearmanr(f[mm],y[mm])[0])
    print(f"  {fn:16s} raw|S|={np.mean(np.abs(raw)):.4f}  residual|S|={np.mean(np.abs(rs)):.4f}  (kept {len(rs)} assets)",flush=True)

json.dump(res,open(pth.join(REPO,"multi_asset/exports/eda/F3_subset_marginal.json"),"w"),indent=2)
print("\n[F3] subset/marginal done",flush=True)
