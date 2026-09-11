"""r12 driver: run the shaping grid on the parameterised device. ENV whitelist asserted+recorded (E-0826-D).
Device = w10_r12.py (= pinned w10_sleeve.py b88e35a4... + {SMA,SBAND,AUX12}); parent sha re-verified here."""
import numpy as np, os, subprocess, time, json, hashlib, sys
R = "/workspace/uplift_2026-09-11/r12_smoothing"; D = R + "/dev"
HC = "/workspace/review_scratch/health_check"
DEV = R + "/w10_r12.py"
PARENT = "/workspace/uplift_2026-09-11/w10_sleeve.py"
assert hashlib.sha256(open(PARENT, "rb").read()).hexdigest() == "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
assert hashlib.sha256(open(DEV, "rb").read()).hexdigest() == "79d7f5709b6602413181ccf69c5580b112ea9bbce0150620a93662b744f32e47"
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(COSTB, "rb").read()).hexdigest()[:16] == "295b4e7b462373e4"
BASE = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
        "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "COSTB_JSON=" + COSTB]
os.makedirs(R + "/arms", exist_ok=True); os.makedirs(D + "/logs", exist_ok=True)
ENVLOG = {}
def run(job):
    tag, sma, sband, aux, sd = job
    dst = R + "/arms/%s.npz" % tag
    if os.path.exists(dst): return tag + " skip"
    env = dict(os.environ); env.update(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4")
    e = list(BASE) + ["FSEED=%d" % sd, "FPRED=f10_A0_s%d.npy" % sd,
                      "SMA=%s" % sma, "SBAND=%s" % sband, "AUX12=%d" % aux]
    cmd = ["env"] + e + ["OUT_TAG=" + tag, "/workspace/venv/bin/python", DEV]
    t = time.time()
    with open(D + "/logs/%s.log" % tag, "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
    if rc != 0 or not os.path.exists(src): return "FAIL %s rc=%d" % (tag, rc)
    Z = np.load(src, allow_pickle=True)
    keep = {"cols": Z["cols"], "rec": Z["d30_n2_c42_rec"], "W": Z["d30_n2_c42_W"], "config_json": Z["config_json"]}
    if aux:
        keep["R12T"] = Z["d30_n2_c42_R12T"]; keep["R12A"] = Z["d30_n2_c42_R12A"]; keep["R12A_cols"] = Z["d30_n2_c42_R12A_cols"]
    np.savez_compressed(dst, **keep)
    os.remove(src)
    ENVLOG[tag] = {"cmd": " ".join(cmd), "env_whitelist": {k.split("=")[0]: k.split("=", 1)[1] for k in e},
                   "OMP_NUM_THREADS": "4", "cwd": D, "python": "/workspace/venv/bin/python", "rc": rc}
    return "%-30s ok %5.1fs" % (tag, time.time() - t)
if __name__ == "__main__":
    which = sys.argv[1]
    jobs = []
    if which == "gate":
        jobs = [("G1_a010_b250_aux0", "0.1", "2.5e-4", 0, 42), ("G1_a010_b250_aux1", "0.1", "2.5e-4", 1, 42)]
    elif which == "grid":
        for sma in ("0.05", "0.10", "0.15", "0.20", "0.30", "0.50", "1.00"):
            for sband in ("0.0", "1.25e-4", "2.5e-4", "5.0e-4"):
                tag = "S_a%s_b%s_s42" % (sma.replace(".", ""), sband.replace(".", "").replace("-", ""))
                jobs.append((tag, sma, sband, 1, 42))
    elif which == "seed2":
        for spec in sys.argv[2:]:
            sma, sband = spec.split(",")
            tag = "S_a%s_b%s_s2027" % (sma.replace(".", ""), sband.replace(".", "").replace("-", ""))
            jobs.append((tag, sma, sband, 1, 2027))
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(run, jobs): print(r, "%.0fs" % (time.time() - t0), flush=True)
    p = R + "/R12_RUN_ENV.json"
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(ENVLOG); old["_BASE"] = BASE; old["_device"] = DEV
    old["_device_sha256"] = hashlib.sha256(open(DEV, "rb").read()).hexdigest()
    old["_parent_sha256"] = hashlib.sha256(open(PARENT, "rb").read()).hexdigest()
    json.dump(old, open(p, "w"), indent=1)
    print("DRIVE_DONE")
