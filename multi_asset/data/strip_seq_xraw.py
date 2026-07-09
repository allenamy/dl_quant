"""ENOSPC recovery (2026-07-09): strip the (S,T,5,4) raw-LOB `Xraw` array from the
NEW extension seq_cache day-files to free disk, WITHOUT touching the original
production window.

Context: the M0 full-history walk-forward replay extended seq_cache back to
2022-01, which filled /mnt/storage (4 TB, 100%). Xraw is 96.1 MB of each 314 MB
day-file. The M0 milestone-0 replay reads only F/y/mask/ts (`want_raw=False` in
seq_panel_dataset.iter_days); np.load is lazy per-key, so a missing Xraw key is a
no-op for it. The ONLY consumer of seq_cache Xraw is train_panel_regarch.py
(P1raw dual-path via iter_days_raw), whose frozen outputs are intact and whose
inputs are rebuildable from the read-only Tardis source.

Safety:
  * CUTOFF guard — strip ONLY day < 20240601. The original production window
    (20240601..20250930, 487 days, referenced by m0_on_h3600cl / stage2b_kheads /
    all R1 artifacts) KEEPS its Xraw.
  * Idempotent — skip files that no longer have an Xraw key.
  * Atomic — write <day>.npz.tmp, verify it loads (F shape + no Xraw), then
    os.replace over the original. A crash leaves the original intact.

Usage: PYTHONPATH=. python multi_asset/data/strip_seq_xraw.py [--cutoff 20240601]
"""
from __future__ import annotations

import argparse
import glob
import os
import os.path as p
import sys
import time

import numpy as np

SEQ_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/seq_cache")
KEEP_KEYS = ("F", "y", "mask", "ts", "feat_names")


def strip(cutoff: int):
    fs = sorted(glob.glob(p.join(SEQ_DIR, "*.npz")))
    print(f"[strip] {len(fs)} files; cutoff day<{cutoff} (>= keeps Xraw)", flush=True)
    t0 = time.time()
    n_strip = n_keep = n_already = n_fail = 0
    freed = 0
    for f in fs:
        base = p.basename(f)
        try:
            day = int(base[:8])
        except ValueError:
            continue
        if day >= cutoff:
            n_keep += 1
            continue
        try:
            z = np.load(f, allow_pickle=True)
            keys = set(z.files)
        except Exception as e:
            n_fail += 1
            print(f"  [FAIL-load] {base}: {e!r}", flush=True)
            continue
        if "Xraw" not in keys:
            n_already += 1
            z.close()
            continue
        sz_before = os.path.getsize(f)
        out = {k: z[k] for k in KEEP_KEYS if k in keys}
        z.close()
        # np.savez APPENDS .npz to the path it's given, so passing f+".tmp"
        # actually writes f+".tmp.npz" — track that real path for verify+replace.
        tmp_base = f + ".tmp"
        tmp = tmp_base + ".npz"
        try:
            np.savez(tmp_base, **out)
            # verify temp before replacing the original
            zt = np.load(tmp, allow_pickle=True)
            assert zt["F"].shape[0] == 14 and zt["F"].shape[2] == 44, "bad F"
            assert "Xraw" not in zt.files, "temp still has Xraw"
            _ = zt["y"].shape, zt["mask"].shape, zt["ts"].shape
            zt.close()
        except Exception as e:
            n_fail += 1
            if p.exists(tmp):
                os.remove(tmp)
            print(f"  [FAIL-write] {base}: {e!r} (original intact)", flush=True)
            continue
        os.replace(tmp, f)              # atomic; frees Xraw bytes
        freed += sz_before - os.path.getsize(f)
        n_strip += 1
        if n_strip % 50 == 0:
            el = time.time() - t0
            print(f"  [{n_strip} stripped] freed={freed/1e9:.1f} GB "
                  f"{el/60:.1f} min (last {base})", flush=True)
    print(f"[strip] done in {(time.time()-t0)/60:.1f} min: stripped={n_strip} "
          f"kept(>=cutoff)={n_keep} already-stripped={n_already} fail={n_fail} "
          f"freed={freed/1e9:.1f} GB", flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", type=int, default=20240601,
                    help="strip Xraw from files with day < cutoff (default "
                         "20240601 = start of the original 487-day window)")
    args = ap.parse_args()
    sys.exit(1 if strip(args.cutoff) else 0)
