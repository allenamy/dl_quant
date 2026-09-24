import hashlib, json, os, time
W = "/dev/shm/news2_2026-09-23"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


m = json.load(open(f"{W}/receipts/P5_DEPLOY_MANIFEST.json"))
mp = f"{W}/receipts/P5_DEPLOY_MANIFEST.json"
t = json.load(open(f"{W}/receipts/TEST_EXPORT_OVERRIDE.json"))
h = {
    "handoff": "HANDOFF_deploy_s42.json",
    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "purpose": ("the handoff surface for the install rehearsal (DEPLOY manual P2) and for lead. Written by "
                "the producing side so it does not depend on me relaying a log line -- the 01:05Z combo "
                "target sat unrelayed for 56 minutes because it only existed in a log."),
    "FROZEN_VERDICT": m["VERDICT"],
    "USER_OVERRIDE": m["USER_OVERRIDE"],
    "override_ruling": {"path": m["user_override"]["override_path"],
                        "sha256_measured": m["user_override"]["override_sha_measured"],
                        "verified": m["user_override"]["override_verified"],
                        "repo_copy": "docs/RULING_user_NC_s42_override_2026-09-24.md"},
    "seed": m["seed"],
    "status": m["export_status"],
    "exported_files": m["exported_files"],
    "executor_pins": m["deploy"]["executor_pins"],
    "V1_gate": m["deploy"]["V1_gate"],
    "numpy_serving_vs_gpu_oof_202609": m["deploy"]["numpy_serving_vs_gpu_oof_202609"],
    "override_gate_selftest": {"receipt": f"{W}/receipts/TEST_EXPORT_OVERRIDE.json",
                               "VERDICT": t["VERDICT"], "cells": t["n_cells"], "n_not_pass": t["n_not_pass"],
                               "cell_names": [c["cell"] for c in t["cells"]]},
    "manifest": {"path": mp, "sha256": sha(mp)},
    "lineage_roots": {k: v for k, v in m["links"].items()},
    "wording_note": ("the only remaining 'PASS' anywhere in the manifest is deploy.V1_gate.PASS, which is "
                     "the numpy-equals-torch numerical equivalence gate (spearman >= 0.99999, maxabs <= 1e-5). "
                     "It is not an admission of the book and its name predates this ruling; renaming it would "
                     "break the pin semantics the executor and the rehearsal read."),
    "not_released": ("s2027 is NOT exported and is NOT a fallback (ruling section 4-1). Only s42 exists in "
                     "deploy/."),
}
out = f"{W}/receipts/HANDOFF_deploy_s42.json"
json.dump(h, open(out, "w"), indent=1)
print("HANDOFF written", out, sha(out)[:24])
for f in h["exported_files"]:
    print("  ", f["name"].ljust(22), f["sha256"])
