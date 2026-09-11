"""R5/ND1 step 4: the full battery on every arm. Frozen readings (declared in PREREG §6)."""
import numpy as np, json, calendar, glob, os, sys
APY=2190; WARM=900
R="/workspace/uplift_2026-09-11/r5_basis"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1; FROZ_LO=T(2025,3,1)
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec" if "rec" in Z.files else "d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    Rr=Rr[m]; ts=ts[m]
    gt=Rr[:,ix["gross_total"]]
    return {"ts":ts,"g":Rr[:,ix["net_ex"]]/gt,"carry":-Rr[:,ix["carry_ex"]]/gt,
            "pnl":Rr[:,ix["pnl_ex"]]/gt,"cost":Rr[:,ix["cost_ex"]]/gt,
            "turn":Rr[:,ix["turnover"]],"gross":gt,"netlong":np.abs(Rr[:,ix["netlong"]])}
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def bootSR(x,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd)); order=np.argsort(inv,kind="stable"); xs=x[order]
    starts=np.searchsorted(inv[order],np.arange(nd)); ends=np.append(starts[1:],len(xs))
    out=np.empty(B)
    for b in range(B):
        v=np.concatenate([xs[starts[j]:ends[j]] for j in idx[b]])
        out[b]=v.mean()/v.std(ddof=1)*np.sqrt(APY)
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
def bootD(d,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd)); order=np.argsort(inv,kind="stable"); xs=d[order]
    starts=np.searchsorted(inv[order],np.arange(nd)); ends=np.append(starts[1:],len(xs))
    out=np.empty(B)
    for b in range(B):
        v=np.concatenate([xs[starts[j]:ends[j]] for j in idx[b]]); out[b]=v.mean()
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))

def bootDSR(a,s,al,days,k,B=2000):
    """paired bootstrap of  SR((1-al)*A0 + al*sleeve) - SR(A0)  over UTC-day blocks"""
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd)); o=np.argsort(inv,kind="stable")
    A=a[o]; S=s[o]
    st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(A))
    out=np.empty(B)
    for b in range(B):
        sl=idx[b]; ia=np.concatenate([np.arange(st[j],en[j]) for j in sl])
        av=A[ia]; sv=S[ia]; cv=(1-al)*av+al*sv
        out[b]=cv.mean()/cv.std(ddof=1)-av.mean()/av.std(ddof=1)
    out*=np.sqrt(APY)
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))

A0=load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz")
OUT={"A0":{"n":int(len(A0["ts"])),"SR_full":sr(A0["g"]),"SR_frozen":sr(A0["g"][A0["ts"]>=FROZ_LO]),
           "mean_g_bps":float(A0["g"].mean()),"carry_frac_of_net":float(A0["carry"].mean()/A0["g"].mean()),
           "turnover":float(A0["turn"].mean())},"arms":{}}
print("A0",json.dumps(OUT["A0"]),flush=True)
pat=sys.argv[1] if len(sys.argv)>1 else "R5_*"
for p in sorted(glob.glob(R+"/arms/%s.npz"%pat)):
    tag=os.path.basename(p)[:-4]
    S=load(p)
    com,ia,ib=np.intersect1d(A0["ts"],S["ts"],return_indices=True)
    a=A0["g"][ia]; s=S["g"][ib]; days=com//86400; fz=com>=FROZ_LO
    lo,hi=bootSR(s,days,0); lo9,hi9=bootSR(s,days,9)
    d={"n":int(len(com)),"SR_full":sr(s),"SR_ci95_k0":[lo,hi],"SR_ci95_k9":[lo9,hi9],
       "SR_frozen":sr(s[fz]),"rho_to_A0_full":float(np.corrcoef(a,s)[0,1]),
       "rho_to_A0_frozen":float(np.corrcoef(a[fz],s[fz])[0,1]),
       "mean_g_bps":float(s.mean()),"mean_pnl_ex_bps":float(S["pnl"][ib].mean()),
       "carry_frac_of_net":float(S["carry"][ib].mean()/s.mean()),
       "cost_bps":float(S["cost"][ib].mean()),"turnover":float(S["turn"][ib].mean()),
       "mean_abs_netlong":float(S["netlong"][ib].mean()),
       "by_year":{str(y):round(sr(s[(com>=T(y,1,1))&(com<T(y+1,1,1))]),3) for y in range(2022,2027)
                  if ((com>=T(y,1,1))&(com<T(y+1,1,1))).sum()>50}}
    # dose response vs A0 (paired, same span)
    d["dose"]={}
    for al in (0.05,0.10,0.20,0.30,0.50):
        C=(1-al)*a+al*s
        dl,dh=bootD(C-a,days,0)
        s0,s1=bootDSR(a,s,al,days,0); s0b,s1b=bootDSR(a,s,al,days,9)
        d["dose"]["%.2f"%al]={"SR_comb":sr(C),"dSharpe":sr(C)-sr(a),
                              "dSharpe_ci95_k0":[s0,s1],"dSharpe_ci95_k9":[s0b,s1b],
                              "dmean_g_ci95_k0":[dl,dh]}
    OUT["arms"][tag]=d
    print(tag,json.dumps({k:v for k,v in d.items() if k!="dose"}),flush=True)
    for k,v in d["dose"].items(): print("   dose",k,json.dumps(v),flush=True)
json.dump(OUT,open(R+"/BATTERY_%s.json"%pat.replace("*","ALL").replace("/","_"),"w"),indent=1)
print("BATTERY_DONE")
