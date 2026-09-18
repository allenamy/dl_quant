#!/usr/bin/env python3
"""compare the archived target_live/<A>.json (what the executor traded) with the sandbox replay's target (same producer code, snapshotted rolling
state, archived king file). Every key must be equal except written_utc; weights compared name by name as exact floats (max |Δw| reported);
weights_sha of the archived doc must equal sha256 of the SANDBOX weights_combo/<A>.npz bytes (the replay rebuilt the same npz)."""
import hashlib, json, os, sys, time
A, ARCH, REP, SB, RC, OUT = sys.argv[1:7]; A = int(A)
rec = {"device": "combo_parity_compare.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "anchor_ts": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "archived": ARCH, "replayed": REP, "sandbox": SB, "combo_stage_rc": int(RC), "why": []}
if int(RC) != 0: rec["why"].append(f"combo_stage rc {RC} in sandbox")
if not os.path.isfile(REP): rec["why"].append("replay wrote no target (COMBO_LIVE abort or bail; see run.log)")
else:
    a = json.load(open(ARCH)); b = json.load(open(REP)); rec["archived_sha"] = hashlib.sha256(open(ARCH, "rb").read()).hexdigest(); rec["replayed_sha"] = hashlib.sha256(open(REP, "rb").read()).hexdigest()
    # ★ R08 (independent review 2026-09-18): bind BOTH documents to the REQUESTED anchor and schema — two files that agree with each other but
    #   describe another anchor (e.g. both A−4h) are not parity for A
    rec["anchor_identity"] = {"requested": A, "archived": a.get("anchor_ts"), "replayed": b.get("anchor_ts"), "schema_archived": a.get("schema"), "schema_replayed": b.get("schema")}
    if a.get("anchor_ts") != A: rec["why"].append(f"archived doc anchor_ts {a.get('anchor_ts')} != requested {A}")
    if b.get("anchor_ts") != A: rec["why"].append(f"replayed doc anchor_ts {b.get('anchor_ts')} != requested {A}")
    if a.get("schema") != "wide_target_v1" or b.get("schema") != "wide_target_v1": rec["why"].append(f"schema not wide_target_v1: {a.get('schema')} / {b.get('schema')}")
    keys = sorted(set(a) | set(b)); diff_keys = []
    for k in keys:
        if k == "written_utc": continue
        if k not in a or k not in b:
            # producer-version delta: FP2-6b added `f10_sha` to the target on 2026-09-17 (producer patched 13:0xZ, first written at the 16Z anchor); an
            # archive written before that by the unpatched producer lacks the key while the replay (patched code) carries it — recorded, not a mismatch
            if k == "f10_sha" and k in b and k not in a and str(a.get("written_utc", "")) < "2026-09-17T16:00:00Z": rec.setdefault("version_delta", []).append("f10_sha added by the FP2-6b producer patch after this archive was written"); continue
            diff_keys.append(f"{k}: present only in {'archived' if k in a else 'replay'}"); continue
        if k == "weights":
            wa, wb = a[k], b[k]; names = sorted(set(wa) | set(wb)); nd = 0; mx = 0.0
            for n in names:
                if n not in wa or n not in wb or float(wa[n]) != float(wb[n]): nd += 1; mx = max(mx, abs(float(wa.get(n, 0.0)) - float(wb.get(n, 0.0))))
            rec["weights"] = {"n_archived": len(wa), "n_replay": len(wb), "n_differing": nd, "max_abs_dw": mx}
            if nd: diff_keys.append(f"weights: {nd} names differ, max|dw| {mx:.3e}")
        elif a[k] != b[k]: diff_keys.append(f"{k}: archived {str(a[k])[:24]} != replay {str(b[k])[:24]}")
    rec["diff_keys"] = diff_keys; rec["why"] += diff_keys
    wnpz = f"{SB}/wide_shadow/state/weights_combo/{A}.npz"
    if os.path.isfile(wnpz):
        ws = hashlib.sha256(open(wnpz, "rb").read()).hexdigest(); rec["replay_weights_npz_sha"] = ws
        if ws != a.get("weights_sha"): rec["why"].append("replay weights npz sha != archived doc.weights_sha")
    else: rec["why"].append("replay wrote no weights_combo npz")
    rec["written_utc"] = {"archived": a.get("written_utc"), "replay": b.get("written_utc")}
pages = f"{SB}/dl_quant_live/live/STUB_PAGES.log"; rec["stub_pages"] = open(pages).read().splitlines() if os.path.isfile(pages) else []
rec["VERDICT"] = "PARITY" if not rec["why"] else "MISMATCH"
json.dump(rec, open(OUT, "w"), indent=1)
print(f"PARITY_{rec['VERDICT']} anchor {A} why={rec['why'][:4]} weights={rec.get('weights')}")
sys.exit(0 if rec["VERDICT"] == "PARITY" else 2)
