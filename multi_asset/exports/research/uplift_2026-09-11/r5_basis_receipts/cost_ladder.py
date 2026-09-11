"""R5/ND1: how much of the basis sleeve is eaten by COST? Same signal, three cost models."""
import numpy as np, os, subprocess, json, hashlib, time
R="/workspace/uplift_2026-09-11/r5_basis"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
CB={"ZEROISH":HC+"/calib/costb_fee_steady.json",
    "PWR230k":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json",
    "PWR2300k":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G2300k.json"}
CB={k:v for k,v in CB.items() if os.path.exists(v)}
ENV=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
     "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
     "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
sig=R+"/dev/sig/R5_FBSLOPE_NOLAG.npz"
def run(j):
    nm,cb=j; tag="R5C_FBSLOPE_NOLAG_"+nm
    dst=R+"/arms/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+ENV+["COSTB_JSON="+cb,"FEMAT_NPZ="+sig,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL "+tag
    Z=np.load(src,allow_pickle=True); np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"]); os.remove(src)
    return tag+" ok"
from concurrent.futures import ThreadPoolExecutor
print("cost models:",list(CB))
with ThreadPoolExecutor(max_workers=3) as ex:
    for r in ex.map(run,list(CB.items())): print(r,flush=True)
