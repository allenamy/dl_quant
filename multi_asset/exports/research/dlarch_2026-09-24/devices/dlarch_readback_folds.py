#!/usr/bin/env python3
"""dlarch_readback_folds.py -- read-back verification of already-completed F10 fold artifacts.

WHY (lead ruling, 2026-09-25): the 8 completed T0 folds were written by the pre-fix trainer, whose
sha was taken AFTER an unverified write (E-0925-A). Before anything is built on them -- in
particular before G1b compares a re-trained 202506 against the archived one -- each artifact must be
read back and shown to be what its receipt says it is.

WHAT MAKES THIS MORE THAN "np.load did not raise":
  the receipt records STATISTICS OF THE CONTENT (test_anchors, scored_pairs, score_sha256,
  model_sha256). This device recomputes each one from the artifact and requires it to match. A file
  that decompresses but lost rows would pass a bare np.load and fail here.

POSITIVE CONTROL (runs first; a clean verdict is not printed without it):
  one fold's scores.npz is copied, the copy is given a size-preserving NUL tail, and the device must
  flag the copy. If the control does not fire, the device says so and returns non-zero instead of
  reporting the folds clean.

Read-only with respect to the fold artifacts: the only file written is the control's own copy, which
is removed. Usage:
  dlarch_readback_folds.py --root <T0 root> --out <receipt.json> --env-whitelist PATH,HOME,LC_CTYPE
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys

import numpy as np

import dlarch_safe_io as sio


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify_fold(d: pathlib.Path):
    """Returns (ok, record). Never raises on a damaged artifact -- damage is the finding."""
    rec = {"fold": d.name}
    rp = d / "FOLD_RECEIPT.json"
    if not rp.exists():
        return False, {**rec, "status": "NO_FOLD_RECEIPT"}
    try:
        R = json.loads(rp.read_text())
    except Exception as e:
        return False, {**rec, "status": f"FOLD_RECEIPT_UNPARSEABLE: {type(e).__name__}"}

    problems = []
    sp, mp = d / "scores.npz", d / "model.pt"

    # ---- scores.npz: read back every array, then recompute the receipt's own statistics ----
    try:
        with np.load(sp, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        P, rows, E_ts, syms = arrays["P"], arrays["rows"], arrays["E_ts"], arrays["symbols"]
        rec["scores"] = {
            "keys": sorted(arrays),
            "P": {"shape": list(P.shape), "dtype": str(P.dtype)},
            "rows": {"shape": list(rows.shape), "dtype": str(rows.dtype)},
            "E_ts": {"shape": list(E_ts.shape), "dtype": str(E_ts.dtype)},
            "symbols": {"shape": list(syms.shape), "dtype": str(syms.dtype)},
            # Spot values as exact BIT PATTERNS, not floats: P legitimately contains NaN, and a
            # float spot value would both trip allow_nan=False and lose the exact bits. hex of the
            # raw bytes is JSON-safe AND exact. (Caught by this device's own allow_nan=False.)
            "spot_P_first_last_hex": [P.ravel()[0].tobytes().hex(), P.ravel()[-1].tobytes().hex()],
            "spot_rows_first_last": [int(rows[0]), int(rows[-1])],
            "spot_E_ts_first_last": [int(E_ts[0]), int(E_ts[-1])],
            "finite_P": int(np.isfinite(P).sum()),
            # bitwise content fingerprints -- this is what G1b compares old vs re-trained
            "P_bytes_sha256": hashlib.sha256(P.tobytes()).hexdigest(),
            "rows_bytes_sha256": hashlib.sha256(rows.tobytes()).hexdigest(),
            "E_ts_bytes_sha256": hashlib.sha256(E_ts.tobytes()).hexdigest(),
            "symbols_bytes_sha256": hashlib.sha256(syms.tobytes()).hexdigest(),
            "sha256": sha(sp),
        }
        if len(rows) != P.shape[0]:
            problems.append(f"rows {len(rows)} != P rows {P.shape[0]}")
        if len(E_ts) != P.shape[0]:
            problems.append(f"E_ts {len(E_ts)} != P rows {P.shape[0]}")
        if len(syms) != P.shape[1]:
            problems.append(f"symbols {len(syms)} != P cols {P.shape[1]}")
        # the receipt's own recorded content statistics
        if R.get("test_anchors") != len(rows):
            problems.append(f"receipt test_anchors {R.get('test_anchors')} != rows {len(rows)}")
        if R.get("scored_pairs") != int(np.isfinite(P).sum()):
            problems.append(f"receipt scored_pairs {R.get('scored_pairs')} != finite P {int(np.isfinite(P).sum())}")
        if R.get("score_sha256") != rec["scores"]["sha256"]:
            problems.append("receipt score_sha256 != sha(scores.npz)")
    except Exception as e:
        problems.append(f"scores.npz unreadable: {type(e).__name__}: {str(e)[:70]}")

    # ---- model.pt ----
    try:
        import torch
        sd = torch.load(mp, map_location="cpu", weights_only=True)
        tensors = {k: v for k, v in sd["state_dict"].items()}
        rec["model"] = {
            "keys": sorted(sd),
            "tensors": {k: {"shape": list(v.shape), "dtype": str(v.dtype),
                            "bytes_sha256": hashlib.sha256(v.detach().cpu().numpy().tobytes()).hexdigest()}
                        for k, v in tensors.items()},
            "param_count": int(sum(v.numel() for v in tensors.values())),
            "input_dim": int(sd.get("input_dim", -1)),
            "fixed_epoch_index": int(sd.get("fixed_epoch_index", -1)),
            "sha256": sha(mp),
        }
        if R.get("model_sha256") != rec["model"]["sha256"]:
            problems.append("receipt model_sha256 != sha(model.pt)")
        if R.get("param_count") not in (None, rec["model"]["param_count"]):
            problems.append(f"receipt param_count {R.get('param_count')} != {rec['model']['param_count']}")
    except Exception as e:
        problems.append(f"model.pt unreadable: {type(e).__name__}: {str(e)[:70]}")

    rec["problems"] = problems
    rec["status"] = "OK" if not problems else "DAMAGED_OR_INCONSISTENT"
    return not problems, rec


def positive_control(donor: pathlib.Path, tmpdir: pathlib.Path):
    """Copy a real scores.npz, give the copy a size-preserving NUL tail, require detection."""
    tmpdir.mkdir(parents=True, exist_ok=True)
    fake = tmpdir / "control_fold"
    fake.mkdir(exist_ok=True)
    shutil.copy2(donor / "scores.npz", fake / "scores.npz")
    shutil.copy2(donor / "model.pt", fake / "model.pt")
    shutil.copy2(donor / "FOLD_RECEIPT.json", fake / "FOLD_RECEIPT.json")
    n = (fake / "scores.npz").stat().st_size
    with open(fake / "scores.npz", "r+b") as f:
        f.seek(-200, os.SEEK_END)
        f.write(b"\0" * 200)
    assert (fake / "scores.npz").stat().st_size == n, "control must preserve size"
    ok, rec = verify_fold(fake)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return (not ok), rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env-whitelist", required=True)
    a = ap.parse_args()
    extra = sorted(set(os.environ) - set(a.env_whitelist.split(",")))
    assert not extra, f"env outside whitelist: {extra}"

    root = pathlib.Path(a.root)
    folds = sorted(p for p in root.iterdir() if p.is_dir() and (p / "FOLD_RECEIPT.json").exists())
    print(f"self_sha256={sha(os.path.abspath(__file__))}")
    print(f"root={root}  folds_with_receipt={len(folds)}")
    if not folds:
        print("READBACK_VERDICT=NO_FOLDS")
        return 1

    fired, ctl = positive_control(folds[0], root.parent / ".readback_control")
    print(f"POSITIVE_CONTROL={'PASS (NUL-tailed copy was flagged)' if fired else 'FAIL -- device has no power'}")
    if fired:
        print(f"    control problems: {ctl['problems'][:2]}")

    results, all_ok = [], True
    for d in folds:
        ok, rec = verify_fold(d)
        results.append(rec)
        all_ok &= ok
        s = rec["scores"]
        print(f"  {rec['fold']:8} {rec['status']:24} P={s['P']['shape']} finite={s['finite_P']:>8} "
              f"score_sha={s['sha256'][:12]} model_sha={rec['model']['sha256'][:12]}")
        for p in rec["problems"]:
            print(f"      PROBLEM {p}")

    receipt = {"device": "dlarch_readback_folds.py", "self_sha256": sha(os.path.abspath(__file__)),
               "root": str(root), "positive_control_fired": bool(fired),
               "positive_control_problems": ctl.get("problems"),
               "folds": results, "all_ok": bool(all_ok)}
    rsha = sio.write_json(a.out, receipt)
    print(f"receipt={a.out} sha256={rsha}")
    verdict = "GREEN" if (all_ok and fired) else "RED"
    print(f"READBACK_VERDICT={verdict} folds={len(folds)} all_ok={all_ok} control_fired={fired}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
