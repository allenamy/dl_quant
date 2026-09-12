"""R7 FUEL-2 part 3: uncertainty on the screen's two decisive statistics, the mechanism test for the
basis arm ('same fuel in a different wrapper?'), where today's dispersion actually sits, and the
target spec for a sleeve.  Same caliber/window as r7_screen.py.  Reads NO environment variable."""
import numpy as np, json, time, calendar, hashlib, os
from scipy.stats import rankdata
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
R="/workspace/uplift_2026-09-11"; OUT=R+"/r7f2"; OUT19="/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r7f2"; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HI=T(2026,8,30,20)
FU=np.load(OUT19+"/R7_FUEL.npz",allow_pickle=True); A=FU["inc"]
fts=A[:,0].astype(np.int64); sig=A[:,2]
CAND={
 "A0_s42":R+"/r3k/arms/A0_PWR230k_s42.npz","A0_s2027":R+"/r3k/arms/A0_PWR230k_s2027.npz",
 "FUND_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz",
 "KING_leg":OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz",
 "XIB_LAG50_s42":R+"/r3k/arms/XIB_PWR230k_s42.npz",
 "AMI_AMQ64":R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz",
 "R5_FBSLOPE_NOLAG":R+"/r5_basis/arms/R5C_FBSLOPE_NOLAG_PWR230k.npz",
 "RESID_SHARPE_s42":R+"/r3k/arms/RS_PWR230k_s42.npz",
}
def load(p):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"; Rr=np.asarray(Z[k],float)
    return np.round(Rr[:,ix["ts"]]).astype(np.int64), Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]]
S={k:load(p) for k,p in CAND.items()}
LO=int(S["A0_s42"][0][900])
fm=(fts>=LO)&(fts<=HI); F_ts=fts[fm]; F_sig=sig[fm]
ok=np.isfinite(F_sig); F_ts=F_ts[ok]; F_sig=F_sig[ok]
q33,q67=np.percentile(F_sig,[100/3,200/3])
TODAY={"masked_m1_SEP":9.0565,"unmasked_SEP":8.7012,"frozen_window_med":12.9123,"aug2026":10.0581}
print("== where today's dispersion sits, on the post-warm replayable distribution (n=%d) =="%len(F_sig))
print("   post-warm sigma: median %.3f  mean %.3f  q33 %.3f  q67 %.3f"%(np.median(F_sig),F_sig.mean(),q33,q67))
PCT={k:round(float((F_sig<=v).mean()*100),2) for k,v in TODAY.items()}
for k,v in TODAY.items(): print("   sigma=%7.4f (%s) -> percentile %5.2f%% of post-warm history"%(v,k,PCT[k]))
def sh(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def dayboot(fn, y, days, B=2000, k=0, seed=20260905):
    rng=np.random.default_rng([seed,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    order=np.argsort(inv); ys=y[order] if y.ndim==1 else y[order]
    starts=np.searchsorted(inv[order],np.arange(nd)); ends=np.append(starts[1:],len(order))
    idx=rng.integers(0,nd,size=(B,nd)); out=[]
    for b in range(B):
        sel=np.concatenate([np.arange(starts[j],ends[j]) for j in idx[b]])
        out.append(fn(ys[sel]))
    return np.array(out)
print("\n== DECISIVE STATISTICS with day-block bootstrap CI95 (B=2000, rng[20260905,0]) ==")
print("%-20s %6s | %-26s | %-26s | %-24s"%("candidate","n","T0 (low-sigma) Sharpe","T2 (high-sigma) Sharpe","T2-T0 Sharpe gap"))
FIN={}
for k,(ts,g) in S.items():
    com,ia,ib=np.intersect1d(F_ts,ts,return_indices=True)
    y=g[ib]; s=F_sig[ia]; days=com//86400
    ter=np.where(s<=q33,0,np.where(s<=q67,1,2))
    r={"n":int(len(com))}
    for j,(nm) in ((0,"T0"),(2,"T2")):
        m=ter==j; yy=y[m]; dd=days[m]
        bs=dayboot(lambda v: float(v.mean()/v.std(ddof=1)*np.sqrt(APY)), yy, dd, k=0)
        r[nm]={"n":int(m.sum()),"sharpe":round(sh(yy),4),
               "ci95":[round(float(np.percentile(bs,2.5)),4),round(float(np.percentile(bs,97.5)),4)],
               "P_gt0":round(float((bs>0).mean()),4),"mean_g":round(float(yy.mean()),4)}
    # gap: paired day-block on the stacked series with a tercile flag
    flag=(ter==2).astype(float); m=ter!=1
    Z=np.column_stack([y[m],flag[m]]); dd=days[m]
    def gapfn(V):
        a=V[V[:,1]==0,0]; b=V[V[:,1]==1,0]
        if len(a)<5 or len(b)<5 or a.std(ddof=1)==0 or b.std(ddof=1)==0: return np.nan
        return float(b.mean()/b.std(ddof=1)*np.sqrt(APY) - a.mean()/a.std(ddof=1)*np.sqrt(APY))
    bs=dayboot(gapfn, Z, dd, k=0); bs=bs[np.isfinite(bs)]
    r["gap_T2_minus_T0"]={"point":round(r["T2"]["sharpe"]-r["T0"]["sharpe"],4),
                          "ci95":[round(float(np.percentile(bs,2.5)),4),round(float(np.percentile(bs,97.5)),4)],
                          "P_gt0":round(float((bs>0).mean()),4)}
    FIN[k]=r
    print("%-20s %6d | %+7.3f [%+7.3f,%+7.3f] P>0 %.3f | %+7.3f [%+7.3f,%+7.3f] | %+7.3f [%+7.3f,%+7.3f] P>0 %.3f"%(
        k,r["n"],r["T0"]["sharpe"],r["T0"]["ci95"][0],r["T0"]["ci95"][1],r["T0"]["P_gt0"],
        r["T2"]["sharpe"],r["T2"]["ci95"][0],r["T2"]["ci95"][1],
        r["gap_T2_minus_T0"]["point"],r["gap_T2_minus_T0"]["ci95"][0],r["gap_T2_minus_T0"]["ci95"][1],r["gap_T2_minus_T0"]["P_gt0"]))
# ---------- MECHANISM: is the basis the same fuel in another wrapper? ----------
print("\n== MECHANISM TEST: basis signal vs the fuel gauge ==")
SB=np.load(R+"/r5_basis/dev/sig/R5_FBSLOPE_NOLAG.npz",allow_pickle=True)
print("   basis sig file keys:",sorted(SB.files))
bts=SB["ts"].astype(np.int64); BM=np.asarray(SB["mat"],float)
brow={int(t):i for i,t in enumerate(bts)}
# per-anchor cross-sectional dispersion of the basis SIGNAL on the same anchors
PW=np.load("/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pwts=PW["ts"].astype(np.int64); pwrow={int(t):i for i,t in enumerate(pwts)}
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]
UM=np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"]); lastm=int(UM["ts"].astype(np.int64)[-1])
sb=[]; sbt=[]
for i,t in enumerate(E_ts):
    if not (LO<=int(t)<=HI): continue
    j=pwrow.get(int(t)); r=brow.get(int(t))
    if j is None or r is None: continue
    m=members[i]; kk=umap.get(int(t))
    if kk is not None: m=m[UMM[kk][m]]
    elif int(t)>lastm: m=m[UMM[-1][m]]
    v=BM[r,m]; v=v[np.isfinite(v)]
    if len(v)<=50: continue
    sbt.append(int(t)); sb.append(float(np.std(v)))
sbt=np.array(sbt,np.int64); sb=np.array(sb)
com,ia,ib=np.intersect1d(F_ts,sbt,return_indices=True)
rr=float(np.corrcoef(F_sig[ia],sb[ib])[0,1]); rs=float(np.corrcoef(rankdata(F_sig[ia]),rankdata(sb[ib]))[0,1])
print("   corr( sigma_fund , xsec SD of the basis signal ) : pearson %+0.4f  spearman %+0.4f   (n=%d)"%(rr,rs,len(com)))
# g-level correlation with the fund leg
tf,gf=S["FUND_leg"]; tb,gb=S["R5_FBSLOPE_NOLAG"]
c2,i1,i2=np.intersect1d(tf,tb,return_indices=True)
mm=(c2>=LO)&(c2<=HI)
print("   corr( g_basis , g_FUNDleg )                      : %+0.4f (n=%d)"%(float(np.corrcoef(gb[i2][mm],gf[i1][mm])[0,1]),int(mm.sum())))
ta,ga=S["A0_s42"]; c3,j1,j2=np.intersect1d(ta,tb,return_indices=True); m3=(c3>=LO)&(c3<=HI)
print("   corr( g_basis , g_A0 )                           : %+0.4f (n=%d)"%(float(np.corrcoef(gb[j2][m3],ga[j1][m3])[0,1]),int(m3.sum())))
MECH={"corr_sigmafund_vs_basis_signal_dispersion_pearson":round(rr,4),"spearman":round(rs,4),"n":int(len(com))}
# ---------- TARGET SPEC ----------
print("\n== TARGET SPEC: what a sleeve must be to lift the book to Sharpe 3.0 at today's dispersion ==")
com,ia,ib=np.intersect1d(F_ts,ta,return_indices=True); yA=ga[ib]; sA=F_sig[ia]; dA=com//86400
BANDS={"today +-2  (7.06..11.06)":(TODAY["masked_m1_SEP"]-2,TODAY["masked_m1_SEP"]+2),
       "bottom tercile  (<=%.2f)"%q33:(0.0,q33),
       "full post-warm":(0.0,1e9)}
SPEC={}
for nm,(lo,hi) in BANDS.items():
    m=(sA>=lo)&(sA<=hi); y=yA[m]
    muA=float(y.mean()); sdA=float(np.std(y,ddof=1)); ShA=muA/sdA*np.sqrt(APY)
    ent={"n":int(m.sum()),"A0_mean_g":round(muA,4),"A0_sd_g":round(sdA,4),"A0_sharpe":round(float(ShA),4),"req":{}}
    for a in (0.15,0.20,0.25,0.30,0.40):
        for rho in (0.0,0.15):
            # sleeve sd assumed equal to A0's sd in the band (the sleeves measured above are 0.79-1.09x of it)
            sdS=sdA
            # solve mu_S such that combined Sharpe = 3.0
            sd_c=np.sqrt((1-a)**2*sdA**2 + a**2*sdS**2 + 2*a*(1-a)*rho*sdA*sdS)
            need_mu_c=3.0*sd_c/np.sqrt(APY)
            muS=(need_mu_c-(1-a)*muA)/a
            ent["req"]["a=%.2f,rho=%.2f"%(a,rho)]={"sleeve_mean_g_bps":round(float(muS),4),
                "sleeve_standalone_sharpe":round(float(muS/sdS*np.sqrt(APY)),4),
                "combined_sd_g":round(float(sd_c),4)}
    SPEC[nm]=ent
    print("  band %-28s n=%4d  A0: E[g] %+6.3f  sd %6.3f  Sharpe %+6.3f"%(nm,m.sum(),muA,sdA,ShA))
    for kk,vv in ent["req"].items():
        print("      need %-16s sleeve E[g] %+7.3f bps  => sleeve standalone Sharpe %+6.3f"%(kk,vv["sleeve_mean_g_bps"],vv["sleeve_standalone_sharpe"]))
json.dump({"self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),"env_whitelist":ENV_WL,
           "today_percentiles":PCT,"today_sigma":TODAY,
           "postwarm_sigma":{"n":int(len(F_sig)),"median":round(float(np.median(F_sig)),4),"mean":round(float(F_sig.mean()),4),
                             "q33":round(float(q33),4),"q67":round(float(q67),4)},
           "decisive":FIN,"mechanism":MECH,"spec":SPEC},open(OUT19+"/R7_FINAL.json","w"),indent=1)
print("FINAL_DONE")
