"""Track D batch 3 — per-anchor cross-sectional residualisation of a signal against the deployed fund
score (PREREG AMENDMENT 1). usage: drive_sleeves3.py NAME1 NAME2 ... (panel column or derived name)"""
import numpy as np, os, sys, subprocess, time
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4s"
OUT="/workspace/uplift_2026-09-11/trackD_v4"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0)
RN8=np.asarray(PW["f_fund_now"],float)*(8.0/IVf)
def col(c):
    if c=="f_fund_rn8": return RN8
    if c=="D_SURP": return RN8-FE1
    if c=="D_MOMSPREAD": return np.asarray(PW["f_mom_30d"],float)-np.asarray(PW["f_mom_7d"],float)
    if c=="D_VOLADJMOM": return np.asarray(PW["f_mom_7d"],float)/(np.abs(np.asarray(PW["f_vol_7d"],float))+1e-6)
    return np.asarray(PW[c],float)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10:
            out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off",f"FEMAT_NPZ={D}/sig/cur3.npz",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python",f"{HC}/w10_health.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"],legs_fund=A["legs_fund"],config_json=A["config_json"])
    os.remove(src); return True
t0=time.time()
for spec in sys.argv[1:]:
    name, sgn = (spec[:-2], 1.0) if spec.endswith("_p") else (spec[:-2], -1.0)
    Z=rz(np.where(BASE,col(name),np.nan))
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    tag=f"SL_ORTH_{name}__{'p' if sgn>0 else 'm'}"
    if os.path.exists(f"{OUT}/{tag}.npz"): continue
    np.savez(f"{D}/sig/cur3.npz",symbols=sym,ts=ts,mat=(sgn*R).astype(np.float32))
    ok=run(tag); print(f"{tag:28s} {'ok' if ok else 'FAIL'} {time.time()-t0:6.1f}s",flush=True)
    os.remove(f"{D}/sig/cur3.npz")
print("BATCH3 DONE")
