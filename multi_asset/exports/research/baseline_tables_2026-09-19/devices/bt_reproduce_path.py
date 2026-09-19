#!/usr/bin/env python3
"""bt_reproduce_path.py — re-runs ONE full-window path (run tag, seed) with the driver version in this directory and compares every array
with an existing path file bitwise. Used to show that a later driver version (e.g. with the §3.4 cost-cell override) reproduces the path files
produced by the committed version when no cost cell is set. Exit 0 only if every array is bitwise equal.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_reproduce_path.py PATH,HOME,LC_CTYPE <config.json> <run tag> <seed> <path.npz> <out.json>
"""
import os, sys, json, time
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL
CFG = json.load(open(sys.argv[2])); TAG = sys.argv[3]; SEED = int(sys.argv[4]); REF = sys.argv[5]; OUTP = sys.argv[6]
T0 = time.time(); fails = []
DL.verify_pins(CFG, lambda n, c, d=None: fails.append(n) if not c else None)
ES, SL, BH, L2 = DL.import_modules(CFG, HERE); SL.install_readonly_guard()
r = next(x for x in CFG["runs"] if x["tag"] == TAG)
C = DL.load_context(CFG, ES, BH, L2, slice(0, int(CFG["window"]["n_anchors"])), [r], lambda n, c, d=None: fails.append(n) if not c else None, lambda *a: None)
arr, out, _ = DL.run_one(C, r, SEED)
Z = np.load(REF)
diff = sorted(k for k in set(arr) | set(Z.files) if k not in arr or k not in Z.files or not np.array_equal(np.asarray(arr[k]), Z[k], equal_nan=True))
rec = dict(device="bt_reproduce_path.py", self_sha256=DL.sha(os.path.abspath(__file__)), driver_lib_sha256=DL.sha(os.path.join(HERE, "bt_driver_lib.py")),
           hist_sim_sha256=DL.sha(os.path.join(HERE, "bt_hist_sim31.py")), tag=TAG, seed=SEED, reference=REF, reference_sha256=DL.sha(REF), pin_failures=fails,
           arrays_compared=len(set(arr) | set(Z.files)), arrays_differing=diff, runtime_s=round(time.time() - T0, 1),
           verdict=("REPRODUCED bitwise" if not diff and not fails else "DIFFERS"))
json.dump(rec, open(OUTP, "w"), indent=1)
print("BT_REPRODUCE_PATH", rec["verdict"], "arrays", rec["arrays_compared"], "differing", diff[:5], "runtime_s", rec["runtime_s"])
sys.exit(0 if rec["verdict"].startswith("REPRODUCED") else 1)
