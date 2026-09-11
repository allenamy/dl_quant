"""P4 device runner. Device = /workspace/uplift_2026-09-11/w10_sleeve.py (PINNED sha b88e35a46b93d712), knobs OFF.
Env COMMON copied VERBATIM from r3_xib/runner.py (itself verbatim from review_scratch/run_v4_arms.sh ARM=A0,
the script that produced the archived A0 artifacts). Only two things vary across my runs:
  FPRED  -- which DL draw's prediction file the model leg rides
  COSTB_JSON -- STD (= archived, for GATE P bitwise) or PWR230k (= the FITTED cost, for every reported number)
Arm is always A0 (no FEMAT injection): this study is about the DL leg itself, not about any new signal.
Usage: runner.py <labels,csv> <costkey> [seats]
"""
import numpy as np, os, sys, subprocess, time, hashlib, json
R = "/workspace/uplift_2026-09-11/r4_nondet"; D = R + "/dev"; OUT = R + "/arms"
HC = "/workspace/review_scratch/health_check"
DEV = "/workspace/uplift_2026-09-11/w10_sleeve.py"
for p in (D + "/logs", D + "/probe_artifacts", OUT): os.makedirs(p, exist_ok=True)
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
COSTB = {"STD": HC + "/calib/costb_fee_steady.json",
         "PWR230k": "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"}
COMMON = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
          "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz", "SLOW_NPY=" + K3]


def run(job):
    label, seat, cb = job
    tag = "R4_A0_%s_%s_s%s" % (cb, seat, label)
    dst = "%s/w10_ablation_series_%s.npz" % (OUT, tag)
    if os.path.exists(dst): return tag + " skip"
    env = dict(os.environ); env.update(OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3", MKL_NUM_THREADS="3")
    cmd = ["env"] + COMMON + ["FSEED=%s" % label, "FPRED=f10_A0_s%s.npy" % label,
                              "COSTB_JSON=" + COSTB[cb]] \
        + (["W3FIX=0.21,0,0.79"] if seat == "fix" else []) \
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
    labels = sys.argv[1].split(",")
    cb = sys.argv[2]
    seats = sys.argv[3].split(",") if len(sys.argv) > 3 else ["dyn", "fix"]
    jobs = [(l, st, cb) for l in labels for st in seats]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(run, jobs): print(r, flush=True)
    print("RUNNER_DONE")
