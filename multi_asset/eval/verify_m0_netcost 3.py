"""INDEPENDENT two-person verification of 0C's replay-reversal finding (2026-07-10):
is M0 net-cost L/S tradeable ONLY in 2025 (net-negative 2023/2024)? Uses the megacap-style
backtest_longshort engine (rank_weights + EMA-hold turnover + net-of-cost), NOT 0C's
m0_replay_score.py — a genuinely separate harness. Per-year, per-signal (M0 / funding / blend),
full-rebalance (alpha=1) + EMA-hold (alpha=0.02), cost 5 bps/side. Plus the persistence read
(cross-sectional weight autocorr w_t vs w_{t-1}) — 0C's mechanism claim.

Run: PYTHONPATH=. python multi_asset/eval/verify_m0_netcost.py
"""
from __future__ import annotations
import glob
import os.path as p
import numpy as np
from multi_asset.eval.backtest_longshort import rank_weights

EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
MIN_ASSETS = 5
COST = 5.0            # bps/side
SEC_PER_YEAR = 365 * 24 * 3600


def load_pred(tag):
    d = p.join(EXPORT, tag)
    ref = np.load(p.join(d, "panel_ref.npz"), allow_pickle=True)
    ts, day, Y, CL = ref["ts"], ref["day"], ref["Y"], ref["CL"]
    T, S = Y.shape
    pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(p.join(d, "fold_*_preds.npz"))):
        z = np.load(f, allow_pickle=True)
        rows = z["te_rows"]
        pred[rows] = z["pred"][rows]
    return ts, day, Y, CL, pred


def _xz(v, idx):
    x = v[idx]; m = x.mean(); s = x.std()
    return (x - m) / s if s > 1e-12 else x * 0.0


def per_year_netcost(day, Y, CL, sig, blend_sig=None, label=""):
    """Build per-clean-period weights on the >=3600 CL grid; return per-year net-Sh
    (full + EMA a=0.02) + persistence (weight autocorr)."""
    T, S = Y.shape
    rows = [t for t in range(T)
            if (CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])).sum() >= MIN_ASSETS]
    W = np.zeros((len(rows), S)); G = np.zeros(len(rows)); yr = np.zeros(len(rows), int)
    tsr = []
    for i, t in enumerate(rows):
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])
        idx = np.where(v)[0]
        if blend_sig is None:
            sc = sig[t, idx]
        else:                                    # equal-risk z-blend
            sc = _xz(sig[t], idx) + _xz(blend_sig[t], idx)
        w = np.zeros(S); w[idx] = rank_weights(sc)
        W[i] = w; G[i] = float((w * np.where(v, Y[t], 0.0)).sum()); yr[i] = day[t] // 10000
    # cadence for annualization (median consecutive clean gap, in periods=1 -> use count/yr)
    def sharpe(net, mask):
        x = net[mask]
        return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan
    out = {}
    for a in (1.0, 0.02):
        Wh = W.copy()
        if a < 1.0:
            for i in range(1, len(Wh)):
                Wh[i] = a * W[i] + (1 - a) * Wh[i - 1]
        # gross under held weights + turnover
        gh = (Wh * np.where(np.isfinite(Y[rows]), Y[rows], 0.0)).sum(1)
        turn = np.zeros(len(Wh)); turn[1:] = np.abs(Wh[1:] - Wh[:-1]).sum(1)
        net = gh - COST * 1e-4 * turn
        for y in (2023, 2024, 2025):
            out[(a, y)] = (sharpe(net, yr == y), float(turn[yr == y].mean()))
    # persistence: cross-sectional weight autocorr per year (full-turnover target weights)
    persist = {}
    for y in (2023, 2024, 2025):
        ii = np.where(yr == y)[0]; ii = ii[ii > 0]
        cs = [np.corrcoef(W[i], W[i - 1])[0, 1] for i in ii if np.std(W[i]) > 0 and np.std(W[i - 1]) > 0]
        persist[y] = float(np.nanmean(cs)) if cs else np.nan
    print(f"\n=== {label} (n={len(rows)} clean periods, cost {COST}bps/side) ===")
    print(f"{'year':>6s} {'netSh_full':>11s} {'netSh_EMA.02':>13s} {'turn_full':>10s} {'turn_EMA':>9s} {'persist':>8s}")
    for y in (2023, 2024, 2025):
        sf, tf = out[(1.0, y)]; se, te = out[(0.02, y)]
        print(f"{y:>6d} {sf:>+11.2f} {se:>+13.2f} {tf:>10.3f} {te:>9.3f} {persist[y]:>+8.2f}")
    return out, persist


def main():
    print("Loading M0 + funding on the fullhist grid ...")
    ts, day, Y, CL, m0 = load_pred("m0_fullhist_wf")
    _, _, _, _, fund = load_pred("fund_ema_fullhist")
    print(f"grid T={len(ts)} CLfrac={CL.mean():.4f} |Y|med={np.median(np.abs(Y[np.isfinite(Y)]))*1e4:.1f}bps")
    per_year_netcost(day, Y, CL, m0, None, "M0 standalone")
    per_year_netcost(day, Y, CL, fund, None, "funding_ema standalone")
    per_year_netcost(day, Y, CL, m0, fund, "BLEND (equal-risk z, M0+funding)")


if __name__ == "__main__":
    main()
