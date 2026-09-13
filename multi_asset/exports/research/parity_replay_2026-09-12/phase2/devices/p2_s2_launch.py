#!/usr/bin/env python3
"""S2 chain parent — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (file sha bc57266e…, commit 8dedb628) §A6.1 / §A6.12, plan P-A.
Loads the 5m cache ONCE, builds one p2_driver.Globals per arm sharing the cache pages, forks one serial production-path chain per arm (<= 8
children, OMP=1 each), waits for all of them, writes receipts/S2_LAUNCH{suffix}.json and prints one S2_LAUNCH_DONE summary line.
The driver p2_driver.py (dc4e6c85…) and the two stage devices are used unchanged. Arm-specific inputs = the arm dict (A6.1) and, for the A0pred
arms only, the F10 fold table replaced by the all-years yearly table of pod_f10_train_ext.py (A6.1: label_end(Y) = E_ext[first_te(Y) - 61] + 4h,
splice_boundary = 2**62 so f10_admissible always takes its yearly branch). Writes only under /workspace/uplift_r2_2026-09-13/P2.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s2_launch.py PATH,HOME,LC_CTYPE [--arms a,b] [--smoke N ISO]"""
import os, sys, json, time, calendar, hashlib, subprocess, traceback
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"   # before numpy; inherited by every forked chain
args = sys.argv[2:]
SMOKE = None
if "--smoke" in args:
    k = args.index("--smoke"); SMOKE = (int(args[k + 1]), args[k + 2]); del args[k:k + 3]
SEL = None
if "--arms" in args:
    k = args.index("--arms"); SEL = args[k + 1].split(","); del args[k:k + 2]
assert not args, f"unknown args {args}"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p2_driver as D
DRIVER_SHA = "dc4e6c8571bcc3bb6c1744fcda5f768ef9f0e3af17111574a15d188623082c54"
PREREG_SHA = "bc57266e5abf103926b2231facb4b12b28137565760ea34b4e8fc49c2cf15769"
assert D.sha(D.__file__) == DRIVER_SHA, "p2_driver.py sha"
SELF_SHA = D.sha(os.path.abspath(__file__))
PROTECTED = (333197, 339489)

ARMS = {   # A6.1, in launch order
    "S2_v4_s42":          dict(king_oof="SLOW_v4", f10_oof="v4RAW_s42", f10_seed="42", universe="pit", serve_policy="withhold", f10_table="driver"),
    "S2_v4_s2027":        dict(king_oof="SLOW_v4", f10_oof="v4RAW_s2027", f10_seed="2027", universe="pit", serve_policy="withhold", f10_table="driver"),
    "S2_A0pred_s42":      dict(king_oof="SLOW_v3_on_v4axis", f10_oof="A0_s42", f10_seed="42", universe="pit", serve_policy="withhold", f10_table="yearly_all"),
    "S2_A0pred_s2027":    dict(king_oof="SLOW_v3_on_v4axis", f10_oof="A0_s2027", f10_seed="2027", universe="pit", serve_policy="withhold", f10_table="yearly_all"),
    "S2_v4_s42_serveall": dict(king_oof="SLOW_v4", f10_oof="v4RAW_s42", f10_seed="42", universe="pit", serve_policy="serve_all", f10_table="driver"),
    "S2_v4_s42_pins":     dict(king_oof="SLOW_v4", f10_oof="v4RAW_s42", f10_seed="42", universe="pins", serve_policy="withhold", f10_table="driver"),
}
TAGS = [t for t in ARMS if SEL is None or t in SEL]
assert TAGS and len(TAGS) <= 8 and (SEL is None or sorted(SEL) == sorted(TAGS)), (SEL, TAGS)

def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
if SMOKE:
    S0 = ts(SMOKE[1]); assert S0 % 14400 == 0
    ANCHORS = list(range(S0, S0 + SMOKE[0] * 14400, 14400)); SUFFIX = "_smoke"
else:
    ANCHORS = list(range(ts("2022-01-31T00:00:00Z"), ts("2026-08-31T00:00:00Z") + 1, 14400)); SUFFIX = ""
    assert len(ANCHORS) == 10039
    U = np.load(D.SRC["universe"][0], allow_pickle=True)
    assert np.array_equal(U["ts"].astype(np.int64), np.array(ANCHORS, np.int64)), "A6.1: chain axis must equal the A0 rec axis (universe.npz)"

def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e: return f"ERR {e}"
def mem_current():
    try: return int(open("/sys/fs/cgroup/memory.current").read().strip())
    except Exception: return None
PRE = dict(utc=D.iso(time.time()), loadavg=open("/proc/loadavg").read().split()[:3], memory_current=mem_current(),
           protected_pids=sh("ps -o pid,stat,etime,args -p %d,%d | cut -c1-160" % PROTECTED),
           top_cpu=sh("ps -eo pid,user,stat,pcpu,rss,etime,args --sort=-pcpu | head -12 | cut -c1-160"),
           nvidia_smi=sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"))
print(json.dumps({"preflight": PRE}), flush=True)
assert float(PRE["loadavg"][0]) <= 12.0, ("A6.12: host busy, queue instead of competing", PRE["loadavg"])

def f10_yearly_all(seed):
    """A6.1 A0pred F10 fold table: pod_f10_train_ext.py yearly folds YV in 2023..2026 (L266-271: train i < first_te - 60 and year < YV) on the dlw_ext axis."""
    EX = np.load(D.SRC["dl_targets_ext"][0], allow_pickle=True)["E_ts"].astype(np.int64); yearly = {}
    for Y in (2023, 2024, 2025, 2026):
        fte = int(np.searchsorted(EX, calendar.timegm((Y, 1, 1, 0, 0, 0)))); yearly[Y] = int(EX[fte - 61]) + D.H4
    return {"seed": seed, "monthly_label_end": {}, "yearly_label_end": yearly, "splice_boundary": 2 ** 62,
            "rule": "AMENDMENT 6 A6.1: f10_A0 = f8_ext f10_V2MAIN yearly OOS, all four years yearly; admissible iff label_end < month start of E"}

# ── globals: the cache is loaded once (first arm), every other arm shares the arrays; OOF files are sha-checked per arm ──
t0 = time.time(); G = {}; ft_override = {}
for n_, tag in enumerate(TAGS):
    arm = dict(ARMS[tag]); arm.update(tag=tag + SUFFIX, start=D.iso(ANCHORS[0]), end=D.iso(ANCHORS[-1]), n_anchors=len(ANCHORS), record_from=None,
                                     combo_launch="fork", contract=f"PREREG AMENDMENT 6 sha256 {PREREG_SHA}", launcher_sha256=SELF_SHA)
    if n_ == 0:
        g = D.Globals(arm, verify_sha=True, load_cache=True); base = g
    else:
        g = D.Globals(arm, verify_sha=False, load_cache=False)
        for k_ in ("king_oof", "f10_oof"):
            p_, s_ = (D.KING_OOF if k_ == "king_oof" else D.F10_OOF)[arm[k_]]; assert D.sha(p_) == s_, (tag, k_, p_)
        g.shas["king_oof"] = D.KING_OOF[arm["king_oof"]][1]; g.shas["f10_oof"] = D.F10_OOF[arm["f10_oof"]][1]
        for k_, (p_, s_) in D.SRC.items(): g.shas[k_] = s_          # verified once on the first arm (same files)
        g.TS = base.TS; g.DATA = base.DATA; g.row_of_ts = base.row_of_ts
    if arm["f10_table"] == "yearly_all":
        g.ft = f10_yearly_all(arm["f10_seed"]); ft_override[tag] = {str(k): D.iso(v) for k, v in g.ft["yearly_label_end"].items()}
    else:
        assert arm["f10_table"] == "driver"
    G[tag] = (arm, g)
    print(json.dumps({"globals": tag, "load_s": round(time.time() - t0, 1), "king_label_end": {str(k): D.iso(v) for k, v in g.kt["label_end"].items()},
                      "f10_yearly": {str(k): D.iso(v) for k, v in g.ft["yearly_label_end"].items()}, "splice_boundary": g.ft["splice_boundary"]}), flush=True)
for tag in TAGS: assert G[tag][1].DATA is G[TAGS[0]][1].DATA
LOAD_S = round(time.time() - t0, 1)
print(json.dumps({"all_globals_s": LOAD_S, "memory_current": mem_current()}), flush=True)

# ── fork one chain per arm ──
children = {}; started = {}
for tag in TAGS:
    arm, g = G[tag]
    rh = D.under(f"{D.P2}/work/runs/{arm['tag']}"); os.makedirs(rh, exist_ok=True)
    out = D.under(f"{D.P2}/receipts/RUN_{arm['tag']}.json"); logp = D.under(f"{D.P2}/receipts/RUN_{arm['tag']}.log")
    sys.stdout.flush(); sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            # fd 1/2 are re-pointed with dup2 ONLY; sys.stdout/sys.stderr stay the interpreter's own objects (held by sys.__stdout__). Smoke attempt 1
            # replaced them with os.fdopen(1) objects: run_stage_forked's own `sys.stdout = os.fdopen(1)` then dropped the last reference to that
            # object in the combo grandchild, whose finaliser closed fd 1 -> empty combo_stage.log and rc=1 (receipts S2_LAUNCH_smoke.attempt1_fdclose.*).
            fd = os.open(logp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644); os.dup2(fd, 1); os.dup2(fd, 2); os.close(fd)
            tc = time.time()
            print(json.dumps({"chain": arm["tag"], "arm": arm, "pid": os.getpid(), "n_anchors": len(ANCHORS), "first": D.iso(ANCHORS[0]), "last": D.iso(ANCHORS[-1])}), flush=True)
            recs = D.run_chain(arm, g, ANCHORS, rh, out, record_from=None, log_every=(1 if len(ANCHORS) <= 50 else 200))
            doc = json.load(open(out)); doc["wall_s"] = round(time.time() - tc, 1); doc["launcher_sha256"] = SELF_SHA; doc["prereg_sha256"] = PREREG_SHA
            doc["argv"] = sys.argv; doc["env"] = dict(os.environ); doc["f10_fold_table_override"] = ft_override.get(tag)
            json.dump(doc, open(out + ".tmp", "w")); os.replace(out + ".tmp", out)
            tt = [r["timing_s"]["total"] for r in recs]
            print("P2_RUN_DONE", arm["tag"], "n", len(recs), "wall_s", doc["wall_s"], "per_anchor_total_s mean", round(float(np.mean(tt)), 3) if tt else None, flush=True)
            code = 0
        except BaseException:
            traceback.print_exc(); code = 1
        finally:
            try: sys.stdout.flush()
            except Exception: pass
            os._exit(code)
    children[pid] = tag; started[tag] = time.time()
    print(json.dumps({"forked": tag, "pid": pid}), flush=True)

RES = {}
while children:
    pid, status = os.wait()
    tag = children.pop(pid); rc = os.waitstatus_to_exitcode(status)
    arm = G[tag][0]; rp = f"{D.P2}/receipts/RUN_{arm['tag']}.json"; info = {}
    if os.path.exists(rp):
        try:
            d = json.load(open(rp)); info = dict(n_records=d.get("n_records"), fatal=d.get("fatal"), driver_sha256=d.get("driver_sha256"), receipt_sha256=D.sha(rp),
                                             vec_sha256=(D.sha(rp.replace(".json", ".vec.npz")) if os.path.exists(rp.replace(".json", ".vec.npz")) else None))
        except Exception as e:
            info = dict(receipt_unreadable=repr(e)[:200])
    RES[tag] = dict(pid=pid, rc=rc, wall_s=round(time.time() - started[tag], 1), **info)
    print(json.dumps({"exited": tag, **RES[tag], "memory_current": mem_current()}), flush=True)

POST = dict(utc=D.iso(time.time()), loadavg=open("/proc/loadavg").read().split()[:3], memory_current=mem_current(),
            protected_pids=sh("ps -o pid,stat,etime,args -p %d,%d | cut -c1-160" % PROTECTED),
            nvidia_smi=sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"))
ALL_OK = all(RES[t]["rc"] == 0 and RES[t].get("n_records") == len(ANCHORS) and RES[t].get("fatal") is None for t in TAGS)
doc = dict(device="p2_s2_launch.py", self_sha256=SELF_SHA, driver_sha256=DRIVER_SHA, prereg_sha256=PREREG_SHA, argv=sys.argv, env=dict(os.environ),
           smoke=SMOKE, n_anchors=len(ANCHORS), first=D.iso(ANCHORS[0]), last=D.iso(ANCHORS[-1]), arms={t: G[t][0] for t in TAGS},
           f10_fold_table_override=ft_override, globals_load_s=LOAD_S, preflight=PRE, postflight=POST, results=RES, all_rc0_and_complete=ALL_OK)
outp = D.under(f"{D.P2}/receipts/S2_LAUNCH{SUFFIX}.json"); json.dump(doc, open(outp + ".tmp", "w"), indent=1); os.replace(outp + ".tmp", outp)
print("S2_LAUNCH_DONE" + SUFFIX, "all_rc0_and_complete=%s" % ALL_OK, " ".join("%s:rc=%s,n=%s" % (t, RES[t]["rc"], RES[t].get("n_records")) for t in TAGS),
      "receipt_sha256=%s" % D.sha(outp), flush=True)
sys.exit(0 if ALL_OK else 3)
