"""R7 FUEL-2: the DISPERSION-DEPENDENCE SCREEN.
For every candidate's per-anchor g = net_ex/gross_total [bps per unit gross], regress on the FUEL GAUGE
sig_fund (1e4 * xsec SD of the 8h-equivalent funding rate over the CRYPTO-m1 member set, definition
verbatim from r6j1_regime.py) and on its change; report the dispersion beta, the bottom-vs-top tercile
Sharpe, and rho to A0 conditional on the tercile.  DESCRIPTIVE ONLY: conditioning on sig_fund is a
statement about E[g | state], not a rule -- exposure control is refuted and is not re-opened here.

CALIBER: v4 chain, g = net_ex/gross_total, CAL=log, fitted cost costb_PWR_G230k.json (sha 295b4e7b462373e4).
WINDOW: post-warm (E-0911-A: A0's first LOOK=900 anchors dropped, and the SAME TIME boundary applied to
every candidate so the rows are comparable) .. 2026-08-30 20:00Z (E-0911-D coverage ceiling for PHI>0 arms,
which also excludes the five E-0911-B funding-blind 08-31 anchors).
ENV: this device reads NO environment variable.
"""
import numpy as np, json, time, calendar, hashlib, os
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
R="/workspace/uplift_2026-09-11"
OUT=R+"/r7f2"; OUT19="/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r7f2"
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HI = T(2026,8,30,20)   # inclusive, E-0911-D

FU=np.load(OUT19+"/R7_FUEL.npz",allow_pickle=True)
Ainc=FU["inc"]           # ts, n_members, sig_fund, disp24, mean8h, frac_neg, n_fin
fts=Ainc[:,0].astype(np.int64); sig=Ainc[:,2]; d24=Ainc[:,3]; mean8=Ainc[:,4]

# --- regime labels, code verbatim from r6j1_regime.py (expanding median, BURN=2190) ---
BURN=2190
def lab1(x):
    L=np.full(len(x),-1,np.int8)
    for i in range(len(x)):
        if i<BURN: continue
        p=x[:i]; p=p[np.isfinite(p)]
        if len(p)<BURN//2 or not np.isfinite(x[i]): continue
        L[i]=1 if x[i]>np.median(p) else 0
    return L
LF=lab1(sig); LD=lab1(d24)
LAB=np.full(len(fts),-1,np.int8); okl=(LF>=0)&(LD>=0); LAB[okl]=LF[okl]*2+LD[okl]
NM={-1:"UNLAB",0:"LL",1:"LH",2:"HL",3:"HH"}

CAND={
 "A0                (in-service book)": [R+"/r3k/arms/A0_PWR230k_s42.npz",      R+"/r3k/arms/A0_PWR230k_s2027.npz"],
 "FUND leg          (standalone book)": [OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz"],
 "KING leg          (standalone book)": [OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz"],
 "REV24 leg         (retired, info)":   [OUT+"/dev/probe_artifacts/w10_ablation_series_R7_LEGREV24_PWR_s42.npz"],
 "XIB_LAG50":                           [R+"/r3k/arms/XIB_PWR230k_s42.npz",     R+"/r3k/arms/XIB_PWR230k_s2027.npz"],
 "AMI sleeve (AMQ64)":                  [R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s42.npz", R+"/p6/arms/w10_ablation_series_P6_AMQ64_PWR_s2027.npz"],
 "AMI variant AMX":                     [R+"/p6/arms/w10_ablation_series_P6_AMX_PWR_s42.npz",  R+"/p6/arms/w10_ablation_series_P6_AMX_PWR_s2027.npz"],
 "AMI variant AMP":                     [R+"/p6/arms/w10_ablation_series_P6_AMP_PWR_s42.npz",  R+"/p6/arms/w10_ablation_series_P6_AMP_PWR_s2027.npz"],
 "AMI variant AMR2":                    [R+"/p6/arms/w10_ablation_series_P6_AMR2_PWR_s42.npz", R+"/p6/arms/w10_ablation_series_P6_AMR2_PWR_s2027.npz"],
 "AMI variant AMQ32":                   [R+"/p6/arms/w10_ablation_series_P6_AMQ32_PWR_s42.npz",R+"/p6/arms/w10_ablation_series_P6_AMQ32_PWR_s2027.npz"],
 "R5_FBSLOPE_NOLAG  (basis)":           [R+"/r5_basis/arms/R5C_FBSLOPE_NOLAG_PWR230k.npz"],
 "RESID_SHARPE (dead axis)":            [R+"/r3k/arms/RS_PWR230k_s42.npz",      R+"/r3k/arms/RS_PWR230k_s2027.npz"],
}
def load(path):
    Z=np.load(path,allow_pickle=True)
    cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    key="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    Rr=np.asarray(Z[key],float)
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64)
    gt=Rr[:,ix["gross_total"]]
    assert np.isfinite(gt).all() and (gt>0).all(), path+": gross_total not finite/positive"
    g=Rr[:,ix["net_ex"]]/gt
    cfg=json.loads(str(Z["config_json"]))
    return ts,g,cfg

# post-warm boundary from A0 row 900 (E-0911-A)
tsA0,gA0,cfgA0=load(CAND["A0                (in-service book)"][0])
LO=int(tsA0[900])
print("post-warm start (A0 row 900):", time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(LO)),
      " cut:", time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(HI)))

fm=(fts>=LO)&(fts<=HI)
F_ts=fts[fm]; F_sig=sig[fm]; F_lab=LAB[fm]; F_d24=d24[fm]; F_mean8=mean8[fm]
# change of the gauge on the fuel axis (consecutive anchors), computed BEFORE the window cut
dsig=np.full(len(fts),np.nan); dsig[1:]=sig[1:]-sig[:-1]
dsig30=np.full(len(fts),np.nan); dsig30[30:]=sig[30:]-sig[:-30]
F_ds=dsig[fm]; F_ds30=dsig30[fm]
good=np.isfinite(F_sig)&np.isfinite(F_ds)&np.isfinite(F_ds30)
F_ts=F_ts[good]; F_sig=F_sig[good]; F_lab=F_lab[good]; F_ds=F_ds[good]; F_ds30=F_ds30[good]; F_d24=F_d24[good]; F_mean8=F_mean8[good]
print("fuel anchors in window:", len(F_ts), " sig_fund mean/med:", round(F_sig.mean(),3), round(float(np.median(F_sig)),3))

# tercile breakpoints: fixed once, on the fuel axis in the window (identical for every candidate)
q33,q67=np.percentile(F_sig,[100/3,200/3])
TER=np.where(F_sig<=q33,0,np.where(F_sig<=q67,1,2))
print("tercile breakpoints sig_fund: <=%.3f | <=%.3f | >"%(q33,q67),
      "counts", [int((TER==k).sum()) for k in (0,1,2)])

def nw_se(X,resid,L):
    n,k=X.shape
    XtXi=np.linalg.inv(X.T@X)
    u=X*resid[:,None]
    S=u.T@u
    for l in range(1,L+1):
        w=1.0-l/(L+1.0)
        G=u[l:].T@u[:-l]
        S=S+w*(G+G.T)
    V=XtXi@S@XtXi
    return np.sqrt(np.diag(V))

def sharpe(x):
    return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>2 and np.std(x,ddof=1)>0 else float("nan")

def dayblock_boot_beta(X,y,days,B=2000,seed=20260905,k=0):
    rng=np.random.default_rng([seed,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    order=np.argsort(inv); Xs=X[order]; ys=y[order]
    starts=np.searchsorted(inv[order],np.arange(nd)); ends=np.append(starts[1:],len(ys))
    out=np.empty((B,X.shape[1]))
    idx=rng.integers(0,nd,size=(B,nd))
    for b in range(B):
        sel=np.concatenate([np.arange(starts[j],ends[j]) for j in idx[b]])
        Xb=Xs[sel]; yb=ys[sel]
        try: out[b]=np.linalg.lstsq(Xb,yb,rcond=None)[0]
        except Exception: out[b]=np.nan
    return out

ROWS={}
# align A0 (seed 42) on the fuel axis once, it is the correlation reference
def align(ts,g):
    com,ia,ib=np.intersect1d(F_ts,ts,return_indices=True)
    return com,ia,g[ib]
comA,iaA,gA = align(tsA0,gA0)
A0map=dict(zip(comA.tolist(),gA.tolist()))

for name,paths in CAND.items():
    ROWS[name]=[]
    for p in paths:
        ts,g,cfg=load(p)
        com,ia,gg=align(ts,g)
        s=F_sig[ia]; ds=F_ds[ia]; ds30=F_ds30[ia]; lab=F_lab[ia]; ter=TER[ia]
        mu,sd=s.mean(),s.std(ddof=1)
        sz=(s-mu)/sd; dsz=(ds-ds.mean())/ds.std(ddof=1)
        X=np.column_stack([np.ones(len(sz)),sz,dsz])
        b,_,_,_=np.linalg.lstsq(X,gg,rcond=None)
        res=gg-X@b
        se=nw_se(X,res,30)
        r2=1.0-res.var()/gg.var()
        # univariate beta on level only
        Xu=np.column_stack([np.ones(len(sz)),sz])
        bu,_,_,_=np.linalg.lstsq(Xu,gg,rcond=None); resu=gg-Xu@bu; seu=nw_se(Xu,resu,30)
        days=com//86400
        BB=dayblock_boot_beta(X,gg,days,k=0)
        sd_g=float(np.std(gg,ddof=1))
        rec={"path":p,"n":int(len(com)),
             "sharpe_full":round(sharpe(gg),4),"mean_g_bps":round(float(gg.mean()),4),"sd_g_bps":round(sd_g,4),
             "beta_sig_bps_per_SD":round(float(b[1]),4),"se_nw30":round(float(se[1]),4),
             "t_nw30":round(float(b[1]/se[1]),3),
             "beta_boot_ci95":[round(float(np.percentile(BB[:,1],2.5)),4),round(float(np.percentile(BB[:,1],97.5)),4)],
             "beta_dsig_bps_per_SD":round(float(b[2]),4),"se_dsig_nw30":round(float(se[2]),4),
             "t_dsig":round(float(b[2]/se[2]),3),
             "beta_norm_ownSD_per_SD":round(float(b[1]/sd_g),4),
             "beta_univariate_bps_per_SD":round(float(bu[1]),4),"t_univariate":round(float(bu[1]/seu[1]),3),
             "R2":round(float(r2),5),
             "sig_mu":round(float(mu),4),"sig_sd":round(float(sd),4),
             "tercile":{},"rho_A0":{},"regime":{}}
        for k in (0,1,2):
            m=ter==k
            rec["tercile"]["T%d"%k]={"n":int(m.sum()),"sharpe":round(sharpe(gg[m]),4),
                                     "mean_g_bps":round(float(gg[m].mean()),4),
                                     "sig_med":round(float(np.median(s[m])),3)}
        ref=np.array([A0map.get(int(t),np.nan) for t in com])
        okr=np.isfinite(ref)
        rec["rho_A0"]["all"]=round(float(np.corrcoef(gg[okr],ref[okr])[0,1]),4) if okr.sum()>10 else None
        for k in (0,1,2):
            m=(ter==k)&okr
            rec["rho_A0"]["T%d"%k]=round(float(np.corrcoef(gg[m],ref[m])[0,1]),4) if m.sum()>10 else None
        for k in (0,1,2,3):
            m=lab==k
            if m.sum()>10:
                mm=m&okr
                rec["regime"][NM[k]]={"n":int(m.sum()),"sharpe":round(sharpe(gg[m]),4),
                                      "rho_A0":round(float(np.corrcoef(gg[mm],ref[mm])[0,1]),4) if mm.sum()>10 else None}
        ROWS[name].append(rec)
        print("%-38s %-28s n=%5d Sh=%7.4f beta=%+8.4f (t %+6.2f) betaN=%+7.4f  T0 Sh=%+8.4f T2 Sh=%+8.4f  rhoA0 all/T0/T2 %s/%s/%s"%(
            name, os.path.basename(p)[:28], rec["n"], rec["sharpe_full"], rec["beta_sig_bps_per_SD"], rec["t_nw30"],
            rec["beta_norm_ownSD_per_SD"], rec["tercile"]["T0"]["sharpe"], rec["tercile"]["T2"]["sharpe"],
            rec["rho_A0"]["all"], rec["rho_A0"]["T0"], rec["rho_A0"]["T2"]), flush=True)

json.dump({"self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
           "env_whitelist":ENV_WL,
           "window":{"lo":time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(LO)),
                     "hi":time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(HI)),"n_fuel_anchors":int(len(F_ts))},
           "tercile_breaks":[round(float(q33),4),round(float(q67),4)],
           "caliber":{"g":"net_ex/gross_total [bps per unit gross]","cost":"costb_PWR_G230k.json",
                      "gauge":"sig_fund = 1e4*xsec SD of 8h-equivalent funding on the CRYPTO-m1 member set"},
           "rows":ROWS}, open(OUT19+"/R7_SCREEN.json","w"), indent=1)
print("SCREEN_DONE")
