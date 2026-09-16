#!/usr/bin/env python3
"""VER-OVERLAP stage 3: the funding bucket, on the venue's own books.

Stage 1 took the live funding bucket from funding.jsonl.  A two-instrument check against the
venue income ledger (daily_nav.realised_by_type["FUNDING_FEE"], sourced from /fapi/v1/income
since 00:00Z) showed funding.jsonl UNDER-reports by 16-26% per day with skipped_no_position=0,
i.e. the disagreement is per-row, not per-name: funding.jsonl is a RECONSTRUCTION
(position_notional_at_settlement x funding_rate, off a position read up to ~73 min stale),
not the venue's charge.  The ledger is the authority on what the account was charged.

So this stage rebuilds the funding comparison on the ledger, and does it CONSERVATIVELY:

  live window  = [00:00:00Z, last daily_nav row of the UTC day]  (~20:45Z, 86% of the day)
  replay window= [00:00:00Z, 00:00:00Z]                          (100% of the day)

The live window is SHORTER, so any "live pays more funding than replay" that survives this is
understated, not overstated.  The device reports the coverage fraction so the direction of the
bias is on the record rather than assumed.

Also emits the fee caliber both sides: replay 3.52 bps by construction vs live commission in
bps of filled notional (deduped fills, BNB converted at the same-anchor BNBUSDT mid).

Read-only.  Writes one json.
"""
import json
import os
import sys
import math
import hashlib
import datetime as dt

UTC = dt.timezone.utc
LIVE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
DAYS = ["20260826", "20260827", "20260828", "20260829", "20260830", "20260831"]
SCAN = ["20260825"] + DAYS + ["20260901"]
CLEAN = ["20260828", "20260830", "20260831"]  # see ver_overlap_stats.LIVE_ONLY_EVENT
TCRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571}


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else float("nan")


def tci(xs):
    n = len(xs)
    if n < 2:
        return {"n": n, "mean": mean(xs), "lo": None, "hi": None}
    m, s = mean(xs), sd(xs)
    se = s / math.sqrt(n)
    hw = TCRIT.get(n - 1, 1.96) * se
    return {"n": n, "mean": m, "sd": s, "se": se, "half_width_95": hw, "lo": m - hw, "hi": m + hw,
            "excludes_zero": (m - hw) * (m + hw) > 0}


def main():
    facts_path, out_path = sys.argv[1], sys.argv[2]
    F = json.load(open(facts_path))
    out = {"device": os.path.abspath(__file__),
           "device_self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "run_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # ---- deduped fills + BNB price, once ----
    bnb = []
    for d in SCAN:
        for r in jl(os.path.join(LIVE, d, "anchors.jsonl")):
            m = r.get("mid_at_anchor_vector")
            if isinstance(m, str):
                m = json.loads(m)
            if m and m.get("BNBUSDT"):
                bnb.append((r["anchor_ts"], float(m["BNBUSDT"])))
    bnb.sort()

    def px(ts):
        return min(bnb, key=lambda x: abs(x[0] - ts))[1]

    seen, fills = set(), []
    for d in SCAN:
        for r in jl(os.path.join(LIVE, d, "fills.jsonl")):
            k = (r["symbol"], r["trade_id"])
            if k in seen:
                continue
            seen.add(k)
            fills.append(r)

    # ---- funding.jsonl, deduped on (settlement_ts, symbol) ----
    fseen, fund = set(), []
    for d in SCAN:
        for r in jl(os.path.join(LIVE, d, "funding.jsonl")):
            k = (r["settlement_ts"], r["symbol"])
            if k in fseen:
                continue
            fseen.add(k)
            fund.append(r)

    R = F["replay_days"]
    G = F["live_gross_by_day"]
    rows = {}
    for d in DAYS:
        navrows = sorted(jl(os.path.join(LIVE, d, "daily_nav.jsonl")), key=lambda r: r["nav_ts"])
        first, last = navrows[0], navrows[-1]
        t0 = dt.datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC).timestamp()
        t1 = last["nav_ts"]
        cover = (t1 - t0) / 86400.0
        ledger_fund = last["realised_by_type"]["FUNDING_FEE"]
        recon_fund = sum(float(r["funding_paid"]) for r in fund if t0 < r["settlement_ts"] <= t1)
        n_settl = sum(1 for r in fund if t0 < r["settlement_ts"] <= t1)
        # commission over the same window, from fills
        cb = cu = 0.0
        turn = 0.0
        nf = 0
        for r in fills:
            if t0 < r["fill_ts"] <= t1:
                cb += float(r.get("commission") or 0.0)
                cu += float(r.get("commission") or 0.0) * px(r["fill_ts"])
                turn += abs(float(r["fill_notional"]))
                nf += 1
        # NAV to normalise by: the day's OPENING nav (first row), and the day's mean nav
        nav_open = first["nav"]
        nav_mean = sum(r["nav"] for r in navrows) / len(navrows)
        r_ = R[d]
        rows[d] = {
            "clean": d in CLEAN,
            "live_window": [dt.datetime.fromtimestamp(t0, UTC).strftime("%H:%M:%SZ"),
                            dt.datetime.fromtimestamp(t1, UTC).strftime("%H:%M:%SZ")],
            "live_window_coverage_of_utc_day": cover,
            "live_nav_open": nav_open,
            "live_nav_mean": nav_mean,
            "live_funding_ledger_usdt": ledger_fund,
            "live_funding_reconstructed_usdt": recon_fund,
            "recon_over_ledger": recon_fund / ledger_fund if ledger_fund else None,
            "n_settlement_rows_reconstructed": n_settl,
            "live_funding_pp_of_nav_mean": 100.0 * ledger_fund / nav_mean,
            "live_gross_over_nav": G[d]["mean_gross_over_nav"],
            "live_funding_pp_per_unit_gross": 100.0 * ledger_fund / nav_mean / G[d]["mean_gross_over_nav"],
            "replay_funding_usdt": r_["funding_usdt"],
            "replay_nav0": r_["nav0"],
            "replay_funding_pp_of_nav0": 100.0 * r_["funding_usdt"] / r_["nav0"],
            "replay_gross_over_nav": r_["gross_over_nav_t0"],
            "replay_funding_pp_per_unit_gross": 100.0 * r_["funding_usdt"] / r_["nav0"] / r_["gross_over_nav_t0"],
            "live_over_replay_funding_ratio_per_unit_gross":
                (ledger_fund / nav_mean / G[d]["mean_gross_over_nav"]) /
                (r_["funding_usdt"] / r_["nav0"] / r_["gross_over_nav_t0"]),
            "live_commission_bnb_native": cb,
            "live_commission_usdt": cu,
            "live_turnover_usdt": turn,
            "live_n_fills": nf,
            "live_fee_bps_of_turnover": (cu / turn * 1e4) if turn else None,
            "replay_fee_bps_of_turnover": (-r_["fee_trade_usdt"] / r_["turnover_usdt"] * 1e4)
                                          if r_["turnover_usdt"] else None,
            "ledger_commission_field": last["realised_by_type"]["COMMISSION"],
        }
    out["per_day"] = rows

    for label, sel in (("all6", DAYS), ("clean_only", CLEAN)):
        diffs = [rows[d]["live_funding_pp_per_unit_gross"] - rows[d]["replay_funding_pp_per_unit_gross"]
                 for d in sel]
        ratios = [rows[d]["live_over_replay_funding_ratio_per_unit_gross"] for d in sel]
        out[label] = {
            "days": sel,
            "funding_diff_pp_per_unit_gross_per_day": tci(diffs),
            "live_over_replay_ratio": {"values": ratios, "mean": mean(ratios),
                                       "min": min(ratios), "max": max(ratios)},
            "mean_live_window_coverage": mean([rows[d]["live_window_coverage_of_utc_day"] for d in sel]),
            "live_fee_bps_mean": mean([rows[d]["live_fee_bps_of_turnover"] for d in sel]),
            "replay_fee_bps_mean": mean([rows[d]["replay_fee_bps_of_turnover"] for d in sel]),
        }

    json.dump(out, open(out_path, "w"), indent=1)
    print("WROTE", out_path)
    print("%-10s %-5s %5s %12s %12s %7s | %9s %9s %6s | %7s %7s" % (
        "day", "clean", "cov", "live_fund_U", "recon_U", "rec/led", "live_pp/g", "rep_pp/g", "ratio",
        "liv_bps", "rep_bps"))
    for d in DAYS:
        r = rows[d]
        print("%-10s %-5s %5.2f %12.2f %12.2f %7.3f | %9.4f %9.4f %6.2f | %7.3f %7.3f" % (
            d, r["clean"], r["live_window_coverage_of_utc_day"], r["live_funding_ledger_usdt"],
            r["live_funding_reconstructed_usdt"], r["recon_over_ledger"],
            r["live_funding_pp_per_unit_gross"], r["replay_funding_pp_per_unit_gross"],
            r["live_over_replay_funding_ratio_per_unit_gross"],
            r["live_fee_bps_of_turnover"], r["replay_fee_bps_of_turnover"]))
    for label in ("all6", "clean_only"):
        x = out[label]
        t = x["funding_diff_pp_per_unit_gross_per_day"]
        print("\n%s (n=%d, mean live-window coverage %.3f of a UTC day -> live side UNDERSTATED):"
              % (label, t["n"], x["mean_live_window_coverage"]))
        print("  funding diff pp/day per unit gross: mean %+0.4f CI95 [%+0.4f, %+0.4f]  %s"
              % (t["mean"], t["lo"], t["hi"], "EXCLUDES 0" if t.get("excludes_zero") else "contains 0"))
        print("  live/replay funding ratio: mean %.2f  range %.2f..%.2f"
              % (x["live_over_replay_ratio"]["mean"], x["live_over_replay_ratio"]["min"],
                 x["live_over_replay_ratio"]["max"]))
        print("  fee bps of filled notional: live %.3f  replay %.3f"
              % (x["live_fee_bps_mean"], x["replay_fee_bps_mean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
