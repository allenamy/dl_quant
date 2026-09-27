"""Collect one anchor's shadow arms from the sandbox into the append-only store, with the identity control.
IDENTITY: the recomputed in-service combo (LIVE_REPLAY) must equal the live state/target_combo/<A>.json weights exactly at the file's own
precision (8 dp, the same names) and its w3m must equal w3_masked (6 dp). Failure => exit 2 and the anchor is stored as VOID
(arms are kept for forensics but the P&L device refuses VOID anchors).
usage: shadow_ab_collect.py <A> <live target_combo json> <sandbox> <stage rc> <AB home> <receipt out>   exit 0 ok / 2 identity fail / 3 unavailable"""
import os, sys, json, hashlib, shutil, time
import numpy as np
A, LIVE, SB, RC, AB, OUT = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def write_verified(p, obj):
    tmp = p + ".tmp"; data = json.dumps(obj, indent=1).encode()
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)
    with open(p, "rb") as f: assert f.read() == data, "receipt read-back mismatch"
    return hashlib.sha256(data).hexdigest()


rec = {"device": "shadow_ab_collect.py", "self_sha256": sha(os.path.abspath(__file__)), "anchor": int(A),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stage_rc": RC}
out_dir = os.path.join(SB, "ab_out"); meta_p = os.path.join(out_dir, "AB_META.json")
if not os.path.exists(os.path.join(SB, "ISOLATION_OK")) or RC != 0 or not os.path.exists(meta_p):
    rec["STATUS"] = "UNAVAILABLE"; rec["why"] = {"isolation_ok": os.path.exists(os.path.join(SB, "ISOLATION_OK")), "rc": RC, "meta": os.path.exists(meta_p)}
    write_verified(OUT, rec); print("SHADOW_AB_COLLECT UNAVAILABLE", rec["why"]); sys.exit(3)
meta = json.load(open(meta_p)); names = meta["names"]
z = np.load(os.path.join(out_dir, "LIVE_REPLAY_combo.npz"))
mine = {names[int(j)]: round(float(v), 8) for j, v in zip(z["idx"], z["val"])}
mine = {k: v for k, v in mine.items() if abs(v) > 1e-9}
live = json.load(open(LIVE)); lw = live["weights"]
diff_names = sorted(set(mine) ^ set(lw)); diff_vals = [k for k in set(mine) & set(lw) if mine[k] != lw[k]]
w3_ok = [round(x, 6) for x in meta["w3m"]] == [round(x, 6) for x in live["w3_masked"]]
ident = (not diff_names) and (not diff_vals) and w3_ok and int(live["anchor_ts"]) == int(A)
rec["identity"] = {"PASS": bool(ident), "n_live": len(lw), "n_replay": len(mine), "names_only_one_side": diff_names[:20],
                   "n_value_mismatch": len(diff_vals), "w3m_equal": w3_ok, "live_file": LIVE, "live_sha256": sha(LIVE)}
dest = os.path.join(AB, "state", A)
if os.path.exists(os.path.join(dest, "COLLECT.json")):
    rec["STATUS"] = "ALREADY_STORED (append-only store; not overwritten)"; write_verified(OUT, rec); print("SHADOW_AB_COLLECT", rec["STATUS"]); sys.exit(0)
os.makedirs(dest, exist_ok=True)
stored = {}
for fn in sorted(os.listdir(out_dir)):
    if fn.endswith(".npz") or fn == "AB_META.json":
        shutil.copyfile(os.path.join(out_dir, fn), os.path.join(dest, fn)); stored[fn] = sha(os.path.join(dest, fn))
        assert stored[fn] == sha(os.path.join(out_dir, fn)), f"copy mismatch {fn}"
for fn in ("HOOK.json", "run.log"):
    if os.path.exists(os.path.join(SB, fn)): shutil.copyfile(os.path.join(SB, fn), os.path.join(dest, fn)); stored[fn] = sha(os.path.join(dest, fn))
rec["stored"] = stored; rec["arms"] = meta["arms"]; rec["STATUS"] = "OK" if ident else "VOID_IDENTITY_FAIL"
rec["receipt_sha256"] = write_verified(os.path.join(dest, "COLLECT.json"), rec)
write_verified(OUT, rec)
print("SHADOW_AB_COLLECT", rec["STATUS"], json.dumps(rec["identity"])[:200])
sys.exit(0 if ident else 2)
