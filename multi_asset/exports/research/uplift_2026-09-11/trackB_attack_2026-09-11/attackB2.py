"""ATTACK 2: the per-unit-gross metric assumes a free rescale to constant gross.
Build the DEPLOYABLE constant-gross book P_t = W_t/gross_t and charge the rescale turnover."""
import numpy as np, calendar, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1)
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_TB_%s_dyn_s%s.npz"
UNIT=2.148  # device tier-weighted bps per unit turnover
def go(nm,s):
    A=np.load(TB%(nm,s),allow_pickle=True); R=A["d30_n2_c42_rec"]; W=np.asarray(A["d30_n2_c42_W"],np.float64)
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64)
    gt=R[:,C["gross_total"]]
    chk=np.abs(W).sum(1)
    P=W/np.where(gt>1e-12,gt,np.nan)[:,None]
    tov_re=np.abs(np.diff(P,axis=0)).sum(1); tov_re=np.concatenate([[np.abs(P[0]).sum()],tov_re])
    tov_dev=R[:,C["turnover"]]/gt
    m=(ts>=FR[0])&(ts<FR[1])
    g=R[:,C["net_ex"]]/gt
    # corrected g: charge the extra rescale turnover
    g_corr = g - (tov_re-tov_dev)*UNIT
    return dict(nm=nm,s=s,gross_mean=gt[m].mean(),gross_std=gt[m].std(),gross_min=gt[m].min(),
                gmax=np.abs(np.diff(gt[m])/gt[m][:-1]).mean(),
                tov_dev=tov_dev[m].mean(),tov_re=tov_re[m].mean(),
                g=g[m].mean(),g_corr=g_corr[m].mean(),
                SR=g[m].mean()/g[m].std(ddof=1)*np.sqrt(2190),
                SR_corr=g_corr[m].mean()/g_corr[m].std(ddof=1)*np.sqrt(2190),
                gmaxabs=float(np.max(np.abs(chk-gt))), ts=ts, g_arr=g, gcorr_arr=g_corr, m=m, gt=gt)
def bootd(ts,d,ci,m):
    dd=d[m]; rng=np.random.default_rng([20260905,ci])
    ud,inv=np.unique(ts[m]//86400,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=dd,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return dd.mean(),np.percentile(mn,2.5),np.percentile(mn,97.5),(mn>0).mean()
arms=["BASE","BAND35e5","BAND45e5","BAND5e4","BAND6e4","EMA007","EMA005","EMA004","EMA015","CAD2"]
print("%-9s %-4s %7s %7s %7s %8s %8s %9s %9s %6s %6s"%("arm","seed","gross","g_std","g_min","tov_dev","tov_RE","g","g_corr","SR","SRcorr"))
res={}
for nm in arms:
    for s in ("42","2027"):
        if not os.path.exists(TB%(nm,s)): continue
        r=go(nm,s); res[(nm,s)]=r
        print("%-9s %-4s %7.4f %7.4f %7.4f %8.4f %8.4f %+9.4f %+9.4f %6.3f %6.3f"%(nm,s,r["gross_mean"],r["gross_std"],r["gross_min"],r["tov_dev"],r["tov_re"],r["g"],r["g_corr"],r["SR"],r["SR_corr"]))
print("\n(sanity |W|.sum - gross_total maxabs = %.3e)"%res[("BASE","42")]["gmaxabs"])
print("\n== dG under the DEPLOYABLE (constant-gross, rescale charged) metric ==")
for nm in arms:
    if nm=="BASE": continue
    for s in ("42","2027"):
        if (nm,s) not in res: continue
        a=res[(nm,s)]; b=res[("BASE",s)]
        d0=bootd(a["ts"],a["g_arr"]-b["g_arr"],3,a["m"])
        d1=bootd(a["ts"],a["gcorr_arr"]-b["gcorr_arr"],3,a["m"])
        print("%-9s s%-5s dG_asjudged %+7.4f [%+7.4f,%+7.4f] | dG_deployable %+7.4f [%+7.4f,%+7.4f] p=%.3f"%(nm,s,d0[0],d0[1],d0[2],d1[0],d1[1],d1[2],d1[3]))
