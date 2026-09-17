#!/usr/bin/env python3
"""mk_prev_sha_record.py <previous month contract .env> <out.json> — the {path: sha256} record of the previous month's ROLLED artifacts
(the eight keys v4_gate_roll_paths.ROLLED), read from the contract as DATA (same $R expansion as the gate), hashed guarded (dataless /
short-read refused). Written once, after that month's chain finished, then frozen and declared as PREV_SHA_JSON in the next contract (FP2-3)."""
import hashlib, json, os, re, stat, sys
ROLLED = ("CACHE", "PANEL_SPLICE", "PANEL_KING", "RAW_PATCH", "HOLE_CELLS", "FUND_AUG", "EMA_STATE_JSON", "EXPORT_PANEL")
def read_env(path):
    kv = {}
    for line in open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s: continue
        k, v = s.split("=", 1); v = v.strip()
        if "R" in kv: v = v.replace("${R}", kv["R"]).replace("$R", kv["R"])
        kv[k] = v
    return kv
def gsha(p):
    st = os.stat(p)
    if st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000): raise SystemExit(f"REFUSE {p}: dataless")
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit(f"REFUSE {p}: short read")
    return h.hexdigest()
if __name__ == "__main__":
    env, out = sys.argv[1:3]; kv = read_env(env); rec = {}; missing = []
    for k in ROLLED:
        p = kv.get(k, "")
        if not p or not os.path.isfile(p): missing.append(k); continue
        rec[p] = gsha(p)
    if missing: print("REFUSE: previous contract has missing/blank/absent rolled paths:", missing); sys.exit(3)
    json.dump(rec, open(out, "w"), indent=1); print(f"PREV_SHA record: {len(rec)} paths -> {out}")
