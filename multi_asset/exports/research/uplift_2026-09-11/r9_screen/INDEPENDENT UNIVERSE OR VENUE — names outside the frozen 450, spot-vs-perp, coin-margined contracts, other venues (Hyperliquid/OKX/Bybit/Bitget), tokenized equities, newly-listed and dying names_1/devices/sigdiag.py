"""OKXRHO signal-layer diagnostic: is OKX funding a different cross-section from Binance funding?
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, json, datetime as dt
from scipy.stats import rankdata
OUT="/workspace/r9okx"; CAP=1788120000
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True)
TS=fe["ts"].astype(np.int64); SY=[str(x) for x in fe["symbols"]]
OK=fe["FE_OKX"]; BC=fe["FE_BINCOLD"]; BW=fe["FE_BINWARM"]
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
PAN=P["f_fund_ema_v1"]; FN=P["f_fund_now"]; IV=P["f_fund_iv"]
T0=int(fe["okx_t0"]); LO=T0+14*86400
rows=np.where((TS>=LO)&(TS<=CAP))[0]
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<10: return np.nan,int(ok.sum())
    return float(np.corrcoef(rankdata(a[ok]),rankdata(b[ok]))[0,1]), int(ok.sum())
res={"n_anchors":len(rows),"lo":dt.datetime.utcfromtimestamp(int(TS[rows[0]])).isoformat()+"Z",
     "hi":dt.datetime.utcfromtimestamp(int(TS[rows[-1]])).isoformat()+"Z"}
for tag,M in (("OKX_vs_PANELwarm",(OK,PAN)),("OKX_vs_BINCOLD",(OK,BC)),("BINCOLD_vs_PANELwarm",(BC,PAN)),("BINWARM_vs_PANELwarm",(BW,PAN))):
    A,Bm=M; rr=[];nn=[]
    for j in rows:
        s,n=sp(A[j],Bm[j]); rr.append(s); nn.append(n)
    rr=np.array(rr,float); nn=np.array(nn)
    g=np.isfinite(rr)
    res[tag]={"anchors_scored":int(g.sum()),"median_xsec_spearman":round(float(np.median(rr[g])),4),
              "p10":round(float(np.percentile(rr[g],10)),4),"p90":round(float(np.percentile(rr[g],90)),4),
              "median_n_names":int(np.median(nn[g]))}
# per-symbol time-series correlation of the two venues' EMA
ps=[]
for k in range(len(SY)):
    a=OK[rows,k]; b=PAN[rows,k]; ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()>200 and np.std(a[ok])>0 and np.std(b[ok])>0: ps.append(float(np.corrcoef(a[ok],b[ok])[0,1]))
ps=np.array(ps)
res["per_symbol_timeseries_corr_OKX_vs_PANEL"]={"n_syms":len(ps),"median":round(float(np.median(ps)),4),
   "p10":round(float(np.percentile(ps,10)),4),"p90":round(float(np.percentile(ps,90)),4)}
print(json.dumps(res,indent=1))
json.dump(res,open(f"{OUT}/RESULT_sigdiag.json","w"),indent=1)
