"""fea82_diff_by_year.py — where in time do the OLD-vs-EXT fea82 differences sit (share of differing cells by anchor year, key-aligned rows), and the same for the
2026-fold TRAINING rows (anchors < 2026) vs the 2026 SCORING rows."""
import numpy as np, json
FO = np.load("/workspace/data/dlw_fea82.npz", allow_pickle=True); FE = np.load("/workspace/dlw_ext/data/dlw_fea82.npz", allow_pickle=True)
pa_o = FO["pair_a"].astype(np.int64); pa_e = FE["pair_a"].astype(np.int64)
ko = pa_o * 829 + FO["pair_s"].astype(np.int64); ke = pa_e * 829 + FE["pair_s"].astype(np.int64); _, io, ie = np.intersect1d(ko, ke, return_indices=True)
A = np.asarray(FO["X"][io], np.float32); B = np.asarray(FE["X"][ie], np.float32); D = np.abs(A - B); D[~(np.isfinite(A) & np.isfinite(B))] = 0
TG = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); yrs = TG["yrs"].astype(int); ya = yrs[pa_o[io]]
out = {"fea82_diff_share_by_year": {int(y): round(float((D[ya == y] > 0).mean()), 6) for y in np.unique(ya)},
       "fea82_diff_cells_by_year": {int(y): int((D[ya == y] > 0).sum()) for y in np.unique(ya)},
       "fea82_max_abs_by_year": {int(y): float(D[ya == y].max()) for y in np.unique(ya)},
       "fea82_cols_80_81_diff_share_pre2026": round(float((D[ya < 2026][:, 80:82] > 0).mean()), 6), "fea82_pre2026_rows_with_diff": int((D[ya < 2026] > 0).any(1).sum()), "fea82_pre2026_rows": int((ya < 2026).sum())}
json.dump(out, open("/workspace/review_scratch/v2main_fold2026/results/fea82_diff_by_year.json", "w"), indent=1); print(json.dumps(out, indent=1))
