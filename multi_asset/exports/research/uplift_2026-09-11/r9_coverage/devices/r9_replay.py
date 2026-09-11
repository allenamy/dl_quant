"""R9 replay driver: the v4-native DL-leg arm (A1 form) on the incumbent axis and on the r6-extended axis.
Device = the PINNED /workspace/uplift_2026-09-11/w10_sleeve.py (sha256 b88e35a46b93d712...), unmodified.
E-0826-D: the env whitelist is ENUMERATED and asserted on the EFFECTIVE strings passed to every child."""
import os, sys, json, time, hashlib, subprocess
import numpy as np
ROOT = "/workspace/uplift_2026-09-11/r9"; U = "/workspace/uplift_2026-09-11"
HC = "/workspace/review_scratch/health_check"; R6 = f"{U}/r6/out"
DEV = f"{U}/w10_sleeve.py"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
DEVSHA = sha(DEV); assert DEVSHA.startswith("b88e35a46b93d712"), DEVSHA
COSTB = f"{U}/r3k/costb_PWR_G230k.json"; COSTSHA = sha(COSTB); assert COSTSHA.startswith("295b4e7b462373e4"), COSTSHA
UMASK = f"{HC}/masks/umask_UPIT_CRYPTO.npz"
# ── the two trees, built here so r6's tree is untouched ──
TREES = {
 "inc": {"dir": f"{ROOT}/dev_inc",
   "links": {"pod_backup_2026-08-21/wide_fea_hist_meta.npz": "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
             "pod_backup_2026-08-21/slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy",
             "pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz": "/workspace/data/wide_panel_4h_v2ext.npz",
             "pod_backup_2026-08-21/nets_histv2_-30_2_42.npy": f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
             "pod_backup_2026-08-21/nets_histv2_0_0_0.npy": f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
             "dlw_2026-08-22": "/workspace/dlw_v4raw",
             "f8_2026-08-22/preds/f10_v4RAW_s42.npy": f"{HC}/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy",
             "f8_2026-08-22/preds/f10_v4RAW_s2027.npy": f"{HC}/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy",
             "f8_2026-08-22/preds/f10_A0_s42.npy": f"{HC}/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy",
             "f8_2026-08-22/preds/f10_A0_s2027.npy": f"{HC}/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"},
   "slow": "/workspace/review_scratch/king_v4/SLOW_v4.npy"},
 "ext": {"dir": f"{ROOT}/dev_ext",
   "links": {"pod_backup_2026-08-21/wide_fea_hist_meta.npz": f"{R6}/meta_newprod_v4_x0910.npz",
             "pod_backup_2026-08-21/slow_pred_hist_oos.npy": f"{R6}/SLOW_v4_x0910.npy",
             "pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz": f"{R6}/wide_panel_4h_v2ext_x0910.npz",
             "pod_backup_2026-08-21/nets_histv2_-30_2_42.npy": f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
             "pod_backup_2026-08-21/nets_histv2_0_0_0.npy": f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
             "dlw_2026-08-22": f"{R6}/dlw_v4raw_x0910",
             "f8_2026-08-22/preds/f10_v4RAWx_s42.npy": f"{ROOT}/out/f10_v4RAWx_s42.npy",
             "f8_2026-08-22/preds/f10_v4RAWx_s2027.npy": f"{ROOT}/out/f10_v4RAWx_s2027.npy"},
   "slow": f"{R6}/SLOW_v4_x0910.npy"}}
for t, T in TREES.items():
    for sub in ("logs", "probe_artifacts", "pod_backup_2026-08-21", "f8_2026-08-22/preds"):
        os.makedirs(f"{T['dir']}/{sub}", exist_ok=True)
    for rel, src in T["links"].items():
        dst = f"{T['dir']}/{rel}"
        assert os.path.exists(src), f"missing source {src}"
        if os.path.islink(dst) or os.path.exists(dst): os.remove(dst)
        os.symlink(src, dst)
ENV_WL = ["LEGS", "CAL", "WRULE", "LOOK", "MEMBERS_TOPN", "FTRIM", "PHI", "UMASK_SCOPE", "UMASK_NPZ",
          "SLOW_NPY", "FSEED", "FPRED", "COSTB_JSON", "OUT_TAG"]
COMMON = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero",
          "PHI=0.45", "UMASK_SCOPE=m1", "UMASK_NPZ=" + UMASK, "COSTB_JSON=" + COSTB]
JOBS = []
for s in ("42", "2027"):
    JOBS.append(("inc", f"R9_A1_inc_s{s}",  ["SLOW_NPY=" + TREES["inc"]["slow"], f"FSEED={s}", f"FPRED=f10_v4RAW_s{s}.npy"]))
    JOBS.append(("ext", f"R9_A1x_ext_s{s}", ["SLOW_NPY=" + TREES["ext"]["slow"], f"FSEED={s}", f"FPRED=f10_v4RAWx_s{s}.npy"]))
def run(tree, tag, extra):
    d = TREES[tree]["dir"]
    if os.path.exists(f"{d}/probe_artifacts/w10_ablation_series_{tag}.npz"): return f"{tag} cached"
    ex = COMMON + extra + ["OUT_TAG=" + tag]
    for e in ex:
        assert e.split("=", 1)[0] in ENV_WL, "env key outside whitelist: " + e
    env = dict(os.environ)
    for k in list(env):
        if k in ENV_WL or k.startswith("TILT") or k in ("W3FIX", "SEATF10", "KMOD", "KTAIL", "KMOD_F10",
            "KMOD_AGREE", "SEATNET", "FUNDSCALE", "FEMAT_NPZ", "TRADE_TOPN", "REF_SKIP", "RNSM", "FTPOS",
            "LTRIM_TH", "CDAMP", "FTRIM_TH", "SLEEVE", "W3FIX"): env.pop(k, None)
    env.update(OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3", MKL_NUM_THREADS="3")
    t0 = time.time()
    with open(f"{d}/logs/{tag}.log", "w") as lf:
        rc = subprocess.call(["env"] + ex + ["/workspace/venv/bin/python", DEV], cwd=d, stdout=lf, stderr=subprocess.STDOUT, env=env)
    return f"{tag} rc={rc} {time.time()-t0:.0f}s"
from concurrent.futures import ThreadPoolExecutor
REC = {"device": DEV, "device_sha256": DEVSHA, "cost_json": COSTB, "cost_sha256": COSTSHA,
       "env_whitelist": ENV_WL, "common_env": COMMON, "trees": {k: {"dir": v["dir"], "links": v["links"]} for k, v in TREES.items()},
       "jobs": [{"tree": j[0], "tag": j[1], "env": j[2]} for j in JOBS],
       "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
t00 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    REC["results"] = list(ex.map(lambda j: run(*j), JOBS))
for r in REC["results"]: print(r, flush=True)
REC["wall_s"] = round(time.time() - t00, 1)
REC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(REC, open(f"{ROOT}/out/RECEIPT_r9_replay_runs.json", "w"), indent=1)
print("R9_REPLAY_DONE", REC["wall_s"], flush=True)
