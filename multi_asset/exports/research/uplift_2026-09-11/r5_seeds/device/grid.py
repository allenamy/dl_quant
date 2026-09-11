"""ROUND 5 SUPPLEMENTARY: separate "the seat is FROZEN" from "the seat is frozen AT 0.21".
Device = r5_seeds/w10_sleeve_seatgrid.py (sha a2693feccb676f41) -- the pinned device with ONLY the W3FIX
whitelist widened. Gate: at W3FIX=0.21,0,0.79 it must reproduce the pinned device BITWISE."""
import numpy as np, os, sys, subprocess, time, json, hashlib
sys.path.insert(0,"/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, blend, save
R="/workspace/uplift_2026-09-11/r5_seeds"; D=R+"/devg"; OUT=R+"/grid"
HC="/workspace/review_scratch/health_check"; DEV=R+"/w10_sleeve_seatgrid.py"
for p in (D+"/logs",D+"/sig",D+"/probe_artifacts",OUT): os.makedirs(p,exist_ok=True)
for k,v in {"dlw_2026-08-22":"/workspace/dlw_v4raw","f8_2026-08-22":R+"/f8x","pod_backup_2026-08-21":R+"/dev/pod_backup_2026-08-21"}.items():
    if not os.path.islink(D+"/"+k): os.symlink(v,D+"/"+k)
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
        "COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json","SLOW_NPY="+K3]
def build_sigs():
    PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
    ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
    FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1); AM=np.asarray(PW["f_amihud_24h"],float)
    ZF=RZ(FE1,B); ZA=RZ(AM,B); ZAL=np.full_like(ZA,np.nan); ZAL[1:]=ZA[:-1]; ZAL=np.where(B,ZAL,np.nan)
    return {k:save(D+"/sig/%s.npz"%k,sym,ts,v) for k,v in {"XIBLAG50":blend((0.5,ZF),(0.5,ZAL))}.items()}
def run(arm,kw,seed,femat,cb):
    tag="G_%s_k%s_s%s_%s"%(arm,("%g"%kw).replace(".","p"),seed,cb)
    dst="%s/w10_ablation_series_%s.npz"%(OUT,tag)
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cost={"FIT":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json","STD":HC+"/calib/costb_fee_steady.json"}[cb]
    cmd=["env"]+[c for c in COMMON if not c.startswith("COSTB_JSON")]+["COSTB_JSON="+cost]+ \
        ["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"W3FIX=%g,0,%g"%(kw,1-kw)] + \
        (["FEMAT_NPZ="+femat] if femat else []) + ["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open("%s/logs/%s.log"%(D,tag),"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src="%s/probe_artifacts/w10_ablation_series_%s.npz"%(D,tag)
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    os.replace(src,dst)
    return "%-30s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    SIG=build_sigs()
    KS=[0.0,0.10,0.21,0.30,0.3568,0.4636,0.5338,0.70,1.0]
    jobs=[(a,k,s,(None if a=="A0" else SIG[a]),"FIT") for a in ("A0","XIBLAG50") for k in KS for s in ("42","2027")]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda j:run(*j),jobs): print(r,flush=True)
    print("GRID_DONE")
