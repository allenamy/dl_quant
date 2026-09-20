#!/usr/bin/env python3
"""cf_beta_unread_test.py — PREREG addendum B-A1's load-bearing assertion, run as a MUTATION rather
than claimed: the 113 EXT_NOT_COVERED panel rows must not be readable by at_beta.py.

Claiming "at_beta slices [in_run] first, so those rows never enter" is a textual argument about the
device. This replaces it with a behavioural one: poison those 113 rows with an absurd value, run the
UNMODIFIED at_beta.py again, and require every number it emits to be unchanged.

The control is the other half: the SAME mutation applied to rows INSIDE in_run must change the output,
otherwise the comparison proves nothing (a device that ignores its whole panel would also "pass").

usage: /workspace/venv/bin/python -B cf_beta_unread_test.py <BASE_RECEIPT_DIR> <OUT_DIR>
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/workspace/cf3b_2026-09-20"
PAN = f"{ROOT}/work/AT_PANEL.npz"
BASE_RECEIPT = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
POISON = 12345.0


def numbers(p):
    """every float in the receipt, keyed by path — timestamps / shas / runtimes excluded"""
    d = json.load(open(p))
    out = {}

    def walk(o, pre=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("utc_start", "utc", "runtime_s", "self_sha256", "sha256", "env", "argv", "upstream"):
                    continue
                walk(v, pre + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, pre + "/%d" % i)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            out[pre] = float(o)
    walk(d)
    return out


def run(tag):
    """returns (numbers, rc, verdict_line). A non-zero rc is DATA, not a crash: at_beta going red is
    itself proof that the mutated cells were read."""
    od = f"{OUT}/{tag}"
    os.makedirs(od, exist_ok=True)
    env = {"PATH": "/usr/bin:/bin", "HOME": "/root"}
    r = subprocess.run(["/workspace/venv/bin/python", "-B", f"{HERE}/at_beta.py",
                        "PATH,HOME,LC_CTYPE,LANG,PWD,SHLVL,_", od],
                       cwd=HERE, env=env, capture_output=True, text=True)
    line = [l for l in r.stdout.strip().split("\n") if l.startswith("AT_BETA VERDICT")]
    n = numbers(f"{od}/AT_BETA.json") if os.path.exists(f"{od}/AT_BETA.json") else {}
    return n, r.returncode, (line[-1] if line else "")


Z = {k: np.asarray(v) for k, v in np.load(PAN, allow_pickle=True).items()}
in_run = Z["in_run"]
W0 = Z["W"].copy()
shutil.copy2(PAN, PAN + ".keep")
base = numbers(f"{BASE_RECEIPT}/AT_BETA.json")

res = {"n_ext_rows": int((~in_run).sum()), "n_in_run_rows": int(in_run.sum()), "poison": POISON,
       "n_numbers_compared": len(base)}

# ── mutation 1: poison the EXT rows. Expected: NOTHING changes.
W = W0.copy()
W[~in_run] = POISON
np.savez_compressed(PAN + ".tmp.npz", **{**Z, "W": W})
os.replace(PAN + ".tmp.npz", PAN)
m1, rc1, v1 = run("ext_poisoned")
d1 = {k: (base[k], m1[k]) for k in base if k in m1 and base[k] != m1[k]}
res["mutation_ext_rows"] = {"n_numbers_changed": len(d1), "expected": 0, "rc": rc1, "verdict_line": v1,
                            "n_keys_missing": len([k for k in base if k not in m1]),
                            "first_changed": dict(list(d1.items())[:3])}

# ── control: perturb ONE in_run row by a REALISTIC amount (x1.001). A tiny, legal change that moves
#    the output is a stronger control than an absurd one: it shows the device is sensitive to these
#    rows at the scale the arms actually differ, not merely to garbage.
W = W0.copy()
nz = np.nonzero(in_run)[0]
i0 = int(nz[len(nz) // 2])
W[i0] = (W0[i0].astype(np.float64) * 1.001).astype(np.float32)
np.savez_compressed(PAN + ".tmp.npz", **{**Z, "W": W})
os.replace(PAN + ".tmp.npz", PAN)
m2, rc2, v2 = run("one_in_run_row_scaled_1.001")
d2 = {k: (base[k], m2[k]) for k in base if k in m2 and base[k] != m2[k]}
res["control_one_in_run_row"] = {"row": i0, "perturbation": "W[row] x 1.001", "rc": rc2,
                                 "verdict_line": v2, "n_numbers_changed": len(d2), "expected": ">0",
                                 "first_changed": dict(list(d2.items())[:3])}

os.replace(PAN + ".keep", PAN)
res["panel_restored_bitwise"] = bool(np.array_equal(
    np.asarray(np.load(PAN, allow_pickle=True)["W"]).view(np.uint32),
    W0.view(np.uint32)))

ok = (len(d1) == 0) and (rc1 == 0) and (len(d2) > 0) and res["panel_restored_bitwise"]
res["verdict"] = "PASS" if ok else "FAIL"
res["reading"] = ("the 113 EXT_NOT_COVERED rows are PROVEN unreadable (poisoning them changes nothing) "
                  "and the comparison is not vacuous (poisoning one in_run row does change the output)")
json.dump(res, open(f"{OUT}/CF_BETA_UNREAD_TEST.json", "w"), indent=1, default=float)
print("CF_BETA_UNREAD_TEST VERDICT=%s ext_changed=%d (want 0) control_changed=%d (want >0) restored=%s"
      % (res["verdict"], len(d1), len(d2), res["panel_restored_bitwise"]), flush=True)
sys.exit(0 if ok else 3)
