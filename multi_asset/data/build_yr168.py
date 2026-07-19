#!/usr/bin/env python3
"""Build Y168/YR168/CL168 (168h weekly slow target) for ARM-S3, EXACT build_wide_dl caliber.

Reuses build_wide_dl._xsec_residualize + wide_factory.build_factors (same 8-BASELINE
standardized-ridge-OLS residual, 2ea686b caliber, no clip). Y168 = forward 168h log-return
from wide_panel_full CLOSE. CL168 = regular 168h-spacing & member & finite. Correctness gate:
reproduce YR4 from the same recipe and require corr>0.999 vs the shipped wide_dl_full YR4.

Output: derived npz wide_dl_full_s3_y168.npz = wide_dl_full (32ch + all keys) + Y168/YR168/CL168,
so ARM-S3 runs --target_horizon 168 --wide_dl_path <this> natively (harness needs YR168/Y168/CL168).
"""
import sys, json, numpy as np
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, M)
from multi_asset.data.build_wide_dl import _xsec_residualize, BASELINE
from multi_asset.data.wide_factory import build_factors

MA = M + "/multi_asset"
PANEL = MA + "/exports/wide_panel_full.npz"
WIDE = MA + "/exports/wide_dl_full.npz"
OUT = MA + "/exports/wide_dl_full_s3_y168.npz"

z = np.load(PANEL, allow_pickle=True)
W = np.load(WIDE, allow_pickle=True)
assert np.array_equal(z["ts"], W["ts"]), "price/panel ts mismatch"
assert list(z["symbols"]) == list(W["symbols"]), "symbols mismatch"

C = z["CLOSE"].astype(np.float64)
logc = np.log(np.where(C > 0, C, np.nan))
T, N = logc.shape
F = build_factors(z)
Xbase = np.stack([F[b][0] for b in BASELINE], axis=2).astype(np.float64)
MEM = W["MEMBER110"]


def fwd(H):
    Y = np.full((T, N), np.nan, np.float32)
    Y[:T - H] = (logc[H:] - logc[:-H]).astype(np.float32)
    return Y


def corr(a, b, m):
    x = a[m] - a[m].mean(); y = b[m] - b[m].mean()
    return float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12))


# ---- correctness gate: reproduce YR4 ----
Y4 = fwd(4)
YR4r = _xsec_residualize(Y4.astype(np.float64), Xbase, MEM)
mv = MEM & np.isfinite(W["YR4"]) & np.isfinite(YR4r)
vcorr = corr(YR4r, W["YR4"].astype(np.float64), mv)
assert vcorr > 0.999, "YR4 reproduction FAILED corr=%.5f -> recipe/Xbase mismatch, do not trust YR168" % vcorr

# ---- build H=168 ----
Y168 = fwd(168)
YR168 = _xsec_residualize(Y168.astype(np.float64), Xbase, MEM).astype(np.float32)
CL168 = np.zeros((T, N), bool)
CL168[np.arange(0, T, 168)] = True
CL168 = CL168 & MEM & np.isfinite(Y168)

out = {k: W[k] for k in W.files}
out["Y168"] = Y168; out["YR168"] = YR168; out["CL168"] = CL168
np.savez_compressed(OUT, **out)

# ---- report ----
dense_cells = int((MEM & np.isfinite(YR168)).sum())              # dense-train footprint
clean_rows = int(CL168.any(1).sum())
import pandas as pd
yr = pd.to_datetime(W["ts"], unit="ms", utc=True).year.to_numpy()
clean_per_year = {int(y): int(CL168[yr == y].any(1).sum()) for y in sorted(set(yr.tolist()))}
rep = {
    "out": OUT, "YR4_repro_corr": round(vcorr, 6),
    "Y168_finite_frac": round(float(np.isfinite(Y168).mean()), 3),
    "YR168_finite_frac": round(float(np.isfinite(YR168).mean()), 3),
    "YR168_std_on_member": round(float(np.nanstd(YR168[MEM])), 5),
    "CL168_clean_anchor_rows_total": clean_rows, "clean_rows_per_year": clean_per_year,
    "dense_train_cells": dense_cells,
    "dense_params_samples": "255k params : %.1fM cells = 1:%.0f" % (dense_cells / 1e6, dense_cells / 255000),
    "embargo_recommend_days": 16, "embargo_reason": "168h horizon + 168h(W=7d) window = 14d min + 2d buffer",
}
json.dump(rep, open(MA + "/exports/eda/yr168_target_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
