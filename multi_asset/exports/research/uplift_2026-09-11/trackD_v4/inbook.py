"""Deployment-shaped arm: A0's exact config, with the fund-leg SCORE replaced by a rank blend of the
in-service fund score and the candidate. Trades net inside one book (unlike the g-series sum)."""
import numpy as np, os, subprocess, time
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4s"
OUT="/workspace/uplift_2026-09-11/trackD_v4"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0)
RN8=np.asarray(PW["f_fund_now"],float)*(8.0/IVf)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10:
            out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan))
ZA=rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan))
ZS=rz(np.where(B,-(RN8-FE1),np.nan))
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1",f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",
        f"COSTB_JSON={HC}/calib/costb_fee_steady.json",f"SLOW_NPY={K3}","FSEED=42","FPRED=f10_A0_s42.npy"]
def run(tag,fem):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+[f"FEMAT_NPZ={fem}",f"OUT_TAG={tag}","/workspace/venv/bin/python",f"{HC}/w10_health.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"],legs_fund=A["legs_fund"],config_json=A["config_json"])
    os.remove(src); return True
ARMS={"IB_PARITY": ZF,                              # must reproduce A0 (rank of the fund score = fund score rank)
      "IB_AM25": 0.75*ZF+0.25*ZA, "IB_AM50": 0.50*ZF+0.50*ZA,
      "IB_AMSU": 0.50*ZF+0.25*ZA+0.25*ZS, "IB_SU25": 0.75*ZF+0.25*ZS}
for tag,M in ARMS.items():
    f=f"{D}/sig/ib.npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    ok=run(tag,f); print(tag,"ok" if ok else "FAIL",flush=True); os.remove(f)
print("INBOOK DONE")
