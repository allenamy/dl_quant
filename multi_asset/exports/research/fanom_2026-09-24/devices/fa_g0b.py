"""G0b: the re-run arm D's path npz shas must match FRESH_RUNS_MANIFEST.json one by one.
Mismatch => the re-run environment differs from the original; STOP, do not overwrite anything published."""
import json, hashlib, os, sys

MAN = "/dev/shm/fanom_2026-09-24/FRESH_RUNS_MANIFEST.json"
RUNS = "/dev/shm/fresh_2026-09-23/runs"
OUT = "/dev/shm/fanom_2026-09-24/receipts/G0B.json"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

M = json.load(open(MAN))
rec = {"gate": "G0b", "manifest": MAN, "manifest_sha256": sha(MAN), "cells": {}}
allok = True; n_checked = 0
for cell, want in M["cells"].items():
    if not cell.startswith("FRESH_s42"): continue
    d = os.path.join(RUNS, cell)
    if not os.path.isdir(d):
        rec["cells"][cell] = {"status": "ABSENT (not re-run)"}; continue
    per = {}; ok = True
    for fn, wsha in sorted(want["paths"].items()):
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            per[fn] = {"status": "MISSING"}; ok = False; continue
        a = sha(p); same = (a == wsha); n_checked += 1
        per[fn] = {"match": bool(same)}
        if not same: per[fn].update({"want": wsha, "got": a})
        ok = ok and same
    agg = {}
    for fn, wsha in sorted(want.get("agg", {}).items()):
        p = os.path.join(d, fn)
        a = sha(p) if os.path.exists(p) else None
        agg[fn] = {"match": bool(a == wsha), "want": wsha, "got": a}
    rec["cells"][cell] = {"n_paths_checked": sum(1 for v in per.values() if "match" in v),
                          "all_paths_match": bool(ok), "paths": per, "agg": agg}
    allok = allok and ok
rec["n_path_files_checked"] = n_checked
rec["G0B_PASS"] = bool(allok and n_checked > 0)
rec["assert_nonvacuous"] = {"n_path_files_checked": n_checked, "must_be_gt_0": True}
assert n_checked > 0, "G0b vacuous: no path files were compared"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(rec, open(OUT, "w"), indent=1)
summary = {c: (v.get("all_paths_match"), v.get("n_paths_checked")) for c, v in rec["cells"].items()}
print("G0B", "PASS" if rec["G0B_PASS"] else "FAIL", "path_files_checked=%d" % n_checked, json.dumps(summary), "receipt=%s" % sha(OUT), flush=True)
sys.exit(0 if rec["G0B_PASS"] else 3)
