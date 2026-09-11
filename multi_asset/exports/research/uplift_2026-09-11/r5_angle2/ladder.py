"""ANGLE 2 / STEP 1+2a: SHIFT LADDER on A0's OWN fund-leg score xz(f_fund_ema_v1), BOTH seats, BOTH seeds.
Arm construction VERBATIM from r4_p1/b1c_a0ctrl.py (APAR = unshifted parity; ASHIFT_k: Q[k:]=ZF[:-k]).
Extra rungs added (denser k) + two LOOK-AHEAD diagnostics (ALEAD_k: Q[:-k]=ZF[k:]) which are NOT
admissible evidence for anything deployable - they exist only to separate 'staleness helps' from
'any time-misalignment helps'.
Device = /workspace/uplift_2026-09-11/w10_sleeve.py UNMODIFIED (sha b88e35a4...). Env = round-4 pin.
ENV WHITELIST asserted (E-0826-D)."""
import numpy as np, os, sys, subprocess, time, hashlib, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, save
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r5a2"; D=R+"/dev"; OUT=R+"/arms"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
BOOK=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
WHITELIST=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ",
           "SLOW_NPY","FSEED","FPRED","COSTB_JSON","W3FIX","FEMAT_NPZ","OUT_TAG",
           "OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"]
DEFAULTED=["LTRIM_TH","CDAMP","FTRIM_TH","FTPOS","RNSM","SLEEVE","SEATNET","SEATF10","KTAIL",
           "KMOD","KMOD_AGREE","KMOD_F10","KMOD_L","FUNDSCALE","TRADE_TOPN","REF_SKIP"]
KS=[1,3,6,12,25,50,101,150,200,300,400,503,750,1009,1500,2000]
LEADS=[6,101,503]
def build():
    PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
    ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
    FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
    ZF=RZ(FE1,B); S={"APAR":save(D+"/sig/A2_PAR.npz",sym,ts,ZF)}
    for k in KS:
        Q=np.full_like(ZF,np.nan); Q[k:]=ZF[:-k]; S["ASHIFT%d"%k]=save(D+"/sig/A2_SHIFT%d.npz"%k,sym,ts,Q)
    for k in LEADS:
        Q=np.full_like(ZF,np.nan); Q[:-k]=ZF[k:]; S["ALEAD%d"%k]=save(D+"/sig/A2_LEAD%d.npz"%k,sym,ts,Q)
    return S
def run(job):
    arm,seat,seed,femat=job
    tag="R5A2_%s_%s_s%s"%(arm,seat,seed); dst=OUT+"/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env={k:v for k,v in os.environ.items() if k not in WHITELIST and k not in DEFAULTED}
    for v in DEFAULTED: assert v not in env, v
    env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    ex=BOOK+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+COSTB] \
       +(["W3FIX=0.21,0,0.79"] if seat=="fix" else [])+(["FEMAT_NPZ="+femat] if femat else [])+["OUT_TAG="+tag]
    for e in ex: assert e.split("=")[0] in WHITELIST, e
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src); return "%-28s ok %5.1fs"%(tag,time.time()-t0)
if __name__=="__main__":
    S=build()
    # A0 knobs-off (no FEMAT) at the round-4 cost model, both seats/seeds - the true baseline
    jobs=[("A0",st,sd,None) for st in ("dyn","fix") for sd in ("42","2027")]
    jobs=[(a,st,sd,S[a]) for a in sorted(S) for st in ("dyn","fix") for sd in ("42","2027")]+jobs
    jobs=[j for j in jobs if j[3] is not None]+[("A0",st,sd,None) for st in ("dyn","fix") for sd in ("42","2027")]
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=14) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    print("LADDER_DONE %.0fs"%(time.time()-t0))
