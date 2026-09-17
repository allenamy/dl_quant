"""fp2_gate_lib.py — shared pieces of the FP2 gates (fp2_gate_step1.py / fp2_gate_step2.py), 2026-09-17.
CONTROLS binding: the receipt $R/controls/CONTROLS.json written by fp2_controls.py must be PASS, its named outputs/inputs must hash to what it
recorded NOW (a moved or rebuilt control is refused), and the builder it ran must be the builder the contract selects (D/$BUILDER_*)."""
import hashlib, json, os
import numpy as np
def sha256_file(p, chunk=16 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""): h.update(b)
    return h.hexdigest()
def bind_controls(R, D, builder_key, builder_name, rehash=("control_king_fea", "control_king_meta", "control_dl_targets")):
    """returns (record dict, list of failure strings). record carries the receipt path/sha and the control output paths."""
    why = []; rec = {"receipt": os.path.join(R, "controls", "CONTROLS.json")}
    if not os.path.isfile(rec["receipt"]): return rec, ["controls receipt missing: " + rec["receipt"]]
    rec["receipt_sha256"] = sha256_file(rec["receipt"]); c = json.load(open(rec["receipt"]))
    if c.get("gate") != "FP2_CONTROLS": why.append("receipt gate != FP2_CONTROLS")
    if c.get("VERDICT") != "PASS" or c.get("PASS") is not True: why.append(f"controls VERDICT {c.get('VERDICT')!r} (need PASS)")
    inside = os.path.join(os.path.realpath(R), "controls") + os.sep   # a receipt copied from ANOTHER root names that root's files: refused, never re-hashed as ours
    for k in rehash:
        p = (c.get("outputs_path") or {}).get(k); s = (c.get("outputs_sha256") or {}).get(k)
        if not p or not os.path.isfile(p): why.append(f"control output missing: {k}={p}"); continue
        if not os.path.realpath(p).startswith(inside): why.append(f"control output outside this root: {k}={p} (root {R})"); continue
        if sha256_file(p) != s: why.append(f"control output changed since the receipt: {k}")
        rec[k] = p
    bpath = os.path.join(D, builder_name); bsha = (c.get("inputs_sha256") or {}).get(builder_key)
    if not os.path.isfile(bpath): why.append(f"selected builder missing in D: {bpath}")
    elif sha256_file(bpath) != bsha: why.append(f"controls ran builder {str(bsha)[:12]} but the contract selects {builder_name} = {sha256_file(bpath)[:12]}")
    rec["builder"] = {"key": builder_key, "name": builder_name, "sha256": bsha}
    rec["controls_checks"] = {k: v.get("ok") for k, v in (c.get("checks") or {}).items()}
    return rec, why
def mask_rows(mask_path, E_ts, symbols):
    """the contract's MEMBER_MASK rows at the given anchors; refuses a missing anchor or a symbol-axis mismatch (returns (None, why))."""
    Mz = np.load(mask_path, allow_pickle=True); msy = [str(s) for s in Mz["symbols"]]
    if msy != [str(s) for s in symbols]: return None, "mask symbols != build symbols"
    mts = Mz["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(mts)}; miss = [int(t) for t in E_ts if int(t) not in row]
    if miss: return None, f"{len(miss)} anchors have no mask row (first {miss[:3]})"
    return np.asarray(Mz["mask"])[[row[int(t)] for t in E_ts]], None
def members_subset_check(E_c, M_c, E_m, M_m, MASK_m):
    """control (unmasked) vs masked build on the anchor axis: masked anchors ⊆ control anchors; per common anchor masked members ⊆ control members and
    (control − masked) ⊆ {mask False}. MASK_m = mask rows aligned to E_m. Returns dict."""
    rc = {int(t): i for i, t in enumerate(E_c)}; only_m = [int(t) for t in E_m if int(t) not in rc]; only_c = [int(t) for t in E_c if int(t) not in {int(x) for x in E_m}]
    out = {"n_control": int(len(E_c)), "n_masked": int(len(E_m)), "anchors_only_masked": len(only_m), "anchors_only_control(dropped_by_mask)": len(only_c), "dropped_first_utc": None,
           "members_not_subset_rows": 0, "removed_not_masked_rows": 0, "rows_with_removals": 0, "cells_removed": 0}
    if only_c:
        import time; out["dropped_first_utc"] = time.strftime("%F %H:%MZ", time.gmtime(min(only_c)))
    for j, t in enumerate(E_m):
        i = rc.get(int(t))
        if i is None: continue
        a = set(int(x) for x in np.asarray(M_c[i]).tolist()); b = set(int(x) for x in np.asarray(M_m[j]).tolist())
        if not b <= a: out["members_not_subset_rows"] += 1; continue
        rem = a - b
        if rem:
            out["rows_with_removals"] += 1; out["cells_removed"] += len(rem)
            if any(bool(MASK_m[j, s]) for s in rem): out["removed_not_masked_rows"] += 1
    out["PASS"] = out["anchors_only_masked"] == 0 and out["members_not_subset_rows"] == 0 and out["removed_not_masked_rows"] == 0
    return out
