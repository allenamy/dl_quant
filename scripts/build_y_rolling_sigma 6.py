"""Build per-day rolling 30d MAD-σ of y_600 (CAUSAL: uses days [D-30, D-1]).

Output: data/y_rolling_sigma_30d.json with {day_str: sigma_value}.
sigma_value is in raw log-return units (not bps).

Usage at training: divide y_600[t] by sigma_day_t → vol-normalized target.
Usage at eval: multiply predicted vol_norm_y by sigma_day → raw y → ×1e4 bps.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", default="data/npz_v4")
    ap.add_argument("--out", default="data/y_rolling_sigma_30d.json")
    ap.add_argument("--window-days", type=int, default=30)
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    print(f"Found {len(days)} days in {npz_dir}")
    print(f"Window: {args.window_days} days (causal, strictly past)")

    # Pre-aggregate y per day (only valid)
    y_by_day: dict[str, np.ndarray] = {}
    for d in days:
        z = np.load(npz_dir / f"{d}.npz")
        y = z["y_600"]
        m = z["y_mask_600"].astype(bool)
        y_valid = y[m]
        if len(y_valid) > 0:
            y_by_day[d] = y_valid

    print(f"Days with valid y: {len(y_by_day)}")

    # For each day D, σ_D = MAD-σ over y from days [D-window, D-1]
    result = {}
    for i, d in enumerate(days):
        start = max(0, i - args.window_days)
        past_y_lists = [y_by_day[dd] for dd in days[start:i] if dd in y_by_day]
        if not past_y_lists:
            result[d] = None
            continue
        past_y = np.concatenate(past_y_lists)
        if len(past_y) < 100:
            result[d] = None
            continue
        med = float(np.median(past_y))
        mad = float(np.median(np.abs(past_y - med)) * 1.4826)
        result[d] = mad if mad > 1e-9 else None
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(days)} {d}: σ_past_{args.window_days}d = {mad*1e4:.2f} bps  (past n={len(past_y):,})", flush=True)

    n_valid = sum(1 for v in result.values() if v is not None)
    print(f"\nValid σ entries: {n_valid}/{len(days)}")
    # Distribution
    valid_sigmas = np.array([v for v in result.values() if v is not None]) * 1e4
    print(f"σ distribution (bps): mean={valid_sigmas.mean():.2f} std={valid_sigmas.std():.2f} min={valid_sigmas.min():.2f} max={valid_sigmas.max():.2f} median={np.median(valid_sigmas):.2f}")
    print(f"Top 5 highest σ days:")
    for d, s in sorted(result.items(), key=lambda kv: -(kv[1] or 0))[:5]:
        if s is not None:
            print(f"  {d}: {s*1e4:.2f} bps")
    print(f"Top 5 lowest σ days (valid):")
    for d, s in sorted([(k,v) for k,v in result.items() if v is not None], key=lambda kv: kv[1])[:5]:
        print(f"  {d}: {s*1e4:.2f} bps")

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n→ {args.out}")


if __name__ == "__main__":
    main()
