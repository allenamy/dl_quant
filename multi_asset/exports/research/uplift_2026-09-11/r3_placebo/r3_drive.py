"""ROUND-3 PLACEBO RE-JUDGE DRIVER.
Device = /workspace/uplift_2026-09-11/w10_sleeve.py, sha256 b88e35a46b93d712..., ALL knobs off
(GATE P bitwise on V4_A0_{dyn,fix}_s{42,2027} rec AND W -- receipt r3_placebo/GATE_P_receipt.json).
Nulls from null_families.py.  Own mirror tree r3_placebo/dev; nothing else is touched.
usage: r3_drive.py <batch>     batch in {calib, standalone, inbook, all}
"""
import numpy as np, os, sys, json, time, subprocess, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from null_families import (NULLS, FAMILY_OF, availability_receipt,
                           make_rz, make_orth, lag1, ema)

HC = "/workspace/review_scratch/health_check"
U  = "/workspace/uplift_2026-09-11"
R  = U + "/r3_placebo"
D  = R + "/dev"
OUT= R + "/out"
DEV= U + "/w10_sleeve.py"
for d in (OUT, D + "/logs", D + "/sig", D + "/probe_artifacts"):
    os.makedirs(d, exist_ok=True)

PW  = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
TS  = PW["ts"].astype(np.int64); SYM = PW["symbols"]
FE1 = np.asarray(PW["f_fund_ema_v1"], float)
BASE= np.isfinite(FE1)
rz  = make_rz(BASE)
ZF  = rz(np.where(BASE, FE1, np.nan))
orth= make_orth(ZF)
M   = lambda X: np.where(BASE, np.asarray(X, float), np.nan)     # impose the device rank base

# ---------------------------------------------------------------- raw features
AMI   = np.asarray(PW["f_amihud_24h"], float)
TBF   = np.asarray(PW["f_tbf_24h"], float)
_FT   = np.load(U + "/r2_factor/feat/AMIRESID.npy")
AMIRES= np.asarray(_FT, float)
RESSKW= np.asarray(np.load(U + "/r2_factor/feat/RESSKEW.npy"), float)
_H    = np.load(U + "/r2_horizon/feats_r2.npz", allow_pickle=True)
assert np.array_equal(_H["ts"].astype(np.int64), TS)
AMI3D = np.asarray(_H["RET_MABS_864"], np.float64) / np.exp(np.asarray(_H["LQV_MEAN_864"], np.float64))
_L    = np.load(U + "/lob/LOBDEPTH.npz", allow_pickle=True)
assert np.array_equal(_L["ts"].astype(np.int64), TS)
LOBD  = np.asarray(_L["mat"], np.float64)
_E    = np.load(U + "/event_state/feats_v4.npz", allow_pickle=True)
assert np.array_equal(_E["ts"].astype(np.int64), TS)
LISTEV= np.asarray(_E["LISTEVT"], float)
_F12  = np.load(U + "/r2_solve2023/out/feats12.npz", allow_pickle=True)
assert np.array_equal(_F12["ts"].astype(np.int64), TS)
F6    = np.asarray(_F12["F6_FUND_TS"], float)
# RESID_SHARPE: the stage-2 offline prediction matrix (no .pt exists; this is all that survives)
_TG   = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
_Ets  = _TG["E_ts"].astype(np.int64)
assert np.array_equal([str(x) for x in _TG["symbols"]], [str(x) for x in SYM])
_OFF  = int(np.searchsorted(_Ets, TS[0])); assert np.array_equal(_Ets[_OFF:_OFF+len(TS)], TS)
RS42  = np.asarray(np.load(U + "/r2_learned/preds/RESID_SHARPE_s42.npy")[_OFF:_OFF+len(TS)], float)
RS2027= np.asarray(np.load(U + "/r2_learned/preds/RESID_SHARPE_s2027.npy")[_OFF:_OFF+len(TS)], float)

# ---------------------------------------------------------------- env blocks
UP = HC + "/masks/umask_UPIT_CRYPTO.npz"; CB = HC + "/calib/costb_fee_steady.json"
K4 = "/workspace/review_scratch/king_v4/SLOW_v4.npy"
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
SLCOM = ["LEGS=001", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=off", "PHI=0",
         "UMASK_SCOPE=m1", "UMASK_NPZ=" + UP, "COSTB_JSON=" + CB, "SLOW_NPY=" + K4]
def IB(seed):
    return ["LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45",
            "UMASK_SCOPE=m1", "UMASK_NPZ=" + UP, "COSTB_JSON=" + CB, "SLOW_NPY=" + K3,
            "FSEED=%s" % seed, "FPRED=f10_A0_s%s.npy" % seed]

# ---------------------------------------------------------------- arm specs
# spec = (raw feature, pipeline applied to the (possibly nulled) raw, env, archived reference)
def P_orth_rz(X):            return orth(rz(M(X)))
def P_orth_rz_lag(X):        return orth(lag1(rz(M(X)), BASE))
def P_orth_ema8_rz_lag(X):   return orth(lag1(rz(ema(M(X), 8)), BASE))
def P_ident(X):              return M(X)

ARMS = {
 # --- standalone sleeves (LEGS=001 PHI=0): the null replaces the whole fund score
 "AMI_lag":        dict(raw=AMI,      pipe=P_orth_rz_lag,      env=SLCOM,
                        ref=U+"/r2_attack/out/AM_REAL.npz"),
 "ORTH_amihud":    dict(raw=AMI,      pipe=P_orth_rz,          env=SLCOM,
                        ref=U+"/trackD_v4/SL_ORTH_f_amihud_24h__p.npz"),
 "ORTH_AMIRESID":  dict(raw=AMIRES,   pipe=P_orth_rz,          env=SLCOM,
                        ref=U+"/r2_factor/out/SL2_ORTH_AMIRESID__p.npz"),
 "ORTH_AMI3D":     dict(raw=AMI3D,    pipe=P_orth_rz,          env=SLCOM,
                        ref=U+"/r2_horizon/out/C_AMI3D__p.npz"),
 "LOBDEPTH_ORTH":  dict(raw=-LOBD,    pipe=P_orth_rz,          env=SLCOM, ref=None),
 "LOBDEPTH_RAW":   dict(raw=-LOBD,    pipe=P_ident,            env=SLCOM,
                        ref=U+"/trackD_v4/SL_LOBDEPTH__m.npz"),
 "TBF_ema08":      dict(raw=TBF,      pipe=P_orth_ema8_rz_lag, env=SLCOM,
                        ref=U+"/r2_sleeve/out/TBF_ema08.npz"),
 "ORTH_LISTEVT":   dict(raw=LISTEV,   pipe=P_orth_rz,          env=SLCOM,
                        ref=U+"/event_state/arms/SL_ORTH_LISTEVT__p.npz"),
 "ORTH_RESSKEW":   dict(raw=-RESSKW,  pipe=P_orth_rz,          env=SLCOM,
                        ref=U+"/r2_factor/out/SL2_ORTH_RESSKEW__m.npz"),
 "RESID_SHARPE":   dict(raw=RS42,     pipe=P_ident,            env=SLCOM,
                        ref=U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz"),
 "RESID_SHARPE_s2027": dict(raw=RS2027, pipe=P_ident,          env=SLCOM,
                        ref=U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_STD.npz"),
 # --- in-book blends (LEGS=101 PHI=0.45 FTRIM=zero): fund score = mix of ZF and the sleeve
 "XIB_LAG50_s42":  dict(raw=AMI, pipe=lambda X: 0.5*ZF + 0.5*P_orth_rz_lag(X), env=IB(42),
                        ref=U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s42.npz"),
 "XIB_LAG50_s2027":dict(raw=AMI, pipe=lambda X: 0.5*ZF + 0.5*P_orth_rz_lag(X), env=IB(2027),
                        ref=U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s2027.npz"),
 "IB_TRI_B_s42":   dict(raw=AMI, raw2=F6,
                        pipe=lambda X, X2: 0.34*ZF + 0.33*lag1(rz(M(X)), BASE) + 0.33*rz(M(X2)),
                        env=IB(42), ref=None),
}
# paired in-book baseline (fund leg untouched) -- no null, run once
BASELINE = {"IB_PARITY_s42": dict(mat=ZF, env=IB(42)),
            "IB_PARITY_s2027": dict(mat=ZF, env=IB(2027))}

# ---------------------------------------------------------------- runner
def run(tag, mat, env):
    p = OUT + "/" + tag + ".npz"
    if os.path.exists(p):
        return tag + " skip"
    f = D + "/sig/" + tag + ".npz"
    np.savez(f, symbols=SYM, ts=TS, mat=np.asarray(mat, np.float32))
    e = dict(os.environ); e.update(OMP_NUM_THREADS="3", OPENBLAS_NUM_THREADS="3", MKL_NUM_THREADS="3")
    cmd = ["env"] + env + ["FEMAT_NPZ=" + f, "OUT_TAG=" + tag, "/workspace/venv/bin/python", DEV]
    with open(D + "/logs/" + tag + ".log", "w") as lf:
        rc = subprocess.call(cmd, cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=e)
    src = D + "/probe_artifacts/w10_ablation_series_" + tag + ".npz"
    if rc != 0 or not os.path.exists(src):
        return "FAIL %s rc=%s" % (tag, rc)
    Z = np.load(src, allow_pickle=True)
    np.savez_compressed(p, cols=Z["cols"], rec=Z["d30_n2_c42_rec"], config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    for ex in (D + "/probe_artifacts/w10_ablation_summary_" + tag + ".json",):
        if os.path.exists(ex): os.remove(ex)
    return tag + " ok"


def jobs_for(arm, null_tags):
    """The null is applied to EVERY raw feature the arm consumes, through the arm's own
    downstream pipeline. The fund-leg reference ZF inside an in-book blend is NOT nulled --
    that half is the live book and must stay itself, so the placebo tests the SLEEVE only."""
    s = ARMS[arm]
    r2 = s.get("raw2")
    call = (lambda *a: s["pipe"](*a))
    out = [("%s__REAL" % arm, call(s["raw"]) if r2 is None else call(s["raw"], r2), s["env"])]
    for nt in null_tags:
        Xn = NULLS[nt](np.asarray(s["raw"], float))
        if r2 is None:
            out.append(("%s__%s" % (arm, nt), call(Xn), s["env"]))
        else:
            X2n = NULLS[nt](np.asarray(r2, float))
            out.append(("%s__%s" % (arm, nt), call(Xn, X2n), s["env"]))
    return out


def avail_report(arm, null_tags):
    s = ARMS[arm]; X = np.asarray(s["raw"], float)
    rep = {}
    for nt in null_tags:
        rep[nt] = availability_receipt(X, NULLS[nt](X))
    return rep


if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    batch = sys.argv[1] if len(sys.argv) > 1 else "calib"
    t0 = time.time()
    if batch == "calib":
        NT = ["R1", "O1", "T1", "P1"]
        J = jobs_for("AMI_lag", NT)
        json.dump(avail_report("AMI_lag", NT), open(R + "/AVAIL_calib.json", "w"), indent=1)
    else:
        NT = ["R1", "R2", "R3", "O1", "O2", "T1", "T2", "T3", "P1"]
        if batch in ("standalone", "all"):
            names = [k for k in ARMS if ARMS[k]["env"] is SLCOM]
        else:
            names = []
        if batch in ("inbook", "all"):
            names += [k for k in ARMS if ARMS[k]["env"] is not SLCOM]
        J = []
        for k in names:
            J += jobs_for(k, NT)
        if batch in ("inbook", "all"):
            for k, v in BASELINE.items():
                J.append((k, v["mat"], v["env"]))
        AV = {k: avail_report(k, NT) for k in names}
        json.dump(AV, open(R + "/AVAIL_%s.json" % batch, "w"), indent=1)
    print("jobs", len(J), flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(lambda j: run(*j), J):
            print("%-40s %6.0fs" % (r, time.time() - t0), flush=True)
    print("BATCH_DONE", batch, round(time.time() - t0, 1))
