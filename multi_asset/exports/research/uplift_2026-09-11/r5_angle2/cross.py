"""ANGLE 2 / STEP 2b+2d. Device COPY w10_sleeve_w3seq.py = pinned w10_sleeve.py + ONE additive knob
W3SEQ_NPZ (per-anchor leg weights). Unset => untouched path. Two gates before any number:
  G1 device-copy gate : W3SEQ unset must reproduce the ladder's arm rec BITWISE.
  G2 seat-echo gate   : W3SEQ = the dynamic seat's OWN reconstructed w3 must reproduce it BITWISE.
Then (b) the 2x2 cross (fresh/stale scores x fresh/stale-implied weights) on the DYNAMIC seat,
and (d) a fixed-king-weight sweep implemented as a CONSTANT W3SEQ (the pinned device whitelists
W3FIX to the single value 0.21,0,0.79, so the sweep needs this knob)."""
import numpy as np, os, sys, subprocess, time, hashlib, json
HC="/workspace/review_scratch/health_check"
R="/workspace/uplift_2026-09-11/r5a2"; D=R+"/dev"; OUT=R+"/arms"; SIG=D+"/sig"
DEVX=R+"/w10_sleeve_w3seq.py"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
K3="/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
BOOK=["LEGS=101","CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","FTRIM=zero","PHI=0.45",
      "UMASK_SCOPE=m1","UMASK_NPZ="+HC+"/masks/umask_UPIT_CRYPTO.npz","SLOW_NPY="+K3]
WHITELIST=["LEGS","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","PHI","UMASK_SCOPE","UMASK_NPZ",
           "SLOW_NPY","FSEED","FPRED","COSTB_JSON","W3FIX","W3SEQ_NPZ","FEMAT_NPZ","OUT_TAG",
           "OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"]
DEFAULTED=["LTRIM_TH","CDAMP","FTRIM_TH","FTPOS","RNSM","SLEEVE","SEATNET","SEATF10","KTAIL",
           "KMOD","KMOD_AGREE","KMOD_F10","KMOD_L","FUNDSCALE","TRADE_TOPN","REF_SKIP"]
def run(tag,seed,femat=None,w3seq=None,keep_full=False,dev=DEVX):
    dst=OUT+"/%s.npz"%tag
    if os.path.exists(dst): return tag+" skip"
    env={k:v for k,v in os.environ.items() if k not in WHITELIST and k not in DEFAULTED}
    for v in DEFAULTED: assert v not in env, v
    env.update(OMP_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",MKL_NUM_THREADS="3")
    ex=BOOK+["FSEED=%s"%seed,"FPRED=f10_A0_s%s.npy"%seed,"COSTB_JSON="+COSTB] \
       +(["FEMAT_NPZ="+femat] if femat else [])+(["W3SEQ_NPZ="+w3seq] if w3seq else [])+["OUT_TAG="+tag]
    for e in ex: assert e.split("=")[0] in WHITELIST, e
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",dev],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=D+"/probe_artifacts/w10_ablation_series_%s.npz"%tag
    if rc!=0 or not os.path.exists(src): return "FAIL %s rc=%s"%(tag,rc)
    Z=np.load(src,allow_pickle=True)
    kw=dict(cols=Z["cols"],rec=Z["d30_n2_c42_rec"],W=Z["d30_n2_c42_W"],config_json=Z["config_json"])
    if keep_full: kw.update(legs_ts=Z["legs_ts"],legs_king=Z["legs_king"],legs_rev24=Z["legs_rev24"],legs_fund=Z["legs_fund"])
    np.savez_compressed(dst,**kw); os.remove(src)
    return "%-34s ok %5.1fs"%(tag,time.time()-t0)
def w3_from_legs(p,LOOK=900,LEGS="101"):
    """VERBATIM reimplementation of w10_sleeve.py w3_at() for WRULE=msharpe, LEGS=101, no W3FIX."""
    Z=np.load(p,allow_pickle=True)
    ts=Z["legs_ts"].astype(np.int64)
    LR={"king":np.asarray(Z["legs_king"],float),"rev24":np.asarray(Z["legs_rev24"],float),"fund":np.asarray(Z["legs_fund"],float)}
    W=np.empty((len(ts),3))
    msk=np.array([1.0 if c=="1" else 0.0 for c in LEGS])
    for pp in range(len(ts)):
        if pp<LOOK: W[pp]=np.array([1/3]*3); continue
        sl=slice(pp-LOOK,pp)
        r=np.stack([LR["king"][sl],LR["rev24"][sl],LR["fund"][sl]])
        shp=np.maximum(r.mean(1)/(r.std(1)+1e-9),0.0)
        w_=shp/shp.sum() if shp.sum()>0 else np.array([1/3]*3)
        w_=w_*msk; w_=w_/w_.sum() if w_.sum()>1e-12 else msk/max(msk.sum(),1.0)
        W[pp]=w_
    return ts,W
def bitwise(p,q):
    x=np.asarray(np.load(p,allow_pickle=True)["rec"],float); y=np.asarray(np.load(q,allow_pickle=True)["rec"],float)
    nx=np.isnan(x); ny=np.isnan(y)
    return bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    RES={"device_copy":DEVX,"device_copy_sha256":hashlib.sha256(open(DEVX,"rb").read()).hexdigest(),
         "device_pinned_sha256":hashlib.sha256(open("/workspace/uplift_2026-09-11/w10_sleeve.py","rb").read()).hexdigest()}
    PAR=SIG+"/A2_PAR.npz"; S101=SIG+"/A2_SHIFT101.npz"
    # --- G1: device copy, knob unset, full npz kept (legs needed for the w3 reconstruction) ---
    jobs=[("R5A2X_FULL_APAR_dyn_s42","42",PAR,None,True),("R5A2X_FULL_ASHIFT101_dyn_s42","42",S101,None,True),
          ("R5A2X_FULL_APAR_dyn_s2027","2027",PAR,None,True),("R5A2X_FULL_ASHIFT101_dyn_s2027","2027",S101,None,True)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda j: run(*j),jobs): print(r,flush=True)
    g1={}
    for a in ("APAR","ASHIFT101"):
        for sd in ("42","2027"):
            g1["%s_s%s"%(a,sd)]=bitwise(OUT+"/R5A2X_FULL_%s_dyn_s%s.npz"%(a,sd),OUT+"/R5A2_%s_dyn_s%s.npz"%(a,sd))
    RES["G1_device_copy_bitwise"]=g1; print("G1",g1,flush=True)
    assert all(g1.values()), "G1 FAILED"
    # --- reconstruct each arm's own dynamic w3 and save as W3SEQ ---
    for a in ("APAR","ASHIFT101"):
        for sd in ("42","2027"):
            ts,W=w3_from_legs(OUT+"/R5A2X_FULL_%s_dyn_s%s.npz"%(a,sd))
            np.savez(SIG+"/W3_%s_s%s.npz"%(a,sd),ts=ts,w3=W)
            print("w3seq %s s%s rows %d mean_king %.4f"%(a,sd,len(ts),W[:,0].mean()),flush=True)
    # --- G2: seat echo ---
    jobs=[("R5A2X_ECHO_%s_s%s"%(a,sd),sd,(PAR if a=="APAR" else S101),SIG+"/W3_%s_s%s.npz"%(a,sd),False)
          for a in ("APAR","ASHIFT101") for sd in ("42","2027")]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda j: run(*j),jobs): print(r,flush=True)
    g2={}
    for a in ("APAR","ASHIFT101"):
        for sd in ("42","2027"):
            g2["%s_s%s"%(a,sd)]=bitwise(OUT+"/R5A2X_ECHO_%s_s%s.npz"%(a,sd),OUT+"/R5A2_%s_dyn_s%s.npz"%(a,sd))
    RES["G2_seat_echo_bitwise"]=g2; print("G2",g2,flush=True)
    json.dump(RES,open(R+"/A2_CROSS_GATES.json","w"),indent=1)
    assert all(g2.values()), "G2 FAILED"
    # --- (b) the 2x2 cross: stale scores x fresh weights, fresh scores x stale weights ---
    jobs=[("R5A2X_SF_s%s"%sd,sd,S101,SIG+"/W3_APAR_s%s.npz"%sd,False) for sd in ("42","2027")] \
        +[("R5A2X_FS_s%s"%sd,sd,PAR ,SIG+"/W3_ASHIFT101_s%s.npz"%sd,False) for sd in ("42","2027")]
    # --- (d) constant-weight sweep (W3FIX generalised) ---
    KW=[0.00,0.10,0.21,0.30,0.3568,0.45,0.60,0.80,1.00]
    ts_any=np.load(SIG+"/W3_APAR_s42.npz")["ts"]
    for kw in KW:
        f=SIG+"/W3_CONST_%s.npz"%("%.4f"%kw).replace(".","p")
        np.savez(f,ts=ts_any,w3=np.tile(np.array([kw,0.0,1.0-kw]),(len(ts_any),1)))
        for a,fm in (("APAR",PAR),("ASHIFT101",S101)):
            for sd in (("42","2027") if kw in (0.21,0.3568) else ("42",)):
                jobs.append(("R5A2X_KW%s_%s_s%s"%(("%.4f"%kw).replace(".","p"),a,sd),sd,fm,f,False))
    with ThreadPoolExecutor(max_workers=14) as ex:
        for r in ex.map(lambda j: run(*j),jobs): print(r,flush=True)
    print("CROSS_RUNS_DONE")
