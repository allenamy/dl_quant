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
S={"A0":load(R+"/r3k/arms/A0_PWR230k_s42.npz"),
   "BASIS":load(R+"/r5_basis/arms/R5C_FBSLOPE_NOLAG_PWR230k.npz"),
   "KING":load(OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz"),
   "AMI":load(R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz"),
   "RS":load(R+"/r3k/arms/RS_PWR230k_s42.npz")}
LO=int(S["A0"][0][900])
fm=(fts>=LO)&(fts<=HI)&np.isfinite(sig); F_ts=fts[fm]; F_sig=sig[fm]
q33,q67=np.percentile(F_sig,[100/3,200/3])
yr=np.array([time.gmtime(int(t)).tm_year for t in F_ts])
ter=np.where(F_sig<=q33,0,np.where(F_sig<=q67,1,2))
print("== year composition of each dispersion tercile (post-warm window) ==")
for j in (0,1,2):
    m=ter==j
    print("  T%d (n=%4d, sig med %6.2f): "%(j,m.sum(),np.median(F_sig[m])), {int(y):int(((yr==y)&m).sum()) for y in sorted(set(yr))})
def sh(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
print("\n== BOTTOM-TERCILE Sharpe, by year (is T0 edge a 2022-23 artifact?) ==")
for k,(ts,g) in S.items():
    com,ia,ib=np.intersect1d(F_ts,ts,return_indices=True)
    y=g[ib]; s=F_sig[ia]; yy=np.array([time.gmtime(int(t)).tm_year for t in com]); tt=np.where(s<=q33,0,np.where(s<=q67,1,2))
    row={}
    for Y in sorted(set(yy.tolist())):
        m=(tt==0)&(yy==Y)
        row[Y]=(int(m.sum()), round(sh(y[m]),3) if m.sum()>30 else None)
    print("  %-6s T0 by year:"%k, row)
print("\n== combined-book target table: required SLEEVE standalone Sharpe in each band ==")
ta,ga=S["A0"]; com,ia,ib=np.intersect1d(F_ts,ta,return_indices=True); yA=ga[ib]; sA=F_sig[ia]
BAND={"today (7.06..11.06)":(7.0565,11.0565),"bottom tercile (<=%.2f)"%q33:(0.0,q33),"full post-warm":(0.0,1e9)}
TAB={}
for nm,(lo,hi) in BAND.items():
    m=(sA>=lo)&(sA<=hi); v=yA[m]; muA=float(v.mean()); sdA=float(np.std(v,ddof=1)); ShA=muA/sdA*np.sqrt(APY)
    TAB[nm]={"n":int(m.sum()),"A0_sharpe":round(float(ShA),3),"A0_mean_g":round(muA,4),"A0_sd_g":round(sdA,3),"req":{}}
    print("  band %-28s n=%4d  A0 Sharpe %+6.3f"%(nm,m.sum(),ShA))
    for tgt in (2.0,2.5,3.0):
        line=[]
        for a in (0.20,0.25,0.30,0.40):
            sdS=sdA; rho=0.0
            sd_c=np.sqrt((1-a)**2*sdA**2+a**2*sdS**2+2*a*(1-a)*rho*sdA*sdS)
            muS=(tgt*sd_c/np.sqrt(APY)-(1-a)*muA)/a
            ShS=muS/sdS*np.sqrt(APY)
            line.append("a=%.2f:%+6.2f"%(a,ShS)); TAB[nm]["req"]["tgt%.1f_a%.2f"%(tgt,a)]=round(float(ShS),3)
        print("     combined target %.1f  ->  required sleeve standalone Sharpe (rho=0):  "%tgt+"  ".join(line))
json.dump({"tercile_year_composition":{("T%d"%j):{int(y):int(((yr==y)&(ter==j)).sum()) for y in sorted(set(yr))} for j in (0,1,2)},
           "target_table":TAB},open(OUT19+"/R7_SPEC.json","w"),indent=1)
print("SPEC_DONE")
