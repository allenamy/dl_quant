#!/usr/bin/env python3
"""Build YR4_kingresid target for ARM-S1 (same-horizon king-residual re-mining).

YR4K = per-ts cross-sectional OLS residual of YR4 on the strictly-OOS king prediction
(0C's king-orthogonal recipe: demean both, beta=(yd.kd)/(kd.kd), resid=yd-beta*kd).
Defined only where king_pred exists (2022+ clean-4h anchors) -> NaN elsewhere (2021 excluded).
Sidecar npz (disk-efficient): ts, symbols, YR4K, KMASK, king_pred. Consumed by the harness
--target_npz hook (input CH stays wide_dl_full_39ch.npz).

Verify: (a) per-ts corr(YR4K, king) ~ 0; (b) corr(YR4K, YR4) ~ 0.95+; (c) 2021 masked.
"""
import json, numpy as np, pandas as pd

M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
W = np.load(M + "/exports/wide_dl_full_39ch.npz", allow_pickle=True)
K = np.load(M + "/exports/eda/king_pred_panel.npz", allow_pickle=True)
OUT = M + "/exports/yr4_kingresid.npz"

assert np.array_equal(W["ts"], K["ts"]) and np.array_equal(W["MEMBER110"], K["member"])
ts = W["ts"].astype(np.int64); symbols = W["symbols"]
YR4 = W["YR4"].astype(np.float64); CL4 = W["CL4"]; mem = W["MEMBER110"]
king = K["king_pred"].astype(np.float64)
T, N = YR4.shape
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()

YR4K = np.full((T, N), np.nan, np.float64)
base_hours = np.where((mem & CL4 & np.isfinite(YR4) & np.isfinite(king)).any(1))[0]
for t in base_hours:
    b = np.where(mem[t] & CL4[t] & np.isfinite(YR4[t]) & np.isfinite(king[t]))[0]
    if b.size < 8:
        continue
    y = YR4[t, b]; k = king[t, b]
    yd = y - y.mean(); kd = k - k.mean()
    denom = float(kd @ kd)
    beta = (yd @ kd) / denom if denom > 1e-12 else 0.0
    YR4K[t, b] = yd - beta * kd

KMASK = np.isfinite(YR4K) & mem                       # king-available residual cells (2022+ clean-4h)

# ---- verify (a) per-ts corr(YR4K, king) ~ 0 ----
acorr = []
for t in base_hours:
    b = np.where(KMASK[t] & np.isfinite(king[t]))[0]
    if b.size < 8:
        continue
    x = YR4K[t, b]; k = king[t, b]
    if x.std() > 1e-12 and k.std() > 1e-12:
        acorr.append(np.corrcoef(x, k)[0, 1])
a_mean = float(np.mean(acorr)); a_absmax = float(np.max(np.abs(acorr)))

# ---- verify (b) corr(YR4K, YR4) over defined cells ----
m = KMASK
xb = YR4K[m]; yb = YR4[m]
xb = xb - xb.mean(); yb = yb - yb.mean()
b_corr = float((xb * yb).sum() / (np.sqrt((xb * xb).sum() * (yb * yb).sum()) + 1e-12))

# ---- verify (c) 2021 masked ----
c_2021 = int(np.isfinite(YR4K[yr == 2021]).sum())
cov_by_year = {int(y): int(KMASK[yr == y].sum()) for y in sorted(set(yr.tolist()))}

np.savez_compressed(OUT, ts=ts, symbols=symbols, YR4K=YR4K.astype(np.float32),
                    KMASK=KMASK, king_pred=king.astype(np.float32))
report = {
    "out": OUT, "recipe": "per-ts OLS residual of YR4 on king_pred (demean+OLS), 0C king-orthogonal caliber",
    "defined_cells": int(KMASK.sum()), "min_members_per_ts": 8,
    "verify_a_perts_corr_YR4K_vs_king": {"mean": round(a_mean, 6), "abs_max": round(a_absmax, 5),
        "PASS": bool(abs(a_mean) < 1e-3 and a_absmax < 1e-2)},
    "verify_b_corr_YR4K_vs_YR4": {"value": round(b_corr, 4), "PASS": bool(b_corr > 0.90)},
    "verify_c_2021_finite_cells": {"n": c_2021, "PASS": bool(c_2021 == 0)},
    "coverage_by_year": cov_by_year,
    "params_samples_note": "255k-param king arch on ~%dk defined cells -> 1:%.1f (healthy)" % (
        KMASK.sum() // 1000, KMASK.sum() / 255000)}
json.dump(report, open(M + "/exports/eda/yr4_kingresid_report.json", "w"), indent=1)
print(json.dumps(report, indent=1))
