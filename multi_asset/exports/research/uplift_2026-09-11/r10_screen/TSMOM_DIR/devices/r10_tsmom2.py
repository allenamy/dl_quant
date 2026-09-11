"""R10 SCREEN TSMOM_DIR -- part 2: GATE A exact, conditional independence, turnover-matched nulls,
downside, combination arithmetic.  ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os, json, hashlib, time
_F = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
      "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","SLEEVE","SEATNET","CDAMP",
      "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","SEATF10","KTAIL","FUNDSCALE","TRADE_TOPN","RNSM",
      "FTPOS","LTRIM_TH","FTRIM_TH","REF_SKIP","PANEL","EXPORT_PANEL","EMA_STATE_JSON")
_bad=[k for k in _F if k in os.environ]; assert not _bad, "E-0826-D env violation: %r"%_bad
import numpy as np
from scipy.stats import spearmanr

OUT="/workspace/uplift_2026-09-11/r10_tsmom"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
UMASK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
CAP=1788120000; WARM=900; QVMIN=250000.0
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
SHAS={k:sha(v) for k,v in dict(META=META,A0=A0P,PANEL=PANEL,COSTB=COSTB,UMASK=UMASK).items()}
for k,v in SHAS.items(): print("SHA256 %-6s %s"%(k,v),flush=True)

m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; T,N=Y.shape
PW=np.load(PANEL,allow_pickle=True); pts=PW["ts"].astype(np.int64)
FNz=np.nan_to_num(PW["f_fund_now"].astype(np.float64),nan=0.0)
IVr=PW["f_fund_iv"].astype(np.float64); IVf=np.where(np.isfinite(IVr)&(IVr>0),IVr,8.0)
pw_row={int(t):j for j,t in enumerate(pts)}
CB=json.load(open(COSTB)); RATE=np.array([t["maker_share"]*t["maker_bps"]+(1-t["maker_share"])*t["taker_bps"] for t in CB["tiers"]])
A=np.load(A0P,allow_pickle=True); cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
RECd=np.asarray(A["d30_n2_c42_rec"],float); WMAT=np.asarray(A["d30_n2_c42_W"],float)
a_ts=RECd[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=WARM)&(a_ts<=CAP); ts_k=a_ts[keep]; NW=int(keep.sum()); assert NW==9138
pos={int(t):i for i,t in enumerate(E_ts)}; IDX=np.array([pos[int(t)] for t in ts_k])
JDX=np.array([pw_row[int(t)] for t in ts_k])
gA0=RECd[keep,ci["net_ex"]]/RECd[keep,ci["gross_total"]]
A0turn=RECd[keep,ci["turnover"]]; A0nl=RECd[keep,ci["netlong"]]
gA0_S0=np.asarray(A["S0_rec"],float)[keep,ci["net_ex"]]/np.asarray(A["S0_rec"],float)[keep,ci["gross_total"]]

# ---------------- exact member reconstruction (UMASK_SCOPE=m1 -> members restricted by the mask)
UM=np.load(UMASK,allow_pickle=True); print("umask keys",[str(k) for k in UM.keys()],flush=True)
uts=UM["ts"].astype(np.int64) if "ts" in UM else None
UMAT=UM["mask"] if "mask" in UM else UM[[k for k in UM.keys() if k!="ts"][0]]
umap={int(t):i for i,t in enumerate(uts)}
MEMB=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
MEMB_M1=MEMB.copy()
nmiss=0
for ii in range(NW):
    t=IDX[ii]; j=JDX[ii]; k=umap.get(int(ts_k[ii]))
    if k is None: nmiss+=1; continue
    MEMB_M1[t] = MEMB[t] & np.asarray(UMAT[k],bool)
print("umask rows missing:",nmiss,flush=True)
Yz=np.where(np.isfinite(Y),Y,0.0)
pnl_dev=RECd[keep,ci["pnl"]]; car_dev=RECd[keep,ci["carry"]]
Wk=WMAT[keep]
pnl_me=1e4*np.array([float((Wk[i][MEMB_M1[IDX[i]]]*Yz[IDX[i]][MEMB_M1[IDX[i]]]).sum()) for i in range(NW)])
car_me=1e4*np.array([float((Wk[i][MEMB_M1[IDX[i]]]*FNz[JDX[i]][MEMB_M1[IDX[i]]]*(4.0/IVf[JDX[i]][MEMB_M1[IDX[i]]])).sum()) for i in range(NW)])
GA=float(np.max(np.abs(pnl_me-pnl_dev))); GA2=float(np.max(np.abs(car_me-car_dev)))
print("GATE A  (umask-exact) max|pnl_me-pnl_dev|   = %.3e bps"%GA,flush=True)
print("GATE A2 (umask-exact) max|carry_me-carry_dev| = %.3e bps"%GA2,flush=True)
print("        corr(pnl_me,pnl_dev) = %.9f"%float(np.corrcoef(pnl_me,pnl_dev)[0,1]),flush=True)

# ---------------- rebuild the primary arm (self-contained, same code as part 1)
QV4H=np.expm1(np.clip(QV,0,30))*48.0; FIN=np.isfinite(Y)
ELIG=MEMB&FIN&(QV4H>=QVMIN)
TIER=np.full((T,N),2,np.int8); TIER[QV4H>=1e6]=1; TIER[QV4H>=5e6]=0
MKT=np.array([float(np.nanmean(np.where(ELIG[t],Y[t],np.nan))) if ELIG[t].any() else 0.0 for t in range(T)])
def trail_sum(k):
    S=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1): S[j:]+=Yz[:T-j]; C[j:]+=FIN[:T-j]
    return S,C
S42,C42=trail_sum(42); VAL42=C42>=30
def build(score,valid,ema=1.0,minn=20,colperm=None,shift=0):
    Wb=np.zeros((NW,N)); prev=np.zeros(N)
    for ii in range(NW):
        t=IDX[ii]-shift
        if t<0: Wb[ii]=prev; continue
        sc_row=score[t]; val_row=valid[t]
        if colperm is not None: sc_row=sc_row[colperm]; val_row=val_row[colperm]
        e=ELIG[IDX[ii]]&val_row&np.isfinite(sc_row)
        n=int(e.sum())
        if n<minn: Wb[ii]=prev; continue
        raw=np.zeros(N); raw[e]=sc_row[e]; aw=np.abs(raw).sum()
        if aw<=0: Wb[ii]=prev; continue
        w=ema*(raw/aw)+(1.0-ema)*prev; aw2=np.abs(w).sum()
        if aw2>0: w=w/aw2
        Wb[ii]=w; prev=w
    return Wb
def account(Wb):
    pnl=1e4*np.einsum("ij,ij->i",Wb,Yz[IDX])
    car=1e4*np.array([float((Wb[i]*FNz[JDX[i]]*(4.0/IVf[JDX[i]])).sum()) for i in range(NW)])
    dW=np.abs(np.diff(Wb,axis=0,prepend=np.zeros((1,N))))
    cst=np.array([float((dW[i]*RATE[TIER[IDX[i]]]).sum()) for i in range(NW)])
    return dict(pnl=pnl,carry=car,cost=cst,net=pnl-car-cst,turn=dW.sum(1),
                netlong=Wb.sum(1)/np.maximum(np.abs(Wb).sum(1),1e-12))
SC=np.sign(S42)
Wp=build(SC,VAL42); R=account(Wp); gT=R["net"]
print("PRIMARY TSMOM_L42_raw net g %+.4f  SR %+.4f  turn %.4f"%(gT.mean(),gT.mean()/gT.std(ddof=1)*np.sqrt(2190),R["turn"].mean()),flush=True)

DAY=(ts_k//86400).astype(np.int64); UD=np.unique(DAY); DIDX=[np.where(DAY==d)[0] for d in UD]
def boot(fn,B=2000,base=20260905):
    o=np.empty(B)
    for b in range(B):
        rng=np.random.default_rng([base,b]); pick=rng.integers(0,len(UD),len(UD))
        sel=np.concatenate([DIDX[p] for p in pick]); o[b]=fn(sel)
    return o
def ci(v): return [float(np.percentile(v,2.5)),float(np.percentile(v,97.5))]
def ann(x):
    s=float(np.std(x,ddof=1)); return float(np.mean(x)/s*np.sqrt(2190)) if s>0 else float("nan")
RES={}

# ---------------- STEP 2 independence
def _rho(sel): 
    a=gT[sel]; b=gA0[sel]
    return float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else np.nan
rho=float(np.corrcoef(gT,gA0)[0,1]); rb=boot(_rho)
q20=np.quantile(gA0,0.20); lose=gA0<=q20
lo_days=set(DAY[lose].tolist())
def _rho_lo(sel):
    s=sel[lose[sel]]
    if len(s)<50: return np.nan
    a=gT[s]; b=gA0[s]
    return float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else np.nan
rlo=float(np.corrcoef(gT[lose],gA0[lose])[0,1]); rlb=boot(_rho_lo); rlb=rlb[np.isfinite(rlb)]
RES["independence"]=dict(
  rho_uncond=rho, rho_uncond_CI95=ci(rb), spearman_uncond=float(spearmanr(gT,gA0).statistic),
  rho_A0_bottom_quintile=rlo, rho_bottomq_CI95=ci(rlb), n_bottom_quintile=int(lose.sum()),
  A0_bottomq_threshold=float(q20), rho_diff_bottom_minus_uncond=float(rlo-rho),
  rho_diff_CI95=ci(rlb-rb[:len(rlb)]) if len(rlb)==2000 else None)
print("rho uncond %+.4f CI %s | rho in A0 bottom quintile %+.4f CI %s"%(rho,np.round(RES["independence"]["rho_uncond_CI95"],4),rlo,np.round(RES["independence"]["rho_bottomq_CI95"],4)),flush=True)

# the hedge test that matters: conditional MEAN, not conditional rho
qs=np.quantile(gA0,[0.2,0.4,0.6,0.8]); bucket=np.digitize(gA0,qs)
qt={}
for b in range(5):
    msk=bucket==b
    mb=boot(lambda s,msk=msk: float(gT[s[msk[s]]].mean()) if msk[s].sum()>20 else np.nan)
    mb=mb[np.isfinite(mb)]
    qt["Q%d"%b]=dict(n=int(msk.sum()),A0_mean=float(gA0[msk].mean()),TSMOM_mean=float(gT[msk].mean()),
                     TSMOM_CI95=ci(mb))
    print("  A0 Q%d n=%4d A0 %+8.3f  TSMOM %+8.4f CI[%+7.3f,%+7.3f]"%(b,msk.sum(),gA0[msk].mean(),gT[msk].mean(),qt["Q%d"%b]["TSMOM_CI95"][0],qt["Q%d"%b]["TSMOM_CI95"][1]),flush=True)
d10=np.quantile(gA0,0.10); w10=gA0<=d10
mb=boot(lambda s: float(gT[s[w10[s]]].mean()) if w10[s].sum()>20 else np.nan); mb=mb[np.isfinite(mb)]
qt["A0_worst_decile"]=dict(n=int(w10.sum()),A0_mean=float(gA0[w10].mean()),TSMOM_mean=float(gT[w10].mean()),TSMOM_CI95=ci(mb))
print("  A0 worst decile n=%d A0 %+.3f TSMOM %+.4f CI %s"%(w10.sum(),gA0[w10].mean(),gT[w10].mean(),np.round(qt["A0_worst_decile"]["TSMOM_CI95"],3)),flush=True)
RES["conditional_means"]=qt

# ---------------- STEP 3 nulls, turnover-matched (SHIFT / RELAB families, per r3_attack null.py)
NULLS={}
for k in (101,503,1009):
    Wn=build(SC,VAL42,shift=k); Rn=account(Wn)
    NULLS["SHIFT%d"%k]=dict(net_g=float(Rn["net"].mean()),SR=ann(Rn["net"]),turn=float(Rn["turn"].mean()),
                            gross_price=float(Rn["pnl"].mean()))
    print("  NULL SHIFT%-5d net %+8.4f SR %+6.3f turn %.4f"%(k,Rn["net"].mean(),ann(Rn["net"]),Rn["turn"].mean()),flush=True)
for d in (1,2,3):
    rng=np.random.default_rng([4242,d]); pi=rng.permutation(N)
    Wn=build(SC,VAL42,colperm=pi); Rn=account(Wn)
    NULLS["RELAB%d"%d]=dict(net_g=float(Rn["net"].mean()),SR=ann(Rn["net"]),turn=float(Rn["turn"].mean()),
                            gross_price=float(Rn["pnl"].mean()))
    print("  NULL RELAB%-5d net %+8.4f SR %+6.3f turn %.4f"%(d,Rn["net"].mean(),ann(Rn["net"]),Rn["turn"].mean()),flush=True)
nv=np.array([NULLS[k]["net_g"] for k in NULLS])
RES["nulls"]=dict(detail=NULLS,null_mean=float(nv.mean()),null_min=float(nv.min()),null_max=float(nv.max()),
                  real_net_g=float(gT.mean()),
                  real_exceeds_all_nulls=bool(gT.mean()>nv.max()))
print("  NULL family: mean %+.4f range [%+.4f,%+.4f] vs REAL %+.4f"%(nv.mean(),nv.min(),nv.max(),gT.mean()),flush=True)

# ---------------- STEP 4 downside
def mdd(g):
    c=np.cumsum(g); pk=np.maximum.accumulate(c); return float(np.max(pk-c))
def dayagg(g):
    o={}
    for d,ix in zip(UD,DIDX): o[int(d)]=float(g[ix].sum())
    return o
def worstday(g):
    dd=np.array([g[ix].sum() for ix in DIDX]); i=int(np.argmin(dd))
    return float(dd.min()), time.strftime("%Y-%m-%d",time.gmtime(int(UD[i])*86400)), float(dd.mean()), float(np.percentile(dd,1))
def betas(g):
    mk=MKT[IDX]*1e4
    b=float(np.polyfit(mk,g,1)[0]); r=float(np.corrcoef(mk,g)[0,1])
    return b,r
bT,rT=betas(gT); bA,rA=betas(gA0)
wT=worstday(gT); wA=worstday(gA0)
tot=np.abs(gT).sum(); top5=float(np.sort(np.abs(gT))[-5:].sum()/tot)
RES["downside_standalone"]=dict(
  netlong_mean=float(R["netlong"].mean()), netlong_abs_mean=float(np.abs(R["netlong"]).mean()),
  netlong_p5_p95=[float(np.percentile(R["netlong"],5)),float(np.percentile(R["netlong"],95))],
  A0_netlong_mean=float(A0nl.mean()), A0_netlong_abs_mean=float(np.abs(A0nl).mean()),
  beta_to_market_bps_per_bps=bT, corr_to_market=rT,
  A0_beta_to_market=bA, A0_corr_to_market=rA,
  sd_per_anchor_bps=float(gT.std(ddof=1)), A0_sd_per_anchor_bps=float(gA0.std(ddof=1)),
  vol_ratio_TSMOM_over_A0=float(gT.std(ddof=1)/gA0.std(ddof=1)),
  worst_utc_day_bps=wT[0], worst_utc_day=wT[1], p1_utc_day_bps=wT[3],
  A0_worst_utc_day_bps=wA[0], A0_worst_utc_day=wA[1], A0_p1_utc_day_bps=wA[3],
  maxDD_bps=mdd(gT), A0_maxDD_bps=mdd(gA0), top5_anchor_share_of_absPnL=top5)
print("\nDOWNSIDE standalone: netlong mean %+.4f abs %.4f | beta_mkt %+.4f (A0 %+.4f) | sd %.2f vs A0 %.2f (x%.2f)"
      %(R["netlong"].mean(),np.abs(R["netlong"]).mean(),bT,bA,gT.std(ddof=1),gA0.std(ddof=1),gT.std(ddof=1)/gA0.std(ddof=1)),flush=True)
print("  worst UTC day TSMOM %+.1f bps (%s) | A0 %+.1f bps (%s) | maxDD TSMOM %.1f A0 %.1f"%(wT[0],wT[1],wA[0],wA[1],mdd(gT),mdd(gA0)),flush=True)

# ---------------- STEP 5 combination (gross adds: combined g = (gA0 + c*gT)/(1+c))
COMB={}
s1=ann(gA0); s2=ann(gT)
for c in (0.02,0.05,0.10,0.20,0.30,0.50,1.00):
    gc=(gA0+c*gT)/(1.0+c); w=worstday(gc)
    mb=boot(lambda s,gc=gc: float(gc[s].mean()))
    COMB["c=%.2f"%c]=dict(mean_g=float(gc.mean()),CI95=ci(mb),SR=ann(gc),maxDD_bps=mdd(gc),
                          worst_utc_day_bps=w[0],worst_utc_day=w[1],p1_day_bps=w[3],
                          dSR=float(ann(gc)-s1),dMaxDD=float(mdd(gc)-mdd(gA0)),
                          dWorstDay=float(w[0]-wA[0]))
    print("  c=%.2f  g %+.4f  SR %+.4f (dSR %+.4f)  maxDD %.1f (d%+.1f)  worstday %+.1f (d%+.1f)"
          %(c,gc.mean(),ann(gc),ann(gc)-s1,mdd(gc),mdd(gc)-mdd(gA0),w[0],w[0]-wA[0]),flush=True)
# in-sample-optimal 2-asset Sharpe (UPPER BOUND)
rho_=rho
S_opt=float(np.sqrt((s1**2+s2**2-2*rho_*s1*s2)/(1-rho_**2)))
x1=(s1-rho_*s2)/(1-rho_**2); x2=(s2-rho_*s1)/(1-rho_**2)
volratio=float(gT.std(ddof=1)/gA0.std(ddof=1))
gross_share=float((x2/volratio)/(x1+x2/volratio)) if (x1+x2/volratio)>0 else float("nan")
SEsr=float(np.sqrt(2190.0/NW))
RES["combination"]=dict(A0_SR=s1,TSMOM_SR=s2,rho=rho_,
  SR_optimal_insample_upper_bound=S_opt,dSR_optimal=float(S_opt-s1),
  risk_share_TSMOM=float(x2/(x1+x2)),gross_share_TSMOM=gross_share,
  SE_annualised_sharpe=SEsr,dSR_in_SE=float((S_opt-s1)/SEsr),
  target_SR=3.966,gap_from_A0=float(3.966-s1),gap_from_optimal_combo=float(3.966-S_opt),
  grid=COMB)
print("\nOPTIMAL(in-sample UPPER BOUND) combined SR %.4f vs A0 %.4f  (+%.4f = %.3f SE)  risk share TSMOM %.1f%%  gross share %.1f%%"
      %(S_opt,s1,S_opt-s1,(S_opt-s1)/SEsr,100*x2/(x1+x2),100*gross_share),flush=True)
print("gap to 3.966: from A0 %.3f ; from optimal combo %.3f"%(3.966-s1,3.966-S_opt),flush=True)

RES["A0"]=dict(d30_mean_g=float(gA0.mean()),d30_SR=s1,S0_mean_g=float(gA0_S0.mean()),S0_SR=ann(gA0_S0),
               turnover_mean=float(A0turn.mean()),netlong_mean=float(A0nl.mean()))
RES["gates"]=dict(GATE_A_pnl_maxabs_bps=GA,GATE_A2_carry_maxabs_bps=GA2,
                  corr_pnl_me_dev=float(np.corrcoef(pnl_me,pnl_dev)[0,1]))
RES["shas"]=SHAS; RES["window_n"]=NW; RES["env_whitelist"]=[]
json.dump(RES,open(OUT+"/STEP245.json","w"),indent=1)
np.savez_compressed(OUT+"/primary_series.npz",ts=ts_k,gT=gT,gA0=gA0,pnl=R["pnl"],carry=R["carry"],
                    cost=R["cost"],turn=R["turn"],netlong=R["netlong"],mkt=MKT[IDX])
print("wrote",OUT+"/STEP245.json",flush=True)
