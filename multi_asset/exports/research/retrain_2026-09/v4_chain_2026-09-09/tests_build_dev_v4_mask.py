#!/usr/bin/env python3
"""tests_build_dev_v4_mask.py — FP2-8 (2026-09-17): build_dev_v4.py's self-check under a declared training member mask, through the REAL script on synthetic inputs.
  M1 unmasked meta, no env ⇒ DEV_V4_DONE (original rule, members bitwise)             M2 RED: masked meta, NO env ⇒ 'meta_newprod_v4 self-check FAIL' (members differ)
  M3 masked meta + DEV_MEMBER_MASK_NPZ ⇒ DEV_V4_DONE, receipt records rows_with_removals / cells_removed, members_ok_under_mask True
  M4 RED: masked meta + a mask that does NOT explain one removal ⇒ self-check FAIL (removed_not_mask_false_rows 1)
  M5 RED: masked meta where a member was ADDED (not subset) + mask ⇒ FAIL (members_not_subset_rows 1)"""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
rng = np.random.default_rng(7); NW = 12; syms = ["BTCUSDT"] + ["S%02dUSDT" % i for i in range(1, NW)]
TS0 = 1640995200; CTS = TS0 + 300 * np.arange(20000, dtype=np.int64); E = CTS[(CTS % 14400 == 0)][10:60]   # 50 anchors
def fixture(members_fn, tmp):
    R = f"{tmp}/R"; HC = f"{R}/health_check"; os.makedirs(f"{HC}/dev_alt/pod_backup_2026-08-21", exist_ok=True); os.makedirs(f"{R}/king", exist_ok=True)
    np.savez(f"{tmp}/cache.npz", ts=CTS, symbols=np.array(syms))
    y4s = rng.normal(0, 0.01, (len(E), NW)).astype(np.float32); qvk = rng.uniform(0, 1, (len(E), NW)).astype(np.float32)
    ref_members = np.empty(len(E), dtype=object)
    for i in range(len(E)): ref_members[i] = np.arange(NW, dtype=np.int64)
    members = np.empty(len(E), dtype=object)
    for i in range(len(E)): members[i] = members_fn(i, ref_members[i])
    os.makedirs(f"{R}/dlw_v4raw/data"); np.savez(f"{R}/dlw_v4raw/data/dlw_targets.npz", E_ts=E, y4s=y4s, symbols=np.array(syms))
    np.savez(f"{R}/king_meta.npz", E_ts=E, members=members, qvk=qvk, names=np.array(["a_v", "a_r"]))
    os.makedirs(f"{R}/ref"); np.savez(f"{R}/ref/meta_newprod_raw.npz", E_ts=E, members=ref_members, y4=y4s, qvk=qvk)
    np.savez(f"{R}/holes.npz", neigh_rows=np.zeros((0, 2), np.int64))
    os.makedirs(f"{R}/bundle"); np.save(f"{R}/bundle/slow_pred_pinned.npy", rng.normal(0, 1, (len(E), 829)).astype(np.float32))
    np.savez(f"{R}/prev_meta.npz", E_ts=E[:-6]); os.makedirs(f"{R}/prev_bundle"); np.save(f"{R}/prev_bundle/slow_pred_pinned.npy", rng.normal(0, 1, (len(E) - 6, 829)).astype(np.float32))
    os.makedirs(f"{R}/dlw_ext/data"); np.savez(f"{R}/dlw_ext/data/dlw_targets.npz", E_ts=E[:-3]); os.makedirs(f"{R}/f8_ext/preds")
    for s in ("42", "2027"): np.save(f"{R}/f8_ext/preds/f10_V2MAIN_s{s}.npy", rng.normal(0, 1, (len(E) - 3, 829)).astype(np.float32))
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "V4_R": R, "V4_HC": HC, "V4_KING_DIR": f"{R}/king", "KING_META": f"{R}/king_meta.npz", "DLW_RAW": f"{R}/dlw_v4raw",
           "CACHE": f"{tmp}/cache.npz", "HOLE_CELLS": f"{R}/holes.npz", "BUNDLE_OUT": f"{R}/bundle", "V4_REF_META": f"{R}/ref/meta_newprod_raw.npz", "V4_PREV_META": f"{R}/prev_meta.npz",
           "V4_PREV_BUNDLE": f"{R}/prev_bundle", "V4_DLW_EXT": f"{R}/dlw_ext", "V4_F8_EXT": f"{R}/f8_ext"}
    return R, env
def maskfile(tmp, mk): p = f"{tmp}/mask.npz"; np.savez(p, ts=E, symbols=np.array(syms), mask=mk); return p
def run(env): r = subprocess.run([PY, f"{HERE}/build_dev_v4.py"], env=env, capture_output=True, text=True); return r.returncode, r.stdout + r.stderr
def receipt(R): p = f"{R}/health_check/dev_v4/BUILD.json"; return json.load(open(p)) if os.path.isfile(p) else None
with tempfile.TemporaryDirectory() as t:
    R, env = fixture(lambda i, m: m, t); rc, out = run(env)
    check("M1 unmasked meta, no env ⇒ DEV_V4_DONE (members bitwise rule unchanged)", rc == 0 and "DEV_V4_DONE" in out and receipt(R)["selfcheck"]["members_equal_outside"] is True and "member_mask" not in receipt(R)["selfcheck"], (rc, out[-200:]))
MASK = np.ones((len(E), NW), bool); MASK[5:8, 3] = False; MASK[:, 9] = False
def masked(i, m): return np.array([j for j in m if MASK[i, j]], np.int64)
with tempfile.TemporaryDirectory() as t:
    R, env = fixture(masked, t); rc, out = run(env)
    check("★★★ M2 RED: masked meta WITHOUT the env ⇒ 'meta_newprod_v4 self-check FAIL' (members differ from the reference), no DEV_V4_DONE", rc != 0 and "self-check FAIL" in out and "DEV_V4_DONE" not in out, (rc, out[-160:]))
with tempfile.TemporaryDirectory() as t:
    R, env = fixture(masked, t); env["DEV_MEMBER_MASK_NPZ"] = maskfile(t, MASK); rc, out = run(env); sc = (receipt(R) or {}).get("selfcheck", {})
    check("M3 masked meta + DEV_MEMBER_MASK_NPZ ⇒ DEV_V4_DONE; receipt: members_ok_under_mask True, rows_with_removals 50, cells_removed 53, mask sha recorded",
          rc == 0 and "DEV_V4_DONE" in out and sc.get("members_ok_under_mask") is True and sc["member_mask"]["rows_with_removals"] == 50 and sc["member_mask"]["cells_removed"] == 53 and len(sc["member_mask"]["sha256"]) == 64, (rc, sc.get("member_mask"), out[-120:]))
with tempfile.TemporaryDirectory() as t:
    R, env = fixture(masked, t); other = MASK.copy(); other[6, 3] = True; env["DEV_MEMBER_MASK_NPZ"] = maskfile(t, other); rc, out = run(env)
    check("★★★ M4 RED: a mask that does NOT explain one removal (anchor 6 symbol 3 is mask-True yet removed) ⇒ self-check FAIL, removed_not_masked_rows 1 (AMENDMENT 8 + F06 receipt keys, shared with fp2_gate_lib)", rc != 0 and "self-check FAIL" in out and '"removed_not_masked_rows": 1' in out, (rc, out[-200:]))
def added(i, m): return np.append(masked(i, m), np.int64(NW - 1)) if i == 2 and (NW - 1) not in masked(i, m) else masked(i, m)
MASK2 = MASK.copy(); MASK2[:, NW - 1] = False
def masked2(i, m):
    base = np.array([j for j in m if MASK2[i, j]], np.int64)
    return np.append(base, np.int64(NW - 1)) if i == 2 else base   # anchor 2 carries a member the reference-under-mask would not: NOT a subset once… (reference = all NW)
with tempfile.TemporaryDirectory() as t:
    # reference has all NW; a masked build can only REMOVE. Make anchor 2 contain a symbol index outside the reference's set by shrinking the reference there.
    R, env = fixture(masked2, t); ref = np.load(f"{R}/ref/meta_newprod_raw.npz", allow_pickle=True); rm = np.array(ref["members"], dtype=object); rm[2] = np.arange(NW - 1, dtype=np.int64)
    np.savez(f"{R}/ref/meta_newprod_raw.npz", E_ts=ref["E_ts"], members=rm, y4=ref["y4"], qvk=ref["qvk"]); env["DEV_MEMBER_MASK_NPZ"] = maskfile(t, MASK2); rc, out = run(env)
    check("★★★ M5 RED: a masked build with a member the reference does not have at a NON-truncated reference row ⇒ self-check FAIL, additions_without_truncation_rows 1 (AMENDMENT 8: additions are legal only at rows the reference truncated at NTOP)", rc != 0 and "self-check FAIL" in out and '"additions_without_truncation_rows": 1' in out, (rc, out[-200:]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
