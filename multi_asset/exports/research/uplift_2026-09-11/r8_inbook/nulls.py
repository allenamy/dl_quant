"""R8/BUILD-1 turnover-matched NULLS.  Construction copied VERBATIM from
/workspace/uplift_2026-09-11/r3_attack_b9646/null.py (sha 91d4c91cb92a6440):
  RELAB_k : ONE fixed symbol permutation applied at every anchor, rng default_rng([4242,k]), k=1,2,3
  SHIFT_k : the whole score matrix advanced by k anchors, k=101,503,1009
Applied to the TILT COMPONENT only (the thing under test), never to the live fund score ZF, so the
null arm is the SAME in-book construction driven by a null basis.  Gates G_T/G_H are recomputed from
the nullified tilt (the whole rule is nullified, not just its input)."""
import numpy as np, os, json, sys, hashlib, subprocess, time
R="/workspace/uplift_2026-09-11/r8_inbook"; D=R+"/dev"; HC="/workspace/review_scratch/health_check"
P=np.load(R+"/parts.npz",allow_pickle=True)
ts=P["ts"].astype(np.int64); sym=P["symbols"]; ZF=np.asarray(P["ZF"],float); ZB=np.asarray(P["ZB"],float)
ORTHF=np.asarray(P["ORTHF"],float); BM=np.asarray(P["BM"],bool)
A0=np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz",allow_pickle=True)
W=np.asarray(A0["W"],float); TR=np.zeros_like(W); TR[1:]=W[1:]-W[:-1]; TR[0]=W[0]
ZBF=np.where(np.isfinite(ZB),-ZB,np.nan)
def nullify(M,kind,k):
    if kind=="RELAB":
        rng=np.random.default_rng([4242,k]); pi=rng.permutation(M.shape[1]); return M[:,pi]
    Q=np.full_like(M,np.nan); Q[k:]=M[:-k]; return Q
def build(tag_arm,kind,k):
    if tag_arm.startswith("R8A_BLEND"):
        a=int(tag_arm.split("_")[-1])/100.0
        Zn=nullify(ZBF,kind,k); Zn=np.where(np.isfinite(Zn),Zn,ZF)
        M=(1-a)*ZF+a*Zn
    elif tag_arm.startswith("R8B_OVL"):
        c=int(tag_arm.split("_")[-1])/100.0
        On=np.nan_to_num(nullify(ORTHF,kind,k)); M=ZF+c*On
    elif tag_arm.startswith("R8C_GT"):
        c=int(tag_arm.split("_")[-1])/100.0
        On=np.nan_to_num(nullify(ORTHF,kind,k))
        G=((np.sign(On)==np.sign(TR))&(np.abs(TR)>0)).astype(float)
        M=ZF+c*On*G
    else: raise SystemExit("unknown arm "+tag_arm)
    return np.where(BM,M,np.nan)
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
assert hashlib.sha256(open(DEV,"rb").read()).hexdigest()[:16]=="b88e35a46b93d712"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
BASE=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
      "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","COSTB_JSON="+COSTB,
      "FSEED=42","FPRED=f10_A0_s42.npy"]
def run(job):
    tag,f=job
    dst=R+"/arms/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+BASE+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src); return "%-34s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    ARMS=sys.argv[1:]
    jobs=[]; MAN={}
    for A in ARMS:
        for kind,k in (("RELAB",1),("RELAB",2),("RELAB",3),("SHIFT",101),("SHIFT",503),("SHIFT",1009)):
            tg="%s_NULL_%s%d_dyn_s42"%(A,kind,k)
            M=build(A,kind,k); p=D+"/sig/%s.npz"%tg
            np.savez(p,symbols=sym,ts=ts,mat=M.astype(np.float32))
            MAN[tg]=p; jobs.append((tg,p))
    json.dump(MAN,open(R+"/NULL_MANIFEST.json","w"),indent=1)
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(run,jobs): print(r,"%.0fs"%(time.time()-t0),flush=True)
    print("NULLS_DONE")
