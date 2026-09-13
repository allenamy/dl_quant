#!/usr/bin/python3
"""LED-05 diagnostic (committed BEFORE any run; read-only on the given root, no venue, no credentials).
The LED-05 rehearsal found watchdog conditions cond5_venue_event and cond6_weight_fidelity change (not trip) when the 52
reconstructed order rows are appended. This device names every changed LEAF of those two conditions (and of any other
condition that changes), with before/after values, so the change can be explained rather than asserted harmless.
Temp root: 20260909 COPIED, other days SYMLINKED; the rows file's verbatim bytes appended to the copy's orders.jsonl.
Usage: led05_watchdog_delta.py --root R --rows F --rows-sha S --executor-tree T --out OUT.json"""
import argparse, hashlib, json, os, shutil, sys, tempfile, time
ap = argparse.ArgumentParser(allow_abbrev=False)
for k in ("--root", "--rows", "--rows-sha", "--executor-tree", "--out"): ap.add_argument(k, required=True)
a = ap.parse_args()
DAY = "20260909"
for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(a.executor_tree, d))
os.environ.setdefault("LIVE_MODE", "DRY_RUN")
import watchdog as WD
blob = open(a.rows, "rb").read()
assert len(blob) == os.stat(a.rows).st_size and hashlib.sha256(blob).hexdigest() == a.rows_sha, "rows sha"
tmp = tempfile.mkdtemp(prefix="led05_wddelta_"); pl = os.path.join(tmp, "pilot_log"); os.makedirs(pl)
src = os.path.join(os.path.abspath(a.root), "pilot_log")
for d in os.listdir(src):
    if d == DAY: shutil.copytree(os.path.join(src, d), os.path.join(pl, d))
    else: os.symlink(os.path.join(src, d), os.path.join(pl, d))
def ev(): return WD.evaluate(pl, venue_events=[], ops_stats=[])
def leaves(x, p=""):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items(): out.update(leaves(v, f"{p}.{k}" if p else str(k)))
        return out
    if isinstance(x, list) and len(x) <= 60 and all(isinstance(v, (dict, list)) for v in x):
        out = {}
        for i, v in enumerate(x): out.update(leaves(v, f"{p}[{i}]"))
        return out
    return {p: json.loads(json.dumps(x, default=repr))}
e0 = ev()
with open(os.path.join(pl, DAY, "orders.jsonl"), "ab") as fh: fh.write(blob)
e1 = ev()
c0, c1 = e0.get("conditions") or {}, e1.get("conditions") or {}
changed = {}
for k in sorted(set(c0) | set(c1)):
    l0, l1 = leaves(c0.get(k)), leaves(c1.get(k))
    diff = {p: {"before": l0.get(p), "after": l1.get(p)} for p in sorted(set(l0) | set(l1)) if l0.get(p) != l1.get(p)}
    if diff: changed[k] = diff
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "executor_tree": a.executor_tree,
       "watchdog_py_sha256": hashlib.sha256(open(os.path.join(a.executor_tree, "live", "watchdog.py"), "rb").read()).hexdigest(),
       "rows_sha256": a.rows_sha, "tripped_before": e0.get("tripped"), "tripped_after": e1.get("tripped"),
       "blind_before": e0.get("conditions_blind"), "blind_after": e1.get("conditions_blind"),
       "top_keys_changed": sorted(k for k in set(e0) | set(e1) if k != "conditions" and json.dumps(e0.get(k), sort_keys=True, default=repr) != json.dumps(e1.get(k), sort_keys=True, default=repr)),
       "changed_leaves": changed}
json.dump(res, open(a.out, "w"), indent=1, default=repr)
shutil.rmtree(tmp)                      # rmtree does not follow the day symlinks (it unlinks them)
print("LED05_WD_DELTA tripped", res["tripped_before"], "->", res["tripped_after"], "conditions changed", {k: len(v) for k, v in changed.items()})
for k, v in changed.items():
    for p, bv in list(v.items())[:25]: print(" ", k, p, str(bv["before"])[:160], "->", str(bv["after"])[:160])
