"""S1 vs S1F 2x2 cross-evaluation — separate "the model improved" from "the target moved".

> **创建:** 2026-08-03 23:1x UTC | **Session:** B4-retrain | **状态:** final
> **作废条件:** 任一 run 重训 ⇒ 重跑

S1F changed the residualisation baseline (funding as-trained -> corrected), so `YR4` is NOT the same
array in the two panels. The harness's `resid_rank_ic` is measured against whichever `YR4` its own
panel carries, which means:

    "S1 resid 0.0449 -> S1F resid 0.0xxx" IS NOT A COMPARISON. Two scores against two different
    targets. A target that is merely easier to hit raises the score without the model improving.

Measured size of the target move: median |ΔYR4| = 3.85e-05 against sd(YR4) = 1.289e-02, i.e. 0.30%
of a standard deviation — 1300x the float-rounding case, so a real change, not noise.

THE FIX — evaluate every model against BOTH targets. No retraining: both runs saved `head_scores`
over their `te_rows`, and both `YR4` arrays are on disk.

    same TARGET, different MODEL  -> what the corrected caliber bought  ("修正口径值多少")
    same MODEL,  different TARGET -> how much the target itself moved
    raw_rank_ic vs Y4             -> independent third line; Y4 is BIT-IDENTICAL across panels,
                                     so this one needs no disentangling at all

Scoring uses the harness's own `_ensemble_ic` / `_perhead_ic` so the caliber matches the leaderboard
exactly rather than being re-implemented here.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
import multi_asset.train.train_wide_harness as TH  # noqa: E402


def fold_scores(run_dir):
    out = []
    i = 0
    while _p.exists(_p.join(run_dir, f"fold_{i}_head_scores.npz")):
        z = np.load(_p.join(run_dir, f"fold_{i}_head_scores.npz"))
        out.append((z["scores"], z["te_rows"]))
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-astrained", required=True, help="causal_v1 (YR from as-trained funding)")
    ap.add_argument("--panel-corrected", required=True, help="corrfund_v1 (YR from corrected funding)")
    ap.add_argument("--runs", nargs="+", required=True, help="label=dir ...")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    A = np.load(a.panel_astrained, allow_pickle=True)
    B = np.load(a.panel_corrected, allow_pickle=True)
    member, CL = A["MEMBER110"], A["CL4"]
    assert np.array_equal(member, B["MEMBER110"]) and np.array_equal(CL, B["CL4"]), \
        "member/CL must match across panels or the scoring grid differs"
    assert np.array_equal(A["Y4"], B["Y4"], equal_nan=True), \
        "Y4 must be bit-identical — it is the only target that makes raw IC comparable"
    TARGETS = {"YR_as_trained": A["YR4"], "YR_corrected": B["YR4"]}
    RAW = A["Y4"]

    rec = {}
    print(f"{'run':34s} {'target':16s} {'mean ens':>10} {'per-fold ensemble resid IC'}")
    for spec in a.runs:
        label, d = spec.split("=", 1)
        folds = fold_scores(d)
        if not folds:
            print(f"{label:34s} (no head_scores)")
            continue
        rec[label] = {}
        for tname, Y in TARGETS.items():
            per = [TH._ensemble_ic(sc, Y, te, member, CL) for sc, te in folds]
            rec[label][tname] = [round(float(x), 5) for x in per]
            print(f"{label:34s} {tname:16s} {np.mean(per):>+10.5f} "
                  f"{[round(float(x), 4) for x in per]}")
        per_raw = [TH._ensemble_ic(sc, RAW, te, member, CL) for sc, te in folds]
        rec[label]["RAW_Y4"] = [round(float(x), 5) for x in per_raw]
        print(f"{label:34s} {'RAW Y4':16s} {np.mean(per_raw):>+10.5f} "
              f"{[round(float(x), 4) for x in per_raw]}")

    print("\n" + "=" * 88)
    print("SAME TARGET, DIFFERENT MODEL  — what the corrected caliber bought")
    for tname in list(TARGETS) + ["RAW_Y4"]:
        print(f"  [{tname}]")
        for arch in ("plain", "xattn"):
            s1 = rec.get(f"S1_{arch}", {}).get(tname)
            s1f = rec.get(f"S1F_{arch}", {}).get(tname)
            if s1 and s1f:
                d = np.array(s1f) - np.array(s1)
                se = d.std(ddof=1) / np.sqrt(len(d))
                print(f"    {arch:6s} S1 {np.mean(s1):+.5f} -> S1F {np.mean(s1f):+.5f}  "
                      f"Δ {d.mean():+.5f}  paired t {d.mean()/se if se > 0 else float('nan'):+.2f}  "
                      f"folds improved {int((d > 0).sum())}/{len(d)}")
    print("\nSAME MODEL, DIFFERENT TARGET — how much the target itself moved")
    for label in rec:
        x, y = rec[label]["YR_as_trained"], rec[label]["YR_corrected"]
        d = np.array(y) - np.array(x)
        print(f"  {label:34s} as_trained {np.mean(x):+.5f} -> corrected {np.mean(y):+.5f}  "
              f"Δ {d.mean():+.5f}")
    print("\n★ Read the columns, not the diagonal: the diagonal (each model on its own target) is "
          "what the harness prints, and it mixes both effects.")

    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()
