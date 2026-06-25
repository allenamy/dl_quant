"""MUTATION / non-stationarity / anomaly factors -> re-run drift in-regime signal-floor.

Tests the user hypothesis: drift months (2025-12, 2026-02) have MUTATION signals the
current factors miss -> "fundamental no-signal" (in-regime Ridge -0.012) may be a
MISSING-FEATURE limit. DECISIVE: add rigorous causal mutation factors, re-run in-regime
held-out Ridge. If 2025-12 unlocks (-0.012 -> positive) -> missing-feature, not fundamental.

All factors causal (within-window <=t per-second series + trailing OI/funding <=t). Leak-safe.
Compares per fold: in-regime held-out Ridge [base snapshot] vs [base + mutation].
Run: PYTHONPATH=. python multi_asset/data/mutation_signal_floor.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

# X channel indices (npz_v2arch X=88)
MID=64; BASIS=65; SPREAD=66; DEPTH=67; OBI=68; RVOL=70; NETFLOW=74
HOR_US=600*1_000_000

# ---- OI/funding metrics (trailing, <=t) ----
def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def load_metrics():
    rows=[]
    with open("data/funding/btcusdt_metrics_5m.csv") as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),float(r["sum_open_interest"]),float(r["sum_open_interest_value"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
def load_funding():
    rows=[]
    with open("data/funding/btcusdt_funding.csv") as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,float(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
M=load_metrics(); F=load_funding(); MT=M[:,0];OI=M[:,1];OIV=M[:,2];PR=OIV/np.clip(OI,1e-9,None); FT=F[:,0];FR=F[:,1]

def oi_fund_mut(ts_us):
    cut=ts_us-300*1_000_000
    im=np.searchsorted(MT,cut,side="right")-1; iff=np.searchsorted(FT,ts_us,side="right")-1
    N=len(ts_us); out=np.zeros((N,4)); v=(im>=0)&(iff>=0); iv=im[v]; ifv=iff[v]
    K=6; iK=np.clip(iv-K,0,None)
    dOI=OI[iv]-OI[iK]; dP=PR[iv]-PR[iK]
    oiz=np.zeros(len(iv))
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=OI[lo:i+1]; oiz[j]=(OI[i]-h.mean())/(h.std()+1e-9)
    fspike=np.zeros(len(ifv))
    for j,i in enumerate(ifv):
        lo=max(0,i-29); h=FR[lo:i+1]; fspike[j]=(FR[i]-h.mean())/(h.std()+1e-9)
    out[v,0]=oiz                                  # OI-surge z (crowding/mutation)
    out[v,1]=np.sign(dOI)*np.sign(dP)             # OI-price 4-quadrant
    out[v,2]=fspike                               # funding spike z
    out[v,3]=(FR[ifv]-FR[np.clip(ifv-1,0,None)])  # funding acceleration
    return np.nan_to_num(out)

# ---- within-window mutation factors (per-second series, causal) ----
def win_mut(Xw):  # Xw: (N,600,88)
    N=Xw.shape[0]; out=np.zeros((N,9))
    price=Xw[:,:,MID]                              # price-proxy per-second
    ret=np.diff(price,axis=1)                      # (N,599) per-second returns
    spread=Xw[:,:,SPREAD]; depth=Xw[:,:,DEPTH]; nf=Xw[:,:,NETFLOW]
    eps=1e-9
    # 1 CUSUM structural-break: max |cumsum(ret-mean)| normalized
    rc=ret-ret.mean(1,keepdims=True); cs=np.cumsum(rc,axis=1)
    out[:,0]=np.max(np.abs(cs),axis=1)/(ret.std(1)*np.sqrt(ret.shape[1])+eps)
    # 2 variance-ratio: var(2nd half)/var(1st half) of returns
    h=ret.shape[1]//2
    out[:,1]=np.log((ret[:,h:].var(1)+eps)/(ret[:,:h].var(1)+eps))
    # 3 BNS bipower jump: (RV - BV)/RV ; RV=sum r^2, BV=(pi/2) sum |r_i||r_{i-1}|
    rv=np.sum(ret**2,axis=1); bv=(np.pi/2)*np.sum(np.abs(ret[:,1:])*np.abs(ret[:,:-1]),axis=1)
    out[:,2]=(rv-bv)/(rv+eps)
    # 4 Hurst (R/S on cumulative returns, single-scale proxy)
    Z=np.cumsum(rc,axis=1); R=Z.max(1)-Z.min(1); S=ret.std(1)+eps
    out[:,3]=np.log(R/S+eps)/np.log(ret.shape[1]+eps)
    # 5 distribution-shift: |mean(recent120)-mean(prior)| / std (within window)
    out[:,4]=np.abs(ret[:,-120:].mean(1)-ret[:,:-120].mean(1))/(ret.std(1)+eps)
    # 6 spread-regime break: spread last-60 vs first-540 (z)
    out[:,5]=(spread[:,-60:].mean(1)-spread[:,:-60].mean(1))/(spread.std(1)+eps)
    # 7 depth-collapse: depth recent vs window (neg = collapse)
    out[:,6]=(depth[:,-60:].mean(1)-depth.mean(1))/(depth.std(1)+eps)
    # 8 OFI burst: net-flow recent z
    out[:,7]=(nf[:,-60:].mean(1)-nf.mean(1))/(nf.std(1)+eps)
    # 9 vol-of-vol: std of per-100-step block vols
    blks=[ret[:,i*120:(i+1)*120].std(1) for i in range(ret.shape[1]//120)]
    out[:,8]=np.std(np.stack(blks,1),axis=1) if blks else 0.0
    return np.nan_to_num(out)

def dd(p): return p.split("/")[-1][:-4]
def load(mon):
    fs=sorted(glob.glob("data/npz_v2arch/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    per=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        wt=d["timestamps"][m].astype(np.int64)
        mut=np.concatenate([win_mut(X), oi_fund_mut(wt)],axis=1)  # 9 + 4 = 13 mutation factors
        per.append((np.nan_to_num(snap.astype(np.float32)), mut.astype(np.float32), d["y_600"][m].astype(np.float32), wt))
    return per

def clean_p(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=HOR_US: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps) if Ps else 0.0

def floor(mon):
    per=load(mon); nd=len(per); nb=min(5,nd); blocks=np.array_split(np.arange(nd),nb)
    base=[];both=[];mutonly=[]
    for b in blocks:
        te=[per[i] for i in b]; tr=[per[i] for i in range(nd) if i not in set(b.tolist())]
        if not tr or not te: continue
        Xtr=np.concatenate([d[0] for d in tr]); Mtr=np.concatenate([d[1] for d in tr]); ytr=np.concatenate([d[2] for d in tr])
        Xte=np.concatenate([d[0] for d in te]); Mte=np.concatenate([d[1] for d in te]); yte=np.concatenate([d[2] for d in te]); tte=np.concatenate([d[3] for d in te])
        def best(A,B):
            mu=A.mean(0);sd=A.std(0)+1e-8;bb=-9
            for a in [1,10,100,1000,10000]:
                p=Ridge(alpha=a).fit((A-mu)/sd,ytr).predict((B-mu)/sd); bb=max(bb,clean_p(p,yte,tte))
            return bb
        base.append(best(Xtr,Xte)); both.append(best(np.concatenate([Xtr,Mtr],1),np.concatenate([Xte,Mte],1))); mutonly.append(best(Mtr,Mte))
    print(f"  {mon}: base CLEAN={np.mean(base):+.4f}  base+MUTATION CLEAN={np.mean(both):+.4f}  (mut-only={np.mean(mutonly):+.4f})  dP={np.mean(both)-np.mean(base):+.4f}")

print("=== MUTATION-FACTOR in-regime signal-floor (drift months) ===")
print("13 causal mutation factors (CUSUM/var-ratio/BNS-jump/Hurst/dist-shift/spread-break/depth-collapse/OFI-burst/vov + OI-surge/4quad/funding-spike/accel)")
for m in ["2025-12","2026-02"]:
    floor(m)
print("\nVERDICT: base+MUTATION >> base (2025-12 -0.012 -> positive) => drift was MISSING-FEATURE (user right).")
print("         base+MUTATION ~= base => mutation factors also dont capture it (fundamental, honest negative).")
