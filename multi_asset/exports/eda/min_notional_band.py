"""Min-notional no-trade band: closing a real backtest-caliber gap.

The canonical replay rebalances every name to target unconditionally. Live cannot: exchanges
enforce a minimum order notional (Binance $5 generic / BTC $50 / ETH,BCH,LTC,ETC,LINK $20;
Hyperliquid $10 flat). At $50k gross a single-name position is ~$455, so a 2% target move is a
~$9 child order -- right on HL's threshold. So live MUST have a no-trade band, and the backtest's
holding path is NOT the live one.

Two opposing forces, net effect unknown a priori:
  - turnover falls  -> cost falls        (helps)
  - skipped trades are exactly the SMALL signal moves, and cross-sectional return is spread over
    many small signals -> IC capture falls (hurts)

★ Also tested: is the band a free PARAMETER rather than a pure constraint? We sweep the exchange
  threshold x {1,2,5,10,20} looking for a net-Sharpe optimum.
  NOTE this is mechanically DIFFERENT from the known-failed EMA-hold experiment (which smoothed
  the SIGNAL and collapsed Sharpe to 2-3). A no-trade band does not touch the signal; it only
  skips uneconomic child orders. Independent test, as instructed.

CALIBER -- deployment-space normalisation:
  The canonical replay's P&L uses the raw book p (L1 gross ~0.4, drifting). A notional threshold
  is an ABSOLUTE dollar test, so the band study runs in DEPLOYMENT space: each anchor's book is
  normalised to unit gross q = p/||p||_1 and deployed at a constant gross G (matching the engine's
  "exposure is NOT modulated" stance). Sharpe is scale-invariant so this is comparable, but it is
  NOT bit-identical to the canonical number -- the no-band normalised baseline is reported
  explicitly as the reference row for every delta in this file.

Out: exports/eda/min_notional_band.{json,md}
"""
import os
import json, sys, time
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.vol_gate import VolGate
from engine.funding_risk import FundingLegRiskControl
from engine.netting import CrossLegNetting
from engine.ic_monitor import xsec_rank_ic

COST_BPS = 1.9
GROSSES = [50_000, 150_000, 500_000, 1_000_000]
MULTS = [0, 1, 2, 5, 10, 20]          # 0 = no band (reference)
WEIGHTS = {
    "champion": {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30},
    "challenger": {"king": 0.50, "s2": 0.17, "funding": 0.17, "size": 0.16},
}
BINANCE_MIN = {"BTCUSDT": 50.0, "ETHUSDT": 20.0, "BCHUSDT": 20.0, "LTCUSDT": 20.0,
               "ETCUSDT": 20.0, "LINKUSDT": 20.0}
BINANCE_DEFAULT = 5.0
HL_MIN = 10.0


def _dsharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def all_anchors(src):
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    yr = pd.to_datetime(src.ts[a], unit="ms", utc=True).year.to_numpy()
    return a, yr


def build_target_path(src, anchors, yr, weights):
    """Run the canonical chain+netting ONCE; return the unit-gross target book per anchor."""
    disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp_ref)
    chain = SignalChain(src, weights=weights, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=99.0)
    res = CrossLegNetting(chain, weights, cost_bps=COST_BPS).run(anchors, src.ts, year_of=yr)
    N = src.N
    Q = np.zeros((len(anchors), N))
    INUNIV = np.zeros((len(anchors), N), bool)
    RET = np.zeros((len(anchors), N))
    for i, (t, m, p) in enumerate(res["net_positions"]):
        g = np.abs(p).sum()
        if g > 1e-12:
            Q[i, m] = p / g
        INUNIV[i, m] = True
        r = src.Y4[t, m]
        RET[i, m] = np.where(np.isfinite(r), r, 0.0)
    return Q, INUNIV, RET


def simulate(Q, INUNIV, RET, thr_vec, gross, yr, days):
    """Walk the band path. Returns per-year metrics + diagnostics.

    Band rule: trade name i only if |dq_i| * gross >= thr_i. Names that have LEFT the universe are
    always traded to zero (reduce-only exits are allowed below min notional, and a stale position
    in a dropped name would otherwise linger forever) -- this choice is flagged in the output.
    """
    n_anch, N = Q.shape
    actual = np.zeros(N)
    pnl = np.zeros(n_anch); turn = np.zeros(n_anch)
    skipped_frac = np.zeros(n_anch); n_skipped = np.zeros(n_anch)
    net_exposure = np.zeros(n_anch); tracking = np.zeros(n_anch)
    ics = np.full(n_anch, np.nan)
    for i in range(n_anch):
        tgt = Q[i]
        delta = tgt - actual
        if thr_vec is None:
            trade = delta
        else:
            big = (np.abs(delta) * gross) >= thr_vec
            exited = (~INUNIV[i]) & (actual != 0.0)     # force-close names out of the universe
            trade = np.where(big | exited, delta, 0.0)
            want = np.abs(delta) > 1e-12
            n_skipped[i] = float((want & ~(big | exited)).sum())
            skipped_frac[i] = (float(np.abs(delta)[want & ~(big | exited)].sum())
                               / max(float(np.abs(delta).sum()), 1e-12))
        actual = actual + trade
        turn[i] = float(np.abs(trade).sum())
        pnl[i] = float(actual @ RET[i])
        net_exposure[i] = float(actual.sum())
        tracking[i] = float(np.abs(actual - tgt).sum())
        m = np.where(INUNIV[i])[0]
        if len(m) >= 8:
            ics[i] = xsec_rank_ic(actual[m], RET[i][m])
    cost = turn * COST_BPS * 1e-4
    pnl_net = pnl - cost
    dfp = pd.DataFrame({"day": days, "yr": yr, "pnl": pnl, "pnl_net": pnl_net})
    daily = dfp.groupby("day").agg(pnl=("pnl", "sum"), pnl_net=("pnl_net", "sum"),
                                   yr=("yr", "first")).reset_index()
    years = sorted(set(int(y) for y in yr))
    per_year = {}
    for y in years:
        dd = daily[daily.yr == y]
        sel = yr == y
        iy = ics[sel]; iy = iy[np.isfinite(iy)]
        per_year[int(y)] = {"net_sharpe": round(_dsharpe(dd["pnl_net"].values), 2),
                            "gross_sharpe": round(_dsharpe(dd["pnl"].values), 2),
                            "rank_ic": round(float(iy.mean()) if len(iy) else np.nan, 4),
                            "turn_per_anchor": round(float(turn[sel].mean()), 4)}
    anch_per_yr = len(Q) / ((days.max() - days.min()) / 365.25)
    icv = ics[np.isfinite(ics)]
    return {
        "per_year": per_year,
        "avg_net_sharpe": round(float(np.mean([per_year[y]["net_sharpe"] for y in years])), 2),
        "avg_rank_ic": round(float(np.mean([per_year[y]["rank_ic"] for y in years])), 4),
        "mean_rank_ic_all": round(float(icv.mean()), 5),
        "turn_ann": round(float(turn.sum() / ((days.max() - days.min()) / 365.25)), 1),
        "turn_per_anchor": round(float(turn.mean()), 4),
        "mean_skipped_name_count": round(float(n_skipped.mean()), 2),
        "mean_skipped_turnover_frac": round(float(skipped_frac.mean()), 4),
        "mean_abs_net_exposure": round(float(np.abs(net_exposure).mean()), 5),
        "mean_tracking_error_l1": round(float(tracking.mean()), 4),
        "eff_cost_bps_of_gross_per_yr": round(float(turn.sum()
                                                    / ((days.max() - days.min()) / 365.25)
                                                    * COST_BPS), 1),
    }


def main():
    t0 = time.time()
    src = PanelSource()
    anchors, yr = all_anchors(src)
    days = (src.ts[anchors] // (1000 * 3600 * 24)).astype(np.int64)
    syms = src.symbols

    thr = {}
    thr["binance"] = np.array([BINANCE_MIN.get(s, BINANCE_DEFAULT) for s in syms], float)
    thr["hyperliquid"] = np.full(len(syms), HL_MIN, float)

    out = {"meta": {
        "created": "2026-07-25",
        "caliber": ("DEPLOYMENT space: book normalised to unit gross each anchor and deployed at "
                    "constant gross G. Sharpe is scale-invariant so deltas are valid, but the "
                    "no-band row here is NOT bit-identical to the canonical 12.21 (which uses the "
                    "raw drifting-gross book). Every delta in this file is against the no-band "
                    "row of the SAME weights config."),
        "band_rule": ("trade name i only if |dq_i| * gross >= threshold_i; names that left the "
                      "universe are always traded to zero (reduce-only exit)"),
        "thresholds": {"binance": "generic $5, BTC $50, ETH/BCH/LTC/ETC/LINK $20",
                       "hyperliquid": "$10 flat"},
        "cost_bps": COST_BPS,
        "vs_ema_hold": ("mechanically different from the known-failed EMA-hold experiment: the "
                        "signal is untouched, only uneconomic child orders are skipped"),
    }, "results": {}}

    for wname, w in WEIGHTS.items():
        Q, INUNIV, RET = build_target_path(src, anchors, yr, w)
        base = simulate(Q, INUNIV, RET, None, 0, yr, days)
        out["results"][wname] = {"no_band": base, "grid": {}}
        print(f"\n=== {wname} === no-band: net Sharpe {base['avg_net_sharpe']:.2f} "
              f"turn/yr {base['turn_ann']:.0f} IC {base['avg_rank_ic']:.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
        for venue in ("binance", "hyperliquid"):
            for G in GROSSES:
                for mult in MULTS:
                    if mult == 0:
                        continue
                    r = simulate(Q, INUNIV, RET, thr[venue] * mult, G, yr, days)
                    key = f"{venue}|{G}|x{mult}"
                    r["d_sharpe_vs_noband"] = round(r["avg_net_sharpe"]
                                                    - base["avg_net_sharpe"], 2)
                    r["ic_capture"] = round(r["avg_rank_ic"] / base["avg_rank_ic"], 4)
                    r["turn_ratio"] = round(r["turn_ann"] / base["turn_ann"], 4)
                    out["results"][wname]["grid"][key] = r
                print(f"  [{venue:12s} G=${G:>9,}] " + " | ".join(
                    f"x{m}: Sh {out['results'][wname]['grid'][f'{venue}|{G}|x{m}']['avg_net_sharpe']:5.2f}"
                    f" ({out['results'][wname]['grid'][f'{venue}|{G}|x{m}']['d_sharpe_vs_noband']:+.2f})"
                    f" turn {out['results'][wname]['grid'][f'{venue}|{G}|x{m}']['turn_ratio']:.2f}"
                    for m in MULTS if m != 0), flush=True)
    json.dump(out, open(MA + "/exports/eda/min_notional_band.json", "w"), indent=1)
    print(f"\n-> min_notional_band.json ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
