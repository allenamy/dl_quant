"""三列差异对账: 生产列反推输入, 与我的输入直接比。
logqvol = log(QVOL) ⇒ exp(生产列) = 生产 QVOL —— 可与我的 QVOL 逐格对账。
gtja: 用我的 CLOSE 复算多个变体, 看哪个匹配生产 —— (a)原样 (b)ffill 后 (c)日窗(72/144/288/576h)。"""
import numpy as np, sys
sys.path.insert(0,"/workspace/code")
from multi_asset.data.wide_factory import _roll
G=np.load("/workspace/data/ohlcv_grid.npz",allow_pickle=True)
D=np.load("/workspace/data/prod3.npz",allow_pickle=True)
rows=D["rows"]; P3=D["C3"]
C=G["CLOSE"].astype(np.float64); QV=G["QVOL"].astype(np.float64)
import pandas as pd
def cc(a,b):
    m=np.isfinite(a)&np.isfinite(b)&((a!=0)|(b!=0))
    return float(np.corrcoef(a[m],b[m])[0,1]) if m.sum()>500 else np.nan
print("═══ logqvol 对账 ═══")
prod_qv=np.exp(P3[:,:,2]); prod_qv[P3[:,:,2]==0]=np.nan
mine=QV[rows]
m=np.isfinite(prod_qv)&np.isfinite(mine)&(mine>0)
ratio=mine[m]/prod_qv[m]
print(f"  QVOL 比值(我/产): 中位 {np.median(ratio):.4f}  P5 {np.percentile(ratio,5):.4f}  P95 {np.percentile(ratio,95):.4f}")
print(f"  比值≈1 的占比 {(np.abs(ratio-1)<0.001).mean()*100:.1f}%")
# 按币看谁最歪
bys={}
for j in range(mine.shape[1]):
    mm=np.isfinite(prod_qv[:,j])&np.isfinite(mine[:,j])&(mine[:,j]>0)
    if mm.sum()>50: bys[j]=float(np.median(mine[mm,j]/prod_qv[mm,j]))
syms=[str(s) for s in G["symbols"]]
worst=sorted(bys.items(),key=lambda kv:abs(np.log(kv[1])))[-6:]
print("  偏得最远的币:", [(syms[j],round(v,3)) for j,v in worst])
print("═══ gtja 变体复算 ═══")
def gtja(Cx):
    return (_roll(Cx,3,"mean")+_roll(Cx,6,"mean")+_roll(Cx,12,"mean")+_roll(Cx,24,"mean"))/(4*Cx)
prod_g=P3[:,:,0]
print(f"  (a) 原样(现行):        corr={cc(gtja(C)[rows].astype(np.float32),prod_g):.4f}")
Cf=pd.DataFrame(C).ffill(limit=24).values
print(f"  (b) CLOSE ffill(24h):  corr={cc(gtja(Cf)[rows].astype(np.float32),prod_g):.4f}")
def gtja_d(Cx):
    return (_roll(Cx,72,"mean")+_roll(Cx,144,"mean")+_roll(Cx,288,"mean")+_roll(Cx,576,"mean"))/(4*Cx)
print(f"  (c) 日窗(72-576h):     corr={cc(gtja_d(C)[rows].astype(np.float32),prod_g):.4f}")
print(f"  (d) 日窗+ffill:        corr={cc(gtja_d(Cf)[rows].astype(np.float32),prod_g):.4f}")
