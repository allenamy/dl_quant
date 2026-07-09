import numpy as np, sys, os.path as op, datetime as dt
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.backtest_longshort import rank_weights
E="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
M=load_panel("m0_fullhist_wf",E); F=load_panel("fund_ema_fullhist",E)
Y,CL=M["Y"],M["CL"].astype(bool); ts=M["ts"].astype(np.int64); 
M0=M["pred"]; FU=F["pred"]
u=1e9 if ts[0]>1e17 else (1e6 if ts[0]>1e14 else 1e3)
yr=np.array([dt.datetime.utcfromtimestamp(int(t)/u).year for t in ts])
ANN=np.sqrt(365*24*3600/3600); MIN=5
def clean_rows(sig,rows):
    return [t for t in rows if (CL[t]&np.isfinite(sig[t])&np.isfinite(Y[t])).sum()>=MIN]
def series(sig,rows):
    rr=clean_rows(sig,rows); S=Y.shape[1]
    tw=np.zeros((len(rr),S)); Yr=np.zeros((len(rr),S))
    for i,t in enumerate(rr):
        v=CL[t]&np.isfinite(sig[t])&np.isfinite(Y[t]); idx=np.where(v)[0]
        tw[i,idx]=rank_weights(sig[t,idx]); Yr[i,idx]=Y[t,idx]
    return tw,Yr
def held(tw,Yr,alpha):
    S=tw.shape[1]; h=np.zeros(S); n=len(tw); g=np.empty(n); tn=np.empty(n)
    for k in range(n):
        new=alpha*tw[k]+(1-alpha)*h; tn[k]=np.abs(new-h).sum(); g[k]=(new*Yr[k]).sum(); h=new
    return g,tn
def sh(x): return x.mean()/x.std()*ANN if x.std()>0 else np.nan
print("year | factor | autocorr(w_t,w_t-1) | alpha: grossSh / net@5 / turnover")
for y in [2023,2024,2025]:
    rows=np.where(yr==y)[0]
    for nm,sig in [("M0",M0),("funding",FU)]:
        tw,Yr=series(sig,rows)
        # per-step weight autocorr (flatten, corr of consecutive rows over all asset-cells)
        a=tw[:-1].ravel(); b=tw[1:].ravel(); m=np.isfinite(a)&np.isfinite(b)
        ac=np.corrcoef(a[m],b[m])[0,1] if m.sum()>10 else np.nan
        out=[]
        for al in (1.0,0.1,0.02):
            g,tn=held(tw,Yr,al); net=g-tn*(5e-4)
            out.append(f"a{al}: gS={sh(g):+.2f} n5={sh(net):+.2f} turn={tn.mean():.3f}")
        print(f"{y} | {nm:8s} | wt-autocorr={ac:+.3f} | "+" | ".join(out))
