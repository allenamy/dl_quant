#!/usr/bin/env python3
"""r15_drive.py — pod2 driver: main arms + GATE P chain (PREREG_r15 §2/§3). CPU only. Live tree never touched.

Every device run is launched with an EXACT env dict (no inheritance) = BASE ∪ A0 knobs ∪ arm knobs ∪ OUT_TAG,
recorded verbatim in the receipt (E-0826-D). The driver itself is launched `env -i ... python r15_drive.py <whitelist>`.
Writes only under /workspace/uplift_2026-09-11/r15_structural/.
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED',
          'MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)

R = "/workspace/uplift_2026-09-11/r15_structural"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"
PIN = "/workspace/uplift_2026-09-11/w10_sleeve.py"; DER = R + "/devices/w10_sleeve_r15.py"; PY = "/workspace/venv/bin/python"
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG = R + "/PREREG_r15_structural_2026-09-12.md"
PREREG_SHA = "097769b087fa0834fb780062bf710134d7e3a67555174de5c26c1668c455f6fc"
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
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root",
        "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                      "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": UM, "SLOW_NPY": K3,
                      "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert float(LOAD0[0]) <= 6.0, ("LOAD TOO HIGH, WAIT", LOAD0)
RUNS = {}
def run(job):
    tag, dev, seed, extra = job
    dst = R + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed)); env.update(extra); env["OUT_TAG"] = tag
    t0 = time.time()
    if not os.path.exists(dst):
        with open(D + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call([PY, dev], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=env)
        shutil.move(src, dst)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), device=dev, device_sha256=(PIN_SHA if dev == PIN else DER_SHA),
                     self_sha256_reported=cfg["UPLIFT"]["self_sha256"], env=env, env_whitelist=sorted(env), out=dst, out_sha256=sha(dst),
                     n_rec=int(Z["d30_n2_c42_rec"].shape[0]), cfg_knobs={k: cfg.get(k) for k in ("FTPOS", "SEATNET", "FTRIM", "FTRIM_TH", "PHI", "LEGS", "CAL", "UMASK_SCOPE", "FSEED", "FPRED", "COSTB_JSON")}, cfg_R15=cfg.get("R15"))
JOBS = []
for s in ("42", "2027"):
    JOBS += [("GP_A0_s" + s, PIN, s, {}),
             ("F_s" + s, PIN, s, {"FTPOS": "1"}), ("S_s" + s, PIN, s, {"SEATNET": "1"}),
             ("F05_s" + s, PIN, s, {"FTPOS": "1", "FTRIM_TH": "-0.0005"}), ("F20_s" + s, PIN, s, {"FTPOS": "1", "FTRIM_TH": "-0.0020"}),
             ("D_A0I_s" + s, DER, s, {"R15_INSTR": "1"}), ("D_FI_s" + s, DER, s, {"FTPOS": "1", "R15_INSTR": "1"}),
             ("D_SI_s" + s, DER, s, {"SEATNET": "1", "R15_INSTR": "1"}), ("SB_s" + s, DER, s, {"R15_SB": "1", "R15_INSTR": "1"})]
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=9) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), [t for t, r in RUNS.items() if r.get("FAIL")]
def bitwise(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    na, nb = np.isnan(a), np.isnan(b)
    ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a - b))))
def cmp(tagA, tagB, archived=False):
    A = np.load(R + "/arms/%s.npz" % tagA, allow_pickle=True)
    if archived: B = np.load(ARCH[tagB][0], allow_pickle=True); kb = {"rec": "rec", "W": "W"}
    else: B = np.load(R + "/arms/%s.npz" % tagB, allow_pickle=True); kb = {"rec": "d30_n2_c42_rec", "W": "d30_n2_c42_W"}
    return {k: bitwise(A["d30_n2_c42_" + k], B[kb[k]]) for k in ("rec", "W")}
GATE = {"P1": {}, "P2": {}, "P3": {}}
for s in ("42", "2027"):
    GATE["P1"]["A0_s" + s + "_vs_archived"] = cmp("GP_A0_s" + s, s, archived=True)
    GATE["P2"]["D_A0I_vs_GP_A0_s" + s] = cmp("D_A0I_s" + s, "GP_A0_s" + s)
    GATE["P3"]["D_FI_vs_F_s" + s] = cmp("D_FI_s" + s, "F_s" + s)
    GATE["P3"]["D_SI_vs_S_s" + s] = cmp("D_SI_s" + s, "S_s" + s)
for g in GATE: GATE[g]["PASS"] = all(v["rec"]["bitwise"] and v["W"]["bitwise"] for k, v in GATE[g].items() if k != "PASS")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, pinned_device_sha256=PIN_SHA, derived_device_sha256=DER_SHA, derived_device=DER,
          env=ENV, inputs=INPUTS, base_env=BASE, a0_knobs_s42=A0("42"), gate=GATE, runs=RUNS,
          gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, loadavg_after=LOAD1,
          wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_r15_drive_gateP.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
print("DONE_r15_drive", RC["wall_s"], "s")
