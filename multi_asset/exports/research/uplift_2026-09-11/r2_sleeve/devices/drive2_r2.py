"""Round-2 stage 2: (a) minus-sign arms for the families whose + arm was negative (AMENDMENT 1);
(b) DOSE curve inside the surviving family (takerflow) -- smoothing halflife and lag depth.
Dose points are the SAME family, not new bets, so they do not enter K."""
import numpy as np, os, subprocess, time, sys
from scipy.stats import rankdata
H="/workspace/review_scratch/health_check"; R="/workspace/uplift_2026-09-11/r2_sleeve"
D=R+"/dev"; OUT=R+"/out"; DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=(rankdata(v[ok])-1.0)/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan))
def orth(Z):
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
def lagn(Z,n):
    L=np.full_like(Z,np.nan)
    if n>0: L[n:]=Z[:-n]
    else: L=Z.copy()
    return np.where(B,L,np.nan)
def ema(M,hl):
    """CAUSAL EMA over anchors of the RAW feature, NaN-safe; state carried per name."""
    a=1.0-0.5**(1.0/hl); O=np.full(M.shape,np.nan); s=np.full(M.shape[1],np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v)
        new=np.where(np.isfinite(s)&ok, s+a*(v-s), np.where(ok,v,s))
        s=new; O[i]=s
    return O
def perm(Z,seed):
    rng=np.random.default_rng(seed); Pm=np.full_like(Z,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i]); n=ok.sum()
        if n>=10:
            v=Z[i,ok].copy(); rng.shuffle(v); Pm[i,ok]=v
    return Pm
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+H+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+H+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag,M,common=SLCOM):
    if os.path.exists(OUT+"/"+tag+".npz"): print("skip",tag,flush=True); return
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    cmd=["env"]+common+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); os.remove(f); return
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f); print("%-26s ok %5.1fs"%(tag,time.time()-t),flush=True)
NEW=np.load(R+"/feat/r2_new_feats.npz",allow_pickle=True)
TBF=np.where(B,np.asarray(PW["f_tbf_24h"],float),np.nan)
if __name__=="__main__":
    w=sys.argv[1]
    if w=="minus":
        for k in ["RSKEW","ROLL","DSEMI","CNTSZ","QVTR"]:
            run("SLm_N_"+k, -orth(rz(np.where(B,np.asarray(NEW[k],float),np.nan))))
        for k in ["f_rev_24h","f_volq_ratio","f_cpos_24h"]:
            run("SLm_L_"+k, -orth(lagn(rz(np.where(B,np.asarray(PW[k],float),np.nan)),1)))
    if w=="tbfdose":
        for n in [0,1,2,3]:
            run("TBF_lag%d"%n, orth(lagn(rz(TBF),n)))
        for hl in [2,4,8,16,32]:
            run("TBF_ema%02d"%hl, orth(lagn(rz(ema(TBF,hl)),1)))
    if w=="stage3": stage3()
    if w=="placebo":
        run("TBF_PLA_permfeat", orth(lagn(rz(perm(TBF,20260911)),1)))
        run("TBF_PLA_orthperm", orth(perm(lagn(rz(TBF),1),20260912)))
    print("DONE_"+w,flush=True)

# --- appended: in-book blend arms (the DEPLOYABLE form) + cross-sleeve correlation inputs ---
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+H+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+H+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
def stage3():
    ZT=lagn(rz(TBF),1); ZA=lagn(rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan)),1)
    run("IB_PARITY_rk", ZF, IBCOM)                       # approximate-parity control
    for w in [25,50]:
        run("IB_TBF%d"%w, (1-w/100.)*ZF + (w/100.)*ZT, IBCOM)
    run("IB_AMLAG50", 0.5*ZF+0.5*ZA, IBCOM)              # round-1 XIB_LAG50 rebuilt with average ranks
    run("IB_AM40_TBF20", 0.4*ZF+0.4*ZA+0.2*ZT, IBCOM)    # both sleeves in the book
