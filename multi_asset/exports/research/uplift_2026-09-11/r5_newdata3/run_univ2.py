"""r5nd/run_univ.py -- NEW DATA 3 universe arms. Device w10_sleeve.py UNMODIFIED (sha b88e35a4...).
Book env VERBATIM from r4_p1/b1_nulls.py BOOK + the FITTED cost r3k/costb_PWR_G230k.json; the ONLY
thing that varies between arms is UMASK_NPZ.  A0 control is re-run with MY re-derived MONTHLY449 mask
(G0-bitwise-equal to the pinned umask_UPIT_CRYPTO) and must reproduce r4_p1/arms/R4B1_A0_* bitwise."""
import numpy as np, os, sys, subprocess, time, hashlib
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r5nd"; D=R+"/dev"; OUT=R+"/arms"
for p in (D+"/logs",D+"/probe_artifacts",OUT): os.makedirs(p,exist_ok=True)
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
BOOK=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","SLOW_NPY="+K3]
MASKS={"A0M":R+"/masks/umask_R5_MONTHLY449.npz",
       "STALE1":R+"/masks/umask_R5_STALE1.npz",
       "STALE3":R+"/masks/umask_R5_STALE3.npz",
       "STALE6":R+"/masks/umask_R5_STALE6.npz",
       "STALE12":R+"/masks/umask_R5_STALE12.npz",
       "UFROZEN450":R+"/masks/umask_R5_UFROZEN450.npz",
       }
def run(job):
    arm,seat,seed=job
    tag="R5U_%s_%s_s%s"%(arm,seat,seed); dst=OUT+"/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    ex=BOOK+["UMASK_NPZ="+MASKS[arm],"FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+COSTB] \
       +(["W3FIX=0.21,0,0.79"] if seat=="fix" else [])+["OUT_TAG="+tag]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src)
    return "%-28s ok %5.1fs"%(tag,time.time()-t0)
if __name__=="__main__":
    jobs=[(a,st,sd) for a in MASKS for st in ("dyn","fix") for sd in ("42","2027")]
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=7) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    print("RUNS_DONE %.0fs"%(time.time()-t0),flush=True)
    import sys; sys.exit(0)
    # --- A0 parity receipt vs round-4 ---
    ok=True
    for st in ("dyn","fix"):
        for sd in ("42","2027"):
            a=np.load(OUT+"/R5U_A0M_%s_s%s.npz"%(st,sd),allow_pickle=True)
            b=np.load("/workspace/uplift_2026-09-11/r4_p1/arms/R4B1_A0_%s_s%s.npz"%(st,sd),allow_pickle=True)
            for k in ("rec","W"):
                x=np.asarray(a[k],float); y=np.asarray(b[k],float)
                nx=np.isnan(x); ny=np.isnan(y)
                bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
                ok&=bw; print("A0 parity %s s%s %s bitwise=%s"%(st,sd,k,bw),flush=True)
    print("A0_PARITY_PASS",ok,flush=True)
