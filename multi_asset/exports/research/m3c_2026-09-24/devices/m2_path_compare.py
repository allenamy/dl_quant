#!/usr/bin/env python3
"""m2_path_compare.py — bitwise comparison of simulator path files (PATH_*_seed_NN.npz) between two run directories, per seed, EVERY array key
(uint64 / raw-byte view; NaN positions must match). Used for (i) the zero-hedge hook control (m2_hook.py with a table of zeros must reproduce
the certified base paths) and (ii) the reproduction control (the unchanged base run under the M2 config must reproduce the certified base
paths, and later Stage 1's OLD paths). A red-capability control is built in: the first compared pair is also compared against the NEXT
seed of the reference, which must differ (proves the comparison can see a difference).
usage: python m2_path_compare.py <dir_a> <dir_b> <seeds comma> <out.json>
"""
import os, sys, json, hashlib, time
import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def path_file(d, seed):
    fs = [f for f in os.listdir(d) if f.startswith("PATH_") and f.endswith(f"_seed_{seed:02d}.npz")]
    if len(fs) != 1: raise SystemExit(f"{d}: {len(fs)} files for seed {seed}")
    return os.path.join(d, fs[0])


def cmp(pa, pb):
    A, B = np.load(pa), np.load(pb)
    ka, kb = sorted(A.files), sorted(B.files)
    res = {"keys_equal": ka == kb, "diff_keys": []}
    for k in ka:
        if k not in B.files: res["diff_keys"].append(k); continue
        a, b = np.ascontiguousarray(A[k]), np.ascontiguousarray(B[k])
        if a.shape != b.shape or a.dtype != b.dtype or a.tobytes() != b.tobytes():
            res["diff_keys"].append(k)
    res["equal"] = res["keys_equal"] and not res["diff_keys"]
    return res


da, db, seeds_s, outp = sys.argv[1:5]
seeds = [int(s) for s in seeds_s.split(",")]
out = {"device": "m2_path_compare.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "dir_a": da, "dir_b": db, "seeds": seeds, "per_seed": {}}
for s in seeds:
    pa, pb = path_file(da, s), path_file(db, s)
    r = cmp(pa, pb); r.update(file_a=os.path.basename(pa), sha_a=sha(pa), file_b=os.path.basename(pb), sha_b=sha(pb)); out["per_seed"][s] = r
    print("seed", s, "EQUAL" if r["equal"] else "DIFF " + ",".join(r["diff_keys"][:10]), flush=True)
s0 = seeds[0]; s1 = s0 + 1 if s0 < 31 else s0 - 1
ctrl = cmp(path_file(da, s0), path_file(db, s1))
out["red_capability_control"] = {"a_seed": s0, "b_seed": s1, "must_differ": True, "differs": not ctrl["equal"], "diff_keys": ctrl["diff_keys"][:20]}
ok = all(v["equal"] for v in out["per_seed"].values()) and out["red_capability_control"]["differs"]
out["VERDICT"] = "BITWISE_EQUAL" if ok else "NOT_EQUAL_OR_CONTROL_FAILED"
json.dump(out, open(outp, "w"), indent=1)
print("M2_PATH_COMPARE", out["VERDICT"], "control_differs", out["red_capability_control"]["differs"], "out_sha256", sha(outp), flush=True)
sys.exit(0 if ok else 1)
