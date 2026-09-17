#!/usr/bin/env python3
"""tests_fp2_gates.py — FP2-8 (2026-09-17): fp2_controls.py + fp2_gate_step1.py + fp2_gate_step2.py end-to-end on a synthetic cache, through their REAL entries.
  G1  controls (v2-no-mask vs 'September' = real v1 outputs) ⇒ PASS; K3 reports exactly the 30 pre-2016 anchors; D1 bitwise
  G2  masked builds + real preflight-shaped receipt ⇒ STEP1 PASS (A, C) and STEP2 PASS (I, C, Q); receipts carry the driver's required input names
  G3  RED: a masked build made with a DIFFERENT mask than the contract's ⇒ STEP1/STEP2 FAIL (removed member not mask-False) — the gate sees the substitution
  G4  RED (last, in place): control output rewritten after the receipt ⇒ both gates UNAVAILABLE (controls binding refused), receipt PASS=false
  G7  RED: a controls receipt copied from another root ⇒ UNAVAILABLE (outputs outside this root)
  G8  truncation-aware member rule (AMENDMENT 8): additions allowed only at truncated control rows and mask-True   G9 RED: addition at a non-truncated row ⇒ FAIL
  G5  RED: preflight pins a different builder sha ⇒ STEP2 UNAVAILABLE (builder identity)
  G6  RED (controls): 'September' king build with one FEA value altered ⇒ controls FAIL on K2 (nothing else)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; sys.path.insert(0, HERE); import fp2_synth
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:260]) if detail is not None else ""), flush=True)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
TMP = tempfile.mkdtemp(prefix="fp2g_"); S = fp2_synth.make(TMP)
BASE = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", TMP), "PYTHONPATH": S["shim"], "OMP_NUM_THREADS": "1"}
def build(script, out, mask="", patch=""):
    os.makedirs(out, exist_ok=True); e = dict(BASE, MEMBER_MASK_NPZ=mask)
    if "fea_ext" in script: e.update(CACHE_IN=S["CACHE"], PANEL_IN=S["KPANEL"], FEA_OUT=f"{out}/wide_fea_v4.npy", META_OUT=f"{out}/wide_fea_v4_meta.npz")
    else: e.update(DLWT_CACHE=S["CACHE"], DLWT_PANEL=S["DPANEL"], DLWT_OUT=out, DLWT_RET_CH="0", DLWT_RAW_PATCH=patch)
    r = subprocess.run([PY, f"{HERE}/{script}"], env=e, cwd=TMP, capture_output=True, text=True); assert r.returncode == 0, (script, r.stdout[-600:], r.stderr[-600:])
def maskfile(name, mk): p = f"{TMP}/{name}.npz"; np.savez(p, ts=S["grid"], symbols=np.array(S["syms"]), mask=mk, definition=np.array(name)); return p
# 'September' = v1 builds
build("pod_fea_ext_clamp.py", f"{TMP}/sept_king"); build("pod_dlw_targets_raw.py", f"{TMP}/sept_dl")
DEV_FILES_FOR_ROOT = ("fp2_gate_step1.py", "fp2_gate_step2.py", "fp2_gate_lib.py", "fp2_controls.py", "v4_gate_common.py", "v4_gate_common_v2.py", "pod_fea_ext_clamp_v2.py", "pod_dlw_targets_raw_v2.py")
def device_dir(R, month="2026-99"):
    """F07 harness: every root gets its OWN device dir with a contract whose FP2 variants are scoped to (month, this root)."""
    D = f"{R}/device"; os.makedirs(D, exist_ok=True)
    for f in DEV_FILES_FOR_ROOT: shutil.copy2(f"{HERE}/{f}", f"{D}/{f}")
    c = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
    for g, f in (("STEP1", "fp2_gate_step1.py"), ("STEP2", "fp2_gate_step2.py")):
        c["gates"][g]["approved_variants"][f]["scope"] = {"V4_MONTH": month, "R": R}
    json.dump(c, open(f"{D}/ELIGIBILITY_CONTRACT.json", "w"), indent=1); return D
def preflight_for(R, D, cache=None, splice=None, king=None, patch=None):
    """the receipt the driver's preflight writes: device shas + external_sha256 of the contract inputs (F07 binds the controls' inputs to it)"""
    inp = {}
    for k, p in (("CACHE", cache or S["CACHE"]), ("PANEL_SPLICE", splice or S["DPANEL"]), ("PANEL_KING", king or S["KPANEL"]), ("RAW_PATCH", patch)):
        if p and os.path.isfile(p): inp[k] = {"path": p, "bytes": os.path.getsize(p), "is_dir": False}          # the REAL preflight layout: path + bytes, no sha for inputs
    os.makedirs(f"{R}/v4_gates", exist_ok=True)
    json.dump({"gate": "PREFLIGHT", "PASS": True, "device_sha256": {f: sha(f"{D}/{f}") for f in DEV_FILES_FOR_ROOT}, "inputs": inp, "external_sha256": {}}, open(f"{R}/v4_gates/preflight.json", "w"))
def controls(R, sept_king=f"{TMP}/sept_king", sept_dl=f"{TMP}/sept_dl"):
    D = f"{R}/device"; (os.path.isdir(D) or device_dir(R))
    e = dict(BASE, R=R, D=D, PY=PY, CACHE=S["CACHE"], PANEL_SPLICE=S["DPANEL"], PANEL_KING=S["KPANEL"], RAW_PATCH="", SEPT_KING_FEA=f"{sept_king}/wide_fea_v4.npy",
             SEPT_KING_META=f"{sept_king}/wide_fea_v4_meta.npz", SEPT_DL_TARGETS=f"{sept_dl}/data/dlw_targets.npz", BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py")
    r = subprocess.run([PY, f"{D}/fp2_controls.py"], env=e, cwd=TMP, capture_output=True, text=True)
    rec = json.load(open(f"{R}/controls/CONTROLS.json")) if os.path.isfile(f"{R}/controls/CONTROLS.json") else None
    return r.returncode, r.stdout + r.stderr, rec
# the king panel starts AFTER the first anchors (as the real v2ext panel starts 2022-01-31 while the cache starts 2022-01-01): fund columns are NaN there
_kp = np.load(S["KPANEL"]); _cut = 40; np.savez(S["KPANEL"], ts=_kp["ts"][_cut:], f_fund_ema=_kp["f_fund_ema"][_cut:], f_fund_now=_kp["f_fund_now"][_cut:])
R1 = f"{TMP}/R1"; os.makedirs(R1); rc, out, rec = controls(R1)
if not os.path.isdir(f"{R1}/controls"): print("UNAVAILABLE: controls produced no directory —", out[-900:]); sys.exit(3)
check("G1 controls PASS (rc 0, VERDICT PASS) with a king panel that starts after the first anchors (fund columns NaN there — real v2ext layout); K3 n_extra == 30 with extra_rows_with_fund_nan > 0; D1 bitwise", rc == 0 and rec and rec["VERDICT"] == "PASS" and next(v for k, v in rec["checks"].items() if k.startswith("K3"))["detail"]["n_extra"] == 30,
      (rc, rec["VERDICT"] if rec else out[-300:], {k: v["ok"] for k, v in (rec or {}).get("checks", {}).items()}))
_k3 = next((v for k, v in (rec or {}).get("checks", {}).items() if k.startswith("K3")), {}); check("G1b K3 detail records the early anchors' funding-NaN rows (> 0) — the criterion that FAILED the first real run", (_k3.get("detail") or {}).get("extra_rows_with_fund_nan", 0) > 0, _k3.get("detail"))
_l0 = os.path.getmtime(f"{R1}/controls/king_nomask/build.log"); _e0 = dict(BASE, VERIFY_ONLY="1"); rcv, outv, recv = controls(R1) if False else (None, None, None)
_ev = dict(BASE, R=R1, D=f"{R1}/device", PY=PY, CACHE=S["CACHE"], PANEL_SPLICE=S["DPANEL"], PANEL_KING=S["KPANEL"], RAW_PATCH="", SEPT_KING_FEA=f"{TMP}/sept_king/wide_fea_v4.npy", SEPT_KING_META=f"{TMP}/sept_king/wide_fea_v4_meta.npz", SEPT_DL_TARGETS=f"{TMP}/sept_dl/data/dlw_targets.npz", BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py", VERIFY_ONLY="1")
_rv = subprocess.run([PY, f"{R1}/device/fp2_controls.py"], env=_ev, cwd=TMP, capture_output=True, text=True); _recv = json.load(open(f"{R1}/controls/CONTROLS.json"))
check("G1c VERIFY_ONLY=1 re-evaluates on the existing rc-0 outputs: PASS, mode verify_only, previous_receipt recorded, no rebuild (build.log untouched)",
      _rv.returncode == 0 and _recv["VERDICT"] == "PASS" and _recv["mode"] == "verify_only" and _recv["previous_receipt"]["VERDICT"] == "PASS" and os.path.getmtime(f"{R1}/controls/king_nomask/build.log") == _l0, (_rv.returncode, _recv.get("mode"), _rv.stdout[-200:]))
# masked builds under the contract mask (symbol 7 False at 3 anchors; symbol 9 False everywhere)
mk = np.ones((S["nP"], S["NW"]), bool); mk[40:43, 7] = False; mk[:, 9] = False; MASK = maskfile("contract_mask", mk)
def masked_run(root, mask):
    build("pod_dlw_targets_raw_v2.py", f"{root}/dlw_v4raw", mask); build("pod_dlw_targets_raw_v2.py", f"{root}/dlw_hf3", mask); build("pod_fea_ext_clamp_v2.py", f"{root}/data", mask)
    for p in (f"{root}/dlw_v4raw/data/dlw_fea82.npz", f"{root}/dlw_hf3/data/dlw_fea82.npz"): open(p, "wb").write(b"fea82-identical")
    os.makedirs(f"{root}/f8_v4/data", exist_ok=True); open(f"{root}/f8_v4/data/f8_fea89.npz", "wb").write(b"fea89")
    os.makedirs(f"{root}/v4_gates", exist_ok=True)
    D = f"{root}/device"; (os.path.isdir(D) or device_dir(root)); preflight_for(root, D)
masked_run(R1, MASK)
def gate(which, R, mask=MASK, extra=None, month="2026-99"):
    D = f"{R}/device"
    if not os.path.isdir(D): device_dir(R, month)
    if not os.path.isfile(f"{R}/v4_gates/preflight.json"): preflight_for(R, D)
    e = dict(BASE, R=R, D=D, V4_MONTH=month, HOLE_CELLS=S["HOLE"], DLW_RAW=f"{R}/dlw_v4raw", DLW_CLIP=f"{R}/dlw_hf3", RAW_PATCH=S["RAWP"], CACHE=S["CACHE"], F8=f"{R}/f8_v4", MEMBER_MASK=mask,
             BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py", KING_FEA=f"{R}/data/wide_fea_v4.npy", KING_META=f"{R}/data/wide_fea_v4_meta.npz")
    e[f"STEP{which}_OUT"] = f"{R}/v4_gates/step{which}.json"; e.update(extra or {})
    r = subprocess.run([PY, f"{D}/fp2_gate_step{which}.py"], env=e, cwd=TMP, capture_output=True, text=True)
    rec = json.load(open(e[f"STEP{which}_OUT"])) if os.path.isfile(e[f"STEP{which}_OUT"]) else None
    return r.returncode, r.stdout + r.stderr, rec
rc1, o1, s1 = gate(1, R1); rc2, o2, s2 = gate(2, R1)
check("G2a STEP1 PASS: A (RAW==CLIP) + C (masked ⊆ control, removals mask-False, targets bitwise); receipt names the driver's 4 required inputs",
      rc1 == 0 and s1 and s1.get("VERDICT") == "PASS" and s1["C_masked_vs_control"]["cells_removed"] >= 3 and all(k in s1.get("inputs_sha256", s1.get("inputs", {})) for k in ("dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4")),
      (rc1, (s1 or {}).get("VERDICT"), (s1 or {}).get("C_masked_vs_control"), o1[-200:] if rc1 else ""))
check("G2b STEP2 PASS: builder identity (preflight == disk == controls), value cols bitwise on common members, y4/qvk bitwise, member index valid; names wide_fea_v4/_meta",
      rc2 == 0 and s2 and s2.get("VERDICT") == "PASS" and s2["C_masked_vs_control"]["value_cols_not_bitwise_rows"] == 0 and s2["C_masked_vs_control"]["cells_removed"] >= 3 and all(k in s2.get("inputs_sha256", s2.get("inputs", {})) for k in ("wide_fea_v4", "wide_fea_v4_meta")),
      (rc2, (s2 or {}).get("VERDICT"), (s2 or {}).get("C_masked_vs_control"), (s2 or {}).get("REFUSED"), o2[-200:] if rc2 else ""))
# G3 RED: builds made with a different mask than the contract's
R3 = f"{TMP}/R3"; os.makedirs(R3); assert controls(R3)[0] == 0
mk2 = np.ones((S["nP"], S["NW"]), bool); mk2[40:43, 11] = False; OTHER = maskfile("other_mask", mk2); masked_run(R3, OTHER)
rc1, o1, s1 = gate(1, R3); rc2, o2, s2 = gate(2, R3)
check("★★★ G3 RED: builds under a substituted mask ⇒ STEP1 FAIL and STEP2 FAIL with removed_not_masked_rows > 0 (rc 3, VERDICT FAIL)",
      rc1 == 3 and rc2 == 3 and s1 and s2 and s1["VERDICT"] == "FAIL" and s2["VERDICT"] == "FAIL" and s1["C_masked_vs_control"]["removed_not_masked_rows"] > 0 and s2["C_masked_vs_control"]["removed_not_masked_rows"] > 0,
      (rc1, rc2, (s1 or {}).get("VERDICT"), (s2 or {}).get("VERDICT")))
# G5 RED: preflight pins another builder sha
R5 = f"{TMP}/R5"; os.makedirs(R5); assert controls(R5)[0] == 0; masked_run(R5, MASK)
pf = json.load(open(f"{R5}/v4_gates/preflight.json")); pf["device_sha256"]["pod_fea_ext_clamp_v2.py"] = "0" * 64; json.dump(pf, open(f"{R5}/v4_gates/preflight.json", "w"))
rc2, o2, s2 = gate(2, R5)
check("★★★ G5 RED: preflight pins a different king builder sha ⇒ STEP2 UNAVAILABLE (builder identity mismatch names all three shas)", rc2 == 3 and s2 and s2["VERDICT"] == "UNAVAILABLE" and "builder_identity" in s2["REFUSED"], (rc2, (s2 or {}).get("REFUSED")))
# G6 RED (controls): a 'September' king build with one value altered
alt = f"{TMP}/sept_king_alt"; shutil.copytree(f"{TMP}/sept_king", alt)
F = np.load(f"{alt}/wide_fea_v4.npy"); M = np.load(f"{alt}/wide_fea_v4_meta.npz", allow_pickle=True); j = int(M["members"][10][0]); F[10, j, 0] = F[10, j, 0] + np.float16(0.5); np.save(f"{alt}/wide_fea_v4.npy", F)
R6 = f"{TMP}/R6"; os.makedirs(R6); rc, out, rec = controls(R6, sept_king=alt)
ks = {k: v["ok"] for k, v in (rec or {}).get("checks", {}).items()}
check("★★★ G6 RED (controls): one altered FEA value in the 'September' build ⇒ controls FAIL on K2 only (K1/K3/K4/D1/D2 still ok)", rc == 1 and rec and rec["VERDICT"] == "FAIL" and [k for k, v in ks.items() if not v] == [k for k in ks if k.startswith("K2")], (rc, ks))
# G7 RED: a controls receipt COPIED from another root (its outputs_path name that root's files) ⇒ UNAVAILABLE 'outside this root'
R7 = f"{TMP}/R7"; os.makedirs(R7); shutil.copytree(f"{R1}/controls", f"{R7}/controls"); masked_run(R7, MASK)
rc1, o1, s1 = gate(1, R7); rc2, o2, s2 = gate(2, R7)
check("★★★ G7 RED: controls receipt copied from another root ⇒ STEP1/STEP2 UNAVAILABLE ('control output outside this root') — a foreign receipt never certifies this root",
      rc1 == 3 and rc2 == 3 and s1 and s2 and s1["VERDICT"] == "UNAVAILABLE" and any("outside this root" in w for w in s1["REFUSED"]["controls_binding"]) and any("outside this root" in w for w in s2["REFUSED"]["controls_binding"]),
      (rc1, rc2, (s1 or {}).get("REFUSED"), None if s1 else o1[-600:]))
# ── F07 (independent review 2026-09-17): the controls must have run on THIS root's preflighted inputs ──
R10 = f"{TMP}/R10"; os.makedirs(R10); _rc10, _o10, _rec10 = controls(R10); masked_run(R10, MASK)          # its own PASS controls on THIS root (same inputs as G2)
_alt_cache = f"{TMP}/cache_other.npz"; shutil.copy2(S["CACHE"], _alt_cache)
preflight_for(R10, f"{R10}/device", cache=_alt_cache)                                          # then the preflight declares ANOTHER cache file than the controls hashed
rc1, o1, s1 = gate(1, R10)
check("★★★ G10 RED (F07): preflight declares a different CACHE path than the controls receipt ran on ⇒ STEP1 UNAVAILABLE 'controls_inputs_vs_preflight' naming CACHE",
      rc1 == 3 and s1 and s1["VERDICT"] == "UNAVAILABLE" and any("CACHE" in w for w in s1["REFUSED"].get("controls_inputs_vs_preflight", [])), (rc1, (s1 or {}).get("REFUSED"), None if s1 else o1[-300:]))

# G4 RED (LAST, in place on R1): control output rewritten after the receipt
R4 = R1
with open(f"{R4}/controls/king_nomask/wide_fea_v4.npy", "r+b") as f: f.seek(200); b = f.read(1); f.seek(200); f.write(bytes([b[0] ^ 1]))
with open(f"{R4}/controls/dl_nomask/data/dlw_targets.npz", "ab") as f: f.write(b"\0")
rc1, o1, s1 = gate(1, R4); rc2, o2, s2 = gate(2, R4)
check("★★★ G4 RED: control outputs changed after the receipt ⇒ STEP1/STEP2 UNAVAILABLE (controls binding refused: 'changed since the receipt'), receipts PASS=false",
      rc1 == 3 and rc2 == 3 and s1 and s2 and s1["VERDICT"] == "UNAVAILABLE" and s2["VERDICT"] == "UNAVAILABLE" and any("changed since the receipt" in w for w in s1["REFUSED"]["controls_binding"]) and any("changed since the receipt" in w for w in s2["REFUSED"]["controls_binding"]),
      (rc1, rc2, (s1 or {}).get("REFUSED"), (s2 or {}).get("REFUSED")))
# G8/G9 (AMENDMENT 8): when more than NTOP=400 names are eligible, masking pushes names ranked 401+ into the masked top-400 (ADDITIONS)
TMP8 = tempfile.mkdtemp(prefix="fp2g8_"); S8 = fp2_synth.make(TMP8, NW=430)   # default TT=8000: the DL alignment self-check needs > 120 anchors
_z8 = dict(np.load(S8["CACHE"], allow_pickle=True)); _d8 = _z8["data"]; _d8[:4000, 380:430, :] = np.nan; np.savez(S8["CACHE"], **{k: (_d8 if k == "data" else v) for k, v in _z8.items()})   # member counts must VARY (390 eligible in the first half, 430→400 later): a uniform count would persist a 2-D object members array
BASE8 = dict(BASE, PYTHONPATH=S8["shim"])
def build8(script, out, mask=""):
    os.makedirs(out, exist_ok=True); e = dict(BASE8, MEMBER_MASK_NPZ=mask)
    if "fea_ext" in script: e.update(CACHE_IN=S8["CACHE"], PANEL_IN=S8["KPANEL"], FEA_OUT=f"{out}/wide_fea_v4.npy", META_OUT=f"{out}/wide_fea_v4_meta.npz")
    else: e.update(DLWT_CACHE=S8["CACHE"], DLWT_PANEL=S8["DPANEL"], DLWT_OUT=out, DLWT_RET_CH="0", DLWT_RAW_PATCH="")
    r = subprocess.run([PY, f"{HERE}/{script}"], env=e, cwd=TMP8, capture_output=True, text=True); assert r.returncode == 0, (script, r.stdout[-400:], r.stderr[-400:])
build8("pod_fea_ext_clamp.py", f"{TMP8}/sept_king"); build8("pod_dlw_targets_raw.py", f"{TMP8}/sept_dl")
R8 = f"{TMP8}/R8"; os.makedirs(R8)
device_dir(R8); e8 = dict(BASE8, R=R8, D=f"{R8}/device", PY=PY, CACHE=S8["CACHE"], PANEL_SPLICE=S8["DPANEL"], PANEL_KING=S8["KPANEL"], RAW_PATCH="", SEPT_KING_FEA=f"{TMP8}/sept_king/wide_fea_v4.npy", SEPT_KING_META=f"{TMP8}/sept_king/wide_fea_v4_meta.npz", SEPT_DL_TARGETS=f"{TMP8}/sept_dl/data/dlw_targets.npz", BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py")
_r8 = subprocess.run([PY, f"{R8}/device/fp2_controls.py"], env=e8, cwd=TMP8, capture_output=True, text=True); assert _r8.returncode == 0, ("controls on the 430-symbol case", {k[:60]: (v["ok"], json.dumps(v["detail"], default=str)[:200]) for k, v in json.load(open(f"{R8}/controls/CONTROLS.json"))["checks"].items()} if os.path.isfile(f"{R8}/controls/CONTROLS.json") else (_r8.stdout + _r8.stderr)[-800:])
mk8 = np.ones((S8["nP"], S8["NW"]), bool); mk8[:, :20] = False   # 20 names masked everywhere: with 430 eligible the control top-400 loses them and the masked top-400 ADDS others
M8 = f"{TMP8}/mask8.npz"; np.savez(M8, ts=S8["grid"], symbols=np.array(S8["syms"]), mask=mk8, definition=np.array("m8"))
build8("pod_dlw_targets_raw_v2.py", f"{R8}/dlw_v4raw", M8); build8("pod_dlw_targets_raw_v2.py", f"{R8}/dlw_hf3", M8); build8("pod_fea_ext_clamp_v2.py", f"{R8}/data", M8)
for p in (f"{R8}/dlw_v4raw/data/dlw_fea82.npz", f"{R8}/dlw_hf3/data/dlw_fea82.npz"): open(p, "wb").write(b"fea82-identical")
os.makedirs(f"{R8}/f8_v4/data", exist_ok=True); open(f"{R8}/f8_v4/data/f8_fea89.npz", "wb").write(b"fea89"); os.makedirs(f"{R8}/v4_gates", exist_ok=True)
D8 = f"{R8}/device"; (os.path.isdir(D8) or device_dir(R8)); preflight_for(R8, D8, cache=S8["CACHE"], splice=S8["DPANEL"], king=S8["KPANEL"])
def gate8(which, R, extra=None):
    e = dict(BASE8, R=R, D=f"{R}/device", V4_MONTH="2026-99", HOLE_CELLS=S8["HOLE"], DLW_RAW=f"{R}/dlw_v4raw", DLW_CLIP=f"{R}/dlw_hf3", RAW_PATCH=S8["RAWP"], CACHE=S8["CACHE"], F8=f"{R}/f8_v4", MEMBER_MASK=M8,
             BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py", KING_FEA=f"{R}/data/wide_fea_v4.npy", KING_META=f"{R}/data/wide_fea_v4_meta.npz")
    e[f"STEP{which}_OUT"] = f"{R}/v4_gates/step{which}.json"; e.update(extra or {})
    r = subprocess.run([PY, f"{R}/device/fp2_gate_step{which}.py"], env=e, cwd=TMP8, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, (json.load(open(e[f"STEP{which}_OUT"])) if os.path.isfile(e[f"STEP{which}_OUT"]) else None)
rc1, o1, s1 = gate8(1, R8); rc2, o2, s2 = gate8(2, R8)
_c1 = (s1 or {}).get("C_masked_vs_control", {}); _c2 = (s2 or {}).get("C_masked_vs_control", {})
check("★★★ G8 truncation (430 eligible > NTOP 400): masking 20 names ⇒ the masked top-400 ADDS names ranked 401+ (rows_with_additions > 0, all at truncated control rows, all mask-True) ⇒ STEP1/STEP2 PASS; value cols bitwise on the intersection",
      rc1 == 0 and rc2 == 0 and _c1.get("rows_with_additions", 0) > 0 and _c1.get("additions_without_truncation_rows") == 0 and _c1.get("additions_not_mask_true_rows") == 0 and _c1.get("removed_not_masked_rows") == 0
      and _c2.get("rows_with_additions", 0) > 0 and _c2.get("value_cols_not_bitwise_rows") == 0, (rc1, rc2, {k: _c1.get(k) for k in ("rows_with_removals","rows_with_additions","cells_added","additions_without_truncation_rows","additions_not_mask_true_rows")}, o2[-160:] if rc2 else ""))
# G9 RED: an addition at a row whose CONTROL was not truncated (control < 400) ⇒ FAIL. Forge it: take the masked king meta and append a mask-True, non-member symbol at anchor 3 after shrinking the control row there.
# ── R09 (independent review round 2): the masked build must be EXACTLY the builders' rule — fp2_member_rule_check.py recomputes it from the cache ──
def mrc(cache, mask, ck, mk, cd, md, out, extra=None):
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "CACHE": cache, "MEMBER_MASK": mask, "CONTROL_KING_META": ck, "MASKED_KING_META": mk, "CONTROL_DL_TARGETS": cd, "MASKED_DL_TARGETS": md, "OUT_JSON": out}; e.update(extra or {})
    r = subprocess.run([PY, f"{HERE}/fp2_member_rule_check.py"], env=e, capture_output=True, text=True); j = json.load(open(out)) if os.path.isfile(out) else None
    return r.returncode, r.stdout + r.stderr, j
_ck8, _mk8, _cd8, _md8 = f"{R8}/controls/king_nomask/wide_fea_v4_meta.npz", f"{R8}/data/wide_fea_v4_meta.npz", f"{R8}/controls/dl_nomask/data/dlw_targets.npz", f"{R8}/dlw_v4raw/data/dlw_targets.npz"
rc, o, j = mrc(S8["CACHE"], M8, _ck8, _mk8, _cd8, _md8, f"{TMP8}/mrc_ok.json")
check("★★★ MR1 (R09) 430-symbol case: the replica reproduces BOTH control builds exactly and BOTH masked builds equal the expected rule ∧ mask → top-400 → ≥50 sets (truncated masked rows > 0) ⇒ PASS rc 0",
      rc == 0 and j and j["VERDICT"] == "PASS" and j["king"]["summary"]["control_reproduced"] and j["king"]["summary"]["masked_exact"] and j["dl"]["summary"]["control_reproduced"] and j["dl"]["summary"]["masked_exact"] and j["king"]["summary"]["n_truncated_masked_rows"] > 0,
      (rc, (j or {}).get("VERDICT"), (j or {}).get("king", {}).get("summary"), o[-300:] if not j else ""))
rc, o, j1 = mrc(S["CACHE"], MASK, f"{R1}/controls/king_nomask/wide_fea_v4_meta.npz", f"{R1}/data/wide_fea_v4_meta.npz", f"{R1}/controls/dl_nomask/data/dlw_targets.npz", f"{R1}/dlw_v4raw/data/dlw_targets.npz", f"{TMP}/mrc_r1.json")
check("★★ MR2 (R09) 80-symbol case (no truncation, mask drops names and anchors): PASS, expected_dropped_by_mask recorded", rc == 0 and j1 and j1["VERDICT"] == "PASS", (rc, (j1 or {}).get("VERDICT"), o[-300:] if not j1 else ""))
def tamper_meta(src, dst, fn):
    Z = np.load(src, allow_pickle=True); d = {k: Z[k] for k in Z.files}; d["E_ts"], d["members"] = fn(np.asarray(d["E_ts"]), np.array(list(d["members"]), dtype=object) if np.asarray(d["members"]).dtype == object else d["members"]); np.savez(dst, **d)
_Mm = np.load(_mk8, allow_pickle=True); _tr = [i for i, m in enumerate(_Mm["members"]) if len(m) == 400]; _i = _tr[0]
def _drop_one(E, M): M = M.copy(); M[_i] = np.asarray(M[_i])[:-1]; return E, M                                            # 399 at a truncated row
def _wrong_one(E, M):
    M = M.copy(); m = np.asarray(M[_i]); cand = [s for s in range(len(_Mm["members"][0]) + 1000) if s not in set(m.tolist()) and s < 430][0]; m2 = m.copy(); m2[-1] = cand; M[_i] = np.sort(m2); return E, M   # 400 but one wrong name
def _extra_one(E, M):
    M = M.copy(); m = np.asarray(M[_i]); cand = [s for s in range(430) if s not in set(m.tolist())][0]; M[_i] = np.sort(np.append(m, cand)); return E, M                    # 401
def _drop_anchor(E, M): return np.delete(E, _i), np.delete(M, _i)                                                                                                        # a kept anchor deleted
for name, fn, what in (("MR3 399 members at a truncated row (a replacement name missing)", _drop_one, "missing_in_build"), ("MR4 400 members but one wrong name (lower-ranked substitute)", _wrong_one, "extra_in_build"),
                       ("MR5 401 members (one extra)", _extra_one, "extra_in_build"), ("MR6 a kept anchor deleted although its masked pool ≥ MIN_MEM", _drop_anchor, "anchors_only_expected")):
    p = f"{TMP8}/mrc_{name[:3]}.npz"; tamper_meta(_mk8, p, fn); rc, o, jt = mrc(S8["CACHE"], M8, _ck8, p, _cd8, _md8, f"{TMP8}/mrc_{name[:3]}.json", extra={"SKIP_DL": "1"})
    km = (jt or {}).get("king", {}).get("masked", {})
    check(f"★★★ {name} ⇒ FAIL (the old subset/truncation rule would PASS this)", rc == 3 and jt and jt["VERDICT"] == "FAIL" and not km.get("PASS") and (km.get("rows_members_differ", 0) == 1 or km.get("n_anchors_only_expected", 0) == 1) and (what in json.dumps(km)),
          (rc, (jt or {}).get("VERDICT"), {k: km.get(k) for k in ("rows_members_differ", "n_anchors_only_expected", "n_anchors_only_build")}, km.get("first_differences", [])[:1]))
p = f"{TMP8}/mrc_MR7.npz"; tamper_meta(_ck8, p, _drop_one); rc, o, jt = mrc(S8["CACHE"], M8, p, _mk8, _cd8, _md8, f"{TMP8}/mrc_MR7.json", extra={"SKIP_DL": "1"})
check("★★★ MR7 a CONTROL meta that is not what the builder produced ⇒ control_reproduced False ⇒ FAIL (the replica is bound to the real builder, not free-floating)", rc == 3 and jt and not jt["king"]["summary"]["control_reproduced"], (rc, (jt or {}).get("king", {}).get("summary")))
Mc = np.load(f"{R8}/controls/king_nomask/wide_fea_v4_meta.npz", allow_pickle=True); Mm = np.load(f"{R8}/data/wide_fea_v4_meta.npz", allow_pickle=True)
_mm = np.array(Mm["members"], dtype=object); _mc = np.array(Mc["members"], dtype=object); j9 = 3
_cm = np.asarray(_mc[j9])[:-5]; _mc[j9] = _cm                                                   # control row now 395 members (not truncated)
_cand = [x for x in range(S8["NW"]) if x not in set(_cm.tolist()) and x not in set(np.asarray(_mm[j9]).tolist()) and mk8[j9, x]][:1]; _mm[j9] = np.append(np.asarray(_mm[j9]), np.int64(_cand[0]))
np.savez(f"{R8}/controls/king_nomask/wide_fea_v4_meta.npz", **{k: (Mc[k] if k != "members" else _mc) for k in Mc.files}); np.savez(f"{R8}/data/wide_fea_v4_meta.npz", **{k: (Mm[k] if k != "members" else _mm) for k in Mm.files})
_recp = json.load(open(f"{R8}/controls/CONTROLS.json")); _recp["outputs_sha256"]["control_king_meta"] = sha(f"{R8}/controls/king_nomask/wide_fea_v4_meta.npz"); json.dump(_recp, open(f"{R8}/controls/CONTROLS.json", "w"))   # rebind the (forged) control meta so the binding passes and the RULE is what fails
rc2, o2, s2 = gate8(2, R8); _c2 = (s2 or {}).get("C_masked_vs_control", {})
check("★★★ G9 RED: an added member at a row whose control was NOT truncated (395 < 400) ⇒ STEP2 FAIL with additions_without_truncation_rows == 1", rc2 == 3 and s2 and s2["VERDICT"] == "FAIL" and _c2.get("additions_without_truncation_rows") == 1, (rc2, {k: _c2.get(k) for k in ("rows_with_additions","additions_without_truncation_rows","additions_not_mask_true_rows")}))
shutil.rmtree(TMP8, ignore_errors=True)
shutil.rmtree(TMP, ignore_errors=True)

# ── F06 (independent review 2026-09-17): "mask not applied" products must not pass; dropped anchors must be explained ──
import importlib.util as _ilu
_gl = _ilu.spec_from_file_location("gl_f06", f"{HERE}/fp2_gate_lib.py"); GLm = _ilu.module_from_spec(_gl); _gl.loader.exec_module(GLm)
_E = np.array([100, 200, 300], np.int64); _MC = [np.arange(60), np.arange(60), np.arange(60)]                   # control: 60 members at 3 anchors
_MASK = np.ones((3, 60), bool); _MASK[:, 50:] = False                                                          # names 50..59 are mask-False everywhere
_ok = GLm.members_subset_check(_E, _MC, _E, [np.arange(50)] * 3, _MASK, ntop=400, MASK_c=_MASK)
check("★ F06-0 baseline green: masked build = control minus the mask-False names ⇒ PASS, retained_not_mask_true_rows 0", _ok["PASS"] and _ok["retained_not_mask_true_rows"] == 0, _ok)
_ig = GLm.members_subset_check(_E, _MC, _E, _MC, _MASK, ntop=400, MASK_c=_MASK)
check("★★★ F06-1 RED: a build that IGNORED the mask (members identical to the control, mask-False names retained) ⇒ FAIL with retained_not_mask_true_rows == 3 (was PASS before F06)",
      not _ig["PASS"] and _ig["retained_not_mask_true_rows"] == 3 and _ig["retained_not_mask_true_cells"] == 30, _ig)
_dr = GLm.members_subset_check(_E, _MC, _E[:2], [np.arange(50)] * 2, _MASK[:2], ntop=400, MASK_c=_MASK)
check("★★★ F06-2 RED: anchor 300 dropped while its control row has 50 mask-True members (≥ MIN_MEM 50) ⇒ dropped_unexplained_rows 1 ⇒ FAIL",
      not _dr["PASS"] and _dr["dropped_unexplained_rows"] == 1 and _dr["dropped_unexplained_first"][0]["ts"] == 300, _dr)
_M2 = _MASK.copy(); _M2[2, :] = False; _M2[2, :10] = True                                                      # at anchor 300 only 10 names are mask-True
_dx = GLm.members_subset_check(_E, _MC, _E[:2], [np.arange(50)] * 2, _M2[:2], ntop=400, MASK_c=_M2)
check("★★ F06-3 the same drop with only 10 mask-True control members (< 50) is EXPLAINED ⇒ PASS", _dx["PASS"] and _dx["dropped_unexplained_rows"] == 0, _dx)
_du = GLm.members_subset_check(_E, _MC, _E[:2], [np.arange(50)] * 2, _MASK[:2], ntop=400, MASK_c=None)
check("★★ F06-4 without control-axis mask rows a dropped anchor is UNVERIFIED ⇒ FAIL (never assumed explained)", not _du["PASS"] and _du["dropped_unverified_rows"] == 1, _du)



print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
