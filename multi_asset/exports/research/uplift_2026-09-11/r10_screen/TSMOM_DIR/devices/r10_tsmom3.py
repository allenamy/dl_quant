"""R10 SCREEN TSMOM_DIR -- part 3: close GATE A under the device's ACTUAL membership rule
(MEMBERS_TOPN=829 rebuilds members from qvk, it does NOT use meta['members']); then the regime
split that decides whether the measured hedge is a 2022 artefact.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os, json, hashlib, time
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","SLEEVE","SEATNET","CDAMP",
    "KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","SEATF10","KTAIL","FUNDSCALE","TRADE_TOPN","RNSM",
    "FTPOS","LTRIM_TH","FTRIM_TH","REF_SKIP","PANEL","EXPORT_PANEL","EMA_STATE_JSON")
assert not [k for k in _F if k in os.environ], "E-0826-D env violation"
import numpy as np
from scipy.stats import spearmanr
OUT="/workspace/uplift_2026-09-11/r10_tsmom"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
UMASK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
CAP=1788120000; WARM=900; QVMIN=250000.0
m=np.load(META,allow_pickle=True); E_ts=m["E_ts"].astype(np.int64)
Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64); members=m["members"]; T,N=Y.shape
PW=np.load(PANEL,allow_pickle=True); pts=PW["ts"].astype(np.int64)
FNz=np.nan_to_num(PW["f_fund_now"].astype(np.float64),nan=0.0)
IVr=PW["f_fund_iv"].astype(np.float64); IVf=np.where(np.isfinite(IVr)&(IVr>0),IVr,8.0)
pw_row={int(t):j for j,t in enumerate(pts)}
CB=json.load(open(COSTB)); RATE=np.array([t["maker_share"]*t["maker_bps"]+(1-t["maker_share"])*t["taker_bps"] for t in CB["tiers"]])
A=np.load(A0P,allow_pickle=True); cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
RECd=np.asarray(A["d30_n2_c42_rec"],float); WMAT=np.asarray(A["d30_n2_c42_W"],float)
a_ts=RECd[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=WARM)&(a_ts<=CAP); ts_k=a_ts[keep]; NW=int(keep.sum())
pos={int(t):i for i,t in enumerate(E_ts)}; IDX=np.array([pos[int(t)] for t in ts_k])
JDX=np.array([pw_row[int(t)] for t in ts_k])
gA0=RECd[keep,ci["net_ex"]]/RECd[keep,ci["gross_total"]]
UM=np.load(UMASK,allow_pickle=True); uts=UM["ts"].astype(np.int64); UMAT=np.asarray(UM["mask"],bool)
umap={int(t):i for i,t in enumerate(uts)}
Yz=np.where(np.isfinite(Y),Y,0.0); FIN=np.isfinite(Y)

# ---- GATE A under the device's ACTUAL rule: MEMBERS_TOPN=829 => members = names with finite qvk
Qn=np.nan_to_num(QV,nan=-1.0); MEMB_DEV=(Qn>-0.5)
MEMB_META=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB_META[t,np.asarray(mm,dtype=int)]=True
print("mean names/anchor  meta-members %.1f | device MEMBERS_TOPN=829 rule %.1f"
      %(MEMB_META[IDX].sum(1).mean(),MEMB_DEV[IDX].sum(1).mean()),flush=True)
Wk=WMAT[keep]; pnl_dev=RECd[keep,ci["pnl"]]; car_dev=RECd[keep,ci["carry"]]
for lbl,BASE in (("meta-members",MEMB_META),("device TOPN829",MEMB_DEV)):
    MM=np.zeros((T,N),bool)
    for ii in range(NW):
        t=IDX[ii]; k=umap[int(ts_k[ii])]
        MM[t]=BASE[t]&UMAT[k]
    p=1e4*np.array([float((Wk[i][MM[IDX[i]]]*Yz[IDX[i]][MM[IDX[i]]]).sum()) for i in range(NW)])
    c=1e4*np.array([float((Wk[i][MM[IDX[i]]]*FNz[JDX[i]][MM[IDX[i]]]*(4.0/IVf[JDX[i]][MM[IDX[i]]])).sum()) for i in range(NW)])
    print("GATE A [%s] max|dpnl| %.3e  max|dcarry| %.3e  meanabs_dpnl %.3e"
          %(lbl,np.max(np.abs(p-pnl_dev)),np.max(np.abs(c-car_dev)),np.mean(np.abs(p-pnl_dev))),flush=True)

# ---- rebuild primary arm (meta-members eligibility = the surveyor's object, reproduced exactly)
QV4H=np.expm1(np.clip(QV,0,30))*48.0
ELIG=MEMB_META&FIN&(QV4H>=QVMIN)
TIER=np.full((T,N),2,np.int8); TIER[QV4H>=1e6]=1; TIER[QV4H>=5e6]=0
MKT=np.array([float(np.nanmean(np.where(ELIG[t],Y[t],np.nan))) if ELIG[t].any() else 0.0 for t in range(T)])
S=np.zeros((T,N)); C=np.zeros((T,N))
for j in range(1,43): S[j:]+=Yz[:T-j]; C[j:]+=FIN[:T-j]
SC=np.sign(S); VAL=C>=30
Wb=np.zeros((NW,N)); prev=np.zeros(N)
for ii in range(NW):
    t=IDX[ii]; e=ELIG[t]&VAL[t]&np.isfinite(SC[t]); n=int(e.sum())
    if n<20: Wb[ii]=prev; continue
    raw=np.zeros(N); raw[e]=SC[t,e]; aw=np.abs(raw).sum()
    if aw<=0: Wb[ii]=prev; continue
    w=raw/aw; Wb[ii]=w; prev=w
pnl=1e4*np.einsum("ij,ij->i",Wb,Yz[IDX])
car=1e4*np.array([float((Wb[i]*FNz[JDX[i]]*(4.0/IVf[JDX[i]])).sum()) for i in range(NW)])
dW=np.abs(np.diff(Wb,axis=0,prepend=np.zeros((1,N))))
cst=np.array([float((dW[i]*RATE[TIER[IDX[i]]]).sum()) for i in range(NW)])
gT=pnl-car-cst; turn=dW.sum(1); netlong=Wb.sum(1)/np.maximum(np.abs(Wb).sum(1),1e-12)

DAY=(ts_k//86400).astype(np.int64); UD=np.unique(DAY); DIDX=[np.where(DAY==d)[0] for d in UD]
def ann(x):
    s=float(np.std(x,ddof=1)); return float(np.mean(x)/s*np.sqrt(2190)) if s>0 else float("nan")
def mdd(g):
    c=np.cumsum(g); return float(np.max(np.maximum.accumulate(c)-c))
YR=np.array([time.gmtime(int(t)).tm_year for t in ts_k])

# ---- tail concentration + the worst day, anchor by anchor
tot=float(np.abs(gT).sum()); top5=float(np.sort(np.abs(gT))[-5:].sum()/tot)
top1pct=float(np.sort(np.abs(gT))[-int(0.01*NW):].sum()/tot)
dd=np.array([gT[ix].sum() for ix in DIDX]); wi=int(np.argmin(dd))
wday=int(UD[wi]); wrows=DIDX[wi]
print("\nTail: top-5 anchors = %.1f%% of sum|g|, top-1%% = %.1f%%"%(100*top5,100*top1pct),flush=True)
print("WORST UTC DAY %s  TSMOM %.1f bps  A0 %.1f bps"%(time.strftime("%Y-%m-%d",time.gmtime(wday*86400)),dd[wi],gA0[wrows].sum()),flush=True)
for r in wrows:
    print("   %s  TSMOM %+9.2f (pnl %+9.2f carry %+7.3f cost %6.3f) netlong %+.3f | A0 %+8.2f | mkt %+7.2f bps"
          %(time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(int(ts_k[r]))),gT[r],pnl[r],car[r],cst[r],netlong[r],gA0[r],1e4*MKT[IDX[r]]),flush=True)
worst10=np.argsort(dd)[:10]
print("\n10 worst TSMOM UTC days (TSMOM | A0 same day):",flush=True)
for i in worst10:
    print("   %s  TSMOM %+9.1f   A0 %+8.1f"%(time.strftime("%Y-%m-%d",time.gmtime(int(UD[i])*86400)),dd[i],gA0[DIDX[i]].sum()),flush=True)
ddA=np.array([gA0[ix].sum() for ix in DIDX]); wA=np.argsort(ddA)[:10]
print("\n10 worst A0 UTC days (A0 | TSMOM same day):",flush=True)
for i in wA:
    print("   %s  A0 %+8.1f   TSMOM %+9.1f"%(time.strftime("%Y-%m-%d",time.gmtime(int(UD[i])*86400)),ddA[i],dd[i]),flush=True)

# ---- REGIME SPLIT: does the hedge survive outside 2022, and in the live regime?
SPANS={"FULL_postwarm":np.ones(NW,bool),
       "ex2022":YR>=2023,
       "2024on":YR>=2024,
       "FROZEN_2025-03-01..2026-08-10":(ts_k>=1740787200)&(ts_k<=1786737600),
       "2026":YR>=2026}
REG={}
print("\nREGIME SPLIT (all net of the fitted PWR_G230k cost and of carry):",flush=True)
print("%-32s %6s %9s %8s %9s %8s %9s %9s %9s"%("span","n","TSMOM g","SR","A0 g","A0 SR","rho","rho|A0Q0","TSMOM|A0Q0"),flush=True)
for nm,msk in SPANS.items():
    n=int(msk.sum())
    if n<300: continue
    t_=gT[msk]; a_=gA0[msk]
    q=np.quantile(a_,0.20); lo=a_<=q
    REG[nm]=dict(n=n,TSMOM_g=float(t_.mean()),TSMOM_SR=ann(t_),A0_g=float(a_.mean()),A0_SR=ann(a_),
                 rho=float(np.corrcoef(t_,a_)[0,1]),rho_A0Q0=float(np.corrcoef(t_[lo],a_[lo])[0,1]),
                 TSMOM_mean_in_A0Q0=float(t_[lo].mean()),A0_mean_in_A0Q0=float(a_[lo].mean()),
                 TSMOM_sd=float(t_.std(ddof=1)),A0_sd=float(a_.std(ddof=1)),
                 TSMOM_maxDD=mdd(t_),A0_maxDD=mdd(a_))
    print("%-32s %6d %+9.4f %+8.3f %+9.4f %+8.3f %+9.4f %+9.4f %+9.3f"
          %(nm,n,t_.mean(),ann(t_),a_.mean(),ann(a_),REG[nm]["rho"],REG[nm]["rho_A0Q0"],REG[nm]["TSMOM_mean_in_A0Q0"]),flush=True)

print("\nPER YEAR (TSMOM net g | gross price g | SR | A0 g):",flush=True)
PY={}
for y in sorted(set(YR.tolist())):
    k=YR==y
    PY[int(y)]=dict(n=int(k.sum()),net_g=float(gT[k].mean()),price_g=float(pnl[k].mean()),
                    SR=ann(gT[k]),A0_g=float(gA0[k].mean()),netlong=float(netlong[k].mean()))
    print("   %d n=%4d net %+8.4f price %+8.4f SR %+6.3f | A0 %+7.4f | netlong %+.3f"
          %(y,k.sum(),gT[k].mean(),pnl[k].mean(),ann(gT[k]),gA0[k].mean(),netlong[k].mean()),flush=True)

# NOTE: the regime-conditional COMBINATION arithmetic lives in r10_tsmom4.py (part 4),
# which reads primary_series.npz written by part 2.  Kept out of here to avoid duplicating it.

json.dump(dict(regime=REG,per_year=PY,
               tail=dict(top5_anchor_share=top5,top1pct_anchor_share=top1pct),
               worst_day=dict(day=time.strftime("%Y-%m-%d",time.gmtime(wday*86400)),
                              TSMOM_bps=float(dd[wi]),A0_bps=float(gA0[wrows].sum())),
               worst10_TSMOM_days=[[time.strftime("%Y-%m-%d",time.gmtime(int(UD[i])*86400)),float(dd[i]),float(gA0[DIDX[i]].sum())] for i in worst10],
               worst10_A0_days=[[time.strftime("%Y-%m-%d",time.gmtime(int(UD[i])*86400)),float(ddA[i]),float(dd[i])] for i in wA],
               env_whitelist=[]),
          open(OUT+"/STEP_REGIME.json","w"),indent=1)
print("\nwrote",OUT+"/STEP_REGIME.json",flush=True)
