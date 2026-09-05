"""stage_preds.py — Track B: convert an ext-grid preds file (nA=10206 rows, dlw_ext grid) to the replay input (0822 grid = first nB=10086 rows; prefix
identity asserted) under replay/dev_alt/f8_2026-08-22/preds/<out name>. Prints sha256 of source and staged file.  usage: stage_preds.py <src.npy> <out_name>"""
import sys, hashlib, numpy as np
src, out = sys.argv[1], sys.argv[2]
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64); Bt = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
nA, nB = len(A), len(Bt); assert np.array_equal(A[:nB], Bt)
P = np.load(src); assert P.shape == (nA, 829), P.shape
Q = np.ascontiguousarray(P[:nB]); dst = f"/workspace/review_scratch/allweather_trackB/replay/dev_alt/f8_2026-08-22/preds/{out}"; np.save(dst, Q)
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
print(f"STAGED {out} <- {src} src_sha {sh(src)[:16]} staged_sha {sh(dst)[:16]} finite_rows_dropped_beyond_nB {int(np.isfinite(P[nB:]).any(1).sum())} finite_rows_kept {int(np.isfinite(Q).any(1).sum())}")
