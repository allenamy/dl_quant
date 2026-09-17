"""fp2_gate_lib.py — shared pieces of the FP2 gates (fp2_gate_step1.py / fp2_gate_step2.py), 2026-09-17.
CONTROLS binding: the receipt $R/controls/CONTROLS.json written by fp2_controls.py must be PASS, its named outputs/inputs must hash to what it
recorded NOW (a moved or rebuilt control is refused), and the builder it ran must be the builder the contract selects (D/$BUILDER_*)."""
import hashlib, json, os, sys
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
    # F07 (independent review 2026-09-17): the receipt's producer and EVERY individual check are bound, not just the top-level verdict
    dev = os.path.join(D, "fp2_controls.py")
    if not os.path.isfile(dev): why.append("fp2_controls.py missing in D")
    elif sha256_file(dev) != c.get("self_sha256"): why.append(f"controls device on disk {sha256_file(dev)[:12]} != receipt self_sha256 {str(c.get('self_sha256'))[:12]}")
    bad = [k for k, v in (c.get("checks") or {}).items() if v.get("ok") is not True]
    if not (c.get("checks")): why.append("receipt has no checks")
    if bad: why.append("controls checks not all True: " + "; ".join(k[:40] for k in bad))
    runs = c.get("runs") or {}
    if set(runs) != {"king", "dl"} or not all(v.get("rc") == 0 for v in runs.values()): why.append("receipt runs must be exactly {king, dl} with rc 0")
    rec["controls_device_sha256"] = c.get("self_sha256"); rec["controls_mode"] = c.get("mode")
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
def check_scope(D, gate):
    """F07: the contract approves an FP2 gate variant for a SPECIFIC month contract and root. The variant refuses to run under any other (V4_MONTH, R)."""
    try: c = json.load(open(os.path.join(D, "ELIGIBILITY_CONTRACT.json")))
    except Exception as e: return [f"contract unreadable: {e!r}"]   # noqa: BLE001
    me = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    var = ((c.get("gates") or {}).get(gate) or {}).get("approved_variants") or {}
    ent = var.get(me) or next((v for k, v in var.items() if k == me), None)
    if not ent: return [f"no approved_variants entry for {me} under gate {gate}"]
    sc = ent.get("scope") or {}
    if not sc: return ["variant has no scope binding (V4_MONTH, R) in the contract"]
    why = []
    if os.environ.get("V4_MONTH") != sc.get("V4_MONTH"): why.append(f"scope V4_MONTH {sc.get('V4_MONTH')!r} != running {os.environ.get('V4_MONTH')!r}")
    if os.path.realpath(os.environ.get("R", "")) != os.path.realpath(sc.get("R", "/nonexistent")): why.append(f"scope R {sc.get('R')!r} != running {os.environ.get('R')!r}")
    return why
def bind_inputs_to_preflight(R, c_inputs_sha, c_inputs_path):
    """F07: the controls ran on THIS root's declared inputs. The driver's preflight records each contract input as {path, bytes} (it does not hash
    the 2 GB cache); so the binding is: same realpath as the preflight's input, same byte size now, and the bytes on disk NOW hash to what the
    controls receipt recorded (so neither the controls nor the preflight saw a different file than the one the gates will read)."""
    pf = os.path.join(R, "v4_gates", "preflight.json"); why = []
    try: P = json.load(open(pf))
    except Exception as e: return [f"preflight receipt unreadable: {e!r}"]   # noqa: BLE001
    if P.get("PASS") is not True: why.append(f"preflight PASS={P.get('PASS')!r}")
    pin = P.get("inputs") or {}
    for k, K in (("cache", "CACHE"), ("panel_splice", "PANEL_SPLICE"), ("panel_king", "PANEL_KING"), ("raw_patch", "RAW_PATCH")):
        cp = (c_inputs_path or {}).get(k) or ""; cs = (c_inputs_sha or {}).get(k)
        if k == "raw_patch" and not cp and K not in pin: continue                       # optional-empty on both sides
        e = pin.get(K)
        if not e or not e.get("path"): why.append(f"preflight has no input {K}"); continue
        if not cp: why.append(f"controls receipt has no path for {k}"); continue
        if os.path.realpath(e["path"]) != os.path.realpath(cp): why.append(f"{K}: preflight {e['path']} != controls {cp}"); continue
        if not os.path.isfile(cp): why.append(f"{K}: file missing now: {cp}"); continue
        if e.get("bytes") is not None and os.path.getsize(cp) != e["bytes"]: why.append(f"{K}: size now {os.path.getsize(cp)} != preflight {e['bytes']}"); continue
        if not cs or sha256_file(cp) != cs: why.append(f"{K}: bytes on disk != controls receipt sha {str(cs)[:12]}")
    return why
def mask_rows(mask_path, E_ts, symbols):
    """the contract's MEMBER_MASK rows at the given anchors; refuses a missing anchor or a symbol-axis mismatch (returns (None, why))."""
    Mz = np.load(mask_path, allow_pickle=True); msy = [str(s) for s in Mz["symbols"]]
    if msy != [str(s) for s in symbols]: return None, "mask symbols != build symbols"
    mts = Mz["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(mts)}; miss = [int(t) for t in E_ts if int(t) not in row]
    if miss: return None, f"{len(miss)} anchors have no mask row (first {miss[:3]})"
    return np.asarray(Mz["mask"])[[row[int(t)] for t in E_ts]], None
def members_subset_check(E_c, M_c, E_m, M_m, MASK_m, ntop=400, MASK_c=None, min_mem=50):
    """control (unmasked) vs masked build on the anchor axis (AMENDMENT 8, truncation-aware; F06 mask-applied evidence):
      masked anchors ⊆ control anchors (a mask can drop an anchor below MIN_MEM, never add one);
      per common anchor: REMOVED = control − masked must all be mask-False;
      ADDED = masked − control is allowed ONLY when the control row was truncated (len(control) == ntop: names ranked ntop+1.. in the
      unmasked pool enter the masked top-ntop once masked names leave) and every added name is mask-True; otherwise the row FAILs.
    F06 (independent review 2026-09-17) — two properties a build that IGNORED the mask would still satisfy under the rules above, now required:
      (i) every member the masked build RETAINS is mask-True at that anchor (a mask-False name kept anywhere ⇒ FAIL);
      (ii) every anchor the masked build DROPS is explained: the control row has < min_mem mask-True members (else the masked builder,
           which keeps the mask-True eligible names and truncates at ntop, could not have fallen below its MIN_MEM); with MASK_c absent a
           dropped anchor is UNVERIFIED and FAILs — never assumed explained.
    MASK_m = mask rows aligned to E_m; MASK_c = mask rows aligned to E_c (or None). Returns dict."""
    rc = {int(t): i for i, t in enumerate(E_c)}; only_m = [int(t) for t in E_m if int(t) not in rc]; only_c = [int(t) for t in E_c if int(t) not in {int(x) for x in E_m}]
    out = {"n_control": int(len(E_c)), "n_masked": int(len(E_m)), "anchors_only_masked": len(only_m), "anchors_only_control(dropped_by_mask)": len(only_c), "dropped_first_utc": None,
           "rows_with_removals": 0, "cells_removed": 0, "removed_not_masked_rows": 0, "rows_with_additions": 0, "cells_added": 0,
           "additions_without_truncation_rows": 0, "additions_not_mask_true_rows": 0, "ntop": int(ntop), "min_mem": int(min_mem),
           "retained_not_mask_true_rows": 0, "retained_not_mask_true_cells": 0, "dropped_unexplained_rows": 0, "dropped_unverified_rows": 0, "dropped_unexplained_first": []}
    if only_c:
        import time; out["dropped_first_utc"] = time.strftime("%F %H:%MZ", time.gmtime(min(only_c)))
        if MASK_c is None: out["dropped_unverified_rows"] = len(only_c)
        else:
            for t in only_c:
                i = rc[t]; n_true = sum(1 for sidx in np.asarray(M_c[i]).tolist() if bool(MASK_c[i, int(sidx)]))
                if n_true >= min_mem:
                    out["dropped_unexplained_rows"] += 1
                    if len(out["dropped_unexplained_first"]) < 5: out["dropped_unexplained_first"].append({"ts": int(t), "control_members": int(len(M_c[i])), "mask_true": int(n_true)})
    for j, t in enumerate(E_m):
        i = rc.get(int(t))
        if i is None: continue
        a = set(int(x) for x in np.asarray(M_c[i]).tolist()); b = set(int(x) for x in np.asarray(M_m[j]).tolist())
        rem = a - b; add = b - a
        kept_false = [sidx for sidx in b if not bool(MASK_m[j, sidx])]
        if kept_false: out["retained_not_mask_true_rows"] += 1; out["retained_not_mask_true_cells"] += len(kept_false)
        if rem:
            out["rows_with_removals"] += 1; out["cells_removed"] += len(rem)
            if any(bool(MASK_m[j, s]) for s in rem): out["removed_not_masked_rows"] += 1
        if add:
            out["rows_with_additions"] += 1; out["cells_added"] += len(add)
            if len(a) != ntop: out["additions_without_truncation_rows"] += 1
            if any(not bool(MASK_m[j, s]) for s in add): out["additions_not_mask_true_rows"] += 1
    out["PASS"] = (out["anchors_only_masked"] == 0 and out["removed_not_masked_rows"] == 0 and out["additions_without_truncation_rows"] == 0 and out["additions_not_mask_true_rows"] == 0
                   and out["retained_not_mask_true_rows"] == 0 and out["dropped_unexplained_rows"] == 0 and out["dropped_unverified_rows"] == 0)
    return out
