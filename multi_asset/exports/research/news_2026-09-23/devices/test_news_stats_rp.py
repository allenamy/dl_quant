"""R10-E02 red/green test for news_stats.select_rp_run (AMENDMENT 2). Uses Stage 1's real R-P reading receipts (OLD: 2 runs scaled+lit;
OLD_HOLD: 1 run; NEW_s42: 2 runs). Baseline must be GREEN first (each real receipt yields the published halted count through the base-cell
directory), then every mutation must be refused with an RPError naming the reason.
usage: python3 test_news_stats_rp.py <dir with BT_P_READING_OVN_{OLD,OLD_HOLD,NEW_s42}.json> <out.json>"""
import os, sys, json, copy, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_stats as NS

D, OUT = sys.argv[1:3]
S1 = "/dev/shm/ovn_2026-09-23/runs"
CASES = {"OLD": ("BT_P_READING_OVN_OLD.json", f"{S1}/OBJB_A0_scaled_rule_raw_UAFE", 32),
         "OLD_HOLD": ("BT_P_READING_OVN_OLD_HOLD.json", f"{S1}/OVN_OLD_HOLD_scaled_rule_raw_UAFE", 10),
         "NEW_s42": ("BT_P_READING_OVN_NEW_s42.json", f"{S1}/OVN_NEW_s42_scaled_rule_raw_UAFE", 0)}
rep = {"baseline": {}, "mutations": {}}
# ---- baseline GREEN (asserted before any mutation) ----
for arm, (fn, d, want) in CASES.items():
    r = NS.select_rp_run(os.path.join(D, fn), d)
    rep["baseline"][arm] = {"halted": r["halted_paths"], "want": want, "run_key": r["run_key"], "n_runs_in_receipt": len(json.load(open(os.path.join(D, fn)))["runs"])}
    assert r["halted_paths"] == want, (arm, r["halted_paths"], want)
base_green = True


def mutated(fn, f):
    R = json.load(open(os.path.join(D, fn))); f(R)
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(R, p); p.close(); return p.name


def run_key(R, d):
    return [k for k, v in R["runs"].items() if os.path.normpath(v["dir"]) == os.path.normpath(d)][0]


def expect_refused(name, path, d, must_contain, check_sha=True):
    try:
        r = NS.select_rp_run(path, d, check_device_sha=check_sha); rep["mutations"][name] = {"refused": False, "got": r["halted_paths"]}
    except NS.RPError as e:
        rep["mutations"][name] = {"refused": True, "reason": str(e)[:200], "reason_as_named": must_contain in str(e)}


fn, d, _ = CASES["OLD_HOLD"]
expect_refused("wrong_arm (OLD_HOLD receipt read for the NEWS_s42 base dir)", os.path.join(D, fn), "/dev/shm/news_2026-09-23/runs/NEWS_s42_scaled_rule_raw_UAFE", "runs match dir")
expect_refused("threshold_-0.99", mutated(fn, lambda R: R["rule"].__setitem__("threshold_cum_return", -0.99)), d, "threshold")
def same_seed(R):
    pp = R["runs"][run_key(R, d)]["bases"][NS.RP_BASE_KEY]["per_path"]
    R["runs"][run_key(R, d)]["bases"][NS.RP_BASE_KEY]["per_path"] = [dict(copy.deepcopy(pp[0]), seed=0) for _ in pp]
expect_refused("32_copies_of_seed0", mutated(fn, same_seed), d, "seeds are not exactly")
def cutoff_2024(R):
    R["rule"]["breach_by"] = "2024-12-31T20:00:00Z"; k = run_key(R, d); R["runs"][k]["window"][-1] = "2024-12-31T20:00:00Z"
    for x in R["runs"][k]["bases"][NS.RP_BASE_KEY]["per_path"]: x["window_last_anchor"] = "2024-12-31T20:00:00Z"
expect_refused("cutoff_2024_receipt", mutated(fn, cutoff_2024), d, "breach_by")
def cutoff_2024_runonly(R):
    k = run_key(R, d)
    for x in R["runs"][k]["bases"][NS.RP_BASE_KEY]["per_path"]: x["window_last_anchor"] = "2024-12-31T20:00:00Z"
expect_refused("cutoff_2024_per_path_only", mutated(fn, cutoff_2024_runonly), d, "window ends")
def dup_run(R):
    k = run_key(R, d); R["runs"][k + " DUP"] = copy.deepcopy(R["runs"][k])
expect_refused("two_runs_same_dir", mutated(fn, dup_run), d, "2 runs match")
expect_refused("device_sha_mismatch", mutated(fn, lambda R: R.__setitem__("self_sha256", "0" * 64)), d, "bt_p_reading sha")
ok = base_green and all(v["refused"] and v["reason_as_named"] for v in rep["mutations"].values())
rep["VERDICT"] = "PASS" if ok else "FAIL"; rep["news_stats_sha256"] = NS.sha(NS.__file__)
json.dump(rep, open(OUT, "w"), indent=1)
print(f"TEST_NEWS_STATS_RP VERDICT={rep['VERDICT']} baseline=GREEN mutations_refused_as_named={sum(1 for v in rep['mutations'].values() if v['refused'] and v['reason_as_named'])}/{len(rep['mutations'])}")
sys.exit(0 if ok else 3)
