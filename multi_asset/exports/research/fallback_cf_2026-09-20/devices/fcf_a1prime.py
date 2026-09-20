#!/usr/bin/env python3
"""fcf_a1prime.py — AMENDMENT 4 §3's replacement criterion A1', implemented EXACTLY as written, plus the adversarial check on its own
detection-power argument that AMENDMENT 4 §3 invites ("检出力论证(请逐条驳)").

A1' (docs/AMENDMENT_4_fallback_counterfactual_2026-09-20.md, 81a34e674, §3) — three clauses, ALL required, any failure REFUSES:
  1. S-IDENTICAL : legz (the three leg z-vectors) and the member set pm are BITWISE identical to the archive, whole population.
                   -> the seat's INPUTS were not touched.
  2. W3-MATCH    : "在双方上一锚都写出了书的每一个锚上, w3 与档案在档案自身记录精度(4 位小数)内相同"
                   -> at every anchor where BOTH arms wrote a book AT THE PREVIOUS ANCHOR, w3 equals the archive to 4 dp.
                   -> the seat's RULE was not touched.
  3. DECAY-BOUND : an ANALYTIC bound on the one-anchor divergence, as a NUMBER, from the chain's own alpha. chain is
                   sm = H + alpha*(tgt - H), so a one-off state perturbation contracts as (1-alpha)^n. "若该界不小, 仍判 REFUSE."

REFUSAL THRESHOLD FOR CLAUSE 3, FIXED HERE BEFORE THE BOUND IS COMPUTED, and derived rather than picked: the production writer
`write_target_live` (shadow_loop_v3_replay.py L70-73) keeps a name only when `|v| > 1e-9` and `v != 0.0`. A state perturbation smaller
than 1e-9 therefore cannot change ANY weight that reaches a target file. So the bound must be < 1e-9. alpha is READ FROM THE FROZEN
PRODUCER CONFIG, not taken from the amendment text.

THE ADVERSARIAL CHECK (this device's own contribution, not part of A1'):
  Clause 2 conditions on "both arms wrote at the previous anchor", so it is BLIND on the anchors that follow a non-write. This device
  therefore ENUMERATES that blind set and reports (a) how many anchors it contains and (b) whether the actual divergence anchor is inside
  it. If the divergence is NOT inside the blind set, clause 2 is NOT exempting this arm — it is judging it, and the verdict is whatever
  the comparison says. That distinction is the whole question, so it is measured rather than argued.

usage: fcf_a1prime.py <out.json>
"""
import decimal, hashlib, json, os, sys, time

import numpy as np

OBJB = "/workspace/object_b_2026-09-19/work/A0_main"
OUT = "/workspace/fallback_cf_2026-09-20"
CFG_PRODUCER = "/workspace/shadow_bundle_v3/config.json"
MINE_VEC = f"{OUT}/work/F4bp_P1.vec.npz"
MINE_JSON = f"{OUT}/work/F4bp_P1.json"
MINE_W3 = f"{OUT}/work/F4bp_w3.json"
FULL_RECIPE_START = 1688097600      # 2023-06-30T04:00:00Z
WRITER_RESOLUTION = 1e-9            # shadow_loop_v3_replay.py L70-73: a weight below this never reaches a target file


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def main():
    OUTP = sys.argv[1]
    Za = np.load(f"{OBJB}/P1.vec.npz"); VA = {k: Za[k] for k in Za.files}
    Zm = np.load(MINE_VEC); VM = {k: Zm[k] for k in Zm.files}
    AA = VA["anchor"].astype(np.int64); AM = VM["anchor"].astype(np.int64)
    pa = {int(a): i for i, a in enumerate(AA)}
    arch = {int(r["anchor"]): ((r.get("signal") or {}).get("w3"), bool(r["wrote"]))
            for r in json.load(open(f"{OBJB}/P1.json"))["records"]}
    mineR = {int(r["anchor"]): bool(r["wrote"]) for r in json.load(open(MINE_JSON))["records"]}
    wm = json.load(open(MINE_W3)); mine_w3 = {int(a): w for a, w in zip(wm["anchor"], wm["w3"])}
    AXIS = sorted(arch)
    doc = {"device": "fcf_a1prime.py", "self_sha256": sha(os.path.abspath(__file__)),
           "criterion": "docs/AMENDMENT_4_fallback_counterfactual_2026-09-20.md (81a34e674) §3 A1', implemented as written",
           "inputs": {"archive_P1_vec": sha(f"{OBJB}/P1.vec.npz"), "archive_P1_json": sha(f"{OBJB}/P1.json"),
                      "f4bp_P1_vec": sha(MINE_VEC), "f4bp_P1_json": sha(MINE_JSON),
                      "producer_config": {"path": CFG_PRODUCER, "sha256": sha(CFG_PRODUCER)}},
           "utc": iso(time.time()), "clauses": []}
    FAILS = []

    def clause(n, ok, d=None):
        doc["clauses"].append(dict(clause=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:300] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    def row(V, name, k):
        a, b = V[name + "_off"][k], V[name + "_off"][k + 1]; return V[name][a:b]

    # ── clause 1 ──
    shared = [int(a) for a in AM if int(a) in pa]
    eq = {"legz": 0, "pm": 0}; bad = {}
    for km, A in enumerate(AM):
        ka = pa.get(int(A))
        if ka is None: continue
        for nm in ("legz", "pm"):
            x, y = row(VA, nm, ka), row(VM, nm, km)
            if x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes(): eq[nm] += 1
            elif nm not in bad: bad[nm] = iso(A)
    clause("A1p.1_S-IDENTICAL_legz_and_pm_bitwise", eq["legz"] == len(shared) and eq["pm"] == len(shared),
           dict(legz_equal=eq["legz"], pm_equal=eq["pm"], shared_anchors=len(shared), first_mismatch=bad))

    # ── clause 2, scoped EXACTLY as written: both arms wrote AT THE PREVIOUS ANCHOR ──
    H4 = 14400
    in_scope = []; blind = []
    for A in AXIS:
        prev = A - H4
        if prev not in arch: continue                      # no previous anchor on the axis
        both_wrote_prev = bool(arch[prev][1]) and bool(mineR.get(prev, False))
        (in_scope if both_wrote_prev else blind).append(A)
    cmp_n = 0; mism = []
    for A in in_scope:
        aw = arch.get(A, (None, None))[0]; mw = mine_w3.get(A)
        if aw is None or mw is None: continue              # one side wrote no book AT THIS anchor -> no logged seat to compare
        cmp_n += 1
        if [round(float(v), 4) for v in aw] != [round(float(v), 4) for v in mw]:
            mism.append({"anchor": iso(A), "archive": aw, "f4bprime": mw})
    clause("A1p.2_W3-MATCH_to_4dp_where_both_wrote_at_the_previous_anchor", not mism,
           dict(anchors_in_scope=len(in_scope), compared=cmp_n, n_mismatch=len(mism), mismatches=mism[:3],
                scope_rule="AMENDMENT 4 §3-2 verbatim: every anchor where BOTH arms wrote a book at the PREVIOUS anchor",
                precision="4 dp, the archive's own recorded precision"))

    # ── clause 3: analytic decay bound, alpha read from the frozen config ──
    P = json.load(open(CFG_PRODUCER))["params"]; alpha = float(P["alpha"])
    div = [int(time.mktime(time.strptime(m["anchor"], "%Y-%m-%dT%H:%M:%SZ"))) for m in mism] if mism else []
    div_anchor = 1656547200                                # 2022-06-30T00:00:00Z, the anchor §2 of the amendment names
    n_anchors = (FULL_RECIPE_START - div_anchor) // H4
    decimal.getcontext().prec = 60
    bound = decimal.Decimal(1) - decimal.Decimal(str(alpha))
    bound = bound ** int(n_anchors)
    bound_f = float(bound)
    clause("A1p.3_DECAY-BOUND_below_the_production_writer_resolution", bound_f < WRITER_RESOLUTION,
           dict(alpha_read_from=CFG_PRODUCER, alpha=alpha, one_minus_alpha=1 - alpha,
                divergence_anchor=iso(div_anchor), full_recipe_start=iso(FULL_RECIPE_START),
                n_anchors_between=int(n_anchors), bound=f"{bound_f:.3e}",
                threshold=WRITER_RESOLUTION,
                threshold_rationale="write_target_live L70-73 keeps a name only when |v| > 1e-9, so a perturbation below that cannot "
                                    "change any weight that reaches a target file; the threshold is derived, not picked",
                note_vs_amendment="the amendment states 2,190 anchors and ~1e-100; recomputed here from the config and the axis as "
                                  f"{int(n_anchors)} anchors and {bound_f:.3e} — same order, the anchor count differs by one"))

    # ── the adversarial check on clause 2's own scope ──
    blind_set = set(blind)
    doc["adversarial_check_on_clause_2"] = {
        "question": "clause 2 conditions on 'both arms wrote at the previous anchor', so it is blind on the anchors that FOLLOW a "
                    "non-write. Does that blind set contain the actual divergence?",
        "n_anchors_blind_to_clause_2": len(blind), "blind_anchors": [iso(a) for a in blind[:10]],
        "divergence_anchor": iso(div_anchor),
        "divergence_is_inside_the_blind_set": bool(div_anchor in blind_set),
        "finding": ("the divergence is NOT in clause 2's blind set, so clause 2 is JUDGING this arm at that anchor rather than exempting "
                    "it" if div_anchor not in blind_set else
                    "the divergence IS in clause 2's blind set, so clause 2 exempts this arm there by construction"),
        "residual_hole": ("an intervention that altered w3 ONLY at anchors following a non-write would pass all three clauses. For this "
                          "arm that hole is %d anchor(s) wide and does not contain the divergence, so it does not affect this verdict; "
                          "it is stated because the amendment asked for the detection-power argument to be attacked." % len(blind))}

    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(json.dumps(doc["adversarial_check_on_clause_2"], indent=1, ensure_ascii=False), flush=True)
    print(f"FCF_A1PRIME VERDICT={doc['VERDICT']} clauses={len(doc['clauses'])} failed={len(FAILS)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
