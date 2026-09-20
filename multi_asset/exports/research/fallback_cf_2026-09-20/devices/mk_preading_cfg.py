#!/usr/bin/env python3
"""mk_preading_cfg.py — freeze the P and P2 reading configs for the F arms, inheriting the `p_reading` / `p2_reading` blocks
BYTE-FOR-BYTE from the certified A0 configs. The only thing that changes is which run directories are read.
usage: mk_preading_cfg.py"""
import hashlib, json, os, sys, time

BASE = "/workspace/baseline_tables_2026-09-19"
OUT = "/workspace/fallback_cf_2026-09-20"
SRC_P = f"{BASE}/RUN_CONFIG_Preading_A0_2026-09-20.json"
SRC_P2 = f"{BASE}/RUN_CONFIG_P2reading_A0_2026-09-20.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


arms = [a for a in sys.argv[1:]] or ["F0", "F1", "F2", "F4a"]
runs = [{"label": f"OBJB_{a}|scaled (F-family arm {a})", "dir": f"{OUT}/runs/OBJB_{a}_scaled_rule_raw_UAFE"} for a in arms]
for r in runs:
    assert os.path.isdir(r["dir"]), r["dir"]

for src, dst, tag in ((SRC_P, f"{OUT}/RUN_CONFIG_Preading_F_2026-09-20.json", "P"),
                      (SRC_P2, f"{OUT}/RUN_CONFIG_P2reading_F_2026-09-20.json", "P2")):
    C = json.load(open(src))
    C["config"] = f"RUN_CONFIG_{tag}reading_F_2026-09-20"
    C["status"] = (f"FROZEN before any reading-{tag} number of the F family; post-processing only. The p_reading"
                   + (" / p2_reading" if tag == "P2" else "") + " block is inherited BYTE-FOR-BYTE from the certified A0 config below.")
    C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    C["object"] = f"reading {tag} for the F-family fallback counterfactual arms ({', '.join(arms)})"
    C["runs"] = runs
    C["pins"]["run_config_of_the_runs_read"] = {"path": f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json",
                                                "sha256": sha(f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json")}
    C["inherited_from"] = {"path": src, "sha256": sha(src),
                           "rule": "every reading parameter (threshold, caliber, halt semantics, starts, bases, granularity"
                                   + (", resume hours, include flags" if tag == "P2" else "") + ") is inherited unchanged; only `runs` differs"}
    json.dump(C, open(dst + ".tmp", "w"), indent=1); os.replace(dst + ".tmp", dst)
    print("wrote", dst, "sha256", sha(dst), "| inherited from", os.path.basename(src), sha(src)[:16])
print("arms:", arms)
