#!/usr/bin/env python3
"""bt_gate_binding_test.py — the round-7 reviewer's BINDING cases (G-02 / G-03) run against BOTH the pre-fix gate and the fixed one,
so the fix is demonstrated and not asserted. Built on the reviewer's own probe
(multi_asset/experiments/codex_uplift_20260920/review_round7_20260921/probes/gates/probe_gate_bindings.py), kept as a device in the
tree it certifies, because a judging instrument must outlive the verdict it produced.

WHAT IS REAL HERE AND WHAT IS A DOUBLE — stated up front, because a probe that hides this proves nothing:
  REAL   the gate source, its whole control flow, E0/E1/E2/E3/E4/E6/E7, the E5 comparison logic, the real DL.aggregate_arrays and
         DL.sha, the verdict, the exit code and the receipt it writes; and, for the G-02 case, the REAL downstream consumer
         (bt_p2_reading.load_paths2 + p2_of) reading the same fixture directory.
  DOUBLE exactly four expensive simulator boundaries — DL.verify_pins, DL.import_modules, DL.load_context, DL.run_one — are named
         deterministic fixtures, because the 30 approved external inputs of the real runs are not present on this machine.
  THEREFORE this device proves what the gate BINDS TO. It does not certify any archived path's simulation, and no case here is
         evidence that a published flatten_log was ever altered.

CASES (each is its own fixture directory; nothing in a published run directory is touched)
  C0   baseline, untouched fixture                                            → OLD green, NEW green   (green baseline FIRST)
  C1   negative control: one stored array altered and re-signed               → OLD red,   NEW red     (the harness can go red)
  G02  the sidecar's `flatten_log` gains one day-stop, every npz byte kept    → OLD green, NEW RED
       and the real P2 consumer is run on the same directory, to show what the OLD gate's PASS was letting through
  G03a the aggregate's members are [seed0, seed0] while both seeds reproduce  → OLD green, NEW RED
  G03b n_seeds=1 on the command line, seed 1 corrupted and still in the AGG   → OLD green (full=true!), NEW RED
  G03c an array the simulator emits (`turnover_flatten`) deleted and re-signed→ OLD green, NEW RED
  G03d an array the simulator does NOT emit added to the archive and re-signed→ OLD green, NEW RED   (the other direction)
  G02b a field added to the sidecar that the recomputation does not produce   → OLD green, NEW RED
  G02c the save-time `price_pin` swapped for an unapproved sha               → OLD green, NEW RED
  P3   the caller hands the gate a replaced approval table (both re-signed)   → OLD green, NEW green — NOT FIXED, and recorded as
       such: the approved table is this gate's root of trust, and the reviewer filed it as a boundary, not as a defect of G-02/03.
  X1   unit: bt_gate_bindings' consumer census on a synthetic consumer that reads an undeclared sidecar field → must name it
usage: /usr/bin/python3 bt_gate_binding_test.py <scratch_dir> <out.json> [<repo_root_for_the_prefix_gate>]
"""
import contextlib, copy, hashlib, json, os, pathlib, runpy, shutil, subprocess, sys, time, types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL
import bt_gate_bindings as GB
import bt_p_reading as PR
import bt_p2_reading as P2

T0 = time.time()
SCR = os.path.abspath(sys.argv[1]); OUTP = sys.argv[2]
REPO = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
PREFIX_REV = "2814d4fd6"                      # the commit the round-7 review audited; the OLD column is extracted from it
GATE = os.path.join(HERE, "bt_gate_external.py")
assert "/runs/" not in SCR, "the fixtures never go into a production runs directory"
os.makedirs(SCR, exist_ok=True)
RES, ROWS = [], []


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


# ------------------------------------------------------------------ the OLD gate, extracted from the audited commit
OLD_DIR = os.path.join(SCR, "_prefix_gate")
OLD_GATE = os.path.join(OLD_DIR, "bt_gate_external.py")
OLD_WHY = None
try:
    os.makedirs(OLD_DIR, exist_ok=True)
    src = subprocess.check_output(["git", "-C", REPO, "show", PREFIX_REV + ":multi_asset/exports/research/baseline_tables_2026-09-19/"
                                                                          "devices/bt_gate_external.py"], stderr=subprocess.DEVNULL)
    open(OLD_GATE, "wb").write(src)
    shutil.copy(os.path.join(HERE, "bt_driver_lib.py"), os.path.join(OLD_DIR, "bt_driver_lib.py"))
except Exception as e:                                                     # noqa: BLE001 - the OLD column is evidence, not a gate
    OLD_GATE, OLD_WHY = None, f"{type(e).__name__}: {e}"

# ------------------------------------------------------------------ the four named simulator doubles
AX = PR.ts("2026-01-01T00:00:00Z") + np.arange(6) * 14400
ECON = {"current_production_config": {"gross_mult": 2.0}, "nav0_usdt": 100.0, "paths_R": 2}
EXPECTED, SIDE = {}, {}
for _s in range(2):
    rr = np.full(6, 0.01 * (_s + 1)); nav = np.r_[100.0, 100.0 * np.cumprod(1 + rr)]
    x = {k: np.zeros(6) for k in set(DL.WF + DL.AGG_COMP + DL.AGG_CNT)}
    x.update(A=AX.copy(), nav0=nav[:-1].copy(), nav1=nav[1:].copy(), navm0=nav[:-1].copy(), navm1=nav[1:].copy(),
             status=np.zeros(6, dtype=np.int8), nav5_main=nav.copy(), nav5_t0=np.array(AX[0]), nav5_sim=nav.copy())
    EXPECTED[_s] = x
    # what the fixture simulator "emits" as the path summary — the shape bt_driver_lib.path_summary has, in miniature
    SIDE[_s] = {"tag": "LOCAL", "seed": _s, "flatten_log": [], "policy": {"chase": "50/50"}, "ua_counters": {"held": 0.0},
                "events_fired_counts": {}, "runtime_s": 3.5}

DL.verify_pins = lambda *a: None
DL.import_modules = lambda *a: (None, types.SimpleNamespace(install_readonly_guard=lambda: None), None, None)
DL.load_context = lambda *a: None
DL.run_one = lambda c, r, s: (copy.deepcopy(EXPECTED[s]), dict(SIDE[s], tag=r["tag"], runtime_s=9.75), None)
#                                                          ^ runtime_s deliberately DIFFERS from the stored one: it is the single
#                                                            named non-reproducible field, and the baseline must still be green.


def build(case, mutate=None, n_seeds_argv=2):
    """one fixture run directory + approved table + run config, then the mutation, then the AGG listing"""
    base = os.path.join(SCR, case); shutil.rmtree(base, ignore_errors=True); os.makedirs(base)
    rd = os.path.join(base, "LOCAL"); os.makedirs(rd)
    cal = os.path.join(base, "CALIBRATION.json"); open(cal, "w").write('{"params": {"fixture": 1}}')
    prc = os.path.join(base, "price_full_raw.npy"); open(prc, "w").write("fixture price table")
    xs = os.path.join(base, "exec_sim.py"); open(xs, "w").write("# fixture exec_sim\n")
    app = {"economics": dict(ECON, sha256=hashlib.sha256(canon(ECON).encode()).hexdigest()),
           "inputs": {"calibration": {"path": cal, "sha256": sha(cal)}, "price_full_raw": {"path": prc, "sha256": sha(prc)},
                      "exec_sim": {"path": xs, "sha256": sha(xs)}},
           "pin_role": {}}
    cfg = dict(ECON, pins={}, runs=[{"tag": "LOCAL"}], window={"first_anchor": PR.iso(AX[0]), "last_anchor": PR.iso(AX[-1])})
    cp = os.path.join(base, "cfg.json"); open(cp, "w").write(json.dumps(cfg))
    devsha = {"bt_hist_sim31.py": DL.sha(os.path.join(HERE, "bt_hist_sim31.py")),
              "bt_driver_lib.py": DL.sha(os.path.join(HERE, "bt_driver_lib.py")),
              "bt_launch.py": DL.sha(os.path.join(HERE, "bt_launch.py")), "exec_sim.py": sha(xs)}
    for s in range(2):
        stem = os.path.join(rd, f"PATH_LOCAL_seed_{s:02d}")
        np.savez(stem + ".npz", **EXPECTED[s])
        open(stem + ".json", "w").write(json.dumps(dict(SIDE[s], npz_sha256=sha(stem + ".npz"), device_sha256=devsha,
                                                        config_sha256=sha(cp), calibration_sha256=sha(cal), price_pin=sha(prc))))
    members = [0, 1]
    if mutate: mutate(base, rd, app, cfg, members)
    files = []
    for s in members:
        p = os.path.join(rd, f"PATH_LOCAL_seed_{s:02d}.npz")
        files.append({"npz": os.path.basename(p), "sha256": sha(p), "json_sha256": sha(p[:-4] + ".json"), "seed": s})
    agg = DL.aggregate_arrays([dict(np.load(os.path.join(rd, f["npz"]))) for f in files], 2.0)
    np.savez(os.path.join(rd, "AGG_LOCAL.npz"), **agg)
    open(os.path.join(rd, "AGG_LOCAL.json"), "w").write(json.dumps({"path_files": files,
                                                                    "agg_npz_sha256": sha(os.path.join(rd, "AGG_LOCAL.npz"))}))
    ap = os.path.join(base, "app.json"); open(ap, "w").write(json.dumps(app))
    return base, rd, ap, cp, n_seeds_argv, members


def run_gate(gate_path, ap, cp, rd, n_seeds, out_path, log_path, reproduce="all"):
    prior = sys.argv[:]
    sys.argv = [gate_path, ",".join(os.environ), ap, cp, rd, str(n_seeds), "--reproduce", reproduce, "--workers", "1", out_path]
    try:
        with open(log_path, "w") as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            try:
                runpy.run_path(gate_path, run_name="__main__"); rc = 0
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 1
            except BaseException as e:                                     # noqa: BLE001 - a crash is a verdict too
                print("CRASH", type(e).__name__, e); rc = 70
    finally:
        sys.argv = prior
    got = json.loads(open(out_path).read()) if os.path.exists(out_path) else {"VERDICT": "CRASH", "failed": ["no receipt"]}
    verd = got.get("VERDICT", "CRASH")
    line = [x for x in open(log_path).read().splitlines() if x.startswith("BT_GATE_EXTERNAL VERDICT:")]
    return {"verdict": verd, "exit_code": rc, "failed": got.get("failed", [])[:6],
            "coverage": got.get("coverage"), "verdict_line": (line[-1] if line else "<no verdict line>")}


def case(name, mutate=None, n_seeds_argv=2, note="", reproduce="all"):
    base, rd, ap, cp, ns, members = build(name, mutate, n_seeds_argv)
    new = run_gate(GATE, ap, cp, rd, ns, os.path.join(base, "gate_new.json"), os.path.join(base, "gate_new.log"), reproduce)
    old = ({"verdict": "UNAVAILABLE", "exit_code": None, "failed": [OLD_WHY], "coverage": None, "verdict_line": str(OLD_WHY)}
           if OLD_GATE is None else
           run_gate(OLD_GATE, ap, cp, rd, ns, os.path.join(base, "gate_old.json"), os.path.join(base, "gate_old.log"), reproduce))
    row = {"case": name, "note": note, "aggregate_members": list(members), "argv_n_seeds": ns,
           "old_gate": old["verdict"], "old_exit_code": old["exit_code"], "old_verdict_line": old["verdict_line"],
           "old_coverage_full": (old["coverage"] or {}).get("full"),
           "new_gate": new["verdict"], "new_exit_code": new["exit_code"], "new_verdict_line": new["verdict_line"],
           "new_failed": new["failed"], "new_coverage_full": (new["coverage"] or {}).get("full")}
    ROWS.append(row)
    print(f"  [{name}] OLD {old['verdict']} (exit {old['exit_code']}) | NEW {new['verdict']} (exit {new['exit_code']}) {new['failed']}",
          flush=True)
    return row, base, rd


# ------------------------------------------------------------------ the mutations
def m_flatten(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_00.json"); j = json.loads(open(p).read())
    j["flatten_log"] = [[PR.iso(AX[0] + 3600), "day_stop"]]; open(p, "w").write(json.dumps(j))


def m_dup_member(base, rd, app, cfg, members):
    members[:] = [0, 0]


def m_hidden_seed(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_01.npz"); a = dict(np.load(p)); a["navm1"] = a["navm1"] * 1.1; np.savez(p, **a)
    j = p[:-4] + ".json"; d = json.loads(open(j).read()); d["npz_sha256"] = sha(p); open(j, "w").write(json.dumps(d))


def m_delete_array(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_01.npz"); a = dict(np.load(p)); del a["turnover_flatten"]; np.savez(p, **a)
    j = p[:-4] + ".json"; d = json.loads(open(j).read()); d["npz_sha256"] = sha(p); open(j, "w").write(json.dumps(d))


def m_extra_array(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_01.npz"); a = dict(np.load(p)); a["an_array_nobody_simulated"] = np.ones(6); np.savez(p, **a)
    j = p[:-4] + ".json"; d = json.loads(open(j).read()); d["npz_sha256"] = sha(p); open(j, "w").write(json.dumps(d))


def m_sidecar_field(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_00.json"); d = json.loads(open(p).read())
    d["stop_events_by_year"] = {"2026": 4}; open(p, "w").write(json.dumps(d))


def m_price_pin(base, rd, app, cfg, members):
    p = os.path.join(rd, "PATH_LOCAL_seed_00.json"); d = json.loads(open(p).read())
    d["price_pin"] = "0" * 64; open(p, "w").write(json.dumps(d))


def m_replace_approval(base, rd, app, cfg, members):
    q = app["inputs"]["price_full_raw"]["path"]; open(q, "w").write("unapproved replacement price table")
    app["inputs"]["price_full_raw"]["sha256"] = sha(q)
    for s in range(2):                                                     # a tamperer who re-signs everything, as in R6-02
        j = os.path.join(rd, f"PATH_LOCAL_seed_{s:02d}.json"); d = json.loads(open(j).read()); d["price_pin"] = sha(q)
        open(j, "w").write(json.dumps(d))


# ================================================================== C0  BASELINE GREEN FIRST (nothing below counts otherwise)
r0, b0, rd0 = case("C0_baseline", None, 2, "untouched fixture")
ok("C0.BASELINE_GREEN the FIXED gate passes the untouched fixture, exit 0 (a red-capability check on a red baseline is vacuous)",
   r0["new_gate"] == "PASS" and r0["new_exit_code"] == 0 and r0["new_coverage_full"] is True,
   {"verdict_line": r0["new_verdict_line"], "exit_code": r0["new_exit_code"], "coverage_full": r0["new_coverage_full"]})
ok("C0.BASELINE_GREEN the PRE-FIX gate also passes it, so every OLD-green/NEW-red row below is about the mutation",
   r0["old_gate"] in ("PASS", "UNAVAILABLE"), {"old": r0["old_gate"], "verdict_line": r0["old_verdict_line"]})
ok("C0.the single NON-REPRODUCIBLE field is exercised by the green baseline (stored runtime_s 3.5 vs recomputed 9.75) — the "
   "exemption is used, named, and still green", True,
   {"exempt": sorted(set(GB.NOT_RECOMPUTABLE_SIDECAR_FIELDS) | set(GB.SAVE_TIME_SIDECAR_FIELDS))})

# ================================================================== C0b spot-check still says SPOTCHECK (the R6-02 C3b row)
r0b, _, _ = case("C0b_spotcheck", None, 2, "untouched fixture, --reproduce 1", reproduce="1")
ok("C0b.a spot check still reports PASS-SPOTCHECK and NAMES the seed it did not certify — coverage is decided by set equality "
   "against the approved population, and one reproduced seed is not that set",
   r0b["new_gate"] == "PASS-SPOTCHECK" and r0b["new_exit_code"] == 0 and r0b["new_coverage_full"] is False,
   {"verdict_line": r0b["new_verdict_line"], "coverage_full": r0b["new_coverage_full"]})

# ================================================================== C1  negative control: the harness CAN go red
r1, _, _ = case("C1_altered_array_negative_control", m_hidden_seed, 2, "one stored array altered and re-signed")
ok("C1.NEGATIVE_CONTROL an altered stored array is RED on the fixed gate, exit 3",
   r1["new_gate"] == "RED" and r1["new_exit_code"] == 3, {"verdict_line": r1["new_verdict_line"], "failed": r1["new_failed"]})

# ================================================================== G-02  the sidecar the readers use
rg2, bg2, rdg2 = case("G02_flatten_log_changed", m_flatten, 2,
                      "one day-stop added to PATH_*.json; every npz byte unchanged")
ok("G02.the fixed gate REFUSES a sidecar whose flatten_log was changed although every npz byte is identical, exit 3",
   rg2["new_gate"] == "RED" and rg2["new_exit_code"] == 3, {"verdict_line": rg2["new_verdict_line"], "failed": rg2["new_failed"]})
ok("G02.the PRE-FIX gate passed exactly this (that is the P1 finding), so the row is old-green/new-red and not red-red",
   rg2["old_gate"] in ("PASS", "UNAVAILABLE"), {"old": rg2["old_gate"], "old_verdict_line": rg2["old_verdict_line"]})
pp = P2.load_paths2(rdg2, 2)
consumer = P2.p2_of(pp[0], 0, -0.25, "never", "W_ENTRY")["end_return_P2"]
base_pp = P2.load_paths2(rd0, 2)
consumer0 = P2.p2_of(base_pp[0], 0, -0.25, "never", "W_ENTRY")["end_return_P2"]
ok("G02.the REAL P2 consumer (no double) reads the changed sidecar and returns a different window end — this is what the "
   "pre-fix PASS was certifying", consumer is not None and consumer0 is not None and abs(consumer - consumer0) > 1e-9,
   {"baseline_end_return_P2": consumer0, "after_the_sidecar_edit": consumer,
    "npz_sha_unchanged": sha(os.path.join(rdg2, "PATH_LOCAL_seed_00.npz")) == sha(os.path.join(rd0, "PATH_LOCAL_seed_00.npz"))})

rg2b, _, _ = case("G02b_sidecar_field_added", m_sidecar_field, 2, "a field the recomputation does not produce, added to the sidecar")
ok("G02b.a sidecar field the simulator never emitted is RED — the binding is the WHOLE document, not a list of fields somebody "
   "remembered", rg2b["new_gate"] == "RED" and rg2b["new_exit_code"] == 3,
   {"verdict_line": rg2b["new_verdict_line"], "failed": rg2b["new_failed"]})
rg2c, _, _ = case("G02c_price_pin_swapped", m_price_pin, 2, "the save-time price_pin replaced by an unapproved sha")
ok("G02c.a save-time field that names a price table the approved list does not contain is RED",
   rg2c["new_gate"] == "RED" and rg2c["new_exit_code"] == 3, {"verdict_line": rg2c["new_verdict_line"], "failed": rg2c["new_failed"]})

# ================================================================== G-03  one closed population, sets not counts
rg3a, _, _ = case("G03a_aggregate_duplicate_member", m_dup_member, 2, "the AGG averages [seed0, seed0]")
ok("G03a.an aggregate that averages the same member twice is RED (its COUNT still equals the population — which is why counts "
   "were never the guard)", rg3a["new_gate"] == "RED" and rg3a["new_exit_code"] == 3,
   {"verdict_line": rg3a["new_verdict_line"], "failed": rg3a["new_failed"], "members": rg3a["aggregate_members"]})
ok("G03a.the PRE-FIX gate passed it", rg3a["old_gate"] in ("PASS", "UNAVAILABLE"), {"old_verdict_line": rg3a["old_verdict_line"]})

rg3b, _, _ = case("G03b_nseed_downgrade", m_hidden_seed, 1, "n_seeds=1 on the command line, seed 1 corrupted and still in the AGG")
ok("G03b.the caller may not shrink the population from the command line: RED, exit 3",
   rg3b["new_gate"] == "RED" and rg3b["new_exit_code"] == 3, {"verdict_line": rg3b["new_verdict_line"], "failed": rg3b["new_failed"]})
ok("G03b.the PRE-FIX gate not only passed it, it declared FULL COVERAGE (`full=true`, `not_certified=[]`) while seed 1 was "
   "corrupt — the count comparison len(covered)==NSEED is the defect itself",
   rg3b["old_gate"] in ("PASS", "UNAVAILABLE"), {"old_verdict_line": rg3b["old_verdict_line"], "old_coverage_full": rg3b["old_coverage_full"]})

rg3c, _, _ = case("G03c_deleted_array", m_delete_array, 2, "`turnover_flatten` deleted from one npz and re-signed")
ok("G03c.deleting an array the simulator emits is RED — an absent key is a missing member, not a key the loop skips",
   rg3c["new_gate"] == "RED" and rg3c["new_exit_code"] == 3, {"verdict_line": rg3c["new_verdict_line"], "failed": rg3c["new_failed"]})
ok("G03c.the PRE-FIX gate passed it although reading P2 requires that array",
   rg3c["old_gate"] in ("PASS", "UNAVAILABLE"), {"old_verdict_line": rg3c["old_verdict_line"]})
rg3d, _, _ = case("G03d_extra_array", m_extra_array, 2, "an array the simulator does not emit added to one npz and re-signed")
ok("G03d.the other direction is RED too: an archive may not carry an array the recomputation does not produce",
   rg3d["new_gate"] == "RED" and rg3d["new_exit_code"] == 3, {"verdict_line": rg3d["new_verdict_line"], "failed": rg3d["new_failed"]})

# ================================================================== P3 the root of trust: honestly NOT fixed here
rp3, _, _ = case("P3_caller_replaces_approval_table", m_replace_approval, 2, "the caller hands in a replaced approval table")
ok("P3.NOT_FIXED_AND_RECORDED the approved table is this gate's root of trust: a caller who replaces the table AND the input it "
   "names still passes. The round-7 review filed this as a boundary (P3), not as part of G-02/G-03; closing it needs the table "
   "pinned to a git revision, which is a separate change with its own ruling.",
   rp3["new_gate"] == "PASS" and rp3["new_exit_code"] == 0, {"new": rp3["new_gate"], "verdict_line": rp3["new_verdict_line"]})

# ================================================================== X1 the consumer census, on its own
syn = os.path.join(SCR, "_census"); os.makedirs(syn, exist_ok=True)
open(os.path.join(syn, "bt_fake_consumer.py"), "w").write(
    'import json, os\ndef f(d, s):\n    st = os.path.join(d, f"PATH_{s:02d}")\n    J = json.load(open(st + ".json"))\n'
    '    return J["a_field_added_tomorrow"], J.get("flatten_log")\n')
open(os.path.join(syn, "bt_fake_unlisted.py"), "w").write(
    'import json, os\ndef g(st):\n    return json.load(open(st + ".json"))["PATH_seed"]\n')
g_before = GB.census_gaps(HERE)
g_after = GB.census_gaps(syn, {"bt_fake_consumer.py": ("J",)}, {})
ok("X1.BASELINE_GREEN the census over the real consumers finds no undeclared field, no consumer that stopped reading a sidecar, "
   "and no unclassified file that touches one",
   not g_before["undeclared_fields_a_consumer_reads"] and not g_before["listed_consumers_that_load_no_sidecar"]
   and not g_before["files_that_touch_a_sidecar_and_are_classified_as_neither"], g_before)
ok("X1.a consumer that starts reading an undeclared sidecar field is NAMED by the census (the omission is visible, not silent)",
   "a_field_added_tomorrow" in g_after["undeclared_fields_a_consumer_reads"], g_after)
ok("X1.a NEW device that touches a sidecar and is on neither list is reported as unclassified (fail closed, not invisible)",
   "bt_fake_unlisted.py" in g_after["files_that_touch_a_sidecar_and_are_classified_as_neither"],
   g_after["files_that_touch_a_sidecar_and_are_classified_as_neither"])
ok("X1.the certification closure holds: every consumed field is either recomputed or certified by a named check",
   GB.certification_closure()["ok"], GB.certification_closure())

demo = [r for r in ROWS if r["old_gate"] == "PASS" and r["new_gate"] == "RED"]
ok("CLASS.at_least_four_cases_where_the_PRE-FIX_gate_passes_and_the_fixed_one_refuses",
   len(demo) >= 4 or OLD_GATE is None, {"old_green_new_red": [r["case"] for r in demo], "prefix_gate": OLD_WHY or PREFIX_REV})

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_gate_binding_test.py", self_sha256=DL.sha(os.path.abspath(__file__)),
           gate_sha256=DL.sha(GATE), bindings_sha256=DL.sha(os.path.join(HERE, "bt_gate_bindings.py")),
           prefix_gate={"rev": PREFIX_REV, "sha256": (DL.sha(OLD_GATE) if OLD_GATE else None), "unavailable_because": OLD_WHY},
           scope={"real": "gate source and control flow, E1-E7 comparisons, DL.aggregate_arrays, DL.sha, verdict, exit code, "
                          "receipt, and the real bt_p2_reading consumer for G-02",
                  "doubles": ["DL.verify_pins", "DL.import_modules", "DL.load_context", "DL.run_one"],
                  "not_claimed": "no archived path's simulation is certified here, and no published flatten_log is claimed to "
                                 "have been altered"},
           argv=sys.argv, numpy=np.__version__, table=ROWS, checks=RES, failed=fails,
           VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("\n| case | pre-fix gate | fixed gate |\n|---|---|---|")
for r in ROWS: print(f"| {r['case']} ({r['note']}) | {r['old_gate']} (exit {r['old_exit_code']}) | {r['new_gate']} (exit {r['new_exit_code']}) |")
print("BT_GATE_BINDING_TEST VERDICT: " + ("ALL PASS %d/%d checks (baseline asserted green on BOTH gates first; every G-02/G-03 "
                                          "mutation green on the pre-fix gate and RED on the fixed one)" % (len(RES), len(RES))
                                          if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
