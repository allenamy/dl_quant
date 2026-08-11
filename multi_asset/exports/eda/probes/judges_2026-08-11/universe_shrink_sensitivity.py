"""Universe-shrink sensitivity: what the book costs when the tradeable universe is truncated
to point-in-time top-N by trailing dollar volume (venue-feasibility question, 2026-07-25).

Motivation: binance.com perps are unavailable to SG retail. Order-book DEX alternatives
(Hyperliquid / dYdX v4) list far fewer perps than Binance's 110-name panel. This measures,
ON EXISTING BINANCE DATA, how the canonical engine (funding-rank + shaping='cap', 4-leg book)
degrades as the universe is truncated to top-N = 110/80/60/50/40/30/20.

★ Point-in-time: membership is rebuilt with the EXACT rule that produced MEMBER110
  (build_wide_dl.py L102-114): 30-day blocks, rank by DVOL30 (trailing-30d mean HOURLY quote
  volume) sampled at the block's first hour. Top-N is a strict nested subset of top-110 --
  no look-ahead.

★ Caliber: STRUCTURAL, same as engine/README.md (1.9 bps explicit cost only, daily x sqrt(365),
  market-neutral, no maker-fill execution stack). Absolute Sharpes are an upper bound; the
  DELTA across N is the deliverable.

★ The DL legs (king, s2) are NOT retrained per universe -- their predictions are reused and
  simply scored/traded on the narrower set. This is the "trade a subset of what we already
  model" question, which is the right first-order venue question. A retrained-on-top-N model
  could differ (probably slightly better on the survivors, since capacity per name is higher).

Outputs: exports/eda/universe_shrink_sensitivity.{json,md}
Run: python multi_asset/exports/eda/universe_shrink_sensitivity.py
"""
import sys, json, time
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS, _l1
from engine.netting import CrossLegNetting
from engine.ic_monitor import xsec_rank_ic

COST_BPS = 1.9
PARTICIPATION = 0.05          # capacity: traded notional per name <= 5% of that name's 4h $ volume
NS = [110, 80, 60, 50, 40, 30, 20]
OUT_JSON = MA + "/exports/eda/universe_shrink_sensitivity.json"
OUT_MD = MA + "/exports/eda/universe_shrink_sensitivity.md"
WIDE_PANEL = MA + "/exports/wide_panel_full.npz"


# ---------------------------------------------------------------- membership
def build_topn_masks(T, N_sym, DV, ns):
    """Reproduce build_wide_dl.py's point-in-time membership rule for each top-N."""
    day = np.arange(T) // 24
    month = day // 30
    out = {}
    for n in ns:
        MEM = np.zeros((T, N_sym), bool)
        for m in np.unique(month):
            rows = np.where(month == m)[0]
            dv = DV[rows[0]]
            fin = np.isfinite(dv)
            if fin.sum() >= n:
                top = np.argsort(-np.where(fin, dv, -np.inf))[:n]
                MEM[np.ix_(rows, top)] = True
            else:
                MEM[rows] = fin[None, :]
        out[n] = MEM
    return out


def _dsharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def _all_anchors(src):
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    yr = pd.to_datetime(src.ts[a], unit="ms", utc=True).year.to_numpy()
    return a, yr


# ---------------------------------------------------------------- one replay
def replay_for_universe(src, DV, anchors_fixed=None, funding_mode="rank", shaping="cap",
                        weights=None):
    """Canonical engine replay on src.member as-is. Mirrors replay_fullhist.run_replay exactly
    (verified bit-for-bit at N=110) and additionally returns turnover/capacity/breadth."""
    cap_on = shaping in ("cap", "calibrated")
    weights = dict(weights or DEFAULT_WEIGHTS)
    if anchors_fixed is None:
        anchors, yr = _all_anchors(src)
    else:
        anchors = anchors_fixed
        yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
    disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp_ref)
    chain = SignalChain(src, weights=weights, funding_mode=funding_mode, vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=(99.0 if cap_on else None))
    years = sorted(set(int(y) for y in yr))

    # funding-leg concentration diagnostic
    conc = []
    for t in anchors:
        legs, _ = chain.leg_signals(int(t))
        w = _l1(legs["funding"])
        if w.size:
            conc.append(float(np.max(np.abs(w))))
    conc = np.array(conc)
    frc.n_gated = 0

    net = CrossLegNetting(chain, weights, cost_bps=COST_BPS)
    res = net.run(anchors, src.ts, calib_by_year=None, year_of=yr)

    # ---- P&L + turnover + capacity, per anchor ----
    pos_by_t = {t: (m, p) for (t, m, p) in res["net_positions"]}
    n_anchor = len(anchors)
    pnl = np.zeros(n_anchor); turn = np.zeros(n_anchor)
    breadth = np.zeros(n_anchor)
    cap_min = np.full(n_anchor, np.nan)     # strict: no name over PARTICIPATION
    cap_p05 = np.full(n_anchor, np.nan)     # relaxed: allow worst 5% of names to breach
    hhi = np.zeros(n_anchor)
    prev = None
    prev_norm = None
    for i, t in enumerate(anchors):
        ti = int(t)
        m, p = pos_by_t[ti]
        ret = src.Y4[ti, m]
        ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(p[ok] * ret[ok]))
        full = np.zeros(src.N); full[m] = p
        if prev is not None:
            turn[i] = float(np.abs(full - prev).sum())
        prev = full
        breadth[i] = int(len(m))
        g = np.abs(full).sum()
        if g > 1e-12:
            pn = full / g
            hhi[i] = float((pn ** 2).sum())
            if prev_norm is not None:
                d = np.abs(pn - prev_norm)
                traded = np.where(d > 1e-7)[0]
                if traded.size:
                    dv4 = DV[ti, traded] * 4.0        # 4h dollar volume (DVOL30 = mean hourly)
                    good = np.isfinite(dv4) & (dv4 > 0)
                    if good.sum() >= 5:
                        ratio = PARTICIPATION * dv4[good] / d[traded][good]
                        cap_min[i] = float(np.min(ratio))
                        cap_p05[i] = float(np.percentile(ratio, 5))
            prev_norm = pn

    cost = turn * COST_BPS * 1e-4
    pnl_net = pnl - cost

    day = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
    dfp = pd.DataFrame({"day": day, "yr": yr, "pnl": pnl, "pnl_net": pnl_net})
    daily = dfp.groupby("day").agg(pnl=("pnl", "sum"), pnl_net=("pnl_net", "sum"),
                                   yr=("yr", "first")).reset_index()
    table = {}
    for y in years:
        sel = (yr == y)
        dd = daily[daily.yr == y]
        ics = np.array([c for c in (xsec_rank_ic(pos_by_t[int(t)][1], src.Y4[int(t), pos_by_t[int(t)][0]])
                                    for t in anchors[sel]) if np.isfinite(c)])
        cm = cap_min[sel]; cp = cap_p05[sel]
        table[int(y)] = {
            "trading_days": int(len(dd)),
            "gross_sharpe": round(_dsharpe(dd["pnl"].values), 2),
            "net_of_cost_sharpe": round(_dsharpe(dd["pnl_net"].values), 2),
            "mean_rank_ic": round(float(ics.mean()) if len(ics) else np.nan, 4),
            "ic_ir": round(float(ics.mean() / (ics.std() + 1e-12)) if len(ics) else np.nan, 3),
            "mean_breadth": round(float(breadth[sel].mean()), 1),
            "turn_per_anchor": round(float(np.mean(turn[sel])), 4),
            "mean_hhi": round(float(hhi[sel].mean()), 5),
            "cap_usd_strict_median": (round(float(np.nanmedian(cm)), 0) if np.isfinite(cm).any() else None),
            "cap_usd_p05relax_median": (round(float(np.nanmedian(cp)), 0) if np.isfinite(cp).any() else None),
        }
    avg_net = round(float(np.mean([table[y]["net_of_cost_sharpe"] for y in years])), 2)
    avg_gross = round(float(np.mean([table[y]["gross_sharpe"] for y in years])), 2)
    avg_ic = round(float(np.mean([table[y]["mean_rank_ic"] for y in years])), 4)

    return {
        "_daily": {"day": daily["day"].values.tolist(), "yr": daily["yr"].values.tolist(),
                   "pnl_net": daily["pnl_net"].values.tolist()},
        "anchors": int(n_anchor),
        "netting": {k: (round(res[k], 3) if isinstance(res[k], float) else res[k])
                    for k in ["hedge_rate", "gross_turn_ann", "net_turn_ann", "savings_bps_yr", "years"]},
        "funding_concentration": {"mean": round(float(conc.mean()), 3),
                                  "p99": round(float(np.percentile(conc, 99)), 3),
                                  "max": round(float(conc.max()), 3)},
        "per_year": table,
        "avg_net_of_cost_sharpe": avg_net,
        "avg_gross_sharpe": avg_gross,
        "avg_mean_rank_ic": avg_ic,
        "median_breadth": round(float(np.median(breadth)), 1),
        "cap_usd_strict_median_all": (round(float(np.nanmedian(cap_min)), 0) if np.isfinite(cap_min).any() else None),
        "cap_usd_p05relax_median_all": (round(float(np.nanmedian(cap_p05)), 0) if np.isfinite(cap_p05).any() else None),
    }


def main():
    t0 = time.time()
    src = PanelSource()
    z = np.load(WIDE_PANEL, allow_pickle=True)
    assert np.array_equal(z["ts"].astype(np.int64), src.ts), "wide_panel_full ts mismatch"
    DV = z["DVOL30"].astype(np.float64)
    T, Nsym = src.member.shape

    masks = build_topn_masks(T, Nsym, DV, NS)
    same110 = bool(np.array_equal(masks[110], src.member))
    print(f"[check] rebuilt top-110 == MEMBER110 bit-for-bit: {same110}", flush=True)
    assert same110, "membership rule does not reproduce MEMBER110 -- abort"

    base_member = src.member.copy()
    src.member = masks[110]
    anchors_110, _ = _all_anchors(src)
    print(f"[check] anchors@110 = {len(anchors_110)}", flush=True)

    results = {}
    for n in NS:
        src.member = masks[n]
        a_n, _ = _all_anchors(src)
        # use each universe's own anchors if identical to 110's; else report + use 110 grid
        # intersected with availability (keeps the P&L grid comparable across N).
        same_anchors = bool(np.array_equal(a_n, anchors_110))
        r = replay_for_universe(src, DV, anchors_fixed=anchors_110)
        r["own_anchors"] = int(len(a_n))
        r["anchors_identical_to_110"] = same_anchors
        r["median_universe_size"] = float(np.median(masks[n].sum(1)))
        results[n] = r
        print(f"[N={n:3d}] anchors={r['anchors']} breadth={r['median_breadth']:.0f} "
              f"avgNet={r['avg_net_of_cost_sharpe']:.2f} avgGross={r['avg_gross_sharpe']:.2f} "
              f"IC={r['avg_mean_rank_ic']:.4f} netturn={r['netting']['net_turn_ann']:.0f} "
              f"cap${r['cap_usd_strict_median_all']:,.0f} ({time.time()-t0:.0f}s)", flush=True)

    src.member = base_member

    # ---- paired moving-block bootstrap on the DAILY net-P&L Sharpe delta vs N=110 ----
    # Deltas are paired (identical days), so bootstrap the per-N daily series jointly with a
    # common block index -> CI on d(Sharpe) that respects the pairing and daily autocorrelation.
    rng = np.random.default_rng(20260725)
    days = np.array(results[110]["_daily"]["day"])
    S = {n: np.array(results[n]["_daily"]["pnl_net"], float) for n in NS}
    for n in NS:
        assert np.array_equal(np.array(results[n]["_daily"]["day"]), days), "daily grid mismatch"
    L = 20                                   # ~3-week blocks
    nd = len(days); nb = int(np.ceil(nd / L)); B = 2000
    starts = rng.integers(0, nd - L, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(B, -1)[:, :nd]
    boot = {}
    for n in NS:
        x = S[n][idx]
        boot[n] = x.mean(1) / (x.std(1) + 1e-12) * np.sqrt(365.0)
    bs = {}
    for n in NS:
        d = boot[n] - boot[110]
        bs[str(n)] = {"sharpe_full_hist": round(float(_dsharpe(S[n])), 2),
                      "d_vs_110": round(float(_dsharpe(S[n]) - _dsharpe(S[110])), 2),
                      "d_ci95": [round(float(np.percentile(d, 2.5)), 2),
                                 round(float(np.percentile(d, 97.5)), 2)],
                      "p_worse_than_110": round(float((d < 0).mean()), 3)}
        print(f"[boot N={n:3d}] full-hist Sharpe {bs[str(n)]['sharpe_full_hist']:.2f} "
              f"d={bs[str(n)]['d_vs_110']:+.2f} CI95={bs[str(n)]['d_ci95']} "
              f"P(worse)={bs[str(n)]['p_worse_than_110']:.3f}", flush=True)

    for n in NS:
        results[n].pop("_daily", None)
    out = {
        "meta": {
            "created": "2026-07-25",
            "task": "venue feasibility (1) universe-shrink cost",
            "caliber": ("STRUCTURAL upper bound -- canonical engine (funding rank + shaping='cap', "
                        "4-leg book, 1.9 bps explicit cost, daily x sqrt(365), market-neutral). "
                        "NO maker-fill execution stack. Deltas across N are the deliverable, not levels."),
            "membership": ("point-in-time top-N by DVOL30 (trailing-30d mean hourly quote volume), "
                           "30-day blocks sampled at block start -- identical rule to MEMBER110 "
                           "(verified bit-for-bit at N=110). Strictly nested, no look-ahead."),
            "dl_legs": "king/s2 predictions reused, NOT retrained per universe",
            "anchor_grid": "fixed to the N=110 anchor set for all N (comparable P&L grid)",
            "capacity_model": (f"traded notional per name per 4h rebalance <= {PARTICIPATION:.0%} of that "
                               "name's point-in-time 4h dollar volume (4 x DVOL30); book held at "
                               "constant unit gross; strict = no name breaches, p05relax = worst 5% "
                               "of traded names allowed to breach. Reported USD = max deployable GROSS."),
            "cost_bps": COST_BPS,
        },
        "by_topn": {str(k): v for k, v in results.items()},
        "bootstrap_full_hist_sharpe": {
            "note": ("paired moving-block bootstrap (L=20 trading days, B=2000) on the pooled "
                     "full-history DAILY net-of-cost P&L; common block index across N so the "
                     "delta respects pairing. Full-history Sharpe != avg-of-years Sharpe."),
            "by_topn": bs},
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1)
    print(f"[done] {OUT_JSON} ({time.time()-t0:.0f}s)", flush=True)
    return out


if __name__ == "__main__":
    main()
