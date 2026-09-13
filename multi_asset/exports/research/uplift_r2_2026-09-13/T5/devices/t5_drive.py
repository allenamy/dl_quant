#!/usr/bin/env python3
"""t5_drive.py — pod2 driver (PREREG_T5 §9 step 3, gate G-P). Runs the T5 derived device (T1_INSTR=1, T5_DUMP=1) for C0 x seeds {42, 2027}
with EXACT env dicts (A0 knobs as in T1/r18 drivers), then asserts every array of the T1 arm bitwise equal (rec, W, T1 per-leg arrays, R18A,
legs series, S0) and the self-reported sha == derived sha. CPU only; writes only under /workspace/uplift_r2_2026-09-13/T5/.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t5_drive.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T1_', 'T5_')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"; T1R = "/workspace/uplift_r2_2026-09-13/T1"
PREREG = R + "/PREREG_T5_deployed_carry_gap_2026-09-13.md"; PREREG_SHA = "33b20fa10109b95d9b4f0ff480619d82cd9bd1b7d2def7cf0a38c7938e83660f"
T1DEV = T1R + "/devices/w10_sleeve_t1.py"; T1DEV_SHA = "0a8114398e7626abe27a3294c1508e1a46bf2f7c2a6fdbda318bc9a262ca00e3"
DER = R + "/devices/w10_sleeve_t5.py"; DER_SHA_MAC = "4c5b972eebfb48c3423b0f6c1336b13cb588fb8ec8edf9c7948d67c59dc05add"; PY = "/workspace/venv/bin/python"
T1ARMS = {"42": (T1R + "/arms/C0_s42.npz", "93484e8186cabc7ab4d739b283665453542b4ea32eb00e9334be5c7879d0dd09"), "2027": (T1R + "/arms/C0_s2027.npz", "d23e4503dfcb44cccf4d9d0ae4ffa0fd1735fba5516d425b8d1b733f7901623c")}
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"; COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG))
assert sha(T1DEV) == T1DEV_SHA, ("T1 DEVICE SHA", sha(T1DEV))
assert sha(COSTB) == COSTB_SHA
for s_, (p_, h_) in T1ARMS.items(): assert sha(p_) == h_, ("T1 ARM SHA", s_, sha(p_))
# generate the derived device on pod2 from pod2's own T1 copy; must equal the Mac-generated sha
subprocess.check_call([PY, R + "/devices/mk_t5_device.py", T1DEV, DER, PREREG])
DER_SHA = sha(DER); assert DER_SHA == DER_SHA_MAC, ("derived device sha differs from Mac", DER_SHA)
SELF_SHA = sha(os.path.abspath(__file__))
for p in (D + "/logs", D + "/probe_artifacts", R + "/arms", R + "/receipts"): os.makedirs(p, exist_ok=True)
BK = D + "/pod_backup_2026-08-21"; os.makedirs(BK, exist_ok=True)
LINKS = {BK + "/nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
         BK + "/nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         BK + "/slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy",
         BK + "/wide_fea_hist_meta.npz": "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
         BK + "/wide_panel_4h_hist_v2.npz": "/workspace/data/wide_panel_4h_v2ext.npz",
         D + "/dlw_2026-08-22": "/workspace/dlw_v4raw", D + "/f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}
for t, v in LINKS.items():
    assert os.path.exists(v), v
    if not os.path.islink(t): os.symlink(v, t)
    assert os.path.realpath(t) == os.path.realpath(v), (t, os.path.realpath(t))
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; UM = HC + "/masks/umask_UPIT_CRYPTO.npz"
INPUTS = {k: dict(realpath=os.path.realpath(v), sha256=sha(v)) for k, v in LINKS.items() if os.path.isfile(v)}
for k in (K3, UM, COSTB, "/workspace/dlw_v4raw/data/dlw_targets.npz", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"):
    INPUTS[k] = dict(realpath=os.path.realpath(k), sha256=sha(k))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                      "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": UM, "SLOW_NPY": K3,
                      "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}
EXTRA_ENV = {"R18_INSTR": "1", "T1_INSTR": "1", "T5_DUMP": "1"}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE, QUEUE", GPU0)
assert float(LOAD0[0]) <= 16.0, ("LOAD TOO HIGH, WAIT", LOAD0)
RUNS = {}
def run(seed):
    tag = "C0_s%s" % seed; dst = R + "/arms/%s_t5.npz" % tag
    env = dict(BASE); env.update(A0(seed)); env.update(EXTRA_ENV); env["OUT_TAG"] = tag
    t0 = time.time()
    if not os.path.exists(dst):
        with open(D + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call([PY, DER], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=env)
        shutil.move(src, dst)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), device=DER, device_sha256=DER_SHA, self_sha256_reported=cfg["UPLIFT"]["self_sha256"], cfg_T5=cfg.get("T5"), cfg_T1=cfg.get("T1"), env=env, out=dst, out_sha256=sha(dst))
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=2) as ex:
    for tag, r in ex.map(run, ["42", "2027"]):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), RUNS
for tag, r in RUNS.items():
    assert r["self_sha256_reported"] == DER_SHA, (tag, r["self_sha256_reported"], DER_SHA)
    assert r["cfg_T5"] and r["cfg_T5"]["T5_DUMP"] == 1 and r["cfg_T5"]["prereg_sha256"] == PREREG_SHA, (tag, r["cfg_T5"])
def bitwise(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape), dtype_a=str(a.dtype), dtype_b=str(b.dtype))
    if a.dtype.kind in "fc":
        na, nb = np.isnan(a), np.isnan(b); ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
        return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a.astype(float) - b.astype(float)))))
    return dict(bitwise=bool(np.array_equal(a, b)), shape=list(a.shape))
GATE = {"P": {}}
for seed in ("42", "2027"):
    tag = "C0_s%s" % seed
    A = np.load(R + "/arms/%s_t5.npz" % tag, allow_pickle=True); B = np.load(T1ARMS[seed][0], allow_pickle=True)
    keysB = sorted(k for k in B.files if k != "config_json"); keysA_extra = sorted(k for k in A.files if k not in B.files)
    g = {k: bitwise(A[k], B[k]) for k in keysB}
    GATE["P"][tag] = dict(n_keys_compared=len(keysB), all_bitwise=all(v["bitwise"] for v in g.values()), failing=[k for k, v in g.items() if not v["bitwise"]], extra_keys_T5=keysA_extra,
                          n_window_anchors=int(A["d30_n2_c42_T5_ts"].shape[0]), window_first=int(A["d30_n2_c42_T5_ts"][0]), window_last=int(A["d30_n2_c42_T5_ts"][-1]))
GATE["P"]["PASS"] = all(v["all_bitwise"] and v["n_window_anchors"] == 31 and v["window_first"] == 1787688000 and v["window_last"] == 1788120000 for k, v in GATE["P"].items() if k != "PASS")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, t1_device_sha256=T1DEV_SHA, derived_device_sha256=DER_SHA, derived_device=DER,
          env=dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv), python=sys.version.split()[0], numpy=np.__version__),
          inputs=INPUTS, base_env=BASE, extra_env=EXTRA_ENV, runs=RUNS, gate=GATE, gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1,
          loadavg_before=LOAD0, loadavg_after=LOAD1, wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_T5_drive_gateP.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
print("DONE_t5_drive", RC["wall_s"], "s")
