"""R7 FUEL-2 part 2: gauge-transform robustness, common-sample table, duplicate audit,
regime-cell reconciliation against round 4, the E[g|sigma] curve, and the sleeve target spec.
Same caliber and window as r7_screen.py. Reads NO environment variable."""
import numpy as np, json, time, calendar, hashlib, os
from scipy.stats import rankdata
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
R="/workspace/uplift_2026-09-11"; OUT=R+"/r7f2"; OUT19="/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r7f2"; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HI=T(2026,8,30,20)
FU=np.load(OUT19+"/R7_FUEL.npz",allow_pickle=True); A=FU["inc"]
fts=A[:,0].astype(np.int64); sig=A[:,2]; d24=A[:,3]; mean8=A[:,4]
BURN=2190
def lab1(x):
    L=np.full(len(x),-1,np.int8)
    for i in range(len(x)):
        if i<BURN: continue
        p=x[:i]; p=p[np.isfinite(p)]
        if len(p)<BURN//2 or not np.isfinite(x[i]): continue
        L[i]=1 if x[i]>np.median(p) else 0
    return L
LF=lab1(sig); LD=lab1(d24); LAB=np.full(len(fts),-1,np.int8)
ok=(LF>=0)&(LD>=0); LAB[ok]=LF[ok]*2+LD[ok]; NM={0:"LL",1:"LH",2:"HL",3:"HH"}
CAND={
 "A0_s42":R+"/r3k/arms/A0_PWR230k_s42.npz",
 "A0_s2027":R+"/r3k/arms/A0_PWR230k_s2027.npz",
 "FUND_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz",
 "KING_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz",
 "REV24_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGREV24_PWR_s42.npz",
 "XIB_LAG50_s42":R+"/r3k/arms/XIB_PWR230k_s42.npz",
 "XIB_LAG50_s2027":R+"/r3k/arms/XIB_PWR230k_s2027.npz",
 "AMI_AMQ64":R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz",
 "AMI_AMP":R+"/p6/arms/w10_ablation_series_P6_AMP_PWR_s42.npz",
 "AMI_AMQ32":R+"/p6/arms/w10_ablation_series_P6_AMQ32_PWR_s42.npz",
 "AMI_AMX":R+"/p6/arms/w10_ablation_series_P6_AMX_PWR_s42.npz",
 "AMI_AMR2":R+"/p6/arms/w10_ablation_series_P6_AMR2_PWR_s42.npz",
 "R5_FBSLOPE_NOLAG":R+"/r5_basis/arms/R5C_FBSLOPE_NOLAG_PWR230k.npz",
 "RESID_SHARPE_s42":R+"/r3k/arms/RS_PWR230k_s42.npz",
 "RESID_SHARPE_s2027":R+"/r3k/arms/RS_PWR230k_s2027.npz",
}
def load(p):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"; Rr=np.asarray(Z[k],float)
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); gt=Rr[:,ix["gross_total"]]
    assert np.isfinite(gt).all() and (gt>0).all()
    return ts, Rr[:,ix["net_ex"]]/gt
S={k:load(p) for k,p in CAND.items()}
LO=int(S["A0_s42"][0][900])
# ---------- duplicate audit ----------
print("== DUPLICATE AUDIT (bitwise g) ==")
base=S["AMI_AMQ64"]
for k in ("AMI_AMP","AMI_AMQ32","AMI_AMX","AMI_AMR2"):
    a=base[1]; b=S[k][1]
    same=bool(a.shape==b.shape and np.array_equal(np.isnan(a),np.isnan(b)) and np.array_equal(a[~np.isnan(a)],b[~np.isnan(b)]))
    print(f"  AMI_AMQ64 vs {k}: g bitwise identical = {same}")
# ---------- axis coverage ----------
print("== AXIS COVERAGE in window ==")
COV={}
for k,(ts,g) in S.items():
    m=(ts>=LO)&(ts<=HI); t=ts[m]
    gaps=np.diff(t); big=np.where(gaps>14400)[0]
    COV[k]={"n":int(m.sum()),"first":time.strftime("%Y-%m-%d",time.gmtime(t[0])),"last":time.strftime("%Y-%m-%d",time.gmtime(t[-1])),
            "n_gaps":int(len(big)),"max_gap_days":round(float(gaps.max()/86400),2),
            "gap_spans":[[time.strftime("%Y-%m-%d",time.gmtime(t[i])),time.strftime("%Y-%m-%d",time.gmtime(t[i+1]))] for i in big[:3]]}
    print(f"  {k:20s} n={COV[k]['n']:5d} {COV[k]['first']}..{COV[k]['last']} gaps={COV[k]['n_gaps']} maxgap={COV[k]['max_gap_days']}d {COV[k]['gap_spans']}")
# ---------- common sample ----------
common=None
for k,(ts,g) in S.items():
    m=(ts>=LO)&(ts<=HI); t=ts[m]
    common=t if common is None else np.intersect1d(common,t)
print("COMMON SAMPLE n =",len(common), time.strftime("%Y-%m-%d",time.gmtime(common[0])),"..",time.strftime("%Y-%m-%d",time.gmtime(common[-1])))
fmap={int(t):i for i,t in enumerate(fts)}
fi=np.array([fmap[int(t)] for t in common])
sg=sig[fi]; lb=LAB[fi]; days=common//86400
assert np.isfinite(sg).all()
# gauge transforms
def z(x): return (x-x.mean())/x.std(ddof=1)
G={"level":z(sg),"log":z(np.log(sg)),"rank":z(rankdata(sg)/len(sg))}
dsig=np.full(len(fts),np.nan); dsig[1:]=np.log(sig[1:])-np.log(sig[:-1])
dl=dsig[fi]; assert np.isfinite(dl).all(); dlz=z(dl)
q33,q67=np.percentile(sg,[100/3,200/3]); TER=np.where(sg<=q33,0,np.where(sg<=q67,1,2))
print("common-sample tercile breaks: %.3f / %.3f  counts %s"%(q33,q67,[int((TER==k).sum()) for k in (0,1,2)]))
def nw(X,r,L=30):
    XtXi=np.linalg.inv(X.T@X); u=X*r[:,None]; Sm=u.T@u
    for l in range(1,L+1):
        w=1-l/(L+1.0); Gm=u[l:].T@u[:-l]; Sm=Sm+w*(Gm+Gm.T)
    return np.sqrt(np.diag(XtXi@Sm@XtXi))
def sh(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>2 else float("nan")
gmap={k:dict(zip(ts.tolist(),g.tolist())) for k,(ts,g) in S.items()}
GC={k:np.array([gmap[k][int(t)] for t in common]) for k in S}
refA=GC["A0_s42"]
ROWS={}
print("\n== COMMON-SAMPLE SCREEN (n=%d) =="%len(common))
hdr="%-20s %7s %8s %8s %8s | %8s %8s %8s | %7s %7s %7s | %7s"%("candidate","Sh","b_lvl","b_log","b_rank","T0 Sh","T1 Sh","T2 Sh","rho all","rho T0","rho T2","t_log")
print(hdr); print("-"*len(hdr))
for k in S:
    y=GC[k]; sd=float(np.std(y,ddof=1)); row={"n":len(y),"sharpe":round(sh(y),4),"mean_g":round(float(y.mean()),4),"sd_g":round(sd,4)}
    for gn,gv in G.items():
        X=np.column_stack([np.ones(len(y)),gv,dlz]); b=np.linalg.lstsq(X,y,rcond=None)[0]
        se=nw(X,y-X@b)
        row["beta_"+gn]=round(float(b[1]),4); row["se_"+gn]=round(float(se[1]),4); row["t_"+gn]=round(float(b[1]/se[1]),3)
        row["betaN_"+gn]=round(float(b[1]/sd),4)
        if gn=="log":
            row["beta_dlog"]=round(float(b[2]),4); row["t_dlog"]=round(float(b[2]/se[2]),3)
            row["R2_log"]=round(float(1-np.var(y-X@b)/np.var(y)),5)
    row["tercile"]={}
    for j in (0,1,2):
        m=TER==j
        row["tercile"]["T%d"%j]={"n":int(m.sum()),"sharpe":round(sh(y[m]),4),"mean_g":round(float(y[m].mean()),4),
                                 "sd_g":round(float(np.std(y[m],ddof=1)),4),"sig_med":round(float(np.median(sg[m])),3),
                                 "rho_A0":round(float(np.corrcoef(y[m],refA[m])[0,1]),4)}
    row["rho_A0_all"]=round(float(np.corrcoef(y,refA)[0,1]),4)
    row["regime"]={}
    for j in (0,1,2,3):
        m=lb==j
        if m.sum()>30:
            row["regime"][NM[j]]={"n":int(m.sum()),"sharpe":round(sh(y[m]),4),"rho_A0":round(float(np.corrcoef(y[m],refA[m])[0,1]),4)}
    row["by_year"]={}
    for yr in range(2022,2027):
        m=(common>=T(yr,1,1))&(common<T(yr+1,1,1))
        if m.sum()>30: row["by_year"][str(yr)]={"n":int(m.sum()),"sharpe":round(sh(y[m]),3),"mean_g":round(float(y[m].mean()),4)}
    ROWS[k]=row
    print("%-20s %7.3f %+8.4f %+8.4f %+8.4f | %8.3f %8.3f %8.3f | %+7.4f %+7.4f %+7.4f | %+7.2f"%(
        k,row["sharpe"],row["beta_level"],row["beta_log"],row["beta_rank"],
        row["tercile"]["T0"]["sharpe"],row["tercile"]["T1"]["sharpe"],row["tercile"]["T2"]["sharpe"],
        row["rho_A0_all"],row["tercile"]["T0"]["rho_A0"],row["tercile"]["T2"]["rho_A0"],row["t_log"]))
print("\n== REGIME-CELL rho(A0, cand)  [round-4 reconciliation] ==")
for k in ("AMI_AMQ64","R5_FBSLOPE_NOLAG","XIB_LAG50_s42","FUND_leg","KING_leg"):
    print("  %-20s"%k, {c:(v["rho_A0"],v["n"]) for c,v in ROWS[k]["regime"].items()})
# ---------- E[g|sigma] curve for A0 ----------
print("\n== E[g | sigma_fund] : A0_s42, decile bins ==")
dec=np.percentile(sg,np.arange(0,101,10)); CURVE=[]
for i in range(10):
    m=(sg>=dec[i])&(sg<dec[i+1] if i<9 else sg<=dec[10])
    y=refA[m]
    # day-block SE of the mean
    ud,inv=np.unique(days[m],return_inverse=True)
    dm=np.array([y[inv==j].mean() for j in range(len(ud))])
    se=float(np.std(dm,ddof=1)/np.sqrt(len(ud)))
    CURVE.append({"bin":i+1,"sig_lo":round(float(dec[i]),3),"sig_hi":round(float(dec[i+1]),3),
                  "sig_med":round(float(np.median(sg[m])),3),"n":int(m.sum()),
                  "mean_g":round(float(y.mean()),4),"se_day":round(se,4),
                  "t":round(float(y.mean()/se),2),"sharpe":round(sh(y),3)})
    print("  d%-2d sig [%7.3f,%7.3f] med %7.3f n=%4d  E[g]=%+7.4f +/- %6.4f (t %+5.2f)  Sh %+6.3f"%(
        i+1,dec[i],dec[i+1],CURVE[-1]["sig_med"],m.sum(),y.mean(),se,CURVE[-1]["t"],CURVE[-1]["sharpe"]))
# band around today's sigma
TODAY_MASKED=9.0565; TODAY_UNMASKED=8.7012
BANDS={}
for nm,(lo,hi) in {"sig 7..11 (today's neighbourhood)":(7.0,11.0),"sig 8..10":(8.0,10.0),"sig<=q33":(0,q33),"sig>q67":(q67,1e9)}.items():
    m=(sg>=lo)&(sg<=hi); y=refA[m]
    ud,inv=np.unique(days[m],return_inverse=True); dm=np.array([y[inv==j].mean() for j in range(len(ud))])
    BANDS[nm]={"n":int(m.sum()),"mean_g":round(float(y.mean()),4),"sd_g":round(float(np.std(y,ddof=1)),4),
               "se_day":round(float(np.std(dm,ddof=1)/np.sqrt(len(ud))),4),"sharpe":round(sh(y),4)}
    print("  A0 in %-32s n=%4d E[g]=%+7.4f +/-%6.4f sd=%6.3f Sharpe %+6.3f"%(nm,m.sum(),y.mean(),BANDS[nm]["se_day"],BANDS[nm]["sd_g"],BANDS[nm]["sharpe"]))
json.dump({"self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),"env_whitelist":ENV_WL,
           "window":[time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(LO)),time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(HI))],
           "coverage":COV,"common_n":int(len(common)),"tercile_breaks":[round(float(q33),4),round(float(q67),4)],
           "rows":ROWS,"curve_A0":CURVE,"bands_A0":BANDS,
           "today_sigma":{"masked_m1":TODAY_MASKED,"unmasked":TODAY_UNMASKED}},
          open(OUT19+"/R7_SCREEN2.json","w"),indent=1)
print("SCREEN2_DONE")
