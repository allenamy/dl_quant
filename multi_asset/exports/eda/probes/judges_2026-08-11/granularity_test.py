"""粒度检验: 小时内的微观变化, 对 4h 视界还剩多少信息?
装置: HL L2 归档(60 币 × 10 档 × 1 分钟 × 14 天) —— 唯一手上有的高频簿。
对每个小时, 由 60 帧算 深度不平衡 imb = (bidQ-askQ)/(bidQ+askQ) 的四个描述:
  D1 均值(小时聚合 —— 现行做法会保留的唯一一个)
  D2 标准差(小时内波动 —— 聚合会丢掉)
  D3 末值-首值 斜率(小时内趋势 —— 聚合会丢掉)
  D4 末值(最新状态 —— 聚合会丢掉)
判读(先写死):
  若 D2/D3/D4 对 4h 前向收益的 |IC| 均 < D1 的 50% ⇒ 小时聚合【几乎无损】, 不必上细粒度;
  若任一 ≥ D1 ⇒ 小时内动态自带信息, 值得以【多描述通道】而非【加长序列】的方式保留。
★ n=14 天, 只作方向; 且 HL≠Binance(不同场所), 结论需在 bookDepth 上复验。
"""
import numpy as np, glob, os
B="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/hl_archive/l2"
fs=sorted(glob.glob(f"{B}/*.npz"))
print(f"L2 文件 {len(fs)} 天")
rows=[]
for f in fs:
    z=np.load(f,allow_pickle=True)
    ts=z["ts"]; coin=z["coin"]; bid=z["bid"]; ask=z["ask"]
    bq=bid[:,:,1].sum(1); aq=ask[:,:,1].sum(1)
    imb=np.where((bq+aq)>0,(bq-aq)/(bq+aq+1e-12),np.nan)
    mid=(bid[:,0,0]+ask[:,0,0])/2
    hr=(ts//3600000 if ts.max()>1e11 else ts//3600)
    rows.append((hr,coin,imb,mid))
HR=np.concatenate([r[0] for r in rows]); CO=np.concatenate([r[1] for r in rows])
IM=np.concatenate([r[2] for r in rows]); MD=np.concatenate([r[3] for r in rows])
coins=sorted(set(CO.tolist())); hrs=sorted(set(HR.tolist()))
ci={c:i for i,c in enumerate(coins)}; hi={h:i for i,h in enumerate(hrs)}
D={k:np.full((len(hrs),len(coins)),np.nan) for k in ("mean","std","slope","last")}
PX=np.full((len(hrs),len(coins)),np.nan)
from collections import defaultdict
buck=defaultdict(list)
for h,c,v,m in zip(HR,CO,IM,MD):
    buck[(hi[h],ci[c])].append((v,m))
for (a,b),lst in buck.items():
    v=np.array([x[0] for x in lst],float); m=np.array([x[1] for x in lst],float)
    v=v[np.isfinite(v)]
    if len(v)<10: continue
    D["mean"][a,b]=v.mean(); D["std"][a,b]=v.std()
    D["slope"][a,b]=v[-len(v)//4:].mean()-v[:len(v)//4].mean(); D["last"][a,b]=v[-1]
    PX[a,b]=m[np.isfinite(m)][-1] if np.isfinite(m).any() else np.nan
fwd=np.full_like(PX,np.nan)
fwd[:-4]=PX[4:]/PX[:-4]-1.0
def zr(x):
    m=np.isfinite(x); o=np.full(len(x),np.nan)
    if m.sum()<8: return o
    r=np.argsort(np.argsort(x[m])).astype(float); o[m]=(r-r.mean())/(r.std()+1e-12); return o
def ic(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    return float(np.nanmean(zr(np.where(m,a,np.nan))*zr(np.where(m,b,np.nan)))) if m.sum()>=8 else np.nan
print(f"网格 {len(hrs)} 小时 × {len(coins)} 币")
base=None
for k in ("mean","std","slope","last"):
    ics=[ic(D[k][t],fwd[t]) for t in range(len(hrs)-4)]
    v=np.nanmean(ics)
    if k=="mean": base=abs(v)
    print(f"  D_{k:6s} IC(vs 4h 前向) = {v:+.4f}   相对均值 {abs(v)/base*100 if base else 0:5.0f}%")
