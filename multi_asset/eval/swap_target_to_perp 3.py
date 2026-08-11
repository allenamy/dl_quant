"""swap_target_to_perp — re-target spot-trained test preds onto the CLEAN PERP y_600.

Approach (a) for the clean-strong DL push: a model is trained SPOT->SPOT on full
history (data/npz_spot, leak-free spot y_600). Its per-fold test_preds.npz /
ema_test_preds.npz therefore carry SPOT targets. To honestly evaluate against the
leak-free PERP target (perp~=spot, corr 0.997+ in strong months), we swap the
`targets` array for the clean-perp y_600 matched by EXACT timestamp, keeping
`predictions` untouched and re-standardizing the perp y with the SAME per-fold
(y_sigma, y_median) so the perp_battery de-standardization stays consistent.
Pearson/Spearman/beta/sigma_ratio are affine-invariant, so this is metric-correct.

Writes a parallel directory <out_dir>/fold_*/ {test_preds.npz, ema_test_preds.npz}
with identical schema but PERP targets, so multi_asset/eval/perp_battery.py runs
unchanged on it.

Rows whose timestamp has no finite clean-perp label (or perp y_mask==0) are
DROPPED from that fold's swapped npz (predictions+targets+mask+timestamps all
sliced together) so the battery only sees rows with a real perp label.

Usage:
    python multi_asset/eval/swap_target_to_perp.py \
        --src_dir experiments/.../clean_strong_base_fullhist \
        --out_dir experiments/.../clean_strong_base_fullhist_PERPEVAL \
        --perp_dir data/npz_spot2perp_clean
"""
from __future__ import annotations

import argparse
import glob
import os
import os.path as p

import numpy as np


def build_perp_lookup(perp_dir):
    """ts(int64 us) -> perp y_600 (raw return), only finite & masked rows."""
    lut = {}
    files = sorted(glob.glob(p.join(perp_dir, "*.npz")))
    if not files:
        raise FileNotFoundError(f"no .npz under {perp_dir}")
    for f in files:
        z = np.load(f)
        if "y_600" not in z or "timestamps" not in z:
            continue
        ts = z["timestamps"].astype(np.int64)
        y = z["y_600"].astype(np.float64)
        if "y_mask_600" in z:
            m = z["y_mask_600"].astype(bool)
        else:
            m = np.ones(y.shape, bool)
        m = m & np.isfinite(y)
        for t, yy in zip(ts[m], y[m]):
            lut[int(t)] = float(yy)
    return lut


def swap_fold(npz_path, lut, out_path, y_clip=5.0):
    z = np.load(npz_path)
    preds = z["predictions"]
    ts = z["timestamps"].astype(np.int64)
    mask = z["mask"].astype(bool) if "mask" in z else np.ones(ts.shape, bool)
    y_sigma = float(z["y_sigma"]) if "y_sigma" in z else 1.0
    y_median = float(z["y_median"]) if "y_median" in z else 0.0

    # match perp y by exact timestamp
    perp_raw = np.full(ts.shape, np.nan, dtype=np.float64)
    hit = np.zeros(ts.shape, bool)
    for i, t in enumerate(ts):
        v = lut.get(int(t))
        if v is not None:
            perp_raw[i] = v
            hit[i] = True

    keep = hit & mask
    n_total = ts.size
    n_hit = int(hit.sum())
    n_keep = int(keep.sum())

    # re-standardize perp y with the SAME per-fold affine + clip the trainer used
    # (run_pipeline_v3 y_norm = (y_median, y_sigma, 5.0); dataset stores
    #  clip((y-median)/sigma, -5, +5) as `targets`). Match that caliber exactly.
    perp_std = np.clip((perp_raw - y_median) / y_sigma, -y_clip, y_clip)

    out = {
        "predictions": preds[keep],
        "targets": perp_std[keep].astype(np.float32),
        "mask": np.ones(int(keep.sum()), bool),
        "timestamps": ts[keep],
        "y_sigma": np.array(y_sigma),
        "y_median": np.array(y_median),
    }
    os.makedirs(p.dirname(out_path), exist_ok=True)
    np.savez(out_path, **out)
    return n_total, n_hit, n_keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--perp_dir", default="data/npz_spot2perp_clean")
    ap.add_argument("--y_clip", type=float, default=5.0,
                    help="standardized-y clip matching run_pipeline_v3 y_norm (default 5.0)")
    args = ap.parse_args()

    print(f"[swap] building perp lookup from {args.perp_dir} ...")
    lut = build_perp_lookup(args.perp_dir)
    print(f"[swap] perp lookup entries: {len(lut)}")

    fold_dirs = sorted(glob.glob(p.join(args.src_dir, "fold_*")))
    if not fold_dirs:
        raise FileNotFoundError(f"no fold_* under {args.src_dir}")

    for fd in fold_dirs:
        fold_name = p.basename(fd)
        for fname in ("test_preds.npz", "ema_test_preds.npz"):
            src = p.join(fd, fname)
            if not p.exists(src):
                print(f"[swap] {fold_name}/{fname}: MISSING, skip")
                continue
            out = p.join(args.out_dir, fold_name, fname)
            n_total, n_hit, n_keep = swap_fold(src, lut, out, y_clip=args.y_clip)
            print(f"[swap] {fold_name}/{fname}: total={n_total} perp_hit={n_hit} "
                  f"kept={n_keep} ({100.0*n_keep/max(n_total,1):.1f}%) -> {out}")

    print(f"[swap] done -> {args.out_dir}")


if __name__ == "__main__":
    main()
