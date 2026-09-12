"""R7 FUEL-2 part 4: the CONFOUND TEST. The bottom dispersion tercile is 97% 2022-2024 (T0 year counts
500/1205/1251/88/3) because sigma_fund TRENDS. So an unconditional tercile split is nearly an era split.
This re-runs the two decisive statistics WITHIN era: (a) year fixed effects in the regression,
(b) terciles formed INSIDE each calendar year (year-specific breakpoints), then pooled.
Same caliber and window. Reads NO environment variable."""
import numpy as np, json, time, calendar, hashlib, os
R="/workspace/uplift_2026-09-11"; OUT=R+"/r7f2"; OUT19="/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r7f2"; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HI=T(2026,8,30,20)
FU=np.load(OUT19+"/R7_FUEL.npz",allow_pickle=True); A=FU["inc"]
fts=A[:,0].astype(np.int64); sig=A[:,2]
def load(p):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"; Rr=np.asarray(Z[k],float)
    return np.round(Rr[:,ix["ts"]]).astype(np.int64), Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]]
S={"A0_s42":R+"/r3k/arms/A0_PWR230k_s42.npz","A0_s2027":R+"/r3k/arms/A0_PWR230k_s2027.npz",
   "FUND_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz",
   "KING_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz",
   "XIB_LAG50_s42":R+"/r3k/arms/XIB_PWR230k_s42.npz",
   "AMI_AMQ64":R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz",
   "R5_FBSLOPE_NOLAG":R+"/r5_basis/arms/R5C_FBSLOPE_NOLAG_PWR230k.npz",
   "RESID_SHARPE_s42":R+"/r3k/arms/RS_PWR230k_s42.npz"}
S={k:load(v) for k,v in S.items()}
LO=int(S["A0_s42"][0][900])
fm=(fts>=LO)&(fts<=HI)&np.isfinite(sig); F_ts=fts[fm]; F_sig=sig[fm]
def nw(X,r,L=30):
    XtXi=np.linalg.inv(X.T@X); u=X*r[:,None]; Sm=u.T@u
    for l in range(1,L+1):
        w=1-l/(L+1.0); G=u[l:].T@u[:-l]; Sm=Sm+w*(G+G.T)
    return np.sqrt(np.diag(XtXi@Sm@XtXi))
def sh(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def dayboot_sh(y,days,B=2000,k=0):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    order=np.argsort(inv); ys=y[order]; st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(ys))
    idx=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        v=np.concatenate([ys[st[j]:en[j]] for j in idx[b]]); out[b]=v.mean()/v.std(ddof=1)*np.sqrt(APY)
    return out
print("== WITHIN-YEAR screen: terciles formed inside each calendar year, then pooled ==")
print("%-20s %6s | %-34s | %-22s | %-24s"%("candidate","n","within-year T0 Sharpe [CI95]","within-year T2 Sh","beta_log | +yearFE"))
RES={}
for k,(ts,g) in S.items():
    com,ia,ib=np.intersect1d(F_ts,ts,return_indices=True)
    y=g[ib]; s=F_sig[ia]; days=com//86400
    yr=np.array([time.gmtime(int(t)).tm_year for t in com])
    ter=np.full(len(y),-1)
    for Y in sorted(set(yr.tolist())):
        m=yr==Y
        if m.sum()<90: continue
        a,b=np.percentile(s[m],[100/3,200/3])
        ter[m]=np.where(s[m]<=a,0,np.where(s[m]<=b,1,2))
    ls=np.log(s); lz=(ls-ls.mean())/ls.std(ddof=1)
    X=np.column_stack([np.ones(len(y)),lz]); bb=np.linalg.lstsq(X,y,rcond=None)[0]; se=nw(X,y-X@bb)
    YRS=sorted(set(yr.tolist()))
    # within-year standardisation of the gauge + year dummies
    lz2=np.zeros(len(y))
    for Y in YRS:
        m=yr==Y
        lz2[m]=(ls[m]-ls[m].mean())/ls[m].std(ddof=1) if m.sum()>30 else 0.0
    D=np.column_stack([ (yr==Y).astype(float) for Y in YRS ])
    X2=np.column_stack([D,lz2]); b2=np.linalg.lstsq(X2,y,rcond=None)[0]; se2=nw(X2,y-X2@b2)
    r={"n":int(len(y)),"beta_log_plain":round(float(bb[1]),4),"t_plain":round(float(bb[1]/se[1]),3),
       "beta_log_yearFE":round(float(b2[-1]),4),"t_yearFE":round(float(b2[-1]/se2[-1]),3),"by":{}}
    for j in (0,2):
        m=ter==j
        bs=dayboot_sh(y[m],days[m])
        r["by"]["T%d"%j]={"n":int(m.sum()),"sharpe":round(sh(y[m]),4),
                          "ci95":[round(float(np.percentile(bs,2.5)),4),round(float(np.percentile(bs,97.5)),4)],
                          "P_gt0":round(float((bs>0).mean()),4),"sig_med":round(float(np.median(s[m])),3)}
    r["within_year_T0_by_year"]={int(Y):(int(((ter==0)&(yr==Y)).sum()), round(sh(y[(ter==0)&(yr==Y)]),3) if ((ter==0)&(yr==Y)).sum()>30 else None) for Y in YRS}
    RES[k]=r
    print("%-20s %6d | %+7.3f [%+7.3f,%+7.3f] P>0 %.3f | %+7.3f (n=%4d) | %+7.4f (t %+5.2f) | %+7.4f (t %+5.2f)"%(
        k,r["n"],r["by"]["T0"]["sharpe"],r["by"]["T0"]["ci95"][0],r["by"]["T0"]["ci95"][1],r["by"]["T0"]["P_gt0"],
        r["by"]["T2"]["sharpe"],r["by"]["T2"]["n"],r["beta_log_plain"],r["t_plain"],r["beta_log_yearFE"],r["t_yearFE"]))
print("\n== within-year T0 Sharpe, by year ==")
for k,v in RES.items(): print("  %-20s"%k, v["within_year_T0_by_year"])
json.dump({"self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),"rows":RES},
          open(OUT19+"/R7_WITHINYEAR.json","w"),indent=1)
print("WITHINYEAR_DONE")
