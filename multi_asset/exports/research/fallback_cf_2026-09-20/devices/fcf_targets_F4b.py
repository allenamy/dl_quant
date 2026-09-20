#!/usr/bin/env python3
"""fcf_targets_F4b.py — build the F4b arm's TARGETS npz from the F4b counterfactual re-chain. Additive: it does not touch the
F0/F1/F2/F4a files or their receipt.

ARM F4b (PREREG §2 F4, reading b — the clean single-variable control):
  preflight PASSED at this anchor -> the archived combo row, untouched (identical to every other arm)
  preflight FAILED at this anchor -> the king file the F4b producer wrote at that anchor, i.e. the producer's own book with the rev24
                                     leg removed and NOTHING else changed (fcf_mk_producer_F4b.py gates G1-G4: exactly one changed
                                     line, line 449; fcf_rechain_assert.py: member sets, all three leg z-vectors and the funding state
                                     bitwise identical to the archived P1 run, so the msharpe seat is unchanged by measurement)
  preflight FAILED and the F4b producer wrote NO file -> kind 0 (hold), the executor's own on_unavailable = hold carries the book.
                                     This is the ARM'S REAL OUTCOME, not a missing measurement: with rev24 removed the book signal was
                                     identically zero, so shadow_loop_v3_replay.run_anchor returned at `if g < 1e-9` without writing.
                                     It is counted and named separately from the F1/F4a "not applicable" subset, which is a different
                                     thing (there the arm's source vector does not exist in the archive at all).

PRODUCTION DEFINITION LINES (E-0920-B) — the ones this arm's rule turns on, copied verbatim:
b_driver.py L261:  scaled = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= f150) and inside and (n_in >= f150) and (g_in > 0.4) and king_w is not None
b_driver.py L343:                  rec["traded_scaled"] = "combo" if crec.get("scaled_ok") else "king"
b_targets.py L40:        elif t == "king": kd = 1; i_, v_ = vec("king_file", k)
shadow_loop_v3_replay.py L449 (the intervention, before -> after):
    z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])
    z = w3[0] * np.nan_to_num(legz["king"]) + 0.0    * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])

usage: fcf_targets_F4b.py [--selftest]
"""
import hashlib, json, os, sys, time

import numpy as np

OBJB = "/workspace/object_b_2026-09-19"
W = f"{OBJB}/work/A0_main"
OUT = "/workspace/fallback_cf_2026-09-20"
JUDGE_FIRST_ANCHOR = 1656547200
JUDGE_LAST_ANCHOR = 1788480000
ARM = "F4b"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def bits(a): return (str(a.dtype), a.shape, a.tobytes())


def load():
    T = np.load(f"{W}/TARGETS_A0_main.npz"); TA = {k: T[k] for k in T.files}
    R = json.load(open(f"{OBJB}/receipts/TARGETS_A0_main.json"))
    K = np.load(f"{OUT}/work/F4b_KING.npz"); VK = {k: K[k] for k in K.files}
    A = TA["anchor"].astype(np.int64)
    assert R["targets_npz_sha256"] == sha(f"{W}/TARGETS_A0_main.npz")
    return TA, R, VK, A


def f4b_row(VK, kpos, A_):
    """the F4b king FILE row at this anchor, or None when the F4b producer wrote no file"""
    k = kpos.get(int(A_))
    if k is None: return None
    a, b = VK["king_file_off"][k], VK["king_file_off"][k + 1]
    return VK["king_file_idx"][a:b].astype(np.int64), VK["king_file_val"][a:b]


def build(TA, VK, A):
    kpos = {int(a): i for i, a in enumerate(VK["anchor"].astype(np.int64))}
    kind_a = TA["scaled_kind"].astype(np.int8); n = len(A)
    kinds = np.zeros(n, np.int8); idxs = []; vals = []; offs = [0]; cls = []
    for k in range(n):
        if kind_a[k] != 1:
            a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
            i_, v_ = TA["scaled_idx"][a:b].astype(np.int64), TA["scaled_val"][a:b]
            kinds[k] = kind_a[k]; cls.append("unchanged")
        else:
            r = f4b_row(VK, kpos, A[k])
            if r is None or len(r[0]) == 0:
                i_, v_ = np.zeros(0, np.int64), np.zeros(0); kinds[k] = 0; cls.append("rule_no_book_written")
            else:
                i_, v_ = r; kinds[k] = 1; cls.append("rule")
        o = np.argsort(i_, kind="stable")
        idxs.append(i_[o].astype(np.int16)); vals.append(np.asarray(v_, np.float64)[o]); offs.append(offs[-1] + len(i_))
    return {"anchor": A.astype(np.int64), "scaled_kind": kinds, "scaled_off": np.array(offs, np.int64),
            "scaled_idx": np.concatenate(idxs).astype(np.int16) if offs[-1] else np.zeros(0, np.int16),
            "scaled_val": np.concatenate(vals) if offs[-1] else np.zeros(0)}, np.array(cls)


def assert_structure(out, TA, VK, A, fail):
    """independent recomputation of every row from the arm's rule, over the whole population"""
    kpos = {int(a): i for i, a in enumerate(VK["anchor"].astype(np.int64))}
    kind_a = TA["scaled_kind"].astype(np.int8); n = len(A); off_w = out["scaled_off"]
    for k in range(n):
        i_w = out["scaled_idx"][off_w[k]:off_w[k + 1]].astype(np.int64); v_w = out["scaled_val"][off_w[k]:off_w[k + 1]]
        if kind_a[k] != 1:
            a, b = TA["scaled_off"][k], TA["scaled_off"][k + 1]
            wi, wv, wk = TA["scaled_idx"][a:b].astype(np.int64), TA["scaled_val"][a:b], int(kind_a[k])
        else:
            r = f4b_row(VK, kpos, A[k])
            if r is None or len(r[0]) == 0: wi, wv, wk = np.zeros(0, np.int64), np.zeros(0), 0
            else:
                o = np.argsort(r[0], kind="stable"); wi, wv, wk = r[0][o], np.asarray(r[1], np.float64)[o], 1
        if int(out["scaled_kind"][k]) != wk or bits(i_w.astype(np.int64)) != bits(wi.astype(np.int64)) or bits(v_w) != bits(np.asarray(wv, np.float64)):
            fail(f"F4b.row@{iso(A[k])}", False, dict(kind_got=int(out["scaled_kind"][k]), kind_want=wk, n_got=len(i_w), n_want=len(wi)))
            return False
    return True


def main():
    t0 = time.time()
    TA, R, VK, A = load()
    ar = json.load(open(f"{OUT}/receipts/FCF_RECHAIN_ASSERT.json"))
    rc = json.load(open(f"{OUT}/receipts/FCF_RECHAIN_F4b.json"))
    rec = {"device": "fcf_targets_F4b.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": "docs/PREREG_fallback_counterfactual_2026-09-20.md §2 F4 (reading b: the clean single-variable rev24 ablation)",
           "inputs": {"TARGETS_arch": {"path": f"{W}/TARGETS_A0_main.npz", "sha256": sha(f"{W}/TARGETS_A0_main.npz")},
                      "F4b_KING": {"path": f"{OUT}/work/F4b_KING.npz", "sha256": sha(f"{OUT}/work/F4b_KING.npz")},
                      "rechain_receipt": {"path": f"{OUT}/receipts/FCF_RECHAIN_F4b.json", "sha256": sha(f"{OUT}/receipts/FCF_RECHAIN_F4b.json")},
                      "rechain_assert_receipt": {"path": f"{OUT}/receipts/FCF_RECHAIN_ASSERT.json", "sha256": sha(f"{OUT}/receipts/FCF_RECHAIN_ASSERT.json")},
                      "producer_gate_receipt": {"path": f"{OUT}/receipts/FCF_PRODUCER_F4b.json", "sha256": sha(f"{OUT}/receipts/FCF_PRODUCER_F4b.json")}},
           "utc": iso(time.time()), "checks": []}
    FAILS = []

    def check(name, ok, detail=None):
        rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:240] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    check("G0.rechain_structural_assertion_passed", ar.get("VERDICT") == "PASS", dict(verdict=ar.get("VERDICT"), failed=ar.get("failed")))
    check("G0.producer_intervention_gate_passed", json.load(open(f"{OUT}/receipts/FCF_PRODUCER_F4b.json")).get("VERDICT") == "PASS")
    check("G0.rechain_is_not_a_smoke", rc.get("smoke_n_anchors") in (None, 0) and rc["anchors"][2] == len(A),
          dict(smoke=rc.get("smoke_n_anchors"), n_anchors=rc["anchors"][2], want=len(A)))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/TARGETS_F4b_GATE.json", "w"), indent=1)
        print("FCF_TARGETS_F4b VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    out, cls = build(TA, VK, A)
    ok = assert_structure(out, TA, VK, A, check)
    kind_a = TA["scaled_kind"].astype(np.int8); fb = kind_a == 1
    check("F4b.structural_assertion_full_population", ok,
          dict(n=int(len(A)), unchanged=int((cls == "unchanged").sum()), rule=int((cls == "rule").sum()),
               rule_no_book_written=int((cls == "rule_no_book_written").sum())))
    diff = [k for k in range(len(A)) if not (int(out["scaled_kind"][k]) == int(kind_a[k])
            and bits(out["scaled_idx"][out["scaled_off"][k]:out["scaled_off"][k + 1]]) == bits(TA["scaled_idx"][TA["scaled_off"][k]:TA["scaled_off"][k + 1]])
            and bits(out["scaled_val"][out["scaled_off"][k]:out["scaled_off"][k + 1]]) == bits(TA["scaled_val"][TA["scaled_off"][k]:TA["scaled_off"][k + 1]]))]
    check("A2.F4b_differs_from_F0_only_on_failing_preflight_anchors", all(bool(fb[k]) for k in diff),
          dict(n_rows_changed=len(diff), n_failing=int(fb.sum())))
    check("A4.the_switch_is_wired_the_book_really_changed_on_fallback_anchors", len(diff) >= 0.90 * int(fb.sum()),
          dict(n_changed=len(diff), n_failing=int(fb.sum()), share=round(len(diff) / max(int(fb.sum()), 1), 6), threshold=0.90))
    nb = [int(A[k]) for k in range(len(A)) if cls[k] == "rule_no_book_written"]
    inside = [a for a in nb if JUDGE_FIRST_ANCHOR <= a <= JUDGE_LAST_ANCHOR]
    check("S-POPULATION.no_book_anchors_named_and_located", True,
          dict(n=len(nb), n_inside_judge_window=len(inside), first=[iso(a) for a in nb[:3]], last=[iso(a) for a in nb[-3:]]))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/TARGETS_F4b_GATE.json", "w"), indent=1)
        print("FCF_TARGETS_F4b VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    p = f"{OUT}/work/TARGETS_F4b_A0_main.npz"
    np.savez_compressed(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
    kc = {"combo": int((out["scaled_kind"] == 2).sum()), "king": int((out["scaled_kind"] == 1).sum()), "hold": int((out["scaled_kind"] == 0).sum())}
    rl = np.diff(out["scaled_off"])
    doc = {"tag": "F4b_A0_main", "arm": "A0", "data": R.get("data"), "fcf_arm": ARM,
           "fcf_arm_rule": "preflight failed -> the king book the F4b counterfactual producer wrote (rev24 leg removed, one line, nothing else); "
                           "if that producer wrote no file, hold",
           "comparison_type": "(1) historical recipe — object B, F-family fallback counterfactual, F4b re-chain (targets only; no returns)",
           "axis": [iso(A[0]), iso(A[-1])], "n_anchors": int(len(A)), "B_CORE_start": R.get("B_CORE_start"), "PRE_window": R.get("PRE_window"),
           "source_targets_npz_sha256": sha(f"{W}/TARGETS_A0_main.npz"), "f4b_king_npz_sha256": sha(f"{OUT}/work/F4b_KING.npz"),
           "counts": kc, "n_rows_rule_applied": int((cls == "rule").sum()),
           "arm_outcome_no_book_written": {"n": len(nb), "n_inside_judge_window": len(inside), "anchors_utc": [iso(a) for a in nb],
                                           "meaning": "the F4b producer's book signal was identically zero, so it wrote nothing and the executor holds; "
                                                      "this is the arm's real outcome, NOT a missing measurement"},
           "written_rows_without_weights": int(((out["scaled_kind"] > 0) & (rl == 0)).sum()),
           "self_sha256": rec["self_sha256"], "utc": iso(time.time())}
    doc["targets_npz_sha256"] = sha(p)
    json.dump(doc, open(f"{OUT}/receipts/TARGETS_F4b_A0_main.json", "w"), indent=1)
    rec["VERDICT"] = "PASS"; rec["failed"] = []; rec["runtime_s"] = round(time.time() - t0, 1)
    rec["arm"] = {"npz": p, "npz_sha256": sha(p), "receipt": f"{OUT}/receipts/TARGETS_F4b_A0_main.json",
                  "receipt_sha256": sha(f"{OUT}/receipts/TARGETS_F4b_A0_main.json"), "counts": kc}
    json.dump(rec, open(f"{OUT}/receipts/TARGETS_F4b_GATE.json", "w"), indent=1)
    print("F4b", json.dumps(kc), "rule", int((cls == 'rule').sum()), "no_book", len(nb), "inside_window", len(inside), flush=True)
    print("FCF_TARGETS_F4b VERDICT=PASS checks=%d receipt_sha256=%s" % (len(rec["checks"]), sha(f"{OUT}/receipts/TARGETS_F4b_GATE.json")), flush=True)


if __name__ == "__main__":
    main()
