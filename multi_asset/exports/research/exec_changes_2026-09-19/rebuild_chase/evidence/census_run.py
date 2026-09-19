"""Census: run one suite in-process with chase_policy.plan_experiment wrapped; log every call's
rho_pre, whether REBUILD fired, and whether REBUILD changed the arm map vs the same call without rho_pre."""
import json, os, runpy, sys
live, suite, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, live)
os.chdir(live)
import chase_policy as CP
_orig = CP.plan_experiment
fh = open(out, "a")
def wrapped(*a, **k):
    rec = _orig(*a, **k)
    k2 = {x: y for x, y in k.items() if x not in ("rho_pre", "rho_pre_detail")}
    base = _orig(*a, **k2)
    fh.write(json.dumps({"suite": suite, "rho_pre": rec.get("rho_pre"), "rebuild": rec.get("rebuild"),
                         "arms_changed": rec["arm"] != base["arm"], "n_pop": rec["n_in_population"],
                         "rho_state": (rec.get("rho_pre_detail") or {}).get("state", "(no detail: direct call)")[:40]}) + "\n")
    fh.flush()
    return rec
CP.plan_experiment = wrapped
sys.argv = [suite]
code = 0
try:
    runpy.run_path(os.path.join(live, suite), run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
print(f"CENSUS_EXIT {suite} {code}")
sys.exit(code)
