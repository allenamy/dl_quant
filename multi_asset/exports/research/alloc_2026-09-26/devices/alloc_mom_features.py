#!/usr/bin/env python3
"""alloc_mom_features.py — family M (DECISION_RULE_combination_layer §8) input: past 1 / 3 / 7 day log returns per name at every anchor.
ZERO book returns: reads only the engine's own 5-minute RAW log-price table (price_full_raw_x0918r.npy, the certified run's price
source) and the legs.npz anchor/symbol axis. Causal: mom_k(A) = lp[A] - lp[A - k*86400], both grid points at or before the anchor A
(the decision is at A + 24 min). NaN when either price is missing or the grid does not reach back. No ranks here (ranks are taken
within each anchor's member set by the arm itself).
Output: npz {E_ts (n,), symbols (829,), mom (n, 829, 3) float64 for k = 1, 3, 7} + a receipt with coverage counts.
usage: /workspace/venv/bin/python -B alloc_mom_features.py <out.npz>
"""
import os, sys, json, hashlib, time
import numpy as np
PX = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PXM = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"
LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"; KS = (1, 3, 7)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    out = sys.argv[1]
    L = np.load(LEGS); a = L["E_ts"].astype(np.int64); syms = L["symbols"]
    m = np.load(PXM); grid = m["grid"].astype(np.int64); assert np.array_equal(m["symbols"], syms), "price table symbols != legs symbols"
    lp = np.load(PX, mmap_mode="r")
    mom = np.full((len(a), len(syms), len(KS)), np.nan)
    i_now = np.searchsorted(grid, a); ok_now = (i_now < len(grid)) & (grid[np.minimum(i_now, len(grid) - 1)] == a)
    for j, k in enumerate(KS):
        t0 = a - k * 86400; i0 = np.searchsorted(grid, t0); ok0 = (i0 < len(grid)) & (grid[np.minimum(i0, len(grid) - 1)] == t0)
        rows = np.flatnonzero(ok_now & ok0)
        mom[rows, :, j] = np.asarray(lp[i_now[rows]]) - np.asarray(lp[i0[rows]])
    rec = {"device": "alloc_mom_features.py", "self_sha256": sha(os.path.abspath(__file__)), "price_meta_sha256": sha(PXM), "legs_sha256": sha(LEGS),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ks_days": KS, "n_anchors": int(len(a)),
           "anchors_with_grid": {str(k): int(np.isfinite(mom[:, :, j]).any(1).sum()) for j, k in enumerate(KS)},
           "finite_cells": {str(k): int(np.isfinite(mom[:, :, j]).sum()) for j, k in enumerate(KS)}}
    np.savez(out + ".tmp.npz", E_ts=a, symbols=syms, mom=mom); os.replace(out + ".tmp.npz", out)
    z = np.load(out); assert np.array_equal(z["mom"], mom, equal_nan=True)
    rec["out"] = out; rec["out_sha256"] = sha(out)
    json.dump(rec, open(out + ".json", "w"), indent=1); assert json.load(open(out + ".json"))["out_sha256"] == rec["out_sha256"]
    print("ALLOC_MOM_FEATURES DONE", json.dumps(rec["anchors_with_grid"]), rec["out_sha256"][:16], flush=True)


if __name__ == "__main__":
    main()
