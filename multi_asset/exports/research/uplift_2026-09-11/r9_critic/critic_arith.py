#!/usr/bin/env python3
"""COMPLETENESS CRITIC arithmetic. ENV WHITELIST = EMPTY SET (asserted below).
Inputs (all read-only, hashed): trackB_realized_cost_rows.json, r3k_impact/costb_PWR_G230k.json,
r9_screen/.../ARITH_r9screen.json, r9_coverage/receipts/RECEIPT_r9_addendum.json.
No device run, no GPU, no exchange call, no write to ~/dl_quant_live or ~/wide_shadow."""
import json, hashlib, math, os, statistics as st

_real_get = os.environ.get
def _no_env(k, d=None):
    raise RuntimeError("E-0826-D violation: script read env var %r; whitelist is EMPTY SET" % k)
os.environ.get = _no_env

B = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/"
def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]

out = {"env_whitelist": [], "gpu_used": False, "live_touched": False, "inputs_sha16": {}}
p_rows = B + "trackB_realized_cost_rows.json"
p_cost = B + "r3k_impact/costb_PWR_G230k.json"
p_arith = B + "r9_screen/CANDIDATE_3_COHORT_AGE_DECAY_CURVE_0/ARITH_r9screen.json"
p_add = B + "r9_coverage/receipts/RECEIPT_r9_addendum.json"
for p in (p_rows, p_cost, p_arith, p_add):
    out["inputs_sha16"][p.replace(B, "")] = sha16(p)

rows = json.load(open(p_rows))
cost = json.load(open(p_cost))
arith = json.load(open(p_arith))
add = json.load(open(p_add))

def f(x):
    try:
        v = float(x); return v
    except Exception:
        return float("nan")
ok = lambda v: v == v
tn = sum(f(r["traded_notional"]) for r in rows if ok(f(r["traded_notional"])))
fee = sum(f(r["fee_usdt"]) for r in rows if ok(f(r["fee_usdt"])))
adv = sum(f(r["adv_cost_usdt"]) for r in rows if ok(f(r["adv_cost_usdt"])))
cov = sum(f(r["mo_cov"]) * f(r["traded_notional"]) for r in rows
          if ok(f(r["mo_cov"])) and ok(f(r["traded_notional"])))
mo = [f(r["markout60_bps"]) for r in rows if ok(f(r["markout60_bps"]))]
out["C1_realized_exec_cost_vs_60s_fair_value"] = {
    "window": "2026-08-01 .. 2026-09-11 (day field of trackB rows)",
    "n_anchor_rows": len(rows), "n_rows_with_finite_markout60": len(mo),
    "traded_notional_usdt": round(tn, 2),
    "markout60_definition_quoted_from_trackB_realized_cost_2026-09-11.py_L6":
        "markout = side_sign*(mid_at_fill_plus_60s - fill_px)/fill_px ; POSITIVE = price moved OUR WAY",
    "fee_bps_of_traded": round(fee / tn * 1e4, 4),
    "adverse_selection_bps_of_traded": round(adv / tn * 1e4, 4),
    "adverse_selection_bps_coverage_adjusted": round(adv / cov * 1e4, 4),
    "fee_plus_adverse_bps_per_unit_traded_one_side": round((fee + adv) / tn * 1e4, 4),
    "markout60_bps_notional_weighted": round(-adv / tn * 1e4, 4),
    "anchors_with_favourable_markout_pct": round(100.0 * sum(1 for v in mo if v > 0) / len(mo), 1),
    "PINNED_MODEL_book_avg_bps_per_unit_turnover": cost["book_avg_bps_per_unit_turnover"],
    "PINNED_MODEL_composition_quoted": cost["model"],
    "ratio_realized_over_pinned": round(((fee + adv) / tn * 1e4) / cost["book_avg_bps_per_unit_turnover"], 4),
    "gap_bps_per_unit_traded": round(((fee + adv) / tn * 1e4) - cost["book_avg_bps_per_unit_turnover"], 4),
}
A0 = arith["A0"]
band1p = [b for b in arith["bands"] if b["band"] == "age1p"][0]
gap = out["C1_realized_exec_cost_vs_60s_fair_value"]["gap_bps_per_unit_traded"]
res = {}
for tname, turn in (("A0_turnover_0.03032_QUOTED_r9screen", 0.03032),
                    ("A0_turnover_0.0335_QUOTED_r2_horizon_L119", 0.0335)):
    dg = turn * gap
    g_new = A0["mean_g_bps"] - dg
    res[tname] = {"extra_cost_bps_per_anchor_per_unit_gross": round(dg, 4),
                  "A0_mean_g_bps_repriced": round(g_new, 4),
                  "A0_sharpe_repriced_assuming_same_vol": round(A0["sharpe"] * g_new / A0["mean_g_bps"], 4),
                  "pct_haircut_to_planning_number": round(100.0 * dg / A0["mean_g_bps"], 2),
                  "NAV_pct_per_year_at_2x_gross_lost": round(dg * 2190 * 2 / 100.0, 3)}
alpha_per_60s = A0["mean_g_bps"] / 240.0
out["C2_planning_number_sensitivity_to_the_cost_gap"] = {
    "A0_mean_g_bps_pinned": A0["mean_g_bps"], "A0_sharpe_pinned": A0["sharpe"], "n": A0["n"],
    "gap_bps_per_unit_traded_notional": gap,
    "by_turnover_assumption": res,
    "confound_test_is_the_markout_just_the_book_being_wrong": {
        "A0_expected_alpha_per_60s_bps": round(alpha_per_60s, 5),
        "measured_markout60_bps": out["C1_realized_exec_cost_vs_60s_fair_value"]["markout60_bps_notional_weighted"],
        "ratio": round(abs(out["C1_realized_exec_cost_vs_60s_fair_value"]["markout60_bps_notional_weighted"]) / alpha_per_60s, 1),
        "reading": "the 60s markout is ~1000x the book's own expected alpha over 60s, so it is "
                   "microstructure (adverse selection), not the book's directional view being wrong."},
    "CAVEAT": "markout at 60s is not proven to be a permanent cost for a multi-day holder; "
              "the desk records no other lag. This is the measurement named in HIGHEST_VALUE_NEXT.",
}
def need(n_years):
    return 3.0 + 1.96 * math.sqrt(2190.0 / (2190.0 * n_years))
out["C3_demonstrability_of_the_stated_objective"] = {
    "SE_annualised_sharpe_formula": "sqrt(2190/n)",
    "point_estimate_needed_for_CI95_lower_bound_over_3.0_by_history_length": {
        "1y": round(need(1), 4), "2y": round(need(2), 4), "3y": round(need(3), 4),
        "4.17y_the_whole_panel": round(3.0 + 1.96 * math.sqrt(2190.0 / 9138), 4),
        "10y_hypothetical": round(need(10), 4)},
    "usable_panel_years": round(9138 / 2190.0, 3),
    "incumbent_frozen_window_best_ever": {"sharpe": 2.9357, "CI95": [1.306, 4.565]},
    "reading": "A NEW component, judged on the data it can have, cannot demonstrate a CI95 lower "
               "bound above 3.0 unless its point estimate exceeds 4.96 (1y) / 4.39 (2y) / 3.97 (4.17y). "
               "The objective as stated is bounded by the length of crypto history, not by skill.",
}
out["C4_A0_baseline_defects_carried_by_every_rho_screen"] = {
    "dead_F10_prefix": {k: add["A0_pinned_window_F10_dead_anchors"][k] for k in
        ("n_total", "n_dead", "frac_dead", "first_dead", "last_dead", "mean_g_on_dead",
         "mean_g_on_live", "sharpe_on_live_only")},
    "forward_windows_since_the_coverage_fix": {
        "r9_newly_covered_s42": {"n": add["newly_covered_anchors_s42"]["n"],
            "mean_g": add["newly_covered_anchors_s42"]["mean_g"],
            "CI95": add["newly_covered_anchors_s42"]["CI95_TASK_B2000"]},
        "r2_horizon_ext_window_QUOTED_L167": {"n": 121, "A0_mean_g": -3.282}},
}
out["C5_age_curve_fact_the_screen_produced_and_argued_away"] = {
    "gross_share_pct_older_than_7d": round(
        sum(b["gross_share_pct"] for b in arith["bands"] if b["band"] in ("age42_83", "age84p")), 3),
    "age42_83": {k: [b for b in arith["bands"] if b["band"] == "age42_83"][0][k]
                 for k in ("gross_share_pct", "standalone_sharpe", "mean_g_bps")},
    "age84p": {k: [b for b in arith["bands"] if b["band"] == "age84p"][0][k]
               for k in ("gross_share_pct", "standalone_sharpe", "mean_g_bps")},
    "young_bands_for_contrast": {b["band"]: [b["standalone_sharpe"], b["mean_g_bps"]]
        for b in arith["bands"] if b["band"] in ("age2_5", "age6_11", "age12_23", "age24_41")},
}
os.environ.get = _real_get
p_out = B + "r9_critic/RECEIPT_r9_critic_2026-09-12.json"
json.dump(out, open(p_out, "w"), indent=1)
print(json.dumps(out, indent=1))
