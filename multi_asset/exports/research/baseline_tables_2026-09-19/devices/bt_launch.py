#!/usr/bin/env python3
"""bt_launch.py — history driver for executor simulator v3.1 in RULE mode (prereg docs/PREREG_baseline_tables_certified_2026-09-19.md §2):
targets (S2 P2-CMB via p2_s2_lib.books, the same function stream R used) → bt_hist_sim31.HistSim31 (exec_sim v3.1 unchanged, pooled
calibration fda34243) → per-path 4h-window ledger + 5-minute NAV, 2.0× constant gross, the −4 % day rule, seeds 0..31.

Reads a FROZEN run configuration (JSON) and refuses unless every pinned input sha equals the file, the price receipt BT_PRICES_FULL is PASS
with the pinned output shas, the copied simulator files equal the approved v3.1 shas, and the 409ea16 executor tree equals INPUT_MANIFEST.
The price source and the UNAVAILABLE policy are PINNED INPUTS of each run (config `runs[*].price` ∈ {old, raw}; `runs[*].policy` ∈
bt_hist_sim31.POLICIES; `runs[*].ua_set` ∈ {UNAVAILABLE_3084, OLD_ZERO_PRICED_INLIFE_NAN}); every output records them.
All loading / path / aggregation code lives in bt_driver_lib.py (the battery calls the same functions).
One parent loads the shared inputs once and forks one child per (run, seed) (single-threaded, nice inherited, read-only guard installed);
a new child starts only while the memory gate passes (v1: memory.max − memory.current + inactive_file; v2 below: memory.max − anon − shmem) ≥ launch.min_available_gib.
Outputs (pod2, <root>/runs/<run>/): PATH_<run>_seed_NN.npz (+ .json with audits / events / counters / shas); after all seeds of a run,
AGG_<run>.npz = the per-window MEAN over the path files read back in seed order + AGG_<run>.json listing every path file and its sha256.
Receipt receipts/BT_LAUNCH_<label>.json (records the parent PGID and every child PID).
v2 (2026-09-19 11:5xZ, after the first full launch paused on its memory gate with 87/128 paths written): (1) the gate counts only
UNRECLAIMABLE memory — memory.max − anon − shmem (v1 also treated ACTIVE page cache, all of it another agent's, as used, and read 15 GiB while
anon was 18.8 of 61 GB); threshold unchanged (launch.min_available_gib = 22 ≥ the 20 GiB rule); (2) --resume: a (run, seed) whose PATH npz + json
exist and whose json's npz_sha256 equals the file is not re-run (paths are deterministic: battery D2, and bt_reproduce_path.py reproduced a
full-window path bitwise); the receipt lists every seed with resumed_existing true / false. Path content does not depend on this file.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE <config.json>
         [--smoke START_ISO N_ANCHORS SEEDS(comma) RUNS(comma) LABEL] [--resume LABEL]
"""
import os, sys, json, time, collections
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL
CFG_P = os.path.abspath(sys.argv[2]); CFG = json.load(open(CFG_P))
SMOKE = None; RESUME = None
if len(sys.argv) > 3 and sys.argv[3] == "--smoke":
    SMOKE = dict(start=DL.ts(sys.argv[4]), n=int(sys.argv[5]), seeds=[int(x) for x in sys.argv[6].split(",")], runs=sys.argv[7].split(","), label=sys.argv[8])
if len(sys.argv) > 3 and sys.argv[3] == "--resume":
    RESUME = sys.argv[4]
ROOT = CFG["paths"]["pod_root"]; LABEL = ("smoke_" + SMOKE["label"]) if SMOKE else ("full_" + RESUME if RESUME else "full")


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


rec = dict(device="bt_launch.py", self_sha256=DL.sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           python=sys.version.split()[0], utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), config=dict(path=CFG_P, sha256=DL.sha(CFG_P)),
           smoke=SMOKE, checks=[], runs={}, pgid=os.getpgid(0), parent_pid=os.getpid(), pids=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:240] if detail is not None else "")
    if not ok: FAILS.append(name)
RP = ROOT + f"/receipts/BT_LAUNCH_{LABEL}.json"
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(RP + ".tmp", "w"), indent=1, default=float); os.replace(RP + ".tmp", RP)
    print(line + " receipt_sha256=" + DL.sha(RP), flush=True); sys.exit(code)


DL.verify_pins(CFG, check)
if FAILS: finish(3, "BT_LAUNCH VERDICT=REFUSED")
ES, SL, BH, L2 = DL.import_modules(CFG, HERE)
check("exec_sim.version_v3.1", ES.VERSION == "v3.1", ES.VERSION)
SL.install_readonly_guard()                                               # inherited by every forked child
RUNS = [r for r in CFG["runs"] if (not SMOKE or r["tag"] in SMOKE["runs"])]
SEEDS = SMOKE["seeds"] if SMOKE else list(range(int(CFG["paths_R"])))
check("runs.selected", len(RUNS) > 0 and len(SEEDS) > 0, dict(runs=[r["tag"] for r in RUNS], seeds=SEEDS))
if SMOKE:
    AX0 = np.arange(DL.ts(CFG["window"]["first_anchor"]), DL.ts(CFG["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
    k0 = int(np.searchsorted(AX0, SMOKE["start"])); sel = slice(k0, k0 + SMOKE["n"])
else:
    sel = slice(0, int(CFG["window"]["n_anchors"]))
C = DL.load_context(CFG, ES, BH, L2, sel, RUNS, check, log)
rec["targets"] = C.target_info
if FAILS: finish(3, "BT_LAUNCH VERDICT=REFUSED")
DEV_SHA = {"device_sha256": {"bt_hist_sim31.py": DL.sha(os.path.join(HERE, "bt_hist_sim31.py")), "bt_driver_lib.py": DL.sha(os.path.join(HERE, "bt_driver_lib.py")),
                             "bt_launch.py": rec["self_sha256"], "exec_sim.py": DL.sha(CFG["pins"]["exec_sim"]["path"])},
           "config_sha256": rec["config"]["sha256"], "calibration_sha256": CFG["pins"]["calibration"]["sha256"]}


def run_dir(tag): return ROOT + ("/runs_smoke/" + SMOKE["label"] + "/" if SMOKE else "/runs/") + tag.replace("|", "_")
def stem_of(tag, s): return run_dir(tag) + f"/PATH_{tag.replace('|', '_')}_seed_{s:02d}"


def child(r, seed):
    os.makedirs(run_dir(r["tag"]), exist_ok=True)
    arr, out, S = DL.run_one(C, r, seed)
    return DL.save_path(stem_of(r["tag"], seed), arr, out, dict(DEV_SHA, price_pin=CFG["pins"][f"price_full_{r['price']}"]["sha256"]))


def aggregate(r):
    tag = r["tag"]; files = []; P = []
    for s in SEEDS:
        st = stem_of(tag, s)
        files.append(dict(seed=s, npz=os.path.basename(st) + ".npz", sha256=DL.sha(st + ".npz"), json_sha256=DL.sha(st + ".json"))); P.append(np.load(st + ".npz"))
    agg = DL.aggregate_arrays(P, C.GM); agg["seeds"] = np.array(SEEDS, np.int64)
    st = run_dir(tag) + f"/AGG_{tag.replace('|', '_')}"
    np.savez(st + ".tmp.npz", **agg); os.replace(st + ".tmp.npz", st + ".npz")
    js = dict(tag=tag, run=r, seeds=SEEDS, path_files=files, agg_npz_sha256=DL.sha(st + ".npz"), rule="bt_driver_lib.aggregate_arrays over the path files in seed order",
              config_sha256=rec["config"]["sha256"], label=LABEL)
    json.dump(js, open(st + ".json", "w"), indent=1)
    return js


def avail_gib():
    """v2: cgroup memory.max − anon − shmem (unreclaimable use only; page cache, active or inactive, is reclaimable)"""
    try:
        mx = int(open("/sys/fs/cgroup/memory.max").read().strip())
        st = dict(l.split() for l in open("/sys/fs/cgroup/memory.stat"))
        return (mx - int(st.get("anon", 0)) - int(st.get("shmem", 0))) / 2 ** 30
    except Exception:
        return float("inf")


def existing(r, s):
    st = stem_of(r["tag"], s)
    if not (os.path.exists(st + ".npz") and os.path.exists(st + ".json")): return None
    o = json.load(open(st + ".json"))
    return o if o.get("npz_sha256") == DL.sha(st + ".npz") else None


JOBS = [(r, s) for r in RUNS for s in SEEDS]
done = collections.defaultdict(int)
if RESUME:
    keep = []
    for r, s in JOBS:
        o = existing(r, s)
        if o is None: keep.append((r, s)); continue
        rec["runs"].setdefault(r["tag"], {"seeds": {}})["seeds"][s] = dict(rc=0, resumed_existing=True, runtime_s=o["runtime_s"], npz_sha256=o["npz_sha256"], audits=o["audits"],
                                                                           events=o["events_fired_counts"], ua=o["ua_counters"], device_sha256=o.get("device_sha256"))
        done[r["tag"]] += 1
    rec["resume"] = {"label": RESUME, "existing": len(JOBS) - len(keep), "to_run": len(keep)}
    JOBS = keep
    log("resume: existing", rec["resume"]["existing"], "to run", len(JOBS))
    for r in RUNS:
        if done[r["tag"]] == len(SEEDS) and not os.path.exists(run_dir(r["tag"]) + f"/AGG_{r['tag'].replace('|', '_')}.json"):
            rec["runs"][r["tag"]]["aggregate"] = aggregate(r); log("aggregated", r["tag"])
        elif done[r["tag"]] == len(SEEDS):
            rec["runs"][r["tag"]]["aggregate"] = json.load(open(run_dir(r["tag"]) + f"/AGG_{r['tag'].replace('|', '_')}.json"))
MAXP = int(CFG["launch"]["max_parallel"]); MINFREE = float(CFG["launch"]["min_available_gib"])
kids = {}; rec["mem_waits"] = 0; rec["mem_gate"] = "memory.max - anon - shmem >= launch.min_available_gib (v2)"
while JOBS or kids:
    while JOBS and len(kids) < MAXP:
        if avail_gib() < MINFREE:
            rec["mem_waits"] += 1
            if kids:
                log("memory: available %.1f GiB < %.1f — waiting for a running path before the next start" % (avail_gib(), MINFREE)); break
            log("memory: available %.1f GiB < %.1f and nothing running — polling every 60 s" % (avail_gib(), MINFREE)); time.sleep(60); continue
        r, s = JOBS.pop(0); pid = os.fork()
        if pid == 0:
            try:
                child(r, s); os._exit(0)
            except BaseException:
                import traceback; traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush(); os._exit(1)
        kids[pid] = (r, s); rec["pids"].append(pid); log("started", r["tag"], "seed", s, "pid", pid, "avail_GiB %.1f" % avail_gib())
    if not kids: continue
    pid, status = os.wait(); r, s = kids.pop(pid); rc = os.waitstatus_to_exitcode(status)
    rr = rec["runs"].setdefault(r["tag"], {"seeds": {}}); rr["seeds"][s] = dict(rc=rc, resumed_existing=False)
    if rc == 0:
        o = json.load(open(stem_of(r["tag"], s) + ".json"))
        rr["seeds"][s].update(runtime_s=o["runtime_s"], npz_sha256=o["npz_sha256"], audits=o["audits"], events=o["events_fired_counts"], ua=o["ua_counters"])
        done[r["tag"]] += 1
        if done[r["tag"]] == len(SEEDS):
            rr["aggregate"] = aggregate(r); log("aggregated", r["tag"])
    log("finished", r["tag"], "seed", s, "rc", rc, "avail_GiB %.1f" % avail_gib())
ok_all = all(v2["rc"] == 0 for v in rec["runs"].values() for v2 in v["seeds"].values()) and sum(len(v["seeds"]) for v in rec["runs"].values()) == len(RUNS) * len(SEEDS)
check("runs.all_rc0", ok_all, {t: {s: v2["rc"] for s, v2 in v["seeds"].items()} for t, v in rec["runs"].items()})
check("runs.audits_clean", all(DL.audits_clean(v2["audits"]) for v in rec["runs"].values() for v2 in v["seeds"].values() if v2["rc"] == 0))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "BT_LAUNCH VERDICT=%s label=%s runs=%d seeds=%d" % (rec["VERDICT"], LABEL, len(RUNS), len(SEEDS)))
