"""Live shadow — champion/challenger dual track on LEG WEIGHTS (0C weight review).

0C's review found king=0.30 is a DOMINATED choice: king->0.50 lifts Sharpe 10.16->12.58 with the
worst year / worst month / max drawdown / negative-day share ALL improving simultaneously, and it
survived five falsification attempts. But every one of those five is a BACKTEST. The only thing
that can close that gap is out-of-sample shadow evidence -- which is what this module produces.

  champion   = king .30 / s2 .10 / funding .30 / size .30   (unchanged; this is what pilot ships)
  challenger = king .50 / s2 .17 / funding .17 / size .16

Same signal, same anchors, same execution assumptions -- ONLY the leg weights differ, so the
difference is attributable to the weights and nothing else.

*** This module is ADDITIVE. It does not touch canonical, does not touch the pilot's default
    weights, and is wired into run_daily.sh as a NON-FATAL step so it can never break the champion
    pipeline. ***

Pre-registered acceptance criteria are in exports/live/challenger/README.md and are frozen BEFORE
data accumulates -- do not revise them after seeing results.

Out: exports/live/challenger/{positions/, pnl_daily.csv, compare.json, daily_report.md}
"""
import glob, json, os, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")

OUT = MA + "/exports/live/challenger"
POS = OUT + "/positions"
CHAMP_POS = MA + "/exports/live/positions"
FILL = 0.51                       # same conservative maker-fill model as paper_pnl.py
COST_CALM, COST_STRESS = 1.9, 2.9
RVOL_STRESS = 18.0

CHAMPION = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
CHALLENGER = {"king": 0.50, "s2": 0.17, "funding": 0.17, "size": 0.16}


def _positions_w(src, anchors, weights):
    """Canonical rank+cap chain + 4h-sync netting under arbitrary leg weights -> unit-gross book."""
    from engine.signal_chain import SignalChain
    from engine.netting import CrossLegNetting
    chain = SignalChain(src, weights=weights, funding_mode="rank", pos_cap_pct=99.0)
    net = CrossLegNetting(chain, weights, cost_bps=1.9)
    yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
    res = net.run(anchors, src.ts, year_of=yr)
    out = {}
    for (t, m, p) in res["net_positions"]:
        g = float(np.abs(p).sum())
        out[int(t)] = (m, (p / g if g > 1e-12 else p))
    return out


def _leg_only(src, anchors, leg):
    """Single-leg unit-gross book (for the funding-leg stress-tail criterion)."""
    w = {k: (1.0 if k == leg else 0.0) for k in CHAMPION}
    return _positions_w(src, anchors, w)


def run(verbose=True):
    os.makedirs(POS, exist_ok=True)
    import signal_loop as SL
    from engine.ic_monitor import xsec_rank_ic, ICMonitor, RetrainTrigger

    src = SL._panelsource_live()
    anchors = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                                & np.isfinite(src.s2)).any(1))[0])
    open_month = pd.to_datetime(src.ts[anchors].max(), unit="ms", utc=True).strftime("%Y-%m")

    champ4 = _positions_w(src, anchors, CHAMPION)
    chall4 = _positions_w(src, anchors, CHALLENGER)
    champ3 = _positions_w(src, anchors, {**CHAMPION, "funding": 0.0})     # Curve A (open month)
    chall3 = _positions_w(src, anchors, {**CHALLENGER, "funding": 0.0})
    fund_leg = _leg_only(src, anchors, "funding")

    syms = np.array(src.symbols)
    frozen_end = int(np.load(SL.KING_FROZEN, allow_pickle=True)["ts"].max())
    new_anchors = anchors[src.ts[anchors] > frozen_end]
    for t in new_anchors:
        ti = int(t); d = pd.to_datetime(src.ts[ti], unit="ms", utc=True)
        rec = {"anchor_ts_ms": int(src.ts[ti]), "anchor_utc": d.isoformat(), "horizon_h": 4,
               "track": "challenger", "weights": CHALLENGER,
               "schema": "target_weight (unit-gross, market-neutral); same schema as the champion feed",
               "curve": {
                   "A_provisional_3leg": {"positions": {syms[j]: round(float(w), 8)
                                                        for j, w in zip(*chall3[ti])}},
                   "B_backfilled_4leg": {"positions": {syms[j]: round(float(w), 8)
                                                       for j, w in zip(*chall4[ti])}}}}
        json.dump(rec, open(f"{POS}/positions_{d.strftime('%Y%m%d_%H')}.json", "w"), indent=1)

    # ---- paired P&L / IC on MATURED anchors (identical execution model for both tracks) ----
    rows = []
    ic_mon = {"champion": ICMonitor(window=60), "challenger": ICMonitor(window=60)}
    trig = RetrainTrigger(margin=0.003, persist=20)
    switches = []
    prev = {"champion": np.zeros(src.N), "challenger": np.zeros(src.N)}
    for t in anchors:
        ti = int(t)
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        rvol = src.btc_rvol_bps_min(ti)
        stress = bool(np.isfinite(rvol) and rvol > RVOL_STRESS)
        cost = COST_STRESS if stress else COST_CALM
        d = pd.to_datetime(src.ts[ti], unit="ms", utc=True)
        row = {"day": d.strftime("%Y-%m-%d"), "anchor_utc": d.isoformat(),
               "regime": "stress" if stress else "calm",
               # anchors past the frozen panel are the only genuinely OUT-OF-SAMPLE evidence;
               # everything at or before it is the backtest restated and proves nothing new.
               "is_shadow": bool(int(src.ts[ti]) > frozen_end)}
        for name, book in (("champion", champ4), ("challenger", chall4)):
            m, p = book[ti]
            w = np.zeros(src.N); w[m] = p
            ok = np.isfinite(ret)
            gross = float(np.nansum(w[ok] * ret[ok]))
            turn = float(np.abs(w - prev[name]).sum()); prev[name] = w
            row[f"{name}_gross"] = gross
            row[f"{name}_turn"] = turn
            row[f"{name}_net"] = FILL * (gross - turn * cost * 1e-4)
            row[f"{name}_ic"] = xsec_rank_ic(p, ret[m])
            ic_mon[name].update(ti, p, ret[m])
        mF, pF = fund_leg[ti]
        row["funding_leg_pnl"] = float(np.nansum(pF * np.where(np.isfinite(ret[mF]), ret[mF], 0.0)))
        if trig.step(ti, ic_mon["champion"].rolling_ic(), ic_mon["challenger"].rolling_ic()):
            switches.append({"anchor_utc": d.isoformat(), "is_shadow": row["is_shadow"]})
        rows.append(row)

    if not rows:
        json.dump({"n_anchors": 0, "note": "no matured anchors yet"},
                  open(OUT + "/compare.json", "w"), indent=1)
        if verbose:
            print("[challenger] no matured anchors yet", flush=True)
        return
    df_all = pd.DataFrame(rows)
    df_all["d_net"] = df_all["challenger_net"] - df_all["champion_net"]
    df_all["d_ic"] = df_all["challenger_ic"] - df_all["champion_ic"]
    # ★ THE EVIDENCE is the shadow slice only. The frozen-panel slice is the backtest restated;
    # reporting it as if it were shadow confirmation would be circular.
    df = df_all[df_all.is_shadow].copy()
    shadow_only = len(df) > 0
    if not shadow_only:
        df = df_all.copy()
    daily = df.groupby("day").agg(champion_net=("champion_net", "sum"),
                                  challenger_net=("challenger_net", "sum"),
                                  d_net=("d_net", "sum"),
                                  champion_turn=("champion_turn", "sum"),
                                  challenger_turn=("challenger_turn", "sum"),
                                  funding_leg_pnl=("funding_leg_pnl", "sum")).reset_index()
    daily["cum_champion"] = daily["champion_net"].cumsum()
    daily["cum_challenger"] = daily["challenger_net"].cumsum()
    daily.to_csv(OUT + "/pnl_daily.csv", index=False)

    def sh(x):
        x = np.asarray(x, float); x = x[np.isfinite(x)]
        return (round(float(x.mean() / (x.std() + 1e-12) * np.sqrt(365.0)), 2)
                if len(x) > 2 else None)

    stress_days = df[df.regime == "stress"]
    q = df["funding_leg_pnl"].quantile(0.05)
    tail = df[df["funding_leg_pnl"] <= q]
    bt = df_all[~df_all.is_shadow]
    cmp_ = {
        "weights": {"champion": CHAMPION, "challenger": CHALLENGER},
        "★_scope": ("ALL metrics below are computed on the SHADOW slice only (anchors after the "
                    "frozen panel end) -- that is the only out-of-sample evidence, and closing "
                    "0C's stated gap is the entire point of this track. The frozen-panel slice is "
                    "the backtest restated and is reported separately under "
                    "`backtest_slice_NOT_evidence` purely as a sanity check."
                    if shadow_only else
                    "NO shadow anchors have matured yet -- the numbers below are the BACKTEST "
                    "slice and are NOT out-of-sample evidence. Treat as a plumbing check only."),
        "is_shadow_evidence": bool(shadow_only),
        "backtest_slice_NOT_evidence": ({
            "n_anchors": int(len(bt)),
            "mean_d_ic": round(float(bt["d_ic"].mean(skipna=True)), 5),
            "d_net_sum": round(float(bt["d_net"].sum()), 6),
            "note": "in-sample restatement of 0C's finding; proves nothing new"}
            if len(bt) else None),
        "n_anchors": int(len(df)), "n_days": int(len(daily)), "open_month": open_month,
        "execution_model": {"fill_rate": FILL, "cost_bps_calm": COST_CALM,
                            "cost_bps_stress": COST_STRESS, "rvol_stress_bps_min": RVOL_STRESS},
        "criterion_a_daily_pnl_direction": {
            "days_challenger_better": int((daily["d_net"] > 0).sum()),
            "days_total": int(len(daily)),
            "win_rate": round(float((daily["d_net"] > 0).mean()), 4),
            "cum_champion": round(float(daily["cum_champion"].iloc[-1]), 6),
            "cum_challenger": round(float(daily["cum_challenger"].iloc[-1]), 6),
            "daily_sharpe_champion": sh(daily["champion_net"]),
            "daily_sharpe_challenger": sh(daily["challenger_net"])},
        "criterion_b_rank_ic": {
            "mean_ic_champion": round(float(df["champion_ic"].mean(skipna=True)), 5),
            "mean_ic_challenger": round(float(df["challenger_ic"].mean(skipna=True)), 5),
            "mean_d_ic": round(float(df["d_ic"].mean(skipna=True)), 5),
            "t_stat_d_ic": round(float(df["d_ic"].mean(skipna=True)
                                       / (df["d_ic"].std(skipna=True) + 1e-12)
                                       * np.sqrt(df["d_ic"].notna().sum())), 2),
            "rolling_ic_champion": round(ic_mon["champion"].rolling_ic(), 5),
            "rolling_ic_challenger": round(ic_mon["challenger"].rolling_ic(), 5),
            "c4_switch_signals_shadow": [s for s in switches if s["is_shadow"]],
            "c4_switch_signals_total_incl_backtest": len(switches)},
        "criterion_c_funding_leg_stress_tail": {
            "n_stress_anchors": int(len(stress_days)),
            "d_net_on_stress_anchors": round(float(stress_days["d_net"].sum()), 6)
            if len(stress_days) else None,
            "funding_leg_p05_pnl": round(float(q), 6),
            "n_tail_anchors": int(len(tail)),
            "champion_net_on_funding_tail": round(float(tail["champion_net"].sum()), 6),
            "challenger_net_on_funding_tail": round(float(tail["challenger_net"].sum()), 6),
            "note": ("0C: the book's fattest left tail is manufactured by the funding leg itself "
                     "(FTX day: solo-funding -0.98% vs whole-book -0.94%). The challenger holds "
                     "LESS funding (0.17 vs 0.30), so it should suffer less here -- if it does not, "
                     "that is evidence against the re-weighting.")},
        "turnover": {"champion_per_anchor": round(float(df["champion_turn"].mean()), 4),
                     "challenger_per_anchor": round(float(df["challenger_turn"].mean()), 4),
                     "ratio": round(float(df["challenger_turn"].mean()
                                          / (df["champion_turn"].mean() + 1e-12)), 3)},
        "caliber": ("shadow paper P&L under the conservative maker-fill model; NOT a fund net "
                    "return. Both tracks share the identical execution model, so the DIFFERENCE "
                    "is the meaningful quantity, not either level."),
    }
    json.dump(cmp_, open(OUT + "/compare.json", "w"), indent=1)

    a = cmp_["criterion_a_daily_pnl_direction"]; b = cmp_["criterion_b_rank_ic"]
    c = cmp_["criterion_c_funding_leg_stress_tail"]
    with open(OUT + "/daily_report.md", "w") as f:
        f.write(f"# Challenger dual-track — {daily['day'].iloc[-1]}\n\n")
        f.write(f"champion {CHAMPION} vs challenger {CHALLENGER}\n\n")
        f.write(("**Scope: SHADOW (out-of-sample) anchors only — this is the evidence.**\n\n"
                 if shadow_only else
                 "**⚠ No shadow anchors matured yet — numbers below are the BACKTEST slice, "
                 "NOT out-of-sample evidence. Plumbing check only.**\n\n"))
        f.write(f"- **(a) daily P&L**: challenger better on {a['days_challenger_better']}/"
                f"{a['days_total']} days (win rate {a['win_rate']:.2f}); cum "
                f"{a['cum_challenger']:.5f} vs {a['cum_champion']:.5f}; daily Sharpe "
                f"{a['daily_sharpe_challenger']} vs {a['daily_sharpe_champion']}\n")
        f.write(f"- **(b) rank-IC**: {b['mean_ic_challenger']:.5f} vs {b['mean_ic_champion']:.5f} "
                f"(Δ {b['mean_d_ic']:+.5f}, t {b['t_stat_d_ic']:+.2f}); C4 switch signals "
                f"(shadow): {len(b['c4_switch_signals_shadow'])}\n")
        f.write(f"- **(c) funding-leg tail**: on the worst 5% funding-leg anchors, challenger "
                f"{c['challenger_net_on_funding_tail']:.5f} vs champion "
                f"{c['champion_net_on_funding_tail']:.5f}\n")
        f.write(f"- turnover ratio challenger/champion: {cmp_['turnover']['ratio']:.2f}\n\n")
        f.write(f"> **{a['days_total']} shadow days so far; the pre-registered rule needs >=60 "
                f"before a switch may be proposed.** Annualised Sharpe on this few days is "
                f"extremely noisy — read the direction, not the level.\n\n")
        f.write("> Shadow paper caliber, not a fund net return. Pre-registered criteria in "
                "README.md — do not revise after seeing results.\n")
    if verbose:
        print(f"[challenger] {len(df)} anchors / {len(daily)} days | "
              f"win rate {a['win_rate']:.2f} | dIC {b['mean_d_ic']:+.5f} "
              f"(t {b['t_stat_d_ic']:+.2f}) | turn ratio {cmp_['turnover']['ratio']:.2f}",
              flush=True)
        print(f"[challenger] -> {OUT}/", flush=True)


if __name__ == "__main__":
    run()
