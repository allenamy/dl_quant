"""HANDOFF ARTIFACT for 0B — a drift gate that cannot be disarmed by clearing its own red.

> created 2026-07-27 | Session: 0C (audit) | 状态: handoff reference implementation
> 作废条件: 0B 在 dl_quant_live/ops/ 落地等效实现后, 本文件降为审计留痕

WHY (the finding this answers)
------------------------------
`dl_quant_live/ops/check_upstream_drift.py` is one of the acceptance suites and has printed

    no drift across 0 vendored modules        exit 0

every run since 2026-07-25T15:44Z. Its fingerprint file `ops/UPSTREAM_MANIFEST.sha256` is 0 bytes.
Git shows it held 19 hashes at `2eed910` ("执行栈迁入 19模块+漂移守卫"), and the commit that says

    "drift_gate 如期变红(vendored副本被改), 按规矩同步回上游+更新指纹后复绿"

carries the stat line `ops/UPSTREAM_MANIFEST.sha256 | 19 -----------` — nineteen deletions, zero
insertions. **The procedure was followed in prose; the mechanism was removed in the artefact.**
"Refreshing the fingerprints" is the standard and correct-sounding repair for this gate's red, and
its failure mode is deleting them. The count that would have revealed it was printed in every
acceptance run for two days.

MEASURED INPUT (0C, 2026-07-27 — the map is data, the A/B call is 0B's decision)
--------------------------------------------------------------------------------
19 same-named files coexist in `dl_quant_live/live/` and `multi_asset/engine/live/`; 15 already
differ, several substantially:

    watchdog.py         1010 vs  491 lines      pilot_metrics.py   608 vs 329
    pilot_log.py         343 vs  199            run_acceptance.sh   29 vs  81
    watchdog_inputs.py   153 vs  130            + 10 more (broker/executor/funding/venue codes/6 suites)

Identical today: deliver_report.py, factor_version_registry.py, production_state_guard.py,
regime_classifier.py. (0C edited factor_version_registry.py on 2026-07-27 — a change this gate
would have caught had it been armed; reported by hand instead.)

THE THREE SELF-CHECKS (team-lead ruling 2026-07-27)
---------------------------------------------------
 1. ARM ONLY THE A-SET. A file deliberately forked (B) must not turn the gate red every day; a
    daily red for a known-and-accepted condition is how a channel gets ignored. But B requires a
    RECORDED REASON — "deliberately different" with no reason is indistinguishable from drift.
 2. FINGERPRINT ROWS >= |A|. The gate's own reference data is now asserted. This is the check that
    would have caught the truncation the moment it happened.
 3. AN EMPTY MANIFEST IS EXIT 1, NEVER A VACUOUS PASS. Zero rows is not "no drift"; it is "no
    evidence", and this gate's whole purpose is to refuse that substitution.

★ AND UNCLASSIFIED IS NOT A THIRD BENIGN STATE. A file present in both trees but absent from the
regime map makes the gate exit 1 with the file named. New duplication must be classified by a human
on the day it appears — that is the only moment anyone knows why it was duplicated.

Run:  python handoff_drift_gate_selfcheck.py            # assert
      python handoff_drift_gate_selfcheck.py --selftest # red/green battery, no repo state touched
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile

# ── the two trees. 0B should replace these with the constants already in check_upstream_drift.py ──
VENDORED = os.path.expanduser("~/dl_quant_live/live")
UPSTREAM = "/Users/haosiyu/Desktop/quant_research/multi_asset/engine/live"
MANIFEST = os.path.expanduser("~/dl_quant_live/ops/UPSTREAM_MANIFEST.sha256")
# The regime map: filename -> ("A", "") | ("B", "why this fork is deliberate")
# 0C leaves it EMPTY on purpose. Filling it is the human decision the ruling assigns to 0B, and a
# map pre-filled by the auditor would make that decision look already taken.
REGIME_MAP_PATH = os.path.expanduser("~/dl_quant_live/ops/UPSTREAM_REGIME.json")


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def both_trees(vendored=VENDORED, upstream=UPSTREAM):
    """Files that exist in BOTH trees — the set duplication actually spans today."""
    if not os.path.isdir(upstream) or not os.path.isdir(vendored):
        return None
    a = {f for f in os.listdir(vendored) if f.endswith((".py", ".sh"))}
    b = {f for f in os.listdir(upstream) if f.endswith((".py", ".sh"))}
    return sorted(a & b)


def load_regime(path=REGIME_MAP_PATH):
    if not os.path.exists(path):
        return None
    return json.load(open(path))


def check(manifest=MANIFEST, regime_path=REGIME_MAP_PATH,
          vendored=VENDORED, upstream=UPSTREAM, verbose=True):
    """Returns (exit_code, report). 0 = no drift over an ARMED, NON-EMPTY A-set."""
    rep = {"findings": [], "n_armed": 0, "n_exempt": 0}
    out = []

    both = both_trees(vendored, upstream)
    if both is None:
        rep["verdict"] = "VACUOUS_BY_DESIGN"
        out.append("upstream tree absent — research-repo copies retired; gate passes vacuously BY "
                   "DESIGN (this is the ONE legitimate empty case, and it is legitimate because "
                   "the thing being guarded no longer exists)")
        if verbose:
            print("\n".join(out))
        return 0, rep

    regime = load_regime(regime_path)
    if regime is None:
        rep["findings"].append(
            f"NO REGIME MAP at {regime_path}. Every duplicated file must be classified A (must "
            f"stay in sync) or B (deliberately forked, with a recorded reason) before this gate "
            f"can arm. {len(both)} files are currently duplicated and none is classified.")
        rep["verdict"] = "FAIL"
        if verbose:
            print("\n".join(rep["findings"]))
        return 1, rep

    unclassified = [f for f in both if f not in regime]
    if unclassified:
        rep["findings"].append(
            "UNCLASSIFIED duplication — these exist in both trees and the regime map does not say "
            "which regime they are in. Unclassified is not a third benign state; classify them on "
            f"the day they appear, while someone still knows why: {unclassified}")
    b_without_reason = [f for f, v in regime.items()
                        if v.get("regime") == "B" and not str(v.get("why", "")).strip()]
    if b_without_reason:
        rep["findings"].append(
            "B-CLASS WITHOUT A REASON — 'deliberately different' with no recorded why is "
            f"indistinguishable from drift, and exempts itself from the gate: {b_without_reason}")

    armed = sorted(f for f in both if regime.get(f, {}).get("regime") == "A")
    rep["n_armed"] = len(armed)
    rep["n_exempt"] = len(both) - len(armed)

    # ── SELF-CHECK 3: an empty armed set is not a pass ──────────────────────────────────────────
    if not armed:
        rep["findings"].append(
            "ARMED SET IS EMPTY. Zero rows is not 'no drift', it is 'no evidence' — the exact "
            "substitution this gate exists to refuse, and the state it silently occupied from "
            "2026-07-25T15:44Z after a fingerprint refresh deleted all 19 rows.")

    # ── SELF-CHECK 2: the gate's own reference data is asserted ─────────────────────────────────
    rows = {}
    if os.path.exists(manifest):
        for line in open(manifest):
            if line.split():
                h, name = line.split()[:2]
                rows[name] = h
    if len(rows) < len(armed):
        rep["findings"].append(
            f"FINGERPRINT FILE UNDER-COVERS THE ARMED SET: {len(rows)} row(s) for {len(armed)} "
            f"armed file(s) — missing {sorted(set(armed) - set(rows))}. A gate whose reference data "
            f"is shorter than the set it guards is partially disarmed, and 'regenerate the "
            f"fingerprints' is precisely the operation that empties it. Regenerate DELIBERATELY, "
            f"then re-run this check.")

    # ── the drift comparison itself, over the armed set only ────────────────────────────────────
    drift = []
    for name in armed:
        lp, up = os.path.join(vendored, name), os.path.join(upstream, name)
        if not os.path.exists(up):
            drift.append((name, "upstream file gone — retire it from the A-set deliberately"))
            continue
        if not os.path.exists(lp):
            drift.append((name, "vendored copy gone"))
            continue
        lh, uh = sha(lp), sha(up)
        if lh != uh:
            drift.append((name, "local != upstream"))
        if name in rows and uh != rows[name]:
            drift.append((name, "upstream moved since vendoring"))
    for name, why in sorted(set(drift)):
        rep["findings"].append(f"DRIFT {name}: {why}")

    rep["armed"] = armed
    rep["verdict"] = "PASS" if not rep["findings"] else "FAIL"
    if verbose:
        for f in rep["findings"]:
            print("  " + f)
        print(f"\nVERDICT: {rep['verdict']}  (armed {rep['n_armed']}, exempt {rep['n_exempt']}, "
              f"fingerprint rows {len(rows)})")
    return (0 if rep["verdict"] == "PASS" else 1), rep


# ── red/green battery — runs entirely in a temp dir, touches no repo state ───────────────────────
def selftest():
    cases, fails = [], []

    def scenario(name, expect, build, why_red):
        d = tempfile.mkdtemp(prefix="dg_")
        v, u = os.path.join(d, "vendored"), os.path.join(d, "upstream")
        os.makedirs(v); os.makedirs(u)
        man, reg = os.path.join(d, "MAN.sha256"), os.path.join(d, "REGIME.json")
        build(v, u, man, reg)
        rc, rep = check(man, reg, v, u, verbose=False)
        ok = rc == expect
        cases.append((name, rc, expect, ok, why_red))
        if not ok:
            fails.append((name, rc, expect, rep["findings"]))

    def _w(p, s):
        open(p, "w").write(s)

    def clean(v, u, man, reg):
        _w(os.path.join(v, "a.py"), "x=1\n"); _w(os.path.join(u, "a.py"), "x=1\n")
        _w(man, f"{sha(os.path.join(u,'a.py'))} a.py\n")
        _w(reg, json.dumps({"a.py": {"regime": "A"}}))

    scenario("G1 armed, in sync -> PASS", 0, clean,
             "goes red if the two copies diverge or the fingerprint moves")

    def drifted(v, u, man, reg):
        clean(v, u, man, reg); _w(os.path.join(u, "a.py"), "x=2\n")
    scenario("R1 armed file diverges -> FAIL", 1, drifted,
             "the gate's original job; red if it stops comparing")

    def empty_man(v, u, man, reg):
        clean(v, u, man, reg); _w(man, "")
    scenario("R2 ★ fingerprint file EMPTIED -> FAIL (the 07-25 event)", 1, empty_man,
             "would PASS in the shipped gate — 'no drift across 0 vendored modules', exit 0")

    def no_a(v, u, man, reg):
        clean(v, u, man, reg); _w(reg, json.dumps({"a.py": {"regime": "B", "why": "forked on purpose"}}))
    scenario("R3 every file exempted -> FAIL (empty armed set)", 1, no_a,
             "an all-B map is a disarmed gate wearing a green badge")

    def b_no_reason(v, u, man, reg):
        clean(v, u, man, reg); _w(reg, json.dumps({"a.py": {"regime": "B"}}))
    scenario("R4 B-class with no recorded reason -> FAIL", 1, b_no_reason,
             "'deliberately different' with no why is self-granted exemption")

    def unclassified(v, u, man, reg):
        clean(v, u, man, reg); _w(os.path.join(v, "new.py"), "y=1\n"); _w(os.path.join(u, "new.py"), "y=1\n")
    scenario("R5 newly duplicated file not in the map -> FAIL", 1, unclassified,
             "new duplication must be classified while someone still knows why")

    def no_map(v, u, man, reg):
        clean(v, u, man, reg); os.unlink(reg)
    scenario("R6 no regime map at all -> FAIL", 1, no_map,
             "an unarmed gate is not a clean gate")

    def retired(v, u, man, reg):
        clean(v, u, man, reg)
        import shutil; shutil.rmtree(u)
    scenario("G2 upstream tree retired -> PASS (the one legitimate empty)", 0, retired,
             "the guarded thing no longer exists; distinguish this from an empty manifest")

    print(f"drift-gate self-check battery — {len(cases)} cases\n")
    for name, rc, expect, ok, why_red in cases:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}   rc={rc} (expected {expect})")
        print(f"        red-when: {why_red}")
    print(f"\n{len(cases)-len(fails)} passed, {len(fails)} failed")
    for f in fails:
        print("  FAILED:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else check()[0])
