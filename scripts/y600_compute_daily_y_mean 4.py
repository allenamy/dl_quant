"""Phase B.2: Precompute per-day y_600 mean for use as regime feature.

Output: data/npz_v4_daily_y_mean.json — {"2023-01-01": 0.000123, ...} where
value is mean of valid (mask=1) y_600 over all samples in that day, in raw
log-return units. Used by dataset.py to inject past_30d_y_mean as a 7th
regime_prior feature.

Causality: this is a per-day aggregate. At runtime, dataset.py uses days
[D-30, D-1] (strictly past) for sample at day D. No future leak.

Usage:
  python scripts/y600_compute_daily_y_mean.py
"""
from __future__ import annotations
import argparse
import json
import pathlib

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz-dir", default="data/npz_v4")
    ap.add_argument("--out", default="data/npz_v4_daily_y_mean.json")
    ap.add_argument("--y-key", default="y_600")
    ap.add_argument("--mask-key", default="y_mask_600")
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    if not days:
        raise SystemExit(f"No NPZ files in {npz_dir}")
    print(f"Scanning {len(days)} days from {days[0]} to {days[-1]}")

    # Phase B.6: store both mean AND std per day for vol-adjusted regime feature
    daily_stats: dict[str, dict] = {}
    skipped = 0
    for d in days:
        try:
            arr = np.load(npz_dir / f"{d}.npz", allow_pickle=True)
            y = arr[args.y_key]
            m = arr[args.mask_key].astype(bool)
            valid = y[m & np.isfinite(y)]
            if len(valid) >= 50:
                daily_stats[d] = {
                    "mean": float(valid.mean()),
                    "std": float(valid.std()),
                    "n": int(len(valid)),
                }
            else:
                skipped += 1
        except Exception as e:
            print(f"  skip {d}: {e}")
            skipped += 1
            continue

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Back-compat: keep flat {day: mean} format for existing B.2 usage,
    # but ADD detailed dict at separate path
    flat_means = {d: s["mean"] for d, s in daily_stats.items()}
    with open(out_path, "w") as f:
        json.dump(flat_means, f, indent=0, sort_keys=True)

    detailed_path = out_path.with_suffix(".detailed.json")
    with open(detailed_path, "w") as f:
        json.dump(daily_stats, f, indent=0, sort_keys=True)

    vals = np.array([s["mean"] for s in daily_stats.values()])
    stds = np.array([s["std"] for s in daily_stats.values()])
    print(f"\n→ {out_path} (flat means)")
    print(f"→ {detailed_path} (mean+std per day)")
    print(f"  {len(daily_stats)} days saved, {skipped} skipped")
    print(f"  y_600 mean stats (raw log-return):")
    print(f"    mean: {vals.mean():+.6e}, std: {vals.std():.6e}, range [{vals.min():+.6e}, {vals.max():+.6e}]")
    print(f"  y_600 std stats (raw log-return):")
    print(f"    mean: {stds.mean():.6e}, std: {stds.std():.6e}, range [{stds.min():.6e}, {stds.max():.6e}]")


if __name__ == "__main__":
    main()
