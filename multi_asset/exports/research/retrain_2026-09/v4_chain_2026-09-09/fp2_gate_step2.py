"""fp2_gate_step2.py — FP2-8 STEP2 gate (king side), 2026-09-17. Contract-keyed like v4_gate_step2_m.py (d99a9109); the previous-month reference
(which a masked build with a v2 axis fails by construction) is REPLACED by the unmasked v2 CONTROL of this run (fp2_controls.py, which itself
proved v2-no-mask == September v1 BITWISE on common anchors and that the only extra anchors are the 30 pre-2016-bar ones):
  B'  controls binding (receipt PASS; control outputs re-hashed; the builder the controls ran == the contract's BUILDER_KING_FEA on disk)
  I   builder identity: preflight.json device_sha256[BUILDER_KING_FEA] == on-disk == controls' builder sha
  C   masked vs control: masked anchors ⊆ control anchors; per common anchor masked members ⊆ control members, removed ⊆ mask-False (mask sha pinned);
      VALUE columns (`_v`) BITWISE equal on common members (per-symbol window statistics do not depend on membership); RANK columns (`_r`) are
      within-member ranks and legitimately differ where membership changed — not compared; y4 / qvk BITWISE equal on common anchors
  Q   member index structural validity for EVERY anchor (AMENDMENT 3 rule of v4_gate_step2_m: integer kind, 1-D, in [0, NW), unique) + >= 1 member
Receipt STEP2 via finalize3; the driver's require_gate names wide_fea_v4 / wide_fea_v4_meta."""
import numpy as np, json, time, os, sys
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import sha256_file; from v4_gate_common_v2 import finalize3; import fp2_gate_lib as GL
_OUT = os.environ.get("STEP2_OUT")
if not _OUT: print("STEP2_REFUSED missing STEP2_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)
_KEYS = ("R", "D", "CACHE", "KING_FEA", "KING_META", "MEMBER_MASK", "BUILDER_KING_FEA")
_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]
INPUTS = {"wide_fea_v4": _E["KING_FEA"] or None, "wide_fea_v4_meta": _E["KING_META"] or None, "cache": _E["CACHE"] or None, "member_mask": _E["MEMBER_MASK"] or None,
          "preflight": (os.path.join(_E["R"], "v4_gates", "preflight.json") if _E["R"] else None),
          "fp2_gate_lib": os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp2_gate_lib.py")}   # AMENDMENT 8: the shared library is a hashed input of the receipt (the contract pins only the gate file)
_missing_files = {k: v for k, v in INPUTS.items() if v is None or not os.path.isfile(v)}; _refused = {}
if _missing_env: _refused["missing_env"] = _missing_env
if _missing_files: _refused["missing_files"] = _missing_files
_ctl, _why = ({}, ["env missing"]) if _missing_env else GL.bind_controls(_E["R"], _E["D"], "builder_king", _E["BUILDER_KING_FEA"])
if _why: _refused["controls_binding"] = _why
_scope = [] if _missing_env else GL.check_scope(_E["D"], "STEP2")
if _scope: _refused["scope_binding"] = _scope   # F07: variant approved for one (V4_MONTH, R) only
_cj = None if (_missing_env or _why) else json.load(open(_ctl["receipt"])); _pfb = [] if _cj is None else GL.bind_inputs_to_preflight(_E["R"], _cj.get("inputs_sha256"), _cj.get("inputs_path"))
if _pfb: _refused["controls_inputs_vs_preflight"] = _pfb   # F07: controls ran on THIS root's inputs
if not (_why or _pfb): INPUTS["control_king_fea"] = _ctl["control_king_fea"]; INPUTS["control_king_meta"] = _ctl["control_king_meta"]; INPUTS["controls_receipt"] = _ctl["receipt"]
_ID = {}
if not _refused:
    _dev = os.path.join(_E["D"], _E["BUILDER_KING_FEA"]); _dv = sha256_file(_dev)
    _pf = (json.load(open(INPUTS["preflight"])).get("device_sha256") or {}).get(_E["BUILDER_KING_FEA"])
    _ID = {"builder": _E["BUILDER_KING_FEA"], "on_disk_sha256": _dv, "preflight_sha256": _pf, "controls_sha256": _ctl["builder"]["sha256"]}
    _idw = [] if (_pf == _dv == _ctl["builder"]["sha256"]) else [f"builder identity mismatch: on-disk {_dv[:12]} preflight {str(_pf)[:12]} controls {str(_ctl['builder']['sha256'])[:12]}"]
    if _idw: _refused["builder_identity"] = _idw
if _refused: print("STEP2_REFUSED", json.dumps(_refused), flush=True); finalize3("STEP2", {"PASS": False, "VERDICT": "UNAVAILABLE", "REFUSED": _refused, "builder_identity": _ID}, _OUT, INPUTS)
R = {"builder_identity": _ID, "B_controls": _ctl}
M4 = np.load(INPUTS["wide_fea_v4_meta"], allow_pickle=True); MC = np.load(INPUTS["control_king_meta"], allow_pickle=True)
F4 = np.load(INPUTS["wide_fea_v4"], mmap_mode="r"); FC = np.load(INPUTS["control_king_fea"], mmap_mode="r")
E4 = M4["E_ts"].astype(np.int64); EC = MC["E_ts"].astype(np.int64); names = [str(x) for x in M4["names"]]
assert names == [str(x) for x in MC["names"]], "names differ from control"
isrank = np.array([n.endswith("_r") for n in names]); NW, NF = F4.shape[1:]
R["names_ok"] = all(n.endswith("_v") or n.endswith("_r") or n in ("fund_ema", "fund_now") for n in names)
syms = [str(s) for s in np.load(INPUTS["cache"], mmap_mode="r")["symbols"]] if False else None
import zipfile
with zipfile.ZipFile(INPUTS["cache"]) as z: syms = [str(s) for s in np.load(z.open("symbols.npy"), allow_pickle=True)]
MASK, _mw = GL.mask_rows(INPUTS["member_mask"], E4, syms)
RC = {}
if MASK is None: RC = {"mask": _mw, "PASS": False}
else:
    M4m = M4["members"]; MCm = MC["members"]
    MASKc, _mwc = GL.mask_rows(INPUTS["member_mask"], EC, syms); RC["mask_rows_control_axis"] = _mwc or "ok"   # F06: needed to explain DROPPED anchors
    RC.update(GL.members_subset_check(EC, MCm, E4, M4m, MASK, MASK_c=MASKc)); RC["mask_sha256"] = sha256_file(INPUTS["member_mask"])
    rc_ = {int(t): i for i, t in enumerate(EC)}; pairs = [(j, rc_[int(t)]) for j, t in enumerate(E4) if int(t) in rc_]
    vcols = np.nonzero(~isrank)[0]; bad_val = 0; bad_y = 0; checked = 0
    Y4, YC, Q4, QC = M4["y4"], MC["y4"], M4["qvk"], MC["qvk"]   # materialised ONCE (an NpzFile key access re-reads the whole array per iteration)
    for j, i in pairs:
        m = np.intersect1d(np.asarray(M4m[j]), np.asarray(MCm[i]))   # AMENDMENT 8: value columns compared on the INTERSECTION members (additions have no control cell)
        a = np.asarray(F4[j])[m][:, vcols]; c = np.asarray(FC[i])[m][:, vcols]
        if not np.array_equal(a.view(np.uint16), c.view(np.uint16)): bad_val += 1
        if not (np.array_equal(Y4[j].view(np.uint32), YC[i].view(np.uint32)) and np.array_equal(Q4[j].view(np.uint32), QC[i].view(np.uint32))): bad_y += 1
        checked += 1
    RC.update({"common_checked": checked, "value_cols_not_bitwise_rows": bad_val, "y4_qvk_not_bitwise_rows": bad_y})
    RC["PASS"] = bool(RC["PASS"] and bad_val == 0 and bad_y == 0)
log("C:", json.dumps(RC)); R["C_masked_vs_control"] = RC
Q = {"n_anchors": int(len(E4)), "invalid_index_rows": 0, "empty_rows": 0, "first_bad": []}
for j in range(len(E4)):
    raw = np.asarray(M4["members"][j]); why = None
    if raw.dtype.kind not in "iu": why = f"dtype {raw.dtype}"
    elif raw.ndim != 1: why = f"ndim {raw.ndim}"
    elif raw.size == 0: Q["empty_rows"] += 1; continue
    elif int(raw.min()) < 0 or int(raw.max()) >= NW: why = "range"
    elif raw.size != int(np.unique(raw).size): why = "duplicates"
    if why: Q["invalid_index_rows"] += 1; Q["first_bad"].append({"i": j, "why": why}) if len(Q["first_bad"]) < 5 else None
Q["PASS"] = Q["invalid_index_rows"] == 0 and Q["empty_rows"] == 0; R["Q_member_index"] = Q
R["PASS"] = bool(R["names_ok"] and R["C_masked_vs_control"]["PASS"] and R["Q_member_index"]["PASS"]); R["VERDICT"] = "PASS" if R["PASS"] else "FAIL"
R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); log("STEP2_GATE", R["VERDICT"]); finalize3("STEP2", R, _OUT, INPUTS)
