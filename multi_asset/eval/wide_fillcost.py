#!/usr/bin/env python3
"""Wide-book fill/effective-cost note (#4b) — honest execution pass for the 110-coin L/S book.

The wide-universe net-cost tiers earlier assumed megacap-grade execution. The 110-coin book
includes small caps where a resting maker order fills only 30-75% and the unfilled remainder must
cross the spread (taker). This quantifies that for the ref arm's ACTUAL orders.

CAVEAT (stated up front): the wide universe has ONLY 1h OHLCV — no LOB depth / trade flow — so
unlike the M0 queue-reactive maker sim (real book), fills here are a PARAMETRIC function of the
per-coin liquidity tier (trailing-30d $volume). This is a tier estimate, not a queue simulation.
The FACTUAL parts (tier membership, order tier-composition, turnover) are assumption-free; the
fill%/bps per tier are labeled assumptions bracketing the team-lead's 30-75% range.

Output: per-tier effective-cost vector + the ref book's tier composition + turnover -> hand 0C.
Usage: PYTHONPATH=. python multi_asset/data/../eval/wide_fillcost.py [--tag wideA_conformer_ref] [--q 0.2]
"""
from __future__ import annotations
import argparse
import os.path as p

import numpy as np

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"

# --- parametric fill model by liquidity tier (LABELED ASSUMPTIONS; no LOB on the wide universe) ---
# daily $vol thresholds (DVOL30 is trailing-30d mean HOURLY quote vol -> *24 ~ daily).
TIERS = [  # (name, daily_$vol_min, maker_fill_frac, filled_cost_bps, unfilled_taker_bps)
    ("mega", 500e6, 0.90, 2.0, 5.0),      # BTC/ETH-grade: near-complete maker fill, tight spread
    ("mid",   50e6, 0.65, 4.0, 9.0),      # liquid alts: partial fill, moderate spread
    ("small",   0.0, 0.45, 8.0, 18.0),    # small caps: 30-75% fill, wide spread + taker crossing
]


def _tier_idx(daily_dvol):
    for i, (_nm, lo, *_x) in enumerate(TIERS):
        if daily_dvol >= lo:
            return i
    return len(TIERS) - 1


def eff_cost_bps(tier_i):
    """Blended effective cost for one unit of target notional in a tier: fill*filled + (1-fill)*taker."""
    _nm, _lo, fill, fbps, tbps = TIERS[tier_i]
    return fill * fbps + (1.0 - fill) * tbps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="wideA_conformer_ref")
    ap.add_argument("--q", type=float, default=0.2, help="long/short fraction of the cross-section")
    args = ap.parse_args()
    D = p.join(E, "train", args.tag)

    pr = np.load(p.join(D, "panel_ref.npz"), allow_pickle=True)
    ts = pr["ts"].astype(np.int64); member = pr["member"]; CL = pr["CL"]; symbols = pr["symbols"]
    T, N = member.shape
    # liquidity: DVOL30 from wide_panel, ts-aligned (daily $vol ~ DVOL30*24)
    wp = np.load(p.join(E, "wide_panel.npz"), allow_pickle=True)
    assert np.array_equal(wp["ts"].astype(np.int64), ts), "panel_ref/wide_panel ts mismatch"
    daily_dvol = wp["DVOL30"].astype(np.float64) * 24.0            # (T,N)

    # composite factor = per-ts z-scored mean over the K heads, stitched across folds
    comp = np.full((T, N), np.nan)
    for fi in range(3):
        f = p.join(D, f"fold_{fi}_head_scores.npz")
        if not p.exists(f):
            continue
        z = np.load(f); sc = z["scores"]; rows = z["te_rows"]
        for t in rows:
            v = member[t] & CL[t] & np.isfinite(sc[t]).any(1)
            if v.sum() < 12:
                continue
            zs = []
            for k in range(sc.shape[2]):
                col = sc[t, v, k]
                if np.isfinite(col).sum() >= 12 and np.nanstd(col) > 1e-12:
                    zs.append((col - np.nanmean(col)) / np.nanstd(col))
            if zs:
                comp[t, v] = np.nanmean(np.stack(zs), axis=0)

    # per-rebalance L/S book on the CL grid: long top-q, short bottom-q of the composite
    rows = np.where(np.isfinite(comp).any(1) & CL.any(1))[0]
    tier_names = [t[0] for t in TIERS]
    notional_by_tier = np.zeros(3)          # sum |weight| by tier (position notional share)
    n_reb = 0
    prev_w = {}                             # symbol -> weight, for turnover
    turn_num = turn_den = 0.0
    eff_cost_accum = 0.0                    # notional-weighted blended effective cost (bps)
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(comp[t]))[0]
        if v.size < 20:
            continue
        nsel = max(1, int(round(args.q * v.size)))
        longs = v[np.argsort(-comp[t, v])[:nsel]]
        shorts = v[np.argsort(comp[t, v])[:nsel]]
        w = {}
        for j in longs:
            w[j] = 0.5 / nsel
        for j in shorts:
            w[j] = -0.5 / nsel
        # tier accounting + effective cost of the (rebalanced) notional
        cur_w = {}
        for j, wj in w.items():
            ti = _tier_idx(daily_dvol[t, j]) if np.isfinite(daily_dvol[t, j]) else 2
            notional_by_tier[ti] += abs(wj)
            cur_w[j] = wj
        # turnover = sum |w_t - w_{t-1}| across the union of held names (drives cost frequency)
        names = set(cur_w) | set(prev_w)
        for j in names:
            dw = abs(cur_w.get(j, 0.0) - prev_w.get(j, 0.0))
            turn_num += dw
            ti = _tier_idx(daily_dvol[t, j]) if np.isfinite(daily_dvol[t, j]) else 2
            eff_cost_accum += dw * eff_cost_bps(ti)     # cost paid ~ traded notional * tier cost
        turn_den += sum(abs(x) for x in cur_w.values())
        prev_w = cur_w
        n_reb += 1

    tot = notional_by_tier.sum()
    share = notional_by_tier / tot if tot > 0 else notional_by_tier
    # blended effective cost per unit TRADED notional (bps), and per-rebalance cost given turnover
    blended_cost_per_traded = eff_cost_accum / turn_num if turn_num > 0 else float("nan")
    turnover_per_reb = turn_num / max(n_reb, 1)          # sum|dw| per rebalance (2.0 = full flip)

    # liquidity tier census of the universe (member-hours)
    mv = member & np.isfinite(daily_dvol)
    tier_census = np.zeros(3)
    dv = daily_dvol[mv]
    for x in (dv,):
        tier_census[0] = np.mean(x >= TIERS[0][1])
        tier_census[1] = np.mean((x >= TIERS[1][1]) & (x < TIERS[0][1]))
        tier_census[2] = np.mean(x < TIERS[1][1])

    print(f"=== WIDE-BOOK FILL/EFFECTIVE-COST NOTE ({args.tag}, q={args.q}) ===")
    print(f"n_rebalances={n_reb}  members/reb~{int(member[rows].sum(1).mean())}")
    print(f"\n[universe liquidity census] fraction of member-hours by daily-$vol tier:")
    for i, nm in enumerate(tier_names):
        lo = TIERS[i][1]
        print(f"  {nm:6s} (>=${lo/1e6:.0f}M/d): {tier_census[i]*100:5.1f}%")
    print(f"\n[ref L/S book tier composition] share of position notional:")
    for i, nm in enumerate(tier_names):
        f, fb, tb = TIERS[i][2], TIERS[i][3], TIERS[i][4]
        print(f"  {nm:6s}: {share[i]*100:5.1f}%   (assume fill={f:.0%} filled={fb:.1f}bps taker={tb:.1f}bps "
              f"-> eff {eff_cost_bps(i):.1f}bps/side)")
    print(f"\n[execution] turnover/rebalance (sum|dw|, 2.0=full flip) = {turnover_per_reb:.3f}")
    print(f"[execution] BLENDED effective cost per traded notional = {blended_cost_per_traded:.2f} bps/side")
    print(f"[execution] => per-rebalance cost ~ {blended_cost_per_traded*turnover_per_reb/2:.2f} bps "
          f"(turnover-scaled, one side)")
    print(f"\nPer-tier effective-cost vector (bps/side) for 0C net-cost verdict: "
          f"{ {tier_names[i]: round(eff_cost_bps(i),2) for i in range(3)} }")
    print("NOTE: fills are a PARAMETRIC tier model (no LOB on wide universe); tier membership + "
          "book composition + turnover are factual. Small-cap tail is the cost driver.")


if __name__ == "__main__":
    main()
