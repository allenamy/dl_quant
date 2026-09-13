#!/usr/bin/env python3
"""t4_book_drive.py — pod2 driver (PREREG_T4 §4). Runs the UNCHANGED r18 derived device w10_sleeve_r18.py with the r18 A0 env,
the r18 base knobs (C0 / NW) and SLOW_NPY pointing at a T4 king file. CPU only; writes only under T4/.
Runs: GATE PB = C0_s42 with K0_v4axis (bitwise vs archived r18 arms/C0_s42.npz); K1 x {C0, NW} x {42, 2027}; K0f x {C0} x {42, 2027}.
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t4_book_drive.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
T4 = "/workspace/uplift_r2_2026-09-13/T4"; D = T4 + "/dev"; R18 = "/workspace/uplift_2026-09-11/r18_foundation"; HC = "/workspace/review_scratch/health_check"
DER = R18 + "/devices/w10_sleeve_r18.py"; DER_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"; PY = "/workspace/venv/bin/python"
PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md") == PREREG_SHA
assert sha(DER) == DER_SHA, ("R18 DEVICE SHA", sha(DER))
KR = json.load(open(T4 + "/receipts/RECEIPT_T4_kings.json"))
assert KR["gates"]["K26"]["PASS"] and KR["gates"]["S0_PASS"] and KR["gates"]["AL"]["PASS"] and KR["gates"]["KF_PASS_bitwise"], KR["gates"]
KING = {k: KR["outputs"][k]["v4axis"] for k in ("K0", "K1", "K0f")}
for k, p in KING.items(): assert sha(p) == KR["outputs"][k]["v4axis_sha256"], (k, "king file changed since t4_kings")
ARCH = {"C0_s42": (R18 + "/arms/C0_s42.npz", "d6298deb8d89df54"), "C0_s2027": (R18 + "/arms/C0_s2027.npz", "fa5ed19a546c4230"),
        "NW_s42": (R18 + "/arms/NW_s42.npz", "afbcd92ea41d7e4c"), "NW_s2027": (R18 + "/arms/NW_s2027.npz", "89d28a319f2bd61f")}
for k, (p, h) in ARCH.items(): assert sha(p).startswith(h), ("ARCHIVED r18 ARM SHA", k, sha(p))
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"; COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"; assert sha(COSTB) == COSTB_SHA
UM = HC + "/masks/umask_UPIT_CRYPTO.npz"
SELF_SHA = sha(os.path.abspath(__file__))
for p in (D + "/logs", D + "/probe_artifacts", T4 + "/arms", T4 + "/receipts"): os.makedirs(p, exist_ok=True)
BK = D + "/pod_backup_2026-08-21"; os.makedirs(BK, exist_ok=True)
LINKS = {BK + "/nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",      # = r18_drive.py L39-47 targets
         BK + "/nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         BK + "/slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy",
         BK + "/wide_fea_hist_meta.npz": "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
         BK + "/wide_panel_4h_hist_v2.npz": "/workspace/data/wide_panel_4h_v2ext.npz",
         D + "/dlw_2026-08-22": "/workspace/dlw_v4raw", D + "/f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}
for t, v in LINKS.items():
    assert os.path.exists(v), v
    if not os.path.islink(t): os.symlink(v, t)
    r18t = t.replace(D, R18 + "/dev"); assert os.path.realpath(t) == os.path.realpath(r18t), ("LINK TARGET != r18", t, os.path.realpath(t), os.path.realpath(r18t))
INPUTS = {k: dict(realpath=os.path.realpath(v), sha256=sha(v)) for k, v in LINKS.items() if os.path.isfile(v)}
for k in (UM, COSTB, "/workspace/dlw_v4raw/data/dlw_targets.npz", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy", *KING.values()):
    INPUTS[k] = dict(realpath=os.path.realpath(k), sha256=sha(k))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed, slow): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                            "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": UM, "SLOW_NPY": slow,
                            "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}     # = r18_drive.py L53-55 with SLOW_NPY as the only substitution
BASEKNOBS = {"C0": {"R18_INSTR": "1"}, "NW": {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1"}}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert float(LOAD0[0]) <= 8.0, ("LOAD TOO HIGH, WAIT", LOAD0)
JOBS = [("PB_K0_C0_s42", "42", "C0", "K0")] + [(f"K1_{b}_s{s}", s, b, "K1") for b in ("C0", "NW") for s in ("42", "2027")] + [(f"K0f_C0_s{s}", s, "C0", "K0f") for s in ("42", "2027")]
RUNS = {}
def run(job):
    tag, seed, base, king = job
    dst = T4 + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed, KING[king])); env.update(BASEKNOBS[base]); env["OUT_TAG"] = tag
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
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), device=DER, device_sha256=DER_SHA, self_sha256_reported=cfg["UPLIFT"]["self_sha256"], env=env, out=dst, out_sha256=sha(dst),
                     base=base, seed=seed, king=king, cfg_SLOW_NPY=cfg.get("SLOW_NPY"), cfg_R18=cfg.get("R18"),
                     cfg_knobs={k: cfg.get(k) for k in ("FTPOS", "SEATNET", "FTRIM", "FTRIM_TH", "PHI", "LEGS", "CAL", "UMASK_SCOPE", "FSEED", "FPRED", "COSTB_JSON", "LOOK", "WRULE", "MEMBERS_TOPN")})
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), [t for t, r in RUNS.items() if r.get("FAIL")]
for tag, r in RUNS.items():
    assert r["self_sha256_reported"] == DER_SHA, (tag, r["self_sha256_reported"])
    assert r["cfg_SLOW_NPY"] == KING[r["king"]], (tag, r["cfg_SLOW_NPY"])
def bitwise(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    na, nb = np.isnan(a), np.isnan(b)
    ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a - b))))
Z = np.load(T4 + "/arms/PB_K0_C0_s42.npz", allow_pickle=True); B = np.load(ARCH["C0_s42"][0], allow_pickle=True)
GATE = {"PB": {k: bitwise(Z["d30_n2_c42_" + k], B["d30_n2_c42_" + k]) for k in ("rec", "W")}}
GATE["PB"]["cols_equal"] = bool([str(c) for c in Z["cols"]] == [str(c) for c in B["cols"]])
GATE["PB"]["PASS"] = bool(GATE["PB"]["rec"]["bitwise"] and GATE["PB"]["W"]["bitwise"] and GATE["PB"]["cols_equal"])
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, device=DER, device_sha256=DER_SHA, env=ENV, inputs=INPUTS, base_env=BASE, base_knobs=BASEKNOBS, archived_r18_arms={k: v[0] for k, v in ARCH.items()},
          gate=GATE, runs=RUNS, gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, loadavg_after=LOAD1,
          wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_book_drive.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
assert GATE["PB"]["PASS"], "GATE PB FAIL"
print("DONE_t4_book_drive", RC["wall_s"], "s")
