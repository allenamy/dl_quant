#!/usr/bin/env python3
"""t6_family.py -- T6 step 1c: apply the FROZEN membership rules (FAMILY_T6.md §2) to the two structural inventory receipts.
NO statistics: reads only config fields, record coverage, file sha256 and g-series sha256 (exact-duplicate detection).
Every per-file decision (include / exclude + reason + role + citing RESULT) is written to FAMILY_T6.json.
Usage: python3 t6_family.py <env_whitelist_csv> <INVENTORY_pod2.json> <INVENTORY_pass2_pod2.json> <out_json>
"""
import os, sys, json, re, hashlib, collections
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
INV, P2, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
U = "/workspace/uplift_2026-09-11/"; R2 = "/workspace/uplift_r2_2026-09-13/"
RS = "multi_asset/exports/research/uplift_2026-09-11/"; RS2 = "multi_asset/exports/research/uplift_r2_2026-09-13/"
# ------------------------------------------------------------------------------------------------------------------
# Directory -> (round label, citing RESULT). Rounds r8..r21 + T2 are the AMENDMENT-5 named scope (flag in_r8_scope).
DIRS = [
 ("r3k/arms", "r3k", RS + "r3k_impact/analyze3.out (+ RESULT_r3_instrument3_xib_seeds_2026-09-11.md for XIB_LAG50)", False),
 ("r4_nondet/arms", "r4_nondet", RS + "RESULT_r4_dl_training_nondeterminism_2026-09-11.md", False),
 ("r4_p1/arms", "r4_p1", RS + "RESULT_r5_angle1_fixed_seat_2026-09-11.md §5 (no local r4_p1 RESULT)", False),
 ("r4p3/arms", "r4p3", RS + "r4p3/RESULT_P3.json", False),
 ("r5_basis/arms", "r5_basis", RS + "RESULT_r5_basis_newdata_2026-09-11.md", False),
 ("r5_basis/dev/probe_artifacts", "r5_basis", RS + "RESULT_r5_basis_newdata_2026-09-11.md", False),
 ("r5_lob/out", "r5_lob", RS + "r5_lob/RESULT_SUMMARY.json", False),
 ("r5_oi/out", "r5_oi", RS + "RESULT_r5_newdata2_liq_oi_2026-09-11.md", False),
 ("r5_seeds/arms", "r5_seeds", RS + "RESULT_r5_angle3_frozen_seed_verdict_2026-09-11.md", False),
 ("r5_seeds/grid", "r5_seeds_grid", RS + "RESULT_r5_angle3_frozen_seed_verdict_2026-09-11.md §7", False),
 ("r5a2/arms", "r5a2", RS + "r5_angle2/A2_CROSS.json + A2_LADDER.json (no .md)", False),
 ("seatladder/dev/probe_artifacts", "seatladder", RS + "RESULT_r5_angle1_fixed_seat_2026-09-11.md", False),
 ("ship1/gateP/dev/probe_artifacts", "ship1", RS + "PREREG_ship1_amihud_4th_leg_2026-09-11.md §E.3", False),
 ("p6/arms", "p6", RS + "PREREG_p6_amihud_sleeve_2026-09-11.md", False),
 ("r7f1/dev_v4/probe_artifacts", "r7f1", RS + "RECEIPT_r7_fuel1_viability_2026-09-12.json", False),
 ("r7f2/dev/probe_artifacts", "r7f2", RS + "RESULT_r7_fuel2_dispersion_screen_2026-09-12.md", False),
 ("r8_inbook/arms", "r8_inbook", RS + "RESULT_r8_basis_inbook_2026-09-12.md", True),
 ("r8b2/dev/probe_artifacts", "r8b2", RS + "RESULT_r8_BUILD2_dispersion_seat_tilt_2026-09-12.md", True),
 ("r8b2/dev2/probe_artifacts", "r8b2", RS + "RESULT_r8_BUILD2_dispersion_seat_tilt_2026-09-12.md", True),
 ("r9/dev_inc/probe_artifacts", "r9", RS + "r9_coverage/RESULT_r9_coverage_2026-09-12.md", True),
 ("r9/dev_ext/probe_artifacts", "r9", RS + "r9_coverage/RESULT_r9_coverage_2026-09-12.md", True),
 ("r10_slowclock/out", "r10_slowclock", RS + "r10_screen/SLOW_CLOCK/RESULT_r10_SLOW_CLOCK_2026-09-12.md", True),
 ("r12_smoothing/arms", "r12_smoothing", RS + "r12_smoothing/RESULT_r12_smoothing_2026-09-12.md", True),
 ("r12_intervene/dev_ext/probe_artifacts", "r12_intervene", RS + "r12_intervene/RESULT_r12_intervention_layer_2026-09-12.md", True),
 ("r14_cleanbase", "r14", RS + "r14_cleanbase/RESULT_r14_clean_baseline_2026-09-12.md", True),
 ("r15_structural/arms", "r15", RS + "r15_structural/RESULT_r15_structural_2026-09-12.md", True),
 ("r15_structural/receipts/arms_rec", "r15", RS + "r15_structural/RESULT_r15_structural_2026-09-12.md", True),
 ("r15_structural/nulls", "r15", RS + "r15_structural/RESULT_r15_structural_2026-09-12.md", True),
 ("r16_asym_band/arms", "r16", RS + "r16_asym_band/RESULT_r16_asym_band_2026-09-12.md", True),
 ("r17_fill_pricing/arms", "r17", RS + "r17_fill_pricing/RESULT_r17_fill_pricing_2026-09-12.md", True),
 ("r17_fill_pricing/receipts/arms_rec", "r17", RS + "r17_fill_pricing/RESULT_r17_fill_pricing_2026-09-12.md", True),
 ("r18_foundation/arms", "r18", RS + "r18_foundation/RESULT_r18_foundation_2026-09-12.md", True),
 ("r18_foundation/receipts/arms_rec", "r18", RS + "r18_foundation/RESULT_r18_foundation_2026-09-12.md", True),
 ("r21_nulls_costbridge/dev_ext/probe_artifacts", "r21", RS + "r21_nulls_costbridge/RESULT_r21_nulls_costbridge_2026-09-12.md", True),
]
T2DIRS = [("T2/arms", "T2", RS2 + "T2/RESULT_T2_carry_net_sizing_2026-09-13.md", True), ("T2/receipts/arms_rec", "T2", RS2 + "T2/RESULT_T2_carry_net_sizing_2026-09-13.md", True)]
def locate(path):
    for d, rnd, cite, scope in DIRS:
        if path.startswith(U + d + "/"): return rnd, cite, scope
    for d, rnd, cite, scope in T2DIRS:
        if path.startswith(R2 + d + "/"): return rnd, cite, scope
    return None, None, None
# ------------------------------------------------------------------------------------------------------------------
# ROLE RULES (first match wins). Each rule: (round, regex on stem, role, include_class, note)
#   include_class: "F1" = full-book tradable member; "SLEEVE" = standalone component book (F4 only); "X" = excluded (reason in role)
N = r"(RELAB|SHIFT|ROT\d|PERM|_NULL|^NULL_|^NUL_T3_(RELAB|SHIFT)|^NUL_TLAD_(RELAB|SHIFT)|^N_[FS]_|^N_X\d|^C_NULL|^R8N_|G2_null)"
RULES = [
 # --- global exclusions by construction -----------------------------------------------------------------------------
 ("*", r"(ALEAD|_look1|_cleadp1|PERFECT|ADV1$|FADV1$)", "EXCL_LOOKAHEAD_CONTROL", "X", "look-ahead / perfect-foresight construction"),
 ("*", r"^R8N_P10_SHIFT0$", "CONTROL_WIRING_DUP", "F1", "SHIFT0 = true series through the null path (bitwise == P10)"),
 ("*", N, "EXCL_NULL", "X", "null / placebo / rotation / shift construction"),
 # --- T2 -------------------------------------------------------------------------------------------------------------
 ("T2", r"^C2_", "EXCL_GARBLED_FUTURE_CONTROL", "X", "shuffle-future leak gate on a garbled tree (PREREG_T2 §4 C2)"),
 ("T2", r"_NW_s\d+$", "EXCL_NW_DEVICE_STATE", "X", "same arm on the r18 NW device state (robustness reading); A0-state twin is the member"),
 ("T2", r"^(GP|PC0N|PC0S)_A0_", "CONTROL_DUP", "F1", "GATE P / kappa==0 control (bitwise A0)"),
 ("T2", r"^PC1S_A0_", "CONTROL_DUP", "F1", "kappa==1 seat control (bitwise r15 S)"),
 ("T2", r"^WIRE_A0_", "DIAGNOSTIC_TRADABLE", "F1", "kappa==1 on the name path (tradable, no archived twin)"),
 ("T2", r"^TW_Ns_(stale1|cleadm1)_", "DIAGNOSTIC_TRADABLE", "F1", "causal tripwire offset of ARM-Nsigma"),
 ("T2", r"^(N|Ns|SK)_A0_", "CANDIDATE", "F1", "PREREG_T2 §3 K=3 arm on the A0 base"),
 # --- r18 ------------------------------------------------------------------------------------------------------------
 ("r18", r"^C0_", "CONTROL_DUP", "F1", "GATE P (bitwise archived A0)"),
 ("r18", r"^(N2|WU|NW|NW_S05|NW_B50)_", "EXCL_NW_DEVICE_STATE", "X", "device-fix state (N2/WU/NW) or smoothing corner re-run on NW; A0-state twins are members"),
 # --- r17 ------------------------------------------------------------------------------------------------------------
 ("r17", r"^(A0DET|A0STO\d|X1DET|FDET|SDET)_", "EXCL_ACCOUNTING_VARIANT", "X", "R17_FILL=1 fill-model accounting of an existing book"),
 ("r17", r"^GP_(FILL0|INSTR|F|S|X1)_", "CONTROL_DUP", "F1", "GATE P1-P4 reproductions (bitwise A0 / r15 F / r15 S / r16 X1)"),
 # --- r16 ------------------------------------------------------------------------------------------------------------
 ("r16", r"^GP_", "CONTROL_DUP", "F1", "GATE P aux0/aux1 (bitwise A0)"),
 ("r16", r"^A_X4_", "CONTROL_TRADABLE_IN_K", "F1", "mirror construction control, inside Bonferroni K=6"),
 ("r16", r"^A_X[01235]_", "CANDIDATE", "F1", "PREREG_r16 K=6 exemption mode"),
 # --- r15 ------------------------------------------------------------------------------------------------------------
 ("r15", r"^(GP_A0|D_A0I|D_FI|D_SI)_", "CONTROL_DUP", "F1", "GATE P / instrumented twins (bitwise A0 / F / S)"),
 ("r15", r"^(F|S|SB|F05|F20)_s\d+$", "CANDIDATE", "F1", "PREREG_r15 K=5 structural arm"),
 # --- r14 ------------------------------------------------------------------------------------------------------------
 ("r14", r"^r14_A0_PWR230k_", "CONTROL_DUP", "F1", "seed-2027 baseline copy (A0)"),
 # --- r12 intervene (A1x device state, W_FULL prefix-equal to A1_inc) ---------------------------------------------
 ("r12_intervene", r"^R12B?_GATEP_", "CONTROL_DUP", "F1", "GATE P (bitwise R9_A1x_ext)"),
 ("r12_intervene", r"^R12_KING3LEG_", "DIAGNOSTIC_TRADABLE", "F1", "I-2 trap book (bitwise R9_PHI0 on W_FULL)"),
 ("r12_intervene", r"^R12_(CEM|BYP)_", "CANDIDATE", "F1", "PREREG_r12 intervention K=29 device arm (A1 base)"),
 # --- r12 smoothing --------------------------------------------------------------------------------------------------
 ("r12_smoothing", r"^G1_", "CONTROL_DUP", "F1", "GATE G1/G1b (bitwise A0)"),
 ("r12_smoothing", r"^S_a\d+_b\w+_s\d+$", "CANDIDATE", "F1", "PREREG_r12_smoothing K=28 grid point"),
 ("r12_smoothing", r"^C_AS_", "DESIGN_VARIANT", "F1", "EXPLORATORY state-conditional smoothing (causal ALTSURGE mask)"),
 # --- r10 slow clock (standalone books) -----------------------------------------------------------------------------
 ("r10_slowclock", r"^PWR_COMBO_S$", "SLEEVE_DESIGN_VARIANT", "SLEEVE", "signal-layer blend of the 13 slow-clock sleeves (standalone book)"),
 ("r10_slowclock", r"^NUL_(T3|TLAD)_REAL$", "SLEEVE_DESIGN_VARIANT", "SLEEVE", "null-test treatment reference (standalone book)"),
 ("r10_slowclock", r"^PWR_", "SLEEVE_CANDIDATE", "SLEEVE", "slow-clock standalone sleeve (LEGS=001 PHI=0)"),
 # --- r9 ---------------------------------------------------------------------------------------------------------------
 ("r9", r"^R9_A1(_inc|x_ext)_", "CANDIDATE", "F1", "A1 = king v4 + F10 v4 RAW (v4-chain model-version candidate); ext is W_FULL-prefix-equal"),
 ("r9", r"^R9_PHI0_(inc|ext)_", "DESIGN_VARIANT", "F1", "A1 legs with PHI=0 (no F10 mixing)"),
 # --- r8b2 -------------------------------------------------------------------------------------------------------------
 ("r8b2", r"^R8_A0_", "CONTROL_DUP", "F1", "TILT device knobs-off (bitwise A0)"),
 ("r8b2", r"^R8_FUND$", "DESIGN_VARIANT", "F1", "single-leg fund book (LEGS=001 PHI=0)"),
 ("r8b2", r"^R8_KING$", "DESIGN_VARIANT", "F1", "single-leg king book (LEGS=100 PHI=0)"),
 ("r8b2", r"^R8_(S|R|P)\d\d_s\d+$", "CANDIDATE", "F1", "PREREG_r8_BUILD2 K=9 seat tilt"),
 # --- r8 in-book -----------------------------------------------------------------------------------------------------
 ("r8_inbook", r"^(R8_A0|R8Z_IDENT|CL_A0|CL_R8Z_IDENT)", "CONTROL_DUP", "F1", "A0 / identity injection (bitwise A0)"),
 ("r8_inbook", r"^CL_R8", "CONTROL_DUP", "F1", "cost-ladder PWR230k rung (same env as dyn_s42)"),
 ("r8_inbook", r"^R8[ABCD]_\w+_dyn_s\d+$", "CANDIDATE", "F1", "PREREG_r8 K=13 in-book arm, dynamic seat"),
 ("r8_inbook", r"^R8[ABCD]_\w+_fix_s\d+$", "DESIGN_VARIANT", "F1", "same arm on fixed seat 0.21 (secondary reading, gate G2)"),
 # --- r7 ---------------------------------------------------------------------------------------------------------------
 ("r7f1", r"^R7_A0_", "CONTROL_DUP", "F1", "FUEL-1 baseline (bitwise A0)"),
 ("r7f1", r"^R7_FUND$", "DESIGN_VARIANT", "F1", "single-leg fund book"),
 ("r7f1", r"^R7_KING$", "DESIGN_VARIANT", "F1", "single-leg king book"),
 ("r7f2", r"^R7_LEGFUND_PWR_", "DESIGN_VARIANT", "F1", "single-leg fund book"),
 ("r7f2", r"^R7_LEGREV24_PWR_", "DESIGN_VARIANT", "F1", "single-leg rev24 book (retired leg)"),
 ("r7f2", r"^R7_LEGKING_PWR_", "DESIGN_VARIANT", "F1", "single-leg king book"),
 # --- p6 (standalone Amihud sleeves) -------------------------------------------------------------------------------
 ("p6", r"^P6_AMQ64_(PWR|G230k)_", "SLEEVE_CANDIDATE", "SLEEVE", "standalone Amihud sleeve"),
 ("p6", r"^P6_(AMP|AMX|AMQ32|AMR2)_", "SLEEVE_CONTROL", "SLEEVE", "Amihud sleeve parity/definition control (standalone)"),
 # --- ship1 / seatladder / r5a2 / r5_seeds / r5_oi / r5_basis / r5_lob / r4* / r3k -------------------------------------
 ("ship1", r"^SHIP1_A0_", "CONTROL_DUP", "F1", "GATE P (bitwise A0)"),
 ("seatladder", r"^LAD_(A0|A_PAR)_dyn_", "CONTROL_DUP", "F1", "A0 / parity (bitwise A0)"),
 ("seatladder", r"^LAD_A_PAR_k\d+_", "CONTROL_DUP", "F1", "parity at fixed seat (bitwise LAD_A0_k)"),
 ("seatladder", r"^LAD_A0_k\d+_", "DESIGN_VARIANT", "F1", "fixed king-weight seat ladder"),
 ("seatladder", r"^LAD_XIB_(dyn|k\d+)_", "CANDIDATE", "F1", "XIB_LAG50 at dynamic / fixed seat"),
 ("r5a2", r"^R5A2(X_FULL|X_ECHO)?_(A0|APAR)", "CONTROL_DUP", "F1", "A0 / parity / device-copy / seat-echo gates (bitwise A0)"),
 ("r5a2", r"^R5A2X_KW\dp\d+_APAR_", "DESIGN_VARIANT", "F1", "constant king-weight seat sweep on the parity (=A0) score"),
 ("r5a2", r"^R5A2X_(FS|SF)_", "EXCL_NULL_DERIVED", "X", "fresh/stale cross built from the SHIFT101 null score"),
 ("r5_seeds", r"_s(7|101|1234|31337)$", "EXCL_REPLICATE_SEED", "X", "F10 seed replicate beyond 42/2027"),
 ("r5_seeds", r"^R5_FIT_(A0|XIBPAR)_", "CONTROL_DUP", "F1", "A0 / XIBPAR bitwise gates"),
 ("r5_seeds", r"^R5_FIT_XIBLAG50_", "CANDIDATE", "F1", "XIB_LAG50 (angle 3)"),
 ("r5_seeds_grid", r"^G_A0_k0p21_", "CONTROL_DUP", "F1", "k=0.21 grid gate (bitwise fixed-seat A0)"),
 ("r5_seeds_grid", r"^G_A0_k", "DESIGN_VARIANT", "F1", "frozen king-weight grid (A0)"),
 ("r5_seeds_grid", r"^G_XIBLAG50_k", "DESIGN_VARIANT", "F1", "frozen king-weight grid (XIB_LAG50)"),
 ("r5_oi", r"^IB_PARITY$", "CONTROL_DUP", "F1", "monotone no-op injection (bitwise A0)"),
 ("r5_oi", r"^IB_", "CANDIDATE", "F1", "PREREG_r5_newdata2 K=8 in-book readout"),
 ("r5_oi", r"^SA_LIQDD_LAG0$", "EXCL_LOOKAHEAD_CONTROL", "X", "leakage diagnostic (LAG0)"),
 ("r5_oi", r"^SA_", "SLEEVE_CANDIDATE", "SLEEVE", "PREREG_r5_newdata2 standalone readout"),
 ("r5_basis", r"^(R5_AMQ64_POSCTRL|R5GS_AMQ64_PWR_s42)$", "SLEEVE_CONTROL", "SLEEVE", "positive control / GATE S (= P6 AMQ64 sleeve)"),
 ("r5_basis", r"^R5C_", "EXCL_ACCOUNTING_VARIANT", "X", "cost-ladder rung"),
 ("r5_basis", r"^R5_(F?B\w+)_(LAG|NOLAG)$", "SLEEVE_CANDIDATE", "SLEEVE", "basis sleeve (declared / post-hoc flipped)"),
 ("r5_lob", r"^CTL_ORTH_AMIHUD", "SLEEVE_CONTROL", "SLEEVE", "reference sleeve"),
 ("r5_lob", r"^R5O?_", "SLEEVE_CANDIDATE", "SLEEVE", "LOB price-space arm"),
 ("r4_nondet", r".", "EXCL_REPLICATE_SEED", "X", "DL training nondeterminism / seed replicate study (A0 only)"),
 ("r4_p1", r"^R4B1_(A0|APAR)_", "CONTROL_DUP", "F1", "A0 / parity (bitwise A0)"),
 ("r4_p1", r"^R4B1_XIB_", "CANDIDATE", "F1", "XIB_LAG50 (blocking test B1)"),
 ("r4p3", r"^IB_LAG50_PWR230k_", "DIAGNOSTIC_TRADABLE", "F1", "argsort-ranker rebuild of XIB_LAG50 (cross-check; not bitwise)"),
 ("r4p3", r"^IB_PAR_PWR230k_", "DIAGNOSTIC_TRADABLE", "F1", "argsort-ranked parity arm (ranking-hole diagnostic; not bitwise A0)"),
 ("r4p3", r"^SL_ORTHLAG_PWR230k_", "SLEEVE_CANDIDATE", "SLEEVE", "standalone orthogonalised Amihud sleeve"),
 ("r4p3", r"^SL_ORTHLAG_RZ_", "SLEEVE_CONTROL", "SLEEVE", "same sleeve with device ranker"),
 ("r3k", r"^A0_PWR230k_", "BASELINE", "F1", "archived A0 (in-service form, v4 caliber)"),
 ("r3k", r"^XIB_PWR230k_", "CANDIDATE", "F1", "XIB_LAG50 at the fitted cost"),
 ("r3k", r"^RS_PWR230k_", "CANDIDATE", "F1", "RESID_SHARPE at the fitted cost"),
 ("r21", r"^R21G_", "CONTROL_DUP", "F1", "G-A2 bitwise gates vs r12 archive"),
]
ROLE_RANK = {"BASELINE": 0, "CANDIDATE": 1, "CONTROL_TRADABLE_IN_K": 2, "DESIGN_VARIANT": 3, "DIAGNOSTIC_TRADABLE": 4, "CONTROL_WIRING_DUP": 5, "CONTROL_DUP": 6,
             "SLEEVE_CANDIDATE": 7, "SLEEVE_DESIGN_VARIANT": 8, "SLEEVE_CONTROL": 9}
F2_ROLES = {"BASELINE", "CANDIDATE", "CONTROL_TRADABLE_IN_K"}
def stem_of(p): return os.path.basename(p).replace(".npz", "").replace("w10_ablation_series_", "")
def seed_of(cfg_fseed, stem):
    return str(cfg_fseed) if cfg_fseed not in (None, "<absent>") else None
inv = json.load(open(INV)); p2 = json.load(open(P2))
cal_by_path = {r["path"]: r for r in inv["rows"]}
A0_42 = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz"; A0_27 = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz"
decisions = []
for o in p2["rows"]:
    p = o["path"]; r = cal_by_path[p]; cal = r.get("cal", {}); nest = r.get("config_nested") or {}
    rnd, cite, scope = locate(p); stem = stem_of(p)
    d = dict(path=p, stem=stem, round=rnd, cite=cite, in_r8_scope=scope, file_sha256=o["file_sha256"], rec_key=o.get("rec_key"),
             n_rows=o.get("n_rows"), ts_first_utc=o.get("ts_first_utc"), ts_last_utc=o.get("ts_last_utc"), wfull_missing=o.get("wfull_missing"),
             g_sha256_wfull=o.get("g_sha256_wfull"), fseed=seed_of(cal.get("FSEED"), stem),
             model_inputs="%s|%s" % (str(cal.get("SLOW_NPY")).rsplit("/", 1)[-1], str(cal.get("FPRED")).rsplit("/", 1)[-1]),
             legs=cal.get("LEGS"), phi=cal.get("PHI"), femat=str(cal.get("FEMAT_NPZ")).rsplit("/", 1)[-1],
             r18_state=(nest.get("R18", {}) or {}).get("R18_ELIG", 0) or (nest.get("R18", {}) or {}).get("R18_WARM", 0))
    role = cls = note = None
    if rnd is None: role, cls, note = "EXCL_UNSCOPED_DIR", "X", "directory not in the scoped device lineage list"
    else:
        for rr, rx, ro, cl, nt in RULES:
            if rr in ("*", rnd) and re.search(rx, stem): role, cls, note = ro, cl, nt; break
        if role is None: role, cls, note = "EXCL_UNCLASSIFIED", "X", "no rule matched (excluded, listed for the lead)"
    # structural gates that override inclusion
    if cls in ("F1", "SLEEVE"):
        if o.get("wfull_missing") != 0: cls, note = "X", note + " | EXCL_GRID: %s W_FULL anchors missing" % o.get("wfull_missing")
        elif o.get("wfull_nonfinite_or_nonpos_gross", 0) != 0: cls, note = "X", note + " | EXCL_NONFINITE_G"
        elif d["fseed"] not in ("42", "2027"): cls, note = "X", note + " | EXCL_SEED %s" % d["fseed"]
        elif d["r18_state"]: cls, note = "X", note + " | EXCL_NW_DEVICE_STATE"
    if role == "BASELINE": d["cite"] = RS + "r18_foundation/RESULT_r18_foundation_2026-09-12.md §4 (C0 = archived A0, GATE P bitwise) + CALIBER_PIN_v4_2026-09-11.md §4"
    d.update(role=role, cls=cls, note=note)
    decisions.append(d)
# ---- dedupe within (seed, g hash) over included files; canonical = BASELINE path if present else best role then lexicographic path
members = {}
for d in decisions:
    if d["cls"] not in ("F1", "SLEEVE"): continue
    key = (d["fseed"], d["g_sha256_wfull"]); members.setdefault(key, []).append(d)
fam = []
for (seed, gh), L in members.items():
    L = sorted(L, key=lambda x: (0 if x["path"] in (A0_42, A0_27) else 1, ROLE_RANK[x["role"]], x["path"]))
    can = L[0]; roles = sorted(set(x["role"] for x in L), key=lambda r_: ROLE_RANK[r_])
    best = roles[0]
    cls = "F1" if any(x["cls"] == "F1" for x in L) else "SLEEVE"
    if best in ("CONTROL_DUP", "CONTROL_WIRING_DUP"):
        # a control whose series is not identical to any included book: keep it only if it is a tradable variant; pure GATE copies must alias a book
        pass
    in_r8 = any(x["in_r8_scope"] for x in L) or can["path"] in (A0_42, A0_27)
    fam.append(dict(seed=seed, g_sha256_wfull=gh, canonical_path=can["path"], canonical_stem=can["stem"], canonical_round=can["round"],
                    canonical_file_sha256=can["file_sha256"], rec_key=can["rec_key"], rows="%s .. %s (%s rows)" % (can["ts_first_utc"], can["ts_last_utc"], can["n_rows"]),
                    model_inputs=can["model_inputs"], role=best, roles_all=roles, cls=cls, cite=can["cite"],
                    in_F1=cls == "F1", in_F2=cls == "F1" and best in F2_ROLES, in_F3=cls == "F1" and in_r8, in_F4=True, in_F5=cls == "F1" and can["model_inputs"].startswith("SLOW_v3_on_v4axis.npy|f10_A0_s"),
                    aliases=[dict(path=x["path"], role=x["role"], round=x["round"], file_sha256=x["file_sha256"]) for x in L[1:]]))
# member ids: sort by seed, family class, round, stem
fam.sort(key=lambda m: (m["seed"], 0 if m["in_F1"] else 1, ROLE_RANK[m["role"]], m["canonical_round"], m["canonical_stem"]))
cnt = collections.Counter()
for m in fam:
    cnt[m["seed"]] += 1; m["member_id"] = "s%s_%03d" % (m["seed"], cnt[m["seed"]])
# consistency checks (structural)
flags = []
for m in fam:
    if m["role"] in ("CONTROL_DUP", "CONTROL_WIRING_DUP"): flags.append("CONTROL-ONLY member (no tradable alias with identical series): %s %s" % (m["seed"], m["canonical_path"]))
A0chk = [m for m in fam if m["canonical_path"] in (A0_42, A0_27)]
assert len(A0chk) == 2 and all(m["role"] == "BASELINE" for m in A0chk), A0chk
excl = collections.Counter((d["round"], d["role"] if d["cls"] == "X" else "INCLUDED", ("GRID" if "EXCL_GRID" in (d["note"] or "") else "")) for d in decisions)
summ = {}
for s in ("42", "2027"):
    ms = [m for m in fam if m["seed"] == s]
    summ[s] = dict(F1=sum(m["in_F1"] for m in ms), F2=sum(m["in_F2"] for m in ms), F3=sum(m["in_F3"] for m in ms), F4=sum(m["in_F4"] for m in ms), F5=sum(m["in_F5"] for m in ms),
                   F1_by_role=dict(collections.Counter(m["role"] for m in ms if m["in_F1"])), F1_by_round=dict(collections.Counter(m["canonical_round"] for m in ms if m["in_F1"])))
out = dict(device="t6_family.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)},
           inventory_sha256=sha(INV), pass2_sha256=sha(P2), n_files_on_caliber=len(decisions), n_members_total=len(fam), summary=summ, flags=flags,
           exclusion_counts=[dict(round=k[0], decision=k[1], grid=k[2], n=v) for k, v in sorted(excl.items(), key=lambda kv: (str(kv[0][0]), kv[0][1]))],
           rules=[dict(round=a, regex=b, role=c, cls=d_, note=e) for a, b, c, d_, e in RULES], members=fam, decisions=decisions)
json.dump(out, open(OUT, "w"), indent=1)
print("SUMMARY t6_family files=%d members=%d s42 F1/F2/F3/F4/F5=%d/%d/%d/%d/%d s2027 F1/F2/F3/F4/F5=%d/%d/%d/%d/%d flags=%d self_sha256=%s"
      % (len(decisions), len(fam), summ["42"]["F1"], summ["42"]["F2"], summ["42"]["F3"], summ["42"]["F4"], summ["42"]["F5"], summ["2027"]["F1"], summ["2027"]["F2"], summ["2027"]["F3"], summ["2027"]["F4"], summ["2027"]["F5"], len(flags), out["self_sha256"][:16]))
