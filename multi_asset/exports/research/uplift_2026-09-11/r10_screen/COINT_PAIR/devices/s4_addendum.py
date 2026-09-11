#!/usr/bin/env python3
"""r10 COINT_PAIR addendum -- sign-reversal arithmetic, concentration-repriced cost, gross-alpha CI,
per-year table, and the honest long-only allocation ladder. ENV WHITELIST = EMPTY SET (E-0826-D)."""
import os, sys, json, time, math, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON",
     "SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","TILT","JUDGE_HC","V2","PANEL_IN"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _forbid(*a,**k): raise AssertionError("E-0826-D violation")
os.environ.get=_forbid
sys.path.insert(0,"/workspace/uplift_2026-09-11/r10_coint")
import s1_engine as EN
np=EN.np
OUT="/workspace/uplift_2026-09-11/r10_coint"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000
tsA=EN.tsA; recA=EN.recA; ci=EN.ci; NW=EN.NW; AIDX=EN.AIDX; y4=EN.y4; qvk=EN.qvk
sel=np.zeros(len(tsA),bool); sel[WARM:]=True; sel&=(tsA<=CUT); TS=tsA[sel]; N=int(sel.sum())
gA0=(recA[:,ci["net_ex"]]/recA[:,ci["gross_total"]])[sel]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
rng=np.random.default_rng([20260905,1]); pick=rng.integers(0,nd,size=(B,nd))
BI=[np.concatenate([order[st[j]:en[j]] for j in pick[b]]) for b in range(B)]
def ci_of(x):
    v=np.array([x[ii].mean() for ii in BI],float)
    return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]
Z=np.load(OUT+"/main_W.npz",allow_pickle=True); W=np.asarray(Z["W"],np.float64)
AC=np.load(OUT+"/main_acct.npz"); P=AC["P"];C=AC["C"];K=AC["K"];G=AC["G"];TU=AC["TU"]
g=(P-C-K)[sel]
R={"step":"ADDENDUM","env_whitelist":[],
   "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
   "prereg_sha256":"ca038101480e76e1ca2ed379a245bc59450315ed19fabc1eec938b87056b6b5e"}
# ---- does the mean-reversion edge exist at all, gross of cost?
R["gross_edge_exists"]={
 "gross_price_alpha_bps":round(float(P[sel].mean()),4),"CI95":ci_of(P[sel]),
 "gross_minus_carry_bps":round(float((P-C)[sel].mean()),4),"CI95_gross_minus_carry":ci_of((P-C)[sel]),
 "cost_bps":round(float(K[sel].mean()),4),"CI95_cost":ci_of(K[sel]),
 "cost_as_pct_of_ABS_gross_price_alpha":round(float(K[sel].mean()/abs(P[sel].mean())*100),2),
 "gross_sharpe_if_cost_were_zero":round(sr((P-C)[sel]),4),
 "gross_price_only_sharpe":round(sr(P[sel]),4)}
# ---- the reverse-sign book (short the spread rule): cost is sign-invariant
netrev=(-P+C-K)[sel]
R["reverse_sign_book"]={
 "note":"flipping the rule flips pnl and carry but NOT cost; cost is a two-sided tax",
 "net_mean_g_bps":round(float(netrev.mean()),4),"CI95":ci_of(netrev),"sharpe":round(sr(netrev),4)}
# ---- concentration-repriced cost
nzc=np.array([np.count_nonzero(W[AIDX[int(t)]]) for t in TS])
WD=EN.WD
nzA=np.array([np.count_nonzero(WD[r]) for r in np.where(sel)[0]])
scale=float(nzA.mean())/float(nzc.mean())
IMP=EN.IMP; adjR=np.array([EN.RATE[i]-IMP[i]+IMP[i]*(scale**0.87) for i in range(3)])
rows=tsA
Kadj=np.zeros(len(rows)); prev=np.zeros(NW)
for r,t in enumerate(rows):
    i=AIDX[int(t)]; m=EN.MEM[i]
    mk=EN.UROW.get(EN.pw_row[int(t)])
    if mk is not None: m=m[mk[m]]
    w=W[i]
    qv4h=np.expm1(np.clip(qvk[i,m],0,30))*48; rt=np.zeros(NW); rt[m]=adjR[EN.tier_of(qv4h)]
    Kadj[r]=float((np.abs(w-prev)*rt).sum()); prev=w
gadj=(P-C-Kadj)[sel]
R["concentration_repriced"]={
 "mean_nonzero_names_A0_live_book":round(float(nzA.mean()),2),
 "mean_nonzero_names_pair_book":round(float(nzc.mean()),2),
 "per_name_notional_multiple":round(scale,3),
 "impact_multiplier_at_exponent_0.87":round(float(scale**0.87),3),
 "base_tier_rates_bps":[round(float(x),4) for x in EN.RATE],
 "repriced_tier_rates_bps":[round(float(x),4) for x in adjR],
 "cost_bps_base":round(float(K[sel].mean()),4),"cost_bps_repriced":round(float(Kadj[sel].mean()),4),
 "net_mean_g_bps_repriced":round(float(gadj.mean()),4),"CI95":ci_of(gadj),
 "sharpe_repriced":round(sr(gadj),4)}
# ---- break-even: what cost rate would the book need?
be=float(P[sel].mean()-C[sel].mean())/float(TU[sel].mean())
R["break_even"]={
 "turnover_mean_pair_book":round(float(TU[sel].mean()),5),
 "turnover_mean_A0":round(float(recA[:,ci["turnover"]][sel].mean()),5),
 "turnover_multiple_vs_A0":round(float(TU[sel].mean()/recA[:,ci["turnover"]][sel].mean()),3),
 "realised_cost_rate_bps_per_unit_turnover":round(float(K[sel].mean()/TU[sel].mean()),4),
 "break_even_cost_rate_bps_per_unit_turnover":round(be,4),
 "pinned_book_avg_rate_bps":2.9537,
 "verdict":"the book needs a per-unit-turnover cost rate of %.3f bps; the fitted model charges %.3f bps"%(be,float(K[sel].mean()/TU[sel].mean()))}
# ---- honest long-only allocation ladder on ACTUAL gross budget (not variance-optimal)
lad={}
sA=float(np.std(gA0,ddof=1)); sC=float(np.std(g,ddof=1))
for wgt in (0.05,0.10,0.15,0.20,0.30):
    x=(1-wgt)*gA0+wgt*g*(sA/sC)          # risk-weight wgt to the candidate, long only
    lad["risk_weight_%.2f"%wgt]={"combined_sharpe":round(sr(x),4),"delta_vs_A0":round(sr(x)-sr(gA0),4)}
R["long_only_allocation_ladder"]={"note":"candidate scaled to A0's per-anchor vol, then risk-weighted LONG. The variance-optimal formula in STEP5 puts a NEGATIVE weight on this candidate (its Sharpe is negative) and is therefore not a deliverable allocation.",
  "ladder":lad,"A0_sharpe":round(sr(gA0),4)}
# ---- per-year table
yr=np.array([int(time.strftime("%Y",time.gmtime(int(t)))) for t in TS])
tab={}
for y in sorted(set(yr.tolist())):
    mm=yr==y
    tab[str(y)]={"n":int(mm.sum()),"pair_net_mean_g_bps":round(float(g[mm].mean()),4),
                 "pair_gross_bps":round(float(P[sel][mm].mean()),4),
                 "pair_cost_bps":round(float(K[sel][mm].mean()),4),
                 "pair_sharpe":round(sr(g[mm]),3),
                 "A0_mean_g_bps":round(float(gA0[mm].mean()),4),"A0_sharpe":round(sr(gA0[mm]),3)}
R["per_year"]=tab
open(OUT+"/ADDENDUM.json","w").write(json.dumps(R,indent=1))
print(json.dumps(R,indent=1))
