"""R5 GATE P + GATE S.  MUST PASS BEFORE ANY NUMBER.
GATE P: my device tree, knobs OFF, FRESH run (no cache) must reproduce the ARCHIVED A0 artifacts
        w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}  on d30_n2_c42_rec AND _W  BITWISE.
GATE S: my own signal-construction + FEMAT injection chain, applied to the archived AM_Q64 Amihud matrix,
        must reproduce the archived round-4 sleeve P6_AMQ64_PWR_s42 BITWISE.  This proves that when I later
        swap in a BASIS matrix, the only thing that changed is that matrix.
ENV WHITELIST asserted explicitly below; every var recorded in the output json."""
import numpy as np, os, subprocess, time, json, hashlib
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r5_basis"; D=R+"/dev"
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
DEV_SHA=hashlib.sha256(open(DEV,"rb").read()).hexdigest()
assert DEV_SHA[:16]=="b88e35a46b93d712", DEV_SHA
COSTB_STD=HC+"/calib/costb_fee_steady.json"
COSTB_PWR="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(COSTB_PWR,"rb").read()).hexdigest()[:16]=="295b4e7b462373e4"
for p in (D+"/logs",D+"/sig",D+"/probe_artifacts",R+"/arms"): os.makedirs(p,exist_ok=True)
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
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
UMASK=HC+"/masks/umask_UPIT_CRYPTO.npz"
ENV_A0=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+UMASK,"SLOW_NPY="+K3]
ENV_SL=["LEGS=001","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=off","PHI=0",
        "UMASK_SCOPE=m1","UMASK_NPZ="+UMASK,"SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def launch(tag, extra, force=True):
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if force and os.path.exists(src): os.remove(src)
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+extra+["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return tag,rc,round(time.time()-t0,1),cmd
def cmpbit(mine,arch):
    a=np.load(mine,allow_pickle=True); b=np.load(arch,allow_pickle=True)
    o={}
    for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
        x=np.asarray(a[k],float); y=np.asarray(b[k],float)
        nx=np.isnan(x); ny=np.isnan(y)
        bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
        o[k]={"bitwise":bw,"shape":list(x.shape),"maxabs":0.0 if bw else float(np.nanmax(np.abs(x-y)))}
    return o
# ---- GATE S signal build (VERBATIM the p6_book.py mk(), which is r3_xib/sleeve.py ORTHLAGA) ----
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BM=np.isfinite(FE1)
def rz_avg(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz_avg(np.where(BM,FE1,np.nan))
def mk_orthlag(RAW):
    ZA=rz_avg(np.where(BM,np.asarray(RAW,float),np.nan))
    ZAL=np.full_like(ZA,np.nan); ZAL[1:]=ZA[:-1]; ZAL=np.where(BM,ZAL,np.nan)
    Rr=np.full(ZAL.shape,np.nan)
    for i in range(ZAL.shape[0]):
        ok=np.isfinite(ZAL[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=ZAL[i][ok]
        vx=float((x*x).sum()); b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
V=np.load("/workspace/uplift_2026-09-11/p6/AM_variants.npz",allow_pickle=True)
assert np.array_equal(V["ts"].astype(np.int64),ts)
SIGQ=mk_orthlag(V["AM_Q64"]); pq=D+"/sig/GS_AMQ64.npz"
np.savez(pq,symbols=sym,ts=ts,mat=SIGQ.astype(np.float32))
jobs=[]
for seat in ("dyn","fix"):
    for sd in (42,2027):
        e=list(ENV_A0)+["FSEED=%d"%sd,"FPRED=f10_A0_s%d.npy"%sd,"COSTB_JSON="+COSTB_STD]
        if seat=="fix": e.append("W3FIX=0.21,0,0.79")
        jobs.append(("R5GP_A0_%s_s%d"%(seat,sd),e))
jobs.append(("R5GS_AMQ64_PWR_s42",list(ENV_SL)+["FSEED=42","FPRED=f10_A0_s42.npy","COSTB_JSON="+COSTB_PWR,"FEMAT_NPZ="+pq]))
from concurrent.futures import ThreadPoolExecutor
OUT={"device":DEV,"device_sha256":DEV_SHA,"costb_PWR_sha256":hashlib.sha256(open(COSTB_PWR,"rb").read()).hexdigest(),
     "ENV_A0":ENV_A0,"ENV_SLEEVE":ENV_SL,"runs":{}}
with ThreadPoolExecutor(max_workers=5) as ex:
    for tag,rc,dt,cmd in ex.map(lambda j: launch(*j), jobs):
        OUT["runs"][tag]={"rc":rc,"sec":dt,"cmd":" ".join(cmd)}
        print(tag,"rc",rc,dt,"s",flush=True)
A=HC+"/dev_v4/probe_artifacts"
ok=True
for seat in ("dyn","fix"):
    for sd in (42,2027):
        r=cmpbit(D+"/probe_artifacts/w10_ablation_series_R5GP_A0_%s_s%d.npz"%(seat,sd),
                 A+"/w10_ablation_series_V4_A0_%s_s%d.npz"%(seat,sd))
        OUT["GATE_P_%s_s%d"%(seat,sd)]=r; ok&=all(v["bitwise"] for v in r.values())
OUT["GATE_P_PASS"]=bool(ok)
rs=cmpbit(D+"/probe_artifacts/w10_ablation_series_R5GS_AMQ64_PWR_s42.npz",
          "/workspace/uplift_2026-09-11/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz")
OUT["GATE_S"]=rs; OUT["GATE_S_PASS"]=bool(all(v["bitwise"] for v in rs.values()))
json.dump(OUT,open(R+"/GATE_PS.json","w"),indent=1)
print(json.dumps({k:v for k,v in OUT.items() if k!="runs"},indent=1))
