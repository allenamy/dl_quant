"""A7 — Liquidity & cost tiering.

Sample ~20 days. Per asset:
  - median spread_bps = (ask - bid) / mid * 1e4
  - effective half-spread (bps) = spread_bps / 2
  - depth-to-move cost (bps) to execute a fixed USD notional (10k and 100k) by walking
    the cumulative depth buckets cumu_{ask}sz_dep_X.

Depth bucket semantics (verified): suffix X = bps distance from mid; cumu_asksz_dep_X is
the CUMULATIVE base-asset size resting within X bps ABOVE mid (ask side). To buy a
notional we walk increasing X; the *incremental* size between consecutive buckets
(dep_{X_{i}} - dep_{X_{i-1}}) is attributable to a price level <= X_i bps. We assign each
increment the bucket's bps level X_i (a conservative upper bound on fill price within that
bucket) and compute the size-weighted average fill bps to fill the requested notional.
cost_bps = VWAP_fill_bps (i.e. slippage above mid; this already INCLUDES crossing the
half-spread since the inner buckets sit at/above the best ask). We report the ASK side
(buy) cost; bid side is symmetric for a sell.

If the requested notional exceeds total visible depth (dep_1000.0), cost is reported as
the deepest bucket level (1000 bps) flagged as ">depth" via a sentinel and counted.

GOAL: tier assets tradeable (low cost) vs predict-only/source-only (high cost).
Placeholder column `predicted_edge_bps` left None for the controller to merge with A2.

Read-only.
"""
from __future__ import annotations

import json
import os.path as p

import numpy as np

from _eda_common import (SYMBOLS, list_all_days, sample_days_spread, col,
                         day_exists, ensure_export_dir)

DEPTHS_BPS = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
NOTIONALS = [10_000.0, 100_000.0]


def walk_cost_bps(mid, cum_sizes, notional):
    """Cost (bps above mid) to buy `notional` USD walking ask cumulative depth.

    cum_sizes : array len(DEPTHS_BPS), cumulative base-asset size within each bps bucket.
    Returns (cost_bps, filled_fully_bool).
    Incremental size in bucket i = cum_sizes[i] - cum_sizes[i-1], priced at DEPTHS_BPS[i] bps.
    """
    target_base = notional / mid  # base units needed (mid-priced target qty)
    filled = 0.0
    weighted_bps = 0.0
    prev = 0.0
    for i, lvl in enumerate(DEPTHS_BPS):
        inc = cum_sizes[i] - prev
        prev = cum_sizes[i]
        if inc <= 0:
            continue
        take = min(inc, target_base - filled)
        if take <= 0:
            break
        weighted_bps += take * lvl
        filled += take
        if filled >= target_base - 1e-12:
            break
    if filled < target_base * 0.999:
        # not enough visible depth: charge remainder at deepest level (1000 bps)
        rem = target_base - filled
        weighted_bps += rem * DEPTHS_BPS[-1]
        filled += rem
        return weighted_bps / filled, False
    return weighted_bps / filled, True


def main():
    all_days = list_all_days()
    days = sample_days_spread(all_days, n=20, start=20230101, end=20251130)
    days = [d for d in days if day_exists(d)]
    print("# A7 — Liquidity & cost tiering")
    print(f"Sampling: {len(days)} days spread 2023-2025: {days[0]}..{days[-1]}.")
    print("Depth suffix X = bps from mid; cost walks cumulative ask depth (buy side).\n")

    acc = {s: {"spread_bps": [], **{f"cost_{int(n)}": [] for n in NOTIONALS},
               **{f"unfilled_{int(n)}": 0 for n in NOTIONALS}, "n_obs": 0}
           for s in SYMBOLS}

    for d in days:
        try:
            from multi_asset.data.bar_loader import load_day_panel
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] day {d} load failed: {e}")
            continue
        for s in SYMBOLS:
            mid = col(dp, s, "mid")
            bid = col(dp, s, "bid")
            ask = col(dp, s, "ask")
            cum = np.stack([col(dp, s, f"cumu_asksz_dep_{X}") for X in DEPTHS_BPS], axis=1)

            valid = np.isfinite(mid) & np.isfinite(bid) & np.isfinite(ask) & (mid > 0)
            valid &= np.isfinite(cum).all(axis=1)
            if valid.sum() < 100:
                continue
            # subsample rows for speed: every 60s
            idx = np.where(valid)[0][::60]
            if idx.size == 0:
                continue
            sp = (ask[idx] - bid[idx]) / mid[idx] * 1e4
            acc[s]["spread_bps"].append(sp)
            acc[s]["n_obs"] += idx.size
            for notion in NOTIONALS:
                costs = np.empty(idx.size)
                nunf = 0
                for j, t in enumerate(idx):
                    c, ok = walk_cost_bps(mid[t], cum[t], notion)
                    costs[j] = c
                    if not ok:
                        nunf += 1
                acc[s][f"cost_{int(notion)}"].append(costs)
                acc[s][f"unfilled_{int(notion)}"] += nunf

    out = {}
    for s in SYMBOLS:
        a = acc[s]
        if a["n_obs"] == 0:
            out[s] = {"n_obs": 0, "note": "no_valid_obs"}
            continue
        sp = np.concatenate(a["spread_bps"])
        rec = {
            "n_obs": int(a["n_obs"]),
            "median_spread_bps": round(float(np.median(sp)), 4),
            "p90_spread_bps": round(float(np.percentile(sp, 90)), 4),
            "eff_half_spread_bps": round(float(np.median(sp)) / 2.0, 4),
        }
        for notion in NOTIONALS:
            c = np.concatenate(a[f"cost_{int(notion)}"])
            rec[f"cost_{int(notion//1000)}k_bps_med"] = round(float(np.median(c)), 4)
            rec[f"cost_{int(notion//1000)}k_bps_p90"] = round(float(np.percentile(c, 90)), 4)
            rec[f"unfilled_frac_{int(notion//1000)}k"] = round(
                a[f"unfilled_{int(notion)}"] / max(a["n_obs"], 1), 4)
        rec["predicted_edge_bps"] = None  # controller merges A2
        out[s] = rec

    # tiering heuristic on 100k round-trip cost (2x one-way ~ spread + 2*slippage)
    for s in SYMBOLS:
        o = out[s]
        if o.get("n_obs", 0) == 0:
            o["tier"] = "no_data"
            continue
        rt_100k = 2.0 * o["cost_100k_bps_med"]  # round trip at 100k
        if rt_100k < 5:
            o["tier"] = "tradeable_liquid"
        elif rt_100k < 15:
            o["tier"] = "tradeable_moderate"
        elif rt_100k < 40:
            o["tier"] = "marginal"
        else:
            o["tier"] = "predict_or_source_only"
        o["roundtrip_100k_bps"] = round(rt_100k, 3)

    result = {
        "analysis": "A7_cost_tiers",
        "sampling": f"{len(days)} days spread 2023-2025: {days[0]}..{days[-1]}, rows every 60s",
        "depths_bps": DEPTHS_BPS,
        "notionals_usd": NOTIONALS,
        "cost_def": "VWAP fill bps above mid walking cumulative ask depth (incl. half-spread)",
        "tier_def": "by 2x one-way 100k cost: <5 liquid, <15 moderate, <40 marginal, else predict/source-only",
        "per_symbol": out,
    }
    ed = ensure_export_dir()
    with open(p.join(ed, "a7_cost_tiers.json"), "w") as f:
        json.dump(result, f, indent=2)

    print("| sym | med_spread_bps | eff_half_sp | cost_10k_med | cost_100k_med | "
          "cost_100k_p90 | unfilled_100k | rt_100k_bps | tier |")
    print("|-----|----------------|-------------|--------------|---------------|"
          "---------------|---------------|-------------|------|")
    for s in SYMBOLS:
        o = out[s]
        if o.get("n_obs", 0) == 0:
            print(f"| {s} | - | - | - | - | - | - | - | no_data |")
            continue
        print(f"| {s} | {o['median_spread_bps']} | {o['eff_half_spread_bps']} | "
              f"{o['cost_10k_bps_med']} | {o['cost_100k_bps_med']} | "
              f"{o['cost_100k_bps_p90']} | {o['unfilled_frac_100k']} | "
              f"{o['roundtrip_100k_bps']} | {o['tier']} |")
    print(f"\nWrote {p.join(ed, 'a7_cost_tiers.json')}")


if __name__ == "__main__":
    main()
