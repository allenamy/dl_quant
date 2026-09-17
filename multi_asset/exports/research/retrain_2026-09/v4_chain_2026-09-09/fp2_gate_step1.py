"""fp2_gate_step1.py — FP2-8 STEP1 gate (DL side), 2026-09-17. Contract-keyed like v4_gate_step1_m.py (79950786); part A copied VERBATIM from it;
part B (the previous-month comparison, which a masked build fails by construction) is REPLACED by:
  B'  binding to the CONTROLS receipt (fp2_controls.py: v2-no-mask == September v1 BITWISE on real data), and
  C   masked build vs the unmasked control: masked anchors ⊆ control anchors (a mask can drop an anchor below MIN_MEM, never add one); per common
      anchor masked members ⊆ control members and every removed member is mask-False at that anchor (mask sha == contract MEMBER_MASK);
      y4s / y4old / qvk / btcv / yrs / has_panel / symbols BITWISE equal on common anchors (targets do not depend on membership); YR4s / YRZ not
      compared (member-set regressions).
Receipt STEP1 via v4_gate_common_v2.finalize3 (three-state); the driver's require_gate names dlw_v4raw_targets / dlw_hf3_targets / fea82_v4raw / fea89_f8v4."""
import numpy as np, json, time, sys, os
t0 = time.time(); R = {}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import sha256_file; from v4_gate_common_v2 import finalize3; import fp2_gate_lib as GL
_OUT = os.environ.get("STEP1_OUT")
if not _OUT: print("STEP1_REFUSED missing STEP1_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)
_KEYS = ("R", "D", "HOLE_CELLS", "DLW_RAW", "DLW_CLIP", "RAW_PATCH", "CACHE", "F8", "MEMBER_MASK", "BUILDER_TARGETS")
_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]
def _p(k, rel=""): return (_E[k] + rel) if _E[k] else None
INPUTS = {"dlw_v4raw_targets": _p("DLW_RAW", "/data/dlw_targets.npz"), "dlw_hf3_targets": _p("DLW_CLIP", "/data/dlw_targets.npz"), "fea82_hf3": _p("DLW_CLIP", "/data/dlw_fea82.npz"),
          "fea82_v4raw": _p("DLW_RAW", "/data/dlw_fea82.npz"), "fea89_f8v4": _p("F8", "/data/f8_fea89.npz"), "raw_patch": _p("RAW_PATCH"), "hole_cells": _p("HOLE_CELLS"), "cache": _p("CACHE"),
          "member_mask": _p("MEMBER_MASK"),
          "fp2_gate_lib": os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp2_gate_lib.py")}   # AMENDMENT 8: the shared library is a hashed input of the receipt (the contract pins only the gate file)
_missing_files = {k: v for k, v in INPUTS.items() if v is None or not os.path.isfile(v)}; _refused = {}
if _missing_env: _refused["missing_env"] = _missing_env
if _missing_files: _refused["missing_files"] = _missing_files
_ctl, _why = ({}, ["env missing"]) if _missing_env else GL.bind_controls(_E["R"], _E["D"], "builder_targets", _E["BUILDER_TARGETS"])
if _why: _refused["controls_binding"] = _why
_scope = [] if _missing_env else GL.check_scope(_E["D"], "STEP1")
if _scope: _refused["scope_binding"] = _scope   # F07: variant approved for one (V4_MONTH, R) only
_cj = None if (_missing_env or _why) else json.load(open(_ctl["receipt"])); _pfb = [] if _cj is None else GL.bind_inputs_to_preflight(_E["R"], _cj.get("inputs_sha256"), _cj.get("inputs_path"))
if _pfb: _refused["controls_inputs_vs_preflight"] = _pfb   # F07: controls ran on THIS root's inputs
if not (_why or _pfb): INPUTS["control_dl_targets"] = _ctl["control_dl_targets"]; INPUTS["controls_receipt"] = _ctl["receipt"]
if _refused: print("STEP1_REFUSED", json.dumps(_refused), flush=True); finalize3("STEP1", {"PASS": False, "VERDICT": "UNAVAILABLE", "REFUSED": _refused}, _OUT, INPUTS)
H = np.load(INPUTS["hole_cells"], allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]; CSYM = H["symbols"]
def eq(a, b):
    if a.dtype == object: return len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))
    if a.dtype.kind in "fc": return a.shape == b.shape and np.array_equal(a, b, equal_nan=True)
    return np.array_equal(a, b)
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
# ---------- A (VERBATIM from v4_gate_step1_m.py 79950786: this run's RAW vs CLIP) ----------
A = np.load(INPUTS["dlw_v4raw_targets"], allow_pickle=True); B = np.load(INPUTS["dlw_hf3_targets"], allow_pickle=True)
assert np.array_equal(A["symbols"], CSYM) and np.array_equal(B["symbols"], CSYM)
RA = {k: eq(A[k], B[k]) for k in ("E_ts", "E_row", "members", "yrs", "has_panel", "symbols", "btcv", "qvk", "y4old")}
log("A bitwise:", RA)
E_row = A["E_row"].astype(np.int64); ya = A["y4s"]; yb = B["y4s"]; nA, NW = ya.shape
P = np.load(INPUTS["raw_patch"]); prow = P["row"].astype(np.int64); pcol = P["col"].astype(np.int64)
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
    d = (fa_ != fb_) | (fa_ & fb_ & (dd_ > 1e-6)); rows = d.any(1); xrows = X.any(1)
    RA[f"{k}_diff_rows"] = int(rows.sum()); RA[f"{k}_diff_rows_outside_patch_rows"] = int((rows & ~xrows).sum())
    RA[f"{k}_noise_max_outside_patch_rows"] = float(np.nanmax(np.where(fa_ & fb_ & ~xrows[:, None], dd_, 0.0)))
RA["PASS"] = bool(all(RA[k] for k in ("E_ts", "E_row", "members", "yrs", "has_panel", "symbols", "btcv", "qvk", "y4old", "y4s_finite_pattern_equal"))
                  and RA["y4s_big_outside_patch_windows"] == 0 and RA["y4s_noise_max_outside_patch"] <= 1e-6
                  and RA["YR4s_diff_rows_outside_patch_rows"] == 0 and RA["YRZ_diff_rows_outside_patch_rows"] == 0)
log("A:", json.dumps(RA)); R["A_raw_vs_clip"] = RA
# ---------- B' controls binding (already verified above; recorded) ----------
R["B_controls"] = _ctl
# ---------- C masked (this run RAW) vs unmasked control ----------
C = np.load(INPUTS["control_dl_targets"], allow_pickle=True); RC = {}
Em = A["E_ts"].astype(np.int64); Ec = C["E_ts"].astype(np.int64)
MASK, _mw = GL.mask_rows(INPUTS["member_mask"], Em, A["symbols"])
if MASK is None: RC["mask"] = _mw; RC["PASS"] = False
else:
    MASKc, _mwc = GL.mask_rows(INPUTS["member_mask"], Ec, A["symbols"]); RC["mask_rows_control_axis"] = _mwc or "ok"   # F06: needed to explain DROPPED anchors
    RC.update(GL.members_subset_check(Ec, C["members"], Em, A["members"], MASK, MASK_c=MASKc)); RC["mask_sha256"] = sha256_file(INPUTS["member_mask"])
    rc_ = {int(t): i for i, t in enumerate(Ec)}; ic = np.array([rc_[int(t)] for t in Em if int(t) in rc_]); im = np.array([j for j, t in enumerate(Em) if int(t) in rc_])
    for k in ("y4s", "y4old", "qvk", "btcv", "yrs", "has_panel"):
        a = A[k][im]; c = C[k][ic]; RC[f"{k}_bitwise"] = bool(a.shape == c.shape and a.dtype == c.dtype and np.array_equal(a.view(np.uint8), c.view(np.uint8)))
    RC["symbols_equal"] = bool(np.array_equal(A["symbols"], C["symbols"]))
    RC["PASS"] = bool(RC["PASS"] and all(RC[f"{k}_bitwise"] for k in ("y4s", "y4old", "qvk", "btcv", "yrs", "has_panel")) and RC["symbols_equal"])
log("C:", json.dumps(RC)); R["C_masked_vs_control"] = RC
R["fea82_copy_identical"] = sha256_file(INPUTS["fea82_v4raw"]) == sha256_file(INPUTS["fea82_hf3"])
R["PASS"] = bool(R["A_raw_vs_clip"]["PASS"] and R["C_masked_vs_control"]["PASS"] and R["fea82_copy_identical"])
R["VERDICT"] = "PASS" if R["PASS"] else "FAIL"; R["neigh_rows"] = NEIGH.tolist(); R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
log("STEP1_GATE", R["VERDICT"]); finalize3("STEP1", R, _OUT, INPUTS)
