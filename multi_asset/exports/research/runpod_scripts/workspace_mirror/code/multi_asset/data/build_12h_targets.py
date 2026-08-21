#!/usr/bin/env python3
"""ARM-N1a 12h targets: Y12/YR12/CL12 (derived panel, build_wide_dl caliber, YR4-repro gated)
+ YR12B (full-book residual: YR12 on [king_pred(CL4), s2_pred_cl4]).

12h = king(4h)-S2(24h) 中间甜带. Derived panel wide_dl_full_12h.npz supports --target_horizon 12;
YR12B sidecar (yr12b_target.npz, --target_npz hook format) = N1a fine-tune target.
"""
import sys, json, numpy as np, pandas as pd
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.build_wide_dl import _xsec_residualize, BASELINE
from multi_asset.data.wide_factory import build_factors
MA = REPO + "/multi_asset"

z = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
K = np.load(MA + "/exports/eda/king_pred_panel.npz", allow_pickle=True)
S = np.load(MA + "/exports/eda/s2_pred_panel_cl4.npz", allow_pickle=True)
assert np.array_equal(z["ts"], W["ts"]) and np.array_equal(W["ts"], K["ts"]) and np.array_equal(W["ts"], S["ts"])

logc = np.log(np.where(z["CLOSE"].astype(np.float64) > 0, z["CLOSE"].astype(np.float64), np.nan))
T, N = logc.shape
F = build_factors(z)
Xbase = np.stack([F[b][0] for b in BASELINE], axis=2).astype(np.float64)
MEM = W["MEMBER110"]; ts = W["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
king = K["king_pred"].astype(np.float64); s2 = S["s2_pred"].astype(np.float64); CL4 = W["CL4"]


def fwd(H):
    Y = np.full((T, N), np.nan, np.float32); Y[:T - H] = (logc[H:] - logc[:-H]).astype(np.float32); return Y


def corr(a, b, m):
    x = a[m] - a[m].mean(); y = b[m] - b[m].mean()
    return float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12))


def perts_corr(a, b, msk):
    cs = []
    for t in np.where(msk.any(1))[0]:
        bb = np.where(msk[t] & np.isfinite(b[t]))[0]
        if bb.size < 8:
            continue
        x, y = a[t, bb], b[t, bb]
        if x.std() > 1e-12 and y.std() > 1e-12:
            cs.append(np.corrcoef(x, y)[0, 1])
    return float(np.mean(cs)), float(np.max(np.abs(cs)))


# ---- YR4-repro gate ----
YR4r = _xsec_residualize(fwd(4).astype(np.float64), Xbase, MEM)
mv = MEM & np.isfinite(W["YR4"]) & np.isfinite(YR4r)
vcorr = corr(YR4r, W["YR4"].astype(np.float64), mv)
assert vcorr > 0.999, "YR4 repro FAILED %.5f" % vcorr

# ---- Part 1: Y12/YR12/CL12 -> derived panel ----
Y12 = fwd(12)
YR12 = _xsec_residualize(Y12.astype(np.float64), Xbase, MEM).astype(np.float32)
CL12 = np.zeros((T, N), bool); CL12[np.arange(0, T, 12)] = True
CL12 = CL12 & MEM & np.isfinite(Y12)
out = {k: W[k] for k in W.files}
out["Y12"] = Y12; out["YR12"] = YR12; out["CL12"] = CL12
np.savez_compressed(MA + "/exports/wide_dl_full_12h.npz", **out)

# ---- Part 2: YR12B (residualize YR12 on [king, s2] at CL4) ----
YR12d = YR12.astype(np.float64)
R = np.full((T, N), np.nan, np.float64)
for t in np.where((MEM & CL4 & np.isfinite(YR12d) & np.isfinite(king) & np.isfinite(s2)).any(1))[0]:
    b = np.where(MEM[t] & CL4[t] & np.isfinite(YR12d[t]) & np.isfinite(king[t]) & np.isfinite(s2[t]))[0]
    if b.size < 8:
        continue
    X = np.column_stack([king[t, b], s2[t, b]]); Xd = X - X.mean(0)
    sd = Xd.std(0); sd = np.where(sd > 1e-12, sd, 1.0); Xd = Xd / sd
    y = YR12d[t, b] - YR12d[t, b].mean()
    beta = np.linalg.solve(Xd.T @ Xd + 1e-6 * np.eye(2), Xd.T @ y)
    R[t, b] = y - Xd @ beta
KMASK = np.isfinite(R) & MEM
np.savez_compressed(MA + "/exports/yr12b_target.npz", ts=ts, symbols=W["symbols"],
                    YR4K=R.astype(np.float32), KMASK=KMASK)

am_k, ax_k = perts_corr(R, king, KMASK); am_s, ax_s = perts_corr(R, s2, KMASK)
rep = {"YR4_repro_corr": round(vcorr, 6),
       "Y12_finite": round(float(np.isfinite(Y12).mean()), 3), "YR12_finite": round(float(np.isfinite(YR12).mean()), 3),
       "CL12_clean_rows": int(CL12.any(1).sum()),
       "YR12B_defined_cells": int(KMASK.sum()), "params_samples_255k": "1:%.1f" % (KMASK.sum() / 255000),
       "verify_a_corr_vs_king": {"mean": round(am_k, 6), "absmax": round(ax_k, 5), "PASS": bool(abs(am_k) < 1e-3 and ax_k < 1e-2)},
       "verify_a_corr_vs_S2": {"mean": round(am_s, 6), "absmax": round(ax_s, 5), "PASS": bool(abs(am_s) < 1e-3 and ax_s < 1e-2)},
       "verify_b_corr_vs_YR12": {"value": round(corr(R, YR12d, KMASK), 4), "PASS": bool(corr(R, YR12d, KMASK) > 0.90)},
       "verify_c_2021_cells": {"n": int(np.isfinite(R[yr == 2021]).sum()), "PASS": bool(int(np.isfinite(R[yr == 2021]).sum()) == 0)},
       "cov_by_year": {int(y): int(KMASK[yr == y].sum()) for y in sorted(set(yr.tolist()))}}
json.dump(rep, open(MA + "/exports/eda/yr12_targets_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
