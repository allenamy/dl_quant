"""Diagnose step-2 'val_sym_bad': value-column diffs (v4 vs v2ext_clamp) on symbols that are not filled symbols of the run. Classify by run,
column, NaN-pattern vs finite-finite, and whether the symbol's membership changed at that anchor."""
import numpy as np, json, time, collections
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]
run_syms = [set(np.unique(H["col"][(H["row"] >= a) & (H["row"] <= b)]).tolist()) for (a, b) in RUNS]
def neigh_of(rows):
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
CTS = np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")["ts"].astype(np.int64)
M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); ME = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); EE = ME["E_ts"].astype(np.int64); COMMON = np.intersect1d(E4, EE); I4 = np.searchsorted(E4, COMMON); IE = np.searchsorted(EE, COMMON)
Erow = np.searchsorted(CTS, COMMON); nn = neigh_of(Erow); names = [str(x) for x in M4["names"]]; isrank = np.array([n.endswith("_r") for n in names]); vcols = np.nonzero(~isrank)[0]
F4 = np.load("/workspace/data/wide_fea_v4.npy", mmap_mode="r"); FC = np.load("/workspace/data/wide_fea_v2ext_clamp.npy", mmap_mode="r")
syms = [str(s) for s in H["symbols"]]
cnt = collections.Counter(); colc = collections.Counter(); ex = []; membchg = 0; finfin = 0; nanpat = 0; tot = 0
for k in range(len(COMMON)):
    if nn[k] < 0: continue
    a = np.asarray(F4[I4[k]]); c = np.asarray(FC[IE[k]]); na = np.isnan(a); nc = np.isnan(c); d = (na != nc) | (~na & ~nc & (a != c))
    dv = d[:, vcols]; rows = np.nonzero(dv.any(1))[0]
    m4 = set(M4["members"][I4[k]].tolist()); me = set(ME["members"][IE[k]].tolist())
    for s in rows:
        if int(s) in run_syms[nn[k]]: continue
        tot += 1; mc = (int(s) in m4) != (int(s) in me); membchg += mc
        cols = vcols[dv[s]]; pat = "nanpat" if (na[s, cols] != nc[s, cols]).any() else "finfin"
        if pat == "finfin": finfin += 1
        else: nanpat += 1
        cnt[(int(nn[k]), pat, "memb_changed" if mc else "memb_same")] += 1
        for cc in cols: colc[names[cc]] += 1
        if len(ex) < 12 and not mc and pat == "finfin": ex.append({"anchor": time.strftime("%F %H:%MZ", time.gmtime(int(COMMON[k]))), "symbol": syms[s], "cols": [names[cc] for cc in cols][:8], "v4": [float(a[s, cc]) for cc in cols][:4], "clamp": [float(c[s, cc]) for cc in cols][:4]})
print("total non-filled-symbol value diffs", tot, "| membership changed", membchg, "| finite-finite", finfin, "| nan-pattern", nanpat)
print("by (run, pattern, membership):", dict(cnt)); print("by column:", colc.most_common(30)); print("examples (finite-finite, membership same):", json.dumps(ex, indent=0)[:3000])
json.dump({"total": tot, "membership_changed": membchg, "finfin": finfin, "nanpat": nanpat, "by_class": {str(k): v for k, v in cnt.items()}, "by_column": dict(colc), "examples": ex}, open("/workspace/review_scratch/v4_gates/step2_diag.json", "w"), indent=1)
