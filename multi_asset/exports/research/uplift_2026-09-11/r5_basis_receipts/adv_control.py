"""R5/ND1 LOOKAHEAD POSITIVE CONTROLS at the BOOK layer (closes the hole that my IC-space ADV1 was
identically k=-1 and therefore no control at all).
  PERFECT : score = y4 itself (the return the book is about to earn). Calibrates the instrument ceiling.
  ADV1    : the real BSLOPE signal read one anchor LATE, computed from bars through E+3h = three of the
            four hours of the return window. Graded, realistic leakage. Both signs run."""
import numpy as np, os, subprocess
R="/workspace/uplift_2026-09-11/r5_basis"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"],float)
emap={int(t):i for i,t in enumerate(E)}
P=np.full((len(ts),len(sym)),np.nan)
for i,t in enumerate(ts):
    j=emap.get(int(t))
    if j is not None: P[i]=y4[j]
np.savez(D+"/sig/R5_PERFECT.npz",symbols=sym,ts=ts,mat=P.astype(np.float32))
Z=np.load(D+"/sig/R5_BSLOPE_NOLAG.npz",allow_pickle=True); M=np.asarray(Z["mat"],float)
A=np.full_like(M,np.nan); A[:-1]=M[1:]
np.savez(D+"/sig/R5_ADV1.npz",symbols=sym,ts=ts,mat=A.astype(np.float32))
np.savez(D+"/sig/R5_FADV1.npz",symbols=sym,ts=ts,mat=(-A).astype(np.float32))
ENV=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
     "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
     "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy","FSEED=42","FPRED=f10_A0_s42.npy",
     "COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"]
def run(tag):
    dst=R+"/arms/R5_%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+ENV+["FEMAT_NPZ=%s/sig/R5_%s.npz"%(D,tag),"OUT_TAG=R5_"+tag,"/workspace/venv/bin/python",DEV]
    with open(D+"/logs/R5_%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_R5_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL "+tag
    Zz=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Zz["cols"],rec=Zz["d30_n2_c42_rec"],config_json=Zz["config_json"]); os.remove(src)
    return tag+" ok"
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=3) as ex:
    for r in ex.map(run,["PERFECT","ADV1","FADV1"]): print(r,flush=True)
