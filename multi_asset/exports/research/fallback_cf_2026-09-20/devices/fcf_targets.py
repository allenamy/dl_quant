#!/usr/bin/env python3
"""fcf_targets.py — F-family fallback counterfactual: build one TARGETS npz per arm from the object-B A0_main archive.

PREREG docs/PREREG_fallback_counterfactual_2026-09-20.md (a964c2f9a) §2. Every arm changes ONLY what is written at an anchor whose
preflight FAILED; the preflight itself, the msharpe seat and the gross normalisation are untouched, and the failing-anchor population is
bitwise identical across arms (asserted, S5).

═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
E-0920-B REQUIREMENT — the production definition lines this device decomposes, copied verbatim (file:line + the code).
No number is emitted until the structural assertions below pass on the FULL anchor population.
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
(1) THE PREFLIGHT — object_b_2026-09-19/devices/b_driver.py, function combo_outcome:
L255:        n = len(pm); okf = int(rec["combo_meta"]["n_f10_scored"]); g = float(np.abs(cr[nz]).sum()); nn = int(len(nz))
L256:        inside = all(syms[int(j)] in live_set for j in nz); g_in = float(sum(abs(cr[j]) for j in nz if syms[int(j)] in live_set))
L257:        n_in = int(sum(1 for j in nz if syms[int(j)] in live_set))
L258:        f380 = math.ceil(380 * n / 400); f150 = math.ceil(150 * n / 400)
L261:        scaled = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= f150) and inside and (n_in >= f150) and (g_in > 0.4) and king_w is not None
    and the decision it drives, same file:
L343:                 rec["traded_scaled"] = "combo" if crec.get("scaled_ok") else "king"
(2) THE KIND MAPPING THIS DEVICE REPLACES — object_b_2026-09-19/devices/b_targets.py:
L38:        A = int(r["anchor"]); t = r.get(key) or ("hold(producer_skip)" if not r.get("wrote") else None)
L39:        if t == "combo": kd = 2; i_, v_ = vec("combo", k)
L40:        elif t == "king": kd = 1; i_, v_ = vec("king_file", k)
L41:        else: kd = 0; i_, v_ = np.zeros(0, np.int64), np.zeros(0)
L42:        kinds.append(kd); idxs.append(i_); vals.append(v_); offs.append(offs[-1] + len(i_))
(3) THE THREE BOOK SHAPES the arms choose between:
  king file  — object_b_2026-09-19/devices/shadow_loop_v3_replay.py, run_anchor step 8 (THREE legs, rev24 included):
L449:     z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])
    then demean / L1 / cap / EMA alpha / deadband / forced exit -> st.H -> write_target_live; recorded by b_driver as VEC["king_file"].
  combo     — object_b_2026-09-19/devices/combo_stage_replay_3520d363.py (rev24 dropped, kc and fc chained separately, 0.55/0.45 mixed):
L232: w3m = np.array([w3[0], 0.0, w3[2]])
L233: w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
L234: z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
L235: z_fc = w3m[0] * np.nan_to_num(zf) + w3m[2] * np.nan_to_num(legz["fund"])
    recorded by b_driver as VEC["combo"] (the target_live_combo file when the device wrote it, else 0.55*kc + 0.45*fc).
  kc        — the king component of the combo, rev24-free, own EMA chain, WITH FTRIM; recorded by b_driver as VEC["kc"].
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

ARMS (prereg §2; R = the main "scaled" reading, the only reading the arms are defined on):
  F0  as-is  : the archived production target. Must reproduce the archive BITWISE (it is the as-is arm) -> assertion A1.
  F1  combo  : preflight failed -> write that anchor's combo book anyway (low gross normalised to 2xNAV as usual).
  F2  hold   : preflight failed -> write no file; the executor's own on_unavailable = hold carries the previous book.
  F4a kc     : preflight failed -> write the rev24-free king component (kc). NAMED CONFOUND: kc also carries FTRIM
               (combo_stage L241-249), so F0-vs-F4a is not a clean rev24 ablation; F4b (producer re-chain) is.
  F3  flat   : NOT BUILT. Production external_book.parse_target L317/L342 rejects an empty / zero-gross target, so a flat target
               cannot travel the target-file channel at all and degenerates to F2 bitwise. Reported to the lead, awaiting a ruling.

E-0920-C REQUIREMENT — closed population, named not-applicable subset, never imputed:
  The arm rule for F1 and F4a needs a combo / kc vector at the failing anchor. Exactly ONE anchor of the 10,039 has none:
  1643587200 = 2022-01-31T00:00:00Z, the cold-start anchor of the whole chain, where the combo stage had no kc/fc state yet.
  It is NOT imputed and NOT silently dropped: it is listed by name in `not_applicable` in every receipt, left at its F0 value,
  and asserted to lie OUTSIDE the judge window (first simulated anchor 2022-06-30T00:00:00Z) so that it enters no number at all.

usage: fcf_targets.py            (build + assert + write)
       fcf_targets.py --selftest (baseline-green-then-mutate control for the structural assertion)
"""
import hashlib, json, os, sys, time

import numpy as np

H4 = 14400
OBJB = "/workspace/object_b_2026-09-19"
W = f"{OBJB}/work/A0_main"
OUT = "/workspace/fallback_cf_2026-09-20"
JUDGE_FIRST_ANCHOR = 1656547200   # 2022-06-30T00:00:00Z, RUN_CONFIG_main_A0_2026-09-19.json window.first_anchor
JUDGE_LAST_ANCHOR = 1788480000    # 2026-08-31T00:00:00Z
ARMS = ("F0", "F1", "F2", "F4a")
ARM_DOC = {
    "F0": "as-is: preflight failed -> the producer's own 3-leg king file (rev24 included). Baseline; reproduces the archive bitwise.",
    "F1": "preflight failed -> that anchor's combo book is written anyway.",
    "F2": "preflight failed -> no file is written; the executor's on_unavailable = hold carries the previous book.",
    "F4a": "preflight failed -> the rev24-free king component kc (NAMED CONFOUND: kc also carries FTRIM).",
}
SRC_VEC = {"F0": "king_file", "F1": "combo", "F2": None, "F4a": "kc"}
ARM_KIND = {"F0": 1, "F1": 2, "F2": 0, "F4a": 1}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def bits(a): return (str(a.dtype), a.shape, a.tobytes())


def load_archive():
    """the three archived inputs, sha-recorded, nothing repaired"""
    src = {"P3_json": f"{W}/P3.json", "P3_vec": f"{W}/P3.vec.npz", "TARGETS_arch": f"{W}/TARGETS_A0_main.npz",
           "TARGETS_receipt": f"{OBJB}/receipts/TARGETS_A0_main.json"}
    shas = {k: sha(v) for k, v in src.items()}
    D = json.load(open(src["P3_json"])); recs = D["records"]
    Z = np.load(src["P3_vec"]); V = {k: Z[k] for k in Z.files}
    T = np.load(src["TARGETS_arch"]); TA = {k: T[k] for k in T.files}
    R = json.load(open(src["TARGETS_receipt"]))
    assert R["targets_npz_sha256"] == shas["TARGETS_arch"], "archived TARGETS npz does not match its own receipt"
    A = V["anchor"].astype(np.int64)
    assert len(recs) == len(A) and all(int(r["anchor"]) == int(a) for r, a in zip(recs, A)), "P3.json / P3.vec axis mismatch"
    assert np.array_equal(TA["anchor"].astype(np.int64), A), "TARGETS axis != P3 axis"
    assert np.all(np.diff(A) == H4), "P3 axis not a contiguous 4h grid"
    return src, shas, recs, V, TA, R, A


def vec(V, name, k):
    """one CSR row of P3.vec.npz — the same accessor b_targets.py L34-36 uses"""
    a, b = V[name + "_off"][k], V[name + "_off"][k + 1]
    return V[name + "_idx"][a:b].astype(np.int64), V[name + "_val"][a:b]


def archived_kind(TA):
    return TA["scaled_kind"].astype(np.int8)


def build_arm(arm, V, TA, A):
    """the arm rule, applied to the FULL population. Returns (kind, off, idx, val, classification).
    classification[k] in {"unchanged" (preflight passed: the combo row, untouched), "rule" (preflight failed: the arm rule applied),
    "not_applicable" (preflight failed but the arm's source vector does not exist: left at F0, named, never imputed)}."""
    kind_a = archived_kind(TA)
    n = len(A)
    kinds = np.zeros(n, np.int8); idxs = []; vals = []; offs = [0]; cls = []
    for k in range(n):
        if kind_a[k] != 1:                                   # preflight passed (or producer skipped): every arm writes the archive's row
            a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
            i_ = TA["scaled_idx"][a:b].astype(np.int64); v_ = TA["scaled_val"][a:b]
            kinds[k] = kind_a[k]; cls.append("unchanged")
        else:
            src = SRC_VEC[arm]
            if src is None:                                   # F2: hold, always expressible
                i_, v_ = np.zeros(0, np.int64), np.zeros(0); kinds[k] = 0; cls.append("rule")
            else:
                i_, v_ = vec(V, src, k)
                if len(i_) == 0 and arm != "F0":              # the arm's source vector does not exist at this anchor
                    a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
                    i_ = TA["scaled_idx"][a:b].astype(np.int64); v_ = TA["scaled_val"][a:b]
                    kinds[k] = kind_a[k]; cls.append("not_applicable")
                else:
                    kinds[k] = ARM_KIND[arm]; cls.append("rule")
        o = np.argsort(i_, kind="stable")                     # b_driver.sparse() already sorts; kept explicit so the row order is defined
        idxs.append(i_[o].astype(np.int16)); vals.append(np.asarray(v_, np.float64)[o]); offs.append(offs[-1] + len(i_))
    out = {"anchor": A.astype(np.int64), "scaled_kind": kinds, "scaled_off": np.array(offs, np.int64),
           "scaled_idx": np.concatenate(idxs).astype(np.int16) if offs[-1] else np.zeros(0, np.int16),
           "scaled_val": np.concatenate(vals) if offs[-1] else np.zeros(0)}
    return out, np.array(cls)


# ─────────────────────────────── structural assertions ───────────────────────────────
def assert_structure(arm, out, cls, V, TA, A, fail):
    """Independent recomputation: read the arm's WRITTEN arrays and check, anchor by anchor over the whole population, that each row
    is exactly what the arm's rule says it must be. Does not reuse build_arm's intermediates."""
    kind_a = archived_kind(TA); n = len(A); kind_w = out["scaled_kind"]; off_w = out["scaled_off"]
    assert len(kind_w) == n and len(off_w) == n + 1 and off_w[0] == 0 and off_w[-1] == len(out["scaled_idx"]) == len(out["scaled_val"])
    na = []
    for k in range(n):
        i_w = out["scaled_idx"][off_w[k]:off_w[k + 1]].astype(np.int64); v_w = out["scaled_val"][off_w[k]:off_w[k + 1]]
        if kind_a[k] != 1:
            a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
            want_i, want_v, want_k = TA["scaled_idx"][a:b].astype(np.int64), TA["scaled_val"][a:b], int(kind_a[k])
            why = "preflight_passed_row_must_be_the_archive"
        else:
            src = SRC_VEC[arm]
            if src is None:
                want_i, want_v, want_k, why = np.zeros(0, np.int64), np.zeros(0), 0, "F2_hold_row_must_be_empty"
            else:
                si, sv = vec(V, src, k)
                if len(si) == 0 and arm != "F0":
                    a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
                    want_i, want_v, want_k = TA["scaled_idx"][a:b].astype(np.int64), TA["scaled_val"][a:b], int(kind_a[k])
                    why = "named_not_applicable_left_at_F0"; na.append(int(A[k]))
                else:
                    o = np.argsort(si, kind="stable"); want_i, want_v, want_k = si[o], np.asarray(sv, np.float64)[o], ARM_KIND[arm]
                    why = f"fallback_row_must_be_{src}"
        if int(kind_w[k]) != want_k:
            fail(f"{arm}.kind@{iso(A[k])}", False, dict(got=int(kind_w[k]), want=want_k, why=why)); return None
        if bits(i_w.astype(np.int64)) != bits(want_i.astype(np.int64)) or bits(v_w) != bits(np.asarray(want_v, np.float64)):
            fail(f"{arm}.row@{iso(A[k])}", False, dict(n_got=len(i_w), n_want=len(want_i), why=why)); return None
    return na


def main():
    t0 = time.time()
    src, shas, recs, V, TA, R, A = load_archive()
    rec = {"device": "fcf_targets.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": "docs/PREREG_fallback_counterfactual_2026-09-20.md (a964c2f9a) §2",
           "inputs": {k: {"path": v, "sha256": shas[k]} for k, v in src.items()},
           "population": {"n_anchors": int(len(A)), "axis": [iso(A[0]), iso(A[-1])], "reading": "scaled (B-scaled main)"},
           "judge_window": {"first_anchor": iso(JUDGE_FIRST_ANCHOR), "last_anchor": iso(JUDGE_LAST_ANCHOR)},
           "python": sys.version.split()[0], "numpy": np.__version__, "utc": iso(time.time()), "checks": [], "arms": {}}
    FAILS = []

    def check(name, ok, detail=None):
        rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:220] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    kind_a = archived_kind(TA)
    fb = kind_a == 1                                       # the failing-preflight population, from the ARCHIVE, shared by every arm
    check("population.closed", int(fb.sum()) + int((kind_a == 2).sum()) + int((kind_a == 0).sum()) == len(A),
          dict(n=int(len(A)), king=int(fb.sum()), combo=int((kind_a == 2).sum()), hold=int((kind_a == 0).sum())))
    bad = [iso(r["anchor"]) for r, b in zip(recs, fb) if (str(r.get("traded_scaled")) == "king") != bool(b)]
    check("population.matches_traded_scaled_records", not bad, dict(n_king=int(fb.sum()), n_mismatch=len(bad), first=bad[:3]))

    built = {}
    for arm in ARMS:
        out, cls = build_arm(arm, V, TA, A)
        na = assert_structure(arm, out, cls, V, TA, A, check)
        if na is None: break
        check(f"{arm}.structural_assertion_full_population", True,
              dict(n=int(len(A)), unchanged=int((cls == "unchanged").sum()), rule=int((cls == "rule").sum()),
                   not_applicable=int((cls == "not_applicable").sum())))
        check(f"{arm}.not_applicable_named_and_outside_judge_window", all(a < JUDGE_FIRST_ANCHOR or a > JUDGE_LAST_ANCHOR for a in na),
              dict(anchors=[iso(a) for a in na], n=len(na)))
        built[arm] = (out, cls, na)

    if "F0" in built:
        out = built["F0"][0]
        same = all(bits(out[k]) == bits(TA[k].astype(out[k].dtype) if TA[k].dtype != out[k].dtype else TA[k])
                   for k in ("anchor", "scaled_kind", "scaled_off", "scaled_idx", "scaled_val"))
        exact = all(str(TA[k].dtype) == str(out[k].dtype) for k in ("scaled_kind", "scaled_off", "scaled_idx", "scaled_val"))
        check("A1.F0_reproduces_the_archived_production_target_bitwise", bool(same and exact),
              dict(arrays_equal=bool(same), dtypes_equal=bool(exact),
                   detail={k: [str(TA[k].dtype), str(out[k].dtype)] for k in ("scaled_kind", "scaled_off", "scaled_idx", "scaled_val")}))

    if len(built) == len(ARMS):
        base = built["F0"][0]
        for arm in ARMS:
            out = built[arm][0]
            diff = [k for k in range(len(A)) if not (int(out["scaled_kind"][k]) == int(base["scaled_kind"][k])
                    and bits(out["scaled_idx"][out["scaled_off"][k]:out["scaled_off"][k + 1]]) == bits(base["scaled_idx"][base["scaled_off"][k]:base["scaled_off"][k + 1]])
                    and bits(out["scaled_val"][out["scaled_off"][k]:out["scaled_off"][k + 1]]) == bits(base["scaled_val"][base["scaled_off"][k]:base["scaled_off"][k + 1]]))]
            check(f"A2.{arm}.differs_from_F0_only_on_failing_preflight_anchors", all(bool(fb[k]) for k in diff),
                  dict(n_rows_changed=len(diff), n_failing=int(fb.sum()), all_inside_failing_set=all(bool(fb[k]) for k in diff)))
            check(f"A3.{arm}.failing_preflight_population_unchanged", int((archived_kind(TA) == 1).sum()) == int(fb.sum()), int(fb.sum()))

    if FAILS:
        rec["VERDICT"] = "REFUSED"; rec["failed"] = FAILS
        json.dump(rec, open(f"{OUT}/receipts/FCF_TARGETS.json", "w"), indent=1)
        print("FCF_TARGETS VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    for arm in ARMS:
        out, cls, na = built[arm]
        p = f"{OUT}/work/TARGETS_{arm}_A0_main.npz"
        np.savez_compressed(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
        npz_sha = sha(p)
        kc = {"combo": int((out["scaled_kind"] == 2).sum()), "king": int((out["scaled_kind"] == 1).sum()), "hold": int((out["scaled_kind"] == 0).sum())}
        rl = np.diff(out["scaled_off"])
        doc = {"tag": f"{arm}_A0_main", "arm": "A0", "data": R.get("data"), "fcf_arm": arm, "fcf_arm_rule": ARM_DOC[arm],
               "comparison_type": "(1) historical recipe — object B, F-family fallback counterfactual (targets only; no returns)",
               "axis": [iso(A[0]), iso(A[-1])], "n_anchors": int(len(A)),
               "B_CORE_start": R.get("B_CORE_start"), "PRE_window": R.get("PRE_window"),
               "source_targets_npz_sha256": shas["TARGETS_arch"], "p3_vec_sha256": shas["P3_vec"], "p3_json_sha256": shas["P3_json"],
               "counts": kc, "n_rows_rule_applied": int((cls == "rule").sum()), "n_rows_unchanged": int((cls == "unchanged").sum()),
               "not_applicable": {"n": len(na), "anchors": [int(a) for a in na], "anchors_utc": [iso(a) for a in na],
                                  "reason": "no combo/kc vector exists at this anchor (cold start of the chain: the combo stage had no kc/fc state); "
                                            "left at the F0 value, never imputed, asserted outside the judge window (E-0920-C)"},
               "written_rows_without_weights": int(((out["scaled_kind"] > 0) & (rl == 0)).sum()),
               "self_sha256": rec["self_sha256"], "utc": iso(time.time())}
        doc["targets_npz_sha256"] = npz_sha
        json.dump(doc, open(f"{OUT}/receipts/TARGETS_{arm}_A0_main.json", "w"), indent=1)
        rec["arms"][arm] = {"npz": p, "npz_sha256": npz_sha, "receipt": f"{OUT}/receipts/TARGETS_{arm}_A0_main.json",
                            "receipt_sha256": sha(f"{OUT}/receipts/TARGETS_{arm}_A0_main.json"), "counts": kc,
                            "n_rule_applied": int((cls == "rule").sum()), "not_applicable": [int(a) for a in na], "rule": ARM_DOC[arm]}
        print(arm, json.dumps(kc), "rule_applied", int((cls == "rule").sum()), "na", [iso(a) for a in na], flush=True)

    rec["VERDICT"] = "PASS"; rec["failed"] = []; rec["runtime_s"] = round(time.time() - t0, 1)
    json.dump(rec, open(f"{OUT}/receipts/FCF_TARGETS.json", "w"), indent=1)
    print(f"FCF_TARGETS VERDICT=PASS checks={len(rec['checks'])} runtime={rec['runtime_s']}s receipt_sha256=" + sha(f"{OUT}/receipts/FCF_TARGETS.json"), flush=True)


def selftest():
    """The structural assertion is only evidence if it can go red. Baseline GREEN first (a red-capability check is vacuous when the
    baseline is already red, 2026-09-16), then four named mutations of the WRITTEN output, each of which MUST make it fail.
    M4 is the one that matters most: it is exactly the E-0920-C failure mode — a fallback anchor silently left at its F0 value."""
    src, shas, recs, V, TA, R, A = load_archive()
    kind_a = archived_kind(TA); fbk = int(np.nonzero(kind_a == 1)[0][900])   # a fallback anchor well inside the judge window
    log = []

    def run(label, mutate):
        out, cls = build_arm("F1", V, TA, A)                       # built from CLEAN inputs
        if mutate: mutate(out)                                     # then the WRITTEN output is corrupted
        fails = []
        assert_structure("F1", out, cls, V, TA, A, lambda n, ok, d=None: fails.append(n))
        ok = (len(fails) == 0)
        log.append((label, ok, fails[:2])); print(("GREEN " if ok else "RED   ") + label, fails[:2], flush=True)
        return ok

    base_green = run("baseline (no mutation) must be GREEN", None)
    if not base_green:
        print("SELFTEST VERDICT=REFUSED baseline is not green; every mutation check below would be vacuous", flush=True); sys.exit(3)
    m1 = not run("M1 one written weight moved by 1 ulp must be RED", lambda o: _bump_val(o, fbk))
    m2 = not run("M2 one written kind flipped must be RED", lambda o: o["scaled_kind"].__setitem__(fbk, 2 if o["scaled_kind"][fbk] != 2 else 1))
    m3 = not run("M3 one written column index changed must be RED", lambda o: _bump_idx(o, fbk))
    m4 = not run("M4 one fallback anchor silently left at its F0 value must be RED (E-0920-C shape)", lambda o: _revert_to_F0(o, TA, fbk))
    ok = base_green and m1 and m2 and m3 and m4
    doc = {"device": "fcf_targets.py --selftest", "self_sha256": sha(os.path.abspath(__file__)),
           "rule": "a mutation check is only evidence when the unmutated baseline is green (2026-09-16)",
           "mutated_anchor": iso(A[fbk]), "results": [{"case": a, "green": b, "first_failures": c} for a, b, c in log],
           "VERDICT": "PASS" if ok else "REFUSED", "utc": iso(time.time())}
    json.dump(doc, open(f"{OUT}/receipts/FCF_TARGETS_SELFTEST.json", "w"), indent=1)
    print("FCF_TARGETS_SELFTEST VERDICT=" + doc["VERDICT"] + f" (baseline green, {sum([m1, m2, m3, m4])}/4 mutations caught)", flush=True)
    sys.exit(0 if ok else 3)


def _bump_val(o, k):
    j = int(o["scaled_off"][k]); o["scaled_val"][j] = np.nextafter(o["scaled_val"][j], np.inf)


def _bump_idx(o, k):
    j = int(o["scaled_off"][k]); o["scaled_idx"][j] = np.int16((int(o["scaled_idx"][j]) + 1) % 829)


def _revert_to_F0(o, TA, k):
    """replace row k with the archived (F0) row, keeping the CSR consistent — the silent 'left it as it was' defect"""
    a, b = int(TA["scaled_off"][k]), int(TA["scaled_off"][k + 1])
    lo, hi = int(o["scaled_off"][k]), int(o["scaled_off"][k + 1])
    o["scaled_idx"] = np.concatenate([o["scaled_idx"][:lo], TA["scaled_idx"][a:b].astype(np.int16), o["scaled_idx"][hi:]])
    o["scaled_val"] = np.concatenate([o["scaled_val"][:lo], TA["scaled_val"][a:b], o["scaled_val"][hi:]])
    d = (b - a) - (hi - lo); o["scaled_off"][k + 1:] += d; o["scaled_kind"][k] = TA["scaled_kind"][k]


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
