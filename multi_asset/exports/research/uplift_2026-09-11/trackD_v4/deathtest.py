"""Falsification: is the amihud / asz alpha produced by names in their terminal window (delisting bias)?
Arm DEATHCUT_k = the same signal with every name set to NaN in its last k anchors before it disappears
from the member set (names still alive at the sample end are untouched)."""
import numpy as np, os, subprocess, time
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4s"
OUT="/workspace/uplift_2026-09-11/trackD_v4"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
BASE=np.isfinite(np.asarray(PW["f_fund_ema_v1"],float))
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]; NW=829
last=np.full(NW,-1,np.int64)
for i in range(len(E)):
    m=np.asarray(mem[i]); ok=np.isfinite(y4[i,m]); last[m[ok]]=i
END=len(E)-1
emap={int(t):i for i,t in enumerate(E)}
ROW=np.array([emap.get(int(t),-1) for t in ts])
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off",f"FEMAT_NPZ={D}/sig/cur5.npz",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python",f"{HC}/w10_health.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"],legs_fund=A["legs_fund"],config_json=A["config_json"])
    os.remove(src); return True
dying=(last>=0)&(last<END-60)
print("dying names:",int(dying.sum()))
for name,sgn in (("f_amihud_24h",1.0),("f_asz_24h",-1.0)):
    M0=np.where(BASE,sgn*np.asarray(PW[name],float),np.nan)
    for K in (60,180):
        M=M0.copy()
        cut=np.zeros(M.shape,bool)
        for c in np.where(dying)[0]:
            lo=last[c]-K
            cut[:,c]=(ROW>=lo)&(ROW<=last[c])&(ROW>=0)
        M=np.where(cut,np.nan,M)
        tag=f"SL_DEATHCUT{K}_{name}__{'p' if sgn>0 else 'm'}"
        np.savez(f"{D}/sig/cur5.npz",symbols=sym,ts=ts,mat=M.astype(np.float32))
        ok=run(tag); print(f"{tag:38s} {'ok' if ok else 'FAIL'}  cells removed {int(cut.sum())}",flush=True)
        os.remove(f"{D}/sig/cur5.npz")
print("DEATHTEST DONE")
