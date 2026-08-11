"""Layer-1 GATE: does the BTC common factor lift ALT per-asset Pearson?
Per-alt Ridge predicting RAW alt_y_600, features = alt's 47 bar feats [+ BTC's 47 feats
as the contemporaneous common factor]. Compare alt-only vs alt+BTC. Walk-forward, clean.
This gates the multi-asset DL build (project rule: Ridge ΔP before DL pod).
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

# align all syms on common ts
per={s:load(s) for s in SYMS}
common=sorted(set.intersection(*[set(per[s][3].tolist()) for s in SYMS]))
idx={s:{int(t):i for i,t in enumerate(per[s][3])} for s in SYMS}
ci=np.array(common)
btc_ts_set=common
# build aligned arrays
def aligned(s):
    X,y,day,ts,cl=per[s]; ii=np.array([idx[s][int(t)] for t in common])
    return X[ii],y[ii],day[ii],cl[ii]
A={s:aligned(s) for s in SYMS}
day=A["bnfbtc"][2]; uniq=np.unique(day)
btcX=A["bnfbtc"][0]

def folddays(f):
    n=uniq.shape[0]
    if f["te"][1]>n: return None
    te0,te1=f["te"]; tr0,tr1=f["tr"]; tri=np.arange(tr0,tr1); tri=tri[tri<te0-EMB]
    return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())

def run(sym, with_btc):
    X,y,_,cl=A[sym]
    F=np.concatenate([X,btcX],axis=1) if with_btc else X
    yh,yt=[],[]
    for f in FOLDS:
        r=folddays(f)
        if r is None: continue
        trd,ted=r; trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))&cl
        if trm.sum()<500 or tem.sum()<20: continue
        Xtr,ytr=F[trm],y[trm]; Xte=F[tem]
        mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
        sig=mad(ytr)
        if not np.isfinite(sig) or sig<=0: continue
        m=RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
        yh.append(m.predict((Xte-mu)/sd)*sig); yt.append(y[tem])
    if not yh: return None
    yh=np.concatenate(yh); yt=np.concatenate(yt)
    return dict(P=round(float(pearsonr(yh,yt)[0]),4), S=round(float(spearmanr(yh,yt)[0]),4), n=len(yh))

res={}
for s in ALTS:
    a=run(s,False); b=run(s,True)
    res[s]=dict(alt_only=a, alt_plus_btc=b,
                dP=round(b["P"]-a["P"],4) if a and b else None,
                dS=round(b["S"]-a["S"],4) if a and b else None)
avgP_only=np.mean([res[s]["alt_only"]["P"] for s in ALTS if res[s]["alt_only"]])
avgP_btc =np.mean([res[s]["alt_plus_btc"]["P"] for s in ALTS if res[s]["alt_plus_btc"]])
avgS_only=np.mean([res[s]["alt_only"]["S"] for s in ALTS if res[s]["alt_only"]])
avgS_btc =np.mean([res[s]["alt_plus_btc"]["S"] for s in ALTS if res[s]["alt_plus_btc"]])
summary=dict(analysis="L1_alt_with_btc_factor",
    avg_alt_P_alt_only=round(float(avgP_only),4), avg_alt_P_with_btc=round(float(avgP_btc),4),
    avg_alt_S_alt_only=round(float(avgS_only),4), avg_alt_S_with_btc=round(float(avgS_btc),4),
    avg_dP_from_btc=round(float(avgP_btc-avgP_only),4), avg_dS_from_btc=round(float(avgS_btc-avgS_only),4),
    per_alt=res)
import os; os.makedirs(EXPORT,exist_ok=True)
json.dump(summary,open(p.join(EXPORT,"L1_alt_with_btc.json"),"w"),indent=2)
print(f"avg ALT per-asset Pearson: alt-only={avgP_only:+.4f}  alt+BTC={avgP_btc:+.4f}  (dP={avgP_btc-avgP_only:+.4f})")
print(f"avg ALT per-asset Spearman: alt-only={avgS_only:+.4f}  alt+BTC={avgS_btc:+.4f}  (dS={avgS_btc-avgS_only:+.4f})")
print(f"\n{'alt':9s} {'P_only':>8s} {'P+BTC':>8s} {'dP':>7s} {'S_only':>8s} {'S+BTC':>8s} {'dS':>7s}")
for s in ALTS:
    r=res[s]; a,b=r["alt_only"],r["alt_plus_btc"]
    if a and b: print(f"{s:9s} {a['P']:>+8.4f} {b['P']:>+8.4f} {r['dP']:>+7.4f} {a['S']:>+8.4f} {b['S']:>+8.4f} {r['dS']:>+7.4f}")
print("\nGATE: if alt+BTC avg P >= ~0.05 AND dP >= +0.01, common factor is the lever -> build multi-asset DL.")
