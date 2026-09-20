#!/usr/bin/env python3
"""fcf_rechain_assert.py — the two-sided structural assertion on the F4b re-chain. Run AFTER fcf_rechain_F4b.py; it emits no result
number and its only job is to decide whether the re-chain may be used at all.

S-IDENTICAL  Everything UPSTREAM of the one changed line (shadow_loop_v3_replay.py L449) must come back BITWISE identical to the
             archived object-B P1 run, anchor by anchor:
               pm    the member set                       (chosen before step 8; nothing to do with z)
               legz  the three leg z-vectors king/rev24/fund, L448 — the line immediately above the intervention
               fe    the funding EMA accumulator per name
               fn    the last funding rate per name
             This is the PROOF that the msharpe seat w3 is unchanged, because w3 is built only from the leg return ledger, which is
             built only from legz and the cache (L410-416, L434-437) — not from the book. The prereg's "不改席位" therefore holds by
             measurement, not by argument. It is also the proof that this harness reproduces the production data path.
S-DIFFERENT  The book sm must actually differ on a large share of anchors. A re-chain whose book came back identical would mean the
             switch was never wired ("零差 = 开关没接上").
S-SEAT       The producer's own logged w3 must equal the archive's logged w3 at every shared anchor. NOTE THE PRECISION HONESTLY: the
             producer logs w3 rounded to 4 decimals (shadow_loop_v3_replay.py L528 `"w3": [round(float(x), 4) for x in w3]`), so this
             check is exact only to 1e-4. It is reported as such and is NOT called bitwise; the bitwise part of the seat claim is
             S-IDENTICAL on legz, which is w3's only book-side input.
S-POPULATION E-0920-C: the anchors where the F4b producer wrote NO book are a named, counted subset, never imputed and never averaged
             with anchors that have a book. They are a real outcome of the counterfactual (at the cold start the king leg has no fold
             and the funding EMA is empty, so with rev24 removed z is identically zero and run_anchor returns at `if g < 1e-9` —
             silently, with no anchor_skip record), not a measurement failure.

usage: fcf_rechain_assert.py [--smoke]
"""
import hashlib, json, os, sys, time

import numpy as np

OUT = "/workspace/fallback_cf_2026-09-20"
ARCH = "/workspace/object_b_2026-09-19/work/A0_main"
SM = "_smoke" if "--smoke" in sys.argv else ""
MINE_VEC = f"{OUT}/work/F4b_P1{SM}.vec.npz"; MINE_JSON = f"{OUT}/work/F4b_P1{SM}.json"
DIFF_MIN_SHARE = 0.90    # frozen before the numbers: at least this share of shared, written anchors must have a different book


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def row(V, name, k):
    a, b = V[name + "_off"][k], V[name + "_off"][k + 1]
    return V[name][a:b]


def main():
    Za = np.load(f"{ARCH}/P1.vec.npz"); VA = {k: Za[k] for k in Za.files}
    Zm = np.load(MINE_VEC); VM = {k: Zm[k] for k in Zm.files}
    AA = VA["anchor"].astype(np.int64); AM = VM["anchor"].astype(np.int64)
    pa = {int(a): i for i, a in enumerate(AA)}
    rec = {"device": "fcf_rechain_assert.py", "self_sha256": sha(os.path.abspath(__file__)),
           "archive_p1_vec_sha256": sha(f"{ARCH}/P1.vec.npz"), "mine_p1_vec_sha256": sha(MINE_VEC),
           "rechain_receipt_sha256": sha(f"{OUT}/receipts/FCF_RECHAIN_F4b{SM}.json") if os.path.exists(f"{OUT}/receipts/FCF_RECHAIN_F4b{SM}.json") else None,
           "smoke": bool(SM), "utc": iso(time.time()), "checks": []}
    FAILS = []

    def check(name, ok, detail=None):
        rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    # S-POPULATION: the closed population is the archived axis; the named subsets are stated with n
    not_written = sorted(set(AA.tolist()) - set(AM.tolist()))
    extra = sorted(set(AM.tolist()) - set(AA.tolist()))
    shared = [int(a) for a in AM if int(a) in pa]
    check("S-POPULATION.closed", len(shared) + len(extra) == len(AM) and len(shared) + len(not_written) == len(AA),
          dict(n_archive=len(AA), n_f4b_written=len(AM), n_shared=len(shared), n_archive_only_f4b_wrote_nothing=len(not_written), n_f4b_only=len(extra)))
    check("S-POPULATION.no_anchor_outside_the_archived_axis", not extra, dict(n=len(extra), first=[iso(a) for a in extra[:3]]))
    rec["f4b_wrote_no_book"] = {"n": len(not_written), "anchors_utc": [iso(a) for a in not_written],
                                "reason": "with rev24 removed the book signal z was identically zero at this anchor, so run_anchor returned at "
                                          "`if g < 1e-9` without writing; in the F4b world the executor holds. NAMED, never imputed (E-0920-C)",
                                "last": iso(not_written[-1]) if not_written else None}

    ident = {"pm": 0, "legz": 0, "fe": 0, "fn": 0}; nshared = 0; diff_sm = 0; first_bad = {}
    for km, A in enumerate(AM):
        ka = pa.get(int(A))
        if ka is None: continue
        nshared += 1
        for nm in ("pm", "legz"):
            a_ = row(VA, nm, ka); m_ = row(VM, nm, km)
            if a_.dtype == m_.dtype and a_.shape == m_.shape and a_.tobytes() == m_.tobytes(): ident[nm] += 1
            elif nm not in first_bad: first_bad[nm] = dict(anchor=iso(A), n_arch=len(a_), n_mine=len(m_))
        for nm in ("fe", "fn"):
            a_ = VA[nm][ka]; m_ = VM[nm][km]
            if a_.dtype == m_.dtype and a_.shape == m_.shape and a_.tobytes() == m_.tobytes(): ident[nm] += 1
            elif nm not in first_bad: first_bad[nm] = dict(anchor=iso(A))
        sa = row(VA, "sm", ka); sm_ = row(VM, "sm", km)
        si_a = row(VA, "sm_idx", ka); si_m = row(VM, "sm_idx", km)
        if not (sa.shape == sm_.shape and sa.tobytes() == sm_.tobytes() and si_a.shape == si_m.shape and si_a.tobytes() == si_m.tobytes()):
            diff_sm += 1
    for nm in ("pm", "legz", "fe", "fn"):
        check(f"S-IDENTICAL.{nm}_bitwise_equal_to_the_archived_P1_on_every_shared_anchor", ident[nm] == nshared,
              dict(equal=ident[nm], shared=nshared, first_mismatch=first_bad.get(nm)))
    check("S-DIFFERENT.the_book_actually_changed", nshared > 0 and diff_sm >= DIFF_MIN_SHARE * nshared,
          dict(anchors_with_a_different_book=diff_sm, shared=nshared, share=round(diff_sm / nshared, 6) if nshared else None,
               threshold=DIFF_MIN_SHARE, note="frozen before the numbers"))

    wa = {int(r["anchor"]): ((r.get("signal") or {}).get("w3")) for r in json.load(open(f"{ARCH}/P1.json"))["records"]}
    wm = json.load(open(f"{OUT}/work/F4b_w3{SM}.json"))
    wmine = {int(a): w for a, w in zip(wm["anchor"], wm["w3"])}
    bad_seat = []; n_seat = 0
    for a in shared:
        x, y = wa.get(a), wmine.get(a)
        if x is None or y is None: continue
        n_seat += 1
        if [round(float(v), 4) for v in x] != [round(float(v), 4) for v in y]: bad_seat.append(iso(a))
    check("S-SEAT.logged_w3_equal_to_the_archive_at_every_shared_anchor_to_1e-4", not bad_seat,
          dict(n_compared=n_seat, n_mismatch=len(bad_seat), first=bad_seat[:3],
               precision="the producer logs w3 rounded to 4 decimals (L528); this check is exact only to 1e-4 and is NOT a bitwise claim — "
                         "the bitwise part of the seat claim is S-IDENTICAL.legz"))

    rec["VERDICT"] = "PASS" if not FAILS else "REFUSED"; rec["failed"] = FAILS
    p = f"{OUT}/receipts/FCF_RECHAIN_ASSERT{SM}.json"
    json.dump(rec, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
    print(f"FCF_RECHAIN_ASSERT VERDICT={rec['VERDICT']} checks={len(rec['checks'])} failed={len(FAILS)} receipt_sha256={sha(p)}", flush=True)
    sys.exit(0 if rec["VERDICT"] == "PASS" else 3)


if __name__ == "__main__":
    main()
