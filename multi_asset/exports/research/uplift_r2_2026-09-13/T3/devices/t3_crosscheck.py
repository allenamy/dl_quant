#!/usr/bin/python3
"""T3 cross-checks (verification of the main device's tightest components with a second path; prereg §3.6 buy/sell item).
(1) entry price vs run mid `a` and maker fill notional re-derived from orders.jsonl ALONE (avg_fill_px, filled_notional,
    mid_at_anchor of the maker rows), compared with the fills.jsonl-based values in t3_passive_rev.py, on ERA2 R1 plans;
(2) mean eligible names per anchor in the window (REV_SHORT receipt: 267.19 over 2022-06..2026-08);
(3) prereg §3.6 buy/sell split of REV_SHORT turnover versus our R1 intended notional.
ENV WHITELIST = EMPTY SET (asserted inside the main device prefix)."""
import hashlib, json, os, time
import numpy as np
T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
MAIN = f"{T3}/devices/t3_passive_rev.py"
src = open(MAIN).read(); cut = src.index("COMP = [")
ns = {"__file__": MAIN, "__name__": "t3_passive_rev_prefix"}
exec(compile(src[:cut], MAIN, "exec"), ns)
era2, orders_by, RT, EIDX, Y4 = ns["era2"], ns["orders_by"], ns["RT"], ns["EIDX"], ns["Y4"]
R1 = [p for p in era2 if p["align"] is not None and p["align"] > 0]
num_f = num_o = den_f = den_o = 0.0; n_cmp = 0; n_skip = 0
for p in R1:
    c = p["c"]
    if c["Nf"] <= 0: continue
    mk = [r for r in orders_by[p["key"]] if r.get("order_type") == "maker" and (r.get("filled_notional") or 0) and r.get("avg_fill_px")]
    if not mk:
        n_skip += 1; continue
    No = sum(abs(float(r["filled_notional"])) for r in mk)
    Fo = No / sum(abs(float(r["filled_notional"])) / float(r["avg_fill_px"]) for r in mk)
    M = float(next(r["mid_at_anchor"] for r in mk if r.get("mid_at_anchor")))
    num_o += No * p["s"] * (Fo / M - 1.0); den_o += No
    num_f += c["f_a"]; den_f += c["Nf"]; n_cmp += 1
I_R1 = sum(p["I"] for p in R1)
e2_E = sorted(set(p["E"] for p in era2))
elig = [int(np.isfinite(RT[EIDX[E]]).sum()) for E in e2_E]
buy_rev = sell_rev = 0.0
for E in e2_E:
    k = EIDX[E]
    w = np.nan_to_num(RT[k] / np.nansum(np.abs(RT[k])))
    wp = np.nan_to_num(RT[k - 1] / np.nansum(np.abs(RT[k - 1])))
    dw = w - wp
    buy_rev += float(dw[dw > 0].sum()); sell_rev += float(-dw[dw < 0].sum())
ours_buy = sum(p["I"] for p in R1 if p["s"] > 0); ours_sell = sum(p["I"] for p in R1 if p["s"] < 0)
OUT = {"device": os.path.abspath(__file__), "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "main_device_sha256": hashlib.sha256(open(MAIN, "rb").read()).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "a_entry_vs_run_mid": {"n_plans_compared": n_cmp, "n_plans_without_order_fill_px": n_skip,
                              "fills_path_bps_per_unit_intended": round(num_f / I_R1 * 1e4, 4), "orders_path_bps_per_unit_intended": round(num_o / I_R1 * 1e4, 4),
                              "fills_path_filled_usdt": round(den_f, 2), "orders_path_filled_usdt": round(den_o, 2)},
       "eligible_names_per_anchor_window_mean": round(float(np.mean(elig)), 2),
       "buy_sell_share": {"rev_short_turnover_buy": round(buy_rev / (buy_rev + sell_rev), 4), "ours_R1_intended_buy": round(ours_buy / (ours_buy + ours_sell), 4)}}
json.dump(OUT, open(f"{T3}/receipts/CROSSCHECK.json", "w"), indent=1)
print(json.dumps(OUT, indent=1))
