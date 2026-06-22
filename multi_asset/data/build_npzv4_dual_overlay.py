"""Build a 2023+ DUAL-SOURCE overlay cache on the PROVEN npz_v4 base.

> **created:** 2026-06-23 | **Session:** v2-dual-source-arch (2023+ base) | **状态:** in-progress
> | **作废条件:** superseded if npz_v4 or npz_perp caches are replaced, or if a native
>   2023+ npz_spot2perp_clean/mid rebuild from Tardis lands.

WHY (the root-cause-driven pivot)
---------------------------------
The decisive root-cause test proved the perp "low 0.04" was a RECIPE/DATA-ERA
artifact, NOT the target: the milestone recipe (npz_v4 spot-book feats, 2023+,
train700, batch1024/lr6e-4) reaches perp y_600 ~0.06, while the v2arch cache
(2024-01+, train300) caps ~0.043. The dual-source LEVERS (perp raw-book gated
residual, bounded cross block) were therefore being tested on a HANDICAPPED base.

This builder overlays the dual-source inputs onto npz_v4's ALREADY-PROVEN 2023+
windows (the 0.06 base), so the levers are added on the good base:

  * ``npz_v4/<day>.npz``  (single-asset repo, 2023-01..2025-09, the milestone cache)
        X (N,600,64) f32     SPOT-book hand feats   (Path A base — the 0.06 signal)
        X_raw (N,600,20,4) f16  SPOT raw LOB        (Path B tower)
        regime_prior (N,6), y_600/y_mask_600, timestamps (window cutoff t, µs)
  * ``npz_perp/<day>.npz``  (multi_asset repo, 2023-01..2026-05)
        X (N,600,64) f32     PERP hand feats        (cross-block source)
        X_raw (N,600,20,4) f16  PERP raw LOB        (Path C residual source)

JOIN: every npz_v4 window timestamp is matched to the npz_perp window with the
same cutoff t up to a CONSTANT per-day whole-second offset (2023 carries a steady
-1s offset; 2024/25 are exact). We assert the offset is constant + small per day,
then position-join. npz_v4's y_600/timestamps/X/X_raw are kept VERBATIM (the proven
leak-free base); only the perp raw book + the bounded cross block are added.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npzv4_dual/<YYYY-MM-DD>.npz with keys:
      X               f32 (N,600,72)   64 SPOT-book + 8 BOUNDED cross channels
      X_raw           f16 (N,600,20,4) SPOT raw LOB        (Path B — verbatim npz_v4)
      X_raw_perp_deep f16 (N,600,20,4) PERP raw LOB        (Path C residual, ts-joined)
      regime_prior    f32 (N,6)        verbatim npz_v4
      y_600           f32 (N,)         verbatim npz_v4 (proven leak-free perp target)
      y_mask_600      uint8 (N,)
      timestamps      i64 (N,)         verbatim npz_v4 window cutoff t (µs)
      cross_names     (8,) object
  plus data/npzv4_dual/build_meta.json.

X LAYOUT: X[:, :, 0:64] = npz_v4 SPOT-book-64 ; X[:, :, 64:72] = bounded cross-8.
  (the matched-BASE arm slices x_channels=64 to recover the exact npz_v4 0.06 base.)

THE 8 BOUNDED CROSS CHANNELS (mid-free — derived from the two aligned 64-feat seqs)
----------------------------------------------------------------------------------
npz_v4 carries no per-second mid grid back to 2023 (mid_cache starts 2024-01), so
the cross block uses ONLY per-step feature DIFFS/ratios from the two aligned 64-dim
SEQUENCES (spot = npz_v4 X, perp = npz_perp X). These are the Ridge-confirmed
signal-bearing cross channels (the mid-grid channels 0/1/6 of the v2arch cross
block were redundant log-ratios ≈0). All bounded — no toxic divergence SEQ.
  0 x_ret_diff      clip(perp_ret1s − spot_ret1s, ±0.01)     basis-velocity proxy
  1 x_mpdev_diff    clip(perp_mpdev − spot_mpdev, ±3)         microprice-dev diff (basis level proxy)
  2 x_spread_ratio  clip(log((p_spr+1)/(s_spr+1)), ±4)        rel liquidity tightness
  3 x_depth_ratio   clip(log(perp_L25/spot_L25), ±4)          rel depth
  4 x_obi_diff      clip(perp_obi_L5 − spot_obi_L5, ±2)       book-pressure differential
  5 x_rvol_ratio    clip(log(perp_rv30/spot_rv30), ±4)        rel short-horizon vol
  6 x_tradeflow_r   tanh(perp_ntf / (|spot_ntf|+1))           rel trade-flow direction
  7 x_pressure_diff clip(perp_bookpress − spot_bookpress, ±3) book-pressure-imbalance diff
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import os.path as p
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
# npz_v4 lives in the SINGLE-ASSET repo (the milestone cache); perp in this repo.
NPZV4_DIR = "/mnt/storage/private/work_hsy/quant_research/data/npz_v4"
PERP_DIR = p.join(_REPO, "data", "npz_perp")
OUT_DIR = p.join(_REPO, "data", "npzv4_dual")

INPUT_LEN = 600
US = 1_000_000
SHIFT_TOL_US = 11 * US
EPS = 1e-8

# 64-feat column indices (shared npz_v4/npz_perp schema; verified by name)
J_RET1S = 0          # log_return_1s
J_SPREAD = 3         # spread_bps
J_OBI_L5 = 6         # obi_L5
J_BID_DEPTH_L25 = 12 # bid_depth_L25
J_ASK_DEPTH_L25 = 13 # ask_depth_L25
J_RVOL30 = 18        # realized_vol_30s
J_NTF = 45           # net_trade_flow_1s
J_MPDEV = 52         # microprice_dev_bps
J_BOOKPRESS = 56     # book_pressure_imbalance

CROSS_NAMES = [
    "x_ret_diff", "x_mpdev_diff", "x_spread_ratio", "x_depth_ratio",
    "x_obi_diff", "x_rvol_ratio", "x_tradeflow_r", "x_pressure_diff",
]


def _build_cross(xs_spot: np.ndarray, xp_perp: np.ndarray) -> np.ndarray:
    """X_cross (N,600,8) — mid-free, all bounded per-step diffs/ratios."""
    Xs = xs_spot.astype(np.float64); Xp = xp_perp.astype(np.float64)
    Xc = np.empty((Xs.shape[0], INPUT_LEN, 8), dtype=np.float64)
    Xc[:, :, 0] = np.clip(Xp[:, :, J_RET1S] - Xs[:, :, J_RET1S], -0.01, 0.01)
    Xc[:, :, 1] = np.clip(Xp[:, :, J_MPDEV] - Xs[:, :, J_MPDEV], -3.0, 3.0)
    s_spr = Xs[:, :, J_SPREAD]; p_spr = Xp[:, :, J_SPREAD]
    Xc[:, :, 2] = np.clip(np.log((np.clip(p_spr, 0, None) + 1.0) /
                                 (np.clip(s_spr, 0, None) + 1.0)), -4.0, 4.0)
    sd = np.abs(Xs[:, :, J_BID_DEPTH_L25]) + np.abs(Xs[:, :, J_ASK_DEPTH_L25])
    pd = np.abs(Xp[:, :, J_BID_DEPTH_L25]) + np.abs(Xp[:, :, J_ASK_DEPTH_L25])
    Xc[:, :, 3] = np.clip(np.log((pd + EPS) / (sd + EPS)), -4.0, 4.0)
    Xc[:, :, 4] = np.clip(Xp[:, :, J_OBI_L5] - Xs[:, :, J_OBI_L5], -2.0, 2.0)
    s_rv = Xs[:, :, J_RVOL30]; p_rv = Xp[:, :, J_RVOL30]
    Xc[:, :, 5] = np.clip(np.log((np.clip(p_rv, 0, None) + EPS) /
                                 (np.clip(s_rv, 0, None) + EPS)), -4.0, 4.0)
    Xc[:, :, 6] = np.tanh(Xp[:, :, J_NTF] / (np.abs(Xs[:, :, J_NTF]) + 1.0))
    Xc[:, :, 7] = np.clip(Xp[:, :, J_BOOKPRESS] - Xs[:, :, J_BOOKPRESS], -3.0, 3.0)
    return np.nan_to_num(Xc, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def build_day(day_str: str, force: bool = False) -> str:
    out_fp = p.join(OUT_DIR, f"{day_str}.npz")
    if p.exists(out_fp) and not force:
        return "skip"
    v4_fp = p.join(NPZV4_DIR, f"{day_str}.npz")
    pp_fp = p.join(PERP_DIR, f"{day_str}.npz")
    if not (p.exists(v4_fp) and p.exists(pp_fp)):
        return "missing-base"

    v4 = np.load(v4_fp, allow_pickle=True)
    pp = np.load(pp_fp, allow_pickle=True)

    Xv = v4["X"]                                    # (Nv,600,64) spot-book
    tv = v4["timestamps"].astype(np.int64)
    tp = pp["timestamps"].astype(np.int64)
    Xp_all = pp["X"]                                # (Np,600,64) perp
    Xraw_perp_all = np.asarray(pp["X_raw"], dtype=np.float16)
    Xraw_spot = np.asarray(v4["X_raw"], dtype=np.float16)

    # Determine the CONSTANT per-day offset (perp − v4) via nearest-neighbour on the
    # first few windows, then position-join all v4 windows to the matching perp idx.
    j0 = np.searchsorted(tp, tv)
    j0 = np.clip(j0, 0, len(tp) - 1)
    # candidate offsets from nearest neighbour
    near = []
    for t in tv[: min(50, len(tv))]:
        k = int(np.argmin(np.abs(tp - t)))
        near.append(int(tp[k] - t))
    off_vals, off_cnts = np.unique(np.array(near), return_counts=True)
    off = int(off_vals[np.argmax(off_cnts)])        # dominant constant offset
    if abs(off) > SHIFT_TOL_US:
        return f"large-offset {off}"
    # join: for each v4 ts, the perp window has cutoff tv+off
    target = tv + off
    idx = np.searchsorted(tp, target)
    idx = np.clip(idx, 0, len(tp) - 1)
    exact = (tp[idx] == target)
    if exact.sum() < 0.95 * len(tv):
        return f"low-match {int(exact.sum())}/{len(tv)} off={off}"
    # keep only exactly-matched v4 windows (drop the few unmatched)
    keep = exact
    Xv = Xv[keep]
    tv = tv[keep]
    Xraw_spot = Xraw_spot[keep]
    rp = np.asarray(v4["regime_prior"], dtype=np.float32)[keep]
    y = np.asarray(v4["y_600"], dtype=np.float32)[keep]
    ym = np.asarray(v4["y_mask_600"]).astype(np.uint8)[keep]
    pidx = idx[keep]
    Xp = Xp_all[pidx]                               # perp 64-feat aligned
    Xraw_perp = Xraw_perp_all[pidx]                 # perp raw book aligned

    if Xraw_spot.shape != Xraw_perp.shape:
        return f"raw-shape-mismatch {Xraw_spot.shape} vs {Xraw_perp.shape}"

    Xcross = _build_cross(Xv, Xp)                    # (N,600,8)
    X72 = np.concatenate([Xv.astype(np.float32), Xcross], axis=-1)   # (N,600,72)

    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez(
        out_fp,
        X=X72.astype(np.float32),
        X_raw=Xraw_spot,
        X_raw_perp_deep=Xraw_perp,
        regime_prior=rp,
        y_600=y,
        y_mask_600=ym,
        timestamps=tv,
        cross_names=np.array(CROSS_NAMES, dtype=object),
    )
    return "built"


def _all_days() -> list[str]:
    v4 = {f[:-4] for f in os.listdir(NPZV4_DIR) if f.endswith(".npz") and f[0].isdigit()}
    pp = {f[:-4] for f in os.listdir(PERP_DIR) if f.endswith(".npz") and f[0].isdigit()}
    return sorted(v4 & pp)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build 2023+ npz_v4 dual-source overlay")
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    days = _all_days() if args.all else args.days
    if not days:
        ap.error("pass --days <d...> or --all")

    print(f"[npzv4_dual] {len(days)} day(s); out={OUT_DIR}", flush=True)
    t0 = time.time(); counts: dict[str, int] = {}
    for i, day in enumerate(days):
        try:
            r = build_day(day, force=args.force)
        except Exception as e:  # noqa: BLE001
            r = f"error:{type(e).__name__}:{e}"
        key = r if r in ("built", "skip") else (r.split()[0] if r else "unknown")
        counts[key] = counts.get(key, 0) + 1
        if r not in ("built", "skip"):
            print(f"  {day}: {r}", flush=True)
        if (i + 1) % 100 == 0 or i + 1 == len(days):
            print(f"  [{i+1}/{len(days)}] {counts} ({time.time()-t0:.0f}s)", flush=True)

    meta = {
        "created": dt.datetime.now(dt.UTC).isoformat(),
        "sources": {"npz_v4": NPZV4_DIR, "perp": PERP_DIR},
        "x_layout": "X[:, :, 0:64]=npz_v4 spot-book-64; [64:72]=bounded cross",
        "cross_names": CROSS_NAMES,
        "counts": counts,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[npzv4_dual] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
