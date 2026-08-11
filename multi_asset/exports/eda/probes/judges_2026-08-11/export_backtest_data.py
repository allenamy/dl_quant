"""Export the backtest data package — factors, positions, membership, reference — from the
assembled panel + prediction panels + the engine. Data-only output (no source in the package).

Produces under exports/live/backtest_pkg/:
  factors_panel.parquet       ts x symbol: the four leg signals (king/S2 OOS predictions +
                              funding/SIZE factor values) + membership, 2023-01 .. 2026-06.
  positions_history.parquet   ts x symbol: the combined market-neutral target weight per 4h anchor
                              (post-netting, post-risk-shaping), same window.
  universe_membership.parquet ts x symbol: point-in-time membership (survivorship-safe), same window.
  reference_results.csv       per-year reconciliation: gross/net Sharpe at several cost levels,
                              rank-IC, turnover, worst calendar month (all five years).
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS, _l1
from engine.netting import CrossLegNetting

OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/backtest_pkg"
COST_MAKER = 1.9        # bps/side, calm maker
COST_STRESS = 2.9       # bps/side, stressed maker
COST_TAKER = 9.5        # bps/side, taker (illustrative — the book is not taker-viable)
WINDOW = ("2023-01", "2026-06")


def _anchors(src, y0=2022, y1=2027):
    months = [f"{y}-{m:02d}" for y in range(y0, y1) for m in range(1, 13) if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    return a


def _sharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def build(src):
    os.makedirs(OUT, exist_ok=True)
    anchors = _anchors(src)
    ts = src.ts; dtA = pd.to_datetime(ts[anchors], unit="ms", utc=True)
    yr = dtA.year.to_numpy()
    syms = np.array(src.symbols)

    # ---- canonical engine: rank funding + 99% cap + 4h-sync netting -> net positions per anchor ----
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", pos_cap_pct=99.0)
    net = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=COST_MAKER)
    res = net.run(anchors, ts, year_of=yr)
    # Renormalize each anchor's net book to UNIT GROSS (Σ|w| = 1). The four legs partially cancel when
    # combined at book weights, leaving raw gross ~0.5; renorming makes "multiply by notional G" give
    # exactly G gross. Scale-invariant for Sharpe/IC; reference_results below is derived from THIS same
    # unit-gross series so positions_history and reference reconcile exactly.
    def _unit_gross(p):
        g = float(np.abs(p).sum())
        return p / g if g > 1e-12 else p
    pos_by_t = {int(t): (m, _unit_gross(p)) for (t, m, p) in res["net_positions"]}

    # ---- per-anchor P&L, turnover, rank-IC ----
    N = src.N
    pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors)); ic = np.full(len(anchors), np.nan)
    prev = np.zeros(N)
    for i, t in enumerate(anchors):
        ti = int(t); m, p = pos_by_t[ti]
        ret = src.Y4[ti, m]; ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(p[ok] * ret[ok]))
        full = np.zeros(N); full[m] = p
        turn[i] = float(np.abs(full - prev).sum()); prev = full
        if ok.sum() >= 5 and np.std(p[ok]) > 1e-12:
            ic[i] = np.corrcoef(rankdata(p[ok]), rankdata(ret[ok]))[0, 1]

    day = (ts[anchors] // 86400000).astype(np.int64)
    month = dtA.strftime("%Y-%m").to_numpy()
    dfp = pd.DataFrame({"day": day, "yr": yr, "month": month, "pnl": pnl, "turn": turn, "ic": ic})

    def year_row(y):
        d = dfp[dfp.yr == y]
        dl = d.groupby("day").agg(g=("pnl", "sum"), t=("turn", "sum")).reset_index()
        gross = dl["g"].values
        def net_sh(cost):
            return round(_sharpe(gross - dl["t"].values * cost * 1e-4), 2)
        # worst calendar month (gross monthly return, in units of daily-sum bps-fraction)
        mm = d.groupby("month")["pnl"].sum()
        return {
            "year": int(y), "trading_days": int(len(dl)),
            "gross_sharpe": round(_sharpe(gross), 2),
            "net_sharpe_maker_1.9bps": net_sh(COST_MAKER),
            "net_sharpe_stress_2.9bps": net_sh(COST_STRESS),
            "net_sharpe_taker_9.5bps": net_sh(COST_TAKER),
            "mean_rank_ic": round(float(np.nanmean(d["ic"])), 4),
            "avg_anchor_turnover": round(float(d["turn"].mean()), 3),
            "worst_calendar_month_pnl": round(float(mm.min()), 5),
        }

    ref = pd.DataFrame([year_row(y) for y in sorted(set(int(x) for x in yr))])
    ref.to_csv(f"{OUT}/reference_results.csv", index=False)

    # ---- window mask for the row-level exports ----
    w0 = pd.Timestamp(WINDOW[0] + "-01", tz="UTC"); w1 = pd.Timestamp(WINDOW[1] + "-01", tz="UTC") + pd.offsets.MonthBegin(1)
    in_win = np.asarray((dtA >= w0) & (dtA < w1))
    win_anchors = anchors[in_win]

    # ---- factors_panel + membership (long format over member coins) ----
    frows, prows, mrows = [], [], []
    fi, si = src.fund_idx, src.size_idx
    for t in win_anchors:
        ti = int(t); tms = int(ts[ti]); d = pd.to_datetime(tms, unit="ms", utc=True)
        mem = np.where(src.member[ti])[0]
        for j in mem:
            mrows.append((tms, syms[j], True))
        trad = src.tradeable(ti)
        for j in trad:
            frows.append((tms, syms[j], src.king[ti, j], src.s2[ti, j],
                          float(src.CH[ti, j, fi]), float(src.CH[ti, j, si])))
        m, p = pos_by_t[ti]
        for jj, j in enumerate(m):
            prows.append((tms, syms[j], float(p[jj])))

    fdf = pd.DataFrame(frows, columns=["ts_ms", "symbol", "king_score", "s2_score", "funding_ema", "size_dvol"])
    fdf["datetime_utc"] = pd.to_datetime(fdf["ts_ms"], unit="ms", utc=True)
    fdf = fdf[["ts_ms", "datetime_utc", "symbol", "king_score", "s2_score", "funding_ema", "size_dvol"]]
    fdf.to_parquet(f"{OUT}/factors_panel.parquet", index=False)

    pdf = pd.DataFrame(prows, columns=["ts_ms", "symbol", "target_weight"])
    pdf["datetime_utc"] = pd.to_datetime(pdf["ts_ms"], unit="ms", utc=True)
    pdf = pdf[["ts_ms", "datetime_utc", "symbol", "target_weight"]]
    pdf.to_parquet(f"{OUT}/positions_history.parquet", index=False)

    mdf = pd.DataFrame(mrows, columns=["ts_ms", "symbol", "member"])
    mdf["datetime_utc"] = pd.to_datetime(mdf["ts_ms"], unit="ms", utc=True)
    mdf = mdf[["ts_ms", "datetime_utc", "symbol", "member"]]
    mdf.to_parquet(f"{OUT}/universe_membership.parquet", index=False)

    print(f"[export] factors {len(fdf):,} rows | positions {len(pdf):,} | membership {len(mdf):,} | "
          f"anchors(window) {len(win_anchors)} | reference years {len(ref)}", flush=True)
    print(f"[export] window {WINDOW[0]}..{WINDOW[1]} | netting hedge {res['hedge_rate']*100:.1f}% "
          f"savings {res['savings_bps_yr']:.0f}bps/yr", flush=True)
    print("reference_results:\n" + ref.to_string(index=False), flush=True)
    return dict(factors=len(fdf), positions=len(pdf), membership=len(mdf), anchors=len(win_anchors))


if __name__ == "__main__":
    build(PanelSource())
