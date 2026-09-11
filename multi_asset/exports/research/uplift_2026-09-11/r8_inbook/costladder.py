"""R8 cost ladder: the same in-book arm priced at near-zero fees, the fitted live-scale model, and the
10x-book model.  Round 5 showed the STANDALONE sleeve goes net-negative at 10x (cost 109.8% of gross).
Question: does in-book netting remove that capacity ceiling?"""
import numpy as np, os, subprocess, time, json, hashlib, sys
R="/workspace/uplift_2026-09-11/r8_inbook"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
assert hashlib.sha256(open(DEV,"rb").read()).hexdigest()[:16]=="b88e35a46b93d712"
COSTS={"ZEROISH":HC+"/calib/costb_fee_steady.json","PWR230k":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json",
       "PWR2300k":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G2300k.json"}
BASE=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
      "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
MAN=json.load(open(R+"/SIG_MANIFEST.json"))
jobs=[]
for cn,cp in COSTS.items():
    for arm in ("R8A_BLEND_010","R8C_GT_025","R8Z_IDENT"):
        jobs.append(("CL_%s_%s"%(arm,cn),MAN[arm]["path"],cp))
    jobs.append(("CL_A0_%s"%cn,None,cp))
def run(j):
    tag,sig,cp=j
    dst=R+"/arms/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    e=list(BASE)+["COSTB_JSON="+cp]+(["FEMAT_NPZ="+sig] if sig else [])
    cmd=["env"]+e+["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL "+tag
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src); return tag+" ok"
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(run,jobs): print(r,flush=True)
print("CL_RUNS_DONE")
