#!/usr/bin/env python3
"""r10 COINT_PAIR STEP 2/3/4/5 -- independence, net edge, nulls, downside, arithmetic.
PREREG sha256 ca038101480e76e1... ENV WHITELIST = THE EMPTY SET (E-0826-D)."""
import os, sys, json, time, math, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH","LTRIM_TH",
     "CDAMP","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG",
     "W3FIX","KMOD","KTAIL","SEATF10","SEATNET","FUNDSCALE","RNSM","FTPOS","SLEEVE","REF_SKIP",
     "TILT","TILT_TAU","TILT_K","JUDGE_HC","V2","PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _forbid(*a,**k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get=_forbid
sys.path.insert(0,"/workspace/uplift_2026-09-11/r10_coint")
import s1_engine as EN
np=EN.np

OUT="/workspace/uplift_2026-09-11/r10_coint"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000; KMAX=40
tsA=EN.tsA; recA=EN.recA; ci=EN.ci; NW=EN.NW; AIDX=EN.AIDX; E_ts=EN.E_ts; y4=EN.y4
Z=np.load(OUT+"/main_W.npz",allow_pickle=True); W=np.asarray(Z["W"],np.float64); nact=Z["nact"]
stats=json.loads(str(Z["stats"]))

sel=np.zeros(len(tsA),bool); sel[WARM:]=True; sel&=(tsA<=CUT)
TS=tsA[sel]; NSEL=int(sel.sum())
gA0=(recA[:,ci["net_ex"]]/recA[:,ci["gross_total"]])[sel]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))

rows=tsA
def acct_rows(Wfull, shift=0, perm=None):
    Wr=np.zeros((len(rows),NW))
    for r,t in enumerate(rows):
        i=AIDX[int(t)]+shift
        if 0<=i<len(E_ts): Wr[r]=Wfull[i]
    if perm is not None: Wr=Wr[:,perm]
    return Wr, EN.account(Wr,rows)

# ---------- MAIN ARM ----------
AC=np.load(OUT+"/main_acct.npz")
P=AC["P"]; C=AC["C"]; K=AC["K"]; G=AC["G"]; TU=AC["TU"]; NAC=AC["nact"]
NET=P-C-K
g_alloc=NET[sel]                    # per unit ALLOCATED capital (gross budget = 1)
util=G[sel]                          # deployed gross / allocated
act=util>1e-12
g_book=np.where(act, NET[sel]/np.maximum(G[sel],1e-300), 0.0)

# ---------- day-block bootstrap ----------
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
def boot(k=1):
    rng=np.random.default_rng([20260905,k]); pick=rng.integers(0,nd,size=(B,nd))
    return [np.concatenate([order[st[j]:en[j]] for j in pick[b]]) for b in range(B)]
BI=boot(1)
def ci_of(fn):
    v=np.array([fn(ii) for ii in BI],float); v=v[np.isfinite(v)]
    return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]

R={"step":"STEP2345","env_whitelist":[],
   "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
   "engine_sha256":hashlib.sha256(open("/workspace/uplift_2026-09-11/r10_coint/s1_engine.py","rb").read()).hexdigest(),
   "prereg_sha256":"ca038101480e76e1ca2ed379a245bc59450315ed19fabc1eec938b87056b6b5e",
   "accounting_identity_vs_device_on_A0":EN.IDENT,
   "build_stats":stats,
   "n":NSEL,"window_utc":[time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[0]))),
                          time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[-1])))],
   "A0_reference":{"mean_g_bps":round(float(gA0.mean()),4),"sharpe":round(sr(gA0),4),
                   "SE_sharpe":round(float(np.sqrt(APY/NSEL)),4)}}

# ---------- STEP 3 : net edge ----------
R["STEP3_NET_EDGE"]={
 "deployment_rate_pct":round(float(act.mean()*100),3),
 "mean_utilisation_gross":round(float(util.mean()),5),
 "mean_active_pairs":round(float(NAC[sel].mean()),3),
 "per_unit_ALLOCATED_capital":{
   "gross_alpha_pnl_bps":round(float(P[sel].mean()),4),
   "carry_bps":round(float(C[sel].mean()),4),
   "cost_bps":round(float(K[sel].mean()),4),
   "net_mean_g_bps":round(float(g_alloc.mean()),4),
   "net_mean_g_CI95":ci_of(lambda ii: g_alloc[ii].mean()),
   "annualised_sharpe":round(sr(g_alloc),4),
   "sharpe_CI95":ci_of(lambda ii: g_alloc[ii].mean()/np.std(g_alloc[ii],ddof=1)*np.sqrt(APY)),
   "SE_annualised_sharpe":round(float(np.sqrt(APY/NSEL)),4),
   "turnover_mean":round(float(TU[sel].mean()),5)},
 "per_unit_DEPLOYED_gross_active_anchors_only":{
   "n_active":int(act.sum()),
   "net_mean_g_bps":round(float(g_book[act].mean()),4),
   "gross_alpha_bps":round(float((P[sel][act]/util[act]).mean()),4),
   "carry_bps":round(float((C[sel][act]/util[act]).mean()),4),
   "cost_bps":round(float((K[sel][act]/util[act]).mean()),4),
   "turnover_mean":round(float((TU[sel][act]/util[act]).mean()),5),
   "annualised_sharpe_on_active":round(sr(g_book[act]),4)},
}
gross_alpha=float(P[sel].sum()); costsum=float(K[sel].sum()); carrysum=float(C[sel].sum())
R["STEP3_NET_EDGE"]["cost_survival_pct_of_gross_price_alpha"]=round(float((gross_alpha-costsum)/gross_alpha*100),3) if gross_alpha!=0 else None
R["STEP3_NET_EDGE"]["net_survival_pct_of_gross_price_alpha"]=round(float(NET[sel].sum()/gross_alpha*100),3) if gross_alpha!=0 else None

# concentration-adjusted cost (pair book is ~5.7x per-name notional of the 450-name book)
IMP=EN.IMP; TIERS=EN.TIERS
names_book=float(np.mean([np.count_nonzero(W[AIDX[int(t)]]) for t in TS[::37]]))
scale=450.0/max(names_book,1.0)
adjR=np.array([EN.RATE[i]-IMP[i]+IMP[i]*(scale**0.87) for i in range(3)])
R["STEP3_NET_EDGE"]["concentration_adjusted_cost"]={
  "mean_nonzero_names_in_pair_book":round(names_book,2),
  "per_name_notional_multiple_vs_450":round(scale,3),
  "impact_multiplier_at_p0.87":round(float(scale**0.87),3),
  "base_tier_rates_bps":[round(float(x),4) for x in EN.RATE],
  "adjusted_tier_rates_bps":[round(float(x),4) for x in adjR]}

# ---------- STEP 2 : independence ----------
def rho_of(a,b,mask=None):
    if mask is not None: a=a[mask]; b=b[mask]
    if len(a)<30 or np.std(a)<1e-15 or np.std(b)<1e-15: return float("nan")
    return float(np.corrcoef(a,b)[0,1])
q20=float(np.quantile(gA0,0.2)); bot=gA0<=q20; loss=gA0<0
IND={}
for nm,gser in (("g_alloc",g_alloc),("g_book_active_only",g_book)):
    IND[nm]={
      "rho_to_A0":round(rho_of(gser,gA0),4),
      "rho_to_A0_CI95":ci_of(lambda ii: rho_of(gser[ii],gA0[ii])),
      "rho_in_A0_bottom_quintile":round(rho_of(gser,gA0,bot),4),
      "rho_bottom_quintile_CI95":ci_of(lambda ii: rho_of(gser[ii],gA0[ii],bot[ii])),
      "n_bottom_quintile":int(bot.sum()),
      "rho_in_A0_LOSS_cells":round(rho_of(gser,gA0,loss),4),
      "rho_loss_CI95":ci_of(lambda ii: rho_of(gser[ii],gA0[ii],loss[ii])),
      "n_loss_cells":int(loss.sum()),
      "mean_g_in_A0_bottom_quintile":round(float(gser[bot].mean()),4),
      "A0_mean_g_in_bottom_quintile":round(float(gA0[bot].mean()),4),
      "mean_g_in_A0_loss_cells":round(float(gser[loss].mean()),4)}
R["STEP2_INDEPENDENCE"]=IND
R["STEP2_INDEPENDENCE"]["A0_bottom_quintile_threshold_bps"]=round(q20,4)

# ---------- G1 : offset spectrum (leakage gate) ----------
spec={}
for L in range(-5,6):
    Wr,(p,c,k,g,tu)=acct_rows(W,shift=L)
    net=(p-c-k)[sel]
    spec[str(L)]={"mean_g_alloc_bps":round(float(net.mean()),4),"turnover":round(float(tu[sel].mean()),5)}
    print("OFFSET",L,spec[str(L)],flush=True)
R["G1_OFFSET_SPECTRUM"]=spec
R["G1_peak_lag"]=max(spec,key=lambda k: spec[k]["mean_g_alloc_bps"])

# ---------- STEP 3b : turnover-matched nulls ----------
NUL={}
for k in (101,503,1009):
    Wr,(p,c,kk,g,tu)=acct_rows(W,shift=-k)   # book at t uses the weight path from t-k
    net=(p-c-kk)[sel]
    NUL["SHIFT%d"%k]={"mean_g_alloc_bps":round(float(net.mean()),4),"sharpe":round(sr(net),4),
                      "turnover":round(float(tu[sel].mean()),5)}
for d in (1,2,3):
    rng=np.random.default_rng([4242,d]); pi=rng.permutation(NW)
    Wr,(p,c,kk,g,tu)=acct_rows(W,perm=pi)
    net=(p-c-kk)[sel]
    NUL["RELAB%d"%d]={"mean_g_alloc_bps":round(float(net.mean()),4),"sharpe":round(sr(net),4),
                      "turnover":round(float(tu[sel].mean()),5)}
real=float(g_alloc.mean())
R["STEP3b_TURNOVER_MATCHED_NULLS"]={"REAL_mean_g_alloc_bps":round(real,4),
  "REAL_mean_g_CI95":R["STEP3_NET_EDGE"]["per_unit_ALLOCATED_capital"]["net_mean_g_CI95"],
  "nulls":NUL,
  "null_min":round(min(v["mean_g_alloc_bps"] for v in NUL.values()),4),
  "null_max":round(max(v["mean_g_alloc_bps"] for v in NUL.values()),4),
  "REAL_beats_all_6":bool(all(real>v["mean_g_alloc_bps"] for v in NUL.values()))}

# ---------- STEP 4 : downside ----------
mkt=np.zeros(len(rows))
for r,t in enumerate(rows):
    i=AIDX[int(t)]; m=EN.MEM[i]
    v=y4[i,m]; v=v[np.isfinite(v)]
    mkt[r]=float(v.mean()*1e4) if len(v) else 0.0
mk=mkt[sel]
def beta(x): 
    return float(np.cov(x,mk)[0,1]/np.var(mk)) if np.var(mk)>0 else float("nan")
def mdd(x):
    cum=np.cumsum(x); return float(np.max(np.maximum.accumulate(cum)-cum))
day=TS//86400; ud2,inv2=np.unique(day,return_inverse=True)
dayg=np.bincount(inv2,weights=g_alloc); dayA=np.bincount(inv2,weights=gA0)
netlong=np.array([W[AIDX[int(t)]].sum() for t in TS])
# tail concentration ruler (rs_conc.py form, per unit gross)
tops=[]
for r in np.where(sel)[0]:
    i=AIDX[int(rows[r])]; w=W[i]
    g=np.abs(w).sum()
    if g<=1e-12: continue
    c=(w/g)*np.nan_to_num(y4[i],nan=0.0)*1e4
    o=np.argsort(-np.abs(c))
    tops.append((float(c.sum()),float(c[o[:5]].sum()),float(c[o[:20]].sum()),int(np.count_nonzero(w))))
Tp=np.array(tops); tot=Tp[:,0].mean()
R["STEP4_DOWNSIDE"]={
 "net_beta_to_equalweight_universe":round(beta(g_alloc),5),
 "A0_net_beta":round(beta(gA0),5),
 "mean_netlong_over_gross":round(float((netlong/np.maximum(util,1e-300))[act].mean()),5),
 "worst_UTC_day_bps":round(float(dayg.min()),3),"A0_worst_UTC_day_bps":round(float(dayA.min()),3),
 "worst_UTC_day_date":time.strftime("%Y-%m-%d",time.gmtime(int(ud2[int(np.argmin(dayg))]*86400))),
 "maxDD_bps_of_gross":round(mdd(g_alloc),2),"A0_maxDD_bps_of_gross":round(mdd(gA0),2),
 "combined_worst_day_at_50_50_bps":round(float((0.5*dayg+0.5*dayA).min()),3),
 "tail_concentration":{"n_anchors":int(len(Tp)),"mean_names_nonzero":round(float(Tp[:,3].mean()),2),
   "leg_ret_bps":round(float(tot),4),
   "top5_share_of_mean":round(float(Tp[:,1].mean()/tot),4) if abs(tot)>1e-12 else None,
   "top20_share_of_mean":round(float(Tp[:,2].mean()/tot),4) if abs(tot)>1e-12 else None,
   "live_fund_leg_control_top20_share":0.1109,
   "ruler":"rs_conc.py sha16 3fd2f76496a593ba form: c_i=(w_i/gross)*y4_i*1e4"}}

# ---------- STEP 5 : arithmetic ----------
s1=sr(gA0); SE=float(np.sqrt(APY/NSEL)); TARGET=3.0+1.96*SE
def comb(s1,s2,r):
    num=s1*s1+s2*s2-2*r*s1*s2; den=1.0-r*r
    return math.sqrt(num/den) if den>1e-12 and num>0 else float("nan")
def s2_needed(s1,r,tgt):
    a=1.0; b=-2*r*s1; c=s1*s1-tgt*tgt*(1-r*r); d=b*b-4*a*c
    return (-b+math.sqrt(d))/2 if d>=0 else float("nan")
s2=sr(g_alloc); rr=rho_of(g_alloc,gA0)
alloc={}
for wgt in (0.1,0.2,0.3,0.5):
    x=(1-wgt)*gA0/np.std(gA0,ddof=1)+wgt*g_alloc/np.std(g_alloc,ddof=1) if np.std(g_alloc,ddof=1)>0 else gA0
    alloc["risk_weight_%.2f"%wgt]={"combined_sharpe":round(sr(x),4),"delta_vs_A0":round(sr(x)-s1,4)}
R["STEP5_ARITHMETIC"]={
 "A0_sharpe":round(s1,4),"candidate_standalone_sharpe":round(s2,4),"rho":round(rr,4),
 "target_point_estimate_for_CI95_lb_over_3.0":round(TARGET,4),
 "gap_in_SE":round((TARGET-s1)/SE,3),
 "zero_rho_standalone_sharpe_that_would_close_gap":round(math.sqrt(max(TARGET*TARGET-s1*s1,0)),4),
 "combined_sharpe_variance_optimal":round(comb(s1,s2,rr),4),
 "delta_vs_A0_variance_optimal":round(comb(s1,s2,rr)-s1,4),
 "standalone_sharpe_needed_at_this_rho":round(s2_needed(s1,rr,TARGET),4),
 "shortfall_multiple":round(s2_needed(s1,rr,TARGET)/s2,3) if s2>0 else None,
 "risk_parity_ladder_empirical":alloc,
 "formula":"combined = sqrt((s1^2+s2^2-2*rho*s1*s2)/(1-rho^2))"}
np.savez_compressed(OUT+"/main_series.npz",ts=TS,g_alloc=g_alloc,g_book=g_book,gA0=gA0,util=util,
                    turn=TU[sel],P=P[sel],C=C[sel],K=K[sel])
open(OUT+"/STEP2345.json","w").write(json.dumps(R,indent=1))
print(json.dumps({k:v for k,v in R.items() if k not in ("G1_OFFSET_SPECTRUM",)},indent=1))
