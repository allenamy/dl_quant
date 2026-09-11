import numpy as np, os, subprocess, time, hashlib
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r2_horizon"; HC="/workspace/review_scratch/health_check"
PB=HC+"/dev_v4/pod_backup_2026-08-21"
PW=np.load(PB+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],np.float64)
BASE=np.isfinite(FE1)                      # the device rank base, per row
def xz(v):                                  # EXACT copy of the device xz()
    out=np.full(len(v),np.nan); ok=np.isfinite(v)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def ZR(M):                                  # device-identical per-row rank, restricted to BASE
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=np.where(BASE[i],M[i],np.nan); out[i]=xz(v)
    return out
ZF=ZR(FE1)                                  # deployed fund-leg rank
def fill(M):
    """finite pattern must equal BASE exactly (so the device rank base is unchanged);
    names in BASE with no feature value get the row mean of the valid residuals (= neutral)."""
    out=np.full(M.shape,np.nan)
    nf=0
    for i in range(M.shape[0]):
        b=BASE[i]
        if b.sum()<10: continue
        v=M[i].copy(); ok=b&np.isfinite(v)
        if ok.sum()<10: continue
        mu=v[ok].mean()
        row=np.where(b, np.where(np.isfinite(v),v,mu), np.nan)
        out[i]=row; nf+=int((b&~np.isfinite(v)).sum())
    return out,nf
def orth(Z):
    """per-anchor cross-sectional orthogonalisation of rank(Z) against ZF, then centre."""
    Zr=ZR(Z); Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Zr[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Zr[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        r=y-b*x; Rr[i][ok]=r-r.mean()
    return Rr
UP=HC+"/masks/umask_UPIT_CRYPTO.npz"; CB=HC+"/calib/costb_fee_steady.json"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+UP,"COSTB_JSON="+CB,"SLOW_NPY="+K3]
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+UP,"COSTB_JSON="+CB,"SLOW_NPY="+K3,"FSEED=42","FPRED=f10_A0_s42.npy"]
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
def run(tag,M,common,extra=None,keepW=False):
    o=R+"/out/"+tag+".npz"
    if os.path.exists(o): return "skip"
    f=R+"/dev/sig/"+tag+".npz"
    np.savez(f,symbols=SYM,ts=TS,mat=np.asarray(M,np.float64))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+common+(extra or [])+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(R+"/dev/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=R+"/dev",stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=R+"/pa/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src):
        print("FAIL",tag,rc,flush=True); return "fail"
    Z=np.load(src,allow_pickle=True)
    d=dict(cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    if keepW: d["W"]=Z["d30_n2_c42_W"]
    np.savez_compressed(o,**d)
    os.remove(src); os.remove(f)
    print("%-18s ok %5.1fs"%(tag,time.time()-t),flush=True)
    return "ok"
