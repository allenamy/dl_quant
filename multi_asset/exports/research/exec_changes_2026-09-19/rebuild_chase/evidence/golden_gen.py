"""Compute golden digests of plan_experiment records with the UNMODIFIED chase_policy (409ea16 blob)."""
import hashlib, importlib.util, json, sys
spec = importlib.util.spec_from_file_location("cp_old", sys.argv[1]); CP = importlib.util.module_from_spec(spec); spec.loader.exec_module(CP)
exec(open(sys.argv[2]).read())
def digest(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
out = {}
for name, kw in GOLDEN_CASES:
    rec = CP.plan_experiment(**kw)
    out[name] = {"sha256": digest(rec), "in_sample": rec["in_sample"], "n_excluded": len(rec["excluded_because"]),
                 "arm_counts": rec["arm_counts"], "keys": sorted(rec)}
    print(name, out[name]["sha256"], rec["in_sample"], rec["arm_counts"], [e[:40] for e in rec["excluded_because"]])
json.dump(out, open(sys.argv[3], "w"), indent=1, sort_keys=True)
