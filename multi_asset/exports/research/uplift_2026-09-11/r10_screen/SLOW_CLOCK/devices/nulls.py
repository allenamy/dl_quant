"""r10 STEP3 nulls: turnover-matched nulls (SHIFT101/503/1009, RELAB1-3) on the BEST-CASE
low-rho horizon objects, at the PINNED cost costb_PWR_G230k.json. Families copied verbatim from
r3_attack/null.py: RELAB = one FIXED symbol permutation at every anchor; SHIFT = whole score matrix
advanced k anchors. Both preserve the per-anchor rank distribution and lag-1 persistence => turnover."""
import numpy as np, sys, os, json, time, subprocess
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ",
 "COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON",
 "PANEL_IN","JUDGE_HC","TILT","TILT_TAU","TILT_K"]
assert not [k for k in ENV_WL if k in os.environ]
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
W10="/workspace/uplift_2026-09-11/r10_slowclock"
CB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
SL=[x for x in SLCOM if not x.startswith("COSTB_JSON")]+["COSTB_JSON="+CB]
F1=np.load(R+"/feats_r2.npz",allow_pickle=True); F2=np.load(R+"/feats_r2b.npz",allow_pickle=True)
g1=lambda k: np.asarray(F1[k],np.float64); g2=lambda k: np.asarray(F2[k],np.float64)
O_T3=orth(g1("TBF_MEAN_864"))
LAD=[orth(g1("TBF_MEAN_864")),orth(g2("TBF_MEAN_2016")),orth(g2("TBF_MEAN_4032")),orth(g2("TBF_MEAN_8640"))]
B=np.zeros(O_T3.shape); C=np.zeros(O_T3.shape)
for O in LAD:
    ok=np.isfinite(O); B[ok]+=O[ok]; C[ok]+=1
O_LAD=np.where(C>0,B/np.maximum(C,1),np.nan)
BASES={"T3":fill(O_T3)[0],"TLAD":fill(O_LAD)[0]}
def mknulls(name,M):
    out=[(name+"_REAL",M)]
    for d in (1,2,3):
        rng=np.random.default_rng([4242,d]); pi=rng.permutation(M.shape[1])
        out.append((name+"_RELAB%d"%d,M[:,pi]))
    for k in (101,503,1009):
        Q=np.full_like(M,np.nan); Q[k:]=M[:-k]
        out.append((name+"_SHIFT%d"%k,Q))
    return out
JOBS=[]
for nm,M in BASES.items(): JOBS+=[("NUL_"+t,X) for t,X in mknulls(nm,M)]
def run(a):
    tag,M=a
    dst=W10+"/out/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    f=W10+"/dev/sig/%s.npz"%tag
    np.savez(f,symbols=SYM,ts=TS,mat=np.asarray(M,np.float64))
    env={k:v for k,v in os.environ.items() if k not in ENV_WL}
    env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+SL+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(W10+"/dev/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=W10+"/dev",stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=W10+"/dev/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(dst,cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    return "%-22s ok %5.1fs"%(tag,time.time()-t)
if __name__=="__main__":
    from multiprocessing import Pool
    print("jobs",len(JOBS),flush=True)
    with Pool(7) as p:
        for r in p.imap_unordered(run,JOBS): print(r,flush=True)
    print("NULLS_DONE")
