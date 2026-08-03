"""One-off inspection: does the S1 clean panel carry the SAME funding caliber as the as-trained one?

> **创建:** 2026-08-03 16:3x UTC | **Session:** B4-retrain | **状态:** final — 一次性核对
> **作废条件:** 新面板被 `engine/live/factor_version_registry.py` 正式登记 ⇒ 改用常规 `--caliber auto`

WHY A PROBE AND NOT JUST RUNNING THE GATE
-----------------------------------------
`assert_funding_dim.py` is the right instrument, but running it as-is has two side effects I am not
entitled to on this machine:

  1. it writes `exports/eda/assert_funding_dim_result.json` — an EXISTING file recording the
     production panel's verdict. Overwriting it would destroy a live record to answer a research
     question. Here `json.dump` is redirected, so the gate computes exactly as it always does and
     only its OUTPUT lands somewhere else.
  2. under `--caliber auto` it (correctly) refuses to judge an artifact that is not declared in
     `engine/live/factor_version_registry.py`, and `wide_dl_full_causal_v1.npz` is not declared —
     nor should it be until someone decides to deploy it. The gate's own header sanctions the
     alternative: "Or pass --caliber explicitly for a one-off inspection."

WHAT IT ESTABLISHES. S1 holds the funding caliber FIXED at as-trained (prereg §2). The clean panel's
funding channels are asserted bit-identical to the as-trained panel's elsewhere, so this is a
SECOND, independent statement of the same fact, in the units the gate speaks (the 4h-vs-8h cohort
rank gap). Two instruments disagreeing would mean one of them is measuring something other than what
its name says.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os.path as _p

HERE = _p.dirname(_p.abspath(__file__))


def load_gate():
    spec = importlib.util.spec_from_file_location("afd", _p.join(HERE, "assert_funding_dim.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", nargs="+", required=True)
    ap.add_argument("--caliber", default="as_trained")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    m = load_gate()
    captured = {}
    real_dump = m.json.dump

    def _capture(obj, fp, **kw):                      # never touches the production record
        captured[obj.get("panel")] = obj

    m.json.dump = _capture
    rcs = {}
    try:
        for p in a.panels:
            print("\n" + "=" * 78 + f"\n{p}\n" + "=" * 78, flush=True)
            rcs[p] = m.main(p, a.caliber)
            print(f"  -> exit {rcs[p]}", flush=True)
    finally:
        m.json.dump = real_dump

    json.dump(dict(caliber_asserted=a.caliber, exit_codes=rcs, results=captured),
              open(a.out, "w"), indent=1, default=str)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()
