"""Track D batch 4 — LOB microstructure sleeves at v4 caliber (PREREG AMENDMENT 2)."""
import numpy as np, os, subprocess, time
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4s"
OUT="/workspace/uplift_2026-09-11/trackD_v4"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
BASE=np.isfinite(np.asarray(PW["f_fund_ema_v1"],float))
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off",f"FEMAT_NPZ={D}/sig/cur4.npz",f"OUT_TAG={tag}",
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
for nm in ["LOBIMB1","LOBIMB5","LOBSLOPE","LOBDEPTH","LOBIMB1D"]:
    z=np.load(f"/workspace/uplift_2026-09-11/lob/{nm}.npz",allow_pickle=True)
    assert np.array_equal(z["ts"].astype(np.int64),ts) and [str(x) for x in z["symbols"]]==[str(x) for x in sym]
    M=np.where(BASE,np.asarray(z["mat"],np.float64),np.nan)
    for sgn,tg in ((1.0,"p"),(-1.0,"m")):
        tag=f"SL_{nm}__{tg}"
        if os.path.exists(f"{OUT}/{tag}.npz"): continue
        np.savez(f"{D}/sig/cur4.npz",symbols=sym,ts=ts,mat=(sgn*M).astype(np.float32))
        ok=run(tag); print(f"{tag:24s} {'ok' if ok else 'FAIL'} {time.time()-t0:6.1f}s",flush=True)
        os.remove(f"{D}/sig/cur4.npz")
print("BATCH4 DONE")
