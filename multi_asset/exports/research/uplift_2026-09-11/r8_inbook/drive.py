"""R8/BUILD-1 step 3: run each in-book arm as ONE BOOK (A0 cell, FEMAT injection).
Device UNMODIFIED (b88e35a4...).  ENV whitelist asserted and recorded (E-0826-D)."""
import numpy as np, os, subprocess, time, json, hashlib, sys
R="/workspace/uplift_2026-09-11/r8_inbook"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
assert hashlib.sha256(open(DEV,"rb").read()).hexdigest()[:16]=="b88e35a46b93d712"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(COSTB,"rb").read()).hexdigest()[:16]=="295b4e7b462373e4"
BASE=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
      "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","COSTB_JSON="+COSTB]
os.makedirs(R+"/arms",exist_ok=True); os.makedirs(D+"/logs",exist_ok=True)
def run(job):
    tag,sig,seat,sd=job
    dst=R+"/arms/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    e=list(BASE)+["FSEED=%d"%sd,"FPRED=f10_A0_s%d.npy"%sd]
    if seat=="fix": e.append("W3FIX=0.21,0,0.79")
    if sig: e.append("FEMAT_NPZ="+sig)
    cmd=["env"]+e+["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src)
    ENVLOG[tag]=" ".join(cmd)
    return "%-26s ok %5.1fs"%(tag,time.time()-t)
ENVLOG={}
if __name__=="__main__":
    which=sys.argv[1] if len(sys.argv)>1 else "main"
    MAN=json.load(open(R+"/SIG_MANIFEST.json"))
    jobs=[]
    if which=="main":      # primary cell: dyn seat, s42
        for k,v in MAN.items(): jobs.append((k+"_dyn_s42",v["path"],"dyn",42))
        jobs.append(("R8_A0_dyn_s42",None,"dyn",42))
    elif which=="second":  # secondary cells for survivors, arm list from argv[2:]
        for k in sys.argv[2:]:
            for seat,sd in (("dyn",2027),("fix",42),("fix",2027)):
                jobs.append(("%s_%s_s%d"%(k,seat,sd),MAN[k]["path"] if k in MAN else None,seat,sd))
        for seat,sd in (("dyn",2027),("fix",42),("fix",2027)):
            jobs.append(("R8_A0_%s_s%d"%(seat,sd),None,seat,sd))
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(run,jobs): print(r,"%.0fs"%(time.time()-t0),flush=True)
    old={}
    if os.path.exists(R+"/R8_RUN_ENV.json"): old=json.load(open(R+"/R8_RUN_ENV.json"))
    old.update(ENVLOG); old["_BASE"]=BASE; old["_device"]=DEV
    json.dump(old,open(R+"/R8_RUN_ENV.json","w"),indent=1)
    print("DRIVE_DONE")
