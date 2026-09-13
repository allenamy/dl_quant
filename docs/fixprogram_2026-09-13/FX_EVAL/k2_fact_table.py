#!/usr/bin/env python3
"""k2_fact_table.py — FIXPROGRAM 2026-09-13 item K2 (FX-EVAL), §0.1 fact table. READ-ONLY on every file it opens.

Locates, by exact substring (never by remembered line number), every label predicate in current research use that emits a
"no difference / not material / indistinguishable / same loss / non-inferior" style label, plus the compliant and out-of-scope
neighbours needed to bound the family. For each anchor it records file:line, the verbatim source line, the file's guarded sha256
(refuses APFS-dataless / short reads, T6 guard rule) and the HEAD blob id. An anchor that is absent or not unique is a hard error.
It opens device code, preregistrations and decision documents only; it opens no result receipt and prints no result number.

Usage: python3 k2_fact_table.py            (writes FACT_TABLE_K2.json and FACT_TABLE_K2.md beside itself; prints one SUMMARY line)
"""
import os, sys, json, stat, hashlib, subprocess, re, time

REPO = "/Users/haosiyu/Desktop/quant_research"
HERE = os.path.dirname(os.path.abspath(__file__))
R2 = "multi_asset/exports/research/uplift_r2_2026-09-13"
R3 = "multi_asset/exports/research/uplift_r3_2026-09-13"
V4 = "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
PR = "multi_asset/exports/research/parity_replay_2026-09-12"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)


def guarded_sha(rel):
    p = os.path.join(REPO, rel); st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE %s: APFS dataless" % rel)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE %s: read %d of %d bytes" % (rel, n, st.st_size))
    return h.hexdigest()


def head_blob(rel):
    r = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD:" + rel], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def locate(rel, needle):
    lines = open(os.path.join(REPO, rel), encoding="utf-8").read().split("\n")
    hits = [i + 1 for i, s in enumerate(lines) if needle in s]
    if len(hits) != 1: raise SystemExit("ANCHOR %s in %s: %d hits %s" % (needle[:60], rel, len(hits), hits[:5]))
    return hits[0], lines[hits[0] - 1].strip()


# class vocabulary (definitions are written into the table)
CLASSES = {
    "SIG-ONLY-NULL": "a no-difference label issued because a CI contains 0 (or a significance gate failed); no equivalence band",
    "POINT-IN-BAND": "a no-difference label issued because a POINT estimate lies inside a band; the band exists but the CI is ignored",
    "POINT-ONLY-LINE": "a one-sided 'not material' label issued because a POINT estimate is below a materiality line; the CI is ignored",
    "CI-OVERLAP-SAME": "a 'same' label issued because one book's point estimate lies inside the other's CI; no band, not a test of the difference",
    "LOSS-WITHOUT-SIGN": "a 'loss' label that does not require the realised mean of the book(s) named to be negative (K1 family)",
    "BAND-NOT-GATING": "an equivalence band exists and is computed, but the label it should gate is issued without it",
    "PRECEDENCE": "the no-difference branch is evaluated before the direction branches, so it can override a significant (A)/(B)",
    "ABSENT-AS-NULL": "a missing statistic (None / no rows) falls through to the 'not material' branch",
    "FAILED-GATE-AS-ABSENCE": "a failed detection/admission gate is written up as absence of the effect, without an upper bound below a usefulness line",
    "PROSE-EQUIVALENCE": "the device label is honest (UNDECIDED), but a decision document restates it as 'indistinguishable'",
    "COMPLIANT": "the label is CI-based against an explicit band or economic line in the direction of the claim",
    "OUT-OF-SCOPE": "deterministic tolerance, percentile position, set overlap, admission or descriptive output: not a sampling-based no-difference claim",
}

ROWS = [
    # ------------------------------------------------------------------ uplift_r2
    dict(id="F01", line="T4", title="king col80 v0/v1 book+IC verdict", classes=["SIG-ONLY-NULL"],
         labels=["MATERIAL", "NOT MATERIAL (at this resolution)"],
         statistic="(A) book Δg(K1−K0) mean, C0 base, KING_LIVE window, seeds 42 & 2027; (B) ΔIC(K1−K0) mean, KING_LIVE",
         ci="CI95 UTC-day block bootstrap NB 2000 (r18 boot)", band="none (the CI half-width is reported as 'resolution')",
         result=[R2 + "/T4/receipts/RECEIPT_T4_judge.json"], relabel="yes: D1 on (A), D4 on (B), joint rule R-T4",
         anchors=[(R2 + "/T4/devices/t4_judge.py", 'def excl0(ci): return bool(ci[0] > 0 or ci[1] < 0)'),
                  (R2 + "/T4/devices/t4_judge.py", 'condA = bool(all(x["ci95_excl0"] for x in A_c0) and (np.sign(A_c0[0]["dg"]) == np.sign(A_c0[1]["dg"])))'),
                  (R2 + "/T4/devices/t4_judge.py", 'condB = bool(B_ic["ci95_excl0"])'),
                  (R2 + "/T4/devices/t4_judge.py", 'verdict = "MATERIAL" if (condA or condB) else "NOT MATERIAL (at this resolution)"'),
                  (R2 + "/T4/PREREG_T4_king_feature_skew_2026-09-13.md", "否则 **NOT MATERIAL(在本分辨率下)**")]),
    dict(id="F02", line="T5c", title="September replay vs deployed readings", classes=["CI-OVERLAP-SAME", "LOSS-WITHOUT-SIGN"],
         labels=["STRATEGY'S OWN LOSS (king chain)", "DEPLOYMENT DIFFERENCE", "SAME DIRECTION WITH A GAP", "UNDECIDABLE"],
         statistic="D_K, R_K window means and paired mean(D_K − R_K), per outcome (price/carry/cost/net), per seed",
         ci="CI95 UTC-day block bootstrap B 2000 (k 81 levels, k 87 diff)", band="none; no sign requirement for 'LOSS'",
         result=[R2 + "/T5c/receipts/pod2/RECEIPT_T5c_bridge.json"], relabel="yes: shared-loss rule R-LOSS with D1",
         anchors=[(R2 + "/T5c/devices/t5c_bridge.py", "same = bool(mean_dk[1] <= mean_rk[0] <= mean_dk[2]); gap = bool(diff[1] > 0 or diff[2] < 0)"),
                  (R2 + "/T5c/devices/t5c_bridge.py", "label = {(True, False): \"STRATEGY'S OWN LOSS (king chain)\""),
                  (R2 + "/T5c/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md", "- **SAME-LOSS(价格)** ⇔ 窗内 R_K 价格均值落在 D_K 价格均值的 CI95 内。")]),
    dict(id="F03", line="T5d (in flight, K1 owner)", title="IV-corrected T5c readings", classes=["BAND-NOT-GATING"],
         labels=["STRATEGY'S OWN LOSS (king chain, target layer)", "BOTH LOST, DEPLOYMENT GAP", "BOTH LOST, UNDECIDABLE", "NOT A SHARED LOSS (...)", "SAME LEVEL"],
         statistic="as F02 on three calibers (T5C / FIX / REG)", ci="CI95 UTC-day block bootstrap B 2000",
         band="δ = 0.25 bps/anchor (PREREG_T5d §6.2), computed as `equiv` but the OWN-LOSS / SAME LEVEL labels are gated by `same` (CI overlap), not by `equiv`",
         result=[], relabel="no (no complete committed result; K1 owner) — reported to lead",
         anchors=[(R2 + "/T5d/devices/t5d_bridge.py", "equiv = bool(-DELTA_EQ <= diff[1] and diff[2] <= DELTA_EQ)"),
                  (R2 + "/T5d/devices/t5d_bridge.py", "label = \"BOTH LOST, DEPLOYMENT GAP\" if gap else (\"STRATEGY'S OWN LOSS (king chain, target layer)\" if same else \"BOTH LOST, UNDECIDABLE\")"),
                  (R2 + "/T5d/devices/t5d_bridge.py", "loss_d = loss_r = None; label = \"DEPLOYMENT GAP\" if gap else (\"SAME LEVEL\" if same else \"UNDECIDABLE\")"),
                  (R2 + "/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md", "- **经济等价带** δ = 0.25 bps/锚")]),
    dict(id="F04", line="T5b Q1", title="FTRIM frozen-residual carry reading", classes=["POINT-ONLY-LINE"],
         labels=["FROZEN-RESIDUAL-MATERIAL", "NOT MATERIAL"], statistic="mean over W1 of C_FROZ carry (positive = paid), bps/anchor/unit gross",
         ci="CI95 UTC-day block (k 501) reported, not used by the label", band="one-sided line 0.05 applied to the point estimate",
         result=[R2 + "/T5b/receipts/RECEIPT_T5b_q1.json"], relabel="yes: one-sided rule R-LINE with D8",
         anchors=[(R2 + "/T5b/devices/t5b_q1.py", 'reading=("FROZEN-RESIDUAL-MATERIAL" if x.mean() >= 0.05 else "NOT MATERIAL")'),
                  (R2 + "/T5b/SPEC_T5b.md", "- **FROZEN-RESIDUAL-MATERIAL ⇔ X̄ ≥ 0.05; 否则 NOT MATERIAL。**")]),
    dict(id="F05", line="T5b Q3", title="executor-added freeze carry reading", classes=["POINT-ONLY-LINE", "ABSENT-AS-NULL"],
         labels=["EXECUTOR-ADDED-FREEZE-MATERIAL", "NOT MATERIAL"], statistic="mean of GAP_EXECFREEZE over W1 ∩ NORMAL anchors, bps/anchor/unit gross",
         ci="CI95 UTC-day block (k 601) reported, not used by the label", band="one-sided line 0.05 on the point estimate; mean None ⇒ NOT MATERIAL",
         result=[R2 + "/T5b/receipts/RECEIPT_T5b_exec.json"], relabel="yes: R-LINE with D8",
         anchors=[(R2 + "/T5b/devices/t5b_exec.py", 'READ3["PRIMARY_GAP_EXECFREEZE"]["reading"] = ("EXECUTOR-ADDED-FREEZE-MATERIAL" if (p["mean"] is not None and p["mean"] >= 0.05) else "NOT MATERIAL")'),
                  (R2 + "/T5b/SPEC_T5b.md", "EXECUTOR-ADDED-FREEZE-MATERIAL ⇔ Ȳ ≥ 0.05 bps / 锚 / 单位 gross; 否则 NOT MATERIAL。")]),
    dict(id="F06", line="T5 ADDENDUM 1", title="H2b proxy share reading", classes=["POINT-IN-BAND"],
         labels=["NEGLIGIBLE", "SMALL", "NOT NEGLIGIBLE"], statistic="Shapley φ_K1 share of the deployed−replay carry gap, per seed",
         ci="CI95 (boot_ratio k 58) stored beside the point; label reads the point only", band="|share| ≤ 0.05 (ADDENDUM_1_SPEC L9) on the point",
         result=[R2 + "/T5/receipts/pod2/RECEIPT_T5_addendum1_h2b.json"], relabel="yes: R-EQ with D5",
         anchors=[(R2 + "/T5/devices/t5_addendum_h2b.py", 'sh_ = OUT[s]["phi_K1"]["share"][0]'),
                  (R2 + "/T5/devices/t5_addendum_h2b.py", 'OUT[s]["reading"] = ("NEGLIGIBLE" if abs(sh_) <= 0.05 else ("NOT NEGLIGIBLE" if abs(sh_) >= 0.20 else "SMALL"))'),
                  (R2 + "/T5/ADDENDUM_1_SPEC_T5_2026-09-13.md", "|φ_K1 占比| ≤ 0.05 ⇒「H2b 对本窗建模 carry 差的代理贡献可忽略」")]),
    dict(id="F07", line="T2", title="carry-net sizing judge", classes=["POINT-IN-BAND"],
         labels=["PROMOTE-candidate", "REJECT", "UNDECIDED (fails: ...)", "flag BELOW-RESOLUTION", "maxDD/HALT 'not worse' (point, declared decision rule)"],
         statistic="paired Δg(arm − A0/NW) W_ALPHA mean per seed; tail maxDD/HALT single-path points",
         ci="CI95 UTC-day block (and CI99-K)", band="verdict: none needed (UNDECIDED is not an equivalence claim); flag BELOW-RESOLUTION = |Δg| < 0.23 on the point",
         result=[R2 + "/T2/receipts/RECEIPT_T2_judge.json"], relabel="yes: equivalence axis R-EQ with D1 beside the unchanged verdict; BELOW-RESOLUTION re-read",
         anchors=[(R2 + "/T2/devices/t2_judge.py", 'o["below_resolution"] = bool(abs(o["dg"]) < RES_BPS)'),
                  (R2 + "/T2/devices/t2_judge.py", 'if any(blk[s]["below_resolution"] for s in s_): flags.append("BELOW-RESOLUTION")'),
                  (R2 + "/T2/devices/t2_judge.py", 'v = "UNDECIDED (fails: %s)" % ", ".join(fail)'),
                  (R2 + "/T2/PREREG_T2_carry_net_sizing_2026-09-13.md", "`BELOW-RESOLUTION` (|Δg| < 0.23)")]),
    dict(id="F08", line="T3", title="passive reversal cost judge", classes=["COMPLIANT"],
         labels=["PASS", "FAIL", "UNDECIDABLE"], statistic="c_eff bps per unit turnover", ci="CI95 day block",
         band="economic line 1.6 bps: PASS ⇔ CI upper < 1.6, FAIL ⇔ CI lower > 1.6", result=[R2 + "/T3/receipts/PASSIVE_REV.json"],
         relabel="no label change possible (CI-based threshold test; UNDECIDABLE ≡ INCONCLUSIVE); value checked mechanically",
         anchors=[(R2 + "/T3/devices/t3_passive_rev.py", 'if hi < GATE_BPS: v = "PASS"'),
                  (R2 + "/T3/devices/t3_passive_rev.py", 'else: v = "UNDECIDABLE"')]),
    dict(id="F09", line="T1 H1/H1fuel", title="state-mix cell verdict", classes=["SIG-ONLY-NULL", "POINT-IN-BAND"],
         labels=["EXPLAINS", "DOES-NOT-EXPLAIN", "UNDECIDED", "aggregate SURVIVES / FALSIFIED / NOT DECIDABLE"],
         statistic="MIX (mix term) and D_T (price drop), bps/anchor; ratio MIX/D_T point", ci="Bonferroni verdict interval vci (family K)",
         band="DOES-NOT-EXPLAIN ⇔ D_T vci_hi < 0 ∧ (MIX vci ∋ 0 ∨ MIX/D_T < 0.25 on points)", result=[R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json"],
         relabel="yes: R-T1H1 with D6", anchors=[(R2 + "/T1/devices/t1_judge.py", 'elif sd_["vci_hi"] < 0 and (sm_["vci_lo"] <= 0 <= sm_["vci_hi"] or ratio < 0.25): v = "DOES-NOT-EXPLAIN"'),
                                                  (R2 + "/T1/devices/t1_judge.py", 'if all(c == "DOES-NOT-EXPLAIN" for c in cells): return "FALSIFIED"'),
                                                  (R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**DOES-NOT-EXPLAIN** ⇔ D_T 判决区间上界 < 0 且(MIX 判决区间含 0 或 MIX/D_T < 0.25)")]),
    dict(id="F10", line="T1 H3", title="half-life cell verdict", classes=["POINT-IN-BAND"],
         labels=["HALF-LIFE", "LEVEL", "NO-DROP", "UNDECIDED", "aggregate SURVIVES / FALSIFIED / NOT DECIDABLE"],
         statistic="ΔE1 (late-lag edge change) against 0.25·|E1_H1|", ci="verdict interval vci (unused by NO-DROP)", band="NO-DROP ⇔ ΔE1 point ≥ −0.25·|E1_H1|",
         result=[R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json"], relabel="yes: R-T1H3 with D6",
         anchors=[(R2 + "/T1/devices/t1_judge.py", 'elif dE1["point"] >= -0.25 * abs(E1H): v = "NO-DROP"'),
                  (R2 + "/T1/devices/t1_judge.py", 'H3["verdict"] = "SURVIVES" if "HALF-LIFE" in fcells else ("FALSIFIED" if all(c in ("LEVEL", "NO-DROP") for c in fcells) else "NOT DECIDABLE")'),
                  (R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**NO-DROP** ⇔ ΔE1 点估计 ≥ −0.25·|E1_H1|")]),
    dict(id="F11", line="T1 H5", title="same-mechanism verdict", classes=["SIG-ONLY-NULL", "POINT-IN-BAND"],
         labels=["SURVIVES (different mechanisms)", "FALSIFIED (same mechanism)", "NOT DECIDABLE"],
         statistic="Δπ and Δσs (LIVE − 2023) on D2 / REAL / REAL scaled; |c1 difference|", ci="verdict interval vci",
         band="FALSIFIED ⇔ |c1d| ≤ 0.20 ∧ all six vci ∋ 0 ∧ |points| ≤ 0.25·|reference points|",
         result=[R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json"], relabel="yes: R-T1H5 with D6",
         anchors=[(R2 + "/T1/devices/t1_judge.py", "elif c1d <= 0.20 and not any(excl(x) for x in (dpD, dsD, dpR, dsR, dpRs, dsRs))"),
                  (R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**H5 证伪(相同)** ⇔ |c1 差| ≤ 0.20 且四个判决区间都含 0")]),
    dict(id="F12", line="T1 H4", title="compensation-ratio verdict", classes=["COMPLIANT"],
         labels=["SURVIVES", "FALSIFIED", "NOT DECIDABLE"], statistic="ρ = price/carry compensation ratio vs half the H1 ratio", ci="verdict interval vci",
         band="FALSIFIED ⇔ vci_lo ≥ 0.5·ρ_H1 on all three live instruments (one-sided, CI-based)", result=[R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json"],
         relabel="no (compliant; reference ρ_H1 at its point — declared boundary)",
         anchors=[(R2 + "/T1/devices/t1_judge.py", 'elif H4["rho_LIVE_D2"]["vci_lo"] >= half and H4["rho_LIVE_REAL"]["vci_lo"] >= half and H4["rho_LIVE_REAL_scaled"]["vci_lo"] >= half: v = "FALSIFIED"')]),
    dict(id="F13", line="T1 H2", title="settlement-interval engineering check", classes=["OUT-OF-SCOPE"],
         labels=["FALSIFIED", "SURVIVES", "NOT DECIDABLE"], statistic="row-level equality of recorded vs snapped intervals", ci="none (deterministic)",
         band="explicit tolerance (all mismatches zero; relative diff ≤ 1e-3)", result=[R2 + "/T1/receipts/RECEIPT_T1_h2.json"], relabel="no (deterministic tolerance)",
         anchors=[(R2 + "/T1/devices/t1_h2.py", '"FALSIFIED" if (H2["all_mismatch_live_zero"] and H2["all_rel_diff_recorded_le_1e-3"]) else')]),
    dict(id="F14", line="T1 position / addendum", title="live window percentile readings", classes=["OUT-OF-SCOPE"],
         labels=["ANOMALOUS", "WITHIN RANGE GIVEN STATE", "INTERMEDIATE", "ANOMALOUS-LOW", "WITHIN RANGE"],
         statistic="percentile of the live-window mean among historical window means", ci="none (position in a reference distribution)",
         band="explicit percentile cut-offs 0.025 / 0.10", result=[R2 + "/T1/receipts/pod2/RECEIPT_T1_judge.json", R2 + "/T1/receipts/pod2/RECEIPT_T1_addendum1.json"],
         relabel="no (not a two-sample contrast; the reading already carries window-sampling variability)",
         anchors=[(R2 + "/T1/devices/t1_judge.py", 'POS["reading"] = ("ANOMALOUS" if all(cp[k] < 0.025 for k in ("REAL", "REAL_scaled", "D2")) else "WITHIN RANGE GIVEN STATE"'),
                  (R2 + "/T1/devices/t1_add_pod.py", 'res["price_reading"] = "ANOMALOUS-LOW" if all(x < 0.025 for x in pps) else ("WITHIN RANGE" if all(x >= 0.10 for x in pps) else "INTERMEDIATE")')]),
    dict(id="F15", line="T5", title="TC2 name overlap reading", classes=["OUT-OF-SCOPE"],
         labels=["SAME NAMES", "PARTIAL", "DIFFERENT NAMES"], statistic="M1 = loss share of August cohort names (full population, no resampling)", ci="none",
         band="explicit cut-offs 0.5 / 0.2 on a deterministic ratio", result=[R2 + "/T5/receipts/pod2/RECEIPT_T5_bridge.json"], relabel="no (deterministic descriptor)",
         anchors=[(R2 + "/T5/devices/t5_bridge.py", 'reading=("SAME NAMES" if M1 >= 0.5 else ("DIFFERENT NAMES" if M1 <= 0.2 else "PARTIAL"))')]),
    dict(id="F16", line="T8", title="book-perception gate: FAIL written as 'cannot predict'", classes=["FAILED-GATE-AS-ABSENCE"],
         labels=["PASS", "UNDECIDED", "FAIL", "INVALID"], statistic="pooled OOS r per model × target × seed (NET / LONG / SHORT)",
         ci="CI95 k=0 and k=9 per cell (C3)", band="usefulness line r ≥ 0.03 (C1) is required to PASS; FAIL does not require r's CI upper < 0.03",
         result=[R2 + "/T8/receipts/pod2/RECEIPT_T8_judge.json", R2 + "/T8/receipts/pod2/RECEIPT_T8_fit.json"], relabel="yes: one-sided R-LINE with D7 (per cell), aggregated by T8 §8 shape",
         anchors=[(R2 + "/T8/devices/t8_judge.py", "c1 = bool(FIN(r) and r >= 0.03)"),
                  (R2 + "/T8/devices/t8_judge.py", '    overall = "FAIL"'),
                  (R2 + "/T8/PREREG_T8.md", "**后果(冻结)**: FAIL ⇒ 「在本分辨率下, 这组锚时状态(§4)与这个模型家族(§5)不能预测下一锚书收益")]),
    dict(id="F17", line="T4 live / T4b", title="live-window descriptive judges and parity gates", classes=["OUT-OF-SCOPE"],
         labels=["(descriptive only)", "gate PASS/FAIL (bitwise / tolerance)"], statistic="per-anchor deltas; bitwise equality", ci="descriptive / none",
         band="n/a", result=[], relabel="no",
         anchors=[(R2 + "/T4/devices/t4_live_judge.py", "Descriptive only; no verdict."),
                  (R2 + "/T4b/devices/t4b_live_judge.py", "Descriptive only.")]),
    # ------------------------------------------------------------------ uplift_r3
    dict(id="F18", line="L2", title="squeeze-direction gate fail labels", classes=["FAILED-GATE-AS-ABSENCE"],
         labels=["PASS", "FAIL + fail_label DIRECTION-ABSENT / UNSTABLE / NOT-BEYOND-FUNDING / VARIANCE / NULL / SHIFT / PRECONDITION"],
         statistic="G (top-decile minus population), dG vs BASE, per model × target × seed", ci="CI (boot_ci) per statistic",
         band="none: DIRECTION-ABSENT ⇐ ¬(G < 0 ∧ G_ci upper < 0); NOT-BEYOND-FUNDING ⇐ ¬(dG < 0 ∧ dG_ci upper < 0)",
         result=[], relabel="no committed judge result yet — red test + adoption before the L2 judge runs",
         anchors=[(R3 + "/L2/devices/l2_b_common.py", 'c1 = cell["G"] < 0 and cell["G_ci"][1] < 0'),
                  (R3 + "/L2/devices/l2_b_common.py", 'c3 = cell["dG"] < 0 and cell["dG_ci"][1] < 0'),
                  (R3 + "/L2/devices/l2_b_judge.py", 'fail_label = None if verdict == "PASS" else ("PRECONDITION" if not pre_ok else labels[order[depth(best)]])')]),
    dict(id="F19", line="L4", title="carry-sleeve hysteresis study verdict", classes=["OUT-OF-SCOPE"],
         labels=["PASS", "FAIL", "NOT PASS (multiplicity)"], statistic="admission rule P0–P3 per arm; nested selection",
         ci="circular 30-day block CI (P2a/P2b)", band="admission: FAIL = no arm PASS_unadj (not an equivalence claim); P3 ρ ≤ 0.30 applied to point estimates (adjacent family)",
         result=[R3 + "/L4/receipts/pod2/RECEIPT_L4_run.json"], relabel="labels: no; RESULT prose checked for equivalence wording after the δ freeze (D2/D3)",
         anchors=[(R3 + "/L4/devices/l4_run.py", 'elif not unadj: verdict = "FAIL"'),
                  (R3 + "/L4/devices/l4_run.py", "P3 = all(v is not None and math.isfinite(v) and v <= 0.30 for v in rh)")]),
    dict(id="F20", line="L4b", title="executable-marks survival", classes=["OUT-OF-SCOPE"],
         labels=["survives / no arm survives"], statistic="admission rule per arm", ci="circular block CI", band="admission; P3 ρ ≤ 0.30 on points (adjacent)",
         result=[R3 + "/L4b/receipts/pod2/RECEIPT_L4b_marks.json"], relabel="labels: no; prose checked after the δ freeze",
         anchors=[(R3 + "/L4b/devices/l4b_marks.py", 'F2_statement=("no arm survives" if not surv else "surviving arms: " + ", ".join(surv))'),
                  (R3 + "/L4b/devices/l4b_marks.py", "P3 = all(math.isfinite(x) and x <= 0.30 for s in rho.values() for x in s.values())")]),
    # ------------------------------------------------------------------ v4 chain judge and gate libraries
    dict(id="F21", line="v4 chain", title="judge_v4 verdicts and their restatement in decision documents", classes=["PROSE-EQUIVALENCE"],
         labels=["(A) PROMOTE / (A) INFO", "(B) REJECT", "(C) UNDECIDED (device) → '(C) 不可区分' (documents)"],
         statistic="paired Δg(arm − base), frozen window, per seat × seed", ci="CI95 UTC-day block bootstrap 2000",
         band="device: none needed ((C) never 'non-inferior'); documents: none (read as indistinguishable)",
         result=[V4 + "/receipts/JUDGE_v4.json", V4 + "/receipts/JUDGE_v4_g3_s2027.json", V4 + "/receipts/JUDGE_v4e_hardened.json", V4 + "/receipts/JUDGE_v4e_informational.json"],
         relabel="yes: equivalence axis R-EQ with D1 on every contrast; document readings re-stated",
         anchors=[(V4 + "/judge_v4.py", 'v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED")'),
                  ("docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md", "全量重训(正确数据/特征/口径)的书与在役形态统计上不可区分"),
                  ("docs/STATUS_three_questions_2026-09-12.md", "v4 全量重训 vs 在役 (C) 不可区分"),
                  ("docs/RULINGS_requested_2026-09-12.md", "正确口径下 (C) 不可区分"),
                  ("docs/RUNBOOK_monthly_retrain_2026-10.md", "在役模型腿在正确口径下 (C) 不可区分")]),
    dict(id="F22", line="P2 S2 (in flight)", title="gate library A6.7 verdict: '(C) indistinguishable'", classes=["POINT-IN-BAND", "PRECEDENCE"],
         labels=["(C) indistinguishable (|Δg| < 0.23)", "(A)", "(B)", "(C) UNDECIDED"], statistic="paired Δg per contrast × window, both seeds",
         ci="CI95 k=0 (k=9 re-read)", band="|Δg| < 0.23 on the POINT of either seed, evaluated before (A)/(B); 0.23 is the r15/r18 bootstrap resolution, not an economic band",
         result=[], relabel="no committed S2 table yet — red test + adoption before p2_s2_tables runs",
         anchors=[(PR + "/phase2/devices/p2_s2_lib.py", 'if any(abs(x) < RES_BPS for x in dg): return "(C) indistinguishable (|Δg| < 0.23)"'),
                  ("docs/PREREG_producer_parity_phase2_oos_2026-09-12.md", "**任一种子 |Δg| < 0.23 bps/锚/gross ⇒「(C) 不可区分」**"),
                  (R2 + "/T2/PREREG_T2_carry_net_sizing_2026-09-13.md", "The bootstrap resolution of this window is 0.23 bps/anchor (r15 §6)")]),
    dict(id="F23", line="R22 v1 (superseded)", title="materiality FIT verdict", classes=["COMPLIANT"],
         labels=["FIT-STRICT", "FIT", "PARTIALLY-FIT", "UNFIT"], statistic="U_mean = |mean| + CI half-width", ci="CI95 day block",
         band="explicit (0.002 / 0.00667 / 0.2); defect in the CI bound (|m|+half-width) already corrected by v2 (reviewer 0158f5d1)",
         result=[], relabel="no (superseded; retained byte-identical)",
         anchors=[(PR + "/devices/materiality_probe.py", "if U_mean <= FIT_STRICT_MEAN and U_max <= FIT_STRICT_MAX:")]),
    dict(id="F24", line="R22 v2", title="baseline-residual scale statement", classes=["COMPLIANT"],
         labels=["BASELINE-RESIDUAL-FAR-BELOW-0.02-0.6-SCALE", "…-COMPARABLE-TO-…", "…-ABOVE-…"], statistic="mean Δg, U_endpoint = max(|lo|, |hi|)",
         ci="CI95 day block", band="U ≤ 0.02/3 (closed boundary) — a TOST-shaped statement", result=[PR + "/RESULT_materiality_2026-09-13.md"],
         relabel="no (compliant); boundary convention noted (closed ≤ vs module strict <)",
         anchors=[(PR + "/devices/materiality_probe_v2.py", "if U <= SCALE_FAR:")]),
    dict(id="F25", line="P2 G2 gates", title="producer parity gates", classes=["OUT-OF-SCOPE"],
         labels=["gate PASS / RED"], statistic="L∞ of weights / targets", ci="none (deterministic)", band="explicit tolerance 1e-6",
         result=[PR + "/phase2/receipts/G2C_verdict.json"], relabel="no (deterministic; K3 owns its anchor binding)",
         anchors=[(PR + "/phase2/devices/p2_g2c_judge.py", 'combo_ok = all(v["combo_rc"] == 0 and v["target_live_Linf"] is not None and v["target_live_Linf"] <= 1e-6 and v["rc_line"] == "rc=0" for v in snap.values())')]),
    dict(id="F26", line="v4 chain tests", title="consumer of the (C) UNDECIDED string", classes=["OUT-OF-SCOPE"],
         labels=["assertion on '(C) UNDECIDED'"], statistic="n/a", ci="n/a", band="n/a", result=[],
         relabel="no; any adoption that renames (C) must update this assertion in the same change",
         anchors=[(V4 + "/tests_pipeline_gates.py", 'and all(v == "(C) UNDECIDED" for k, v in j["verdicts"].items() if not k.startswith("A1e"))')]),
]

# lines scanned that emit no label of the family (recorded so the boundary is explicit)
SCANNED_NO_FAMILY = {
    R2 + "/T6/devices": "PBO / DSR / nested statistics; no no-difference label (reviewer R4-R2..R4-R4 cover its reading issues)",
    R2 + "/T7/devices": "data feasibility only; no return statistic",
    R3 + "/L3/devices": "data feasibility only; no return statistic",
}
VOCAB = re.compile(r"NOT.?MATERIAL|INDISTINGUISH|indistinguish|NEGLIGIBLE|negligible|NON.?INFERIOR|non.?inferior|NOT.?WORSE|not.?worse|SAME.?LOSS|OWN LOSS|SAME LEVEL|SAME NAMES|DOES-NOT-EXPLAIN|NO-DROP|WITHIN RANGE|DIRECTION-ABSENT|NOT-BEYOND|\"CLOSES\"|不可区分|不劣|追平|持平|可忽略")

# tier 2: same vocabulary in closed programs (devices only) — listed, not re-labelled
TIER2_ROOTS = ["multi_asset/exports/research/uplift_2026-09-11", "multi_asset/exports/research/retrain_2026-09"]


def scan(root, suffix=".py", skip=("/receipts/", "/private/", "/replay_home")):
    out = []
    for dp, dn, fn in os.walk(os.path.join(REPO, root)):
        rel_dp = os.path.relpath(dp, REPO)
        if any(s.strip("/") in rel_dp.split(os.sep) for s in skip): continue
        for f in sorted(fn):
            if not f.endswith(suffix) or re.search(r" \d+\.py$", f): continue
            rel = os.path.join(rel_dp, f)
            try: txt = open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read().split("\n")
            except OSError: continue
            for i, s in enumerate(txt):
                if VOCAB.search(s): out.append(dict(file=rel, line=i + 1, text=s.strip()[:200]))
    return out


def main():
    rows = []
    for r in ROWS:
        loc = []
        for rel, needle in r["anchors"]:
            ln, src = locate(rel, needle)
            loc.append(dict(file=rel, line=ln, source=src[:400], file_sha256=guarded_sha(rel), head_blob=head_blob(rel)))
        rr = {k: v for k, v in r.items() if k != "anchors"}; rr["anchors"] = loc
        rr["result_files"] = [dict(file=p, head_blob=head_blob(p)) for p in r["result"]]
        rows.append(rr)
    scanned = {}
    for d, why in SCANNED_NO_FAMILY.items():
        hits = scan(d); scanned[d] = dict(reason=why, vocabulary_hits=hits)
    tier2 = [h for root in TIER2_ROOTS for h in scan(root)]
    prose = {}   # knowledge-base prose with the same vocabulary (aud-kb / K4 territory): per-file counts only
    for f in sorted(os.listdir(os.path.join(REPO, "docs"))) + ["../STATE.md"]:
        rel = os.path.normpath(os.path.join("docs", f))
        if not rel.endswith(".md") or not os.path.isfile(os.path.join(REPO, rel)): continue
        n = sum(1 for s_ in open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") if VOCAB.search(s_))
        if n: prose[rel] = n
    out = dict(tool="k2_fact_table.py", self_sha256=guarded_sha(os.path.relpath(os.path.abspath(__file__), REPO)),
               head=subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
               built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), classes=CLASSES, rows=rows,
               scanned_no_family=scanned, vocabulary_regex=VOCAB.pattern, tier2_closed_program_hits=tier2, prose_vocabulary_counts=prose,
               note="opens code, preregistrations and decision documents only; no receipt is opened and no result number is printed")
    json.dump(out, open(os.path.join(HERE, "FACT_TABLE_K2.json"), "w"), indent=1, ensure_ascii=False)
    L = ["> **创建:** %s | **Session:** FX-EVAL (K2) session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 事实表(先于代码; 只读码/预注册/决策文档, 未开任何结果收据) | **作废条件:** 被登记装置或文档改动(逐锚 sha 见 JSON)" % out["built_utc"],
         "", "# K2 事实表 · 「无差 / 不重要 / 不可区分 / 同亏 / 不劣」类标签谓词", "",
         "机器版: `FACT_TABLE_K2.json`(每个锚点: 文件:行、原文、guarded sha256、HEAD blob)。由 `k2_fact_table.py` 按原文子串定位(不凭行号记忆), 锚点缺失或不唯一即报错。", "",
         "## 类别", ""] + ["- **%s**: %s" % (k, v) for k, v in CLASSES.items()] + ["", "## 表", "",
         "| id | 线 | 谓词(文件:行) | 标签 | 统计量 / CI | 等价带 | 类别 | 已提交结果 | 重标 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        anc = "<br>".join("`%s:%d`" % (a["file"].replace("multi_asset/exports/research/", ""), a["line"]) for a in r["anchors"])
        res = "<br>".join("`%s`" % f["file"].replace("multi_asset/exports/research/", "") for f in r["result_files"]) or "—"
        e = lambda x: str(x).replace("|", "\\|")
        L.append("| %s | %s | %s | %s | %s / %s | %s | %s | %s | %s |" % (r["id"], e(r["line"]), anc, e("; ".join(r["labels"])), e(r["statistic"]), e(r["ci"]), e(r["band"]), ", ".join(r["classes"]), res, e(r["relabel"])))
    L += ["", "## 同一词表扫描但无该族标签的目录", ""] + ["- `%s`: %s(词表命中 %d 行)" % (d, v["reason"], len(v["vocabulary_hits"])) for d, v in scanned.items()]
    L += ["", "## 第二层: 已关闭纲领中的同族词(只列出, 本项不重标; 见报告「未证边界」)", "", "词表: `%s`" % VOCAB.pattern, "", "| 文件:行 | 原文(截 200) |", "|---|---|"]
    L += ["| `%s:%d` | %s |" % (h["file"].replace("multi_asset/exports/research/", ""), h["line"], h["text"].replace("|", "\\|")) for h in tier2]
    L += ["", "## 知识库文字中的同族词(计数; K4 / aud-kb 范围, 本项只把 F21 的四处决策文档列为重标对象)", "", "| 文件 | 命中行数 |", "|---|---|"]
    L += ["| `%s` | %d |" % (k, v) for k, v in sorted(prose.items(), key=lambda kv: -kv[1])]
    open(os.path.join(HERE, "FACT_TABLE_K2.md"), "w").write("\n".join(L) + "\n")
    n_in = sum(1 for r in rows if not set(r["classes"]) <= {"COMPLIANT", "OUT-OF-SCOPE"})
    print("SUMMARY k2_fact_table rows=%d defect_rows=%d compliant_or_out=%d anchors=%d tier2_hits=%d prose_files=%d prose_lines=%d" % (
        len(rows), n_in, len(rows) - n_in, sum(len(r["anchors"]) for r in rows), len(tier2), len(prose), sum(prose.values())))


if __name__ == "__main__":
    main()
