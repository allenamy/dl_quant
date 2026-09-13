"""PREREG_v4 section 2 step 2 gates (king side).
 wide_fea_v4 (holefix2 + clamp) vs wide_fea_v2ext_clamp (_ext + clamp): differing anchors only inside hole neighbourhoods; value-col diffs only for filled symbols.
 wide_fea_v4 vs wide_fea_v2ext (_ext, unclamped): differing anchors ⊆ first-138 (E_row < 8640, E-0909-A) ∪ hole neighbourhoods.
 meta: E_ts bitwise = v2ext meta; members / y4 / qvk differences only inside hole neighbourhoods (y4/qvk symbols ⊆ filled)."""
# [M] MONTH-GENERIC (W7 2026-09-12, docs/PREREG_v4_gates_monthly_2026-09-12.md): every path comes from the month contract env (chain_lib.load_month_env exports it);
# [M] the reference is the PREVIOUS month's contract-pinned king build (PREV_KING_FEA / PREV_META; September = v2ext_clamp / v2ext_meta); PREV_KING_FEA_UNCLAMPED is the unclamped
# [M] build on the reference axis (September: v2ext) or the literal NONE (clamp checks v4_vs_ext / clamp_vs_ext NOT evaluated, recorded in the receipt, §3.3); thresholds/statistics verbatim;
# [M] anchors after the reference axis end are the extension tail (§3.4); a reference identical to the candidate is refused (§3.5); missing inputs are refused with a PASS=false receipt (§3.6).
# [M] AMENDMENT 1 (researcher B-R4): NONE is bound to the builder identity (PREV_CLAMP_BUILDER_SHA256 == preflight-pinned == on-disk pod_fea_ext_clamp.py, else refused); every new-tail anchor
# [M] must have >= 1 member and a member-cell finite fraction >= 0.90 (tail_quality, always present when a tail exists, part of PASS).
# [M] AMENDMENT 2 (2026-09-13, researcher F-R3): the new-tail member index is validated STRUCTURALLY FIRST (1-D, integer, in [0, NW), no duplicates) and an invalid index is
# [M] never used as a subscript; only then does the 0.90 floor apply. The floor is a FINITE-CELL gate on the tail — it is not a causal or predictive-validity gate (§3.7).
import numpy as np, json, time, os, sys
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize, sha256_file   # [M] refusal receipts go through finalize BEFORE any load
_OUT = os.environ.get("STEP2_OUT")   # [M] required, no September default
if not _OUT: print("STEP2_REFUSED missing STEP2_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)   # [M]
_KEYS = ("HOLE_CELLS", "CACHE", "KING_FEA", "KING_META", "PREV_KING_FEA", "PREV_KING_FEA_UNCLAMPED", "PREV_META")   # [M] month contract keys this gate reads (PREREG §2)
_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]   # [M]
NO_UNCLAMPED = _E["PREV_KING_FEA_UNCLAMPED"] == "NONE"   # [M] PREREG §3.3: the contract (user word) says no unclamped build exists on the reference axis
INPUTS = {"wide_fea_v4": _E["KING_FEA"] or None, "wide_fea_v4_meta": _E["KING_META"] or None, "wide_fea_v2ext_clamp": _E["PREV_KING_FEA"] or None,   # [M]
          "wide_fea_v2ext": None if NO_UNCLAMPED else (_E["PREV_KING_FEA_UNCLAMPED"] or None), "wide_fea_v2ext_meta": _E["PREV_META"] or None, "hole_cells": _E["HOLE_CELLS"] or None, "cache": _E["CACHE"] or None}   # [M]
_missing_files = {k: v for k, v in INPUTS.items() if (v is None or not os.path.isfile(v)) and not (k == "wide_fea_v2ext" and NO_UNCLAMPED)}; _refused = {}   # [M]
if _missing_env: _refused["missing_env"] = _missing_env   # [M]
if _missing_files: _refused["missing_files"] = _missing_files   # [M]
if not _refused:   # [M] reference must not be the candidate (PREREG §3.5): a file compared with itself verifies nothing
    _sh = {}; _S = lambda k: _sh.setdefault(k, sha256_file(INPUTS[k]))   # [M]
    _pairs = [("wide_fea_v4", "wide_fea_v2ext_clamp"), ("wide_fea_v4_meta", "wide_fea_v2ext_meta")] + ([] if NO_UNCLAMPED else [("wide_fea_v4", "wide_fea_v2ext"), ("wide_fea_v2ext_clamp", "wide_fea_v2ext")])   # [M]
    _same = [f"{a}=={b}" for a, b in _pairs if _S(a) == _S(b)]   # [M]
    if _same: _refused["reference_is_candidate"] = _same   # [M]
_CLAMP_CHECKS = None   # [M] AMENDMENT 1 (B-R4): under NONE the builder identity is verified here, not assumed
if NO_UNCLAMPED:   # [M]
    _pin = os.environ.get("PREV_CLAMP_BUILDER_SHA256", ""); _root = os.environ.get("R", ""); _deps = os.path.join(_root, "v4_gates", "deps_preflight_device.json") if _root else ""   # [M]
    _dev = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pod_fea_ext_clamp.py"); _why = []; _pf = None; _dv = None   # [M]
    if not _pin: _why.append("PREV_CLAMP_BUILDER_SHA256 unset (the contract must pin the September-verified builder sha)")   # [M]
    if not _root: _why.append("R unset (month root: the preflight deps receipt cannot be located)")   # [M]
    elif not os.path.isfile(_deps): _why.append(f"preflight deps receipt missing: {_deps}")   # [M]
    else:   # [M]
        _dd = json.load(open(_deps)).get("deps_sha256", {}); _hits = [v for k, v in _dd.items() if k.endswith("/pod_fea_ext_clamp.py")]   # [M]
        _pf = _hits[0] if len(_hits) == 1 else None   # [M]
        if _pf is None: _why.append(f"preflight deps receipt pins pod_fea_ext_clamp.py {len(_hits)} times (need exactly 1): {_deps}")   # [M]
    if not os.path.isfile(_dev): _why.append(f"builder missing beside the gate: {_dev}")   # [M]
    else: _dv = sha256_file(_dev)   # [M]
    if _pin and _pf and _pf != _pin: _why.append(f"preflight-pinned builder {_pf[:12]} != contract pin {_pin[:12]}")   # [M]
    if _pin and _dv and _dv != _pin: _why.append(f"on-disk builder {_dv[:12]} != contract pin {_pin[:12]}")   # [M]
    if _why: _refused["clamp_builder_identity"] = {"why": _why, "pinned_sha256": _pin or None, "preflight_pinned_sha256": _pf, "device_file_sha256": _dv}   # [M]
    else: _CLAMP_CHECKS = {"mode": "NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE (v4_vs_ext / clamp_vs_ext not computed)", "builder": "pod_fea_ext_clamp.py", "pinned_sha256": _pin, "preflight_pinned_sha256": _pf, "device_file_sha256": _dv, "preflight_deps_receipt": _deps}   # [M] identity verified (AMENDMENT 1)
if _refused: print("STEP2_REFUSED", json.dumps(_refused), flush=True); finalize("STEP2", {"PASS": False, "REFUSED": _refused}, _OUT, INPUTS)   # [M] rc 3; receipt PASS=false; missing shas None
H = np.load(INPUTS["hole_cells"], allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]   # [M] $HOLE_CELLS
run_syms = [set(np.unique(H["col"][(H["row"] >= a) & (H["row"] <= b)]).tolist()) for (a, b) in RUNS]
def neigh_of(rows):
    out = np.full(len(rows), -1, np.int64)
    for k, (lo, hi) in enumerate(NEIGH): out[(rows >= lo) & (rows <= hi)] = k
    return out
CTS = np.load(INPUTS["cache"])["ts"].astype(np.int64)   # [M] $CACHE
M4 = np.load(INPUTS["wide_fea_v4_meta"], allow_pickle=True); ME = np.load(INPUTS["wide_fea_v2ext_meta"], allow_pickle=True)   # [M] $KING_META vs $PREV_META (the previous month's meta; September: v2ext)
E4 = M4["E_ts"].astype(np.int64); EE = ME["E_ts"].astype(np.int64); R = {"E_ts_equal": bool(np.array_equal(E4, EE)), "nA_v4": int(len(E4)), "nA_v2ext": int(len(EE))}
# axis: v4 may carry extra anchors (hole fills at the tail make anchors pass the member filter); extra anchors must lie inside a hole neighbourhood
COMMON = np.intersect1d(E4, EE); I4 = np.searchsorted(E4, COMMON); IE = np.searchsorted(EE, COMMON); assert np.array_equal(E4[I4], COMMON) and np.array_equal(EE[IE], COMMON)
def rows_of(E): r = np.searchsorted(CTS, E); assert np.array_equal(CTS[r], E); return r
x4 = np.setdiff1d(E4, EE); xE = np.setdiff1d(EE, E4)
R["anchors_only_v4"] = [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t))) for t in x4]; R["anchors_only_v2ext"] = [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t))) for t in xE]
_o4 = (neigh_of(rows_of(x4)) < 0) if len(x4) else np.zeros(0, bool); _t4 = x4 > int(EE.max())   # [M] extension tail (PREREG §3.4): only-in-new anchors AFTER the reference axis end
R["anchors_only_v4_outside_neigh"] = int((_o4 & ~_t4).sum()); R["anchors_only_v2ext_outside_neigh"] = int((neigh_of(rows_of(xE)) < 0).sum()) if len(xE) else 0   # [M] tail not counted
if int((_o4 & _t4).sum()): R["anchors_only_v4_tail_exempt"] = int((_o4 & _t4).sum()); R["ref_axis_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(EE.max())))   # [M] conditional: present iff the tail rule was load-bearing
Erow = rows_of(COMMON); nn = neigh_of(Erow); f138 = Erow < 8640; R["n_first138"] = int(f138.sum()); R["n_common"] = int(len(COMMON))
names = [str(x) for x in M4["names"]]; isrank = np.array([n.endswith("_r") for n in names]); R["cols_not_v_or_r"] = [n for n in names if not (n.endswith("_r") or n.endswith("_v"))]
assert names == [str(x) for x in ME["names"]]
M4m = M4["members"]; MEm = ME["members"]
F4 = np.load(INPUTS["wide_fea_v4"], mmap_mode="r"); FC = np.load(INPUTS["wide_fea_v2ext_clamp"], mmap_mode="r"); FE = None if NO_UNCLAMPED else np.load(INPUTS["wide_fea_v2ext"], mmap_mode="r")   # [M] $KING_FEA / $PREV_KING_FEA / $PREV_KING_FEA_UNCLAMPED (NONE allowed, §3.3)
assert F4.shape[1:] == FC.shape[1:] and F4.shape[0] == len(E4) and FC.shape[0] == len(EE) and (NO_UNCLAMPED or (FE.shape[1:] == FC.shape[1:] and FE.shape[0] == len(EE))), (F4.shape, FC.shape, None if NO_UNCLAMPED else FE.shape)   # [M]
nA = len(COMMON); NW, NF = F4.shape[1:]
def cmp(a, b):
    na = np.isnan(a); nb = np.isnan(b); return (na != nb) | (~na & ~nb & (a != b))
S = {"v4_vs_clamp": {"anchors": 0, "outside": 0, "val_pairs": 0, "val_sym_bad": 0, "val_sym_membership_nanpat": 0, "rank_pairs": 0}, "v4_vs_ext": {"anchors": 0, "outside_138_and_neigh": 0, "in_first138": 0},
     "clamp_vs_ext": {"anchors": 0, "outside_138": 0}}
if NO_UNCLAMPED: del S["v4_vs_ext"], S["clamp_vs_ext"]; R["clamp_checks"] = _CLAMP_CHECKS   # [M] conditional: present iff NONE; the builder identity was verified above (AMENDMENT 1)
CH = 128
for s in range(0, nA, CH):
    idx = np.arange(s, min(s + CH, nA)); a = np.asarray(F4[I4[idx]]); c = np.asarray(FC[IE[idx]]); e = None if NO_UNCLAMPED else np.asarray(FE[IE[idx]])   # [M]
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
    if not NO_UNCLAMPED:   # [M] clamp checks only when an unclamped reference exists (PREREG §3.3)
        d2 = cmp(a, e).any((1, 2))   # [M] (frozen L48, indented)
        S["v4_vs_ext"]["anchors"] += int(d2.sum()); S["v4_vs_ext"]["outside_138_and_neigh"] += int((d2 & ~f138[idx] & (nn[idx] < 0)).sum()); S["v4_vs_ext"]["in_first138"] += int((d2 & f138[idx]).sum())   # [M] (frozen L49, indented)
        d3 = cmp(c, e).any((1, 2)); S["clamp_vs_ext"]["anchors"] += int(d3.sum()); S["clamp_vs_ext"]["outside_138"] += int((d3 & ~f138[idx]).sum())   # [M] (frozen L50, indented)
    if s % 2048 == 0: log(f"{s}/{nA}", json.dumps(S))
R["features"] = S
_tail_idx = np.searchsorted(E4, x4[_t4]) if len(x4) else np.zeros(0, np.int64)   # [M] AMENDMENT 1 (B-R4): new-tail anchors = only-in-new AND after the reference axis end (§3.4)
if len(_tail_idx):   # [M] tail quality gate: every tail anchor needs a STRUCTURALLY VALID member index, >= 1 member and a member-cell finite fraction >= 0.90 (floor pre-registered from the September calibration: min 0.9756, median 1.0)
    # [M] ★ AMENDMENT 2 (2026-09-13, review §3.D / researcher probe tail_invalid_negative_member_index_ACCEPTED): the index was fed straight to numpy, so members=[-1]
    # [M]   read the LAST column, scored finite fraction 1.0 and PASSed. A member index is a symbol index: it must be a 1-D vector of integers in [0, NW) without
    # [M]   duplicates. Validity is decided FIRST and an invalid index is NEVER used to read features; only then does the finite-fraction floor apply (PREREG §3.7).
    _ffs = []; _nms = []; _mbad = []   # [M]
    for _i in _tail_idx:   # [M]
        _raw = np.asarray(M4m[_i]); _why = []   # [M]
        try: _m = _raw.astype(np.int64)   # [M] a member index that cannot even be read as integers is a clean FAIL receipt, not an uncaught cast (rc 1, no receipt)
        except Exception as _e: _m = np.zeros(0, np.int64); _why.append(f"not castable to an integer index ({type(_e).__name__})")   # [M]
        if _why: pass   # [M]
        elif _raw.ndim != 1: _why.append(f"ndim {_raw.ndim} != 1 (a member index is a vector)")   # [M]
        elif _raw.size and _raw.dtype.kind not in "iu" and not np.array_equal(_m, _raw): _why.append(f"dtype {_raw.dtype} is not an integer index")   # [M]
        elif _m.size and (int(_m.min()) < 0 or int(_m.max()) >= NW): _why.append(f"index range [{int(_m.min())}, {int(_m.max())}] outside [0, {NW})")   # [M]
        elif _m.size != int(np.unique(_m).size): _why.append(f"{_m.size - int(np.unique(_m).size)} duplicate index(es)")   # [M]
        if _why: _mbad.append({"anchor_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(E4[_i]))), "i": int(_i), "members": _raw.reshape(-1).tolist()[:8], "why": _why})   # [M]
        _nms.append(int(_m.size)); _ffs.append(float(np.isfinite(np.asarray(F4[_i])[_m]).mean()) if (_m.size and not _why) else 0.0)   # [M] an invalid index is never used as a subscript
    _ffs = np.array(_ffs); R["tail_quality"] = {"n_tail_anchors": int(len(_tail_idx)), "member_index_ok": not _mbad, "member_finite_frac_min": float(_ffs.min()), "member_finite_frac_median": float(np.median(_ffs)), "n_members_min": int(min(_nms)), "floor": 0.90,   # [M]
                                                "ok": bool(not _mbad and (_ffs >= 0.90).all() and min(_nms) >= 1)}   # [M]
    if _mbad: R["tail_quality"]["member_index_bad"] = _mbad   # [M] conditional: present iff the structural rule was load-bearing
# meta
mrows = np.array([not np.array_equal(M4m[i], MEm[j]) for i, j in zip(I4, IE)]); R["members_diff_rows"] = int(mrows.sum()); R["members_diff_rows_outside_neigh"] = int((mrows & (nn < 0)).sum())
for k in ("y4", "qvk"):
    a = M4[k][I4]; b = ME[k][IE]; d = cmp(a, b); r_, s_ = np.nonzero(d); R[f"{k}_diff_cells"] = int(d.sum()); R[f"{k}_diff_outside_neigh"] = int((nn[r_] < 0).sum())
    R[f"{k}_diff_symbol_not_filled"] = int(sum(1 for r, y in zip(r_, s_) if not (nn[r] >= 0 and int(y) in run_syms[nn[r]])))
R["PASS"] = bool(S["v4_vs_clamp"]["outside"] == 0 and S["v4_vs_clamp"]["val_sym_bad"] == 0 and (NO_UNCLAMPED or (S["v4_vs_ext"]["outside_138_and_neigh"] == 0 and S["clamp_vs_ext"]["outside_138"] == 0)) and ("tail_quality" not in R or R["tail_quality"]["ok"])   # [M] clamp checks not evaluated under NONE (§3.3); tail quality (AMENDMENT 1); the rest verbatim
                 and R["members_diff_rows_outside_neigh"] == 0 and all(R[f"{k}_diff_outside_neigh"] == 0 and R[f"{k}_diff_symbol_not_filled"] == 0 for k in ("y4", "qvk")) and R["n_first138"] == 138
                 and R["anchors_only_v4_outside_neigh"] == 0 and R["anchors_only_v2ext_outside_neigh"] == 0)
R["neigh_rows"] = NEIGH.tolist(); R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
log("STEP2_GATE", "PASS" if R["PASS"] else "FAIL", json.dumps(R))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize   # review b0a573a1 P1-PIPE: FAIL exits 3, receipt carries input shas
finalize("STEP2", R, _OUT, INPUTS)   # [M] names = the REQUIRED_INPUTS registry roles (wide_fea_v2ext* = the previous month's build); `cache` is an extra; wide_fea_v2ext is None under NONE
