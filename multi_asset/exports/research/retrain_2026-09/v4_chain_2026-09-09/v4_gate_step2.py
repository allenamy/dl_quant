"""PREREG_v4 section 2 step 2 gates (king side).
 wide_fea_v4 (holefix2 + clamp) vs wide_fea_v2ext_clamp (_ext + clamp): differing anchors only inside hole neighbourhoods; value-col diffs only for filled symbols.
 wide_fea_v4 vs wide_fea_v2ext (_ext, unclamped): differing anchors ⊆ first-138 (E_row < 8640, E-0909-A) ∪ hole neighbourhoods.
 meta: E_ts bitwise = v2ext meta; members / y4 / qvk differences only inside hole neighbourhoods (y4/qvk symbols ⊆ filled)."""
import numpy as np, json, time, os
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]
run_syms = [set(np.unique(H["col"][(H["row"] >= a) & (H["row"] <= b)]).tolist()) for (a, b) in RUNS]
def neigh_of(rows):
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
CTS = np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")["ts"].astype(np.int64)
M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); ME = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); EE = ME["E_ts"].astype(np.int64); R = {"E_ts_equal": bool(np.array_equal(E4, EE)), "nA_v4": int(len(E4)), "nA_v2ext": int(len(EE))}
# axis: v4 may carry extra anchors (hole fills at the tail make anchors pass the member filter); extra anchors must lie inside a hole neighbourhood
COMMON = np.intersect1d(E4, EE); I4 = np.searchsorted(E4, COMMON); IE = np.searchsorted(EE, COMMON); assert np.array_equal(E4[I4], COMMON) and np.array_equal(EE[IE], COMMON)
def rows_of(E): r = np.searchsorted(CTS, E); assert np.array_equal(CTS[r], E); return r
x4 = np.setdiff1d(E4, EE); xE = np.setdiff1d(EE, E4)
R["anchors_only_v4"] = [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t))) for t in x4]; R["anchors_only_v2ext"] = [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t))) for t in xE]
R["anchors_only_v4_outside_neigh"] = int((neigh_of(rows_of(x4)) < 0).sum()) if len(x4) else 0; R["anchors_only_v2ext_outside_neigh"] = int((neigh_of(rows_of(xE)) < 0).sum()) if len(xE) else 0
Erow = rows_of(COMMON); nn = neigh_of(Erow); f138 = Erow < 8640; R["n_first138"] = int(f138.sum()); R["n_common"] = int(len(COMMON))
names = [str(x) for x in M4["names"]]; isrank = np.array([n.endswith("_r") for n in names]); R["cols_not_v_or_r"] = [n for n in names if not (n.endswith("_r") or n.endswith("_v"))]
assert names == [str(x) for x in ME["names"]]
M4m = M4["members"]; MEm = ME["members"]
F4 = np.load("/workspace/data/wide_fea_v4.npy", mmap_mode="r"); FC = np.load("/workspace/data/wide_fea_v2ext_clamp.npy", mmap_mode="r"); FE = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r")
assert F4.shape[1:] == FC.shape[1:] == FE.shape[1:] and F4.shape[0] == len(E4) and FC.shape[0] == len(EE) == FE.shape[0], (F4.shape, FC.shape, FE.shape)
nA = len(COMMON); NW, NF = F4.shape[1:]
def cmp(a, b):
    na = np.isnan(a); nb = np.isnan(b); return (na != nb) | (~na & ~nb & (a != b))
S = {"v4_vs_clamp": {"anchors": 0, "outside": 0, "val_pairs": 0, "val_sym_bad": 0, "val_sym_membership_nanpat": 0, "rank_pairs": 0}, "v4_vs_ext": {"anchors": 0, "outside_138_and_neigh": 0, "in_first138": 0},
     "clamp_vs_ext": {"anchors": 0, "outside_138": 0}}
CH = 128
for s in range(0, nA, CH):
    idx = np.arange(s, min(s + CH, nA)); a = np.asarray(F4[I4[idx]]); c = np.asarray(FC[IE[idx]]); e = np.asarray(FE[IE[idx]])
    d = cmp(a, c); da = d.any((1, 2))
    if da.any():
        S["v4_vs_clamp"]["anchors"] += int(da.sum()); S["v4_vs_clamp"]["outside"] += int((da & (nn[idx] < 0)).sum())
        dv = d[:, :, ~isrank].any(2); dr = d[:, :, isrank].any(2); S["v4_vs_clamp"]["val_pairs"] += int(dv.sum()); S["v4_vs_clamp"]["rank_pairs"] += int(dr.sum())
        r_, s_ = np.nonzero(dv); na = np.isnan(a); nc = np.isnan(c)
        for r, y in zip(r_, s_):   # AMENDMENT 1 item 3: non-filled symbols may differ only as NaN-pattern changes caused by a membership change (qvk ranking moved by the fill)
            if nn[idx[r]] >= 0 and int(y) in run_syms[nn[idx[r]]]: continue
            cols = np.nonzero(d[r, y][~isrank])[0]; vc = np.nonzero(~isrank)[0][cols]; nanpat = bool((na[r, y, vc] != nc[r, y, vc]).any())
            memb = (int(y) in set(M4m[I4[idx[r]]].tolist())) != (int(y) in set(MEm[IE[idx[r]]].tolist()))
            if nanpat and memb and not ((~na[r, y, vc] & ~nc[r, y, vc]) & (a[r, y, vc] != c[r, y, vc])).any(): S["v4_vs_clamp"]["val_sym_membership_nanpat"] += 1
            else: S["v4_vs_clamp"]["val_sym_bad"] += 1
    d2 = cmp(a, e).any((1, 2))
    S["v4_vs_ext"]["anchors"] += int(d2.sum()); S["v4_vs_ext"]["outside_138_and_neigh"] += int((d2 & ~f138[idx] & (nn[idx] < 0)).sum()); S["v4_vs_ext"]["in_first138"] += int((d2 & f138[idx]).sum())
    d3 = cmp(c, e).any((1, 2)); S["clamp_vs_ext"]["anchors"] += int(d3.sum()); S["clamp_vs_ext"]["outside_138"] += int((d3 & ~f138[idx]).sum())
    if s % 2048 == 0: log(f"{s}/{nA}", json.dumps(S))
R["features"] = S
# meta
mrows = np.array([not np.array_equal(M4m[i], MEm[j]) for i, j in zip(I4, IE)]); R["members_diff_rows"] = int(mrows.sum()); R["members_diff_rows_outside_neigh"] = int((mrows & (nn < 0)).sum())
for k in ("y4", "qvk"):
    a = M4[k][I4]; b = ME[k][IE]; d = cmp(a, b); r_, s_ = np.nonzero(d); R[f"{k}_diff_cells"] = int(d.sum()); R[f"{k}_diff_outside_neigh"] = int((nn[r_] < 0).sum())
    R[f"{k}_diff_symbol_not_filled"] = int(sum(1 for r, y in zip(r_, s_) if not (nn[r] >= 0 and int(y) in run_syms[nn[r]])))
R["PASS"] = bool(S["v4_vs_clamp"]["outside"] == 0 and S["v4_vs_clamp"]["val_sym_bad"] == 0 and S["v4_vs_ext"]["outside_138_and_neigh"] == 0 and S["clamp_vs_ext"]["outside_138"] == 0
                 and R["members_diff_rows_outside_neigh"] == 0 and all(R[f"{k}_diff_outside_neigh"] == 0 and R[f"{k}_diff_symbol_not_filled"] == 0 for k in ("y4", "qvk")) and R["n_first138"] == 138
                 and R["anchors_only_v4_outside_neigh"] == 0 and R["anchors_only_v2ext_outside_neigh"] == 0)
R["neigh_rows"] = NEIGH.tolist(); R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
os.makedirs("/workspace/review_scratch/v4_gates", exist_ok=True); json.dump(R, open("/workspace/review_scratch/v4_gates/step2.json", "w"), indent=1)
log("STEP2_GATE", "PASS" if R["PASS"] else "FAIL", json.dumps(R))
