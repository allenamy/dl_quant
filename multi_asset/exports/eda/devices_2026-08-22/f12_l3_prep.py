"""L3 快模型数据整备 @jpline(2026-08-23)。设计 DESIGN_lob_shallow_campaign §6 (L3 v1 规格冻结)。
产物 f8_2026-08-22/data/f12_l3.npz:
  ts5 (T,) 5m 网格; X_lob (T,60,21) = 12带 lnot z + 9 流量(5m 聚合); X_kl (T,60,8) 5m K线通道;
  COND (nA_map) 见 cond_*: 171 列 4h 锚级 ffill 映射表(行索引, 训练时 gather); Y (T,60,4) 前瞻 5m/30m/1h/4h(ret5 和);
  syms60, scol60(829 列号), yr5 (T,) 年份。全部结构因果: X 用 ≤ bar 收盘, Y 用 > 收盘。"""
import os, glob, json, time
import numpy as np
ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
CACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
Z = np.load(CACHE, allow_pickle=True)
CD = Z["data"]; CTS = Z["ts"].astype(np.int64); csyms = [str(s) for s in Z["symbols"]]
log("5m cache", CD.shape)
parts = sorted(glob.glob(f"{OUT}/data/f11_parts/*.npz"))
syms60 = [str(np.load(p, allow_pickle=True)["sym"]) for p in parts]
scol60 = [csyms.index(s) for s in syms60]
NS = len(syms60)
lob_files = {s: f"{ROOT}/lob_bookdepth/npz/{s}.npz" for s in syms60}
# 网格: 取 LOB 时代 5m bars(2023-01 起)
i0 = int(np.searchsorted(CTS, 1672531200))
ts5 = CTS[i0:]; T = len(ts5)
KL = CD[i0:, scol60, :8].astype(np.float32)          # (T,60,8)
R5 = np.nan_to_num(KL[:, :, 0], nan=0.0)
FIN = np.isfinite(CD[i0:, scol60, 0])
# 前瞻 Y: ret5 和 (t+1..t+k)
def fwd(k):
    c = np.cumsum(np.vstack([np.zeros((1, NS), np.float32), R5]), 0)
    o = np.full((T, NS), np.nan, np.float32)
    o[:T - k] = c[1 + k:] - c[1:T - k + 1 + 0]
    o[:T - k][~FIN[:T - k]] = np.nan
    return o
Y = np.stack([fwd(1), fwd(6), fwd(12), fwd(48)], -1)
log("targets done")
# LOB → 5m 流: 每 5m bar 取窗内 30s 行
XL = np.full((T, NS, 21), np.nan, np.float32)
for j, s in enumerate(syms60):
    z = np.load(lob_files[s]); lts = z["ts"].astype(np.int64); L = z["lnot"].astype(np.float32)
    NOT = np.expm1(L); bidN = NOT[:, :6]; askN = NOT[:, 11:5:-1]
    with np.errstate(all="ignore"):
        I = (bidN - askN) / (bidN + askN + 1e-9)          # 距序 5..0.2
        tot = bidN[:, :5].sum(1) + askN[:, :5].sum(1) + 1e-9
        dB = np.vstack([np.zeros((1, 6)), np.diff(bidN, 0 if False else 1, axis=0)])
        dA = np.vstack([np.zeros((1, 6)), np.diff(askN, axis=0)])
        ofi1 = (dB[:, 4] - dA[:, 4]) / tot; ofiI = (dB[:, :5] - dA[:, :5]).sum(1) / tot
        wd = np.minimum(dB[:, 4] + dA[:, 4], 0) / tot
        wda = (np.minimum(dB[:, 4], 0) - np.minimum(dA[:, 4], 0)) / tot
    Lz = np.log1p(NOT)
    ends = np.searchsorted(lts, ts5, side="right")        # 窗末(≤ bar 收盘)
    starts = np.searchsorted(lts, ts5 - 300, side="right")
    ok = (ends > starts) & (ends > 0)
    e1 = np.maximum(ends - 1, 0)
    # 12 带 lnot(bar 末快照, 逐币 z 标准化)
    snap = Lz[e1]; mu = np.nanmean(Lz, 0); sd = np.nanstd(Lz, 0) + 1e-6
    XL[ok, j, :12] = ((snap - mu) / sd)[ok]
    # 9 流量: bar 末失衡 4 + 窗内和 4 + 窗行数
    csum = lambda v: np.concatenate([[0], np.cumsum(np.nan_to_num(v))])
    for ci, v in enumerate((I[:, 4], I[:, 2], I[:, 0], None)):
        if v is not None:
            XL[ok, j, 12 + ci] = v[e1][ok]
    XL[ok, j, 15] = (I[:, 4][e1] - np.where(np.isfinite(I[:, 5][e1]), I[:, 5][e1], I[:, 4][e1]))[ok]  # 近带梯度(02 可得时)
    for ci, v in enumerate((ofi1, ofiI, wd, wda)):
        cs = csum(v)
        XL[ok, j, 16 + ci] = (cs[ends] - cs[starts])[ok]
    XL[ok, j, 20] = (ends - starts)[ok]
    if j % 10 == 0:
        log("lob", j, s)
# 171 列锚级映射: 每 5m bar → 最近 ≤ 的 dlw 锚行号
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64)
amap = np.searchsorted(E_ts, ts5, side="right") - 1        # -1 = 无锚
yr5 = np.array([time.gmtime(int(t)).tm_year for t in ts5], np.int16)
np.savez(f"{OUT}/data/f12_l3.npz", ts5=ts5, X_lob=XL.astype(np.float16), X_kl=KL.astype(np.float16),
         Y=Y.astype(np.float16), amap=amap.astype(np.int32), yr5=yr5,
         syms60=np.array(syms60), scol60=np.array(scol60, np.int32))
log("F12_PREP_DONE", XL.shape, "cover", round(float(np.isfinite(XL[:, :, 0]).mean()), 3))
