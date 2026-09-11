"""TURNOVER-MATCHED NULLS for RESID_SHARPE. Device w10_sleeve.py UNMODIFIED (sha b88e35a4...).
Env copied verbatim from r2_learned/drive_r2.py COMMON. Two null families, both of which preserve the
score's per-anchor rank distribution AND its lag-1 persistence (hence its turnover) exactly:
  RELAB_k : a single FIXED symbol permutation applied at every anchor (destroys symbol<->score mapping)
  SHIFT_k : the whole score matrix advanced by k anchors (destroys time alignment, keeps everything else)
Reports net_ex AND pnl_ex (gross-of-carry-and-cost) per the round-3 brief."""
import numpy as np, os, subprocess, time, sys
R2="/workspace/uplift_2026-09-11/r2_learned"; HC="/workspace/review_scratch/health_check"
W="/workspace/uplift_2026-09-11/r3_attack_b9646"
D=W+"/dev"; OUT=W+"/out"
for d in (D+"/logs",OUT,W+"/sig"): os.makedirs(d,exist_ok=True)
for src,dst in ((R2+"/dev/pod_backup_2026-08-21",D+"/pod_backup_2026-08-21"),
                (R2+"/dev/f8_2026-08-22",D+"/f8_2026-08-22"),
                ("/workspace/dlw_v4raw",D+"/dlw_2026-08-22")):
    if not os.path.exists(dst) and os.path.exists(os.path.realpath(src)): os.symlink(os.path.realpath(src),dst)
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); sym=TG["symbols"]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); assert np.array_equal(PW["symbols"],sym)
OFF=int(np.searchsorted(E_ts,pts[0])); assert np.array_equal(E_ts[OFF:OFF+len(pts)],pts)
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        "UMASK_NPZ=%s/masks/umask_UPIT_CRYPTO.npz"%HC,"COSTB_JSON=%s/calib/costb_fee_steady.json"%HC,
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
def run(tag,f):
    env=dict(os.environ); env.update({"OMP_NUM_THREADS":"3","OPENBLAS_NUM_THREADS":"3","MKL_NUM_THREADS":"3"})
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off","FEMAT_NPZ="+f,"OUT_TAG="+tag,
         "/workspace/venv/bin/python",R2+"/w10_sleeve.py"]
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/%s.npz"%tag,cols=A["cols"],rec=A["d30_n2_c42_rec"],config_json=A["config_json"])
    os.remove(src); return tag+" ok"
if __name__=="__main__":
    P=np.load(R2+"/preds/RESID_SHARPE_s42.npy")[OFF:OFF+len(pts)]
    jobs=[]
    for d in (1,2,3):
        rng=np.random.default_rng([4242,d]); pi=rng.permutation(P.shape[1])
        f=W+"/sig/RELAB%d.npz"%d; np.savez(f,symbols=sym,ts=pts,mat=np.asarray(P[:,pi],np.float32))
        jobs.append(("NULL_RELAB%d"%d,f))
    for k in (101,503,1009):
        Q=np.full_like(P,np.nan); Q[k:]=P[:-k]
        f=W+"/sig/SHIFT%d.npz"%k; np.savez(f,symbols=sym,ts=pts,mat=np.asarray(Q,np.float32))
        jobs.append(("NULL_SHIFT%d"%k,f))
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(lambda a: run(*a), jobs): print(r,"%.0fs"%(time.time()-t0),flush=True)
    print("NULLS_DONE")
