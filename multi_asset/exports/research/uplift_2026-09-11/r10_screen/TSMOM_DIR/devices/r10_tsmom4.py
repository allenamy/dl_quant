"""R10 SCREEN TSMOM_DIR -- part 4: regime-conditional combination with day-block bootstrap CIs on
the rho and on the conditional mean, i.e. is the sign flip real or noise.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os, json, time
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","SLEEVE","SEATNET","CDAMP",
    "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","SEATF10","KTAIL","FUNDSCALE","TRADE_TOPN","RNSM",
    "FTPOS","LTRIM_TH","FTRIM_TH","REF_SKIP","PANEL","EXPORT_PANEL","EMA_STATE_JSON")
assert not [k for k in _F if k in os.environ], "E-0826-D env violation"
import numpy as np
OUT="/workspace/uplift_2026-09-11/r10_tsmom"
Z=np.load(OUT+"/primary_series.npz")
ts=Z["ts"].astype(np.int64); gT=Z["gT"]; gA0=Z["gA0"]; netlong=Z["netlong"]; turn=Z["turn"]
pnl=Z["pnl"]; car=Z["carry"]; cst=Z["cost"]
NW=len(ts); YR=np.array([time.gmtime(int(t)).tm_year for t in ts])
def ann(x):
    s=float(np.std(x,ddof=1)); return float(np.mean(x)/s*np.sqrt(2190)) if s>0 else float("nan")
def mdd(g):
    c=np.cumsum(g); return float(np.max(np.maximum.accumulate(c)-c))
def ci(v): return [float(np.percentile(v,2.5)),float(np.percentile(v,97.5))]
SPANS={"FULL_postwarm":np.ones(NW,bool),"ex2022":YR>=2023,"2024on":YR>=2024,
       "FROZEN_2025-03-01..2026-08-10":(ts>=1740787200)&(ts<=1786737600),
       "2025on":YR>=2025,"2026":YR>=2026}
OUTJ={}
for nm,msk in SPANS.items():
    n=int(msk.sum())
    if n<300: continue
    t_=gT[msk]; a_=gA0[msk]; d_=(ts[msk]//86400).astype(np.int64)
    UD=np.unique(d_); DI=[np.where(d_==x)[0] for x in UD]
    def boot(fn,B=2000):
        o=np.empty(B)
        for b in range(B):
            rng=np.random.default_rng([20260905,b]); p=rng.integers(0,len(UD),len(UD))
            o[b]=fn(np.concatenate([DI[q] for q in p]))
        return o
    q=np.quantile(a_,0.20); lo=a_<=q
    r=float(np.corrcoef(t_,a_)[0,1])
    rb=boot(lambda s:(float(np.corrcoef(t_[s],a_[s])[0,1]) if t_[s].std()>0 and a_[s].std()>0 else np.nan))
    rb=rb[np.isfinite(rb)]
    rlo=float(np.corrcoef(t_[lo],a_[lo])[0,1])
    rlb=boot(lambda s:(float(np.corrcoef(t_[s][lo[s]],a_[s][lo[s]])[0,1]) if lo[s].sum()>50 and t_[s][lo[s]].std()>0 else np.nan))
    rlb=rlb[np.isfinite(rlb)]
    mlo=float(t_[lo].mean())
    mlb=boot(lambda s:(float(t_[s][lo[s]].mean()) if lo[s].sum()>50 else np.nan)); mlb=mlb[np.isfinite(mlb)]
    gb=boot(lambda s: float(t_[s].mean()))
    s1=ann(a_); s2=ann(t_); SE=float(np.sqrt(2190.0/n))
    sopt=float(np.sqrt(max(s1**2+s2**2-2*r*s1*s2,0.0)/(1-r**2)))
    row=dict(n=n,TSMOM_net_g=float(t_.mean()),TSMOM_net_CI95=ci(gb),TSMOM_SR=s2,SE_SR=SE,
             A0_g=float(a_.mean()),A0_SR=s1,rho=r,rho_CI95=ci(rb),
             rho_in_A0_bottom_quintile=rlo,rho_bq_CI95=ci(rlb),
             TSMOM_mean_in_A0_bottom_quintile=mlo,TSMOM_mean_bq_CI95=ci(mlb),
             A0_mean_in_bq=float(a_[lo].mean()),
             SR_opt_upper_bound=sopt,dSR=float(sopt-s1),dSR_in_SE=float((sopt-s1)/SE),
             TSMOM_sd=float(t_.std(ddof=1)),A0_sd=float(a_.std(ddof=1)),
             netlong_abs_mean=float(np.abs(netlong[msk]).mean()),
             turnover=float(turn[msk].mean()),price_g=float(pnl[msk].mean()),
             carry_g=float(car[msk].mean()),cost_g=float(cst[msk].mean()),
             cost_survival_pct=float(100*t_.mean()/pnl[msk].mean()) if pnl[msk].mean()!=0 else None)
    dA=np.array([a_[ix].sum() for ix in DI])
    for c in (0.02,0.05,0.10,0.20):
        gc=(a_+c*t_)/(1+c); dc=np.array([gc[ix].sum() for ix in DI])
        row["c=%.2f"%c]=dict(SR=ann(gc),dSR=float(ann(gc)-s1),maxDD=mdd(gc),dMaxDD=float(mdd(gc)-mdd(a_)),
                             worstday=float(dc.min()),dWorstday=float(dc.min()-dA.min()))
    OUTJ[nm]=row
    print("\n=== %s  n=%d"%(nm,n),flush=True)
    print("  TSMOM net g %+.4f CI %s | SR %+.3f (SE %.3f) | A0 SR %.3f"%(t_.mean(),np.round(row["TSMOM_net_CI95"],3),s2,SE,s1),flush=True)
    print("  rho %+.4f CI %s | rho|A0Q0 %+.4f CI %s | TSMOM mean in A0Q0 %+.3f CI %s (A0 there %+.2f)"
          %(r,np.round(row["rho_CI95"],4),rlo,np.round(row["rho_bq_CI95"],4),mlo,np.round(row["TSMOM_mean_bq_CI95"],2),a_[lo].mean()),flush=True)
    print("  optimal(UB) SR %.4f  dSR %+.4f = %.3f SE"%(sopt,sopt-s1,(sopt-s1)/SE),flush=True)
    for c in (0.02,0.05,0.10,0.20):
        rr=row["c=%.2f"%c]
        print("   c=%.2f SR %+.4f (d%+.4f) maxDD %.1f (d%+.1f) worstday %+.1f (d%+.1f)"
              %(c,rr["SR"],rr["dSR"],rr["maxDD"],rr["dMaxDD"],rr["worstday"],rr["dWorstday"]),flush=True)
json.dump(dict(by_regime=OUTJ,env_whitelist=[]),open(OUT+"/STEP_REGIME2.json","w"),indent=1)
print("\nwrote",OUT+"/STEP_REGIME2.json",flush=True)
