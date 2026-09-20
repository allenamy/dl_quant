#!/usr/bin/env python3
"""fcf_doc_check.py — re-print, straight from the receipts, every number the result doc states in prose (§0, §6, §7).
The doc's tables are machine-rendered; these are the ones a human typed, so they are the ones that can be wrong.
usage: fcf_doc_check.py   (prints "receipt value" next to "as written in the doc"; any row that does not match is a defect)
"""
import json

R = "/workspace/fallback_cf_2026-09-20/receipts"
T = json.load(open(f"{R}/FCF_TABLES.json"))
W = json.load(open(f"{R}/FCF_RISK_WEIGHTS.json"))
P = json.load(open(f"{R}/FCF_P_READING.json"))
FB = "fallback_subsample_HIST"
HI = "HIST_2023-06-30→2025-12-31 (the FINDING's window)"
RL = "R_level_2023-06-30→2026-08-31"
rows = []


def add(label, got, doc):
    rows.append((label, got, doc))


for a in ("F0", "F1", "F2", "F4a"):
    c = T["arms"][a]["cells"][FB]
    add(f"§0/§3.1 {a} fallback g", round(c["g"], 4), {"F0": -1.2438, "F1": -0.0750, "F2": -0.4807, "F4a": -0.6993}[a])
    add(f"§3.1 {a} fallback sharpe", round(c["sharpe_daily"], 3), {"F0": -2.038, "F1": -0.148, "F2": -0.774, "F4a": -1.179}[a])
for a in ("F1", "F2", "F4a"):
    p = T["paired_vs_F0"][a][FB]
    add(f"§0/§4 {a}-F0 fallback dg", round(p["d_g"]["estimate"], 4), {"F1": 1.1688, "F2": 0.7631, "F4a": 0.5445}[a])
    add(f"§4 {a}-F0 fallback CI lo", round(p["d_g"]["ci95"][0], 4), {"F1": 0.4470, "F2": -0.7365, "F4a": 0.1172}[a])
    add(f"§4 {a}-F0 fallback CI hi", round(p["d_g"]["ci95"][1], 4), {"F1": 1.9711, "F2": 2.3798, "F4a": 0.9985}[a])
    add(f"§4 {a}-F0 fallback seeds same sign", p["per_fill_path_delta"]["g"]["n_seeds_with_the_same_sign"], 32)
add("§0 F1-F0 HIST dg", round(T["paired_vs_F0"]["F1"][HI]["d_g"]["estimate"], 4), 0.2795)
add("§0 F1-F0 R dg", round(T["paired_vs_F0"]["F1"][RL]["d_g"]["estimate"], 4), 0.2202)
f5 = T["prereg_s5_falsification"]["lead_prior_F1_on_the_fallback_subsample_comes_in_BELOW_the_combo_bucket"]
add("§0/§7 F1 fallback g CI lo", round(f5["ci95"][0], 4), -1.5131)
add("§0/§7 F1 fallback g CI hi", round(f5["ci95"][1], 4), 1.2307)
add("§7 combo bucket reference", round(f5["combo_bucket_reference"], 4), 0.4903)
add("§7 CI excludes the reference", f5["ci95_excludes_the_reference"], False)
add("§0 rev24 share of the F0->F1 gap (%)",
    round(100 * T["paired_vs_F0"]["F4a"][FB]["d_g"]["estimate"] / T["paired_vs_F0"]["F1"][FB]["d_g"]["estimate"], 1), 46.6)
for a in ("F0", "F1", "F4a"):
    c = W["arms"][a]["cells"]["fallback_subsample_full_recipe"]["written"]
    add(f"§5.1 {a} amplification median", round(c["amplification_gross_mult_over_gross_in"]["median"], 3),
        {"F0": 3.348, "F1": 5.303, "F4a": 3.405}[a])
    add(f"§5.1 {a} effective names median", round(c["effective_names_1_over_sumw2"]["median"], 1),
        {"F0": 224.5, "F1": 211.4, "F4a": 233.4}[a])
add("§5.1 F1 gross_in median", round(W["arms"]["F1"]["cells"]["fallback_subsample_full_recipe"]["written"]["gross_in"]["median"], 4), 0.3772)
g = W["prereg_s4_F1_concentration_gate"]
add("§5.1 gate ratio fallback∩full-recipe", round(g["fallback_subsample_full_recipe"]["ratio"], 3), 1.097)
add("§5.1 gate breached anywhere", any(v["breached"] for v in g.values()), False)
h = W["arms"]["F2"]["consecutive_hold_runs"]
add("§5.2 F2 longest hold, full-recipe (anchors)", h["full_recipe_window"]["longest_anchors"], 130)
add("§5.2 F2 longest hold, full-recipe (days)", h["full_recipe_window"]["longest_days"], 21.7)
add("§5.2 F2 longest hold, whole window (anchors)", h["whole_window"]["longest_anchors"], 1110)
add("§5.3 F2 untradable p95 (effective, fallback)", round(
    W["arms"]["F2"]["cells"]["fallback_subsample_full_recipe"]["effective_book_held"]["untradable_weight_share"]["p95"], 4), 0.0125)
B2 = "FULL_RECIPE window start @ 2023-06-30T04:00:00Z"
B1 = "run window start @ 2022-06-30T00:00:00Z"
for lab, B, want in (("FULLRECIPE", B2, {"F0": 32, "F1": 32, "F2": 10, "F4a": 32}), ("RUNWINDOW", B1, {"F0": 32, "F1": 0, "F2": 0, "F4a": 0})):
    for nm, r in P["runs"].items():
        a = nm.split("arm ")[-1].rstrip(")")
        mem = r["bases"][B]["summary"]["end_return_phalt"]["population"]["members"]
        add(f"§6.1 {lab} {a} paths breaching", sum(1 for m in mem if m.get("fired")), want[a])
        add(f"§6.1 {lab} {a} P-halt end mean", round(r["bases"][B]["summary"]["end_return_phalt"]["measured"]["mean"], 4),
            {("FULLRECIPE", "F0"): -0.2527, ("FULLRECIPE", "F1"): -0.2519, ("FULLRECIPE", "F2"): 1.2889, ("FULLRECIPE", "F4a"): -0.2514,
             ("RUNWINDOW", "F0"): -0.2527, ("RUNWINDOW", "F1"): 3.0995, ("RUNWINDOW", "F2"): 2.6908, ("RUNWINDOW", "F4a"): 2.5397}[(lab, a)])
# §6.2 — the hand-typed reading-P2 table (W_ENTRY, the AMENDMENT 4 main slice)
P2 = json.load(open(f"{R}/FCF_P2_READING.json"))
DOC_P2 = {
    ("RUNWINDOW", "12"): {"F0": -0.2526, "F1": 3.0161, "F2": 2.6456, "F4a": 2.4756},
    ("RUNWINDOW", "sim"): {"F0": -0.2527, "F1": 3.0995, "F2": 2.6908, "F4a": 2.5397},
    ("RUNWINDOW", "never"): {"F0": -0.2332, "F1": -0.0397, "F2": 0.0898, "F4a": -0.0397},
    ("FULLRECIPE", "12"): {"F0": -0.2530, "F1": -0.2519, "F2": 0.6567, "F4a": -0.2512},
    ("FULLRECIPE", "sim"): {"F0": -0.2527, "F1": -0.2519, "F2": 1.2889, "F4a": -0.2514},
    ("FULLRECIPE", "never"): {"F0": -0.2513, "F1": -0.1752, "F2": -0.1278, "F4a": -0.2241},
}
for (lab, H), want in DOC_P2.items():
    B = B1 if lab == "RUNWINDOW" else B2
    for nm, r in P2["runs"].items():
        a = nm.split("arm ")[-1].rstrip(")")
        m = r["bases"][B][H]["W_ENTRY"]["summary"]["end_return_P2"]["measured"]
        add(f"§6.2 {lab} H={H} {a} end_return_P2 mean", round(m["mean"], 4), want[a])
        add(f"§6.2 {lab} H={H} {a} n_eff beside the mean", m["n_eff"], 32)
# §6.1 median halt anchors quoted in the doc
for lab, B, want in (("FULLRECIPE", B2, {"F0": "2024-03-18T16:00:00Z", "F1": "2024-07-15T16:00:00Z", "F2": "2024-08-05T08:00:00Z",
                                         "F4a": "2024-06-18T08:00:00Z"}),
                     ("RUNWINDOW", B1, {"F0": "2023-01-18T16:00:00Z"})):
    for nm, r in P["runs"].items():
        a = nm.split("arm ")[-1].rstrip(")")
        if a not in want: continue
        ha = sorted(m2["halt_anchor"] for m2 in r["bases"][B]["summary"]["end_return_phalt"]["population"]["members"] if m2.get("fired"))
        add(f"§6.1 {lab} {a} median halt anchor", ha[len(ha) // 2] if ha else None, want[a])
bad = [r for r in rows if r[1] != r[2]]
for lab, got, doc in rows:
    print(("  OK   " if got == doc else "MISMATCH ") + f"{lab:52s} receipt={got!r:>12}  doc={doc!r}")
print(f"\nFCF_DOC_CHECK VERDICT={'PASS' if not bad else 'MISMATCH'} checked={len(rows)} mismatching={len(bad)}")
raise SystemExit(0 if not bad else 3)
