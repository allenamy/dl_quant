"""F1+F2 特征构建(设计稿 §1.3, 判据先冻于 §1.4): 从 cache450 的 5m bar 造日频充分统计 → 滚动窗因子.
F1 流动性/摩擦: amihud_7/30, roll_30, zeroret_7/30, volconc_7, avgsz_z30
F2 高阶矩/分布: rskew_7/30, rkurt_30, maxday_30, semiv_30, udvol_30
右端 = 锚所在日的前一【完整】日(严格 ≤t, 慢窗牺牲 <24h 新鲜度, 声明于 provenance).
env: CACHE_IN META_IN OUT_NPY
"""
import os, sys, time
import numpy as np
import pandas as pd

C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64)
ts = C["ts"]; data = C["data"]; chs = [str(c) for c in C["ch"]]
iR, iQV, iSZ = chs.index("ret5"), chs.index("log_qv"), chs.index("log_avgsz")
T, NS, _ = data.shape
nD = (T - 1) // 288
print(f"T {T} syms {NS} days {nD}", flush=True)

# 逐日充分统计(float64 累计, 防 float16 精度)
S = {k: np.zeros((nD, NS)) for k in
     ("n", "sr", "sr2", "sr3", "sr4", "sr2dn", "zero", "qv", "qvup", "qvdn", "sxy", "npair", "sz", "szn")}
for d in range(nD):
    blk = np.asarray(data[1 + d * 288: 1 + (d + 1) * 288], dtype=np.float32)  # (288, NS, 7)
    r = blk[:, :, iR]; ok = np.isfinite(r)
    rz = np.where(ok, r, 0.0)
    qv = np.where(np.isfinite(blk[:, :, iQV]), np.expm1(blk[:, :, iQV].astype(np.float64)), 0.0)
    S["n"][d] = ok.sum(0); S["sr"][d] = rz.sum(0)
    S["sr2"][d] = (rz ** 2).sum(0); S["sr3"][d] = (rz ** 3).sum(0); S["sr4"][d] = (rz ** 4).sum(0)
    S["sr2dn"][d] = np.where(rz < 0, rz ** 2, 0).sum(0)
    S["zero"][d] = (ok & (np.abs(r) < 1e-5)).sum(0)
    S["qv"][d] = qv.sum(0)
    S["qvup"][d] = np.where(rz > 0, qv, 0).sum(0); S["qvdn"][d] = np.where(rz < 0, qv, 0).sum(0)
    x, y = rz[1:], rz[:-1]; pok = ok[1:] & ok[:-1]
    S["sxy"][d] = np.where(pok, x * y, 0).sum(0); S["npair"][d] = pok.sum(0)
    szv = blk[:, :, iSZ]; szok = np.isfinite(szv)
    S["sz"][d] = np.where(szok, szv, 0).sum(0); S["szn"][d] = szok.sum(0)
    if (d + 1) % 300 == 0: print(f"day {d+1}/{nD}", flush=True)

def wsum(a, W):
    c = np.cumsum(a, 0); out = np.full_like(a, np.nan)
    out[W - 1:] = c[W - 1:] - np.r_[np.zeros((1, a.shape[1])), c[:-W]][: a.shape[0] - W + 1]
    return out

dret = S["sr"]; dsz = np.where(S["szn"] > 0, S["sz"] / np.maximum(S["szn"], 1), np.nan)
dilliq = np.abs(dret) / (S["qv"] + 1.0)
F = {}
for W in (7, 30):
    nW = wsum(S["n"], W); minok = nW >= W * 288 * 0.5
    F[f"amihud_{W}"] = np.where(minok, wsum(dilliq, W) / W, np.nan)
    F[f"zeroret_{W}"] = np.where(minok, wsum(S["zero"], W) / np.maximum(nW, 1), np.nan)
# roll_30: pair 自协方差
np30, sxy30 = wsum(S["npair"], 30), wsum(S["sxy"], 30)
sx30 = wsum(S["sr"], 30)  # 近似: pair 端点和 ≈ 全和(差两端点, 30d 上可忽略)
mokr = np30 >= 30 * 288 * 0.5
cov = sxy30 / np.maximum(np30, 1) - (sx30 / np.maximum(wsum(S["n"], 30), 1)) ** 2
F["roll_30"] = np.where(mokr, 2 * np.sqrt(np.maximum(-cov, 0)), np.nan)
# volconc_7: 日 qv 份额 HHI
qv7 = wsum(S["qv"], 7)
hh = np.full_like(qv7, np.nan)
for d in range(6, nD):
    w = S["qv"][d - 6: d + 1]; tot = w.sum(0)
    hh[d] = np.where(tot > 0, (w ** 2).sum(0) / np.maximum(tot, 1e-9) ** 2, np.nan)
F["volconc_7"] = hh
# avgsz_z30
szdf = pd.DataFrame(dsz)
F["avgsz_z30"] = ((szdf - szdf.rolling(30, min_periods=20).mean()) /
                  (szdf.rolling(30, min_periods=20).std() + 1e-9)).values
# F2 矩族
for W in (7, 30):
    n = wsum(S["n"], W); m1 = wsum(S["sr"], W) / np.maximum(n, 1)
    m2 = wsum(S["sr2"], W) / np.maximum(n, 1) - m1 ** 2
    m3 = wsum(S["sr3"], W) / np.maximum(n, 1) - 3 * m1 * m2 - m1 ** 3
    ok = (n >= W * 288 * 0.5) & (m2 > 1e-12)
    F[f"rskew_{W}"] = np.where(ok, m3 / np.maximum(m2, 1e-12) ** 1.5, np.nan)
    if W == 30:
        m4 = wsum(S["sr4"], W) / np.maximum(n, 1) - 4 * m1 * m3 - 6 * m1 ** 2 * m2 - m1 ** 4
        F["rkurt_30"] = np.where(ok, m4 / np.maximum(m2, 1e-12) ** 2 - 3, np.nan)
        F["semiv_30"] = np.where(ok, wsum(S["sr2dn"], W) / np.maximum(wsum(S["sr2"], W), 1e-12), np.nan)
        qup, qdn = wsum(S["qvup"], W), wsum(S["qvdn"], W)
        F["udvol_30"] = np.where(ok, (qup - qdn) / np.maximum(qup + qdn, 1e-9), np.nan)
ddf = pd.DataFrame(dret)
F["maxday_30"] = (ddf.rolling(30, min_periods=20).max() /
                  (ddf.rolling(30, min_periods=20).std() + 1e-9)).values
COLS = ["amihud_7", "amihud_30", "roll_30", "zeroret_7", "zeroret_30", "volconc_7", "avgsz_z30",
        "rskew_7", "rskew_30", "rkurt_30", "maxday_30", "semiv_30", "udvol_30"]
DAY = np.stack([F[c] for c in COLS], axis=2)  # (nD, NS, 13)
# 锚映射: 锚所在日的前一完整日
t0 = int(pd.Timestamp("2022-01-01").timestamp())
rows = np.clip((E_ts - t0) // 86400 - 1, -1, nD - 1)
OUT = np.full((len(E_ts), NS, len(COLS)), np.nan, np.float32)
for i, rw in enumerate(rows):
    if rw >= 0: OUT[i] = DAY[rw]
np.save(os.environ["OUT_NPY"] + ".tmp.npy", OUT)
os.replace(os.environ["OUT_NPY"] + ".tmp.npy", os.environ["OUT_NPY"])
np.save(os.environ["OUT_NPY"].replace(".npy", "_cols.npy"), np.array(COLS))
print(f"F12_BUILD_DONE anchors {len(E_ts)} cols {len(COLS)} finite {np.isfinite(OUT).mean():.3f}", flush=True)
