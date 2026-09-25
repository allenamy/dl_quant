#!/usr/bin/env python3
"""dlarch_identity_compare.py -- bitwise comparison of two F10 runs, fold by fold.

WHY: two separate claims need the same operation, and the previous G1 comparison was done inline and
never archived (a discipline gap I am closing here -- a judgement device must outlive its verdict):
  G1  -- my trainer reproduces the reference recipe `news2_train_f10.py` bitwise (unmasked control)
  G1b -- the E-0925-A save-path fix changed nothing numerically: a re-trained fold reproduces the
         artifact the pre-fix trainer wrote, bitwise

WHAT IS COMPARED: every array in scores.npz (P, rows, E_ts, symbols) and every tensor in model.pt,
by shape, dtype and raw bytes. `tobytes()` compares NaN bit patterns exactly, which is what identity
means for a prediction matrix that is NaN wherever a symbol is absent.

POSITIVE CONTROL (runs first): the comparison function is applied to A against a copy of A with ONE
float32 perturbed, and must report a difference. Without it, "identical" could just mean the
comparator never looks. A run whose control does not fire returns non-zero and prints no green.

Usage:
  dlarch_identity_compare.py --a <dirA> --b <dirB> --folds 2023,202609 --label "..." \
      --out <receipt.json> --env-whitelist PATH,HOME,LC_CTYPE
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys

import numpy as np

import dlarch_safe_io as sio


def bsha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def cmp_arrays(name, x, y):
    """Returns a list of difference descriptions (empty == bitwise identical)."""
    d = []
    if x.shape != y.shape:
        d.append(f"{name}: shape {x.shape} vs {y.shape}")
        return d
    if x.dtype != y.dtype:
        d.append(f"{name}: dtype {x.dtype} vs {y.dtype}")
        return d
    hx, hy = bsha(x), bsha(y)
    if hx != hy:
        # quantify, so a difference is reportable and not just a boolean
        try:
            fa, fb = np.asarray(x, np.float64), np.asarray(y, np.float64)
            both = np.isfinite(fa) & np.isfinite(fb)
            nde = int((fa[both] != fb[both]).sum())
            mx = float(np.abs(fa[both] - fb[both]).max()) if both.any() else float("nan")
            nan_mismatch = int((np.isfinite(fa) != np.isfinite(fb)).sum())
            d.append(f"{name}: bytes differ (sha {hx[:12]} vs {hy[:12]}); "
                     f"differing finite cells={nde} max|delta|={mx:g} finiteness-mismatch cells={nan_mismatch}")
        except Exception:
            d.append(f"{name}: bytes differ (sha {hx[:12]} vs {hy[:12]}); not numerically comparable")
    return d


def load_scores(p: pathlib.Path):
    with np.load(p / "scores.npz", allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def load_model(p: pathlib.Path):
    import torch
    sd = torch.load(p / "model.pt", map_location="cpu", weights_only=True)
    out = {f"state_dict.{k}": v.detach().cpu().numpy() for k, v in sd["state_dict"].items()}
    for k in ("mu", "sd"):
        if k in sd:
            v = sd[k]
            out[k] = v.detach().cpu().numpy() if hasattr(v, "detach") else np.asarray(v)
    return out


def compare_dicts(A: dict, B: dict, prefix: str):
    diffs = []
    if set(A) != set(B):
        diffs.append(f"{prefix}: keys differ  only_A={sorted(set(A) - set(B))} only_B={sorted(set(B) - set(A))}")
    for k in sorted(set(A) & set(B)):
        diffs += cmp_arrays(f"{prefix}.{k}", A[k], B[k])
    return diffs


def compare_fold(da: pathlib.Path, db: pathlib.Path):
    diffs, info = [], {}
    try:
        SA, SB = load_scores(da), load_scores(db)
        diffs += compare_dicts(SA, SB, "scores")
        info["scores_P_sha_a"] = bsha(SA["P"]); info["scores_P_sha_b"] = bsha(SB["P"])
        info["P_shape"] = list(SA["P"].shape)
    except Exception as e:
        diffs.append(f"scores unreadable: {type(e).__name__}: {str(e)[:70]}")
    try:
        MA, MB = load_model(da), load_model(db)
        diffs += compare_dicts(MA, MB, "model")
    except Exception as e:
        diffs.append(f"model unreadable: {type(e).__name__}: {str(e)[:70]}")
    return diffs, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env-whitelist", required=True)
    args = ap.parse_args()
    extra = sorted(set(os.environ) - set(args.env_whitelist.split(",")))
    assert not extra, f"env outside whitelist: {extra}"

    A, B = pathlib.Path(args.a), pathlib.Path(args.b)
    folds = args.folds.split(",")
    print(f"self_sha256={hashlib.sha256(open(os.path.abspath(__file__),'rb').read()).hexdigest()}")
    print(f"label={args.label}")
    print(f"A={A}\nB={B}\nfolds={folds}")

    # ---- positive control, before any green is printed ----
    ctl = "UNAVAILABLE"
    try:
        S = load_scores(A / folds[0])
        P2 = S["P"].copy().ravel()
        idx = int(np.flatnonzero(np.isfinite(P2))[0])
        P2[idx] = np.float32(P2[idx] + np.float32(1e-6))
        cd = cmp_arrays("control.P", S["P"], P2.reshape(S["P"].shape))
        # Do NOT truncate this string: it ends in a formatted number, and cutting it mid-digits
        # makes the magnitude read wrong (a real "1.00024e-06" once printed as "1.00").
        ctl = f"PASS ({cd[0]})" if cd else "FAIL -- comparator did not see a one-cell change"
    except Exception as e:
        ctl = f"UNAVAILABLE ({type(e).__name__}: {str(e)[:50]})"
    print(f"POSITIVE_CONTROL={ctl}")

    results, all_same = [], True
    for f in folds:
        da, db = A / f, B / f
        if not da.exists() or not db.exists():
            results.append({"fold": f, "status": "MISSING", "a_exists": da.exists(), "b_exists": db.exists()})
            all_same = False
            print(f"  {f:8} MISSING  a={da.exists()} b={db.exists()}")
            continue
        diffs, info = compare_fold(da, db)
        results.append({"fold": f, "status": "IDENTICAL" if not diffs else "DIFFERS",
                        "diffs": diffs, **info})
        all_same &= not diffs
        print(f"  {f:8} {'IDENTICAL' if not diffs else 'DIFFERS'}  P={info.get('P_shape')} "
              f"P_sha={str(info.get('scores_P_sha_a'))[:12]}")
        for d in diffs:
            print(f"      DIFF {d}")

    receipt = {"device": "dlarch_identity_compare.py",
               "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
               "label": args.label, "a": str(A), "b": str(B), "folds": folds,
               "positive_control": ctl, "all_identical": bool(all_same), "results": results}
    rsha = sio.write_json(args.out, receipt)
    print(f"receipt={args.out} sha256={rsha}")
    verdict = "GREEN" if (all_same and ctl.startswith("PASS")) else "RED"
    print(f"DLARCH_IDENTITY={verdict} all_identical={all_same} control={ctl.split()[0]}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
