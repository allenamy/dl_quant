"""Build book-derived novel-feature overlay NPZs for V5 push.

Reads data/npz_v4/<date>.npz, computes 16 novel features from X_raw using the
compute_novel_features function from v5push_ridge_novel_features_y600.py, writes
data/npz_v4_novel_book/<date>.npz with:
  timestamps     (N,) int64
  novel_feats    (N, 16) float32
  feat_names     (16,) <U32

This is the overlay that V5 training reads alongside the base 64 features in X.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import pathlib
import time

import numpy as np

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from v5push_ridge_novel_features_y600 import compute_novel_features


def process_day(in_path: pathlib.Path, out_dir: pathlib.Path, force: bool = False):
    day = in_path.stem
    out_path = out_dir / f"{day}.npz"
    if out_path.exists() and not force:
        return day, "skip", 0.0
    t0 = time.time()
    try:
        z = np.load(in_path, allow_pickle=True)
        Xr = z["X_raw"]
        ts = z["timestamps"] if "timestamps" in z.files else np.zeros(len(Xr), dtype=np.int64)
        if Xr.shape[0] == 0:
            return day, "empty", 0.0
        novel, names = compute_novel_features(Xr)
        novel = np.nan_to_num(novel, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        feat_names = np.array(names, dtype="<U32")
        np.savez_compressed(out_path, timestamps=ts, novel_feats=novel, feat_names=feat_names)
        return day, "ok", time.time() - t0
    except Exception as e:
        return day, f"err:{type(e).__name__}:{str(e)[:60]}", time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/npz_v4")
    ap.add_argument("--out", default="data/npz_v4_novel_book")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    days = sorted(src.glob("20??-??-??.npz"))
    print(f"Building novel-book overlay for {len(days)} days → {out}")
    t_start = time.time()

    ok = skipped = errored = 0
    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(process_day, d, out, args.force) for d in days]
        for i, fut in enumerate(cf.as_completed(futures)):
            day, status, dt = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skipped += 1
            else:
                errored += 1
                print(f"  {day}: {status} ({dt:.2f}s)")
            if (i + 1) % 50 == 0:
                print(f"  progress {i+1}/{len(days)} ok={ok} skip={skipped} err={errored} ({time.time()-t_start:.0f}s)", flush=True)

    print(f"\nDone: ok={ok} skip={skipped} err={errored} in {time.time()-t_start:.0f}s → {out}")


if __name__ == "__main__":
    main()
