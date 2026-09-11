"""Adversarial re-runs of Track D: placebos the author did not run, the S7 lag fix, and the mix dose curve.
Same device (w10_health.py sha 8684d9a9...), own mirror tree, own probe_artifacts. dev_v4/dev_v4s untouched."""
import numpy as np, os, subprocess, time, sys
HC="/workspace/review_scratch/health_check"; A="/workspace/uplift_2026-09-11/attack_trackD_newalpha"
D=A+"/dev"; OUT=A+"/out"
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
ZF=rz(np.where(B,FE1,np.nan))
ZA=rz(np.where(B,AM,np.nan))
# lag by one panel row: signal as of the PREVIOUS 4h anchor (24h window ends before the i-1->i bar)
ZA_LAG=np.full_like(ZA,np.nan); ZA_LAG[1:]=ZA[:-1]
ZA_LAG=np.where(B,ZA_LAG,np.nan)
# per-anchor permutation placebo (same marginal, no cross-sectional information)
rng=np.random.default_rng(20260911)
ZP=np.full_like(ZA,np.nan)
for i in range(ZA.shape[0]):
    ok=np.isfinite(ZA[i]); n=ok.sum()
    if n>=10:
        v=ZA[i,ok].copy(); rng.shuffle(v); ZP[i,ok]=v
ZR=rz(np.where(B,np.asarray(PW["f_range_24h"],float),np.nan))
ZV=rz(np.where(B,np.asarray(PW["f_volq_ratio"],float),np.nan))
def orth(Z):
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    return R
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+HC+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+HC+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag,M,common,extra=None):
    if os.path.exists(OUT+"/"+tag+".npz"): print("skip",tag,flush=True); return
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    cmd=["env"]+common+(extra or [])+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",HC+"/w10_health.py"]
    t=time.time()
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); os.remove(f); return
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    print("%-16s ok %5.1fs"%(tag,time.time()-t),flush=True)
JOBS=[]
JOBS.append(("XIB_PARITY",ZF,IBCOM,None))
JOBS.append(("XIB_PERM50",0.5*ZF+0.5*rz(ZP),IBCOM,None))
JOBS.append(("XIB_LAG50",0.5*ZF+0.5*ZA_LAG,IBCOM,None))
JOBS.append(("XIB_RANGE50",0.5*ZF+0.5*ZR,IBCOM,None))
JOBS.append(("XIB_VOLQ50",0.5*ZF+0.5*ZV,IBCOM,None))
for w in [0.1,0.2,0.3,0.4,0.6,0.75,0.9]:
    JOBS.append(("XIB_D%02d"%int(w*100),(1-w)*ZF+w*ZA,IBCOM,None))
JOBS.append(("XSL_ORTHPERM",orth(rz(ZP)),SLCOM,None))
JOBS.append(("XSL_ORTHLAG",orth(ZA_LAG),SLCOM,None))
JOBS.append(("XSL_AMLAG",ZA_LAG,SLCOM,None))
if __name__=="__main__":
    only=sys.argv[1:] 
    for tag,M,com,ex in JOBS:
        if only and not any(o in tag for o in only): continue
        run(tag,M,com,ex)
    print("DONE")
