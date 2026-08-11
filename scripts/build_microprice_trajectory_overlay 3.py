"""Build microprice-trajectory per-day overlay NPZ from `data/npz_v4/*.npz`.

v5push Track v8 (2026-05-15): builds per-(N, T) overlay aligned to npz_v4
windows with 4 channels of microprice trajectory features (60s rolling within
each 600s input window). Mirrors TV overlay format (`tv_feats`+`feat_names`).

Cleaner than v7 — no cross-day state needed since 60s lookback is strictly
within each 600s window. Each day processed independently.

Usage:
    python scripts/build_microprice_trajectory_overlay.py \
        --npz-dir data/npz_v4 \
        --out-dir data/npz_v4_microprice_trajectory
"""
from __future__ import annotations
import argparse
import os
import pathlib
import sys
import time
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.features.microprice_trajectory_features import (  # noqa: E402
    compute_microprice_trajectory_features,
    FEAT_NAMES,
)


def process_day(npz_path: pathlib.Path, out_path: pathlib.Path) -> dict | None:
    try:
        with np.load(npz_path, allow_pickle=True) as z:
            if "X_raw" not in z.files:
                return {"status": "skip_no_xraw"}
            x_raw = np.asarray(z["X_raw"], dtype=np.float32)  # (N, T, L, 4)
            timestamps = np.asarray(z["timestamps"], dtype=np.int64)
    except Exception as e:
        return {"status": "load_fail", "error": str(e)}

    if x_raw.shape[0] == 0 or x_raw.ndim != 4:
        return {"status": "skip_empty"}

    try:
        tv_feats = compute_microprice_trajectory_features(x_raw)  # (N, T, 4)
    except Exception as e:
        return {"status": "compute_fail", "error": str(e)}

    # Sanity stats
    ema_range = (float(tv_feats[..., 0].min()), float(tv_feats[..., 0].max()))
    slope_range = (float(tv_feats[..., 1].min()), float(tv_feats[..., 1].max()))
    persist_range = (float(tv_feats[..., 2].min()), float(tv_feats[..., 2].max()))
    amp_range = (float(tv_feats[..., 3].min()), float(tv_feats[..., 3].max()))
    n_nan = int(np.isnan(tv_feats).sum())

    np.savez_compressed(
        out_path,
        tv_feats=tv_feats,
        feat_names=np.array(FEAT_NAMES, dtype="<U28"),
        timestamps=timestamps,  # window-end ts for diagnostic
    )
    return {
        "status": "ok",
        "shape": tv_feats.shape,
        "ema_range": ema_range,
        "slope_range": slope_range,
        "persist_range": persist_range,
        "amp_range": amp_range,
        "nan": n_nan,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--start-day", default=None)
    ap.add_argument("--end-day", default=None)
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    days = sorted(
        [p.stem for p in npz_dir.iterdir() if p.suffix == ".npz" and len(p.stem) == 10]
    )
    if args.start_day:
        days = [d for d in days if d >= args.start_day]
    if args.end_day:
        days = [d for d in days if d <= args.end_day]

    print(f"[build_micro] Processing {len(days)} days")
    t_start = time.time()
    n_ok = n_skip = n_fail = 0
    for i, day in enumerate(days):
        out_path = out_dir / f"{day}.npz"
        if out_path.exists():
            n_skip += 1
            continue
        npz_path = npz_dir / f"{day}.npz"
        result = process_day(npz_path, out_path)
        if result is None:
            n_fail += 1
            continue
        if result["status"] == "ok":
            n_ok += 1
            if (n_ok % 50) == 0 or i == len(days) - 1:
                elapsed = time.time() - t_start
                print(
                    f"  [{day}] saved ({n_ok}/{len(days)}, {elapsed:.0f}s, "
                    f"shape={result['shape']}, "
                    f"ema∈{result['ema_range']}, persist∈{result['persist_range']}, "
                    f"nan={result['nan']})"
                )
        else:
            n_fail += 1
            print(f"  [{day}] {result.get('status')}: {result.get('error', '')}")

    elapsed = time.time() - t_start
    print(
        f"[build_micro] Done in {elapsed:.0f}s. "
        f"saved={n_ok} skipped={n_skip} failed={n_fail}. Output: {out_dir}"
    )


if __name__ == "__main__":
    main()
