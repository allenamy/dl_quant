"""三件套: F2 重测(dropna) / F7 根因抽检 / Y8+Y12 目标列构建。
Y4 交叉断言 = 重建路线的第二路独立校验(与 baseline8 互补):
  corr(由自建 CLOSE 算的 forward-4h, 生产面板 Y4) 应 ≈1 —— 不到 0.999 就停下找差。"""
import glob, sys, hashlib
import numpy as np
import pandas as pd

print("═"*70); print("[F2-fix] count_top vs sum_top (dropna 后)")
for s in ("BTCUSDT","SOLUSDT","OPUSDT"):
    parts=[]
    for fp in sorted(glob.glob(f"/workspace/data/raw/metrics/{s}-2*.csv")):
        try: parts.append(pd.read_csv(fp, usecols=["create_time","count_toptrader_long_short_ratio","sum_toptrader_long_short_ratio"]))
        except Exception: pass
    df=pd.concat(parts,ignore_index=True)
    a=pd.to_numeric(df["count_toptrader_long_short_ratio"],errors="coerce")
    b=pd.to_numeric(df["sum_toptrader_long_short_ratio"],errors="coerce")
    m=(a>0)&(b>0)&np.isfinite(a)&np.isfinite(b)
    la,lb=np.log(a[m]),np.log(b[m])
    c=np.corrcoef(la,lb)[0,1]
    div=lb-la
    print(f"  {s:10s} n={m.sum():,}  corr(log,log)={c:+.3f}  分歧 sd={div.std():.3f}  "
          f"{'★ 独立轴(分歧项进 v2)' if c<0.9 else '近冗余(分歧项不进)'}")

print("\n[F7-root] BTC 三起最大 OI 跳变的原始帧")
parts=[]
for fp in sorted(glob.glob("/workspace/data/raw/metrics/BTCUSDT-2*.csv")):
    try: parts.append(pd.read_csv(fp, usecols=["create_time","sum_open_interest"]))
    except Exception: pass
df=pd.concat(parts,ignore_index=True)
oi=pd.to_numeric(df["sum_open_interest"],errors="coerce").values
dlo=np.abs(np.diff(np.log(np.where(oi>0,oi,np.nan))))
top=np.argsort(-np.nan_to_num(dlo))[:3]
for i in top:
    print(f"  跳变 {dlo[i]*100:.0f}% @ {df['create_time'].iloc[i+1]}:")
    for j in range(max(0,i-1), min(len(df), i+3)):
        print(f"    {df['create_time'].iloc[j]}  oi={oi[j]:,.0f}")

print("\n═"*35); print("[Y8/Y12] 目标列构建 + Y4 交叉断言")
G=np.load("/workspace/data/ohlcv_grid.npz",allow_pickle=True)
P=np.load("/workspace/data/panel_targets.npz",allow_pickle=True)
R=np.load("/workspace/data/wide_dl_rebuilt32.npz",allow_pickle=True)
C=G["CLOSE"].astype(np.float64); T,N=C.shape
logc=np.log(np.where(C>0,C,np.nan))
MEM=P["MEMBER110"]
# Y4 交叉断言
y4_mine=np.full((T,N),np.nan,np.float32); y4_mine[:-4]=(logc[4:]-logc[:-4]).astype(np.float32)
y4_prod=P["Y4"]
m=MEM&np.isfinite(y4_mine)&np.isfinite(y4_prod)
cc=np.corrcoef(y4_mine[m],y4_prod[m])[0,1]
print(f"  ★ Y4 交叉断言: corr(自建, 生产) = {cc:.6f}  n={m.sum():,}  {'PASS' if cc>0.999 else '★★FAIL — 停, 先找差'}")
assert cc>0.999, "自建 CLOSE 与生产面板 Y4 不一致"
sys.path.insert(0,"/workspace/code")
from multi_asset.data.build_wide_dl import _xsec_residualize
names=[str(x) for x in R["ch_names"]]
bidx=[names.index(b) for b in [str(x) for x in R["baseline_cols"]]]
Xbase=R["CH"][:,:,bidx].astype(np.float64)
out={"ts":P["ts"],"symbols":P["symbols"]}
for H in (8,12):
    Y=np.full((T,N),np.nan,np.float32); Y[:T-H]=(logc[H:]-logc[:-H]).astype(np.float32)
    YR=_xsec_residualize(Y.astype(np.float64),Xbase,MEM)
    CL=np.zeros((T,N),bool); CL[np.arange(0,T,H)]=True; CL=CL&MEM&np.isfinite(Y)
    out[f"Y{H}"]=Y; out[f"YR{H}"]=YR.astype(np.float32); out[f"CL{H}"]=CL
    print(f"  H={H}: Y finite {np.isfinite(Y).mean():.3f}  YR finite {np.isfinite(YR).mean():.3f}  CL 行 {int(CL.any(1).sum())}")
np.savez("/workspace/data/y8y12_sidecar.npz",**out)
h=hashlib.sha256(open("/workspace/data/y8y12_sidecar.npz","rb").read()).hexdigest()[:16]
print(f"saved y8y12_sidecar.npz  sha256[:16]={h}")
