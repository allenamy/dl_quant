"""Phase 3.2 — POOLED cross-sectional Ridge baseline (the linear cross-sectional ceiling).
Target = cross-sectionally demeaned, per-asset-MAD-sigma-normalized residual y_tilde
(market-neutral). Features = cross-sectionally standardized (z across assets per ts).
One pooled Ridge over all (asset,timestamp). Eval = cross-sectional rank-IC on clean test.
This is the proper multi-asset baseline (vs A2b's per-asset Ridge xsec rank-IC 0.0114).
Leakage-safe: reuse A2 fold layout (train-only standardization, embargo, clean non-overlap test).
"""
from __future__ import annotations
import json, os.path as p
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
SYMBOLS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada",
           "bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
FOLDS = [dict(tr=(0,250),te=(272,312)), dict(tr=(80,330),te=(352,392)), dict(tr=(160,410),te=(432,472))]
EMBARGO=1
ALPHA=10.0   # cross-sectional ridge; modest shrinkage

def load(sym):
    d=np.load(p.join(CACHE,f"{sym}.npz")); return d["X"],d["y"],d["day"],d["ts"],d["clean600"]

# assemble aligned panel: dict ts -> {sym: (xrow, y, clean, day)}
def build_panel():
    per={s:load(s) for s in SYMBOLS}
    # common ts across all syms (intersection)
    ts_sets=[set(per[s][3].tolist()) for s in SYMBOLS]
    common=sorted(set.intersection(*ts_sets))
    cidx={int(t):i for i,t in enumerate(common)}
    nF=per["bnfbtc"][0].shape[1]
    nT=len(common); nS=len(SYMBOLS)
    X=np.full((nT,nS,nF),np.nan,np.float32); Y=np.full((nT,nS),np.nan,np.float32)
    CL=np.zeros((nT,nS),bool); DAY=np.zeros(nT,np.int64)
    for si,s in enumerate(SYMBOLS):
        Xs,ys,days,tss,cl=per[s]
        idx={int(t):i for i,t in enumerate(tss)}
        for t in common:
            j=idx[int(t)]; i=cidx[int(t)]
            X[i,si]=Xs[j]; Y[i,si]=ys[j]; CL[i,si]=cl[j]; DAY[i]=days[j]
    return np.array(common),DAY,X,Y,CL

def main():
    ts,day,X,Y,CL=build_panel()
    uniq=np.unique(day); nF=X.shape[2]
    print(f"panel: nT={len(ts)} nS={len(SYMBOLS)} nF={nF} days={len(uniq)}")

    # cross-sectional residual target + per-asset MAD-sigma (computed on TRAIN per fold below)
    def fold_days(fold):
        n=uniq.shape[0]
        if fold["te"][1]>n: return None
        te0,te1=fold["te"]; tr0,tr1=fold["tr"]
        tri=np.arange(tr0,tr1); tri=tri[tri<te0-EMBARGO]
        return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())

    all_ic=[]; per_fold=[]
    for fold in FOLDS:
        r=fold_days(fold)
        if r is None: continue
        trd,ted=r
        trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))
        # cross-sectional demean of y per timestamp (market-neutral residual)
        def xsdemean(Yblock, mask_rows):
            out=np.full_like(Yblock,np.nan)
            for i in np.where(mask_rows)[0]:
                row=Yblock[i]; v=np.isfinite(row)
                if v.sum()>=5:
                    out[i,v]=row[v]-row[v].mean()
            return out
        Ytr_res=xsdemean(Y,trm); Yte_res=xsdemean(Y,tem)
        # per-asset MAD-sigma on train residual
        sig=np.array([np.median(np.abs(Ytr_res[trm,si][np.isfinite(Ytr_res[trm,si])]-
                      np.median(Ytr_res[trm,si][np.isfinite(Ytr_res[trm,si])])))*1.4826
                      if np.isfinite(Ytr_res[trm,si]).sum()>10 else np.nan for si in range(len(SYMBOLS))])
        # cross-sectional standardize X per timestamp (z across assets), then pool
        def xsz(Xblock,mask_rows):
            out=np.full_like(Xblock,np.nan)
            for i in np.where(mask_rows)[0]:
                blk=Xblock[i]; v=np.isfinite(blk).all(1)
                if v.sum()>=5:
                    mu=blk[v].mean(0); sd=blk[v].std(0); sd=np.where(sd>1e-9,sd,1.0)
                    out[i,v]=(blk[v]-mu)/sd
            return out
        Xtr_z=xsz(X,trm); Xte_z=xsz(X,tem)
        # flatten train samples (asset,ts) with finite x + residual y
        def flat(Xz,Yr,mask_rows):
            xs,ys=[],[]
            for i in np.where(mask_rows)[0]:
                for si in range(len(SYMBOLS)):
                    if np.isfinite(Xz[i,si]).all() and np.isfinite(Yr[i,si]) and np.isfinite(sig[si]) and sig[si]>0:
                        xs.append(Xz[i,si]); ys.append(Yr[i,si]/sig[si])
            return np.array(xs),np.array(ys)
        Xf,Yf=flat(Xtr_z,Ytr_res,trm)
        if len(Xf)<1000: continue
        m=Ridge(alpha=ALPHA); m.fit(Xf,Yf)
        # predict test, eval cross-sectional rank-IC on CLEAN rows
        for i in np.where(tem)[0]:
            v=np.isfinite(Xte_z[i]).all(1) & CL[i] & np.isfinite(Yte_res[i])
            if v.sum()>=5:
                pred=m.predict(Xte_z[i,v])
                ic=spearmanr(pred,Yte_res[i,v])[0]
                if np.isfinite(ic): all_ic.append(ic)
        per_fold.append(len(all_ic))
    ic=np.array(all_ic)
    res=dict(analysis="phase3_xsec_ridge_pooled",
             target="cross-sectional demeaned residual / per-asset MAD-sigma",
             features="cross-sectionally z-scored across assets per timestamp",
             mean_xsec_rank_ic=round(float(ic.mean()),4),
             ir=round(float(ic.mean()/ic.std()*np.sqrt(len(ic))),3) if ic.std()>0 else None,
             n_ts=len(ic),
             vs_per_asset_ridge_xsec_ic=0.0114)
    import os; os.makedirs(EXPORT,exist_ok=True)
    json.dump(res,open(p.join(EXPORT,"phase3_xsec_ridge.json"),"w"),indent=2)
    print(json.dumps(res,indent=2))

if __name__=="__main__":
    main()
