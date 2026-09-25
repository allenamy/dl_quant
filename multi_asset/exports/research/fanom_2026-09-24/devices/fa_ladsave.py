"""fa_ladsave.py — extract a ladder cell's COMPLETE per-path series into a small npz so the cell can be freed.
Without this the cells accumulate at ~0.44 GiB each and the run gate's own /dev/shm floor blocks the queue -- which is
exactly what happened after the first two baselines. Saving per-path `r` is what the canonical news_stats.dbar needs
(per-path daily differences, then mean across paths), so nothing has to be re-run later to add a reading.

usage: ... fa_ladsave.py WL <cell_dir> <out.npz>
"""
import os, sys, json, hashlib
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
CELL, OUT = sys.argv[2], sys.argv[3]
sys.path.insert(0, "/dev/shm/news_2026-09-23/engine")
import bt_tables as BT, bt_driver_lib as DL


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


tag = os.path.basename(CELL)
P = []
for k in range(32):
    s = f"{CELL}/PATH_{tag}_seed_{k:02d}"
    J = json.load(open(s + ".json"))
    assert J["npz_sha256"] == sha(s + ".npz"), f"{tag} seed {k}: npz sha mismatch"
    assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k, f"{tag} seed {k}: audit/seed"
    P.append(BT.series_from_path(np.load(s + ".npz")))
A = P[0]["A"].astype(np.int64)
for p in P:
    assert np.array_equal(p["A"].astype(np.int64), A), "path axes differ"
d = {"anchors": A}
for k in ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt"):
    d[k + "_per_path"] = np.stack([p[k] for p in P]).astype(np.float64)
np.savez_compressed(OUT + ".tmp.npz", **d); os.replace(OUT + ".tmp.npz", OUT)
print("FA_LADSAVE %s -> %s  n=%d paths=32 sha=%s" % (tag, os.path.basename(OUT), len(A), sha(OUT)[:16]), flush=True)
