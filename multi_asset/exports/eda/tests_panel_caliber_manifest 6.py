"""Red/green battery for `assert_panel_caliber_manifest.py`.

> created 2026-07-27 | Session: 0C | 状态: permanent | 作废条件: 随守卫一同退役

EVERY CASE STATES WHAT WOULD MAKE IT RED. A suite whose cases only ever pass has not been shown to
be able to fail, and a guard that has never been observed failing is indistinguishable from a guard
that cannot fail — which is precisely the state the neighbouring drift gate has been in since
2026-07-25 (empty fingerprint file, "no drift across 0 vendored modules", exit 0, every day).

THE LOAD-BEARING CASE IS R1. It substitutes a REAL corrected rebuild of the training panel
(`exports/wide_dl_full_fundfix.npz`, produced by the 2026-07-25 fix) into the slot of the panel the
frozen heads were trained on. It must FAIL. That is the whole thesis of this guard: it asserts
CONSISTENCY WITH TRAINING, not correctness. A guard that welcomed the more-correct panel would wave
through exactly the drift it exists to catch.

★★ GATE COVERAGE — WHAT THESE REDS PROVE, AND WHAT THEY DO NOT
--------------------------------------------------------------
A battery that lists only what it checks invites the reader to assume it checks everything adjacent.
So, explicitly (team-lead ruling 2026-07-27, registered as a declared blind spot rather than left to
be discovered):

  PROVEN by R1 — the gate catches a panel whose `funding_ema` AND `xsr_fund` were rebuilt through the
    real corrected pipeline (`wide_dl_full_fundfix.npz` is a genuine `apply_funding_fix` output, not a
    synthetic perturbation), while the manifest expects `as_trained`.
  ★ PROVEN 2026-07-27 (OPEN ITEM C — CLOSED) by `xsr_fund_faithful_redtest.py`: the gate catches a
    caliber change reaching `xsr_fund` INDEPENDENTLY of `funding_ema`, and it names the channel that
    actually moved rather than both. Both channels are taken from REAL pipeline outputs — a mixed
    panel is built by splicing one channel from `wide_dl_live_fundfix.npz` into `wide_dl_live.npz`,
    never by scaling a stored column, because multiplying by a constant would test arithmetic rather
    than the derivation path. Measured, stride-4 across the full history (12187 anchors):

        xsr_fund corrected / funding_ema as-trained, declared as_trained
            -> funding_ema -0.3803 PASS | xsr_fund +0.1454 FAIL   VERDICT FAIL: ['xsr_fund']
        funding_ema corrected / xsr_fund as-trained, declared as_trained
            -> VERDICT FAIL: ['funding_ema']
        the same mixed panel declared corrected     -> VERDICT FAIL: ['funding_ema']

    So the "two channels DISAGREE" case is covered too: a mixed panel is wrong under BOTH
    declarations and belongs to neither caliber. Side result, measured not assumed: the two real
    panels differ in EXACTLY `['funding_ema', 'xsr_fund']`, which independently confirms the
    settlement-interval fix is confined to the funding pair.

  ⇒ The fixture is validated by a known-answer gate before it is trusted to test anything (the pure
    subsamples must still reproduce BOTH references), because this gate's bands are calibrated on
    history-spanning sampling and a tail window reads −0.0485 on a perfectly good as-trained panel.

Run:  python multi_asset/exports/eda/tests_panel_caliber_manifest.py
Exit 0 = all cases behaved as specified.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assert_funding_dim as AFD
import assert_panel_caliber_manifest as M

MA = M.MA
RESULTS = []


def case(name, expect_rc, why_red):
    """Decorator: registers a case with the condition that would make it RED."""
    def deco(fn):
        RESULTS.append((name, expect_rc, why_red, fn))
        return fn
    return deco


def _tmp_manifest(mutate):
    man = copy.deepcopy(M.load_manifest())
    assert man is not None, "no blessed manifest — run --bless on the machine that holds the panels"
    mutate(man)
    fd, p = tempfile.mkstemp(suffix=".json", prefix="pcm_")
    os.close(fd)
    json.dump(man, open(p, "w"), indent=1)
    return p


# ── GREEN ────────────────────────────────────────────────────────────────────────────────────────
@case("G1 real state passes",
      0, "would go red if any held panel's funding caliber left the blessed band, or if the "
         "frozen checkpoints changed")
def g1():
    rc, rep = M.assert_manifest(verbose=False)
    return rc, rep


@case("G2 forced re-measurement still passes (the hash shortcut is not hiding a failure)",
      0, "would go red if the bit-identity shortcut were masking a panel whose MEASURED caliber "
         "disagrees with its blessed one")
def g2():
    rc, rep = M.assert_manifest(verbose=False, force_measure=True)
    return rc, rep


# ── RED ──────────────────────────────────────────────────────────────────────────────────────────
@case("R1 ★ a REAL corrected rebuild of the training panel must FAIL",
      1, "would go green if the guard rewarded 'more correct' instead of asserting "
         "'consistent with what the frozen weights were fitted on'")
def r1():
    sub = MA + "/exports/wide_dl_full_fundfix.npz"
    if not os.path.exists(sub):
        return "SKIP", {"why": f"{sub} not on this machine"}
    rc, rep = M.assert_manifest(substitutes={"exports/wide_dl_full.npz": sub}, verbose=False)
    assert any("corrected" in f for f in rep["findings"]), \
        f"failed, but not for the corrected-caliber reason: {rep['findings']}"
    return rc, rep


@case("R2 a changed frozen generation must FAIL (stale blessing)",
      1, "would go green if the caliber expectation were free-floating instead of keyed to the "
         "model version — the accident the FORWARD NOTE warns about")
def r2():
    p = _tmp_manifest(lambda m: m["generation"].__setitem__("id", "deadbeefdeadbeef"))
    try:
        rc, rep = M.assert_manifest(p, verbose=False)
        assert any("GENERATION CHANGED" in f for f in rep["findings"]), rep["findings"]
        return rc, rep
    finally:
        os.unlink(p)


@case("R3 flipping the blessed expectation to `corrected` must FAIL on the real panels",
      1, "this is the DISCRIMINATION CONTROL for G1: if G1's green survived this flip, G1 would be "
         "green for a reason unrelated to the panels")
def r3():
    def flip(m):
        for v in m["panels"].values():
            v["caliber"] = "corrected"
            v.pop("file_sha256_16", None)          # force real measurement, not the hash shortcut
    p = _tmp_manifest(flip)
    try:
        rc, rep = M.assert_manifest(p, verbose=False)
        return rc, rep
    finally:
        os.unlink(p)


@case("R4 a reading in the FORBIDDEN MIDDLE must FAIL and say so",
      1, "would go green if a mid-band reading were absorbed by a single two-sided tolerance "
         "instead of being called out as an undeclared change")
def r4():
    mid = (AFD.REF_AS_TRAINED + AFD.REF_CORRECTED) / 2.0
    real = AFD.measure_gaps

    def fake(panel, stride=4):
        return ({c: {"mean_gap": round(mid, 4), "n": 999} for c in AFD.CHANNELS + ["Y4"]}, [])
    AFD.measure_gaps = fake
    try:
        p = _tmp_manifest(lambda m: [v.pop("file_sha256_16", None) for v in m["panels"].values()])
        try:
            rc, rep = M.assert_manifest(p, verbose=False)
            assert any("FORBIDDEN MIDDLE" in f for f in rep["findings"]), rep["findings"]
            return rc, rep
        finally:
            os.unlink(p)
    finally:
        AFD.measure_gaps = real


# ── UNKNOWN (the anti-vacuity cases) ─────────────────────────────────────────────────────────────
@case("U1 no manifest at all is UNKNOWN, not clean",
      2, "would be wrong at either 0 (never-blessed reads as healthy) or 1 (an unarmed guard "
         "is not a detected defect)")
def u1():
    p = tempfile.mktemp(suffix=".json")
    rc, rep = M.assert_manifest(p, verbose=False)
    return rc, rep


@case("U2 ★ generation matches but NO panel is present -> UNKNOWN, never PASS",
      2, "would go green on an empty denominator — the exact shape of the drift gate's "
         "'no drift across 0 vendored modules'")
def u2():
    def blank(m):
        m["panels"] = {"exports/does_not_exist.npz": {"caliber": "as_trained", "role": "none"}}
    p = _tmp_manifest(blank)
    try:
        rc, rep = M.assert_manifest(p, verbose=False)
        assert any("VACUOUS" in f for f in rep["findings"]), rep["findings"]
        return rc, rep
    finally:
        os.unlink(p)


@case("U3 half the generation unreadable -> UNKNOWN (a partial identity is not an identity)",
      2, "would be wrong at 0 (an unread checkpoint could have been swapped invisibly) and wrong at "
         "1 (an unreadable file is not a detected drift)")
def u3():
    saved = M.GENERATION_MEMBERS["s2"]
    M.GENERATION_MEMBERS["s2"] = ["/nonexistent/s2.pt"]
    try:
        rc, rep = M.assert_manifest(verbose=False)
        assert any("GENERATION UNIDENTIFIABLE" in f for f in rep["findings"]), rep["findings"]
        return rc, rep
    finally:
        M.GENERATION_MEMBERS["s2"] = saved


# ── pure-function boundaries ─────────────────────────────────────────────────────────────────────
@case("B1 classify_gap boundaries: both references, both edges, and the middle",
      0, "would go red if the bands overlapped or the middle were reachable from either side")
def b1():
    A, C, T = AFD.REF_AS_TRAINED, AFD.REF_CORRECTED, AFD.FAIL_ABS
    checks = [
        (A, "as_trained"), (C, "corrected"),
        (A + T - 1e-9, "as_trained"), (A - T + 1e-9, "as_trained"),
        (C + T - 1e-9, "corrected"), (C - T + 1e-9, "corrected"),
        (A + T + 1e-6, "MIDDLE"), (C - T - 1e-6, "MIDDLE"), ((A + C) / 2, "MIDDLE"),
    ]
    bad = [(g, want, AFD.classify_gap(g)) for g, want in checks if AFD.classify_gap(g) != want]
    assert not bad, f"classify_gap disagrees: {bad}"
    return 0, {"n_boundaries": len(checks)}


def run():
    print(f"panel-caliber manifest battery — {len(RESULTS)} cases\n", flush=True)
    fails, skips = [], []
    for name, expect, why_red, fn in RESULTS:
        try:
            rc, rep = fn()
        except AssertionError as e:
            fails.append((name, f"assertion inside case: {e}"))
            print(f"  FAIL  {name}\n        {e}", flush=True)
            continue
        if rc == "SKIP":
            skips.append((name, rep.get("why")))
            print(f"  SKIP  {name}  ({rep.get('why')})", flush=True)
            continue
        ok = rc == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}   rc={rc} (expected {expect})", flush=True)
        if not ok:
            fails.append((name, f"rc={rc} expected {expect}; findings={rep.get('findings')}"))
        print(f"        red-when: {why_red}", flush=True)
    print(f"\n{len(RESULTS) - len(fails) - len(skips)} passed, {len(fails)} failed, "
          f"{len(skips)} skipped", flush=True)
    for n, w in fails:
        print(f"  FAILED: {n} — {w}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
