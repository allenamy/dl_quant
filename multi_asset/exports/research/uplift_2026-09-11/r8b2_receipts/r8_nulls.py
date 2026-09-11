"""BUILD 2, prereg test (d): TURNOVER-MATCHED NULLS for the dispersion seat tilt.
The per-anchor PERMUTATION placebo is DEFECTIVE (raises turnover 2.6-7.7x, reads negative on churn cost).
The right null here keeps the tilt multiplier's marginal distribution AND its lag-1 persistence exactly,
and destroys only its time alignment with the book: feed the device a SHIFTED / ROTATED sigma series.
  SHIFT_k : sigma advanced by k anchors (sig[t] <- sig[t-k]); first k anchors get NaN => no tilt
  ROT_j   : circular rotation of the sigma series by a fixed pseudorandom offset
WIRING CHECK: SHIFT0 (the true series fed through the same path) must reproduce the device-1 arm BITWISE.
Device 2 = device 1 + TILT_SIG_NPZ; with TILT_SIG_NPZ unset it is bitwise-identical to device 1 (GATE P2)."""
import numpy as np, os, subprocess, time, json, hashlib
HC="/workspace/review_scratch/health_check"
ROOT="/workspace/uplift_2026-09-11/r8b2"; D=ROOT+"/dev2"; SIG=ROOT+"/sig"
for p in (D+"/logs", D+"/probe_artifacts", SIG, ROOT+"/out"): os.makedirs(p,exist_ok=True)
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
DEV=ROOT+"/w10_sleeve_tilt2.py"
DEVSHA=hashlib.sha256(open(DEV,'rb').read()).hexdigest(); assert DEVSHA.startswith("0ff501815bdc564f")
DEV1=ROOT+"/w10_sleeve_tilt.py"
assert hashlib.sha256(open(DEV1,'rb').read()).hexdigest().startswith("7dd6324acd361081")
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
assert hashlib.sha256(open(COSTB,'rb').read()).hexdigest().startswith("295b4e7b462373e4")
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY",
        "FSEED","FPRED","COSTB_JSON","OUT_TAG","TILT","TILT_TAU","TILT_K","TILT_SIG_NPZ","W3FIX"]
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","UMASK_SCOPE=m1",
        "UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3,"COSTB_JSON="+COSTB]
# ---- the sigma series on the device's own anchor axis ----
MT=np.load(BK+"/wide_fea_hist_meta.npz",allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64)
S=np.load("/workspace/uplift_2026-09-11/r7f1/out/sigma_variants.npz",allow_pickle=True)
C=[str(c) for c in S["cols"]]; SR_=S["rec"]; GL=dict(zip(SR_[:,0].astype(np.int64),SR_[:,C.index("LIVE_sig")]))
sig=np.array([GL.get(int(t),np.nan) for t in E_ts])
print("sigma series on device axis: n=%d finite=%d"%(len(sig),int(np.isfinite(sig).sum())),flush=True)
def wsig(name,arr):
    f=SIG+"/%s.npz"%name; np.savez(f,ts=E_ts,sig=np.asarray(arr,float)); return f
FEEDS={"SHIFT0":wsig("SHIFT0",sig)}
for k in (101,503,1009):
    q=np.full_like(sig,np.nan); q[k:]=sig[:-k]; FEEDS["SHIFT%d"%k]=wsig("SHIFT%d"%k,q)
for j in (1,2,3):
    off=int(np.random.default_rng([20260912,j]).integers(1500,len(sig)-1500))
    FEEDS["ROT%d"%j]=wsig("ROT%d"%j,np.roll(sig,off)); print("ROT%d offset %d"%(j,off),flush=True)
A0E=["LEGS=101","PHI=0.45","FSEED=42","FPRED=f10_A0_s42.npy"]
TILTS={"S00":["TILT=step","TILT_TAU=4.75","TILT_K=0.0"],"P10":["TILT=pow","TILT_TAU=4.75","TILT_K=1.0"]}
def run(tag, extra):
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if os.path.exists(src): return tag+" cached"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    for k in list(env):
        if k.startswith("TILT"): env.pop(k)
    ex=COMMON+extra+["OUT_TAG="+tag]
    for e in ex: assert e.split("=",1)[0] in ENV_WL, "env key outside whitelist: "+e
    cmd=["env"]+ex+["/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%s rc=%d %.0fs"%(tag,rc,time.time()-t0)
JOBS=[]
# GATE P2: device 2, ALL tilt knobs off, must reproduce the archived A0 (fee_steady cost, both seats/seeds)
for seat in ("dyn","fix"):
    for sd in (42,2027):
        e=["LEGS=101","PHI=0.45","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero",
           "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3,
           "FSEED=%d"%sd,"FPRED=f10_A0_s%d.npy"%sd,"COSTB_JSON="+HC+"/calib/costb_fee_steady.json"]
        if seat=="fix": e=e+["W3FIX=0.21,0,0.79"]
        JOBS.append(("GP8B_A0_%s_s%d"%(seat,sd),e))
for arm,tk in TILTS.items():
    for fn,fp in FEEDS.items():
        JOBS.append(("R8N_%s_%s"%(arm,fn), A0E+tk+["TILT_SIG_NPZ="+fp]))
from concurrent.futures import ThreadPoolExecutor
t00=time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(lambda j: run(*j), JOBS): print(r,flush=True)
print("wall %.0fs"%(time.time()-t00),flush=True)
def bw(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); nx=np.isnan(x); ny=np.isnan(y)
    return bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
OUT={"device2":DEV,"device2_sha256":DEVSHA,"device1_sha256":hashlib.sha256(open(DEV1,'rb').read()).hexdigest(),
     "env_whitelist":ENV_WL,"common_env":COMMON,"feeds":FEEDS,"jobs":[[t,e] for t,e in JOBS]}
# GATE P2
AR=HC+"/dev_v4/probe_artifacts"; okp=True; gp={}
for seat in ("dyn","fix"):
    for sd in (42,2027):
        a=np.load(D+"/probe_artifacts/w10_ablation_series_GP8B_A0_%s_s%d.npz"%(seat,sd),allow_pickle=True)
        b=np.load(AR+"/w10_ablation_series_V4_A0_%s_s%d.npz"%(seat,sd),allow_pickle=True)
        r={k:bw(a[k],b[k]) for k in ("d30_n2_c42_rec","d30_n2_c42_W")}
        cfg=json.loads(str(a["config_json"])); r["cfg_self_sha"]=cfg["HEALTH"]["device_sha256"]
        r["cfg_TILT"]=cfg["TILT"]; r["cfg_TILT_SIG_NPZ"]=cfg["TILT_SIG_NPZ"]
        okp&= r["d30_n2_c42_rec"] and r["d30_n2_c42_W"] and r["cfg_self_sha"]==DEVSHA
        gp["%s_s%d"%(seat,sd)]=r
OUT["GATE_P2"]=gp; OUT["GATE_P2_PASS"]=bool(okp); print("GATE_P2_PASS",okp,flush=True)
# WIRING CHECK: SHIFT0 == device-1 arm, bitwise
wc={}; okw=True
for arm in TILTS:
    a=np.load(D+"/probe_artifacts/w10_ablation_series_R8N_%s_SHIFT0.npz"%arm,allow_pickle=True)
    b=np.load(ROOT+"/dev/probe_artifacts/w10_ablation_series_R8_%s_s42.npz"%arm,allow_pickle=True)
    r={k:bw(a[k],b[k]) for k in ("d30_n2_c42_rec","d30_n2_c42_W")}
    okw&= r["d30_n2_c42_rec"] and r["d30_n2_c42_W"]; wc[arm]=r
OUT["WIRING_SHIFT0_EQ_DEVICE1"]=wc; OUT["WIRING_PASS"]=bool(okw); print("WIRING_PASS",okw,flush=True)
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(ROOT+"/out/R8_NULLS_DRIVE.json","w"),indent=1)
print("NULLS_DRIVE_DONE")
