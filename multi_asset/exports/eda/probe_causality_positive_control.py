"""POSITIVE CONTROL for `tests_panel_causality_train.py` — can the instrument see the defect at all?

> **创建:** 2026-08-03 16:4x UTC | **Session:** B4-retrain | **状态:** final — 仪器有效性对照
> **作废条件:** 毒化方案(cut / 幅度 / 被毒化的键)改变 ⇒ 必须重跑, 否则主测的绿失去含义

WHY THIS EXISTS
---------------
`tests_panel_causality_train.py` reports 32/32 channels causal on the clean panel. That reading has
TWO possible causes and they are not distinguishable from inside it:

    (i)  the one-line fix worked;
    (ii) the poison never reached ch31's construction in the first place, so ch31 would have come
         back "causal" even unfixed.

The suite's "poison actually reached the panel" check rules out the poison being inert GLOBALLY, but
not being inert FOR THE ONE CHANNEL THE WHOLE EXPERIMENT IS ABOUT. A blind test and a working system
both print green.

SO: run the SAME poison, the SAME cut, the SAME source, through the **UNPATCHED** builder — the one
with `np.convolve(..., "same")` still in it — and require the opposite result:

    ch31 MUST move, and its reach MUST be exactly the audited 11 rows (RESULT_channel_cutoff_audit
    SHA `eedab22a…` §2: out[t] <- input[t-12 … t+11]);
    the other 31 channels MUST still be clean.

Only after this goes red-where-it-should does the main suite's green mean "the leak is gone" rather
than "the test cannot see leaks".

Usage:
  python probe_causality_positive_control.py --source <wide_panel_full.npz> \
         --as-trained <wide_dl_full.npz> --scratch <dir> [--cut 30000]
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
from multi_asset.data import build_wide_dl as _ORIG          # noqa: E402  UNPATCHED on purpose

# the main suite is a sibling script, not a package module — load it by path so the poison recipe is
# literally THE SAME OBJECT the main suite used, not a second copy that could drift from it.
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "tt", _p.join(_p.dirname(_p.abspath(__file__)), "tests_panel_causality_train.py"))
TT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TT)

# Audited support of convolve('same', ones(24)) is out[t] <- input[t-12 … t+11] — ELEVEN future taps.
# ★ THAT MAKES THE FIRST CONTAMINATED ROW cut-10, NOT cut-11, AND THE COUNT 11 (rows cut-10 … cut).
#   out[t] sees the poison iff t+11 >= cut+1, i.e. t >= cut-10. My first version asserted
#   `cut - first == 11` and went red against a panel that was behaving exactly as audited. The taps
#   and the row-offset differ by one because the row AT the cut is itself contaminated and counts.
#   The invariant worth pinning is the COUNT (= number of future taps), not the offset.
LEAK_ROWS = 11           # rows <= cut that the centered window contaminates: cut-10 … cut

_n_pass, _fail = 0, []


def ok(cond, label, detail=""):
    global _n_pass
    print(("  OK    " if cond else "  FAIL  ") + label + (f"  — {detail}" if detail else ""),
          flush=True)
    if cond:
        _n_pass += 1
    else:
        _fail.append(label)
    return cond


class LoadOnlyNumpy:
    """numpy with `load` intercepted and NOTHING else — in particular convolve stays CENTERED."""

    def __init__(self, payload):
        self._payload = payload

    def __getattr__(self, name):
        return getattr(np, name)

    def load(self, *a, **k):
        return self._payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--as-trained", required=True, dest="as_trained")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--cut", type=int, default=30000)
    ap.add_argument("--reuse", action="store_true",
                    help="reuse an existing poisoned build instead of rebuilding (same cut only)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    CUT = a.cut

    outp = _p.join(a.scratch, "wide_dl_POISONED_unpatched_control.npz")
    if a.reuse and _p.exists(outp):
        print(f"[control] reusing existing poisoned build {outp} (--reuse)", flush=True)
    else:
        print(f"[control] poisoning the UNPATCHED builder -> {outp}  (cut {CUT})", flush=True)
        payload = TT.poison(a.source, CUT)             # identical poison to the main suite
        saved = _ORIG.np
        try:
            _ORIG.np = LoadOnlyNumpy(payload)
            try:
                _ORIG.build(panel=a.source, outpath=outp)
            except SystemExit as e:
                print(f"[control] post-write funding gate raised (expected, undeclared panel): {e}",
                      flush=True)
        finally:
            _ORIG.np = saved

    O = np.load(a.as_trained, allow_pickle=True)
    P = np.load(outp, allow_pickle=True)
    names = [str(x) for x in O["ch_names"]]
    J = names.index("betaadj_ret24")

    print("\n[C1] the leak IS visible to this poison when it is not fixed")
    c0, c1 = O["CH"][: CUT + 1, :, J], P["CH"][: CUT + 1, :, J]
    moved = not np.array_equal(c0, c1, equal_nan=True)
    first = TT.first_diff_row(c0, c1)
    ok(moved, "★★★ ch31 MOVES under poison in the unpatched builder — this is what the main suite "
              "would have caught had the fix not taken; its green is therefore meaningful",
       f"first moved row {first} = cut-{CUT - first}")
    dirty = np.where((c0 != c1).any(1))[0]
    expect = np.arange(CUT - LEAK_ROWS + 1, CUT + 1)
    ok(np.array_equal(dirty, expect),
       f"★★ ...and the contaminated window is EXACTLY the audited {LEAK_ROWS} rows "
       f"(cut-{LEAK_ROWS - 1} … cut), contiguous, with cut-{LEAK_ROWS} clean",
       f"measured rows {dirty.min() if len(dirty) else None}…{dirty.max() if len(dirty) else None}"
       f" count={len(dirty)}")

    print("\n[C2] the poison is not indiscriminate — the other 31 stay clean even unpatched")
    bad = [nm for j, nm in enumerate(names)
           if j != J and not np.array_equal(O["CH"][: CUT + 1, :, j], P["CH"][: CUT + 1, :, j],
                                            equal_nan=True)]
    ok(not bad, "31/31 non-ch31 channels unchanged at rows <= cut in the unpatched build too "
                "(so the main suite's 32/32 is a real change in ch31, not a change in the poison)",
       bad[:4])

    print("\n[C3] the control's baseline is the real shipped artifact, not a re-derivation")
    ok(not np.array_equal(O["CH"][CUT + 1:, :, J], P["CH"][CUT + 1:, :, J], equal_nan=True),
       "post-cut ch31 differs — the unpatched build reproduces the SHIPPED as-trained panel closely "
       "enough that its only disagreement with it is the poison itself")

    print("\n" + "=" * 78)
    total = _n_pass + len(_fail)
    print(f"PASS {_n_pass}/{total}" + ("" if not _fail else f"   FAILED: {_fail}"))
    if a.out:
        json.dump(dict(source=a.source, as_trained=a.as_trained, cut=CUT, ch31_index=J,
                       first_contaminated_row=int(first),
                       contaminated_rows_le_cut=[int(x) for x in dirty],
                       audited_leak_rows=LEAK_ROWS,
                       n_pass=_n_pass, n_total=total, failed=_fail, dirty_others=bad),
                  open(a.out, "w"), indent=1)
        print(f"record -> {a.out}")
    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    main()
