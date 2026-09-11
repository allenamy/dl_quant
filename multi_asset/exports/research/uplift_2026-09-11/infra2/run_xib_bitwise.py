"""INFRA2 BITWISE DEVICE RUNNER (round 2, 2026-09-11).

The DEVICE is unchanged: /workspace/review_scratch/health_check/w10_health.py, sha256 8684d9a9...,
the same program that produced the archived A0 artifacts. Nothing in it is edited — the round-1
residual was never in the device, it was in the SIGNAL BUILDER that fed FEMAT_NPZ (ORDINAL vs AVERAGE
ranks on a feature with ties on 90% of panel rows). This runner rebuilds the injected matrix with
xib_signal.RZ (the device's own xz) and writes the FULL arm artifact (cols, symbols, W, config_json)
under the arm-name convention the judge loads.

Arms (all four judged cells each: seat dyn/fix x seed 42/2027, A0's exact config otherwise):
  XIBPAR   = xz(f_fund_ema_v1)                                  -> must be BITWISE A0
  XIBLAG50 = 0.5*xz(f_fund_ema_v1) + 0.5*xz(f_amihud_24h)[t-1]  -> round 1's XIB_LAG50, re-measured
  XIBOLD50 = the SAME blend built with the round-1 ORDINAL ranker (the control that isolates the fix)
"""
import numpy as np, os, sys, subprocess, time, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xib_signal import RZ, blend, save

HC = "/workspace/review_scratch/health_check"
ROOT = "/workspace/uplift_2026-09-11/infra2"
D = ROOT + "/dev"; OUT = ROOT + "/arms"
for p in (D + "/logs", D + "/sig", D + "/probe_artifacts", OUT): os.makedirs(p, exist_ok=True)
BK = D + "/pod_backup_2026-08-21"; os.makedirs(BK, exist_ok=True)
LINKS = {"nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
         "nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         "slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy",
         "wide_fea_hist_meta.npz": "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
         "wide_panel_4h_hist_v2.npz": "/workspace/data/wide_panel_4h_v2ext.npz"}
for k, v in LINKS.items():
    t = BK + "/" + k
    if not os.path.islink(t): os.symlink(v, t)
for k, v in {"dlw_2026-08-22": "/workspace/dlw_v4raw", "f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}.items():
    if not os.path.islink(D + "/" + k): os.symlink(v, D + "/" + k)

PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
ts = PW["ts"].astype(np.int64); sym = PW["symbols"]
FE1 = np.asarray(PW["f_fund_ema_v1"], float); B = np.isfinite(FE1)
AM = np.asarray(PW["f_amihud_24h"], float)
ZF = RZ(FE1, B)
ZA = RZ(AM, B)
ZA_LAG = np.full_like(ZA, np.nan); ZA_LAG[1:] = ZA[:-1]; ZA_LAG = np.where(B, ZA_LAG, np.nan)   # window ends one anchor before E


def rz_old(M):
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = ok.sum()
        if n >= 10: out[i, ok] = np.argsort(np.argsort(v[ok])) / max(n - 1, 1) - 0.5
    return out


ZFo = rz_old(np.where(B, FE1, np.nan)); ZAo = rz_old(np.where(B, AM, np.nan))
ZAo_LAG = np.full_like(ZAo, np.nan); ZAo_LAG[1:] = ZAo[:-1]; ZAo_LAG = np.where(B, ZAo_LAG, np.nan)

MATS = {"XIBPAR": ZF,
        "XIBLAG50": blend((0.5, ZF), (0.5, ZA_LAG)),
        "XIBOLD50": np.where(np.isfinite(ZFo) & np.isfinite(ZAo_LAG), 0.5 * np.nan_to_num(ZFo) + 0.5 * np.nan_to_num(ZAo_LAG), np.nan)}

K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
COMMON = ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
          "UMASK_SCOPE=m1", "UMASK_NPZ=" + HC + "/masks/umask_UPIT_CRYPTO.npz",
          "COSTB_JSON=" + HC + "/calib/costb_fee_steady.json", "SLOW_NPY=" + K3]


def run(arm, seat, seed, femat):
    tag = f"V4_{arm}_{seat}_s{seed}"
    dst = f"{OUT}/w10_ablation_series_{tag}.npz"
    if os.path.exists(dst): print("skip", tag, flush=True); return dst
    env = dict(os.environ); env.update(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4")
    cmd = ["env"] + COMMON + [f"FSEED={seed}", f"FPRED=f10_A0_s{seed}.npy"] \
        + (["W3FIX=0.21,0,0.79"] if seat == "fix" else []) \
        + [f"FEMAT_NPZ={femat}", f"OUT_TAG={tag}", "/workspace/venv/bin/python", HC + "/w10_health.py"]
    t = time.time()
    with open(f"{D}/logs/{tag}.log", "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc != 0 or not os.path.exists(src): print("FAIL", tag, rc, flush=True); return None
    os.replace(src, dst); os.replace(f"{D}/probe_artifacts/w10_ablation_summary_{tag}.json", f"{OUT}/w10_ablation_summary_{tag}.json")
    print("%-26s ok %5.1fs  sha %s" % (tag, time.time() - t, hashlib.sha256(open(dst, 'rb').read()).hexdigest()[:16]), flush=True)
    return dst


if __name__ == "__main__":
    only = sys.argv[1:]
    for arm, M in MATS.items():
        if only and arm not in only: continue
        f = save(f"{D}/sig/{arm}.npz", sym, ts, M)
        for seat in ("dyn", "fix"):
            for seed in ("42", "2027"):
                run(arm, seat, seed, f)
    print("RUNNER_DONE")
