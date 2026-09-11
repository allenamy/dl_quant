"""P6 step 6: the sleeve CAPACITY ladder, same POWER-shape fitted cost jsons round 3 built for A0."""
import os,subprocess,time,hashlib,numpy as np,json,calendar
R="/workspace/uplift_2026-09-11/p6"; D=R+"/dev"; OUT=R+"/arms"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COMMON=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
GS=["230k","460k","920k","1380k","2300k","4600k"]
def run(g):
    tag="P6_AMQ64_G%s_s42"%g
    dst="%s/w10_ablation_series_%s.npz"%(OUT,tag)
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+COMMON+["FSEED=42","FPRED=f10_A0_s42.npy",
         "COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G%s.json"%g,
         "FEMAT_NPZ="+D+"/sig/SL_AMQ64.npz","OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    with open("%s/logs/%s.log"%(D,tag),"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src="%s/probe_artifacts/w10_ablation_series_%s.npz"%(D,tag)
    if rc!=0 or not os.path.exists(src): return "FAIL "+tag
    os.replace(src,dst); return tag+" ok"
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(run,GS): print(r,flush=True)
APY=2190; WARM=900
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1
def sr_of(p,key):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z[key],float)[WARM:]; ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    g=(Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]])[m]
    return float(np.mean(g)/np.std(g,ddof=1)*np.sqrt(APY)), float(g.mean())
TAB={}
print("%-10s %18s %18s"%("G","sleeve SR (g)","A0 SR (g)"))
for g in GS:
    s=sr_of("%s/w10_ablation_series_P6_AMQ64_G%s_s42.npz"%(OUT,g),"d30_n2_c42_rec")
    pa="/workspace/uplift_2026-09-11/r3k/arms/A0_PWR%s_s42.npz"%g
    a=sr_of(pa,"rec") if os.path.exists(pa) else (float("nan"),float("nan"))
    TAB[g]={"sleeve_SR":s[0],"sleeve_g":s[1],"A0_SR":a[0],"A0_g":a[1]}
    print("%-10s %8.4f (%7.4f) %8.4f (%7.4f)"%(g,s[0],s[1],a[0],a[1]))
json.dump(TAB,open(R+"/P6_CAPACITY.json","w"),indent=1)
print("CAP_DONE")
