"""P6 step 4: the HONEST uplift. Paper combination of the live-shape book (A0, fitted cost K=0.17, G=230k)
with the standalone Amihud sleeve, at the g = net_ex/gross_total caliber.  This is a TWO-PORTFOLIO
CALCULATION, not a run book: it assumes the combined book splits the SAME total gross a/(1-a) between the
two sleeves and that cost is the gross-weighted average of the two stand-alone costs.  Netting between the
sleeves can only REDUCE turnover at fixed total gross, so the cost term here is an upper bound; the
alpha term is exact only if the two books do not fight each other inside the neutrality band."""
import numpy as np, json, calendar, os
APY=2190; WARM=900
P6="/workspace/uplift_2026-09-11/p6/arms"; R3K="/workspace/uplift_2026-09-11/r3k/arms"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1; FROZ_LO=T(2025,3,1)
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec" if "rec" in Z.files else "d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    return ts[m], (Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]])[m]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def bootSR(x,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd))
    out=np.empty(B)
    order=np.argsort(inv); xs=x[order]; starts=np.searchsorted(inv[order],np.arange(nd)); ends=np.append(starts[1:],len(xs))
    for b in range(B):
        v=np.concatenate([xs[starts[j]:ends[j]] for j in idx[b]])
        out[b]=v.mean()/v.std(ddof=1)*np.sqrt(APY)
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
OUT={}
for seed in ("42","2027"):
    ta,ga=load("%s/A0_PWR230k_s%s.npz"%(R3K,seed))
    tb,gb=load("%s/w10_ablation_series_P6_AMQ64_PWR_s%s.npz"%(P6,seed))
    tc,gc=load("%s/w10_ablation_series_P6_AMQ64_PWR400_s%s.npz"%(P6,seed))
    com,ia,ib=np.intersect1d(ta,tb,return_indices=True)
    _,ia2,ic=np.intersect1d(ta,tc,return_indices=True)
    A=ga[ia]; S=gb[ib]; S4=gc[ic]; days=com//86400
    fz=com>=FROZ_LO
    rho=float(np.corrcoef(A,S)[0,1])
    D={"n":int(len(com)),"rho_A0_sleeve":rho,"SR_A0":sr(A),"SR_sleeve":sr(S),"SR_sleeve_topn400":sr(S4),
       "SR_A0_frozen":sr(A[fz]),"SR_sleeve_frozen":sr(S[fz]),"rho_frozen":float(np.corrcoef(A[fz],S[fz])[0,1]),
       "alloc":{}}
    for a in (0.10,0.20,0.25,0.30,0.35,0.40,0.50):
        C=(1-a)*A+a*S
        lo,hi=bootSR(C,days,0)
        D["alloc"]["%.2f"%a]={"SR_full":sr(C),"SR_ci95_k0":[lo,hi],"SR_frozen":sr(C[fz]),
                              "SR_gain_vs_A0":sr(C)-sr(A),
                              "by_year":{str(y):round(sr(C[(com>=T(y,1,1))&(com<T(y+1,1,1))]),3)
                                         for y in range(2023,2027)}}
    # A0 own CI for reference
    lo,hi=bootSR(A,days,0); D["SR_A0_ci95_k0"]=[lo,hi]
    lo,hi=bootSR(S,days,0); D["SR_sleeve_ci95_k0"]=[lo,hi]
    D["by_year_A0"]={str(y):round(sr(A[(com>=T(y,1,1))&(com<T(y+1,1,1))]),3) for y in range(2022,2027)}
    D["by_year_sleeve"]={str(y):round(sr(S[(com>=T(y,1,1))&(com<T(y+1,1,1))]),3) for y in range(2022,2027)}
    OUT["s"+seed]=D
    print("seed",seed,json.dumps({k:v for k,v in D.items() if k!="alloc"},indent=1),flush=True)
    for a,v in D["alloc"].items(): print("  alloc",a,json.dumps(v),flush=True)
json.dump(OUT,open("/workspace/uplift_2026-09-11/p6/P6_COMBO.json","w"),indent=1)
print("COMBO_DONE")
