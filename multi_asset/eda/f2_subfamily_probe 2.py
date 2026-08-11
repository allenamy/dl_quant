"""F2 sub-family probe — isolate the NOVEL features (Kyle lambda + flow-tox)
vs the ones already covered by the 44 baseline (dollimb/cntimb/vpin overlap with
baseline dollarflow/cntflow/vpin). Reuses the cached _f2_assembled.npz (instant).
Reports avg dP / dS / per-fold sign consistency for each sub-family added on top
of the 44 baseline. CPU-only.
"""
from __future__ import annotations
import os, numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
CACHE_F2 = os.path.join(REPO, "multi_asset/exports/eda/_f2_assembled.npz")
SYMS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada",
        "bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS = np.logspace(-2, 4, 13); EMB = 1
FOLDS = [dict(tr=(0,250),te=(272,312)), dict(tr=(80,330),te=(352,392)),
         dict(tr=(160,410),te=(432,472))]
CACHE = os.path.join(REPO, "multi_asset/exports/panel_cache")

z = np.load(CACHE_F2, allow_pickle=True)
names = list(z["names"])
asm = {}
for s in SYMS:
    if f"{s}__X" in z:
        asm[s] = dict(X=z[f"{s}__X"], y=z[f"{s}__y"], day=z[f"{s}__day"],
                      cl=z[f"{s}__cl"], F2=z[f"{s}__F2"])
# full cache day axis for folds
cd = np.unique(np.load(os.path.join(CACHE, "bnfbtc.npz"))["day"])
FULL = cd

def mad(x):
    x = x[np.isfinite(x)]
    return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan

def folddays(f):
    if f["te"][1] > FULL.shape[0]: return None
    te0,te1=f["te"]; tr0,tr1=f["tr"]
    tri=np.arange(tr0,tr1); tri=tri[tri<te0-EMB]
    return set(FULL[tri].tolist()), set(FULL[te0:te1].tolist())

def run_perfold(s, cols):
    a = asm[s]; X,y,day,cl = a["X"],a["y"],a["day"],a["cl"]
    F = X if cols is None else np.concatenate([X, a["F2"][:, cols]], axis=1)
    out=[]
    for f in FOLDS:
        r=folddays(f)
        if r is None: out.append(None); continue
        trd,ted=r; trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))&cl
        if trm.sum()<300 or tem.sum()<20: out.append(None); continue
        Xtr,ytr=F[trm],y[trm]; Xte=F[tem]
        mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
        sig=mad(ytr)
        if not np.isfinite(sig) or sig<=0: out.append(None); continue
        m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
        pred=m.predict((Xte-mu)/sd)*sig
        out.append((float(pearsonr(pred,y[tem])[0]), float(spearmanr(pred,y[tem])[0])))
    return out

def pooled(s, cols):
    a=asm[s]; X,y,day,cl=a["X"],a["y"],a["day"],a["cl"]
    F = X if cols is None else np.concatenate([X, a["F2"][:, cols]], axis=1)
    yh,yt=[],[]
    for f in FOLDS:
        r=folddays(f)
        if r is None: continue
        trd,ted=r; trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))&cl
        if trm.sum()<300 or tem.sum()<20: continue
        Xtr,ytr=F[trm],y[trm]; Xte=F[tem]
        mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
        sig=mad(ytr)
        if not np.isfinite(sig) or sig<=0: continue
        m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
        yh.append(m.predict((Xte-mu)/sd)*sig); yt.append(y[tem])
    if not yh: return None
    yh=np.concatenate(yh); yt=np.concatenate(yt)
    return float(pearsonr(yh,yt)[0]), float(spearmanr(yh,yt)[0])

idx = {n:i for i,n in enumerate(names)}
SUBS = {
    "kyle_only":  [idx[n] for n in ["f2_kyle_300s","f2_kyle_abs_300s","f2_kyle_600s","f2_kyle_abs_600s"]],
    "flowtox":    [idx[n] for n in ["f2_flowtox_300s","f2_flowac_300s"]],
    "kyle+tox":   [idx[n] for n in ["f2_kyle_300s","f2_kyle_abs_300s","f2_kyle_600s","f2_kyle_abs_600s","f2_flowtox_300s","f2_flowac_300s"]],
    "imb_only":   [idx[n] for n in ["f2_dollimb_300s","f2_cntimb_300s","f2_dollimb_60s","f2_cntimb_60s"]],
    "sizeasym":   [idx[n] for n in ["f2_sizeasym_60s","f2_sizeasym_300s","f2_logtsize_60s","f2_logtsize_300s"]],
}

base_pf = {s: run_perfold(s, None) for s in asm}
base_pool = {s: pooled(s, None) for s in asm}
ok = [s for s in asm if base_pool[s]]

print(f"{'subfamily':12s} {'avg dP':>8s} {'avg dS':>8s}  per-fold mean dP (fracpos)")
for name, cols in SUBS.items():
    dps_pool=[]; dss_pool=[]
    fold_dp=[[] for _ in FOLDS]
    for s in ok:
        p = pooled(s, cols)
        if p and base_pool[s]:
            dps_pool.append(p[0]-base_pool[s][0]); dss_pool.append(p[1]-base_pool[s][1])
        pf = run_perfold(s, cols)
        for fi in range(len(FOLDS)):
            if pf[fi] and base_pf[s][fi]:
                fold_dp[fi].append(pf[fi][0]-base_pf[s][fi][0])
    fold_str = "  ".join(
        f"f{fi}={np.mean(fold_dp[fi]):+.4f}({(np.array(fold_dp[fi])>0).mean():.2f})"
        for fi in range(len(FOLDS)))
    print(f"{name:12s} {np.mean(dps_pool):>+8.4f} {np.mean(dss_pool):>+8.4f}  {fold_str}")
