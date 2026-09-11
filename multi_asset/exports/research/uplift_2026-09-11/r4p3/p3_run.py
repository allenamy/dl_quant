"""ROUND-4 P3 step 0+1. GATE P (fresh, knobs-off, bitwise vs archived A0) and the two
missing arms at the FITTED cost model costb_PWR_G230k.json:
  SL_ORTHLAG  = standalone orthogonalised Amihud sleeve (LEGS=001, PHI=0, FTRIM=off)
  IB_PAR      = the argsort-ranked fund-leg parity arm (LEGS=101) -- ranking-hole diagnostic
Signal construction copied VERBATIM from infra1_cost/reprice.py so my sleeve is the SAME
object round 1-3 measured. Also re-runs SL_ORTHLAG at STD to prove bitwise identity with
the archived SL_ORTHLAG_STD_s42.npz.
Device = /workspace/uplift_2026-09-11/w10_sleeve.py, UNMODIFIED, knobs off.
"""
import numpy as np, os, subprocess, time, json, hashlib, sys
from concurrent.futures import ThreadPoolExecutor
HC="/workspace/review_scratch/health_check"
U="/workspace/uplift_2026-09-11"
R=U+"/r4p3"; D=R+"/dev"
for p in (D+"/logs",D+"/probe_artifacts",D+"/sig",R+"/arms",R+"/out"): os.makedirs(p,exist_ok=True)
BK=D+"/pod_backup_2026-08-21"; os.makedirs(BK,exist_ok=True)
LINKS={"nets_histv2_-30_2_42.npy":"/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
       "nets_histv2_0_0_0.npy":"/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
       "slow_pred_hist_oos.npy":"/workspace/review_scratch/king_v4/SLOW_v4.npy",
       "wide_fea_hist_meta.npz":"/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
       "wide_panel_4h_hist_v2.npz":"/workspace/data/wide_panel_4h_v2ext.npz"}
for k,v in LINKS.items():
    t=BK+"/"+k
    if not os.path.islink(t): os.symlink(v,t)
for k,v in {"dlw_2026-08-22":"/workspace/dlw_v4raw","f8_2026-08-22":HC+"/dev_v4/f8_2026-08-22"}.items():
    if not os.path.islink(D+"/"+k): os.symlink(v,D+"/"+k)
DEV=U+"/w10_sleeve.py"
DEVSHA=hashlib.sha256(open(DEV,'rb').read()).hexdigest()
print("device sha256",DEVSHA,flush=True)
assert DEVSHA.startswith("b88e35a46b93d712"), DEVSHA
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
PWR=U+"/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(PWR,'rb').read()).hexdigest().startswith("295b4e7b462373e4")
STD=HC+"/calib/costb_fee_steady.json"

def launch(tag,extra,env_extra=None):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+extra+["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%s rc=%d %.0fs"%(tag,rc,time.time()-t0)

# ---------------- GATE P ----------------
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
def gp(job):
    seat,seed=job
    tag=f"P3GP_A0_{seat}_s{seed}"
    if os.path.exists(D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag): return tag+" cached"
    ex=COMMON+[f"FSEED={seed}",f"FPRED=f10_A0_s{seed}.npy","COSTB_JSON="+HC+"/calib/costb_fee_steady.json"]
    if seat=="fix": ex=ex+["W3FIX=0.21,0,0.79"]
    return launch(tag,ex)

# ---------------- signals (VERBATIM from infra1_cost/reprice.py) ----------------
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
AM=np.asarray(PW["f_amihud_24h"],float)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan)); ZA=rz(np.where(B,AM,np.nan))
ZA_LAG=np.full_like(ZA,np.nan); ZA_LAG[1:]=ZA[:-1]; ZA_LAG=np.where(B,ZA_LAG,np.nan)
def orth(Z):
    Rm=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rm[i][ok]=y-b*x
    return Rm
ORTHLAG=orth(ZA_LAG); LAG50=0.5*ZF+0.5*ZA_LAG
SLCOM=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
  "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz",
  "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def IBCOM(seed):
    return ["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3,
      f"FSEED={seed}",f"FPRED=f10_A0_s{seed}.npy"]
def arm(job):
    tag,M,base,costb=job
    if os.path.exists(R+"/arms/"+tag+".npz"): return tag+" skip"
    f=D+"/sig/"+tag+".npz"; np.savez(f,symbols=sym,ts=ts,mat=M.astype(np.float32))
    r=launch(tag,base+["COSTB_JSON="+costb,"FEMAT_NPZ="+f])
    src=D+"/probe_artifacts/w10_ablation_series_"+tag+".npz"
    if not os.path.exists(src): return "FAIL "+r
    Z=np.load(src,allow_pickle=True)
    np.savez_compressed(R+"/arms/"+tag+".npz",cols=Z["cols"],rec=Z["d30_n2_c42_rec"],config_json=Z["config_json"])
    os.remove(src); os.remove(f)
    return r
JOBS=[("SL_ORTHLAG_STD_s42",ORTHLAG,SLCOM,STD),
      ("SL_ORTHLAG_PWR230k_s42",ORTHLAG,SLCOM,PWR),
      ("IB_PAR_PWR230k_s42",ZF,IBCOM(42),PWR),
      ("IB_PAR_PWR230k_s2027",ZF,IBCOM(2027),PWR),
      ("IB_LAG50_PWR230k_s42",LAG50,IBCOM(42),PWR),
      ("IB_LAG50_PWR230k_s2027",LAG50,IBCOM(2027),PWR)]
with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(gp,[(s,sd) for s in ("dyn","fix") for sd in (42,2027)]): print(r,flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(arm,JOBS): print(r,flush=True)

# ---------------- verdicts ----------------
A=HC+"/dev_v4/probe_artifacts"
OUT={"device":DEV,"device_sha256":DEVSHA,"costb_PWR_sha256":hashlib.sha256(open(PWR,'rb').read()).hexdigest()}
ok=True
for seat in ("dyn","fix"):
    for sd in (42,2027):
        a=np.load(D+f"/probe_artifacts/w10_ablation_series_P3GP_A0_{seat}_s{sd}.npz",allow_pickle=True)
        b=np.load(A+f"/w10_ablation_series_V4_A0_{seat}_s{sd}.npz",allow_pickle=True)
        r={}
        for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
            x=np.asarray(a[k],float); y=np.asarray(b[k],float)
            nx=np.isnan(x); ny=np.isnan(y)
            bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
            r[k]={"bitwise":bw,"shape":list(x.shape),"maxabs":0.0 if bw else float(np.nanmax(np.abs(x-y)))}
            ok&=bw
        OUT[f"GATEP_{seat}_s{sd}"]=r
OUT["GATE_P_PASS"]=bool(ok)
# sleeve parity vs archived
mine=np.load(R+"/arms/SL_ORTHLAG_STD_s42.npz",allow_pickle=True)["rec"].astype(float)
arch=np.load(U+"/infra1_cost/out/SL_ORTHLAG_STD_s42.npz",allow_pickle=True)["rec"].astype(float)
nx=np.isnan(mine); ny=np.isnan(arch)
bw=bool(mine.shape==arch.shape and np.array_equal(nx,ny) and np.array_equal(mine[~nx],arch[~ny]))
OUT["SLEEVE_PARITY_vs_archived_STD"]={"bitwise":bw,"shape":list(mine.shape),
   "maxabs":0.0 if bw else float(np.nanmax(np.abs(mine-arch)))}
json.dump(OUT,open(R+"/GATE_P_r4p3.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
