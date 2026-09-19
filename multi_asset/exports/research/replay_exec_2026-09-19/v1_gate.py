#!/usr/bin/env python3
"""replay_exec 2026-09-19 · V1 gate (PROGRAM_credible_replay_regime_optimization_2026-09-19 §3, tolerances FROZEN there — copied
verbatim below, never tuned here) + mode (b) − mode (a).

V1 (08-26 00Z → 09-18 20Z, the 142 LIVE_G 4h NAV windows whose start lies in that anchor range):
  fee          Σ sim fee / Σ live fee                                             ∈ [0.8, 1.25]
  turnover     (Σ sim turnover / Σ sim gross0) / (Σ live turnover / Σ live gross0) ∈ [0.8, 1.25]
  funding      Σ sim funding / Σ live funding                                     ∈ [0.8, 1.25]
  price        (i) mean of the per-UTC-day differences (sim − live, day = UTC day of the window start) has a 95% UTC-day block
                   bootstrap CI that contains 0 (B = 20000 resamples of days with replacement, percentile CI, seed 20260919);
               (ii) |Σ (sim − live)| ≤ max(|Σ live price|, 0.5 bps × Σ live gross0)   ["0.5 bps/锚/gross × Σgross": one anchor
                   per window, gross = the window's live gross0]
Live side: price_and_trading / funding / fee / gross0 exactly as LIVE_G_DECOMPOSITION (closed cash identity); live turnover =
Σ |quote notional| of every executed trade in (t0, t1] — collapsed ledger fills ∪ MISSING_TRADES ∪ FLATTEN_CLOSURE raw venue
trades (the same trade population the cash identity closes on).
Any FAIL ⇒ the replay may not be called "真实生产策略"; the report names the gap. No retuning after this runs (the calibration
receipt carries frozen_before_v1 = true and its sha is printed here).
usage: v1_gate.py <sim_live.json> <sim_rule.json> <out.json> [mirror]
"""
import collections, json, math, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L

BAND = (0.8, 1.25)                 # PROGRAM §3 V1 (frozen)
PRICE_BPS = 0.5                    # PROGRAM §3 V1 (frozen): 0.5 bps / anchor / gross
B_BOOT, SEED = 20000, 20260919


def day_of(t):
    return time.strftime("%Y-%m-%d", time.gmtime(float(t)))


def block_bootstrap_mean_ci(daily, B=B_BOOT, seed=SEED):
    x = np.asarray(daily, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    m = x[idx].mean(axis=1)
    return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def judge(sim_w, live_w, live_turn):
    """pure: the four V1 items from aligned window lists (same length, same order)"""
    assert len(sim_w) == len(live_w) and all(abs(a["t0"] - b["t0"]) < 1e-6 for a, b in zip(sim_w, live_w))
    S = lambda rows, k: sum(float(r[k]) for r in rows)
    fee_r = S(sim_w, "fee") / S(live_w, "fee")
    fund_r = S(sim_w, "funding") / S(live_w, "funding")
    to_sim = S(sim_w, "turnover") / S(sim_w, "gross0")
    to_live = sum(live_turn) / S(live_w, "gross0")
    to_r = to_sim / to_live
    days = collections.OrderedDict()
    for a, b in zip(sim_w, live_w):
        days.setdefault(day_of(b["t0"]), 0.0)
        days[day_of(b["t0"])] += float(a["price_trade"]) - float(b["price_trade"])
    mean, lo, hi = block_bootstrap_mean_ci(list(days.values()))
    tot = S(sim_w, "price_trade") - S(live_w, "price_trade")
    tol = max(abs(S(live_w, "price_trade")), PRICE_BPS * 1e-4 * S(live_w, "gross0"))
    items = {
        "fee": {"sim": S(sim_w, "fee"), "live": S(live_w, "fee"), "ratio": fee_r, "band": BAND, "pass": BAND[0] <= fee_r <= BAND[1]},
        "turnover_over_gross": {"sim": to_sim, "live": to_live, "sim_turnover": S(sim_w, "turnover"), "live_turnover": sum(live_turn),
                                "sim_sum_gross0": S(sim_w, "gross0"), "live_sum_gross0": S(live_w, "gross0"), "ratio": to_r, "band": BAND,
                                "pass": BAND[0] <= to_r <= BAND[1]},
        "funding": {"sim": S(sim_w, "funding"), "live": S(live_w, "funding"), "ratio": fund_r, "band": BAND, "pass": BAND[0] <= fund_r <= BAND[1]},
        "price_and_trading": {"sim": S(sim_w, "price_trade"), "live": S(live_w, "price_trade"), "total_diff": tot, "tolerance": tol,
                              "tolerance_terms": {"abs_live_total_price": abs(S(live_w, "price_trade")),
                                                  "half_bps_x_sum_live_gross0": PRICE_BPS * 1e-4 * S(live_w, "gross0")},
                              "n_days": len(days), "daily_diff_mean": mean, "daily_diff_ci95": [lo, hi], "bootstrap": {"B": B_BOOT, "seed": SEED},
                              "ci_contains_0": lo <= 0.0 <= hi, "total_within_tol": abs(tot) <= tol,
                              "per_day_diff": dict(days)},
    }
    items["price_and_trading"]["pass"] = items["price_and_trading"]["ci_contains_0"] and items["price_and_trading"]["total_within_tol"]
    return items


def live_turnover(M, live_w):
    tr = L.all_trades(M, live_w[0]["t0"] - 1, live_w[-1]["t1"] + 1)
    ts = [x["ts"] for x in tr]
    out = []
    import bisect
    for w in live_w:
        i = bisect.bisect_right(ts, w["t0"]); j = bisect.bisect_right(ts, w["t1"])
        out.append(sum(abs(x["sn"]) for x in tr[i:j]))
    return out, len(tr)


def main():
    sim_a_p, sim_b_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    M = L.Mirror(sys.argv[4] if len(sys.argv) > 4 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    A = json.load(open(sim_a_p)); B = json.load(open(sim_b_p))
    assert A["mode"] == "live" and B["mode"] == "rule" and not any(A["knobs"].values()) and not any(B["knobs"].values())
    assert A["calibration"]["sha256"] == B["calibration"]["sha256"]
    cal = json.load(open(os.path.join(L.REPO, A["calibration"]["path"])))
    assert cal["frozen_before_v1"] is True and L.sha_file(os.path.join(L.REPO, A["calibration"]["path"])) == A["calibration"]["sha256"]
    W, _ = L.live_windows()
    live_w = [w for w in W if L.A_V1_FIRST <= L.nominal(w["t0"]) <= L.A_V1_LAST]
    sim_w = A["windows"]
    lt, n_tr = live_turnover(M, live_w)
    items = judge(sim_w, live_w, lt)
    lines = []
    for k in ("fee", "turnover_over_gross", "funding"):
        it = items[k]
        lines.append(f"V1 {k:<20} sim {it['sim']:>14,.4f}  live {it['live']:>14,.4f}  ratio {it['ratio']:.4f}  band [0.8, 1.25]  {'PASS' if it['pass'] else 'FAIL'}")
    p = items["price_and_trading"]
    lines.append(f"V1 price_and_trading   sim {p['sim']:>12,.2f}  live {p['live']:>12,.2f}  total diff {p['total_diff']:+,.2f}  tol {p['tolerance']:,.2f}  "
                 f"daily-diff mean {p['daily_diff_mean']:+,.2f} CI95 [{p['daily_diff_ci95'][0]:+,.2f}, {p['daily_diff_ci95'][1]:+,.2f}] "
                 f"(n_days {p['n_days']})  CI∋0 {p['ci_contains_0']}  |diff|≤tol {p['total_within_tol']}  {'PASS' if p['pass'] else 'FAIL'}")
    all_pass = all(items[k]["pass"] for k in items)
    lines.append(f"V1 VERDICT: {'PASS' if all_pass else 'FAIL'} ({sum(items[k]['pass'] for k in items)}/4 items)")
    # ── mode (b) − mode (a) on the same windows ──
    tot = lambda rows: {k: sum(float(r[k]) for r in rows) for k in ("price_trade", "funding", "fee", "turnover")}
    ta, tb = tot(A["windows"]), tot(B["windows"])
    net = lambda t: t["price_trade"] + t["funding"] - t["fee"]
    eq_a, eq_b = A["windows"][-1]["equity1"], B["windows"][-1]["equity1"]
    byday = collections.OrderedDict()
    for a, b in zip(A["windows"], B["windows"]):
        d = day_of(a["t0"]); byday.setdefault(d, 0.0)
        byday[d] += (float(b["price_trade"]) + float(b["funding"]) - float(b["fee"])) - (float(a["price_trade"]) + float(a["funding"]) - float(a["fee"]))
    sg = sum(float(w["gross0"]) for w in A["windows"])
    b_minus_a = {"net_pnl_a": net(ta), "net_pnl_b": net(tb), "net_b_minus_a": net(tb) - net(ta),
                 "components_b_minus_a": {k: tb[k] - ta[k] for k in ta}, "final_equity_a": eq_a, "final_equity_b": eq_b,
                 "final_equity_b_minus_a": eq_b - eq_a, "bps_per_anchor_per_gross_on_mode_a_gross": (net(tb) - net(ta)) / sg * 1e4,
                 "per_day_net_b_minus_a": byday,
                 "events_a": [e for e in A["events_fired"] if e["type"] == "FLATTEN"], "events_b": [e for e in B["events_fired"] if e["type"] == "FLATTEN"],
                 "anchors_not_traded_a": {r["utc"]: r["status"] for r in A["anchors"] if r["status"] != "TRADE"},
                 "anchors_not_traded_b": {r["utc"]: r["status"] for r in B["anchors"] if r["status"] != "TRADE"}}
    lines.append(f"(b)−(a): net P&L {b_minus_a['net_b_minus_a']:+,.2f} USDT (price {b_minus_a['components_b_minus_a']['price_trade']:+,.2f}, "
                 f"funding {b_minus_a['components_b_minus_a']['funding']:+,.2f}, fee {-b_minus_a['components_b_minus_a']['fee']:+,.2f}); "
                 f"final equity (b) {eq_b:,.2f} − (a) {eq_a:,.2f} = {eq_b - eq_a:+,.2f}")
    # ── diagnostics (not verdict items) ──
    corr = float(np.corrcoef([w["price_trade"] for w in sim_w], [w["price_trade"] for w in live_w])[0, 1])
    diag = {"window_price_corr_sim_live": corr,
            "sum_gross0_sim_over_live": sum(w["gross0"] for w in sim_w) / sum(w["gross0"] for w in live_w),
            "final_equity_sim_a": eq_a, "live_nav_last_window_end_usdt": None,
            "per_window": [{"from": b["from"], "sim_price": a["price_trade"], "live_price": b["price_trade"], "sim_fund": a["funding"], "live_fund": b["funding"],
                            "sim_fee": a["fee"], "live_fee": b["fee"], "sim_gross0": a["gross0"], "live_gross0": b["gross0"], "sim_turn": a["turnover"],
                            "live_turn": t} for a, b, t in zip(sim_w, live_w, lt)],
            "n_live_trades": n_tr,
            "calibration_consistency_in_sample": {
                "sim_exec_over_plan": sum(r["exec_maker"] + r["exec_taker"] for r in A["anchors"] if r.get("plan_turnover")) /
                                      sum(r["plan_turnover"] for r in A["anchors"] if r.get("plan_turnover")),
                "sim_taker_share": sum(r["exec_taker"] for r in A["anchors"] if r.get("plan_turnover")) /
                                   sum(r["exec_maker"] + r["exec_taker"] for r in A["anchors"] if r.get("plan_turnover")),
                "live_exec_over_plan": cal["calibration"]["6_turnover_paired"]["sum_exec_over_sum_plan"],
                "live_taker_share": cal["calibration"]["6_turnover_paired"]["taker_share_of_exec_notional"],
                "note": "the fill model reproducing its own calibration target in-sample — a consistency check, NOT validation"},
            "stops_sim_a": [e for e in A["events_fired"] if e["type"] == "STOP"]}
    doc = {"device": "v1_gate.py", "device_sha256": L.sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": "/usr/bin/python3 " + " ".join([os.path.relpath(os.path.abspath(__file__), L.REPO)] + sys.argv[1:]),
           "program_tolerances_frozen_in": "docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md §3 V1",
           "inputs_sha256": dict(L.input_shas(M), **{os.path.relpath(os.path.abspath(p), L.REPO): L.sha_file(p) for p in (sim_a_p, sim_b_p)}),
           "sim_devices": {"exec_sim_sha256_a": A["device_sha256"], "exec_sim_sha256_b": B["device_sha256"], "calibration_sha256": A["calibration"]["sha256"]},
           "verdict_lines": lines, "all_pass": all_pass, "items": items, "mode_b_minus_a": b_minus_a, "diagnostics": diag}
    with open(out_p + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
