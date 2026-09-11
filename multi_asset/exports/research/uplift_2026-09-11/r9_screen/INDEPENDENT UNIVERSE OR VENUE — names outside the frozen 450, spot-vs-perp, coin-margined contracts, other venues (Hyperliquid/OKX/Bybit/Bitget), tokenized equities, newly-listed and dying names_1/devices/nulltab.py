"""rho-to-A0 and standalone mean g for the turnover-matched null arms. ENV WHITELIST = EMPTY SET."""
import os
assert not [k for k in ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED",
   "COSTB_JSON","MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG") if k in os.environ]
import numpy as np, json
OUT="/workspace/r9okx"; A0B="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/"; MINE=f"{OUT}/dev/probe_artifacts/"
CAP=1788120000
def ser(p,key="d30_n2_c42_rec"):
    a=np.load(p,allow_pickle=True); ci={str(c):i for i,c in enumerate(a["cols"])}; r=a[key]
    gt=r[:,ci["gross_total"]]
    return r[:,ci["ts"]].astype(np.int64), r[:,ci["net_ex"]]/np.where(gt>0,gt,np.nan), r[:,ci["turnover"]]
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True); LO=int(fe["okx_t0"])+14*86400
tA,gA,_=ser(A0B+"w10_ablation_series_V4_A0_dyn_s42.npz"); mA={int(t):v for t,v in zip(tA,gA)}
def blocks(ts):
    d=ts//86400; u,inv=np.unique(d,return_inverse=True); return [np.where(inv==k)[0] for k in range(len(u))]
def boot(fn,ts,*a,B=2000):
    bl=blocks(ts); nb=len(bl); o=np.empty(B)
    for k in range(B):
        rng=np.random.default_rng([20260905,k]); idx=np.concatenate([bl[p] for p in rng.integers(0,nb,nb)])
        o[k]=fn(*[x[idx] for x in a])
    return o
rows={}
for tag in ["R9_OKX_fund","R9_NULLCSHIFT53_fund","R9_NULLCSHIFT101_fund","R9_NULLCSHIFT251_fund",
            "R9_NULLRELAB1_fund","R9_NULLRELAB2_fund","R9_NULLRELAB3_fund"]:
    p=MINE+f"w10_ablation_series_{tag}.npz"
    if not os.path.exists(p): continue
    ts,g,tn=ser(p)
    k=(ts>=LO)&(ts<=CAP)&np.isfinite(g)&np.array([int(t) in mA for t in ts])
    x=g[k]; T=ts[k]; y=np.array([mA[int(t)] for t in T]); ok=np.isfinite(y); x,T,y,tn=x[ok],T[ok],y[ok],tn[k][ok]
    r=float(np.corrcoef(x,y)[0,1])
    bs=boot(lambda p_,q_: float(np.corrcoef(p_,q_)[0,1]),T,x,y)
    bm=boot(lambda p_: float(p_.mean()),T,x)
    rows[tag]={"n":int(len(x)),"rho_A0":round(r,4),
      "rho_ci95":[round(float(np.percentile(bs,2.5)),4),round(float(np.percentile(bs,97.5)),4)],
      "mean_g":round(float(x.mean()),4),
      "mean_g_ci95":[round(float(np.percentile(bm,2.5)),4),round(float(np.percentile(bm,97.5)),4)],
      "sharpe_ann":round(float(x.mean()/x.std(ddof=1)*np.sqrt(2190)),4),
      "turnover":round(float(tn.mean()),5)}
print(json.dumps(rows,indent=1)); json.dump(rows,open(f"{OUT}/RESULT_nulls.json","w"),indent=1)
print()
print("{:24s} {:>4s} {:>9s} {:>20s} {:>9s} {:>22s} {:>8s} {:>9s}".format("ARM","n","rho(A0)","rho CI95","mean g","mean g CI95","SR","turnover"))
for k,v in rows.items():
    print("{:24s} {:4d} {:+9.4f} [{:+7.4f},{:+7.4f}] {:+9.4f} [{:+8.4f},{:+8.4f}] {:+8.3f} {:9.5f}".format(
      k,v["n"],v["rho_A0"],v["rho_ci95"][0],v["rho_ci95"][1],v["mean_g"],v["mean_g_ci95"][0],v["mean_g_ci95"][1],v["sharpe_ann"],v["turnover"]))
