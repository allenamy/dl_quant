"""I-2 TRAP: the paper scorer has been scoring the RETIRED 3-leg king book.
Build that book's own realised rank-IC and compare with the DEPLOYED (blended PHI=0.45) book's IC."""
import os, json, subprocess, time, hashlib
import numpy as np
from scipy.stats import rankdata
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; HC="/workspace/review_scratch/health_check"
R6=f"{U}/r6/out"; TREE=f"{R}/dev_ext"; T=f"{TREE}/probe_artifacts"; DEV=f"{R}/w12b_intervene.py"
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY","FSEED","FPRED","COSTB_JSON","OUT_TAG"]
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","UMASK_SCOPE=m1",
        "UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","COSTB_JSON="+U+"/r3k/costb_PWR_G230k.json",
        "SLOW_NPY="+R6+"/SLOW_v4_x0910.npy","FSEED=42","FPRED=f10_v4RAWx_s42.npy"]
JOBS=[("R12_KING3LEG_s42",COMMON+["LEGS=101","PHI=0"])]      # retired 3-leg king book (king+rev24+fund, no DL)
for tag,ex in JOBS:
    if os.path.exists(f"{T}/w10_ablation_series_{tag}.npz"): print(tag,"cached"); continue
    ex=ex+["OUT_TAG="+tag]
    for e in ex: assert e.split("=",1)[0] in ENV_WL, e
    env=dict(os.environ)
    for k in list(env):
        if k in ENV_WL or k in ("CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","R12_NULL","W3FIX","FTPOS"): env.pop(k,None)
    env.update(OMP_NUM_THREADS="4")
    with open(f"{TREE}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=TREE,stdout=lf,stderr=subprocess.STDOUT,env=env)
    print(tag,"rc",rc,flush=True)
MT=np.load(f"{R6}/meta_newprod_v4_x0910.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]; mi={int(t):i for i,t in enumerate(E_ts)}
MON=np.load(f"{R}/out/monitors.npz",allow_pickle=True); IC_DEP=MON["ic"]; ts=MON["ts"].astype(np.int64)
Z=np.load(f"{T}/w10_ablation_series_R12_KING3LEG_s42.npz",allow_pickle=True)
COLS=[str(c) for c in Z["cols"]]; C={k:i for i,k in enumerate(COLS)}
Rr=np.asarray(Z["d30_n2_c42_rec"],float); W3=np.asarray(Z["d30_n2_c42_W"],float)
ts3=np.round(Rr[:,C["ts"]]).astype(np.int64)
ic3=np.full(len(ts3),np.nan)
for p in range(len(ts3)):
    i=mi[int(ts3[p])]; m=members[i]; w=W3[p,m]; yy=np.asarray(y4[i,m],np.float64)
    ok=np.isfinite(yy)&(np.abs(w)>1e-12)
    if ok.sum()>=30: ic3[p]=float(np.corrcoef(rankdata(w[ok]),rankdata(yy[ok]))[0,1])
com={int(t):p for p,t in enumerate(ts3)}
idx=np.array([com[int(t)] for t in ts if int(t) in com]); sel=np.array([int(t) in com for t in ts])
a=IC_DEP[sel]; b=ic3[idx]; ok=np.isfinite(a)&np.isfinite(b)
def tm(x,L):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x); f=np.isfinite(x).astype(float)
    cs=np.concatenate([[0.],np.cumsum(v)]); cn=np.concatenate([[0.],np.cumsum(f)])
    for i in range(L,len(x)):
        n=cn[i]-cn[i-L]
        if n>=L/2: o[i]=(cs[i]-cs[i-L])/n
    return o
OUT={"n_common":int(ok.sum()),
 "anchor_ic_corr_deployed_vs_retired3leg":float(np.corrcoef(a[ok],b[ok])[0,1]),
 "mean_ic_deployed":float(np.nanmean(a)),"mean_ic_retired3leg":float(np.nanmean(b)),
 "mean_abs_diff":float(np.nanmean(np.abs(a[ok]-b[ok])))}
for L in (24,42):
    ta,tb=tm(a,L),tm(b,L); o2=np.isfinite(ta)&np.isfinite(tb)
    for th in (-0.0228,-0.0443):
        fa,fb=ta[o2]<th,tb[o2]<th
        OUT[f"trail{L}_th{abs(th)}"]={"corr":float(np.corrcoef(ta[o2],tb[o2])[0,1]),
          "fire_rate_deployed_pct":float(100*fa.mean()),"fire_rate_retired_pct":float(100*fb.mean()),
          "agreement_pct":float(100*(fa==fb).mean()),
          "retired_fires_deployed_not_pct":float(100*(fb&~fa).mean()),
          "deployed_fires_retired_not_pct":float(100*(fa&~fb).mean())}
print(json.dumps(OUT,indent=1))
json.dump(OUT,open(f"{R}/out/I2_TRAP.json","w"),indent=1)
print("TRAP_DONE")
