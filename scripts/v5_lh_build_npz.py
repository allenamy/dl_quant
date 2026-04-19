#!/usr/bin/env python3
"""Build V5-LH NPZ for all days from V4 NPZ.

Pipeline:
  1. Compute feature redundancy filter on first N training days (default 700).
  2. Save filter metadata to data/npz_v5_lh/_filter_meta.json.
  3. For each V4 day NPZ, stitch 3 non-overlapping 600-step windows into
     1800-step LH inputs (Task 12 pipeline), applying kept-feature projection
     and optional Savitzky-Golay filter.

Run on POD after mamba-ssm install. ~6-12 hrs for 991 days on NFS volume.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np

from src.features_v5_lh.redundancy_filter import select_features
from src.features_v5_lh.pipeline_lh import build_lh_npz_from_v4


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src-dir", type=pathlib.Path, default=pathlib.Path("data/npz_v4"))
    p.add_argument("--dst-dir", type=pathlib.Path, default=pathlib.Path("data/npz_v5_lh"))
    p.add_argument("--input-len", type=int, default=1800)
    p.add_argument("--filter-fold-train-days", type=int, default=700,
                   help="Use first N days (fold-0 train set) to compute redundancy filter")
    p.add_argument("--r-threshold", type=float, default=0.95)
    p.add_argument("--sg-window", type=int, default=None,
                   help="Savitzky-Golay filter window (odd int). None disables.")
    p.add_argument("--sg-polyorder", type=int, default=2)
    p.add_argument("--filter-target", type=str, default="y_180",
                   help="Target key used for IC tie-breaking in the redundancy filter")
    p.add_argument("--skip-filter", action="store_true",
                   help="Skip redundancy filter, keep all features (no filter meta written)")
    p.add_argument("--resume", action="store_true",
                   help="Skip days whose LH NPZ already exists in dst-dir")
    args = p.parse_args()

    args.dst_dir.mkdir(parents=True, exist_ok=True)
    days = sorted(f.stem for f in args.src_dir.glob("*.npz") if not f.stem.startswith("_"))
    print(f"[build_npz] {len(days)} V4 days in {args.src_dir}")
    if len(days) == 0:
        print("[build_npz] no V4 NPZ found — check --src-dir", file=sys.stderr)
        sys.exit(1)

    # ---- Step 1: compute redundancy filter ----
    if args.skip_filter:
        kept = None
        meta = {
            "r_threshold": None,
            "n_features_original": None,
            "kept_indices": None,
            "input_len": args.input_len,
            "sg_window": args.sg_window,
            "sg_polyorder": args.sg_polyorder,
            "skipped": True,
        }
        print("[build_npz] skipping redundancy filter (--skip-filter)")
    else:
        print(f"[build_npz] computing redundancy filter on first {args.filter_fold_train_days} days "
              f"(target={args.filter_target}, r_threshold={args.r_threshold})")
        X_all, y_all = [], []
        for i, day in enumerate(days[:args.filter_fold_train_days]):
            src = np.load(str(args.src_dir / f"{day}.npz"), allow_pickle=True)
            if args.filter_target not in src.files:
                raise KeyError(
                    f"target {args.filter_target!r} missing from {day}.npz "
                    f"(files: {sorted(src.files)})"
                )
            # Use LAST timestep of V4 window as feature row (matches Task 12's
            # anchor timestep convention, so IC is measured at the prediction
            # moment).
            X_all.append(src["X"][:, -1, :].astype(np.float32))
            y_all.append(src[args.filter_target].astype(np.float32))
            if (i + 1) % 100 == 0:
                print(f"  [filter] {i + 1}/{args.filter_fold_train_days} days loaded")
        X_all = np.concatenate(X_all, axis=0)
        y_all = np.concatenate(y_all, axis=0)
        print(f"[build_npz] filter input: X={X_all.shape}, y={y_all.shape}")
        kept = select_features(X_all, y_all, r_threshold=args.r_threshold)
        print(f"[build_npz] kept {len(kept)}/{X_all.shape[1]} features after redundancy filter")

        meta = {
            "r_threshold": args.r_threshold,
            "n_features_original": int(X_all.shape[1]),
            "kept_indices": kept,
            "n_features_kept": len(kept),
            "input_len": args.input_len,
            "sg_window": args.sg_window,
            "sg_polyorder": args.sg_polyorder,
            "filter_fold_train_days": args.filter_fold_train_days,
            "filter_target": args.filter_target,
        }

    with open(args.dst_dir / "_filter_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[build_npz] filter metadata written to {args.dst_dir}/_filter_meta.json")

    # ---- Step 2: build each day's LH NPZ ----
    t0 = time.time()
    n_done = 0
    n_skipped = 0
    for i, day in enumerate(days):
        src_path = args.src_dir / f"{day}.npz"
        dst_path = args.dst_dir / f"{day}.npz"
        if args.resume and dst_path.exists():
            n_skipped += 1
            continue
        try:
            build_lh_npz_from_v4(
                src_path, dst_path,
                input_len=args.input_len,
                kept_feature_indices=kept,
                sg_window=args.sg_window,
                sg_polyorder=args.sg_polyorder,
            )
            n_done += 1
        except Exception as e:
            print(f"[build_npz] ERROR on {day}: {e}", file=sys.stderr)
            raise
        if (i + 1) % 25 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta_min = (len(days) - (i + 1)) / rate / 60 if rate > 0 else float("inf")
            print(f"[build_npz] {i + 1}/{len(days)} days done "
                  f"({n_done} new, {n_skipped} resumed) — ETA {eta_min:.1f} min")

    elapsed = time.time() - t0
    print(f"[build_npz] FINISHED {len(days)} days in {elapsed / 60:.1f} min "
          f"({n_done} built, {n_skipped} resumed)")


if __name__ == "__main__":
    main()
