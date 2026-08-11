"""DEEP re-examination: is the order-flow signal being lost by my feature construction?
Compute OFI / trade-flow / book-dynamics PROPERLY (raw rolling sums, simple z-score)
on BTC and measure univariate Spearman vs y_600. If raw flow >> my current features,
the blocker is feature construction (the causal expanding-RMS normalization), not the data.
"""
import numpy as np, sys
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import load_day_panel
from scipy.stats import spearmanr, pearsonr

SYM="bnfbtc"
# sample ~20 days across 2024-2025
DAYS=[20240115,20240201,20240301,20240401,20240501,20240601,20240701,20240801,20240901,
      20241001,20241101,20241201,20250101,20250201,20250301,20250401,20250501,20250601,20250701,20250801]
H=600; STRIDE=600  # clean

def roll_sum(a,w):
    c=np.cumsum(np.nan_to_num(a)); out=c.copy(); out[w:]=c[w:]-c[:-w]; return out

allrows={}
def push(name,x,y):
    m=np.isfinite(x)&np.isfinite(y)
    allrows.setdefault(name,[[],[]]); allrows[name][0].append(x[m]); allrows[name][1].append(y[m])

for d in DAYS:
    try: P=load_day_panel(d,[SYM])
    except Exception: continue
    X=P.data[SYM]; c=P.cols
    def col(n): return X[:,c.index(n)].astype(float)
    mid=col("mid"); n=len(mid)
    logm=np.log(mid)
    # y_600 forward, clean stride
    t=np.arange(0,n-H-1,STRIDE)
    y=logm[t+H]-logm[t]
    # ---- PROPER OFI (CKS) from 5 levels: signed queue change ----
    bp=[col("bid")]+[col(f"bid_{i}") for i in range(1,5)]
    bs=[col("bidsz")]+[col(f"bidsz_{i}") for i in range(1,5)]
    ap=[col("ask")]+[col(f"ask_{i}") for i in range(1,5)]
    as_=[col("asksz")]+[col(f"asksz_{i}") for i in range(1,5)]
    ofi=np.zeros(n)
    for L in range(5):
        bpL,bsL,apL,asL=bp[L],bs[L],ap[L],as_[L]
        dbp=np.diff(bpL,prepend=bpL[0]); dap=np.diff(apL,prepend=apL[0])
        bsp=np.roll(bsL,1); bsp[0]=bsL[0]; asp=np.roll(asL,1); asp[0]=asL[0]
        e_b=np.where(dbp>0,bsL,np.where(dbp<0,-bsp,bsL-bsp))
        e_a=np.where(dap<0,asL,np.where(dap>0,-asp,asL-asp))
        ofi+=e_b-e_a
    # ---- trade flow imbalance (raw) ----
    tqb=col("tdQtyBuy"); tqs=col("tdQtySell")
    tflow=(tqb-tqs)
    tflow_imb=(tqb-tqs)/(tqb+tqs+1e-9)
    # dollar flow
    dflow=col("tdQtyPxBuy")-col("tdQtyPxSell")
    # book add/del flow
    bkflow=(col("bkAddBid")-col("bkDelBid"))-(col("bkAddAsk")-col("bkDelAsk"))
    # mid-change asym
    mca=col("midChgUp")-col("midChgDn")
    # ---- rolling-sum windows, sample at t ----
    for nm,series in [("OFI",ofi),("tradeflow",tflow),("dollarflow",dflow),("bookflow",bkflow),("midchg",mca)]:
        for w in (30,60,300):
            push(f"{nm}_{w}s", roll_sum(series,w)[t], y)
    push("tflow_imb_60s", roll_sum(tflow_imb,60)[t]/60, y)
    # reference: simple OBI L1 + 5min reversal
    push("obi_L1", ((bs[0]-as_[0])/(bs[0]+as_[0]+1e-9))[t], y)
    push("ret_300s", (logm[t]-logm[np.maximum(t-300,0)]), y)

print(f"{'feature':16s} {'Spearman':>9s} {'Pearson':>9s} {'n':>8s}")
rows=[]
for nm,(xs,ys) in allrows.items():
    x=np.concatenate(xs); y=np.concatenate(ys)
    if len(x)<500: continue
    s=spearmanr(x,y).correlation; pe=pearsonr(x,y)[0]
    rows.append((nm,s,pe,len(x)))
for nm,s,pe,n in sorted(rows,key=lambda r:-abs(r[1])):
    print(f"{nm:16s} {s:>+9.4f} {pe:>+9.4f} {n:>8d}")
print("\nIf OFI/tradeflow Spearman >> 0.04 here but my features_ma versions were ~0.01, the")
print("blocker = my causal expanding-RMS normalization destroyed the flow signal.")
