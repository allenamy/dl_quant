"""0C — RED/GREEN battery for the per-artifact caliber ROUTING (the stamp), 2026-07-29 ruling.

> created 2026-07-29 | Session: 0C | 状态: permanent | 作废条件: 随 assert_funding_dim 一同退役

WHAT THIS PROVES, AND WHY THREE CASES AND NOT ONE
--------------------------------------------------
Team-lead ruling (2026-07-29), verbatim requirement:

    "把日跑面板换成修正口径 ⇒ 必须红; 把全史面板换成 as-trained 口径 ⇒ 必须红;
     现状 ⇒ 必须绿。三条缺一不可 —— 只证第三条等于没证。"

A guard that has only ever been observed green is indistinguishable from a guard that cannot go red.
And a guard that goes red in ONE direction is a guard for one caliber: it would catch a live panel
that got accidentally normalised, and wave through a factor-leg panel that never got normalised at
all. Both directions must be demonstrated, each against the caliber it is supposed to protect.

★ ONE CORRECTION TO THE RULING'S SECOND CASE, MEASURED, NOT ARGUED
-------------------------------------------------------------------
The ruling states the pair as "日跑面板=as-trained / 全史面板=修正". The second half is not the
current state and must not be made so:

    exports/wide_dl_full.npz   is AS-TRAINED  (measured -0.3837, 0C 2026-07-27) and that is CORRECT:
                               it is the panel the frozen king/s2 heads were fitted on, built
                               2026-07-11, deliberately never rebuilt after the 07-25 fix.

Rebuilding it into the corrected caliber is the MIRROR of the defect the ruling is fixing — it would
feed frozen weights a distribution they were never fitted on, and (before 07-27) the gate would have
gone green for it. The corrected caliber belongs to the FACTOR LEG: `*_fundfix.npz`.

⇒ So the second direction is demonstrated where the corrected caliber actually lives:
     an artifact that MUST be corrected, whose contents are as-trained  ->  MUST BE RED.
  Same assertion, same symmetry, pointed at the artifact that really holds that expectation. The
  ruling's own case — the training panel turned corrected — is also proven, as case R_FULL, because
  it is the accident the FORWARD NOTE warns about.

FAITHFUL: NO SYNTHETIC CHANNELS
-------------------------------
Every fixture's channels are bytes from REAL pipeline outputs — `wide_dl_live.npz` (as-trained) and
`wide_dl_live_fundfix.npz` (the corrected rebuild) — row-subsampled with a uniform stride across the
FULL history. Nothing is scaled or perturbed: multiplying a stored column by a constant would test
arithmetic rather than the derivation path. What VARIES between fixtures is the stamp, i.e. what the
artifact CLAIMS to be — which is precisely the routing under test.

  ⇒ Known-answer gate first (KA1/KA2): the subsample must still reproduce BOTH references before it
    is trusted to test anything. The bands are calibrated on history-spanning sampling; a tail
    window reads -0.0485 on a perfectly good as-trained panel, so this is not decoration.

Run (server, where the real panels live):
    python multi_asset/exports/eda/tests_caliber_stamp_routing.py
Exit 0 = every case behaved as specified.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import panel_caliber_stamp as PCS                                          # noqa: E402

MA = os.path.dirname(os.path.dirname(HERE))                                # .../multi_asset
GATE = os.path.join(HERE, "assert_funding_dim.py")
AS_TRAINED = os.environ.get("PANEL_AS_TRAINED", MA + "/exports/live/wide_dl_live.npz")
CORRECTED = os.environ.get("PANEL_CORRECTED", MA + "/exports/live/wide_dl_live_fundfix.npz")
OUT = os.environ.get("STAMP_FIXTURES", "/tmp/caliber_stamp_fixtures")
STRIDE = 4

WHY = "red-test fixture: channels are real pipeline bytes; the STAMP is the variable under test"


# ── fixtures ─────────────────────────────────────────────────────────────────────────────────────
def build_fixtures(out=OUT, stride=STRIDE):
    for p in (AS_TRAINED, CORRECTED):
        if not os.path.exists(p):
            raise SystemExit(f"missing real panel {p} — this battery is faithful only against "
                             f"actual pipeline outputs; do not substitute a synthetic one")
    os.makedirs(out, exist_ok=True)
    a = np.load(AS_TRAINED, allow_pickle=True)
    b = np.load(CORRECTED, allow_pickle=True)
    sl = slice(None, None, stride)
    common = dict(symbols=a["symbols"], ch_names=a["ch_names"])
    arrays_at = dict(ts=a["ts"][sl], MEMBER110=a["MEMBER110"][sl], Y4=a["Y4"][sl],
                     CH=a["CH"][sl], **common)
    arrays_co = dict(ts=b["ts"][sl], MEMBER110=b["MEMBER110"][sl], Y4=b["Y4"][sl],
                     CH=b["CH"][sl], **common)

    def save(name, arrays, stamp_caliber):
        p = os.path.join(out, name)
        kw = dict(arrays)
        if stamp_caliber is not None:
            kw.update(PCS.make(stamp_caliber, "tests_caliber_stamp_routing.py", WHY))
        with open(p, "wb") as f:
            np.savez(f, **kw)
        return p

    paths = {
        # contents      stamp            purpose
        "ka_astrained": save("ka_astrained.npz", arrays_at, "as_trained"),
        "ka_corrected": save("ka_corrected.npz", arrays_co, "corrected"),
        "d1_corrected_content_astrained_stamp":
            save("d1_corrected_content_astrained_stamp.npz", arrays_co, "as_trained"),
        "d2_astrained_content_corrected_stamp":
            save("d2_astrained_content_corrected_stamp.npz", arrays_at, "corrected"),
        "unstamped": save("unstamped.npz", arrays_at, None),
    }
    # rename-proofness: a byte-identical copy of the green fixture under a name no rule knows
    paths["renamed"] = os.path.join(out, "zz_some_other_name_nobody_declared.npz")
    shutil.copyfile(paths["ka_astrained"], paths["renamed"])
    # a stamp that is present but broken — must be CANNOT JUDGE, and must not read as absent
    broken = os.path.join(out, "broken_stamp.npz")
    kw = dict(arrays_at); kw[PCS.STAMP_KEY] = np.array(json.dumps({"schema": "not/mine"}))
    with open(broken, "wb") as f:
        np.savez(f, **kw)
    paths["broken"] = broken
    print(f"fixtures -> {out}  (stride {stride}, {arrays_at['ts'].shape[0]} anchors each)\n",
          flush=True)
    return paths


def gate(panel, caliber=None):
    cmd = [sys.executable, GATE, "--panel", panel]
    if caliber:
        cmd += ["--caliber", caliber]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def verdict_line(out):
    return next((l for l in out.splitlines() if l.startswith("VERDICT")), "")


def basis_line(out):
    return next((l for l in out.splitlines() if l.startswith("[caliber]")), "")


# ── cases ────────────────────────────────────────────────────────────────────────────────────────
CASES = [
    ("KA1 known answer: real as-trained bytes, stamped as_trained", "ka_astrained", 0,
     "the subsample must still reproduce the as-trained reference, or nothing below is evidence"),
    ("KA2 known answer: real corrected bytes, stamped corrected", "ka_corrected", 0,
     "and the corrected reference too — otherwise the stride window, not the routing, is what the "
     "reds below would be measuring"),

    ("★ D1 the DAILY panel accidentally CORRECTED (contents corrected, stamp as_trained)",
     "d1_corrected_content_astrained_stamp", 1,
     "RULING CASE 1. Green here = an unintended normalisation of the live splice passes, and the "
     "frozen heads silently get a distribution they were never fitted on"),

    ("★ D2 an artifact that MUST be corrected but is NOT (contents as-trained, stamp corrected)",
     "d2_astrained_content_corrected_stamp", 1,
     "RULING CASE 2 (pointed at the caliber that actually holds the `corrected` expectation — the "
     "factor leg). Green here = 'the one that should have been fixed was not' passes unnoticed"),

    ("★ D3 status quo: real live-panel bytes carrying the stamp its builder writes", "ka_astrained",
     0,
     "RULING CASE 3. Red here would stop the shadow for a panel that is exactly what it should be "
     "— the 2026-07-26 failure itself. (Same bytes as the live panel; the stamp is what the "
     "deployed builder writes, so this is the post-deploy daily state.)"),

    ("S1 rename-proofness: the green fixture under a name no rule knows", "renamed", 0,
     "the whole point of the ruling. A path-keyed router gives CANNOT JUDGE (or worse, the "
     "expectation belonging to whatever used to live at that path); a stamp travels with the bytes"),

    ("S2 no stamp and no declared sha256 -> CANNOT JUDGE, never PASS", "unstamped", 2,
     "wrong at 0 (an undeclared artifact reading as healthy is how a default becomes a filename "
     "rule) and wrong at 1 (nothing was measured against anything — that is not a violation)"),

    ("S3 a BROKEN stamp is CANNOT JUDGE, and is not reported as absent", "broken", 2,
     "'somebody declared something and it is unreadable' is a defect; flattening it into 'nobody "
     "declared anything' loses the only fact that names one"),
]


def run():
    paths = build_fixtures()
    fails = []
    for name, key, want_rc, why_red in CASES:
        panel = AS_TRAINED if key is None else paths[key]
        rc, out = gate(panel)
        ok = rc == want_rc
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}\n        rc={rc} (want {want_rc})")
        print(f"        {basis_line(out)}")
        print(f"        {verdict_line(out) or out.strip().splitlines()[0][:160]}")
        print(f"        red-when: {why_red}\n", flush=True)
        if not ok:
            fails.append((name, rc, want_rc))

    # ── D3-live: the panel ACTUALLY ON DISK right now, with BOTH branches specified ─────────────
    # ★ NOT AN "EXPECTED RED" ROW. A row that says "this is expected to fail" is a standing
    # instruction to ignore a colour, and the factor registry deleted exactly such a row on 07-27
    # for that reason. This case asserts a STATE-DEPENDENT fact with both branches written down:
    #   the panel carries a stamp   -> the gate must judge it, and it must PASS  (rc 0)
    #   the panel carries no stamp  -> the builder change is not deployed on this machine yet, and
    #                                  the only honest verdict is CANNOT JUDGE  (rc 2)
    # The second branch is a DEPLOYMENT fact about the artifact, not a property of the gate, and it
    # stops being reachable the moment the first post-deploy build runs. If it is still reachable a
    # week from now, that itself is the finding.
    print("  --- the live panel as it exists on disk on THIS machine ---", flush=True)
    stamped = PCS.has_stamp(AS_TRAINED)
    want_rc = 0 if stamped else 2
    rc, out = gate(AS_TRAINED)
    ok = rc == want_rc
    print(f"  {'ok  ' if ok else 'FAIL'}  ★ D3-live {os.path.basename(AS_TRAINED)} "
          f"({'stamped' if stamped else 'UNSTAMPED — builder change not deployed here'})\n"
          f"        rc={rc} (want {want_rc})\n        {basis_line(out) or verdict_line(out)}")
    print("        red-when: rc=0 on an UNSTAMPED panel would mean the router invented an "
          "expectation for an artifact nobody declared — the defect this ruling removes; rc!=0 on "
          "a stamped one would be the 07-26 stall again\n", flush=True)
    if not ok:
        fails.append(("D3-live", rc, want_rc))

    # ── R_FULL: the ruling's own second case, on the training panel, if both artifacts are here ──
    full = MA + "/exports/wide_dl_full.npz"
    fullfix = MA + "/exports/wide_dl_full_fundfix.npz"
    print("  --- the FROZEN TRAINING panel (declared by content sha256, not by name) ---",
          flush=True)
    for label, p, want_rc, why in [
        ("R_FULL-a wide_dl_full.npz as it is (as-trained, correct for this generation)",
         full, 0, "red here = the panel the frozen heads were fitted on is being called wrong"),
        ("★ R_FULL-b wide_dl_full_fundfix.npz — the REAL corrected rebuild of that same panel",
         fullfix, 0,
         "it is DECLARED corrected by its own sha256, so it passes AS ITSELF; the accident the "
         "ruling names is this artifact taking the TRAINING panel's ROLE, which is case R_ROLE"),
    ]:
        if not os.path.exists(p):
            print(f"  SKIP  {label} ({p} not on this machine)\n", flush=True)
            continue
        rc, out = gate(p)
        ok = rc == want_rc
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}\n        rc={rc} (want {want_rc})")
        print(f"        {basis_line(out)}\n        {verdict_line(out)}\n        red-when: {why}\n",
              flush=True)
        if not ok:
            fails.append((label, rc, want_rc))

    # R_ROLE: the corrected rebuild standing in the training panel's ROLE. The role-level assertion
    # lives in assert_panel_caliber_manifest (R1 there); here we prove the same thing at the level
    # this gate owns — the artifact's own declaration is overridden by the role it is being used in.
    if os.path.exists(fullfix):
        rc, out = gate(fullfix, caliber="as_trained")
        ok = rc == 1
        print(f"  {'ok  ' if ok else 'FAIL'}  ★ R_ROLE corrected rebuild asked to be the "
              f"TRAINING caliber\n        rc={rc} (want 1)\n        {verdict_line(out)}")
        print("        red-when: green here would mean a 'more correct' panel is welcome in a "
              "frozen model's input slot — the exact drift this chain exists to catch\n", flush=True)
        if not ok:
            fails.append(("R_ROLE", rc, 1))

    print(f"{'ALL CASES BEHAVED AS SPECIFIED' if not fails else 'FAILURES: ' + str(fails)}",
          flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
