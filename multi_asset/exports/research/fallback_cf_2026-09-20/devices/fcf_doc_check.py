#!/usr/bin/env python3
"""fcf_doc_check.py — re-print, straight from the receipts, every number the result doc states in prose (§0, §6, §7).
The doc's tables are machine-rendered; these are the ones a human typed, so they are the ones that can be wrong.

═══ 2026-09-21 REPAIR — round-7 independent review, finding FB-04 ═══════════════════════════════════════════════════
The `--without-arm` switch used to skip assertions only INSIDE `add()`, while the argument expressions had already
dereferenced `T['arms']['F4bp']`. So the demotion drill's "the remaining prose still verifies with the arm gone" step
was run against the SHIPPED table with the arm still in it; pointing this file at a table that genuinely lacks the arm
raised `KeyError: 'F4bp'`. "We can demote with one line" was an assertion about a path that had never executed.

Three changes, all shaped like the class and not like the name F4bp:
  1. `_Absent` — a removable arm that is really missing yields a sentinel that propagates through subscripting and
     arithmetic, so no call site has to be edited; `add()` turns any row that touches one into a COUNTED skip. An arm
     that is missing and NOT declared removable still raises, because that is a real defect.
  2. `--tables <path>` — the drill now points this checker at its OWN rebuilt no-arm table, which is the drill it
     claimed to be running.
  3. `--status <path>` (required) — arm standing is consumed from `FCF_ARM_STATUS`: this checker fails closed on an arm
     with no declared status, refuses to let a non-pre-registered arm's number be labelled a conclusion, and renders
     the tables through `fcf_render` to assert every marked arm's row carries its marker.
  `--doc <path>` additionally enforces the prose contract against the same status receipt.

usage: fcf_doc_check.py [--receipts DIR] [--tables FCF_TABLES.json] [--status FCF_ARM_STATUS.json]
                        [--without-arm ARM] [--doc RESULT.md] [--emit report.json]
"""
import importlib.util, json, os, re, sys

# --without-arm <ARM>: exercise the demotion path. Assertions ABOUT that arm are skipped (and COUNTED, so a skip that silently
# does nothing is visible in the verdict line); every other assertion must still pass. Used by fcf_demotion_drill.py.
# NOTE the boundary match: labels contain forms like 'F4bp-F0', which split() keeps as ONE token, so a token test silently
# skipped nothing the first time I wrote this. Non-alphanumeric boundaries also stop 'F4b' matching 'F4bp'.
def _opt(name, default=None):
    for _i, _a in enumerate(sys.argv):
        if _a == name and _i + 1 < len(sys.argv): return sys.argv[_i + 1]
    return default


WITHOUT = _opt('--without-arm')
R = _opt('--receipts', "/workspace/fallback_cf_2026-09-20/receipts")
TABLES = _opt('--tables', f"{R}/FCF_TABLES.json")
STATUS = _opt('--status', f"{R}/FCF_ARM_STATUS_2026-09-21.json")
DOCPATH = _opt('--doc')
EMIT = _opt('--emit')
DEVDIR = _opt('--devices', os.path.dirname(os.path.abspath(__file__)))
REMOVABLE = {WITHOUT} if WITHOUT else set()
SKIPPED = []


class _Absent:
    """An arm that is genuinely not in the input AND was declared removable. Propagates so that a call site written for
    a present arm keeps working; `add()` counts every row that touches one as a skip."""
    __slots__ = ("arm", "path")

    def __init__(self, arm, path=""): self.arm, self.path = arm, path
    def __getitem__(self, k): return _Absent(self.arm, f"{self.path}[{k!r}]")
    def get(self, k, default=None): return _Absent(self.arm, f"{self.path}.get({k!r})")
    def _op(self, *a, **k): return _Absent(self.arm, self.path + "<op>")
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = _op
    __truediv__ = __rtruediv__ = __floordiv__ = __neg__ = __abs__ = _op
    def __round__(self, n=None): return _Absent(self.arm, self.path + "<round>")
    def __repr__(self): return f"<ABSENT {self.arm}{self.path}>"
    def __eq__(self, o): return False
    def __ne__(self, o): return True
    def __hash__(self): return hash(("_Absent", self.arm))


def _armget(container, arm, where="?"):
    """The ONE way this file reaches an arm-keyed value. Missing + declared removable -> counted-skip sentinel;
    missing + NOT declared removable -> hard KeyError, because that is a real defect and must not be swallowed."""
    if isinstance(container, dict) and arm in container: return container[arm]
    if arm in REMOVABLE: return _Absent(arm, f"{where}[{arm!r}]")
    raise KeyError(f"{where}[{arm!r}]")


class _ArmMap(dict):
    """A receipt's arm-keyed mapping. Subscripting goes through _armget, so every existing `X['arms'][a]` call site
    inherits the behaviour without being edited."""

    def __init__(self, d, where): super().__init__(d); self._where = where
    def __getitem__(self, k): return _armget(dict(self), k, self._where)
    def get(self, k, default=None):
        try: return self[k]
        except KeyError: return default


def _run(runs, arm):
    """P/P2 receipts key their runs by a name that ENDS in 'arm <A>)'. Missing + removable -> sentinel."""
    hit = [k for k in runs if k.endswith(f"arm {arm})")]
    if hit: return runs[hit[0]]
    if arm in REMOVABLE: return _Absent(arm, f"runs[...arm {arm})]")
    raise KeyError(f"runs[...arm {arm})]")


def _absent_in(x):
    if isinstance(x, _Absent): return x
    if isinstance(x, (list, tuple)):
        for v in x:
            r = _absent_in(v)
            if r is not None: return r
    return None


T = json.load(open(TABLES))
W = json.load(open(f"{R}/FCF_RISK_WEIGHTS.json"))
P = json.load(open(f"{R}/FCF_P_READING.json"))
S = json.load(open(STATUS))
T["arms"] = _ArmMap(T["arms"], "T.arms"); T["paired_vs_F0"] = _ArmMap(T["paired_vs_F0"], "T.paired_vs_F0")
W["arms"] = _ArmMap(W["arms"], "W.arms")
FB = "fallback_subsample_HIST"
HI = "HIST_2023-06-30→2025-12-31 (the FINDING's window)"
RL = "R_level_2023-06-30→2026-08-31"
rows = []


# Standing rows (status./render./doc.) are about whether the demotion reached the consumers, NOT about the arm's
# numbers, so they run in EVERY mode — including the mode where the arm has been pulled. They are written to exist in
# both modes, which is what keeps `checked_without + skipped == checked_full` a real balance identity.
STANDING = ("status.", "render.", "doc.")


def add(label, got, doc):
    if (WITHOUT and not label.startswith(STANDING)
            and re.search(r'(?<![A-Za-z0-9])' + re.escape(WITHOUT) + r'(?![A-Za-z0-9])', label)):
        SKIPPED.append(label); return
    miss = _absent_in(got)
    if miss is not None:
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
# ---- AMENDMENT 3 \u00a74 condition 2, AFTER the round-7 FB-01 repair ----
# The withdrawn receipt (FCF_F4BP_VS_KC.json) is NOT read here: its A-check took both operands from one field of one
# file. What is re-read is the repaired device's receipt, and the rows below assert the REFUSAL, not a pass.
KCP = _opt('--kc', f"{R}/FCF_F4BP_VS_KC_2026-09-21.json")
KC = json.load(open(KCP))
kck = {c["check"].split(".")[0]: c for c in KC["checks"]}
B398 = ("residual_contains__FTRIM_earlier_in_H+chain_state_cold_start+seat_divergence_at_or_before_this_anchor"
        "+seat_unresolved_at_or_before_this_anchor")
ISO = "residual_contains__chain_state_cold_start"
cc = KC["C_residual_on_simulated_fallback_anchors"]
add("\u00a78.4c2 device verdict (the withdrawn device said PASS)", KC["VERDICT"], "REFUSED")
add("\u00a78.4c2 A0 the two sides never share a source field", kck["A0"]["ok"], True)
add("\u00a78.4c2 A1 anchors compared", kck["A1"]["detail"]["compared"], 10038)
add("\u00a78.4c2 A2 'byte-identical legz \u21d2 equal seat record' holds", kck["A2"]["ok"], False)
add("\u00a78.4c2 A3 seat records agree on every anchor", kck["A3"]["ok"], False)
add("\u00a78.4c2 n anchors where the seat records are REFUTED", kck["A3"]["detail"]["n_refuted"], 1)
add("\u00a78.4c2 the refuted anchor", kck["A3"]["detail"]["refuted_anchors"], ["2022-06-30T00:00:00Z"])
_wz = kck["A3"]["detail"]["worst_real_z_difference"]
add("\u00a78.4c2 real max|\u0394z| at that anchor", _wz["max_abs_dz"], 0.2535211267605634)
add("\u00a78.4c2 members at that anchor", _wz["members"], 137)
add("\u00a78.4c2 legz sha256, byte-identical on BOTH sides there", _wz["legz_sha256_both_sides"],
    "fc80ce64810baddc262ae6f8af8dc1bbc7e1ef5bfa854478696edcdc7d126f71")
add("\u00a78.4c2 archive masked seat there", _wz["archive_masked_seat"], [0.0, 0.0, 1.0])
add("\u00a78.4c2 F4b\u2032 masked seat there", _wz["candidate_masked_seat"], [0.5, 0.0, 0.5])
add("\u00a78.4c2 what the records can support", KC["A_z_equality"]["claim_available_from_these_records"],
    "BOUNDED, not bitwise")
add("\u00a78.4c2 n BOUNDED_NOT_BITWISE", KC["A_z_equality"]["BOUNDED_NOT_BITWISE"]["n"], 9865)
add("\u00a78.4c2 n UNRESOLVED_BY_THE_RECORDS (no measurement, not agreement)",
    KC["A_z_equality"]["UNRESOLVED_BY_THE_RECORDS"]["n"], 172)
add("\u00a78.4c2 anchors where FTRIM zeroed nothing AT THIS ANCHOR",
    kck["B"]["detail"]["anchors_where_FTRIM_zeroed_nothing_AT_THIS_ANCHOR"], 1963)
add("\u00a78.4c2 anchors where FTRIM had NEVER fired before",
    kck["B"]["detail"]["anchors_where_FTRIM_had_NEVER_fired_before"], 2)
add("\u00a78.4c2 first anchor FTRIM ever fired", kck["B"]["detail"]["first_anchor_FTRIM_ever_fired"],
    "2022-01-31T04:00:00Z")
add("\u00a78.4c2 an ISOLATED chain-state bucket exists", kck["C"]["ok"], False)
add("\u00a78.4c2 isolated chain-state bucket n (no measurement, not 0)", cc[ISO]["n"], 0)
add("\u00a78.4c2 the 398-anchor bucket, renamed to what is measured to be in it", cc[B398]["n"], 398)
add("\u00a78.4c2 that bucket's L1 median (the NUMBER did not move; its isolation claim was withdrawn)",
    round(cc[B398]["sum_abs_dw_L1"]["median"], 4), 0.0239)
add("\u00a78.4c2 chain-state-alone reading", KC["C_verdict"]["chain_state_alone"],
    "UNMEASURED \u2014 the isolated bucket is empty")
# The next two rows read off a NON-PRE-REGISTERED arm. They are labelled as such here so the re-reader cannot be
# quoted as reproducing a conclusion; `status.*` below asserts that standing from the status receipt.
add("\u00a70.3 F4bp SENSITIVITY: its \u0394g as a share of the F0\u2192F1 gap (NOT a rev24 estimate) (%)",
    round(100 * T["paired_vs_F0"]["F4bp"][FB4]["d_g"]["estimate"] / T["paired_vs_F0"]["F1"][FB4]["d_g"]["estimate"], 1), 16.1)
add("\u00a70.3 F4a / F4bp \u0394g ratio (both arms confounded; NOT '2.9\u00d7 overstatement of rev24') (x)",
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
add("\u00a78.5.2 A1' clause 3 ok IN THE FROZEN RECEIPT (the clause itself is WITHDRAWN: E-0921-E)", cl["A1p.3_"]["ok"], True)
d3 = cl["A1p.3_"]["detail"]
add("\u00a78.5.2 alpha read from the frozen config", d3["alpha"], 0.1)
add("\u00a78.5.2 n anchors to the full-recipe start", d3["n_anchors_between"], 2191)
add("\u00a78.5.2 decay bound AS THE FROZEN DEVICE COMPUTED IT (WITHDRAWN as a bound: E-0921-E)", d3["bound"], "5.563e-101")
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
    add(f"\u00a76 {_a} paths with pre-base flattens", _armget(_pre, _a, "SC._pre"), _n)
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
    _we = _run(_P2["runs"], _a)["bases"][_B]["never"]["W_ENTRY"]["summary"]["end_return_P2"]["measured"]
    add(f"\u00a76.2 never row is the W-ENTRY figure for {_a}", round(_we["mean"], 4), _v)
# ---- §2.1 control now also covers the sidecar (the gap the seed-claim correction exposed) ----
_C0 = json.load(open(f"{R}/FCF_CONTROL_F0.json"))
add("\u00a72.1 control verdict", _C0["VERDICT"], "PASS")
add("\u00a72.1 seeds bitwise equal", _C0["n_seeds_bitwise_equal"], 32)
add("\u00a76(a) sidecar flatten_log identical (why the seed match is NOT independent evidence)",
    _C0["n_sidecar_flatten_log_identical"], 32)
add("\u00a76(a) no substantive sidecar key differs",
    max(len(v["sidecar_substantive_keys_differing"]) for v in _C0["seeds"].values()), 0)
# ---- the entailment premise for §6(a): the reading parameters ARE the certified ones, so the seed match is a consequence ----
_MY = json.load(open("/workspace/fallback_cf_2026-09-20/RUN_CONFIG_P2reading_F_2026-09-20.json"))
_CE = json.load(open("/workspace/baseline_tables_2026-09-19/RUN_CONFIG_P2reading_A0_2026-09-20.json"))
for _k in ("p_reading", "p2_reading", "paths_R"):
    add(f"\u00a76(a) reading config `{_k}` byte-identical to the certified config",
        json.dumps(_MY.get(_k), sort_keys=True) == json.dumps(_CE.get(_k), sort_keys=True), True)
add("\u00a76(a) base anchors identical",
    [b["anchor"] for b in _MY["p_reading"]["bases"]], [b["anchor"] for b in _CE["p_reading"]["bases"]])
# ---- the sealed-initial-state question (§2.1): proved benign, not assumed ----
_SS = json.load(open(f"{R}/FCF_SEALED_STATE_PROBE.json"))
add("\u00a72.1 sealed-state probe verdict", _SS["VERDICT"], "PASS")
add("\u00a72.1 the two sealed shas really do differ",
    sum(1 for v in _SS["seeds"].values() if v["observed_differ"]), 32)
add("\u00a72.1 my sealed sha reproduced by flat-start + MY tag",
    sum(1 for v in _SS["seeds"].values() if v["mine_reproduced"]), 32)
add("\u00a72.1 certified sealed sha reproduced by the SAME object with ONLY the tag swapped",
    sum(1 for v in _SS["seeds"].values() if v["certified_reproduced"]), 32)
add("\u00a72.1 finding is reading (a) benign", _SS["finding"].startswith("(a) BENIGN"), True)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# ARM STANDING \u2014 round-7 FB-04. These rows are NOT about a number; they are about whether the demotion reached the
# consumers. Everything below is driven by the status receipt, so demoting a DIFFERENT arm tomorrow is enforced here
# without editing this file.
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
_arms_in_tables = sorted(dict(T["arms"]))
_undeclared = [a for a in _arms_in_tables if a not in S["arms"]]
add("status.every arm in the tables has a declared status (fail closed)", _undeclared, [])
add("status.F of record", S["F_of_record"], "F4a")
add("status.the live verdict on rev24", S["live_verdict"], "rev24 \u7684\u8d21\u732e\u672a\u77e5")
add("status.F_of_record carries a pre-registered verdict",
    S["arms"][S["F_of_record"]]["carries_a_preregistered_verdict"], True)
for _a in sorted(S["arms"]):
    _v = S["arms"][_a]
    add(f"status.{_a} preregistered/non_preregistered are negations", _v["preregistered"] == (not _v["non_preregistered"]), True)
    if _v["non_preregistered"]:
        add(f"status.{_a} is NOT allowed to carry a pre-registered verdict", _v["carries_a_preregistered_verdict"], False)
        add(f"status.{_a} carries a label and a short marker", bool(_v["label"] and _v["label_short"]), True)
add("status.the SET of arms declared non-pre-registered",
    sorted(a for a, v in S["arms"].items() if v["non_preregistered"]), ["F4bp"])
add("status.the SET of arms carrying a marker",
    sorted(a for a, v in S["arms"].items() if v.get("label_short")), ["F4a", "F4bp"])

# The renderer is a consumer: render the SAME tables through it and assert the markers actually came out.
_rend_path = os.path.join(DEVDIR, "fcf_render.py")
_spec = importlib.util.spec_from_file_location("fcf_render_under_check", _rend_path)
_rend = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_rend)
try:
    _txt = _rend.render(TABLES, f"{R}/FCF_RISK_WEIGHTS.json", STATUS)
    _rend_refused = None
except _rend.StatusMissing as _e:
    _txt = ""; _rend_refused = str(_e)
add("render.the renderer accepted these tables (no arm with an undeclared status)", _rend_refused, None)
add("render.rows that name a marked arm without its marker", len(_rend.unlabelled_rows(_txt, S)), 0)
_data_txt = _txt.split("### A ·", 1)[-1]          # exclude the standing note, which lists DECLARED arms, not table arms
for _a, _v in sorted(S["arms"].items()):
    if not _v.get("label_short"): continue
    _n_rows = sum(1 for l in _data_txt.splitlines() if l.startswith("| ") and l.split("|")[1].strip().split(" ")[0] == _a)
    # expected is derived, not hardcoded: an arm present in the tables must produce marked rows; a pulled arm must
    # produce none. The row therefore EXISTS in both modes, so the drill's balance identity stays a real identity.
    add(f"render.{_a} produces marked rows iff it is in the tables", _n_rows > 0, _a in _arms_in_tables)

# The prose is a consumer too. --doc enforces it against the same status receipt.
if DOCPATH:
    _doc = open(DOCPATH, encoding="utf-8").read()
    _lines = _doc.splitlines()
    _wm = S["withdrawn_marker"]
    for _a, _v in sorted(S["arms"].items()):
        if not _v["non_preregistered"]: continue
        add(f"doc.{_a} label appears in the prose", _v["label"] in _doc, True)
        _mark = _v["label_short"].lstrip("\u26a0 ")          # the marker's TEXT, without the warning glyph
        _names = [_a, "F4b\u2032"] if _a == "F4bp" else [_a]
        _claims = [l for l in _lines
                   if any(nm in l for nm in _names) and any(m in l for m in S["conclusion_markers"])
                   and _mark not in l and _wm not in l]
        add(f"doc.lines that make a CLAIM about {_a} without its marker or a withdrawal marker",
            _claims[:3], [])
    _ofrec = [l for l in _lines if "F4 of record" in l and _wm not in l
              and f"F4 of record = {S['F_of_record']}" not in l and f"F4 of record\u300d= {S['F_of_record']}" not in l
              and f"**{S['F_of_record']}**" not in l]
    add("doc.live 'F4 of record' lines that do not name the arm of record", _ofrec[:3], [])
    add("doc.the live verdict sentence is present", S["live_verdict"] in _doc, True)
    add("doc.every withdrawn clause kept its original bytes behind the marker",
        sum(1 for l in _lines if _wm in l) > 0, True)

    # A registered withdrawal is only real if the prose that still carries its number carries the marker too. This loop
    # is driven by the registry, not by a list of sentences: registering the NEXT withdrawal with its `tokens` is the
    # whole of the work, and a doc that repeats the number bare goes red here without anyone editing this file.
    for _w in S["withdrawn"]:
        for _tok in _w.get("tokens", []):
            _bare = [l for l in _lines if _tok in l and _wm not in l]
            add(f"doc.lines repeating the withdrawn token {_tok!r} with no withdrawal marker", _bare[:3], [])

bad = [r for r in rows if r[1] != r[2]]
for lab, got, doc in rows:
    print(("  OK   " if got == doc else "MISMATCH ") + f"{lab:52s} receipt={got!r:>12}  doc={doc!r}")
if EMIT:
    json.dump({"tables": TABLES, "status": STATUS, "doc": DOCPATH, "without_arm": WITHOUT,
               "checked_labels": sorted(l for l, _, _ in rows), "skipped_labels": sorted(SKIPPED),
               "n_checked": len(rows), "n_skipped": len(SKIPPED), "n_mismatching": len(bad),
               "mismatching": [[l, repr(g), repr(d)] for l, g, d in bad]},
              open(EMIT, "w"), ensure_ascii=False, indent=1)
print(f"\nFCF_DOC_CHECK VERDICT={'PASS' if not bad else 'MISMATCH'} checked={len(rows)} mismatching={len(bad)}"
      f" skipped={len(SKIPPED)} without_arm={WITHOUT} tables={TABLES} status={STATUS} doc={DOCPATH}")
raise SystemExit(0 if not bad else 3)
