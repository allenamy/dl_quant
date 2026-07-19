"""Full-history engine replay 2022-2026 — the FIRST engine-caliber honest Sharpe table.

Complete pipeline: 4-leg signals -> C5 funding-risk -> combine -> C6 cross-leg netting -> net
positions; vol-gate is execution-tactic-only (exposure NOT modulated). P&L = net_pos . realized 4h
return; net-of-cost subtracts netted turnover x tick-cost. Reports per-year gross + net-of-cost
Sharpe, netting savings (vs 0C 86-179 bps/yr), and the FTX funding-tail before/after C5.
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.netting import CrossLegNetting
from engine.ic_monitor import xsec_rank_ic

COST_BPS = 1.9
src = PanelSource()

# ---- all king-4h anchors 2022-01 .. 2026-06 ----
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
          if not (y == 2026 and m > 6)]
anchors = np.concatenate([src.month_anchors(ym) for ym in months])
anchors = np.unique(anchors)
yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
print("[replay] anchors=%d span=%s..%s" % (len(anchors),
      str(pd.Timestamp(src.ts[anchors[0]], unit="ms").date()),
      str(pd.Timestamp(src.ts[anchors[-1]], unit="ms").date())), flush=True)

# ---- C5 funding-risk (dispersion ref from full history) ----
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=DEFAULT_WEIGHTS, vol_gate=VolGate(src), funding_risk=frc)
chain_noRC = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_risk=None)   # ablation for FTX tail

# ---- C6 netting ----
net = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=COST_BPS)
res = net.run(anchors, src.ts)
print("[C6 netting] hedge_rate=%.1f%% gross_turn=%.0f net_turn=%.0f savings=%.1f bps/yr (0C: 86-179)" % (
    res["hedge_rate"] * 100, res["gross_turn_ann"], res["net_turn_ann"], res["savings_bps_yr"]), flush=True)

# ---- P&L from netted positions + net-of-cost ----
pos_by_t = {t: (m, p) for (t, m, p) in res["net_positions"]}
pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors)); prev = None; prev_m = None
for i, t in enumerate(anchors):
    m, p = pos_by_t[int(t)]
    ret = src.Y4[int(t), m]                                   # realized 4h fwd logret (fraction)
    ok = np.isfinite(ret)
    pnl[i] = float(np.nansum(p[ok] * ret[ok]))
    full = np.zeros(src.N); full[m] = p
    if prev is not None:
        turn[i] = float(np.abs(full - prev).sum())
    prev = full
cost = turn * COST_BPS * 1e-4
pnl_net = pnl - cost

# ---- aggregate anchor P&L -> DAILY, per-year DAILY Sharpe x sqrt(365) (0C book_assembly caliber) ----
day = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
dfp = pd.DataFrame({"day": day, "yr": yr, "pnl": pnl, "pnl_net": pnl_net})
daily = dfp.groupby("day").agg(pnl=("pnl", "sum"), pnl_net=("pnl_net", "sum"), yr=("yr", "first")).reset_index()


def dsharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


table = {}
for y in sorted(set(yr.tolist())):
    dd = daily[daily.yr == y]
    ics = np.array([c for c in (xsec_rank_ic(pos_by_t[int(t)][1], src.Y4[int(t), pos_by_t[int(t)][0]])
                                for t in anchors[yr == y]) if np.isfinite(c)])
    table[int(y)] = {"trading_days": int(len(dd)),
                     "gross_sharpe": round(dsharpe(dd["pnl"].values), 2),
                     "net_of_cost_sharpe": round(dsharpe(dd["pnl_net"].values), 2),
                     "mean_rank_ic": round(float(ics.mean()) if len(ics) else np.nan, 4)}

# ---- FTX funding-tail before/after C5 ----
ftx_t = int(np.argmin(np.abs(src.ts - int(pd.Timestamp("2022-11-09 00:00", tz="UTC").timestamp() * 1000))))
# nearest anchor to FTX day
ftx_anchor = int(anchors[np.argmin(np.abs(anchors - ftx_t))])
legs_rc, m = chain.leg_signals(ftx_anchor); legs_no, _ = chain_noRC.leg_signals(ftx_anchor)
ftx = {"anchor_date": str(pd.Timestamp(src.ts[ftx_anchor], unit="ms").date()),
       "funding_leg_max_abs_noRC": round(float(np.max(np.abs(legs_no["funding"]))), 2),
       "funding_leg_max_abs_withRC": round(float(np.max(np.abs(legs_rc["funding"]))), 2),
       "disp_gated_days": frc.n_gated}

out = {"anchors": int(len(anchors)), "cost_bps": COST_BPS,
       "netting": {k: (round(res[k], 3) if isinstance(res[k], float) else res[k])
                   for k in ["hedge_rate", "gross_turn_ann", "net_turn_ann", "savings_bps_yr", "years"]},
       "per_year": table, "ftx_funding_tail": ftx}
json.dump(out, open("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/engine_fullhist_replay.json", "w"), indent=1)
print(json.dumps(out, indent=1))
