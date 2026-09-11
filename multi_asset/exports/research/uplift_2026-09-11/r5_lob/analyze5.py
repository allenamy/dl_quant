"""R5 NEW-DATA-4 judge. COMMON span = every arm + A0 live, post-warm (E-0911-A: drop first 900 device
anchors), full cycle end 2026-08-10 20:00. g = net_ex/gross_total. UTC-day block bootstrap 2000."""
import numpy as np, calendar, json, glob, os, sys
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
 "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
R="/workspace/uplift_2026-09-11/r5_lob"; OUT=R+"/out"
K=int(sys.argv[1]) if len(sys.argv)>1 else 16
END=T(2026,8,10,20)+1
YR={"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
    "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),END)}
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); Rr=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(Rr[:,0]).astype(np.int64),Rr
tA,RA=load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz")
tA2,RA2=load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz")
gA=RA[:,C["net_ex"]]/RA[:,C["gross_total"]]; gA2=RA2[:,C["net_ex"]]/RA2[:,C["gross_total"]]
POSTWARM=tA[900]
tags=sorted(os.path.basename(p)[:-4] for p in glob.glob(OUT+"/*.npz"))
S={}
for tg in tags:
    t,Rr=load(OUT+"/"+tg+".npz")
    g=np.where(Rr[:,C["gross_total"]]>1e-12,Rr[:,C["net_ex"]]/np.maximum(Rr[:,C["gross_total"]],1e-12),np.nan)
    assert np.isin(t,tA).all(), tg
    RF=np.full((len(tA),Rr.shape[1]),np.nan); gg=np.full(len(tA),np.nan)
    pos=np.searchsorted(tA,t); assert (tA[pos]==t).all(), tg
    RF[pos]=Rr; gg[pos]=g
    S[tg]=(tA,gg,RF)
live=np.ones(len(tA),bool)
for tg in tags:
    if tg.startswith("NULL_"): continue
    live&=np.isfinite(S[tg][1])&(np.nan_to_num(S[tg][2][:,C["gross_total"]],nan=0.0)>1e-9)
M=live&(tA>=POSTWARM)&(tA<END)&np.isfinite(gA)
print("COMMON span n=%d  %s -> %s   (A0 post-warm full-cycle n=%d)"%(
  M.sum(),__import__("time").strftime("%Y-%m-%d %H:%M",__import__("time").gmtime(tA[M][0])),
  __import__("time").strftime("%Y-%m-%d %H:%M",__import__("time").gmtime(tA[M][-1])),
  ((tA>=POSTWARM)&(tA<END)).sum()))
SE=np.sqrt(2190/M.sum()); print("SE(annualised Sharpe) on COMMON = %.4f"%SE)
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
def boot(v,d,seed,B=2000):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    Sm=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=Sm[idx].sum(1)/N[idx].sum(1)
    return (np.percentile(mn,2.5),np.percentile(mn,97.5),
            np.percentile(mn,100*(0.05/K)/2),np.percentile(mn,100*(1-(0.05/K)/2)))
day=tA[M]//86400
AM=S.get("CTL_ORTH_AMIHUD__p")
print()
print("A0_PWR230k s42 on COMMON: g %+0.4f Sharpe %+0.3f | s2027 g %+0.4f Sharpe %+0.3f"%(
  gA[M].mean(),sh(gA[M]),gA2[M].mean(),sh(gA2[M])))
if AM is not None:
    print("CTL_ORTH_AMIHUD__p on COMMON: g %+0.4f Sharpe %+0.3f"%(AM[1][M].mean(),sh(AM[1][M])))
print()
hdr="%-22s %8s %7s %7s %7s | %8s %8s %9s %9s | %7s %7s %7s %7s %7s %7s"%(
  "arm","g","SR","rhoA0","rhoAMI","CI95lo","CI95hi","BONFlo","BONFhi","carryfr","turn","2023","2024","2025","2026")
print(hdr); print("-"*len(hdr))
res={}
for tg in tags:
    t,g,Rr=S[tg]
    v=g[M]; ci=boot(v,day,abs(hash(tg))%9973)
    rA=np.corrcoef(v,gA[M])[0,1]
    rM=np.corrcoef(v,AM[1][M])[0,1] if AM is not None else np.nan
    nx=Rr[M,C["net_ex"]]/Rr[M,C["gross_total"]]; ca=Rr[M,C["carry_ex"]]/Rr[M,C["gross_total"]]
    cf=ca.mean()/nx.mean() if abs(nx.mean())>1e-9 else np.nan
    yrs=[g[(tA>=lo)&(tA<hi)&M].mean() for y,(lo,hi) in YR.items()]
    res[tg]={"g":round(float(v.mean()),4),"SR":round(float(sh(v)),4),"rho_A0":round(float(rA),4),
             "rho_AMI":round(float(rM),4),"ci95":[round(float(ci[0]),4),round(float(ci[1]),4)],
             "bonf":[round(float(ci[2]),4),round(float(ci[3]),4)],"carry_frac":round(float(cf),4),
             "turnover":round(float(Rr[M,C["turnover"]].mean()),5),
             "by_year":{y:round(float(x),4) for y,x in zip(YR,yrs)},"n":int(M.sum())}
    print("%-22s %+8.4f %+7.3f %+7.3f %+7.3f | %+8.4f %+8.4f %+9.4f %+9.4f | %+7.3f %7.4f %+7.3f %+7.3f %+7.3f %+7.3f"%(
      tg,v.mean(),sh(v),rA,rM,ci[0],ci[1],ci[2],ci[3],cf,Rr[M,C["turnover"]].mean(),*yrs))
res["_meta"]={"K":K,"n_common":int(M.sum()),"SE_sharpe":round(float(SE),4),
  "A0_g":round(float(gA[M].mean()),4),"A0_SR":round(float(sh(gA[M])),4),
  "A0_s2027_SR":round(float(sh(gA2[M])),4),
  "AMI_SR":round(float(sh(AM[1][M])),4) if AM is not None else None,
  "span":[int(tA[M][0]),int(tA[M][-1])],"cost":"/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"}
json.dump(res,open(R+"/RESULT_r5_lob.json","w"),indent=1)
