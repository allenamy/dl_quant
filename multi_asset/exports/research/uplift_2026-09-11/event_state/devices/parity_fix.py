"""Close round-1 defect (3): make the sleeve-injection path BITWISE, not approximate.
Round-1 injected argsort(argsort(v))/(n-1)-0.5 cast to float32; the device xz() uses scipy rankdata (ties
averaged). Ties + the cast are the whole residual. Inject rankdata-based ranks in float64 instead."""
import numpy as np, os, subprocess, sys
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4ev"
OUT="/workspace/uplift_2026-09-11/event_state/arms_ib"
PW=np.load(f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]; FE1=np.asarray(PW["f_fund_ema_v1"],float)
def xzrank(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=int(ok.sum())
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1",f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",
        f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
for tag,dt in [("IB_PARITY2_f64_s42",np.float64),("IB_PARITY2_f32_s42",np.float32)]:
    sf=f"{D}/sig/{tag}.npz"; np.savez(sf,symbols=sym,ts=ts,mat=xzrank(FE1).astype(dt))
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["FSEED=42","FPRED=f10_A0_s42.npy",f"FEMAT_NPZ={sf}",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python","/workspace/uplift_2026-09-11/w10_sleeve.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    os.remove(sf)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    A0=np.load(f"{D}/probe_artifacts/w10_ablation_series_GP_dyn_s42.npz",allow_pickle=True)
    A=np.load(src,allow_pickle=True)
    for key in ("d30_n2_c42_rec","d30_n2_c42_W"):
        x=A0[key]; y=A[key]
        print(tag,key,"BITWISE_EQ" if np.array_equal(x,y) else "maxabs %.3e"%float(np.nanmax(np.abs(x-y))),flush=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",rec=A["d30_n2_c42_rec"],config_json=A["config_json"]); os.remove(src)
