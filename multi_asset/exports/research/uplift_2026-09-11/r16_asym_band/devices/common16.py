"""r16 shared launcher: env -i whitelist (E-0826-D), pinned shas asserted, per-run env + cmd recorded."""
import numpy as np, os, subprocess, time, json, hashlib
R = "/workspace/uplift_2026-09-11/r16_asym_band"; D = R + "/dev"
HC = "/workspace/review_scratch/health_check"
DEV = R + "/w10_r16.py"
PARENT = "/workspace/uplift_2026-09-11/w10_sleeve.py"
PREREG = R + "/PREREG_r16_asym_band_2026-09-12.md"
COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
SHA = {"parent": "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650",
       "prereg": "68bc4fdb7f619dbb9ca10fc868f86b1f31f227029f7b58aead309f4620ab2b0c",
       "costb": "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53",
       "A0_s42": "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339",
       "A0_s2027": "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def assert_pins():
    assert sha(PARENT) == SHA["parent"], sha(PARENT)
    assert sha(PREREG) == SHA["prereg"], sha(PREREG)
    assert sha(COSTB) == SHA["costb"], sha(COSTB)
    for s in (42, 2027):
        p = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s%d.npz" % s
        assert sha(p) == SHA["A0_s%d" % s], p
    return sha(DEV)
BASE = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
        "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "COSTB_JSON=" + COSTB]
SYS = ["PATH=/workspace/venv/bin:/usr/bin:/bin", "HOME=/root", "LANG=C.UTF-8",
       "OMP_NUM_THREADS=4", "OPENBLAS_NUM_THREADS=4", "MKL_NUM_THREADS=4"]
def setup():
    for p in (D + "/logs", D + "/probe_artifacts", R + "/arms", R + "/receipts"): os.makedirs(p, exist_ok=True)
    links = {"pod_backup_2026-08-21": "/workspace/uplift_2026-09-11/r8_inbook/dev/pod_backup_2026-08-21",
             "dlw_2026-08-22": "/workspace/dlw_v4raw", "f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}
    for k, v in links.items():
        t = D + "/" + k
        if not os.path.islink(t): os.symlink(v, t)
def run(tag, seed, xmode, xnull, aux, keep_W=True):
    """returns (tag, status, envrec)"""
    dst = R + "/arms/%s.npz" % tag
    if os.path.exists(dst): return tag, "skip", None
    e = list(BASE) + ["FSEED=%d" % seed, "FPRED=f10_A0_s%d.npy" % seed,
                      "XMODE=%s" % xmode, "XNULL=%d" % xnull, "AUX16=%d" % aux,
                      "PREREG16_PATH=" + PREREG, "OUT_TAG=" + tag]
    cmd = ["env", "-i"] + SYS + e + ["/workspace/venv/bin/python", DEV]
    t = time.time()
    with open(D + "/logs/%s.log" % tag, "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env={})
    src = D + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
    if rc != 0 or not os.path.exists(src): return tag, "FAIL rc=%d" % rc, None
    Z = np.load(src, allow_pickle=True)
    keep = {"cols": Z["cols"], "rec": Z["d30_n2_c42_rec"], "config_json": Z["config_json"]}
    if keep_W: keep["W"] = Z["d30_n2_c42_W"]
    if aux: keep["R16A"] = Z["d30_n2_c42_R16A"]; keep["R16A_cols"] = Z["d30_n2_c42_R16A_cols"]
    np.savez_compressed(dst, **keep); os.remove(src)
    js = D + "/probe_artifacts/w10_ablation_summary_%s.json" % tag
    envrec = {"cmd": " ".join(cmd), "env_whitelist": {k.split("=")[0]: k.split("=", 1)[1] for k in SYS + e},
              "launcher": "env -i (inherits nothing)", "cwd": D, "python": "/workspace/venv/bin/python", "rc": rc,
              "device_sha256": sha(DEV), "elapsed_s": round(time.time() - t, 1)}
    return tag, "ok %5.1fs" % (time.time() - t), envrec
def save_env(name, recs):
    p = R + "/receipts/" + name
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update({k: v for k, v in recs.items() if v is not None})
    old["_BASE"] = BASE; old["_SYS"] = SYS; old["_device"] = DEV; old["_device_sha256"] = sha(DEV)
    old["_parent_sha256"] = sha(PARENT); old["_prereg_sha256"] = sha(PREREG); old["_costb_sha256"] = sha(COSTB)
    json.dump(old, open(p, "w"), indent=1)
def loadavg(): return float(open("/proc/loadavg").read().split()[0])
def gpu():
    return subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip()
