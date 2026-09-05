"""build_composite.py — replay input for AMENDMENT 1(b): F10 walk-forward predictions with the 2026 year COVERED by the new fold.
composite[row < first 2026 anchor] = old-generation walk-forward folds 2023/2024/2025 (bitwise the health_check FPRED input, NaN-padded to the ext grid);
composite[2026 rows] = the new 2026 fold (this campaign). Also the same composite with the 09-01 ext-run 2026 fold (context), and a bitwise check of the
new 2026 rows against the 09-01 ext-run rows. Writes only under review_scratch/v2main_fold2026/preds/."""
import numpy as np, hashlib, json, time
ROOT = "/workspace/review_scratch/v2main_fold2026"
TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = TE["E_ts"].astype(np.int64); yrs = TE["yrs"].astype(int); nA = len(E)
first_te = int(np.where(yrs == 2026)[0][0]); assert first_te == 8754
def sha16(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
rep = {"first_te": first_te, "first_test_E_ts": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(E[first_te]))), "seeds": {}}
for s in (42, 2027):
    old = np.load(f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{s}.npy"); new = np.load(f"{ROOT}/preds/f10_V2MAIN_ext2026_s{s}.npy"); e01 = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{s}.npy")
    assert old.shape == (10086, 829) and new.shape == (nA, 829) and e01.shape == (nA, 829)
    assert np.isnan(new[:first_te]).all(), "new fold file must be NaN before 2026"
    assert np.isfinite(new[first_te:]).any(1).all(), "new fold rows must all be finite"
    comp = np.full((nA, 829), np.nan, np.float32); comp[:10086] = old; comp[first_te:] = new[first_te:]
    comp01 = np.full((nA, 829), np.nan, np.float32); comp01[:10086] = old; comp01[first_te:] = e01[first_te:]
    pc = f"{ROOT}/preds/f10_V2MAIN_ext2026comp_s{s}.npy"; p01 = f"{ROOT}/preds/f10_V2MAIN_ext0901comp_s{s}.npy"; np.save(pc, comp); np.save(p01, comp01)
    C = np.load(pc); assert np.array_equal(np.nan_to_num(C[:first_te], nan=-9), np.nan_to_num(old[:first_te], nan=-9)) and np.array_equal(np.nan_to_num(C[first_te:], nan=-9), np.nan_to_num(new[first_te:], nan=-9))
    eq26 = bool(np.array_equal(np.nan_to_num(new[first_te:], nan=-9), np.nan_to_num(e01[first_te:], nan=-9)))
    d26 = np.nan_to_num(new[first_te:], nan=0) - np.nan_to_num(e01[first_te:], nan=0)
    rep["seeds"][str(s)] = {"composite": pc, "composite_sha16": sha16(pc), "composite0901": p01, "composite0901_sha16": sha16(p01), "old_sha16": sha16(f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{s}.npy"), "new_sha16": sha16(f"{ROOT}/preds/f10_V2MAIN_ext2026_s{s}.npy"),
                            "rows_from_old": first_te, "rows_from_new": int(nA - first_te), "old_finite_rows_used": int(np.isfinite(old[:first_te]).any(1).sum()),
                            "new_vs_ext0901_2026_rows_bitwise_equal": eq26, "new_vs_ext0901_2026_max_abs_diff": float(np.abs(d26).max()), "new_vs_ext0901_2026_n_cells_diff": int((np.abs(d26) > 0).sum()), "n_cells_finite_2026": int(np.isfinite(new[first_te:]).sum())}
    print(s, json.dumps(rep["seeds"][str(s)]))
json.dump(rep, open(f"{ROOT}/results/composite.json", "w"), indent=1)
