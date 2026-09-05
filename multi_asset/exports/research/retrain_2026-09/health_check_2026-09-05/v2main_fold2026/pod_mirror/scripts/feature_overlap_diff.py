"""feature_overlap_diff.py — receipt for the 'data-generation difference' between the OLD generation (/workspace/data, 08-22, to 08-10) and the EXT generation
(/workspace/dlw_ext + /workspace/f8_ext, 09-01, to 08-30) on the overlapping rows (pair_a < 10086): cells differing, max|Δ|, per-column share of differing cells.
The 2026 walk-forward fold trains on anchors < 2026 only, i.e. entirely inside the overlap, so any old-vs-new fold difference must come from these cells
(plus GPU nondeterminism). Read-only."""
import numpy as np, json
FO = np.load("/workspace/data/dlw_fea82.npz", allow_pickle=True); FE = np.load("/workspace/dlw_ext/data/dlw_fea82.npz", allow_pickle=True)
pa_o = FO["pair_a"].astype(np.int64); pa_e = FE["pair_a"].astype(np.int64); n_o = len(pa_o)
out = {}
# rows are (anchor, symbol) pairs sorted by anchor; the member set differs at one overlap anchor (MANIFEST: 2026-01-15 08Z 400th seat ACXUSDT<->PROMPTUSDT qvk tie) -> align by key
ko = pa_o * 829 + FO["pair_s"].astype(np.int64); ke = pa_e * 829 + FE["pair_s"].astype(np.int64)
_, io, ie = np.intersect1d(ko, ke, return_indices=True)
out["row_alignment"] = {"old_rows": int(n_o), "ext_rows_in_overlap_anchors": int((pa_e < 10086).sum()), "matched_keys": int(len(io)), "old_rows_unmatched": int(n_o - len(io)), "ext_overlap_rows_unmatched": int((pa_e < 10086).sum() - len(io))}
print("row alignment", out["row_alignment"], flush=True)
def cmp(name, A, B):
    A = np.asarray(A, np.float32); B = np.asarray(B, np.float32); fa = np.isfinite(A); fb = np.isfinite(B)
    both = fa & fb; d = np.abs(A - B); d[~both] = 0
    nanmis = int((fa != fb).sum()); ndiff = int((d > 0).sum()); col_share = (d > 0).mean(0)
    rel = d / (np.abs(B) + 1e-6)
    r = {"rows": int(A.shape[0]), "cols": int(A.shape[1]), "cells": int(A.size), "nan_pattern_mismatch_cells": nanmis, "cells_diff_gt0": ndiff, "share_diff": round(ndiff / A.size, 6), "max_abs_diff": float(d.max()),
         "p99_abs_diff_of_differing": float(np.percentile(d[d > 0], 99)) if ndiff else 0.0, "median_rel_diff_of_differing": float(np.median(rel[d > 0])) if ndiff else 0.0,
         "cols_with_any_diff": int((col_share > 0).sum()), "top_cols_by_share": [(int(c), round(float(col_share[c]), 4), float(d[:, c].max())) for c in np.argsort(-col_share)[:8] if col_share[c] > 0],
         "rows_with_any_diff_share": round(float((d > 0).any(1).mean()), 6)}
    # by anchor-year of the differing cells
    return r
out["fea82"] = cmp("fea82", FO["X"][io], FE["X"][ie]); del FO, FE
GO = np.load("/workspace/data/f8_fea89.npz", allow_pickle=True); GE = np.load("/workspace/f8_ext/data/f8_fea89.npz", allow_pickle=True)
assert np.array_equal(GO["pair_a"].astype(np.int64), pa_o) and np.array_equal(GE["pair_a"].astype(np.int64), pa_e)
out["fea89"] = cmp("fea89", GO["X"][io], GE["X"][ie])
# where in time do the fea89 differences sit? (share of differing cells by anchor year)
TG = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); yrs = TG["yrs"].astype(int); ya = yrs[pa_o[io]]
A_ = np.asarray(GO["X"][io], np.float32); B_ = np.asarray(GE["X"][ie], np.float32); D = np.abs(A_ - B_); D[~(np.isfinite(A_) & np.isfinite(B_))] = 0
out["fea89_diff_share_by_year"] = {int(y): round(float((D[ya == y] > 0).mean()), 6) for y in np.unique(ya)}
json.dump(out, open("/workspace/review_scratch/v2main_fold2026/results/feature_overlap_diff.json", "w"), indent=1); print(json.dumps(out, indent=1))
