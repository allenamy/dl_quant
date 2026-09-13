#!/usr/bin/python3
"""LED-01 follow-up diagnostic (committed BEFORE any run; read-only, no venue, no credentials).
The LED-05 rehearsal printed a different watchdog conditions_sha256 on the ef60f85 tree and on the fix tree for the SAME
ledger copy, although watchdog.py is untouched by the chain. This device names every differing leaf.
  --dump: in a subprocess per tree, watchdog.evaluate(<temp root>/pilot_log -> symlink to the given root's pilot_log,
          venue_events=[], ops_stats=[]) and write {tripped, blind, conditions} as JSON.
  --diff: compare two dumps leaf by leaf; lists of dicts are walked element by element.
Usage: led01_watchdog_tree_parity.py --dump --root R --executor-tree T --out F
       led01_watchdog_tree_parity.py --diff A.json B.json --out F"""
import argparse, hashlib, json, os, sys, tempfile, time
ap = argparse.ArgumentParser(allow_abbrev=False)
ap.add_argument("--dump", action="store_true"); ap.add_argument("--diff", nargs=2)
ap.add_argument("--root"); ap.add_argument("--executor-tree"); ap.add_argument("--out", required=True)
a = ap.parse_args()
def leaves(x, p=""):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items(): out.update(leaves(v, f"{p}.{k}" if p else str(k)))
        return out
    if isinstance(x, list) and x and all(isinstance(v, dict) for v in x):
        out = {}
        for i, v in enumerate(x): out.update(leaves(v, f"{p}[{i}]"))
        return out
    return {p: x}
if a.dump:
    for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(a.executor_tree, d))
    os.environ.setdefault("LIVE_MODE", "DRY_RUN")
    import watchdog as WD
    tmp = tempfile.mkdtemp(prefix="led01_wdparity_")
    os.symlink(os.path.join(os.path.abspath(a.root), "pilot_log"), os.path.join(tmp, "pilot_log"))
    ev = WD.evaluate(os.path.join(tmp, "pilot_log"), venue_events=[], ops_stats=[])
    os.unlink(os.path.join(tmp, "pilot_log")); os.rmdir(tmp)
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "executor_tree": a.executor_tree,
           "watchdog_py_sha256": hashlib.sha256(open(os.path.join(a.executor_tree, "live", "watchdog.py"), "rb").read()).hexdigest(),
           "tripped": ev.get("tripped"), "blind": ev.get("conditions_blind"),
           "conditions": json.loads(json.dumps(ev.get("conditions") or {}, default=repr)),
           "tmp_path": tmp}
    json.dump(res, open(a.out, "w"), indent=1)
    print("DUMP", a.executor_tree, "tripped", res["tripped"], "sha", hashlib.sha256(json.dumps(res["conditions"], sort_keys=True).encode()).hexdigest())
else:
    A, B = (json.load(open(p)) for p in a.diff)
    la, lb = leaves(A["conditions"]), leaves(B["conditions"])
    diff = {p: {"a": la.get(p), "b": lb.get(p)} for p in sorted(set(la) | set(lb)) if la.get(p) != lb.get(p)}
    res = {"a": a.diff[0], "b": a.diff[1], "a_tree": A["executor_tree"], "b_tree": B["executor_tree"],
           "tmp_a": A.get("tmp_path"), "tmp_b": B.get("tmp_path"),
           "tripped": [A["tripped"], B["tripped"]], "n_leaves": [len(la), len(lb)], "n_diff": len(diff), "diff": diff}
    json.dump(res, open(a.out, "w"), indent=1, default=repr)
    print("DIFF n_leaves", res["n_leaves"], "n_diff", len(diff))
    for p, v in list(diff.items())[:40]: print(" ", p, str(v["a"])[:150], "|", str(v["b"])[:150])
