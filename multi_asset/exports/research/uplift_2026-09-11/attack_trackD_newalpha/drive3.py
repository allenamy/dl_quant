import numpy as np, os, subprocess, time
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
ZF=rz(np.where(B,FE1,np.nan)); ZA=rz(np.where(B,AM,np.nan))
def orth(Z):
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    return R
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag,M,costb):
    if os.path.exists(OUT+"/"+tag+".npz"): print("skip",tag,flush=True); return
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    cmd=["env"]+SLCOM+["COSTB_JSON="+costb,"FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",HC+"/w10_health.py"]
    t=time.time()
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); os.remove(f); return
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f); print("%-20s ok %5.1fs"%(tag,time.time()-t),flush=True)
run("XSL_ORTH_ILLQ",orth(ZA),A+"/costb_illiq.json")
run("XSL_ORTH_STD",orth(ZA),HC+"/calib/costb_fee_steady.json")
print("DONE3")
