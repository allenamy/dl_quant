"""R5 NEW-DATA-4 driver. LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<injected price-space score>
=> standalone fund-leg-shaped book on the injected score. Cost = the FITTED PWR G230k model.
Env whitelist asserted verbatim below (E-0826-D)."""
import numpy as np, os, sys, subprocess, time, json
HC="/workspace/review_scratch/health_check"; R="/workspace/uplift_2026-09-11/r5_lob"
D=R+"/dev"; OUT=R+"/out"; FEAT=R+"/feat"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
for d in (OUT,D+"/logs",D+"/sig"): os.makedirs(d,exist_ok=True)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
from scipy.stats import rankdata
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
def orth(Z):
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        "UMASK_NPZ=%s/masks/umask_UPIT_CRYPTO.npz"%HC,"COSTB_JSON="+COSTB,
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
ENV_WHITELIST=COMMON+["LEGS=001","PHI=0","FTRIM=off","FEMAT_NPZ=<per-arm>","OUT_TAG=<per-arm>",
                      "OMP_NUM_THREADS=3","OPENBLAS_NUM_THREADS=3","MKL_NUM_THREADS=3"]
def run(tag,f):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off","FEMAT_NPZ="+f,"OUT_TAG="+tag,
         "/workspace/venv/bin/python",DEV]
    with open(R+"/commands.txt","a") as cf: cf.write("CMD[%s] (cwd=%s) %s\n"%(tag,D," ".join(cmd)))
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/%s.npz"%tag,cols=A["cols"],rec=A["d30_n2_c42_rec"],config_json=A["config_json"])
    os.remove(src); return True
def getfeat(nm):
    z=np.load("%s/%s.npz"%(FEAT,nm),allow_pickle=True)
    assert np.array_equal(z["ts"].astype(np.int64),ts) and [str(x) for x in z["symbols"]]==[str(x) for x in sym],nm
    return np.asarray(z["mat"],np.float64)
if __name__=="__main__":
    jobs=json.load(open(sys.argv[1])); t0=time.time()
    print("ENV_WHITELIST "+json.dumps(ENV_WHITELIST),flush=True)
    for j in jobs:
        tag=j["tag"]
        if os.path.exists(OUT+"/%s.npz"%tag): print("skip",tag,flush=True); continue
        if j.get("feat"):
            M=np.where(BASE,getfeat(j["feat"]),np.nan)
            if j["kind"]=="orth": M=orth(rz(M))
            elif j["kind"]=="raw": M=rz(M)
            else: raise SystemExit("kind "+j["kind"])
            # turnover-matched nulls, construction copied verbatim from r3_attack_b9646/null.py
            if j.get("null","").startswith("RELAB"):
                rng=np.random.default_rng([4242,int(j["null"][5:])]); M=M[:,rng.permutation(M.shape[1])]
            elif j.get("null","").startswith("SHIFT"):
                k=int(j["null"][5:]); Q=np.full_like(M,np.nan); Q[k:]=M[:-k]; M=Q
            S=float(j["sgn"])*M
        f=D+"/sig/%s.npz"%tag
        np.savez(f,symbols=sym,ts=ts,mat=np.asarray(S,np.float32))
        ok=run(tag,f); os.remove(f)
        print("%-30s %s %6.1fs"%(tag,"ok" if ok else "FAIL",time.time()-t0),flush=True)
    print("BATCH DONE",time.time()-t0,flush=True)
