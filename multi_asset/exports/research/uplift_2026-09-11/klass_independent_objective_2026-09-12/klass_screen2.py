"""KLASS SURVEY -- independence SCREEN. NOT a judge verdict. NOT a candidate. NO deployment claim.
ENV WHITELIST (E-0826-D) = EMPTY SET.

Question this answers: for structurally-different standalone objectives buildable on the PINNED v4
accounting matrix, what is the MEASURED rho of their per-anchor return series to A0's g series --
unconditionally AND inside the cells where A0 loses (the docket's corrected screen).

Pins: meta_newprod_v4.npz (RAW accounting y4) ; dev_v4 A0_dyn_s42 d30_n2_c42_rec.
Window: drop first 900 device anchors (E-0911-A) ; cap 2026-08-30 20:00Z (E-0911-D) -> n=9138.
Cost: reported at TWO rates that bracket the measured range -- A0's own 3.78 bps/unit turnover
(this archive, fee_steady) and 13.2 bps/unit (the rate r5 measured for a NEW illiquid-tilted
signal under costb_PWR_G230k). Carry (funding) is EXCLUDED from every number: y4 is price only.
"""
import os, json, hashlib
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], "E-0826-D env violation"
import numpy as np
from scipy.stats import rankdata, spearmanr

META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
CAP=1788120000
m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; T,N=Y.shape
a=np.load(A0P,allow_pickle=True); cols=list(a["cols"]); ci={c:i for i,c in enumerate(cols)}
rec=a["d30_n2_c42_rec"]; a_ts=rec[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=900)&(a_ts<=CAP)
a_ts_k=a_ts[keep]; gA0=rec[keep,ci["net_ex"]]/rec[keep,ci["gross_total"]]
pos={int(t):i for i,t in enumerate(E_ts)}
IDX=np.array([pos[int(t)] for t in a_ts_k]); NW=len(IDX)
print(f"window n={NW}  A0 meang={gA0.mean():+.4f} SR={gA0.mean()/gA0.std(ddof=1)*np.sqrt(2190):+.4f}")

# ---------- eligibility: member AND finite y4 AND live liquidity gate (shadow_loop_v3 L473-474)
MEMB=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
QV4H=np.expm1(np.clip(QV,0,30))*48.0
ELIG=MEMB & np.isfinite(Y) & (QV4H>=2.5e5)
print("mean eligible names per anchor (window):", round(float(ELIG[IDX].sum(1).mean()),1))

Yz=np.where(np.isfinite(Y),Y,0.0)                 # for trailing sums only
FIN=np.isfinite(Y)

def xsdemean(A,M):
    out=np.where(M,A,np.nan)
    mu=np.nanmean(out,axis=1,keepdims=True)
    return np.where(M,out-mu,np.nan)

def trail_sum(k):
    """sum of y4 over anchors t-1 ... t-k  (strictly before E_t). NaN-as-0, count tracked."""
    S=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1):
        S[j:]+=Yz[:T-j]; C[j:]+=FIN[:T-j]
    return S,C

def trail_std(k):
    S1=np.zeros((T,N)); S2=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1):
        S1[j:]+=Yz[:T-j]; S2[j:]+=Yz[:T-j]**2; C[j:]+=FIN[:T-j]
    with np.errstate(invalid='ignore',divide='ignore'):
        mu=S1/np.maximum(C,1); v=S2/np.maximum(C,1)-mu**2
    return np.sqrt(np.maximum(v,0)),C

MKT=np.array([np.nanmean(np.where(ELIG[t],Y[t],np.nan)) if ELIG[t].any() else 0.0 for t in range(T)])

# ---------- objective definitions (scores at anchor t use ONLY rows <= t-1)
S1,C1=trail_sum(1); S6,C6=trail_sum(6); S42,C42=trail_sum(42); SD42,CD42=trail_std(42)
MK1=np.zeros(T); MK1[1:]=MKT[:T-1]
MK6=np.zeros(T); 
for j in range(1,7): MK6[j:]+=MKT[:T-j]
MK42=np.zeros(T)
for j in range(1,43): MK42[j:]+=MKT[:T-j]

OBJ={}
OBJ["REV1_xs"]      = (-(S1-MK1[:,None]),            C1>=1,  "xs reversal, 1 anchor (4h) -- statistical liquidity provision")
OBJ["REV6_xs"]      = (-(S6-MK6[:,None]),            C6>=5,  "xs reversal, 6 anchors (24h) -- CONTROL = the retired rev24 leg")
OBJ["MOM42_xs"]     = ( (S42-MK42[:,None]),          C42>=30,"xs price momentum 7d -- CONTROL, known panel column")
OBJ["BAV_xs"]       = (-SD42,                        CD42>=30,"bet-against-vol: long low realised vol -- delta-one VRP proxy")
OBJ["TSMOM_net"]    = ( np.sign(S42),                C42>=30,"per-name time-series momentum, NET exposure allowed -- directional book")

def build_weights(score,valid,net_book=False):
    W=np.zeros((T,N))
    for ii in range(NW):
        t=IDX[ii]
        e=ELIG[t]&valid[t]&np.isfinite(score[t])
        n=int(e.sum())
        if n<20: continue
        s=score[t,e]
        if net_book:
            w=s.astype(float)                       # already +-1
        else:
            r=rankdata(s)/(n+1.0)-0.5
            w=r-r.mean()
        aw=np.abs(w).sum()
        if aw<=0: continue
        W[t,e]=w/aw
    return W

def evaluate(W):
    g_gross=np.zeros(NW); tno=np.zeros(NW)
    prev=None
    for ii in range(NW):
        t=IDX[ii]
        w=W[t]
        g_gross[ii]=1e4*float(np.nansum(w*np.where(np.isfinite(Y[t]),Y[t],0.0)))
        if prev is None: tno[ii]=np.abs(w).sum()
        else: tno[ii]=np.abs(w-prev).sum()
        prev=w
    return g_gross,tno

def ann(x): 
    s=x.std(ddof=1)
    return float(x.mean()/s*np.sqrt(2190)) if s>0 else float('nan')

q20=np.quantile(gA0,0.20); lose=gA0<=q20
res={}
print("\n%-12s %7s %7s %8s %8s %8s %8s %8s %8s" % ("obj","grossG","SR_gr","turn","SR@3.78","SR@13.2","rho","rhoSpear","rho|A0 bottom20%"))
for name,(sc,val,desc) in OBJ.items():
    W=build_weights(sc,val,net_book=name.endswith("_net"))
    gg,tn=evaluate(W)
    net_lo=gg-3.7766*tn; net_hi=gg-13.2*tn
    rho=float(np.corrcoef(gg,gA0)[0,1]); rs=float(spearmanr(gg,gA0).statistic)
    rlo=float(np.corrcoef(gg[lose],gA0[lose])[0,1])
    res[name]=dict(desc=desc,gross_g=float(gg.mean()),SR_gross=ann(gg),turnover=float(tn.mean()),
                   SR_net_378=ann(net_lo),SR_net_132=ann(net_hi),net_g_378=float(net_lo.mean()),
                   net_g_132=float(net_hi.mean()),rho_A0=rho,spearman_A0=rs,rho_A0_bottom20=rlo)
    print("%-12s %+7.4f %+7.3f %8.4f %+8.3f %+8.3f %+8.4f %+8.4f %+8.4f" %
          (name,gg.mean(),ann(gg),tn.mean(),ann(net_lo),ann(net_hi),rho,rs,rlo))

json.dump(dict(window_n=NW,A0_mean_g=float(gA0.mean()),A0_SR=ann(gA0),
               A0_bottom20_threshold=float(q20),objectives=res,
               env_whitelist=[], note="SCREEN ONLY -- crude rank book, carry excluded, not the w10 judge"),
          open("/workspace/uplift_2026-09-11/KLASS_SCREEN.json","w"),indent=1)
print("\nwrote /workspace/uplift_2026-09-11/KLASS_SCREEN.json")

# ---------- leak guard: offset spectrum of REV1 score vs y4 at k=-3..+3
sc,val,_=OBJ["REV1_xs"]
print("\nOFFSET SPECTRUM (xs rank IC of REV1 score vs y4 shifted by k); k=0 must be the tradable read")
for k in range(-3,4):
    ics=[]
    for ii in range(0,NW,3):
        t=IDX[ii]; tt=t+k
        if tt<0 or tt>=T: continue
        e=ELIG[t]&val[t]&np.isfinite(sc[t])&np.isfinite(Y[tt])
        if e.sum()<20: continue
        ics.append(spearmanr(sc[t,e],Y[tt,e]).statistic)
    ics=np.array(ics); ics=ics[np.isfinite(ics)]
    print(f"  k={k:+d}  IC={ics.mean():+.5f}  t={ics.mean()/ics.std(ddof=1)*np.sqrt(len(ics)):+.2f}  n={len(ics)}")
