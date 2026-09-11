"""BUILD 2 FINAL: the full-axis reading of every arm and every null, on the SAME axis and metric.
FULL AXIS = the deployable object: where an arm holds no book (device skipped the anchor because the
tilted w3 was the zero vector) it earns g = 0. Pairing on the intersection instead CONDITIONS on
'the msharpe king seat was positive', which is a selection, so both readings are reported.
Primary gate from the frozen prereg: theta = year-FE mean of d, Bonferroni K=9 => 99.44% CI must exclude 0,
AND >= 4 of 5 years positive."""
import numpy as np, calendar, time, json, hashlib
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
U="/workspace/uplift_2026-09-11"; R=U+"/r8b2"; APY=2190; WARM=900; CUT=T(2026,8,30,20); B=4000
K_DECL=9; ALPHA=0.05/K_DECL; LO=100*ALPHA/2; HI=100-LO; TAU=4.75
GS=T(2026,8,19,0); GE=T(2026,8,21,20); HS=T(2026,8,11,0); HE=T(2026,8,30,20); FITCUT=T(2026,8,10,20)
S=np.load(U+"/r7f1/out/sigma_variants.npz",allow_pickle=True); C=[str(c) for c in S["cols"]]
GL=dict(zip(S["rec"][:,0].astype(np.int64),S["rec"][:,C.index("LIVE_sig")]))
def load(p):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    A=np.asarray(Z[k],float)[WARM:]; ts=np.round(A[:,ix["ts"]]).astype(np.int64); m=ts<=CUT
    return ts[m],(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[m],(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[m],A[:,ix["turnover"]][m]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def bstat(ts,fn,seed):
    dd=ts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    o=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(o))
    rng=np.random.default_rng([20260912,seed]); pk=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        ii=np.concatenate([o[st[j]:en[j]] for j in pk[b]]); out[b]=fn(ii)
    return out
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]; return (float(np.percentile(v,lo)),float(np.percentile(v,hi)))
ts0,g0,p0,t0_=load(U+"/r3k/arms/A0_PWR230k_s42.npz")
YR=np.array([time.gmtime(int(t)).tm_year for t in ts0]); YEARS=sorted(set(YR.tolist()))
sig=np.array([GL.get(int(t),np.nan) for t in ts0])
def fullaxis(p):
    tsa,ga,pa,ta=load(p)
    keep=np.isin(ts0,tsa); back=np.isin(tsa,ts0)
    gf=np.zeros_like(g0); gf[keep]=ga[back]
    pf=np.zeros_like(p0); pf[keep]=pa[back]
    tf=np.zeros_like(t0_); tf[keep]=ta[back]
    return gf,pf,tf,int((~keep).sum())
def report(p,label,seed=401):
    gf,pf,tf,nb=fullaxis(p)
    d=gf-g0; dp=pf-p0
    th=float(np.mean([d[YR==y].mean() for y in YEARS]))
    bt=bstat(ts0,lambda ii: float(np.mean([d[ii][YR[ii]==y].mean() for y in YEARS if (YR[ii]==y).sum()>0])),seed)
    bd=bstat(ts0,lambda ii: d[ii].mean(),seed+1)
    gv=(ts0>=GS)&(ts0<=GE); ho=(ts0>=HS)&(ts0<=HE); fit=ts0<=FITCUT; lo=sig<TAU
    npos=sum(1 for y in YEARS if d[YR==y].mean()>0)
    r={"label":label,"n_no_book":nb,"delta_g":round(float(d.mean()),4),
       "delta_g_CI95":[round(x,4) for x in ci(bd)],
       "delta_pnl_ex":round(float(dp.mean()),4),
       "theta_yearFE":round(th,4),"theta_CI95":[round(x,4) for x in ci(bt)],
       "theta_CI_bonf9944":[round(x,4) for x in ci(bt,LO,HI)],
       "per_year":{int(y):round(float(d[YR==y].mean()),4) for y in YEARS},
       "n_years_positive":int(npos),
       "arm_sharpe":round(sr(gf),4),"delta_sharpe":round(sr(gf)-sr(g0),4),
       "turnover_ratio":round(float(tf.mean()/t0_.mean()),4),
       "marginal_turnover":round(float(tf.mean()-t0_.mean()),6),
       "delta_g_low_sigma":round(float(d[lo].mean()),4),"delta_g_high_sigma":round(float(d[~lo].mean()),4),
       "giveback_delta_g":round(float(d[gv].mean()),4),
       "giveback_delta_sharpe":round(sr(gf[gv])-sr(g0[gv]),4),
       "heldout_delta_g":round(float(d[ho].mean()),4),
       "heldout_delta_g_CI95":[round(x,4) for x in ci(bstat(ts0[ho],lambda ii: d[ho][ii].mean(),seed+2))],
       "insample_fit_delta_g":round(float(d[fit].mean()),4),
       "GATE_a_PASS":bool(th>0 and ci(bt,LO,HI)[0]>0 and npos>=4)}
    return r
OUT={"caliber":"FULL AXIS g=net_ex/gross_total (0 where no book); post-warm 900; cut 2026-08-30 20Z; fitted cost costb_PWR_G230k.json",
     "K_declared":K_DECL,"bonf_ci_pct":round(100-100*ALPHA,2),"B":B,
     "A0":{"n":len(g0),"mean_g":round(float(g0.mean()),4),"sharpe":round(sr(g0),4),
           "giveback_mean_g":round(float(g0[(ts0>=GS)&(ts0<=GE)].mean()),4),
           "giveback_sharpe":round(sr(g0[(ts0>=GS)&(ts0<=GE)]),4)},
     "arms":{},"nulls":{}}
GRID=["S00","S25","S50","S75","R00","R25","R50","P05","P10"]
print("%-12s %8s %18s %9s %20s %4s %8s %7s %9s %9s"%("arm","d_g","d_g CI95","theta","theta bonf99.44","yr+","d_SR","noBook","GB d_g","HO d_g"))
for nm in GRID:
    r=report(R+"/dev/probe_artifacts/w10_ablation_series_R8_%s_s42.npz"%nm,nm,401+7*GRID.index(nm))
    OUT["arms"][nm]=r
    print("%-12s %+8.4f %18s %+9.4f %20s %4d %+8.4f %7d %+9.4f %+9.4f  GATE_a=%s"%(
        nm,r["delta_g"],r["delta_g_CI95"],r["theta_yearFE"],r["theta_CI_bonf9944"],r["n_years_positive"],
        r["delta_sharpe"],r["n_no_book"],r["giveback_delta_g"],r["heldout_delta_g"],r["GATE_a_PASS"]))
print()
for arm in ("S00","P10"):
    for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3"):
        r=report(R+"/dev2/probe_artifacts/w10_ablation_series_R8N_%s_%s.npz"%(arm,n),"%s/%s"%(arm,n),500+hash(arm+n)%900)
        OUT["nulls"]["%s/%s"%(arm,n)]=r
    real=OUT["arms"][arm]
    nd=[OUT["nulls"]["%s/%s"%(arm,n)]["delta_g"] for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3")]
    nt=[OUT["nulls"]["%s/%s"%(arm,n)]["theta_yearFE"] for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3")]
    npx=[OUT["nulls"]["%s/%s"%(arm,n)]["delta_pnl_ex"] for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3")]
    nnb=[OUT["nulls"]["%s/%s"%(arm,n)]["n_no_book"] for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3")]
    OUT["arms"][arm]["FULLAXIS_NULLS"]={"null_delta_g":nd,"null_theta":nt,"null_delta_pnl_ex":npx,"null_n_no_book":nnb,
        "beats_all_on_delta_g":bool(real["delta_g"]>max(nd)),"beats_all_on_theta":bool(real["theta_yearFE"]>max(nt)),
        "beats_all_on_pnl_ex":bool(real["delta_pnl_ex"]>max(npx)),
        "empirical_p":round((1+sum(1 for x in nd if x>=real["delta_g"]))/7,4)}
    print("FULL-AXIS NULLS %s: REAL d_g %+.4f theta %+.4f pnl_ex %+.4f noBook %d"%(arm,real["delta_g"],real["theta_yearFE"],real["delta_pnl_ex"],real["n_no_book"]))
    for n in ("SHIFT101","SHIFT503","SHIFT1009","ROT1","ROT2","ROT3"):
        q=OUT["nulls"]["%s/%s"%(arm,n)]
        print("   %-10s d_g %+.4f  theta %+.4f  pnl_ex %+.4f  noBook %d"%(n,q["delta_g"],q["theta_yearFE"],q["delta_pnl_ex"],q["n_no_book"]))
    print("   beats all: d_g=%s theta=%s pnl_ex=%s  empirical p=%.4f\n"%(
        OUT["arms"][arm]["FULLAXIS_NULLS"]["beats_all_on_delta_g"],OUT["arms"][arm]["FULLAXIS_NULLS"]["beats_all_on_theta"],
        OUT["arms"][arm]["FULLAXIS_NULLS"]["beats_all_on_pnl_ex"],OUT["arms"][arm]["FULLAXIS_NULLS"]["empirical_p"]))
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(R+"/out/R8_FINAL.json","w"),indent=1)
print("FINAL_DONE")
