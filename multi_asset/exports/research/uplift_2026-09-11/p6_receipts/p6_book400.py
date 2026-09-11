"""P6 step 3: the LIVE universe width. shadow_bundle/config.json params NTOP=400 (live) vs MEMBERS_TOPN=829 (replay).
Same device, same signals as p6_book.py; only MEMBERS_TOPN changes. Amihud is an ILLIQUIDITY factor, so where its
P&L sits in the liquidity cross-section decides whether the live book can trade it at all."""
import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/p6")
import os, subprocess, time, hashlib
R="/workspace/uplift_2026-09-11/p6"; D=R+"/dev"; OUT=R+"/arms"
HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COMMON=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
CBP="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def run(job):
    arm,seed,topn=job
    tag="P6_%s_PWR%d_s%s"%(arm,topn,seed)
    dst="%s/w10_ablation_series_%s.npz"%(OUT,tag)
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+COMMON+["MEMBERS_TOPN=%d"%topn,"FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+CBP,
                        "FEMAT_NPZ="+D+"/sig/SL_%s.npz"%arm,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open("%s/logs/%s.log"%(D,tag),"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src="%s/probe_artifacts/w10_ablation_series_%s.npz"%(D,tag)
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    os.replace(src,dst)
    return "%-26s ok %5.1fs sha %s"%(tag,time.time()-t,hashlib.sha256(open(dst,"rb").read()).hexdigest()[:16])
from concurrent.futures import ThreadPoolExecutor
jobs=[(a,s,n) for a in ("AMQ64","AMX") for s in ("42","2027") for n in (400,600)]
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(run,jobs): print(r,flush=True)
print("P6_BOOK400_DONE")
