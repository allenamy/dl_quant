#!/usr/bin/env python3
"""t5c_drive.py — pod2 driver (PREREG_T5c §4, §9 step 3; gates G-UM, G-X). CPU only under nice; 4 device runs x 3 BLAS threads <= 12 cores.
Builds the carry-forward universe mask, the x0910 dev tree (read-only links), generates the T5c device from the T5 device (sha must equal the Mac
copy), runs KA x {42, 2027} and KB x {42, 2027} with exact env dicts, then compares every T1-arm array bitwise with the KA runs on anchors <= 08-30 20Z.
Launch: bash devices/launch_pod2.sh t5c_drive.py
"""
import os, sys, json, time, hashlib, subprocess, shutil
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T1_', 'T5_')
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
assert sorted(k for k in os.environ if k.startswith(BANNED)) == [], "CALIBER FLAG PRESENT"
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5c"; D = R + "/dev"; T1R = "/workspace/uplift_r2_2026-09-13/T1"; T5R = "/workspace/uplift_r2_2026-09-13/T5"; HC = "/workspace/review_scratch/health_check"; R6 = "/workspace/uplift_2026-09-11/r6/out"
PREREG_SHA = "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"; T5DEV_SHA = "4c5b972eebfb48c3423b0f6c1336b13cb588fb8ec8edf9c7948d67c59dc05add"; DER_SHA_MAC = "23604230871b8fc7efd7b3ba31fccaf6850a3d159ce08f872755dd6068a0a8c5"
PY = "/workspace/venv/bin/python"; DER = R + "/devices/w10_sleeve_t5c.py"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md") == PREREG_SHA
assert sha(T5R + "/devices/w10_sleeve_t5.py") == T5DEV_SHA
KERC = json.load(open(R + "/receipts/RECEIPT_T5c_king_extend.json")); KA = R + "/kings/KA_x0910.npy"; assert sha(KA) == KERC["out_sha256"] and KERC["prefix_copy"]["bitwise"]
KB = R6 + "/SLOW_v4_x0910.npy"
EXP = {KB: "8136f922ef9e4fe94b3d3971ce02083b2815771a43ee7173fcece8c36444575e", HC + "/masks/umask_UPIT_CRYPTO.npz": "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5",
       R6 + "/wide_panel_4h_v2ext_x0910.npz": "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549", R6 + "/meta_newprod_v4_x0910.npz": "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245",
       R6 + "/dlw_v4raw_x0910/data/dlw_targets.npz": "5b628413d0c06d2a989c1ab624783238e7871a9f6a84675be372901a5fbb27de",
       HC + "/dev_v4_x0910/f8_2026-08-22/preds/f10_A0_s42.npy": "609b03794b57d142f162d3b7f3374fec8e17d4b747d65c6c17ee641f7188a9f5", HC + "/dev_v4_x0910/f8_2026-08-22/preds/f10_A0_s2027.npy": "2e88ca5e718d1f5d6e18d220859876c395222d67c04615605915b2fdd9da5240",
       "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json": "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53",
       T1R + "/arms/C0_s42.npz": "93484e8186cabc7ab4d739b283665453542b4ea32eb00e9334be5c7879d0dd09", T1R + "/arms/C0_s2027.npz": "d23e4503dfcb44cccf4d9d0ae4ffa0fd1735fba5516d425b8d1b733f7901623c"}
for p, h in EXP.items(): assert sha(p) == h, ("INPUT SHA", p)
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE", GPU0)
t0 = time.time()
subprocess.check_call([PY, R + "/devices/mk_t5c_device.py", T5R + "/devices/w10_sleeve_t5.py", DER, R + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md"])
DER_SHA = sha(DER); assert DER_SHA == DER_SHA_MAC, ("derived device sha differs from Mac", DER_SHA)
# ---- G-UM: carry-forward universe mask on the x0910 panel axis
UM = np.load(HC + "/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True); PX = np.load(R6 + "/wide_panel_4h_v2ext_x0910.npz", allow_pickle=True)
uts = UM["ts"].astype(np.int64); pts = PX["ts"].astype(np.int64); assert [str(s) for s in UM["symbols"]] == [str(s) for s in PX["symbols"]]
assert np.array_equal(pts[:len(uts)], uts), "umask ts is not a prefix of the x0910 panel ts"
M2 = np.concatenate([UM["mask"], np.repeat(UM["mask"][-1:], len(pts) - len(uts), axis=0)], axis=0)
os.makedirs(R + "/masks", exist_ok=True); UMF = R + "/masks/umask_UPIT_CRYPTO_cf_x0910.npz"
np.savez_compressed(UMF, ts=pts, symbols=UM["symbols"], mask=M2)
chk = np.load(UMF, allow_pickle=True)
G_UM = dict(prefix_rows=int(len(uts)), added_rows=int(len(pts) - len(uts)), prefix_bitwise=bool(np.array_equal(chk["mask"][:len(uts)], UM["mask"]) and np.array_equal(chk["ts"][:len(uts)], uts)),
            added_equal_last_row=bool((chk["mask"][len(uts):] == UM["mask"][-1]).all()), dtype=str(chk["mask"].dtype), last_original_ts=int(uts[-1]), out=UMF, out_sha256=sha(UMF))
G_UM["PASS"] = bool(G_UM["prefix_bitwise"] and G_UM["added_equal_last_row"] and chk["mask"].dtype == UM["mask"].dtype)
print("G-UM", json.dumps(G_UM), flush=True); assert G_UM["PASS"]
# ---- dev tree (read-only links)
for p in (D + "/logs", D + "/probe_artifacts", R + "/arms"): os.makedirs(p, exist_ok=True)
BK = D + "/pod_backup_2026-08-21"; os.makedirs(BK, exist_ok=True)
LINKS = {BK + "/nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy", BK + "/nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         BK + "/slow_pred_hist_oos.npy": KA, BK + "/wide_fea_hist_meta.npz": R6 + "/meta_newprod_v4_x0910.npz", BK + "/wide_panel_4h_hist_v2.npz": R6 + "/wide_panel_4h_v2ext_x0910.npz",
         D + "/dlw_2026-08-22": R6 + "/dlw_v4raw_x0910", D + "/f8_2026-08-22": HC + "/dev_v4_x0910/f8_2026-08-22"}
for t, v in LINKS.items():
    assert os.path.exists(v), v
    if not os.path.islink(t): os.symlink(v, t)
    assert os.path.realpath(t) == os.path.realpath(v), (t, os.path.realpath(t))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed, slow): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010", "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0",
                            "UMASK_NPZ": UMF, "SLOW_NPY": slow, "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"}
EXTRA = {"R18_INSTR": "1", "T1_INSTR": "1", "T5_DUMP": "1"}
JOBS = [("KA_s42", "42", KA), ("KA_s2027", "2027", KA), ("KB_s42", "42", KB), ("KB_s2027", "2027", KB)]
RUNS = {}
def run(job):
    tag, seed, slow = job; dst = R + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed, slow)); env.update(EXTRA); env["OUT_TAG"] = tag; t1 = time.time()
    if not os.path.exists(dst):
        with open(D + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call(["nice", "-n", "10", PY, DER], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=env)
        shutil.move(src, dst)
        try: os.remove(D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t1, 1), self_sha256_reported=cfg["UPLIFT"]["self_sha256"], cfg_T5=cfg.get("T5"), env=env, out=dst, out_sha256=sha(dst))
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as ex:
    for tag, r in ex.map(run, JOBS):
        RUNS[tag] = r; print("RUN", tag, r.get("rc"), r.get("secs"), flush=True)
assert not any(r.get("FAIL") for r in RUNS.values()), RUNS
for tag, r in RUNS.items(): assert r["self_sha256_reported"] == DER_SHA and r["cfg_T5"]["t5c_prereg_sha256"] == PREREG_SHA, tag
# ---- G-X: KA runs vs T1 arms on anchors <= 2026-08-30 20Z
T_LAST = 1788120000
def eqbits(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype: return False
    if a.dtype.kind in "fc":
        na, nb = np.isnan(a), np.isnan(b); return bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return bool(np.array_equal(a, b))
GX = {}
for seed in ("42", "2027"):
    A = np.load(R + "/arms/KA_s%s.npz" % seed, allow_pickle=True); Bt = np.load(T1R + "/arms/C0_s%s.npz" % seed, allow_pickle=True)
    res = {}
    for pre in ("d30_n2_c42", "S0"):
        ra = A[pre + "_rec"][:, 0].astype(np.int64); rb = Bt[pre + "_rec"][:, 0].astype(np.int64)
        ia = np.nonzero(ra <= T_LAST)[0]; ib = np.nonzero(rb <= T_LAST)[0]
        res[pre + "_rows"] = dict(n_a=int(len(ia)), n_b=int(len(ib)), ts_equal=bool(np.array_equal(ra[ia], rb[ib])))
        for k in Bt.files:
            if not k.startswith(pre + "_") or k.endswith("_axes") or k.endswith("_cols"): continue
            x, y = A[k], Bt[k]
            if k.endswith("R18A"):
                xa = x[x[:, 0] <= T_LAST]; yb = y[y[:, 0] <= T_LAST]; res[k] = eqbits(xa, yb)
            elif x.ndim >= 1 and x.shape[0] == len(ra) and y.shape[0] == len(rb):
                res[k] = eqbits(x[ia], y[ib])
    la = A["legs_ts"].astype(np.int64); lb = Bt["legs_ts"].astype(np.int64); ja = np.nonzero(la <= T_LAST)[0]; jb = np.nonzero(lb <= T_LAST)[0]
    res["legs_ts"] = bool(np.array_equal(la[ja], lb[jb]))
    for k in ("legs_king", "legs_fund", "legs_rev24"): res[k] = eqbits(A[k][ja], Bt[k][jb])
    res["cols_symbols"] = bool([str(c) for c in A["cols"]] == [str(c) for c in Bt["cols"]] and [str(c) for c in A["symbols"]] == [str(c) for c in Bt["symbols"]])
    res["n_arrays_compared"] = sum(1 for v in res.values() if isinstance(v, bool))
    res["all_equal"] = all(v for v in res.values() if isinstance(v, bool)) and all(v["ts_equal"] for kk, v in res.items() if kk.endswith("_rows"))
    GX["C0_s" + seed] = res
G_X = dict(per_seed=GX, PASS=all(v["all_equal"] for v in GX.values()))
print("G-X", json.dumps(G_X), flush=True)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, t5_device_sha256=T5DEV_SHA, derived_device_sha256=DER_SHA, inputs={p: h for p, h in EXP.items()}, KA=dict(path=KA, sha256=sha(KA)),
          gate_G_UM=G_UM, gate_G_X=G_X, runs=RUNS, links={t: os.path.realpath(t) for t in LINKS}, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, load_before=LOAD0, load_after=LOAD1, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5c_drive.json", "w"), indent=1, default=str)
print("DONE_t5c_drive", RC["wall_s"])
