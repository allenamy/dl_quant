#!/usr/bin/env python3
"""r18_drive.py — pod2 driver (PREREG_r18 §2/§3): 12 device runs with EXACT env dicts (no inheritance), GATE P
(C0 knobs-off vs archived A0 bitwise on rec and W, both seeds). CPU only; live tree never touched.
Launched `env -i PATH=... HOME=... /workspace/venv/bin/python r18_drive.py PATH,HOME`.
Writes only under /workspace/uplift_2026-09-11/r18_foundation/.
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
R = "/workspace/uplift_2026-09-11/r18_foundation"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"
PIN = "/workspace/uplift_2026-09-11/w10_sleeve.py"; DER = R + "/devices/w10_sleeve_r18.py"; PY = "/workspace/venv/bin/python"
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG = R + "/PREREG_r18_foundation_2026-09-12.md"; PREREG_SHA = "51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c"
ARCH = {"42": ("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz", "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339"),
        "2027": ("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz", "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b")}
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
assert sha(PIN) == PIN_SHA, ("PINNED DEVICE SHA", sha(PIN))
DER_SHA = sha(DER)
assert sha(COSTB) == COSTB_SHA, ("COSTB SHA", sha(COSTB))
for s_, (p_, h_) in ARCH.items(): assert sha(p_) == h_, ("ARCHIVED A0 SHA", s_, sha(p_))
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
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; UM = HC + "/masks/umask_UPIT_CRYPTO.npz"
INPUTS = {k: dict(realpath=os.path.realpath(v), sha256=sha(v)) for k, v in LINKS.items() if os.path.isfile(v)}
for k in (K3, UM, COSTB, "/workspace/dlw_v4raw/data/dlw_targets.npz", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"):
    INPUTS[k] = dict(realpath=os.path.realpath(k), sha256=sha(k))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                      "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": UM, "SLOW_NPY": K3,
                      "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert float(LOAD0[0]) <= 6.0, ("LOAD TOO HIGH, WAIT", LOAD0)
ARMS = {"C0": {"R18_INSTR": "1"}, "N2": {"R18_ELIG": "1", "R18_INSTR": "1"}, "WU": {"R18_WARM": "1", "R18_INSTR": "1"},
        "NW": {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1"},
        "NW_S05": {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1", "SMA": "0.05", "SBAND": "2.5e-4"},
        "NW_B50": {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1", "SMA": "0.10", "SBAND": "5.0e-4"}}
RUNS = {}
def run(job):
    tag, seed, extra = job
    dst = R + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed)); env.update(extra); env["OUT_TAG"] = tag
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
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), device=DER, device_sha256=DER_SHA, self_sha256_reported=cfg["UPLIFT"]["self_sha256"], env=env, env_whitelist=sorted(env), out=dst, out_sha256=sha(dst),
                     n_rec=int(Z["d30_n2_c42_rec"].shape[0]), cfg_knobs={k: cfg.get(k) for k in ("FTPOS", "SEATNET", "FTRIM", "FTRIM_TH", "PHI", "LEGS", "CAL", "UMASK_SCOPE", "FSEED", "FPRED", "COSTB_JSON", "LOOK", "WRULE", "MEMBERS_TOPN")}, cfg_R18=cfg.get("R18"))
JOBS = [(a + "_s" + s, s, ARMS[a]) for a in ("C0", "N2", "WU", "NW", "NW_S05", "NW_B50") for s in ("42", "2027")]
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), [t for t, r in RUNS.items() if r.get("FAIL")]
for tag, r in RUNS.items():   # self-report must equal the derived device sha (E-0826-C)
    assert r["self_sha256_reported"] == DER_SHA, (tag, r["self_sha256_reported"], DER_SHA)
def bitwise(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    na, nb = np.isnan(a), np.isnan(b)
    ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a - b))))
GATE = {"P": {}}
for s in ("42", "2027"):
    A = np.load(R + "/arms/C0_s%s.npz" % s, allow_pickle=True); B = np.load(ARCH[s][0], allow_pickle=True)
    GATE["P"]["C0_s" + s + "_vs_archived"] = {k: bitwise(A["d30_n2_c42_" + k], B[k]) for k in ("rec", "W")}
    GATE["P"]["C0_s" + s + "_vs_archived"]["cols_equal"] = bool([str(c) for c in A["cols"]] == [str(c) for c in B["cols"]])
GATE["P"]["PASS"] = all(v["rec"]["bitwise"] and v["W"]["bitwise"] and v["cols_equal"] for k, v in GATE["P"].items() if k != "PASS")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, pinned_device_sha256=PIN_SHA, derived_device_sha256=DER_SHA, derived_device=DER, env=ENV, inputs=INPUTS, base_env=BASE, a0_knobs_s42=A0("42"), arms=ARMS, gate=GATE, runs=RUNS,
          gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, loadavg_after=LOAD1, wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_r18_drive_gateP.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
print("DONE_r18_drive", RC["wall_s"], "s")
