"""GATE P (round 8, BUILD 2). The TILT device with knobs OFF must reproduce the ARCHIVED A0 artifacts
BITWISE on d30_n2_c42_rec AND d30_n2_c42_W, all four cells (seat dyn/fix x seed 42/2027).
Structure copied verbatim from r7f2/gateP_r7.py (which passed 4/4); only DEV and ROOT change.
E-0826-D: the env whitelist is enumerated below and asserted against every env string passed."""
import numpy as np, os, subprocess, time, json, hashlib
HC="/workspace/review_scratch/health_check"
ROOT="/workspace/uplift_2026-09-11/r8b2/gateP"
D=ROOT+"/dev"
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
DEV="/workspace/uplift_2026-09-11/r8b2/w10_sleeve_tilt.py"
DEVSHA=hashlib.sha256(open(DEV,'rb').read()).hexdigest()
BASESHA=hashlib.sha256(open("/workspace/uplift_2026-09-11/w10_sleeve.py",'rb').read()).hexdigest()
print("tilt device sha256", DEVSHA); print("pinned base sha256", BASESHA)
assert BASESHA.startswith("b88e35a46b93d712"), "pinned base device moved"
assert DEVSHA.startswith("7dd6324acd361081"), "tilt device sha does not match the prereg"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY",
        "FSEED","FPRED","COSTB_JSON","OUT_TAG","W3FIX","TILT","TILT_TAU","TILT_K"]
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
def run(seat,seed):
    tag=f"GP8_A0_{seat}_s{seed}"
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if os.path.exists(src): return tag+" cached"
    env=dict(os.environ); env.update(OMP_NUM_THREADS="4",OPENBLAS_NUM_THREADS="4",MKL_NUM_THREADS="4")
    for k in list(env):
        if k.startswith("TILT"): env.pop(k)   # knobs OFF must mean ABSENT, not inherited
    ex=COMMON+[f"FSEED={seed}",f"FPRED=f10_A0_s{seed}.npy",
               "COSTB_JSON="+HC+"/calib/costb_fee_steady.json","OUT_TAG="+tag]
    if seat=="fix": ex.append("W3FIX=0.21,0,0.79")
    for e in ex: assert e.split("=",1)[0] in ENV_WL, "env key outside whitelist: "+e
    cmd=["env"]+ex+["/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%s rc=%d %.0fs"%(tag,rc,time.time()-t0)
from concurrent.futures import ThreadPoolExecutor
jobs=[(s,sd) for s in ("dyn","fix") for sd in (42,2027)]
t00=time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    for r in ex.map(lambda j: run(*j), jobs): print(r,flush=True)
print("wall %.0fs"%(time.time()-t00))
A=HC+"/dev_v4/probe_artifacts"
OUT={"device":DEV,"device_sha256":DEVSHA,"base_sha256":BASESHA,"env_whitelist":ENV_WL,"common_env":COMMON}
ok=True
for seat in ("dyn","fix"):
    for sd in (42,2027):
        mine=D+f"/probe_artifacts/w10_ablation_series_GP8_A0_{seat}_s{sd}.npz"
        arch=A+f"/w10_ablation_series_V4_A0_{seat}_s{sd}.npz"
        a=np.load(mine,allow_pickle=True); b=np.load(arch,allow_pickle=True)
        r={}
        for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
            x=np.asarray(a[k],float); y=np.asarray(b[k],float)
            nx=np.isnan(x); ny=np.isnan(y)
            bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
            r[k]={"bitwise":bw,"shape":list(x.shape),"maxabs":0.0 if bw else float(np.nanmax(np.abs(x-y)))}
            ok&=bw
        cfg=json.loads(str(a["config_json"]))
        r["cfg_self_sha256"]=cfg["HEALTH"]["device_sha256"]
        r["cfg_TILT"]=cfg["TILT"]; r["cfg_ncols"]=len([str(c) for c in a["cols"]])
        ok&= (r["cfg_self_sha256"]==DEVSHA) and cfg["TILT"]=="" and r["cfg_ncols"]==23
        OUT[f"{seat}_s{sd}"]=r
OUT["PASS"]=bool(ok)
json.dump(OUT,open(ROOT+"/GATE_P_r8.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
