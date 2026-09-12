#!/usr/bin/env python3
"""r17_drive.py — pod2 driver: GATE P chain (P1-P4) + all declared arms (PREREG_r17 §4/§5). CPU only. Live tree never touched.

Every device run is launched with an EXACT env dict (no inheritance) = BASE ∪ A0 knobs ∪ arm knobs ∪ OUT_TAG,
recorded verbatim in the receipt (E-0826-D). The driver itself is launched `env -i ... python r17_drive.py <whitelist>`.
Writes only under /workspace/uplift_2026-09-11/r17_fill_pricing/.
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','R16','R17','XMODE','XNULL','AUX16','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)

U = "/workspace/uplift_2026-09-11"; R = U + "/r17_fill_pricing"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"
PIN = U + "/w10_sleeve.py"; DER = R + "/devices/w10_sleeve_r17.py"; PY = "/workspace/venv/bin/python"
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG = R + "/PREREG_r17_fill_pricing_2026-09-12.md"; PREREG_SHA = "a7533b922c68e6dc575b1eadd3d19f62d4d271393ec5d58621c31aa65f5ae272"
AMEND1 = R + "/PREREG_AMENDMENT_1_r17_2026-09-12.md"; AMEND1_SHA = "70c8142ac4595fb4e83659daaa83cd3a68ba1284f103fd77ba3a14ba3f3269bd"
TABLE = R + "/receipts/r17_fill_table.json"; TABLE_SHA = sys.argv[2] if len(sys.argv) > 2 else None
ARCH = {"42": (U + "/r3k/arms/A0_PWR230k_s42.npz", "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339"),
        "2027": (U + "/r3k/arms/A0_PWR230k_s2027.npz", "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b")}
X1REF = {"42": (U + "/r16_asym_band/arms/A_X1_s42.npz", "cdec63ed669265ad8255c02af09a583947a6c271ddf8ebf1eb439a67476fbafa"),
         "2027": (U + "/r16_asym_band/arms/A_X1_s2027.npz", "baecf30e384ffcdc875319a086ab39277663ee0f23abd8d54cb01dd35a0c0ff9")}
R15REF = {("F", s): U + "/r15_structural/arms/F_s%s.npz" % s for s in ("42", "2027")}; R15REF.update({("S", s): U + "/r15_structural/arms/S_s%s.npz" % s for s in ("42", "2027")})
COSTB = U + "/r3k/costb_PWR_G230k.json"; COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG)); assert sha(AMEND1) == AMEND1_SHA, ("AMEND1 SHA", sha(AMEND1))
assert sha(PIN) == PIN_SHA, ("PINNED DEVICE SHA", sha(PIN)); assert sha(COSTB) == COSTB_SHA, ("COSTB SHA", sha(COSTB))
if TABLE_SHA: assert sha(TABLE) == TABLE_SHA, ("FILL TABLE SHA", sha(TABLE))
TABLE_SHA = sha(TABLE); DER_SHA = sha(DER)
for s_, (p_, h_) in ARCH.items(): assert sha(p_) == h_, ("ARCHIVED A0 SHA", s_, sha(p_))
for s_, (p_, h_) in X1REF.items(): assert sha(p_) == h_, ("ARCHIVED r16 X1 SHA", s_, sha(p_))
R15G = json.load(open(U + "/r15_structural/receipts/RECEIPT_r15_drive_gateP.json"))
for (a_, s_), p_ in R15REF.items(): assert sha(p_) == R15G["runs"]["%s_s%s" % (a_, s_)]["out_sha256"], ("ARCHIVED r15 arm SHA", a_, s_)
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
for k in (K3, UM, COSTB, TABLE, "/workspace/dlw_v4raw/data/dlw_targets.npz", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"):
    INPUTS[k] = dict(realpath=os.path.realpath(k), sha256=sha(k))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                      "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": UM, "SLOW_NPY": K3,
                      "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB, "R17_PREREG_PATH": PREREG, "R17_AMEND1_PATH": AMEND1}
FILL = {"R17_FILL": "1", "R17_TABLE": TABLE, "R17_INSTR": "1", "R17_GROSS_USDT": "232000"}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert float(LOAD0[0]) <= 6.0, ("LOAD TOO HIGH, WAIT", LOAD0)
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
                     n_rec=int(Z["d30_n2_c42_rec"].shape[0]), has_R17=bool("d30_n2_c42_R17" in Z), cfg_knobs={k: cfg.get(k) for k in ("FTPOS", "SEATNET", "FTRIM", "FTRIM_TH", "PHI", "LEGS", "CAL", "UMASK_SCOPE", "FSEED", "FPRED", "COSTB_JSON")}, cfg_R17=cfg.get("R17"))
JOBS = []
for s in ("42", "2027"):
    JOBS += [("GP_FILL0_s" + s, s, {}), ("GP_X1_s" + s, s, {"R17_X1": "1"}), ("GP_F_s" + s, s, {"FTPOS": "1"}), ("GP_S_s" + s, s, {"SEATNET": "1"}), ("GP_INSTR_s" + s, s, {"R17_INSTR": "1"}),
             ("A0DET_s" + s, s, dict(FILL, R17_MODE="det")), ("X1DET_s" + s, s, dict(FILL, R17_MODE="det", R17_X1="1")), ("FDET_s" + s, s, dict(FILL, R17_MODE="det", FTPOS="1")), ("SDET_s" + s, s, dict(FILL, R17_MODE="det", SEATNET="1"))]
    JOBS += [("A0STO%d_s%s" % (k, s), s, dict(FILL, R17_MODE="stoch", R17_SEED=str(k))) for k in range(1, 6)]
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
FAILS = [t for t, r in RUNS.items() if r.get("FAIL")]
def bitwise(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    na, nb = np.isnan(a), np.isnan(b); ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a - b))))
def cmp(tagA, refpath, kb):
    A = np.load(R + "/arms/%s.npz" % tagA, allow_pickle=True); B = np.load(refpath, allow_pickle=True)
    return {k: bitwise(A["d30_n2_c42_" + k], B[kb[k]]) for k in ("rec", "W")}
GATE = {"P1": {}, "P2": {}, "P3": {}, "P4": {}}
for s in ("42", "2027"):
    if "GP_FILL0_s" + s in RUNS and not RUNS["GP_FILL0_s" + s].get("FAIL"):
        GATE["P1"]["FILL0_s%s_vs_archived_A0" % s] = cmp("GP_FILL0_s" + s, ARCH[s][0], {"rec": "rec", "W": "W"})
        if not RUNS["GP_INSTR_s" + s].get("FAIL"): GATE["P4"]["INSTR_vs_FILL0_s" + s] = cmp("GP_INSTR_s" + s, R + "/arms/GP_FILL0_s%s.npz" % s, {"rec": "d30_n2_c42_rec", "W": "d30_n2_c42_W"})
    if not RUNS["GP_X1_s" + s].get("FAIL"): GATE["P2"]["X1_s%s_vs_r16_A_X1" % s] = cmp("GP_X1_s" + s, X1REF[s][0], {"rec": "rec", "W": "W"})
    if not RUNS["GP_F_s" + s].get("FAIL"): GATE["P3"]["F_s%s_vs_r15_F" % s] = cmp("GP_F_s" + s, R15REF[("F", s)], {"rec": "d30_n2_c42_rec", "W": "d30_n2_c42_W"})
    if not RUNS["GP_S_s" + s].get("FAIL"): GATE["P3"]["S_s%s_vs_r15_S" % s] = cmp("GP_S_s" + s, R15REF[("S", s)], {"rec": "d30_n2_c42_rec", "W": "d30_n2_c42_W"})
for g in GATE: GATE[g]["PASS"] = bool(GATE[g]) and all(v["rec"]["bitwise"] and v["W"]["bitwise"] for k, v in GATE[g].items() if k != "PASS")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND1_SHA, pinned_device_sha256=PIN_SHA, derived_device_sha256=DER_SHA, derived_device=DER, fill_table_sha256=TABLE_SHA,
          env=ENV, inputs=INPUTS, base_env=BASE, a0_knobs_s42=A0("42"), fill_knobs=FILL, gate=GATE, runs=RUNS, fails=FAILS,
          gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, loadavg_after=LOAD1,
          wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_r17_drive_gateP.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("FAILS", FAILS)
print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
print("DONE_r17_drive", RC["wall_s"], "s")
