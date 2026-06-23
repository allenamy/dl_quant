"""Layer-1 (correct mechanism): inject BTC's PREDICTION (distilled common factor),
not raw BTC features. Per fold: BTC Ridge -> yhat_btc; alt Ridge on [yhat_btc + alt feats]
-> raw alt_y. Compare per-asset Pearson vs alt-only. yhat_btc is the 1-feature common factor.
"""
from __future__ import annotations
import json, os.path as p
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

CACHE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
EXPORT="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
SYMS=["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALTS=[s for s in SYMS if s!="bnfbtc"]
ALPHAS=np.logspace(-2,4,13); EMB=1
FOLDS=[dict(tr=(0,250),te=(272,312)),dict(tr=(80,330),te=(352,392)),dict(tr=(160,410),te=(432,472))]

def mad(x):
    x=x[np.isfinite(x)]; return float(np.median(np.abs(x-np.median(x)))*1.4826) if x.size else np.nan
def load(s):
    d=np.load(p.join(CACHE,f"{s}.npz")); return d["X"],d["y"],d["day"],d["ts"],d["clean600"]

per={s:load(s) for s in SYMS}
common=sorted(set.intersection(*[set(per[s][3].tolist()) for s in SYMS]))
idx={s:{int(t):i for i,t in enumerate(per[s][3])} for s in SYMS}
def aligned(s):
    X,y,day,ts,cl=per[s]; ii=np.array([idx[s][int(t)] for t in common]); return X[ii],y[ii],day[ii],cl[ii]
A={s:aligned(s) for s in SYMS}
day=A["bnfbtc"][2]; uniq=np.unique(day)

def folddays(f):
    n=uniq.shape[0]
    if f["te"][1]>n: return None
    te0,te1=f["te"]; tr0,tr1=f["tr"]; tri=np.arange(tr0,tr1); tri=tri[tri<te0-EMB]
    return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())

def fit_pred(F,y,trm,tem):
    Xtr,ytr=F[trm],y[trm]; mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
    sig=mad(ytr)
    if not np.isfinite(sig) or sig<=0: return None,None
    m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
    pred_tr=m.predict((Xtr-mu)/sd)*sig; pred_te=m.predict((F[tem]-mu)/sd)*sig
    return pred_tr,pred_te

res={}
for s in ALTS: res[s]={"only":([],[]),"with":([],[])}
for f in FOLDS:
    r=folddays(f)
    if r is None: continue
    trd,ted=r; trm=np.isin(day,list(trd)); tem0=np.isin(day,list(ted))
    # BTC yhat (common factor) for train+test
    bX,bY=A["bnfbtc"][0],A["bnfbtc"][1]
    btr,bte=fit_pred(bX,bY,trm,tem0)
    if btr is None: continue
    for s in ALTS:
        X,y,_,cl=A[s]; tem=tem0&cl
        # alt-only
        _,p_only=fit_pred(X,y,trm,tem)
        # alt + yhat_btc (1 distilled feature)
        Fp=np.concatenate([X, np.zeros((len(X),1))],axis=1)
        Fp[trm,-1]=btr; Fp[tem,-1]=bte
        _,p_with=fit_pred(Fp,y,trm,tem)
        if p_only is not None:
            res[s]["only"][0].append(p_only); res[s]["only"][1].append(y[tem])
        if p_with is not None:
            res[s]["with"][0].append(p_with); res[s]["with"][1].append(y[tem])

def metr(pair):
    if not pair[0]: return None
    yh=np.concatenate(pair[0]); yt=np.concatenate(pair[1])
    return dict(P=round(float(pearsonr(yh,yt)[0]),4), S=round(float(spearmanr(yh,yt)[0]),4))
out={}
for s in ALTS:
    a=metr(res[s]["only"]); b=metr(res[s]["with"])
    out[s]=dict(alt_only=a, alt_plus_btcpred=b, dP=round(b["P"]-a["P"],4) if a and b else None, dS=round(b["S"]-a["S"],4) if a and b else None)
aP=np.mean([out[s]["alt_only"]["P"] for s in ALTS]); bP=np.mean([out[s]["alt_plus_btcpred"]["P"] for s in ALTS])
aS=np.mean([out[s]["alt_only"]["S"] for s in ALTS]); bS=np.mean([out[s]["alt_plus_btcpred"]["S"] for s in ALTS])
summary=dict(analysis="L1_alt_with_btc_PREDICTION",
    avg_alt_P_only=round(float(aP),4),avg_alt_P_with_btcpred=round(float(bP),4),avg_dP=round(float(bP-aP),4),
    avg_alt_S_only=round(float(aS),4),avg_alt_S_with_btcpred=round(float(bS),4),avg_dS=round(float(bS-aS),4),per_alt=out)
import os; os.makedirs(EXPORT,exist_ok=True); json.dump(summary,open(p.join(EXPORT,"L1_alt_with_btcpred.json"),"w"),indent=2)
print(f"avg ALT P: only={aP:+.4f} +BTCpred={bP:+.4f} (dP={bP-aP:+.4f}) | S: only={aS:+.4f} +BTCpred={bS:+.4f} (dS={bS-aS:+.4f})")
print(f"\n{'alt':9s} {'P_only':>8s} {'P+BTCp':>8s} {'dP':>7s} {'S_only':>8s} {'S+BTCp':>8s} {'dS':>7s}")
for s in ALTS:
    o=out[s]; a,b=o["alt_only"],o["alt_plus_btcpred"]
    print(f"{s:9s} {a['P']:>+8.4f} {b['P']:>+8.4f} {o['dP']:>+7.4f} {a['S']:>+8.4f} {b['S']:>+8.4f} {o['dS']:>+7.4f}")
print("\nGATE: if +BTCpred lifts avg alt P by >=+0.01 -> the distilled common-factor mechanism works -> multi-asset DL with cross-asset attention is the path.")
