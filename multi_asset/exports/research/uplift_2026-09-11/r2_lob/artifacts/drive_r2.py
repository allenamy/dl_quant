"""Round-2 LOB sleeve driver. Same device/env as round-1 drive_sleeves*.py (w10_health.py sha 8684d9a9...).
LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<injected score> => standalone fund-leg-shaped book on the injected score."""
import numpy as np, os, sys, subprocess, time, json
HC = "/workspace/review_scratch/health_check"; D = "/workspace/uplift_2026-09-11/dev_v4s"
OUT = "/workspace/uplift_2026-09-11/r2/arms"; LOB = "/workspace/uplift_2026-09-11/r2/lob2"
os.makedirs(OUT, exist_ok=True); os.makedirs(D + "/sigr2", exist_ok=True)
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
ts = PW["ts"].astype(np.int64); sym = PW["symbols"]
FE1 = np.asarray(PW["f_fund_ema_v1"], float); BASE = np.isfinite(FE1)
def rz(M):
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = ok.sum()
        if n >= 10: out[i, ok] = np.argsort(np.argsort(v[ok])) / max(n - 1, 1) - 0.5
    return out
ZF = rz(np.where(BASE, FE1, np.nan))
ZV = rz(np.where(BASE, np.asarray(PW["f_vol_7d"], float), np.nan))
def orth(Z):
    R = np.full(Z.shape, np.nan)
    for i in range(Z.shape[0]):
        ok = np.isfinite(Z[i]) & np.isfinite(ZF[i])
        if ok.sum() < 10: continue
        x = ZF[i][ok]; y = Z[i][ok]; vx = float((x * x).sum())
        b = float((x * y).sum() / vx) if vx > 1e-12 else 0.0
        R[i][ok] = y - b * x
    return R
def orth2(Z):
    """per-anchor cross-sectional residual of Z against [1, rank(fund_ema_v1), rank(vol_7d)]"""
    R = np.full(Z.shape, np.nan)
    for i in range(Z.shape[0]):
        ok = np.isfinite(Z[i]) & np.isfinite(ZF[i]) & np.isfinite(ZV[i])
        if ok.sum() < 20: continue
        X = np.column_stack([np.ones(ok.sum()), ZF[i][ok], ZV[i][ok]]); y = Z[i][ok]
        try: bb, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError: continue
        R[i][ok] = y - X @ bb
    return R
COMMON = ["CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "UMASK_SCOPE=m1",
          "UMASK_NPZ=%s/masks/umask_UPIT_CRYPTO.npz" % HC, "COSTB_JSON=%s/calib/costb_fee_steady.json" % HC,
          "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag, sigfile):
    env = dict(os.environ); env.update(OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
    cmd = ["env"] + COMMON + ["LEGS=001", "PHI=0", "FTRIM=off", "FEMAT_NPZ=" + sigfile,
           "OUT_TAG=" + tag, "/workspace/venv/bin/python", HC + "/w10_health.py"]
    with open("%s/logs/%s.log" % (D, tag), "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    src = "%s/probe_artifacts/w10_ablation_series_%s.npz" % (D, tag)
    if rc != 0 or not os.path.exists(src):
        print("FAIL", tag, rc, flush=True); return False
    A = np.load(src, allow_pickle=True)
    np.savez_compressed("%s/%s.npz" % (OUT, tag), cols=A["cols"], rec=A["d30_n2_c42_rec"],
                        legs_ts=A["legs_ts"], legs_fund=A["legs_fund"], config_json=A["config_json"])
    os.remove(src); return True
def getmat(nm):
    z = np.load("%s/%s.npz" % (LOB, nm), allow_pickle=True)
    assert np.array_equal(z["ts"].astype(np.int64), ts), nm
    assert [str(x) for x in z["symbols"]] == [str(x) for x in sym], nm
    return np.asarray(z["mat"], np.float64)
if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1]))
    t0 = time.time()
    for j in jobs:
        tag = j["tag"]
        if os.path.exists("%s/%s.npz" % (OUT, tag)): print("skip", tag, flush=True); continue
        M = np.where(BASE, getmat(j["feat"]), np.nan)
        if j.get("perm"):
            rng = np.random.default_rng([20260911, int(j["perm"])])
            P = np.full(M.shape, np.nan)
            for i in range(M.shape[0]):
                ok = np.isfinite(M[i]); n = ok.sum()
                if n: P[i, ok] = M[i, ok][rng.permutation(n)]
            M = P
        if j["kind"] == "orth":
            M = orth(rz(M))
        elif j["kind"] == "orth2":
            M = orth2(rz(M))
        elif j["kind"] == "orthperm":
            Z = rz(M); rng = np.random.default_rng([20260911, 900 + int(j["perm"])])
            P = np.full(Z.shape, np.nan)
            for i in range(Z.shape[0]):
                ok = np.isfinite(Z[i]); n = ok.sum()
                if n: P[i, ok] = Z[i, ok][rng.permutation(n)]
            M = orth(P)
        if j.get("lag"):
            L = np.full(M.shape, np.nan); L[int(j["lag"]):] = M[:-int(j["lag"])]; M = L
        f = "%s/sigr2/%s.npz" % (D, tag)
        np.savez(f, symbols=sym, ts=ts, mat=(float(j["sgn"]) * M).astype(np.float32))
        ok = run(tag, f)
        print("%-34s %s %6.1fs" % (tag, "ok" if ok else "FAIL", time.time() - t0), flush=True)
        os.remove(f)
    print("BATCH DONE", time.time() - t0)
