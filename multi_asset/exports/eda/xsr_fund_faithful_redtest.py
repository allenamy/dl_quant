"""OPEN ITEM C — the faithful `xsr_fund` red test for the funding-caliber gate.

> created 2026-07-27 | Session: 0C | 状态: final (item closed) | 作废条件: 两份真实面板之一不再存在

WHY THIS EXISTS
---------------
`assert_funding_dim` checks two channels: `funding_ema` (the raw factor) and `xsr_fund` (its
cross-sectional percentile rank). The gate's original red test substituted a whole corrected panel,
which moves BOTH channels at once — so the `xsr_fund` limb was **argued** ("a rank transform
preserves a group shift, and both derive from the same source") and never **demonstrated**. I
registered that as a declared blind spot rather than let it read as covered. This closes it.

★ FAITHFUL MEANS: NO SYNTHETIC SCALING.
Both channels are taken from REAL pipeline outputs — `wide_dl_live.npz` (as-trained) and
`wide_dl_live_fundfix.npz` (the corrected rebuild, `rate*(8/interval_h)` applied per row BEFORE the
EMA, with `xsr_fund` re-derived downstream). A mixed panel is built by taking ONE channel from one
real panel and the rest from the other. Multiplying a stored channel by a constant would have
tested my arithmetic, not the derivation path — and the two are exactly what this item was about.

MEASURED (2026-07-27, stride-4 subsample spanning the FULL history, 12187 anchors)
---------------------------------------------------------------------------------
First, the two real panels differ in **exactly two channels** — measured, not assumed:

    channels differing between as-trained and corrected: ['funding_ema', 'xsr_fund']

which independently corroborates that the settlement-interval fix is confined to the funding pair.

  KNOWN-ANSWER GATE (validate the fixture before trusting it to test anything):
    pure_astrained   declared as_trained  -> funding_ema -0.3803 / xsr_fund -0.3803   PASS
    pure_corrected   declared corrected   -> funding_ema +0.1445 / xsr_fund +0.1454   PASS

  THE CASE THAT WAS NEVER DEMONSTRATED — one channel moved, the other left alone:
    xsr_fund corrected, funding_ema as-trained, declared as_trained
        -> funding_ema -0.3803 as_trained PASS | xsr_fund +0.1454 corrected FAIL
        -> VERDICT FAIL: ['xsr_fund']                                    exit 1
    funding_ema corrected, xsr_fund as-trained, declared as_trained
        -> funding_ema +0.1445 corrected FAIL | xsr_fund -0.3803 as_trained PASS
        -> VERDICT FAIL: ['funding_ema']                                 exit 1
    the same mixed panel declared corrected
        -> VERDICT FAIL: ['funding_ema']                                 exit 1

⇒ The gate detects a caliber change reaching `xsr_fund` INDEPENDENTLY of `funding_ema`, and it
  attributes the failure to the channel that actually moved rather than to both. The limb is now
  demonstrated. **Argued does not count; demonstrated does.**

★ NOTE ON THE SUBSAMPLE. `assert_funding_dim`'s header warns that its bands are calibrated on
history-spanning sampling — a TAIL window reads −0.0485 on a perfectly good as-trained panel. A
uniform stride across the full history is a different operation and preserves the 4h/8h cohort mix,
which is why the known-answer gate above is not decoration: it is the evidence that this particular
subsample still reproduces both references before any conclusion is drawn from it.

Usage (server, where both real panels live):
    python xsr_fund_faithful_redtest.py            # rebuild fixtures, run all five cases, assert
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(MA, "exports", "live")
GATE = os.path.join(MA, "exports", "eda", "assert_funding_dim.py")
AS_TRAINED = os.path.join(LIVE, "wide_dl_live.npz")
CORRECTED = os.path.join(LIVE, "wide_dl_live_fundfix.npz")
OUT = "/tmp/xsrfix"
STRIDE = 4


def build(out=OUT, stride=STRIDE):
    for p in (AS_TRAINED, CORRECTED):
        if not os.path.exists(p):
            raise SystemExit(f"missing real panel {p} — this test is faithful only against the "
                             f"actual pipeline outputs; do not substitute a synthetic one")
    os.makedirs(out, exist_ok=True)
    a = np.load(AS_TRAINED, allow_pickle=True)
    b = np.load(CORRECTED, allow_pickle=True)
    ch = [str(c) for c in a["ch_names"]]
    i_f, i_x = ch.index("funding_ema"), ch.index("xsr_fund")
    sl = slice(None, None, stride)
    CHa, CHb = a["CH"][sl], b["CH"][sl]
    base = dict(ts=a["ts"][sl], symbols=a["symbols"], ch_names=a["ch_names"],
                MEMBER110=a["MEMBER110"][sl], Y4=a["Y4"][sl])
    diff = [ch[k] for k in range(CHa.shape[2])
            if not np.allclose(np.nan_to_num(CHa[:, :, k]), np.nan_to_num(CHb[:, :, k]),
                               equal_nan=True, atol=0, rtol=0)]
    print(f"channels differing between the two real panels: {diff}")
    if sorted(diff) != ["funding_ema", "xsr_fund"]:
        print("  ★ the corrected rebuild moved channels beyond the funding pair — the mixed "
              "fixtures below would then differ in more than the one channel under test")

    def save(name, CH):
        np.savez(os.path.join(out, name), CH=CH.astype(np.float32), **base)

    save("pure_astrained.npz", CHa)
    save("pure_corrected.npz", CHb)
    m1 = CHa.copy(); m1[:, :, i_x] = CHb[:, :, i_x]
    save("mixed_xsr_corrected.npz", m1)
    m2 = CHa.copy(); m2[:, :, i_f] = CHb[:, :, i_f]
    save("mixed_fund_corrected.npz", m2)
    print(f"fixtures written to {out} (stride {stride}, {base['ts'].shape[0]} anchors)")
    return diff


def gate(panel, caliber):
    r = subprocess.run([sys.executable, GATE, "--panel", os.path.join(OUT, panel),
                        "--caliber", caliber], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    build()
    cases = [
        # panel, declared, want_rc, want_failed_channels, why_this_case_exists
        ("pure_astrained.npz", "as_trained", 0, [],
         "KNOWN ANSWER — the fixture must reproduce the as-trained reference before it can test"),
        ("pure_corrected.npz", "corrected", 0, [],
         "KNOWN ANSWER — and the corrected reference too, or the subsample is not representative"),
        ("mixed_xsr_corrected.npz", "as_trained", 1, ["xsr_fund"],
         "★ THE ITEM: xsr_fund moved ALONE. Green here would mean the gate only ever saw "
         "funding_ema and inferred the rest."),
        ("mixed_fund_corrected.npz", "as_trained", 1, ["funding_ema"],
         "the mirror — a rule that only checks one channel checks nothing on the other"),
        ("mixed_xsr_corrected.npz", "corrected", 1, ["funding_ema"],
         "a mixed panel is wrong under BOTH declarations; it belongs to neither caliber"),
    ]
    fails = []
    for panel, caliber, want_rc, want_ch, why in cases:
        rc, out = gate(panel, caliber)
        verdict = next((l for l in out.splitlines() if l.startswith("VERDICT")), "")
        got_ch = [c for c in ("funding_ema", "xsr_fund") if c in verdict]
        ok = rc == want_rc and got_ch == want_ch
        print(f"\n  {'ok  ' if ok else 'FAIL'}  {panel} declared {caliber}")
        print(f"        rc={rc} (want {want_rc})  failed-channels={got_ch} (want {want_ch})")
        print(f"        {verdict}")
        print(f"        why: {why}")
        if not ok:
            fails.append(panel + "/" + caliber)
    print(f"\n{len(cases) - len(fails)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
