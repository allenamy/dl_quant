"""FINAL portfolio scorecard — Book-1 (funding_ema + M0 DL factor). Per-factor + equal-risk z-blend:
net-cost break-even + net-Sharpe @ realistic tiers, turnover, latency decay, per-fold + MONTHLY
stability, max drawdown, and the funding↔M0 correlation. CPU, honest raw-y (canonical ≥3600 CL).

Blend = per-ts equal-risk cross-sectional z-score sum (both factors positive-IC-oriented). Operating
turnover = the best-break-even EMA alpha (the deployable low-turnover point). Reuses the L/S engine.
"""
from __future__ import annotations
import argparse, datetime as dt, numpy as np, os, sys, os.path as op
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.backtest_longshort import rank_weights

MIN_ASSETS = 5
SEC_PER_YEAR = 365 * 24 * 3600
ALPHA_GRID = (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02)


def _zc(x):
    m, s = x.mean(), x.std()
    return (x - m) / s if s > 1e-12 else x * 0.0


def blend(preds, Y, CL):
    """Per-ts equal-risk z-blend of a list of factor preds (over jointly-valid assets)."""
    T, S = Y.shape; out = np.full((T, S), np.nan)
    for t in range(T):
        v = CL[t] & np.isfinite(Y[t])
        for P in preds:
            v = v & np.isfinite(P[t])
        if v.sum() < MIN_ASSETS:
            continue
        idx = np.where(v)[0]; out[t, idx] = sum(_zc(P[t, idx]) for P in preds)
    return out


def _clean_rows(sig, Y, CL):
    rows = [t for t in range(Y.shape[0]) if (CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])).sum() >= MIN_ASSETS]
    return np.array(rows, int)


def book_stats(sig, Y, CL, ts, day, horizon, cost_bps=2.0):
    T, S = Y.shape; rows = _clean_rows(sig, Y, CL)
    tw = np.zeros((len(rows), S)); Yr = np.zeros((len(rows), S)); rts = ts[rows]; rday = day[rows]
    for i, t in enumerate(rows):
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t]); idx = np.where(v)[0]
        tw[i, idx] = rank_weights(sig[t, idx]); Yr[i, idx] = Y[t, idx]
    n = len(rows); per_yr = SEC_PER_YEAR / horizon; ann = np.sqrt(per_yr)

    def held_series(alpha):
        held = np.zeros(S); g = np.empty(n); tn = np.empty(n)
        for k in range(n):
            new = alpha * tw[k] + (1 - alpha) * held
            tn[k] = np.abs(new - held).sum(); g[k] = float((new * Yr[k]).sum()); held = new
        return g, tn
    # operating alpha = best NET-SHARPE at the headline cost (the deployable operating point).
    # NOT max-break-even: for an UNPROFITABLE fast/one-period signal, max-BE wrongly selects the
    # full-turnover point (least-negative gross/turnover) whose net-Sh is catastrophic; a rational
    # deployer instead EMA-holds to minimise turnover cost. Net-Sh-optimal gives that honest point.
    # For profitable/persistent signals both criteria pick the same low-turnover alpha (no change to
    # the validated 2025/funding numbers); the fix only affects unprofitable fast signals (M0 2023/24:
    # −22 full-turnover -> −2 EMA-hold). Cross-checked vs 0B backtest_longshort (2026-07-10).
    c = cost_bps * 1e-4
    best = dict(nsh=-1e18, alpha=ALPHA_GRID[0])
    for al in ALPHA_GRID:
        g, tn = held_series(al); net = g - tn * c
        nsh = net.mean() / net.std() * ann if net.std() > 0 else -1e18
        if nsh > best["nsh"]:
            best = dict(nsh=float(nsh), alpha=al)
    g, tn = held_series(best["alpha"])
    be = float(g.mean() / tn.mean() * 1e4) if tn.mean() > 1e-12 else np.nan  # break-even AT the operating alpha
    net = g - tn * c                                            # per-period net PnL at the headline cost
    netsh = float(net.mean() / net.std() * ann) if net.std() > 0 else np.nan
    # stressed-cost grid: net-Sharpe at 2 / 5 / 10 bps/side (at the operating alpha chosen above)
    net_sh_grid = {}
    for cb in (2.0, 5.0, 10.0):
        nn = g - tn * (cb * 1e-4)
        net_sh_grid[cb] = round(float(nn.mean() / nn.std() * ann), 2) if nn.std() > 0 else None
    grosssh = float(g.mean() / g.std() * ann) if g.std() > 0 else np.nan
    # per-fold (3 blocks by day)
    ud = np.unique(rday); ed = [ud[len(ud) * i // 3] for i in range(3)] + [ud[-1] + 1]
    pf = []
    for i in range(3):
        m = (rday >= ed[i]) & (rday < ed[i + 1])
        pf.append(round(float(net[m].mean() / net[m].std() * ann), 2) if m.sum() > 5 and net[m].std() > 0 else None)
    # monthly stability
    months = np.array([dt.datetime.utcfromtimestamp(int(t) / (1e9 if t > 1e17 else 1e3)).strftime("%Y-%m") for t in rts])
    mo = {}
    for mth in sorted(set(months)):
        mm = months == mth
        mo[mth] = dict(net_bps=round(float(net[mm].sum() * 1e4), 1),
                       sh=round(float(net[mm].mean() / net[mm].std() * ann), 2) if mm.sum() > 5 and net[mm].std() > 0 else None,
                       n=int(mm.sum()))
    pos_months = sum(1 for v in mo.values() if v["net_bps"] > 0)
    # max drawdown on cumulative net (bps)
    cum = np.cumsum(net) * 1e4; peak = np.maximum.accumulate(cum); dd = cum - peak
    return dict(n=n, be=round(be, 2), alpha=best["alpha"], turnover=round(float(tn.mean()), 4),
                gross_sh=round(grosssh, 2), net_sh_c2=round(netsh, 2), net_sh_grid=net_sh_grid,
                net_ann_bps_c2=round(float(net.mean() * per_yr * 1e4), 0),
                per_fold_net_sh=pf, months_pos=f"{pos_months}/{len(mo)}", max_dd_bps=round(float(dd.min()), 1),
                monthly=mo, ret_series=(rts, net))


def latency(sig, Y, CL, ts, horizon, lags=(0, 180, 360)):
    rows = _clean_rows(sig, Y, CL); ts = ts.astype(np.int64)
    unit = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else (1e3 if ts[0] > 1e11 else 1.0))
    tol = float(np.median(np.diff(np.unique(ts)))) * 0.75
    W = {}
    for t in rows:
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t]); idx = np.where(v)[0]
        W[t] = (idx, rank_weights(sig[t, idx]))
    out = {}
    for lag in lags:
        gg = []
        for t in rows:
            j = np.searchsorted(ts, ts[t] + int(round(lag * unit)))
            cand = [c for c in (j - 1, j, j + 1) if 0 <= c < len(ts)]
            bj = min(cand, key=lambda c: abs(ts[c] - (ts[t] + lag * unit))) if cand else None
            if bj is not None and abs(ts[bj] - (ts[t] + lag * unit)) <= tol and np.isfinite(Y[bj]).any():
                idx, w = W[t]; gg.append(float((w * np.where(np.isfinite(Y[bj, idx]), Y[bj, idx], 0.0)).sum()))
        out[lag] = round(float(np.mean(gg)), 4) if gg else None
    g0 = out.get(0) or 1.0
    return {lag: (round(v / g0, 2) if v is not None and g0 else None) for lag, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train")
    ap.add_argument("--horizon", type=int, default=3600)
    a = ap.parse_args()
    F = load_panel("fund_ema_h3600", a.export)
    Y, CL, ts, day = F["Y"], F["CL"], F["ts"].astype(np.int64), F["day"].astype(np.int64)
    funding = F["pred"]; M0 = load_panel("fund_resid_h3600", a.export)["pred"]
    from multi_asset.eval.factor_scorer import factor_corr, _perts_ic
    icf = float(_perts_ic(funding, Y, CL)[0].mean()); icm = float(_perts_ic(M0, Y, CL)[0].mean())
    comb = blend([funding, M0], Y, CL)                          # equal-risk (headline)
    comb_icw = blend([icf * funding, icm * M0], Y, CL)          # IC-weighted (sensitivity; z-of-scaled = same as z, so weight the z's)
    comb_icw = np.full_like(comb, np.nan)
    for t in range(Y.shape[0]):                                 # IC-weighted z-blend: icf·z(f)+icm·z(m)
        v = CL[t] & np.isfinite(funding[t]) & np.isfinite(M0[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN_ASSETS:
            idx = np.where(v)[0]; comb_icw[t, idx] = icf * _zc(funding[t, idx]) + icm * _zc(M0[t, idx])
    print(f"funding↔M0 cross-factor corr = {factor_corr(funding, M0, CL)} | IC_funding {icf:+.4f} IC_M0 {icm:+.4f}")
    for nm, sig in [("funding_ema", funding), ("M0_dl", M0),
                    ("BLEND equal-risk (HEADLINE)", comb), ("BLEND IC-weighted (sensitivity)", comb_icw)]:
        ic, _ = _perts_ic(sig, Y, CL); st = book_stats(sig, Y, CL, ts, day, a.horizon); lat = latency(sig, Y, CL, ts, a.horizon)
        print(f"\n=== {nm} ===  rank-IC {ic.mean():+.4f}")
        print(f"  BE/side {st['be']} bps | net-Sh @2/5/10bps {st['net_sh_grid']} | gross-Sh {st['gross_sh']} | "
              f"turnover {st['turnover']} | net@2 ann {st['net_ann_bps_c2']:.0f} bps")
        print(f"  per-fold net-Sh {st['per_fold_net_sh']} | months net-positive {st['months_pos']} | max-DD {st['max_dd_bps']} bps")
        print(f"  latency decay (0/180/360s) {lat}")
        print(f"  monthly net bps: " + " ".join(f"{m}:{v['net_bps']:.0f}" for m, v in st['monthly'].items()))
    print("DONE_SCORECARD")


if __name__ == "__main__":
    main()
