"""Build daily y_600 statistics JSON for v6b regime feature aggregation.

Reads each NPZ in data/npz_v4/, computes per-day mean+std of y_600 (mask=1),
saves JSON {day_str: {"mean": float, "std": float, "n": int}}.

Used by dataset.py _compute_past_y_stat for v6b multi-timescale regime features.
Strictly causal: each day's stat is computed only from that day's data.

Usage:
    python scripts/build_daily_y_stats_json.py \\
        --npz-dir data/npz_v4 \\
        --out data/v6b_daily_y_stats.json
"""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import numpy as np


def compute_day_stats(npz_path: pathlib.Path) -> dict | None:
    try:
        z = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        print(f"  skip {npz_path.name}: load error {e}")
        return None
    if "y_600" not in z.files or "y_mask_600" not in z.files:
        print(f"  skip {npz_path.name}: no y_600/y_mask_600")
        return None
    y = np.asarray(z["y_600"], dtype=np.float64).reshape(-1)
    m = np.asarray(z["y_mask_600"], dtype=np.float64).reshape(-1)
    valid = m > 0
    n = int(valid.sum())
    if n < 10:
        return None
    yv = y[valid]
    # Reject inf/nan
    yv = yv[np.isfinite(yv)]
    if len(yv) < 10:
        return None
    return {
        "mean": float(np.mean(yv)),
        "std": float(np.std(yv)),
        "n": int(len(yv)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not npz_dir.exists():
        raise FileNotFoundError(npz_dir)

    files = sorted([p for p in npz_dir.iterdir() if p.suffix == ".npz" and len(p.stem) == 10])
    print(f"Found {len(files)} day NPZ files in {npz_dir}")

    stats: dict[str, dict] = {}
    n_skipped = 0
    for i, p in enumerate(files):
        day = p.stem  # YYYY-MM-DD
        s = compute_day_stats(p)
        if s is None:
            n_skipped += 1
            continue
        stats[day] = s
        if (i + 1) % 100 == 0:
            print(f"  processed {i+1}/{len(files)} ({len(stats)} valid, {n_skipped} skipped)")

    # Sample summary
    means = [v["mean"] for v in stats.values()]
    stds = [v["std"] for v in stats.values()]
    print(f"\nTotal days written: {len(stats)} (skipped {n_skipped})")
    print(f"Daily mean of y_600 (across days): {np.mean(means):+.6e}")
    print(f"Daily std  of y_600 (across days): {np.mean(stds):.6e}")

    with open(out, "w") as f:
        json.dump(stats, f, indent=0)
    print(f"Saved: {out} ({os.path.getsize(out) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
