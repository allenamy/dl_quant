"""r10 SLOW_CLOCK STEP 3: re-price the 13 rho-selected signed horizon arms at the PINNED fitted cost
costb_PWR_G230k.json. Device w10_sleeve.py UNMODIFIED (sha b88e35a4...). Signals rebuilt VERBATIM from
r2_horizon/drive_ABCD.py + drive_EXT.py. Also emits COMBO_S = equal-weight blend of the same 13 signed
orthogonalised residuals (one book), for the null battery."""
import numpy as np, sys, os, json, hashlib, time, subprocess
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ",
 "COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON",
 "PANEL_IN","JUDGE_HC","TILT","TILT_TAU","TILT_K"]
assert not [k for k in ENV_WL if k in os.environ], [k for k in ENV_WL if k in os.environ]
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *              # PW, TS, SYM, BASE, ZF, ZR, xz, fill, orth, SLCOM, DEV, R
W10="/workspace/uplift_2026-09-11/r10_slowclock"
CB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
SL=[x for x in SLCOM if not x.startswith("COSTB_JSON")]+["COSTB_JSON="+CB]
F1=np.load(R+"/feats_r2.npz",allow_pickle=True); F2=np.load(R+"/feats_r2b.npz",allow_pickle=True)
assert np.array_equal(F1["ts"].astype(np.int64),TS) and np.array_equal(F2["ts"].astype(np.int64),TS)
g1=lambda k: np.asarray(F1[k],np.float64); g2=lambda k: np.asarray(F2[k],np.float64)
IVf=np.where(np.isfinite(PW["f_fund_iv"])&(np.asarray(PW["f_fund_iv"])>0),np.asarray(PW["f_fund_iv"],np.float64),8.0)
RN8=np.nan_to_num(np.asarray(PW["f_fund_now"],np.float64),nan=0.0)*(8.0/IVf)
RN8=np.where(np.isfinite(np.asarray(PW["f_fund_now"])),RN8,np.nan)
FE2=np.asarray(PW["f_fund_ema_v2"],np.float64)
def lagrank(Z,L):
    o=np.full(Z.shape,np.nan); o[L:]=Z[:-L]; return o
ZRN=ZR(RN8); ZFE2=ZR(FE2)
RAW={
 "A_REV1H":  -g1("RET_SUM_12"),        "A_VOL1H":  g1("RET_MSQ_12"),
 "A_TBF1H":   g1("TBF_MEAN_12"),       "A_QVS1H":  g1("LQV_MEAN_12")-g1("LQV_MEAN_288"),
 "B_REV12H": -g1("RET_SUM_144"),       "B_TBF12H": g1("TBF_MEAN_144"),
 "C_TBF3D":   g1("TBF_MEAN_864"),
 "C_TBF7D":   g2("TBF_MEAN_2016"),     "C_TBF14D": g2("TBF_MEAN_4032"), "C_TBF30D": g2("TBF_MEAN_8640"),
 "D_FCHG12H": ZRN-lagrank(ZRN,3),      "D_FCHG3D": ZRN-lagrank(ZRN,18), "D_FSLOPE": ZF-ZFE2,
}
SIGN=json.load(open(W10+"/rc/S12.json"))["S4_step4_sign_from_TRAIN_mean_g_only"]
assert sorted(SIGN)==sorted(RAW), (sorted(SIGN),sorted(RAW))
ORTH={nm:orth(X) for nm,X in RAW.items()}
SGN={nm:(1.0 if SIGN[nm]=="__p" else -1.0) for nm in RAW}
BL=np.zeros(ZF.shape); CNT=np.zeros(ZF.shape)
for nm,O in ORTH.items():
    S=SGN[nm]*O; ok=np.isfinite(S); BL[ok]+=S[ok]; CNT[ok]+=1
BLEND=np.where(CNT>0,BL/np.maximum(CNT,1),np.nan)
JOBS=[]
for nm in RAW:
    M,_=fill(SGN[nm]*ORTH[nm]); JOBS.append(("PWR_"+nm+SIGN[nm],M))
M,_=fill(BLEND); JOBS.append(("PWR_COMBO_S",M))
def run(a):
    tag,M=a
    dst=W10+"/out/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    f=W10+"/dev/sig/%s.npz"%tag
    np.savez(f,symbols=SYM,ts=TS,mat=np.asarray(M,np.float64))
    env={k:v for k,v in os.environ.items() if k not in ENV_WL}
    env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+SL+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(W10+"/dev/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=W10+"/dev",stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=W10+"/dev/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    return "%-24s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    from multiprocessing import Pool
    print("jobs",len(JOBS),"COSTB",CB,flush=True)
    with Pool(7) as p:
        for r in p.imap_unordered(run,JOBS): print(r,flush=True)
    print("REPRICE_DONE")
