"""P3 step 1b: rebuild the standalone orthogonalised Amihud sleeve with the DEVICE'S OWN ranker
(infra2/xib_signal.RZ = scipy rankdata AVERAGE), closing the argsort-ranking caliber hole in the
round-1 sleeve builder rather than asserting it is immaterial. Cost = fitted PWR G230k."""
import numpy as np, os, subprocess, time, sys, hashlib
sys.path.insert(0,"/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, save
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"
R=U+"/r4p3"; D=R+"/dev"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1); AM=np.asarray(PW["f_amihud_24h"],float)
ZF=RZ(FE1,B); ZA=RZ(AM,B)
ZA_LAG=np.full_like(ZA,np.nan); ZA_LAG[1:]=ZA[:-1]; ZA_LAG=np.where(B,ZA_LAG,np.nan)
Rm=np.full(ZA.shape,np.nan)
for i in range(ZA.shape[0]):
    ok=np.isfinite(ZA_LAG[i])&np.isfinite(ZF[i])
    if ok.sum()<10: continue
    x=ZF[i][ok]; y=ZA_LAG[i][ok]; vx=float((x*x).sum())
    b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
    Rm[i][ok]=y-b*x
tag="SL_ORTHLAG_RZ_PWR230k_s42"
f=D+"/sig/"+tag+".npz"; save(f,sym,ts,Rm)
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
cmd=["env"]+SLCOM+["COSTB_JSON="+U+"/r3k/costb_PWR_G230k.json","FEMAT_NPZ="+f,"OUT_TAG="+tag,
     "/workspace/venv/bin/python",U+"/w10_sleeve.py"]
t0=time.time()
with open(D+"/logs/"+tag+".log","w") as lf:
    rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
Z=np.load(src,allow_pickle=True)
np.savez_compressed(R+"/arms/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
os.remove(src)
print("rc",rc,"%.0fs"%(time.time()-t0))
