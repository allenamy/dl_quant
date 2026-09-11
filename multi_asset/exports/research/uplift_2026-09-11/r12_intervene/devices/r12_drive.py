"""r12 driver. Device = w12_intervene.py (= PINNED w10_sleeve.py + r12 branches).
E-0826-D: env whitelist ENUMERATED and asserted on the EFFECTIVE strings passed to every child."""
import os, sys, json, time, hashlib, subprocess
import numpy as np
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; HC="/workspace/review_scratch/health_check"
R6=f"{U}/r6/out"; R9=f"{U}/r9"
DEV=f"{R}/w12_intervene.py"; PIN=f"{U}/w10_sleeve.py"; COSTB=f"{U}/r3k/costb_PWR_G230k.json"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
assert sha(PIN).startswith("b88e35a46b93d712"); assert sha(COSTB).startswith("295b4e7b462373e4")
DEVSHA=sha(DEV)
TREE=f"{R}/dev_ext"
LINKS={"pod_backup_2026-08-21/wide_fea_hist_meta.npz":f"{R6}/meta_newprod_v4_x0910.npz",
 "pod_backup_2026-08-21/slow_pred_hist_oos.npy":f"{R6}/SLOW_v4_x0910.npy",
 "pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz":f"{R6}/wide_panel_4h_v2ext_x0910.npz",
 "pod_backup_2026-08-21/nets_histv2_-30_2_42.npy":f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy",
 "pod_backup_2026-08-21/nets_histv2_0_0_0.npy":f"{HC}/dev_alt/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
 "dlw_2026-08-22":f"{R6}/dlw_v4raw_x0910",
 "f8_2026-08-22/preds/f10_v4RAWx_s42.npy":f"{R9}/out/f10_v4RAWx_s42.npy",
 "f8_2026-08-22/preds/f10_v4RAWx_s2027.npy":f"{R9}/out/f10_v4RAWx_s2027.npy"}
for sub in ("logs","probe_artifacts","pod_backup_2026-08-21","f8_2026-08-22/preds"): os.makedirs(f"{TREE}/{sub}",exist_ok=True)
for rel,src in LINKS.items():
    assert os.path.exists(src), src
    d=f"{TREE}/{rel}"
    if os.path.islink(d) or os.path.exists(d): os.remove(d)
    os.symlink(src,d)
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY",
        "FSEED","FPRED","COSTB_JSON","OUT_TAG","CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A"]
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","COSTB_JSON="+COSTB,
        "SLOW_NPY="+R6+"/SLOW_v4_x0910.npy"]
def seed_env(s): return [f"FSEED={s}", f"FPRED=f10_v4RAWx_s{s}.npy"]
JOBS=[]
def add(tag,extra,seed="42"): JOBS.append((tag,COMMON+seed_env(seed)+extra))
# ---- GATE P: every branch OFF must be bitwise-identical to the archived R9_A1x_ext_s42 ----
add("R12_GATEP_s42",[])
# ---- I-1 CEM: 3 quantiles x 2 modes = 6 ----
for q in ("0.90","0.95","0.99"):
    for md in ("neutral","derisk"):
        add("R12_CEM_%s_%s_s42"%(q.replace("0.",""),md),["CEM_Q="+q,"CEM_MODE="+md])
# ---- I-3 BYP: 3 states x 2 q at a=1.00, + 3 states at q=0.95 a=0.30 = 9 ----
for st in ("rally","rev","either"):
    for q in ("0.90","0.95"):
        add("R12_BYP_%s_%s_a100_s42"%(st,q.replace("0.","")),["BYP_STATE="+st,"BYP_Q="+q,"BYP_A=1.00"])
    add("R12_BYP_%s_95_a030_s42"%st,["BYP_STATE="+st,"BYP_Q=0.95","BYP_A=0.30"])
def run(job):
    tag,ex=job; ex=ex+["OUT_TAG="+tag]
    for e in ex: assert e.split("=",1)[0] in ENV_WL, "env outside whitelist: "+e
    dst=f"{TREE}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if os.path.exists(dst): return tag+" cached"
    env=dict(os.environ)
    for k in list(env):
        if k in ENV_WL or k in ("W3FIX","SEATF10","KMOD","KTAIL","KMOD_F10","KMOD_AGREE","SEATNET",
            "FUNDSCALE","FEMAT_NPZ","TRADE_TOPN","REF_SKIP","RNSM","FTPOS","LTRIM_TH","CDAMP","SLEEVE"):
            env.pop(k,None)
    env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    t0=time.time()
    with open(f"{TREE}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=TREE,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%-34s rc=%d %5.0fs"%(tag,rc,time.time()-t0)
if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(run,JOBS): print(r,"%.0fs"%(time.time()-t0),flush=True)
    REC={"device":DEV,"device_sha256":DEVSHA,"pinned_src_sha256":sha(PIN),"cost_sha256":sha(COSTB),
         "prereg_sha256":"17dd2db7b116b2625f6e7eacab7caf9eb025876e1a3f564f32429f31a2ea551f",
         "env_whitelist":ENV_WL,"common_env":COMMON,"tree":TREE,"links":LINKS,
         "jobs":[{"tag":t,"env":e} for t,e in JOBS],
         "done_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"self_sha256":sha(os.path.abspath(__file__))}
    json.dump(REC,open(f"{R}/out/RUN_ENV_r12.json","w"),indent=1)
    print("DRIVE_DONE",len(JOBS),"jobs")
