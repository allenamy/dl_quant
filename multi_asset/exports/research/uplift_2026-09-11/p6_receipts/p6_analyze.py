"""P6 analysis. Statistic per the pin: g = net_ex/gross_total (bps/anchor/unit gross), paired per anchor,
UTC-day block bootstrap 2000, rng numpy.default_rng([20260905,k]) k in {0,9}.
E-0911-A: every FULL-CYCLE reading DROPS the first LOOK=900 device anchors."""
import numpy as np, json, calendar, os
A="/workspace/uplift_2026-09-11/p6/arms"; APY=2190; WARM=900
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1; FROZ_LO=T(2025,3,1)
def load(tag):
    Z=np.load(A+"/w10_ablation_series_%s.npz"%tag,allow_pickle=True)
    cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["d30_n2_c42_rec"],float)
    Rr=Rr[WARM:]                      # E-0911-A
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64)
    m=ts<FULL_HI
    return ts[m],Rr[m],ix
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>2 else float("nan")
def boot(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return [float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5))],float((mn>0).mean())
OUT={"warm_dropped":WARM,"full_hi_utc":"2026-08-10 20Z inclusive"}
ARMS=[t[:-4] for t in sorted(os.listdir(A)) if t.startswith("w10_ablation_series_P6_") and t.endswith(".npz")]
ARMS=[a.replace("w10_ablation_series_","") for a in ARMS]
LV={}
print("%-26s %6s %9s %8s %9s %9s %9s"%("arm","n","mean_g","Sharpe","turnover","gross_tot","nsel"))
for tag in ARMS:
    ts,Rr,ix=load(tag)
    g=Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]]
    LV[tag]={"n":int(len(ts)),"mean_g":float(g.mean()),"sharpe":sr(g),
             "turnover":float(Rr[:,ix["turnover"]].mean()),
             "gross_total":float(Rr[:,ix["gross_total"]].mean()),
             "nsel":float(Rr[:,ix["nsel"]].mean()),
             "cost_ex_bps":float(Rr[:,ix["cost_ex"]].mean()),
             "pnl_ex_bps":float(Rr[:,ix["pnl_ex"]].mean()),
             "carry_ex_bps":float(Rr[:,ix["carry_ex"]].mean())}
    print("%-26s %6d %9.5f %8.4f %9.4f %9.4f %9.1f"%(tag,len(ts),g.mean(),sr(g),
          Rr[:,ix["turnover"]].mean(),Rr[:,ix["gross_total"]].mean(),Rr[:,ix["nsel"]].mean()))
    # per year
    yr={}
    for y in range(2022,2027):
        mm=(ts>=T(y,1,1))&(ts<T(y+1,1,1))
        if mm.sum()>50: yr[str(y)]={"n":int(mm.sum()),"sharpe":sr(g[mm]),"mean_g":float(g[mm].mean())}
    LV[tag]["by_year"]=yr
    mf=ts>=FROZ_LO
    LV[tag]["frozen"]={"n":int(mf.sum()),"sharpe":sr(g[mf]),"mean_g":float(g[mf].mean())}
OUT["levels"]=LV
# ---- paired contrasts ----
PAIRS=[("P6_AMQ64_PWR_s42","P6_AMX_PWR_s42"),("P6_AMQ64_PWR_s2027","P6_AMX_PWR_s2027"),
       ("P6_AMP_PWR_s42","P6_AMX_PWR_s42"),("P6_AMP_PWR_s2027","P6_AMX_PWR_s2027"),
       ("P6_AMQ32_PWR_s42","P6_AMQ64_PWR_s42"),("P6_AMQ32_PWR_s2027","P6_AMQ64_PWR_s2027"),
       ("P6_AMR2_PWR_s42","P6_AMQ64_PWR_s42"),("P6_AMR2_PWR_s2027","P6_AMQ64_PWR_s2027"),
       ("P6_AMQ64_PWR400_s42","P6_AMQ64_PWR_s42"),("P6_AMQ64_PWR400_s2027","P6_AMQ64_PWR_s2027"),
       ("P6_AMQ64_PWR600_s42","P6_AMQ64_PWR_s42"),("P6_AMQ64_PWR600_s2027","P6_AMQ64_PWR_s2027")]
CON={}
print()
print("%-46s %6s %+10s %24s %6s %24s"%("contrast (arm - ref)","n","delta_g","CI95(k=0)","P>0","CI95(k=9)"))
for a,b in PAIRS:
    if not (os.path.exists(A+"/w10_ablation_series_%s.npz"%a) and os.path.exists(A+"/w10_ablation_series_%s.npz"%b)):
        print("MISSING",a,b); continue
    ta,Ra,ix=load(a); tb,Rb,_=load(b)
    com,ia,ib=np.intersect1d(ta,tb,return_indices=True)
    ga=(Ra[:,ix["net_ex"]]/Ra[:,ix["gross_total"]])[ia]; gb=(Rb[:,ix["net_ex"]]/Rb[:,ix["gross_total"]])[ib]
    d=ga-gb; days=com//86400
    c0,p0=boot(d,days,0); c9,p9=boot(d,days,9)
    CON["%s|%s"%(a,b)]={"n":int(len(com)),"delta_g":float(d.mean()),"ci95_k0":c0,"p_k0":p0,"ci95_k9":c9,"p_k9":p9,
                        "sharpe_arm":sr(ga),"sharpe_ref":sr(gb),"d_sharpe":sr(ga)-sr(gb),
                        "bitwise_equal_g":bool(np.array_equal(ga,gb))}
    print("%-46s %6d %+10.6f [%+9.6f,%+9.6f] %6.3f [%+9.6f,%+9.6f]"%(a+" - "+b,len(com),d.mean(),c0[0],c0[1],p0,c9[0],c9[1]))
OUT["contrasts"]=CON
json.dump(OUT,open("/workspace/uplift_2026-09-11/p6/P6_BOOK.json","w"),indent=1)
print("ANALYZE_DONE")
