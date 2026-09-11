"""R3-CRITICAL-1 step E: re-price A0 / XIB_LAG50 / RESID_SHARPE at the FITTED impact.
Device = /workspace/uplift_2026-09-11/w10_sleeve.py, UNMODIFIED (GATE P bitwise, r3k/GATE_P_r3k.json).
Only COSTB_JSON varies.  A0 = knobs-off (NO FEMAT injection) -> bitwise-identical book to the archived
A0 at STD, so the STD->FIT delta is a pure cost effect.
XIB_LAG50 built with the DEVICE'S OWN ranker (infra2/xib_signal.RZ), not round-1's ordinal builder.
"""
import numpy as np, os, sys, subprocess, time, json, hashlib
sys.path.insert(0,"/workspace/uplift_2026-09-11/infra2")
from xib_signal import RZ, blend, save
HC="/workspace/review_scratch/health_check"; R3="/workspace/uplift_2026-09-11/r3k"
A1="/workspace/uplift_2026-09-11/infra1_cost"; R2="/workspace/uplift_2026-09-11/r2_learned"
D=R3+"/dev"; OUT=R3+"/arms"
for p in (D+"/logs",D+"/sig",D+"/probe_artifacts",OUT): os.makedirs(p,exist_ok=True)
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1); AM=np.asarray(PW["f_amihud_24h"],float)
ZF=RZ(FE1,B); ZA=RZ(AM,B)
ZA_LAG=np.full_like(ZA,np.nan); ZA_LAG[1:]=ZA[:-1]; ZA_LAG=np.where(B,ZA_LAG,np.nan)
save(D+"/sig/XIB.npz",sym,pts,blend((0.5,ZF),(0.5,ZA_LAG)))
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); assert np.array_equal(TG["symbols"],sym)
OFF=int(np.searchsorted(E_ts,pts[0])); assert np.array_equal(E_ts[OFF:OFF+len(pts)],pts)
for s in ("42","2027"):
    P=np.load(R2+"/preds/RESID_SHARPE_s%s.npy"%s)[OFF:OFF+len(pts)]
    np.savez(D+"/sig/RS_s%s.npz"%s,symbols=sym,ts=pts,mat=np.asarray(P,np.float32))
COSTB={"STD":HC+"/calib/costb_fee_steady.json","X1":A1+"/costb_honest_X1.json",
       "H0":A1+"/costb_honest_H0.json"}
for G in (230,345,460,690,920,1380,2300,4600,9200,23000):
    COSTB["FIT%dk"%G]=R3+"/costb_FIT_G%dk.json"%G
    COSTB["FITU%dk"%G]=R3+"/costb_FIT_G%dk_U.json"%G
for G in (230,345,460,690,920,1380,1840,2300,2760,3220,3680,4140,4600,9200,23000):
    COSTB["PWR%dk"%G]=R3+"/costb_PWR_G%dk.json"%G
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
BOOK=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
SLEEVE=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
def run(job):
    arm,cb,seed=job
    tag="%s_%s_s%s"%(arm,cb,seed)
    dst=OUT+"/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    if arm=="A0":   ex=BOOK+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed]
    elif arm=="XIB":ex=BOOK+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"FEMAT_NPZ="+D+"/sig/XIB.npz"]
    elif arm=="RS": ex=SLEEVE+["FEMAT_NPZ="+D+"/sig/RS_s%s.npz"%seed]
    else: return "unknown "+arm
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+ex+["COSTB_JSON="+COSTB[cb],"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    os.remove(src)
    return "%-26s ok %5.1fs"%(tag,time.time()-t0)
if __name__=="__main__":
    mode=sys.argv[1]
    if mode=="main":
        jobs=[(a,c,s) for a in ("A0","XIB","RS") for c in ("STD","X1","FIT230k","FITU230k") for s in ("42","2027")]
    elif mode=="pwr":
        jobs=[(a,"PWR230k",s) for a in ("A0","XIB","RS") for s in ("42","2027")]
        jobs+=[("A0","PWR%dk"%G,"42") for G in (345,460,690,920,1380,1840,2300,2760,3220,3680,4140,4600,9200)]
        jobs+=[("XIB","PWR%dk"%G,"42") for G in (460,920,1840,2300,3220,4600)]
        jobs+=[("RS","PWR%dk"%G,"42") for G in (460,920,1840,2300,3220,4600)]
    elif mode=="cap":
        jobs=[("A0","FIT%dk"%G,"42") for G in (345,460,690,920,1380,2300,4600,9200,23000)]
        jobs+=[("XIB","FIT%dk"%G,"42") for G in (460,920,2300,4600)]
        jobs+=[("RS","FIT%dk"%G,"42") for G in (460,920,2300,4600)]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    print("DONE",mode)
