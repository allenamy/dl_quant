#!/usr/bin/env python3
"""tests_equivalence_labels.py — FIXPROGRAM 2026-09-13 item K2 (FX-EVAL). Red-first tests for the shared equivalence-labelling module.

    python3 tests_equivalence_labels.py --impl legacy    # the CURRENT predicates, AST-extracted verbatim and pinned (k2_legacy_predicates.py)
    python3 tests_equivalence_labels.py --impl module    # equivalence_labels.py + the K2 re-label compositions (k2_rules.py)

Group X (both impls): synthetic inputs, one TRUTH category each. A misfire cell is one where the current predicate issues a claim the
interval does not support; its neighbours are cells where the current predicate is right. In legacy mode the harness also checks that
the set of failing cells equals the declared misfire set (EXPECTED_LEGACY_RED): the red must be the declared red, for the declared reason.
Group M (module only): the module contract (mandatory δ with unit / justification / source and no default; strict TOST boundaries;
interval validation; aggregation; loss sign; direction labels unchanged). Group P (module only): direction labels are identical to the
frozen judge_v4 rule on 2000 random cell pairs, and to the P2 A6.7 rule wherever its |Δg| < 0.23 branch is not taken.

Module contract the tests pin (written before the module exists):
  equivalence_labels: Margin(*, delta, unit, justification, source); Interval(*, point, lo, hi, level); LabelError;
    equivalence(ci, *, margin); one_sided(ci, *, margin, material_side, center=0.0); aggregate(readings); direction_v4(cells);
    v4_label(cells, *, margin); shared_loss_reading(*, deployed_means, replay_means, differences, margin); loss_label_admissible(label, means)
    constants EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE / WITHIN_MARGIN / BEYOND_MARGIN
  k2_rules: rule_t4, rule_t5c, rule_t5b, rule_t5_addendum, rule_t2_axis, rule_v4, rule_t1h1_cell, rule_t1_agg_h1, rule_t1h3_cell,
    rule_t1_agg_h3, rule_t1h5, rule_t8_reading, rule_l2_first_fail
Prints one line per check and a SUMMARY line; exit 0 only if every check passes.
"""
import os, sys, math, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FX = "/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EVAL"
sys.path.insert(0, FX); sys.path.insert(0, HERE)
IMPL = sys.argv[sys.argv.index("--impl") + 1] if "--impl" in sys.argv else None
assert IMPL in ("legacy", "module"), "usage: --impl legacy|module"

# ---------------------------------------------------------------------------------------------- categories (claim classes)
NO_DIFFERENCE = "NO_DIFFERENCE"            # a two-sided 'same / not material / indistinguishable / negligible' claim
BELOW_LINE = "BELOW_LINE"                  # a one-sided 'not material' claim (below a materiality line)
NO_EFFECT = "NO_EFFECT"                    # an absence claim ('does not explain', 'no drop', 'cannot predict', 'direction absent')
INCONCLUSIVE_C = "INCONCLUSIVE"            # nothing established
MATERIAL = "MATERIAL"                      # a material difference / effect established
EFFECT = "EFFECT"                          # a positive finding (explains, half-life, PASS, all gate conditions hold)
DIR_A, DIR_B = "DIRECTION_A", "DIRECTION_B"
SHARED_LOSS_SAME = "SHARED_LOSS_SAME"      # 'the strategy's own loss': both lost and the difference is established as immaterial
SHARED_LOSS_OPEN = "SHARED_LOSS_OPEN"      # both lost, difference not established either way
GAP = "GAP_DETECTED"                       # a deployment gap is detected
NOT_SHARED = "NOT_SHARED_LOSS"             # at least one book did not lose, no gap
ABSENT_STAT = "NOT_RELABELLABLE"           # the statistic is absent

LEGACY_CAT = {
    "NOT MATERIAL (at this resolution)": NO_DIFFERENCE, "MATERIAL": MATERIAL,
    "STRATEGY'S OWN LOSS (king chain)": SHARED_LOSS_SAME, "DEPLOYMENT DIFFERENCE": GAP, "SAME DIRECTION WITH A GAP": GAP, "UNDECIDABLE": INCONCLUSIVE_C,
    "NOT MATERIAL": BELOW_LINE, "FROZEN-RESIDUAL-MATERIAL": MATERIAL, "EXECUTOR-ADDED-FREEZE-MATERIAL": MATERIAL,
    "NEGLIGIBLE": NO_DIFFERENCE, "NOT NEGLIGIBLE": MATERIAL, "SMALL": "SMALL",
    "(C) indistinguishable (|Δg| < 0.23)": NO_DIFFERENCE, "(A)": DIR_A, "(B)": DIR_B, "(C) UNDECIDED": INCONCLUSIVE_C,
    "(A) PROMOTE": DIR_A, "(B) REJECT": DIR_B,
    "EXPLAINS": EFFECT, "DOES-NOT-EXPLAIN": NO_EFFECT, "UNDECIDED": INCONCLUSIVE_C,
    "SURVIVES": EFFECT, "FALSIFIED": NO_EFFECT, "NOT DECIDABLE": INCONCLUSIVE_C,
    "HALF-LIFE": EFFECT, "LEVEL": EFFECT, "NO-DROP": NO_EFFECT,
    "SURVIVES (different mechanisms)": EFFECT, "FALSIFIED (same mechanism)": NO_DIFFERENCE,
    "PASS": EFFECT, "FAIL": NO_EFFECT, "INVALID": "INVALID",
    "DIRECTION-ABSENT": NO_EFFECT, "UNSTABLE": NO_EFFECT, "NOT-BEYOND-FUNDING": NO_EFFECT, "VARIANCE": NO_EFFECT, "NULL": NO_EFFECT, "SHIFT": NO_EFFECT,
}
MODULE_CAT = {
    "NOT MATERIAL (equivalent within ±δ)": NO_DIFFERENCE, "MATERIAL (established beyond ±δ)": MATERIAL, "INCONCLUSIVE": INCONCLUSIVE_C,
    "SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ": SHARED_LOSS_SAME, "SHARED LOSS, DIFFERENCE INCONCLUSIVE": SHARED_LOSS_OPEN,
    "SHARED LOSS, MATERIAL DIFFERENCE": GAP,
    "NOT MATERIAL (established below line)": BELOW_LINE, "MATERIAL (established at or above line)": MATERIAL,
    "NOT RE-LABELLABLE (statistic absent)": ABSENT_STAT,
    "NEGLIGIBLE (established)": NO_DIFFERENCE, "NOT NEGLIGIBLE (established)": MATERIAL,
    "EQUIVALENT": NO_DIFFERENCE, "NOT EQUIVALENT": MATERIAL,
    "(A)": DIR_A, "(B)": DIR_B, "(C) EQUIVALENT": NO_DIFFERENCE, "(C) INCONCLUSIVE": INCONCLUSIVE_C, "(C) NOT EQUIVALENT": MATERIAL,
    "EXPLAINS": EFFECT, "DOES-NOT-EXPLAIN": NO_EFFECT, "UNDECIDED": INCONCLUSIVE_C,
    "SURVIVES": EFFECT, "FALSIFIED": NO_EFFECT, "NOT DECIDABLE": INCONCLUSIVE_C, "HALF-LIFE": EFFECT, "LEVEL": EFFECT, "NO-DROP": NO_EFFECT,
    "SURVIVES (different mechanisms)": EFFECT, "FALSIFIED (same mechanism)": NO_DIFFERENCE,
    "PASS": EFFECT, "UNDECIDED (T8)": INCONCLUSIVE_C, "FAIL (usefulness excluded: r < line in every cell)": NO_EFFECT,
    "FAIL: failed to detect; usefulness not excluded": INCONCLUSIVE_C,
}


def module_cat(label):
    if label.startswith("NOT A SHARED LOSS"): return GAP if "; gap detected" in label else NOT_SHARED
    if label.endswith("NOT ESTABLISHED (failed gate; no absence margin declared)"): return INCONCLUSIVE_C
    return MODULE_CAT[label]


# ---------------------------------------------------------------------------------------------- harness
RESULTS = []


def check(cid, fn):
    try:
        ok, detail = fn()
        RESULTS.append((cid, "PASS" if ok else "FAIL", detail))
    except Exception as e:     # a crash is never a valid red
        RESULTS.append((cid, "ERROR", "%s: %s | %s" % (type(e).__name__, e, traceback.format_exc().strip().split("\n")[-3][:200])))


def expect(cid, truth, legacy_fn, module_fn):
    def run():
        if IMPL == "legacy":
            label = legacy_fn(); cat = LEGACY_CAT.get(label, "UNMAPPED:" + str(label))
        else:
            label = module_fn(); cat = module_cat(label)
        return cat == truth, "impl=%s label=%r category=%s truth=%s" % (IMPL, label, cat, truth)
    check(cid, run)


if IMPL == "legacy":
    import k2_legacy_predicates as KL
    LEG = KL.Legacy()
else:
    import equivalence_labels as EL
    import k2_rules as KR


def M(delta, unit="bps / 4h anchor / unit gross", why="synthetic test margin standing in for a declared economic band", src="tests_equivalence_labels.py"):
    return EL.Margin(delta=delta, unit=unit, justification=why, source=src)


LEVEL = 0.95


# ---------------------------------------------------------------------------------------------- X01 T4 materiality
def t4_book(cells, ic):
    BOOK = {}
    for arm in ("K1_minus_K0|C0", "K1_minus_K0|NW", "K0f_minus_K0|C0"):
        for s, (dg, lo, hi) in zip(("42", "2027"), cells):
            BOOK["%s|s%s" % (arm, s)] = {"KING_LIVE": dict(dg=dg, ci95=[lo, hi], ci95_excl0=bool(lo > 0 or hi < 0))}
    icd = dict(mean=ic[0], ci95=[ic[1], ic[2]], ci95_excl0=bool(ic[1] > 0 or ic[2] < 0))
    SCORE = {"KING_LIVE": {"dIC_K1_minus_K0": icd, "dIC_K0f_minus_K0": dict(icd)}}
    return BOOK, SCORE


def x01(cid, truth, cells, ic, d_book=0.02, d_ic=0.003):
    expect(cid, truth, lambda: LEG.t4_verdict(*t4_book(cells, ic)),
           lambda: KR.rule_t4({s: c for s, c in zip(("42", "2027"), cells)}, ic, book_margin=M(d_book), ic_margin=M(d_ic, unit="rank-IC"), level=LEVEL)["label"])


x01("X01_T4_wide_CI_straddling_zero__MISFIRE", INCONCLUSIVE_C, [(0.018, -0.030, 0.063), (0.016, -0.033, 0.065)], (-0.0001, -0.0003, 0.0001))
x01("X01n1_T4_tight_inside_band", NO_DIFFERENCE, [(0.001, -0.010, 0.012), (0.000, -0.011, 0.010)], (0.0, -0.001, 0.001))
x01("X01n2_T4_large_significant", MATERIAL, [(0.30, 0.20, 0.40), (0.28, 0.18, 0.38)], (0.0, -0.001, 0.001))
x01("X01n3_T4_significant_but_negligible__CONVERSE_MISFIRE", NO_DIFFERENCE, [(0.010, 0.004, 0.016), (0.011, 0.005, 0.017)], (0.0, -0.001, 0.001))
x01("X01n4_T4_seeds_disagree__MISFIRE", INCONCLUSIVE_C, [(0.20, 0.10, 0.30), (0.000, -0.010, 0.010)], (0.0, -0.001, 0.001))
x01("X01n5_T4_book_tight_IC_beyond_band", MATERIAL, [(0.001, -0.010, 0.012), (0.000, -0.011, 0.010)], (0.006, 0.004, 0.008))   # added at C3 (neighbour)


# ---------------------------------------------------------------------------------------------- X02 T5c shared loss
DAYS61 = np.repeat(np.arange(11), [6, 6, 6, 5, 6, 6, 5, 6, 5, 5, 5])
RNG = np.random.default_rng(20260913)
BASE = RNG.uniform(0, 1, 61)


def x02(cid, truth, dk, rk, kind="return"):
    def mod():
        r = LEG_T5C_NUMBERS(dk, rk)
        return KR.rule_t5c(r["D_K"], r["R_K"], r["diff_D_minus_R"], margin=M(0.05), level=LEVEL, kind=kind)["label"]
    expect(cid, truth, lambda: LEG.t5c_readings(dk, rk, DAYS61)["label"], mod)


def LEG_T5C_NUMBERS(dk, rk):
    """the stored numbers a receipt would hold (point, lo, hi); computed with the device's own boot so both impls see the same intervals"""
    import k2_legacy_predicates as KL2
    return KL2.Legacy().t5c_readings(dk, rk, DAYS61)


x02("X02_T5c_both_profitable_identical__MISFIRE", NOT_SHARED, 10 + 10 * BASE, 10 + 10 * BASE)
x02("X02n1_T5c_both_lose_identical", SHARED_LOSS_SAME, -10 - 10 * BASE, -10 - 10 * BASE)
x02("X02n2_T5c_both_lose_noisy_difference__MISFIRE", SHARED_LOSS_OPEN, -10 + 15 * RNG.standard_normal(61), -9 + 15 * RNG.standard_normal(61))
x02("X02n3_T5c_deployed_lost_replay_won_gap", GAP, -15 - 5 * BASE, 15 + 5 * BASE)
x02("X02n4_T5c_replay_lost_deployed_won_gap", GAP, 15 + 5 * BASE, -15 - 5 * BASE)   # added at C3 (neighbour)


# ---------------------------------------------------------------------------------------------- X03/X04 T5b one-sided line
def series_with_mean(m, n=60):
    z = RNG.standard_normal(n); z = z - z.mean(); return m + 0.2 * z


def x03(cid, truth, mean, lo, hi):
    expect(cid, truth, lambda: LEG.t5b_q1_reading(series_with_mean(mean)), lambda: KR.rule_t5b(mean, (lo, hi), margin=M(0.05), level=LEVEL))


x03("X03_T5b_point_below_line_CI_crosses__MISFIRE", INCONCLUSIVE_C, 0.03, -0.05, 0.11)
x03("X03n1_T5b_clearly_material", MATERIAL, 0.12, 0.08, 0.16)
x03("X03n2_T5b_clearly_below_line", BELOW_LINE, -0.12, -0.245, -0.021)
x03("X03n3_T5b_near_zero_tight", BELOW_LINE, 0.0, -0.01, 0.01)


def x04(cid, truth, mean, ci):
    expect(cid, truth, lambda: LEG.t5b_exec_reading(mean), lambda: KR.rule_t5b(mean, ci, margin=M(0.05), level=LEVEL))


x04("X04_T5b_exec_statistic_absent__MISFIRE", ABSENT_STAT, None, None)
x04("X04n1_T5b_exec_material", MATERIAL, 0.2, (0.1, 0.3))
x04("X04n2_T5b_exec_below", BELOW_LINE, 0.01, (-0.02, 0.03))
x04("X04n3_T5b_exec_wide__MISFIRE", INCONCLUSIVE_C, 0.04, (-0.2, 0.3))
x04("X04n4_T5b_exec_lower_end_on_the_line_is_material", MATERIAL, 0.08, (0.05, 0.11))   # added at C3 (neighbour, boundary lo == line)


# ---------------------------------------------------------------------------------------------- X05 T5 addendum share
def x05(cid, truth, cells):
    expect(cid, truth, lambda: LEG.t5_addendum_reading(cells[0][0]), lambda: KR.rule_t5_addendum(cells, margin=M(0.05, unit="share of gap"), not_negligible_line=0.20, level=LEVEL))


x05("X05_T5add_point_negligible_CI_wide__MISFIRE", INCONCLUSIVE_C, [(0.01, -0.15, 0.17)])
x05("X05n1_T5add_negligible_tight", NO_DIFFERENCE, [(0.005, -0.009, 0.006)])
x05("X05n2_T5add_not_negligible", MATERIAL, [(0.5, 0.3, 0.7)])
x05("X05n3_T5add_not_negligible_negative", MATERIAL, [(-0.3, -0.5, -0.25)])


# ---------------------------------------------------------------------------------------------- X06 T2 BELOW-RESOLUTION flag
def t2_rb(cells):
    RB = {}
    for s, (dg, lo, hi) in zip(("42", "2027"), cells):
        blk = dict(dg=dg, ci95=[lo, hi], ci99K=[lo - 0.05, hi + 0.05], dtau_pct=0.0, dcarry=0.0)
        blk["below_resolution"] = LEG.t2_below_resolution(dg) if IMPL == "legacy" else None
        RB[s] = dict(W_ALPHA=blk, tail_arm=dict(maxdd=-0.10, halt=0), tail_base=dict(maxdd=-0.10, halt=0))
    return RB


def x06(cid, truth_claims_no_difference, cells):
    def run():
        if IMPL == "legacy":
            d = LEG.t2_decide(t2_rb(cells), True, "not_fired"); claims = "BELOW-RESOLUTION" in d["flags"]; label = "%s %s" % (d["verdict"], d["flags"])
        else:
            label = KR.rule_t2_axis(cells, margin=M(0.05), level=LEVEL); claims = module_cat(label) == NO_DIFFERENCE
        return claims == truth_claims_no_difference, "impl=%s label=%r claims_no_difference=%s truth=%s" % (IMPL, label, claims, truth_claims_no_difference)
    check(cid, run)


x06("X06_T2_below_resolution_wide_CI__MISFIRE", False, [(-0.10, -0.40, 0.20), (-0.08, -0.38, 0.22)])
x06("X06n1_T2_promote_like", False, [(0.5, 0.3, 0.7), (0.45, 0.25, 0.65)])
x06("X06n2_T2_tight_inside_band", True, [(0.01, -0.02, 0.03), (0.0, -0.03, 0.03)])
x06("X06n3_T2_reject_like", False, [(-0.30, -0.45, -0.15), (-0.32, -0.47, -0.17)])


# ---------------------------------------------------------------------------------------------- X07 P2 A6.7 precedence
def x07(cid, truth, cells):
    pc = {s: dict(dg=c[0], ci95_k0=[c[1], c[2]]) for s, c in zip(("42", "2027"), cells)}
    expect(cid, truth, lambda: LEG.p2_verdict(pc, 0), lambda: KR.rule_v4(cells, margin=M(0.05), level=LEVEL))


x07("X07_P2_significant_positive_below_0p23__MISFIRE", DIR_A, [(0.20, 0.10, 0.30), (0.19, 0.09, 0.29)])
x07("X07b_P2_wide_CI_small_point__MISFIRE", INCONCLUSIVE_C, [(0.02, -0.20, 0.24), (0.03, -0.19, 0.25)])
x07("X07n1_P2_clear_A", DIR_A, [(0.5, 0.3, 0.7), (0.5, 0.3, 0.7)])
x07("X07n2_P2_clear_B", DIR_B, [(-0.5, -0.7, -0.3), (-0.5, -0.7, -0.3)])
x07("X07n3_P2_undecided_large_point", INCONCLUSIVE_C, [(0.3, -0.1, 0.7), (0.3, -0.1, 0.7)])
x07("X07n4_P2_tight_inside_band", NO_DIFFERENCE, [(0.01, -0.02, 0.03), (0.0, -0.03, 0.03)])


# ---------------------------------------------------------------------------------------------- X08 T1 H1
def s_(point, lo, hi): return dict(point=point, vci_lo=lo, vci_hi=hi, ci95_lo=lo, ci95_hi=hi)


def x08(cid, truth, D, MIX):
    ratio = MIX[0] / D[0] if D[0] != 0 else float("nan")
    expect(cid, truth, lambda: LEG.t1_h1_cell(s_(*D), s_(*MIX), ratio), lambda: KR.rule_t1h1_cell(D, MIX, fraction=0.25, level=LEVEL))


x08("X08_T1H1_mix_CI_contains_zero__MISFIRE", INCONCLUSIVE_C, (-3.0, -5.0, -1.0), (-1.2, -2.9, 0.4))
x08("X08n1_T1H1_explains", EFFECT, (-3.0, -5.0, -1.0), (-2.5, -3.5, -1.5))
x08("X08n2_T1H1_does_not_explain_tight", NO_EFFECT, (-3.5, -5.0, -2.0), (0.01, -0.2, 0.3))
x08("X08n3_T1H1_drop_not_significant", INCONCLUSIVE_C, (-0.2, -0.5, 1.0), (-0.1, -0.3, 0.1))


def x08agg(cid, truth, D, MIX):
    cells = {(s, T): (D, MIX) for s in ("DISP24", "BREADTH72") for T in ("T_A", "T_L")}
    def leg():
        cv = {k: LEG.t1_h1_cell(s_(*v[0]), s_(*v[1]), v[1][0] / v[0][0]) for k, v in cells.items()}
        return LEG.t1_h1_agg(cv)
    def mod():
        return KR.rule_t1_agg_h1([KR.rule_t1h1_cell(v[0], v[1], fraction=0.25, level=LEVEL) for v in cells.values()])
    expect(cid, truth, leg, mod)


x08agg("X08agg_T1H1_FALSIFIED_from_CIs_containing_zero__MISFIRE", INCONCLUSIVE_C, (-3.0, -5.0, -1.0), (-1.2, -2.9, 0.4))
x08agg("X08aggn1_T1H1_FALSIFIED_tight", NO_EFFECT, (-3.5, -5.0, -2.0), (0.01, -0.2, 0.3))


# ---------------------------------------------------------------------------------------------- X09 T1 H3
def h3cell(dE0, dE1, E0H, E1H, E0T, E1T):
    return dict(dE0=s_(*dE0), dE1=s_(*dE1), E0H=E0H, E1H=E1H, E0T=E0T, E1T=E1T)


def x09(cid, truth, cell):
    expect(cid, truth, lambda: LEG.t1_h3([h3cell(*cell), h3cell(*cell)])[1],
           lambda: KR.rule_t1_agg_h3([KR.rule_t1h3_cell(*cell, fraction=0.25, level=LEVEL)] * 2))


x09("X09_T1H3_no_drop_from_point__MISFIRE", INCONCLUSIVE_C, ((0.0, -10.0, 10.0), (-20.0, -100.0, 60.0), 50.0, 100.0, 50.0, 80.0))
x09("X09n1_T1H3_half_life", EFFECT, ((0.0, -10.0, 10.0), (-12.0, -20.0, -5.0), 50.0, 100.0, 45.0, 88.0))
x09("X09n2_T1H3_no_drop_tight", NO_EFFECT, ((0.0, -10.0, 10.0), (-5.0, -15.0, 5.0), 50.0, 100.0, 50.0, 95.0))
x09("X09n3_T1H3_level_is_a_CI_established_falsification", NO_EFFECT, ((-20.0, -30.0, -10.0), (-40.0, -60.0, -20.0), 50.0, 100.0, 30.0, 60.0))


# ---------------------------------------------------------------------------------------------- X10 T1 H5
def x10(cid, truth, c1d, six, pi23, ss23):
    names = ("dpD", "dsD", "dpR", "dsR", "dpRs", "dsRs")
    def leg():
        return LEG.t1_h5(c1d, *[s_(*six[n]) for n in names], pi23[0], ss23[0])
    def mod():
        return KR.rule_t1h5(c1d, {n: six[n] for n in names}, pi23, ss23, fraction=0.25, level=LEVEL)
    expect(cid, truth, leg, mod)


WIDE6 = dict(dpD=(0.05, -0.9, 1.0), dsD=(0.1, -1.5, 1.7), dpR=(0.04, -1.0, 1.1), dsR=(0.08, -1.4, 1.6), dpRs=(0.05, -1.1, 1.2), dsRs=(0.1, -1.6, 1.8))
TIGHT6 = dict(dpD=(0.01, -0.05, 0.06), dsD=(0.02, -0.1, 0.12), dpR=(0.0, -0.06, 0.05), dsR=(0.01, -0.11, 0.1), dpRs=(0.01, -0.07, 0.08), dsRs=(0.02, -0.12, 0.13))
SIG6 = dict(dpD=(0.9, 0.5, 1.3), dsD=(0.1, -1.5, 1.7), dpR=(0.8, 0.4, 1.2), dsR=(0.08, -1.4, 1.6), dpRs=(0.85, 0.45, 1.25), dsRs=(0.1, -1.6, 1.8))
x10("X10_T1H5_same_mechanism_from_wide_CIs__MISFIRE", INCONCLUSIVE_C, 0.10, WIDE6, (1.0, 0.6, 1.4), (2.0, 1.5, 2.5))
x10("X10n1_T1H5_same_mechanism_tight", NO_DIFFERENCE, 0.10, TIGHT6, (1.0, 0.6, 1.4), (2.0, 1.5, 2.5))
x10("X10n2_T1H5_different_mechanisms", EFFECT, 0.60, SIG6, (1.0, 0.6, 1.4), (2.0, 1.5, 2.5))
x10("X10n3_T1H5_share_difference_middling", INCONCLUSIVE_C, 0.35, TIGHT6, (1.0, 0.6, 1.4), (2.0, 1.5, 2.5))


# ---------------------------------------------------------------------------------------------- X11 T8
def t8_FR(r, k0, k9, folds_pos=5, spec0_best=True, price=(0.0, -0.01, 0.01)):
    cells = {}
    for m in ("R", "L"):
        for t in ("NET", "LONG", "SHORT", "CARRY"):
            for s in ("42", "2027"):
                rr, kk0, kk9 = (0.6, (0.5, 0.7), (0.5, 0.7)) if t == "CARRY" else (r, k0, k9)
                spec = {"0": {"r": rr if spec0_best else rr - 0.02}, "1": {"r": rr - 0.01 if spec0_best else rr}, "2": {"r": rr - 0.02}, "3": {"r": rr - 0.03}}
                cells["%s_%s_s%s" % (m, t, s)] = dict(model=m, target=t, seed=s, pool=dict(r=rr, ci95_k0=list(kk0), ci95_k9=list(kk9)),
                                                      folds=[dict(r=(0.01 if q < folds_pos else -0.01)) for q in range(5)], spectrum=spec,
                                                      C4_price=dict(r=price[0], ci95_k0=[price[1], price[2]], ci95_k9=[price[1], price[2]]),
                                                      decomp=dict(share_S=0.2, r_e=0.0, r_e_ci95_k0=[-0.01, 0.01], r_e_ci95_k9=[-0.01, 0.01]))
    return dict(cells=cells)


T8_M = np.linspace(0.0, 0.0316, 500)
T8_NULL = {"%s_%s" % (m, t): T8_M.copy() for m in ("R", "L") for t in ("NET", "LONG", "SHORT")}


def x11(cid, truth, **kw):
    FR = t8_FR(**kw)
    def leg():
        return LEG.t8(FR, T8_M, T8_NULL, dict(ALL_PASS=True))[0]
    def mod():   # the T8 verdict itself is unchanged by K2: it is taken from the frozen predicate, only its reading is re-labelled
        import k2_legacy_predicates as KL2
        verdict = KL2.Legacy().t8(FR, T8_M, T8_NULL, dict(ALL_PASS=True))[0]
        cells = {k: dict(point=v["pool"]["r"], ci_k0=tuple(v["pool"]["ci95_k0"]), ci_k9=tuple(v["pool"]["ci95_k9"])) for k, v in FR["cells"].items() if v["target"] != "CARRY"}
        return KR.rule_t8_reading(verdict, cells, margin=M(0.03, unit="pooled OOS Pearson r"), level=LEVEL)
    expect(cid, truth, leg, mod)


x11("X11_T8_FAIL_usefulness_not_excluded__MISFIRE", INCONCLUSIVE_C, r=0.02, k0=(-0.01, 0.05), k9=(-0.012, 0.052))
x11("X11n1_T8_FAIL_usefulness_excluded", NO_EFFECT, r=0.0, k0=(-0.02, 0.02), k9=(-0.021, 0.021))
x11("X11n2_T8_PASS", EFFECT, r=0.06, k0=(0.04, 0.08), k9=(0.039, 0.081), price=(0.05, 0.03, 0.07))
x11("X11n3_T8_UNDECIDED_spectrum_peak_not_zero", INCONCLUSIVE_C, r=0.06, k0=(0.04, 0.08), k9=(0.039, 0.081), price=(0.05, 0.03, 0.07), spec0_best=False)


# ---------------------------------------------------------------------------------------------- X12 L2 absence labels
def l2_cell(G, Gci, years, dG, dGci, TBci=(-0.3, -0.1), Hci=(-0.1, 0.2), Gmed=-0.2, z=-3.0, q05=-2.0, shift=True):
    return dict(G=G, G_ci=list(Gci), G_years={str(y): years for y in (2023, 2024, 2025, 2026)}, dG=dG, dG_ci=list(dGci), TB_ci=list(TBci), H_ci=list(Hci), G_med=Gmed, z=z, q05=q05, shift_peak_forward_is_0=shift)


def x12(cid, truth, cell):
    def leg():
        conds, first = LEG.l2_reading(cell); return "PASS" if first is None else first
    def mod():
        conds, first = LEG_L2_CONDS(cell)
        lab = KR.rule_l2_first_fail(conds, first); return "PASS" if lab is None else lab
    expect(cid, truth, leg, mod)


def LEG_L2_CONDS(cell):
    import k2_legacy_predicates as KL2
    return KL2.Legacy().l2_reading(cell)     # the gate conditions themselves are unchanged; only the wording of a failure is re-labelled


x12("X12_L2_direction_absent_from_CI_upper_just_above_zero__MISFIRE", INCONCLUSIVE_C, l2_cell(-0.4, (-0.9, 0.05), -0.3, -0.2, (-0.4, -0.05)))
x12("X12b_L2_not_beyond_funding_from_CI_containing_zero__MISFIRE", INCONCLUSIVE_C, l2_cell(-0.4, (-0.7, -0.1), -0.3, -0.05, (-0.3, 0.2)))
x12("X12n1_L2_all_conditions_hold", EFFECT, l2_cell(-0.4, (-0.7, -0.1), -0.3, -0.2, (-0.4, -0.05)))
x12("X12n2_L2_boundary_z_equal_q05_holds", EFFECT, l2_cell(-0.4, (-0.7, -0.1), -0.3, -0.2, (-0.4, -0.05), z=-2.0, q05=-2.0))   # added at C3 (neighbour)
x12("X12n3_L2_boundary_G_upper_just_below_zero_holds", EFFECT, l2_cell(-0.4, (-0.7, -1e-9), -0.3, -0.2, (-0.4, -1e-9)))   # added at C3 (neighbour)


# ---------------------------------------------------------------------------------------------- X13 judge_v4 device label (honest) on a wide CI
def x13(cid, truth, cells):
    r = [dict(delta=c[0], ci95=[c[1], c[2]]) for c in cells]
    expect(cid, truth, lambda: LEG.v4_verdict(r), lambda: KR.rule_v4(cells, margin=M(0.05), level=LEVEL))


x13("X13_v4_C_on_wide_CI_device_is_honest", INCONCLUSIVE_C, [(0.05, -0.20, 0.30), (0.04, -0.21, 0.29)])
x13("X13n1_v4_A", DIR_A, [(0.3, 0.1, 0.5), (0.3, 0.1, 0.5)])
x13("X13n2_v4_B", DIR_B, [(-0.3, -0.5, -0.1), (-0.3, -0.5, -0.1)])
x13("X13n3_v4_one_seed_significant_other_wide", INCONCLUSIVE_C, [(0.3, 0.1, 0.5), (0.1, -0.3, 0.5)])   # added at C3 (neighbour)

EXPECTED_LEGACY_RED = {
    "X01_T4_wide_CI_straddling_zero__MISFIRE", "X01n3_T4_significant_but_negligible__CONVERSE_MISFIRE", "X01n4_T4_seeds_disagree__MISFIRE",
    "X02_T5c_both_profitable_identical__MISFIRE", "X02n2_T5c_both_lose_noisy_difference__MISFIRE",
    "X03_T5b_point_below_line_CI_crosses__MISFIRE", "X04_T5b_exec_statistic_absent__MISFIRE", "X04n3_T5b_exec_wide__MISFIRE",
    "X05_T5add_point_negligible_CI_wide__MISFIRE", "X06_T2_below_resolution_wide_CI__MISFIRE",
    "X07_P2_significant_positive_below_0p23__MISFIRE", "X07b_P2_wide_CI_small_point__MISFIRE",
    "X08_T1H1_mix_CI_contains_zero__MISFIRE", "X08agg_T1H1_FALSIFIED_from_CIs_containing_zero__MISFIRE",
    "X09_T1H3_no_drop_from_point__MISFIRE", "X10_T1H5_same_mechanism_from_wide_CIs__MISFIRE",
    "X11_T8_FAIL_usefulness_not_excluded__MISFIRE",
    "X12_L2_direction_absent_from_CI_upper_just_above_zero__MISFIRE", "X12b_L2_not_beyond_funding_from_CI_containing_zero__MISFIRE",
}


# ---------------------------------------------------------------------------------------------- Group M: module contract
if IMPL == "module":
    def raises(exc, f):
        try: f()
        except exc: return True
        except Exception: return False
        return False

    good = dict(delta=0.05, unit="bps / 4h anchor / unit gross", justification="declared economic band for the unit test contract", source="tests")
    check("M01_margin_has_no_defaults", lambda: (raises(TypeError, lambda: EL.Margin()) and raises(TypeError, lambda: EL.Margin(delta=0.05))
                                                  and raises(TypeError, lambda: EL.Margin(delta=0.05, unit="u", justification="j" * 30)), "TypeError without delta/unit/justification/source"))
    check("M02_margin_rejects_bad_values", lambda: (all(raises(EL.LabelError, lambda kv=kv: EL.Margin(**dict(good, **kv))) for kv in
                                                         (dict(delta=0.0), dict(delta=-0.05), dict(delta=float("nan")), dict(delta=float("inf")), dict(unit=""), dict(unit="   "),
                                                          dict(justification=""), dict(justification="too short"), dict(source=""))), "delta<=0/NaN/inf, blank unit/justification/source, justification < 20 chars"))
    check("M03_interval_validation", lambda: (raises(TypeError, lambda: EL.Interval(point=0.0, lo=-1.0, hi=1.0))
                                               and all(raises(EL.LabelError, lambda kv=kv: EL.Interval(**dict(dict(point=0.0, lo=-1.0, hi=1.0, level=0.95), **kv))) for kv in
                                                       (dict(lo=float("nan")), dict(hi=float("inf")), dict(point=float("nan")), dict(lo=2.0), dict(level=1.0), dict(level=0.0))), "level mandatory; NaN/inf/lo>hi/level outside (0,1) rejected"))
    mg = EL.Margin(**good)
    iv = lambda lo, hi: EL.Interval(point=(lo + hi) / 2, lo=lo, hi=hi, level=0.95)
    check("M04_strict_boundaries", lambda: ((EL.equivalence(iv(-0.05, 0.01), margin=mg)["label"], EL.equivalence(iv(-0.01, 0.05), margin=mg)["label"],
                                             EL.equivalence(iv(-0.0499, 0.0499), margin=mg)["label"], EL.equivalence(iv(0.05, 0.2), margin=mg)["label"],
                                             EL.equivalence(iv(-0.2, -0.05), margin=mg)["label"], EL.equivalence(iv(0.0499, 0.2), margin=mg)["label"])
                                            == (EL.INCONCLUSIVE, EL.INCONCLUSIVE, EL.EQUIVALENT, EL.NOT_EQUIVALENT, EL.NOT_EQUIVALENT, EL.INCONCLUSIVE), "lo=-δ or hi=δ: INCONCLUSIVE; strictly inside: EQUIVALENT; lo>=δ or hi<=-δ: NOT EQUIVALENT"))
    check("M05_reading_carries_margin_and_alpha", lambda: (lambda r: (math.isclose(r["alpha_per_side"], 0.025) and r["delta"] == 0.05 and r["unit"] == good["unit"]
                                                                       and r["justification"] == good["justification"] and r["source"] == "tests", str({k: r[k] for k in ("alpha_per_side", "delta", "unit")})))(EL.equivalence(iv(-0.01, 0.01), margin=mg)))
    check("M06_one_sided", lambda: ((EL.one_sided(iv(-0.1, 0.049), margin=mg, material_side="upper")["label"], EL.one_sided(iv(0.05, 0.1), margin=mg, material_side="upper")["label"],
                                     EL.one_sided(iv(0.0, 0.05), margin=mg, material_side="upper")["label"], EL.one_sided(iv(-0.049, 0.3), margin=mg, material_side="lower")["label"],
                                     EL.one_sided(iv(-0.3, -0.05), margin=mg, material_side="lower")["label"], EL.one_sided(iv(0.96, 1.2), margin=mg, material_side="lower", center=1.0)["label"])
                                    == (EL.WITHIN_MARGIN, EL.BEYOND_MARGIN, EL.INCONCLUSIVE, EL.WITHIN_MARGIN, EL.BEYOND_MARGIN, EL.WITHIN_MARGIN)
                                    and raises(EL.LabelError, lambda: EL.one_sided(iv(0, 1), margin=mg, material_side="both")), "upper: hi<L within, lo>=L beyond; lower mirrors; center shifts; bad side rejected"))
    check("M07_aggregate", lambda: ((EL.aggregate([EL.equivalence(iv(-0.01, 0.01), margin=mg)] * 2)["label"], EL.aggregate([EL.equivalence(iv(0.1, 0.2), margin=mg)] * 2)["label"],
                                     EL.aggregate([EL.equivalence(iv(0.1, 0.2), margin=mg), EL.equivalence(iv(-0.01, 0.01), margin=mg)])["label"],
                                     EL.aggregate([EL.equivalence(iv(0.1, 0.2), margin=mg), EL.equivalence(iv(-0.01, 0.01), margin=mg)])["seed_conflict"])
                                    == (EL.EQUIVALENT, EL.NOT_EQUIVALENT, EL.INCONCLUSIVE, True) and raises(EL.LabelError, lambda: EL.aggregate([])), "all-same kept; mixed extremes INCONCLUSIVE + seed_conflict; empty rejected"))
    check("M08_v4_label_direction_unchanged_and_C_split", lambda: ((EL.v4_label([iv(0.01, 0.04)] * 2, margin=mg)["label"], EL.v4_label([iv(0.01, 0.04)] * 2, margin=mg)["equivalence"],
                                                                     EL.v4_label([iv(-0.3, -0.1)] * 2, margin=mg)["label"], EL.v4_label([iv(-0.01, 0.02)] * 2, margin=mg)["label"],
                                                                     EL.v4_label([iv(-0.2, 0.3)] * 2, margin=mg)["label"], EL.v4_label([iv(0.1, 0.3), iv(-0.3, -0.1)], margin=mg)["label"])
                                                                    == ("(A)", EL.EQUIVALENT, "(B)", "(C) EQUIVALENT", "(C) INCONCLUSIVE", "(C) NOT EQUIVALENT"), "(A) stays (A) even when EQUIVALENT; (C) split three ways"))
    check("M09_loss_requires_negative_realised_means", lambda: ((EL.shared_loss_reading(deployed_means=[0.0], replay_means=[-1.0], differences=[iv(-0.01, 0.01)], margin=mg)["label"].startswith("NOT A SHARED LOSS"),
                                                                  EL.shared_loss_reading(deployed_means=[-1.0], replay_means=[-1.0], differences=[iv(-0.01, 0.01)], margin=mg)["label"],
                                                                  raises(EL.LabelError, lambda: EL.shared_loss_reading(deployed_means=[float("nan")], replay_means=[-1.0], differences=[iv(-0.01, 0.01)], margin=mg)))
                                                                 == (True, "SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ", True), "mean 0 is not a loss; NaN rejected"))
    check("M10_loss_label_guard", lambda: ((EL.loss_label_admissible("STRATEGY'S OWN LOSS (king chain)", [10.0, 12.0]), EL.loss_label_admissible("STRATEGY'S OWN LOSS (king chain)", [-1.0, -2.0]),
                                            EL.loss_label_admissible("NOT A SHARED LOSS (neither lost)", [1.0, 2.0]), EL.loss_label_admissible("DEPLOYMENT DIFFERENCE", [1.0]))
                                           == (False, True, True, True), "a LOSS label with a non-negative mean is inadmissible"))
    check("M11_no_point_only_api", lambda: (raises(TypeError, lambda: EL.equivalence(0.01, margin=mg)) and raises(TypeError, lambda: EL.equivalence((0.0, 0.01), margin=mg))
                                            and raises(TypeError, lambda: EL.equivalence(iv(-0.01, 0.01))), "floats / tuples / missing margin rejected"))

    # added at C3 (after the first green run; the checks above are unchanged — see k2_ast_retention_check.py)
    check("M12_aggregate_rejects_mixing_two_sided_and_one_sided", lambda: (raises(EL.LabelError, lambda: EL.aggregate([EL.equivalence(iv(-0.01, 0.01), margin=mg), EL.one_sided(iv(-0.01, 0.01), margin=mg, material_side="upper")])), "mixed kinds rejected"))
    check("M13_one_sided_seed_conflict", lambda: ((lambda a: (a["label"], a["seed_conflict"]))(EL.aggregate([EL.one_sided(iv(-0.1, 0.0), margin=mg, material_side="upper"), EL.one_sided(iv(0.1, 0.2), margin=mg, material_side="upper")])) == (EL.INCONCLUSIVE, True), "WITHIN + BEYOND => INCONCLUSIVE with seed_conflict"))
    check("M14_loss_guard_empty_or_nonfinite_means", lambda: ((EL.loss_label_admissible("SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ", []), EL.loss_label_admissible("SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ", [float("nan")])) == (False, False), "no means / NaN => inadmissible"))
    check("M15_v4_label_and_shared_loss_need_margin", lambda: (raises(TypeError, lambda: EL.v4_label([iv(0.1, 0.2)])) and raises(TypeError, lambda: EL.shared_loss_reading(deployed_means=[-1.0], replay_means=[-1.0], differences=[iv(-0.01, 0.01)])), "no margin => TypeError"))
    check("M16_single_seed_can_not_turn_C_into_equivalent_when_the_other_is_wide", lambda: (EL.v4_label([iv(-0.01, 0.01), iv(-0.3, 0.3)], margin=mg)["label"] == "(C) INCONCLUSIVE", "(C) EQUIVALENT needs every seed inside the band"))

    # added at C3 after mutation run 1 (k2_mutation_run.py): each check below kills one surviving mutant
    check("M17_direction_A_requires_point_positive_as_judge_v4", lambda: (EL.direction_v4([EL.Interval(point=-0.01, lo=0.001, hi=0.2, level=0.95)] * 2) == "(C)", "point <= 0 with lo > 0 is (C) in judge_v4; kills M-g"))
    check("M18_t1h1_band_uses_least_extreme_drop", lambda: (KR.rule_t1h1_cell((-4.0, -6.0, -1.0), (-0.1, -0.5, 0.3), fraction=0.25, level=0.95) == "UNDECIDED", "a mix of -0.5 can be 50% of a drop of 1; kills R-b"))
    check("M19_t8_usefulness_excluded_needs_k0_and_k9", lambda: (KR.rule_t8_reading("FAIL", {"R_NET_s42": dict(point=0.0, ci_k0=(-0.02, 0.02), ci_k9=(-0.03, 0.035))}, margin=M(0.03, unit="pooled OOS Pearson r"), level=0.95)
                                                              == "FAIL: failed to detect; usefulness not excluded", "k9 upper 0.035 >= 0.03; kills R-c"))
    T1H5_SIX_SMALL = {n: (0.0, -0.1, 0.1) for n in ("dpD", "dsD", "dpR", "dsR", "dpRs", "dsRs")}
    check("M20_t1h5_band_uses_least_extreme_reference", lambda: ((KR.rule_t1h5(0.1, T1H5_SIX_SMALL, (1.0, 0.2, 1.8), (2.0, 1.5, 2.5), fraction=0.25, level=0.95),
                                                                  KR.rule_t1h5(0.1, T1H5_SIX_SMALL, (1.0, -0.2, 2.2), (2.0, 1.5, 2.5), fraction=0.25, level=0.95)) == ("NOT DECIDABLE", "NOT DECIDABLE"),
                                                                 "band 0.25*0.2 = 0.05 < 0.1; a reference CI containing 0 gives no band; kills R-e"))
    check("M21_t5addendum_not_negligible_needs_every_seed", lambda: (KR.rule_t5_addendum([(0.5, 0.3, 0.7), (0.1, -0.1, 0.3)], margin=M(0.05, unit="share of gap"), not_negligible_line=0.20, level=0.95) == "INCONCLUSIVE", "one seed beyond 0.20, the other not; kills R-f"))

    # ------------------------------------------------------------------------------------------ Group P: direction labels unchanged (properties)
    import k2_legacy_predicates as KLP
    LEGP = KLP.Legacy()
    rng = np.random.default_rng(7)

    def prop_v4():
        bad = []
        for i in range(2000):
            c = []
            for _ in range(2):
                p = rng.normal(0, 0.3); h = abs(rng.normal(0, 0.3)); c.append((p, p - h * rng.uniform(0.2, 1.8), p + h * rng.uniform(0.2, 1.8)))
            leg = LEGP.v4_verdict([dict(delta=x[0], ci95=[x[1], x[2]]) for x in c]).split(" ")[0]
            mod = EL.direction_v4([EL.Interval(point=x[0], lo=x[1], hi=x[2], level=0.95) for x in c])
            if leg != mod: bad.append((c, leg, mod))
        return not bad, "2000 random pairs; mismatches=%d %s" % (len(bad), bad[:2])
    check("P01_direction_equals_frozen_judge_v4_rule", prop_v4)

    def prop_p2():
        bad = []; n = 0
        for i in range(4000):
            c = []
            for _ in range(2):
                p = rng.normal(0, 0.6); h = abs(rng.normal(0, 0.3)); c.append((p, p - h * rng.uniform(0.2, 1.8), p + h * rng.uniform(0.2, 1.8)))
            if any(abs(x[0]) < 0.23 for x in c): continue
            n += 1
            leg = LEGP.p2_verdict({s: dict(dg=x[0], ci95_k0=[x[1], x[2]]) for s, x in zip(("42", "2027"), c)}, 0)
            mod = EL.direction_v4([EL.Interval(point=x[0], lo=x[1], hi=x[2], level=0.95) for x in c])
            if leg.split(" ")[0] != mod: bad.append((c, leg, mod))
        return (not bad and n > 500), "%d random pairs with both |Δg| >= 0.23; mismatches=%d %s" % (n, len(bad), bad[:2])
    check("P02_direction_equals_P2_A67_outside_its_0p23_branch", prop_p2)

# ---------------------------------------------------------------------------------------------- report
for cid, st, det in RESULTS:
    print("%-5s %s — %s" % (st, cid, det))
n = len(RESULTS); fails = {c for c, s, _ in RESULTS if s == "FAIL"}; errors = {c for c, s, _ in RESULTS if s == "ERROR"}
if IMPL == "legacy":
    xs = {c for c, _, _ in RESULTS if c.startswith("X")}
    print("LEGACY RED SET == EXPECTED MISFIRE SET: %s (failing %d, expected %d, unexpected red %s, expected-but-green %s, errors %d)" % (
        fails == EXPECTED_LEGACY_RED and not errors, len(fails), len(EXPECTED_LEGACY_RED), sorted(fails - EXPECTED_LEGACY_RED), sorted(EXPECTED_LEGACY_RED - fails), len(errors)))
print("SUMMARY impl=%s checks=%d pass=%d fail=%d error=%d" % (IMPL, n, n - len(fails) - len(errors), len(fails), len(errors)))
sys.exit(0 if not fails and not errors else 1)
