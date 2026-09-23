#!/usr/bin/env python3
"""Red/green test for fresh_stats.select_rp_run (the R-P run-selection contract; review R10-E02 found that a reading receipt can
hold two runs — scaled + lit — so `assert len(runs)==1` is not a selection).

Baseline is asserted GREEN FIRST and every baseline cell prints its measured values (not just PASS): for each real receipt the
selector must return exactly one run, through the base-cell directory the tables load, and — where the published count is known —
the published halted count. Only then is each mutation required to be REFUSED with an RPError naming the reason.

usage: python -B test_fresh_stats_rp.py PATH,HOME,LC_CTYPE <cases.json> <out.json>
  cases.json = [{"name":…, "receipt":…, "dir":…, "want": <int or null>}, …]   (want=null ⇒ baseline records the measured count)
"""
import os, sys, json, copy, tempfile
WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fresh_stats as FS

CASES_PATH, OUT = sys.argv[2:4]
CASES = json.load(open(CASES_PATH))
rep = {"device": "test_fresh_stats_rp.py", "self_sha256": FS.sha(os.path.abspath(__file__)), "fresh_stats_sha256": FS.sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fresh_stats.py")),
       "cases_file": CASES_PATH, "cases_sha256": FS.sha(CASES_PATH), "baseline": {}, "mutations": {}}

# ───── baseline GREEN, asserted before any mutation; every measured attribute printed ─────
for c in CASES:
    r = FS.select_rp_run(c["receipt"], c["dir"])
    R = json.load(open(c["receipt"]))
    rep["baseline"][c["name"]] = {"receipt": c["receipt"], "expected_dir": c["dir"], "run_key": r["run_key"], "run_dir": r["run_dir"],
                                  "n_runs_in_receipt": len(R["runs"]), "run_keys_in_receipt": list(R["runs"]),
                                  "halted_paths": r["halted_paths"], "want": c["want"], "n_paths": r["n_paths"],
                                  "threshold": r["threshold"], "base": r["base"], "window_end": r["window_end"]}
    assert r["n_paths"] == FS.NPATH, (c["name"], "n_paths", r["n_paths"])
    if c["want"] is not None:
        assert r["halted_paths"] == c["want"], (c["name"], r["halted_paths"], c["want"])
rep["baseline_green"] = True
assert rep["baseline_green"], "baseline must be green before any mutation is meaningful"

BASE = CASES[0]                      # the receipt mutations are applied to
OTHER = CASES[1] if len(CASES) > 1 else CASES[0]


def mutated(path, f):
    R = json.load(open(path)); f(R)
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(R, p); p.close(); return p.name


def run_key_for(R, d):
    return [k for k, v in R["runs"].items() if os.path.normpath(v["dir"]) == os.path.normpath(d)][0]


def expect_refused(name, path, d, must_contain, check_sha=True):
    try:
        r = FS.select_rp_run(path, d, check_device_sha=check_sha)
        rep["mutations"][name] = {"refused": False, "got_halted": r["halted_paths"], "run_key": r["run_key"], "reason_as_named": False}
    except FS.RPError as e:
        rep["mutations"][name] = {"refused": True, "reason": str(e)[:300], "reason_as_named": must_contain in str(e)}


# 1. wrong arm: a real receipt read for a directory that belongs to another arm
expect_refused(f"wrong_arm ({os.path.basename(BASE['receipt'])} read for {os.path.basename(OTHER['dir'])})", BASE["receipt"], OTHER["dir"] if OTHER["dir"] != BASE["dir"] else BASE["dir"] + "_OTHER", "runs match dir")
# 2. threshold moved off the frozen −25 %
expect_refused("threshold_-0.99", mutated(BASE["receipt"], lambda R: R["rule"].__setitem__("threshold_cum_return", -0.99)), BASE["dir"], "threshold")
# 3. the FULL_RECIPE base removed from the rule
expect_refused("full_recipe_base_removed", mutated(BASE["receipt"], lambda R: R["rule"].__setitem__("bases", [b for b in R["rule"]["bases"] if b.get("anchor") != FS.RP_BASE_ANCHOR])), BASE["dir"], "FULL_RECIPE base")
# 4. 32 copies of seed 0 instead of 32 distinct paths


def dup_seed0(R):
    k = run_key_for(R, BASE["dir"]); pp = R["runs"][k]["bases"][FS.RP_BASE_KEY]["per_path"]
    R["runs"][k]["bases"][FS.RP_BASE_KEY]["per_path"] = [copy.deepcopy(pp[0]) for _ in range(FS.NPATH)]


expect_refused("32_copies_of_seed0", mutated(BASE["receipt"], dup_seed0), BASE["dir"], "seeds are not exactly")
# 5. window cut off at the end of 2024 (rule level)
expect_refused("cutoff_2024_rule", mutated(BASE["receipt"], lambda R: R["rule"].__setitem__("breach_by", "2024-12-31T20:00:00Z")), BASE["dir"], "breach_by")
# 6. window cut off at the end of 2024 (per-path level only — the rule still claims the full window)


def cut_perpath(R):
    k = run_key_for(R, BASE["dir"])
    for x in R["runs"][k]["bases"][FS.RP_BASE_KEY]["per_path"]: x["window_last_anchor"] = "2024-12-31T20:00:00Z"


expect_refused("cutoff_2024_per_path_only", mutated(BASE["receipt"], cut_perpath), BASE["dir"], "per-path window ends")
# 7. two runs claiming the same directory (the ambiguity the old `len(runs)==1` assertion could not see)


def dup_run(R):
    k = run_key_for(R, BASE["dir"]); R["runs"][k + " DUP"] = copy.deepcopy(R["runs"][k])


expect_refused("two_runs_same_dir", mutated(BASE["receipt"], dup_run), BASE["dir"], "runs match dir")
# 8. n_paths field no longer 32
expect_refused("n_paths_31", mutated(BASE["receipt"], lambda R: R["runs"][run_key_for(R, BASE["dir"])].__setitem__("n_paths", 31)), BASE["dir"], "n_paths")
# 9. a different bt_p_reading device produced the receipt
expect_refused("device_sha_mismatch", mutated(BASE["receipt"], lambda R: R.__setitem__("self_sha256", "0" * 64)), BASE["dir"], "bt_p_reading sha")

rep["VERDICT"] = "PASS" if all(v["refused"] and v["reason_as_named"] for v in rep["mutations"].values()) else "FAIL"
json.dump(rep, open(OUT, "w"), indent=1)
print("TEST_FRESH_STATS_RP VERDICT=" + rep["VERDICT"], "baseline", json.dumps({k: {"halted": v["halted_paths"], "want": v["want"], "n_runs": v["n_runs_in_receipt"]} for k, v in rep["baseline"].items()}),
      "mutations_refused", sum(v["refused"] for v in rep["mutations"].values()), "/", len(rep["mutations"]), flush=True)
sys.exit(0 if rep["VERDICT"] == "PASS" else 3)
