"""ANGLE 2 (round 5) GATE P. Device /workspace/uplift_2026-09-11/w10_sleeve.py UNMODIFIED, knobs OFF.
Must reproduce archived V4_A0_{dyn,fix}_s{42,2027} d30_n2_c42_rec AND _W BITWISE.
Tree/env copied VERBATIM from r4_p1/gateP.py. Only OUT_TAG prefix and dir differ.
ENV WHITELIST asserted explicitly (E-0826-D)."""
import numpy as np, os, sys, subprocess, time, json, hashlib
HC="/workspace/review_scratch/health_check"
ROOT="/workspace/uplift_2026-09-11/r5a2"; D=ROOT+"/dev"
for p in (D+"/logs",D+"/probe_artifacts",ROOT+"/out",ROOT+"/sig",ROOT+"/arms"): os.makedirs(p,exist_ok=True)
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
DEV="/workspace/uplift_2026-09-11/w10_sleeve.py"
print("device sha256",hashlib.sha256(open(DEV,"rb").read()).hexdigest(),flush=True)
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
# --- ENV WHITELIST (every variable the device reads; unlisted => device default, asserted below) ---
WHITELIST=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ",
           "SLOW_NPY","FSEED","FPRED","COSTB_JSON","W3FIX","FEMAT_NPZ","OUT_TAG",
           "OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"]
DEFAULTED=["LTRIM_TH","CDAMP","FTRIM_TH","FTPOS","RNSM","SLEEVE","SEATNET","SEATF10","KTAIL",
           "KMOD","KMOD_AGREE","KMOD_F10","KMOD_L","FUNDSCALE","TRADE_TOPN","REF_SKIP"]
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
def run(seat,seed):
    tag="R5A2P_A0_%s_s%s"%(seat,seed)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if os.path.exists(src): return tag+" cached"
    env={k:v for k,v in os.environ.items() if k not in WHITELIST and k not in DEFAULTED}
    for v in DEFAULTED: assert v not in env, v
    env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    ex=COMMON+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,
               "COSTB_JSON="+HC+"/calib/costb_fee_steady.json","OUT_TAG="+tag]
    if seat=="fix": ex.append("W3FIX=0.21,0,0.79")
    for e in ex: assert e.split("=")[0] in WHITELIST, e
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%s rc=%d %.0fs"%(tag,rc,time.time()-t0)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as ex:
    for r in ex.map(lambda j: run(*j),[(s,sd) for s in ("dyn","fix") for sd in (42,2027)]): print(r,flush=True)
A=HC+"/dev_v4/probe_artifacts"
OUT={"device":DEV,"device_sha256":hashlib.sha256(open(DEV,"rb").read()).hexdigest(),
     "env_whitelist":WHITELIST,"env_defaulted":DEFAULTED}
ok=True
for seat in ("dyn","fix"):
    for sd in (42,2027):
        a=np.load(D+"/probe_artifacts/w10_ablation_series_R5A2P_A0_%s_s%d.npz"%(seat,sd),allow_pickle=True)
        b=np.load(A+"/w10_ablation_series_V4_A0_%s_s%d.npz"%(seat,sd),allow_pickle=True)
        r={}
        for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
            x=np.asarray(a[k],float); y=np.asarray(b[k],float)
            nx=np.isnan(x); ny=np.isnan(y)
            bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
            r[k]={"bitwise":bw,"shape":list(x.shape),"mean_absdiff":0.0 if bw else float(np.nanmean(np.abs(x-y)))}
            ok&=bw
        OUT["%s_s%d"%(seat,sd)]=r
OUT["PASS"]=bool(ok)
json.dump(OUT,open(ROOT+"/GATE_P_r5a2.json","w"),indent=1)
print(json.dumps({k:(v if k!="env_whitelist" and k!="env_defaulted" else "...") for k,v in OUT.items()},indent=1))
