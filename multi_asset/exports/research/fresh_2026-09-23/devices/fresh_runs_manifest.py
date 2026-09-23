"""fresh_runs_manifest.py — hash every FRESH engine path file before runs/ is deleted.

FRESH_STATS.json pins the CONTROL arm's path shas (control_path_shas, 10 cells) but not FRESH's own. Without this
manifest, deleting runs/ would leave the FRESH side of the comparison with no byte-level record, and a later re-run
could not be checked against what actually produced the verdict. This device writes that record. It also re-reads each
path json's own npz_sha256 and asserts it matches the file on disk, so the manifest certifies the files as they were read.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fresh_runs_manifest.py PATH,HOME,LC_CTYPE <runs_root> <out.json>
"""
import os, sys, json, time, hashlib

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
RUNS, OUT = sys.argv[2:4]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    rec = {"device": "fresh_runs_manifest.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs_root": RUNS,
           "why": "FRESH_STATS.json pins only the control arm's path shas; this pins FRESH's own, so runs/ can be deleted "
                  "and a later re-run can still be checked byte for byte against what produced the verdict.",
           "cells": {}}
    n_files = n_json_ok = 0
    for d in sorted(os.listdir(RUNS)):
        p = os.path.join(RUNS, d)
        if not os.path.isdir(p): continue
        npz = sorted(f for f in os.listdir(p) if f.endswith(".npz"))
        cell = {"n_npz": len(npz), "paths": {}, "agg": {}}
        for f in npz:
            fp = os.path.join(p, f); h = sha(fp); n_files += 1
            jp = fp[:-4] + ".json"
            assert os.path.exists(jp), f"{fp}: no sidecar json"
            J = json.load(open(jp))
            if f.startswith("AGG_"):
                # the run-level aggregate carries its sha under a different key
                cell["agg"][f] = h
                assert J["agg_npz_sha256"] == h, f"{fp}: json agg_npz_sha256 != file"
            else:
                cell["paths"][f] = h
                assert J["npz_sha256"] == h, f"{fp}: json npz_sha256 != file"
            n_json_ok += 1
        rec["cells"][d] = cell
    rec["totals"] = {"n_cells": len(rec["cells"]), "n_npz": n_files, "n_json_sha_verified": n_json_ok}
    assert n_json_ok == n_files, f"{n_files - n_json_ok} npz files have no json to verify against"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
    print(f"FRESH_RUNS_MANIFEST written {OUT} {sha(OUT)} cells={rec['totals']['n_cells']} "
          f"npz={rec['totals']['n_npz']} json_verified={rec['totals']['n_json_sha_verified']}", flush=True)


if __name__ == "__main__":
    main()
