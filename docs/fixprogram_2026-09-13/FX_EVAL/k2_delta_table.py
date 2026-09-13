#!/usr/bin/env python3
"""k2_delta_table.py — FIXPROGRAM 2026-09-13 item K2 (FX-EVAL): the δ table and the mechanical re-label rules, written and frozen
BEFORE any affected result receipt is opened by this item. READ-ONLY on every source it cites.

Every δ is tied to a line that already existed in a committed program / preregistration / specification document (located by exact
substring; the file's first-add commit and time are recorded) or is a scripted unit conversion of such a line. No δ is chosen from a
result of the contrasts it will re-label. Numbers that the author had already seen before this freeze (from STATE.md, programme
pointers, the reviewer's report, the dispatch message, or incidental grep output) are listed in `exposure` — the freeze is not blind.

Usage: python3 k2_delta_table.py     (writes DELTA_TABLE_K2.json / .md beside itself; prints one SUMMARY line)
"""
import os, json, stat, hashlib, subprocess, math, time

REPO = "/Users/haosiyu/Desktop/quant_research"; HERE = os.path.dirname(os.path.abspath(__file__))
R2 = "multi_asset/exports/research/uplift_r2_2026-09-13"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)


def gsha(rel):
    p = os.path.join(REPO, rel); st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE dataless " + rel)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE short read " + rel)
    return h.hexdigest()


def src(rel, needle):
    lines = open(os.path.join(REPO, rel), encoding="utf-8").read().split("\n")
    hits = [i + 1 for i, s in enumerate(lines) if needle in s]
    if len(hits) != 1: raise SystemExit("SOURCE ANCHOR %r in %s: %d hits" % (needle[:50], rel, len(hits)))
    add = subprocess.run(["git", "-C", REPO, "log", "--diff-filter=A", "--format=%h %cI", "--", rel], capture_output=True, text=True).stdout.strip().split("\n")[-1]
    blame = subprocess.run(["git", "-C", REPO, "blame", "-L", "%d,%d" % (hits[0], hits[0]), "--porcelain", "HEAD", "--", rel], capture_output=True, text=True).stdout.split("\n")
    line_commit = blame[0].split(" ")[0][:8] if blame and blame[0] else None
    ctime = next((b.split(" ", 1)[1] for b in blame if b.startswith("committer-time ")), None)
    return dict(file=rel, line=hits[0], text=lines[hits[0] - 1].strip()[:300], file_sha256=gsha(rel), file_first_add=add,
                line_last_commit=line_commit, line_last_commit_utc=(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ctime))) if ctime else None))


# ------------------------------------------------------------------ scripted conversions (inputs are prereg facts, not contrast results)
G_A0 = 0.6341957; SR_A0 = 1.2912234; ANN = math.sqrt(2190.0); GROSS = 2.0          # T2 PREREG L38 (A0 s42 W_ALPHA), √2190 anchors/yr, constant_leverage_2.00
SIGMA_G = G_A0 * ANN / SR_A0
def conv(d): return dict(share_of_A0_WALPHA_net=d / G_A0, annualised_sharpe=d * ANN / SIGMA_G, nav_pct_per_year_at_gross2=d * 2190 * GROSS / 100.0)
D1 = 0.05
CONV = dict(inputs=dict(g_A0_WALPHA_s42_bps=G_A0, sharpe_A0_WALPHA_s42=SR_A0, anchors_per_year=2190, gross_over_nav=GROSS, sigma_g_bps=SIGMA_G),
            D1=conv(D1), T2_ceiling_0p11=conv(0.11), R22_EFF_LO_0p02=conv(0.02), T5d_band_0p25=conv(0.25), T2_resolution_0p23=conv(0.23))
D2 = round(conv(D1)["annualised_sharpe"], 2); D3 = GROSS * D1
IC_KING = 0.063; D4 = 0.003

DELTAS = [
    dict(key="D1", family="book_dg", unit="bps / 4h anchor / unit gross (g = net_ex / gross_total; paired Δg or a component of it: price, carry, cost)",
         delta=D1, use="two-sided R-EQ unless the rule states one-sided R-LINE",
         justification=[
             "the programme's own pre-declared materiality line for book-level effects in this unit (PROGRAM_uplift_r2 L155, written when T5b was dispatched; SPEC_T5b L62 / L122 frozen before any T5b number)",
             "economic size (scripted, CONV.D1): 7.9 % of the A0 W_ALPHA mean net 0.6341957; +0.10 annualised Sharpe at A0's σ; 2.19 % NAV per year at gross 2.0",
             "half of the T2 frozen ceiling for an entire carry-sizing redesign (0.11 bps ⇒ ≤ +0.2 Sharpe, T2 PREREG L10): a difference below half of what the programme's largest plausible structural uplift could buy is not decision-relevant",
             "inside the strategy-change scale the replay instrument was built to judge, [0.02, 0.60] bps (PREREG_parity_materiality L15)",
             "NOT the source: T4 RESULT quotes '±0.05 bps/锚' as its CI half-width (a resolution, result-derived); the coincidence is recorded, the line above is the source"],
         sensitivity=[0.02, 0.25], sensitivity_note="0.02 = R22 EFF_LO (smallest strategy change the replay was asked to judge); 0.25 = PREREG_T5d §6.2 band (≈ 39 % of A0 net — too wide to be called negligible by the L155 line). Sensitivity columns never set a label.",
         sources=[src(R2 + "/PROGRAM_uplift_r2_2026-09-13.md", "读法先冻结: 均值 ≥ 0.05 bps/锚/gross = 实质"),
                  src(R2 + "/T5b/SPEC_T5b.md", "- **FROZEN-RESIDUAL-MATERIAL ⇔ X̄ ≥ 0.05; 否则 NOT MATERIAL。**"),
                  src(R2 + "/T5b/SPEC_T5b.md", "EXECUTOR-ADDED-FREEZE-MATERIAL ⇔ Ȳ ≥ 0.05 bps / 锚 / 单位 gross; 否则 NOT MATERIAL。"),
                  src(R2 + "/T2/PREREG_T2_carry_net_sizing_2026-09-13.md", "Baseline facts carried from r15/r18 (VERIFIED there; re-asserted by the T2 judge): A0 s42 W_ALPHA g **0.6341957**"),
                  src(R2 + "/T2/PREREG_T2_carry_net_sizing_2026-09-13.md", "**Ceiling, frozen before any number (program P5).** Uncompensated carry"),
                  src("docs/PREREG_parity_materiality_2026-09-13.md", "测一个 0.02–0.6 bps/锚 的策略改动时"),
                  src(R2 + "/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md", "- **经济等价带** δ = 0.25 bps/锚")],
         applies_to=["F01 (A)", "F02 (price/carry/cost/net differences)", "F04/F05 (one-sided, as D8)", "F07", "F21", "F22 (future S2 tables)"]),
    dict(key="D2", family="book_dsharpe", unit="annualised Sharpe (per-anchor Sharpe × √2190)", delta=D2, use="two-sided R-EQ",
         justification=["D1 converted at A0 W_ALPHA σ (CONV.D1.annualised_sharpe = %.4f, rounded to 2 dp)" % conv(D1)["annualised_sharpe"],
                        "used only where a document asserts ΔSharpe equivalence (L4 / L4b prose check, P2 ΔSharpe if ever labelled)"],
         sensitivity=[round(conv(0.02)["annualised_sharpe"], 3), round(conv(0.25)["annualised_sharpe"], 3)], sources=[], applies_to=["F19/F20 prose (if any)"]),
    dict(key="D3", family="nav_dg_2x", unit="bps / 4h anchor of NAV at gross 2.0", delta=D3, use="two-sided R-EQ",
         justification=["D1 × gross 2.0 (constant_leverage_2.00); for series already levered (L4b multiplies A0 g by 2.0)"],
         sensitivity=[0.04, 0.50], sources=[], applies_to=["F19/F20 prose (if any)"]),
    dict(key="D4", family="score_dic", unit="rank-IC (per-anchor cross-sectional Spearman, window mean over anchors)", delta=D4, use="two-sided R-EQ",
         justification=["≈ 5 %% (%.1f %%) of the canonical wide-450 king score-layer IC 0.063 raw (PREREG_leg_ablation L6): a one-twentieth change in the king's ranking skill" % (100 * D4 / IC_KING),
                        "equals the project's standing minimum incremental-alpha line (#29: an added channel must earn ≥ +0.003; DLv2 acceptance prereg L55)",
                        "NOT book-economic: the IC→book mapping is refuted twice (PREREG_leg_ablation L58 §4.3), so an EQUIVALENT at D4 is a score-scale statement and cannot by itself carry 'NOT MATERIAL' for the book"],
         sensitivity=[0.0015, 0.006], sources=[src("docs/PREREG_leg_ablation_2026-08-26.md", "vs king 0.063/0.048"),
                                             src("docs/2026-07-09_DLv2_acceptance_protocol_prereg.md", "each added input/channel ≈ −0.013 unless it earns ≥ +0.003 net alpha"),
                                             src("docs/PREREG_leg_ablation_2026-08-26.md", "- **判据 §4.3 触发**: LGBM-K171 的分数 IC 是 V2MAIN 的")],
         applies_to=["F01 (B)"]),
    dict(key="D5", family="share_of_gap", unit="fraction of the deployed − replay gap attributed by Shapley (dimensionless)", delta=0.05, use="two-sided R-EQ; NOT NEGLIGIBLE established ⇔ CI beyond ±0.20",
         justification=["the addendum's own declared negligibility band |share| ≤ 0.05 (and ≥ 0.20 'not negligible'), now applied to the CI instead of the point",
                        "DISCLOSED: the spec line was committed in the same commit as its receipt (39ec7c1e) — it is not provably pre-declared; it is the only declared band for this unit"],
         sensitivity=[0.025, 0.10], sources=[src(R2 + "/T5/ADDENDUM_1_SPEC_T5_2026-09-13.md", "|φ_K1 占比| ≤ 0.05 ⇒「H2b 对本窗建模 carry 差的代理贡献可忽略」")], applies_to=["F06"]),
    dict(key="D6", family="t1_relative", unit="fraction of the T1 reference level (dimensionless)", delta=0.25, use="rules R-T1H1 (one-sided), R-T1H3 (one-sided), R-T1H5 (two-sided)",
         justification=["T1's own pre-registered relative lines (H1 ratio 0.25, H3 NO-DROP 0.25, H5 0.25), frozen before any T1 number; K2 changes only the object they are applied to (verdict interval instead of point) and makes the reference conservative where the receipt stores its interval"],
         sensitivity=[0.125, 0.50], sources=[src(R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**DOES-NOT-EXPLAIN** ⇔ D_T 判决区间上界 < 0 且(MIX 判决区间含 0 或 MIX/D_T < 0.25)"),
                                           src(R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**NO-DROP** ⇔ ΔE1 点估计 ≥ −0.25·|E1_H1|"),
                                           src(R2 + "/T1/PREREG_T1_edge_diagnosis_2026-09-13.md", "**H5 证伪(相同)** ⇔ |c1 差| ≤ 0.20 且四个判决区间都含 0")],
         applies_to=["F09", "F10", "F11"]),
    dict(key="D7", family="t8_useful_r", unit="pooled out-of-sample Pearson r (T8 §6)", delta=0.03, use="one-sided R-LINE: usefulness excluded ⇔ CI95 upper < 0.03 under k=0 and k=9",
         justification=["T8's own frozen usefulness line C1 (r ≥ 0.03), inherited from the project's perceptibility gate |corr| ≥ 0.03 (adaptive_turnover_family_closed, quoted in PREREG_T8 L16)",
                        "the frozen FAIL consequence ('cannot predict at this resolution') is an absence claim; it needs r < 0.03 to be excluded from above, which a failed C1/C3 does not establish"],
         sensitivity=[0.015, 0.06], sources=[src(R2 + "/T8/PREREG_T8.md", "- C1: `r_pool ≥ 0.03`"),
                                           src(R2 + "/T8/PREREG_T8.md", "**后果(冻结)**: FAIL ⇒ 「在本分辨率下")], applies_to=["F16"]),
    dict(key="D8", family="t5b_carry_line", unit="bps / 4h anchor / unit gross, positive = carry paid", delta=D1, use="one-sided R-LINE, material side = upper (paid ≥ 0.05)",
         justification=["identical to D1 and to SPEC_T5b's own frozen line; K2 applies it to the CI95 upper instead of the point"],
         sensitivity=[0.02, 0.25], sources=[], applies_to=["F04", "F05"]),
    dict(key="D9", family="r22_scale_far", unit="bps / 4h anchor / unit gross", delta=0.02 / 3.0, use="compliance recomputation only (closed boundary ≤ as frozen)",
         justification=["R22 v2 frozen SCALE_FAR = EFF_LO / 3"], sensitivity=[], sources=[src("multi_asset/exports/research/parity_replay_2026-09-12/devices/materiality_probe_v2.py", "SCALE_FAR = EFF_LO / 3.0")], applies_to=["F24"]),
    dict(key="D10", family="t3_cost_line", unit="bps per unit turnover", delta=1.6, use="compliance recomputation only",
         justification=["T3 frozen gate (PROGRAM §2 T3 / AMENDMENT 1 item 3)"], sensitivity=[], sources=[src(R2 + "/T3/devices/t3_passive_rev.py", "GATE_BPS = 1.6")], applies_to=["F08"]),
]

RULES = {
    "R-EQ": "two-sided, per interval [lo, hi] at two-sided level c: EQUIVALENT ⇔ −δ < lo ∧ hi < δ (TOST at α = (1−c)/2 per side; with c = 0.95 that is α = 0.025, stricter than the usual 90 % CI TOST); NOT EQUIVALENT ⇔ lo ≥ δ ∨ hi ≤ −δ; INCONCLUSIVE otherwise. Non-finite lo/hi, lo > hi, δ ≤ 0 or non-finite ⇒ error, never a label.",
    "R-LINE": "one-sided materiality line L, material side 'upper': BELOW LINE (not material, established) ⇔ hi < L; AT/ABOVE LINE (material, established) ⇔ lo ≥ L; INCONCLUSIVE otherwise. Side 'lower' mirrors.",
    "R-SEEDS": "a rule that needs several intervals jointly (seeds, cells): aggregate EQUIVALENT / BELOW ⇔ every member is; NOT EQUIVALENT / AT-ABOVE ⇔ every member is; else INCONCLUSIVE, with seed_conflict flagged when both extremes occur.",
    "R-DIR": "direction labels are the device's own frozen rule recomputed verbatim and never changed; in the judge_v4 / P2 shape (A) ⇔ all seeds point > 0 ∧ lo > 0, (B) ⇔ all seeds hi < 0, else (C); (C) is split by R-SEEDS∘R-EQ into (C) EQUIVALENT / (C) INCONCLUSIVE / (C) NOT EQUIVALENT, and no no-difference branch may be evaluated before (A)/(B).",
    "R-LOSS": "a label containing LOSS may name a book only if that book's realised window mean (the stored point) is < 0. Shared-loss reading on return outcomes (price, net): both realised means < 0, then the paired difference by R-SEEDS∘R-EQ(D1): EQUIVALENT ⇒ 'SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ' (the only form that may be read as 'the strategy's own loss'); NOT EQUIVALENT ⇒ 'SHARED LOSS, MATERIAL DIFFERENCE'; INCONCLUSIVE ⇒ 'SHARED LOSS, DIFFERENCE INCONCLUSIVE'; otherwise 'NOT A SHARED LOSS (<who> lost)'. Carry and cost outcomes get R-EQ only, never loss wording.",
    "R-T4": "NOT MATERIAL ⇔ book (A) R-SEEDS∘R-EQ(Δg CI95, D1) = EQUIVALENT ∧ (B) R-EQ(ΔIC CI95, D4) = EQUIVALENT; MATERIAL (established) ⇔ book aggregate NOT EQUIVALENT ∨ ΔIC NOT EQUIVALENT; otherwise INCONCLUSIVE. The book-only reading is reported beside; the stored significance flags condA/condB are reported unchanged.",
    "R-T1H1": "DOES-NOT-EXPLAIN (established) ⇔ D_T vci_hi < 0 ∧ MIX vci_lo > −0.25·|D_T vci_hi| (union bound: |D_T| ≥ |vci_hi| and MIX > −0.25·|vci_hi| ⇒ MIX/D_T < 0.25); EXPLAINS as frozen; else UNDECIDED; H1 aggregates by T1's own rule.",
    "R-T1H3": "HALF-LIFE and LEVEL as frozen; NO-DROP (established) ⇔ ΔE1 vci_lo > −0.25·|E1_H1| with E1_H1 at its stored point (no interval stored ⇒ the reference uncertainty is ignored: declared non-conservative); else UNDECIDED; H3 aggregates by T1's own rule.",
    "R-T1H5": "FALSIFIED (same mechanism, established) ⇔ |c1 difference| ≤ 0.20 ∧ each of the six contrasts (Δπ, Δσs on D2 / REAL / REAL scaled) has R-EQ(vci, 0.25·m) = EQUIVALENT where m = min(|lo|, |hi|) of the stored CI95 of its 2023 reference if that CI excludes 0 (otherwise not establishable); SURVIVES as frozen; else NOT DECIDABLE.",
    "R-T8": "T8 verdicts unchanged. Per cell (model ∈ {R, L} × target ∈ {NET, LONG, SHORT} × seed): usefulness excluded ⇔ pooled r CI95 upper < 0.03 under both k=0 and k=9. The frozen FAIL consequence sentence is licensed only if every cell has usefulness excluded; otherwise the FAIL reads 'failed to detect; usefulness not excluded'.",
    "R-T5B": "R-LINE with L = 0.05 (upper = paid) on each reading's stored CI95; mean or CI absent ⇒ NOT RE-LABELLABLE (statistic absent).",
    "R-T5ADD": "per seed: NEGLIGIBLE (established) ⇔ R-EQ(share CI95, 0.05) = EQUIVALENT; NOT NEGLIGIBLE (established) ⇔ share CI95 lower ≥ 0.20 ∨ upper ≤ −0.20; else INCONCLUSIVE; seeds by R-SEEDS.",
    "R-T2": "verdicts unchanged; per arm × base: R-SEEDS∘R-EQ(W_ALPHA Δg CI95, D1); the BELOW-RESOLUTION flag is re-read as that axis.",
    "R-V4": "every JUDGE_v4 receipt: per (contrast, seat) R-DIR recomputed from the stored per-seed delta / ci95 must reproduce the stored verdict prefix; (C) split by R-SEEDS∘R-EQ(ci95, D1); extended-window contrasts likewise (secondary).",
    "R-COMPLY": "T3: PASS/FAIL/UNDECIDABLE recomputed from the stored CI and 1.6; R22 v2: scale statement recomputed from the stored U_endpoint; any mismatch is reported.",
    "R-PROSE": "after the freeze: committed RESULT text of L4 / L4b and the four decision documents of F21 are searched with the fact-table vocabulary; each hit asserting equivalence of a sampled statistic is re-read with the matching D row; admission statements are recorded as such.",
    "R-ABSENT": "a field the rule needs that is absent from the receipt ⇒ NOT RE-LABELLABLE (field absent: <path>); never a default, never skipped silently.",
    "R-CI": "the interval used is always the one the frozen rule used for its own label (T4 ci95; T2 W_ALPHA ci95; T1 vci; T8 ci95_k0 and ci95_k9; T5c CI95 k81 levels / k87 difference; v4 ci95; T5b CI95; T5 addendum share CI95); percentile bootstrap intervals are taken as stored, never recomputed.",
}

EXPOSURE = [
    "T4: book Δg +0.0181 [−0.030, +0.063] / +0.0161 [−0.033, +0.065], ΔIC −0.000101 [−0.000272, +0.000070], '±0.05 resolution' — STATE.md 07:4xZ, PROGRAM_uplift_r2 L158, dispatch message",
    "T5c: D_K −5.9617, R_K −4.7622 / −5.0654, D−R −1.1996 [−4.1863, +1.5949] / −0.8964 [−3.8669, +1.8074]; net −7.23 vs −5.87 / −6.17 — reviewer REVIEW_round4 §4.1, STATE.md",
    "T5b: frozen-residual carry −0.120 [−0.245, −0.021] 'NOT MATERIAL (PROVISIONAL)' — PROGRAM_uplift_r2 L171 (grep output)",
    "T5 addendum: s42 +0.00006 [−0.00041, +0.00055], 0.005 %, NEGLIGIBLE; s2027 +0.00003, 0.003 % — RESULT_T5 L162–163 (incidental grep output)",
    "T3: c_eff +1.13 [−15.87, +24.74] UNDECIDABLE — STATE.md, memory index",
    "T2: arm Δg points κ* −0.30 / σ-bins +0.17 / seat −0.03, all UNDECIDED — STATE.md 06:1xZ",
    "T8: 'r ≈ 0, hit rate = base rate', verdict FAIL; AMENDMENT_1 c_N table (incidental grep output)",
    "v4 chain: A1−A0 dyn +0.061 [−0.168, +0.287] / +0.048 [−0.171, +0.270], fix +0.005 [−0.076, +0.087] / −0.010 [−0.102, +0.088], (C) — RESULT_v4_chain L10 (incidental grep output)",
    "R22 v2: mean −0.000146, CI95 [−0.00166, +0.00126] — STATE.md, memory",
    "T1: H1/H3/H4/H5 NOT DECIDABLE; H3 ΔE1 −135.9 [−257, −15]; H5 72.9 % vs 6.7 %; 'mix explains at most 18 %' — PROGRAM_uplift_r2 L103 (grep output)",
    "L2 / L4 / L4b / P2 S2: no result number seen",
    "decision-relevant: T4's stored upper ends (+0.063 / +0.065) were known when D1 was frozen; D1 = 0.05 (PROGRAM L155 line) makes T4 INCONCLUSIVE while the T5d band 0.25 would make it EQUIVALENT. D1 is taken from the programme-level line that predates the T5d band; both are shown as sensitivity so the dependence is visible, not hidden",
]


def main():
    out = dict(tool="k2_delta_table.py", self_sha256=gsha(os.path.relpath(os.path.abspath(__file__), REPO)),
               head=subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
               built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), conversions=CONV, deltas=DELTAS, rules=RULES, exposure=EXPOSURE,
               statement="frozen before this item opened any affected result receipt; every later re-label uses exactly these values and rules")
    json.dump(out, open(os.path.join(HERE, "DELTA_TABLE_K2.json"), "w"), indent=1, ensure_ascii=False)
    L = ["> **创建:** %s | **Session:** FX-EVAL (K2) session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 冻结(sha 见 DELTA_TABLE_K2_FREEZE.txt; 先于本项打开任何受影响结果收据) | **作废条件:** 只能以带日期的 AMENDMENT 另立并先记 sha" % out["built_utc"],
         "", "# K2 δ 表与机械重标规则", "", "机器版 `DELTA_TABLE_K2.json`(含每个来源的文件:行、原文、sha、首次入库提交、该行最后提交)。", "",
         "## 换算(脚本算, 输入 = T2 PREREG L38 的 A0 基线事实)", "", "```", json.dumps(CONV, indent=1), "```", "", "## δ", "",
         "| key | 统计量族 | 单位 | δ | 用法 | 理由 | 敏感性(不定标签) |", "|---|---|---|---|---|---|---|"]
    e = lambda x: str(x).replace("|", "\\|")
    for d in DELTAS:
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (d["key"], d["family"], e(d["unit"]), ("%.6g" % d["delta"]), e(d["use"]), e(" · ".join("(%d) %s" % (i + 1, j) for i, j in enumerate(d["justification"]))), e(d["sensitivity"])))
    L += ["", "### 来源锚点", ""]
    for d in DELTAS:
        for s_ in d["sources"]:
            L.append("- %s ← `%s:%d` (首次入库 %s; 该行最后提交 %s %s): %s" % (d["key"], s_["file"], s_["line"], s_["file_first_add"], s_["line_last_commit"], s_["line_last_commit_utc"], e(s_["text"][:160])))
    L += ["", "## 规则", ""] + ["- **%s**: %s" % (k, v) for k, v in RULES.items()]
    L += ["", "## 冻结前已看到的数字(非盲; 如实列出)", ""] + ["- %s" % x for x in EXPOSURE]
    open(os.path.join(HERE, "DELTA_TABLE_K2.md"), "w").write("\n".join(L) + "\n")
    print("SUMMARY k2_delta_table deltas=%d rules=%d sources=%d D1=%.3f D2=%.2f D3=%.2f D4=%.4f sigma_g=%.4f D1_sharpe=%.4f" % (
        len(DELTAS), len(RULES), sum(len(d["sources"]) for d in DELTAS), D1, D2, D3, D4, SIGMA_G, conv(D1)["annualised_sharpe"]))


if __name__ == "__main__":
    main()
