#!/usr/bin/env python3
"""Build full-book residual targets YR4B / YR24B for the two new frontier arms.

YR{H}B = per-ts cross-sectional OLS residual of YR{H} on STANDARDIZED [king_pred, S2_pred].
(funding+zoo already residualized out of YR{H}; king+S2 add the DL legs -> residual over the
full 4-leg book.) Both pred panels are strictly OOS -> causal (same argument as YR4K). Defined
only where BOTH preds exist = CL24 anchors (2022+); NaN elsewhere.

Sidecars in the --target_npz hook format (keys YR4K [content=YR{H}B], KMASK).
Verify: (a) corr(YR{H}B, king)~0 & corr(YR{H}B, S2)~0; (b) corr vs YR{H}; (c) 2021 masked.
"""
import json, numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
K = np.load(MA + "/exports/eda/king_pred_panel.npz", allow_pickle=True)
S = np.load(MA + "/exports/eda/s2_pred_panel_cl4.npz", allow_pickle=True)   # densified CL4
assert np.array_equal(W["ts"], K["ts"]) and np.array_equal(W["ts"], S["ts"])
assert np.array_equal(W["MEMBER110"], K["member"]) and np.array_equal(W["MEMBER110"], S["member"])

ts = W["ts"].astype(np.int64); symbols = W["symbols"]; mem = W["MEMBER110"]
king = K["king_pred"].astype(np.float64); s2 = S["s2_pred"].astype(np.float64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = king.shape


def resid_on_preds(YR, CLH):
    R = np.full((T, N), np.nan, np.float64)
    hours = np.where((mem & CLH & np.isfinite(YR) & np.isfinite(king) & np.isfinite(s2)).any(1))[0]
    for t in hours:
        b = np.where(mem[t] & CLH[t] & np.isfinite(YR[t]) & np.isfinite(king[t]) & np.isfinite(s2[t]))[0]
        if b.size < 8:
            continue
        X = np.column_stack([king[t, b], s2[t, b]])
        Xd = X - X.mean(0)
        sd = Xd.std(0); sd = np.where(sd > 1e-12, sd, 1.0); Xd = Xd / sd
        y = YR[t, b] - YR[t, b].mean()
        XtX = Xd.T @ Xd + 1e-6 * np.eye(2)
        beta = np.linalg.solve(XtX, Xd.T @ y)
        R[t, b] = y - Xd @ beta
    return R


def corr(a, b, m):
    x = a[m] - a[m].mean(); y = b[m] - b[m].mean()
    return float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12))


def perts_corr(a, b, KMASK):
    cs = []
    for t in np.where(KMASK.any(1))[0]:
        bb = np.where(KMASK[t] & np.isfinite(b[t]))[0]
        if bb.size < 8:
            continue
        x = a[t, bb]; y = b[t, bb]
        if x.std() > 1e-12 and y.std() > 1e-12:
            cs.append(np.corrcoef(x, y)[0, 1])
    return float(np.mean(cs)), float(np.max(np.abs(cs)))


report = {}
for H, YRk, Yk, CLk, tag in [(4, "YR4", "Y4", "CL4", "yr4b"), (24, "YR24", "Y24", "CL4", "yr24b")]:
    YR = W[YRk].astype(np.float64); CLH = W[CLk]
    R = resid_on_preds(YR, CLH)
    KMASK = np.isfinite(R) & mem
    # verify
    am_k, ax_k = perts_corr(R, king, KMASK)
    am_s, ax_s = perts_corr(R, s2, KMASK)
    m = KMASK
    b_corr = corr(R, YR, m)
    c_2021 = int(np.isfinite(R[yr == 2021]).sum())
    cov_by_year = {int(y): int(KMASK[yr == y].sum()) for y in sorted(set(yr.tolist()))}
    OUT = MA + "/exports/%s_target.npz" % tag
    np.savez_compressed(OUT, ts=ts, symbols=symbols,
                        YR4K=R.astype(np.float32), KMASK=KMASK)   # hook-format keys (content=YR{H}B)
    report[tag] = {
        "out": OUT, "target": YRk + "B", "H": H, "defined_cells": int(KMASK.sum()),
        "params_samples_255k": "1:%.1f" % (KMASK.sum() / 255000),
        "verify_a_perts_corr_vs_king": {"mean": round(am_k, 6), "absmax": round(ax_k, 5), "PASS": bool(abs(am_k) < 1e-3 and ax_k < 1e-2)},
        "verify_a_perts_corr_vs_S2": {"mean": round(am_s, 6), "absmax": round(ax_s, 5), "PASS": bool(abs(am_s) < 1e-3 and ax_s < 1e-2)},
        "verify_b_corr_vs_YR": {"value": round(b_corr, 4), "PASS": bool(b_corr > 0.90)},
        "verify_c_2021_cells": {"n": c_2021, "PASS": bool(c_2021 == 0)},
        "coverage_by_year": cov_by_year}

json.dump(report, open(MA + "/exports/eda/yr4b_yr24b_report.json", "w"), indent=1)
print(json.dumps(report, indent=1))
