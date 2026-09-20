#!/usr/bin/env python3
"""bt_p_config_for.py — writes the reading-P config for another arm by copying the ALREADY FROZEN one and changing only which runs it reads.

Why a device and not an edit: the P-reading parameters (threshold −25.00 %, the caliber, the halt semantics, breach_by, the 17 quarterly
starts, the two bases, the granularities) must be the ones frozen before any P number existed. This device copies that block BYTE FOR BYTE
and asserts it afterwards; it changes only `config`, `object`, `created_utc`, `runs` and the pinned sha of the run config being read. If the
source block and the written block differ in any way, it refuses.
usage: /workspace/venv/bin/python -B bt_p_config_for.py PATH,HOME,LC_CTYPE <source_p_config.json> <run_config.json> <arm_tag_prefix> <runs_root> <label> <out.json>
"""
import os, sys, json, time, hashlib

if __name__ == "__main__":
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"

SRC, RUNCFG, PREFIX, ROOT, LABEL, OUT = sys.argv[2:8]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


S = json.load(open(SRC)); R = json.load(open(RUNCFG))
C = json.loads(json.dumps(S))
C["config"] = os.path.basename(OUT)[:-5] if OUT.endswith(".json") else os.path.basename(OUT)
C["object"] = f"reading P for {LABEL} (runs of {os.path.basename(RUNCFG)}, window {R['window']['first_anchor']} → {R['window']['last_anchor']})"
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["pins"]["run_config_of_the_runs_read"] = {"path": os.path.basename(RUNCFG), "sha256": sha(RUNCFG)}
C["derived_from"] = {"p_config": os.path.basename(SRC), "sha256": sha(SRC),
                     "rule": "the whole p_reading block is copied byte for byte from the config frozen before any P number existed"}
runs = []
for r in R["runs"]:
    if r.get("cost_cell"): continue
    tag = r["tag"]; d = os.path.join(ROOT, tag.replace("|", "_"))
    runs.append({"label": f"{tag.split('|')[0]}|{r['book']} ({'main reading' if r['book'] == 'scaled' else 'reported'}, {LABEL})", "dir": d})
assert runs and all(os.path.basename(x["dir"]).startswith(PREFIX) for x in runs), f"run dirs do not all start with {PREFIX}: {runs}"
C["runs"] = runs
assert C["p_reading"] == S["p_reading"], "the frozen p_reading block was altered — refused"
assert C["pins"]["prereg_amendment_2"] == S["pins"]["prereg_amendment_2"], "the AMENDMENT 2 pin was altered — refused"
json.dump(C, open(OUT, "w"), indent=1, ensure_ascii=False)
print("BT_P_CONFIG_FOR wrote", OUT, sha(OUT)[:16], "| runs:", [x["dir"].split("/")[-1] for x in runs], "| p_reading block identical to", os.path.basename(SRC))
