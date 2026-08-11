"""Part 3 of the band study: is a no-trade band a useful FREE PARAMETER?

Exchange minimums turn out to be non-binding (see min_notional_band.json: at x1 only ~1-2 names
of ~110 are skipped per rebalance, 0.04% of turnover, IC capture 1.000). So the interesting
question is the RELATIVE band the lead also asked for: skip when |dq_i| < b (fraction of gross),
swept wide enough to actually bind, with a paired block-bootstrap on the winner.

Also settles the turnover-caliber question: the canonical "751 net / 857 gross per year" is
expressed in the book's RAW drifting-gross units. Deployed at constant gross the same path is
751/mean_gross per year. That ratio is reported here because it is an input to the fee surface.

Out: exports/eda/band_optimum.json
"""
import os
import json, sys, time
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import min_notional_band as MB
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.vol_gate import VolGate
from engine.funding_risk import FundingLegRiskControl
from engine.netting import CrossLegNetting

BANDS = [0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
COSTS = [1.9, 4.8, 8.34]     # engine assumption / HL taker@50k+fee / HL taker@500k top40+fee


def sim_rel(Q, INUNIV, RET, band, yr, days, cost_bps):
    n, N = Q.shape
    actual = np.zeros(N)
    pnl = np.zeros(n); turn = np.zeros(n)
    for i in range(n):
        d = Q[i] - actual
        if band <= 0:
            trade = d
        else:
            keep = (np.abs(d) >= band) | ((~INUNIV[i]) & (actual != 0.0))
            trade = np.where(keep, d, 0.0)
        actual = actual + trade
        turn[i] = np.abs(trade).sum()
        pnl[i] = actual @ RET[i]
    pnl_net = pnl - turn * cost_bps * 1e-4
    df = pd.DataFrame({"day": days, "yr": yr, "p": pnl_net})
    daily = df.groupby("day").agg(p=("p", "sum"), yr=("yr", "first")).reset_index()
    years = sorted(set(int(y) for y in yr))
    py = {int(y): round(MB._dsharpe(daily[daily.yr == y]["p"].values), 2) for y in years}
    yrs_span = (days.max() - days.min()) / 365.25
    return {"avg_net_sharpe": round(float(np.mean(list(py.values()))), 2), "per_year": py,
            "turn_ann": round(float(turn.sum() / yrs_span), 1),
            "daily": daily["p"].values, "day": daily["day"].values, "dyr": daily["yr"].values}


def main():
    t0 = time.time()
    src = PanelSource()
    anchors, yr = MB.all_anchors(src)
    days = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)

    # mean raw book gross -> the turnover caliber conversion
    w = MB.WEIGHTS["champion"]
    disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp_ref)
    chain = SignalChain(src, weights=w, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=99.0)
    res = CrossLegNetting(chain, w, cost_bps=1.9).run(anchors, src.ts, year_of=yr)
    gross = np.array([np.abs(p).sum() for (_, _, p) in res["net_positions"]])
    mg = float(gross.mean())
    print(f"[caliber] mean raw book gross = {mg:.4f} (median {np.median(gross):.4f})", flush=True)

    out = {"turnover_caliber": {
        "canonical_net_turn_ann_raw_units": 750.775,
        "canonical_gross_turn_ann_raw_units": 857.25,
        "mean_raw_book_gross": round(mg, 4),
        "net_turn_ann_at_constant_deployed_gross": round(750.775 / mg, 1),
        "gross_turn_ann_at_constant_deployed_gross": round(857.25 / mg, 1),
        "why": ("the canonical figures are |dp| summed on the book's RAW positions, whose L1 "
                "gross averages ~%.2f, not 1. Sharpe is unaffected (cost and P&L scale together), "
                "but any ABSOLUTE reading -- 'we trade N x book value per year', exchange fee "
                "tiers, volume-based rate cards -- must use the constant-gross figure, which is "
                "1/%.2f = %.2fx larger." % (mg, mg, 1 / mg)),
    }, "relative_band": {}}

    for wname in ("champion", "challenger"):
        Q, INUNIV, RET = MB.build_target_path(src, anchors, yr, MB.WEIGHTS[wname])
        out["relative_band"][wname] = {}
        for cost in COSTS:
            rows = {}
            base = None
            for b in BANDS:
                r = sim_rel(Q, INUNIV, RET, b, yr, days, cost)
                if b == 0.0:
                    base = r
                rows[str(b)] = {"avg_net_sharpe": r["avg_net_sharpe"], "per_year": r["per_year"],
                                "turn_ann": r["turn_ann"],
                                "turn_ratio": round(r["turn_ann"] / base["turn_ann"], 4),
                                "d_vs_noband": round(r["avg_net_sharpe"]
                                                     - base["avg_net_sharpe"], 2),
                                "equiv_usd_at_50k": round(b * 50_000, 1),
                                "equiv_usd_at_500k": round(b * 500_000, 1),
                                "_daily": r["daily"]}
            # paired block bootstrap: best band vs no band
            best_b = max([b for b in BANDS if b > 0],
                         key=lambda b: rows[str(b)]["avg_net_sharpe"])
            A = base["daily"]; B = rows[str(best_b)]["_daily"]
            rng = np.random.default_rng(20260725)
            nd = len(A); L = 20; nb = int(np.ceil(nd / L)); NB = 2000
            st = rng.integers(0, nd - L, size=(NB, nb))
            idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(NB, -1)[:, :nd]
            sa = A[idx].mean(1) / (A[idx].std(1) + 1e-12) * np.sqrt(365)
            sb = B[idx].mean(1) / (B[idx].std(1) + 1e-12) * np.sqrt(365)
            d = sb - sa
            for k in rows:
                rows[k].pop("_daily", None)
            out["relative_band"][wname][f"cost_{cost}bps"] = {
                "by_band": rows, "best_band": best_b,
                "bootstrap_best_vs_noband": {
                    "delta": round(float(MB._dsharpe(B) - MB._dsharpe(A)), 2),
                    "ci95": [round(float(np.percentile(d, 2.5)), 2),
                             round(float(np.percentile(d, 97.5)), 2)],
                    "p_better": round(float((d > 0).mean()), 3)}}
            print(f"[{wname} cost={cost}bps] " + " ".join(
                f"b={b}:{rows[str(b)]['avg_net_sharpe']:.2f}({rows[str(b)]['turn_ratio']:.2f})"
                for b in BANDS) +
                f" | best {best_b} d={out['relative_band'][wname][f'cost_{cost}bps']['bootstrap_best_vs_noband']['delta']:+.2f} "
                f"CI{out['relative_band'][wname][f'cost_{cost}bps']['bootstrap_best_vs_noband']['ci95']}",
                flush=True)
    json.dump(out, open(MA + "/exports/eda/band_optimum.json", "w"), indent=1)
    print(f"-> band_optimum.json ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
