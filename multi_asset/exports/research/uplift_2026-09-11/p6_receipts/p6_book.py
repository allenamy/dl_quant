"""P6 step 2: BOOK-LAYER price of the panel-vs-producer Amihud residual, and of the ext-vs-holefix2 caliber gap.
Signal construction copied VERBATIM from r3_xib/sleeve.py mk(rz_avg) (= arm ORTHLAGA, the INFRA-2 ranker fix).
Only the Amihud MATRIX is swapped; funding (f_fund_ema_v1) and the B mask stay the research objects.
Device env copied VERBATIM from r3_xib/sleeve.py COMMON (kind SL: LEGS=001 PHI=0 -> standalone sleeve, no F10 leg).
"""
import numpy as np, os, sys, subprocess, time, hashlib, json
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/p6"; D=R+"/dev"; OUT=R+"/arms"
HC="/workspace/review_scratch/health_check"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
for p in (D+"/logs",D+"/sig",D+"/probe_artifacts",OUT): os.makedirs(p,exist_ok=True)
for k,v in {"dlw_2026-08-22":"/workspace/dlw_v4raw","f8_2026-08-22":HC+"/dev_v4/f8_2026-08-22"}.items():
    if not os.path.islink(D+"/"+k): os.symlink(v,D+"/"+k)
BK=D+"/pod_backup_2026-08-21"; os.makedirs(BK,exist_ok=True)
for k,v in {"nets_histv2_-30_2_42.npy":"/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
       "nets_histv2_0_0_0.npy":"/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
       "slow_pred_hist_oos.npy":"/workspace/review_scratch/king_v4/SLOW_v4.npy",
       "wide_fea_hist_meta.npz":"/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
       "wide_panel_4h_hist_v2.npz":"/workspace/data/wide_panel_4h_v2ext.npz"}.items():
    t=BK+"/"+k
    if not os.path.islink(t): os.symlink(v,t)

PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
V=np.load(R+"/AM_variants.npz",allow_pickle=True)
assert np.array_equal(V["ts"].astype(np.int64),ts), "axis mismatch"
AMS={"AMX":V["AM_X"],"AMP":V["AM_P"],"AMQ64":V["AM_Q64"],"AMQ32":V["AM_Q32"],"AMR2":V["AM_R2"]}

def rz_avg(M):                       # the device xz() (w10_sleeve.py L139-142)
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz_avg(np.where(B,FE1,np.nan))
def mk(AM):
    ZA=rz_avg(np.where(B,np.asarray(AM,float),np.nan))
    ZAL=np.full_like(ZA,np.nan); ZAL[1:]=ZA[:-1]; ZAL=np.where(B,ZAL,np.nan)
    Rr=np.full(ZAL.shape,np.nan)
    for i in range(ZAL.shape[0]):
        ok=np.isfinite(ZAL[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=ZAL[i][ok]
        vx=float((x*x).sum()); b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
SIG={}
for nm,AM in AMS.items():
    Mt=mk(AM); p=D+"/sig/SL_%s.npz"%nm
    np.savez(p,symbols=sym,ts=ts,mat=Mt.astype(np.float32)); SIG[nm]=p
    print("sig",nm,"finite",float(np.isfinite(Mt).mean()),flush=True)

COMMON=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
CB={"STD":HC+"/calib/costb_fee_steady.json",
    "PWR":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"}
def run(job):
    arm,seed,cb=job
    tag="P6_%s_%s_s%s"%(arm,cb,seed)
    dst="%s/w10_ablation_series_%s.npz"%(OUT,tag)
    if os.path.exists(dst): return tag+" skip"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+COMMON+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+CB[cb],
                        "FEMAT_NPZ="+SIG[arm],"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t=time.time()
    with open("%s/logs/%s.log"%(D,tag),"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src="%s/probe_artifacts/w10_ablation_series_%s.npz"%(D,tag)
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%d"%(tag,rc)
    os.replace(src,dst)
    return "%-24s ok %5.1fs sha %s"%(tag,time.time()-t,hashlib.sha256(open(dst,"rb").read()).hexdigest()[:16])
if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    jobs=[("AMX","42","STD")]+[(a,s,"PWR") for a in AMS for s in ("42","2027")]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(run,jobs): print(r,flush=True)
    # PARITY GATE: AMX/STD/s42 must be BITWISE the archived SL_ORTHLAGA_STD_s42
    a=np.load(OUT+"/w10_ablation_series_P6_AMX_STD_s42.npz",allow_pickle=True)
    b=np.load("/workspace/uplift_2026-09-11/r3_xib/arms/w10_ablation_series_SL_ORTHLAGA_STD_s42.npz",allow_pickle=True)
    g={}
    for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
        x=np.asarray(a[k],float); y=np.asarray(b[k],float)
        nx=np.isnan(x); ny=np.isnan(y)
        g[k]={"bitwise":bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny])),
              "maxabs":float(np.nanmax(np.abs(x-y))) if x.shape==y.shape else None}
    json.dump(g,open(R+"/P6_SLEEVE_PARITY.json","w"),indent=1)
    print("SLEEVE_PARITY",json.dumps(g),flush=True)
    print("P6_BOOK_DONE")
