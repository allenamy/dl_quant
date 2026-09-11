"""Track G driver: sleeve arms LEGS=001 PHI=0 FTRIM=off with FEMAT injection. usage: drive_G.py SPEC..."""
import numpy as np, os, sys, subprocess, time, json
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4ev"
OUT="/workspace/uplift_2026-09-11/event_state/arms"; os.makedirs(OUT,exist_ok=True)
ES="/workspace/uplift_2026-09-11/event_state"
PW=np.load(f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
F=np.load(f"{ES}/feats_v4.npz",allow_pickle=True)
assert np.array_equal(F["ts"].astype(np.int64),ts)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag,sigfile):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off",f"FEMAT_NPZ={sigfile}",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python","/workspace/uplift_2026-09-11/w10_sleeve.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],
                        legs_ts=A["legs_ts"],config_json=A["config_json"])
    os.remove(src); return True
def getmat(name,seed=None):
    """name forms: RAW:<F>  ORTH:<F>  PERM:<F>  PERMORTH:<F>"""
    kind,f=name.split(":")
    M=np.where(BASE,np.asarray(F[f],float),np.nan)
    if kind=="RAW": return M
    if kind=="PERM":
        rng=np.random.default_rng(seed); O=np.full(M.shape,np.nan)
        for i in range(M.shape[0]):
            ok=np.isfinite(M[i]); v=M[i][ok]; rng.shuffle(v); O[i,ok]=v
        return O
    Z=rz(M)
    if kind=="PERMORTH":
        rng=np.random.default_rng(seed)
        for i in range(Z.shape[0]):
            ok=np.isfinite(Z[i]); v=Z[i][ok]; rng.shuffle(v); Z[i,ok]=v
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; x=x-x.mean(); y2=y-y.mean(); vx=float((x*x).sum())
        b=float((x*y2).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y2-b*x
    return R
t0=time.time()
for spec in sys.argv[1:]:
    body,sg=spec.rsplit("__",1); sgn=1.0 if sg=="p" else -1.0
    _b=body.replace(":","_"); tag="SL_"+_b+"__"+sg
    if os.path.exists(f"{OUT}/{tag}.npz"): print("skip",tag,flush=True); continue
    M=getmat(body,seed=20260911)
    sf=f"{D}/sig/{tag}.npz"
    np.savez(sf,symbols=sym,ts=ts,mat=(sgn*M).astype(np.float32))
    ok=run(tag,sf); os.remove(sf)
    print("%-34s %s %6.1fs"%(tag,"ok" if ok else "FAIL",time.time()-t0),flush=True)
print("DRIVE_DONE")
