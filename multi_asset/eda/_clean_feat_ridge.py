"""Decisive: clean BTC Ridge on PROPERLY-built raw flow/reversal features (simple z-score,
NO expanding-RMS). If it hits ~0.05 Spearman, the blocker was feature construction, data is fine."""
import numpy as np, sys
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import load_day_panel
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import RidgeCV
H=600; STRIDE=600
# train days then test days (walk-forward, time-ordered)
TRAIN=[20240601,20240701,20240801,20240901,20241001,20241101,20241201,20250101,20250201]
TEST =[20250301,20250401,20250501,20250601,20250701,20250801]
def roll(a,w):
    c=np.cumsum(np.nan_to_num(a)); o=c.copy(); o[w:]=c[w:]-c[:-w]; return o
def feats(d):
    P=load_day_panel(d,["bnfbtc"]); X=P.data["bnfbtc"]; c=P.cols
    col=lambda n:X[:,c.index(n)].astype(float)
    mid=col("mid"); lm=np.log(mid); n=len(mid)
    bp=[col("bid")]+[col(f"bid_{i}") for i in range(1,5)]; bs=[col("bidsz")]+[col(f"bidsz_{i}") for i in range(1,5)]
    ap=[col("ask")]+[col(f"ask_{i}") for i in range(1,5)]; az=[col("asksz")]+[col(f"asksz_{i}") for i in range(1,5)]
    tqb,tqs=col("tdQtyBuy"),col("tdQtySell"); tf=tqb-tqs; df=col("tdQtyPxBuy")-col("tdQtyPxSell")
    bk=(col("bkAddBid")-col("bkDelBid"))-(col("bkAddAsk")-col("bkDelAsk")); mca=col("midChgUp")-col("midChgDn")
    obi=(bs[0]-az[0])/(bs[0]+az[0]+1e-9)
    t=np.arange(300,n-H-1,STRIDE)
    F=[]
    for w in (60,300):
        F+=[ (lm[t]-lm[t-w]), roll(tf,w)[t], roll(df,w)[t], roll(bk,w)[t], roll(mca,w)[t] ]
    F+=[obi[t], (lm[t]-lm[t-30])]
    F=np.array(F).T
    y=lm[t+H]-lm[t]
    return F,y
def build(days):
    Fs,ys=[],[]
    for d in days:
        try: F,y=feats(d); Fs.append(F); ys.append(y)
        except Exception as e: print("skip",d,e)
    return np.concatenate(Fs),np.concatenate(ys)
Xtr,ytr=build(TRAIN); Xte,yte=build(TEST)
gtr=np.isfinite(Xtr).all(1)&np.isfinite(ytr); Xtr,ytr=Xtr[gtr],ytr[gtr]
gte=np.isfinite(Xte).all(1)&np.isfinite(yte); Xte,yte=Xte[gte],yte[gte]
print(f"train n={len(Xtr)} test n={len(Xte)} (after NaN drop)")
mu,sd=Xtr.mean(0),Xtr.std(0); sd=np.where(sd>1e-12,sd,1.0)
sig=np.median(np.abs(ytr-np.median(ytr)))*1.4826
m=RidgeCV(alphas=np.logspace(-2,4,13)); m.fit((Xtr-mu)/sd, ytr/sig)
p=m.predict((Xte-mu)/sd)
ok=np.isfinite(p)&np.isfinite(yte)
print(f"\nCLEAN raw-feature BTC Ridge (test 2025-03..08): P={pearsonr(p[ok],yte[ok])[0]:+.4f} S={spearmanr(p[ok],yte[ok]).correlation:+.4f} n={ok.sum()}")
print("single-asset BTC ref ~0.058 P; my bar-DL pipeline got 0.030")
