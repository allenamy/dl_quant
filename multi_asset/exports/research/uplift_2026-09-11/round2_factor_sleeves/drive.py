"""Round-2 sleeve driver. Device = /workspace/uplift_2026-09-11/w10_sleeve.py (sha256 b88e35a4...),
all six uplift knobs left at their defaults => GATE P bitwise path (verified 2026-09-11, 8/8 arrays).
Standalone sleeve config copied verbatim from round 1's SLCOM."""
import numpy as np, os, subprocess, time, sys, json, hashlib
HC="/workspace/review_scratch/health_check"
R ="/workspace/uplift_2026-09-11/r2_factor"
D =R+"/dev"; OUT=R+"/out"; FT=R+"/feat"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
PAN=D+"/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
P=np.load(PAN,allow_pickle=True); ts=P["ts"].astype(np.int64); sym=P["symbols"]
B=np.load(FT+"/_B.npy"); ZFUND=np.load(FT+"/_ZFUND.npy").astype(np.float64)

def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def orth(Z):
    """per-anchor cross-sectional OLS residual of Z on the DEPLOYED fund rank (round-1 operator, verbatim)"""
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZFUND[i])
        if ok.sum()<10: continue
        x=ZFUND[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
def permute(M,seed):
    rng=np.random.default_rng(seed); Pm=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        ok=np.isfinite(M[i]); n=ok.sum()
        if n>=10:
            v=M[i,ok].copy(); rng.shuffle(v); Pm[i,ok]=v
    return Pm

SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+HC+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
IBCOM=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "COSTB_JSON="+HC+"/calib/costb_fee_steady.json",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy","FSEED=42","FPRED=f10_A0_s42.npy"]

def run(tag,M,common,nthread=4):
    if os.path.exists(OUT+"/"+tag+".npz"): return "skip"
    f=D+"/sig/"+tag+".npz"
    np.savez(f,symbols=sym,ts=ts,mat=np.asarray(M,np.float32))
    env=dict(os.environ); env.update(OMP_NUM_THREADS=str(nthread),OPENBLAS_NUM_THREADS=str(nthread),MKL_NUM_THREADS=str(nthread))
    cmd=["env"]+common+["FEMAT_NPZ="+f,"OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    with open(D+"/logs/"+tag+".log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=R+"/pa/w10_ablation_series_"+tag+".npz"
    if rc!=0 or not os.path.exists(src):
        os.remove(f); return "FAIL rc=%d"%rc
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(OUT+"/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    for ex in (R+"/pa/w10_ablation_summary_"+tag+".json",):
        if os.path.exists(ex): os.remove(ex)
    return "ok"

FAMS=json.load(open(R+"/feat_manifest.json"))["families"]
if __name__=="__main__":
    mode=sys.argv[1]; only=sys.argv[2:] 
    os.makedirs(OUT,exist_ok=True)
    t0=time.time()
    for fam in FAMS:
        if only and fam not in only: continue
        F=np.load(FT+"/"+fam+".npy").astype(np.float64)
        F=np.where(B,F,np.nan)
        for sgn,tg in ((1.0,"p"),(-1.0,"m")):
            Z=rz(sgn*F)
            if mode=="orth":
                st=run("SL2_ORTH_%s__%s"%(fam,tg),orth(Z),SLCOM)
                print("%-28s %s  %6.1fs"%("SL2_ORTH_%s__%s"%(fam,tg),st,time.time()-t0),flush=True)
            elif mode=="raw":
                st=run("SL2_RAW_%s__%s"%(fam,tg),Z,SLCOM)
                print("%-28s %s  %6.1fs"%("SL2_RAW_%s__%s"%(fam,tg),st,time.time()-t0),flush=True)
            elif mode=="perm":
                Zp=rz(permute(sgn*F,20260911))
                st=run("SL2_PERM_%s__%s"%(fam,tg),orth(Zp),SLCOM)
                print("%-28s %s  %6.1fs"%("SL2_PERM_%s__%s"%(fam,tg),st,time.time()-t0),flush=True)
    print("DONE",time.time()-t0)
