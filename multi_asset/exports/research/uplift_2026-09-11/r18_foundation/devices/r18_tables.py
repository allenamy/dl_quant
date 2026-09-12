#!/usr/bin/env python3
"""r18_tables.py — render every table of RESULT_r18 from the receipts (numbers never typed by hand).
Reads receipts/RECEIPT_r18_{drive_gateP,gates,judge,lev}.json; writes receipts/TABLES_r18.md. Local (Mac) or pod2."""
import json, sys, os
R = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = json.load(open(R + "/receipts/RECEIPT_r18_drive_gateP.json")); GT = json.load(open(R + "/receipts/RECEIPT_r18_gates.json")); J = json.load(open(R + "/receipts/RECEIPT_r18_judge.json")); LV = json.load(open(R + "/receipts/RECEIPT_r18_lev.json"))
S = ("42", "2027"); L = []
def f(x, d=4, s=True): return ("%+." + str(d) + "f") % x if s else ("%." + str(d) + "f") % x
def ci(c, d=3): return "[%s, %s]" % (f(c[0], d), f(c[1], d))
def pct(x, d=2): return "%.{}f%%".format(d) % (100 * x)
L.append("# TABLES r18 (rendered from receipts by devices/r18_tables.py)\n")
L.append("prereg sha %s · amendment sha %s · derived device sha %s · judge self_sha %s · lev self_sha %s\n" % (J["prereg_sha256"][:16], GT["amendment_sha256"][:16], J["derived_device_sha256"][:16], J["self_sha256"][:16], LV["self_sha256"][:16]))
# ---- gates
L.append("## T0 Gates\n\n| gate | result |\n|---|---|")
for k, v in G["gate"]["P"].items():
    if k != "PASS": L.append("| GATE P %s | rec bitwise %s (shape %s, maxabs %s) · W bitwise %s (maxabs %s) · cols equal %s |" % (k, v["rec"]["bitwise"], v["rec"]["shape"], v["rec"]["maxabs"], v["W"]["bitwise"], v["W"]["maxabs"], v["cols_equal"]))
r = GT["GATE_R"]; L.append("| GATE R (reviewer 108/108/3, OLD rule, archived A0 s42) | cells %d · anchors %d · held %d · prior gross %.11f · max|W| on fut cells %.1f · full-axis fut cells %d ⇒ **%s** |" % (r["W_ALPHA_future_missing_eligible_cells"], r["anchors_with_any"], r["previously_held_cells"], r["previous_gross_affected_sum"], r["future_missing_current_W_max"], r["full_axis_future_missing_eligible_cells"], "PASS" if r["PASS"] else "FAIL"))
y = GT["GATE_Y"]; L.append("| GATE Y as registered (plain-sum formula, 60 anchors) | NaN mismatch fwd %d / closed %d · value maxabs fwd %.4f / closed %.4f ⇒ **%s** (formula wrong, window right; see AMENDMENT 1) |" % (y["fwd_nan_mismatch"], y["closed_nan_mismatch"], y["fwd_maxabs"], y["closed_maxabs"], "PASS" if y["PASS"] else "FAIL"))
y2 = GT["GATE_Y2"]; ex = y2["mismatch_exposure_archived_A0_s42"]
L.append("| GATE Y2 (AMENDMENT 1: Π(1+r)−1, full axis %d anchors) | NaN mismatch fwd %d / closed %d ⇒ window **%s** · finite fwd cells %d · value>1e-5 cells fwd %d / closed %d (maxabs %.4f / %.4f) |" % (y2["n_anchors"], y2["fwd_nan_mismatch"], y2["closed_nan_mismatch"], "PASS" if y2["window_PASS"] else "FAIL", y2["fwd_finite_cells"], y2["fwd_value_mismatch_cells"], y2["closed_value_mismatch_cells"], y2["fwd_maxabs"], y2["closed_maxabs"]))
L.append("| GATE Y2 mismatch exposure in archived A0 s42 | %d cells on %d anchors; traded (|W|>0) %d (W_ALPHA %d); Σ|W|·|Δy4| = %.4f bps W_FULL / %.4f bps W_ALPHA; max cell %.4f bps; median |Δy4| %.4f, max %.4f |" % (ex["cells"], ex["anchors"], ex["cells_traded"], ex["cells_traded_WALPHA"], ex["sum_absW_x_absdy_bps_WFULL"], ex["sum_absW_x_absdy_bps_WALPHA"], ex["max_cell_bps"], ex["median_absdy"], ex["max_absdy"]))
L.append("| GATE Y2 mismatch cells by symbol | %s |" % json.dumps(ex["by_symbol"])); L.append("| GATE Y2 mismatch cells by month | %s |" % json.dumps(ex["by_month"]))
L.append("| env (driver) | whitelist %s; loadavg %s → %s; GPU %s → %s; PIDs %s → %s |\n" % (G["env"]["env_whitelist"], G["loadavg_before"], G["loadavg_after"], G["gpu_before"], G["gpu_after"], G["protected_pids_before"].replace("\n", ";"), G["protected_pids_after"].replace("\n", ";")))
# ---- levels
L.append("## T1 Levels (g bps/anchor/unit gross; Sharpe; matched turnover) — C0 = archived A0 bitwise\n\n| arm | seed | window | n | g | CI95 | Sharpe (SE) | τ matched | pnl / carry / cost | netlong |\n|---|---|---|---|---|---|---|---|---|---|")
for s in S:
    for arm, key in (("C0", ("C0", s)), ("NW", ("NW", s))):
        for w in ("W_FULL", "W_ALPHA", "KING_LIVE"):
            v = J[arm][s]["level_" + w]
            L.append("| %s | %s | %s | %d | %s | %s | %.4f (%.3f) | %.5f | %s / %s / %s | %s |" % (arm, s, w, v["n"], f(v["g"]), ci(v["ci95"]), v["sharpe"], v["sharpe_se"], v["tau_matched"], f(v["pnl"]), f(v["carry"]), f(v["cost"]), f(v["netlong"])))
L.append("")
# ---- deltas
L.append("## T2 Paired Δg vs C0 (same seed, same anchors); K=%d Bonferroni\n\n| arm | seed | window | Δg | CI95 (k0) | CI95 (k9) | CI99K | Δpnl / Δcarry / Δcost | Δτ %% | anchors where g differs | first / last differing anchor | Sharpe arm vs C0 |\n|---|---|---|---|---|---|---|---|---|---|---|---|" % J["K"])
for s in S:
    for arm in ("N2", "WU", "NW"):
        for w in ("W_FULL", "W_ALPHA", "KING_LIVE"):
            v = J[arm][s][w] if arm != "NW" else J["NW"][s]["vs_C0"][w]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s / %s / %s | %+.2f | %d / %d | %s / %s | %.4f vs %.4f |" % (arm, s, w, f(v["dg"]), ci(v["ci95"]), ci(v.get("ci95_k9", [float("nan"), float("nan")])), ci(v["ci99K"]), f(v["dpnl"]), f(v["dcarry"]), f(v["dcost"]), v["dtau_pct"], v["n_anchors_g_differs"], v["n"], v["first_anchor_g_differs"], v["last_anchor_g_differs"], v["sharpe_arm"], v["sharpe_base"]))
L.append("")
L.append("## T2b Smoothing corners on the FIXED book (Δg vs NW, same seed)\n\n| arm | seed | window | g arm | Δg vs NW | CI95 | CI99K | Δτ % | Sharpe arm vs NW |\n|---|---|---|---|---|---|---|---|---|")
for s in S:
    for arm in ("NW_S05", "NW_B50"):
        for w in ("W_ALPHA", "W_FULL"):
            v = J["NW"][s]["smoothing_" + arm][w]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %+.2f | %.4f vs %.4f |" % (arm, s, w, f(v["g_arm"]), f(v["dg"]), ci(v["ci95"]), ci(v["ci99K"]), v["dtau_pct"], v["sharpe_arm"], v["sharpe_base"]))
L.append("")
# ---- per-year
L.append("## T3 Per-year g (W_FULL rows; year of anchor)\n\n| seed | arm | " + " | ".join(str(y) for y in sorted(J["C0"]["42"]["level_W_FULL"]["by_year"])) + " |\n|---|---|" + "---|" * len(J["C0"]["42"]["level_W_FULL"]["by_year"]))
for s in S:
    for arm in ("C0", "NW"):
        by = J[arm][s]["level_W_FULL"]["by_year"]; L.append("| %s | %s | " % (s, arm) + " | ".join("%s (n %d)" % (f(by[y]["g"], 3), by[y]["n"]) for y in sorted(by)) + " |")
L.append("")
# ---- N2
L.append("## T4 N2 — causal eligibility\n")
for s in S:
    n = J["N2"][s]
    L.append("**seed %s** · aux (device-counted, W_FULL): eligibility changed cells %d (new-only %d, old-only %d) on %d anchors; W_ALPHA: %d (%d / %d) on %d anchors. Input-side (gates): new-only %d full / %d W_ALPHA, old-only %d / %d, both-NaN-liquid %d / %d." % (
        s, n["aux_full"]["n_elig_changed"], n["aux_full"]["n_new_only"], n["aux_full"]["n_old_only"], n["aux_full"]["anchors_changed"], n["aux_WA"]["n_elig_changed"], n["aux_WA"]["n_new_only"], n["aux_WA"]["n_old_only"], n["aux_WA"]["anchors_changed"],
        n["input_side_counts"]["new_only_full"], n["input_side_counts"]["new_only_WALPHA"], n["input_side_counts"]["old_only_full"], n["input_side_counts"]["old_only_WALPHA"], n["input_side_counts"]["both_nan_liquid_full"], n["input_side_counts"]["both_nan_liquid_WALPHA"]))
    u = n["unknown_return_exposure"]; L.append("unknown-return exposure under N2 (selected names whose forward return is NaN, booked 0): W_FULL %d cells on %d anchors, Σ|sm| %.5f (max per anchor %.5f); W_ALPHA %d cells / %d anchors, Σ|sm| %.5f. Under C0: %d cells." % (u["WT"]["cells"], u["WT"]["anchors"], u["WT"]["sum_abs_sm"], u["WT"]["max_abs_sm_anchor"], u["WA"]["cells"], u["WA"]["anchors"], u["WA"]["sum_abs_sm"], n["c0_unknown_return_cells_WT"]))
    L.append("\n| reviewer cell | C0 W[i−1] → W[i] → W[i+1] | N2 W[i−1] → W[i] → W[i+1] | kept at i | exit at i+1 |\n|---|---|---|---|---|")
    for c in n["reviewer_cells"]: L.append("| %s %s | %+.6f → %+.6f → %+.6f | %+.6f → %+.6f → %+.6f | %s | %s |" % (c["iso"], c["symbol"], c["C0_W_prev"], c["C0_W"], c["C0_W_next"], c["N2_W_prev"], c["N2_W"], c["N2_W_next"], c["N2_position_kept_at_i"], c["N2_exit_at_i_plus_1"]))
    L.append("")
# ---- WU
L.append("## T5 WU — warm-up book\n")
for s in S:
    w = J["WU"][s]
    L.append("**seed %s** · warm rows 0..899 = %s .. %s · w3 (king, rev24, fund) unique triples before %s → after %s · rev24 weight exactly 0 on all warm rows after: %s · max |w3_rev24| after row 900: C0 %.3g, WU %.3g · rows with leg_rev24 ≠ 0: before %d, after %d" % (
        s, w["warm_rows"]["first"], w["warm_rows"]["last"], w["w3_before"]["unique_triples"], w["w3_after"]["unique_triples"], w["rev24_weight_zero_on_all_warm_rows_after"], w["rev24_weight_after_row900_C0_max"], w["rev24_weight_after_row900_WU_max"], w["leg_rev24_nonzero_rows_before"], w["leg_rev24_nonzero_rows_after"]))
    a = w["anchor_2022_06_07_20Z"]; L.append("\n| 2022-06-07 20Z | g | net_ex (bps) | gross_total | leg_king | leg_rev24 | leg_fund | w3 | pnl / carry / cost (per unit gross) |\n|---|---|---|---|---|---|---|---|---|")
    for k in ("before", "after"): v = a[k]; L.append("| %s | %s | %s | %.4f | %s | %s | %s | %s | %s / %s / %s |" % (k, f(v["g"], 2), f(v["net_ex_bps"], 2), v["gross_total"], f(v["leg_king"], 2), f(v["leg_rev24"], 2), f(v["leg_fund"], 2), [round(x, 3) for x in v["w3"]], f(v["pnl"], 2), f(v["carry"], 2), f(v["cost"], 2)))
    d = w["day_2022_06_07"]; L.append("\n| UTC day 2022-06-07 | anchors | Σg | day ret @2.0× | Σ leg_king | Σ leg_rev24 | Σ leg_fund | per-anchor g |\n|---|---|---|---|---|---|---|---|")
    for k in ("before", "after"): v = d[k]; L.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (k, v["anchors"], f(v["sum_g"], 2), pct(v["day_ret_L2"]), f(v["sum_leg_king"], 2), f(v["sum_leg_rev24"], 2), f(v["sum_leg_fund"], 2), [round(x, 1) for x in v["per_anchor_g"]]))
    L.append("\n| worst UTC day (L=2.0, M=1.0, W_FULL) | day | day ret | anchors | Σg | Σ leg_king | Σ leg_rev24 | Σ leg_fund |\n|---|---|---|---|---|---|---|---|")
    for k in ("before", "after"): v = w["worst_day_L2_M1_" + k]; dd = v["decomposition"]; L.append("| %s | %s | %s | %d | %s | %s | %s | %s |" % (k, v["worst_day"], pct(v["day_ret"]), dd["anchors"], f(dd["sum_g"], 2), f(dd["sum_leg_king"], 2), f(dd["sum_leg_rev24"], 2), f(dd["sum_leg_fund"], 2)))
    L.append("")
# ---- tail tables
def tailtab(title, t):
    L.append("### %s\n\n| L | M | maxDD (peak→trough) | worst day | halt ≤−4%% | alert ≤−2.68%% | halts/yr | P(1y true maxDD≥25%%) | P(1y start-loss≥25%%) [r12's] | median 1y ret | ann ret | day σ |\n|---|---|---|---|---|---|---|---|---|---|---|---|" % title)
    for k in sorted(t, key=lambda k: (float(k.split("_")[1][1:]), float(k.split("_")[0][1:]))):
        v = t[k]; L.append("| %.2f | %.4f | %s (%s→%s) | %s %s | %d | %d | %.2f | %s | %s | %s | %s | %s |" % (v["L"], v["M"], pct(v["maxdd"], 1), v["maxdd_peak"], v["maxdd_trough"], v["worst_day"], pct(v["worst_day_ret"]), v["halt"], v["alert"], v["halt_per_yr"], pct(v["p_true_maxDD25"], 2), pct(v["p_start_loss25"], 2), pct(v["median_1y_ret"], 1), pct(v["ann_ret"], 1), pct(v["sd_day"], 3)))
    L.append("")
L.append("## T6 Tail tables (W_FULL, n=%d, UTC-day compounding; M=1.4042 is a SENSITIVITY, not a fact)\n" % J["windows"]["W_FULL"])
for s in S:
    tailtab("C0 (archived A0) seed %s" % s, J["C0"][s]["tail"]); tailtab("WU seed %s" % s, J["WU"][s]["tail"]); tailtab("N2 seed %s" % s, J["N2"][s]["tail"]); tailtab("NW (fixed baseline) seed %s" % s, J["NW"][s]["tail"])
# ---- published
L.append("## T7 Published verdicts re-read against NW (archived arms, defects ON; Δ_vs_NW = Δ_vs_A0 − (NW−A0))\n\n| arm | seed | window | Δg vs A0 | CI95 | excl 0 | Δg vs NW | CI95 | excl 0 | sign change | CI-status change | NW−A0 |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in sorted(J["published"]):
    v = J["published"][k]
    if v.get("missing"): L.append("| %s | missing %s |" % (k, v["path"])); continue
    for w in ("W_ALPHA", "KING_LIVE"):
        a, n_ = v["vs_A0"][w], v["vs_NW"][w]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (k.split("/")[0] + " " + k.split("/")[1], k.split("/")[2], w, f(a["dg"]), ci(a["ci95"]), a["ci95_excl0"], f(n_["dg"]), ci(n_["ci95"]), n_["ci95_excl0"], v["sign_change_" + w], v["ci_status_change_" + w], f(v["NW_minus_A0_W_ALPHA"])))
L.append("")
# ---- lev
L.append("## T8 LEV12-FIX — corrected gate on every r12 cell (archived, defects ON) and on the fixed baseline\n")
L.append("reconcile with r12's LEV12.json (p_start_loss25 ≡ r12's `p_1y_dd_ge25`, halts, medians, feasible L under the old gate): all match 1e-9 = **%s**, feasible-L match = **%s**. Reconcile with reviewer's RECEIPT_smoothing.json (6 arms, p_true and p_start at every L, M∈{1.0,1.4042}): all match 1e-9 = **%s**.\n" % (LV["reconcile_r12_LEV12"]["all_match_1e9"], LV["reconcile_r12_LEV12"]["all_feasible_match"], LV["reconcile_reviewer"]["all_match_1e9"]))
for M in ("M1.4042", "M1.0000"):
    L.append("### %s\n\n| arm | α | b | b/α | kind | L=1: halts/yr | L=1: P start-loss≥25 (old) | **L=1: P true maxDD≥25** | L=1: median 1y | max feasible L (old gate) | **max feasible L (true gate)** | median 1y @ feasible(true) | L=2: P true |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|" % M)
    for tag in sorted(LV["arms"], key=lambda t: (LV["arms"][t]["kind"], LV["arms"][t]["SMA"], LV["arms"][t]["SBAND"], str(LV["arms"][t]["seed"]))):
        a = LV["arms"][tag]; m = a[M]; r1 = m["at_L1"]
        L.append("| %s | %.2f | %.2e | %.4f | %s | %.2f | %s | **%s** | %s | %s | **%s** | %s | %s |" % (tag, a["SMA"], a["SBAND"], a["SBAND"] / a["SMA"], a["kind"].replace("archived_r12_defects_on", "archived").replace("fixed_baseline_r18", "FIXED"), r1["halt_per_yr"], pct(r1["p_start_loss25"]), pct(r1["p_true_maxDD25"]), "%+.1f%%" % r1["median_1y_ret_pct"], m["max_feasible_L_oldgate"], m["max_feasible_L_true"], ("%+.1f%%" % m["median_1y_ret_at_feasible_true_pct"]) if m["max_feasible_L_true"] is not None else "n/a", pct(m["at_L2"]["p_true_maxDD25"])))
    L.append("")
L.append("### Round-12 claims under the corrected gate (M=1.4042 as r12 used)\n")
for k, v in LV["round12_claims"].items():
    if k == "d_slower_is_better":
        L.append("- **d** slower is better (POINT ESTIMATES, no CI): " + json.dumps({kk: {M: dict(slower_better_at_feasible=vv[M]["slower_better_at_feasible"], slower_better_at_L1=vv[M]["slower_better_at_L1"], same_feasible_L=vv[M]["same_feasible_L"], per_arm=vv[M]["per_arm"]) for M in vv} for kk, vv in v.items() if kk != "note"}))
    else: L.append("- **%s** %s" % (k, json.dumps(v)))
open(R + "/receipts/TABLES_r18.md", "w").write("\n".join(L) + "\n"); print("wrote", R + "/receipts/TABLES_r18.md", len(L), "lines")
