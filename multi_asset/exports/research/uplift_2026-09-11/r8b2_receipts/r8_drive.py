"""BUILD 2 driver. Runs, in one pass:
  (1) FIRST-HAND REPRODUCTION arms with the TILT device, knobs OFF, at the FITTED cost:
      A0 (LEGS=101 PHI=0.45), FUND (LEGS=001 PHI=0), KING (LEGS=100 PHI=0) -- each asserted BITWISE
      against the round-7 / round-3 archived artifact it is meant to reproduce.
  (2) The 9 DECLARED TILT ARMS at s42 (PREREG_r8_BUILD2 section 4).
E-0826-D: env whitelist enumerated and asserted on every env string."""
import numpy as np, os, subprocess, time, json, hashlib, sys
HC="/workspace/review_scratch/health_check"
ROOT="/workspace/uplift_2026-09-11/r8b2"; D=ROOT+"/dev"
for p in (D+"/logs", D+"/probe_artifacts", ROOT+"/out"): os.makedirs(p,exist_ok=True)
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
DEV=ROOT+"/w10_sleeve_tilt.py"
DEVSHA=hashlib.sha256(open(DEV,'rb').read()).hexdigest(); assert DEVSHA.startswith("7dd6324acd361081")
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
COSTSHA=hashlib.sha256(open(COSTB,'rb').read()).hexdigest(); assert COSTSHA.startswith("295b4e7b462373e4")
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY",
        "FSEED","FPRED","COSTB_JSON","OUT_TAG","TILT","TILT_TAU","TILT_K"]
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","UMASK_SCOPE=m1",
        "UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3,"COSTB_JSON="+COSTB]
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
A0E=["LEGS=101","PHI=0.45","FSEED=42","FPRED=f10_A0_s42.npy"]
JOBS=[("R8_A0_s42",A0E),
      ("R8_A0_s2027",["LEGS=101","PHI=0.45","FSEED=2027","FPRED=f10_A0_s2027.npy"]),
      ("R8_FUND",["LEGS=001","PHI=0","FSEED=42","FPRED=f10_A0_s42.npy"]),
      ("R8_KING",["LEGS=100","PHI=0","FSEED=42","FPRED=f10_A0_s42.npy"])]
GRID=[("S00","step","0.0"),("S25","step","0.25"),("S50","step","0.5"),("S75","step","0.75"),
      ("R00","ramp","0.0"),("R25","ramp","0.25"),("R50","ramp","0.5"),
      ("P05","pow","0.5"),("P10","pow","1.0")]
for nm,form,k in GRID:
    JOBS.append(("R8_%s_s42"%nm, A0E+["TILT="+form,"TILT_TAU=4.75","TILT_K="+k]))
from concurrent.futures import ThreadPoolExecutor
t00=time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(lambda j: run(*j), JOBS): print(r,flush=True)
print("wall %.0fs"%(time.time()-t00),flush=True)
# ---- bitwise reproduction assertions ----
def bw(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); nx=np.isnan(x); ny=np.isnan(y)
    return bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
REP={}
PAIRS=[("R8_A0_s42","/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz",("rec","W")),
       ("R8_A0_s2027","/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz",("rec","W")),
       ("R8_FUND","/workspace/uplift_2026-09-11/r7f2/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz",("d30_n2_c42_rec","d30_n2_c42_W")),
       ("R8_KING","/workspace/uplift_2026-09-11/r7f2/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz",("d30_n2_c42_rec","d30_n2_c42_W"))]
ok=True
for tag,ref,keys in PAIRS:
    a=np.load(D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag,allow_pickle=True)
    b=np.load(ref,allow_pickle=True)
    r={}
    for mk,rk in zip(("d30_n2_c42_rec","d30_n2_c42_W"),keys):
        r[rk]={"bitwise":bw(a[mk],b[rk]),"shape":list(np.asarray(a[mk]).shape)}
        ok&=r[rk]["bitwise"]
    r["ref"]=ref; r["ref_sha16"]=hashlib.sha256(open(ref,'rb').read()).hexdigest()[:16]
    REP[tag]=r; print("REPRO",tag,json.dumps(r),flush=True)
json.dump({"device":DEV,"device_sha256":DEVSHA,"costb_sha256":COSTSHA,"env_whitelist":ENV_WL,
           "common_env":COMMON,"jobs":[[t,e] for t,e in JOBS],"repro":REP,"REPRO_PASS":bool(ok)},
          open(ROOT+"/out/R8_DRIVE.json","w"),indent=1)
print("REPRO_PASS",ok)
print("DRIVE_DONE")
