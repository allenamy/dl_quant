"""r12 turnover-matched NULLS + second seed.
Null construction (declared before any null number, amends PREREG_r12 §1 by SPECIFYING the 6 nulls
for a threshold rule; family names and rng seeds copied VERBATIM from r3_attack_b9646/null.py):
  SHIFT_k  (k=101,503,1009): the arm's OWN fire mask advanced by k anchors  -> timing nullified,
           firing COUNT preserved exactly => turnover-matched by construction.
  RELAB_k  (k=1,2,3, rng default_rng([4242,k])): a single fixed symbol permutation applied to the
           funding row used for RANKING only (the carry actually paid stays the true panel)
           -> name selection nullified, firing times and count preserved exactly.
E-0826-D: env whitelist enumerated + asserted."""
import os, sys, json, time, hashlib, subprocess, glob
import numpy as np
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; HC="/workspace/review_scratch/health_check"
R6=f"{U}/r6/out"; R9=f"{U}/r9"; TREE=f"{R}/dev_ext"; T=f"{TREE}/probe_artifacts"
DEV=f"{R}/w12b_intervene.py"; COSTB=f"{U}/r3k/costb_PWR_G230k.json"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
os.makedirs(f"{R}/nullsig",exist_ok=True)
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY",
        "FSEED","FPRED","COSTB_JSON","OUT_TAG","CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","R12_NULL"]
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
        "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","COSTB_JSON="+COSTB,
        "SLOW_NPY="+R6+"/SLOW_v4_x0910.npy"]
DC=["ts","bill_pre","bill_post","cem_fire","cem_n","cem_th","byp_fire","a_ema","s6","byp_q","mkt_med"]
def diag(tag):
    Z=np.load(f"{T}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    return np.asarray(Z["d30_n2_c42_DIAG"],float)
NW=829
JOBS=[]
def mknull(arm_tag, fire_col, base_env):
    D=diag(arm_tag); ts=D[:,0].astype(np.int64); f=D[:,DC.index(fire_col)]>0.5
    for k in (101,503,1009):
        q=np.zeros(len(f),bool); q[k:]=f[:-k]
        assert q.sum()<=f.sum()
        p=f"{R}/nullsig/{arm_tag}_SHIFT{k}.npz"; np.savez(p,ts=ts,force_fire=q)
        JOBS.append((f"{arm_tag}_NULL_SHIFT{k}", base_env+["R12_NULL="+p]))
    if arm_tag.startswith("R12_CEM"):
        for k in (1,2,3):
            rng=np.random.default_rng([4242,k]); pi=rng.permutation(NW)
            p=f"{R}/nullsig/{arm_tag}_RELAB{k}.npz"; np.savez(p,ts=ts,force_fire=f,sym_perm=pi)
            JOBS.append((f"{arm_tag}_NULL_RELAB{k}", base_env+["R12_NULL="+p]))
    else:
        for k in (1,2,3):
            rng=np.random.default_rng([4242,k]); q=rng.permutation(f)   # same count, random times
            p=f"{R}/nullsig/{arm_tag}_RELAB{k}.npz"; np.savez(p,ts=ts,force_fire=q)
            JOBS.append((f"{arm_tag}_NULL_RELAB{k}", base_env+["R12_NULL="+p]))
def seedenv(s): return [f"FSEED={s}",f"FPRED=f10_v4RAWx_s{s}.npy"]
# --- device-integrity re-gate on w12b (all branches off, both seeds) ---
JOBS.append(("R12B_GATEP_s42",COMMON+seedenv("42")))
# --- second seed for the informative arms ---
SECOND=[("R12_CEM_99_neutral",["CEM_Q=0.99","CEM_MODE=neutral"]),
        ("R12_CEM_95_neutral",["CEM_Q=0.95","CEM_MODE=neutral"]),
        ("R12_CEM_99_derisk", ["CEM_Q=0.99","CEM_MODE=derisk"]),
        ("R12_CEM_90_neutral",["CEM_Q=0.90","CEM_MODE=neutral"]),
        ("R12_BYP_either_90_a100",["BYP_STATE=either","BYP_Q=0.90","BYP_A=1.00"]),
        ("R12_BYP_rev_90_a100",["BYP_STATE=rev","BYP_Q=0.90","BYP_A=1.00"])]
for tg,ex in SECOND:
    JOBS.append((tg+"_s2027", COMMON+seedenv("2027")+ex))
JOBS.append(("R12B_GATEP_s2027",COMMON+seedenv("2027")))
# --- nulls for the CEM family and the two biggest BYP arms ---
mknull("R12_CEM_99_neutral_s42","cem_fire",COMMON+seedenv("42")+["CEM_Q=0.99","CEM_MODE=neutral"])
mknull("R12_CEM_95_neutral_s42","cem_fire",COMMON+seedenv("42")+["CEM_Q=0.95","CEM_MODE=neutral"])
mknull("R12_BYP_either_90_a100_s42","byp_fire",COMMON+seedenv("42")+["BYP_STATE=either","BYP_Q=0.90","BYP_A=1.00"])
def run(job):
    tag,ex=job; ex=ex+["OUT_TAG="+tag]
    for e in ex: assert e.split("=",1)[0] in ENV_WL, "env outside whitelist: "+e
    if os.path.exists(f"{T}/w10_ablation_series_{tag}.npz"): return tag+" cached"
    env=dict(os.environ)
    for k in list(env):
        if k in ENV_WL or k in ("W3FIX","SEATF10","KMOD","KTAIL","KMOD_F10","KMOD_AGREE","SEATNET",
            "FUNDSCALE","FEMAT_NPZ","TRADE_TOPN","REF_SKIP","RNSM","FTPOS","LTRIM_TH","CDAMP","SLEEVE"): env.pop(k,None)
    env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    t0=time.time()
    with open(f"{TREE}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=TREE,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%-42s rc=%d %4.0fs"%(tag,rc,time.time()-t0)
if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    t0=time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(run,JOBS): print(r,"%.0fs"%(time.time()-t0),flush=True)
    json.dump({"device":DEV,"device_sha256":sha(DEV),"w12_sha256":sha(f"{R}/w12_intervene.py"),
               "env_whitelist":ENV_WL,"jobs":[{"tag":t,"env":e} for t,e in JOBS],
               "null_families":"SHIFT101/503/1009 (fire mask advanced) + RELAB1/2/3 (rng default_rng([4242,k]); CEM: symbol permutation on the RANKING funding row; BYP: permutation of the fire mask)",
               "done_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"self_sha256":sha(os.path.abspath(__file__))},
              open(f"{R}/out/RUN_ENV_r12_nulls.json","w"),indent=1)
    print("NULLS_DONE",len(JOBS))
