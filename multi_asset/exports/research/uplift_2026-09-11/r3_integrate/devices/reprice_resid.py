"""R3-INTEGRATE: re-price the RESID_SHARPE standalone sleeve under INFRA-1 honest cost models.
Device w10_sleeve.py UNMODIFIED (sha b88e35a4...). Only COSTB_JSON varies. Env copied verbatim
from r2_learned/drive_r2.py COMMON (which itself is run_v4_arms.sh COMMON)."""
import numpy as np, os, json, subprocess, sys, time, hashlib
R2="/workspace/uplift_2026-09-11/r2_learned"
A1="/workspace/uplift_2026-09-11/infra1_cost"
R3="/workspace/uplift_2026-09-11/r3_integrate"
HC="/workspace/review_scratch/health_check"
D=R3+"/dev"; OUT=R3+"/out"
for d in (D+"/logs", OUT, R3+"/sig"): os.makedirs(d, exist_ok=True)
# mirror tree links (device needs pod_backup_2026-08-21 / f8 / dlw)
for src,dst in ((R2+"/dev/pod_backup_2026-08-21", D+"/pod_backup_2026-08-21"),
                (R2+"/dev/f8_2026-08-22", D+"/f8_2026-08-22"),
                ("/workspace/dlw_v4raw", D+"/dlw_2026-08-22")):
    if not os.path.exists(dst):
        os.symlink(os.path.realpath(src), dst)
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); sym=TG["symbols"]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); psym=PW["symbols"]
assert np.array_equal(psym,sym)
OFF=int(np.searchsorted(E_ts,pts[0])); assert np.array_equal(E_ts[OFF:OFF+len(pts)],pts)
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        "UMASK_NPZ=%s/masks/umask_UPIT_CRYPTO.npz"%HC,
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
COSTB={"STD":HC+"/calib/costb_fee_steady.json"}
for t in ("H0","X1","X2","X3"): COSTB[t]=A1+"/costb_honest_%s.json"%t
def run(tag, matfile, cb):
    env=dict(os.environ); env.update({"OMP_NUM_THREADS":"3","OPENBLAS_NUM_THREADS":"3","MKL_NUM_THREADS":"3"})
    cmd=["env"]+COMMON+["COSTB_JSON="+COSTB[cb],"LEGS=001","PHI=0","FTRIM=off","FEMAT_NPZ="+matfile,
         "OUT_TAG="+tag,"/workspace/venv/bin/python",R2+"/w10_sleeve.py"]
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src):
        return "FAIL %s rc=%s"%(tag,rc)
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/%s.npz"%tag,cols=A["cols"],rec=A["d30_n2_c42_rec"],config_json=A["config_json"])
    os.remove(src)
    return tag+" ok"
if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    jobs=[]
    for name in ("RESID_SHARPE_s42","RESID_SHARPE_s2027"):
        P=np.load(R2+"/preds/%s.npy"%name)[OFF:OFF+len(pts)]
        f=R3+"/sig/%s.npz"%name
        np.savez(f,symbols=sym,ts=pts,mat=np.asarray(P,np.float32))
        for cb in ("STD","H0","X1","X2","X3"):
            jobs.append(("RS_%s_%s"%(name,cb), f, cb))
    t0=time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(lambda j: run(*j), jobs):
            print("%-42s %6.0fs"%(r,time.time()-t0), flush=True)
    print("REPRICE_DONE")
