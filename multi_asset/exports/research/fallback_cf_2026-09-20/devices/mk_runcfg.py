#!/usr/bin/env python3
"""mk_runcfg.py — freeze the F-family run configuration from the CERTIFIED baseline-tables A0 config.
Everything is inherited byte-for-byte except: paths.pod_root, and the runs list (one run per arm, all main "scaled" reading,
no cost cells). The pins, window, nav0, paths_R, seeds, simulator, calibration, executor tree and production config are untouched."""
import hashlib, json, os, time

BASE = "/workspace/baseline_tables_2026-09-19"
OUT = "/workspace/fallback_cf_2026-09-20"
ARMS = ["F0", "F1", "F2", "F4a"]
ROLE = {
    "F0": "PREREG F-family §2 F0 · baseline = in-service behaviour: preflight fails -> the producer's 3-leg king file (rev24). "
          "ALSO THE CONTROL: its targets reproduce the archived production target bitwise, so its 32 paths must reproduce the certified "
          "run OBJB_A0|scaled|rule|raw|UAFE bitwise.",
    "F1": "PREREG F-family §2 F1 · preflight fails -> the combo book is written anyway.",
    "F2": "PREREG F-family §2 F2 · preflight fails -> no file; the executor's own on_unavailable = hold carries the previous book.",
    "F4a": "PREREG F-family §2 F4 (reading a) · preflight fails -> the rev24-free king component kc. NAMED CONFOUND: kc also carries FTRIM.",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


src = f"{BASE}/RUN_CONFIG_main_A0_2026-09-19.json"
C = json.load(open(src))
tmpl = C["runs"][0]
uni = dict(tmpl["targets"]["universe"])

runs = []
for arm in ARMS:
    npz = f"{OUT}/work/TARGETS_{arm}_A0_main.npz"; rcp = f"{OUT}/receipts/TARGETS_{arm}_A0_main.json"
    r = {"arm": f"OBJB_{arm}", "events": "rule", "price": "raw", "policy": "UA-FREEZE-EXCLUDE", "ua_set": "UNAVAILABLE_3084",
         "tag": f"OBJB_{arm}|scaled|rule|raw|UAFE", "book": "scaled",
         "targets": {"source": "objb", "reading": "scaled", "arm": "A0",
                     "sources": [{"npz": npz, "npz_sha256": sha(npz), "receipt": rcp, "receipt_sha256": sha(rcp)}],
                     "universe": uni},
         "role": ROLE[arm]}
    runs.append(r)

C["config"] = "RUN_CONFIG_fallback_cf_F_2026-09-20"
C["status"] = "FROZEN before any F-family number exists (targets built and structurally asserted first: receipts/FCF_TARGETS.json)"
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["prereg"] = ("docs/PREREG_fallback_counterfactual_2026-09-20.md (a964c2f9a) — the F family; the judge, window, simulator, prices, "
               "calibration and executor tree are INHERITED UNCHANGED from RUN_CONFIG_main_A0_2026-09-19.json (sha " + sha(src) + "), "
               "per F-prereg §3 '判官 = 认证生产路径 … 不另建判官'")
C["object"] = ("certified object B (recipe-matched OOF history), in-service recipe A0, B-scaled main reading — with ONE substitution: "
               "the target npz per arm, built by fcf_targets.py from the same archive")
C["runs"] = runs
C["paths"] = dict(C["paths"], pod_root=OUT, mac_root="multi_asset/exports/research/fallback_cf_2026-09-20")
C["frozen_by"] = {"device": "fcf_targets.py", "receipt": f"{OUT}/receipts/FCF_TARGETS.json", "receipt_sha256": sha(f"{OUT}/receipts/FCF_TARGETS.json")}
C["f_family"] = {"arms_built": ARMS,
                 "F3_not_built": ("production external_book.parse_target L317/L342 rejects an empty / zero-gross target, so 'target all zero' "
                                  "cannot travel the target-file channel and degenerates to F2 bitwise; reported to the lead, awaiting a ruling"),
                 "F4b_not_in_this_config": "producer re-chain with w3[1]:=0 (shadow_loop_v3_replay.py L449); separate config if the lead rules for it",
                 "retrospective_level": "R (2023-06-30 -> 2026-08-31): CAN ONLY REFUSE, NEVER PROMOTE (F-prereg §3)"}
C.pop("objb_lineage", None)
C["objb_lineage_inherited"] = json.load(open(src)).get("objb_lineage")

p = f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json"
json.dump(C, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
print("wrote", p, "sha256", sha(p))
print("source config sha256", sha(src))
print("runs", [r["tag"] for r in C["runs"]])
print("window", C["window"]["first_anchor"], "->", C["window"]["last_anchor"], C["window"]["n_anchors"], "anchors; paths_R", C["paths_R"])
