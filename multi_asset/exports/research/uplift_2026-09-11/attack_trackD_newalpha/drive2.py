"""Cost-stress: the device's live-calibrated tiers charge the LEAST liquid tier LESS than the most liquid
(blended 2.013 vs 2.202 bps/unit). An illiquidity-tilt sleeve is therefore priced by a model with no
liquidity term. Re-run A0-shaped and IB_AM50 under two honest alternatives."""
import numpy as np, os, subprocess, time, json, sys
HC="/workspace/review_scratch/health_check"; A="/workspace/uplift_2026-09-11/attack_trackD_newalpha"
D=A+"/dev"; OUT=A+"/out"
def blended(mk,tk,sh): return sh*mk+(1-sh)*tk
T0=(1.8001,4.5001,0.8511); T1=(1.799,4.4988,0.9246); T2=(1.7998,4.5002,0.921)
b0,b1,b2=blended(*T0),blended(*T1),blended(*T2)
print("device blended bps/unit by tier: t0(qv>=5e6) %.4f  t1(>=1e6) %.4f  t2(rest) %.4f"%(b0,b1,b2))
def mk_json(path,scales):
    tiers=[]
    for (mk,tk,sh),s in zip((T0,T1,T2),scales):
        tiers.append({"name":"t","maker_bps":mk*s,"taker_bps":tk*s,"maker_share":sh})
    json.dump({"tiers":tiers},open(path,"w"))
    print(path,[round(blended(t["maker_bps"],t["taker_bps"],t["maker_share"]),3) for t in tiers])
FLAT=A+"/costb_flat.json";  mk_json(FLAT,[1.0, b0/b1, b0/b2])
ILLQ=A+"/costb_illiq.json"; mk_json(ILLQ,[1.0, 1.5*b0/b1, 2.5*b0/b2])
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
AM=np.asarray(PW["f_amihud_24h"],float)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan)); ZA=rz(np.where(B,AM,np.nan))
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]
def run(tag,M,costb):
    if os.path.exists(OUT+"/"+tag+".npz"): print("skip",tag,flush=True); return
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    cmd=["env"]+IBCOM+["COSTB_JSON="+costb,"FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",HC+"/w10_health.py"]
    t=time.time()
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); os.remove(f); return
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f); print("%-20s ok %5.1fs"%(tag,time.time()-t),flush=True)
STD=HC+"/calib/costb_fee_steady.json"
run("XIB_AM50_STD",0.5*ZF+0.5*ZA,STD)
run("XIB_PAR_FLAT",ZF,FLAT); run("XIB_AM50_FLAT",0.5*ZF+0.5*ZA,FLAT)
run("XIB_PAR_ILLQ",ZF,ILLQ); run("XIB_AM50_ILLQ",0.5*ZF+0.5*ZA,ILLQ)
print("DONE2")
