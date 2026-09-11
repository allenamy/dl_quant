"""VRP_DELTA1 SCREEN -- r10, branch research/book-uplift-2026-09-11.
ENV WHITELIST (E-0826-D) = EMPTY SET.  Run as: env -i /workspace/venv/bin/python vrp1_screen.py

Candidate: delta-one shadow of the volatility risk premium = bet-against-vol.
  score_t,i = -( trailing realised vol of y4 over anchors t-1..t-L ), L=42 (7d)
  weights   = cross-sectional centred rank over eligible names, normalised sum|w| = 1
Causality: score at anchor t reads ONLY rows <= t-1 of the RAW accounting matrix. y4[t] is the
FORWARD 4h return from E_ts[t] (alignment re-verified here by an offset spectrum).

PINS (sha recomputed in this run):
  meta_newprod_v4.npz  RAW accounting (E-0908-B compliant, no clipped compounding)
  dev_v4 A0_dyn_s42 d30_n2_c42_rec / _W
  costb_PWR_G230k.json  tier rates, G=$230k
Window: drop first 900 device anchors (E-0911-A), cap ts<=2026-08-30T20Z (E-0911-D) -> expect n=9138.
Statistic: g = net_ex/gross_total, bps per 4h anchor per unit gross.
"""
import os, sys, json, hashlib, time
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
_bad=[k for k in _F if k in os.environ]
assert not _bad, "E-0826-D env violation: %s"%_bad
import numpy as np
from scipy.stats import rankdata, spearmanr

t0=time.time()
OUT="/workspace/uplift_2026-09-11/r10_screen/VRP_DELTA1"
os.makedirs(OUT,exist_ok=True)
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def sha(p): 
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<22), b''): h.update(c)
    return h.hexdigest()
SHAS={k:sha(v) for k,v in [("meta_newprod_v4",META),("A0_series",A0P),("costb_PWR_G230k",COSTB)]}
SHAS["self"]=sha(os.path.abspath(__file__))
for k,v in SHAS.items(): print("sha256 %-20s %s"%(k,v))

CAP=1788120000; WARM=900
m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; T,N=Y.shape
a=np.load(A0P,allow_pickle=True); cols=[str(c) for c in a["cols"]]; ci={c:i for i,c in enumerate(cols)}
SYM=a["symbols"]
rec=a["d30_n2_c42_rec"]; a_ts=rec[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=WARM)&(a_ts<=CAP)
a_ts_k=a_ts[keep]
gA0 =rec[keep,ci["net_ex"]]/rec[keep,ci["gross_total"]]
pA0 =rec[keep,ci["pnl_ex"]]/rec[keep,ci["gross_total"]]
cA0 =rec[keep,ci["cost_ex"]]/rec[keep,ci["gross_total"]]
tnA0=rec[keep,ci["turnover"]]/rec[keep,ci["gross_total"]]
WA0 =a["d30_n2_c42_W"][keep].astype(np.float64)
pos={int(t):i for i,t in enumerate(E_ts)}
IDX=np.array([pos[int(t)] for t in a_ts_k]); NW=len(IDX)
assert np.array_equal(IDX, np.arange(IDX[0],IDX[0]+NW)), "window not contiguous on E_ts"
ANN=np.sqrt(2190.0)
def ann(x):
    s=np.std(x,ddof=1); return float(np.mean(x)/s*ANN) if s>0 else float("nan")
print("window n=%d  %d..%d   A0 meang=%+.4f SR=%+.4f  A0 turn=%.4f A0 costrate=%.4f"%(
    NW,a_ts_k[0],a_ts_k[-1],gA0.mean(),ann(gA0),tnA0.mean(),cA0.mean()/tnA0.mean()))

# ---------------- eligibility + cost tiers (live definitions, shadow_loop_v3 L473-474 / L520)
MEMB=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
QV4H=np.expm1(np.clip(QV,0,30))*48.0        # qvk is LOG quote-volume; expm1 belongs here, NOT on y4
ELIG=MEMB & np.isfinite(Y) & (QV4H>=2.5e5)
TIER=np.full((T,N),2,np.int8); TIER[QV4H>=1e6]=1; TIER[QV4H>=5e6]=0
CB=json.load(open(COSTB))
RATES=np.array(CB["blended_bps_per_unit_turnover"],float)   # [tier0,tier1,tier2]
RATE=RATES[TIER]
print("cost rates",RATES,"book_avg",CB["book_avg_bps_per_unit_turnover"])
print("mean eligible names/anchor:",round(float(ELIG[IDX].sum(1).mean()),1))

Yz=np.where(np.isfinite(Y),Y,0.0); FIN=np.isfinite(Y)
def trail_std(k):
    S1=np.zeros((T,N)); S2=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1):
        S1[j:]+=Yz[:T-j]; S2[j:]+=Yz[:T-j]**2; C[j:]+=FIN[:T-j]
    with np.errstate(invalid='ignore',divide='ignore'):
        mu=S1/np.maximum(C,1); v=S2/np.maximum(C,1)-mu**2
    return np.sqrt(np.maximum(v,0)),C
def trail_sum(k):
    S=np.zeros((T,N)); C=np.zeros((T,N))
    for j in range(1,k+1): S[j:]+=Yz[:T-j]; C[j:]+=FIN[:T-j]
    return S,C

def build_W(score,valid):
    W=np.zeros((NW,N))
    for ii in range(NW):
        t=IDX[ii]
        e=ELIG[t]&valid[t]&np.isfinite(score[t])
        n=int(e.sum())
        if n<20: continue
        r=rankdata(score[t,e])/(n+1.0)-0.5
        w=r-r.mean(); s=np.abs(w).sum()
        if s>0: W[ii,e]=w/s
    return W
def build_Wprev(score,valid):
    """weights at the anchor immediately BEFORE the window, so the first turnover is a true delta"""
    t=IDX[0]-1
    e=ELIG[t]&valid[t]&np.isfinite(score[t]); w=np.zeros(N)
    if e.sum()>=20:
        r=rankdata(score[t,e])/(int(e.sum())+1.0)-0.5; ww=r-r.mean(); s=np.abs(ww).sum()
        if s>0: w[e]=ww/s
    return w
def evaluate(W,w_prev):
    gg=np.zeros(NW); tn=np.zeros(NW); cst=np.zeros(NW); cflat=np.zeros(NW)
    prev=w_prev
    for ii in range(NW):
        t=IDX[ii]; w=W[ii]
        gg[ii]=1e4*float(np.sum(w*Yz[t]))
        d=np.abs(w-prev); tn[ii]=d.sum()
        cst[ii]=float(np.sum(d*RATE[t])); cflat[ii]=CB["book_avg_bps_per_unit_turnover"]*tn[ii]
        prev=w
    return gg,tn,cst,cflat

L=42
SD,CD=trail_std(L)
SC=-SD; VAL=CD>=30
W=build_W(SC,VAL); wprev=build_Wprev(SC,VAL)
gg,tn,cst,cflat=evaluate(W,wprev)
net=gg-cst; netflat=gg-cflat
print("\n== VRP_DELTA1 (L=42) ==")
print("gross g %+0.4f  SR_gross %+0.4f   turnover %.5f"%(gg.mean(),ann(gg),tn.mean()))
print("cost tiered %.4f (rate %.4f/unit)   cost flat %.4f"%(cst.mean(),cst.mean()/tn.mean(),cflat.mean()))
print("NET g %+0.4f  SR_net %+0.4f   |  NETflat g %+0.4f SR %+0.4f"%(net.mean(),ann(net),netflat.mean(),ann(netflat)))
print("cost survival %.1f%% of gross"%(100.0*net.mean()/gg.mean()))

# ---------------- alignment / leak guard: offset spectrum
def offspec(score,valid,label):
    out={}
    for k in range(-3,4):
        ics=[]
        for ii in range(0,NW,3):
            t=IDX[ii]; tt=t+k
            if tt<0 or tt>=T: continue
            e=ELIG[t]&valid[t]&np.isfinite(score[t])&np.isfinite(Y[tt])
            if e.sum()<20: continue
            ics.append(spearmanr(score[t,e],Y[tt,e]).statistic)
        ics=np.array(ics); ics=ics[np.isfinite(ics)]
        out[k]=dict(IC=float(ics.mean()),t=float(ics.mean()/ics.std(ddof=1)*np.sqrt(len(ics))),n=int(len(ics)))
        print("  %s k=%+d IC=%+.5f t=%+.2f n=%d"%(label,k,out[k]["IC"],out[k]["t"],out[k]["n"]))
    return out
print("\nOFFSET SPECTRUM VRP_DELTA1 score vs y4")
OS_V=offspec(SC,VAL,"VRP")
S1,C1=trail_sum(1)
print("OFFSET SPECTRUM control REV1 (must be -1.000 at k=-1 by construction: alignment proof)")
OS_R=offspec(-S1,C1>=1,"REV1")

# ---------------- block bootstrap machinery
DAY=(a_ts_k//86400).astype(np.int64)
udays,dinv=np.unique(DAY,return_inverse=True)
DGROUPS=[np.where(dinv==j)[0] for j in range(len(udays))]
NB=2000
def boot_idx(k):
    rng=np.random.default_rng([20260905,int(k)])
    pick=rng.integers(0,len(DGROUPS),len(DGROUPS))
    return np.concatenate([DGROUPS[j] for j in pick])
BOOT=[boot_idx(k) for k in range(NB)]
def bci(fn):
    v=np.array([fn(b) for b in BOOT]); v=v[np.isfinite(v)]
    return float(np.percentile(v,2.5)),float(np.percentile(v,97.5))

# ---------------- STEP 2: independence
def prho(x,y): 
    s=np.corrcoef(x,y)[0,1]; return float(s)
rho=prho(net,gA0); rsp=float(spearmanr(net,gA0).statistic)
rho_g=prho(gg,gA0)
rho_ci=bci(lambda b: np.corrcoef(net[b],gA0[b])[0,1])
q20=float(np.quantile(gA0,0.20)); lose=gA0<=q20
rho_lo=prho(net[lose],gA0[lose])
rho_lo_ci=bci(lambda b: (np.corrcoef(net[b][gA0[b]<=q20],gA0[b][gA0[b]<=q20])[0,1]
                         if (gA0[b]<=q20).sum()>50 else np.nan))
print("\n== STEP 2 INDEPENDENCE ==")
print("rho(net, A0.g) = %+0.4f  CI95 [%+0.4f,%+0.4f]   spearman %+0.4f   rho(gross,A0)=%+0.4f"%(rho,rho_ci[0],rho_ci[1],rsp,rho_g))
print("A0 bottom-quintile threshold %+0.4f  n_lose=%d"%(q20,int(lose.sum())))
print("rho | A0 bottom quintile = %+0.4f  CI95 [%+0.4f,%+0.4f]"%(rho_lo,rho_lo_ci[0],rho_lo_ci[1]))
mean_lose=float(net[lose].mean()); mean_lose_ci=bci(lambda b: net[b][gA0[b]<=q20].mean() if (gA0[b]<=q20).sum()>50 else np.nan)
print("candidate NET mean g inside A0's losing cells = %+0.4f  CI95 [%+0.4f,%+0.4f]  (A0 there %+0.4f)"%(
    mean_lose,mean_lose_ci[0],mean_lose_ci[1],float(gA0[lose].mean())))

# weight-space overlap with A0's actual book
cos=np.zeros(NW)
for ii in range(NW):
    u=W[ii]; v=WA0[ii]
    du=np.linalg.norm(u); dv=np.linalg.norm(v)
    cos[ii]=float(u@v/(du*dv)) if du>0 and dv>0 else np.nan
cos=cos[np.isfinite(cos)]
print("weight-space cosine(VRP_w, A0_w): mean %+0.4f  median %+0.4f  p5 %+0.4f p95 %+0.4f"%(
    cos.mean(),np.median(cos),np.percentile(cos,5),np.percentile(cos,95)))

json.dump(dict(shas=SHAS,n=NW,note="stage1"),open(OUT+"/_stage1.json","w"),indent=1)
np.savez_compressed(OUT+"/series_stage1.npz",ts=a_ts_k,gA0=gA0,gg=gg,net=net,tn=tn,cst=cst,
                    W=W.astype(np.float32))
print("\nstage1 %.0fs"%(time.time()-t0))
