"""r10_combine STEP 5 -- diagnostics the report quotes verbatim:
TRAIN-fitted allocation weights and what they do on the HOLDOUT; NAV consequences of
each allocation; per-year table; and the equal-risk gross/risk shares.
ENV WHITELIST (E-0826-D) = EMPTY SET.  Caliber pin v4 (2026-09-09)."""
import os, sys, json, hashlib, calendar, time
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
assert not [k for k in _FORBID if k in os.environ]
import numpy as np
from scipy.optimize import minimize
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<22),b''): h.update(b)
    return h.hexdigest()
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r10_combine"
z=np.load(OUT+"/series/books_on_pinned_axis.npz",allow_pickle=True)
TS=z["ts"]; NAMES=[str(x) for x in z["names"]]; G=z["G"]; TU=z["TU"]
n=len(TS); APY=2190.0; SE=float(np.sqrt(APY/n)); IX={k:i for i,k in enumerate(NAMES)}
def ann(x):
    s=np.std(x,ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s>0 else float('nan')
def mdd(x):
    c=np.concatenate([[0.0],np.cumsum(x)]); return float(np.max(np.maximum.accumulate(c)-c))
DAY=TS//86400; ud,inv=np.unique(DAY,return_inverse=True); nd=len(ud)
def worstday(x):
    d=np.bincount(inv,weights=x,minlength=nd); i=int(np.argmin(d))
    return float(d[i]), time.strftime("%Y-%m-%d",time.gmtime(int(ud[i])*86400))
def fit(Gk,minmean=None):
    m_=Gk.mean(0); C_=np.cov(Gk.T,ddof=1); k=Gk.shape[1]
    def neg(c):
        v=float(c@C_@c); return 1e6 if v<=0 else -float((c@m_)/np.sqrt(v))
    cons=[{"type":"eq","fun":lambda c:c.sum()-1.0}]
    if minmean is not None: cons.append({"type":"ineq","fun":lambda c: float(c@m_)-minmean})
    best=None
    for s0 in [np.ones(k)/k]+[np.eye(k)[i]*0.9+0.1/k for i in range(k)]:
        try:
            r_=minimize(neg,s0,method="SLSQP",bounds=[(0,1)]*k,constraints=cons,
                        options={"maxiter":800,"ftol":1e-12})
            if r_.success and (best is None or r_.fun<best.fun): best=r_
        except Exception: pass
    c=np.clip(best.x,0,1); return c/c.sum()
POOLS={"POOL_A_all_primary":["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"],
       "POOL_B_survivors":["A0","TSMOM","VRP"],
       "POOL_C_survivors_bestarm":["A0","TSMOM_best","VRP","CMUM_best","SLOW_best"]}
tr=TS<=T(2024,12,31,20); ho=TS>=T(2025,1,1,0)
gA0=G[:,IX["A0"]]
R={"step":"S5_DIAG","self_sha256":sha(os.path.abspath(__file__)),"env_whitelist":[],
   "env_seen_at_runtime":ENV_SEEN,"numpy":np.__version__}
print("=== TRAIN-fitted (2022-06-30..2024-12-31) max-Sharpe weights, evaluated on HOLDOUT (2025-01-01..2026-08-30) ===")
print("A0 alone: TRAIN SR %+0.4f  HOLDOUT SR %+0.4f  HOLDOUT mean_g %+0.4f"
      %(ann(gA0[tr]),ann(gA0[ho]),gA0[ho].mean()))
TRH={"A0_alone":{"train_sharpe":round(ann(gA0[tr]),4),"holdout_sharpe":round(ann(gA0[ho]),4),
                 "holdout_mean_g":round(float(gA0[ho].mean()),4)}}
for pn,keys in POOLS.items():
    idx=[IX[k] for k in keys]; Gk=G[:,idx]; Tk=TU[:,idx]
    c=fit(Gk[tr]); g=Gk@c
    TRH[pn]={"train_fitted_gross_share":dict(zip(keys,[round(float(x),5) for x in c])),
             "train_sharpe":round(ann(g[tr]),4),"holdout_sharpe":round(ann(g[ho]),4),
             "holdout_mean_g":round(float(g[ho].mean()),4),
             "holdout_SE":round(float(np.sqrt(APY/ho.sum())),4),
             "holdout_vs_A0_sharpe":round(ann(g[ho])-ann(gA0[ho]),4),
             "holdout_vs_A0_in_SE":round((ann(g[ho])-ann(gA0[ho]))/float(np.sqrt(APY/ho.sum())),3)}
    print("%-26s c=%s  TRAIN %+0.4f  HOLDOUT %+0.4f (A0 %+0.4f, delta %+0.2f SE)"
          %(pn,dict(zip(keys,np.round(c,4).tolist())),ann(g[tr]),ann(g[ho]),ann(gA0[ho]),
            TRH[pn]["holdout_vs_A0_in_SE"]))
R["train_fitted_then_holdout"]=TRH
print("\n=== NAV consequence of each allocation (2.0x gross, full window) ===")
NAV={}
def row(tag,keys,c):
    idx=[IX[k] for k in keys]; g=G[:,idx]@c; t=float((TU[:,idx]@c).mean()); wd,wds=worstday(g)
    o={"gross_share":dict(zip(keys,[round(float(x),5) for x in c])),
       "mean_g_bps":round(float(g.mean()),4),"ann_sharpe":round(ann(g),4),
       "NAV_pct_per_yr_at_2x":round(float(g.mean())*APY*2.0/100.0,2),
       "turnover":round(t,5),"maxDD_bps":round(mdd(g),1),"worst_day_bps":round(wd,1),"worst_day":wds}
    NAV[tag]=o
    print("%-44s SR %+7.4f  g %+7.4f  NAV%%/yr %+7.2f  turn %7.5f  mDD %8.1f  wday %+8.1f"
          %(tag,o["ann_sharpe"],o["mean_g_bps"],o["NAV_pct_per_yr_at_2x"],t,o["maxDD_bps"],wd))
    return o
row("A0_alone",["A0"],np.array([1.0]))
for pn,keys in POOLS.items():
    idx=[IX[k] for k in keys]
    sd=np.array([np.std(G[:,i],ddof=1) for i in idx]); er=(1/sd)/np.sum(1/sd)
    row(pn+" | equal-risk",keys,er)
    row(pn+" | maxSharpe IS",keys,fit(G[:,idx]))
    row(pn+" | maxSharpe return-preserving",keys,fit(G[:,idx],minmean=float(gA0.mean())))
R["NAV_table"]=NAV
print("\n=== equal-risk shares ===")
ER={}
for pn,keys in POOLS.items():
    idx=[IX[k] for k in keys]; sd=np.array([np.std(G[:,i],ddof=1) for i in idx])
    er=(1/sd)/np.sum(1/sd); Ck=np.cov(G[:,idx].T,ddof=1); rc=er*(Ck@er); rc=rc/rc.sum()
    ER[pn]={"sd_per_anchor_bps":dict(zip(keys,[round(float(x),3) for x in sd])),
            "gross_share":dict(zip(keys,[round(float(x),5) for x in er])),
            "realised_risk_share":dict(zip(keys,[round(float(x),5) for x in rc]))}
    print(pn,json.dumps(ER[pn]["gross_share"]))
R["equal_risk_shares"]=ER
yrs=np.array([int(time.strftime("%Y",time.gmtime(int(t)))) for t in TS])
PY={}
for nm in NAMES:
    PY[nm]={str(y):{"mean_g_bps":round(float(G[yrs==y,IX[nm]].mean()),4),
                    "ann_sharpe":round(ann(G[yrs==y,IX[nm]]),4),
                    "n":int((yrs==y).sum())} for y in sorted(set(yrs.tolist()))}
R["per_year_per_book"]=PY
print("\n=== per-year mean g (bps/anchor) ===")
hdr=sorted(set(yrs.tolist()))
print("%-12s"%"book"+" ".join("%10d"%y for y in hdr))
for nm in ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS","TSMOM_best","CMUM_best","SLOW_best","CMUM_static"]:
    print("%-12s"%nm+" ".join("%+10.4f"%PY[nm][str(y)]["mean_g_bps"] for y in hdr))
json.dump(R,open(OUT+"/receipts/S5_DIAG.json","w"),indent=1)
print("\nwrote",OUT+"/receipts/S5_DIAG.json")
