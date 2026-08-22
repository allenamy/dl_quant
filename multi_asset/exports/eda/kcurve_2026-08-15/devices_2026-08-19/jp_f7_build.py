"""F7 定向改造族(根因驱动: P1 降方差×3窗 / P2 慢带≥90d / P3 树够不到+吃宽度):
G1 稳定化二阶: corr_pv_90, rank_mom_d90, rank_std_90, vr3_180
G2 自史分位(ts_rank 机制): mom_z_1y, rvol_z_1y, illiq_z_1y
G3 非对称耦合: beta_asym_90(上行β−下行β), sharpe_mom_90, corr_stab_90
env: CACHE_IN META_IN OUT_NPY
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import rankdata
C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64)
chs = [str(c) for c in C["ch"]]; iR, iQV = chs.index("ret5"), chs.index("log_qv")
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
data = C["data"]; T, NS, _ = data.shape; nD = (T - 1) // 288
dret = np.full((nD, NS), np.nan); dqv = np.full((nD, NS), np.nan)
for d in range(nD):
    blk = np.asarray(data[1 + d * 288: 1 + (d + 1) * 288][:, :, [iR, iQV]], dtype=np.float32)
    r, q = blk[:, :, 0], blk[:, :, 1]
    ok = np.isfinite(r)
    dret[d] = np.where(ok.sum(0) >= 144, np.where(ok, r, 0).sum(0), np.nan)
    qo = np.isfinite(q)
    dqv[d] = np.where(qo.sum(0) >= 144, np.where(qo, np.expm1(q.astype(np.float64)), 0).sum(0), np.nan)
    if (d + 1) % 400 == 0: print(f"day {d+1}/{nD}", flush=True)
np.savez_compressed(os.path.dirname(os.environ["OUT_NPY"]) + "/daily_base.npz", dret=dret, dqv=dqv)
D = pd.DataFrame(dret)
mom30 = D.rolling(30, min_periods=20).sum()
rk_mom = np.full((nD, NS), np.nan)
for d in range(nD):
    v = mom30.values[d]; ok = np.isfinite(v)
    if ok.sum() > 5: rk_mom[d, ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
RK = pd.DataFrame(rk_mom)
dlq = pd.DataFrame(np.log1p(dqv)).diff()
F = {}
F["corr_pv_90"] = D.rolling(90, min_periods=60).corr(dlq).values
F["rank_mom_d90"] = (RK - RK.shift(90)).values
F["rank_std_90"] = RK.rolling(90, min_periods=60).std().values
r3 = D.rolling(3, min_periods=3).sum()
F["vr3_180"] = (r3.rolling(180, min_periods=120).var() / (3 * D.rolling(180, min_periods=120).var() + 1e-12)).values
rvol30 = D.rolling(30, min_periods=20).std()
illiq30 = (D.abs() / (pd.DataFrame(dqv) + 1)).rolling(30, min_periods=20).mean()
for nm, S in (("mom", mom30), ("rvol", rvol30), ("illiq", illiq30)):
    m = S.rolling(365, min_periods=120).mean(); sd = S.rolling(365, min_periods=120).std()
    F[f"{nm}_z_1y"] = ((S - m) / (sd + 1e-12)).clip(-5, 5).values
btc = D[iBTC]
up = (btc > 0).astype(float); dn = (btc < 0).astype(float)
def beta_side(mask):
    num = D.mul(btc * mask, axis=0).rolling(90, min_periods=60).sum()
    den = (btc ** 2 * mask).rolling(90, min_periods=60).sum()
    return num.div(den + 1e-12, axis=0)
F["beta_asym_90"] = (beta_side(up) - beta_side(dn)).values
F["sharpe_mom_90"] = (D.rolling(90, min_periods=60).sum() / (D.rolling(90, min_periods=60).std() * np.sqrt(90) + 1e-12)).values
c30 = D.rolling(30, min_periods=20).corr(btc)
F["corr_stab_90"] = c30.rolling(90, min_periods=60).std().values
COLS = ["corr_pv_90", "rank_mom_d90", "rank_std_90", "vr3_180", "mom_z_1y", "rvol_z_1y", "illiq_z_1y",
        "beta_asym_90", "sharpe_mom_90", "corr_stab_90"]
DAY = np.stack([F[c] for c in COLS], axis=2).astype(np.float32)
t0 = int(pd.Timestamp("2022-01-01").timestamp())
rows = np.clip((E_ts - t0) // 86400 - 1, -1, nD - 1)
OUT = np.full((len(E_ts), NS, len(COLS)), np.nan, np.float32)
for i, rw in enumerate(rows):
    if rw >= 0: OUT[i] = DAY[rw]
np.save(os.environ["OUT_NPY"] + ".tmp.npy", OUT)
os.replace(os.environ["OUT_NPY"] + ".tmp.npy", os.environ["OUT_NPY"])
np.save(os.environ["OUT_NPY"].replace(".npy", "_cols.npy"), np.array(COLS))
print(f"F7_BUILD_DONE anchors {len(E_ts)} cols {len(COLS)} finite {np.isfinite(OUT).mean():.3f}", flush=True)
