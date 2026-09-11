"""Round-2 sleeve arms. Device = /workspace/uplift_2026-09-11/w10_sleeve.py (GATE P bitwise on all four
archived A0 arms, receipt gate_p.json). Standalone sleeve = LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<injected>.
All knobs default-off. Own mirror tree r2_sleeve/dev; dev_v4 untouched."""
import numpy as np, os, subprocess, time, sys
H="/workspace/review_scratch/health_check"; R="/workspace/uplift_2026-09-11/r2_sleeve"
D=R+"/dev"; OUT=R+"/out"; DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
from scipy.stats import rankdata
def rz(M):
    # AVERAGE ranks (the device's own rankdata convention). argsort-ranking would manufacture a
    # spurious order inside tie blocks -- ROLL is 34.6% tied, f_fund_iv is 99.4% tied.
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
def lag1(Z):
    L=np.full_like(Z,np.nan); L[1:]=Z[:-1]; return np.where(B,L,np.nan)
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
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+H+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+H+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
def run(tag,M,common):
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
    os.remove(src); os.remove(f)
    print("%-22s ok %5.1fs"%(tag,time.time()-t),flush=True)
# ---- feature assembly ----
NEW=np.load(R+"/feat/r2_new_feats.npz",allow_pickle=True)
assert (NEW["ts"].astype(np.int64)==ts).all(), "new-feature ts axis mismatch"
Zs={}
LGRP=["f_tbf_24h","f_rev_24h","f_vol_7d","f_range_24h","f_cpos_24h","f_volq_ratio","f_mom_30d","f_fund_iv"]
for k in LGRP: Zs["L_"+k]=lag1(rz(np.where(B,np.asarray(PW[k],float),np.nan)))
NGRP=["ROLL","VR","RSKEW","JUMP","DSEMI","ILLQTR","QVTR","CNTSZ"]
for k in NGRP: Zs["N_"+k]=rz(np.where(B,np.asarray(NEW[k],float),np.nan))
# positive control: round-1 XSL_ORTHLAG
Zs["PC_amihud_lag"]=lag1(rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan)))
if __name__=="__main__":
    which=sys.argv[1] if len(sys.argv)>1 else "screen"
    if which=="screen":
        for nm,Z in Zs.items(): run("SL_"+nm,orth(Z),SLCOM)
    print("DONE_"+which,flush=True)
