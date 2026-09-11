"""ROUND 5 / ANGLE 3 runner. Device = /workspace/uplift_2026-09-11/w10_sleeve.py (PINNED sha b88e35a4...), knobs off.
COMMON copied VERBATIM from r3_xib/runner.py (which copied review_scratch/run_v4_arms.sh ARM=A0).
Two cost planes:
  STD  = health_check/calib/costb_fee_steady.json   (what the ORIGINAL 6-seed rule ran at; needed for GATE P bitwise)
  FIT  = r3k/costb_PWR_G230k.json sha 295b4e7b...   (the FITTED model; what this round judges at)
Seeds are HOMOGENEOUS in-service-object draws (V2=1), preds aligned onto the v4 DL axis by build_dev_v4.align().
"""
import numpy as np, os, sys, subprocess, time, json, hashlib
sys.path.insert(0, "/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, blend, save
R = "/workspace/uplift_2026-09-11/r5_seeds"; D = R + "/dev"; OUT = R + "/arms"
HC = "/workspace/review_scratch/health_check"
DEV = "/workspace/uplift_2026-09-11/w10_sleeve.py"
for p in (D + "/logs", D + "/sig", D + "/probe_artifacts", OUT, R + "/receipts"): os.makedirs(p, exist_ok=True)
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
COST = {"STD": HC + "/calib/costb_fee_steady.json",
        "FIT": "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"}
def common(cb):
    return ["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
            "UMASK_SCOPE=m1","UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz",
            "COSTB_JSON=" + COST[cb], "SLOW_NPY=" + K3]
def build_sigs():
    PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
    ts = PW["ts"].astype(np.int64); sym = PW["symbols"]
    FE1 = np.asarray(PW["f_fund_ema_v1"], float); B = np.isfinite(FE1)
    AM = np.asarray(PW["f_amihud_24h"], float)
    ZF = RZ(FE1, B); ZA = RZ(AM, B)
    ZAL = np.full_like(ZA, np.nan); ZAL[1:] = ZA[:-1]; ZAL = np.where(B, ZAL, np.nan)
    M = {"XIBPAR": ZF, "XIBLAG50": blend((0.5, ZF), (0.5, ZAL))}
    return {k: save(D + "/sig/%s.npz" % k, sym, ts, v) for k, v in M.items()}
def run(arm, seat, seed, cb, femat, predroot):
    tag = "R5_%s_%s_%s_s%s" % (cb, arm, seat, seed)
    dst = "%s/w10_ablation_series_%s.npz" % (OUT, tag)
    if os.path.exists(dst): return tag + " skip"
    env = dict(os.environ); env.update(OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3", MKL_NUM_THREADS="3")
    if predroot: env["F10_PRED_DIR"] = predroot
    cmd = ["env"] + common(cb) + ["FSEED=%s" % seed, "FPRED=f10_A0_s%s.npy" % seed] \
        + (["W3FIX=0.21,0,0.79"] if seat == "fix" else []) \
        + (["FEMAT_NPZ=" + femat] if femat else []) \
        + ["OUT_TAG=" + tag, "/workspace/venv/bin/python", DEV]
    t = time.time()
    with open("%s/logs/%s.log" % (D, tag), "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = "%s/probe_artifacts/w10_ablation_series_%s.npz" % (D, tag)
    if rc != 0 or not os.path.exists(src): return "FAIL %s rc=%d" % (tag, rc)
    os.replace(src, dst)
    js = "%s/probe_artifacts/w10_ablation_summary_%s.json" % (D, tag)
    if os.path.exists(js): os.replace(js, "%s/w10_ablation_summary_%s.json" % (OUT, tag))
    return "%-34s ok %5.1fs sha %s" % (tag, time.time() - t, hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16])
if __name__ == "__main__":
    SIG = build_sigs()
    spec = json.loads(sys.argv[1])     # [[arm,seat,seed,costband], ...]
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(a, st, s, cb, (None if a == "A0" else SIG[a]), None) for a, st, s, cb in spec]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(lambda j: run(*j), jobs): print(r, flush=True)
    print("RUNNER_DONE")
