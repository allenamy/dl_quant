"""fea89 (f8_v4 vs f8_hf2) diffs OUTSIDE the hole neighbourhoods: magnitude (max/median |Δ| per column), time distribution (by month), distance
from the nearest fill run, and whether any diff precedes the first fill (would indicate nondeterminism rather than propagation)."""
import numpy as np, json, collections, time
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]
run_syms = [set(np.unique(H["col"][(H["row"] >= a) & (H["row"] <= b)]).tolist()) for (a, b) in RUNS]
def neigh_of(rows):
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
NW = 829; TG = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True); Er = TG["E_row"].astype(np.int64); Ets = TG["E_ts"].astype(np.int64)
Fa = np.load("/workspace/f8_v4/data/f8_fea89.npz", allow_pickle=True); Fb = np.load("/workspace/f8_hf2/data/f8_fea89.npz", allow_pickle=True); names = [str(x) for x in Fa["names"]]
ka = Fa["pair_a"].astype(np.int64) * NW + Fa["pair_s"].astype(np.int64); kb = Fb["pair_a"].astype(np.int64) * NW + Fb["pair_s"].astype(np.int64)
oa = np.argsort(ka, kind="stable"); ob = np.argsort(kb, kind="stable"); ka = ka[oa]; kb = kb[ob]; common = np.intersect1d(ka, kb); ia = oa[np.searchsorted(ka, common)]; ib = ob[np.searchsorted(kb, common)]
Xa = Fa["X"]; Xb = Fb["X"]
colmax = collections.defaultdict(float); colcnt = collections.Counter(); colabs = collections.defaultdict(list); months = collections.Counter(); anchors = set(); dist = []
first_fill = int(RUNS[0][0])
for s in range(0, len(common), 200000):
    a = Xa[ia[s:s+200000]]; b = Xb[ib[s:s+200000]]; na = np.isnan(a); nb = np.isnan(b); d = (na != nb) | (~na & ~nb & (a != b))
    keys = common[s:s+200000]; er = Er[keys // NW]; nn = neigh_of(er); out = (nn < 0) & d.any(1)
    for r in np.nonzero(out)[0]:
        e = int(er[r]); anchors.add(int(keys[r] // NW)); months[time.strftime("%Y-%m", time.gmtime(int(Ets[keys[r] // NW])))] += 1
        dist.append(min(abs(e - int(x)) for run in RUNS for x in run))
        for c in np.nonzero(d[r])[0]:
            dv = abs(float(a[r, c]) - float(b[r, c])) if (not na[r, c] and not nb[r, c]) else float("inf"); colcnt[names[c]] += 1; colmax[names[c]] = max(colmax[names[c]], dv); colabs[names[c]].append(dv)
res = {"outside_pairs": int(sum(colcnt.values()) and len(dist)), "n_anchors": len(anchors), "months": dict(sorted(months.items())), "dist_rows_min": int(min(dist)) if dist else None, "dist_rows_p50": float(np.median(dist)) if dist else None, "dist_rows_max": int(max(dist)) if dist else None,
       "any_before_first_fill": bool(any(Er[a_] < first_fill for a_ in anchors)),
       "columns": {k: {"n": colcnt[k], "max_abs": colmax[k], "median_abs": float(np.median([x for x in colabs[k] if np.isfinite(x)])) if any(np.isfinite(colabs[k])) else None, "n_nanpat": int(sum(1 for x in colabs[k] if not np.isfinite(x)))} for k in sorted(colcnt, key=lambda k: -colcnt[k])}}
print(json.dumps({k: v for k, v in res.items() if k != "columns"})); print("columns (top 25):"); 
for k in list(res["columns"])[:25]: print("  ", k, res["columns"][k])
al = sorted(anchors); print("anchor list (first 12 / last 6):", [time.strftime("%F %H:%MZ", time.gmtime(int(Ets[i]))) for i in al[:12]], [time.strftime("%F %H:%MZ", time.gmtime(int(Ets[i]))) for i in al[-6:]])
json.dump(res, open("/workspace/review_scratch/v4_gates/step1_diag2.json", "w"), indent=1); print("DIAG2_DONE")
