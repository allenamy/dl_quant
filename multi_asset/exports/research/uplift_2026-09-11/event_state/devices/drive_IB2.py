"""Track G in-book blend arms: A0 config verbatim, fund-leg score -> 0.5*rank(fund)+0.5*rank(feature).
Plus IB_PARITY (inject rank(fund) alone) as the parity receipt."""
import numpy as np, os, sys, subprocess, time
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4ev"
OUT="/workspace/uplift_2026-09-11/event_state/arms_ib2"; os.makedirs(OUT,exist_ok=True)
ES="/workspace/uplift_2026-09-11/event_state"
PW=np.load(f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
F=np.load(f"{ES}/feats_v4.npz",allow_pickle=True)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=int(ok.sum())
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1",f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",
        f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
def run(tag,sigfile,seed):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+[f"FSEED={seed}",f"FPRED=f10_A0_s{seed}.npy",f"FEMAT_NPZ={sigfile}",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python","/workspace/uplift_2026-09-11/w10_sleeve.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],config_json=A["config_json"])
    os.remove(src); return True
t0=time.time()
for spec in sys.argv[1:]:
    nm,seed=spec.split("@")
    if nm=="PARITY": M=ZF.copy()
    else:
        sgn=1.0 if nm.endswith("_p") else -1.0; f=nm[:-2]
        M=0.5*ZF+0.5*sgn*rz(np.where(BASE,np.asarray(F[f],float),np.nan))
    tag=f"IBR_{nm}_s{seed}"
    if os.path.exists(f"{OUT}/{tag}.npz"): print("skip",tag,flush=True); continue
    sf=f"{D}/sig/{tag}.npz"; np.savez(sf,symbols=sym,ts=ts,mat=M.astype(np.float64))
    ok=run(tag,sf,seed); os.remove(sf)
    print("%-30s %s %6.1fs"%(tag,"ok" if ok else "FAIL",time.time()-t0),flush=True)
print("IB_DONE")
