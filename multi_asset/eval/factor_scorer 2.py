"""Factor-factory scorer — multi-asset v2 (1h cross-sectional L/S). Standalone, reusable, CPU-only.

Extracts the per-timestamp cross-sectional Spearman rank-IC (the signal the L/S book monetises;
same operator as backtest_longshort.py) into a reusable scorer, and adds the metrics the factor
pipeline needs: IC-IR, IC t-stat, breadth, IC-decay (entry-delay), and — the EDGE metric — the
INCREMENTAL orthogonal IC on the commoditized-baseline residual.

Consumes the panel_ref format: ts[T], day[T], Y[T,S] (forward return), CL[T,S] (clean ≥H non-overlap
mask), symbols[S]. A "factor" or a "baseline pred" is any [T,S] float array aligned to the panel.

================================ 5-GATE FACTOR PIPELINE (design) ================================
A factor is ACCEPTED into the book only if it clears all five, walk-forward / OOS, sign pre-registered:
  (a) xs-IC / IR      — mean per-ts cross-sectional rank-IC + IC-IR (=meanIC/stdIC·√n_ts) + t-stat +
                        %positive-ts + breadth.  GATE: |IC-IR| ≥ 0.3 AND sign-stable across folds.
  (b) INCREMENTAL IC  — rank-IC of the factor vs the BASELINE-RESIDUAL of Y (per-ts, Y minus its
                        cross-sectional OLS projection on the baseline preds). THE EDGE METRIC = what
                        the factor adds beyond the commoditized baseline.  GATE: incr-IC-IR ≥ 0.3
                        (a factor with high raw IC but ~0 incremental IC is already priced in — REJECT).
  (c) orthogonality   — max |per-ts rank-corr| vs each already-accepted factor.  GATE: |corr| < 0.7
                        (not a near-duplicate of an existing factor).
  (d) walk-forward Ridge — ΔP (per-day-CLEAN Pearson) from adding the factor to the panel cross-sectional
                        Ridge, expanding-window OOS, per-fold sign-consistent.  GATE: ΔP ≥ +0.003. [downstream]
  (e) net-cost L/S    — Δ net-Sharpe / Δ break-even-per-side from adding the factor to the L/S book
                        (backtest_longshort / ls_gate).  GATE: improves net-of-cost economics. [downstream]
Every a/b number must survive a within-ts SHUFFLE-NULL (permute the factor across assets → IC ≈ 0).
This module implements (a),(b),(c) + IC-decay + the null; (d),(e) are the downstream Ridge / L/S hooks.
"""
from __future__ import annotations
import argparse, glob, json, os.path as op
import numpy as np
from scipy.stats import rankdata

MIN_ASSETS = 5


def _ric(f, y):
    """Spearman rank-IC = Pearson corr of average-ranks. ~10x faster than scipy spearmanr in a hot loop
    (validated bit-identical to spearmanr to <1e-9 on the panel cross-check)."""
    rf = rankdata(f); ry = rankdata(y)
    rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum())
    return float((rf * ry).sum() / d) if d > 1e-12 else np.nan


# ----------------------------- core cross-sectional IC -----------------------------
def _perts_ic(F, Y, CL, min_assets=MIN_ASSETS):
    """Per-timestamp cross-sectional Spearman rank-IC of factor F[T,S] vs forward return Y[T,S],
    over the clean & jointly-valid assets. Returns (ic_array, breadth_array) over usable rows."""
    T = F.shape[0]; ics = []; brd = []
    for t in range(T):
        v = CL[t] & np.isfinite(F[t]) & np.isfinite(Y[t])
        nv = int(v.sum())
        if nv < min_assets:
            continue
        f = F[t, v]; y = Y[t, v]
        if np.std(f) < 1e-12 or np.std(y) < 1e-12:
            continue
        ic = _ric(f, y)
        if np.isfinite(ic):
            ics.append(ic); brd.append(nv)
    return np.array(ics), np.array(brd)


def ic_summary(ics, brd, label=""):
    if len(ics) == 0:
        return dict(label=label, n_ts=0, mean_ic=np.nan, ic_ir=np.nan, tstat=np.nan, pos_frac=np.nan, breadth=np.nan)
    m, s, n = float(ics.mean()), float(ics.std()), len(ics)
    ir = m / s * np.sqrt(n) if s > 1e-12 else np.nan          # IC-IR (info ratio of the IC series)
    return dict(label=label, n_ts=n, mean_ic=round(m, 4), ic_std=round(s, 4),
                ic_ir=round(float(ir), 3) if np.isfinite(ir) else None,
                tstat=round(float(m / (s / np.sqrt(n))), 2) if s > 1e-12 else None,
                pos_frac=round(float((ics > 0).mean()), 3), breadth=round(float(brd.mean()), 1))


# ----------------------------- (b) incremental orthogonal IC (the edge metric) -----------------------------
def incremental_ic(F, BASE, Y, CL, min_assets=MIN_ASSETS):
    """Rank-IC of the factor vs the baseline-RESIDUAL of Y: per-ts, residualise Y against the baseline
    (Y_resid = Y − β̂·BASE − α̂, cross-sectional OLS), then spearman(F, Y_resid). Isolates the info the
    factor adds BEYOND the baseline. (Baseline is de-meaned/scaled per-ts inside the OLS.)"""
    T = F.shape[0]; ics = []; brd = []
    for t in range(T):
        v = CL[t] & np.isfinite(F[t]) & np.isfinite(Y[t]) & np.isfinite(BASE[t])
        if v.sum() < min_assets:
            continue
        f = F[t, v]; y = Y[t, v]; b = BASE[t, v]
        if np.std(b) < 1e-12:
            yres = y - y.mean()
        else:
            beta = np.cov(y, b)[0, 1] / np.var(b)
            yres = y - (beta * (b - b.mean()) + y.mean())     # residual of Y orthogonal to baseline
        if np.std(f) < 1e-12 or np.std(yres) < 1e-12:
            continue
        ic = _ric(f, yres)
        if np.isfinite(ic):
            ics.append(ic); brd.append(int(v.sum()))
    return np.array(ics), np.array(brd)


# ----------------------------- (c) factor-factor orthogonality -----------------------------
def factor_corr(FA, FB, CL, min_assets=MIN_ASSETS):
    """Mean per-ts cross-sectional rank-corr between two factors (dup check)."""
    T = FA.shape[0]; cs = []
    for t in range(T):
        v = CL[t] & np.isfinite(FA[t]) & np.isfinite(FB[t])
        if v.sum() < min_assets:
            continue
        a = FA[t, v]; b = FB[t, v]
        if np.std(a) < 1e-12 or np.std(b) < 1e-12:
            continue
        c = _ric(a, b)
        if np.isfinite(c):
            cs.append(c)
    return round(float(np.mean(cs)), 3) if cs else np.nan


# ----------------------------- IC-decay (entry-delay) -----------------------------
def ic_decay(F, Y, CL, lags=(0, 1, 2, 4, 8), min_assets=MIN_ASSETS):
    """Entry-delay decay: IC of F at clean-row k vs Y at clean-row k+L (act L rebalance-periods late).
    Shows how fast the factor's edge decays with latency — directly relevant to net-cost tradeability."""
    rows = [t for t in range(F.shape[0]) if (CL[t] & np.isfinite(F[t]) & np.isfinite(Y[t])).sum() >= min_assets]
    rows = np.array(rows); out = {}
    for L in lags:
        ics = []
        for k in range(len(rows) - L):
            t0, t1 = rows[k], rows[k + L]
            v = CL[t0] & CL[t1] & np.isfinite(F[t0]) & np.isfinite(Y[t1])
            if v.sum() < min_assets:
                continue
            f = F[t0, v]; y = Y[t1, v]
            if np.std(f) < 1e-12 or np.std(y) < 1e-12:
                continue
            ic = _ric(f, y)
            if np.isfinite(ic):
                ics.append(ic)
        out[L] = round(float(np.mean(ics)), 4) if ics else None
    return out


# ----------------------------- shuffle-null -----------------------------
def shuffle_null(F, Y, CL, n=20, seed=0, min_assets=MIN_ASSETS):
    """Permute the factor ACROSS assets within each ts → cross-sectional IC must collapse to ~0.
    Returns (null_mean, null_std, real_mean, z)."""
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n):
        Fs = F.copy()
        for t in range(F.shape[0]):
            v = np.where(CL[t] & np.isfinite(F[t]))[0]
            if len(v) >= min_assets:
                Fs[t, v] = F[t, v[rng.permutation(len(v))]]
        ic, _ = _perts_ic(Fs, Y, CL, min_assets)
        if len(ic): means.append(ic.mean())
    real, _ = _perts_ic(F, Y, CL, min_assets)
    nm, ns = float(np.mean(means)), float(np.std(means) + 1e-12)
    return dict(null_mean=round(nm, 4), null_std=round(ns, 4), real_mean=round(float(real.mean()), 4),
                z=round((float(real.mean()) - nm) / ns, 2))


# ----------------------------- top-level factor score (gates a + decay + null) -----------------------------
def score_factor(F, Y, CL, base=None, existing=None, label="factor", do_null=True):
    ics, brd = _perts_ic(F, Y, CL)
    out = dict(gate_a=ic_summary(ics, brd, label), ic_decay=ic_decay(F, Y, CL))
    if base is not None:
        bics, bbrd = incremental_ic(F, base, Y, CL)
        out["gate_b_incremental"] = ic_summary(bics, bbrd, "incremental_vs_baseline")
    if existing:
        out["gate_c_orthogonality"] = {nm: factor_corr(F, EF, CL) for nm, EF in existing.items()}
    if do_null:
        out["shuffle_null"] = shuffle_null(F, Y, CL)
    return out


# ----------------------------- panel / preds loader -----------------------------
def load_panel(tag, export):
    d = op.join(export, tag)
    ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    Y, CL = ref["Y"].astype(np.float64), ref["CL"].astype(bool)
    T, S = Y.shape
    pred = np.full((T, S), np.nan, np.float64)
    for f in sorted(glob.glob(op.join(d, "fold_*_preds.npz"))):
        z = np.load(f); pred[z["te_rows"]] = z["pred"][z["te_rows"]]
    return dict(ts=ref["ts"], day=ref["day"], Y=Y, CL=CL, pred=pred, symbols=[str(s) for s in ref["symbols"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True); ap.add_argument("--label", default="baseline_pred")
    ap.add_argument("--export", default="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train")
    a = ap.parse_args()
    P = load_panel(a.tag, a.export)
    # self-demo: score the baseline pred as if it were a factor (gate a + decay + null)
    out = score_factor(P["pred"], P["Y"], P["CL"], label=a.label, do_null=True)
    print(json.dumps(out, indent=2))
    print("DONE_FACTOR_SCORER")


if __name__ == "__main__":
    main()
