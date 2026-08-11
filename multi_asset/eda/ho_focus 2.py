"""Focused follow-up on the HO winners (bs, ll). Reuses gate load + walkforward.
 (1) per-fold P breakdown (resolve single-perfold display).
 (2) bs-only, bs+ll combined, and bs+ll+rg block-dP on perp_y per regime.
 (3) bs ROW-shift leak check: shift bs feature rows forward by ~one horizon worth
     of pred-rows; a true >=t leak would inflate the bs block-dP.
"""
import sys, glob, os.path as p, numpy as np
from scipy.stats import pearsonr
_REPO="/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0,_REPO)
from multi_asset.eda.ho_factors_gate import (load_days, STRONG_FOLDS, CHOPPY_FOLDS,
    LASTTS_DIR, _have, _first_ge, TEST_DAYS, VAL_DAYS, MIN_TRAIN_DAYS)
from multi_asset.eda.perpY_ridge_gate import _fit_select, _predict
from multi_asset.data.build_ho_factors import HO_FAMILIES

def _alld_through(end):
    a=sorted({p.basename(f)[:-4] for f in glob.glob(p.join(LASTTS_DIR,"*.npz")) if p.basename(f)[0].isdigit()})
    return [d for d in a if d<=end and _have(d)]

def wf_perfold(X, y, di, dl, folds, name):
    out=[]
    for fold in folds:
        ts0=_first_ge(dl, fold["test_start"]); te0,te1=ts0,ts0+TEST_DAYS
        va0,va1=te0-VAL_DAYS,te0; tr0,tr1=0,va0-1
        if te1>len(dl) or va0<0 or (tr1-tr0)<MIN_TRAIN_DAYS:
            out.append((fold["name"],"unavail",None)); continue
        trm=np.isin(di,np.arange(tr0,tr1)); vam=np.isin(di,np.arange(va0,va1)); tem=np.isin(di,np.arange(te0,te1))
        if trm.sum()<500 or vam.sum()<20 or tem.sum()<20:
            out.append((fold["name"],"few",None)); continue
        sel=_fit_select(X[trm],y[trm],X[vam],y[vam],"madz")
        if sel is None: out.append((fold["name"],"badsig",None)); continue
        w,b,c,s,sg,lam,vp=sel; yh=_predict(X[tem],w,b,c,s,sg); yt=y[tem]
        P=float(pearsonr(yh,yt)[0]) if np.std(yh)>0 and np.std(yt)>0 else float("nan")
        out.append((fold["name"],"ok",(round(P,4),int(tem.sum()),f"{dl[te0]}..{dl[te1-1]}")))
    return out

def pooled_P(X,y,di,dl,folds):
    yhs,yys=[],[]
    for fold in folds:
        ts0=_first_ge(dl,fold["test_start"]); te0,te1=ts0,ts0+TEST_DAYS; va0,va1=te0-VAL_DAYS,te0; tr0,tr1=0,va0-1
        if te1>len(dl) or va0<0 or (tr1-tr0)<MIN_TRAIN_DAYS: continue
        trm=np.isin(di,np.arange(tr0,tr1));vam=np.isin(di,np.arange(va0,va1));tem=np.isin(di,np.arange(te0,te1))
        if trm.sum()<500 or vam.sum()<20 or tem.sum()<20: continue
        sel=_fit_select(X[trm],y[trm],X[vam],y[vam],"madz")
        if sel is None: continue
        w,b,c,s,sg,lam,vp=sel; yhs.append(_predict(X[tem],w,b,c,s,sg)); yys.append(y[tem])
    if not yhs: return float("nan"),0
    yh=np.concatenate(yhs);yy=np.concatenate(yys)
    return (float(pearsonr(yh,yy)[0]) if np.std(yh)>0 else float("nan")), len(yy)

def run(name, folds):
    last=max(f["test_start"] for f in folds); import datetime as dt
    y,mo=map(int,last[:7].split("-")); nd=(dt.date(y+(mo==12),(mo%12)+1,1)-dt.date(y,mo,1)).days
    days=_alld_through(f"{last[:7]}-{nd:02d}")
    data=load_days(days, verbose=False); dl=data["kept_days"]; di=data["day_idx"]
    spot64=data["spot64"];cur=data["cur"];ho=data["ho"];py=data["perp_y"]
    current=np.concatenate([spot64,cur],1)
    baseP,n=pooled_P(current,py,di,dl,folds)
    print(f"\n=== {name} (n={n}) base CURRENT P={baseP:+.4f} ===")
    print(" base per-fold:", wf_perfold(current,py,di,dl,folds,"base"))
    combos={"bs":["bs"],"ll":["ll"],"bs+ll":["bs","ll"],"bs+ll+rg":["bs","ll","rg"],
            "bs+rg":["bs","rg"]}
    for cn,fams in combos.items():
        Xf=np.concatenate([ho[f] for f in fams],1)
        cP,_=pooled_P(np.concatenate([current,Xf],1),py,di,dl,folds)
        pf=wf_perfold(np.concatenate([current,Xf],1),py,di,dl,folds,cn)
        print(f"  CUR+{cn:9s} P={cP:+.4f} dP={cP-baseP:+.4f}  perfold={[(x[0],x[2][0] if x[1]=='ok' else x[1]) for x in pf]}")
    # bs row-shift leak check: shift bs rows forward within each day-block by 'rows'
    bs=ho["bs"].copy()
    # shift forward by 5 pred-rows (~ a horizon-ish gap on the clean grid) within day
    di_arr=di; bs_sh=bs.copy()
    for d in np.unique(di_arr):
        m=np.where(di_arr==d)[0]
        if m.size>6:
            bs_sh[m[:-5]]=bs[m[5:]]  # row i gets a FUTURE row's bs (leak direction)
    cP,_=pooled_P(np.concatenate([current,bs],1),py,di,dl,folds)
    cPs,_=pooled_P(np.concatenate([current,bs_sh],1),py,di,dl,folds)
    print(f"  bs leak check: CUR+bs P={cP:+.4f}  CUR+bs(rows+5 future) P={cPs:+.4f}  (future-shift must NOT exceed)")

if __name__=="__main__":
    run("STRONG",STRONG_FOLDS)
    run("CHOPPY",CHOPPY_FOLDS)
