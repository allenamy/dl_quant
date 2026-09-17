#!/usr/bin/env python3
"""tests_fp2_gates.py — FP2-8 (2026-09-17): fp2_controls.py + fp2_gate_step1.py + fp2_gate_step2.py end-to-end on a synthetic cache, through their REAL entries.
  G1  controls (v2-no-mask vs 'September' = real v1 outputs) ⇒ PASS; K3 reports exactly the 30 pre-2016 anchors; D1 bitwise
  G2  masked builds + real preflight-shaped receipt ⇒ STEP1 PASS (A, C) and STEP2 PASS (I, C, Q); receipts carry the driver's required input names
  G3  RED: a masked build made with a DIFFERENT mask than the contract's ⇒ STEP1/STEP2 FAIL (removed member not mask-False) — the gate sees the substitution
  G4  RED (last, in place): control output rewritten after the receipt ⇒ both gates UNAVAILABLE (controls binding refused), receipt PASS=false
  G7  RED: a controls receipt copied from another root ⇒ UNAVAILABLE (outputs outside this root)
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
def controls(R, sept_king=f"{TMP}/sept_king", sept_dl=f"{TMP}/sept_dl"):
    e = dict(BASE, R=R, D=HERE, PY=PY, CACHE=S["CACHE"], PANEL_SPLICE=S["DPANEL"], PANEL_KING=S["KPANEL"], RAW_PATCH="", SEPT_KING_FEA=f"{sept_king}/wide_fea_v4.npy",
             SEPT_KING_META=f"{sept_king}/wide_fea_v4_meta.npz", SEPT_DL_TARGETS=f"{sept_dl}/data/dlw_targets.npz", BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py")
    r = subprocess.run([PY, f"{HERE}/fp2_controls.py"], env=e, cwd=TMP, capture_output=True, text=True)
    rec = json.load(open(f"{R}/controls/CONTROLS.json")) if os.path.isfile(f"{R}/controls/CONTROLS.json") else None
    return r.returncode, r.stdout + r.stderr, rec
R1 = f"{TMP}/R1"; os.makedirs(R1); rc, out, rec = controls(R1)
if not os.path.isdir(f"{R1}/controls"): print("UNAVAILABLE: controls produced no directory —", out[-900:]); sys.exit(3)
check("G1 controls PASS (rc 0, VERDICT PASS); K3 n_extra == 30; D1 bitwise", rc == 0 and rec and rec["VERDICT"] == "PASS" and rec["checks"]["K3 anchors only in v2 are EXACTLY the pre-2016-bar anchors (E_row in [576, 2016)) and their member features are finite"]["detail"]["n_extra"] == 30,
      (rc, rec["VERDICT"] if rec else out[-300:], {k: v["ok"] for k, v in (rec or {}).get("checks", {}).items()}))
# masked builds under the contract mask (symbol 7 False at 3 anchors; symbol 9 False everywhere)
mk = np.ones((S["nP"], S["NW"]), bool); mk[40:43, 7] = False; mk[:, 9] = False; MASK = maskfile("contract_mask", mk)
def masked_run(root, mask):
    build("pod_dlw_targets_raw_v2.py", f"{root}/dlw_v4raw", mask); build("pod_dlw_targets_raw_v2.py", f"{root}/dlw_hf3", mask); build("pod_fea_ext_clamp_v2.py", f"{root}/data", mask)
    for p in (f"{root}/dlw_v4raw/data/dlw_fea82.npz", f"{root}/dlw_hf3/data/dlw_fea82.npz"): open(p, "wb").write(b"fea82-identical")
    os.makedirs(f"{root}/f8_v4/data", exist_ok=True); open(f"{root}/f8_v4/data/f8_fea89.npz", "wb").write(b"fea89")
    os.makedirs(f"{root}/v4_gates", exist_ok=True)
    json.dump({"gate": "PREFLIGHT", "PASS": True, "device_sha256": {"pod_fea_ext_clamp_v2.py": sha(f"{HERE}/pod_fea_ext_clamp_v2.py"), "pod_dlw_targets_raw_v2.py": sha(f"{HERE}/pod_dlw_targets_raw_v2.py")}}, open(f"{root}/v4_gates/preflight.json", "w"))
masked_run(R1, MASK)
def gate(which, R, mask=MASK, extra=None):
    e = dict(BASE, R=R, D=HERE, HOLE_CELLS=S["HOLE"], DLW_RAW=f"{R}/dlw_v4raw", DLW_CLIP=f"{R}/dlw_hf3", RAW_PATCH=S["RAWP"], CACHE=S["CACHE"], F8=f"{R}/f8_v4", MEMBER_MASK=mask,
             BUILDER_TARGETS="pod_dlw_targets_raw_v2.py", BUILDER_KING_FEA="pod_fea_ext_clamp_v2.py", KING_FEA=f"{R}/data/wide_fea_v4.npy", KING_META=f"{R}/data/wide_fea_v4_meta.npz")
    e[f"STEP{which}_OUT"] = f"{R}/v4_gates/step{which}.json"; e.update(extra or {})
    r = subprocess.run([PY, f"{HERE}/fp2_gate_step{which}.py"], env=e, cwd=TMP, capture_output=True, text=True)
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
      (rc1, rc2, (s1 or {}).get("REFUSED")))
# G4 RED (LAST, in place on R1): control output rewritten after the receipt
R4 = R1
with open(f"{R4}/controls/king_nomask/wide_fea_v4.npy", "r+b") as f: f.seek(200); b = f.read(1); f.seek(200); f.write(bytes([b[0] ^ 1]))
with open(f"{R4}/controls/dl_nomask/data/dlw_targets.npz", "ab") as f: f.write(b"\0")
rc1, o1, s1 = gate(1, R4); rc2, o2, s2 = gate(2, R4)
check("★★★ G4 RED: control outputs changed after the receipt ⇒ STEP1/STEP2 UNAVAILABLE (controls binding refused: 'changed since the receipt'), receipts PASS=false",
      rc1 == 3 and rc2 == 3 and s1 and s2 and s1["VERDICT"] == "UNAVAILABLE" and s2["VERDICT"] == "UNAVAILABLE" and any("changed since the receipt" in w for w in s1["REFUSED"]["controls_binding"]) and any("changed since the receipt" in w for w in s2["REFUSED"]["controls_binding"]),
      (rc1, rc2, (s1 or {}).get("REFUSED"), (s2 or {}).get("REFUSED")))
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
