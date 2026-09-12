"""r21_nulls.py -- Part A driver (PREREG_r21 sha256 c4de6df3... SS A1-A3). pod2, CPU only.
  GATE G-A2 : w21 with R21_DOSE unset == archived w12b series, bitwise (true arm; archived SHIFT101 null).
  Nulls     : RELAB1-3 (archived sym_perm, true fire mask) ; SHIFTC101/503/1009 (fire mask advanced CIRCULARLY inside the
              eligible region [900,N) so the fire count is preserved exactly).  Three CEM arms (99n, 95n, 99d).
  Re-solve  : per null, R21_DOSE by bracketing + bisection until |dturn_null - dturn_true|/|dturn_true| <= 1% (r13b L28 rule),
              dturn in the receipt's own caliber (cost_ex/gross_total/2.9537, post-warm 900).
Every subprocess env is whitelisted (r12's 20 names + R21_DOSE) and written to RUN_ENV_r21.json with the device's config_json."""
import os, sys, json, time, hashlib, subprocess, threading
import numpy as np
from concurrent.futures import ThreadPoolExecutor
U="/workspace/uplift_2026-09-11"; R12=f"{U}/r12_intervene"; R21=f"{U}/r21_nulls_costbridge"; HC="/workspace/review_scratch/health_check"
T12=f"{R12}/dev_ext/probe_artifacts"; TREE=f"{R21}/dev_ext"; T=f"{TREE}/probe_artifacts"; DEV=f"{R21}/w21_intervene.py"
COSTB=f"{U}/r3k/costb_PWR_G230k.json"; R6=f"{U}/r6/out"
PREREG_SHA="c4de6df3a37483462d4e10373c30ea4137c02c78f9a23e06148007c5ce246232"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
assert sha(f"{R21}/PREREG_r21_2026-09-12.md")==PREREG_SHA
assert sha(f"{R12}/w12b_intervene.py")=="ce3b79836a60647d7a110f6e82c0c929e19b4ce86e7e460ebf801f99883f5926"
assert sha(COSTB)=="295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
DEV_SHA=sha(DEV)
# ---- dev tree: same layout as r12/dev_ext, own probe_artifacts (never write into r12's archive) ----
for d in (T,f"{TREE}/logs",f"{R21}/nullsig",f"{R21}/out"): os.makedirs(d,exist_ok=True)
for name in ("pod_backup_2026-08-21","f8_2026-08-22","dlw_2026-08-22"):
    dst=f"{TREE}/{name}"; src=os.path.realpath(f"{R12}/dev_ext/{name}")
    if not os.path.lexists(dst): os.symlink(src,dst)
    assert os.path.realpath(dst)==src, (dst,src)
ENV_WL=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ","SLOW_NPY","FSEED","FPRED","COSTB_JSON","OUT_TAG",
        "CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","R12_NULL","R21_DOSE"]
COMMON=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45","UMASK_SCOPE=m1",
        "UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","COSTB_JSON="+COSTB,"SLOW_NPY="+R6+"/SLOW_v4_x0910.npy","FSEED=42","FPRED=f10_v4RAWx_s42.npy"]
ARMS={"R12_CEM_99_neutral_s42":["CEM_Q=0.99","CEM_MODE=neutral"],
      "R12_CEM_95_neutral_s42":["CEM_Q=0.95","CEM_MODE=neutral"],
      "R12_CEM_99_derisk_s42": ["CEM_Q=0.99","CEM_MODE=derisk"]}
WARM=900; RATE=2.9537; sl=slice(WARM,None); NW=829
SEM=threading.Semaphore(8); RUNS=[]; RUNS_LOCK=threading.Lock()
def run(tag,ex):
    ex=list(ex)+["OUT_TAG="+tag]
    for e in ex: assert e.split("=",1)[0] in ENV_WL, "env outside whitelist: "+e
    out=f"{T}/w10_ablation_series_{tag}.npz"
    if os.path.exists(out): return out
    env={k:v for k,v in os.environ.items() if k not in ENV_WL and k not in ("W3FIX","SEATF10","KMOD","KTAIL","KMOD_F10","KMOD_AGREE","SEATNET","FUNDSCALE","FEMAT_NPZ","TRADE_TOPN","REF_SKIP","RNSM","FTPOS","LTRIM_TH","CDAMP","SLEEVE")}
    env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    t0=time.time()
    with SEM:
        with open(f"{TREE}/logs/{tag}.log","w") as lf:
            rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=TREE,stdout=lf,stderr=subprocess.STDOUT,env=env)
    cfg=None
    if rc==0 and os.path.exists(out):
        try: cfg=json.loads(str(np.load(out,allow_pickle=True)["config_json"]))
        except Exception as e: cfg={"config_json_parse_error":str(e)}
    with RUNS_LOCK: RUNS.append({"tag":tag,"env":ex,"rc":rc,"seconds":round(time.time()-t0,1),"config_R12":(cfg or {}).get("R12"),"R21_DOSE_selfreport":(cfg or {}).get("R21_DOSE"),"R12_NULL_selfreport":(cfg or {}).get("R12_NULL")})
    assert rc==0 and os.path.exists(out), f"run failed {tag} rc={rc}"
    return out
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; C={k:i for i,k in enumerate(cols)}
    Rr=np.asarray(Z["d30_n2_c42_rec"],float); gt=Rr[:,C["gross_total"]]
    D=np.asarray(Z["d30_n2_c42_DIAG"],float)
    return {"rec":Rr,"W":np.asarray(Z["d30_n2_c42_W"]),"DIAG":D,"g":Rr[:,C["net_ex"]]/gt,"tov":Rr[:,C["cost_ex"]]/gt/RATE,"tovf":Rr[:,C["turnover"]]/gt}
A0=load(f"{T12}/w10_ablation_series_R12B_GATEP_s42.npz")
def stats(S):
    f=S["DIAG"][:,3]; return {"dg":float(S["g"][sl].mean()-A0["g"][sl].mean()),"dturn_frac_pct":float(100*(S["tov"][sl].mean()/A0["tov"][sl].mean()-1)),
        "dturn_file_pct":float(100*(S["tovf"][sl].mean()/A0["tovf"][sl].mean()-1)),"fire_n":int((f+S["DIAG"][:,6])[sl].sum()),
        "cem_n_mean":float(S["DIAG"][f>0.5,4].mean()) if (f>0.5).any() else 0.0,"cost_ex_per_gross":float((S["tov"][sl]*RATE).mean())}
OUT={"prereg_sha256":PREREG_SHA,"device":DEV,"device_sha256":DEV_SHA,"env_whitelist":ENV_WL,"start_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"gates":{},"arms":{}}
# ================= GATE G-A2 =================
g1=run("R21G_TRUE_CEM99n",COMMON+ARMS["R12_CEM_99_neutral_s42"])
g2=run("R21G_NULL_SHIFT101",COMMON+ARMS["R12_CEM_99_neutral_s42"]+["R12_NULL="+f"{R12}/nullsig/R12_CEM_99_neutral_s42_SHIFT101.npz"])
def bitwise(a,b):
    A=load(a); B=load(b)
    return {"rec_bitwise":bool(np.array_equal(A["rec"],B["rec"])),"W_bitwise":bool(np.array_equal(A["W"],B["W"])),
            "DIAG_bitwise":bool(np.array_equal(A["DIAG"],B["DIAG"],equal_nan=True)),"rec_maxabs":float(np.nanmax(np.abs(A["rec"]-B["rec"])))}
OUT["gates"]["G_A2_true_arm"]=bitwise(g1,f"{T12}/w10_ablation_series_R12_CEM_99_neutral_s42.npz")
OUT["gates"]["G_A2_null_SHIFT101"]=bitwise(g2,f"{T12}/w10_ablation_series_R12_CEM_99_neutral_s42_NULL_SHIFT101.npz")
assert all(v["rec_bitwise"] and v["W_bitwise"] for v in OUT["gates"].values()), OUT["gates"]
print("GATE G-A2 PASS",json.dumps(OUT["gates"]),flush=True)
json.dump(OUT,open(f"{R21}/out/BISECT_r21_partial.json","w"),indent=1)
# ================= null signatures =================
def fire_mask(arm):
    S=load(f"{T12}/w10_ablation_series_{arm}.npz"); D=S["DIAG"]; return D[:,0].astype(np.int64), (D[:,3]>0.5), S
NULLS={}
for arm in ARMS:
    ts,f,S=fire_mask(arm); N=len(f); idx=np.where(f)[0]; assert idx.min()>=WARM, idx.min()
    NULLS[arm]={}
    for k in (101,503,1009):
        q=np.zeros(N,bool); q[WARM+((idx-WARM+k)%(N-WARM))]=True; assert q.sum()==f.sum()
        p=f"{R21}/nullsig/{arm}_SHIFTC{k}.npz"; np.savez(p,ts=ts,force_fire=q)
        orig=f"{R12}/nullsig/{arm}_SHIFT{k}.npz"
        same_as_r12=bool(os.path.exists(orig) and np.array_equal(np.load(orig)["force_fire"],q))
        NULLS[arm][f"SHIFTC{k}"]={"sig":p,"construction":"fire mask advanced k anchors, circular in [900,N)","fires":int(q.sum()),"identical_to_r12_mask":same_as_r12,
                                   "r12_fires_dropped":int(f.sum()-np.load(orig)["force_fire"].sum()) if os.path.exists(orig) else None}
    for k in (1,2,3):
        rng=np.random.default_rng([4242,k]); pi=rng.permutation(NW)
        orig=f"{R12}/nullsig/{arm}_RELAB{k}.npz"
        if os.path.exists(orig):
            oz=np.load(orig); assert np.array_equal(oz["force_fire"],f) and np.array_equal(oz["sym_perm"],pi), orig
            p=orig; new=False
        else:
            p=f"{R21}/nullsig/{arm}_RELAB{k}.npz"; np.savez(p,ts=ts,force_fire=f,sym_perm=pi); new=True
        NULLS[arm][f"RELAB{k}"]={"sig":p,"construction":"true fire mask; ranking funding row symbol-permuted default_rng([4242,k])","fires":int(f.sum()),"new_for_r21":new}
    OUT["arms"][arm]={"true":stats(S),"nulls":NULLS[arm]}
    print(arm,"true",OUT["arms"][arm]["true"],flush=True)
# ================= bisection =================
def evaluate(arm,nm,dose):
    info=NULLS[arm][nm]
    # archived series reusable only when the signature is r12's own and dose==0
    if dose==0.0 and (nm.startswith("RELAB") and not info.get("new_for_r21") or (nm.startswith("SHIFTC") and info["identical_to_r12_mask"])):
        k=nm.replace("SHIFTC","SHIFT"); path=f"{T12}/w10_ablation_series_{arm}_NULL_{k}.npz"
        if os.path.exists(path): return dict(stats(load(path)),dose=0.0,source="r12_archive")
    tag=f"{arm}_N_{nm}_D{dose:+.6f}".replace("+","p").replace("-","m")
    path=run(tag,COMMON+ARMS[arm]+["R12_NULL="+info["sig"],"R21_DOSE=%.6f"%dose])
    return dict(stats(load(path)),dose=dose,source=tag)
def solve(arm,nm):
    target=OUT["arms"][arm]["true"]["dturn_frac_pct"]; tol=0.01*abs(target); evals=[]
    def f(d):
        r=evaluate(arm,nm,d); evals.append(r); return r["dturn_frac_pct"]
    v0=f(0.0)
    if abs(v0-target)>tol:
        if v0<target:
            lo,hi=0.0,0.5
            while f(hi)<target and hi<64: lo,hi=hi,hi*2
        else:
            hi,lo=0.0,-0.5
            while f(lo)>target and lo>-1.0: hi,lo=lo,max(lo*2,-1.0)
        vlo=[e for e in evals if e["dose"]==lo][-1]["dturn_frac_pct"]; vhi=[e for e in evals if e["dose"]==hi][-1]["dturn_frac_pct"]
        if vlo<=target<=vhi:
            for _ in range(16):
                mid=0.5*(lo+hi); v=f(mid)
                if abs(v-target)<=tol: break
                if v<target: lo=mid
                else: hi=mid
    best=min(evals,key=lambda e:abs(e["dturn_frac_pct"]-target))
    return {"target_dturn_frac_pct":target,"tol_abs":tol,"n_evals":len(evals),"evals":evals,"matched":best,
            "rel_mismatch_after":abs(best["dturn_frac_pct"]-target)/abs(target),"matched_within_1pct":bool(abs(best["dturn_frac_pct"]-target)<=tol)}
jobs=[(arm,nm) for arm in ARMS for nm in NULLS[arm]]
t0=time.time()
with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
    res=list(ex.map(lambda j: (j,solve(*j)),jobs))
for (arm,nm),r in res: OUT["arms"][arm]["nulls"][nm].update(r)
OUT["wall_seconds"]=round(time.time()-t0,1); OUT["end_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
json.dump(OUT,open(f"{R21}/out/BISECT_r21.json","w"),indent=1)
json.dump({"device":DEV,"device_sha256":DEV_SHA,"env_whitelist":ENV_WL,"runs":RUNS,"n_runs":len(RUNS),"self_sha256":sha(os.path.abspath(__file__))},open(f"{R21}/out/RUN_ENV_r21.json","w"),indent=1)
for arm in ARMS:
    tr=OUT["arms"][arm]["true"]; print("\n==",arm,"true dturn %.6f dg %.6f fires %d"%(tr["dturn_frac_pct"],tr["dg"],tr["fire_n"]))
    for nm,v in OUT["arms"][arm]["nulls"].items():
        m=v["matched"]; print("  %-9s dose %+.5f dturn %.6f (rel %.4f) fires %d dg %+.6f cem_n %.3f evals %d ok=%s"%(nm,m["dose"],m["dturn_frac_pct"],v["rel_mismatch_after"],m["fire_n"],m["dg"],m["cem_n_mean"],v["n_evals"],v["matched_within_1pct"]))
print("NULLS_DONE runs",len(RUNS),"wall",OUT["wall_seconds"])
