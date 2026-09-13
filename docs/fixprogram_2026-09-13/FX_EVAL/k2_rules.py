#!/usr/bin/env python3
"""k2_rules.py — FIXPROGRAM 2026-09-13 item K2: the frozen re-label rules of DELTA_TABLE_K2.json (sha ad6af207…), composed from the shared
module equivalence_labels. Direction branches of every device are kept exactly as frozen; only the no-difference / absence branches
change: they now need an interval inside (or beyond) a declared band. Used by tests_equivalence_labels.py and k2_relabel.py.
"""
import math, os, sys
sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common")
import equivalence_labels as EL


def _iv(t, level):
    return EL.Interval(point=float(t[0]), lo=float(t[1]), hi=float(t[2]), level=level)


def _scaled(margin, delta, why):
    return EL.Margin(delta=delta, unit=margin.unit if isinstance(margin, EL.Margin) else "fraction of reference", justification=why, source="k2_rules.py (derived from a declared relative line)")


# R-T4 ------------------------------------------------------------------------------------------------------------------------------
def rule_t4(book, ic, *, book_margin, ic_margin, level):
    """book: {seed: (dg, lo, hi)}; ic: (mean, lo, hi)"""
    b = EL.aggregate([EL.equivalence(_iv(v, level), margin=book_margin) for v in book.values()])
    i = EL.equivalence(_iv(ic, level), margin=ic_margin)
    if b["label"] == EL.EQUIVALENT and i["label"] == EL.EQUIVALENT: label = "NOT MATERIAL (equivalent within ±δ)"
    elif b["label"] == EL.NOT_EQUIVALENT or i["label"] == EL.NOT_EQUIVALENT: label = "MATERIAL (established beyond ±δ)"
    else: label = "INCONCLUSIVE"
    return dict(label=label, book=b, ic=i, book_only=b["label"],
                detected_book_all_seeds=all(v[1] > 0 or v[2] < 0 for v in book.values()), detected_ic=bool(ic[1] > 0 or ic[2] < 0))


# R-LOSS on T5c readings ------------------------------------------------------------------------------------------------------------
def rule_t5c(D_K, R_K, diff, *, margin, level, kind):
    """D_K, R_K, diff: stored [point, lo, hi] (one seed); kind 'return' (price, net) or 'level' (carry, cost)"""
    if kind == "return":
        return EL.shared_loss_reading(deployed_means=[D_K[0]], replay_means=[R_K[0]], differences=[_iv(diff, level)], margin=margin)
    e = EL.equivalence(_iv(diff, level), margin=margin)
    return dict(label={EL.EQUIVALENT: "SAME LEVEL (equivalent within ±δ)", EL.NOT_EQUIVALENT: "DIFFERENT LEVEL (beyond ±δ)"}.get(e["label"], "INCONCLUSIVE"), difference=e["label"])


def rule_t5c_seeds(D_K_by_seed, R_K_by_seed, diff_by_seed, *, margin, level, kind):
    seeds = sorted(diff_by_seed)
    if kind == "return":
        return EL.shared_loss_reading(deployed_means=[D_K_by_seed[s][0] for s in seeds], replay_means=[R_K_by_seed[s][0] for s in seeds],
                                      differences=[_iv(diff_by_seed[s], level) for s in seeds], margin=margin)
    agg = EL.aggregate([EL.equivalence(_iv(diff_by_seed[s], level), margin=margin) for s in seeds])
    return dict(label={EL.EQUIVALENT: "SAME LEVEL (equivalent within ±δ)", EL.NOT_EQUIVALENT: "DIFFERENT LEVEL (beyond ±δ)"}.get(agg["label"], "INCONCLUSIVE"),
                difference=agg["label"], seed_conflict=agg["seed_conflict"])


# R-T5B ------------------------------------------------------------------------------------------------------------------------------
def rule_t5b(mean, ci, *, margin, level):
    if mean is None or ci is None or any(x is None for x in ci): return "NOT RE-LABELLABLE (statistic absent)"
    r = EL.one_sided(EL.Interval(point=float(mean), lo=float(ci[0]), hi=float(ci[1]), level=level), margin=margin, material_side="upper")
    return {EL.WITHIN_MARGIN: "NOT MATERIAL (established below line)", EL.BEYOND_MARGIN: "MATERIAL (established at or above line)"}.get(r["label"], "INCONCLUSIVE")


# R-T5ADD ----------------------------------------------------------------------------------------------------------------------------
def rule_t5_addendum(cells, *, margin, not_negligible_line, level):
    ivs = [_iv(c, level) for c in cells]
    eq = EL.aggregate([EL.equivalence(v, margin=margin) for v in ivs])
    if eq["label"] == EL.EQUIVALENT: return "NEGLIGIBLE (established)"
    if all(v.lo >= not_negligible_line or v.hi <= -not_negligible_line for v in ivs): return "NOT NEGLIGIBLE (established)"
    return "INCONCLUSIVE"


# R-T2 / R-V4 / P2 --------------------------------------------------------------------------------------------------------------------
def rule_t2_axis(cells, *, margin, level):
    return EL.aggregate([EL.equivalence(_iv(c, level), margin=margin) for c in cells])["label"]


def rule_v4(cells, *, margin, level):
    return EL.v4_label([_iv(c, level) for c in cells], margin=margin)["label"]


# R-T1H1 / R-T1H3 / R-T1H5 -----------------------------------------------------------------------------------------------------------
def rule_t1h1_cell(D, MIX, *, fraction, level):
    """D, MIX: (point, vci_lo, vci_hi). EXPLAINS as frozen; DOES-NOT-EXPLAIN only if MIX > -fraction·|D| is established with |D| at its
    least extreme plausible value |vci_hi| (union bound)"""
    ratio = MIX[0] / D[0] if D[0] != 0 else float("nan")
    if D[2] < 0 and MIX[2] < 0 and ratio >= 0.5: return "EXPLAINS"
    if D[2] < 0:
        m = EL.Margin(delta=fraction * abs(D[2]), unit="bps / anchor (fraction %.3g of |D_T vci_hi|)" % fraction,
                      justification="T1 PREREG L110 relative line applied to the verdict interval of MIX with |D_T| at its least extreme value", source="PREREG_T1 L110 via DELTA_TABLE_K2 D6")
        if EL.one_sided(_iv(MIX, level), margin=m, material_side="lower")["label"] == EL.WITHIN_MARGIN: return "DOES-NOT-EXPLAIN"
    return "UNDECIDED"


def rule_t1_agg_h1(cells):
    if "EXPLAINS" in cells: return "SURVIVES"
    if all(c == "DOES-NOT-EXPLAIN" for c in cells): return "FALSIFIED"
    return "NOT DECIDABLE"


def rule_t1h3_cell(dE0, dE1, E0H, E1H, E0T, E1T, *, fraction, level):
    """dE0, dE1: (point, vci_lo, vci_hi). HALF-LIFE and LEVEL as frozen; NO-DROP only if dE1 > -fraction·|E1H| is established"""
    if dE1[2] < 0 and E0T >= 0.75 * E0H and dE0[1] <= 0 <= dE0[2]: return "HALF-LIFE"
    if dE0[2] < 0 and (E0T / E0H if E0H != 0 else math.inf) <= (E1T / E1H if E1H != 0 else math.inf) + 0.25: return "LEVEL"
    if E1H != 0:
        m = EL.Margin(delta=fraction * abs(E1H), unit="bps (fraction %.3g of |E1_H1|)" % fraction,
                      justification="T1 PREREG L132 relative NO-DROP line applied to the verdict interval of dE1 (E1_H1 at its stored point)", source="PREREG_T1 L132 via DELTA_TABLE_K2 D6")
        if EL.one_sided(_iv(dE1, level), margin=m, material_side="lower")["label"] == EL.WITHIN_MARGIN: return "NO-DROP"
    return "UNDECIDED"


def rule_t1_agg_h3(fcells):
    return "SURVIVES" if "HALF-LIFE" in fcells else ("FALSIFIED" if all(c in ("LEVEL", "NO-DROP") for c in fcells) else "NOT DECIDABLE")


def rule_t1h5(c1d, six, ref_pi, ref_ss, *, fraction, level):
    """six: {dpD, dsD, dpR, dsR, dpRs, dsRs: (point, vci_lo, vci_hi)}; ref_pi / ref_ss: (point, ci95_lo, ci95_hi) of the 2023 references"""
    excl = lambda t: t[1] > 0 or t[2] < 0
    if c1d >= 0.50 and ((excl(six["dpD"]) and excl(six["dpR"]) and excl(six["dpRs"])) or (excl(six["dsD"]) and excl(six["dsR"]) and excl(six["dsRs"]))):
        return "SURVIVES (different mechanisms)"
    if c1d <= 0.20:
        def band(ref):
            return None if (ref[1] <= 0 <= ref[2]) else fraction * min(abs(ref[1]), abs(ref[2]))
        bp, bs = band(ref_pi), band(ref_ss)
        if bp and bs:
            ok = True
            for n, b in (("dpD", bp), ("dpR", bp), ("dpRs", bp), ("dsD", bs), ("dsR", bs), ("dsRs", bs)):
                m = EL.Margin(delta=b, unit="same unit as the 2023 reference", justification="T1 PREREG L146 relative line (0.25 of the least extreme 2023 reference) on the verdict interval",
                              source="PREREG_T1 L146 via DELTA_TABLE_K2 D6")
                ok = ok and EL.equivalence(_iv(six[n], level), margin=m)["label"] == EL.EQUIVALENT
            if ok: return "FALSIFIED (same mechanism)"
    return "NOT DECIDABLE"


# R-T8 ------------------------------------------------------------------------------------------------------------------------------
def rule_t8_reading(verdict, cells, *, margin, level):
    """verdict: the frozen T8 overall verdict (unchanged); cells: {key: dict(point, ci_k0=(lo, hi), ci_k9=(lo, hi))}"""
    if verdict != "FAIL": return verdict if verdict != "UNDECIDED" else "UNDECIDED (T8)"
    excluded = []
    for k, c in cells.items():
        r0 = EL.one_sided(EL.Interval(point=c["point"], lo=c["ci_k0"][0], hi=c["ci_k0"][1], level=level), margin=margin, material_side="upper")["label"]
        r9 = EL.one_sided(EL.Interval(point=c["point"], lo=c["ci_k9"][0], hi=c["ci_k9"][1], level=level), margin=margin, material_side="upper")["label"]
        excluded.append(r0 == EL.WITHIN_MARGIN and r9 == EL.WITHIN_MARGIN)
    return "FAIL (usefulness excluded: r < line in every cell)" if excluded and all(excluded) else "FAIL: failed to detect; usefulness not excluded"


# L2 failure wording ----------------------------------------------------------------------------------------------------------------------
def rule_l2_first_fail(conds, first_fail):
    if first_fail is None: return None
    key = next(k for k in ("C1", "C2", "C3", "C4", "C5", "C6") if not conds[k])
    return "%s NOT ESTABLISHED (failed gate; no absence margin declared)" % key
