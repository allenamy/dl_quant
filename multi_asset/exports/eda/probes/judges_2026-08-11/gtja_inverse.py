"""反演生产 gtja 的真实构造: 扫窗口族 × 价格源, corr 最高者即真凶。"""
import numpy as np, sys
sys.path.insert(0,"/workspace/code")
from multi_asset.data.wide_factory import _roll
G=np.load("/workspace/data/ohlcv_grid.npz",allow_pickle=True)
D=np.load("/workspace/data/prod3.npz",allow_pickle=True)
rows=D["rows"]; prod=D["C3"][:,:,0]
C=G["CLOSE"].astype(np.float64)
QV=G["QVOL"].astype(np.float64); V=G["VOL"].astype(np.float64)
VW=np.where(V>0,QV/np.where(V>0,V,np.nan),np.nan)
def cc(x):
    a=x[rows].astype(np.float32); b=prod
    m=np.isfinite(a)&np.isfinite(b)&((a!=0)|(b!=0))
    return float(np.corrcoef(a[m],b[m])[0,1]) if m.sum()>500 else np.nan
def g(P,ws):
    return sum(_roll(P,w,"mean") for w in ws)/(len(ws)*P)
CAND={}
for k in (1,2,3,4,6,8):
    CAND[f"close k={k} ({[3*k,6*k,12*k,24*k]})"]=g(C,[3*k,6*k,12*k,24*k])
CAND["vwap k=1"]=g(VW,[3,6,12,24])
CAND["vwap k=4"]=g(VW,[12,24,48,96])
# 4h 子采样后滚动(4h-bar 解释), ffill 回 1h 网格
import pandas as pd
C4=C[::4]
g4=g(C4,[3,6,12,24])
full=np.full_like(C,np.nan); full[::4]=g4
CAND["close 4h-bar (3,6,12,24)@4h"]=pd.DataFrame(full).ffill(limit=3).values
res=sorted(((nm,cc(x)) for nm,x in CAND.items()),key=lambda kv:-(kv[1] if np.isfinite(kv[1]) else -9))
for nm,c in res: print(f"  {nm:34s} corr={c:.4f}")
print(f"\n★ 最佳: {res[0][0]}  corr={res[0][1]:.4f}")
