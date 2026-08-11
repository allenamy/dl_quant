"""DECISIVE: is the MARKET FACTOR (common move) more predictable using ALL 14 assets'
combined flow than single-BTC (0.058)? market_y = equal-weight avg y_600 across assets;
market_X = cross-asset aggregate features. If market predictable >0.07, per-asset 0.10 reachable."""
import numpy as np, json, os.path as p
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV
C="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
SYMS=["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
FOLDS=[dict(tr=(0,250),te=(272,312)),dict(tr=(80,330),te=(352,392)),dict(tr=(160,410),te=(432,472))]
def load(s):
    d=np.load(p.join(C,f"{s}.npz")); return d["X"],d["y"],d["day"],d["ts"],d["clean600"]
per={s:load(s) for s in SYMS}
common=sorted(set.intersection(*[set(per[s][3].tolist()) for s in SYMS]))
idx={s:{int(t):i for i,t in enumerate(per[s][3])} for s in SYMS}
def al(s):
    X,y,day,ts,cl=per[s]; ii=np.array([idx[s][int(t)] for t in common]); return X[ii],y[ii],day[ii],cl[ii]
A={s:al(s) for s in SYMS}
day=A["bnfbtc"][2]; uniq=np.unique(day); cl=A["bnfbtc"][3]
# market_y = equal-weight avg of per-asset y (per-asset MAD-normalized first so comparable)
def madn(y):
    s=np.median(np.abs(y[np.isfinite(y)]-np.median(y[np.isfinite(y)])))*1.4826; return y/s if s>0 else y
Ynorm=np.column_stack([madn(A[s][1]) for s in SYMS])
market_y=np.nanmean(Ynorm,axis=1)
# market_X = mean of features across assets (aggregate state) + BTC features
Xstack=np.stack([A[s][0] for s in SYMS],axis=0)  # (14, N, F)
market_X=np.concatenate([np.nanmean(Xstack,axis=0), A["bnfbtc"][0]],axis=1)  # agg + BTC
def folddays(f):
    n=uniq.shape[0]
    if f["te"][1]>n: return None
    te0,te1=f["te"]; tr0,tr1=f["tr"]; tri=np.arange(tr0,tr1); tri=tri[tri<te0-1]
    return set(uniq[tri].tolist()),set(uniq[te0:te1].tolist())
yh,yt=[],[]
for f in FOLDS:
    r=folddays(f)
    if r is None: continue
    trd,ted=r; trm=np.isin(day,list(trd)); tem=np.isin(day,list(ted))&cl
    Xtr=market_X[trm]; ytr=market_y[trm]; Xte=market_X[tem]; yte=market_y[tem]
    gtr=np.isfinite(Xtr).all(1)&np.isfinite(ytr); Xtr,ytr=Xtr[gtr],ytr[gtr]
    gte=np.isfinite(Xte).all(1)&np.isfinite(yte); Xte,yte2=Xte[gte],yte[gte]
    mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
    m=RidgeCV(alphas=np.logspace(-2,4,13)); m.fit((Xtr-mu)/sd,ytr)
    yh.append(m.predict((Xte-mu)/sd)); yt.append(yte2)
yh=np.concatenate(yh); yt=np.concatenate(yt)
P=pearsonr(yh,yt)[0]; S=spearmanr(yh,yt).correlation
print(f"MARKET FACTOR predictability (all-asset aggregate flow -> avg y): P={P:+.4f} S={S:+.4f} n={len(yh)}")
print(f"  single-BTC was ~0.058. If market >> 0.058, per-asset 0.10 reachable via projection (0.70*market).")
print(f"  implied per-asset Pearson from projection alone: ~{0.70*P:+.4f}")
