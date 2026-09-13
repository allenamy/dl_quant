#!/usr/bin/env python3
"""k2_relabel.py — FIXPROGRAM 2026-09-13 item K2 (FX-EVAL): mechanical re-label of committed results under the FROZEN δ table
(DELTA_TABLE_K2.json, sha ad6af207…, frozen 13:19:08Z) and the shared module. READ-ONLY on every receipt and document it opens
(hash-guarded reads; nothing under the result directories is written). The re-labels are PROPOSALS for the lead; no RESULT file is edited.

Order per family:
  1. G-REPRO (the original chain): the pinned verbatim legacy predicate is re-run on the stored numbers and must reproduce the stored label.
     A family that does not reproduce is reported NOT RE-LABELLABLE (reproduction failed) and gets no new label.
  2. New label by the frozen rule (k2_rules.py over equivalence_labels.py) with the frozen primary δ.
  3. Sensitivity labels at the δ values the table lists (never used as the label).
Writes RELABEL_TABLE_K2.json / .md beside itself; prints one SUMMARY line; exit 0 only if every reproduction gate passes.
"""
import os, sys, json, stat, hashlib, math, re, time, subprocess, glob
import numpy as np

REPO = "/Users/haosiyu/Desktop/quant_research"; HERE = os.path.dirname(os.path.abspath(__file__))
RS = REPO + "/multi_asset/exports/research"; R2 = RS + "/uplift_r2_2026-09-13"; R3 = RS + "/uplift_r3_2026-09-13"; V4 = RS + "/retrain_2026-09/v4_chain_2026-09-09"
sys.path.insert(0, HERE); sys.path.insert(0, RS + "/common")
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
DELTA_SHA = "ad6af2075ca71ed756be26bbe7759761f981add24f02581de41c3f014643dea6"
INPUTS = {}


def gread(path):
    """guarded read (T6 rule): refuse dataless files and short reads; record sha256"""
    st = os.stat(path)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE dataless: " + path)
    with open(path, "rb") as f: b = f.read()
    if len(b) != st.st_size: raise SystemExit("REFUSE short read: " + path)
    INPUTS[os.path.relpath(path, REPO)] = hashlib.sha256(b).hexdigest(); return b


def gjson(path): return json.loads(gread(path).decode("utf-8"))


DT = gjson(HERE + "/DELTA_TABLE_K2.json"); assert INPUTS["docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.json"] == DELTA_SHA, "δ table is not the frozen one"
DROW = {d["key"]: d for d in DT["deltas"]}
# guarded reads BEFORE any import or AST extraction: an evicted (dataless) module or device file is refused, never read as empty
for p in (RS + "/common/equivalence_labels.py", HERE + "/k2_rules.py", HERE + "/k2_legacy_predicates.py", os.path.abspath(__file__), HERE + "/FACT_TABLE_K2.json",
          R2 + "/T4/devices/t4_judge.py", R2 + "/T5c/devices/t5c_bridge.py", R2 + "/T5b/devices/t5b_q1.py", R2 + "/T5b/devices/t5b_exec.py", R2 + "/T5/devices/t5_addendum_h2b.py",
          R2 + "/T2/devices/t2_judge.py", RS + "/parity_replay_2026-09-12/phase2/devices/p2_s2_lib.py", R2 + "/T1/devices/t1_judge.py", R2 + "/T8/devices/t8_judge.py",
          R3 + "/L2/devices/l2_b_common.py", V4 + "/judge_v4.py"): gread(p)
import equivalence_labels as EL
import k2_rules as KR
import k2_legacy_predicates as KL
LEG = KL.Legacy()
LEVEL95 = 0.95


def margin(key, delta=None, unit=None):
    d = DROW[key]
    return EL.Margin(delta=float(d["delta"] if delta is None else delta), unit=unit or d["unit"], justification=d["justification"][0], source="DELTA_TABLE_K2.json %s (sha %s)" % (key, DELTA_SHA[:8]))


def z_level(z): return math.erf(float(z) / math.sqrt(2.0))


# ------------------------------------------------------------------------------------------------ claim classes for stored and new labels
NO_DIFF, BELOW, NO_EFFECT, INCONC, MATERIAL, EFFECT = "NO_DIFFERENCE", "BELOW_LINE", "NO_EFFECT", "INCONCLUSIVE", "MATERIAL", "EFFECT"
DET_IMM, NO_CLAIM = "DETECTED_BUT_WITHIN_BAND", "NO_CLAIM"
SL_SAME, SL_OPEN, SL_MAT, GAP, NOT_SHARED, DIR_A, DIR_B, NR = "SHARED_LOSS_SAME", "SHARED_LOSS_OPEN", "SHARED_LOSS_MATERIAL_DIFF", "GAP_DETECTED", "NOT_SHARED_LOSS", "DIRECTION_A", "DIRECTION_B", "NOT_RELABELLABLE"


def claim(label):
    L = str(label).split(" (PROVISIONAL")[0]      # T5b's provisional suffix does not change the claim class
    if L in ("—",) or L.startswith("admission:"): return NO_CLAIM
    if L.startswith("NOT RE-LABELLABLE"): return NR
    if L.endswith("; gap detected (CI excludes 0)"):
        return DET_IMM if (L.startswith("SAME LEVEL (equivalent") or L.startswith("SHARED LOSS, DIFFERENCE EQUIVALENT")) else GAP
    if L.startswith("BASELINE-RESIDUAL-FAR-BELOW"): return NO_DIFF
    if L.startswith("BASELINE-RESIDUAL-COMPARABLE"): return INCONC
    if L.startswith("BASELINE-RESIDUAL-ABOVE"): return MATERIAL
    if L == "ρ ≈ 0 (point estimates)": return NO_DIFF
    if L.startswith("NOT MATERIAL (at this resolution)") or L.startswith("NOT MATERIAL (equivalent"): return NO_DIFF
    if L == "MATERIAL" or L.startswith("MATERIAL (established"): return MATERIAL
    if L.startswith("STRATEGY'S OWN LOSS") or L.startswith("SHARED LOSS, DIFFERENCE EQUIVALENT"): return SL_SAME
    if L.startswith("SHARED LOSS, DIFFERENCE INCONCLUSIVE") or L.startswith("BOTH LOST, UNDECIDABLE"): return SL_OPEN
    if L.startswith("SHARED LOSS, MATERIAL DIFFERENCE"): return SL_MAT
    if L.startswith("NOT A SHARED LOSS"): return GAP if ("; gap detected" in L or L.endswith("gap)")) else NOT_SHARED
    if L in ("DEPLOYMENT DIFFERENCE", "DEPLOYMENT GAP", "SAME DIRECTION WITH A GAP", "BOTH LOST, DEPLOYMENT GAP"): return GAP
    if L == "SAME LEVEL" or L.startswith("SAME LEVEL (equivalent") or L in ("EQUIVALENT", "(C) EQUIVALENT", "NEGLIGIBLE", "NEGLIGIBLE (established)", "FALSIFIED (same mechanism)") or "不可区分" in L or L.startswith("(C) indistinguishable"): return NO_DIFF
    if L.startswith("DIFFERENT LEVEL") or L in ("NOT EQUIVALENT", "(C) NOT EQUIVALENT", "NOT NEGLIGIBLE", "NOT NEGLIGIBLE (established)"): return MATERIAL
    if L.startswith("NOT MATERIAL"): return BELOW
    if L.startswith("FROZEN-RESIDUAL-MATERIAL") or L.startswith("EXECUTOR-ADDED-FREEZE-MATERIAL"): return MATERIAL
    if L in ("INCONCLUSIVE", "(C) INCONCLUSIVE", "UNDECIDABLE", "UNDECIDED", "NOT DECIDABLE", "(C) UNDECIDED", "SMALL") or L.startswith("UNDECIDED") or L.startswith("FAIL: failed to detect"): return INCONC
    if L in ("DOES-NOT-EXPLAIN", "NO-DROP", "FALSIFIED") or L.startswith("FAIL (usefulness excluded") or L == "FAIL (with the frozen consequence 'cannot predict')": return NO_EFFECT
    if L in ("EXPLAINS", "HALF-LIFE", "LEVEL", "SURVIVES", "SURVIVES (different mechanisms)", "PASS"): return EFFECT
    if L.startswith("(A)"): return DIR_A
    if L.startswith("(B)"): return DIR_B
    return "UNMAPPED:" + L


ROWS, GATES = [], {}


STRONG = {NO_DIFF, BELOW, NO_EFFECT, SL_SAME, SL_MAT, MATERIAL, EFFECT, DIR_A, DIR_B, GAP, NOT_SHARED, DET_IMM}


def status_of(cs, cn):
    if cs == NO_CLAIM and cn == NO_CLAIM: return "NO_CLAIM"
    if cn == NR: return "NOT_RELABELLABLE"
    if cs == cn: return "UNCHANGED"
    if cs == GAP and cn == DET_IMM: return "REFINED"          # the device's detection is kept; the band adds that it is immaterial
    if cs in STRONG and cn in (INCONC, SL_OPEN): return "WITHDRAWN"
    if cs in (INCONC, SL_OPEN) and cn in STRONG: return "STRENGTHENED"
    return "CHANGED"


def detected(t): return bool(t[1] > 0 or t[2] < 0)


def row(family, result, item, stored, new, numbers, rule, sens=None, note=""):
    cs, cn = claim(stored), claim(new); st = status_of(cs, cn)
    ROWS.append(dict(family=family, result=os.path.relpath(result, REPO) if result else None, item=item, stored_label=stored, stored_claim=cs, new_label=new, new_claim=cn,
                     status=st, changed=st in ("WITHDRAWN", "STRENGTHENED", "REFINED", "CHANGED"), numbers=numbers, rule=rule, sensitivity=sens or {}, note=note))


def gate(name, ok, detail):
    GATES[name] = dict(PASS=bool(ok), detail=detail); return bool(ok)


def r3(t): return [round(float(x), 6) for x in t]


# ================================================================================================ T4 (F01)
def fam_t4():
    p = R2 + "/T4/receipts/RECEIPT_T4_judge.json"; R = gjson(p)
    legacy = LEG.t4_verdict(R["book"], R["score"]); stored = R["verdict"]["verdict"]
    if not gate("G-REPRO T4", legacy == stored, dict(legacy=legacy, stored=stored)):
        return row("T4", p, "verdict", stored, "NOT RE-LABELLABLE (reproduction failed)", {}, "R-T4")
    book = {s: (R["book"]["K1_minus_K0|C0|s%s" % s]["KING_LIVE"]["dg"], *R["book"]["K1_minus_K0|C0|s%s" % s]["KING_LIVE"]["ci95"]) for s in ("42", "2027")}
    icd = R["score"]["KING_LIVE"]["dIC_K1_minus_K0"]; ic = (icd["mean"], icd["ci95"][0], icd["ci95"][1])
    new = KR.rule_t4(book, ic, book_margin=margin("D1"), ic_margin=margin("D4"), level=LEVEL95)
    sens = {"D1=%g" % d: KR.rule_t4(book, ic, book_margin=margin("D1", d), ic_margin=margin("D4"), level=LEVEL95)["label"] for d in DROW["D1"]["sensitivity"]}
    sens.update({"D4=%g" % d: KR.rule_t4(book, ic, book_margin=margin("D1"), ic_margin=margin("D4", d), level=LEVEL95)["label"] for d in DROW["D4"]["sensitivity"]})
    nums = dict(book_C0_KL={s: r3(v) for s, v in book.items()}, dIC_KL=r3(ic), book_axis=new["book"]["label"], book_members=new["book"]["members"], ic_axis=new["ic"]["label"])
    row("T4", p, "verdict (C0 base, KING_LIVE)", stored, new["label"], nums, "R-T4 with D1 = %g, D4 = %g" % (DROW["D1"]["delta"], DROW["D4"]["delta"]), sens)
    nw = {s: (R["book"]["K1_minus_K0|NW|s%s" % s]["KING_LIVE"]["dg"], *R["book"]["K1_minus_K0|NW|s%s" % s]["KING_LIVE"]["ci95"]) for s in ("42", "2027")}
    nnw = KR.rule_t4(nw, ic, book_margin=margin("D1"), ic_margin=margin("D4"), level=LEVEL95)
    row("T4", p, "reported-only NW base (same test)", "NOT MATERIAL (at this resolution)" if not R["verdict"]["condA_NW_KL"] else "MATERIAL", nnw["label"],
        dict(book_NW_KL={s: r3(v) for s, v in nw.items()}, book_axis=nnw["book"]["label"]), "R-T4 with D1, D4 (reported only; not in the frozen verdict)")


# ================================================================================================ T2 (F07)
def fam_t2():
    p = R2 + "/T2/receipts/RECEIPT_T2_judge.json"; R = gjson(p); ok_all = True
    for arm in R["decisions"]:
        for base, key in (("A0", "A0_verdict"), ("NW", "NW_reading")):
            RB = R["results"][arm]["bases"][base]; st = R["decisions"][arm][key]
            leg = LEG.t2_decide(RB, R["C2_from_drive"]["arm_PASS"].get(arm), R["decisions"][arm]["tripwire_state"])
            brs = {s: LEG.t2_below_resolution(RB[s]["W_ALPHA"]["dg"]) == RB[s]["W_ALPHA"]["below_resolution"] for s in RB}
            ok = leg["verdict"] == st["verdict"] and leg["flags"] == st["flags"] and all(brs.values()); ok_all &= ok
            if not ok:
                row("T2", p, "%s %s" % (arm, base), st["verdict"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg["verdict"], flags=leg["flags"]), "R-T2"); continue
            cells = [(st["dg"][s], st["ci95"][s][0], st["ci95"][s][1]) for s in ("42", "2027")]
            axis = KR.rule_t2_axis(cells, margin=margin("D1"), level=LEVEL95)
            stored_axis = "(C) indistinguishable (|Δg| < 0.23)" if "BELOW-RESOLUTION" in st["flags"] else "UNDECIDED"   # the flag is the only no-difference claim T2 makes
            sens = {"D1=%g" % d: KR.rule_t2_axis(cells, margin=margin("D1", d), level=LEVEL95) for d in DROW["D1"]["sensitivity"]}
            row("T2", p, "%s vs %s: verdict '%s' flags %s — equivalence axis" % (arm, base, st["verdict"], st["flags"]), stored_axis, axis,
                dict(dg_ci95={s: r3(c) for s, c in zip(("42", "2027"), cells)}), "R-T2 (verdict unchanged) with D1 = %g" % DROW["D1"]["delta"], sens)
    gate("G-REPRO T2", ok_all, "decide() and below_resolution reproduced for every arm × base")


# ================================================================================================ T5c (F02) and T5d (F03, committed after the freeze)
KIND5 = dict(P="return", N="return", C="level", K="level")


def show(label, diffs):
    """R-DIR rendering: keep the frozen device's own detection flag (difference CI excludes 0 in every member) visible next to the band reading.
    Added after relabel run 1 (receipts/relabel_run1_before_rendering_fix.log); no label decision depends on it."""
    diffs = list(diffs)
    if diffs and all(detected(t) for t in diffs) and not label.startswith("NOT A SHARED LOSS"): return label + "; gap detected (CI excludes 0)"
    return label


def t5c_legacy_label(D, Rk, diff):
    ns = dict(np=np, days=np.zeros(1), B=1, one=np.ones(1)); exec(compile("\n".join(LEG.code["T5C"]), "<legacy T5C>", "exec"), ns)
    it = iter([list(D), list(Rk), list(diff)]); ns["boot"] = lambda *a, **k: next(it)
    return ns["readings"](np.zeros(2), np.zeros(2))["label"]


def fam_t5c():
    p = R2 + "/T5c/receipts/pod2/RECEIPT_T5c_bridge.json"; R = gjson(p); res = R["result"]; ok_all = True
    groups = [("KA", res["seeds"], "readings"), ("KA excl 09-06", res["seeds"], "readings_excl_0906"), ("KB", res["KB"], "readings"), ("KB excl 09-06", res["KB"], "readings_excl_0906")]
    for lineage, src, rk in groups:
        tags = sorted(src)
        for q in ("P", "C", "K", "N"):
            per = {}
            for tag in tags:
                rd = src[tag][rk][q]; leg = t5c_legacy_label(rd["D_K"], rd["R_K"], rd["diff_D_minus_R"]); ok = leg == rd["label"]; ok_all &= ok
                per[tag] = rd
                if not ok: row("T5c", p, "%s %s %s" % (lineage, tag, q), rd["label"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-LOSS"); continue
                new = KR.rule_t5c(rd["D_K"], rd["R_K"], rd["diff_D_minus_R"], margin=margin("D1"), level=LEVEL95, kind=KIND5[q])
                sens = {"D1=%g" % d: show(KR.rule_t5c(rd["D_K"], rd["R_K"], rd["diff_D_minus_R"], margin=margin("D1", d), level=LEVEL95, kind=KIND5[q])["label"], [rd["diff_D_minus_R"]]) for d in DROW["D1"]["sensitivity"]}
                row("T5c", p, "%s %s outcome %s (per tag)" % (lineage, tag, q), rd["label"], show(new["label"], [rd["diff_D_minus_R"]]), dict(D_K=r3(rd["D_K"]), R_K=r3(rd["R_K"]), D_minus_R=r3(rd["diff_D_minus_R"])),
                    "R-LOSS (%s) with D1 = %g" % (KIND5[q], DROW["D1"]["delta"]), sens)
            if len(per) == 2 and all(src[t][rk][q]["label"] == src[tags[0]][rk][q]["label"] for t in tags):
                D = {t: per[t]["D_K"] for t in tags}; Rr = {t: per[t]["R_K"] for t in tags}; Df = {t: per[t]["diff_D_minus_R"] for t in tags}
                new = KR.rule_t5c_seeds(D, Rr, Df, margin=margin("D1"), level=LEVEL95, kind=KIND5[q])
                sens = {"D1=%g" % d: show(KR.rule_t5c_seeds(D, Rr, Df, margin=margin("D1", d), level=LEVEL95, kind=KIND5[q])["label"], Df.values()) for d in DROW["D1"]["sensitivity"]}
                row("T5c", p, "%s outcome %s (label needs both seeds, PREREG §6)" % (lineage, q), per[tags[0]]["label"], show(new["label"], Df.values()),
                    dict(D_minus_R={t: r3(Df[t]) for t in tags}, R_K_points={t: round(Rr[t][0], 6) for t in tags}, D_K_point=round(D[tags[0]][0], 6)), "R-LOSS over seeds (%s) with D1" % KIND5[q], sens)
    gate("G-REPRO T5c", ok_all, "legacy readings() predicate re-run on every stored interval triple")


def fam_t5d():
    p = R2 + "/T5d/receipts/pod2/RECEIPT_T5d_bridge.json"; R = gjson(p)
    f = KL._File(R2 + "/T5d/devices/t5d_bridge.py"); gread(R2 + "/T5d/devices/t5d_bridge.py")
    code = f.funcdef("def readings(dk, rk, kind, sel=None, dd=None):"); seg_sha = hashlib.sha256(code.encode()).hexdigest()
    kinds = eval(compile(f.named_assign('OUTC = ("P", "C", "K", "N"); KIND = dict(P="return", N="return", C="cost", K="cost")', "KIND").split("=", 1)[1].strip(), "<kind>", "eval"), dict(dict=dict))
    ok_all = True
    for tag in sorted(R["readings"]):
        for cal in R["readings"][tag]:
            for q, rd in R["readings"][tag][cal].items():
                ns = dict(np=np, DELTA_EQ=float(R["delta_equivalence_bps"])); exec(compile(code, "<legacy T5d readings>", "exec"), ns)
                it = iter([list(rd["D_K"]), list(rd["R_K"]), list(rd["diff_D_minus_R"])]); ns["boot"] = lambda *a, **k: next(it)
                leg = ns["readings"](np.zeros(2), np.zeros(2), kinds[q])["label"]; ok = leg == rd["label"]; ok_all &= ok
                if not ok: row("T5d", p, "%s %s %s" % (tag, cal, q), rd["label"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-LOSS"); continue
                kind = "return" if kinds[q] == "return" else "level"
                new = KR.rule_t5c(rd["D_K"], rd["R_K"], rd["diff_D_minus_R"], margin=margin("D1"), level=LEVEL95, kind=kind)
                sens = {"D1=%g" % d: show(KR.rule_t5c(rd["D_K"], rd["R_K"], rd["diff_D_minus_R"], margin=margin("D1", d), level=LEVEL95, kind=kind)["label"], [rd["diff_D_minus_R"]]) for d in DROW["D1"]["sensitivity"]}
                row("T5d", p, "%s %s outcome %s (per tag)" % (tag, cal, q), rd["label"], show(new["label"], [rd["diff_D_minus_R"]]), dict(D_K=r3(rd["D_K"]), R_K=r3(rd["R_K"]), D_minus_R=r3(rd["diff_D_minus_R"]), T5d_EQUIV_0p25=rd.get("EQUIV")),
                    "R-LOSS (%s) with D1 = %g — added after the freeze (T5d committed e73f50e6 after C1); rule and δ unchanged" % (kind, DROW["D1"]["delta"]), sens)
    for lin in ("KA", "KB"):
        tags = [t for t in sorted(R["readings"]) if t.startswith(lin)]
        for cal in R["readings"][tags[0]]:
            for q in ("P", "C", "K", "N"):
                rds = {t: R["readings"][t][cal][q] for t in tags}
                if len({rd["label"] for rd in rds.values()}) != 1: continue
                kind = "return" if kinds[q] == "return" else "level"
                D = {t: rds[t]["D_K"] for t in tags}; Rr = {t: rds[t]["R_K"] for t in tags}; Df = {t: rds[t]["diff_D_minus_R"] for t in tags}
                new = KR.rule_t5c_seeds(D, Rr, Df, margin=margin("D1"), level=LEVEL95, kind=kind)
                sens = {"D1=%g" % d: show(KR.rule_t5c_seeds(D, Rr, Df, margin=margin("D1", d), level=LEVEL95, kind=kind)["label"], Df.values()) for d in DROW["D1"]["sensitivity"]}
                row("T5d", p, "%s %s outcome %s (both seeds)" % (lin, cal, q), rds[tags[0]]["label"], show(new["label"], Df.values()), dict(D_minus_R={t: r3(Df[t]) for t in tags}),
                    "R-LOSS over seeds (%s) with D1 — added after the freeze" % kind, sens)
    gate("G-REPRO T5d", ok_all, dict(detail="T5d readings() (AST-extracted from t5d_bridge.py, not pinned at C2) re-run on stored triples", segment_sha256=seg_sha))


# ================================================================================================ T5b (F04, F05)
def fam_t5b():
    p = R2 + "/T5b/receipts/RECEIPT_T5b_q1.json"; R = gjson(p); ok_all = True
    for name, v in R["readings"].items():
        if "reading" not in v: continue
        base = v["reading"].split(" (PROVISIONAL")[0]; suffix = v["reading"][len(base):]
        leg = LEG.t5b_q1_reading(np.array([v["mean"]])); ok = leg == base; ok_all &= ok
        if not ok: row("T5b Q1", p, name, v["reading"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-T5B"); continue
        new = KR.rule_t5b(v["mean"], v["ci95"], margin=margin("D8"), level=LEVEL95)
        sens = {"D8=%g" % d: KR.rule_t5b(v["mean"], v["ci95"], margin=margin("D8", d), level=LEVEL95) for d in DROW["D8"]["sensitivity"]}
        row("T5b Q1", p, "%s (%s)" % (name, v.get("role")), v["reading"], new + suffix, dict(mean=round(v["mean"], 6), ci95=r3(v["ci95"]), n=v["n_anchors"]), "R-T5B with D8 = %g (upper = paid)" % DROW["D8"]["delta"], sens)
    p2 = R2 + "/T5b/receipts/RECEIPT_T5b_exec.json"; X = gjson(p2); v = X["Q3"]["readings"]["PRIMARY_GAP_EXECFREEZE"]
    leg = LEG.t5b_exec_reading(v["mean"]); ok = leg == v["reading"]; ok_all &= ok
    if ok:
        new = KR.rule_t5b(v["mean"], v["ci95"], margin=margin("D8"), level=LEVEL95)
        sens = {"D8=%g" % d: KR.rule_t5b(v["mean"], v["ci95"], margin=margin("D8", d), level=LEVEL95) for d in DROW["D8"]["sensitivity"]}
        row("T5b Q3", p2, "PRIMARY_GAP_EXECFREEZE", v["reading"], new, dict(mean=round(v["mean"], 6), ci95=r3(v["ci95"]), n=v["n_anchors"]), "R-T5B with D8", sens)
    else:
        row("T5b Q3", p2, "PRIMARY_GAP_EXECFREEZE", v["reading"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-T5B")
    gate("G-REPRO T5b", ok_all, "t5b_q1 / t5b_exec reading expressions re-run on stored means")


# ================================================================================================ T5 addendum (F06)
def fam_t5add():
    p = R2 + "/T5/receipts/pod2/RECEIPT_T5_addendum1_h2b.json"; R = gjson(p); ok_all = True; cells = []
    for s, v in R["result"].items():
        sh = v["phi_K1"]["share"]; leg = LEG.t5_addendum_reading(sh[0]); ok = leg == v["reading"]; ok_all &= ok; cells.append(tuple(sh))
        if not ok: row("T5 addendum", p, "seed %s" % s, v["reading"], "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-T5ADD"); continue
        new = KR.rule_t5_addendum([tuple(sh)], margin=margin("D5"), not_negligible_line=0.20, level=LEVEL95)
        sens = {"D5=%g" % d: KR.rule_t5_addendum([tuple(sh)], margin=margin("D5", d), not_negligible_line=0.20, level=LEVEL95) for d in DROW["D5"]["sensitivity"]}
        row("T5 addendum", p, "seed %s φ_K1 share" % s, v["reading"], new, dict(share=r3(sh)), "R-T5ADD with D5 = %g" % DROW["D5"]["delta"], sens)
    gate("G-REPRO T5 addendum", ok_all, "reading expression re-run on stored share points")


# ================================================================================================ T1 (F09, F10, F11)
def fam_t1():
    p = R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json"; R = gjson(p); o = R["result"]; ok_all = True
    T = lambda s: (s["point"], s["vci_lo"], s["vci_hi"])
    for arm, a in o["arms"].items():
        H1 = a["H1"]; newcells = {}; legcells = {}
        for S in ("DISP24", "BREADTH72", "SIGF", "MUF"):
            for Tt, Dk in (("T_A", "D_TA"), ("T_L", "D_TL")):
                c = H1["%s|%s" % (S, Tt)]; leg = LEG.t1_h1_cell(H1[Dk], c["MIX"], c["mix_over_D"]); ok = leg == c["cell_verdict"]; ok_all &= ok
                legcells[(S, Tt)] = leg
                lvl = z_level(c["MIX"]["z"])
                new = KR.rule_t1h1_cell(T(H1[Dk]), T(c["MIX"]), fraction=DROW["D6"]["delta"], level=lvl) if ok else "NOT RE-LABELLABLE (reproduction failed)"
                newcells[(S, Tt)] = new
                sens = {"D6=%g" % d: KR.rule_t1h1_cell(T(H1[Dk]), T(c["MIX"]), fraction=d, level=lvl) for d in DROW["D6"]["sensitivity"]}
                row("T1 H1 cell", p, "%s %s|%s" % (arm, S, Tt), c["cell_verdict"], new, dict(D_T_vci=r3(T(H1[Dk])), MIX_vci=r3(T(c["MIX"])), vci_level=round(lvl, 5)), "R-T1H1 with D6 = %g" % DROW["D6"]["delta"], sens)
        for agg, vars_ in (("H1_verdict", ("DISP24", "BREADTH72")), ("H1fuel_verdict", ("SIGF", "MUF"))):
            leg = LEG.t1_h1_agg({(S, Tt): legcells[(S, Tt)] for S in vars_ for Tt in ("T_A", "T_L")}, vars_); ok = leg == H1[agg]; ok_all &= ok
            new = KR.rule_t1_agg_h1([newcells[(S, Tt)] for S in vars_ for Tt in ("T_A", "T_L")]) if ok else "NOT RE-LABELLABLE (reproduction failed)"
            row("T1 H1", p, "%s %s" % (arm, agg), H1[agg], new, {}, "T1 aggregate over re-labelled cells")
        H5 = a["H5"]; six = {k: H5[v] for k, v in (("dpD", "dpi_D2"), ("dsD", "dsig_D2"), ("dpR", "dpi_REAL"), ("dsR", "dsig_REAL"), ("dpRs", "dpi_REAL_scaled"), ("dsRs", "dsig_REAL_scaled"))}
        leg = LEG.t1_h5(abs(H5["c1_diff"]), *[six[n] for n in ("dpD", "dsD", "dpR", "dsR", "dpRs", "dsRs")], H5["pi_2023"]["point"], H5["sigma_short_2023"]["point"]); ok = leg == H5["verdict"]; ok_all &= ok
        lv = z_level(six["dpD"]["z"])
        ref = lambda s: (s["point"], s["ci95_lo"], s["ci95_hi"])
        new = KR.rule_t1h5(abs(H5["c1_diff"]), {n: T(six[n]) for n in six}, ref(H5["pi_2023"]), ref(H5["sigma_short_2023"]), fraction=DROW["D6"]["delta"], level=lv) if ok else "NOT RE-LABELLABLE (reproduction failed)"
        row("T1 H5", p, "%s H5" % arm, H5["verdict"], new, dict(c1_diff=round(H5["c1_diff"], 6), pi_2023=r3(ref(H5["pi_2023"])), sigma_short_2023=r3(ref(H5["sigma_short_2023"]))), "R-T1H5 with D6")
    H3 = o["H3"]; legf = []; newf = []
    for key in ("fund|LAG_M2026_08", "fund|LIVE_LAG", "king|LAG_M2026_08", "f10_s42|LAG_M2026_08", "f10_s2027|LAG_M2026_08"):
        c = H3[key]; cell = dict(dE0=c["dE0"], dE1=c["dE1"], E0H=c["E0_H1"], E1H=c["E1_H1"], E0T=c["E0_T"], E1T=c["E1_T"])
        legv, _ = LEG.t1_h3([cell]); ok = legv[0] == c["cell_verdict"]; ok_all &= ok
        lvl = z_level(c["dE1"]["z"])
        new = KR.rule_t1h3_cell(T(c["dE0"]), T(c["dE1"]), c["E0_H1"], c["E1_H1"], c["E0_T"], c["E1_T"], fraction=DROW["D6"]["delta"], level=lvl) if ok else "NOT RE-LABELLABLE (reproduction failed)"
        if key.startswith("fund|"): legf.append(legv[0]); newf.append(new)
        sens = {"D6=%g" % d: KR.rule_t1h3_cell(T(c["dE0"]), T(c["dE1"]), c["E0_H1"], c["E1_H1"], c["E0_T"], c["E1_T"], fraction=d, level=lvl) for d in DROW["D6"]["sensitivity"]}
        row("T1 H3 cell", p, key, c["cell_verdict"], new, dict(dE0_vci=r3(T(c["dE0"])), dE1_vci=r3(T(c["dE1"])), E1_H1=round(c["E1_H1"], 4)), "R-T1H3 with D6", sens)
    legH3 = "SURVIVES" if "HALF-LIFE" in legf else ("FALSIFIED" if all(x in ("LEVEL", "NO-DROP") for x in legf) else "NOT DECIDABLE")
    ok = legH3 == H3["verdict"]; ok_all &= ok
    row("T1 H3", p, "H3 verdict (fund cells)", H3["verdict"], KR.rule_t1_agg_h3(newf) if ok else "NOT RE-LABELLABLE (reproduction failed)", {}, "T1 aggregate over re-labelled fund cells")
    gate("G-REPRO T1", ok_all, "H1 cells + aggregates, H3 cells + aggregate, H5 re-run on stored summaries for all four arms")


# ================================================================================================ T8 (F16)
def fam_t8():
    d = R2 + "/T8/receipts/pod2"; J = gjson(d + "/RECEIPT_T8_judge.json"); F = gjson(d + "/RECEIPT_T8_fit.json"); B = gjson(d + "/RECEIPT_T8_build.json")
    rows_ = []
    for q in sorted(glob.glob(d + "/RECEIPT_T8_null_*.json")): rows_ += gjson(q)["rows"]
    rows_.sort(key=lambda x: x["r"]); assert [x["r"] for x in rows_] == list(range(500))
    M = np.array([x["M"] for x in rows_]); cellnull = {"%s_%s" % (m, t): np.array([x["%s_%s" % (m, t)] for x in rows_]) for m in ("R", "L") for t in ("NET", "LONG", "SHORT")}
    overall, tv, mt, crit = LEG.t8(F, M, cellnull, B)
    ok = overall == J["T8"] and all(tv[t]["verdict"] == J["target"][t]["verdict"] for t in tv) and all(mt[k]["verdict"] == J["model_target"][k]["verdict"] for k in mt)
    gate("G-REPRO T8", ok, dict(legacy=overall, stored=J["T8"]))
    cells = {k: dict(point=v["pool"]["r"], ci_k0=tuple(v["pool"]["ci95_k0"]), ci_k9=tuple(v["pool"]["ci95_k9"])) for k, v in F["cells"].items() if v["target"] != "CARRY"}
    stored = "FAIL (with the frozen consequence 'cannot predict')" if J["T8"] == "FAIL" else J["T8"]
    new = KR.rule_t8_reading(J["T8"], cells, margin=margin("D7"), level=LEVEL95) if ok else "NOT RE-LABELLABLE (reproduction failed)"
    excl = {}
    for k, c in cells.items():
        r0 = EL.one_sided(EL.Interval(point=c["point"], lo=c["ci_k0"][0], hi=c["ci_k0"][1], level=LEVEL95), margin=margin("D7"), material_side="upper")["label"]
        r9 = EL.one_sided(EL.Interval(point=c["point"], lo=c["ci_k9"][0], hi=c["ci_k9"][1], level=LEVEL95), margin=margin("D7"), material_side="upper")["label"]
        excl[k] = dict(r=round(c["point"], 5), ci_k0=r3(c["ci_k0"]), ci_k9=r3(c["ci_k9"]), usefulness_excluded=bool(r0 == EL.WITHIN_MARGIN and r9 == EL.WITHIN_MARGIN))
    sens = {"D7=%g" % dd: KR.rule_t8_reading(J["T8"], cells, margin=margin("D7", dd), level=LEVEL95) for dd in DROW["D7"]["sensitivity"]}
    row("T8", d + "/RECEIPT_T8_judge.json", "T8 overall", stored, new, dict(cells=excl, n_cells_usefulness_not_excluded=sum(1 for v in excl.values() if not v["usefulness_excluded"])), "R-T8 with D7 = %g" % DROW["D7"]["delta"], sens)


# ================================================================================================ judge_v4 (F21) + decision documents
def fam_v4():
    ok_all = True; main = None
    for fn in ("JUDGE_v4.json", "JUDGE_v4_g3_s2027.json", "JUDGE_v4e_hardened.json", "JUDGE_v4e_informational.json"):
        p = V4 + "/receipts/" + fn; J = gjson(p)
        if fn == "JUDGE_v4.json": main = J
        for key, st in J["verdicts"].items():
            con, seat = key.split("|")
            r = [J["contrasts"].get("%s|%s|s%s" % (con, seat, s)) for s in ("42", "2027")]
            if any(x is None for x in r): row("v4", p, key, st, "NOT RE-LABELLABLE (field absent: contrast seed)", {}, "R-V4"); continue
            leg = LEG.v4_verdict(r); ok = leg.split(" ")[0] == st.split(" ")[0]; ok_all &= ok
            if not ok: row("v4", p, key, st, "NOT RE-LABELLABLE (reproduction failed)", dict(legacy=leg), "R-V4"); continue
            cells = [(x["delta"], x["ci95"][0], x["ci95"][1]) for x in r]
            new = KR.rule_v4(cells, margin=margin("D1"), level=LEVEL95)
            sens = {"D1=%g" % d: KR.rule_v4(cells, margin=margin("D1", d), level=LEVEL95) for d in DROW["D1"]["sensitivity"]}
            row("v4", p, "%s (frozen window)" % key, st, new, dict(cells=[r3(c) for c in cells]), "R-V4 with D1 = %g" % DROW["D1"]["delta"], sens)
            e = [J.get("contrasts_extended", {}).get("%s|%s|s%s" % (con, seat, s)) for s in ("42", "2027")]
            if all(x is not None for x in e):
                ce = [(x["delta"], x["ci95"][0], x["ci95"][1]) for x in e]
                row("v4 extended (secondary)", p, "%s (extended window)" % key, "(C) UNDECIDED" if LEG.v4_verdict(e).startswith("(C)") else LEG.v4_verdict(e), KR.rule_v4(ce, margin=margin("D1"), level=LEVEL95),
                    dict(cells=[r3(c) for c in ce]), "R-V4 with D1 (secondary window; stored JSON has no verdict for it — legacy rule recomputed)")
    gate("G-REPRO v4", ok_all, "judge_v4 verdict expression re-run on stored per-seed contrasts in four receipts")
    # decision documents that restate the (C) as 'indistinguishable'
    docs = [("docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md", "全量重训(正确数据/特征/口径)的书与在役形态统计上不可区分"),
            ("docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md", "与在役形态在书层统计上不可区分"),
            ("docs/STATUS_three_questions_2026-09-12.md", "⇒ **(C) 不可区分**"),
            ("docs/STATUS_three_questions_2026-09-12.md", "v4 全量重训 vs 在役 (C) 不可区分"),
            ("docs/RULINGS_requested_2026-09-12.md", "正确口径下 (C) 不可区分"),
            ("docs/RUNBOOK_monthly_retrain_2026-10.md", "在役模型腿在正确口径下 (C) 不可区分")]
    seat_cells = {seat: [(main["contrasts"]["A1-A0|%s|s%s" % (seat, s)]["delta"], *main["contrasts"]["A1-A0|%s|s%s" % (seat, s)]["ci95"]) for s in ("42", "2027")] for seat in ("dyn", "fix")}
    cited = {"dyn": [(0.061, -0.168, 0.287), (0.048, -0.171, 0.270)], "fix": [(0.005, -0.076, 0.087), (-0.010, -0.102, 0.088)]}   # RESULT_v4_chain L10 as written
    num_ok = all(abs(a_ - b_) < 5e-4 for seat in cited for c, r in zip(cited[seat], seat_cells[seat]) for a_, b_ in zip(c, r))
    gate("G-PROSE-NUMBERS v4", num_ok, dict(receipt={k: [r3(c) for c in v] for k, v in seat_cells.items()}, cited_in_RESULT_v4_chain_L10=cited))
    cells = seat_cells["dyn"]
    for rel, needle in docs:
        text = gread(REPO + "/" + rel).decode("utf-8").split("\n"); ln = [i + 1 for i, l in enumerate(text) if needle in l]
        if len(ln) != 1: row("v4 decision document", REPO + "/" + rel, needle, "(anchor not unique: %d)" % len(ln), "NOT RE-LABELLABLE (anchor)", {}, "R-PROSE"); continue
        per_seat = {seat: KR.rule_v4(seat_cells[seat], margin=margin("D1"), level=LEVEL95) for seat in ("dyn", "fix")}
        new = per_seat["dyn"] if per_seat["dyn"] == per_seat["fix"] else "dyn %s / fix %s" % (per_seat["dyn"], per_seat["fix"])
        row("v4 decision document", REPO + "/" + rel, "L%d: …%s…" % (ln[0], needle), "(C) 不可区分 (restated from (C) UNDECIDED)", new, dict(A1_A0={k: [r3(c) for c in v] for k, v in seat_cells.items()}, per_seat=per_seat),
            "R-PROSE → R-V4 with D1 (A1−A0 both seats, JUDGE_v4.json)", {"D1=%g" % d: {seat: KR.rule_v4(seat_cells[seat], margin=margin("D1", d), level=LEVEL95) for seat in ("dyn", "fix")} for d in DROW["D1"]["sensitivity"]})


# ================================================================================================ compliant families (F08 T3, F24 R22 v2)
def fam_compliance():
    p = R2 + "/T3/receipts/PASSIVE_REV.json"; R = gjson(p); j = R["results"]["R1_primary"]["judgement"]
    lo, hi = j["ci95"]; v = "PASS" if hi < j["gate_bps"] else ("FAIL" if lo > j["gate_bps"] else "UNDECIDABLE")
    gate("G-COMPLY T3", v == j["verdict"], dict(recomputed=v, stored=j["verdict"]))
    row("T3 (compliant)", p, "R1_primary c_eff vs 1.6", j["verdict"], "INCONCLUSIVE" if v == "UNDECIDABLE" else v, dict(c_eff=j["c_eff_point"], ci95=j["ci95"]), "R-COMPLY (CI-based threshold test; UNDECIDABLE ≡ INCONCLUSIVE)")
    p2 = RS + "/parity_replay_2026-09-12/receipts/MATERIALITY_v2_dg_1788624000_1789200000.json"; M = gjson(p2)
    g = KL._File(RS + "/parity_replay_2026-09-12/devices/materiality_probe_v2.py"); gread(RS + "/parity_replay_2026-09-12/devices/materiality_probe_v2.py")
    ns = dict(); exec(compile("\n".join([g.stmt("EFF_LO, EFF_HI = 0.02, 0.60"), g.stmt("SCALE_FAR = EFF_LO / 3.0"), g.stmt("SCALE_COMPARABLE = EFF_HI / 3.0"), g.funcdef("def scale_word(U):")]), "<legacy R22 v2>", "exec"), ns)
    ok_all = True
    for pair, v2 in M["results"].items():
        rd = v2["reading"]; sw = ns["scale_word"](rd["U_endpoint"]); ok = sw == rd["scale_statement"]; ok_all &= ok
        e = EL.equivalence(EL.Interval(point=rd["mean_dg"], lo=rd["ci95"][0], hi=rd["ci95"][1], level=LEVEL95), margin=margin("D9"))["label"]
        row("R22 v2 (compliant)", p2, pair, rd["scale_statement"], "EQUIVALENT" if e == EL.EQUIVALENT else e, dict(mean=rd["mean_dg"], ci95=r3(rd["ci95"]), U_endpoint=rd["U_endpoint"]),
            "R-COMPLY: module R-EQ at D9 = %.6g (strict) vs frozen closed boundary" % DROW["D9"]["delta"], note="scale statement recomputed: %s" % sw)
    gate("G-COMPLY R22 v2", ok_all, "scale_word re-run on stored U_endpoint")


# ================================================================================================ admission families and results not yet committed
def fam_admission():
    p = R3 + "/L4/receipts/pod2/RECEIPT_L4_run.json"; R = gjson(p)
    row("L4 (admission)", p, "study verdict", "admission: " + R["verdict"]["study"], "admission: " + R["verdict"]["study"], dict(arms_PASS_unadj=R["verdict"]["arms_PASS_unadj"]), "none: admission verdict, not an equivalence claim")
    p2 = R3 + "/L4b/receipts/pod2/RECEIPT_L4b_marks.json"; X = gjson(p2)
    row("L4b (admission)", p2, "F2 statement", "admission: " + X["F2_statement"], "admission: " + X["F2_statement"], {}, "none: admission statement")
    vocab = re.compile(gjson(HERE + "/FACT_TABLE_K2.json")["vocabulary_regex"])
    for rel in ("multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md", "multi_asset/exports/research/uplift_r3_2026-09-13/L4b/RESULT_L4b.md"):
        text = gread(REPO + "/" + rel).decode("utf-8").split("\n"); hits = [i + 1 for i, l in enumerate(text) if vocab.search(l)]
        GATES["R-PROSE %s" % rel] = dict(PASS=True, detail=dict(frozen_vocabulary_hits=hits))
    text = gread(REPO + "/multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md").decode("utf-8").split("\n")
    ln = [i + 1 for i, l in enumerate(text) if "ρ to A0 ≈ 0" in l]
    row("L4 prose (outside the frozen vocabulary)", REPO + "/multi_asset/exports/research/uplift_r3_2026-09-13/L4/RESULT_L4.md", "L%s: 'ρ to A0 ≈ 0'" % ",".join(map(str, ln)), "ρ ≈ 0 (point estimates)",
        "NOT RE-LABELLABLE (no frozen δ for a correlation)", {}, "R-PROSE (supplementary scan; a δ for ρ was not declared before the freeze and is not added now)")
    for fam, why in (("P2 S2 (F22)", "no committed S2 table yet; adopt the module before p2_s2_tables runs"), ("L2 (F18)", "no committed judge result yet; declare an absence margin or use NOT ESTABLISHED wording before the judge runs")):
        row(fam, None, "—", "—", "—", {}, "adoption only", note=why)


def render(out):
    e = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
    L = ["> **创建:** %s | **Session:** FX-EVAL (K2) | **状态:** 重标提案表(机械套用冻结 δ 表 sha %s; 不改任何 RESULT 原文; 由 lead 复审后应用) | **作废条件:** 被重标收据或冻结 δ 表改变(逐文件 sha 见 JSON inputs)" % (out["built_utc"], DELTA_SHA[:8]),
         "", "# K2 重标表(提案)", "",
         "装置 `k2_relabel.py`(只读; 每个输入先 guarded 读并记 sha)。每个家族先过 **G-REPRO**: 用 C2 钉住的逐字旧谓词在存储数字上重算, 必须复现存储标签, 否则该家族不给新标签。新标签 = `k2_rules.py`(冻结规则) × `equivalence_labels.py` × 冻结主 δ; 敏感性列只报不定标签。",
         "", "状态词: **WITHDRAWN** = 原标签断言的「无差 / 不重要 / 同亏 / 无效应 / (点估计)重要」在区间与带下不成立; **REFINED** = 保留装置自己的检出, 带内补「经济上可忽略」; **UNCHANGED** = 断言类别不变(可能由点估计变为区间确立); **NOT_RELABELLABLE** / **NO_CLAIM** 见各行。", "",
         "## 门", "", "| 门 | PASS | 细节 |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % (e(k), v["PASS"], e(json.dumps(v["detail"], ensure_ascii=False))[:300]) for k, v in out["gates"].items()]
    import collections
    cnt = collections.Counter((r["family"], r["status"]) for r in out["rows"])
    L += ["", "## 计数", "", "| 家族 | 状态 | 行数 |", "|---|---|---|"] + ["| %s | %s | %d |" % (e(f), st, n) for (f, st), n in sorted(cnt.items())]
    order = ["WITHDRAWN", "REFINED", "CHANGED", "STRENGTHENED", "NOT_RELABELLABLE", "UNCHANGED", "NO_CLAIM"]
    for st in order:
        rows = [r for r in out["rows"] if r["status"] == st]
        if not rows: continue
        L += ["", "## %s(%d 行)" % (st, len(rows)), "", "| 家族 | 条目 | 原标签 | 新标签(提案) | 数字 | 规则 | 敏感性(不定标签) | 收据 |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            L.append("| %s | %s | %s | **%s** | %s | %s | %s | `%s` |" % (e(r["family"]), e(r["item"]), e(r["stored_label"]), e(r["new_label"]), e(json.dumps(r["numbers"], ensure_ascii=False))[:320],
                                                                   e(r["rule"]), e(json.dumps(r["sensitivity"], ensure_ascii=False)), e((r["result"] or "—").replace("multi_asset/exports/research/", ""))))
    open(HERE + "/RELABEL_TABLE_K2.md", "w").write("\n".join(L) + "\n")


def main():
    t0 = time.time()
    for f in (fam_t4, fam_t2, fam_t5c, fam_t5d, fam_t5b, fam_t5add, fam_t1, fam_t8, fam_v4, fam_compliance, fam_admission): f()
    changed = [r for r in ROWS if r["changed"]]
    repro_ok = all(v["PASS"] for k, v in GATES.items() if k.startswith("G-"))
    out = dict(tool="k2_relabel.py", built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), head=subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
               delta_table_sha256=DELTA_SHA, inputs=INPUTS, gates=GATES, rows=ROWS, n_rows=len(ROWS), n_changed=len(changed), all_gates_pass=repro_ok,
               statement="proposals only; no RESULT file edited; δ and rules exactly as frozen at adeda8e7")
    json.dump(out, open(HERE + "/RELABEL_TABLE_K2.json", "w"), indent=1, ensure_ascii=False, default=float)
    render(out)
    print("GATES", json.dumps({k: v["PASS"] for k, v in GATES.items()}, ensure_ascii=False))
    for r in changed: print("%s | %s | %s | %s -> %s" % (r["status"], r["family"], r["item"][:90], r["stored_label"], r["new_label"]))
    import collections
    print("SUMMARY k2_relabel rows=%d changed=%d status=%s gates_pass=%s wall=%.1fs" % (len(ROWS), len(changed), dict(collections.Counter(r["status"] for r in ROWS)), repro_ok, time.time() - t0))
    sys.exit(0 if repro_ok else 1)


if __name__ == "__main__":
    main()
