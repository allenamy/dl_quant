"""DECOMPOSE the 2025-10 Ridge CLEAN +0.169 -- explain it (real momentum) or expose it (artifact).

Addresses the 3 inflation suspects:
 1. ALPHA: print EXACT per-alpha CLEAN (already flat 0.16-0.17, but confirm) + alpha chosen by TRAIN-SUB
    validation (NOT test) -> the honest deployable number.
 2. DECOMPOSE: top Ridge features by |coef| + each one's RAW univariate CLEAN Pearson with y_600. Is it ONE
    explicable feature (momentum/microprice) or diffuse? + is 2025-10 a strong-MOMENTUM month:
    corr(y_600, past-60s-return) and AR1 corr(y_600[t], y_600[t-600s]).
 3. CALIBER: clean_p N + per-offset spread (4 non-overlapping offsets) + 95% CI on the IC (1.96/sqrt(N-3)).
    Single-offset IC (one non-overlapping subset) as the most conservative number.

Run on SERVER: PYTHONPATH=. python multi_asset/data/decompose_ridge_169.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

CACHE="data/npz_v2arch"
# channel names for npz_v2arch (64 spot + 16 perp-trade + 8 cross). We label the snapshot vector:
# snapshot = [last-step(88) , 60s-mean(88)] = 176 dims. Index i<88 = last-step ch i; i>=88 = mean ch (i-88).
PT=["pt_buy_volume_1s","pt_sell_volume_1s","pt_net_trade_flow_1s","pt_trade_imbalance_1s",
    "pt_cumulative_net_flow_30s","pt_cumulative_net_flow_300s","pt_trade_intensity_30s","pt_vwap_return_1s",
    "pt_kyle_lambda_30s","pt_vpin_60s","pt_vpin_300s","pt_price_impact_30s","pt_net_flow_x_spread",
    "pt_net_flow_x_vol","pt_net_flow_rank_1h","pt_large_trade_arrival_60s"]
CROSS=["x_mid_ratio_log","x_basis_bps","x_spread_ratio_log","x_depth_ratio_log","x_obi_diff",
       "x_mpdev_diff","x_rvol_ratio_log","x_tradeflow_ratio"]
def chname(j):
    base = j if j<88 else j-88
    tag = "last" if j<88 else "mean"
    if base<64: nm=f"spot{base}"
    elif base<80: nm=PT[base-64]
    else: nm=CROSS[base-80]
    return f"{nm}.{tag}"

def dd(p): return os.path.basename(p)[:-4]
def load(mons):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7] in mons]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    return np.nan_to_num(np.concatenate(Xs)), np.concatenate(ys), np.concatenate(ts)

def clean_idx(ts, off):
    o=np.argsort(ts); keep=[]; last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=600*1_000_000: keep.append(o[i]); last=ts[o[i]]
    return np.array(keep)

def clean_p_detail(p,y,ts):
    Ps=[]; Ns=[]
    for off in range(4):
        k=clean_idx(ts,off)
        if len(k)>30:
            r=pearsonr(p[k],y[k])[0]
            if np.isfinite(r): Ps.append(r); Ns.append(len(k))
    return np.array(Ps), np.array(Ns)

def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

tm="2025-10"
pm=prior_months(tm)
Xtr,ytr,ttr=load(pm); Xte,yte,tte=load([tm])
mu=Xtr.mean(0); sd=Xtr.std(0)+1e-8
Xtr_s=(Xtr-mu)/sd; Xte_s=(Xte-mu)/sd
print(f"=== DECOMPOSE 2025-10 Ridge CLEAN +0.169 ===  Ntr={len(ytr)} Nte={len(yte)}")

# ---- 1. per-alpha CLEAN (mean + per-offset) + alpha by TRAIN-SUB validation ----
print("\n[1] PER-ALPHA CLEAN (test) -- is 0.169 alpha-cherry-picked?")
for a in [1,10,100,1000]:
    r=Ridge(alpha=a).fit(Xtr_s,ytr); p=r.predict(Xte_s)
    Ps,Ns=clean_p_detail(p,yte,tte)
    print(f"  alpha={a:>4d}: CLEAN mean={Ps.mean():+.4f}  per-offset={np.round(Ps,3)}  N/offset~{int(Ns.mean())}")
# alpha by train-sub (last 10% of train as val) -- honest, no test peeking
c=int(len(ytr)*0.9); best=None
for a in [1,10,100,1000]:
    r=Ridge(alpha=a).fit(Xtr_s[:c],ytr[:c]); ph=r.predict(Xtr_s[c:])
    P=pearsonr(ph,ytr[c:])[0] if ph.std()>1e-9 else -9
    if best is None or P>best[0]: best=(P,a)
a_honest=best[1]
r=Ridge(alpha=a_honest).fit(Xtr_s,ytr); p=r.predict(Xte_s)
Ps,Ns=clean_p_detail(p,yte,tte)
print(f"  -> alpha by TRAIN-SUB val = {a_honest}; CLEAN mean={Ps.mean():+.4f} (the HONEST deployable number)")

# ---- 3. CALIBER: N + per-offset + single-offset + 95% CI ----
print("\n[3] CALIBER: clean_p detail")
print(f"  per-offset Pearson = {np.round(Ps,4)} (N/offset = {Ns.tolist()})")
print(f"  single-offset (most conservative) = {Ps[0]:+.4f}")
N=int(Ns.mean()); ci=1.96/np.sqrt(max(N-3,1))
print(f"  N~{N}/offset -> 95% CI ±{ci:.4f}  => IC {Ps.mean():+.4f} ± {ci:.4f} (sep from 0? {'YES' if Ps.mean()-ci>0 else 'NO'})")

# ---- 2. feature decomposition ----
print("\n[2a] TOP Ridge features by |coef| + raw univariate CLEAN Pearson(feature, y):")
coef=r.coef_; top=np.argsort(np.abs(coef))[::-1][:12]
k0=clean_idx(tte,0)
for j in top:
    uni=pearsonr(Xte_s[k0,j],yte[k0])[0]
    print(f"  {chname(j):22s} coef={coef[j]:+.3f}  univ-CLEAN-P={uni:+.4f}")
# concentration: how much of pred variance from top-5 features?
contrib=np.abs(coef)*Xtr_s.std(0)  # std already 1, so ~|coef|
share=np.sort(contrib)[::-1]; tot=share.sum()
print(f"  top-1 |coef| share={share[0]/tot:.1%}, top-5 share={share[:5].sum()/tot:.1%}, top-20 share={share[:20].sum()/tot:.1%}  (diffuse if top-20 small)")

print("\n[2b] Is 2025-10 a strong-MOMENTUM month?")
# y autocorr at 600s lag (consecutive non-overlapping windows)
o=np.argsort(tte); ys=yte[o]; ts=tte[o]
k=clean_idx(tte,0); yk=yte[k]
ar1=pearsonr(yk[:-1],yk[1:])[0] if len(yk)>30 else np.nan
print(f"  AR1 corr(y_600[t], y_600[t+600s]) on non-overlap = {ar1:+.4f}  (>0.3 = trending)")
# past-60s return proxy = pt_vwap_return or x_mid_ratio_log last-step; corr with y
for nm,j in [("x_mid_ratio_log.last",80),("pt_vwap_return_1s.last",64+7),("pt_cumulative_net_flow_300s.last",64+5)]:
    uni=pearsonr(Xte_s[k0,j],yte[k0])[0]
    print(f"  corr({nm}, y_600) CLEAN = {uni:+.4f}")
print("\nDONE_DECOMP.")
