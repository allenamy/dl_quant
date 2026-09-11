"""BUILD 2: (i) s2027 replication of the two lead arms; (ii) the HONEST full-axis reading of S00.
S00 sets w_fund->0 below tau; when the msharpe seat also has w_king=0 (king trailing Sharpe <= 0) the
whole w3 vector is zero, the device's `if g < 1e-9: continue` fires and NO BOOK EXISTS at that anchor.
Pairing on the intersection silently conditions on 'the king seat was positive'. The deployable object
earns ZERO on those anchors, so the full-axis comparison fills g=0 there. Both readings are reported."""
import numpy as np, os, subprocess, time, json, hashlib, calendar
HC="/workspace/review_scratch/health_check"
ROOT="/workspace/uplift_2026-09-11/r8b2"; D=ROOT+"/dev"
DEV=ROOT+"/w10_sleeve_tilt.py"
DEVSHA=hashlib.sha256(open(DEV,'rb').read()).hexdigest(); assert DEVSHA.startswith("7dd6324acd361081")
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
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
    for e in ex: assert e.split("=",1)[0] in ENV_WL, e
    t0=time.time()
    with open(D+"/logs/%s.log"%tag,"w") as lf:
        rc=subprocess.call(["env"]+ex+["/workspace/venv/bin/python",DEV],cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    return "%s rc=%d %.0fs"%(tag,rc,time.time()-t0)
A27=["LEGS=101","PHI=0.45","FSEED=2027","FPRED=f10_A0_s2027.npy"]
JOBS=[("R8_S00_s2027",A27+["TILT=step","TILT_TAU=4.75","TILT_K=0.0"]),
      ("R8_P10_s2027",A27+["TILT=pow","TILT_TAU=4.75","TILT_K=1.0"]),
      ("R8_R00_s2027",A27+["TILT=ramp","TILT_TAU=4.75","TILT_K=0.0"])]
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=3) as ex:
    for r in ex.map(lambda j: run(*j), JOBS): print(r,flush=True)
# ---- analysis ----
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
U="/workspace/uplift_2026-09-11"; APY=2190; WARM=900; CUT=T(2026,8,30,20); B=4000
GS=T(2026,8,19,0); GE=T(2026,8,21,20); HS=T(2026,8,11,0); HE=T(2026,8,30,20); TAU=4.75
S=np.load(U+"/r7f1/out/sigma_variants.npz",allow_pickle=True); C=[str(c) for c in S["cols"]]
GL=dict(zip(S["rec"][:,0].astype(np.int64),S["rec"][:,C.index("LIVE_sig")]))
def load(p):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    A=np.asarray(Z[k],float)[WARM:]; ts=np.round(A[:,ix["ts"]]).astype(np.int64); m=ts<=CUT
    return ts[m],(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[m]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def bstat(ts,fn,seed):
    dd=ts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    o=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(o))
    rng=np.random.default_rng([20260912,seed]); pk=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        ii=np.concatenate([o[st[j]:en[j]] for j in pk[b]]); out[b]=fn(ii)
    return out
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]; return (float(np.percentile(v,lo)),float(np.percentile(v,hi)))
OUT={"device_sha256":DEVSHA,"env_whitelist":ENV_WL,"jobs":[[t,e] for t,e in JOBS]}
for sd,a0p in ((42,U+"/r3k/arms/A0_PWR230k_s42.npz"),(2027,U+"/r3k/arms/A0_PWR230k_s2027.npz")):
    ts0,g0=load(a0p); yr=np.array([time.gmtime(int(t)).tm_year for t in ts0]); YEARS=sorted(set(yr.tolist()))
    for arm in ("S00","R00","P10"):
        tsa,ga=load(D+"/probe_artifacts/w10_ablation_series_R8_%s_s%d.npz"%(arm,sd))
        # FULL-AXIS: the arm earns 0 where it holds no book
        gf=np.zeros_like(g0); mm=np.isin(ts0,tsa)
        gf[mm]=ga[np.isin(tsa,ts0)]
        d=gf-g0
        th=float(np.mean([d[yr==y].mean() for y in YEARS]))
        gv=(ts0>=GS)&(ts0<=GE); ho=(ts0>=HS)&(ts0<=HE)
        r={"seed":sd,"n_axis":len(g0),"n_anchors_with_no_book":int((~mm).sum()),
           "fullaxis_delta_g":round(float(d.mean()),4),
           "fullaxis_delta_g_CI95":[round(x,4) for x in ci(bstat(ts0,lambda ii: d[ii].mean(),301))],
           "fullaxis_theta_yearFE":round(th,4),
           "fullaxis_arm_sharpe":round(sr(gf),4),"A0_sharpe":round(sr(g0),4),
           "fullaxis_delta_sharpe":round(sr(gf)-sr(g0),4),
           "fullaxis_per_year_delta_g":{int(y):round(float(d[yr==y].mean()),4) for y in YEARS},
           "giveback_delta_g":round(float(d[gv].mean()),4),
           "heldout_delta_g":round(float(d[ho].mean()),4)}
        OUT["%s_s%d"%(arm,sd)]=r
        print("%s s%d  FULLAXIS dg=%+.4f CI%s theta=%+.4f dSR=%+.4f  noBook=%d  GB=%+.4f HO=%+.4f"%(
            arm,sd,r["fullaxis_delta_g"],r["fullaxis_delta_g_CI95"],r["fullaxis_theta_yearFE"],
            r["fullaxis_delta_sharpe"],r["n_anchors_with_no_book"],r["giveback_delta_g"],r["heldout_delta_g"]),flush=True)
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(ROOT+"/out/R8_REP.json","w"),indent=1)
print("REP_DONE")
