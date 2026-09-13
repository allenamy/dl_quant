#!/usr/bin/env python3
"""t1_tables_addendum.py — Mac. Render receipts/TABLES_T1_ADDENDUM1.md from the ADDENDUM 1 receipts only (formatting, no computation)."""
import os, sys, json
T1 = os.path.abspath(sys.argv[1])
D = json.load(open(T1 + "/receipts/pod2/RECEIPT_T1_addendum1.json"))["result"]
M = json.load(open(T1 + "/receipts/RECEIPT_T1_addendum1_mac.json")); PS = json.load(open(T1 + "/receipts/RECEIPT_T1_addendum1_posthoc_split.json"))["result"]
out = []; w = lambda s="": out.append(s)
ci = lambda t: "%+.3f [%+.2f, %+.2f]" % (t[0], t[1][0], t[1][1])
w("# TABLES · T1 ADDENDUM 1 (rendered by `devices/t1_tables_addendum.py`; do not edit by hand)")
w(); w("Post-result readings requested by the lead (spec `ADDENDUM_1_SPEC_T1_2026-09-13.md` sha 79b7c067…). Units bps / 4h anchor / unit gross. T1's frozen verdicts are unchanged.")
w(); w("## A0 · gates"); w("| gate | result |"); w("|---|---|")
g = D["gate_G_T2"]; w("| G-T2 (T2 estimator loaded from T2 source; refit 2026-08-01 b̂ and d4 live b̂) | %s: %.15f vs %.15f; %.15f vs %.15f |" % (g["PASS"], g["refit_0801_b"], g["receipt_b"], g["d4_b"], g["receipt_d4_b"]))
g = D["X3"]["gate_G30"]; w("| G30 (C0 on 30 anchors vs T2 +5.76/+5.66, 1.013/1.019) | %s: price %.4f / %.4f, carry %.4f / %.4f |" % (g["PASS"], g["C0_s42_price"], g["C0_s2027_price"], g["C0_s42_carry"], g["C0_s2027_carry"]))
w(); w("## A1 · units (X1)")
w("| source line | meaning |"); w("|---|---|")
for c in M["checks"]: w("| `%s` L%s | %s |" % (c["file"], ",".join(map(str, c["line"])), c["meaning"]))
x = D["X1"]; gn = x["gross_norm_held_abs_over_realized_gross"]
w(); w("held notional / realized_gross over LIVE_REAL: mean %.4f (p10 %.4f, p90 %.4f, n %d) ⇒ unit same: **%s**" % (gn["mean"], gn["p10"], gn["p90"], gn["n"], x["unit_same"]))
c = x["common_carry_REAL_over_D2"]; w("common 78 anchors: realized carry %.3f vs modelled (D2) %.3f ⇒ ratio %.3f; per-anchor slope %.3f, intercept %+.3f" % (c["mean_REAL"], c["mean_D2"], c["ratio_of_means"], c["slope"], c["intercept"]))
w("30 anchors: replay own-book carry / deployed-book (D2) carry: " + ", ".join("%s %.3f" % (k, v) for k, v in x["A30_carry_replay_over_D2"].items()))
w(); w("| numerator | value | ÷ W_ALPHA | ÷ H1_2026 | ÷ 2026-07 | ÷ T1 §9 analog |"); w("|---|---|---|---|---|---|")
for n, v in x["numerators"].items():
    r = x["ratio_table"][n]; w("| %s | %.3f | %.2f | %.2f | %.2f | %.2f |" % (n, v, r["W_ALPHA"], r["H1_2026"], r["M2026_07"], r["analog_T1_s9"]))
w("denominators (C0_s42): " + ", ".join("%s %.4f" % (k, v) for k, v in x["denominators_C0_s42"].items()))
w(); w("## A2 · carry and price percentiles against same-state history (X2)")
for arm in ("C0_s42", "NW_s2027"):
    for W in ("W_reg", "W_com", "W_30"):
        b = D["X2"][arm][W]
        w(); w("**%s · %s** — windows %d, conditional %d (years %s) · carry reading **%s** · price reading **%s**" % (arm, W, b["n_windows"], b["n_cond"], b["cond_years"], b["carry_reading"], b["price_reading"]))
        w("conditional carry quantiles 2.5/10/50/90/97.5: %s · price: %s" % ([round(v, 3) for v in b["cond_carry_q"]], [round(v, 2) for v in b["cond_price_q"]]))
        w("| statistic | live value | unconditional pct | conditional pct |"); w("|---|---|---|---|")
        for k, v in b["stats"].items(): w("| %s | %+.3f | %.3f | %.3f |" % (k, v["value"], v["uncond_pct"], v["cond_pct"]))
w(); w("## A3 · the 30 replayable anchors and the window split (X3)")
a = D["X3"]["A30_means"]
w("ledger on %d of 30 anchors: price %+.3f, carry %.3f · D2 on %d: price %+.3f, carry %.3f" % (a["REAL_n"], a["REAL_price"], a["REAL_carry"], a["D2_n"], a["D2_price"], a["D2_carry"]))
w("| arm | replay price (30) | replay carry (30) | replay g (30) | on the ledger's 27: replay price | ledger price | ledger − replay | D2 − replay (BOOK) | ledger − D2 |"); w("|---|---|---|---|---|---|---|---|---|")
for arm, v in D["X3_per_arm"].items():
    p = v["paired_on_A30_REAL"]; w("| %s | %+.3f | %.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |" % (arm, v["price_A30"], v["carry_A30"], v["g_A30"], p["replay_price_on_REAL_subset"], p["REAL_price"], p["mean_REAL_minus_replay"], p["mean_D2_minus_replay"], p["mean_REAL_minus_D2"]))
w(); w("registered split (spec X3): " + json.dumps(D["X3"]["split"]) + " · reading (a) %s · reading (b) %s" % (D["X3"]["reading_a"], D["X3"]["reading_b"]))
w(); w("POST-HOC split at comparable ends (`RECEIPT_T1_addendum1_posthoc_split.json`):"); w("| segment | ledger n | ledger price | ledger carry | D2 n | D2 price | D2 carry |"); w("|---|---|---|---|---|---|---|")
for k, v in PS.items(): w("| %s | %d | %s | %s | %d | %s | %s |" % (k, v["REAL_n"], "%+.3f" % v["REAL_price"] if v["REAL_price"] is not None else "—", "%.3f" % v["REAL_carry"] if v["REAL_carry"] is not None else "—", v["D2_n"], "%+.3f" % v["D2_price"] if v["D2_price"] is not None else "—", "%.3f" % v["D2_carry"] if v["D2_carry"] is not None else "—"))
w(); w("| UTC day | ledger price (mean/anchor, n) | D2 price (mean/anchor, n) |"); w("|---|---|---|")
for dday, v in D["X3"]["daily_REAL"].items():
    dv = D["X3"]["daily_D2"].get(dday); w("| %s | %+.2f (%d) | %s |" % (dday, v["mean"], v["n"], ("%+.2f (%d)" % (dv["mean"], dv["n"])) if dv else "—"))
w(); w("30-anchor rows (ledger / D2): " + json.dumps(D["X3"]["A30_anchor_rows"]))
w(); w("## A4 · H4 bridge vs T2 κ* (X4) — b = compensated fraction, κ = 1 − b")
w("| period · σ bin | S0 = T2 (winsor, FZ) | S1 unwinsor | S2 no FZ | S3 book fund-leg | S3w | S3 long | S3 short | S4 short cohort ρ | S5 arm (C0) | fund carry |"); w("|---|---|---|---|---|---|---|---|---|---|---|")
for key, v in D["X4"]["S0_S2"].items():
    s = D["X4"]["S3_S5"]["C0_s42"].get(key, {})
    if "S0_b" not in v or "S3_b" not in s: w("| %s | n %s | | | | | | | | | |" % (key, v.get("n"))); continue
    w("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (key, ci(v["S0_b"]), ci(v["S1_b"]), ci(v["S2_b"]), ci(s["S3_b"]), ci(s["S3w_b"]), ci(s["S3_long_b"]), ci(s["S3_short_b"]), ci(s["S4_rho"]), ci(s["S5_b_arm"]) if "S5_b_arm" in s else "—", ci(s["fund_carry_bps"])))
lv = D["X4"]["live"]; x = lv["x0910_0826_0910"]
w(); w("live 2026-08-26 00Z..09-10 00Z (x0910, n %d): S0 %s · S1 %s · S2 %s · deployed-book price/carry %+.3f · ledger book price/carry %+.3f" % (x["n"], ci(x["S0_b"]), ci(x["S1_b"]), ci(x["S2_b"]), lv["D2_book_price_over_carry"], lv["REAL_book_price_over_carry"]))
w(); w("expanding path (C0_s42; T2 b̂ from T2's receipt next to T1 cumulative ratios at the same refit dates)"); w("| refit | T2 b̂ | T1 S3 cum | T1 S4 cum | T1 S5 cum | rec rows |"); w("|---|---|---|---|---|---|")
for p in D["X4"]["path"]: w("| %s | %s | %+.3f | %+.3f | %+.3f | %d |" % (p["T_iso"], ("%+.3f" % p["T2_b"]) if p["T2_b"] is not None else "—", p["T1_S3_b_cum"], p["T1_S4_rho_cum"], p["T1_S5_b_arm_cum"], p["n_rec"]))
w(); w("NW_s2027 S3/S4 by period · bin: " + "; ".join("%s S3 %+.2f S4 %+.2f" % (k, v["S3_b"][0], v["S4_rho"][0]) for k, v in D["X4"]["S3_S5"]["NW_s2027"].items() if "S3_b" in v))
w(); w("## A5 · H5 low-dispersion mechanism check (X5; T2 σ cut points %s)" % D["t2_sigma_cut_points_20260801"])
for arm in ("C0_s42", "C0_s2027", "NW_s42", "NW_s2027"):
    w(); w("**%s**" % arm); w("| period | M1 low share (T2 σ / SIGF<4.75) | bin | n | fund carry | S3 b | eff. fund gross share | w3_fund | g | M2 / M3 / M4 → reading |"); w("|---|---|---|---|---|---|---|---|---|---|")
    for p, o in D["X5"][arm].items():
        for b in ("low", "mid", "high"):
            x = o.get(b, {})
            if "g" not in x: continue
            tail = ("%s / %s / %s → **%s** (M3 diff %s)" % (o.get("M2"), o.get("M3"), o.get("M4"), o.get("fits"), ci(o["M3_diff_low_minus_high"]))) if (b == "high" and "fits" in o) else ""
            w("| %s | %.3f / %.3f | %s | %d | %s | %s | %s | %.3f | %s | %s |" % (p, o["M1_share_low_T2sigma"], o["M1_share_SIGF_lt_4p75"], b, x["n"], ci(x["fund_carry_bps"]), ci(x["S3_b"]), ci(x["fund_eff_gross_share"]), x["w3_fund_nominal"], ci(x["g"]), tail))
w(); w("live window: " + json.dumps(D["X5"]["live_window"]))
open(T1 + "/receipts/TABLES_T1_ADDENDUM1.md", "w").write("\n".join(out) + "\n"); print("wrote receipts/TABLES_T1_ADDENDUM1.md", len(out), "lines")
