"""Track D v4-caliber sleeve driver (PREREG_trackD_sleeves_2026-09-11).
For each frozen candidate: build the injected score matrix, run w10_health.py (sha 8684d9a9...) on the
dev_v4s mirror with LEGS=001 PHI=0, reduce the artifact to rec-only, delete the large files.
Every number that follows comes from this device. READ-ONLY on all v4 artifacts."""
import numpy as np, os, json, subprocess, hashlib, time, sys
HC = "/workspace/review_scratch/health_check"
D  = "/workspace/uplift_2026-09-11/dev_v4s"
OUT= "/workspace/uplift_2026-09-11/trackD_v4"
os.makedirs(OUT, exist_ok=True); os.makedirs(f"{D}/sig", exist_ok=True)
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
ts = PW["ts"].astype(np.int64); sym = PW["symbols"]
FN = np.asarray(PW["f_fund_now"], float); IV = np.asarray(PW["f_fund_iv"], float)
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = FN * (8.0/IVf)
FE1 = np.asarray(PW["f_fund_ema_v1"], float); BASE = np.isfinite(FE1)
def rz(M):
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = ok.sum()
        if n >= 10:
            out[i, ok] = np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def col(c): return np.asarray(PW[c], float)
SIG = {c: col(c) for c in ["f_rev_4h","f_rev_24h","f_rev_3d","f_mom_7d","f_mom_30d","f_mom_7d_x24",
       "f_vol_7d","f_volq_ratio","f_amihud_24h","f_range_24h","f_cpos_24h","f_tbf_24h","f_asz_24h",
       "f_fund_iv","f_fund_ema","f_fund_ema_v2"]}
SIG["f_fund_rn8"]   = RN8
SIG["D_SURP"]       = RN8 - FE1
SIG["D_MOMSPREAD"]  = col("f_mom_30d") - col("f_mom_7d")
SIG["D_VOLADJMOM"]  = col("f_mom_7d")/(np.abs(col("f_vol_7d"))+1e-6)
SIG["D_ILLIQ_FUND"] = rz(np.where(BASE, col("f_amihud_24h"), np.nan)) * rz(np.where(BASE, FE1, np.nan))
SIG["FUND_V1"]      = FE1
COMMON = ["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
          f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz", f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
          "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag, extra):
    env = dict(os.environ); env["OMP_NUM_THREADS"]="2"; env["OPENBLAS_NUM_THREADS"]="2"; env["MKL_NUM_THREADS"]="2"
    cmd = ["env"] + COMMON + extra + [f"OUT_TAG={tag}", "/workspace/venv/bin/python", f"{HC}/w10_health.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc != 0 or not os.path.exists(src):
        print(f"FAIL {tag} rc={rc}", flush=True); return None
    A = np.load(src, allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz", cols=A["cols"], rec=A["d30_n2_c42_rec"], rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"], legs_fund=A["legs_fund"], config_json=A["config_json"])
    os.remove(src)
    return True
ARMS = []
for name, M in SIG.items():
    for sgn, tg in ((1.0,"p"), (-1.0,"m")):
        ARMS.append((f"SL_{name}__{tg}", name, sgn))
if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    man = {}
    t0 = time.time()
    for tag, name, sgn in ARMS:
        if only and only not in tag: continue
        if os.path.exists(f"{OUT}/{tag}.npz"): print("skip", tag, flush=True); continue
        M = np.where(BASE, sgn*np.asarray(SIG[name], np.float64), np.nan).astype(np.float32)
        f = f"{D}/sig/cur.npz"
        np.savez(f, symbols=sym, ts=ts, mat=M)
        ok = run(tag, ["LEGS=001","PHI=0","FTRIM=off", f"FEMAT_NPZ={f}"])
        man[tag] = {"signal": name, "sign": sgn, "ok": bool(ok)}
        print(f"{tag:28s} {'ok' if ok else 'FAIL'}  {time.time()-t0:6.1f}s", flush=True)
        os.remove(f)
    json.dump(man, open(f"{OUT}/arms_manifest.json","w"), indent=1)
    print("ALL DONE", time.time()-t0)
