"""F3 路径/持久 + F4 截面结构 特征构建(设计 §1.3; 右端=锚前一完整日, 同 F12 声明).
F3: vr3_60, trendr2_30(带号R²), dist_hi_30, dist_hi_90, updays_30
F4: beta_btc_30, idio_share_30, corr_mkt_30
env: CACHE_IN META_IN OUT_NPY
"""
import os
import numpy as np
import pandas as pd

C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64)
chs = [str(c) for c in C["ch"]]; iR = chs.index("ret5")
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
data = C["data"]; T, NS, _ = data.shape; nD = (T - 1) // 288
# 日收益(逐块扫 ret5 通道)
dret = np.full((nD, NS), np.nan)
for d in range(nD):
    r = np.asarray(data[1 + d * 288: 1 + (d + 1) * 288, :, iR], dtype=np.float32)
    ok = np.isfinite(r)
    s = np.where(ok, r, 0).sum(0)
    dret[d] = np.where(ok.sum(0) >= 144, s, np.nan)
    if (d + 1) % 400 == 0: print(f"day {d+1}/{nD}", flush=True)
D = pd.DataFrame(dret)
cum = D.fillna(0).cumsum().where(D.notna())
tser = pd.Series(np.arange(nD), dtype=float)
F = {}
r3 = D.rolling(3, min_periods=3).sum()
F["vr3_60"] = (r3.rolling(60, min_periods=40).var() / (3 * D.rolling(60, min_periods=40).var() + 1e-12)).values
corr_t = cum.rolling(30, min_periods=20).corr(tser)
F["trendr2_30"] = (corr_t * corr_t.abs()).values
for W in (30, 90):
    F[f"dist_hi_{W}"] = (cum - cum.rolling(W, min_periods=int(W * 0.66)).max()).values
F["updays_30"] = (D.gt(0).rolling(30, min_periods=20).sum() / D.notna().rolling(30, min_periods=20).sum()).values
btc = D[iBTC]
cov_b = D.rolling(30, min_periods=20).cov(btc)
var_b = btc.rolling(30, min_periods=20).var()
F["beta_btc_30"] = cov_b.div(var_b + 1e-12, axis=0).values
corr_b = D.rolling(30, min_periods=20).corr(btc)
F["idio_share_30"] = (1 - corr_b ** 2).values
mkt = D.mean(axis=1)
F["corr_mkt_30"] = D.rolling(30, min_periods=20).corr(mkt).values
COLS = ["vr3_60", "trendr2_30", "dist_hi_30", "dist_hi_90", "updays_30",
        "beta_btc_30", "idio_share_30", "corr_mkt_30"]
DAY = np.stack([F[c] for c in COLS], axis=2).astype(np.float32)
t0 = int(pd.Timestamp("2022-01-01").timestamp())
rows = np.clip((E_ts - t0) // 86400 - 1, -1, nD - 1)
OUT = np.full((len(E_ts), NS, len(COLS)), np.nan, np.float32)
for i, rw in enumerate(rows):
    if rw >= 0: OUT[i] = DAY[rw]
np.save(os.environ["OUT_NPY"] + ".tmp.npy", OUT)
os.replace(os.environ["OUT_NPY"] + ".tmp.npy", os.environ["OUT_NPY"])
np.save(os.environ["OUT_NPY"].replace(".npy", "_cols.npy"), np.array(COLS))
print(f"F34_BUILD_DONE anchors {len(E_ts)} cols {len(COLS)} finite {np.isfinite(OUT).mean():.3f}", flush=True)
