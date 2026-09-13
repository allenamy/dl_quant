#!/usr/bin/env python3
"""t5d_tables.py — Mac. Renders receipts/TABLES_T5d.md from the T5d receipts only (no recomputation). PREREG_T5d §9 step 5.
Part P (post-hoc) is rendered from RECEIPT_T5d_posthoc.json and is labelled as post-hoc description.
Launch: /usr/bin/python3 devices/t5d_tables.py "$PWD"
"""
import os, sys, json, hashlib, time
T = os.path.abspath(sys.argv[1]); sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
J = lambda p: json.load(open(T + "/" + p))
SC = J("receipts/RECEIPT_T5d_prefreeze_scan.json"); IS = J("receipts/RECEIPT_T5d_interval_sources.json"); PN = J("receipts/pod2/RECEIPT_T5d_ivfix_panel.json"); DR = J("receipts/pod2/RECEIPT_T5d_drive.json")
BR = J("receipts/pod2/RECEIPT_T5d_bridge.json"); RD = J("receipts/RECEIPT_T5d_bridge_run2_diff.json"); PH = J("receipts/pod2/RECEIPT_T5d_posthoc.json")
PS = J("receipts/pod2/RECEIPT_T5d_posthoc_seed.json"); PF = J("receipts/pod2/RECEIPT_T5d_posthoc_fallback.json"); PD = J("receipts/RECEIPT_T5d_posthoc_dk_carry.json")
import csv, gzip
LISTP = "/Users/haosiyu/cc_tmp/t5d_2026-09-13/iv_sources_per_settlement.csv.gz"; assert sha(LISTP) == PH["A"]["per_settlement_list_sha256"]
LROWS = list(csv.DictReader(gzip.open(LISTP, "rt", newline=""))); BYS = {}
for r_ in LROWS: BYS.setdefault(r_["symbol"], []).append(r_)
def secs_since_prev(sym, ts):
    L_ = BYS[sym]; i_ = [q for q, r_ in enumerate(L_) if r_["source"] == "fallback_x0910" and r_["settlement_utc"] == ts][0]
    return int(L_[i_]["settlement_ts"]) - int(L_[i_ - 1]["settlement_ts"]) if i_ > 0 else None
T5CB = json.load(open(os.path.dirname(T) + "/T5c/receipts/pod2/RECEIPT_T5c_bridge.json"))
assert RD["PASS"] and RD["run2"]["sha256"] == sha(T + "/receipts/pod2/RECEIPT_T5d_bridge.json")
assert PH["inputs"]["/workspace/uplift_r2_2026-09-13/T5d/receipts/T5d_bridge_components.npz"] == BR["components_npz_sha256"]
ci = lambda x, d=2: "%+.*f [%+.*f, %+.*f]" % (d, x[0], d, x[1], d, x[2])
pct = lambda x: "%+.0f%% [%+.0f, %+.0f]" % (100 * x[0], 100 * x[1], 100 * x[2])
QN = dict(P="price", C="carry", K="cost", N="net"); TAGS = ("KA_s42", "KA_s2027"); KB = ("KB_s42", "KB_s2027")
GN = dict(T="T FTRIM (D: none before 09-02 12Z, ledger rule after)", W="W seat (D: archived w3m, seeded from 09-05 16Z)", B="B fund rank base (D: members before 09-04 04Z, M1 base after)",
          V="V fund values / freshness", M="M member set", X="X exit rule", S="S eligibility", P="P replay per-name stop layer", H="H state path (D: 08-30 04Z warm start)", REM="REM king-score differences + unreconciled")
g = BR["gates"]
L = ["# TABLES · T5d (rendered by `devices/t5d_tables.py` from receipts; do not edit by hand)\n",
     "King chain only (V2MAIN arm NOT MEASURED). Window %s .. %s, 61 anchors, 11 UTC-day blocks — **CIs are descriptive**. Units bps / 4h anchor / unit gross. D_K = deployed king chain; R_K = A0 replay king chain. Target layer only. "
     "Calibers: **T5C** = T5c weights priced with x0910 intervals (reproduces T5c); **FIX** = the same weights priced with corrected intervals; **REG** = regenerated replay (corrected panel: FTRIM, fund EMA, state and W regenerated) priced with corrected intervals. "
     "D_K is archived, so its FIX and REG values are the same. Equivalence band δ = %.2f. Rendered %s.\n" % (BR["window"][0], BR["window"][1], BR["delta_equivalence_bps"], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]
# ---------------------------------------------------------------- T0 gates
L.append("## T0 · gates\n| gate | blocking | result |\n|---|---|---|")
envs = {"interval_sources (Mac)": IS["env"]["whitelist"], "ivfix_panel": PN["env"]["whitelist"], "bridge": BR["env"]["whitelist"], "posthoc": PH["env"]["whitelist"]}
L.append("| G-FREEZE / G-ENV | yes | every device asserts prereg sha `a1ef16cd…`; env whitelists: %s; drive children env per run recorded (`RECEIPT_T5d_drive.json`) |" % "; ".join("%s %s" % (k, ",".join(v)) for k, v in envs.items()))
pods = (("ivfix_panel", PN), ("drive", DR), ("bridge", BR), ("posthoc", PH), ("posthoc_seed", PS), ("posthoc_fallback", PF))
L.append("| G-POD | yes | all pod2 devices under `nice -n 10`, bridge Pool(16), others one process; GPU before → after: %s; PIDs 333197/339489 unchanged in every receipt: %s |" % ("; ".join("%s %s → %s" % (n, r["gpu_before"], r["gpu_after"]) for n, r in pods), all(r["pids_before"] == r["pids_after"] and "333197" in r["pids_before"] and "339489" in r["pids_before"] for _, r in pods)))
r6 = PN["gate_G_R6"]
L.append("| G-R6 (r6 algebra with r6's own intervals reproduces x0910 tail cells) | yes | %s; %d symbols with events, %d seeded; mismatches %s |" % (r6["PASS"], r6["symbols_with_rows"], r6["symbols_seeded"], ", ".join("%s %d" % (k, v) for k, v in r6["n_mismatch"].items())))
il = PN["gate_G_IV_LEDGER"]
L.append("| G-IV-LEDGER (ledger iv vs snapped timestamp gap, same settlement) | no | %d tail settlements: ledger %d, gap %d; ledger ≠ gap **%d**; settlements whose interval changed %d, names %d |" % (il["tail_events"], il["ledger_source"], il["gap_source"], il["n_ledger_vs_gap_mismatch"], il["changed_events"], len(il["changed_symbols"])))
ie = PN["gate_G_IV_EXEC"]
L.append("| G-IV-EXEC (iv_true vs executor funding_interval_h) | no | %d settlements checked, **%d** mismatches (names %s); classification in P1 |" % (ie["checked"], ie["n_mismatch"], ", ".join(sorted({m[0].replace("USDT", "") for m in ie["mismatch"]}))))
gs = PN["gate_G_SCOPE"]
L.append("| G-SCOPE (only tail f_fund_iv / v1 / v2 differ) | yes | %s; %s; f_fund_now and f_fund_ema unchanged |" % (gs["PASS"], "; ".join("%s %d cells, %d names, pre-cut %d" % (k, v["cells"], len(v["names"]), v["prefix_cells"]) for k, v in gs["per_key"].items())))
gu = DR["gate_G_UM_KA"]
L.append("| G-UM / G-KA (mask, KA/KB kings and T5c arms = T5c receipts) | yes | %s |" % all(gu.values()))
gx = DR["gate_G_Xprime"]["per_run"]
L.append("| G-X′ (T5d arms = T5c arms on anchors ≤ 08-31 00Z) | yes | %s; %d arrays per run bitwise; arrays that change after the cut: %s |" % (DR["gate_G_Xprime"]["PASS"], gx["KA_s42"]["n_arrays"], ", ".join(gx["KA_s42"]["arrays_that_change_after_cut"])))
L.append("| G-PRED (synthetic label controls a–d, before real data) | yes | %s; a %s · b %s · c %s · d %s |" % (g["G_PRED"]["PASS"], g["G_PRED"]["a"], g["G_PRED"]["b"], g["G_PRED"]["c"], g["G_PRED"]["d"]))
L.append("| G-RAW | yes | %s |" % g["G_RAW"]["PASS"])
L.append("| G-SIM-R (simulator = regenerated arms, king chain and legs) | yes | %s; %s |" % (g["G_SIM_R"]["PASS"], ", ".join("%s %.1e/%.1e" % (k, v["max_abs_sm"], v["max_abs_legs"]) for k, v in g["G_SIM_R"]["per_run"].items())))
L.append("| G-T1c (x0910 caliber reproduces T1 D2 and T5 §6.2) | yes | %s; n %d, max|Δ| price %.1e, carry %.1e; short price %.10f |" % (g["G_T1c"]["PASS"], g["G_T1c"]["n"], g["G_T1c"]["max_abs_price"], g["G_T1c"]["max_abs_carry"], g["G_T1c"]["T5_short_price_per_anchor"]))
L.append("| G-ARCH-D | yes | %s; max|Δ| %.1e |" % (g["G_ARCH_D"]["PASS"], g["G_ARCH_D"]["max_abs"]))
L.append("| G-FIXW (fixed weights: price and cost bitwise unchanged; T5c caliber recomputed bitwise) | yes | %s |" % g["G_FIXW"]["PASS"])
L.append("| G-T5C (T5c readings reproduced from the T5c arms) | yes | %s; max|Δ| %.1e |" % (g["G_T5C"]["PASS"], g["G_T5C"]["max_abs"]))
L.append("| G-CLOSE (Shapley and fixed order close per anchor, REG) | yes | %s; max %.1e |" % (g["G_CLOSE"]["PASS"], g["G_CLOSE"]["max_abs"]))
L.append("| bridge run 2 vs run 1 (descriptive fields added only) | — | %s; run-1 fields changed: %s; fields added %d; components npz identical %s |\n" % (RD["PASS"], ", ".join(d[0] for d in RD["run1_fields_changed"]), len(RD["fields_added"]), RD["components_npz_equal"]))
# ---------------------------------------------------------------- T1 interval correction
L.append("## T1 · interval correction\n| item | value |\n|---|---|")
L.append("| pre-freeze scan (08-30 04Z..09-10 00Z, timestamp gap) | incumbent %d cells, %d mismatches; tail %d cells, **%d** mismatches, %d names |" % (SC["cells_checked"]["incumbent"], SC["iv_mismatch_cells"]["incumbent"], SC["cells_checked"]["tail"], SC["iv_mismatch_cells"]["tail"], SC["n_names"]))
L.append("| producer ledger (two aux snapshots) | %d symbols, %d settlements from 2026-08-28 00Z; snapshot conflicts %d |" % (IS["ledger_symbols"], IS["ledger_rows"], IS["ledger_snapshot_conflicts"]))
L.append("| executor funding records 08-30..09-11 | %d symbols, %d settlements; duplicate rows %d; interval conflicts %d |" % (IS["executor_symbols"], IS["executor_rows"], IS["executor_duplicate_rows"], IS["executor_interval_conflicts"]))
L.append("| names with a changed settlement interval | %s |" % ", ".join(x.replace("USDT", "") for x in il["changed_symbols"]))
L.append("| corrected panel | `%s…` (pod2 `T5d/panel/`) |\n" % PN["out_sha256"][:16])
# ---------------------------------------------------------------- T2 deltas
DL = BR["deltas"]
L.append("## T2 · the two deltas (k 89; level CIs here use k 89 and differ slightly from T3/T4)\n")
L.append("Δ_fixed = FIX − T5C (same weights, corrected intervals); Δ_regen = REG − T5C (regenerated replay); weight effect = REG − FIX. Price and cost cannot move under fixed weights (G-FIXW).\n")
L.append("| book · seed | outcome | T5C | FIX | REG | Δ_fixed | Δ_regen | weight effect | Δ_regen excl. 09-06 |\n|---|---|---|---|---|---|---|---|---|")
for t in TAGS + KB:
    for q in ("P", "C", "K", "N"):
        d = DL[t][q]; dd = 3 if q == "K" else 3
        L.append("| R_K %s%s | %s | %s | %s | %s | %s | %s | %s | %s |" % (t, " (sensitivity)" if t in KB else "", QN[q], ci(d["T5c"]), ci(d["FIX"]), ci(d["REG"]), ci(d["delta_fixed"], dd), ci(d["delta_regen"], dd), ci(d["weight_effect"], dd), ci(d["delta_regen_excl_0906"], dd)))
for nm in ("D_K", "D_B"):
    for q in ("P", "C", "K", "N"):
        d = DL[nm][q]
        L.append("| %s (archived; no regeneration) | %s | %s | %s | = FIX | %s | — | — | — |" % (nm, QN[q], ci(d["T5c"]), ci(d["FIX"]), ci(d["delta_fixed"], 3)))
L.append("")
# ---------------------------------------------------------------- T3 readings
RDG = BR["readings"]
L.append("## T3 · readings with the corrected predicate (PREREG_T5d §6.1–§6.2; label needs both seeds)\n")
L.append("| seed · caliber | outcome | D_K mean | R_K mean | D_K − R_K | LOSS_D | LOSS_R | SAME | GAP | label | what the paired CI excludes |\n|---|---|---|---|---|---|---|---|---|---|---|")
for t in TAGS + KB:
    for cal in ("T5C", "FIX", "REG", "REG_excl_0906"):
        for q in ("P", "C", "K", "N"):
            if t in KB and cal in ("FIX",) and q == "K": continue
            r = RDG[t][cal][q]
            L.append("| %s · %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (t, cal, QN[q], ci(r["D_K"]), ci(r["R_K"]), ci(r["diff_D_minus_R"]), r["LOSS_D"] if r["LOSS_D"] is not None else "—", r["LOSS_R"] if r["LOSS_R"] is not None else "—", r["SAME"], r["GAP"], r["label"], r["difference_reading"]))
L.append("\n**Label changes.** T5c receipt label (old predicate) → T5C caliber (new predicate) → FIX → REG, per outcome:\n")
L.append("| seed | outcome | T5c (old) | T5C (new) | FIX | REG | REG excl. 09-06 |\n|---|---|---|---|---|---|---|")
for t in TAGS + KB:
    old = T5CB["result"]["seeds"][t]["readings"] if t in TAGS else T5CB["result"]["KB"][t]["readings"]
    for q in ("P", "C", "K", "N"):
        if q not in old: continue
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (t, QN[q], old[q]["label"], RDG[t]["T5C"][q]["label"], RDG[t]["FIX"][q]["label"], RDG[t]["REG"][q]["label"], RDG[t]["REG_excl_0906"][q]["label"]))
L.append("")
# ---------------------------------------------------------------- T4 levels
LV = BR["levels"]
L.append("## T4 · levels (k 81)\n| book | caliber | price | carry | cost | net |\n|---|---|---|---|---|---|")
for nm in ("D_K", "D_B", "D_F"):
    for cal in ("T5C", "FIX"):
        x = LV[cal][nm]; L.append("| %s | %s | %s | %s | %s | %s |" % (nm, cal if cal == "T5C" else "corrected", ci(x["P"]), ci(x["C"]), ci(x["K"], 3), ci(x["N"])))
for t in TAGS + KB:
    for cal in ("T5C", "FIX", "REG"):
        x = LV["R_K"][t][cal]; L.append("| R_K %s | %s | %s | %s | %s | %s |" % (t, cal, ci(x["P"]), ci(x["C"]), ci(x["K"], 3), ci(x["N"])))
L.append("\nDeployed book vs deployed king chain, price per anchor: correlation %.4f; mean(D_B − D_K) %s.\n" % (BR["D_B_vs_D_K_price"]["corr"], ci(BR["D_B_vs_D_K_price"]["mean_diff"])))
# ---------------------------------------------------------------- T5 FTRIM switches
FW = BR["ftrim_and_weights"]
L.append("## T5 · replay FTRIM trigger switches and weight distance (REG vs T5C, KA)\n")
L.append("| seed | switches (all in window) | mean L1 weight distance in window | largest L1 (anchor) | names with the largest mean |Δw| (×1e3) |\n|---|---|---|---|---|")
for t in TAGS:
    f = FW[t]; L.append("| %s | %d (%d) | %.4f | %s | %s |" % (t, f["n_switch"], f["n_switch_in_window"], f["weight_L1_mean_window"], "; ".join("%s %.4f" % (a, v) for a, v in f["weight_L1_max"][:3]), ", ".join("%s %.2f" % (n.replace("USDT", ""), 1e3 * v) for n, v in f["names_weight_change"][:8])))
L.append("\n| anchor | name | funding rate now | iv x0910 → true | rn8 bp x0910 → true | killed T5C / REG |\n|---|---|---|---|---|---|")
for x in FW["KA_s42"]["switches"]:
    L.append("| %s | %s | %+.6f | %g → %g | %+.1f → %+.1f | %s / %s |" % (x["anchor"], x["symbol"], x["fn"], x["iv_x0910"], x["iv_true"], x["rn8_x0910_bp"], x["rn8_true_bp"], x["killed_T5c"], x["killed_REG"]))
same = [(a["anchor"], a["symbol"], a["killed_REG"]) for a in FW["KA_s42"]["switches"]] == [(a["anchor"], a["symbol"], a["killed_REG"]) for a in FW["KA_s2027"]["switches"]]
L.append("\nSwitch list identical for s2027: %s.\n" % same)
# ---------------------------------------------------------------- T6 bridge
BRG = BR["bridge_REG"]; ORD = ["T", "B", "W", "V", "M", "S", "X", "P", "H"]
for q, lab in (("P", "a"), ("C", "b"), ("N", "c")):
    L.append("## T6%s · %s gap decomposition on REG (Shapley primary; bps/anchor; shares unstable when the gap CI contains 0; T5c value for comparison)\n" % (lab, QN[q]))
    L.append("| component | s42 mean | s42 share | s2027 mean | s2027 share | T5c s42 | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |\n|---|---|---|---|---|---|---|---|---|")
    a = BRG["KA_s42"][q]; b = BRG["KA_s2027"][q]; c5 = T5CB["result"]["seeds"]["KA_s42"]["bridge"][q]
    for c in ["phi_" + x for x in "TWBVMXSPH"] + ["REM"]:
        k = c.replace("phi_", "")
        L.append("| %s | %s | %s | %s | %s | %+.2f | %s | %s | %s |" % (GN[k], ci(a["mean"][c]), pct(a["share"][c]), ci(b["mean"][c]), pct(b["share"][c]), c5["mean"][c][0], ("%+.2f / %+.2f" % (a["sequential"][k], b["sequential"][k])) if k in ORD else "—",
                                                   ("%+.2f" % a["one_at_a_time"][k]) if k in ORD else "—", ("%+.2f" % a["leave_one_out"][k]) if k in ORD else "—"))
    L.append("| **total D_K − R_K** | %s | | %s | | %+.2f | excl. 09-06: %s / %s | | |" % (ci(a["delta"]), ci(b["delta"]), c5["delta"][0], ci(a["excl_0906_delta"]), ci(b["excl_0906_delta"])))
    per = a["periods"]
    L.append("\nREM reading (model difference): s42 %s; s2027 %s. Period means (s42): φ_T before/after 09-02 12Z %+.2f / %+.2f; φ_B before/after 09-04 04Z %+.2f / %+.2f; φ_W before/after 09-05 16Z %+.2f / %+.2f; REM before/after 09-01 08Z %+.2f / %+.2f. Closure max %.1e / fixed order %.1e.\n"
             % (a["REM_model_difference_reading"], b["REM_model_difference_reading"], per["T"]["before"], per["T"]["after"], per["B"]["before"], per["B"]["after"], per["W"]["before"], per["W"]["after"], per["REM"]["before"], per["REM"]["after"], a["closure_maxabs"], a["closure_seq_maxabs"]))
k42 = BRG["KA_s42"]["K"]; k27 = BRG["KA_s2027"]["K"]
L.append("Cost gap on REG: s42 %s (REM %s), s2027 %s.\n" % (ci(k42["delta"], 3), ci(k42["mean"]["REM"], 3), ci(k27["delta"], 3)))
# ---------------------------------------------------------------- T7 side lens and names
p42 = BRG["KA_s42"]["P"]; p27 = BRG["KA_s2027"]["P"]
L.append("## T7 · side lens, price by own-sign side (REG)\n| book | long | short | gross share short |\n|---|---|---|---|")
L.append("| D_K | %s | %s | %.3f |" % (ci(p42["side_lens"]["D_K"]["long"]), ci(p42["side_lens"]["D_K"]["short"]), p42["side_gross_short"]["D_K"]))
L.append("| R_K (s42) | %s | %s | %.3f |" % (ci(p42["side_lens"]["R_K"]["long"]), ci(p42["side_lens"]["R_K"]["short"]), p42["side_gross_short"]["R_K"]))
L.append("| R_K (s2027) | %s | %s | %.3f |" % (ci(p27["side_lens"]["R_K"]["long"]), ci(p27["side_lens"]["R_K"]["short"]), p27["side_gross_short"]["R_K"]))
L.append("| D_K − R_K (s42 / s2027) | %s / %s | %s / %s | |\n" % (ci(p42["side_lens"]["diff_long"]), ci(p27["side_lens"]["diff_long"]), ci(p42["side_lens"]["diff_short"]), ci(p27["side_lens"]["diff_short"])))
L.append("## T8 · the deployed king chain's largest short-side price losses and the regenerated replay's same names (s42; Σ over window, bps; weights ×1e3; rn8 from the corrected panel)\n| name | D_K short Σ | R_K short Σ | w_D mean | w_R mean | rn8 mean bp |\n|---|---|---|---|---|---|")
for x in p42["short_losers_D_K_15"]:
    L.append("| %s | %+.1f | %+.1f | %+.2f | %+.2f | %s |" % (x["symbol"], x["D_short_sum"], x["R_short_sum"], 1e3 * x["wD"], 1e3 * x["wR"], ("%+.1f" % x["rn8_bp"]) if x["rn8_bp"] is not None else "—"))
L.append("\n## T9 · names where the deployed king chain did worse than the regenerated replay (s42; mean bps/anchor of the per-name price gap; weights ×1e3)\n| name | gap | w_D | w_R |\n|---|---|---|---|")
for x in p42["names_total_gap"][:12]:
    L.append("| %s | %+.3f | %+.2f | %+.2f |" % (x["symbol"], x["gap"], 1e3 * x["wD"], 1e3 * x["wR"]))
L.append("\n**Per-name Shapley of the price gap (s42, REG), most negative / most positive five:**\n")
for k in ("T", "P", "M", "V", "W", "H"):
    n = p42["names"][k]
    L.append("- %s: − %s · + %s" % (GN[k], ", ".join("%s %+.2f" % (x["symbol"], x["phi"]) for x in n["top_neg"][:5]), ", ".join("%s %+.2f" % (x["symbol"], x["phi"]) for x in n["top_pos"][:5])))
L.append("\n## T10 · replay diagnostics (REG)\n| item | s42 | s2027 |\n|---|---|---|")
L.append("| replay FTRIM kills per anchor, REG (T5C) | %.2f (%.2f) | %.2f (%.2f) |" % (p42["R_ftrim_kills_mean"], p42["R_ftrim_kills_mean_T5C"], p27["R_ftrim_kills_mean"], p27["R_ftrim_kills_mean_T5C"]))
L.append("| replay eligible names per anchor | %.0f | %.0f |" % (p42["R_nsel_mean"], p27["R_nsel_mean"]))
L.append("| replay stop layer: names blocked per anchor / new fires in window | %.1f / %d | %.1f / %d |" % (p42["R_stop_blocks"]["names_blocked_mean"], p42["R_stop_blocks"]["new_fires_in_window"], p27["R_stop_blocks"]["names_blocked_mean"], p27["R_stop_blocks"]["new_fires_in_window"]))
L.append("| node skips | %d | %d |\n" % (BR["node_skips"]["KA_s42"], BR["node_skips"]["KA_s2027"]))
# ---------------------------------------------------------------- P post-hoc
A = PH["A"]; Bp = PH["B"]; C = PH["C"]; D = PH["D"]
L.append("## P · POST-HOC description (`devices/t5d_posthoc.py`, written after the bridge numbers were seen; not a gate, not a reading)\n")
L.append("### P1 · per-settlement interval sources\n| item | value |\n|---|---|")
L.append("| re-derivation of the corrected tail cells from the per-settlement list = T5d panel | %s (%s) |" % (A["repro"]["PASS"], ", ".join("%s %d" % (k, v) for k, v in A["repro"]["n_mismatch"].items())))
L.append("| tail settlements by source | %s |" % ", ".join("%s %d" % (k, v) for k, v in sorted(A["source_counts"]["tail"].items())))
L.append("| settlements in the 24 h before the cut by source | %s |" % ", ".join("%s %d" % (k, v) for k, v in sorted(A["source_counts"]["pre24"].items())))
L.append("| settlements whose interval changed | %d (list in the receipt; full per-settlement list `%s`, sha `%s…`) |" % (A["n_changed"], os.path.basename(A["per_settlement_list"]), A["per_settlement_list_sha256"][:16]))
L.append("")
if A["fallback_settlements"]:
    L.append("Settlements with neither a ledger record nor a usable gap (interval left at the x0910 value; seconds since the previous record from the per-settlement list):\n\n| name | settlement | iv used | seconds since previous record | hours to next | executor | in force at tail anchors |\n|---|---|---|---|---|---|---|")
    for x in A["fallback_settlements"]:
        L.append("| %s | %s | %g | %s | %s | %s | %s |" % (x["symbol"], x["settlement"], x["iv_used"], secs_since_prev(x["symbol"], x["settlement"]), x["hours_to_next"], x["executor"], ", ".join(x["in_force_at"]) or "none"))
    L.append("")
L.append("Weights on the %d in-force cells of these settlements (`RECEIPT_T5d_posthoc_fallback.json`): cells with any nonzero weight in the deployed king chain, the deployed book or any replay arm (T5C/REG × KA/KB × two seeds): **%d**; max |w| %.1e; name in the replay member set at those cells: %s.\n"
         % (PF["n_cells"], PF["n_cells_with_any_nonzero_weight"], PF["max_abs_weight_any_book"], any(v for c in PF["cells"] for k, v in c.items() if k.startswith("member_"))))
em = [x for x in A["executor_mismatches"] if not x.get("pre_window")]; ep = [x for x in A["executor_mismatches"] if x.get("pre_window")]
L.append("Executor mismatches inside the recomputed range: %d; the executor value equals an interval that iv_true takes within the next 8 h: %d; equals one within the previous 8 h: %d.\n" % (len(em), sum(x["executor_shows_upcoming_interval"] for x in em), sum(x["executor_shows_previous_interval"] for x in em)))
unc = [x for x in em if not x["executor_shows_upcoming_interval"]]
L.append("Not classified (%d): %s — both after the window end, where the event data stop at the 09-11 15:04Z fetch.\n" % (len(unc), "; ".join("%s %s" % (x["symbol"], x["settlement"]) for x in unc)))
L.append("| name | settlement | iv_true (source, gap) | executor | iv_true within next 8 h |\n|---|---|---|---|---|")
for x in em:
    L.append("| %s | %s | %g (%s, %s) | %g | %s |" % (x["symbol"], x["settlement"], x["iv_true"], x["source"], x["gap"], x["executor"], x["iv_true_next_8h"]))
if ep:
    L.append("\nExecutor settlements before the recomputed range where the event-stream (x0910 lineage) interval differs from the executor:\n\n| name | settlement | stream iv | executor | ledger | gap |\n|---|---|---|---|---|---|")
    for x in ep: L.append("| %s | %s | %g | %g | %s | %s |" % (x["symbol"], x["settlement"], x["iv_stream"], x["executor"], x["ledger"], x["gap"]))
L.append("\n### P2 · incumbent rows (≤ 08-31 00Z) against the producer ledger\n| item | value |\n|---|---|")
ir = Bp["incumbent_rows"]; se = Bp["stream_events"]
L.append("| base panel rows %s .. %s: in-force settlement found in ledger | %d cells checked; not in ledger %d; rate ≠ ledger-aligned stream rate %d; **f_fund_iv ≠ ledger iv %d** (names: %s) |" % (ir["first_anchor"], ir["last_anchor"], ir["checked"], ir["not_in_ledger"], ir["rate_mismatch"], ir["n_iv_mismatch"], ", ".join(ir["iv_mismatch_names"]) or "none"))
L.append("| event-stream settlements 08-28 00Z .. 08-31 00Z vs ledger | %d checked; **iv ≠ ledger %d** (names: %s) |" % (se["checked"], se["n_iv_mismatch"], ", ".join(se["names"]) or "none"))
if ir["iv_mismatch"]:
    L.append("\n| name | anchor | panel iv | ledger iv | in-force settlement | stream iv |\n|---|---|---|---|---|---|")
    for x in ir["iv_mismatch"][:40]: L.append("| %s | %s | %g | %g | %s | %g |" % tuple(x))
if Bp["v1_seed_linear_response"]:
    L.append("\nCounterfactual only (the check after this table shows the stored seed was **not** built with these intervals): v1 EMA seed at the cut if the base panel had used the event-stream intervals on the mismatching pre-cut settlements (linear response):\n\n| name | settlements | v1 seed | correction | rank of seed → corrected (of finite) | decay at 09-02 00Z / window end |\n|---|---|---|---|---|---|")
    for x in Bp["v1_seed_linear_response"]:
        L.append("| %s | %d | %+.3e | %+.3e | %d → %d (of %d) | %.3f / %.3f |" % (x["symbol"], x["n_events"], x["v1_seed"], x["v1_seed_correction_if_base_used_stream_iv"], x["rank_of_seed"], x["rank_if_changed"], x["names_finite"], x["decay_factor_at_09_02_00Z"], x["decay_factor_at_window_end"]))
L.append("\n**Which intervals built the stored v1 EMA seed** (`RECEIPT_T5d_posthoc_seed.json`; recursion from the stored v1 at %s to %s, max relative error vs stored float32 at each anchor):\n" % (PS["window"][0], PS["window"][1]))
L.append("| names | ledger/gap intervals | x0910 event-stream intervals |\n|---|---|---|")
cs = PS["controls_names_without_interval_difference"]
L.append("| %d control names (no interval difference) | median %.1e, p99 %.1e | same vectors |" % (cs["controls_L_anchor"]["n"], cs["controls_L_anchor"]["median_rel_err"], cs["controls_L_anchor"]["p99"]))
for nm_, v in PS["names_with_stream_ledger_difference"].items():
    L.append("| %s (%d of %d settlements differ) | %.1e | %.3f |" % (nm_, v["n_iv_differs"], v["n_events"], v["L_anchor"], v["S_anchor"]))
L.append("\n### P3 · where the regenerated weights moved the replay (REG − T5C, bps/anchor)\n")
for t in TAGS:
    c = C[t]; tt = c["totals"]
    L.append("**%s** — totals: price %+.4f, carry weight part %+.4f, carry repricing part %+.4f, cost %+.4f, net %+.4f (residual vs components %.1e).\n" % (t, tt["P"], tt["C_weight"], tt["C_reprice"], tt["K"], tt["N"], c["max_abs_residual_vs_components"]))
    L.append("| subset | price | carry (weight) | carry (repricing) | cost | net |\n|---|---|---|---|---|---|")
    for lab, key in (("FTRIM-switch names (%s)" % ", ".join(x.replace("USDT", "") for x in c["ftrim_switch_names"]), "subtotal_ftrim_switch_names"), ("other names with changed intervals", "subtotal_other_iv_changed_names"), ("all other names", "subtotal_rest")):
        v = c[key]; L.append("| %s | %+.4f | %+.4f | %+.4f | %+.4f | %+.4f |" % (lab, v["P"], v["C_weight"], v["C_reprice"], v["K"], v["N"]))
    L.append("\n| UTC day | anchors | price | carry | cost | net | contribution to window-mean net |\n|---|---|---|---|---|---|---|")
    for dname, v in c["per_day"].items():
        L.append("| %s | %d | %+.3f | %+.3f | %+.4f | %+.3f | %+.4f |" % (dname, v["n"], v["P"], v["C"], v["K"], v["N"], v["contribution_to_window_mean_N"]))
    L.append("\nNames with the largest |price change|: %s.\n" % ", ".join("%s %+.4f (net %+.4f)" % (x["symbol"].replace("USDT", ""), x["P"], x["N"]) for x in c["names_abs_P"][:6]))
    L.append("\n| name (most negative net change) | price | carry (weight) | carry (repricing) | cost | net | interval changed | FTRIM switch |\n|---|---|---|---|---|---|---|---|")
    for x in c["names_most_negative_N"][:10]:
        L.append("| %s | %+.4f | %+.4f | %+.4f | %+.5f | %+.4f | %s | %s |" % (x["symbol"], x["P"], x["C_weight"], x["C_reprice"], x["K"], x["N"], x["iv_changed"], x["ftrim_switch"]))
    L.append("")
L.append("### P4 · construction-only part of the D_K − R_K gap (sum of the nine group Shapley values = total − REM; k 90)\n| seed | caliber | outcome | total | REM (model) | construction | reading |\n|---|---|---|---|---|---|---|")
for t in TAGS:
    for cal in ("REG", "T5C"):
        for q in ("P", "C", "N"):
            v = D[t][cal][q]; L.append("| %s | %s | %s | %s | %s | %s | %s |" % (t, cal, QN[q], ci(v["total"]), ci(v["REM"]), ci(v["construction"]), v["reading"]))
L.append("\n### P5 · where the deployed books' fixed-weight carry correction comes from (`devices/t5d_posthoc_dk_carry.py`; Σ w·(C4 corrected − C4 x0910)·1e4 / 61; producer FTRIM from %s)\n" % PD["ftrim_on"])
for nm in ("D_K", "D_B"):
    v = PD["result"][nm]
    L.append("**%s** — total %+.4f (before FTRIM start %+.4f over %d anchors, after %+.4f over %d)%s.\n" % (nm, v["total"], v["before_ftrim"], v["n_before"], v["after_ftrim"], v["n_after"], ("; residual vs components %.1e" % v["max_abs_residual_vs_components"]) if v["max_abs_residual_vs_components"] is not None else ""))
    L.append("| name | total | before FTRIM start | after | held anchors with a changed interval | first .. last | mean weight there (×1e3) | carry ratio corrected / x0910 |\n|---|---|---|---|---|---|---|---|")
    for x in v["names"]:
        if x["anchors_changed_and_held"] == 0: continue
        L.append("| %s | %+.4f | %+.4f | %+.4f | %d | %s .. %s | %+.2f | %s |" % (x["symbol"], x["total"], x["before_ftrim"], x["after_ftrim"], x["anchors_changed_and_held"], x["first"], x["last"], 1e3 * x["mean_weight_when_changed"], ", ".join("%g" % q for q in x["carry_ratio_corr_over_x0910"])))
    L.append("")
L.append("\n## T11 · devices and inputs\n| item | sha256 |\n|---|---|")
for nm, h in (("t5d_interval_sources.py", IS["self_sha256"]), ("t5d_ivfix_panel.py", PN["self_sha256"]), ("t5d_drive.py", DR["self_sha256"]), ("w10_sleeve_t5c.py (T5c device, unchanged)", DR["device_sha256"]), ("t5d_bridge.py (run 2)", BR["self_sha256"]),
              ("t5d_bridge.py (run 1, archived)", RD["run1"]["device_sha256"]), ("t5d_posthoc.py", PH["self_sha256"]), ("corrected panel (pod2)", PN["out_sha256"]), ("bridge components npz", BR["components_npz_sha256"]), ("interval source list (cc_tmp)", IS["out_sha256"]), ("per-settlement source list (pod2, cc_tmp)", A["per_settlement_list_sha256"]), ("t5d_posthoc_seed.py", PS["self_sha256"]), ("t5d_posthoc_fallback.py", PF["self_sha256"]), ("t5d_posthoc_dk_carry.py (Mac)", PD["self_sha256"])):
    L.append("| %s | `%s` |" % (nm, h))
for p_, h in PN["inputs"].items(): L.append("| %s | `%s` |" % (p_, h))
for tag, r in DR["runs"].items(): L.append("| arm %s (pod2 only) | `%s` |" % (tag, r["out_sha256"]))
open(T + "/receipts/TABLES_T5d.md", "w").write("\n".join(L) + "\n"); print("wrote TABLES_T5d.md", len(L), "lines")
