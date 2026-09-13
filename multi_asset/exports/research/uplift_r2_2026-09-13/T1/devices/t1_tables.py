#!/usr/bin/env python3
"""t1_tables.py — Mac. Render receipts/TABLES_T1.md from the T1 receipts only (no computation beyond formatting and re-reading stored numbers).
usage: /usr/bin/python3 devices/t1_tables.py <T1 dir>"""
import os, sys, json, hashlib
T1 = os.path.abspath(sys.argv[1]); RP = T1 + "/receipts/pod2"
J = json.load(open(RP + "/RECEIPT_T1_judge.json")); D = J["result"]
G = json.load(open(RP + "/RECEIPT_T1_drive_gates.json"))
S = json.load(open(RP + "/RECEIPT_T1_states.json")); LG = json.load(open(RP + "/RECEIPT_T1_lags.json")); D2R = json.load(open(RP + "/RECEIPT_T1_d2.json"))
RL = json.load(open(T1 + "/receipts/RECEIPT_T1_realized.json")); H2 = json.load(open(T1 + "/receipts/RECEIPT_T1_h2.json"))
H2BT = json.load(open(RP + "/RECEIPT_T1_h2b_train.json")); H2BS = json.load(open(T1 + "/receipts/RECEIPT_T1_h2b_serve.json")); H2BP = json.load(open(RP + "/RECEIPT_T1_h2b_dlposthoc.json"))
PHC = json.load(open(T1 + "/receipts/RECEIPT_T1_posthoc_live_reconcile.json")); PHP = json.load(open(RP + "/RECEIPT_T1_posthoc_common_position.json"))
ARMS = ["C0_s42", "C0_s2027", "NW_s42", "NW_s2027"]
out = []
def w(s=""): out.append(s)
def ci(s, nd=3): return "%+.*f [%+.*f, %+.*f]" % (nd, s["point"], nd, s["ci95_lo"], nd, s["ci95_hi"])
def vci(s, nd=3): return "%+.*f vci[%+.*f, %+.*f]" % (nd, s["point"], nd, s["vci_lo"], nd, s["vci_hi"])
w("# TABLES · T1 edge diagnosis (rendered by `devices/t1_tables.py` from receipts; do not edit by hand)")
w(); w("Units: bps per 4h anchor per unit gross. g = price − carry − cost. CI95 = UTC-day block bootstrap percentile (B=2000). vci = verdict interval point ± z_K·SE (z in T0).")
w(); w("## T0 · gates and z")
gP = G["gate"]["P"]; gI = G["gate"]["I"]
w("| gate | result |"); w("|---|---|")
w("| GATE P (rec/W/S0/R18A/legs bitwise vs r18 arms, 4 arms) | %s |" % gP["PASS"])
w("| GATE I (identities; NW rev24 == 0) | %s; C0 rev24 remnant Σ|contrib| / Σ|g| on W_ALPHA = %s |" % (gI["PASS"], ", ".join("%s %.4f" % (a, gI[a]["rev24_sum_abs_contrib_WALPHA_bps"] / gI[a]["all_sum_abs_g_WALPHA_bps"]) for a in ARMS if a.startswith("C0"))))
w("| GATE X (x0910 meta/panel == pinned on overlap, strict) | %s |" % S["gate_X"]["PASS_strict"])
w("| GATE S (state causality, 60 perturbed anchors) | %s (bad %d) |" % (S["gate_S"]["PASS"], S["gate_S"]["n_bad"]))
w("| GATE LAG0 (h=0 legs == NW_s42 legs_king/legs_fund) | %s (maxabs king %.1e, fund %.1e) |" % (LG["gate_LAG0"]["PASS"], LG["gate_LAG0"]["maxabs_king"], LG["gate_LAG0"]["maxabs_fund"]))
w("| GATE D2 (per-anchor == r6 D2 price) | %s (n %d, maxabs %.1e) |" % (D2R["gate_D2"]["PASS"], D2R["gate_D2"]["n_compared"], D2R["gate_D2"]["maxabs_per_anchor_price_r6variant"]))
w("| GATE L (REAL per-anchor == r6 j1_realized) | %s (%d/%d anchors, 0 mismatches) |" % (RL["gate_L"]["PASS"], RL["gate_L"]["n_compared"], RL["gate_L"]["n_r6_rows"]))
gr = D["arms"]["C0_s42"]["H4"]["gate_R_W_ALPHA"]; gr2 = D["arms"]["C0_s2027"]["H4"]["gate_R_W_ALPHA"]
w("| GATE R (r15 ARM-F − A0 on W_ALPHA) | s42 Δpnl %+.4f Δcarry %+.4f Δcost %+.4f Δg %+.4f; s2027 %+.4f / %+.4f / %+.4f / %+.4f (r15: −0.1847/−0.2404/+0.0378/+0.0179; −0.1793/−0.2353/+0.0367/+0.0193) |" % (gr["dpnl"], gr["dcarry"], gr["dcost"], gr["dg"], gr2["dpnl"], gr2["dcarry"], gr2["dcost"], gr2["dg"]))
w("| GATE H2 (15 names in producer ledger + ema) | %s |" % H2["gate_H2"]["PASS"])
w(); w("z: " + ", ".join("%s %.4f" % (k, v) for k, v in D["z"].items()))
w(); w("## T1 · windows")
w("| window | n | first | last | days |"); w("|---|---|---|---|---|")
for k, v in D["windows"].items():
    w("| %s | %s | %s | %s | %s |" % (k, v.get("n"), v.get("first"), v.get("last"), v.get("n_days", "")))
w(); w("## T2 · levels by period (replay executor caliber)")
for arm in ("C0_s42", "NW_s2027"):
    w(); w("### %s" % arm)
    w("| period | g | price | carry | cost | price fund | price king | price f10 | price long | price short |"); w("|---|---|---|---|---|---|---|---|---|---|")
    L = D["arms"][arm]["levels"]
    for n in ["W_ALPHA", "Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026"] + ["M2025_%02d" % m for m in range(1, 13)] + ["M2026_%02d" % m for m in range(1, 9)] + ["LIVE_REPLAY"]:
        x = L[n]
        w("| %s | %s | %s | %s | %.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |" % (n, ci(x["g"]), ci(x["price"]), ci(x["carry"]), x["cost"]["point"], x["price_fund"]["point"], x["price_king"]["point"], x["price_f10"]["point"], x["price_L"]["point"], x["price_S"]["point"]))
w(); w("## T3 · live window levels")
w("| instrument | stat | value |"); w("|---|---|---|")
for k in ("price", "carry", "g_pre", "price_L", "price_S", "carry_L", "carry_S", "gross_L", "gross_S"): w("| LIVE_D2 (deployed × replay y4, to 09-10 00Z) | %s | %s |" % (k, ci(D["LIVE_D2_levels"][k])))
for k in ("price", "carry", "cost", "g", "g_r6net", "price_s", "carry_s", "g_s", "price_L", "price_S", "carry_L", "carry_S", "cost_L", "cost_S", "gross_L", "gross_S"): w("| LIVE_REAL (ledger, to 09-11 20Z) | %s | %s |" % (k, ci(D["LIVE_REAL_levels"][k])))
r5 = D["LIVE_REAL_W5_R6_reconciliation"]; w("| LIVE_REAL ∩ E ≤ 1789056000 (= 2026-09-10 16:00Z; r6 W5 bound, whose code comment says 00Z) | n / price / funding / cost / g / r6-net | %d / %+.3f / %+.3f / %+.3f / %+.3f / %+.3f |" % (r5["n"], r5["price"], r5["fund"], r5["fee_timing_cost"], r5["g"], r5["g_r6net"]))
c = PHC["result"]
w("| POST-HOC common 78 anchors | REAL price / carry / cost / g ; D2 price / carry / g_pre | %+.3f / %+.3f / %+.3f / %+.3f ; %+.3f / %+.3f / %+.3f |" % (c["common"]["real_price"], c["common"]["real_carry"], c["common"]["real_cost"], c["common"]["real_g"], c["common"]["d2_price"], c["common"]["d2_carry"], c["common"]["d2_g_pre"]))
w("| POST-HOC only-REAL 11 anchors (%s…%s) | REAL price / g | %+.2f / %+.2f |" % (c["only_real_utc"][0], c["only_real_utc"][-1], c["only_real"]["real_price"], c["only_real"]["real_g"]))
w("| POST-HOC only-D2 11 anchors (%s) | D2 price / g_pre | %+.2f / %+.2f |" % (", ".join(c["only_d2_utc"]), c["only_d2"]["d2_price"], c["only_d2"]["d2_g_pre"]))
rg = c["common_price_regression_real_on_d2"]; w("| POST-HOC common anchors | REAL price ~ D2 price | slope %.4f intercept %+.4f ρ %.4f |" % (rg["slope"], rg["intercept"], rg["rho"]))
w(); w("## T4 · ranked cells: contribution to (g_T − g_H1_2026)")
for arm in ARMS:
    A = D["arms"][arm]["cells"]
    w(); w("### %s" % arm)
    for T in ("M2026_08", "LIVE_REPLAY", "M2026_07", "Y2023"):
        x = A[T]; w(); w("**%s** Δg %+.3f (Σ cells %+.3f)" % (T, x["dg"], x["sum_cells"]))
        w("| rank | cell (component\\|side, leg) | contribution | CI95 | mean T | mean H1 |"); w("|---|---|---|---|---|---|")
        for q, cc in enumerate(x["cells"][:(24 if arm == "C0_s42" else 6)]): w("| %d | %s | %+.3f | [%+.3f, %+.3f] | %+.3f | %+.3f |" % (q + 1, cc["cell"], cc["contrib"], cc["ci95"][0], cc["ci95"][1], cc["mean_T"], cc["mean_H1"]))
    for T in ("LIVE_D2", "LIVE_REAL", "LIVE_REAL_scaled"):
        x = A[T]; w(); w("**%s** %s" % (T, "Δg_pre %+.3f" % x["dg_pre"] if "dg_pre" in x else "Δg %+.3f" % x["dg"]))
        w("| rank | cell | contribution | CI95 | mean T | mean H1 (replay) |"); w("|---|---|---|---|---|---|")
        for q, cc in enumerate(x["cells"]): w("| %d | %s | %+.3f | [%+.3f, %+.3f] | %+.3f | %+.3f |" % (q + 1, cc["cell"], cc["contrib"], cc["ci95"][0], cc["ci95"][1], cc["mean_T"], cc["mean_H1"]))
w(); w("## T5 · state × cell (C0_s42; quintiles Q1..Q5 on PRE_LIVE; top 8 of each; mix/within on g)")
A = D["arms"]["C0_s42"]["cells"]
for T in ("M2026_08", "Y2023", "LIVE_D2", "LIVE_REAL"):
    for s, v in A[T]["state_cells"].items():
        head = "**%s × %s** Σ %+.3f" % (T, s, v["sum_contrib"])
        if "mix" in v: head += " · mix %+.3f · within %+.3f" % (v["mix"], v["within"])
        head += " · f_T %s · f_H1 %s" % ([round(x, 2) for x in v["f_T"]], [round(x, 2) for x in v["f_H1"]])
        w(); w(head); w("| cell | contribution | CI95 |"); w("|---|---|---|")
        for cc in v["top30"][:8]: w("| %s | %+.3f | [%+.3f, %+.3f] |" % (cc["cell"], cc["contrib"], cc["ci95"][0], cc["ci95"][1]))
w(); w("Quintile edges (PRE_LIVE): " + "; ".join("%s %s" % (k, [round(x, 4) for x in v]) for k, v in D["quintile_edges_PRE_LIVE"].items()))
w(); w("## T6 · deliverable (2): price-edge-gone / carry-persisted by month (F_MONTH, K=10)")
for arm in ARMS:
    M = D["arms"][arm]["month"]; w(); w("### %s — P_ref %.3f, C_ref %.3f → **%s**" % (arm, M["P_ref"], M["C_ref"], M["vanish"]))
    w("| month | price (vci) | carry CI95 | price gone | carry persisted |"); w("|---|---|---|---|---|")
    for k, v in M["months"].items(): w("| %s | %s | %s | %s | %s |" % (k, vci(v["price"]), ci(v["carry"]), v.get("price_gone"), v.get("carry_persisted", "—")))
w(); w("## T7 · H1 / H1-fuel (F_H1, K=10)")
for arm in ARMS:
    H = D["arms"][arm]["H1"]; w(); w("### %s — H1 **%s**, H1-fuel **%s**; D_TA %s; D_TL %s" % (arm, H["H1_verdict"], H["H1fuel_verdict"], vci(H["D_TA"]), vci(H["D_TL"])))
    w("| state|target | MIX | MIX/D | cell verdict | μ_b (STATE_FIT) | f_H1 | f_T |"); w("|---|---|---|---|---|---|---|")
    for k, v in H.items():
        if "|" in k: w("| %s | %s | %.3f | %s | %s | %s | %s |" % (k, vci(v["MIX"]), v["mix_over_D"], v["cell_verdict"], [round(x, 2) for x in v["mu_STATE_FIT"]], [round(x, 2) for x in v["f_H1"]], [round(x, 2) for x in v["f_T"]]))
w(); w("## T8 · H3 signal-level lag profiles (F_H3, K=8) — verdict **%s**" % D["H3"]["verdict"])
w("| leg|target | n H1 / T | E0 H1 → T | E1 H1 → T | ΔE0 | ΔE1 | cell | t½ H1 / T |"); w("|---|---|---|---|---|---|---|---|---|")
for k, v in D["H3"].items():
    if k == "verdict": continue
    w("| %s | %d / %d | %+.3f → %+.3f | %+.2f → %+.2f | %s | %s | %s | %s / %s |" % (k, v["n_H1"], v["n_T"], v["E0_H1"], v["E0_T"], v["E1_H1"], v["E1_T"], vci(v["dE0"]), vci(v["dE1"], 2), v["cell_verdict"], v["t_half_H1"], v["t_half_T"]))
for k, v in D["H3"].items():
    if k == "verdict": continue
    w(); w("%s profile h=0..23 — H1: %s" % (k, [round(x, 2) for x in v["profile_H1"]])); w("%s profile h=0..23 — T : %s" % (k, [round(x, 2) for x in v["profile_T"]]))
w(); w("## T9 · H4 compensation (F_H4, K=3)")
for arm in ARMS:
    H = D["arms"][arm]["H4"]; w(); w("### %s — **%s**" % (arm, H["verdict"]))
    w("ρ_H1 %s · ρ_LIVE_D2 %s · ρ_LIVE_REAL %s · ρ_LIVE_REAL scaled %s" % (vci(H["rho_H1"]), vci(H["rho_LIVE_D2"]), vci(H["rho_LIVE_REAL"]), vci(H["rho_LIVE_REAL_scaled"])))
    w("| period | ρ cohort-direct | cohort price | cohort carry | κ arm-based (r15 def.) | Δpnl | Δcarry |"); w("|---|---|---|---|---|---|---|")
    for n, v in H["by_period"].items(): w("| %s | %s | %+.3f | %+.3f | %s | %s | %s |" % (n, ci(v["rho"]), v["coh_price"], v["coh_carry"], ci(v["kappa"]) if "kappa" in v else "n/a (no NW ARM-F)", ("%+.3f" % v["dpnl"]) if "dpnl" in v else "", ("%+.3f" % v["dcarry"]) if "dcarry" in v else ""))
    w("LIVE cohort price/carry: D2 %s; REAL %s" % ([round(x, 3) for x in H["LIVE_D2_coh_price_carry"]], [round(x, 3) for x in H["LIVE_REAL_coh_price_carry"]]))
w(); w("## T10 · H5 (F_H5, K=4)")
for arm in ARMS:
    H = D["arms"][arm]["H5"]; w(); w("### %s — **%s**" % (arm, H["verdict"]))
    w("c1 share SIGF<4.75: Y2023 %.3f · LIVE_D2 %.3f · diff %+.3f" % (H["c1_share_SIGF_lt_4p75"]["Y2023"], H["c1_share_SIGF_lt_4p75"]["LIVE_D2"], H["c1_diff"]))
    w("| stat | 2023 | LIVE_D2 | LIVE_REAL |"); w("|---|---|---|---|")
    w("| π = price/carry | %s | %s | %s |" % (ci(H["pi_2023"]), ci(H["pi_LIVE_D2"]), ci(H["pi_LIVE_REAL"])))
    w("| σs = short price / short gross | %s | %s | %s |" % (ci(H["sigma_short_2023"]), ci(H["sigma_short_LIVE_D2"]), ci(H["sigma_short_LIVE_REAL"])))
    w("Δπ D2 %s · Δσ D2 %s · Δπ REAL %s · Δσ REAL %s · Δπ REAL scaled %s · Δσ REAL scaled %s" % (vci(H["dpi_D2"]), vci(H["dsig_D2"]), vci(H["dpi_REAL"]), vci(H["dsig_REAL"]), vci(H["dpi_REAL_scaled"]), vci(H["dsig_REAL_scaled"])))
w(); w("## T11 · deliverable (5): live window in the historical state distribution")
for arm in ("C0_s42", "NW_s2027"):
    P = D["arms"][arm]["position"]; w(); w("### %s — reading **%s**" % (arm, P["reading"]))
    w("| state | live mean | pct in PRE_LIVE anchors | pct in %d-anchor window means (n %d) |" % (P["window_len"], P["n_windows"])); w("|---|---|---|---|")
    for s in P["live_mean_state"]: w("| %s | %.4f | %.3f | %.3f |" % (s, P["live_mean_state"][s], P["pct_in_PRE_LIVE_anchors"][s], P["pct_in_window_means"][s]))
    a = P["analog"]; w("kNN analog (1000 anchors, max dist %.3f, years %s): g %s · price %s · carry %s · cost %s" % (a["max_dist"], a["years"], ci(a["g"]), ci(a["price"]), ci(a["carry"]), ci(a["cost"])))
    w("live stats %s · unconditional pct %s · conditional pct %s" % ({k: round(v, 3) for k, v in P["live_stats"].items()}, {k: round(v, 3) for k, v in P["uncond_pct"].items()}, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in P["cond_pct"].items()}))
pp = PHP["result"]; w(); w("POST-HOC common 78 anchors: live REAL g %+.3f (scaled %+.3f), D2 g_pre %+.3f; " % (pp["live_REAL_g"], pp["live_REAL_g_scaled"], pp["live_D2_g_pre"]) + "; ".join("%s uncond %s cond %s (cond years %s)" % (a, {k: round(v, 3) for k, v in x["uncond"].items()}, {k: round(v, 3) for k, v in x["cond"].items()}, x["cond_years"]) for a, x in pp["arms"].items()))
w(); w("## T12 · H2 / H2b")
w("| name | rows | span-table h | LIVE rows | LIVE recorded iv | LIVE snapped gap | mismatch LIVE / all | EMA rel diff (recorded iv) |"); w("|---|---|---|---|---|---|---|---|")
for s, v in H2["E2"].items(): w("| %s | %d | %s | %d | %s | %s | %d / %d | %.1e |" % (s, v["n_rows"], v["span_table_interval_h"], v["n_live_rows"], v["live_recorded_iv_counts"], v["live_snapped_gap_counts"], v["mismatch_live"], v["mismatch_all"], v["rel_diff_recorded_iv"]))
w(); w("H2 verdict **%s**; venue cross-check (executor income ledger interval vs producer iv): stale-15 %s; all names n %d mismatch %d; producer iv≠gap rows all names %d of %d (all before 2026-08-15)" % (H2["H2"]["VERDICT"], {k: (v["n"], v["mismatch"]) for k, v in H2["venue_crosscheck_stale15"].items()}, H2["venue_crosscheck_all_names"]["n"], H2["venue_crosscheck_all_names"]["mismatch"], H2["producer_ledger_all_names_iv_vs_gap"]["mismatch"], H2["producer_ledger_all_names_iv_vs_gap"]["n_rows"]))
w("REAL book-layer share of the 15 names in LIVE_REAL: %s" % H2["real_shares"])
w("Replay layer (C0_s42): %s" % D["arms"]["C0_s42"]["H2_descriptive_replay"])
w("D2 layer: 15-name gross %s · price %s · carry %s · fund signal |z| share %s · fund signal lr0 of 15 %s vs all %s" % (ci(D["LIVE_D2_levels"]["st15_gross"], 4), ci(D["LIVE_D2_levels"]["st15_price"]), ci(D["LIVE_D2_levels"]["st15_carry"]), ci(D["LIVE_D2_levels"]["fundsig_st15_absz_share"], 4), ci(D["LIVE_D2_levels"]["fundsig_st15_lr0"]), ci(D["LIVE_D2_levels"]["fundsig_lr0"])))
w(); w("| H2b training file | cells (iv=4) | s0 (== float16 v0) | s1 (== float16 v1) |"); w("|---|---|---|---|")
for k in ("king_v2ext_0901", "king_v4", "dl_ext_0901", "dl_v4raw"): x = H2BT["result"][k]; w("| %s | %d | %.6f | %.6f |" % (k, x["n_cells"], x["s0"], x["s1"]))
w("training caliber by rule: **%s**; serving (xfer_panel_live, %d names iv=4): served/v1 %.6f, served/v0 %.6f → %s" % (H2BT["result"]["training_caliber"], H2BS["result"]["n_names_iv4"], H2BS["result"]["median_served_over_v1"], H2BS["result"]["median_served_over_v0"], H2BS["result"]["serving_caliber"]))
w("POST-HOC DL non-matching cells: %s" % {k: dict(n_neq=v["n_neq"], stored_over_v0_pct=v["ratio_stored_over_v0_pct"], fund_now_equal_on_neq=round(v["fund_now_share_equal_on_neq_cells"], 4)) for k, v in H2BP["result"].items()})
w("LIVE_D2 non-8h names: gross %s · price %s · carry %s" % (ci(D["LIVE_D2_levels"]["non8h_gross"], 4), ci(D["LIVE_D2_levels"]["non8h_price"]), ci(D["LIVE_D2_levels"]["non8h_carry"])))
w(); w("## T13 · verdict agreement across arms"); w("```"); w(json.dumps(D["verdict_agreement"], indent=1)); w("```")
open(T1 + "/receipts/TABLES_T1.md", "w").write("\n".join(out) + "\n")
print("wrote receipts/TABLES_T1.md", len(out), "lines")
