"""OKXRHO final diagnostics: venue-specific residual, A0-loss-cell behaviour, combined-Sharpe arithmetic.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, json, datetime as dt
OUT="/workspace/r9okx"; A0B="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/"; MINE=f"{OUT}/dev/probe_artifacts/"
CAP=1788120000; BURN=14*86400
def ser(p,key="d30_n2_c42_rec"):
    a=np.load(p,allow_pickle=True); ci={str(c):i for i,c in enumerate(a["cols"])}; r=a[key]
    ts=r[:,ci["ts"]].astype(np.int64); gt=r[:,ci["gross_total"]]
    g=r[:,ci["net_ex"]]/np.where(gt>0,gt,np.nan)
    return ts,g,r[:,ci["turnover"]]
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True); LO=int(fe["okx_t0"])+BURN
A={}
for n,f in (("A0_s42","w10_ablation_series_V4_A0_dyn_s42.npz"),("A0_s2027","w10_ablation_series_V4_A0_dyn_s2027.npz")):
    A[n]=ser(A0B+f)
C={}
for n,f in (("OKX","R9_OKX_fund"),("BIN388","R9_BINCOLD388_fund"),("BINFULL","R9_BINCOLD_fund")):
    C[n]=ser(MINE+f"w10_ablation_series_{f}.npz")
ts0=A["A0_s42"][0]
keep=set(int(t) for t in ts0 if LO<=int(t)<=CAP)
for d in list(A.values())+list(C.values()): keep &= set(int(t) for t in d[0])
TS=np.array(sorted(keep))
def al(d):
    m={int(t):(v,w) for t,v,w in zip(d[0],d[1],d[2])}
    return np.array([m[t][0] for t in TS]), np.array([m[t][1] for t in TS])
gA0,_=al(A["A0_s42"]); gA0b,_=al(A["A0_s2027"])
gOK,tOK=al(C["OKX"]); g388,_=al(C["BIN388"]); gBF,_=al(C["BINFULL"])
ok=np.isfinite(gA0)&np.isfinite(gOK)&np.isfinite(g388)&np.isfinite(gBF)
TS,gA0,gA0b,gOK,tOK,g388,gBF=[x[ok] for x in (TS,gA0,gA0b,gOK,tOK,g388,gBF)]
def blocks(ts):
    d=(ts//86400); u,inv=np.unique(d,return_inverse=True); return [np.where(inv==k)[0] for k in range(len(u))]
def boot(fn,ts,*a,B=2000):
    bl=blocks(ts); nb=len(bl); o=np.empty(B)
    for k in range(B):
        rng=np.random.default_rng([20260905,k]); idx=np.concatenate([bl[p] for p in rng.integers(0,nb,nb)])
        o[k]=fn(*[x[idx] for x in a])
    return o
def ci(v): return round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)
res={"n":int(len(TS)),"lo":dt.datetime.utcfromtimestamp(int(TS[0])).isoformat()+"Z","hi":dt.datetime.utcfromtimestamp(int(TS[-1])).isoformat()+"Z"}

# 1) venue-specific residual: what a vendor would actually buy
X=np.column_stack([np.ones(len(TS)),gA0,g388])
beta=np.linalg.lstsq(X,gOK,rcond=None)[0]
resid=gOK-X@beta
b=boot(lambda r: float(r.mean()), TS, resid)
res["venue_residual"]={"beta_const":round(float(beta[0]),4),"beta_A0":round(float(beta[1]),4),"beta_BIN388":round(float(beta[2]),4),
  "mean_resid_bps":round(float(resid.mean()),4),"ci95":list(ci(b)),
  "sharpe_resid_ann":round(float(resid.mean()/resid.std(ddof=1)*np.sqrt(2190)),4),
  "R2_of_OKX_on_A0_and_BIN388":round(float(1-resid.var()/gOK.var()),4)}

# 2) A0-loss cells
for tag,g in (("OKX",gOK),("BIN388",g388),("BINFULL",gBF)):
    m=gA0<0; q=gA0<=np.quantile(gA0,0.2)
    res.setdefault("A0_loss_cells",{})[tag]={
      "n_loss":int(m.sum()),"mean_g_cand_in_loss":round(float(g[m].mean()),4),
      "ci95":list(ci(boot(lambda a,b_: float(a[b_<0].mean()), TS, g, gA0))),
      "rho_uncond":round(float(np.corrcoef(g,gA0)[0,1]),4),
      "rho_in_loss":round(float(np.corrcoef(g[m],gA0[m])[0,1]),4),
      "rho_in_worst_q20":round(float(np.corrcoef(g[q],gA0[q])[0,1]),4),
      "mean_g_cand_in_worst_q20":round(float(g[q].mean()),4)}
res["A0_loss_cells"]["A0_itself"]={"mean_g_A0_in_loss":round(float(gA0[gA0<0].mean()),4),
  "mean_g_A0_in_worst_q20":round(float(gA0[gA0<=np.quantile(gA0,0.2)].mean()),4)}

# 3) combined-Sharpe arithmetic (optimal 2-asset allocation)
def comb(s1,s2,rho):
    if abs(rho)>=1: return None
    return float(np.sqrt(max((s1*s1+s2*s2-2*rho*s1*s2)/(1-rho*rho),0.0)))
S_A0=1.2912; TARGET=3.966
rho_pt=float(np.corrcoef(gOK,gA0)[0,1])
s2_pt=float(gOK.mean()/gOK.std(ddof=1)*np.sqrt(2190))
res["combined_arithmetic"]={
 "S_A0_crossregime":S_A0,"target":TARGET,
 "rho_point":round(rho_pt,4),"cand_sharpe_point_418anchors":round(s2_pt,4),
 "SE_cand_sharpe":round(float(np.sqrt(2190/len(TS))),4),
 "combined_at_point_estimates":round(comb(S_A0,s2_pt,rho_pt),4),
 "gap_remaining":round(TARGET-comb(S_A0,s2_pt,rho_pt),4),
 "combined_if_cand_sharpe_zero":round(comb(S_A0,0.0,rho_pt),4),
 "cand_sharpe_needed_alone_at_rho0":3.705,
 "cand_sharpe_needed_to_hit_target_at_this_rho":round(float(
    rho_pt*S_A0+np.sqrt(max(TARGET*TARGET*(1-rho_pt*rho_pt)-S_A0*S_A0*(1-rho_pt*rho_pt)-0*0,0.0)+0.0)),4)}
# solve exactly: find s2 such that comb(S_A0,s2,rho)=TARGET
lo_,hi_=0.0,50.0
for _ in range(200):
    mid=(lo_+hi_)/2
    if comb(S_A0,mid,rho_pt)<TARGET: lo_=mid
    else: hi_=mid
res["combined_arithmetic"]["cand_sharpe_needed_to_hit_target_at_this_rho"]=round((lo_+hi_)/2,4)
print(json.dumps(res,indent=1)); json.dump(res,open(f"{OUT}/RESULT_final.json","w"),indent=1)
