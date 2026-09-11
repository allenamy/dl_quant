"""R5/ND1 step 3: run the standalone sleeve for every declared arm. Device UNMODIFIED (b88e35a4...).
ENV whitelist asserted and recorded. LEGS=001 PHI=0 -> standalone: FSEED/FPRED are inert (device only
loads F10 when PHI>0), so arms are seed-independent; recorded anyway."""
import numpy as np, os, subprocess, time, json, hashlib, sys
R="/workspace/uplift_2026-09-11/r5_basis"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
assert hashlib.sha256(open(DEV,"rb").read()).hexdigest()[:16]=="b88e35a46b93d712"
COSTB_PWR="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(COSTB_PWR,"rb").read()).hexdigest()[:16]=="295b4e7b462373e4"
ENV_SL=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy",
        "FSEED=42","FPRED=f10_A0_s42.npy","COSTB_JSON="+COSTB_PWR]
os.makedirs(R+"/arms",exist_ok=True)
def run(job):
    tag,sig=job
    dst=R+"/arms/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+ENV_SL+["FEMAT_NPZ="+sig,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src)
    return "%-22s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    jobs=[]
    if len(sys.argv)>1 and sys.argv[1]=="nulls":
        MAN=json.load(open(R+"/NULL_MANIFEST.json"))
        jobs=[(k,v) for k,v in MAN.items()]
    else:
        MAN=json.load(open(R+"/SIG_MANIFEST.json"))
        jobs=[("R5_"+k,v["path"]) for k,v in MAN.items()]
    json.dump({"ENV":ENV_SL,"device":DEV,"jobs":dict(jobs)},open(R+"/RUN_ENV_%s.json"%(sys.argv[1] if len(sys.argv)>1 else "arms"),"w"),indent=1)
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(run,jobs): print(r,"%.0fs"%(time.time()-t0),flush=True)
    print("DRIVE_DONE")
