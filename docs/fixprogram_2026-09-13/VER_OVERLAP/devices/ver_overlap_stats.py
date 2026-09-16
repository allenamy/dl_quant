#!/usr/bin/env python3
"""VER-OVERLAP stage 2: difference decomposition + resolution, from the stage-1 FACTS json.

Reads only the FACTS json produced by ver_overlap_compare.py and the replay DAILY_AGGREGATES
(for the August sub-period split).  Writes one json.  Nothing else.

What it computes, in the order the caliber file fixed:
  1. per-day live-minus-replay, in percentage points of NAV, decomposed into price/funding/fee.
     The three bucket differences sum to the net difference by construction (identity checked).
  2. the same on a GROSS-NORMALISED basis: each side's daily % divided by that side's own
     gross/NAV for the day, so a day where live ran 1.46x and replay 1.95x is comparable.
  3. clean-day subset: days with no live-only event.  The excluded days are named, not dropped
     silently.
  4. RESOLUTION: with n clean days, the two-sided 95% t-interval half-width on the mean daily
     difference.  This is the smallest daily difference the comparison could have detected.
  5. the replay's own August split 08-01..08-25 vs 08-26..08-31, so the -5.9586% month can be
     located in time.
"""
import json
import os
import sys
import math
import datetime as dt
import hashlib

UTC = dt.timezone.utc
WORKTREE = "/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907"
DAILY_AGG = os.path.join(
    WORKTREE,
    "multi_asset/exports/research/codex_causal_fullchain_2026-09-14/integration/"
    "current_rule_mark_cash_audit_20260915/completed/nohalt_current_main/audit1/DAILY_AGGREGATES.json",
)

# t critical values, two-sided 95%, df = n-1
TCRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306}

# days with a live-only event -> not evidence about the strategy.  Reason recorded with each.
LIVE_ONLY_EVENT = {
    "20260826": "watchdog TRIP 12:47:02Z -> whole-book flatten + reduce-only; 16Z anchor placed 0 "
                "orders with realized_gross 0.0; 20Z rebuilt from flat to only 1.04x gross. "
                "Also gross_mult 1.5 for 5 of 6 anchors vs replay 1.95.",
    "20260827": "external deposit +5449.62 USDT (36% of NAV) intraday, and the leverage ramp "
                "1.5 -> 1.75 -> 2.0 completed during the day (live mean gross/NAV 1.85 vs replay 2.02).",
    "20260829": "20Z anchor: producer target file missing after 21 attempts -> action=HOLD, no "
                "anchors row, no orders; book held 16Z -> 08-30 00Z (8h instead of 4h).",
}


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def tci(xs):
    n = len(xs)
    if n < 2:
        return {"n": n, "mean": mean(xs) if xs else None, "sd": None, "se": None,
                "half_width_95": None, "lo": None, "hi": None}
    m, s = mean(xs), sd(xs)
    se = s / math.sqrt(n)
    hw = TCRIT.get(n - 1, 1.96) * se
    return {"n": n, "mean": m, "sd": s, "se": se, "half_width_95": hw, "lo": m - hw, "hi": m + hw}


def main():
    if len(sys.argv) != 3:
        print("usage: ver_overlap_stats.py <FACTS.json> <out.json>", file=sys.stderr)
        return 2
    facts_path, out_path = sys.argv[1], sys.argv[2]
    F = json.load(open(facts_path))
    out = {
        "device": os.path.abspath(__file__),
        "device_self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "facts_input": facts_path,
        "facts_input_sha256": hashlib.sha256(open(facts_path, "rb").read()).hexdigest(),
        "run_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live_only_events": LIVE_ONLY_EVENT,
    }

    R = F["replay_days"]
    G = F["live_gross_by_day"]
    days = sorted(R)

    for conv, key in (("CONV_B_midnight", "live_days_convB_midnight"),
                      ("CONV_A_watchdog", "live_days_convA_watchdog")):
        L = F[key]
        rows = {}
        for d in days:
            r, l = R[d], L[d]
            if r["status"] != "OK" or l["status"] != "OK":
                rows[d] = {"status": "SKIP"}
                continue
            n0r, n0l = r["nav0"], l["nav0"]
            pr = {k: 100.0 * r[k + "_usdt"] / n0r for k in ("price", "funding", "fee_trade", "fee_settle")}
            pl = {k: 100.0 * l[k + "_usdt"] / n0l for k in ("price", "funding", "fee_trade", "fee_settle")}
            net_r, net_l = r["net_pct_of_nav0"], l["net_pct_of_nav0"]
            gr = r["gross_over_nav_t0"]
            gl = G[d]["mean_gross_over_nav"]
            diff = {k: pl[k] - pr[k] for k in pr}
            rows[d] = {
                "status": "OK",
                "clean": d not in LIVE_ONLY_EVENT,
                "replay_net_pct": net_r,
                "live_net_pct": net_l,
                "diff_net_pp": net_l - net_r,
                "replay_buckets_pp": pr,
                "live_buckets_pp": pl,
                "diff_buckets_pp": diff,
                "diff_identity_residual_pp": (net_l - net_r) - sum(diff.values()),
                "replay_gross_over_nav": gr,
                "live_gross_over_nav": gl,
                "replay_net_per_unit_gross_pp": net_r / gr if gr else None,
                "live_net_per_unit_gross_pp": net_l / gl if gl else None,
                "diff_net_per_unit_gross_pp": (net_l / gl - net_r / gr) if (gr and gl) else None,
                "replay_turnover_over_nav": r["turnover_usdt"] / n0r,
                "live_turnover_over_nav": l["turnover_usdt"] / n0l,
                "replay_fee_bps_of_turnover": (-r["fee_trade_usdt"] / r["turnover_usdt"] * 1e4)
                                              if r["turnover_usdt"] else None,
                "live_fee_bps_of_turnover": (-l["fee_trade_usdt"] / l["turnover_usdt"] * 1e4)
                                            if l["turnover_usdt"] else None,
            }
        blk = {"per_day": rows}
        for label, sel in (("all6", days), ("clean_only", [d for d in days if d not in LIVE_ONLY_EVENT])):
            ok = [d for d in sel if rows[d].get("status") == "OK"]
            blk[label] = {
                "days": ok,
                "net_diff_pp": tci([rows[d]["diff_net_pp"] for d in ok]),
                "price_diff_pp": tci([rows[d]["diff_buckets_pp"]["price"] for d in ok]),
                "funding_diff_pp": tci([rows[d]["diff_buckets_pp"]["funding"] for d in ok]),
                "fee_diff_pp": tci([rows[d]["diff_buckets_pp"]["fee_trade"] for d in ok]),
                "net_diff_per_unit_gross_pp": tci([rows[d]["diff_net_per_unit_gross_pp"] for d in ok]),
                "replay_daily_sd_pp": sd([rows[d]["replay_net_pct"] for d in ok]),
                "live_daily_sd_pp": sd([rows[d]["live_net_pct"] for d in ok]),
                "replay_cum_pct": 100.0 * (math.prod(1 + rows[d]["replay_net_pct"] / 100 for d in ok) - 1),
                "live_cum_pct": 100.0 * (math.prod(1 + rows[d]["live_net_pct"] / 100 for d in ok) - 1),
            }
        out[conv] = blk

    # ---- replay August, split at the live start ----
    agg = json.load(open(DAILY_AGG))
    idx = {dt.datetime.fromtimestamp(r["ts_ms"] / 1000, UTC).strftime("%Y%m%d"): r for r in agg}

    def seg(a, b, name):
        r0, r1 = idx[a], idx[b]
        s0, s1 = r0["independent_totals"], r1["independent_totals"]
        n0, n1 = r0["independent_nav"], r1["independent_nav"]
        dn = n1 - n0
        df = s1["funding_cash"] - s0["funding_cash"]
        dc = -(s1["ordinary_fees"] - s0["ordinary_fees"])
        ds = -(s1["settlement_fees"] - s0["settlement_fees"])
        # daily returns inside the segment
        d0 = dt.datetime.strptime(a, "%Y%m%d").replace(tzinfo=UTC)
        d1 = dt.datetime.strptime(b, "%Y%m%d").replace(tzinfo=UTC)
        rets, cur = [], d0
        while cur < d1:
            k0 = cur.strftime("%Y%m%d")
            k1 = (cur + dt.timedelta(days=1)).strftime("%Y%m%d")
            rets.append(100.0 * (idx[k1]["independent_nav"] / idx[k0]["independent_nav"] - 1))
            cur += dt.timedelta(days=1)
        return {"name": name, "from": a, "to": b, "n_days": len(rets),
                "nav0": n0, "nav1": n1, "pct": 100.0 * dn / n0,
                "price_pp": 100.0 * (dn - df - dc - ds) / n0,
                "funding_pp": 100.0 * df / n0, "fee_pp": 100.0 * dc / n0,
                "daily_mean_pp": mean(rets), "daily_sd_pp": sd(rets),
                "daily_sharpe_ann": mean(rets) / sd(rets) * math.sqrt(365) if sd(rets) else None,
                "worst_day_pp": min(rets), "best_day_pp": max(rets)}

    out["replay_august_split"] = [
        seg("20260801", "20260901", "2026-08 whole month (doc says -5.9586%)"),
        seg("20260801", "20260826", "2026-08-01..08-25 (before live combo started)"),
        seg("20260826", "20260901", "2026-08-26..08-31 (the overlap window)"),
    ]

    json.dump(out, open(out_path, "w"), indent=1)
    print("WROTE", out_path)
    for s in out["replay_august_split"]:
        print("REPLAY %-46s %3dd  %+8.4f%%  price %+8.4f fund %+7.4f fee %+7.4f  worst day %+7.4f  sd %6.4f"
              % (s["name"], s["n_days"], s["pct"], s["price_pp"], s["funding_pp"], s["fee_pp"],
                 s["worst_day_pp"], s["daily_sd_pp"]))
    for conv in ("CONV_B_midnight", "CONV_A_watchdog"):
        b = out[conv]
        print("\n--- %s ---" % conv)
        for label in ("all6", "clean_only"):
            x = b[label]
            print(" %-10s n=%d  replay_cum %+7.3f%%  live_cum %+7.3f%%" % (
                label, x["net_diff_pp"]["n"], x["replay_cum_pct"], x["live_cum_pct"]))
            for nm in ("net_diff_pp", "price_diff_pp", "funding_diff_pp", "fee_diff_pp",
                       "net_diff_per_unit_gross_pp"):
                t = x[nm]
                if t["half_width_95"] is None:
                    print("    %-28s n=%d mean %+8.4f (no CI)" % (nm, t["n"], t["mean"]))
                else:
                    print("    %-28s mean %+8.4f  sd %7.4f  CI95 [%+8.4f, %+8.4f]  halfwidth %.4f  %s" % (
                        nm, t["mean"], t["sd"], t["lo"], t["hi"], t["half_width_95"],
                        "EXCLUDES 0" if t["lo"] * t["hi"] > 0 else "contains 0"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
