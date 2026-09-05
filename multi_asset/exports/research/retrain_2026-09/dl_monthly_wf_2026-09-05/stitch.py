"""stitch.py — dl_monthly_wf: build the replay-grid prediction files from the trainer's stitched ext-grid file and print coverage receipts.
ext grid  = /workspace/dlw_ext/data/dlw_targets.npz (10206 anchors, 2022-01-03 00Z → 2026-08-30 20Z) — the monthly files live here.
0822 grid = /workspace/data/dlw_targets.npz (10086 anchors, → 2026-08-10 20Z) = the replay device's F10 alignment grid (dlw_2026-08-22/data/dlw_targets.npz);
            E_ts prefix-identical and symbols identical (asserted) ⇒ projection = first 10086 rows.
Outputs (written to replay/dev/ and replay/dev_alt/ f8_2026-08-22/preds/, real directories):
  f10_V2MAIN_{TAG}_s42.npy      pure monthly (NaN before 2025-01-01) on the 0822 grid          — lead's literal FPRED spec; sensitivity arm
  f10_V2MAIN_{TAG}spl_s42.npy   spliced: yearly-fold rows < 2025-01-01, monthly rows >= 2025-01-01 — identical book state entering 2025-01; primary arm
usage: stitch.py <TAG> [<TAG>...]   (TAG = mE60 | mE1)"""
import sys, os, json, time, hashlib, calendar
import numpy as np
R = "/workspace/review_scratch/dl_monthly_wf"; YEARLY = "/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); B = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)
Ea = A["E_ts"].astype(np.int64); Eb = B["E_ts"].astype(np.int64); nB = len(Eb)
assert np.array_equal(Ea[:nB], Eb) and [str(s) for s in A["symbols"]] == [str(s) for s in B["symbols"]]
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); assert Ea[i25] == T25
Y = np.load(YEARLY); assert Y.shape == (nB, 829), Y.shape
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea])
out = {"yearly": {"path": YEARLY, "sha256": sha(YEARLY), "finite_rows": int(np.isfinite(Y).any(1).sum()), "first_finite": iso(Eb[np.where(np.isfinite(Y).any(1))[0][0]]), "last_finite": iso(Eb[np.where(np.isfinite(Y).any(1))[0][-1]])}}
for TAG in sys.argv[1:]:
    src = f"{R}/preds/f10_V2MAIN_{TAG}_s42.npy"; P = np.load(src); assert P.shape == (len(Ea), 829), P.shape
    fin = np.isfinite(P).any(1)
    assert int(np.isfinite(P[:i25]).sum()) == 0, "pre-2025 rows must be NaN in the pure monthly file"
    cov = {int(m): int(fin[ym == m].sum()) for m in sorted(set(ym[ym >= 202501].tolist()))}
    expect = {int(m): int((ym == m).sum()) for m in cov}
    # rows with <50 member rows are legitimately NaN in every file (trainer skips them); count them from the yearly file on the overlap
    pure = P[:nB].copy(); spl = Y.copy(); spl[i25:] = pure[i25:]
    assert np.array_equal(spl[:i25], Y[:i25], equal_nan=True) and np.array_equal(spl[i25:], pure[i25:], equal_nan=True)
    ovl = slice(i25, nB); mask_eq = np.array_equal(np.isfinite(pure[ovl]), np.isfinite(Y[ovl]))
    rows_diff = int((np.isfinite(pure[ovl]).any(1) != np.isfinite(Y[ovl]).any(1)).sum()); cells_diff = int((np.isfinite(pure[ovl]) != np.isfinite(Y[ovl])).sum())
    rec = {"src": src, "src_sha256": sha(src), "finite_rows_ext": int(fin.sum()), "first_finite": iso(Ea[np.where(fin)[0][0]]) if fin.any() else None, "last_finite": iso(Ea[np.where(fin)[0][-1]]) if fin.any() else None,
           "coverage_by_month": {str(m): f"{cov[m]}/{expect[m]}" for m in cov}, "pre2025_finite_cells": 0, "overlap_2025_to_0810_finite_mask_equal_to_yearly": mask_eq, "overlap_rows_with_mask_diff": rows_diff, "overlap_cells_with_mask_diff": cells_diff, "outputs": {}}
    for v in ("dev", "dev_alt"):
        d = f"{R}/replay/{v}/f8_2026-08-22/preds"; os.makedirs(d, exist_ok=True)
        p1 = f"{d}/f10_V2MAIN_{TAG}_s42.npy"; p2 = f"{d}/f10_V2MAIN_{TAG}spl_s42.npy"
        np.save(p1, pure.astype(np.float32)); np.save(p2, spl.astype(np.float32)); rec["outputs"][v] = {os.path.basename(p1): sha(p1), os.path.basename(p2): sha(p2)}
    out[TAG] = rec
    print(f"{TAG}: finite rows {fin.sum()} {rec['first_finite']} → {rec['last_finite']}; coverage {rec['coverage_by_month']}; overlap mask==yearly {mask_eq} (rows diff {rows_diff}, cells diff {cells_diff}); pre-2025 finite 0 OK", flush=True)
json.dump(out, open(f"{R}/logs/stitch_{'_'.join(sys.argv[1:])}.json", "w"), indent=1)
print("STITCH_DONE", flush=True)
