"""Build npz_v2arch_augms = npz_v2arch (88ch) + X_basis(10) concatenated INTO X (-> 98ch).

> **created:** 2026-07-05 | **Session:** fable-regime-breakthrough (basis DL confirmation) | **状态:** in-progress

NON-DESTRUCTIVE: reads the READ-ONLY npz_v2arch base, writes a NEW dir npz_v2arch_augms.
X[:, :, :88] is a byte-identical copy of npz_v2arch["X"] (base dtype preserved); the 10
basis-DYNAMICS channels (add_basis_dynamics.BASIS_NAMES) are appended as X[:, :, 88:98].
All other keys (X_raw, X_raw_perp_deep, X_long, regime_prior, y_600, y_mask_600,
timestamps, *_names) are copied verbatim. A `basis_names` key is added for provenance.

SOURCE REPOINT (verified 2026-07-05, alignment battery):
  - spot source npz_v4 -> npz_spot : col0(ret1s)/col6(obi_L5) corr(v4,spot)=1.0000,
    byte-identical mean/std; npz_spot spans 2023-01-01..2026-05-31 (full range, no cutoff).
  - perp source npz_perp (full range 2023-01-01..2026-05-31).
  - base npz_v2arch (88ch, 2023-08-19..2026-05-31); base ts 100% subset of npz_spot ts;
    all µs; per-day window count matches (477) -> no length mismatch.

The 10 X_basis channels are RAW (bps/dynamics units, consistent with the existing
cross channel x_basis_bps=ch81). The dataset applies per-channel static train-window
z-norm (width-agnostic, auto-covers ch88:97); RevIN-skip on ch80/81 + 88:97 then
preserves basis level/sign (see build_v2arch_aug README in the report).

Usage:
  python multi_asset/data/build_v2arch_aug.py --days 2026-01-15 2025-10-15   # smoke
  python multi_asset/data/build_v2arch_aug.py --start 2024-06-01 --end 2026-02-10  # full
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import sys
import time

import numpy as np

# repo root (this file: <repo>/multi_asset/data/build_v2arch_aug.py)
_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)

import multi_asset.data.add_basis_dynamics as ab  # noqa: E402

# --- SOURCE REPOINT (verified) -------------------------------------------------
ab.NPZV4_DIR = p.join(_REPO, "data", "npz_spot")    # clean full-range SPOT (was npz_v4)
ab.PERP_DIR = p.join(_REPO, "data", "npz_perp")     # full-range PERP
ab.DUAL_DIR = p.join(_REPO, "data", "npz_v2arch")   # BASE (keepv mask + pred_secs source)

BASE_DIR = ab.DUAL_DIR
OUT_DIR = p.join(_REPO, "data", "npz_v2arch_augms")
US = ab.US
BASE_NC = 88


def build_one(day: str, force: bool = False) -> str:
    bfp = p.join(BASE_DIR, f"{day}.npz")
    ofp = p.join(OUT_DIR, f"{day}.npz")
    if not p.exists(bfp):
        return "missing-base"
    if p.exists(ofp) and not force:
        return "skip"
    dl = dict(np.load(bfp, allow_pickle=True))
    base_nc = int(dl["X"].shape[-1])
    if base_nc != BASE_NC:
        return f"base-not-88({base_nc})"
    cur = ab._day_series(day)
    if cur is None:
        return "no-series"
    ts_sec, secg, pret, sret, pobi, sobi = cur
    # prior-day stitch for a warm basis anchor + rolling windows (verbatim build_day)
    pday = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
    pc = ab._day_series(pday)
    if pc is not None:
        _, psecg, ppret, psret, ppobi, psobi = pc
        keep = psecg < secg[0]
        secg = np.concatenate([psecg[keep], secg])
        pret = np.concatenate([ppret[keep], pret])
        sret = np.concatenate([psret[keep], sret])
        pobi = np.concatenate([ppobi[keep], pobi])
        sobi = np.concatenate([psobi[keep], sobi])
    pred_secs = dl["timestamps"].astype(np.int64) // US
    Xb = ab._build_basis(pret, sret, pobi, sobi, pred_secs, secg)  # (N,600,10) f32
    if Xb.shape[0] != dl["X"].shape[0]:
        return f"len-mismatch {Xb.shape[0]} vs {dl['X'].shape[0]}"
    if Xb.shape[1] != dl["X"].shape[1]:
        return f"seqlen-mismatch {Xb.shape[1]} vs {dl['X'].shape[1]}"
    base_dtype = dl["X"].dtype  # PRESERVE base dtype so X[:,:,:88] stays byte-identical
    X_new = np.concatenate([dl["X"], Xb.astype(base_dtype)], axis=-1)  # (N,600,98)
    dl["X"] = X_new
    dl["basis_names"] = np.array(ab.BASIS_NAMES, dtype=object)
    tmp = ofp + ".tmp"
    with open(tmp, "wb") as fh:  # file handle => np.savez does NOT append ".npz"
        np.savez(fh, **dl)
    os.replace(tmp, ofp)
    return "built"


def _daterange(start: str, end: str):
    d0 = dt.date.fromisoformat(start)
    d1 = dt.date.fromisoformat(end)
    d = d0
    while d <= d1:
        yield d.isoformat()
        d += dt.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.days:
        days = args.days
    elif args.start and args.end:
        # only days the base actually has
        have = set(f[:-4] for f in os.listdir(BASE_DIR) if f.endswith(".npz") and f[0].isdigit())
        days = [d for d in _daterange(args.start, args.end) if d in have]
    else:
        ap.error("pass --days or --start/--end")
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"[augms] BASE={BASE_DIR}", flush=True)
    print(f"[augms] SPOT={ab.NPZV4_DIR}  PERP={ab.PERP_DIR}", flush=True)
    print(f"[augms] OUT={OUT_DIR}  n_days={len(days)}", flush=True)
    t0 = time.time()
    counts: dict[str, int] = {}
    for i, day in enumerate(days):
        try:
            r = build_one(day, force=args.force)
        except Exception as e:  # noqa: BLE001
            r = f"error:{type(e).__name__}:{e}"
        k = r if r in ("built", "skip") else (r.split()[0] if r else "unk")
        counts[k] = counts.get(k, 0) + 1
        if r not in ("built", "skip"):
            print(f"  {day}: {r}", flush=True)
        if (i + 1) % 50 == 0 or i + 1 == len(days):
            print(f"  [{i+1}/{len(days)}] {counts} ({time.time()-t0:.0f}s)", flush=True)
    print(f"[augms] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
