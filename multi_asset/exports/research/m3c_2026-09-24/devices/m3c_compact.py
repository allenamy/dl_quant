#!/usr/bin/env python3
"""m3c_compact.py — disk-footprint device for M3c (pod2 has no room for full path files: /dev/shm is closed to M3c, /root has < 1 GB).
For every PATH_*_seed_NN.npz in <run_dir> (the certified launcher's output, 32 files), writes <run_dir>/COMPACT/PATH_*_seed_NN.npz holding ONLY
the arrays that bt_tables.series_from_path and m3_readout.py read — A, nav0, navm0, navm1, price_trade, funding, fee, turnover, unk_excluded,
unk_price, unk_funding, unk_notional, n_flatten_events, n_stop_events, status, end_dust_usdt, nav5_t0, nav5_main — each asserted BITWISE equal
to the full file's array after the write (read back); then, only if every kept array matched, deletes the full npz. The path .json files
(audits, device shas, npz_sha256 of the FULL file) stay next to the compact files. Receipt: <run_dir>/COMPACT/COMPACT_RECEIPT.json with the
full file's sha256 (and that it equals the path json's npz_sha256), the compact file's sha256, and the kept keys.
Refuses a directory without exactly 32 path npz; never touches anything outside <run_dir>.
usage: /workspace/venv/bin/python -B m3c_compact.py <run_dir>
"""
import os, sys, json, hashlib, time
import numpy as np

KEEP = ("A", "nav0", "navm0", "navm1", "price_trade", "funding", "fee", "turnover", "unk_excluded", "unk_price", "unk_funding", "unk_notional",
        "n_flatten_events", "n_stop_events", "status", "end_dust_usdt", "nav5_t0", "nav5_main")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


d = os.path.abspath(sys.argv[1]); cd = os.path.join(d, "COMPACT"); os.makedirs(cd, exist_ok=True)
files = sorted(f for f in os.listdir(d) if f.startswith("PATH_") and f.endswith(".npz"))
if len(files) != 32: raise SystemExit(f"{d}: {len(files)} full path files, expected 32 — refused")
rec = {"device": "m3c_compact.py", "self_sha256": sha(os.path.abspath(__file__)), "run_dir": d, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "kept_keys": list(KEEP), "files": {}}
for f in files:
    p = os.path.join(d, f); js = json.load(open(p[:-4] + ".json")); fs = sha(p)
    if js.get("npz_sha256") != fs: raise SystemExit(f"{f}: full npz sha {fs[:16]} != its path json {str(js.get('npz_sha256'))[:16]} — refused")
    Z = np.load(p); arr = {k: Z[k] for k in KEEP}
    cp = os.path.join(cd, f); np.savez(cp[:-4] + ".tmp.npz", **arr); os.replace(cp[:-4] + ".tmp.npz", cp)
    R = np.load(cp)
    ok = sorted(R.files) == sorted(KEEP) and all(np.ascontiguousarray(R[k]).tobytes() == np.ascontiguousarray(arr[k]).tobytes() and R[k].dtype == arr[k].dtype
                                                  and R[k].shape == arr[k].shape for k in KEEP)
    if not ok: raise SystemExit(f"{f}: compact read-back differs — full file kept")
    rec["files"][f] = {"full_sha256": fs, "compact_sha256": sha(cp), "full_bytes": os.path.getsize(p), "compact_bytes": os.path.getsize(cp)}
    os.remove(p)
    os.replace(p[:-4] + ".json", cp[:-4] + ".json")
json.dump(rec, open(os.path.join(cd, "COMPACT_RECEIPT.json"), "w"), indent=1)
print("M3C_COMPACT DONE", d, "files", len(rec["files"]), "bytes_full", sum(v["full_bytes"] for v in rec["files"].values()),
      "bytes_compact", sum(v["compact_bytes"] for v in rec["files"].values()), "receipt_sha256", sha(os.path.join(cd, "COMPACT_RECEIPT.json")), flush=True)
