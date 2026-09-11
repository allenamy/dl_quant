"""R8 step 0-bis: reproduce the round-5 INCUMBENT (the return-series blend) with round-5 battery.py math
VERBATIM, to prove my ruler is round-5 ruler.  This is NOT an in-book form: it is
  C = (1-a)*g_A0 + a*g_sleeve   -> two separate books combined at the g layer, each paying its own turnover."""
import numpy as np, json, calendar
APY=2190; WARM=900
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec" if "rec" in Z.files else "d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    Rr=Rr[m]; ts=ts[m]; gt=Rr[:,ix["gross_total"]]
    return {"ts":ts,"g":Rr[:,ix["net_ex"]]/gt,"pnl":Rr[:,ix["pnl_ex"]]/gt,"cost":Rr[:,ix["cost_ex"]]/gt,
            "carry":-Rr[:,ix["carry_ex"]]/gt,"turn":Rr[:,ix["turnover"]]}
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def bootDSR(a,s,al,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd)); o=np.argsort(inv,kind="stable"); A=a[o]; S=s[o]
    st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(A)); out=np.empty(B)
    for b in range(B):
        ia=np.concatenate([np.arange(st[j],en[j]) for j in idx[b]])
        av=A[ia]; sv=S[ia]; cv=(1-al)*av+al*sv
        out[b]=cv.mean()/cv.std(ddof=1)-av.mean()/av.std(ddof=1)
    out*=np.sqrt(APY); return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
A0=load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz")
S=load("/workspace/uplift_2026-09-11/r5_basis/arms/R5_FBSLOPE_NOLAG.npz")
com,ia,ib=np.intersect1d(A0["ts"],S["ts"],return_indices=True)
a=A0["g"][ia]; s=S["g"][ib]; days=com//86400
OUT={"n_intersect":int(len(com)),"A0_SR_on_intersect":sr(a),"A0_SR_full_own_span":sr(A0["g"]),
     "sleeve_SR":sr(s),"sleeve_mean_g":float(s.mean()),"sleeve_pnl_ex":float(S["pnl"][ib].mean()),
     "sleeve_cost":float(S["cost"][ib].mean()),"sleeve_turn":float(S["turn"][ib].mean()),
     "A0_turn":float(A0["turn"][ia].mean()),"rho":float(np.corrcoef(a,s)[0,1]),"dose":{}}
OUT["sleeve_cost_surv_frac"]=1-OUT["sleeve_cost"]/OUT["sleeve_pnl_ex"]
for al in (0.05,0.10,0.20,0.30,0.50):
    C=(1-al)*a+al*s
    k0=bootDSR(a,s,al,days,0); k9=bootDSR(a,s,al,days,9)
    OUT["dose"]["%.2f"%al]={"SR_comb":sr(C),"dSharpe":sr(C)-sr(a),"ci95_k0":list(k0),"ci95_k9":list(k9),
        "dg":float(C.mean()-a.mean()),
        "blend_turn":float((1-al)*A0["turn"][ia].mean()+al*S["turn"][ib].mean()),
        "dturn_frac":float(((1-al)*A0["turn"][ia].mean()+al*S["turn"][ib].mean())/A0["turn"][ia].mean()-1)}
print(json.dumps(OUT,indent=1))
json.dump(OUT,open("/workspace/uplift_2026-09-11/r8_inbook/REPRO_R5_INCUMBENT.json","w"),indent=1)
