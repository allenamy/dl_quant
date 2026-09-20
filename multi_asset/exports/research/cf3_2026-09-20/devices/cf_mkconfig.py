#!/usr/bin/env python3
"""cf_mkconfig.py — CF3 step 3a: build the FROZEN run configuration for the judge.

Takes the certified baseline-tables configuration RUN_CONFIG_main_A0_2026-09-19.json and changes
exactly two families of fields:
  (1) runs  -> one run per CF3 arm target file (book "scaled", events "rule", price "raw",
               policy UA-FREEZE-EXCLUDE, ua_set UNAVAILABLE_3084 — identical to the certified A0 run)
  (2) paths.pod_root -> /workspace/cf3_2026-09-20   (nothing is written under baseline_tables)
Every pin keeps the certified sha; the simulator / calibration / gate / executor-manifest pins are
re-pointed at byte-identical copies under this task's own devices_bt/ and the identity is asserted.

usage: /workspace/venv/bin/python -B cf_mkconfig.py <OUT_CONFIG_PATH>
"""
import hashlib
import json
import os
import sys
import time

SRC = "/workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0_2026-09-19.json"
ROOT = "/workspace/cf3_2026-09-20"
DEV = f"{ROOT}/devices_bt"
ARMS = ["BASE", "noFUND", "noKING", "noF10", "onlyFUND", "onlyKING", "onlyF10", "NONE",
        "noFUND_GF", "noKING_GF", "noF10_GF", "onlyFUND_GF", "onlyKING_GF", "onlyF10_GF"]
# NONE_GF is byte-identical to NONE (its book is empty on every anchor, so both gate conventions
# fall back to the king file); it is asserted equal below and not run twice.


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


out_path = sys.argv[1]
C = json.load(open(SRC))
src_sha = sha(SRC)

# NONE_GF == NONE assertion (so that one run covers both gate conventions for the empty coalition)
a, b = f"{ROOT}/work/TARGETS_CF_NONE.npz", f"{ROOT}/work/TARGETS_CF_NONE_GF.npz"
assert os.path.exists(b) and sha(a) == sha(b), "NONE_GF is not byte-identical to NONE — run it separately"

base_run = [r for r in C["runs"] if r["tag"] == "OBJB_A0|scaled|rule|raw|UAFE"][0]
UNI = base_run["targets"]["universe"]

runs = []
for arm in ARMS:
    npz = f"{ROOT}/work/TARGETS_CF_{arm}.npz"
    rcp = f"{ROOT}/receipts/TARGETS_CF_{arm}.json"
    gate = "G-FROZEN" if arm.endswith("_GF") else "G-FAITHFUL"
    runs.append({
        "arm": f"CF_{arm}", "events": "rule", "price": "raw", "policy": "UA-FREEZE-EXCLUDE",
        "ua_set": "UNAVAILABLE_3084", "tag": f"CF_{arm}|scaled|rule|raw|UAFE", "book": "scaled",
        "targets": {"source": "objb", "reading": "scaled", "arm": "A0",
                    "sources": [{"npz": npz, "npz_sha256": sha(npz),
                                 "receipt": rcp, "receipt_sha256": sha(rcp)}],
                    "universe": UNI},
        "role": f"CF3 counterfactual re-chain, coalition {arm.replace('_GF', '')}, gate convention {gate}"
        + (" (= the certified OBJB_A0|scaled run's book, bitwise; Gate J control)" if arm == "BASE" else ""),
    })

C["config"] = os.path.basename(out_path).replace(".json", "")
C["status"] = "FROZEN before any CF3 outcome number (arms are bitwise-gated by CF_ARMS)"
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["object"] = ("CF3 three-signal counterfactual re-chain of the certified object B A0_main "
               "(B-scaled reading); 8 coalitions x 2 gate conventions, NONE_GF == NONE")
C["prereg"] = ("docs/PREREG_three_signal_counterfactual_2026-09-20.md (c5427ee30) + addenda A1 (ea8054e87), "
               "A2 (6ce1902fe), A3 (f27a716c5)")
C["derived_from"] = {"path": SRC, "sha256": src_sha,
                     "changed_fields": ["runs", "paths.pod_root", "config", "status", "created_utc",
                                        "object", "prereg", "frozen_by", "objb_lineage", "pending",
                                        "cost_cells", "launch.max_parallel",
                                        "pins.exec_sim/simlib/v1b_gate/v1_gate/calibration/input_manifest"
                                        " (re-pointed at byte-identical copies under devices_bt/)"]}
C["runs"] = runs
C["paths"] = dict(C["paths"])
C["paths"]["pod_root"] = ROOT
C["paths"]["mac_root"] = "multi_asset/exports/research/cf3_2026-09-20"
C["cost_cells"] = {}
C["launch"] = dict(C["launch"])
C["launch"]["max_parallel"] = 8
C["pending"] = {"(a) arm target files": "filled: 15 files written by cf_arms.py, BASE bitwise-gated vs the archive",
                "(b) gate conventions": "filled: G-FAITHFUL + G-FROZEN (PREREG addendum A3)"}
C["frozen_by"] = {"device": "cf_mkconfig.py", "sha256": sha(os.path.abspath(__file__)),
                  "upstream_receipts": {p: sha(f"{ROOT}/receipts/{p}") for p in ("CF_REBUILD.json", "CF_ARMS.json")}}
C["objb_lineage"] = {"note": "targets are CF3 re-chains of object B A0_main; the BASE arm is bitwise identical "
                             "to /workspace/object_b_2026-09-19/work/A0_main/TARGETS_A0_main.npz",
                     "objb_targets_sha256": sha("/workspace/object_b_2026-09-19/work/A0_main/TARGETS_A0_main.npz")}

# re-point the simulator pins at this task's byte-identical copies
for k, rel in (("exec_sim", "exec_copy/exec_sim.py"), ("simlib", "exec_copy/simlib.py"),
               ("v1b_gate", "exec_copy/v1b_gate.py"), ("v1_gate", "exec_copy/v1_gate.py"),
               ("calibration", "exec_copy/CALIBRATION_v3_POOLED_20260826_20260910.json"),
               ("input_manifest", "exec_copy/INPUT_MANIFEST.json")):
    p = f"{DEV}/{rel}"
    got = sha(p)
    assert got == C["pins"][k]["sha256"], (k, got, C["pins"][k]["sha256"])
    C["pins"][k] = {"path": p, "sha256": got}

tmp = out_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(C, f, indent=1)
os.replace(tmp, out_path)
print("CF_MKCONFIG wrote %s sha256=%s n_runs=%d" % (out_path, sha(out_path), len(runs)), flush=True)
