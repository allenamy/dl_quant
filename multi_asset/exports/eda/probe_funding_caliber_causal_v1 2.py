"""One-off inspection: does the S1 clean panel carry the SAME funding caliber as the as-trained one?

> **创建:** 2026-08-03 16:3x UTC | **Session:** B4-retrain | **状态:** final — 一次性核对
> **作废条件:** 新面板被 `engine/live/factor_version_registry.py` 正式登记 ⇒ 改用常规 `--caliber auto`

WHY A PROBE AND NOT JUST RUNNING THE GATE
-----------------------------------------
`assert_funding_dim.py` is the right instrument, but running it as-is has two side effects I am not
entitled to on this machine:

  1. it writes `exports/eda/assert_funding_dim_result.json` — an EXISTING file recording the
     production panel's verdict. Overwriting it would destroy a live record to answer a research
     question. Here the gate's `EDA` output DIRECTORY is redirected, so it computes exactly as it
     always does and only its output lands somewhere else.

★★ HOW THIS WENT WRONG THE FIRST TIME, KEPT HERE BECAUSE THE FIX IS NOT THE OBVIOUS ONE
   (B4-retrain, 2026-08-03 16:04Z — I destroyed the file this paragraph is about).
   v1 patched `json.dump` to a capture function and believed that was sufficient. The gate's call is

       json.dump(dict(...), open(EDA + "assert_funding_dim_result.json", "w"), indent=1)

   and **Python evaluates the arguments before it calls anything**. `open(..., "w")` TRUNCATES on
   open. So the file was emptied to 0 bytes by the argument, while my replacement writer — which
   never touched a disk — reported success. Patching the WRITER cannot protect a file that the
   ARGUMENT already destroyed.
   ⇒ The defensible interception point is the one that decides WHERE, not the one that decides
     WHETHER: redirect `EDA`, so the truncating `open` happens on a path I own.
   ⇒ General form: when neutralising a side effect, find the first expression that performs it, not
     the function that appears to. `dump` is the verb in that line; `open` is the one that writes.
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
import os
import os.path as _p

HERE = _p.dirname(_p.abspath(__file__))


def _stat(path):
    """(size, mtime_ns) or None — the pair that would change if anything wrote to the file.

    ★ Recorded BEFORE and AFTER and compared. The v1 defect was invisible precisely because nothing
      checked: the probe reported success while the file it was protecting sat at 0 bytes. An
      interception that is not verified against the thing it protects is a hope, not a guard.
    """
    try:
        s = os.stat(path)
        return [s.st_size, s.st_mtime_ns]
    except FileNotFoundError:
        return None


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
    prod_record = m.EDA + "assert_funding_dim_result.json"
    before = _stat(prod_record)

    redirect_dir = _p.join(_p.dirname(_p.abspath(a.out)), "gate_output")
    os.makedirs(redirect_dir, exist_ok=True)
    real_eda = m.EDA
    m.EDA = redirect_dir + os.sep                     # the TRUNCATING open() now lands here
    rcs = {}
    try:
        for p in a.panels:
            print("\n" + "=" * 78 + f"\n{p}\n" + "=" * 78, flush=True)
            rcs[p] = m.main(p, a.caliber)
            print(f"  -> exit {rcs[p]}", flush=True)
            side = _p.join(redirect_dir, "assert_funding_dim_result.json")
            if _p.exists(side):                       # one per panel, else they overwrite each other
                os.replace(side, _p.join(
                    redirect_dir, _p.basename(p).replace(".npz", "") + "_gate.json"))
    finally:
        m.EDA = real_eda

    after = _stat(prod_record)
    untouched = (before == after)
    print(f"\n[guard] production record {prod_record}\n        before = {before}\n"
          f"        after  = {after}\n        UNTOUCHED: {untouched}", flush=True)

    json.dump(dict(caliber_asserted=a.caliber, exit_codes=rcs, redirect_dir=redirect_dir,
                   production_record_untouched=untouched,
                   production_record_before=before, production_record_after=after),
              open(a.out, "w"), indent=1, default=str)
    print(f"\nrecord -> {a.out}")
    if not untouched:
        raise SystemExit(
            "[probe] THIS RUN CHANGED THE PRODUCTION GATE RECORD — the exact failure this file's "
            "header documents, recurring. Do not re-run; report the change.")


if __name__ == "__main__":
    main()
