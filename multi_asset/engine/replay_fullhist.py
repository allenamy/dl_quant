"""Full-history engine replay 2022-2026 -- the engine-caliber honest Sharpe table.

Complete pipeline: 4-leg L1 sub-portfolios -> C5 funding-risk -> combine -> C6 cross-leg netting ->
shape (v1: now on the P&L path) -> net positions; vol-gate is execution-tactic-only (exposure NOT
modulated). P&L = net_pos . realized 4h return; net-of-cost subtracts netted turnover x tick-cost.
Reports per-year gross + net-of-cost Sharpe, netting savings, funding-leg concentration, FTX tail.

CANONICAL (0C 2026-07-15) = funding rank + shaping='cap' (99pct pos-cap only). Isotonic C3
(shaping='calibrated') is the DEPLOYABLE-CALIBRATED variant -- its role is real E[bps] for
Kelly/net-cost gating, at an explicit -1.3 avg-Sharpe cost (isotonic tail-saturation is net-negative
reshaping here). The z-mode +1.3 I earlier credited to isotonic was really the pos-cap trimming
z-outliers (C5's job); under rank the outliers are gone so cap is near-free and isotonic is pure cost.

*** STRUCTURAL-CALIBER, not deployable Sharpe -- see engine/README.md (0C positioning verdict). ***

Importable: run_replay(funding_mode, use_c5, use_shaping) -> dict. CLI flags below.
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS, _l1
from engine.netting import CrossLegNetting
from engine.isotonic_calib import IsotonicCalibrator
from engine.ic_monitor import xsec_rank_ic

COST_BPS = 1.9
OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/engine_fullhist_replay.json"
_SRC = None


def get_src():
    global _SRC
    if _SRC is None:
        _SRC = PanelSource()
    return _SRC


def _all_anchors(src):
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    yr = pd.to_datetime(src.ts[a], unit="ms", utc=True).year.to_numpy()
    return a, yr


def _dsharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def run_replay(funding_mode="z", use_c5=True, shaping="cap", weights=None, verbose=True):
    """shaping: 'none' = demean only (baseline caliber); 'cap' = 99pct pos-cap + demean (CANONICAL --
    trims outliers, near-free once funding is rank-bounded); 'calibrated' = cap + walk-forward isotonic
    C3 (the DEPLOYABLE-CALIBRATED variant: real E[bps] for Kelly/net-cost gating, at an explicit cost --
    0C: isotonic reshaping is net-negative in this sparse-tail signal, cuts mean not vol)."""
    assert shaping in ("none", "cap", "calibrated")
    cap_on = shaping in ("cap", "calibrated"); calibrate = (shaping == "calibrated")
    src = get_src(); weights = dict(weights or DEFAULT_WEIGHTS)
    anchors, yr = _all_anchors(src)
    disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = (FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                 disp_ref=disp_ref) if use_c5 else None)
    chain = SignalChain(src, weights=weights, funding_mode=funding_mode, vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=(99.0 if cap_on else None))

    # ---- walk-forward yearly C3 calibrators (fit on PRIOR year; first year -> identity) ----
    calib_by_year = {}
    years = sorted(set(int(y) for y in yr))
    if calibrate:
        for y in years:
            prior = anchors[yr == (y - 1)]
            calib_by_year[y] = (chain.fit_calibrator_on(prior, IsotonicCalibrator())
                                if len(prior) > 200 else None)
        chain.calibrator = None

    # ---- funding-leg single-name L1 concentration diagnostic (over all anchors) ----
    conc = []
    for t in anchors:
        legs, _ = chain.leg_signals(int(t)); w = _l1(legs["funding"])
        if w.size:
            conc.append(float(np.max(np.abs(w))))
    conc = np.array(conc)
    if frc is not None:
        frc.n_gated = 0

    # ---- C6 netting (routes each net book through shape_position) ----
    net = CrossLegNetting(chain, weights, cost_bps=COST_BPS)
    res = net.run(anchors, src.ts, calib_by_year=(calib_by_year if calibrate else None), year_of=yr)
    if verbose:
        print("[C6 netting] hedge=%.1f%% gross=%.0f net=%.0f save=%.1f bps/yr | funding-conc mean/p99/max=%.3f/%.3f/%.3f" % (
            res["hedge_rate"] * 100, res["gross_turn_ann"], res["net_turn_ann"], res["savings_bps_yr"],
            conc.mean(), np.percentile(conc, 99), conc.max()), flush=True)

    # ---- P&L from netted (shaped) positions + net-of-cost ----
    pos_by_t = {t: (m, p) for (t, m, p) in res["net_positions"]}
    pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors)); prev = None
    for i, t in enumerate(anchors):
        m, p = pos_by_t[int(t)]
        ret = src.Y4[int(t), m]
        ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(p[ok] * ret[ok]))
        full = np.zeros(src.N); full[m] = p
        if prev is not None:
            turn[i] = float(np.abs(full - prev).sum())
        prev = full
    cost = turn * COST_BPS * 1e-4
    pnl_net = pnl - cost

    # ---- anchor P&L -> DAILY -> per-year DAILY Sharpe x sqrt(365) ----
    day = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
    dfp = pd.DataFrame({"day": day, "yr": yr, "pnl": pnl, "pnl_net": pnl_net})
    daily = dfp.groupby("day").agg(pnl=("pnl", "sum"), pnl_net=("pnl_net", "sum"),
                                   yr=("yr", "first")).reset_index()
    table = {}
    for y in years:
        dd = daily[daily.yr == y]
        ics = np.array([c for c in (xsec_rank_ic(pos_by_t[int(t)][1], src.Y4[int(t), pos_by_t[int(t)][0]])
                                    for t in anchors[yr == y]) if np.isfinite(c)])
        table[int(y)] = {"trading_days": int(len(dd)),
                         "gross_sharpe": round(_dsharpe(dd["pnl"].values), 2),
                         "net_of_cost_sharpe": round(_dsharpe(dd["pnl_net"].values), 2),
                         "mean_rank_ic": round(float(ics.mean()) if len(ics) else np.nan, 4)}
    avg_net = round(float(np.mean([table[y]["net_of_cost_sharpe"] for y in years])), 2)

    # ---- FTX funding-tail before/after C5 (funding leg max-abs, current weighting) ----
    ftx_day = int(pd.Timestamp("2022-11-09 00:00", tz="UTC").timestamp() * 1000)
    ftx_t = int(np.argmin(np.abs(src.ts - ftx_day)))
    ftx_anchor = int(anchors[np.argmin(np.abs(anchors - ftx_t))])
    chain_rc = SignalChain(src, weights=weights, funding_mode=funding_mode, funding_risk=frc)
    chain_no = SignalChain(src, weights=weights, funding_mode=funding_mode, funding_risk=None)
    lrc, _ = chain_rc.leg_signals(ftx_anchor); lno, _ = chain_no.leg_signals(ftx_anchor)
    ftx = {"anchor_date": str(pd.Timestamp(src.ts[ftx_anchor], unit="ms").date()),
           "funding_leg_max_abs_noRC": round(float(np.max(np.abs(lno["funding"]))), 3),
           "funding_leg_max_abs_withRC": round(float(np.max(np.abs(lrc["funding"]))), 3),
           "disp_gated_days": (frc.n_gated if frc is not None else 0)}

    out = {"config": {"funding_mode": funding_mode, "c5": bool(use_c5), "shaping": shaping},
           "anchors": int(len(anchors)), "cost_bps": COST_BPS,
           "netting": {k: (round(res[k], 3) if isinstance(res[k], float) else res[k])
                       for k in ["hedge_rate", "gross_turn_ann", "net_turn_ann", "savings_bps_yr", "years"]},
           "funding_concentration": {"mean": round(float(conc.mean()), 3),
                                     "p99": round(float(np.percentile(conc, 99)), 3),
                                     "max": round(float(conc.max()), 3)},
           "per_year": table, "avg_net_of_cost_sharpe": avg_net, "ftx_funding_tail": ftx}
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--funding_mode", default="rank", choices=["z", "rank"])
    ap.add_argument("--no_c5", action="store_true")
    ap.add_argument("--shaping", default="cap", choices=["none", "cap", "calibrated"])
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    out = run_replay(funding_mode=a.funding_mode, use_c5=not a.no_c5, shaping=a.shaping)
    if a.out and a.out != "-":
        json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))
