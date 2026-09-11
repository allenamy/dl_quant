"""R5/ND1: paired comparison ARM vs each turnover-matched null. Reports BOTH pnl_ex (gross) and g (net),
plus turnover, so the reader can see the null really is turnover-matched."""
import numpy as np, json, calendar, glob, os, sys
APY=2190; WARM=900; R="/workspace/uplift_2026-09-11/r5_basis"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1
def load(p):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec" if "rec" in Z.files else "d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI; Rr=Rr[m]; ts=ts[m]
    gt=Rr[:,ix["gross_total"]]
    return ts,Rr[:,ix["net_ex"]]/gt,Rr[:,ix["pnl_ex"]]/gt,Rr[:,ix["turnover"]]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def bootD(d,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    idx=rng.integers(0,nd,size=(B,nd)); o=np.argsort(inv,kind="stable"); xs=d[o]
    st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(xs))
    out=np.empty(B)
    for b in range(B): out[b]=np.concatenate([xs[st[j]:en[j]] for j in idx[b]]).mean()
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
ARM=sys.argv[1]
ta,ga,pa,tua=load(R+"/arms/R5_%s.npz"%ARM)
OUT={"arm":ARM,"arm_SR_g":sr(ga),"arm_mean_g":float(ga.mean()),"arm_mean_pnl_ex":float(pa.mean()),
     "arm_turnover":float(tua.mean()),"nulls":{}}
allbeat=True
for p in sorted(glob.glob(R+"/arms/NULL_%s_*.npz"%ARM)):
    tag=os.path.basename(p)[:-4]
    tb,gb,pb,tub=load(p)
    com,ia,ib=np.intersect1d(ta,tb,return_indices=True); days=com//86400
    dg=ga[ia]-gb[ib]; dp=pa[ia]-pb[ib]
    lo,hi=bootD(dg,days,0); lo9,hi9=bootD(dg,days,9)
    plo,phi=bootD(dp,days,0)
    beat=bool(lo>0 and lo9>0)
    allbeat&=beat
    OUT["nulls"][tag]={"n":int(len(com)),"null_SR_g":sr(gb[ib]),"null_mean_g":float(gb[ib].mean()),
      "null_mean_pnl_ex":float(pb[ib].mean()),"null_turnover":float(tub[ib].mean()),
      "turnover_ratio_null_over_arm":round(float(tub[ib].mean()/tua[ia].mean()),4),
      "d_mean_g":float(dg.mean()),"d_g_ci95_k0":[lo,hi],"d_g_ci95_k9":[lo9,hi9],
      "d_mean_pnl_ex":float(dp.mean()),"d_pnl_ex_ci95_k0":[plo,phi],"BEATS":beat}
    print(tag,json.dumps(OUT["nulls"][tag]),flush=True)
OUT["BEATS_ALL"]=bool(allbeat)
json.dump(OUT,open(R+"/NULLS_%s.json"%ARM,"w"),indent=1)
print("BEATS_ALL",allbeat)
