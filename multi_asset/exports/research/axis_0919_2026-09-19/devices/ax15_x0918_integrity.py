"""AX15 (axis_0919): after the x0918r build, re-hash every x0918 artifact listed in receipts/INVENTORY.json (written at 10:2xZ, before any x0918r
work) and require sha256 equality — the x0918 set must be byte-identical after the variant build. Pure reads.
env: AX_INVENTORY AX_RECEIPT"""
import os, json, hashlib, time
INV = os.environ["AX_INVENTORY"]; RPT = os.environ["AX_RECEIPT"]; assert not os.path.exists(RPT)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
inv = json.load(open(INV))["inventory"]; res = {}
for k, v in inv.items():
    if v.get("MISSING"): res[k] = {"path": v["path"], "status": "MISSING_IN_INVENTORY"}; continue
    s = sha(v["path"]); res[k] = {"path": v["path"], "inventory_sha256": v["sha256"], "now_sha256": s, "equal": s == v["sha256"], "mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(v["path"])))}
out = {"device": "ax15_x0918_integrity.py", "self_sha256": sha(os.path.abspath(__file__)), "inventory": INV, "inventory_sha256": sha(INV), "n": len(res),
       "n_equal": sum(1 for r in res.values() if r.get("equal")), "files": res, "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
out["PASS"] = out["n_equal"] == out["n"]
json.dump(out, open(RPT, "w"), indent=1)
print("AX15", "PASS" if out["PASS"] else "FAIL", out["n_equal"], "/", out["n"], flush=True)
