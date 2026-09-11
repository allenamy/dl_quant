"""R8/BUILD-1 GATE P.  MUST PASS BEFORE ANY NUMBER.
My device tree, knobs OFF, FRESH run (artifacts deleted first) must reproduce the ARCHIVED A0 artifacts
w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027} on d30_n2_c42_rec AND _W BITWISE.
ENV whitelist asserted explicitly and recorded (E-0826-D)."""
import numpy as np, os, subprocess, time, json, hashlib
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r8_inbook"; D=R+"/dev"
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
def launch(tag, extra):
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if os.path.exists(src): os.remove(src)
    env=dict(os.environ); env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    cmd=["env"]+extra+["OUT_TAG="+tag,"/workspace/venv/bin/python",DEV]
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return tag,rc,round(time.time()-t0,1)," ".join(cmd)
def cmpbit(mine,arch):
    a=np.load(mine,allow_pickle=True); b=np.load(arch,allow_pickle=True)
    o={}
    for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
        x=np.asarray(a[k],float); y=np.asarray(b[k],float)
        nx=np.isnan(x); ny=np.isnan(y)
        bw=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
        o[k]={"bitwise":bw,"shape":list(x.shape),"maxabs":0.0 if bw else float(np.nanmax(np.abs(x-y)))}
    return o
jobs=[]
for seat in ("dyn","fix"):
    for sd in (42,2027):
        e=list(ENV_A0)+["FSEED=%d"%sd,"FPRED=f10_A0_s%d.npy"%sd,"COSTB_JSON="+COSTB_STD]
        if seat=="fix": e.append("W3FIX=0.21,0,0.79")
        jobs.append(("R8GP_A0_%s_s%d"%(seat,sd),e))
from concurrent.futures import ThreadPoolExecutor
OUT={"device":DEV,"device_sha256":DEV_SHA,"costb_PWR_sha256":hashlib.sha256(open(COSTB_PWR,"rb").read()).hexdigest(),
     "prereg_sha256":"83f4bed01cd90f9f415e0d2a89e173fb23ff8c89c2567633a99c923ddea03c8e",
     "ENV_A0":ENV_A0,"runs":{}}
with ThreadPoolExecutor(max_workers=4) as ex:
    for tag,rc,dt,cmd in ex.map(lambda j: launch(*j), jobs):
        OUT["runs"][tag]={"rc":rc,"sec":dt,"cmd":cmd}; print(tag,"rc",rc,dt,"s",flush=True)
A=HC+"/dev_v4/probe_artifacts"
ok=True
for seat in ("dyn","fix"):
    for sd in (42,2027):
        r=cmpbit(D+"/probe_artifacts/w10_ablation_series_R8GP_A0_%s_s%d.npz"%(seat,sd),
                 A+"/w10_ablation_series_V4_A0_%s_s%d.npz"%(seat,sd))
        OUT["GATE_P_%s_s%d"%(seat,sd)]=r; ok&=all(v["bitwise"] for v in r.values())
OUT["GATE_P_PASS"]=bool(ok)
json.dump(OUT,open(R+"/GATE_P.json","w"),indent=1)
print(json.dumps({k:v for k,v in OUT.items() if k!="runs"},indent=1))
