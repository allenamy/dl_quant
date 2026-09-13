#!/usr/bin/env python3
"""t5d_drive.py — pod2 driver (PREREG_T5d §3; gates G-UM, G-KA, G-X'). CPU only under nice; 4 device runs x 3 BLAS threads <= 12 cores.
The T5c device (w10_sleeve_t5c.py, sha asserted, read in place) runs KA x {42, 2027} and KB x {42, 2027} with exactly the T5c env dicts; the only
change is the panel link, which points to the corrected panel. Gate G-X': every array of each T5d arm equals the matching T5c arm bitwise on all
rows with anchor <= 2026-08-31 00Z (T5c itself equals the T1 arms on <= 08-30 20Z).
Launch: bash devices/launch_pod2.sh t5d_drive.py
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T1_', 'T5_')
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
assert sorted(k for k in os.environ if k.startswith(BANNED)) == [], "CALIBER FLAG PRESENT"
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5d"; D = R + "/dev"; T5C = "/workspace/uplift_r2_2026-09-13/T5c"; HC = "/workspace/review_scratch/health_check"; R6 = "/workspace/uplift_2026-09-11/r6/out"
PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"; DEV = T5C + "/devices/w10_sleeve_t5c.py"; DEV_SHA = "23604230871b8fc7efd7b3ba31fccaf6850a3d159ce08f872755dd6068a0a8c5"; PY = "/workspace/venv/bin/python"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA; assert sha(DEV) == DEV_SHA
PRC = json.load(open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json")); PANEL = PRC["out"]; assert sha(PANEL) == PRC["out_sha256"] and PRC["gate_G_R6"]["PASS"] and PRC["gate_G_SCOPE"]["PASS"]
T5D = json.load(open(T5C + "/receipts/RECEIPT_T5c_drive.json")); T5K = json.load(open(T5C + "/receipts/RECEIPT_T5c_king_extend.json"))
KA = T5C + "/kings/KA_x0910.npy"; KB = R6 + "/SLOW_v4_x0910.npy"; UMF = T5D["gate_G_UM"]["out"]
G_UMKA = dict(umask=sha(UMF) == T5D["gate_G_UM"]["out_sha256"], KA=sha(KA) == T5K["out_sha256"], KB=sha(KB) == "8136f922ef9e4fe94b3d3971ce02083b2815771a43ee7173fcece8c36444575e")
for tag, r in T5D["runs"].items(): G_UMKA["T5c_arm_" + tag] = sha(r["out"]) == r["out_sha256"]
assert all(G_UMKA.values()), G_UMKA
EXP = {R6 + "/meta_newprod_v4_x0910.npz": "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245", R6 + "/dlw_v4raw_x0910/data/dlw_targets.npz": "5b628413d0c06d2a989c1ab624783238e7871a9f6a84675be372901a5fbb27de",
       HC + "/dev_v4_x0910/f8_2026-08-22/preds/f10_A0_s42.npy": "609b03794b57d142f162d3b7f3374fec8e17d4b747d65c6c17ee641f7188a9f5", HC + "/dev_v4_x0910/f8_2026-08-22/preds/f10_A0_s2027.npy": "2e88ca5e718d1f5d6e18d220859876c395222d67c04615605915b2fdd9da5240",
       "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json": "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"}
for p, h in EXP.items(): assert sha(p) == h, ("INPUT SHA", p)
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE", GPU0)
t0 = time.time()
for p in (D + "/logs", D + "/probe_artifacts", R + "/arms"): os.makedirs(p, exist_ok=True)
BK = D + "/pod_backup_2026-08-21"; os.makedirs(BK, exist_ok=True)
LINKS = {BK + "/nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy", BK + "/nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         BK + "/slow_pred_hist_oos.npy": KA, BK + "/wide_fea_hist_meta.npz": R6 + "/meta_newprod_v4_x0910.npz", BK + "/wide_panel_4h_hist_v2.npz": PANEL,
         D + "/dlw_2026-08-22": R6 + "/dlw_v4raw_x0910", D + "/f8_2026-08-22": HC + "/dev_v4_x0910/f8_2026-08-22"}
for t, v in LINKS.items():
    assert os.path.exists(v), v
    if not os.path.islink(t): os.symlink(v, t)
    assert os.path.realpath(t) == os.path.realpath(v), (t, os.path.realpath(t))
RUNS = {}
def run(tag):
    envT = dict(T5D["runs"][tag]["env"]); assert envT["UMASK_NPZ"] == UMF and envT["SLOW_NPY"] in (KA, KB)
    dst = R + "/arms/%s.npz" % tag; t1 = time.time()
    if not os.path.exists(dst):
        with open(D + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call(["nice", "-n", "10", PY, DEV], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=envT)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=envT)
        shutil.move(src, dst)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t1, 1), self_sha256_reported=cfg["UPLIFT"]["self_sha256"], env=envT, out=dst, out_sha256=sha(dst))
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as ex:
    for tag, r in ex.map(run, ["KA_s42", "KA_s2027", "KB_s42", "KB_s2027"]):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), RUNS
for tag, r in RUNS.items(): assert r["self_sha256_reported"] == DEV_SHA, tag
T_CUT = 1788134400
def eqbits(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype: return False
    if a.dtype.kind in "fc":
        na, nb = np.isnan(a), np.isnan(b); return bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return bool(np.array_equal(a, b))
GX = {}
for tag in RUNS:
    A = np.load(R + "/arms/%s.npz" % tag, allow_pickle=True); Bt = np.load(T5D["runs"][tag]["out"], allow_pickle=True)
    res = {}; later_diff = {}
    for pre in ("d30_n2_c42", "S0"):
        ra = A[pre + "_rec"][:, 0].astype(np.int64); rb = Bt[pre + "_rec"][:, 0].astype(np.int64)
        assert np.array_equal(ra, rb), (tag, pre, "row axis differs")
        ia = ra <= T_CUT
        for k in Bt.files:
            if not k.startswith(pre + "_") or k.endswith("_axes") or k.endswith("_cols") or "_T5_" in k: continue
            x, y = A[k], Bt[k]
            if k.endswith("R18A"): res[k] = eqbits(x[x[:, 0] <= T_CUT], y[y[:, 0] <= T_CUT]); continue
            if x.ndim >= 1 and x.shape[0] == len(ra):
                res[k] = eqbits(x[ia], y[ia]); later_diff[k] = not eqbits(x[~ia], y[~ia])
    ta = A["d30_n2_c42_T5_ts"].astype(np.int64); assert np.array_equal(ta, Bt["d30_n2_c42_T5_ts"].astype(np.int64)); it = ta <= T_CUT
    for k in Bt.files:
        if "_T5_" in k and k != "d30_n2_c42_T5_ts":
            x, y = A[k], Bt[k]
            if x.ndim >= 1 and x.shape[0] == len(ta): res[k] = eqbits(x[it], y[it])
    la = A["legs_ts"].astype(np.int64); ja = la <= T_CUT
    for k in ("legs_king", "legs_fund", "legs_rev24"): res[k] = eqbits(A[k][ja], Bt[k][ja]); later_diff[k] = not eqbits(A[k][~ja], Bt[k][~ja])
    GX[tag] = dict(n_arrays=len(res), all_equal=all(res.values()), failing=[k for k, v in res.items() if not v], arrays_that_change_after_cut=sorted(k for k, v in later_diff.items() if v))
G_X = dict(per_run=GX, PASS=all(v["all_equal"] for v in GX.values()))
print("G-X'", json.dumps(G_X), flush=True)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, device=DEV, device_sha256=DEV_SHA, panel=PANEL, panel_sha256=PRC["out_sha256"], gate_G_UM_KA=G_UMKA, gate_G_Xprime=G_X,
          runs=RUNS, links={t: os.path.realpath(t) for t in LINKS}, inputs=EXP, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, load_before=LOAD0, load_after=LOAD1, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_drive.json", "w"), indent=1, default=str)
assert G_X["PASS"], "G-X' failed: stop"
print("DONE_t5d_drive", RC["wall_s"])
