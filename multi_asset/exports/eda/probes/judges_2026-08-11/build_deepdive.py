import json, numpy as np
EDA = "multi_asset/exports/eda/"
tk = json.load(open(EDA + "tick_vs_1s_raw.json"))
tc = json.load(open(EDA + "tickcorrected_apply_raw.json"))
br = json.load(open(EDA + "bar_regime_raw.json"))

# tick vs 1s aggregate
frr, mkt, mkb = [], [], []
for day in tk["days"]:
    t = tk["per_day"][day]["tick"]; b = tk["per_day"][day]["bar1s"]
    if t and b:
        frr.append(t["fill_rate"]["300"]["0.01"] / b["fill_rate"]["300"]["0.01"])
        mkt.append(t["markout_mean"]); mkb.append(b["markout_mean"])

# regime buckets (tick markout)
def bucket(lo, hi):
    xs = [(tk["per_day"][d]["tick"]) for d in tk["days"]
          if tk["per_day"][d]["tick"] and lo <= tk["per_day"][d]["tick"]["rvol_bps_min"] < hi]
    return dict(n=len(xs), markout=round(float(np.mean([x["markout_mean"] for x in xs])), 2),
                p25=round(float(np.mean([x["markout_p25"] for x in xs])), 1),
                fill=round(float(np.mean([x["fill_rate"]["300"]["0.01"] for x in xs])), 2))


yrs = ["2022", "2023", "2024", "2025", "2026"]


def sc(tag):
    r = tc["scenarios"][tag]
    return dict(net=[r.get(y, {}).get("net_sh") for y in yrs], cost24=r.get("2024", {}).get("eff_cost_bps"),
               fill24=r.get("2024", {}).get("fill"))


verdict = dict(
    title="Track-1 maker-fill DEEPDIVE — tick-level validation + regime stress", created="2026-07-12",
    auditor="0C",
    headline=("The 1s-bar approximation was OPTIMISTIC on BOTH axes and the biases do NOT offset (user's "
              "instinct correct): fill-rate overstated ~1.5x (tick/bar 0.6), and markout badly UNDER-stated "
              "adverse selection (1s ~0 vs tick -1 calm / -3 stress / -5.3 worst crash). BUT the book-level "
              "correction is MODEST: tick-corrected effective cost ~1.9 bps (normal) / ~2.7-2.9 (stress) vs "
              "Track-1 ~1.5; net Sharpe stays +8 to +20 EVERY year incl the stress-adverse scenario. PILOT "
              "VERDICT SURVIVES the tick correction. The concentrated residual risk is CRASH-DAY adverse "
              "selection (mean -5.3, p25 tail -20 bps) -> add a vol-gate."),
    part1_tick_validation=dict(
        method="true tick FIFO queue on Tardis µs book_snapshot_25 + trades (binance-futures BTCUSDT), 12 days",
        fill_ratio_tick_over_bar=round(float(np.mean(frr)), 2),
        fill_finding=("1s-bar OVERSTATES fill-rate ~1.5x because it counts ALL opposite-side volume as consuming "
                      "our queue, but tick-accurately only volume at price <=p0 does (when price drifts away, that "
                      "volume misses us). tick fill(1%,k300) 0.45-0.66 vs bar 0.75-0.96."),
        markout_tick_mean=round(float(np.mean(mkt)), 2), markout_bar_mean=round(float(np.mean(mkb)), 2),
        markout_finding=("1s markout was ~0/favorable (WRONG) — it missed adverse selection because the 1s "
                         "fill-time + 1s mid smear the µs adverse move. TRUE tick adverse selection: you fill "
                         "EXACTLY when aggressive flow hits you = when price is about to move against you."),
        cancel_exclusion="negligible (cancel-clear 0-9%): excluding cancels does NOT offset the aggregation optimism.",
        bias_offset_hypothesis="REFUTED — the biases compound (both optimistic), they do not cancel."),
    part2_regime=dict(
        fill_liquidity_invariance="HOLDS on crash days — cross-coin fill std TIGHTENS in stress (calm 0.084 -> "
                                  "stress 0.031); bar fill regime-stable (calm 0.87 / normal 0.88 / stress 0.95).",
        spread_widening="spreads widen ~2x in stress (calm 0.69 / normal 0.85 / stress 1.50 bps median).",
        tick_markout_by_regime=dict(calm=bucket(0, 7), normal=bucket(7, 18), stress=bucket(18, 999),
                                    worst_crash="2024-08-05 (rvol 29.8): markout -5.30, p25 -20.4"),
        stress_downgrade="adverse markout x3-5 (calm -1.0 -> stress -3.2 -> worst crash -5.3); p25 tail -3.8 "
                         "-> -20. fill-rate ~stable. crash days = MAX turnover = concentrated risk."),
    part4_tick_corrected_bound=dict(
        normal_adverse_5M=dict(full=sc("advnormal_AUM5M_k300_full"), calib=sc("advnormal_AUM5M_k300_calib")),
        stress_adverse_5M=dict(full=sc("advstress_AUM5M_k300_full"), calib=sc("advstress_AUM5M_k300_calib")),
        effective_cost="~1.9 bps (normal) / ~2.7-2.9 bps (stress) vs Track-1 ~1.5 — a modest +0.4-1.4 bps.",
        net_sharpe="+8 to +20 EVERY year, all AUM/k/tier/adverse scenarios; pilot survives."),
    verdict=dict(
        ruling="PILOT STILL WORTH IT (survives tick correction), with an ADDED vol-gate requirement.",
        revised_proposal=dict(
            size="$2-5M gross (higher fill at smaller size)",
            book="calib-grounded / mega+mid core; small tail optional",
            working="k=900s (15-min) passive -> DOUBLES maker fill (0.27->0.51) vs k=300; taker-complete residual",
            NEW_vol_gate=("★ on high-vol / crash days (BTC rvol > ~18 bps/min or a real-time vol trigger) REDUCE "
                          "participation / widen working window / lean taker-neutral — adverse selection blows to "
                          "-5 bps mean with a -20 bps tail; this is the concentrated risk (crash = max turnover)."),
            success_criteria=["realized adverse markout <= tick-measured (-1 calm / -3 stress)",
                              "realized fill >= 0.5 at k900",
                              "realized effective cost <= 2.5 bps (normal) / <= 3.5 bps (stress-day)"],
            stop_loss=["effective cost > 4 bps sustained", "crash-day markout tail worse than -25 bps",
                       "fill << tick curve at k900"])),
    honesty_caveats=[
        "★ tick markout is BTC-ONLY; ALT adverse selection is UNMEASURED and likely WORSE (less liquid -> more "
        "toxic flow). I applied the BTC markout uniformly -> a possible UNDER-estimate for the alt legs = the "
        "biggest residual uncertainty. A pilot should measure alt-leg markout live.",
        "static-order-at-p0 tick sim (no repricing) -> fill-rate is a LOWER bound; a chasing maker fills more. "
        "Truth is between tick (lazy) and bar (chasing); I used tick (conservative).",
        "fill-rate liquidity-invariance validated on BTC across regimes + bar cross-coin; assumed for the "
        "tick-corrected alt fills.",
        "net-Sharpe MAGNITUDE (8-20) retains the frequency x breadth caveat; the deployable conclusion is the "
        "effective COST (~1.9-2.9 bps tick-corrected) still << gross edge."],
    methodological_lesson=("1s-bar aggregation is NOT a conservative proxy for maker-fill economics — it is "
                           "OPTIMISTIC (overstates fill, misses adverse selection). Future execution modeling "
                           "MUST use tick data for markout; 1s bars are OK only for order-of-magnitude spread/notl."))
json.dump(verdict, open(EDA + "makerfill_deepdive.json", "w"), indent=2, default=str)
print("SAVED", EDA + "makerfill_deepdive.json")
print("fill ratio T/B", round(np.mean(frr), 2), "| tick mk mean", round(np.mean(mkt), 2), "| regime:",
      bucket(0, 7)["markout"], bucket(7, 18)["markout"], bucket(18, 999)["markout"])
