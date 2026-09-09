"""Exact fill geometry of holefix2 vs _ext: a cell (row, symbol) is a FILL iff any channel finite in holefix2 and all channels NaN in _ext.
Also re-asserts that no cell finite in _ext changed value (the two holefix rounds receipted this; here it is the same statement on the
final canonical cache in one pass). Output feeds the PREREG v4 §2 step-1/2 'hole neighbourhood' gates: intervals [run_start-48, run_end+8640] rows."""
import numpy as np, time, json
t0 = time.time()
def load(p):
    Z = np.load(p); d = Z["data"]; return Z["ts"].astype(np.int64), Z["symbols"], d
ts, syms, dH = load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"); print(f"holefix2 loaded {dH.shape} {time.time()-t0:.0f}s", flush=True)
finH = np.isfinite(dH).any(2)
ts2, syms2, dE = load("/workspace/data/dlnative_5m_wide829_f16_ext.npz"); print(f"ext loaded {dE.shape} {time.time()-t0:.0f}s", flush=True)
assert np.array_equal(ts, ts2) and np.array_equal(syms, syms2)
finE = np.isfinite(dE).any(2)
fill = finH & ~finE; lost = finE & ~finH
# value identity on pre-existing cells (all channels): compare where ext finite
same = 0; diff = 0; maxabs = 0.0
for c in range(dH.shape[2]):
    a = dH[:, :, c]; b = dE[:, :, c]; ok = np.isfinite(b)
    eq = (a[ok] == b[ok]); same += int(eq.sum()); diff += int((~eq).sum())
    if (~eq).any(): maxabs = max(maxabs, float(np.nanmax(np.abs(a[ok][~eq].astype(np.float32) - b[ok][~eq].astype(np.float32)))))
print(f"pre-existing cells (all ch): equal {same} / differing {diff} maxabs {maxabs:.3e}", flush=True)
rows, cols = np.nonzero(fill); print(f"fill cells {len(rows)} lost cells {int(lost.sum())}", flush=True)
# runs of rows that contain any fill -> intervals
anyrow = fill.any(1); idx = np.nonzero(anyrow)[0]
runs = []; 
if len(idx):
    s = idx[0]; p = idx[0]
    for r in idx[1:]:
        if r > p + 288: runs.append((int(s), int(p))); s = r     # gap > 1 day starts a new run
        p = r
    runs.append((int(s), int(p)))
def d(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
per = []
for a, b in runs:
    sub = fill[a:b+1]; sy = np.nonzero(sub.any(0))[0]
    per.append({"row_start": a, "row_end": b, "ts_start": d(ts[a]), "ts_end": d(ts[b]), "n_cells": int(sub.sum()), "n_symbols": int(len(sy)), "symbols": [str(syms[j]) for j in sy]})
    print(f"run rows [{a},{b}] {d(ts[a])} .. {d(ts[b])} cells {int(sub.sum())} symbols {len(sy)}", flush=True)
ivals = np.array([[max(a - 48, 0), b + 8640] for a, b in runs], np.int64)
np.savez("/workspace/review_scratch/holefix2_cells.npz", row=rows.astype(np.int32), col=cols.astype(np.int32), ts=ts[rows], fill_runs=np.array(runs, np.int64), neigh_rows=ivals, symbols=syms,
         lost_rows=np.nonzero(lost)[0].astype(np.int32), lost_cols=np.nonzero(lost)[1].astype(np.int32))
json.dump({"n_fill": int(len(rows)), "n_lost": int(lost.sum()), "preexisting_equal": same, "preexisting_diff": diff, "maxabs": maxabs, "runs": per, "neigh_rows_rule": "[run_start-48, run_end+8640]"}, open("/workspace/review_scratch/holefix2_cells.json", "w"), indent=1)
print("HOLE_CELLS_DONE", f"{time.time()-t0:.0f}s", flush=True)
