"""SWAPPKG step-1 evidence, LOCAL half (read-only on ~/wide_shadow).
For every archived producer snapshot state/snap/<A>/ with A <= NEW axis end (1789776000 = 2026-09-19T00Z):
  - production member list pm (aux.json prev_rec.members; what King/F10 were served on at A)
  - which symbols_panel columns have ANY finite log_qv in the last 2016 rows of the rolling cache
    (the producer only fetches klines for cfg symbols_live, shadow_loop_v3.py:406).
Writes pop_check_local.json (with sha256 of every file read). No writes outside this directory."""
import os, json, hashlib, glob, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.expanduser("~/wide_shadow")
NEW_AXIS_END = 1789776000
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
cfgp = f"{WS}/shadow_bundle/config.json"; cfg = json.load(open(cfgp))
syms = cfg["symbols_panel"]; live = set(cfg["symbols_live"])
out = {"device": "pop_check_local.py", "self_sha256": sha(os.path.abspath(__file__)),
       "inputs": {cfgp: sha(cfgp)}, "n_symbols_panel": len(syms), "n_symbols_live": len(live), "anchors": {}}
for d in sorted(glob.glob(f"{WS}/state/snap/17*")):
    A = int(os.path.basename(d))
    if A > NEW_AXIS_END: continue
    for fn in ("aux.json", "rolling.npz"): out["inputs"][f"{d}/{fn}"] = sha(f"{d}/{fn}")
    aux = json.load(open(f"{d}/aux.json")); pr = aux["prev_rec"]
    assert int(pr["anchor_ts"]) == A, (A, pr["anchor_ts"])
    with np.load(f"{d}/rolling.npz", allow_pickle=True) as z:
        ts = z["ts"].astype(np.int64); D = z["data"]
        assert int(ts[-1]) == A, (A, int(ts[-1]))
        fin = np.isfinite(D[-2016:, :, 3].astype(np.float32)).sum(0)
    have = [j for j in range(len(syms)) if fin[j] > 0]
    out["anchors"][str(A)] = {"members": [int(x) for x in pr["members"]],
                              "cols_with_data_last2016": have,
                              "n_cols_with_data": len(have),
                              "n_cols_with_data_in_live": int(sum(syms[j] in live for j in have)),
                              "n_cols_with_data_outside_live": int(sum(syms[j] not in live for j in have))}
    print(A, len(pr["members"]), len(have), flush=True)
json.dump(out, open(f"{HERE}/receipts/pop_check_local.json", "w"))
print("POP_CHECK_LOCAL_DONE anchors", len(out["anchors"]))
