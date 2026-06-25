"""DECISIVE TEST: can a RICH JOINT (≤t) regime representation CAUSALLY PREDICT the forward regime?

User hypothesis: the regime-gate failed (cosmetic) maybe because the descriptor (vol/trend 6ch) is INADEQUATE,
not because of low-SNR. A rich JOINT representation (spot+perp book + funding + OI) might causally characterize
the regime -> then a gate could learn (with regime-supervision). FALSIFIABLE: predict FORWARD regime from ≤t joint
features. If IC/acc > chance -> regime causally learnable (build supervised gate). If ~chance -> not characterizable.

LEAK-SAFE: features strictly from window data <=t (trailing) + OI/funding settled <=t. Labels from REALIZED
FUTURE windows (the thing we predict). Walk-forward (train past months -> predict future month).

JOINT features (per window, ≤t):
  basis (last x_basis_bps), basis_mom, spot-perp: spread_ratio, depth_ratio, rvol_ratio, obi_diff, tradeflow_ratio
  (the 8 cross channels, last-step) + ptrade aggregates (net-flow, vpin-ish) + OI-surge-z, OI-flow, funding-z,
  funding x OI, OI-price 4-quadrant + within-window vol(60/300/full), vol-accel, AR1(120), CUSUM, var-ratio.
FORWARD-regime LABELS (realized, causal target):
  L_trend  = sign-consistency of forward returns = AR1 of the NEXT N windows' y_600 (trending>0 / reverting<0)
  L_strong = dispersion (std) of the NEXT N windows' |y_600| (strong/favorable regime)
Run: PYTHONPATH=. python multi_asset/data/causal_regime_predict.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge, LogisticRegression
from scipy.stats import pearsonr, spearmanr

MID=64;BASIS=65;SPREAD=66;DEPTH=67;OBI=68;RVOL=70;TRADEF=71;NETFLOW=74
def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def load_csv(path, cols):
    rows=[]
    with open(path) as f:
        for r in csv.DictReader(f):
            try: rows.append([ (parse_us(r[cols[0]]) if cols[0]=="create_time" else int(r[cols[0]])*1000) ]+[float(r[c]) for c in cols[1:]])
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
MET=load_csv("data/funding/btcusdt_metrics_5m.csv",["create_time","sum_open_interest","sum_open_interest_value"])
FUN=load_csv("data/funding/btcusdt_funding.csv",["fundingTime_ms","fundingRate"])
MT=MET[:,0];OI=MET[:,1];OIV=MET[:,2];PR=OIV/np.clip(OI,1e-9,None);FT=FUN[:,0];FR=FUN[:,1]

def oifund(ts):
    cut=ts-300*1_000_000; im=np.searchsorted(MT,cut,"right")-1; iff=np.searchsorted(FT,ts,"right")-1
    N=len(ts);out=np.zeros((N,5));v=(im>=0)&(iff>=0);iv=im[v];ifv=iff[v];K=6;iK=np.clip(iv-K,0,None)
    dOI=OI[iv]-OI[iK];dP=PR[iv]-PR[iK]
    oiz=np.array([ (OI[i]-OI[max(0,i-71):i+1].mean())/(OI[max(0,i-71):i+1].std()+1e-9) for i in iv])
    fz=np.array([ (FR[i]-FR[max(0,i-29):i+1].mean())/(FR[max(0,i-29):i+1].std()+1e-9) for i in ifv])
    out[v,0]=dOI/(np.abs(OI[iv])+1e-9);out[v,1]=oiz;out[v,2]=fz;out[v,3]=fz*oiz;out[v,4]=np.sign(dOI)*np.sign(dP)
    return np.nan_to_num(out)

def joint_feats(X, ts):  # X (N,600,88)
    N=X.shape[0]; price=X[:,:,MID]; ret=np.diff(price,1); eps=1e-9
    f=[]
    # cross/book last-step (8)
    for c in [BASIS,SPREAD,DEPTH,OBI,RVOL,TRADEF]: f.append(X[:,-1,c])
    f.append(X[:,:,NETFLOW][:,-60:].mean(1))
    # within-window dynamics
    f.append(ret[:,-60:].std(1)); f.append(ret[:,-300:].std(1)); f.append(ret.std(1))      # vol 60/300/full
    f.append(ret[:,-60:].std(1)/(ret.std(1)+eps))                                            # vol-accel
    rc=ret-ret.mean(1,keepdims=True); cs=np.cumsum(rc,1); f.append(np.max(np.abs(cs),1)/(ret.std(1)*np.sqrt(ret.shape[1])+eps))  # CUSUM
    h=ret.shape[1]//2; f.append(np.log((ret[:,h:].var(1)+eps)/(ret[:,:h].var(1)+eps)))      # var-ratio
    basis=X[:,:,BASIS]; f.append(basis[:,-1]-basis[:,-61])                                   # basis mom
    F=np.stack(f,1)
    return np.nan_to_num(np.concatenate([F, oifund(ts)],1))   # ~17 joint causal features

def dd(p): return p.split("/")[-1][:-4]
def load_month(mon):
    fs=sorted(glob.glob("data/npz_v2arch/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    Fs=[];ys=[];tss=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        Fs.append(joint_feats(d["X"][m], d["timestamps"][m].astype(np.int64))); ys.append(d["y_600"][m].astype(np.float32)); tss.append(d["timestamps"][m].astype(np.int64))
    return np.concatenate(Fs),np.concatenate(ys),np.concatenate(tss)

def fwd_labels(y,ts,N=30):
    # for each window i, forward window = next N windows (by time order). causal label from realized future.
    o=np.argsort(ts); y=y[o]; n=len(y)
    Ltrend=np.full(n,np.nan); Lstrong=np.full(n,np.nan)
    for i in range(n-N):
        fy=y[i+1:i+1+N]
        if len(fy)>5 and fy.std()>0:
            Ltrend[i]=np.corrcoef(fy[:-1],fy[1:])[0,1]   # forward AR1: trending(+)/reverting(-)
            Lstrong[i]=np.abs(fy).std()                   # forward |y| dispersion: strong-favorable
    return Ltrend,Lstrong,o

# walk-forward: train 2025-02..2025-11, predict each of 2025-12, 2026-02 (drift) + 2025-04 (strong) + 2025-08
TR=["2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09"]
print("=== CAUSAL FORWARD-REGIME PREDICTABILITY (joint <=t feats -> forward regime) ===")
Ftr=[];Ltr_t=[];Ltr_s=[]
for mon in TR:
    F,y,ts=load_month(mon); lt,ls,o=fwd_labels(y,ts); F=F[o]
    keep=~np.isnan(lt); Ftr.append(F[keep]); Ltr_t.append(lt[keep]); Ltr_s.append(ls[keep])
Ftr=np.concatenate(Ftr);Ltr_t=np.concatenate(Ltr_t);Ltr_s=np.concatenate(Ltr_s)
mu=Ftr.mean(0);sd=Ftr.std(0)+1e-8
rt=Ridge(alpha=10).fit((Ftr-mu)/sd,Ltr_t); rs=Ridge(alpha=10).fit((Ftr-mu)/sd,Ltr_s)
for mon in ["2025-10","2025-11","2025-12","2026-02"]:
    try:
        F,y,ts=load_month(mon); lt,ls,o=fwd_labels(y,ts); F=F[o]
        keep=~np.isnan(lt); Fk=(F[keep]-mu)/sd
        pt=rt.predict(Fk); ps=rs.predict(Fk)
        ic_t=spearmanr(pt,lt[keep])[0]; ic_s=spearmanr(ps,ls[keep])[0]
        # trend direction accuracy
        acc=np.mean(np.sign(pt)==np.sign(lt[keep]))
        print(f"  {mon}: FWD-TREND IC={ic_t:+.4f} (dir-acc {acc:.3f}) | FWD-STRONG IC={ic_s:+.4f}  (n={keep.sum()})")
    except Exception as e: print(f"  {mon}: {e}")
print("\nVERDICT: IC>>0 (e.g. >0.05) + dir-acc>0.55 -> regime CAUSALLY predictable from joint feats (gate learnable w/ supervision).")
print("         IC~0 + acc~0.5 -> regime NOT causally characterizable from this data (the real limit).")
