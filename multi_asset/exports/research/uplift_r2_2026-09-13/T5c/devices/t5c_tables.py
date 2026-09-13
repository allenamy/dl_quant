#!/usr/bin/env python3
"""t5c_tables.py — Mac. Renders receipts/TABLES_T5c.md from the T5c receipts only (no recomputation). PREREG_T5c §9 step 5."""
import os, sys, json, hashlib, time
T = os.path.abspath(sys.argv[1])
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md") == "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"
BR = json.load(open(T + "/receipts/pod2/RECEIPT_T5c_bridge.json")); DR = json.load(open(T + "/receipts/pod2/RECEIPT_T5c_drive.json"))
KE = json.load(open(T + "/receipts/pod2/RECEIPT_T5c_king_extend.json")); LI = json.load(open(T + "/receipts/RECEIPT_T5c_live_ingredients.json"))
RES = BR["result"]; S = RES["seeds"]; G = RES["groups"]; ORD = RES["order"]
ci = lambda x, d=2: "%+.*f [%+.*f, %+.*f]" % (d, x[0], d, x[1], d, x[2])
pct = lambda x: "%+.0f%% [%+.0f, %+.0f]" % (100 * x[0], 100 * x[1], 100 * x[2])
QN = dict(P="price", C="carry", K="cost", N="net")
GN = dict(T="T FTRIM (D: none before 09-02 12Z, ledger rule after)", W="W seat (D: archived w3m, seeded from 09-05 16Z)", B="B fund rank base (D: members before 09-04 04Z, M1 base after)",
          V="V fund values / freshness", M="M member set", X="X exit rule", S="S eligibility", P="P replay per-name stop layer", H="H state path (D: 08-30 04Z warm start)", REM="REM king-score differences + unreconciled")
L = ["# TABLES · T5c (rendered by `devices/t5c_tables.py` from receipts; do not edit by hand)\n",
     "King chain only (V2MAIN arm NOT MEASURED). Window %s .. %s, %d anchors, %d UTC-day blocks — **CIs are descriptive**. Units bps / 4h anchor / unit gross of the book. D_K = deployed king chain (state_H_kc); R_K = A0 replay king chain (KA lineage). Target layer only. Rendered %s.\n"
     % (RES["window"][0], RES["window"][1], RES["n_window"], RES["n_days"], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]
g = BR["gates"]; gx = DR["gate_G_X"]["per_seed"]
L.append("## T0 · gates\n| gate | result |\n|---|---|")
L.append("| G-UM (carry-forward mask) | %s; prefix %d rows bitwise, %d rows added = last row |" % (DR["gate_G_UM"]["PASS"], DR["gate_G_UM"]["prefix_rows"], DR["gate_G_UM"]["added_rows"]))
L.append("| G-X (KA runs vs T1 C0 arms, anchors <= 08-30 20Z) | %s; %d arrays bitwise per seed, %d rows |" % (DR["gate_G_X"]["PASS"], gx["C0_s42"]["n_arrays_compared"], gx["C0_s42"]["d30_n2_c42_rows"]["n_a"]))
gk = KE["gate_G_KC"]
L.append("| G-KC (8d79186b on v4 x0910 features vs A0 king, 2026 overlap; not blocking) | bitwise %.1f%% of %d cells; member Spearman median %.4f, min %.4f; by month median Jan–Jul 1.0000, **Aug %.4f** ⇒ label: feature-lineage switch |" % (100 * gk["bitwise_equal_share"], gk["cells_both_finite"], gk["spearman_median"], gk["spearman_min"], gk["spearman_median_by_month"]["2026-08"]))
L.append("| KA array | prefix copy bitwise %s; extension %d anchors × %d–%d names; sha `%s…` |" % (KE["prefix_copy"]["bitwise"], KE["extension"]["anchors"], KE["extension"]["finite_per_anchor_min"], KE["extension"]["finite_per_anchor_max"], KE["out_sha256"][:12]))
L.append("| G-RAW (device y4 == x0910 meta == dlw RAW y4s) | %s |" % g["G_RAW"]["PASS"])
L.append("| G-SIM-R (king chain + legs vs device, 66 anchors, KA and KB, both seeds) | %s; max|Δ| %s |" % (g["G_SIM_R"]["PASS"], ", ".join("%s %.1e/%.1e" % (k, v["max_abs_sm"], v["max_abs_legs"]) for k, v in g["G_SIM_R"]["per_run"].items())))
t1 = g["G_T1c"]
L.append("| G-T1c (deployed book vs T1 D2; T5 §6.2 short price) | %s; %d anchors, max|Δ| price %.1e, carry %.1e; short price %.10f vs %.10f |" % (t1["PASS"], t1["n"], t1["max_abs_price"], t1["max_abs_carry"], t1["T5_short_price_per_anchor"], t1["T5_value"]))
L.append("| G-CLOSE (Shapley and fixed order, P/C/K/N, per anchor) | %s; max %.1e |" % (g["G_CLOSE"]["PASS"], max(max(v2.values()) for v in g["G_CLOSE"]["per_seed"].values() for v2 in v.values())))
L.append("| G-ARCH-D (target_live = 0.55·kc + 0.45·fc, 66 anchors) | %s; max|Δ| %.1e |" % (LI["G_ARCH_D"]["PASS"], LI["G_ARCH_D"]["max_abs"]))
L.append("| G-ING-S (sel count = producer log; archived nonzero ⊆ pm∩sel∩LIVE) | %s; violations %d; count mismatches %d |" % (LI["G_ING_S"]["PASS"], LI["G_ING_S"]["total_violations"], len(LI["G_ING_S"]["count_mismatch"])))
L.append("| G-ING-V (backward EMA 09-13 → 09-04 00Z reproduces stored fund z) | %s; max|Δz| %.1e |" % (LI["G_ING_V"]["PASS"], LI["G_ING_V"]["max_abs_dz"]))
gb = LI["G_ING_B"]
L.append("| G-ING-B (M1 base) | **%s** — (i) 09-13 04Z M1 fund z max|Δ| %.1e, old z %.1e, fund_base_n %d = %d; (ii) per-anchor fund_base_n mismatches at %s: %s |" % (gb["PASS"], gb["i_max_abs_dz_M1"], gb["i_max_abs_dz_old"], gb["i_fund_base_n"], gb["i_logged"], ", ".join(gb["ii_mismatch"]), "; ".join("%s recon %d vs logged %d" % (a, gb["ii"][a]["recon"], gb["ii"][a]["logged"]) for a in gb["ii_mismatch"])))
L.append("| G-ING-T (FTRIM-recorded rn8 vs ledger reconstruction) | %s; %d names checked, max|Δ| %.1e, missing %d |" % (LI["G_ING_T"]["PASS"], LI["G_ING_T"]["n_checked"], LI["G_ING_T"]["max_abs"], LI["G_ING_T"]["n_missing"]))
L.append("| G-POD | GPU %s → %s; PIDs %s → %s |\n" % (BR["gpu_before"], BR["gpu_after"], BR["pids_before"].replace("\n", "; "), BR["pids_after"].replace("\n", "; ")))
L.append("## T1 · readings (PREREG §6; label needs both seeds)\n| lineage · seed | outcome | D_K mean | R_K mean | D_K − R_K | SAME-LOSS | GAP | label | label excl. 09-06 |\n|---|---|---|---|---|---|---|---|---|")
for tag in ("KA_s42", "KA_s2027"):
    for q in ("P", "C", "K", "N"):
        rd = S[tag]["readings"][q]; rx = S[tag]["readings_excl_0906"][q]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (tag, QN[q], ci(rd["D_K"]), ci(rd["R_K"]), ci(rd["diff_D_minus_R"]), rd["SAME_LOSS"], rd["DEPLOYMENT_GAP"], rd["label"], rx["label"]))
for tag, o in RES["KB"].items():
    for q in ("P", "C", "N"):
        rd = o["readings"][q]
        L.append("| %s (sensitivity) | %s | %s | %s | %s | %s | %s | %s | %s |" % (tag, QN[q], ci(rd["D_K"]), ci(rd["R_K"]), ci(rd["diff_D_minus_R"]), rd["SAME_LOSS"], rd["DEPLOYMENT_GAP"], rd["label"], o["readings_excl_0906"][q]["label"]))
L.append("\n## T2 · levels (descriptive; same for both seeds except R_K)\n| book | price | carry | cost | net |\n|---|---|---|---|---|")
lv = S["KA_s42"]["levels"]
for nm in ("D_K", "R_K", "D_B", "D_F"):
    L.append("| %s | %s | %s | %s | %s |" % (nm + (" (KA s42)" if nm == "R_K" else ""), ci(lv[nm]["P"]), ci(lv[nm]["C"]), ci(lv[nm]["K"], 3), ci(lv[nm]["N"])))
lv2 = S["KA_s2027"]["levels"]["R_K"]
L.append("| R_K (KA s2027) | %s | %s | %s | %s |" % (ci(lv2["P"]), ci(lv2["C"]), ci(lv2["K"], 3), ci(lv2["N"])))
dd = S["KA_s42"]["D_B_vs_D_K_price"]
L.append("\nDeployed book vs deployed king chain, price per anchor: correlation %.4f; mean(D_B − D_K) %s.\n" % (dd["corr"], ci(dd["mean_diff"])))
for q in ("P", "C", "N"):
    L.append("## T3%s · %s gap decomposition (Shapley primary; bps/anchor means with CI; shares shown but unstable when the gap CI contains 0)\n" % ({"P": "a", "C": "b", "N": "c"}[q], QN[q]))
    L.append("| component | s42 mean | s42 share | s2027 mean | s2027 share | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |\n|---|---|---|---|---|---|---|---|")
    a = S["KA_s42"]["bridge"][q]; b = S["KA_s2027"]["bridge"][q]
    for c in ["phi_" + x for x in G] + ["REM"]:
        k = c.replace("phi_", "")
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (GN[k], ci(a["mean"][c]), pct(a["share"][c]), ci(b["mean"][c]), pct(b["share"][c]), ("%+.2f / %+.2f" % (a["sequential"][k], b["sequential"][k])) if k in ORD else "—",
                                                     ("%+.2f" % a["one_at_a_time"][k]) if k in G else "—", ("%+.2f" % a["leave_one_out"][k]) if k in G else "—"))
    L.append("| **total D_K − R_K** | %s | | %s | | excl. 09-06: %s / %s | | |" % (ci(a["delta"]), ci(b["delta"]), ci(a["excl_0906"]["delta"]), ci(b["excl_0906"]["delta"])))
    per = a["periods"]
    L.append("\nPeriod means (s42): φ_T before/after 09-02 12Z %+.2f / %+.2f; φ_B before/after 09-04 04Z %+.2f / %+.2f; φ_W before/after 09-05 16Z %+.2f / %+.2f; REM before/after 09-01 08Z %+.2f / %+.2f.\n"
             % (per["T"]["before"], per["T"]["after"], per["B"]["before"], per["B"]["after"], per["W"]["before"], per["W"]["after"], per["REM"]["before"], per["REM"]["after"]))
p42 = S["KA_s42"]["bridge"]["P"]; p27 = S["KA_s2027"]["bridge"]["P"]
L.append("## T4 · side lens, price by own-sign side\n| book | long | short | gross share short |\n|---|---|---|---|")
for nm in ("D_K", "R_K"):
    L.append("| %s (s42) | %s | %s | %.3f |" % (nm, ci(p42["side_lens"][nm]["long"]), ci(p42["side_lens"][nm]["short"]), p42["side_lens"][nm]["gross_short"]))
L.append("| R_K (s2027) | %s | %s | %.3f |" % (ci(p27["side_lens"]["R_K"]["long"]), ci(p27["side_lens"]["R_K"]["short"]), p27["side_lens"]["R_K"]["gross_short"]))
L.append("| D_K − R_K (s42 / s2027) | %s / %s | %s / %s | |\n" % (ci(p42["side_lens"]["diff_long"]), ci(p27["side_lens"]["diff_long"]), ci(p42["side_lens"]["diff_short"]), ci(p27["side_lens"]["diff_short"])))
L.append("## T5 · the deployed king chain's largest short-side price losses and the replay's same names (s42; Σ over window, bps; weights ×1e3)\n| name | D_K short Σ | R_K short Σ | w_D mean | w_R mean | rn8 mean bp |\n|---|---|---|---|---|---|")
for x in p42["short_losers_D_K"]:
    L.append("| %s | %+.1f | %+.1f | %+.2f | %+.2f | %s |" % (x["symbol"], x["D_short_sum"], x["R_short_sum"], 1e3 * x["wD"], 1e3 * x["wR"], ("%+.1f" % x["rn8_bp"]) if x["rn8_bp"] is not None else "—"))
L.append("\n## T6 · names where the deployed king chain did worse than the replay (s42; mean bps/anchor of the per-name price gap; weights ×1e3)\n| name | gap | w_D | w_R |\n|---|---|---|---|")
for x in p42["names_total_gap"][:12]:
    L.append("| %s | %+.3f | %+.2f | %+.2f |" % (x["symbol"], x["gap"], 1e3 * x["wD"], 1e3 * x["wR"]))
L.append("\n**Per-name Shapley of the price gap (s42), most negative / most positive five:**\n")
for k in ("T", "P", "M", "V", "W", "H"):
    n = p42["names"][k]
    L.append("- %s: − %s · + %s" % (GN[k], ", ".join("%s %+.2f" % (x["symbol"], x["phi"]) for x in n["top_neg"][:5]), ", ".join("%s %+.2f" % (x["symbol"], x["phi"]) for x in n["top_pos"][:5])))
L.append("\n## T7 · replay diagnostics\n| item | s42 | s2027 |\n|---|---|---|")
L.append("| replay FTRIM kills per anchor (king chain) | %.1f | %.1f |" % (p42["R_ftrim_kills_mean"], p27["R_ftrim_kills_mean"]))
L.append("| replay eligible names per anchor | %.0f | %.0f |" % (p42["R_nsel_mean"], p27["R_nsel_mean"]))
L.append("| replay stop layer: names blocked per anchor / new fires in window | %.1f / %d | %.1f / %d |" % (p42["R_stop_blocks"]["names_blocked_mean"], p42["R_stop_blocks"]["new_fires_in_window"], p27["R_stop_blocks"]["names_blocked_mean"], p27["R_stop_blocks"]["new_fires_in_window"]))
L.append("| node skips | %d | %d |" % (S["KA_s42"]["node_skips"], S["KA_s2027"]["node_skips"]))
L.append("\n## T8 · devices and inputs\n| item | sha256 |\n|---|---|")
L.append("| t5c_bridge.py | `%s` |" % BR["self_sha256"]); L.append("| t5c_drive.py | `%s` |" % DR["self_sha256"]); L.append("| w10_sleeve_t5c.py (derived) | `%s` |" % DR["derived_device_sha256"])
L.append("| t5c_king_extend.py | `%s` |" % KE["self_sha256"]); L.append("| t5c_live_ingredients.py | `%s` |" % LI["self_sha256"])
for p, h in BR["inputs"].items(): L.append("| %s | `%s` |" % (p, h))
for tag, r in DR["runs"].items(): L.append("| arm %s (pod2 only) | `%s` |" % (tag, r["out_sha256"]))
L.append("| carry-forward mask (pod2) | `%s` |" % DR["gate_G_UM"]["out_sha256"])
open(T + "/receipts/TABLES_T5c.md", "w").write("\n".join(L) + "\n"); print("wrote TABLES_T5c.md", len(L), "lines")
