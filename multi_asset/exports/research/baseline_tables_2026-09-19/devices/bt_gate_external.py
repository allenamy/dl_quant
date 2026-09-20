#!/usr/bin/env python3
"""bt_gate_external.py — the acceptance gate REBOUND TO EXTERNAL INPUTS (round-6 review R6-02, lead's ruling 2026-09-20).

WHAT WAS WRONG WITH THE OLD GATE (the class, not the instance): every check was INTERNALLY CONSISTENT — the battery recomputed the 32-path
mean from the path files and compared shas the receipts themselves carried, and the pin check compared each input's hash to the value the RUN
CONFIG declared. So a tampered artefact whose receipts are recomputed to match (modified initial cash, modified base prices with the config's
sha updated, modified path economics re-signed) still passes. PASS therefore certified self-consistency, not that the numbers came from the
specified simulated execution on the specified inputs.

WHAT THIS GATE DOES INSTEAD
  E1  EXTERNAL INPUTS: every input is re-hashed FROM ITS OWN PATH and compared to an APPROVED TABLE committed in the research repo
      (APPROVED_INPUTS_2026-09-20.json). No sha is read from the run config or from any receipt.
  E2  ECONOMIC CONSTANTS: the canonical-JSON sha of the run config's economics (current_production_config + nav0_usdt + paths_R) must equal
      the approved constants sha ⇒ a changed initial cash / gross multiplier / chase weights is caught even if every receipt agrees with it.
  E3  the run config's own pins must MATCH the approved table (path and sha) ⇒ a tampered copy of the config on the machine is caught.
  E4  INITIAL STATE of every stored path: nav0[0] and navm0[0] equal the approved initial cash and gross0[0] == 0.
  E5  ECONOMIC RECOMPUTATION FROM THE EXTERNAL INPUTS ALONE: `--reproduce K` seeds per run directory are RE-RUN through the simulator with
      every input path taken from the APPROVED table (never from the config), on exactly the anchors the stored path declares, and every array
      — the window ledger (price P&L, funding, fees, turnover, NAV) and the 5-minute NAV — must be bitwise equal to the stored one. A tampered
      path cannot satisfy this by being self-consistent: the numbers are recomputed from the sealed ledger, the pinned price table, the pinned
      targets and the pinned calibration.
  E6  the old internal checks are KEPT (they are necessary, just not sufficient): AGG = the mean of the path files, and each path npz matches
      the sha its own json carries.
COVERAGE IS PART OF THE VERDICT (added 2026-09-20 after this device's own tamper test caught it): E5 only certifies the seeds it actually
re-ran. Re-running one sampled seed out of 32 catches a tampered path with probability 1/32, and the first version of this gate duly passed a
run directory whose seed 01 had been altered while seed 00 was the one reproduced. So:
  * `--reproduce all` re-runs every seed  ⇒ verdict **PASS** (publication grade),
  * `--reproduce K` with K < n_seeds      ⇒ verdict **PASS-SPOTCHECK**, which names the seeds covered and states that the rest are NOT
    certified. A spot check may not be cited as a publication gate.
  * `--reproduce 0` is refused outright (a zero-measurement pass).
`--workers J` forks J children after the shared inputs are loaded once (the price panel is shared copy-on-write, as in bt_launch.py).
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_gate_external.py PATH,HOME,LC_CTYPE
         <approved_inputs.json> <run_config.json> <run_dir> <n_seeds> --reproduce <K|all> [--workers J] <out.json>
"""
import os, sys, json, time, hashlib, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL

T0 = time.time()
APP_P, CFG_P, RUN_D, NSEED = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
_kv = sys.argv[sys.argv.index("--reproduce") + 1] if "--reproduce" in sys.argv else "0"
K = -1 if _kv == "all" else int(_kv)                       # -1 = every seed
JOBS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
OUTP = sys.argv[-1]
APP = json.load(open(APP_P)); CFG = json.load(open(CFG_P))
RES = []


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def econ_sha(cfg):
    """the economics this run was supposed to use — hashed as one block so no single field can be changed silently"""
    return hashlib.sha256(canon({"current_production_config": cfg["current_production_config"], "nav0_usdt": cfg["nav0_usdt"],
                                 "paths_R": cfg["paths_R"]}).encode()).hexdigest()


# ---------------- E1 external inputs ----------------
missing = []
for role, e in APP["inputs"].items():
    p = e["path"]
    if not os.path.exists(p):
        missing.append(role); ok(f"E1.{role}.present", False, p); continue
    got = DL.sha(p)
    ok(f"E1.{role}.sha_from_its_own_path_equals_the_approved_table", got == e["sha256"], {"path": p, "got": got[:16], "approved": e["sha256"][:16]})
ok("E1.every_approved_input_present", not missing, missing)

# ---------------- E2 economic constants ----------------
got_econ = econ_sha(CFG)
ok("E2.economics_block_sha_equals_the_approved_one", got_econ == APP["economics"]["sha256"],
   {"got": got_econ[:16], "approved": APP["economics"]["sha256"][:16], "block": "current_production_config + nav0_usdt + paths_R"})
ok("E2.initial_cash_equals_the_approved_constant", float(CFG["nav0_usdt"]) == float(APP["economics"]["nav0_usdt"]),
   {"config": CFG["nav0_usdt"], "approved": APP["economics"]["nav0_usdt"]})

# ---------------- E3 the config's pins vs the approved table ----------------
bad_pins = {}
for k, v in CFG["pins"].items():
    if "sha256" not in v or "path" not in v: continue
    a = APP["inputs"].get(APP["pin_role"].get(k, k))
    if a is None:
        bad_pins[k] = "no approved entry for this pin"
    elif a["sha256"] != v["sha256"] or os.path.abspath(a["path"]) != os.path.abspath(v["path"]):
        bad_pins[k] = {"config": {"path": v["path"], "sha": v["sha256"][:16]}, "approved": {"path": a["path"], "sha": a["sha256"][:16]}}
ok("E3.run_config_pins_match_the_approved_table", not bad_pins, bad_pins)
tg = {}
for r in CFG["runs"]:
    for s in (r.get("targets") or {}).get("sources", []):
        tg[os.path.abspath(s["npz"])] = s["npz_sha256"]
bad_t = {p: sh for p, sh in tg.items() if not any(os.path.abspath(e["path"]) == p and e["sha256"] == sh for e in APP["inputs"].values())}
ok("E3.target_files_named_by_the_runs_are_approved", not bad_t, bad_t)

# ---------------- E4 / E6 stored paths ----------------
tag = os.path.basename(RUN_D.rstrip("/"))
stems = [os.path.join(RUN_D, f"PATH_{tag}_seed_{s:02d}") for s in range(NSEED)]
present = [s for s in stems if os.path.exists(s + ".npz") and os.path.exists(s + ".json")]
ok("E4.all_paths_present", len(present) == NSEED, {"found": len(present), "expected": NSEED})
sha_bad = [os.path.basename(s) for s in present if json.load(open(s + ".json")).get("npz_sha256") != DL.sha(s + ".npz")]
ok("E6.each_path_npz_matches_the_sha_in_its_own_json", not sha_bad, sha_bad)
init = {}
for s in present:
    Z = np.load(s + ".npz")
    init[os.path.basename(s)] = {"nav0": float(Z["nav0"][0]), "navm0": float(Z["navm0"][0]), "gross0": float(Z["gross0"][0])}
n0 = float(APP["economics"]["nav0_usdt"])
bad_init = {k: v for k, v in init.items() if not (v["nav0"] == n0 and v["navm0"] == n0 and v["gross0"] == 0.0)}
ok("E4.initial_state_of_every_path_equals_the_approved_initial_cash_and_a_flat_book", not bad_init, {"approved_nav0": n0, "bad": bad_init})
aggj = [f for f in os.listdir(RUN_D) if f.startswith("AGG_") and f.endswith(".json")]
if len(aggj) != 1:
    ok("E6.one_AGG_file", False, aggj)
else:
    J = json.load(open(os.path.join(RUN_D, aggj[0]))); Z = np.load(os.path.join(RUN_D, aggj[0][:-5] + ".npz"))
    shas_ok = all(DL.sha(os.path.join(RUN_D, f["npz"])) == f["sha256"] for f in J["path_files"]) and DL.sha(os.path.join(RUN_D, aggj[0][:-5] + ".npz")) == J["agg_npz_sha256"]
    ok("E6.AGG_listing_shas_match_the_files", shas_ok, {"n_paths": len(J["path_files"])})
    P = [np.load(os.path.join(RUN_D, f["npz"])) for f in sorted(J["path_files"], key=lambda f: f["seed"])]
    re_ = DL.aggregate_arrays(P, float(APP["economics"]["current_production_config"]["gross_mult"]))
    ok("E6.AGG_equals_the_mean_of_the_path_files", all(np.array_equal(re_[k], Z[k]) for k in re_), {"keys": len(re_), "n_paths": len(P)})

# ---------------- E5 economic recomputation from the external inputs alone ----------------
K_eff = NSEED if K < 0 else min(K, NSEED)
ok("E5.reproduce_count_is_positive (a zero-measurement pass is refused)", K_eff > 0, {"--reproduce": _kv, "seeds_to_reproduce": K_eff})
rep = {}
if K_eff > 0 and present:
    CFG2 = json.loads(json.dumps(CFG))                      # the run config with EVERY pinned path/sha replaced by the approved table's
    for k, v in CFG2["pins"].items():
        a = APP["inputs"].get(APP["pin_role"].get(k, k))
        if a and "sha256" in v: v["path"], v["sha256"] = a["path"], a["sha256"]
    for r in CFG2["runs"]:
        for s in (r.get("targets") or {}).get("sources", []):
            for e in APP["inputs"].values():
                if os.path.basename(e["path"]) == os.path.basename(s["npz"]): s["npz"], s["npz_sha256"] = e["path"], e["sha256"]
                if os.path.basename(e["path"]) == os.path.basename(s["receipt"]): s["receipt"], s["receipt_sha256"] = e["path"], e["sha256"]
    CFG2["current_production_config"] = APP["economics"]["current_production_config"]; CFG2["nav0_usdt"] = APP["economics"]["nav0_usdt"]
    pin_fail = []
    DL.verify_pins(CFG2, lambda n, c, d=None: pin_fail.append(n) if not c else None)
    ok("E5.pins_verify_against_the_approved_paths", not pin_fail, pin_fail)
    ES, SL, BH, L2 = DL.import_modules(CFG2, HERE); SL.install_readonly_guard()
    run = next(x for x in CFG2["runs"] if x["tag"] == json.load(open(present[0] + ".json"))["tag"])
    A_ref = np.load(present[0] + ".npz")["A"].astype(np.int64)
    AX = np.arange(DL.ts(CFG2["window"]["first_anchor"]), DL.ts(CFG2["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
    i0 = int(np.searchsorted(AX, A_ref[0])); sel = slice(i0, i0 + len(A_ref))
    ok("E5.the_anchors_being_reproduced_are_on_the_config_axis", bool(np.array_equal(AX[sel], A_ref)),
       {"first": DL.iso(int(A_ref[0])) if hasattr(DL, "iso") else int(A_ref[0]), "n": len(A_ref)})
    cfail = []
    C = DL.load_context(CFG2, ES, BH, L2, sel, [run], lambda n, c, d=None: cfail.append(n) if not c else None, lambda *a: None)
    ok("E5.context_loads_from_the_approved_inputs", not cfail, cfail)
    seeds = sorted({int(json.load(open(s + ".json"))["seed"]) for s in present})[:K_eff]

    def compare(seed):
        st = os.path.join(RUN_D, f"PATH_{tag}_seed_{seed:02d}")
        arr, _out, _S = DL.run_one(C, run, seed)
        Z = np.load(st + ".npz"); diffs = {}
        for k in Z.files:
            a, b = np.asarray(Z[k]), np.asarray(arr[k])
            if a.shape != b.shape: diffs[k] = {"shape": [list(a.shape), list(b.shape)]}; continue
            if a.tobytes() == b.tobytes(): continue
            if a.dtype.kind == "f":
                neq = ~((a == b) | (np.isnan(a) & np.isnan(b)))
                if not neq.any(): continue
                dd = np.abs(a - b); dd = dd[np.isfinite(dd)]
                diffs[k] = {"n_differ": int(neq.sum()), "max_abs_delta": (float(dd.max()) if dd.size else None)}
            else:
                diffs[k] = {"n_differ": int(np.sum(a != b))}
        return {"keys": len(Z.files), "differing_keys": diffs}

    tmp = os.path.join(os.path.dirname(OUTP), ".gate_ext_%d" % os.getpid()); os.makedirs(tmp, exist_ok=True)
    kids, queue = {}, list(seeds)                                   # fork per seed: the loaded panel is shared copy-on-write
    while queue or kids:
        while queue and len(kids) < max(1, JOBS):
            seed = queue.pop(0); pid = os.fork()
            if pid == 0:
                try:
                    json.dump(compare(seed), open(os.path.join(tmp, f"{seed}.json"), "w")); os._exit(0)
                except BaseException:
                    import traceback; traceback.print_exc(); os._exit(1)
            kids[pid] = seed
        pid, status = os.wait(); seed = kids.pop(pid); rc = os.waitstatus_to_exitcode(status)
        r_ = json.load(open(os.path.join(tmp, f"{seed}.json"))) if rc == 0 and os.path.exists(os.path.join(tmp, f"{seed}.json")) else {"keys": 0, "differing_keys": {"__child__": f"rc {rc}"}}
        rep[f"seed_{seed:02d}"] = r_
        ok(f"E5.seed{seed:02d}.re-run_from_external_inputs_is_bitwise_the_stored_path", not r_["differing_keys"], {"differing": r_["differing_keys"]})
    shutil.rmtree(tmp, ignore_errors=True)
    ok("E5.every_reproduced_seed_accounted_for", len(rep) == len(seeds), {"reproduced": len(rep), "asked": len(seeds)})
fails = [r["check"] for r in RES if not r["ok"]]
covered = sorted(int(k.split("_")[1]) for k in rep)
full = len(covered) == NSEED
verdict = "RED" if fails else ("PASS" if full else "PASS-SPOTCHECK")
out = dict(device="bt_gate_external.py", self_sha256=DL.sha(os.path.abspath(__file__)), driver_lib_sha256=DL.sha(os.path.join(HERE, "bt_driver_lib.py")),
           argv=sys.argv, numpy=np.__version__, approved_table={"path": APP_P, "sha256": DL.sha(APP_P)}, run_config={"path": CFG_P, "sha256": DL.sha(CFG_P)},
           run_dir=RUN_D, n_seeds=NSEED, reproduce=_kv, workers=JOBS, reproduced=rep, initial_state=init,
           coverage={"seeds_reproduced": covered, "n_reproduced": len(covered), "n_seeds": NSEED, "full": full,
                     "not_certified": sorted(set(range(NSEED)) - set(covered)),
                     "meaning": ("every path in this directory was recomputed from the external inputs" if full else
                                 "ONLY the listed seeds were recomputed; the others are NOT certified by E5 and this receipt may not be cited as a publication gate")},
           checks=RES, failed=fails, VERDICT=verdict, runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
n_ok = sum(r["ok"] for r in RES)
print("BT_GATE_EXTERNAL VERDICT: " + (
      ("%s %d/%d checks (inputs re-hashed from source against the approved table; %d/%d paths recomputed bitwise from those inputs%s)"
       % (verdict, n_ok, len(RES), len(covered), NSEED, "" if full else "; seeds " + ",".join(str(x) for x in out["coverage"]["not_certified"]) + " NOT certified"))
      if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails[:8])), flush=True)
sys.exit(0 if not fails else 3)
