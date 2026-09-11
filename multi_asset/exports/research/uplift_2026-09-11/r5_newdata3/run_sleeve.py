"""r5nd/run_sleeve.py -- NEW DATA 3 listing-age sleeve arms (in-book FEMAT injection, exactly the
mechanism of inbook.py / r4_p1/b1_nulls.py). Device w10_sleeve.py UNMODIFIED.
Signal builder = infra2/xib_signal.py (device-identical rankdata ranker).
Book env VERBATIM from run_univ.py with UMASK_NPZ = my MONTHLY449 (G0-bitwise = pinned A0 mask).
Usage: python run_sleeve.py base | python run_sleeve.py nulls | python run_sleeve.py solo
"""
import numpy as np, os, sys, subprocess, time, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, blend, save
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r5nd"; D=R+"/dev"; OUT=R+"/arms"; SIG=R+"/sig"
for p in (D+"/logs",D+"/probe_artifacts",OUT,SIG): os.makedirs(p,exist_ok=True)
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
MASK=R+"/masks/umask_R5_MONTHLY449.npz"
BOOK=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+MASK,"SLOW_NPY="+K3]
SOLO=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
      "UMASK_SCOPE=m1","UMASK_NPZ="+MASK,"SLOW_NPY="+K3]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
AG=np.load(R+"/agemat.npz",allow_pickle=True)
assert np.array_equal(AG["ts"].astype(np.int64),ts) and [str(x) for x in AG["symbols"]]==[str(x) for x in sym]
AGE=np.asarray(AG["age_days"],float)
print("cells with finite fund score: %d | of those with finite age: %d (%.5f)"%(
      int(B.sum()), int((B&np.isfinite(AGE)).sum()), float((B&np.isfinite(AGE)).sum()/max(B.sum(),1))),flush=True)
ZF=RZ(FE1,B); ZY=RZ(-AGE,B); AY=2.0*ZY   # ZY in [-0.5,0.5] -> AY in [-1,1]; young = +1
def mk(tag,M): return save(SIG+"/%s.npz"%tag,sym,ts,M)
def femat_mod(a): return np.where(B,ZF*(1.0+a*np.nan_to_num(AY,nan=0.0)),np.nan)
SIGS={}
SIGS["IB_PAR"]=mk("IB_PAR",blend((1.0,ZF)))
SIGS["SL_AGE25"]=mk("SL_AGE25",blend((0.75,ZF),(0.25,ZY)))
SIGS["SL_AGE50"]=mk("SL_AGE50",blend((0.50,ZF),(0.50,ZY)))
SIGS["SL_AGEMOD50"]=mk("SL_AGEMOD50",femat_mod(0.5))
SIGS["SL_AGEMOD100"]=mk("SL_AGEMOD100",femat_mod(1.0))
SIGS["SOLO_AGE"]=mk("SOLO_AGE",blend((1.0,ZY)))
SIGS["SOLO_FUND"]=mk("SOLO_FUND",blend((1.0,ZF)))
# --- turnover-matched nulls applied to the AGE input only (verbatim families from null.py) ---
def nulls_of(Zin):
    out={}
    for k in (101,503,1009):
        Q=np.full_like(Zin,np.nan); Q[k:]=Zin[:-k]; out["SHIFT%d"%k]=np.where(B,Q,np.nan)
    for d in (1,2,3):
        rng=np.random.default_rng([4242,d]); pi=rng.permutation(Zin.shape[1])
        out["RELAB%d"%d]=np.where(B,Zin[:,pi],np.nan)
    return out
NZ=nulls_of(ZY); NA=nulls_of(AY)
for k,Q in NZ.items(): SIGS["N50_"+k]=mk("N50_"+k,blend((0.50,ZF),(0.50,Q)))
for k,Q in NA.items(): SIGS["NM_"+k]=mk("NM_"+k,np.where(B,ZF*(1.0+1.0*np.nan_to_num(Q,nan=0.0)),np.nan))
for k,Q in NZ.items(): SIGS["NSOLO_"+k]=mk("NSOLO_"+k,blend((1.0,Q)))
json.dump({k:v for k,v in SIGS.items()},open(R+"/sig_manifest_r5.json","w"),indent=1)
def run(job):
    arm,seat,seed,kind=job
    tag="R5S_%s_%s_s%s"%(arm,seat,seed) if kind=="book" else "R5O_%s_%s_s%s"%(arm,seat,seed)
    dst=OUT+"/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    base=BOOK if kind=="book" else SOLO
    ex=base+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+COSTB,"FEMAT_NPZ="+SIGS[arm]] \
       +(["W3FIX=0.21,0,0.79"] if seat=="fix" else [])+["OUT_TAG="+tag]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src); return "%-30s ok %5.1fs"%(tag,time.time()-t0)
if __name__=="__main__":
    what=sys.argv[1] if len(sys.argv)>1 else "base"
    if what=="base": arms=["IB_PAR","SL_AGE25","SL_AGE50","SL_AGEMOD50","SL_AGEMOD100"]; kind="book"
    elif what=="nulls": arms=[k for k in SIGS if k.startswith("N50_") or k.startswith("NM_")]; kind="book"
    elif what=="solo": arms=["SOLO_AGE","SOLO_FUND"]+[k for k in SIGS if k.startswith("NSOLO_")]; kind="solo"
    else: raise SystemExit("bad arg")
    jobs=[(a,st,sd,kind) for a in arms for st in ("dyn","fix") for sd in ("42","2027")]
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=7) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    print("%s_DONE %.0fs"%(what.upper(),time.time()-t0),flush=True)
    if what=="base":
        ok=True
        for st in ("dyn","fix"):
            for sd in ("42","2027"):
                a=np.load(OUT+"/R5S_IB_PAR_%s_s%s.npz"%(st,sd),allow_pickle=True)
                b=np.load(OUT+"/R5U_A0M_%s_s%s.npz"%(st,sd),allow_pickle=True)
                for k in ("rec","W"):
                    x=np.asarray(a[k],float); y=np.asarray(b[k],float)
                    nx=np.isnan(x); ny=np.isnan(y)
                    bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
                    ok&=bw; print("FEMAT parity %s s%s %s bitwise=%s"%(st,sd,k,bw),flush=True)
        print("FEMAT_PARITY_PASS",ok,flush=True)
