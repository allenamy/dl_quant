#!/usr/bin/env python3
"""t5_tables.py — Mac. Renders receipts/TABLES_T5.md from the T5 receipts only (no recomputation). PREREG_T5 §9 step 5."""
import os, sys, json, hashlib, time
T5 = os.path.abspath(sys.argv[1])
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T5 + "/PREREG_T5_deployed_carry_gap_2026-09-13.md") == "33b20fa10109b95d9b4f0ff480619d82cd9bd1b7d2def7cf0a38c7938e83660f"
BR = json.load(open(T5 + "/receipts/pod2/RECEIPT_T5_bridge.json")); DR = json.load(open(T5 + "/receipts/pod2/RECEIPT_T5_drive_gateP.json"))
LI = json.load(open(T5 + "/receipts/RECEIPT_T5_live_ingredients.json")); AD = json.load(open(T5 + "/receipts/pod2/RECEIPT_T5_addendum1_h2b.json"))
S = BR["result"]["seeds"]; G = BR["result"]["groups"]; ORD = BR["result"]["order"]
ci = lambda x, d=3: "%+.*f [%+.*f, %+.*f]" % (d, x[0], d, x[1], d, x[2])
pct = lambda x: "%+.1f%% [%+.1f, %+.1f]" % (100 * x[0], 100 * x[1], 100 * x[2])
GNAME = dict(G0="G0 口径(装置 carry 分子只含成员)", T="T FTRIM(回放有, 部署窗内无)", W="W 席位 w3", B="B fund 秩基(829 基 → 成员内)", V="V fund 值与新鲜度(面板 → 生产者 EMA)",
             M="M 成员集(meta∩UMASK → 生产者 400)", X="X 出场规则", S="S 可交易门", P="P 止损层(回放独有)", H="H 状态路径(部署暖启动)", Z="Z 执行口径 reshape", REM="REM 分数(king + V2MAIN)与未对上部分")
L = []
L.append("# TABLES · T5 (rendered by `devices/t5_tables.py` from receipts; do not edit by hand)\n")
L.append("Units: modelled carry, bps / 4h anchor / unit gross, positive = paid. A_T5 = 27 combo anchors 2026-08-26 04Z..08-30 20Z (excl. 08-29 20Z, 08-30 00Z). CIs: UTC-day block bootstrap over **5 day-blocks — descriptive, not a test**. Rendered %s.\n" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
g = BR["gates"]
L.append("## T0 · gates\n| gate | result |\n|---|---|")
L.append("| G-P (T5 device vs T1 arms, 24 arrays, both seeds) | %s; window anchors %d; derived sha `%s…` |" % (DR["gate"]["P"]["PASS"], DR["gate"]["P"]["C0_s42"]["n_window_anchors"], DR["derived_device_sha256"][:12]))
t1 = g["G_T1"]
L.append("| G-T1 (reproduce T1) | %s; D2 A29 mean %.9f vs T1 %.9f, per-anchor maxabs %.1e; replay A30 carry s42 %.10f vs %.10f, s2027 %.10f vs %.10f |" % (t1["PASS"], t1["D2_mean_A29"], t1["T1_D2_mean_A29"], t1["D2_per_anchor_maxabs"], t1["R_carry_A30_s42"], t1["T1_R_carry_A30_s42"], t1["R_carry_A30_s2027"], t1["T1_R_carry_A30_s2027"]))
L.append("| G-PANEL (device panel rows == x0910 rows, FN & IV, 30 rows × 829) | %s |" % g["G_PANEL"]["PASS"])
gs = g["G_SIM_R"]["per_seed"]
L.append("| G-SIM-R (simulator all-R vs device dump) | %s; max|Δ| s42 %s; s2027 %s |" % (g["G_SIM_R"]["PASS"], {k: "%.1e" % v for k, v in gs["42"]["maxabs"].items()}, {k: "%.1e" % v for k, v in gs["2027"]["maxabs"].items()}))
L.append("| G-ARCH-D (target_live == 0.55·kc + 0.45·fc) | %s; maxabs %.1e (Mac and pod2) |" % (g["G_ARCH_D"]["PASS"] and LI["G_ARCH_D"]["PASS"], g["G_ARCH_D"]["max_abs"]))
L.append("| G-LEG (Σ legs = book) | %s; R %.1e, B_N %.1e |" % (g["G_LEG"]["PASS"], g["G_LEG"]["R"], g["G_LEG"]["BN"]))
L.append("| G-CLOSE (every lens, per anchor) | %s; max %s |" % (g["G_CLOSE"]["PASS"], "%.1e" % max(max(v.values()) for v in g["G_CLOSE"]["per_seed"].values())))
v = LI["G_ING_V"]; s_ = LI["G_ING_S"]
L.append("| G-ING-V (backward EMA 09-13 → 09-04 00Z reproduces stored fund z) | %s; max|Δz| %.1e; acc rel err max %.1e |" % (v["PASS"], v["max_abs_dz_members"], v["acc_rel_err_max"]))
L.append("| G-ING-S (archived nonzero ⊆ pm∩sel∩LIVE; sel count == producer log) | %s; violations %d; count mismatches %d |" % (s_["PASS"], s_["total_violations"], len(s_["anchors_sel_count_mismatch"])))
L.append("| G-POD | GPU %s → %s; PIDs %s → %s |" % (BR["gpu_before"], BR["gpu_after"], BR["pids_before"].replace("\n", "; "), BR["pids_after"].replace("\n", "; ")))
L.append("| K group included (T4 served-king arrays for the window) | %s → (e) NOT MEASURED in the main table |\n" % BR["K_included"])
L.append("## T1 · headline (A_T5, n = 27)\n| seed | C_D deployed | C_R replay (T1 caliber) | Δ | C_D / C_R |\n|---|---|---|---|---|")
for sd in ("42", "2027"):
    h = S[sd]["headline"]; L.append("| %s | %s | %s | %s | %s |" % (sd, ci(h["C_D"]), ci(h["C_R_T1"]), ci(h["Delta"]), ci(h["ratio"])))
kf = BR["kingform_anchors"]
L.append("\nExcluded king-form anchors (descriptive): " + "; ".join("%s C_D %.3f vs C_R %.3f (s42)" % (a, x["C_D"], x["C_R_T1"]) for a, x in kf["42"].items()) + ". T1's 2.218 (A29) includes these two.\n")
L.append("## T2 · construction bridge — Shapley (primary), fixed order, one-at-a-time, leave-one-out\n| component | s42 mean | s42 share of Δ | s2027 mean | s2027 share | order step s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |\n|---|---|---|---|---|---|---|---|")
for c in ["G0"] + ["phi_" + x for x in G] + ["REM"]:
    k = c.replace("phi_", ""); a = S["42"]["shapley"]; b = S["2027"]["shapley"]
    seq = ("%+.3f / %+.3f" % (S["42"]["sequential"]["mean"][k], S["2027"]["sequential"]["mean"][k])) if k in ORD else "—"
    oat = ("%+.3f" % S["42"]["one_at_a_time"][k]) if k in G else "—"; loo = ("%+.3f" % S["42"]["leave_one_out"][k]) if k in G else "—"
    L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (GNAME.get(k, k), ci(a["mean"][c]), pct(a["share"][c]), ci(b["mean"][c]), pct(b["share"][c]), seq, oat, loo))
L.append("\nFixed order: %s. Shapley efficiency maxabs %.1e / %.1e. Node skips %d / %d.\n" % (" → ".join(ORD), S["42"]["shapley"]["efficiency_maxabs"], S["2027"]["shapley"]["efficiency_maxabs"], S["42"]["node_skips"], S["2027"]["node_skips"]))
L.append("## T3 · per UTC day (s42; s2027 within ±0.02)\n| day | n | C_D | C_R | Δ | φ_T | φ_H | φ_P | φ_M | REM |\n|---|---|---|---|---|---|---|---|---|---|")
for d, x in S["42"]["per_day"].items():
    L.append("| %s | %d | %.3f | %.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |" % (d, x["n"], x["C_D"], x["C_R_T1"], x["Delta"], x["phi_T"], x["phi_H"], x["phi_P"], x["phi_M"], x["REM"]))
L.append("\n## T4 · L-S lens: side (own sign) × 8h-equivalent current rate (TC1)\n| cell | C_D cell | C_R cell | Δ cell s42 | share s42 | share s2027 |\n|---|---|---|---|---|---|")
for key, x in S["42"]["LS"]["cells"].items():
    if abs(x["D"]) + abs(x["R"]) < 0.001: continue
    L.append("| %s | %+.3f | %+.3f | %s | %s | %s |" % (key, x["D"], x["R"], ci(x["delta_mean"]), pct(x["delta_share"]), pct(S["2027"]["LS"]["cells"][key]["delta_share"])))
t = S["42"]["TC1"]; t2 = S["2027"]["TC1"]
L.append("\n**TC1** short ∧ rn8 ≤ −10bp: share of Δ %s (s42) / %s (s2027) ⇒ **%s / %s**. That cohort is %.1f%% of the deployed book's carry and %.1f%% of the replay's; its gross share %.1f%% (D) vs %.1f%% (R).\n" % (pct(t["delta_share"]), pct(t2["delta_share"]), t["reading_point"], t2["reading_point"], 100 * t["D_cohort_share_of_CD"], 100 * t["R_cohort_share_of_CR"], 100 * S["42"]["LS"]["gross_share"]["D_short_le_m10"], 100 * S["42"]["LS"]["gross_share"]["R_short_le_m10"]))
L.append("## T5 · L-N lens: name sets (task b, c)\n| cell | s42 mean | s42 share | s2027 share |\n|---|---|---|---|")
for c, x in S["42"]["LN"]["cells"].items():
    L.append("| %s | %s | %s | %s |" % (c, ci(x["mean"]), pct(x["mean_share"]), pct(S["2027"]["LN"]["cells"][c]["mean_share"])))
nn = S["42"]["LN"]["n_names_mean"]
L.append("\nNames per anchor (mean): only in D %.1f, only in R %.1f, common %.1f. Top common names by Σ(w̃_D − w̃_R)·c (s42, bps/anchor; weights ×1e3 per unit gross; rn8 mean bp):\n" % (nn["onlyD"], nn["onlyR"], nn["common"]))
L.append("| name | contribution | w_D | w_R | rn8 |\n|---|---|---|---|---|")
for x in S["42"]["LN"]["top_common"][:15]:
    L.append("| %s | %+.4f | %+.2f | %+.2f | %s |" % (x["symbol"], x["contrib"], 1e3 * x["wD_mean"], 1e3 * x["wR_mean"], ("%+.1f" % x["rn8_mean_bp"]) if x["rn8_mean_bp"] is not None else "—"))
L.append("\n## T6 · L-C lens: chains, legs, seats (task a)\n| book | K chain | F (V2MAIN) chain | K-king | K-fund | F-f10 | F-fund | inherited (K+F) |\n|---|---|---|---|---|---|---|---|")
for sd in ("42", "2027"):
    lc = S[sd]["LC"]; r_ = lc["R"]; bn = lc["BN"]
    L.append("| R s%s | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |" % (sd, lc["R_chain"]["K"], lc["R_chain"]["F"], r_["K-king"][0], r_["K-fund"][0], r_["F-f10"][0], r_["F-fund"][0], r_["K-inherited"][0] + r_["F-inherited"][0]))
    L.append("| B_N s%s (D rules, R scores) | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |" % (sd, lc["BN_chain"]["K"], lc["BN_chain"]["F"], bn["K-king"][0], bn["K-fund"][0], bn["F-f10"][0], bn["F-fund"][0], bn["K-inherited"][0] + bn["F-inherited"][0]))
lc = S["42"]["LC"]
L.append("| D (archived) | %s | %s | not measurable | not measurable | not measurable | not measurable | — |" % (ci(lc["D"]["K_chain"]), ci(lc["D"]["F_chain"])))
L.append("\nSeats (mean over A_T5): replay w3 = [%.3f, %.3f, %.3f]; deployed w3m = [%.3f, %.3f, %.3f]. Fund-leg share of the replay's carry %.1f%%. The B_N leg split keeps banded positions on their inherited attribution (T1 leg convention), so its \"inherited\" column is a bookkeeping convention, not a staleness measure.\n" % (tuple(lc["seats"]["w3_R_mean"]) + tuple(lc["seats"]["w3m_D_mean"]) + (100 * lc["fund_leg_share_of_carry"]["R"],)))
L.append("## T7 · names behind each large component (per-name Shapley, s42, bps/anchor; weights ×1e3)\n")
for k in ("T", "H", "P", "M", "V", "B"):
    L.append("**%s** (component mean %+.3f):\n\n| name | φ | w_D | w_R | rn8 bp | live |\n|---|---|---|---|---|---|" % (GNAME[k], S["42"]["shapley"]["mean"]["phi_" + k][0]))
    rows = S["42"]["names_per_group"][k]["top_pos"][:10] if S["42"]["shapley"]["mean"]["phi_" + k][0] >= 0 else S["42"]["names_per_group"][k]["top_neg"][:10]
    for x in rows:
        L.append("| %s | %+.4f | %+.2f | %+.2f | %s | %s |" % (x["symbol"], x["phi"], 1e3 * x["wD_mean"], 1e3 * x["wR_mean"], ("%+.1f" % x["rn8_mean_bp"]) if x["rn8_mean_bp"] is not None else "—", x["live"]))
    L.append("")
tc = BR["TC2"]
L.append("## T8 · TC2: August deep-negative short cohort vs early-September short-side price losses (deployed book, D2 on x0910 y4)\n")
L.append("E2a = %d anchors (08-31 00Z..09-10 00Z), 09-06 = %d anchors, C_Aug = %d names. **M1 = %.3f**, M2 (09-06) = %.3f, M3 = %.3f ⇒ **%s** (threshold 0.2; M1 is within 0.011 of it). Short-side price over E2a: all names %+.2f bps/anchor; C_Aug names %+.2f bps/anchor.\n" % (tc["n_E2a"], tc["n_0906"], tc["n_C_Aug"], tc["M1"], tc["M2"], tc["M3"], tc["reading"], tc["total_short_price_E2a_per_anchor"], tc["C_Aug_short_price_E2a_per_anchor"]))
L.append("| top short loser (E2a) | Σ short price bps | 09-06 | in C_Aug | Aug carry Σ | anchors short | short ∧ rn8 ≤ −10bp |\n|---|---|---|---|---|---|---|")
for x in tc["top15_short_losers"]:
    L.append("| %s | %+.2f | %+.2f | %s | %.2f | %d | %d |" % (x["symbol"], x["L_short_E2a_bps_sum"], x["L_short_0906"], x["in_C_Aug"], x["aug_carry_bps_sum"], x["E2a_anchors_short"], x["E2a_anchors_short_rn8_le_m10"]))
L.append("\n| C_Aug name (by Aug carry) | Aug carry Σ bps | E2a short price Σ bps |\n|---|---|---|")
for x in tc["C_Aug_names_by_aug_carry"][:12]:
    L.append("| %s | %.2f | %+.2f |" % (x["symbol"], x["aug_carry_bps_sum"], x["L_short_E2a"]))
L.append("\n## T9 · diagnostics\n| item | s42 | s2027 |\n|---|---|---|")
L.append("| REM split: flow at A (C_D − v(N′)) | %s | %s |" % (ci(S["42"]["Nprime"]["flow_at_A"], 4), ci(S["2027"]["Nprime"]["flow_at_A"], 4)))
L.append("| REM split: carried state (v(N′) − v(G)) | %s | %s |" % (ci(S["42"]["Nprime"]["carried_state"], 4), ci(S["2027"]["Nprime"]["carried_state"], 4)))
L.append("| B_N vs D: unit-gross L1 distance / weight correlation | %.4f / %.4f | %.4f / %.4f |" % (S["42"]["BN_vs_D"]["L1_mean"], S["42"]["BN_vs_D"]["corr_mean"], S["2027"]["BN_vs_D"]["L1_mean"], S["2027"]["BN_vs_D"]["corr_mean"]))
L.append("| replay FTRIM kills per anchor (king chain / V2MAIN chain); members; sel | %.1f / %.1f; %.0f; %.0f | %.1f / %.1f; %.0f; %.0f |" % (S["42"]["R_ftrim"]["mean_killed_king_chain"], S["42"]["R_ftrim"]["mean_killed_f10_chain"], S["42"]["R_ftrim"]["mean_nmem"], S["42"]["R_ftrim"]["mean_nsel"], S["2027"]["R_ftrim"]["mean_killed_king_chain"], S["2027"]["R_ftrim"]["mean_killed_f10_chain"], S["2027"]["R_ftrim"]["mean_nmem"], S["2027"]["R_ftrim"]["mean_nsel"]))
L.append("\n## T10 · ADDENDUM 1 (post-hoc proxy for e): replay king model, column 80 v0 → v1 (T4 K0 → K1)\n| seed | φ_K1 mean | share of Δ | at R node | at N node | node range | K0–K1 member rank corr (mean / min) | reading |\n|---|---|---|---|---|---|---|---|")
for sd, o in AD["result"].items():
    ga = AD["gate_A1"]["per_seed"][sd]
    L.append("| %s | %s | %s | %+.5f | %+.5f | [%+.4f, %+.4f] | %.4f / %.4f | %s |" % (sd, ci(o["phi_K1"]["mean"], 5), pct(o["phi_K1"]["share"]), o["dK1_at_R"]["mean"][0], o["dK1_at_N"]["mean"][0], o["dK1_node_range"][0], o["dK1_node_range"][1], ga["king_rank_corr_K0_K1_mean"], ga["king_rank_corr_K0_K1_min"], o["reading"]))
L.append("\nGate A1: K0 rows == device SLOW rows %s; K0 nodes == main run %s. Not the served booster 29ffaf58.\n" % (AD["gate_A1"]["PASS"], all(o["gate_K0_nodes_equal_main_run"] for o in AD["result"].values())))
L.append("## T11 · devices and inputs\n| item | sha256 |\n|---|---|")
L.append("| t5_bridge.py (self) | `%s` |" % BR["self_sha256"]); L.append("| t5_drive.py (self) | `%s` |" % DR["self_sha256"]); L.append("| w10_sleeve_t5.py (derived) | `%s` |" % DR["derived_device_sha256"])
L.append("| t5_live_ingredients.py (self) | `%s` |" % LI["self_sha256"]); L.append("| t5_addendum_h2b.py (self) | `%s` |" % AD["self_sha256"])
for p, h in BR["inputs"].items(): L.append("| %s | `%s` |" % (p, h))
L.append("| arms C0_s42_t5 / C0_s2027_t5 (pod2) | `%s` / `%s` |" % (DR["runs"]["C0_s42"]["out_sha256"], DR["runs"]["C0_s2027"]["out_sha256"]))
open(T5 + "/receipts/TABLES_T5.md", "w").write("\n".join(L) + "\n")
print("wrote TABLES_T5.md", len(L), "lines")
