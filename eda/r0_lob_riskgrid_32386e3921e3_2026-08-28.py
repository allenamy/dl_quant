"""R0 · 锚间风险网格特征 @jpline(2026-08-28)。派生自归档 f11_lob_features.py(数学逐字复刻),
仅改: 网格=20min(锚间监控历史版), 输入=pod2_evac_2026-08-26/lob_npz(608名, 30s, 2/1-8/23),
输出=每名 20min 特征序列(核心10量 + e1h/e4h EMA)。用法: python r0_lob_riskgrid.py <shard> <nshards>"""
import os, sys, glob, time
import numpy as np
from scipy.signal import lfilter
B = "/mnt/storage/private/work_hsy/pod2_evac_2026-08-26/lob_npz"
OUT = "/mnt/storage/private/work_hsy/r0_riskgrid_2026-08-28"
E_ts = np.arange(1769904000, 1787875200, 1200, dtype=np.int64)  # 2026-02-01 → 2026-08-24, 20min
def ema_irr(vals, ts, hl):
    v = np.asarray(vals, np.float64); ok = np.isfinite(v)
    if ok.sum() < 10: return np.full(len(v), np.nan)
    idx = np.where(ok, np.arange(len(v)), 0); np.maximum.accumulate(idx, out=idx)
    vf = v[idx]; first = np.argmax(ok); vf[:first] = v[ok][0]
    al = 1 - np.exp(-np.log(2) * 30.0 / hl)
    o = lfilter([al], [1, -(1 - al)], vf, zi=[vf[0] * (1 - al)])[0]
    o[:first] = np.nan
    return o
shard, nsh = int(sys.argv[1]), int(sys.argv[2])
os.makedirs(f"{OUT}/parts", exist_ok=True); T0 = time.time()
files = sorted(glob.glob(f"{B}/*.npz"))
for fi, f in enumerate(files):
    if fi % nsh != shard: continue
    sym = os.path.basename(f)[:-4]
    op = f"{OUT}/parts/{sym}.npz"
    if os.path.exists(op): continue
    try:
        z = np.load(f)
        ts = z["ts"].astype(np.int64); L = z["lnot"].astype(np.float32)
        NOT = np.expm1(L)
        bidN = NOT[:, [0, 1, 2, 3, 4, 5]]; askN = NOT[:, [11, 10, 9, 8, 7, 6]]
        with np.errstate(all="ignore"):
            I = (bidN - askN) / (bidN + askN + 1e-9)
            Inear = I[:, 4]
            x5 = np.array([5, 4, 3, 2, 1.0]); xc = x5 - x5.mean(); den = (xc ** 2).sum()
            s_asym = (np.log1p(bidN[:, :5]) * xc).sum(1) / den - (np.log1p(askN[:, :5]) * xc).sum(1) / den
            dB = np.vstack([np.zeros((1, 6)), np.diff(bidN, axis=0)])
            dA = np.vstack([np.zeros((1, 6)), np.diff(askN, axis=0)])
            tot = bidN[:, :5].sum(1) + askN[:, :5].sum(1) + 1e-9
            core = {"Inear": Inear, "s_asym": s_asym,
                    "ofi_near": (dB[:, 4] - dA[:, 4]) / tot,
                    "ofi_int": (dB[:, :5] - dA[:, :5]).sum(1) / tot,
                    "wd": np.minimum(dB[:, 4] + dA[:, 4], 0) / tot,
                    "wd_asym": (np.minimum(dB[:, 4], 0) - np.minimum(dA[:, 4], 0)) / tot,
                    "logtot": np.log1p(tot)}
        cols = {}
        for k, v in core.items(): cols[f"{k}_last"] = v
        for k in ("Inear", "s_asym", "ofi_near", "ofi_int", "wd", "wd_asym"):
            for hl, tag in ((3600, "1h"), (14400, "4h")):
                cols[f"{k}_e{tag}"] = ema_irr(core[k], ts, hl)
        pos = np.searchsorted(ts, E_ts, side="right") - 1
        ok = (pos >= 0) & np.where(pos >= 0, (E_ts - ts[np.maximum(pos, 0)]) <= 3600, False)
        names = sorted(cols)
        FE = np.full((len(E_ts), len(names)), np.nan, np.float32)
        for ci, k in enumerate(names): FE[ok, ci] = cols[k][pos[ok]]
        np.savez_compressed(op, fe=FE, names=np.array(names), E_ts=E_ts, sym=sym)
        print(f"[{time.time()-T0:6.0f}s] {sym} cover={np.isfinite(FE[:,0]).mean():.2f}", flush=True)
    except Exception as e:
        print(f"ERR {sym}: {e}", flush=True)
print("R0_SHARD_DONE", shard, flush=True)
