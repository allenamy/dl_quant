"""Round-2 sleeve driver: pred matrix (DL axis 10212x829) -> FEMAT_NPZ (panel axis 10039x829)
-> w10_sleeve.py (GATE-P bitwise device) as a STANDALONE book: LEGS=001 PHI=0 FTRIM=off.
Env copied verbatim from run_v4_arms.sh COMMON. Writes reduced artifacts to out/."""
import numpy as np, os, json, subprocess, sys, time, hashlib
R2="/workspace/uplift_2026-09-11/r2_learned"
HC="/workspace/review_scratch/health_check"
D=R2+"/dev"; OUT=R2+"/out"
os.makedirs(OUT,exist_ok=True); os.makedirs(R2+"/sig",exist_ok=True)
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); sym=TG["symbols"]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); psym=PW["symbols"]
assert np.array_equal(psym,sym)
OFF=int(np.searchsorted(E_ts,pts[0])); assert np.array_equal(E_ts[OFF:OFF+len(pts)],pts)
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        "UMASK_NPZ=%s/masks/umask_UPIT_CRYPTO.npz"%HC,"COSTB_JSON=%s/calib/costb_fee_steady.json"%HC,
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"]
def run(tag, matfile, extra=()):
    env=dict(os.environ); env.update({"OMP_NUM_THREADS":"3","OPENBLAS_NUM_THREADS":"3","MKL_NUM_THREADS":"3"})
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off","FEMAT_NPZ="+matfile]+list(extra)+["OUT_TAG="+tag,
         "/workspace/venv/bin/python",R2+"/w10_sleeve.py"]
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src):
        print("FAIL",tag,"rc",rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/%s.npz"%tag,cols=A["cols"],rec=A["d30_n2_c42_rec"],rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"],legs_fund=A["legs_fund"],config_json=A["config_json"])
    os.remove(src); return True
def write_mat(M, path):
    np.savez(path,symbols=sym,ts=pts,mat=np.asarray(M,np.float32))
def xrank_rows(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=int(ok.sum())
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok])).astype(np.float64)/max(n-1,1)-0.5
    return out
if __name__=="__main__":
    todo=sys.argv[1:]
    man={}
    t0=time.time()
    # ---- device-validity receipt: inject the deployed fund score itself ----
    if "PARITY" in todo or not todo:
        f=R2+"/sig/parity.npz"; write_mat(np.asarray(PW["f_fund_ema_v1"],np.float32),f)
        man["SLPAR_FUNDV1"]=run("SLPAR_FUNDV1",f)
    for name in todo:
        if name=="PARITY": continue
        p=R2+"/preds/%s.npy"%name
        if not os.path.exists(p): print("no pred",p,flush=True); continue
        P=np.load(p)[OFF:OFF+len(pts)]
        f=R2+"/sig/%s.npz"%name
        write_mat(P,f); man["SL_"+name]=run("SL_"+name,f)
        # sign-mirror arm (declared in prereg: NOT a free parameter, reported for completeness only)
        write_mat(-P,f); man["SLm_"+name]=run("SLm_"+name,f)
        print("%-28s %.0fs"%(name,time.time()-t0),flush=True)
    json.dump(man,open(OUT+"/manifest_%d.json"%int(time.time()),"w"),indent=1)
    print("DRIVE_DONE",man)
