#!/usr/bin/env python3
"""t2_tripwire.py — PREREG_T2 §7 leakage investigation for every arm whose A0-base W_ALPHA Δg point estimate exceeded +0.165
on either seed (read from RECEIPT_T2_judge.json). Offset spectrum on both seeds, A0 env:
  (a) path shift by refit months: stale1 (month M uses the refit of M-1) and lookahead1 (month M uses the refit of M+1)
  (b) name arms only: carry-input lead T2_CLEAD = -1 (panel row j-1, 4h stale) and +1 (row j+1, 4h future)
PASS iff, on both seeds, Δg(stale1) >= 0.5·Δg(0) AND (name arms) Δg(CLEAD -1) >= 0.5·Δg(0). Look-ahead offsets are reported, not gates.
Exact env dict per run (no inheritance); CPU only; writes only under /workspace/uplift_r2_2026-09-13/T2/.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_tripwire.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, shutil, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R15', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T2')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
T0 = time.time()
T2 = "/workspace/uplift_r2_2026-09-13/T2"; D = T2 + "/dev"; HC = "/workspace/review_scratch/health_check"; UP = "/workspace/uplift_2026-09-11"; PY = "/workspace/venv/bin/python"; DER = T2 + "/devices/w10_sleeve_t2.py"
PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"; DER_SHA = "380d6265082c67742a8cf47f844d76cf0e3cc3ca25557b29bdaf6c747907d341"
TRIP = 0.165; UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); NB = 2000
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(T2 + "/PREREG_T2_carry_net_sizing_2026-09-13.md") == PREREG_SHA and sha(DER) == DER_SHA
KR = json.load(open(T2 + "/receipts/RECEIPT_T2_kappa_main.json")); DR = json.load(open(T2 + "/receipts/RECEIPT_T2_drive.json")); JR = json.load(open(T2 + "/receipts/RECEIPT_T2_judge.json"))
assert KR["C1"]["PASS"] and DR["gate"]["P"]["PASS"] and DR["gate"]["PC0"]["PASS"] and DR["gate"]["PC1"]["PASS"]
PATHS = {k: KR["path_outputs"][k] for k in ("main", "stale1", "lookahead1")}
for k, v in PATHS.items(): assert sha(v["path"]) == v["sha256"], k
FIRED = [a for a, v in JR["decisions"].items() if v["tripwire_fired"]]
MODE = {a: JR["results"][a]["mode"] for a in JR["results"]}; KCOL = {a: JR["results"][a]["kcol"] for a in JR["results"]}
print("fired arms", FIRED, flush=True)
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
UM = HC + "/masks/umask_UPIT_CRYPTO.npz"; K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; COSTB = UP + "/r3k/costb_PWR_G230k.json"
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010", "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0",
                      "UMASK_NPZ": UM, "SLOW_NPY": K3, "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}
while float(open("/proc/loadavg").read().split()[0]) > 6.0:
    print("load > 6, waiting", flush=True); time.sleep(30)
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
RUNS = {}
def run(job):
    tag, seed, extra = job; dst = T2 + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed)); env.update(extra); env["OUT_TAG"] = tag; t0 = time.time()
    if not os.path.exists(dst):
        with open(T2 + "/logs/%s.log" % tag, "w") as lf: rc = subprocess.call([PY, DER], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=env)
        shutil.move(src, dst)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), env=env, env_whitelist=sorted(env), out=dst, out_sha256=sha(dst), self_sha256_reported=cfg["UPLIFT"]["self_sha256"], cfg_T2=cfg["T2"])
JOBS = []
for a in FIRED:
    for s in ("42", "2027"):
        common = {"T2_MODE": MODE[a], "T2_KCOL": KCOL[a]}
        JOBS += [("TW_%s_stale1_s%s" % (a, s), s, {**common, "T2_KPATH": PATHS["stale1"]["path"]}), ("TW_%s_look1_s%s" % (a, s), s, {**common, "T2_KPATH": PATHS["lookahead1"]["path"]})]
        if MODE[a] == "name":
            JOBS += [("TW_%s_cleadm1_s%s" % (a, s), s, {**common, "T2_KPATH": PATHS["main"]["path"], "T2_CLEAD": "-1"}), ("TW_%s_cleadp1_s%s" % (a, s), s, {**common, "T2_KPATH": PATHS["main"]["path"], "T2_CLEAD": "1"})]
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=6) as ex:
    for tag, r in ex.map(run, JOBS): RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), [t for t, r in RUNS.items() if r.get("FAIL")]
assert all(r["self_sha256_reported"] == DER_SHA for r in RUNS.values())
def g_of(tag):
    Z = np.load(T2 + "/arms/%s.npz" % tag, allow_pickle=True); C = [str(c) for c in Z["cols"]]; r = np.asarray(Z["d30_n2_c42_rec"], float)
    ts = r[:, C.index("ts")].astype(np.int64); g = r[:, C.index("net_ex")] / r[:, C.index("gross_total")]; car = r[:, C.index("carry_ex")] / r[:, C.index("gross_total")]; pnl = r[:, C.index("pnl_ex")] / r[:, C.index("gross_total")]
    return ts, g, car, pnl
DAYK = None
def boot(d, mask, ts):
    day = ts // 86400; idx = np.nonzero(mask)[0]; u, inv = np.unique(day[idx], return_inverse=True); tot = np.zeros(len(u)); cnt = np.zeros(len(u)); np.add.at(tot, inv, d[idx]); np.add.at(cnt, inv, 1.0)
    nd = len(u); ms = np.array([(lambda r_: tot[r_].sum() / cnt[r_].sum())(np.random.default_rng([20260905, k]).integers(0, nd, nd)) for k in range(NB)])
    return [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]
OUT = {}
for a in FIRED:
    per = {}
    for s in ("42", "2027"):
        ts, gb, cb, pb = g_of("GP_A0_s%s" % s); wa = ts <= UB; wa[:900] = False; assert wa.sum() == 9138
        res = {}
        for lab, tag in (("offset0", "%s_A0_s%s" % (a, s)), ("path_stale1", "TW_%s_stale1_s%s" % (a, s)), ("path_lookahead1", "TW_%s_look1_s%s" % (a, s)), ("carry_lead_minus1_stale", "TW_%s_cleadm1_s%s" % (a, s)), ("carry_lead_plus1_future", "TW_%s_cleadp1_s%s" % (a, s))):
            if not os.path.exists(T2 + "/arms/%s.npz" % tag): continue
            t_, g_, c_, p_ = g_of(tag); assert np.array_equal(t_, ts)
            d = g_ - gb; res[lab] = dict(tag=tag, dg=float(d[wa].mean()), ci95=boot(d, wa, ts), dcarry=float((c_ - cb)[wa].mean()), dpnl=float((p_ - pb)[wa].mean()))
        dg0 = res["offset0"]["dg"]
        cond_stale = bool(res["path_stale1"]["dg"] >= 0.5 * dg0)
        cond_clead = bool(res["carry_lead_minus1_stale"]["dg"] >= 0.5 * dg0) if MODE[a] == "name" else None
        per[s] = dict(offsets=res, reference="A0_s%s (GP_A0_s%s)" % (s, s), cond_path_stale1_ge_half=cond_stale, cond_carry_lead_minus1_ge_half=cond_clead,
                      ratio_stale1=res["path_stale1"]["dg"] / dg0 if dg0 else None, ratio_clead_m1=(res["carry_lead_minus1_stale"]["dg"] / dg0) if (dg0 and MODE[a] == "name") else None,
                      ratio_lookahead1=res["path_lookahead1"]["dg"] / dg0 if dg0 else None, ratio_clead_p1=(res["carry_lead_plus1_future"]["dg"] / dg0) if (dg0 and MODE[a] == "name") else None)
    PASS = all(per[s]["cond_path_stale1_ge_half"] and (per[s]["cond_carry_lead_minus1_ge_half"] is not False) for s in ("42", "2027"))
    OUT[a] = dict(PASS=bool(PASS), seeds=per, rule="PASS iff both seeds: dg(path stale1) >= 0.5*dg(0) AND (name arms) dg(CLEAD -1) >= 0.5*dg(0); look-ahead offsets reported, not gates (PREREG §7)")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, derived_device_sha256=DER_SHA, env=ENV, judge_receipt_sha256_at_start=sha(T2 + "/receipts/RECEIPT_T2_judge.json"), fired=FIRED, paths=PATHS, runs=RUNS, arms=OUT,
          gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, wall_s=round(time.time() - T0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T2 + "/receipts/RECEIPT_T2_tripwire.json", "w"), indent=1, default=float)
for a, v in OUT.items():
    for s, p in v["seeds"].items():
        print(a, "s" + s, json.dumps({k: (round(o["dg"], 4), [round(x, 4) for x in o["ci95"]]) for k, o in p["offsets"].items()}), "stale>=half", p["cond_path_stale1_ge_half"], "clead-1>=half", p["cond_carry_lead_minus1_ge_half"])
    print(a, "TRIPWIRE PASS", v["PASS"])
print("DONE_t2_tripwire", RC["wall_s"], "s")
