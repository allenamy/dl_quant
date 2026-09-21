#!/usr/bin/env python3
"""fcf_f4bp_vs_kc.py — AMENDMENT 3 §4 condition 2: prove, don't assert, what separates F4a (= the archived kc component) from F4b′.

THE RULING (docs/AMENDMENT_3_fallback_counterfactual_2026-09-20.md, 32c4ff43e §4-2), verbatim in substance:
  "「F4a − F4b′ = FTRIM 单独贡献」必须被证明, 不得声称。先断言 z(F4b′) 与 z_kc 逐位相同; 若书仍有差, 残差来自链状态路径
   (F4b′ 背的是 king 链从 2022-01 冷启动的 H, kc 背的是 combo 阶段起点的 H_kc), 必须具名并单独量化, 不得并进 FTRIM。
   lead 预期这两条状态路径不同。"

═══ 2026-09-21 REPAIR — round-7 independent review, finding FB-01 ═══════════════════════════════════════════════════
WRITTEN AFTER THE DIFFICULTY WAS SHOWN TO ME, AND SAYING SO. The previous version of this device (self_sha256
6cc54b653366df38b87a296d3ca09eabaf5608cae492a3dbb9e012677751b706, receipt FCF_F4BP_VS_KC.json,
"A.z_F4bprime_equals_z_kc_before_FTRIM_bitwise_on_every_anchor ... equal=10038 compared=10038") took BOTH operands of
its equality from ONE field of ONE file — the archive's `combo_meta.w3_masked` — and then evaluated the same
expression with and without a `+ w[1]*rev24` term whose coefficient it had itself just set to +0.0. It never opened
the candidate's own recorded seat and never compared a real z. Its "bitwise identical on the whole population" was
`x + 0.0 == x`, which is true of any x. The reviewer's counter-example, reproduced by this device (see
`A3.seat_records_disagree_beyond_the_records_own_resolution`):
    2022-06-30T00:00:00Z, 137 members, legz byte-identical on both sides
    (sha256 fc80ce64810baddc262ae6f8af8dc1bbc7e1ef5bfa854478696edcdc7d126f71),
    archive masked seat [0,0,1]  vs  F4b′ masked seat [.5,0,.5],  real max|Δz| = 0.2535211267605634.

WHAT THIS VERSION DOES DIFFERENTLY
  1. TWO INDEPENDENTLY GENERATED SOURCES, ENFORCED BY A LEDGER, NOT BY A COMMENT. Every read is registered as
     (side, path, field). `A0` REFUSES if the two sides ever share a (path, field) pair, so "one field read twice"
     cannot come back silently. Each side brings its OWN legz, its OWN recorded seat and its OWN book:
         archive / kc  : P1.vec.npz(legz,pm) · P3.json(combo.combo_meta.w3_masked) · P3.vec.npz(kc)
         candidate F4b′: F4bp_P1.vec.npz(legz,pm) · F4bp_w3.json(w3) · F4bp_KING.npz(king_file)
  2. IDENTICAL legz DOES NOT IMPLY IDENTICAL SEATS OR AN IDENTICAL BOOK — asserted, not remarked. `A2` counts the
     anchors on which legz is byte-identical AND the recorded seats nevertheless disagree beyond the records' own
     resolution; if that count is > 0 the implication is measured-false and the check says so in the receipt.
  3. NEITHER RECORD IS FULL PRECISION, SO NO "BITWISE" CLAIM IS AVAILABLE FROM THEM. `combo_meta.w3_masked` is a
     6-decimal record (combo_stage L279) and `F4bp_w3.json` a 4-decimal one (F4b′ producer L529). Each anchor is
     therefore classified into exactly one of three, and the three partition the population:
         REFUTED_BY_THE_RECORDS   seats differ by more than the joint record tolerance ⇒ z really differs
         BOUNDED_NOT_BITWISE      seats agree to the records' resolution ⇒ |Δz| is BOUNDED, never proved zero
         UNRESOLVED_BY_THE_RECORDS the record cannot decide which branch of the masking rule ran (e.g. a recorded
                                  w3[0]+w3[2] == 0.0000 at 4dp cannot exclude a true sum above the 1e-12 branch
                                  threshold) ⇒ no measurement, NOT agreement
  4. THE RESIDUAL BUCKETS ARE NAMED FROM WHAT IS MEASURED TO BE IN THEM, NOT FROM A FIXED STRING. The old bucket
     `FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE` selected on `ftrim.n_kc == 0` AT THE CURRENT ANCHOR. That
     excludes same-anchor truncation and nothing else: an FTRIM that fired at an earlier anchor is already inside the
     EMA state H (the reviewer measured L1 = 0.045 under exactly that condition), and so is any earlier seat
     divergence. Each anchor's mechanism set is now COMPUTED (`mechanisms()`) and the bucket key is generated from it,
     so a bucket can only be called isolated when the measurement says it is isolated. On this data the isolated
     bucket is EMPTY and prints as no-measurement.

E-0920-C: every cell prints its n; a subset with no members prints as no-measurement, never as 0.
E-0826-D: the environment overrides actually read are enumerated in the receipt (`env`), and only the whitelist below
is consulted.
usage: fcf_f4bp_vs_kc.py <out.json>     env: FCF_OBJB, FCF_OUT (both optional; recorded in the receipt)
"""
import hashlib, json, os, sys, time

import numpy as np

ENV_WHITELIST = ("FCF_OBJB", "FCF_OUT")
OBJB = os.environ.get("FCF_OBJB", "/workspace/object_b_2026-09-19/work/A0_main")
OUT = os.environ.get("FCF_OUT", "/workspace/fallback_cf_2026-09-20")
JUDGE_FIRST, JUDGE_LAST = 1656547200, 1788480000

ARCHIVE, CANDIDATE = "archive_kc", "candidate_F4bprime"
# the number of decimals each side's seat record is written with, at its source:
#   combo_stage_replay_3520d363.py L279  round(float(x), 6)
#   shadow_loop_v3_replay_F4bp.py  L529  round(float(x), 4)
SEAT_RECORD_DECIMALS = {ARCHIVE: 6, CANDIDATE: 4}
MASK_BRANCH_THRESHOLD = 1e-12          # combo_stage L233 / F4bp L449: `if w3m.sum() > 1e-12`


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


class SourceLedger:
    """Every operand is registered here with the side that consumed it. Two sides sharing one (path, field) is the
    exact defect FB-01 caught, so it is a machine check and not a docstring promise."""

    def __init__(self): self.reads = {}

    def read(self, side, path, field, value):
        self.reads.setdefault(side, set()).add((os.path.realpath(path), field))
        return value

    def shared(self):
        sides = sorted(self.reads)
        out = []
        for i in range(len(sides)):
            for j in range(i + 1, len(sides)):
                for pf in sorted(self.reads[sides[i]] & self.reads[sides[j]]):
                    out.append({"sides": [sides[i], sides[j]], "path": pf[0], "field": pf[1]})
        return out

    def dump(self):
        return {s: sorted([p, f] for p, f in v) for s, v in self.reads.items()}


def mask_rule(w3):
    """The candidate producer's own masking rule, shadow_loop_v3_replay_F4bp.py L449, transcribed once."""
    w3m = np.array([w3[0], 0.0, w3[2]], np.float64)
    s = w3m.sum()
    return (w3m / s, "normalised") if s > MASK_BRANCH_THRESHOLD else (np.array([0.5, 0.0, 0.5]), "fallback")


def seat_tolerance(side, w_raw=None, masked_sum=None):
    """Per-component bound on how far a side's TRUE masked seat can sit from its RECORDED masked seat, given only the
    number of decimals the record was written with. For a side that records the seat ALREADY masked+normalised the
    bound is just the rounding step. For a side that records the RAW seat and is masked here, the normalisation
    propagates: with |Δw_i| ≤ e and s = w_0 + w_2, |Δ(w_i/s)| ≤ (e·s + w_i·2e)/s² ≤ 3e/s."""
    e = 0.5 * 10.0 ** (-SEAT_RECORD_DECIMALS[side])
    if w_raw is None:
        return e
    s = float(w_raw[0] + w_raw[2])
    if s <= 0:
        return float("inf")           # the record cannot even decide which branch of the rule ran
    return 3.0 * e / s


def load(p):
    z = np.load(p); return {k: z[k] for k in z.files}


def main():
    OUTP = sys.argv[1]
    LED = SourceLedger()

    P1A = f"{OBJB}/P1.vec.npz"; P3J = f"{OBJB}/P3.json"; P3V = f"{OBJB}/P3.vec.npz"
    P1C = f"{OUT}/work/F4bp_P1.vec.npz"; W3C = f"{OUT}/work/F4bp_w3.json"; KGC = f"{OUT}/work/F4bp_KING.npz"

    VA = load(P1A); V3 = load(P3V); VC = load(P1C); K = load(KGC)
    D = json.load(open(P3J))["records"]
    Wc = json.load(open(W3C))
    kind = load(f"{OBJB}/TARGETS_A0_main.npz")["scaled_kind"]

    A3 = V3["anchor"].astype(np.int64)
    pa = {int(a): i for i, a in enumerate(VA["anchor"].astype(np.int64))}
    pc = {int(a): i for i, a in enumerate(VC["anchor"].astype(np.int64))}
    kpos = {int(a): i for i, a in enumerate(K["anchor"].astype(np.int64))}
    arch_seat = {int(r["anchor"]): ((r.get("combo") or {}).get("combo_meta") or {}).get("w3_masked") for r in D}
    arch_ftrim = {int(r["anchor"]): ((r.get("combo") or {}).get("ftrim") or {}) for r in D}
    cand_seat = {int(a): w for a, w in zip(Wc["anchor"], Wc["w3"])}

    doc = {"device": "fcf_f4bp_vs_kc.py", "self_sha256": sha(os.path.abspath(__file__)),
           "repair": "round-7 review FB-01; written after the reviewer's counter-example was shown (stated in the docstring)",
           "supersedes": {"receipt": "FCF_F4BP_VS_KC.json",
                          "device_self_sha256": "6cc54b653366df38b87a296d3ca09eabaf5608cae492a3dbb9e012677751b706",
                          "withdrawn_claim": "A.z_F4bprime_equals_z_kc_before_FTRIM_bitwise_on_every_anchor equal=10038 compared=10038",
                          "why": "both operands were one field of one file; the expression compared was x + 0.0 == x"},
           "ruling": "docs/AMENDMENT_3_fallback_counterfactual_2026-09-20.md (32c4ff43e) §4 condition 2",
           "env": {k: os.environ.get(k) for k in ENV_WHITELIST},
           "sides": {ARCHIVE: {"legz_pm": P1A, "seat": P3J + "::combo.combo_meta.w3_masked", "book": P3V + "::kc",
                               "seat_record_decimals": SEAT_RECORD_DECIMALS[ARCHIVE], "seat_is_recorded": "already masked+normalised"},
                     CANDIDATE: {"legz_pm": P1C, "seat": W3C + "::w3", "book": KGC + "::king_file",
                                 "seat_record_decimals": SEAT_RECORD_DECIMALS[CANDIDATE], "seat_is_recorded": "raw; masked here by the producer's own rule"}},
           "inputs": {k: sha(v) for k, v in (("P1.vec", P1A), ("P3.vec", P3V), ("P3.json", P3J),
                                             ("F4bp_P1.vec", P1C), ("F4bp_w3", W3C), ("F4bp_KING", KGC))},
           "utc": iso(time.time()), "checks": []}
    FAILS = []

    def check(n, ok, d=None):
        doc["checks"].append(dict(check=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:280] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    def row(V, name, k):
        a, b = V[name + "_off"][k], V[name + "_off"][k + 1]; return V[name][a:b]

    def vec(V, name, k):
        a, b = V[name + "_off"][k], V[name + "_off"][k + 1]
        return V[name + "_idx"][a:b].astype(np.int64), V[name + "_val"][a:b]

    # ── A1: the two sides are read from independent sources ───────────────────────────────────────────────────────
    common = sorted(set(pa) & set(pc) & set(arch_seat) & set(cand_seat))
    common = [a for a in common if arch_seat[a] is not None]
    only_arch = sorted((set(pa) & set(arch_seat)) - set(common)); only_cand = sorted((set(pc) & set(cand_seat)) - set(common))

    # ── A2/A3: per-anchor seat and z comparison, each side from its own record ────────────────────────────────────
    CLS = {"REFUTED_BY_THE_RECORDS": [], "BOUNDED_NOT_BITWISE": [], "UNRESOLVED_BY_THE_RECORDS": []}
    legz_identical_but_seat_refuted = []
    worst = {"anchor": None, "max_abs_dz": -1.0, "bound": None}
    per_anchor = {}
    for A in common:
        ia, ic = pa[A], pc[A]
        lza = LED.read(ARCHIVE, P1A, "legz", row(VA, "legz", ia))
        lzc = LED.read(CANDIDATE, P1C, "legz", row(VC, "legz", ic))
        na = len(LED.read(ARCHIVE, P1A, "pm", row(VA, "pm", ia)))
        nc = len(LED.read(CANDIDATE, P1C, "pm", row(VC, "pm", ic)))
        if na != nc or len(lza) != 3 * na or len(lzc) != 3 * nc: continue
        wa = np.asarray(LED.read(ARCHIVE, P3J, "combo.combo_meta.w3_masked", arch_seat[A]), np.float64)
        wc_raw = np.asarray(LED.read(CANDIDATE, W3C, "w3", cand_seat[A]), np.float64)
        wc, branch = mask_rule(wc_raw)
        tol = seat_tolerance(ARCHIVE) + seat_tolerance(CANDIDATE, w_raw=wc_raw)
        dseat = float(np.abs(wa - wc).max())
        kga, fda = lza[:na], lza[2 * na:]
        kgc, fdc = lzc[:nc], lzc[2 * nc:]
        za = wa[0] * np.nan_to_num(kga) + wa[2] * np.nan_to_num(fda)
        zc = wc[0] * np.nan_to_num(kgc) + wc[1] * np.nan_to_num(lzc[nc:2 * nc]) + wc[2] * np.nan_to_num(fdc)
        dz = float(np.abs(za - zc).max()) if na else 0.0
        scale = float(np.abs(np.nan_to_num(kga)).max() + np.abs(np.nan_to_num(fda)).max()) if na else 0.0
        dz_bound = tol * scale
        if not np.isfinite(tol):
            cls = "UNRESOLVED_BY_THE_RECORDS"
        elif dseat > tol:
            cls = "REFUTED_BY_THE_RECORDS"
        else:
            cls = "BOUNDED_NOT_BITWISE"
        CLS[cls].append(A)
        per_anchor[A] = dict(cls=cls, dseat=dseat, tol=tol, dz=dz, dz_bound=dz_bound, branch=branch)
        if cls == "REFUTED_BY_THE_RECORDS":
            if lza.tobytes() == lzc.tobytes():
                legz_identical_but_seat_refuted.append(A)
            if dz > worst["max_abs_dz"]:
                worst = {"anchor": iso(A), "members": int(na), "max_abs_dz": dz,
                         "legz_sha256_both_sides": hashlib.sha256(lza.tobytes()).hexdigest() if lza.tobytes() == lzc.tobytes() else None,
                         "archive_masked_seat": wa.tolist(), "candidate_masked_seat": wc.tolist(),
                         "candidate_raw_seat_as_recorded": wc_raw.tolist(), "seat_tolerance": tol, "bound": dz_bound}

    check("A0.the_two_sides_never_share_a_source_field", not LED.shared(),
          dict(shared=LED.shared(), reads=LED.dump(),
               why="FB-01: the withdrawn version read combo_meta.w3_masked for BOTH operands, so its equality was x+0==x"))
    check("A1.population_is_closed_and_both_sides_are_named", len(common) > 0,
          dict(compared=len(common), only_in_archive=[iso(a) for a in only_arch[:5]], n_only_in_archive=len(only_arch),
               only_in_candidate=[iso(a) for a in only_cand[:5]], n_only_in_candidate=len(only_cand),
               partition_closes=len(CLS["REFUTED_BY_THE_RECORDS"]) + len(CLS["BOUNDED_NOT_BITWISE"])
               + len(CLS["UNRESOLVED_BY_THE_RECORDS"]) == len(per_anchor)))
    # This check carries teeth on purpose: it is GREEN exactly when "same legz ⇒ same seat" survives contact with the
    # data, and RED exactly when that implication — the unstated premise of the withdrawn conclusion — is false here.
    check("A2.byte_identical_legz_implies_an_equal_seat_record", not legz_identical_but_seat_refuted,
          dict(anchors_with_byte_identical_legz_and_a_refuted_seat=len(legz_identical_but_seat_refuted),
               first=[iso(a) for a in legz_identical_but_seat_refuted[:3]],
               reading=("RED means the implication 'same legz ⇒ same seat ⇒ same book' is measured-FALSE on this very "
                        "data, so nothing downstream may infer seat or book identity from the legz identity that "
                        "A1′ clause 1 proved")))
    check("A3.seat_records_agree_on_every_compared_anchor", not CLS["REFUTED_BY_THE_RECORDS"],
          dict(n_refuted=len(CLS["REFUTED_BY_THE_RECORDS"]),
               refuted_anchors=[iso(a) for a in CLS["REFUTED_BY_THE_RECORDS"][:5]],
               worst_real_z_difference=worst if worst["anchor"] else None,
               n_bounded_not_bitwise=len(CLS["BOUNDED_NOT_BITWISE"]),
               n_unresolved=len(CLS["UNRESOLVED_BY_THE_RECORDS"])))
    bounded = [per_anchor[a] for a in CLS["BOUNDED_NOT_BITWISE"]]
    doc["A_z_equality"] = {
        "claim_available_from_these_records": "BOUNDED, not bitwise",
        "why": ("both seats are rounded records (6dp archive / 4dp candidate); a bitwise claim needs full-precision "
                "seats from both producers, which neither writes today — see the seat contract in the round-7 notes"),
        "REFUTED_BY_THE_RECORDS": ({"n": 0, "note": "no member — no measurement, not 0"} if not CLS["REFUTED_BY_THE_RECORDS"] else
                                   {"n": len(CLS["REFUTED_BY_THE_RECORDS"]),
                                    "anchors": [iso(a) for a in CLS["REFUTED_BY_THE_RECORDS"]],
                                    "max_abs_dz": {iso(a): per_anchor[a]["dz"] for a in CLS["REFUTED_BY_THE_RECORDS"]}}),
        "BOUNDED_NOT_BITWISE": ({"n": 0, "note": "no member — no measurement, not 0"} if not bounded else
                                {"n": len(bounded),
                                 "max_abs_dz_measured_from_the_records": {"median": float(np.median([b["dz"] for b in bounded])),
                                                                          "max": float(np.max([b["dz"] for b in bounded]))},
                                 "bound_on_abs_dz_from_record_rounding": {"median": float(np.median([b["dz_bound"] for b in bounded])),
                                                                          "max": float(np.max([b["dz_bound"] for b in bounded]))}}),
        "UNRESOLVED_BY_THE_RECORDS": ({"n": 0, "note": "no member — no measurement, not 0"} if not CLS["UNRESOLVED_BY_THE_RECORDS"] else
                                      {"n": len(CLS["UNRESOLVED_BY_THE_RECORDS"]),
                                       "first": iso(CLS["UNRESOLVED_BY_THE_RECORDS"][0]),
                                       "last": iso(CLS["UNRESOLVED_BY_THE_RECORDS"][-1]),
                                       "why": ("recorded w3[0]+w3[2] == 0 at 4dp cannot exclude a true sum above the "
                                               f"{MASK_BRANCH_THRESHOLD:g} branch threshold, so which branch of the masking "
                                               "rule actually ran is not decidable from the record")})}

    # ── B: FTRIM footprint, at this anchor AND earlier in H ───────────────────────────────────────────────────────
    ordered = sorted(arch_ftrim)
    fired_before = {}; seen = 0
    for a in ordered:
        fired_before[a] = seen
        if int(arch_ftrim[a].get("n_kc") or 0) > 0: seen += 1
    refuted_set = set(CLS["REFUTED_BY_THE_RECORDS"]); unres_set = set(CLS["UNRESOLVED_BY_THE_RECORDS"])
    refuted_before = {}; unres_before = {}; sr = su = 0
    for a in ordered:
        refuted_before[a] = sr; unres_before[a] = su
        if a in refuted_set: sr += 1
        if a in unres_set: su += 1
    n_ft0 = sum(1 for a in ordered if int(arch_ftrim[a].get("n_kc") or 0) == 0 and arch_ftrim[a])
    check("B.FTRIM_footprint_named_at_the_anchor_AND_earlier_in_H", True,
          dict(anchors_with_an_ftrim_record=sum(1 for a in ordered if arch_ftrim[a]),
               anchors_where_FTRIM_zeroed_nothing_AT_THIS_ANCHOR=n_ft0,
               anchors_where_FTRIM_had_NEVER_fired_before=sum(1 for a in ordered if fired_before[a] == 0),
               first_anchor_FTRIM_ever_fired=next((iso(a) for a in ordered if int(arch_ftrim[a].get("n_kc") or 0) > 0), None),
               meaning=("`n_kc == 0` excludes FTRIM truncation AT THIS ANCHOR only. An FTRIM that fired earlier is "
                        "already carried in the EMA state H, so it is NOT excluded by that selector — this is the "
                        "isolation the withdrawn bucket name claimed and did not have")))

    # ── C: the residual, bucketed by the mechanisms MEASURED to be in it ──────────────────────────────────────────
    def mechanisms(a):
        m = ["chain_state_cold_start"]                       # always: the two chains start from different H
        if int(arch_ftrim.get(a, {}).get("n_kc") or 0) > 0: m.append("FTRIM_at_this_anchor")
        if fired_before.get(a, 0) > 0: m.append("FTRIM_earlier_in_H")
        if a in refuted_set or refuted_before.get(a, 0) > 0: m.append("seat_divergence_at_or_before_this_anchor")
        if a in unres_set or unres_before.get(a, 0) > 0: m.append("seat_unresolved_at_or_before_this_anchor")
        return sorted(m)

    NW = int(max(int(K["king_file_idx"].max()) if len(K["king_file_idx"]) else 0,
                 int(V3["kc_idx"].max()) if len(V3["kc_idx"]) else 0)) + 1
    buckets = {}
    for k3, A in enumerate(A3):
        A = int(A)
        if kind[k3] != 1 or not (JUDGE_FIRST <= A <= JUDGE_LAST): continue
        kk = kpos.get(A); i3 = k3
        if kk is None: continue
        a_, b_ = K["king_file_off"][kk], K["king_file_off"][kk + 1]
        bi, bv = K["king_file_idx"][a_:b_].astype(np.int64), K["king_file_val"][a_:b_]
        ci, cv = vec(V3, "kc", i3)
        x = np.zeros(NW); y = np.zeros(NW); x[bi] = bv; y[ci] = cv
        d = np.abs(x - y)
        key = "residual_contains__" + "+".join(mechanisms(A))
        b = buckets.setdefault(key, {"mechanisms": mechanisms(A), "mx": [], "l1": [], "dg": [], "anchors": []})
        b["mx"].append(float(d.max())); b["l1"].append(float(d.sum()))
        b["dg"].append(float(np.abs(x).sum() - np.abs(y).sum())); b["anchors"].append(A)

    ISOLATED_KEY = "residual_contains__chain_state_cold_start"
    res = {}
    for key, b in sorted(buckets.items()):
        res[key] = {"n": len(b["mx"]), "mechanisms": b["mechanisms"],
                    "isolates_chain_state_alone": b["mechanisms"] == ["chain_state_cold_start"],
                    "max_abs_dw": {"median": float(np.median(b["mx"])), "p95": float(np.percentile(b["mx"], 95)), "max": float(np.max(b["mx"]))},
                    "sum_abs_dw_L1": {"median": float(np.median(b["l1"])), "p95": float(np.percentile(b["l1"], 95)), "max": float(np.max(b["l1"]))},
                    "gross_difference_F4bprime_minus_kc": {"median": float(np.median(b["dg"])),
                                                           "p05": float(np.percentile(b["dg"], 5)), "p95": float(np.percentile(b["dg"], 95))},
                    "first": iso(b["anchors"][0]), "last": iso(b["anchors"][-1])}
    if ISOLATED_KEY not in res:
        res[ISOLATED_KEY] = {"n": 0, "mechanisms": ["chain_state_cold_start"], "isolates_chain_state_alone": True,
                             "note": "no member — no measurement, not 0"}
    doc["C_residual_on_simulated_fallback_anchors"] = res
    doc["C_bucket_naming"] = ("the key is generated from mechanisms() — the mechanisms MEASURED to be present — so a bucket "
                              "can be called isolated only when the measurement says so. The withdrawn version hardcoded "
                              "`CHAIN_STATE_ALONE` on a selector (`n_kc == 0` at the current anchor) that does not isolate it.")
    iso_n = res[ISOLATED_KEY]["n"]
    check("C.an_isolated_chain_state_bucket_EXISTS_and_is_measured", iso_n > 0,
          dict(isolated_bucket=ISOLATED_KEY, n=iso_n,
               buckets={k: v["n"] for k, v in sorted(res.items())},
               reading=("n == 0 means NO anchor in the judge window carries the chain-state path alone, so the withdrawn "
                        "number 0.0239 named 'CHAIN-STATE PATH, ALONE' was not isolated: every judge-window anchor also "
                        "carries earlier FTRIM in H (and, from 2022-06-30T00:00Z on, an earlier seat divergence too)")))
    doc["C_verdict"] = {
        "chain_state_alone": ("UNMEASURED — the isolated bucket is empty" if iso_n == 0 else
                              res[ISOLATED_KEY]["sum_abs_dw_L1"]["median"]),
        "reading": ("AMENDMENT 3 §4-3 asked whether the chain-state path is negligible. It cannot be answered from these "
                    "buckets, because no bucket isolates it. What IS measured is that the residual is not attributable to "
                    "FTRIM: every bucket also contains chain state, earlier FTRIM and (post-2022-06-30) a seat divergence. "
                    "'F4a − F4b′ = FTRIM alone' stays FALSE; no point estimate for rev24 is licensed.")}

    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "max_abs_dz"})
                      for k, v in doc["A_z_equality"].items()}, indent=1)[:1200], flush=True)
    print("C buckets:", json.dumps({k: v["n"] for k, v in sorted(res.items())}), flush=True)
    print(f"FCF_F4BP_VS_KC VERDICT={doc['VERDICT']} checks={len(doc['checks'])} failed={len(FAILS)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
