#!/usr/bin/env python3
"""INFRA-1 step 6: re-price the round-1 Amihud family under the honest cost models.
Device = w10_health.py (sha 8684d9a9...), UNMODIFIED. Only COSTB_JSON changes.
Signal construction copied VERBATIM from attack_trackD_newalpha/drive.py (same rng seed 20260911)."""
import numpy as np, os, subprocess, time, sys, json, hashlib
from concurrent.futures import ThreadPoolExecutor
HC="/workspace/review_scratch/health_check"; A="/workspace/uplift_2026-09-11/infra1_cost"
D=A+"/dev"; OUT=A+"/out"
for d in (D+"/sig", D+"/logs", OUT, "/tmp/pa_infra1"): os.makedirs(d, exist_ok=True)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
AM=np.asarray(PW["f_amihud_24h"],float)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan)); ZA=rz(np.where(B,AM,np.nan))
ZA_LAG=np.full_like(ZA,np.nan); ZA_LAG[1:]=ZA[:-1]; ZA_LAG=np.where(B,ZA_LAG,np.nan)
rng=np.random.default_rng(20260911)
ZP=np.full_like(ZA,np.nan)
for i in range(ZA.shape[0]):
    ok=np.isfinite(ZA[i]); n=ok.sum()
    if n>=10:
        v=ZA[i,ok].copy(); rng.shuffle(v); ZP[i,ok]=v
def orth(Z):
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    return R
SIG={"PAR":ZF, "AM50":0.5*ZF+0.5*ZA, "LAG50":0.5*ZF+0.5*ZA_LAG, "D60":0.4*ZF+0.6*ZA,
     "PERM50":0.5*ZF+0.5*rz(ZP)}
SLSIG={"ORTHLAG":orth(ZA_LAG), "ORTHPERM":orth(rz(ZP)), "AMLAG":ZA_LAG}
COSTB={"STD":HC+"/calib/costb_fee_steady.json"}
for tag in ("H0","H05","H1","H15","H2","H225","H25","H275","H3","H4","H5","H6","X1","X15","X2","X25","X3"): COSTB[tag]=A+f"/costb_honest_{tag}.json"
def common(kind,seed):
    if kind=="IB":
        return ["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
          "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
          "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy",f"FSEED={seed}",f"FPRED=f10_A0_s{seed}.npy"]
    return ["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
      "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(job):
    kind,arm,cb,seed=job
    tag=f"{kind}_{arm}_{cb}_s{seed}"
    if os.path.exists(OUT+"/"+tag+".npz"): return tag+" skip"
    M=(SIG if kind=="IB" else SLSIG)[arm]
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+common(kind,seed)+["COSTB_JSON="+COSTB[cb],"FEMAT_NPZ="+f,"OUT_TAG="+tag,
         "/workspace/venv/bin/python",HC+"/w10_health.py"]
    t=time.time()
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src):
        os.remove(f); return f"FAIL {tag} rc={rc}"
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    return "%-34s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "gate"
    if mode=="gate":
        jobs=[("IB","PAR","STD",42),("IB","LAG50","STD",42)]
    elif mode=="main":
        CB=["H0","H05","H1","H15","H2","H3","H4","H6"]
        jobs=[("IB",a,c,42) for a in ("PAR","AM50","LAG50","D60","PERM50") for c in CB]
        jobs+=[("SL",a,c,42) for a in ("ORTHLAG","ORTHPERM") for c in ["STD"]+CB]
    elif mode=="fine":
        CB=["H225","H25","H275","H5"]
        jobs=[("IB",a,c,42) for a in ("PAR","LAG50","AM50") for c in CB]
    elif mode=="exec":
        CB=["X1","X15","X2","X25","X3"]
        jobs=[("IB",a,c,s) for s in (42,2027) for a in ("PAR","LAG50") for c in CB]+[("IB","AM50",c,42) for c in CB]+[("SL","ORTHLAG",c,42) for c in CB]
    elif mode=="seed2":
        jobs=[("IB",a,c,2027) for a in ("PAR","LAG50") for c in ("STD","H0","H1","H2","H3","H4","H6")]
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    print("DONE",mode)
