"""PREREG_v4 section 2 step 1 gates (DL side).
 A. dlw_v4raw (holefix2 + raw_patch) vs dlw_hf3 (holefix2, CLIP): axis/members/qvk/btcv/y4old/yrs/has_panel/symbols bitwise;
    y4s: every |diff| > 1e-6 lies in a patched accounting window (E_row+1 <= patched bar <= E_row+48); rest <= 1e-6 noise;
    YR4s/YRZ (row-level residual/rank): differing rows are rows that contain a patched cell.
 B. dlw_hf3 vs dlw_hf2 (holefix2 vs holefix) targets, fea82 (dlw_hf3 vs dlw_hf2), fea89 (f8_v4 vs f8_hf2): differences only inside the
    hole neighbourhoods [run_start-48, run_end+8640] from holefix2_cells.npz; value columns only for filled symbols; rank columns any symbol."""
# [M] MONTH-GENERIC (W7 2026-09-12, docs/PREREG_v4_gates_monthly_2026-09-12.md): every path comes from the month contract env (chain_lib.load_month_env exports it);
# [M] the reference is the PREVIOUS month's contract-pinned build (PREV_DLW_CLIP / PREV_F8, September = hf2 / f8_hf2); thresholds and statistics are the frozen ones verbatim;
# [M] anchors/pairs after the reference axis end are the extension tail (§3.4); a reference identical to the candidate is refused (§3.5); missing inputs are refused with a PASS=false receipt (§3.6).
import numpy as np, json, time, sys
t0 = time.time(); R = {}
import os   # [M]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize, sha256_file   # [M] refusal receipts go through finalize BEFORE any load
_OUT = os.environ.get("STEP1_OUT")   # [M] required, no September default
if not _OUT: print("STEP1_REFUSED missing STEP1_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)   # [M]
_KEYS = ("HOLE_CELLS", "DLW_RAW", "DLW_CLIP", "RAW_PATCH", "PREV_DLW_CLIP", "CACHE", "F8", "PREV_F8")   # [M] month contract keys this gate reads (PREREG §2)
_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]   # [M]
def _p(k, rel=""): return (_E[k] + rel) if _E[k] else None   # [M]
INPUTS = {"dlw_v4raw_targets": _p("DLW_RAW", "/data/dlw_targets.npz"), "dlw_hf3_targets": _p("DLW_CLIP", "/data/dlw_targets.npz"), "dlw_hf2_targets": _p("PREV_DLW_CLIP", "/data/dlw_targets.npz"),   # [M]
          "fea82_hf3": _p("DLW_CLIP", "/data/dlw_fea82.npz"), "fea82_hf2": _p("PREV_DLW_CLIP", "/data/dlw_fea82.npz"), "fea82_v4raw": _p("DLW_RAW", "/data/dlw_fea82.npz"),   # [M]
          "fea89_f8v4": _p("F8", "/data/f8_fea89.npz"), "fea89_f8hf2": _p("PREV_F8", "/data/f8_fea89.npz"), "raw_patch": _p("RAW_PATCH"), "hole_cells": _p("HOLE_CELLS"), "cache": _p("CACHE")}   # [M]
_missing_files = {k: v for k, v in INPUTS.items() if v is None or not os.path.isfile(v)}; _refused = {}   # [M]
if _missing_env: _refused["missing_env"] = _missing_env   # [M]
if _missing_files: _refused["missing_files"] = _missing_files   # [M]
if not _refused:   # [M] reference must not be the candidate (PREREG §3.5): a file compared with itself verifies nothing
    _sh = {}; _S = lambda k: _sh.setdefault(k, sha256_file(INPUTS[k]))   # [M]
    _same = [f"{a}=={b}" for a, b in (("dlw_hf3_targets", "dlw_hf2_targets"), ("fea82_hf3", "fea82_hf2"), ("fea89_f8v4", "fea89_f8hf2")) if _S(a) == _S(b)]   # [M]
    if _same: _refused["reference_is_candidate"] = _same   # [M]
if _refused: print("STEP1_REFUSED", json.dumps(_refused), flush=True); finalize("STEP1", {"PASS": False, "REFUSED": _refused}, _OUT, INPUTS)   # [M] rc 3; receipt PASS=false; missing shas None
H = np.load(INPUTS["hole_cells"], allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]; CSYM = H["symbols"]   # [M] $HOLE_CELLS
run_syms = []
for (a, b) in RUNS:
    sel = (H["row"] >= a) & (H["row"] <= b); run_syms.append(set(np.unique(H["col"][sel]).tolist()))
def neigh_of(rows):
    """index of the neighbourhood interval containing each cache row (-1 = outside)."""
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
def sym_ok(rowsn, cols):
    """value-column diffs: symbol must be a filled symbol of that neighbourhood's run."""
    return np.array([(n >= 0) and (int(c) in run_syms[n]) for n, c in zip(rowsn, cols)], bool)
def eq(a, b):
    if a.dtype == object: return len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))
    if a.dtype.kind in "fc": return a.shape == b.shape and np.array_equal(a, b, equal_nan=True)
    return np.array_equal(a, b)
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
# ---------- A ----------
A = np.load(INPUTS["dlw_v4raw_targets"], allow_pickle=True); B = np.load(INPUTS["dlw_hf3_targets"], allow_pickle=True)   # [M] $DLW_RAW / $DLW_CLIP (this month RAW vs CLIP)
assert np.array_equal(A["symbols"], CSYM) and np.array_equal(B["symbols"], CSYM)
RA = {k: eq(A[k], B[k]) for k in ("E_ts", "E_row", "members", "yrs", "has_panel", "symbols", "btcv", "qvk", "y4old")}
log("A bitwise:", RA)
E_row = A["E_row"].astype(np.int64); ya = A["y4s"]; yb = B["y4s"]; nA, NW = ya.shape
P = np.load(INPUTS["raw_patch"]); prow = P["row"].astype(np.int64); pcol = P["col"].astype(np.int64)   # [M] $RAW_PATCH
X = np.zeros((nA, NW), bool)
for t, c in zip(prow, pcol):
    lo = np.searchsorted(E_row, t - 48); hi = np.searchsorted(E_row, t - 1, side="right")   # E_row in [t-48, t-1]
    X[lo:hi, c] = True
fa = np.isfinite(ya); fb = np.isfinite(yb); RA["y4s_finite_pattern_equal"] = bool((fa == fb).all())
D = fa & fb & (ya != yb); dd = np.abs(ya.astype(np.float64) - yb.astype(np.float64)); big = D & (dd > 1e-6)
RA.update({"y4s_diff_cells": int(D.sum()), "y4s_big_cells": int(big.sum()), "y4s_big_outside_patch_windows": int((big & ~X).sum()),
           "y4s_noise_max_outside_patch": float(dd[D & ~X].max()) if (D & ~X).any() else 0.0, "patch_window_cells_finite": int((X & fa).sum()),
           "patch_window_cells_zero_diff": int((X & fa & ~D).sum()), "y4s_maxabs_in_patch": float(dd[big].max()) if big.any() else 0.0,
           "patch_anchors": int(X.any(1).sum()), "patch_symbols": int(X.any(0).sum())})
for k in ("YR4s", "YRZ"):
    a = A[k]; b = B[k]; fa_, fb_ = np.isfinite(a), np.isfinite(b); dd_ = np.abs(a.astype(np.float64) - b.astype(np.float64))
    d = (fa_ != fb_) | (fa_ & fb_ & (dd_ > 1e-6)); rows = d.any(1); xrows = X.any(1)   # same 1e-6 cumsum-noise band as y4s (PREREG step 1); YRZ is a rank -> exact
    RA[f"{k}_diff_rows"] = int(rows.sum()); RA[f"{k}_diff_rows_outside_patch_rows"] = int((rows & ~xrows).sum())
    RA[f"{k}_noise_max_outside_patch_rows"] = float(np.nanmax(np.where(fa_ & fb_ & ~xrows[:, None], dd_, 0.0)))
RA["PASS"] = bool(all(RA[k] for k in ("E_ts", "E_row", "members", "yrs", "has_panel", "symbols", "btcv", "qvk", "y4old", "y4s_finite_pattern_equal"))
                  and RA["y4s_big_outside_patch_windows"] == 0 and RA["y4s_noise_max_outside_patch"] <= 1e-6
                  and RA["YR4s_diff_rows_outside_patch_rows"] == 0 and RA["YRZ_diff_rows_outside_patch_rows"] == 0)
log("A:", json.dumps(RA)); R["A_raw_vs_clip"] = RA
# ---------- B targets ----------
C = np.load(INPUTS["dlw_hf2_targets"], allow_pickle=True); RB = {}   # [M] $PREV_DLW_CLIP = the PREVIOUS month's contract-pinned CLIP build (September: hf2)
Eb = B["E_ts"].astype(np.int64); Ec = C["E_ts"].astype(np.int64); RB["E_ts_equal"] = bool(np.array_equal(Eb, Ec)); RB["E_row_equal"] = bool(np.array_equal(B["E_row"], C["E_row"]))
if not RB["E_ts_equal"]:
    only_b = np.setdiff1d(Eb, Ec); only_c = np.setdiff1d(Ec, Eb); rb = (only_b - int(np.load(INPUTS["cache"])["ts"][0])) // 300   # [M] $CACHE
    _tail = only_b > int(Ec.max()); _out = neigh_of(rb) < 0   # [M] extension tail (PREREG §3.4): only-in-new anchors AFTER the reference axis end are this month's new data
    RB["axis_only_hf3"] = len(only_b); RB["axis_only_hf2"] = len(only_c); RB["axis_only_hf3_outside_neigh"] = int((_out & ~_tail).sum())   # [M] tail not counted
    if int((_out & _tail).sum()): RB["axis_only_hf3_tail_exempt"] = int((_out & _tail).sum()); RB["ref_axis_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(Ec.max())))   # [M] conditional: present iff the tail rule was load-bearing
ib = np.searchsorted(Eb, np.intersect1d(Eb, Ec)); ic = np.searchsorted(Ec, np.intersect1d(Eb, Ec)); Er = B["E_row"].astype(np.int64)[ib]; nb = neigh_of(Er)
Bm = B["members"]; Cm = C["members"]   # materialise once (NpzFile[key] inside a loop re-reads the pickled array every access)
mrows = np.array([not np.array_equal(Bm[i], Cm[j]) for i, j in zip(ib, ic)]); RB["members_diff_rows"] = int(mrows.sum()); RB["members_diff_rows_outside_neigh"] = int((mrows & (nb < 0)).sum())
for k, rowlevel in (("y4s", False), ("y4old", False), ("qvk", False), ("YR4s", True), ("YRZ", True)):
    a = B[k][ib]; c = C[k][ic]; fa_ = np.isfinite(a); fc_ = np.isfinite(c); d = (fa_ != fc_) | (fa_ & fc_ & (np.abs(a.astype(np.float64) - c.astype(np.float64)) > 1e-6))
    r_, s_ = np.nonzero(d); RB[f"{k}_diff_cells"] = int(d.sum()); RB[f"{k}_diff_outside_neigh"] = int((nb[r_] < 0).sum())
    if not rowlevel: RB[f"{k}_diff_symbol_not_filled"] = int((~sym_ok(nb[r_], s_)).sum())
    ex = fa_ & fc_ & (a != c) & ~d; RB[f"{k}_noise_cells_le_1e-6"] = int(ex.sum())
RB["PASS"] = bool(RB["members_diff_rows_outside_neigh"] == 0 and all(RB[f"{k}_diff_outside_neigh"] == 0 for k in ("y4s", "y4old", "qvk", "YR4s", "YRZ"))
                  and all(RB[f"{k}_diff_symbol_not_filled"] == 0 for k in ("y4s", "y4old", "qvk")) and (RB["E_ts_equal"] or RB.get("axis_only_hf3_outside_neigh", 1) == 0))
log("B targets:", json.dumps(RB)); R["B_targets_hf3_vs_hf2"] = RB
# ---------- B features ----------
def fea_gate(pa_, pb_, Erow_a, Erow_b, tag):
    Fa = np.load(pa_, allow_pickle=True); Fb = np.load(pb_, allow_pickle=True); names = [str(x) for x in Fa["names"]]; assert names == [str(x) for x in Fb["names"]]
    isrank = np.array([n.endswith("_r") for n in names]); other = [n for n in names if not (n.endswith("_r") or n.endswith("_v"))]
    ka = Fa["pair_a"].astype(np.int64) * NW + Fa["pair_s"].astype(np.int64); kb = Fb["pair_a"].astype(np.int64) * NW + Fb["pair_s"].astype(np.int64)
    oa = np.argsort(ka, kind="stable"); ob = np.argsort(kb, kind="stable"); ka = ka[oa]; kb = kb[ob]
    common = np.intersect1d(ka, kb); ia = oa[np.searchsorted(ka, common)]; ib_ = ob[np.searchsorted(kb, common)]
    only_a = np.setdiff1d(ka, kb); only_b = np.setdiff1d(kb, ka)
    res = {"n_pairs_a": int(len(ka)), "n_pairs_b": int(len(kb)), "pairs_only_a": int(len(only_a)), "pairs_only_b": int(len(only_b)), "cols_not_v_or_r": other}
    _oa = neigh_of(Erow_a[only_a // NW]) < 0; _ta = Erow_a[only_a // NW] > int(Erow_b.max())   # [M] extension tail (PREREG §3.4): pairs at anchors after the reference's last E_row
    res["pairs_only_a_outside_neigh"] = int((_oa & ~_ta).sum()); res["pairs_only_b_outside_neigh"] = int((neigh_of(Erow_b[only_b // NW]) < 0).sum())   # [M] tail not counted
    if int((_oa & _ta).sum()): res["pairs_only_a_tail_exempt"] = int((_oa & _ta).sum())   # [M] conditional: present iff the tail rule was load-bearing
    Xa = Fa["X"]; Xb = Fb["X"]; nd_pairs = 0; bad_anchor = 0; bad_sym = 0; ncell_v = 0; ncell_r = 0
    CH = 200000
    for s in range(0, len(common), CH):
        a = Xa[ia[s:s+CH]]; b = Xb[ib_[s:s+CH]]; na_ = np.isnan(a); nb_ = np.isnan(b); d = (na_ != nb_) | (~na_ & ~nb_ & (a != b))
        if not d.any(): continue
        rows = np.nonzero(d.any(1))[0]; keys = common[s:s+CH][rows]; er = Erow_a[keys // NW]; sy = keys % NW; nn = neigh_of(er)
        nd_pairs += len(rows); bad_anchor += int((nn < 0).sum()); dv = d[rows][:, ~isrank].any(1); dr = d[rows][:, isrank].any(1)
        ncell_v += int(dv.sum()); ncell_r += int(dr.sum()); bad_sym += int((dv & ~sym_ok(nn, sy)).sum())
    res.update({"common_pairs_diff": nd_pairs, "diff_pairs_outside_neigh": bad_anchor, "diff_pairs_valuecols": ncell_v, "diff_pairs_rankcols": ncell_r, "valuecol_diff_symbol_not_filled": bad_sym})
    res["PASS"] = bool(res["pairs_only_a_outside_neigh"] == 0 and res["pairs_only_b_outside_neigh"] == 0 and bad_anchor == 0 and bad_sym == 0)
    log(tag, json.dumps(res)); return res
ErB = B["E_row"].astype(np.int64); ErC = C["E_row"].astype(np.int64)
R["B_fea82_hf3_vs_hf2"] = fea_gate(INPUTS["fea82_hf3"], INPUTS["fea82_hf2"], ErB, ErC, "B fea82:")   # [M] $DLW_CLIP vs $PREV_DLW_CLIP
R["B_fea89_f8v4_vs_f8hf2"] = fea_gate(INPUTS["fea89_f8v4"], INPUTS["fea89_f8hf2"], ErB, ErC, "B fea89:")   # [M] $F8 vs $PREV_F8
import hashlib
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
R["fea82_copy_identical"] = sha(INPUTS["fea82_v4raw"]) == sha(INPUTS["fea82_hf3"])   # [M] $DLW_RAW vs $DLW_CLIP fea82
R["PASS"] = bool(R["A_raw_vs_clip"]["PASS"] and R["B_targets_hf3_vs_hf2"]["PASS"] and R["B_fea82_hf3_vs_hf2"]["PASS"] and R["B_fea89_f8v4_vs_f8hf2"]["PASS"] and R["fea82_copy_identical"])
R["neigh_rows"] = NEIGH.tolist(); R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize   # review b0a573a1 P1-PIPE: FAIL exits 3, receipt carries input shas
log("STEP1_GATE", "PASS" if R["PASS"] else "FAIL")
finalize("STEP1", R, _OUT, INPUTS)   # [M] names = the REQUIRED_INPUTS registry roles (dlw_hf3_targets = this month's CLIP, dlw_hf2_targets = the previous month's); `cache` is an extra
