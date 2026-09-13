#!/usr/bin/env python3
"""t1_drive.py — pod2 driver (PREREG_T1 §8 GATE P / GATE I / GATE E; AMENDMENT 1).
Runs the T1 derived device (T1_INSTR=1) for C0 and NW x seeds {42, 2027} with EXACT env dicts, then:
  GATE P: d30_n2_c42_{rec,W} and S0_{rec,W} bitwise equal to the r18 arms (same knobs, device + dead T1 branches);
  GATE I: per-name sum_l smr_l == smr, per-anchor pnl/carry/cost identities, rev24 == 0 on NW (W_ALPHA), C0 rev24 remnant reported.
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t1_drive.py PATH,HOME,LC_CTYPE
CPU only; writes only under /workspace/uplift_r2_2026-09-13/T1/.
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T1_')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T1"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"
R18 = "/workspace/uplift_2026-09-11/r18_foundation"
R18DEV = R18 + "/devices/w10_sleeve_r18.py"; R18_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
DER = R + "/devices/w10_sleeve_t1.py"; PY = "/workspace/venv/bin/python"
PREREG = R + "/PREREG_T1_edge_diagnosis_2026-09-13.md"; PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"
AMEND = R + "/PREREG_AMENDMENT_1_T1_2026-09-13.md"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"
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
assert sha(AMEND) == AMEND_SHA, ("AMENDMENT SHA", sha(AMEND))
assert sha(R18DEV) == R18_SHA, ("R18 DEVICE SHA", sha(R18DEV))
assert sha(COSTB) == COSTB_SHA, ("COSTB SHA", sha(COSTB))
DER_SHA = sha(DER); SELF_SHA = sha(os.path.abspath(__file__))
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
ARMS = {"C0": {"R18_INSTR": "1", "T1_INSTR": "1"}, "NW": {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1", "T1_INSTR": "1"}}
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE, QUEUE", GPU0)
assert float(LOAD0[0]) <= 16.0, ("LOAD TOO HIGH, WAIT", LOAD0)
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
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), device=DER, device_sha256=DER_SHA, self_sha256_reported=cfg["UPLIFT"]["self_sha256"], cfg_T1=cfg.get("T1"), cfg_R18=cfg.get("R18"),
                     env=env, out=dst, out_sha256=sha(dst))
JOBS = [(a + "_s" + s, s, ARMS[a]) for a in ("C0", "NW") for s in ("42", "2027")]
from concurrent.futures import ThreadPoolExecutor
t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), "s", flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), [t for t, r in RUNS.items() if r.get("FAIL")]
for tag, r in RUNS.items():
    assert r["self_sha256_reported"] == DER_SHA, (tag, r["self_sha256_reported"], DER_SHA)
    assert r["cfg_T1"] and r["cfg_T1"]["T1_INSTR"] == 1 and r["cfg_T1"]["prereg_sha256"] == PREREG_SHA, (tag, r["cfg_T1"])
def bitwise(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    af = a.astype(float); bf = b.astype(float); na, nb = np.isnan(af), np.isnan(bf)
    ok = bool(np.array_equal(na, nb) and np.array_equal(af[~na], bf[~nb]) and a.dtype == b.dtype)
    return dict(bitwise=ok, shape=list(a.shape), dtype_a=str(a.dtype), dtype_b=str(b.dtype), maxabs=0.0 if ok else float(np.nanmax(np.abs(af - bf))))
TS_WA0 = 1656547200; TS_WA1 = 1788120000   # 2022-06-30 00Z .. 2026-08-30 20Z
GATE = {"P": {}, "I": {}}
for tag in RUNS:
    A = np.load(R + "/arms/%s.npz" % tag, allow_pickle=True); B = np.load(R18 + "/arms/%s.npz" % tag, allow_pickle=True)
    g = {k: bitwise(A[k], B[k]) for k in ("d30_n2_c42_rec", "d30_n2_c42_W", "S0_rec", "S0_W", "d30_n2_c42_R18A", "legs_king", "legs_fund", "legs_rev24")}
    g["cols_equal"] = bool([str(c) for c in A["cols"]] == [str(c) for c in B["cols"]])
    GATE["P"][tag] = g
    rec = A["d30_n2_c42_rec"]; ts = rec[:, 0].astype(np.int64)
    wa = np.where((ts >= TS_WA0) & (ts <= TS_WA1))[0]
    ID = A["d30_n2_c42_T1ID"]; AGG = A["d30_n2_c42_T1AGG"]
    assert ID.shape[0] == rec.shape[0] and AGG.shape == (rec.shape[0], 6, 4), (ID.shape, AGG.shape, rec.shape)
    pnl_sum = AGG[:, 0:2, :].sum((1, 2)); car_sum = AGG[:, 2:4, :].sum((1, 2)); cost_sum = AGG[:, 4:6, :].sum((1, 2))
    gi = dict(n_rows=int(rec.shape[0]), wa_first=int(ts[wa[0]]), wa_last=int(ts[wa[-1]]), wa_n=int(len(wa)), wa_first_row=int(wa[0]), wa_last_row=int(wa[-1]),
              max_name_identity=float(np.abs(ID[:, 0]).max()), max_pnl_identity=float(np.abs(ID[:, 1]).max()), max_carry_identity=float(np.abs(ID[:, 2]).max()), max_cost_identity=float(np.abs(ID[:, 3]).max()),
              max_kinghalf_identity=float(np.abs(ID[:, 5]).max()),
              agg_vs_rec_pnl=float(np.abs(pnl_sum - rec[:, 19]).max()), agg_vs_rec_carry=float(np.abs(car_sum - rec[:, 20]).max()), agg_vs_rec_cost=float(np.abs(cost_sum - rec[:, 21]).max()),
              rev24_max_abs_smr_comp_WALPHA=float(np.abs(ID[wa, 4]).max()),
              rev24_sum_abs_contrib_WALPHA_bps=float(np.abs(AGG[wa][:, :, 1]).sum()), all_sum_abs_g_WALPHA_bps=float(np.abs(rec[wa, 18]).sum()))
    gi["PASS_identities"] = bool(gi["max_name_identity"] <= 1e-12 and gi["max_pnl_identity"] <= 1e-7 and gi["max_carry_identity"] <= 1e-7 and gi["max_cost_identity"] <= 1e-7 and gi["max_kinghalf_identity"] <= 1e-12
                                 and gi["agg_vs_rec_pnl"] <= 1e-7 and gi["agg_vs_rec_carry"] <= 1e-7 and gi["agg_vs_rec_cost"] <= 1e-7)
    gi["rev24_rule"] = ("NW: must be <= 1e-12" if tag.startswith("NW") else "C0: reported only (AMENDMENT 1)")
    gi["PASS_rev24"] = bool(gi["rev24_max_abs_smr_comp_WALPHA"] <= 1e-12) if tag.startswith("NW") else None
    GATE["I"][tag] = gi
GATE["P"]["PASS"] = all(all(v[k]["bitwise"] for k in ("d30_n2_c42_rec", "d30_n2_c42_W", "S0_rec", "S0_W", "d30_n2_c42_R18A", "legs_king", "legs_fund", "legs_rev24")) and v["cols_equal"] for k2, v in GATE["P"].items() if k2 != "PASS")
GATE["I"]["PASS"] = all(v["PASS_identities"] and (v["PASS_rev24"] in (True, None)) and v["wa_n"] == 9138 and v["wa_first"] == TS_WA0 and v["wa_last"] == TS_WA1 for k2, v in GATE["I"].items() if k2 != "PASS")
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, r18_device_sha256=R18_SHA, derived_device_sha256=DER_SHA, derived_device=DER,
          env=dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv), python=sys.version.split()[0], numpy=np.__version__),
          inputs=INPUTS, base_env=BASE, arms=ARMS, runs=RUNS, gate=GATE, gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1,
          loadavg_before=LOAD0, loadavg_after=LOAD1, wall_s=round(time.time() - t0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_drive_gates.json", "w"), indent=1, default=str)
print(json.dumps(GATE, indent=1)); print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1)
print("DONE_t1_drive", RC["wall_s"], "s")
