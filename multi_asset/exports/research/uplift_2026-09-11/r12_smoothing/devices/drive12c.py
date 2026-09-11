"""r12c driver (EXPLORATORY state-conditional shaping). ENV whitelist recorded (E-0826-D)."""
import numpy as np, os, subprocess, time, json, hashlib, sys
R = "/workspace/uplift_2026-09-11/r12_smoothing"; D = R + "/dev"; HC = "/workspace/review_scratch/health_check"
DEV = R + "/w10_r12c.py"
assert hashlib.sha256(open(R + "/w10_r12.py", "rb").read()).hexdigest() == "79d7f5709b6602413181ccf69c5580b112ea9bbce0150620a93662b744f32e47"
assert hashlib.sha256(open(DEV, "rb").read()).hexdigest() == "6a6d2b0a426d4ca6a175873d707e5ecbae9850df1678b2559cf544624e8c2fcd"
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
BASE = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
        "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "COSTB_JSON=" + COSTB,
        "FSEED=42", "FPRED=f10_A0_s42.npy", "AUX12=1"]
ENVLOG = {}
def run(job):
    tag, sma, sband, mask, smahi, sbandhi = job
    dst = R + "/arms/%s.npz" % tag
    if os.path.exists(dst): return tag + " skip"
    env = dict(os.environ); env.update(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4")
    e = list(BASE) + ["SMA=%s" % sma, "SBAND=%s" % sband]
    if mask: e += ["STATEMASK_NPZ=%s/mask_%s.npz" % (R, mask), "SMAHI=%s" % smahi, "SBANDHI=%s" % sbandhi]
    cmd = ["env"] + e + ["OUT_TAG=" + tag, "/workspace/venv/bin/python", DEV]
    t = time.time()
    with open(D + "/logs/%s.log" % tag, "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
    if rc != 0 or not os.path.exists(src): return "FAIL %s rc=%d" % (tag, rc)
    Z = np.load(src, allow_pickle=True)
    np.savez_compressed(dst, cols=Z["cols"], rec=Z["d30_n2_c42_rec"], W=Z["d30_n2_c42_W"],
                        config_json=Z["config_json"], R12T=Z["d30_n2_c42_R12T"], R12A=Z["d30_n2_c42_R12A"],
                        R12A_cols=Z["d30_n2_c42_R12A_cols"])
    os.remove(src)
    ENVLOG[tag] = {"cmd": " ".join(cmd), "env_whitelist": {k.split("=")[0]: k.split("=", 1)[1] for k in e}, "rc": rc}
    return "%-34s ok %5.1fs" % (tag, time.time() - t)
JOBS = [
 ("G2_null_nomask", "0.10", "2.5e-4", None, None, None),                    # gate: no mask => must be bitwise the deployed arm
 ("C_AS_fast_a010", "0.10", "2.5e-4", "ALTSURGE", "1.00", "0.0"),
 ("C_AS_med_a010", "0.10", "2.5e-4", "ALTSURGE", "0.30", "0.0"),
 ("C_AS_fast_a005", "0.05", "2.5e-4", "ALTSURGE", "1.00", "0.0"),
 ("C_NULL101_a010", "0.10", "2.5e-4", "NULLSHIFT101", "1.00", "0.0"),
 ("C_NULL503_a010", "0.10", "2.5e-4", "NULLSHIFT503", "1.00", "0.0"),
 ("C_NULL1009_a010", "0.10", "2.5e-4", "NULLSHIFT1009", "1.00", "0.0"),
]
if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=7) as ex:
        for r in ex.map(run, JOBS): print(r, "%.0fs" % (time.time() - t0), flush=True)
    p = R + "/R12C_RUN_ENV.json"
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(ENVLOG); old["_BASE"] = BASE; old["_device"] = DEV
    old["_device_sha256"] = hashlib.sha256(open(DEV, "rb").read()).hexdigest()
    json.dump(old, open(p, "w"), indent=1); print("DRIVE12C_DONE")
