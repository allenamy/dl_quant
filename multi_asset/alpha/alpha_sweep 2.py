#!/usr/bin/env python3
"""Batch screen of the Alpha-101 / GTJA-191 formula library at y_3600 (multiple-testing discipline).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

For every formula: standalone xsec rank-IC (pooled over all 3 folds' clean OOS test ts) + EMPIRICAL-
NULL z (permute Y across ts, N perms — the persistent-factor null mean is NOT 0, so z-vs-null is the
honest significance, not IC-vs-0) + per-fold IC (3 disjoint OOS month-blocks = the holdout structure).

★ MULTIPLE-TESTING BAR (pre-registered, ~70 tests → Bonferroni p≈0.05 ⇒ |z|≥3, not 2.5):
   SURVIVOR ⇔ |z| ≥ 3.0  AND  sign-consistent across all 3 folds.
Reports the FULL ranked table (including nulls — the honest distribution). Survivors → 0C factory.

Same panel/grid/Y/CL/folds as the funding & order-flow screens (ohlcv_panel ts == mid_panel grid),
so the alpha ICs are directly comparable to funding_ema (z=−2.50) and signed-flow (z=+0.41).
Usage: PYTHONPATH=. python multi_asset/alpha/alpha_sweep.py [--horizon 3600] [--nperm 20] [--zbar 3.0]
"""
from __future__ import annotations
import argparse, json, os, os.path as p, time
import numpy as np
from scipy.stats import rankdata

from multi_asset.baselines.xsec_ridge import SYMBOLS, FOLDS
from multi_asset.alpha.formulas import build_formulas
from multi_asset.alpha.ops import delay

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
OHLCV = ROOT + "/ohlcv_panel.npz"
MH = ROOT + "/mh_targets_long"
OUT = ROOT + "/eda"
NS = 1_000_000_000


class Panel:
    pass


def load_panel():
    z = np.load(OHLCV, allow_pickle=True)
    P = Panel()
    P.ts = z["ts"].astype(np.int64); P.day = z["day"].astype(np.int64)
    P.open = z["OPEN"].astype(np.float64); P.high = z["HIGH"].astype(np.float64)
    P.low = z["LOW"].astype(np.float64); P.close = z["CLOSE"].astype(np.float64)
    P.vol = z["VOL"].astype(np.float64); P.vwap = z["VWAP"].astype(np.float64)
    P.sf = z["SF"].astype(np.float64)
    P.returns = P.close / delay(P.close, 1) - 1.0
    return P


def build_YCL(ts, day, horizon):
    """y_horizon GLOBAL-fill + CL (≥horizon non-overlap per day) — identical to xsec_ridge_h."""
    nT, nS = len(ts), len(SYMBOLS)
    Y = np.full((nT, nS), np.nan, np.float32)
    for f in sorted(os.listdir(MH)):
        if not (f.endswith(".npz") and f[:-4].isdigit()):
            continue
        z = np.load(p.join(MH, f)); yts = z["ts"].astype(np.int64)
        yv = z[f"y_{horizon}"]; ym = z[f"m_{horizon}"]
        pos = np.searchsorted(yts, ts)
        okc = (pos < len(yts)) & (yts[np.clip(pos, 0, len(yts) - 1)] == ts)
        rows = np.where(okc)[0]; cols = pos[rows]
        for si in range(nS):
            m = ym[si, cols]
            Y[rows[m], si] = yv[si, cols[m]]
    CL = np.zeros((nT, nS), bool); Hns = horizon * NS
    for d in np.unique(day):
        r = np.where(day == d)[0]; last = -(1 << 62); keep = []
        for i in r:
            if int(ts[i]) - last >= Hns:
                keep.append(i); last = int(ts[i])
        if keep:
            CL[np.array(keep)] = True
    return Y, CL


def xsdemean_rows(Y, rowmask):
    out = np.full_like(Y, np.nan)
    for i in np.where(rowmask)[0]:
        row = Y[i]; v = np.isfinite(row)
        if v.sum() >= 5:
            out[i, v] = row[v] - row[v].mean()
    return out


def _ic_over_rows(Xf, Yr, rows, CL):
    """Mean xsec rank-IC of one factor over the given ts rows (clean only)."""
    ics = []
    for i in rows:
        v = CL[i] & np.isfinite(Xf[i]) & np.isfinite(Yr[i])
        if v.sum() >= 5:
            ic = np.corrcoef(rankdata(Xf[i, v]), rankdata(Yr[i, v]))[0, 1]
            if np.isfinite(ic):
                ics.append(ic)
    return float(np.mean(ics)) if ics else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=3600)
    ap.add_argument("--nperm", type=int, default=20)
    ap.add_argument("--zbar", type=float, default=3.0)
    a = ap.parse_args()
    t0 = time.time()

    P = load_panel()
    Y, CL = build_YCL(P.ts, P.day, a.horizon)
    uniq = np.unique(P.day)
    # all-fold OOS test days + per-fold masks
    te_days_all, fold_masks = set(), []
    for fold in FOLDS:
        te0, te1 = fold["te"]
        fd = set(uniq[te0:te1].tolist()) if te1 <= len(uniq) else set()
        te_days_all |= fd
        fold_masks.append(np.isin(P.day, list(fd)))
    tem = np.isin(P.day, list(te_days_all))
    test_rows = np.where(tem)[0]
    Yr = xsdemean_rows(Y, tem)
    print(f"[sweep] panel nT={len(P.ts)} nS={len(SYMBOLS)} test_ts={len(test_rows)} "
          f"horizon={a.horizon} building formulas...", flush=True)

    F = build_formulas(P)
    names = list(F.keys())
    print(f"[sweep] {len(names)} formulas built in {(time.time()-t0)/60:.1f}min; screening...", flush=True)

    # real pooled IC + per-fold IC
    real, perfold = {}, {}
    for nm in names:
        Xf = np.asarray(F[nm], dtype=np.float64)
        if Xf.shape != Y.shape:
            real[nm] = np.nan; perfold[nm] = [np.nan] * len(FOLDS); continue
        real[nm] = _ic_over_rows(Xf, Yr, test_rows, CL)
        perfold[nm] = [_ic_over_rows(Xf, Yr, np.where(fm)[0], CL) for fm in fold_masks]
    print(f"[sweep] real ICs done {(time.time()-t0)/60:.1f}min; {a.nperm}-perm empirical null...", flush=True)

    # empirical null: permute Y across ts, recompute pooled IC per factor
    rng = np.random.default_rng(0)
    null = {nm: [] for nm in names}
    for pi in range(a.nperm):
        Yp = Y[rng.permutation(len(Y))]
        Ypr = xsdemean_rows(Yp, tem)
        for nm in names:
            Xf = np.asarray(F[nm], dtype=np.float64)
            if Xf.shape == Y.shape:
                null[nm].append(_ic_over_rows(Xf, Ypr, test_rows, CL))
        if (pi + 1) % 5 == 0:
            print(f"    null perm {pi+1}/{a.nperm} {(time.time()-t0)/60:.1f}min", flush=True)

    rows = []
    for nm in names:
        arr = np.array([x for x in null[nm] if np.isfinite(x)])
        mu = float(arr.mean()) if len(arr) else np.nan
        sd = float(arr.std()) if len(arr) else np.nan
        iv = real[nm]
        z = (iv - mu) / (sd + 1e-9) if np.isfinite(iv) and np.isfinite(mu) else np.nan
        pf = perfold[nm]
        signs = set(int(np.sign(x)) for x in pf if np.isfinite(x) and x != 0)
        consistent = len(signs) == 1
        survivor = np.isfinite(z) and abs(z) >= a.zbar and consistent
        rows.append(dict(name=nm, ic=iv, null_mu=mu, null_sd=sd, z=z,
                         perfold=[None if not np.isfinite(x) else round(x, 4) for x in pf],
                         sign_consistent=consistent, survivor=bool(survivor)))
    rows.sort(key=lambda r: (-abs(r["z"]) if np.isfinite(r["z"]) else 0))

    os.makedirs(OUT, exist_ok=True)
    res = dict(analysis="alpha101_gtja191_sweep", horizon=a.horizon, nperm=a.nperm, zbar=a.zbar,
               n_formulas=len(names), n_survivors=sum(r["survivor"] for r in rows),
               vs_funding_ema_z=-2.50, table=rows)
    json.dump(res, open(p.join(OUT, f"alpha_sweep_h{a.horizon}.json"), "w"), indent=2, default=str)

    print(f"\n[sweep] {len(names)} formulas | {res['n_survivors']} survivors (|z|≥{a.zbar} & sign-consistent) "
          f"| {(time.time()-t0)/60:.1f}min\n")
    print(f"{'formula':14s} {'IC':>8s} {'null_mu':>8s} {'z':>7s}  {'perfold':>26s}  surv")
    for r in rows:
        pf = "/".join(f"{x:+.3f}" if x is not None else " None " for x in r["perfold"])
        ics = f"{r['ic']:+.4f}" if np.isfinite(r["ic"]) else "  NaN "
        zs = f"{r['z']:+.2f}" if np.isfinite(r["z"]) else "  NaN "
        print(f"{r['name']:14s} {ics:>8s} {r['null_mu']:>+8.4f} {zs:>7s}  {pf:>26s}  {'★' if r['survivor'] else ''}")
    print(f"\n-> {OUT}/alpha_sweep_h{a.horizon}.json")


if __name__ == "__main__":
    main()
