#!/usr/bin/env python3
"""fcf_doc_check.py — re-print, straight from the receipts, every number the result doc states in prose (§0, §6, §7).
The doc's tables are machine-rendered; these are the ones a human typed, so they are the ones that can be wrong.
usage: fcf_doc_check.py   (prints "receipt value" next to "as written in the doc"; any row that does not match is a defect)
"""
import json, re, sys

# --without-arm <ARM>: exercise the demotion path. Assertions ABOUT that arm are skipped (and COUNTED, so a skip that silently
# does nothing is visible in the verdict line); every other assertion must still pass. Used by fcf_demotion_drill.py.
# NOTE the boundary match: labels contain forms like 'F4bp-F0', which split() keeps as ONE token, so a token test silently
# skipped nothing the first time I wrote this. Non-alphanumeric boundaries also stop 'F4b' matching 'F4bp'.
WITHOUT = None
for _i, _a in enumerate(sys.argv):
    if _a == '--without-arm' and _i + 1 < len(sys.argv): WITHOUT = sys.argv[_i + 1]
SKIPPED = []

R = "/workspace/fallback_cf_2026-09-20/receipts"
T = json.load(open(f"{R}/FCF_TABLES.json"))
W = json.load(open(f"{R}/FCF_RISK_WEIGHTS.json"))
P = json.load(open(f"{R}/FCF_P_READING.json"))
FB = "fallback_subsample_HIST"
HI = "HIST_2023-06-30→2025-12-31 (the FINDING's window)"
RL = "R_level_2023-06-30→2026-08-31"
rows = []


def add(label, got, doc):
    if WITHOUT and re.search(r'(?<![A-Za-z0-9])' + re.escape(WITHOUT) + r'(?![A-Za-z0-9])', label):
        SKIPPED.append(label); return
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
        if a not in want: continue
        add(f"\u00a76.1 {lab} {a} paths breaching", sum(1 for m in mem if m.get("fired")), want[a])
        add(f"§6.1 {lab} {a} P-halt end mean", round(r["bases"][B]["summary"]["end_return_phalt"]["measured"]["mean"], 4),
            {("FULLRECIPE", "F0"): -0.2527, ("FULLRECIPE", "F1"): -0.2519, ("FULLRECIPE", "F2"): 1.2889, ("FULLRECIPE", "F4a"): -0.2514,
             ("RUNWINDOW", "F0"): -0.2527, ("RUNWINDOW", "F1"): 3.0995, ("RUNWINDOW", "F2"): 2.6908, ("RUNWINDOW", "F4a"): 2.5397}[(lab, a)])
# §6.2 — the hand-typed reading-P2 table (W_ENTRY, the AMENDMENT 4 main slice)
P2 = json.load(open(f"{R}/FCF_P2_READING.json"))
DOC_P2 = {
    ("RUNWINDOW", "12"): {"F0": -0.2526, "F1": 3.0161, "F2": 2.6456, "F4a": 2.4756, "F4bp": 2.1020},
    ("RUNWINDOW", "sim"): {"F0": -0.2527, "F1": 3.0995, "F2": 2.6908, "F4a": 2.5397, "F4bp": 2.1170},
    ("RUNWINDOW", "never"): {"F0": -0.2332, "F1": -0.0397, "F2": 0.0898, "F4a": -0.0397, "F4bp": -0.0249},
    ("FULLRECIPE", "12"): {"F0": -0.2530, "F1": -0.2519, "F2": 0.6567, "F4a": -0.2512, "F4bp": -0.2533},
    ("FULLRECIPE", "sim"): {"F0": -0.2527, "F1": -0.2519, "F2": 1.2889, "F4a": -0.2514, "F4bp": -0.2529},
    ("FULLRECIPE", "never"): {"F0": -0.2513, "F1": -0.1752, "F2": -0.1278, "F4a": -0.2241, "F4bp": -0.2506},
}
for (lab, H), want in DOC_P2.items():
    B = B1 if lab == "RUNWINDOW" else B2
    for nm, r in P2["runs"].items():
        a = nm.split("arm ")[-1].rstrip(")")
        m = r["bases"][B][H]["W_ENTRY"]["summary"]["end_return_P2"]["measured"]
        w_ = want.get(a, None)
        if w_ is None:
            print("  NOTE  \u00a76.2 %s H=%s %-5s end_return_P2 mean = %+.4f  (n_eff %d) \u2014 not yet quoted in the doc"
                  % (lab, H, a, m["mean"], m["n_eff"])); continue
        add(f"\u00a76.2 {lab} H={H} {a} end_return_P2 mean", round(m["mean"], 4), w_)
        # E-0920-C balance identity: measured + not-applicable must close on the declared population. Stays green on a
        # legitimately incomplete population (a path that traded no anchor of the window); still red if a member vanishes
        # from both sides. Raised by p2-aggregation-fix, who owns the aggregator: a hardcoded n_eff == 32 would go red on a
        # CORRECT number the moment a never/later-base figure is printed, and the cheap way out would be to relax it.
        blk = r["bases"][B][H]["W_ENTRY"]["summary"]["end_return_P2"]
        add(f"§6.2 {lab} H={H} {a} population closes (n_eff + no_measurement == population_n)",
            m["n_eff"] + blk["no_measurement"]["n"], m["population_n"])
        # a SEPARATE, differently-named claim, so "arithmetic closed" and "population happens to be complete" are not welded:
        add(f"§6.2 {lab} H={H} {a} population is COMPLETE for the printed figure", m["n_eff"], m["population_n"])
# §6.1 median halt anchors quoted in the doc
for lab, B, want in (("FULLRECIPE", B2, {"F0": "2024-03-18T16:00:00Z", "F1": "2024-07-15T16:00:00Z", "F2": "2024-08-05T08:00:00Z",
                                         "F4a": "2024-06-18T08:00:00Z"}),
                     ("RUNWINDOW", B1, {"F0": "2023-01-18T16:00:00Z"})):
    for nm, r in P["runs"].items():
        a = nm.split("arm ")[-1].rstrip(")")
        if a not in want: continue
        ha = sorted(m2["halt_anchor"] for m2 in r["bases"][B]["summary"]["end_return_phalt"]["population"]["members"] if m2.get("fired"))
        add(f"§6.1 {lab} {a} median halt anchor", ha[len(ha) // 2] if ha else None, want[a])
# §6.1b — the UNSATURATED quantities (survival days, no-halt end return) the doc now leads with
U = json.load(open(f"{R}/FCF_P_UNSATURATED.json"))
DOC_U = {
    ("2023-06-30T04:00:00Z"): {"F0": (32, 262.5, 266.7, 1.3463), "F1": (32, 381.5, 380.7, 2.2100),
                               "F2": (10, 402.2, 397.4, 1.9542), "F4a": (32, 352.8, 346.1, 1.7667),
                               "F4bp": (32, 262.8, 270.1, 1.4803)},
    ("2022-06-30T00:00:00Z"): {"F0": (32, 202.7, 235.0, 1.4448), "F1": (0, None, None, 3.0995),
                               "F2": (0, None, None, 2.6908), "F4a": (0, None, None, 2.5397),
                               "F4bp": (0, None, None, 2.1170)},
}
for B, d in U["bases"].items():
    want = DOC_U[d["base_anchor_utc"]]
    for a, v in d["arms"].items():
        nb, med, mean, nohalt = want[a]
        sv = v["survival_days_to_halt"]
        add(f"§6.1b {d['base_anchor_utc']} {a} breaching", v["paths_breaching"], nb)
        add(f"§6.1b {d['base_anchor_utc']} {a} survival median", None if sv["median"] is None else round(sv["median"], 1), med)
        add(f"§6.1b {d['base_anchor_utc']} {a} survival mean", None if sv["mean"] is None else round(sv["mean"], 1), mean)
        add(f"§6.1b {d['base_anchor_utc']} {a} no-halt end mean", round(v["end_return_no_halt"]["mean"], 4), nohalt)
        add(f"§6.1b {d['base_anchor_utc']} {a} survival n_measured == breaching", sv["n_measured"], nb)
        add(f"§6.1b {d['base_anchor_utc']} {a} never-halt named count", sv["no_measurement"]["n"], 32 - nb)
u = U["bases"]["FULL_RECIPE window start @ 2023-06-30T04:00:00Z"]["arms"]
add("§0/§6.1b F1 survives longer than F0 (median days)",
    round(u["F1"]["survival_days_to_halt"]["median"] - u["F0"]["survival_days_to_halt"]["median"], 0), 119.0)
add("§0/§6.1b that as a share of F0 (%)",
    round(100 * (u["F1"]["survival_days_to_halt"]["median"] / u["F0"]["survival_days_to_halt"]["median"] - 1), 0), 45.0)
add("§0/§6.1b no-halt end gap F1-F0 (pp)",
    round(100 * (u["F1"]["end_return_no_halt"]["mean"] - u["F0"]["end_return_no_halt"]["mean"]), 0), 86.0)
# ---- F4b′ (F4 of record) and AMENDMENT 3 §4 conditions 1 and 2 ----
FB4 = "fallback_subsample_HIST"; EX = "fallback_subsample_HIST_EXCL_allrev24"; AR = "allrev24_anchors_that_are_fallback"
for a, lvl, dg, lo, hi in (("F0", -1.2438, None, None, None), ("F1", -0.0750, 1.1688, 0.4470, 1.9711),
                           ("F2", -0.4807, 0.7631, -0.7365, 2.3798), ("F4a", -0.6993, 0.5445, 0.1172, 0.9985),
                           ("F4bp", -1.0562, 0.1876, -0.1393, 0.5119)):
    add(f"\u00a70.3/\u00a78.4 {a} fallback g (incl)", round(T["arms"][a]["cells"][FB4]["g"], 4), lvl)
    if dg is not None:
        q = T["paired_vs_F0"][a][FB4]["d_g"]
        add(f"\u00a70.3 {a}-F0 fallback dg (incl)", round(q["estimate"], 4), dg)
        add(f"\u00a70.3 {a}-F0 fallback CI (incl)", [round(q["ci95"][0], 4), round(q["ci95"][1], 4)], [lo, hi])
for a, lvl, dg, lo, hi in (("F0", -1.2335, None, None, None), ("F1", -0.0410, 1.1925, 0.4631, 2.0008),
                           ("F2", -0.4610, 0.7725, -0.7321, 2.4002), ("F4a", -0.6857, 0.5478, 0.1203, 1.0011),
                           ("F4bp", -1.0428, 0.1907, -0.1372, 0.5170)):
    add(f"\u00a78.4c1 {a} fallback g (EXCL allrev24)", round(T["arms"][a]["cells"][EX]["g"], 4), lvl)
    if dg is not None:
        q = T["paired_vs_F0"][a][EX]["d_g"]
        add(f"\u00a78.4c1 {a}-F0 dg (EXCL)", round(q["estimate"], 4), dg)
        add(f"\u00a78.4c1 {a}-F0 CI (EXCL)", [round(q["ci95"][0], 4), round(q["ci95"][1], 4)], [lo, hi])
add("\u00a78.4c1 n incl", T["cell_definitions"][FB4]["n_anchors"], 1323)
add("\u00a78.4c1 n excl", T["cell_definitions"][EX]["n_anchors"], 1321)
add("\u00a78.4c1 allrev24 on the 10039 axis", T["allrev24_subset"]["n_on_the_10039_anchor_axis"], 172)
add("\u00a78.4c1 allrev24 in the judge window", T["allrev24_subset"]["n_in_the_judge_window"], 172)
add("\u00a78.4c1 allrev24 that are fallback (n)", T["cell_definitions"][AR]["n_anchors"], 70)
for a, lvl, sh in (("F0", -4.5435, -8.626), ("F1", -0.1020, -0.385), ("F2", -0.3856, -4.634),
                   ("F4a", 0.2647, 1.061), ("F4bp", 0.3436, 1.233)):
    add(f"\u00a78.4c1 70-anchor {a} g", round(T["arms"][a]["cells"][AR]["g"], 4), lvl)
    add(f"\u00a78.4c1 70-anchor {a} sharpe", round(T["arms"][a]["cells"][AR]["sharpe_daily"], 3), sh)
KC = json.load(open(f"{R}/FCF_F4BP_VS_KC.json"))
zc = [c for c in KC["checks"] if c["check"].startswith("A.")][0]["detail"]
add("\u00a78.4c2 z(F4b\u2032)==z_kc pre-FTRIM, equal", zc["equal"], 10038)
add("\u00a78.4c2 z(F4b\u2032)==z_kc pre-FTRIM, compared", zc["compared"], 10038)
bc = [c for c in KC["checks"] if c["check"].startswith("B.")][0]["detail"]
add("\u00a78.4c2 anchors where FTRIM zeroed nothing", bc["anchors_where_FTRIM_zeroed_nothing"], 1963)
cc = KC["C_residual_on_simulated_fallback_anchors"]
add("\u00a78.4c2 chain-state-only n", cc["FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE"]["n"], 398)
add("\u00a78.4c2 ftrim+chain n", cc["FTRIM_fired__residual_is_FTRIM_PLUS_CHAIN_STATE"]["n"], 2039)
add("\u00a78.4c2 chain-state-only L1 median",
    round(cc["FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE"]["sum_abs_dw_L1"]["median"], 4), 0.0239)
add("\u00a78.4c2 ftrim+chain L1 median",
    round(cc["FTRIM_fired__residual_is_FTRIM_PLUS_CHAIN_STATE"]["sum_abs_dw_L1"]["median"], 4), 0.0534)
add("\u00a78.4c2 ratio", round(KC["C_verdict"]["ratio_ftrim_plus_chain_over_chain_alone"], 2), 2.23)
add("\u00a70.3 rev24 share of the gap, CLEAN (%)",
    round(100 * T["paired_vs_F0"]["F4bp"][FB4]["d_g"]["estimate"] / T["paired_vs_F0"]["F1"][FB4]["d_g"]["estimate"], 1), 16.1)
add("\u00a70.3 F4a overstates rev24 by (x)",
    round(T["paired_vs_F0"]["F4a"][FB4]["d_g"]["estimate"] / T["paired_vs_F0"]["F4bp"][FB4]["d_g"]["estimate"], 1), 2.9)
P2R = json.load(open(f"{R}/FCF_P2_READING.json"))["assertions"]
add("\u00a76 W_ENTRY==W_CARRY cells equal", sum(1 for x in P2R if x["W_ENTRY_equals_W_CARRY"]), 46)
add("\u00a76 W_ENTRY==W_CARRY cells differing", sum(1 for x in P2R if not x["W_ENTRY_equals_W_CARRY"]), 4)
add("\u00a76 all differing cells are H=never", all(x["H"] == "never" for x in P2R if not x["W_ENTRY_equals_W_CARRY"]), True)
# ---- AMENDMENT 4 A1' (§8.5) ----
AP = json.load(open(f"{R}/FCF_A1PRIME.json"))
cl = {c["clause"][:6]: c for c in AP["clauses"]}
add("\u00a78.5.2 A1' overall verdict", AP["VERDICT"], "REFUSED")
add("\u00a78.5.2 A1' clause 1 (legz/pm bitwise) ok", cl["A1p.1_"]["ok"], True)
add("\u00a78.5.2 A1' clause 1 legz equal", cl["A1p.1_"]["detail"]["legz_equal"], 10038)
add("\u00a78.5.2 A1' clause 1 pm equal", cl["A1p.1_"]["detail"]["pm_equal"], 10038)
add("\u00a78.5.2 A1' clause 2 (W3-MATCH) ok", cl["A1p.2_"]["ok"], False)
add("\u00a78.5.2 A1' clause 2 anchors in scope", cl["A1p.2_"]["detail"]["anchors_in_scope"], 10037)
add("\u00a78.5.2 A1' clause 2 n_mismatch", cl["A1p.2_"]["detail"]["n_mismatch"], 1)
add("\u00a78.5.2 A1' clause 2 the mismatching anchor", cl["A1p.2_"]["detail"]["mismatches"][0]["anchor"], "2022-06-30T00:00:00Z")
add("\u00a78.5.2 A1' clause 3 (decay bound) ok", cl["A1p.3_"]["ok"], True)
d3 = cl["A1p.3_"]["detail"]
add("\u00a78.5.2 alpha read from the frozen config", d3["alpha"], 0.1)
add("\u00a78.5.2 n anchors to the full-recipe start", d3["n_anchors_between"], 2191)
add("\u00a78.5.2 decay bound", d3["bound"], "5.563e-101")
add("\u00a78.5.2 decay threshold (writer resolution)", d3["threshold"], 1e-09)
ad = AP["adversarial_check_on_clause_2"]
add("\u00a78.5.5 clause-2 blind set size", ad["n_anchors_blind_to_clause_2"], 1)
add("\u00a78.5.5 the blind anchor", ad["blind_anchors"][0], "2022-01-31T04:00:00Z")
add("\u00a78.5.5 divergence inside the blind set?", ad["divergence_is_inside_the_blind_set"], False)
# ---- p2's receipt-only positive control on the W_ENTRY/W_CARRY split (§6 declaration 1) ----
SC = json.load(open(f"{R}/FCF_SEMANTICS_CONTROL.json"))
scc = {c["check"]: c for c in SC["checks"]}
add("\u00a76 semantics control verdict", SC["VERDICT"], "PASS")
add("\u00a76 predicted == observed differing set",
    scc["predicted_differing_set_equals_observed_differing_set"]["ok"], True)
add("\u00a76 n predicted differing",
    scc["predicted_differing_set_equals_observed_differing_set"]["detail"]["n_predicted"], 4)
add("\u00a76 n observed differing",
    scc["predicted_differing_set_equals_observed_differing_set"]["detail"]["n_observed"], 4)
add("\u00a76 split is exercised (flag demonstrably wired)",
    "the_split_is_EXERCISED_by_this_data_so_the_flag_is_demonstrably_wired" in scc, True)
_pre = {c["run"]: c["n_paths_with_pre_base_flattens"] for c in SC["cells"]
        if c["H"] == "never" and c["base"] == "2023-06-30T04:00:00Z"}
for _a, _n in (("F0", 4), ("F1", 32), ("F2", 0), ("F4a", 32), ("F4bp", 32)):
    add(f"\u00a76 {_a} paths with pre-base flattens", _pre.get(_a), _n)
# ---- the three consequences p2-aggregation-fix derived from the per-arm counts (§6) ----
_P2 = json.load(open(f"{R}/FCF_P2_READING.json"))
_B = "FULL_RECIPE window start @ 2023-06-30T04:00:00Z"
for _nm, _r in _P2["runs"].items():
    _a = _nm.split("arm ")[-1].rstrip(")")
    _blk = _r["bases"][_B]["never"]["W_CARRY"]["summary"]["end_return_P2"]
    _m, _nmz = _blk["measured"], _blk["no_measurement"]
    if _a == "F0":
        # by_reason[...]["members"] is a flat list of seed ints, not of records
        _seeds = sorted(x for v in _nmz["by_reason"].values() for x in v["members"])
        add("\u00a76(a) F0 pre-base-flatten seeds", _seeds, [3, 5, 12, 17])
        add("\u00a76(a) F0 n with pre-base flattens", _nmz["n"], 4)
    if _a in ("F1", "F4a", "F4bp"):
        add(f"\u00a76(b) {_a} W_CARRY/never n_eff", _m["n_eff"], 0)
        add(f"\u00a76(b) {_a} W_CARRY/never measured.mean is None", _m["mean"] is None, True)
        add(f"\u00a76(b) {_a} W_CARRY/never whole_population.mean", _blk["whole_population"]["mean"], 0.0)
    if _a == "F2":
        add("\u00a76(c) F2 W_CARRY/never has no unmeasured member", _nmz["n"], 0)
        for _H in ("12", "8", "20", "sim", "never"):
            _e = _r["bases"][_B][_H]["W_ENTRY"]["summary"]["end_return_P2"]["measured"]
            _c = _r["bases"][_B][_H]["W_CARRY"]["summary"]["end_return_P2"]["measured"]
            add(f"\u00a76(c) F2 H={_H} W_ENTRY block byte-identical to W_CARRY",
                json.dumps(_e, sort_keys=True) == json.dumps(_c, sort_keys=True), True)
# the doc must NOT quote the W_CARRY 0.0 anywhere: the §6.2 never row is W-ENTRY
for _a, _v in (("F0", -0.2513), ("F1", -0.1752), ("F2", -0.1278), ("F4a", -0.2241), ("F4bp", -0.2506)):
    _we = _P2["runs"][[k for k in _P2["runs"] if k.endswith(f"arm {_a})")][0]]["bases"][_B]["never"]["W_ENTRY"]["summary"]["end_return_P2"]["measured"]
    add(f"\u00a76.2 never row is the W-ENTRY figure for {_a}", round(_we["mean"], 4), _v)
bad = [r for r in rows if r[1] != r[2]]
for lab, got, doc in rows:
    print(("  OK   " if got == doc else "MISMATCH ") + f"{lab:52s} receipt={got!r:>12}  doc={doc!r}")
print(f"\nFCF_DOC_CHECK VERDICT={'PASS' if not bad else 'MISMATCH'} checked={len(rows)} mismatching={len(bad)}"
      + (f' | skipped(--without-arm {WITHOUT}): {len(SKIPPED)}' if WITHOUT else ''))
raise SystemExit(0 if not bad else 3)
