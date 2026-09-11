"""R9 control: is the newly-covered window negative BECAUSE the DL fold is a month stale, or is the
window itself bad? PHI=0 removes the DL leg entirely (king+fund only) on the same extended tree.
ENV whitelist enumerated + asserted (E-0826-D)."""
import os, json, time, hashlib, subprocess, calendar
import numpy as np
U = "/workspace/uplift_2026-09-11"; ROOT = U + "/r9"; HC = "/workspace/review_scratch/health_check"
DEV = U + "/w10_sleeve.py"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
assert sha(DEV).startswith("b88e35a46b93d712")
COSTB = U + "/r3k/costb_PWR_G230k.json"; assert sha(COSTB).startswith("295b4e7b462373e4")
ENV_WL = ["LEGS", "CAL", "WRULE", "LOOK", "MEMBERS_TOPN", "FTRIM", "PHI", "UMASK_SCOPE", "UMASK_NPZ",
          "SLOW_NPY", "FSEED", "FPRED", "COSTB_JSON", "OUT_TAG"]
COMMON = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero",
          "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz", "COSTB_JSON=" + COSTB]
JOBS = [("ext", "R9_PHI0_ext_s42", ["PHI=0", "SLOW_NPY=" + U + "/r6/out/SLOW_v4_x0910.npy", "FSEED=42", "FPRED=f10_v4RAWx_s42.npy"]),
        ("inc", "R9_PHI0_inc_s42", ["PHI=0", "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy", "FSEED=42", "FPRED=f10_v4RAW_s42.npy"])]
def run(tree, tag, extra):
    d = f"{ROOT}/dev_{tree}"
    if os.path.exists(f"{d}/probe_artifacts/w10_ablation_series_{tag}.npz"): return tag + " cached"
    ex = COMMON + extra + ["OUT_TAG=" + tag]
    for e in ex: assert e.split("=", 1)[0] in ENV_WL, e
    env = dict(os.environ)
    for k in list(env):
        if k in ENV_WL: env.pop(k, None)
    env.update(OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3", MKL_NUM_THREADS="3")
    with open(f"{d}/logs/{tag}.log", "w") as lf:
        rc = subprocess.call(["env"] + ex + ["/workspace/venv/bin/python", DEV], cwd=d, stdout=lf, stderr=subprocess.STDOUT, env=env)
    return f"{tag} rc={rc}"
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as ex:
    for r in ex.map(lambda j: run(*j), JOBS): print(r, flush=True)
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
CUT_OLD = T(2026, 8, 30, 20); WARM = 900; APY = 2190
def load(p):
    Z = np.load(p, allow_pickle=True); cc = [str(c) for c in Z["cols"]]; ix = {c: i for i, c in enumerate(cc)}
    k = "rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R = np.asarray(Z[k], float); return np.round(R[:, ix["ts"]]).astype(np.int64), R, ix
def sr(x): return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(APY)) if len(x) > 5 else float("nan")
OUT = {"env_whitelist": ENV_WL, "common": COMMON, "device_sha256": sha(DEV)}
for tag, tree in (("R9_PHI0_ext_s42", "ext"), ("R9_A1x_ext_s42", "ext"), ("R9_PHI0_inc_s42", "inc")):
    p = f"{ROOT}/dev_{tree}/probe_artifacts/w10_ablation_series_{tag}.npz"
    ts, R, ix = load(p); ts = ts[WARM:]; g = (R[:, ix["net_ex"]] / R[:, ix["gross_total"]])[WARM:]
    new = ts > CUT_OLD; old = ts <= CUT_OLD
    OUT[tag] = {"n_all": int(len(ts)),
                "old_window": {"n": int(old.sum()), "mean_g": round(float(g[old].mean()), 4), "sharpe": round(sr(g[old]), 4)},
                "new_61": ({"n": int(new.sum()), "first": iso(ts[new][0]), "last": iso(ts[new][-1]),
                            "mean_g": round(float(g[new].mean()), 4), "sharpe": round(sr(g[new]), 4)} if new.any() else None)}
json.dump(OUT, open(ROOT + "/out/RECEIPT_r9_control_phi0.json", "w"), indent=1, default=float)
print(json.dumps(OUT, indent=1))
