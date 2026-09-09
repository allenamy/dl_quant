"""Diagnose step-1 feature-gate value-column diffs on non-filled symbols (f8 fea89 f8_v4 vs f8_hf2; fea82 for completeness): by column, NaN-pattern vs finite-finite, run."""
import numpy as np, json, collections, sys
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]
run_syms = [set(np.unique(H["col"][(H["row"] >= a) & (H["row"] <= b)]).tolist()) for (a, b) in RUNS]
def neigh_of(rows):
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
NW = 829; Er = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True)["E_row"].astype(np.int64)
def diag(pa, pb, tag):
    Fa = np.load(pa, allow_pickle=True); Fb = np.load(pb, allow_pickle=True); names = [str(x) for x in Fa["names"]]
    ka = Fa["pair_a"].astype(np.int64) * NW + Fa["pair_s"].astype(np.int64); kb = Fb["pair_a"].astype(np.int64) * NW + Fb["pair_s"].astype(np.int64)
    oa = np.argsort(ka, kind="stable"); ob = np.argsort(kb, kind="stable"); ka = ka[oa]; kb = kb[ob]; common = np.intersect1d(ka, kb); ia = oa[np.searchsorted(ka, common)]; ib = ob[np.searchsorted(kb, common)]
    Xa = Fa["X"]; Xb = Fb["X"]; colc = collections.Counter(); pat = collections.Counter(); byrun = collections.Counter(); ex = []
    for s in range(0, len(common), 200000):
        a = Xa[ia[s:s+200000]]; b = Xb[ib[s:s+200000]]; na = np.isnan(a); nb = np.isnan(b); d = (na != nb) | (~na & ~nb & (a != b))
        rows = np.nonzero(d.any(1))[0]
        if not len(rows): continue
        keys = common[s:s+200000][rows]; er = Er[keys // NW]; sy = keys % NW; nn = neigh_of(er)
        for r, e, y, n in zip(rows, er, sy, nn):
            if n >= 0 and int(y) in run_syms[n]: continue
            cols = np.nonzero(d[r])[0]; nanp = bool((na[r, cols] != nb[r, cols]).any()); ff = bool((~na[r, cols] & ~nb[r, cols] & (a[r, cols] != b[r, cols])).any())
            pat["nanpat" if nanp and not ff else ("finfin" if ff and not nanp else "mixed")] += 1; byrun[int(n)] += 1
            for c in cols: colc[names[c]] += 1
            if ff and len(ex) < 6: ex.append({"anchor_row": int(e), "symbol": int(y), "cols": [names[c] for c in cols][:6], "a": [float(a[r, c]) for c in cols][:3], "b": [float(b[r, c]) for c in cols][:3]})
    res = {"non_filled_diff_pairs": sum(pat.values()), "pattern": dict(pat), "by_run": {str(k): v for k, v in byrun.items()}, "by_column": colc.most_common(40), "examples_finfin": ex}
    print(tag, json.dumps(res)[:3000], flush=True); return res
out = {"fea89": diag("/workspace/f8_v4/data/f8_fea89.npz", "/workspace/f8_hf2/data/f8_fea89.npz", "fea89:"), "fea82": diag("/workspace/dlw_hf3/data/dlw_fea82.npz", "/workspace/dlw_hf2/data/dlw_fea82.npz", "fea82:")}
json.dump(out, open("/workspace/review_scratch/v4_gates/step1_diag.json", "w"), indent=1); print("DIAG_DONE")
