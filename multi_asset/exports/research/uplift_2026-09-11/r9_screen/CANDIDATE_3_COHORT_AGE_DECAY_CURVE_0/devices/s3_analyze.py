#!/usr/bin/env python3
"""r9_screen STEP 2/3/4 -- the curve, the rho screen, the arithmetic. ENV WHITELIST = EMPTY SET."""
import os, json, time, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON",
     "SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","TILT","TILT_TAU","TILT_K","JUDGE_HC","V2"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _f(*a,**k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get=_f
OUT="/workspace/uplift_2026-09-11/r9_screen"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000; AMAX=84
Z=np.load(OUT+"/cohort_arrays.npz",allow_pickle=True)
ts=Z["ts"]; rec=Z["rec"]; cols=[str(c) for c in Z["cols"]]; ci={c:i for i,c in enumerate(cols)}
sel=np.zeros(len(ts),bool); sel[WARM:]=True; sel&= (ts<=CUT)
TS=ts[sel]
gA0=(rec[:,ci["net_ex"]]/rec[:,ci["gross_total"]])[sel]
GTOT=rec[:,ci["gross_total"]][sel]
R={"env_whitelist":[], "self_sha256":hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
   "caliber":"g = net_ex/gross_total bps/4h anchor per unit gross; post-warm drop 900 (E-0911-A); cut 2026-08-30 20Z (E-0911-D); cost = pinned costb_PWR_G230k.json (sha16 295b4e7b462373e4)",
   "n":int(sel.sum()),"window_utc":[time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[0]))),
                                    time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[-1])))]}
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
R["A0_reference_reproduced_first_hand"]={
  "n":int(len(gA0)),"mean_g_bps":round(float(gA0.mean()),4),"annualised_sharpe":round(sr(gA0),4),
  "SE_annualised_sharpe":round(float(np.sqrt(APY/len(gA0))),4),
  "turnover_mean":round(float(rec[:,ci["turnover"]][sel].mean()),5),
  "cost_ex_mean_bps":round(float((rec[:,ci["cost_ex"]]/rec[:,ci["gross_total"]])[sel].mean()),4),
  "brief_says":{"mean_g":0.6342,"sharpe":1.2912,"n":9138,"turnover":0.03032,"cost":0.1675}}
# ---- day-block bootstrap
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
def boot_idx(k):
    rng=np.random.default_rng([20260905,k]); pick=rng.integers(0,nd,size=(B,nd))
    return [np.concatenate([order[st[j]:en[j]] for j in pick[b]]) for b in range(B)]
BI=boot_idx(1)
def ci_of(fn):
    v=np.array([fn(ii) for ii in BI]); v=v[np.isfinite(v)]
    return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]
MODES=("PRORATA","FIFO")
BANDS=[("age0",0,0),("age1",1,1),("age2_5",2,5),("age6_11",6,11),("age12_23",12,23),
       ("age24_41",24,41),("age42_83",42,83),("age84p",84,84),("age1p",1,84),("age2p",2,84),
       ("age6p",6,84),("age12p",12,84),("age42p",42,84)]
for mode in MODES:
    P=Z[mode+"_P"][sel]; C=Z[mode+"_C"][sel]; K=Z[mode+"_K"][sel]; Gt=Z[mode+"_Gt"][sel]
    M={}
    # ---- R1/R2/R3 per-age curve
    tab=[]
    for a in range(AMAX+1):
        g=Gt[:,a].sum()
        if g<=0: continue
        tab.append({"age":a,"gross_share_pct":round(float(Gt[:,a].sum()/Gt.sum()*100),4),
          "holding_rate_bps":round(float((P[:,a]-C[:,a]).sum()/g),5),
          "gross_price_rate_bps":round(float(P[:,a].sum()/g),5),
          "carry_rate_bps":round(float(C[:,a].sum()/g),5),
          "cost_rate_bps":round(float(K[:,a].sum()/g),5),
          "net_rate_bps":round(float((P[:,a]-C[:,a]-K[:,a]).sum()/g),5),
          "contribution_to_A0_g_bps":round(float((P[:,a]-C[:,a]-K[:,a]).sum()/GTOT.sum()),5)})
        if a<=45 or a==AMAX: pass
    M["per_age_curve"]=tab
    M["contribution_sums_to_A0_g"]={"sum_of_contributions":round(float(sum(t["contribution_to_A0_g_bps"] for t in tab)),5),
                                    "A0_g_gross_weighted":round(float((rec[:,ci["net_ex"]][sel]).sum()/GTOT.sum()),5)}
    # ---- bands: standalone series, rho screen
    bands={}
    for nm,lo,hi in BANDS:
        p=P[:,lo:hi+1].sum(1); c=C[:,lo:hi+1].sum(1); k=K[:,lo:hi+1].sum(1); g=Gt[:,lo:hi+1].sum(1)
        ok=g>1e-9
        if ok.sum()<100: continue
        gb=np.where(ok,(p-c-k)/np.maximum(g,1e-300),np.nan)
        hb=np.where(ok,(p-c)/np.maximum(g,1e-300),np.nan)
        v=gb[ok]; a0=gA0[ok]
        rho=float(np.corrcoef(v,a0)[0,1])
        # conditional on A0 loss cells
        loss=ok&(gA0<0); win=ok&(gA0>=0)
        rho_loss=float(np.corrcoef(gb[loss],gA0[loss])[0,1]) if loss.sum()>50 else float("nan")
        rho_win=float(np.corrcoef(gb[win],gA0[win])[0,1]) if win.sum()>50 else float("nan")
        q=np.quantile(gA0,0.2); wq=ok&(gA0<=q)
        rho_q1=float(np.corrcoef(gb[wq],gA0[wq])[0,1]) if wq.sum()>50 else float("nan")
        okall=np.where(ok)[0]; okset=set(okall.tolist())
        def sub(ii,mask=None):
            jj=ii[np.isin(ii,okall)]
            if mask is not None: jj=jj[mask[jj]]
            return jj
        def f_rho(ii):
            jj=sub(ii)
            return np.corrcoef(gb[jj],gA0[jj])[0,1] if len(jj)>30 else np.nan
        def f_rho_loss(ii):
            jj=sub(ii,loss)
            return np.corrcoef(gb[jj],gA0[jj])[0,1] if len(jj)>30 else np.nan
        def f_mean(ii):
            jj=sub(ii); return gb[jj].mean() if len(jj)>30 else np.nan
        def f_sr(ii):
            jj=sub(ii)
            return gb[jj].mean()/np.std(gb[jj],ddof=1)*np.sqrt(APY) if len(jj)>30 else np.nan
        bands[nm]={"n_anchors":int(ok.sum()),
          "gross_share_pct":round(float(g.sum()/Gt.sum()*100),3),
          "mean_g_bps":round(float(np.nanmean(gb)),4),"mean_g_CI95":ci_of(f_mean),
          "holding_rate_bps":round(float((p-c).sum()/g.sum()),5),
          "sharpe":round(float(sr(v)),4),"sharpe_CI95":ci_of(f_sr),
          "SE_annualised_sharpe":round(float(np.sqrt(APY/ok.sum())),4),
          "rho_to_A0":round(rho,4),"rho_to_A0_CI95":ci_of(f_rho),
          "rho_to_A0_in_A0_LOSS_cells":round(rho_loss,4),"rho_loss_CI95":ci_of(f_rho_loss),
          "n_loss_cells":int(loss.sum()),
          "rho_to_A0_in_A0_WIN_cells":round(rho_win,4),
          "rho_to_A0_in_A0_worst_quintile":round(rho_q1,4),
          "mean_g_in_A0_loss_cells":round(float(np.nanmean(gb[loss])),4) if loss.sum()>50 else None,
          "A0_mean_g_in_loss_cells":round(float(gA0[loss].mean()),4),
          "cost_rate_bps":round(float(k.sum()/g.sum()),5)}
    M["bands"]=bands
    R[mode]=M
open(OUT+"/CURVE_r9screen.json","w").write(json.dumps(R,indent=1))
print(json.dumps(R["A0_reference_reproduced_first_hand"],indent=1))
for mode in MODES:
    print("=== ",mode," per-age (first 16 + tail) ===")
    t=R[mode]["per_age_curve"]
    for row in t[:16]+t[-3:]: print(row)
    print("SUMCHK",R[mode]["contribution_sums_to_A0_g"])
    print("--- bands ---")
    for nm,d in R[mode]["bands"].items():
        print("%-10s share%%=%7.3f  meanG=%8.4f  hold=%8.4f  SR=%7.3f  rhoA0=%+0.4f  rhoLOSS=%+0.4f"%(
            nm,d["gross_share_pct"],d["mean_g_bps"],d["holding_rate_bps"],d["sharpe"],d["rho_to_A0"],d["rho_to_A0_in_A0_LOSS_cells"]))
