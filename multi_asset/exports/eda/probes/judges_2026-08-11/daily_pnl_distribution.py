#!/usr/bin/env python3
"""Daily P&L DISTRIBUTION of the canonical engine, in the caliber a stop-loss must be set in.

READ-ONLY over the panels. Writes ONE json to the path given on the command line. Imports the
engine components; modifies nothing.

★★ WHY THIS IS NOT JUST "read the Sharpe table"
A stop-loss threshold is a statement about the TAIL of the daily return distribution, and the
published table carries only Sharpe. Sharpe is a ratio; a threshold needs magnitudes.

★★★ AND WHY THE NATIVE ENGINE NUMBERS WOULD BE THE WRONG MAGNITUDES — the caliber correction.
`replay_fullhist` computes `pnl_t = Σ p_t · ret_t` where `p_t` is the netted book. That book's
GROSS DRIFTS: it is not renormalised, and its mean L1 norm is ~0.52 (the same fact recorded for
turnover, where canonical 751/857 are raw-drifting-gross units needing a ~1.94x correction to be
read as absolute deployed turnover).
The DEPLOYED book does not drift: `legs.to_notional(target_w, symbols, gross)` scales to a CONSTANT
25,000 USDT gross every anchor, and the vol gate deliberately pins exposure_mult to 1.0.
⇒ Reading the engine's native per-anchor P&L as "return on the deployed book" understates every
  quantile by roughly the same ~1.9x, which would set a stop-loss ~1.9x too tight — i.e. one that
  fires on ordinary days. That is the specific failure the thresholds must avoid.
⇒ So the deployed-caliber return is `pnl_t / Σ|p_t|`, and turnover is recomputed on the
  renormalised book. BOTH calibers are reported side by side so the correction is auditable
  rather than asserted.

★ WHAT THIS STILL DOES NOT COVER, and it bounds how the output may be used:
The engine is STRUCTURAL caliber (engine/README.md): frictionless apart from an explicit 1.9 bps,
no maker-fill slippage, no adverse selection, no fill-rate < 1, no queueing, no impact, no
capacity. Every one of those ADDS dispersion in production. ⇒ the distribution below is a LOWER
BOUND on how wide the real daily distribution is, so a threshold placed at its p1 would be
TOO TIGHT in production. It is a floor to set thresholds outside of, not a calibration target.
"""
import json
import sys

import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource                       # noqa: E402
from engine.funding_risk import FundingLegRiskControl             # noqa: E402
from engine.vol_gate import VolGate                               # noqa: E402
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS      # noqa: E402
from engine.netting import CrossLegNetting                        # noqa: E402

COST_BPS = 1.9
LEVERAGE = 5.0            # deployed: 25,000 gross on >=5,000 equity (config/book.json)
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/daily_pnl_distribution.json"


def main():
    src = PanelSource()
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()

    # CANONICAL: rank funding + C5 (inert under rank, kept for bit-identity) + 99pct pos-cap
    disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp_ref)
    chain = SignalChain(src, weights=dict(DEFAULT_WEIGHTS), funding_mode="rank",
                        vol_gate=VolGate(src), funding_risk=frc, pos_cap_pct=99.0)
    net = CrossLegNetting(chain, dict(DEFAULT_WEIGHTS), cost_bps=COST_BPS)
    res = net.run(anchors, src.ts, calib_by_year=None, year_of=yr)
    pos_by_t = {t: (m, p) for (t, m, p) in res["net_positions"]}

    n = len(anchors)
    pnl_raw = np.zeros(n)       # engine native: Σ p·ret, drifting gross
    gross = np.zeros(n)         # Σ|p| at each anchor — the drift itself
    turn_raw = np.zeros(n)      # Σ|Δp| in native units
    turn_dep = np.zeros(n)      # Σ|Δ(p/Σ|p|)| — the renormalised (deployed) book's turnover
    prev_raw = prev_dep = None
    for i, t in enumerate(anchors):
        m, p = pos_by_t[int(t)]
        ret = src.Y4[int(t), m]
        ok = np.isfinite(ret)
        pnl_raw[i] = float(np.nansum(p[ok] * ret[ok]))
        g = float(np.abs(p).sum())
        gross[i] = g
        full = np.zeros(src.N)
        full[m] = p
        dep = full / g if g > 0 else full
        if prev_raw is not None:
            turn_raw[i] = float(np.abs(full - prev_raw).sum())
            turn_dep[i] = float(np.abs(dep - prev_dep).sum())
        prev_raw, prev_dep = full, dep

    # deployed caliber: the book is renormalised to constant gross every anchor
    with np.errstate(divide="ignore", invalid="ignore"):
        ret_dep = np.where(gross > 0, pnl_raw / gross, np.nan)
    cost_raw = turn_raw * COST_BPS * 1e-4
    cost_dep = turn_dep * COST_BPS * 1e-4

    day = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
    df = pd.DataFrame({"day": day, "yr": yr,
                       "raw_gross": pnl_raw, "raw_net": pnl_raw - cost_raw,
                       "dep_gross": ret_dep, "dep_net": ret_dep - cost_dep,
                       "gross_l1": gross})
    d = df.groupby("day").agg(raw_gross=("raw_gross", "sum"), raw_net=("raw_net", "sum"),
                              dep_gross=("dep_gross", "sum"), dep_net=("dep_net", "sum"),
                              gross_l1=("gross_l1", "mean"), yr=("yr", "first")).reset_index()

    def stats(x, scale=1.0):
        x = np.asarray(x, float) * scale
        x = x[np.isfinite(x)]
        q = lambda p: float(np.percentile(x, p))                  # noqa: E731
        cum = np.cumsum(x)
        peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
        return {"n_days": int(len(x)), "mean": float(x.mean()), "std": float(x.std()),
                "sharpe_ann": float(x.mean() / (x.std() + 1e-12) * np.sqrt(365.0)),
                "p01": q(1), "p05": q(5), "p25": q(25), "p50": q(50), "p75": q(75),
                "p95": q(95), "p99": q(99),
                "worst_day": float(x.min()), "best_day": float(x.max()),
                "max_drawdown": float((cum - peak).min()),
                "total_return": float(cum[-1])}

    out = {
        "caliber_note": ("engine STRUCTURAL caliber: frictionless apart from an explicit "
                         f"{COST_BPS} bps, no maker-fill slippage / adverse selection / "
                         "fill-rate<1 / queueing / impact / capacity. Every one of those ADDS "
                         "dispersion, so these quantiles are a LOWER BOUND on the real spread. "
                         "A threshold set AT p1 here would be too tight in production."),
        "config": {"funding_mode": "rank", "c5": True, "shaping": "cap",
                   "cost_bps": COST_BPS, "leverage": LEVERAGE},
        "anchors": int(n), "days": int(len(d)),
        "gross_drift": {"mean_L1": float(gross.mean()), "p05": float(np.percentile(gross, 5)),
                        "p50": float(np.percentile(gross, 50)),
                        "p95": float(np.percentile(gross, 95)),
                        "why": ("the engine book is NOT renormalised; the deployed book is "
                                "(constant 25,000 gross). Dividing by this is the whole "
                                "difference between the two calibers below.")},
        "turnover_ann": {"raw": float(turn_raw.sum() / (len(d) / 365.0)),
                         "deployed": float(turn_dep.sum() / (len(d) / 365.0))},
        # (1) what the engine natively reports — comparable to the published Sharpe table
        "A_engine_native_drifting_gross": stats(d["raw_net"]),
        # (2) the same days, as a return on the DEPLOYED constant gross
        "B_deployed_constant_gross": stats(d["dep_net"]),
        # (3) the same, expressed on EQUITY at 5x — the unit a stop-loss limit is written in
        "C_deployed_pct_of_EQUITY_at_5x": stats(d["dep_net"], scale=LEVERAGE * 100.0),
        "C_gross_only_no_cost": stats(d["dep_gross"], scale=LEVERAGE * 100.0),
        "per_year_equity_pct": {int(y): stats(d[d.yr == y]["dep_net"], LEVERAGE * 100.0)
                                for y in sorted(set(int(v) for v in d.yr))},
    }
    # how often would a candidate day-loss limit have fired, per year and overall
    eq = np.asarray(d["dep_net"], float) * LEVERAGE * 100.0
    eq = eq[np.isfinite(eq)]
    out["candidate_day_limits"] = {
        f"{lim}%": {"n_days_breached": int((eq < lim).sum()),
                    "pct_of_days": round(float((eq < lim).mean() * 100), 4),
                    "once_per_N_days": (round(float(len(eq) / max((eq < lim).sum(), 1)), 1)
                                        if (eq < lim).sum() else None)}
        for lim in (-1.0, -2.0, -3.0, -4.0, -5.0, -6.7, -10.0, -15.0)}
    # ★ the SERIES itself, so the threshold work can be redone without re-running the replay —
    # and so a re-centring study (what happens to breach counts when the deployable mean is far
    # below this structural one) can use the REAL fat-tailed shape instead of a normal fit.
    out["daily_series_equity_pct_at_5x"] = [round(float(v), 6) for v in
                                            (np.asarray(d["dep_net"], float) * LEVERAGE * 100.0)]
    out["daily_series_days"] = [int(v) for v in d["day"]]
    json.dump(out, open(OUT, "w"), indent=1)
    print("WROTE", OUT)
    b, c = out["B_deployed_constant_gross"], out["C_deployed_pct_of_EQUITY_at_5x"]
    print(f"days={out['days']}  gross_L1 mean={out['gross_drift']['mean_L1']:.4f}")
    print(f"B deployed  net: mean={b['mean']:.6f} std={b['std']:.6f} p01={b['p01']:.6f} "
          f"worst={b['worst_day']:.6f} maxDD={b['max_drawdown']:.6f}")
    print(f"C equity@5x net: mean={c['mean']:.3f}% std={c['std']:.3f}% p01={c['p01']:.3f}% "
          f"p05={c['p05']:.3f}% p50={c['p50']:.3f}% p95={c['p95']:.3f}% p99={c['p99']:.3f}%")
    print(f"C equity@5x    : worst_day={c['worst_day']:.3f}%  maxDD={c['max_drawdown']:.3f}%  "
          f"sharpe={c['sharpe_ann']:.2f}")
    for k, v in out["candidate_day_limits"].items():
        print(f"   day-limit {k:>7s}: {v['n_days_breached']:5d} days "
              f"({v['pct_of_days']:.3f}%), once per {v['once_per_N_days']} days")


if __name__ == "__main__":
    main()
