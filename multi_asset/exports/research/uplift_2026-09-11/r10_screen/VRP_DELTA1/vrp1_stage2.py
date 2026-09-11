"""VRP_DELTA1 SCREEN stage2: nulls, Amihud-identity test, downside, combined arithmetic.
ENV WHITELIST (E-0826-D) = EMPTY SET.  env -i /workspace/venv/bin/python vrp1_stage2.py"""
import os, json, hashlib, time
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
_bad=[k for k in _F if k in os.environ]; assert not _bad, "E-0826-D env violation: %s"%_bad
import numpy as np
from scipy.stats import rankdata, spearmanr
t0=time.time()
OUT="/workspace/uplift_2026-09-11/r10_screen/VRP_DELTA1"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<22), b''): h.update(c)
    return h.hexdigest()
SHAS={"meta_newprod_v4":sha(META),"A0_series":sha(A0P),"costb_PWR_G230k":sha(COSTB),
      "panel_v2ext":sha(PANEL),"self_stage2":sha(os.path.abspath(__file__))}
for k,v in SHAS.items(): print("sha256 %-18s %s"%(k,v))
CAP=1788120000; WARM=900; ANN=np.sqrt(2190.0)
def ann(x):
    s=np.std(x,ddof=1); return float(np.mean(x)/s*ANN) if s>0 else float("nan")

m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; T,N=Y.shape
a=np.load(A0P,allow_pickle=True); cols=[str(c) for c in a["cols"]]; ci={c:i for i,c in enumerate(cols)}
rec=a["d30_n2_c42_rec"]; a_ts=rec[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=WARM)&(a_ts<=CAP); a_ts_k=a_ts[keep]
gA0=rec[keep,ci["net_ex"]]/rec[keep,ci["gross_total"]]
pos={int(t):i for i,t in enumerate(E_ts)}
IDX=np.array([pos[int(t)] for t in a_ts_k]); NW=len(IDX)
MEMB=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
QV4H=np.expm1(np.clip(QV,0,30))*48.0
ELIG=MEMB&np.isfinite(Y)&(QV4H>=2.5e5)
TIER=np.full((T,N),2,np.int8); TIER[QV4H>=1e6]=1; TIER[QV4H>=5e6]=0
CB=json.load(open(COSTB)); RATES=np.array(CB["blended_bps_per_unit_turnover"],float); RATE=RATES[TIER]
Yz=np.where(np.isfinite(Y),Y,0.0); FIN=np.isfinite(Y)
def trail_std(k):
    S1=np.zeros((T,N)); S2=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1):
        S1[j:]+=Yz[:T-j]; S2[j:]+=Yz[:T-j]**2; C[j:]+=FIN[:T-j]
    with np.errstate(invalid='ignore',divide='ignore'):
        mu=S1/np.maximum(C,1); v=S2/np.maximum(C,1)-mu**2
    return np.sqrt(np.maximum(v,0)),C
def build_W(score,valid,idx=None):
    ii_list=IDX if idx is None else idx
    W=np.zeros((len(ii_list),N))
    for k,t in enumerate(ii_list):
        e=ELIG[t]&valid[t]&np.isfinite(score[t]); n=int(e.sum())
        if n<20: continue
        r=rankdata(score[t,e])/(n+1.0)-0.5; w=r-r.mean(); s=np.abs(w).sum()
        if s>0: W[k,e]=w/s
    return W
def wprev_of(score,valid):
    t=IDX[0]-1; e=ELIG[t]&valid[t]&np.isfinite(score[t]); w=np.zeros(N)
    if e.sum()>=20:
        r=rankdata(score[t,e])/(int(e.sum())+1.0)-0.5; ww=r-r.mean(); s=np.abs(ww).sum()
        if s>0: w[e]=ww/s
    return w
def evaluate(W,w_prev):
    gg=np.zeros(NW); tn=np.zeros(NW); cst=np.zeros(NW); prev=w_prev
    for ii in range(NW):
        t=IDX[ii]; w=W[ii]
        gg[ii]=1e4*float(np.sum(w*Yz[t])); d=np.abs(w-prev)
        tn[ii]=d.sum(); cst[ii]=float(np.sum(d*RATE[t])); prev=w
    return gg,tn,cst
def run(score,valid):
    W=build_W(score,valid); gg,tn,cst=evaluate(W,wprev_of(score,valid)); return W,gg,tn,cst,gg-cst

L=42; SD,CD=trail_std(L); SC=-SD; VAL=CD>=30
W,gg,tn,cst,net=run(SC,VAL)
print("\nREAL  gross %+0.4f turn %.5f cost %.4f NET %+0.4f SR_net %+0.4f"%(gg.mean(),tn.mean(),cst.mean(),net.mean(),ann(net)))

# ---- block bootstrap on the candidate's own numbers
DAY=(a_ts_k//86400).astype(np.int64); ud,dinv=np.unique(DAY,return_inverse=True)
DG=[np.where(dinv==j)[0] for j in range(len(ud))]
BOOT=[]
for k in range(2000):
    rng=np.random.default_rng([20260905,int(k)])
    BOOT.append(np.concatenate([DG[j] for j in rng.integers(0,len(DG),len(DG))]))
def bci(fn):
    v=np.array([fn(b) for b in BOOT]); v=v[np.isfinite(v)]
    return float(np.percentile(v,2.5)),float(np.percentile(v,97.5))
net_ci=bci(lambda b: net[b].mean()); gg_ci=bci(lambda b: gg[b].mean())
sr_ci =bci(lambda b: net[b].mean()/net[b].std(ddof=1)*ANN)
print("NET mean g CI95 [%+0.4f,%+0.4f]   gross CI95 [%+0.4f,%+0.4f]   SR_net CI95 [%+0.4f,%+0.4f]"%(
    net_ci+gg_ci+sr_ci))
SE_SR=float(np.sqrt(2190.0/NW))
print("SE(annualised Sharpe)=sqrt(2190/%d)=%.4f -> parametric CI95 [%+0.4f,%+0.4f]"%(
    NW,SE_SR,ann(net)-1.96*SE_SR,ann(net)+1.96*SE_SR))

# ---- STEP 3b: turnover-matched nulls (families of r3_attack_b9646/null.py, applied in THIS device)
NULLS={}
for k in (101,503,1009):
    Q=np.full_like(SC,np.nan); V=np.zeros_like(VAL)
    Q[k:]=SC[:-k]; V[k:]=VAL[:-k]
    _,g2,t2,c2,n2=run(Q,V); NULLS["SHIFT%d"%k]=(g2,t2,n2)
for d in (1,2,3):
    rng=np.random.default_rng([4242,int(d)]); p=rng.permutation(N)
    Q=SC[:,p]; V=VAL[:,p]
    _,g2,t2,c2,n2=run(Q,V); NULLS["RELAB%d"%d]=(g2,t2,n2)
print("\n== turnover-matched nulls (SHIFT101/503/1009, RELAB1-3) ==")
print("%-10s %8s %8s %9s %8s"%("arm","grossG","turn","NETg","SR_net"))
print("%-10s %+8.4f %8.5f %+9.4f %+8.4f"%("REAL",gg.mean(),tn.mean(),net.mean(),ann(net)))
NR={}
for k,(g2,t2,n2) in NULLS.items():
    NR[k]=dict(gross=float(g2.mean()),turn=float(t2.mean()),net=float(n2.mean()),sr=ann(n2))
    print("%-10s %+8.4f %8.5f %+9.4f %+8.4f"%(k,g2.mean(),t2.mean(),n2.mean(),ann(n2)))
nv=np.array([NR[k]["net"] for k in NR])
print("null NET mean %+0.4f sd %0.4f ; REAL z vs nulls = %+0.2f ; REAL exceeds %d/%d nulls"%(
    nv.mean(),nv.std(ddof=1),(net.mean()-nv.mean())/nv.std(ddof=1),int((net.mean()>nv).sum()),len(nv)))

# ---- STEP 2b: is VRP_DELTA1 the Amihud sleeve wearing a different name?
P=np.load(PANEL,allow_pickle=True); pts=P["ts"].astype(np.int64)
assert np.array_equal(P["symbols"],a["symbols"])
OFF=int(np.searchsorted(E_ts,pts[0])); assert np.array_equal(E_ts[OFF:OFF+len(pts)],pts)
AMI=np.full((T,N),np.nan); AMI[OFF:OFF+len(pts)]=np.asarray(P["f_amihud_24h"],float)
AVAL=np.isfinite(AMI)
# rejected-sleeve sign: XIB_LAG50 = 0.5*rank(f_fund_ema)+0.5*rank(amihud) -> LONG illiquid
_,gA,tA,cA,nA=run(AMI,AVAL)
_,gAm,tAm,cAm,nAm=run(-AMI,AVAL)
# size / liquidity tilt proxy
LQ=np.where(np.isfinite(QV4H),np.log(np.maximum(QV4H,1.0)),np.nan)
_,gL,tL,cL,nL=run(LQ,np.isfinite(LQ))
print("\n== STEP 2b AMIHUD / SIZE IDENTITY TEST ==")
for nm,(g2,n2) in [("AMI_long_illiquid",(gA,nA)),("AMI_long_liquid",(gAm,nAm)),("SIZE_long_liquid",(gL,nL))]:
    print("%-18s gross %+0.4f NET %+0.4f SR_net %+0.4f  rho(NET,VRPnet)=%+0.4f  rho(gross,VRPgross)=%+0.4f"%(
        nm,g2.mean(),n2.mean(),ann(n2),np.corrcoef(n2,net)[0,1],np.corrcoef(g2,gg)[0,1]))
rho_ami=float(np.corrcoef(nA,net)[0,1]); rho_amiC=bci(lambda b: np.corrcoef(nA[b],net[b])[0,1])
rho_sz =float(np.corrcoef(nL,net)[0,1])
print("rho(VRP_net, AMIHUD_sleeve_net) = %+0.4f CI95 [%+0.4f,%+0.4f]"%(rho_ami,rho_amiC[0],rho_amiC[1]))
# cross-sectional score identity per anchor
xs_ami=[];xs_sz=[]
for ii in range(0,NW,7):
    t=IDX[ii]; e=ELIG[t]&VAL[t]&np.isfinite(SC[t])
    e2=e&np.isfinite(AMI[t])
    if e2.sum()>=30: xs_ami.append(spearmanr(SC[t,e2],AMI[t,e2]).statistic)
    e3=e&np.isfinite(LQ[t])
    if e3.sum()>=30: xs_sz.append(spearmanr(SC[t,e3],LQ[t,e3]).statistic)
xs_ami=np.array(xs_ami); xs_sz=np.array(xs_sz)
print("per-anchor xs Spearman( -vol42 , amihud_24h ) mean %+0.4f  median %+0.4f  n=%d"%(xs_ami.mean(),np.median(xs_ami),len(xs_ami)))
print("per-anchor xs Spearman( -vol42 , log qv4h  ) mean %+0.4f  median %+0.4f  n=%d"%(xs_sz.mean(),np.median(xs_sz),len(xs_sz)))
# rho of the AMIHUD sleeve to A0, unconditional and in A0's losing cells (reproduce the known reject)
q20=float(np.quantile(gA0,0.20)); lose=gA0<=q20
print("AMIHUD sleeve rho to A0: uncond %+0.4f ; in A0 bottom quintile %+0.4f   [known reject: +0.343/+0.438]"%(
    np.corrcoef(nA,gA0)[0,1], np.corrcoef(nA[lose],gA0[lose])[0,1]))

# ---- lookback robustness
print("\n== lookback robustness ==")
ROB={}
for LL in (12,42,84,168):
    sd,cd=trail_std(LL); _,g2,t2,c2,n2=run(-sd,cd>=max(8,LL*3//4 if LL<84 else 60))
    ROB[LL]=dict(gross=float(g2.mean()),turn=float(t2.mean()),net=float(n2.mean()),sr=ann(n2),
                 rho_A0=float(np.corrcoef(n2,gA0)[0,1]))
    print("L=%3d gross %+0.4f turn %.5f NET %+0.4f SR_net %+0.4f rho_A0 %+0.4f"%(
        LL,g2.mean(),t2.mean(),n2.mean(),ann(n2),ROB[LL]["rho_A0"]))

# ---- STEP 4 downside
MKT=np.array([1e4*np.nanmean(np.where(ELIG[t],Y[t],np.nan)) if ELIG[t].any() else 0.0 for t in IDX])
def beta(x,y): return float(np.polyfit(y,x,1)[0])
def dd(x):
    c=np.cumsum(x); return float((np.maximum.accumulate(c)-c).max())
def dayagg(x):
    return np.array([x[dinv==j].sum() for j in range(len(ud))])
dn=dayagg(net); dA=dayagg(gA0)
def conc(x):
    s=np.sort(x); n=len(x)
    return dict(top1pct_share_of_total=float(s[-max(1,n//100):].sum()/x.sum()) if x.sum()!=0 else float('nan'),
                worst1pct_sum=float(s[:max(1,n//100)].sum()),
                frac_positive=float((x>0).mean()))
print("\n== STEP 4 DOWNSIDE ==")
print("net beta to market           VRP %+0.5f   A0 %+0.5f"%(beta(net,MKT),beta(gA0,MKT)))
print("net beta to A0               VRP %+0.5f"%beta(net,gA0))
print("maxDD (bps gross, cum sum)   VRP %8.1f   A0 %8.1f"%(dd(net),dd(gA0)))
print("worst UTC day (bps gross)    VRP %8.2f   A0 %8.2f"%(dn.min(),dA.min()))
print("worst anchor (bps gross)     VRP %8.2f   A0 %8.2f"%(net.min(),gA0.min()))
print("frac positive anchors        VRP %8.4f   A0 %8.4f"%((net>0).mean(),(gA0>0).mean()))
cv=conc(net); ca=conc(gA0)
print("top1%% anchors share of total VRP %8.3f   A0 %8.3f"%(cv["top1pct_share_of_total"],ca["top1pct_share_of_total"]))
print("worst 1%% anchors sum        VRP %8.1f   A0 %8.1f"%(cv["worst1pct_sum"],ca["worst1pct_sum"]))

# ---- STEP 5 honest arithmetic
s1=ann(gA0); s2=ann(net); rho=float(np.corrcoef(net,gA0)[0,1])
BRIEF_S1=1.2912
def comb_opt(s1,s2,r): return float(np.sqrt(max((s1*s1+s2*s2-2*r*s1*s2)/(1-r*r),0.0)))
print("\n== STEP 5 ARITHMETIC ==")
print("A0 SR(this archive, dyn_s42 d30) %+0.4f ; A0 SR(brief) %+0.4f ; cand SR_net %+0.4f ; rho %+0.4f"%(s1,s2,rho,) if False else
      "A0 SR(this archive)=%+0.4f  A0 SR(brief)=%+0.4f  cand SR_net=%+0.4f  rho=%+0.4f"%(s1,BRIEF_S1,s2,rho))
print("MV-optimal combined SR  (archive A0) %+0.4f   (brief A0) %+0.4f"%(comb_opt(s1,s2,rho),comb_opt(BRIEF_S1,s2,rho)))
print("gross-zero-cost ceiling: cand SR_gross %+0.4f -> MV-optimal with brief A0 %+0.4f"%(ann(gg),comb_opt(BRIEF_S1,ann(gg),float(np.corrcoef(gg,gA0)[0,1]))))
best=None
LAM={}
for lam in [0.0,0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50]:
    gc=(1-lam)*gA0+lam*net; s=ann(gc); LAM[lam]=s
    if best is None or s>best[1]: best=(lam,s)
    print("  lam=%.2f of gross to VRP -> combined SR %+0.4f  (dSR %+0.4f)"%(lam,s,s-s1))
lam_b=best[0]
dsr_ci=bci(lambda b: ann((1-lam_b)*gA0[b]+lam_b*net[b])-ann(gA0[b]))
print("best lam=%.2f SR %+0.4f ; dSR vs A0 = %+0.4f CI95 [%+0.4f,%+0.4f]"%(lam_b,best[1],best[1]-s1,dsr_ci[0],dsr_ci[1]))
TARGET=3.966
print("target %.3f ; shortfall from archive-A0 combined = %.4f SR = %.2f SE"%(TARGET,TARGET-comb_opt(s1,s2,rho),(TARGET-comb_opt(s1,s2,rho))/SE_SR))
need=float(np.sqrt(max(TARGET**2-BRIEF_S1**2,0)))
print("an uncorrelated source would still need standalone SR %.4f to reach %.3f alongside brief A0 ; this one delivers %.4f (%.1f%%)"%(
    need,TARGET,s2,100*s2/need))

json.dump(dict(
 shas=SHAS, env_whitelist=[], n=NW, window=[int(a_ts_k[0]),int(a_ts_k[-1])],
 real=dict(gross_g=float(gg.mean()),gross_SR=ann(gg),turnover=float(tn.mean()),
           cost_bps=float(cst.mean()),cost_rate_bps_per_unit=float(cst.mean()/tn.mean()),
           net_g=float(net.mean()),net_g_CI95=list(net_ci),net_SR=ann(net),net_SR_CI95_block=list(sr_ci),
           net_SR_CI95_param=[ann(net)-1.96*SE_SR,ann(net)+1.96*SE_SR],
           cost_survival_pct=float(100*net.mean()/gg.mean())),
 A0=dict(mean_g=float(gA0.mean()),SR=s1,brief_SR=BRIEF_S1),
 rho=dict(uncond=rho,bottom_quintile=float(np.corrcoef(net[lose],gA0[lose])[0,1])),
 nulls=NR, null_summary=dict(mean=float(nv.mean()),sd=float(nv.std(ddof=1)),real=float(net.mean())),
 amihud=dict(rho_VRPnet_AMIsleeve=rho_ami,CI95=list(rho_amiC),
             rho_VRPnet_SIZEsleeve=rho_sz,
             xs_spearman_score_vs_amihud=float(xs_ami.mean()),
             xs_spearman_score_vs_logqv=float(xs_sz.mean()),
             AMI_sleeve_rho_A0_uncond=float(np.corrcoef(nA,gA0)[0,1]),
             AMI_sleeve_rho_A0_lose=float(np.corrcoef(nA[lose],gA0[lose])[0,1]),
             AMI_sleeve_net_g=float(nA.mean()),AMI_sleeve_SR=ann(nA)),
 lookback=ROB,
 downside=dict(beta_mkt=beta(net,MKT),beta_mkt_A0=beta(gA0,MKT),beta_A0=beta(net,gA0),
               maxDD_bps=dd(net),maxDD_bps_A0=dd(gA0),worst_day_bps=float(dn.min()),
               worst_day_bps_A0=float(dA.min()),worst_anchor=float(net.min()),
               worst_anchor_A0=float(gA0.min()),frac_pos=float((net>0).mean()),conc=cv,conc_A0=ca),
 arithmetic=dict(comb_opt_archiveA0=comb_opt(s1,s2,rho),comb_opt_briefA0=comb_opt(BRIEF_S1,s2,rho),
                 comb_opt_zerocost_briefA0=comb_opt(BRIEF_S1,ann(gg),float(np.corrcoef(gg,gA0)[0,1])),
                 lam_grid={str(k):v for k,v in LAM.items()},best_lam=lam_b,best_SR=best[1],
                 dSR_CI95=list(dsr_ci),target=TARGET,required_standalone_SR=need,SE_SR=SE_SR),
 ), open(OUT+"/RECEIPT_VRP_DELTA1.json","w"), indent=1)
np.savez_compressed(OUT+"/series_VRP_DELTA1.npz",ts=a_ts_k,gA0=gA0,gross=gg,net=net,turnover=tn,cost=cst,
                    ami_net=nA,size_net=nL,mkt=MKT)
print("\nstage2 %.0fs -> RECEIPT_VRP_DELTA1.json"%(time.time()-t0))
