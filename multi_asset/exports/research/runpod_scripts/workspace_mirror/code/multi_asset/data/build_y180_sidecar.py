"""y_180 SIDECAR overlay for npz_v2arch (mh180 arm, Stage-3 opportunity).

Builds the leak-free 180s forward perp log-return per window, aligned ROW-FOR-ROW to
the npz_v2arch cache timestamps, into an OVERLAY dir ``data/npz_v2arch_y180/`` (source
cache is READ-ONLY). Reuses the SAME re-anchor math as build_perp_y_clean
(``reanchor_y600`` with horizon=180): y_180 = log(perp_mid[s+180] / perp_mid[s]) at the
window prediction second s (= feature cutoff), from mid_cache perp_mid. Strictly causal.

Per-day OUT npz keys:
  y_180      (N,) f32   re-anchored 180s perp fwd log-return; 0 where invalid
  y_mask_180 (N,) uint8 valid iff the base window is valid (npz_v2arch y_mask_600)
             AND both 180s legs present
  timestamps (N,) i64   VERBATIM npz_v2arch timestamps (for the loader alignment assert)

The DualLOBDataset merges this via ``y180_sidecar_dir`` -> multi-horizon (y_180, y_600),
primary = y_600 (last). Note: y_mask_180 ⊆ y_mask_600 by construction (aligned aux mask;
loses the ~0.6% cross-day-tail rows where the 600s leg is absent — negligible for an aux).

Run on SERVER (needs npz_v2arch + mid_cache):
  PYTHONPATH=. python multi_asset/data/build_y180_sidecar.py --start 2023-08-19 --end 2026-02-06 --procs 8
"""
from __future__ import annotations
import argparse, os, os.path as p, time, datetime as dt
from concurrent.futures import ProcessPoolExecutor
import numpy as np

from multi_asset.data.build_perp_y_clean import reanchor_y600, _stitched_grid

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
SRC_DIR = p.join(_REPO, "data", "npz_v2arch")     # timestamps + base mask (READ)
OUT_DIR = p.join(_REPO, "data", "npz_v2arch_y180")
HORIZON = 180


def build_one_day(day: str, out_path: str) -> dict:
    t0 = time.time()
    src = p.join(SRC_DIR, "%s.npz" % day)
    if not p.exists(src):
        raise FileNotFoundError("npz_v2arch missing: %s" % src)
    with np.load(src, allow_pickle=True) as z:
        ts = z["timestamps"].astype(np.int64)
        base_mask = z["y_mask_600"].astype(bool)   # base window validity (& 600-leg)
    sec, perp_mid = _stitched_grid(day)             # today (+ next day stitched)
    y180, leg_valid = reanchor_y600(ts, sec, perp_mid, horizon=HORIZON)
    y_mask = (base_mask & leg_valid).astype(np.uint8)
    y_180 = np.where(y_mask == 0, 0.0, y180).astype(np.float32)
    assert ts.shape[0] == y_180.shape[0] == y_mask.shape[0]

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(tmp, y_180=y_180, y_mask_180=y_mask, timestamps=ts)
    os.replace(tmp, out_path)
    yv = y180[y_mask.astype(bool)]
    return {"N": int(ts.shape[0]), "n_valid": int(y_mask.sum()),
            "y_bps_std": float(np.std(yv) * 1e4) if yv.size else float("nan"),
            "secs": time.time() - t0, "mb": os.path.getsize(out_path) / 1e6}


def _days_in_range(start: str, end: str) -> list[str]:
    present = {f[:-4] for f in os.listdir(SRC_DIR) if f.endswith(".npz") and f[0].isdigit()}
    s = dt.date.fromisoformat(start); e = dt.date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        if d.isoformat() in present:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _worker(args):
    day, force = args
    out = p.join(OUT_DIR, "%s.npz" % day)
    if (not force) and p.exists(out):
        return (day, "skip", None)
    try:
        return (day, "ok", build_one_day(day, out))
    except Exception as e:
        return (day, "fail", "%s: %s" % (type(e).__name__, e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.all:
        days = sorted(f[:-4] for f in os.listdir(SRC_DIR) if f.endswith(".npz") and f[0].isdigit())
    elif a.start and a.end:
        days = _days_in_range(a.start, a.end)
    else:
        ap.error("pass --all or --start/--end")
    os.makedirs(OUT_DIR, exist_ok=True)
    print("[y180] %d day(s) -> %s (procs=%d)" % (len(days), OUT_DIR, a.procs), flush=True)
    t0 = time.time(); n_ok = n_skip = n_fail = 0; fails = []
    with ProcessPoolExecutor(max_workers=a.procs) as ex:
        for i, (day, st, info) in enumerate(ex.map(_worker, [(d, a.force) for d in days])):
            if st == "ok":
                n_ok += 1
                if i % 100 == 0 or i == len(days) - 1:
                    print("  [%d/%d] %s N=%d valid=%d y_std=%.2fbps %.1fkB" % (
                        i + 1, len(days), day, info["N"], info["n_valid"],
                        info["y_bps_std"], info["mb"] * 1000), flush=True)
            elif st == "skip":
                n_skip += 1
            else:
                n_fail += 1; fails.append((day, info))
    print("[y180] DONE in %.1f min: ok=%d skip=%d fail=%d -> %s" % (
        (time.time() - t0) / 60, n_ok, n_skip, n_fail, OUT_DIR), flush=True)
    if fails:
        print("  FAILS:", fails[:10], flush=True)


if __name__ == "__main__":
    main()
