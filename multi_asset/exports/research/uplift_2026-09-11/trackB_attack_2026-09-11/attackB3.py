"""ATTACK 3: (i) bootstrap CI on the GOAL metric (annualised Sharpe of g), (ii) absolute (not per-gross)
component decomposition, (iii) concentration of the renormalised deployable book, (iv) dG by gross tercile."""
import numpy as np, calendar, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1)
EXT=(T(2025,3,1),T(2026,8,31,20)+1)
Y24=(T(2024,1,1),T(2026,8,10,20)+1)
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_TB_%s_dyn_s%s.npz"
def ld(nm,s):
    A=np.load(TB%(nm,s),allow_pickle=True); R=A["d30_n2_c42_rec"]; W=np.asarray(A["d30_n2_c42_W"],np.float64)
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64); return ts,R,W
def bootSR(ts,g,m,ci,paired=None):
    """UTC-day block bootstrap of the ANNUALISED SHARPE of g (and of the paired dSharpe if paired given)."""
    rng=np.random.default_rng([20260905,ci])
    d=ts[m]//86400; ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    order=np.argsort(inv,kind="stable"); inv_s=inv[order]
    starts=np.searchsorted(inv_s,np.arange(nd)); ends=np.searchsorted(inv_s,np.arange(nd),side="right")
    gv=g[m][order]; pv=paired[m][order] if paired is not None else None
    S=[];P=[]
    idx=rng.integers(0,nd,size=(2000,nd))
    for b in range(2000):
        sel=np.concatenate([np.arange(starts[k],ends[k]) for k in idx[b]])
        v=gv[sel]; S.append(v.mean()/v.std(ddof=1)*np.sqrt(2190))
        if pv is not None:
            u=pv[sel]; P.append(v.mean()/v.std(ddof=1)*np.sqrt(2190)-u.mean()/u.std(ddof=1)*np.sqrt(2190))
    S=np.array(S)
    out=(float(np.percentile(S,2.5)),float(np.percentile(S,97.5)),float((S>3.0).mean()))
    if pv is not None:
        P=np.array(P); out=out+(float(np.mean(P)),float(np.percentile(P,2.5)),float(np.percentile(P,97.5)),float((P>0).mean()))
    return out
print("=== (i) GOAL METRIC: annualised Sharpe with day-block bootstrap CI, frozen window ===")
print("%-9s %-5s %7s %-22s %8s | %-28s"%("arm","seed","SR","CI95(SR)","P(SR>3)","dSR vs BASE [CI95] P>0"))
base={}
for s in ("42","2027"):
    ts,R,_=ld("BASE",s); m=(ts>=FR[0])&(ts<FR[1]); base[s]=(ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],m)
for nm in ("BASE","BAND45e5","BAND5e4","EMA005","BAND35e5"):
    for s in ("42","2027"):
        if not os.path.exists(TB%(nm,s)): continue
        ts,R,_=ld(nm,s); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]; m=(ts>=FR[0])&(ts<FR[1])
        sr=g[m].mean()/g[m].std(ddof=1)*np.sqrt(2190)
        if nm=="BASE": r=bootSR(ts,g,m,7); extra=""
        else:
            r=bootSR(ts,g,m,7,paired=base[s][1]); extra="%+6.3f [%+6.3f,%+6.3f] P>0=%.3f"%(r[3],r[4],r[5],r[6])
        print("%-9s %-5s %7.3f [%+6.3f,%+6.3f]      %8.3f | %s"%(nm,s,sr,r[0],r[1],r[2],extra))

print("\n=== (ii) ABSOLUTE components (bps/anchor, NOT per gross) — tests the 'denominator' story ===")
print("%-9s %-5s %9s %9s %9s %9s %9s %9s"%("arm","seed","abs_net","abs_pnl","abs_carry","abs_cost","gross","g=net/gr"))
for nm in ("BASE","BAND35e5","BAND45e5","BAND5e4","BAND6e4","EMA005","EMA004","CAD2"):
    for s in ("42",):
        if not os.path.exists(TB%(nm,s)): continue
        ts,R,_=ld(nm,s); m=(ts>=FR[0])&(ts<FR[1])
        print("%-9s %-5s %+9.4f %+9.4f %+9.4f %+9.4f %9.4f %+9.4f"%(nm,s,R[m,C["net_ex"]].mean(),R[m,C["pnl_ex"]].mean(),R[m,C["carry_ex"]].mean(),R[m,C["cost_ex"]].mean(),R[m,C["gross_total"]].mean(),(R[m,C["net_ex"]]/R[m,C["gross_total"]]).mean()))

print("\n=== (iii) CONCENTRATION of the deployable (renormalised to unit gross) book ===")
print("%-9s %-5s %9s %9s %9s %9s"%("arm","seed","effN","max|w|","top10%gr","nsel"))
for nm in ("BASE","BAND5e4","BAND6e4","EMA005"):
    for s in ("42",):
        ts,R,W=ld(nm,s); m=(ts>=FR[0])&(ts<FR[1])
        P=np.abs(W[m])/np.abs(W[m]).sum(1,keepdims=True)
        effN=(1.0/(P**2).sum(1)).mean(); mx=P.max(1).mean()
        top10=np.sort(P,axis=1)[:,-10:].sum(1).mean()
        print("%-9s %-5s %9.1f %9.4f %9.4f %9.1f"%(nm,s,effN,mx,top10,R[m,C["nsel"]].mean()))

print("\n=== (iv) where does dG come from? split by BASE gross tercile, and by window ===")
for nm in ("BAND5e4","EMA005"):
    for s in ("42","2027"):
        ts,R,_=ld(nm,s); tb,Rb,_=ld("BASE",s)
        g=R[:,C["net_ex"]]/R[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
        m=(ts>=FR[0])&(ts<FR[1]); d=(g-gb)
        q=np.quantile(Rb[m,C["gross_total"]],[1/3,2/3])
        gg=Rb[:,C["gross_total"]]
        t1=m&(gg<=q[0]); t2=m&(gg>q[0])&(gg<=q[1]); t3=m&(gg>q[1])
        mE=(ts>=EXT[0])&(ts<EXT[1]); m24=(ts>=Y24[0])&(ts<Y24[1])
        print("%-9s s%-5s dG frozen %+6.3f | lowGross %+6.3f midGross %+6.3f highGross %+6.3f | EXTENDED(to 08-31) %+6.3f | 2024-01..08-10 %+6.3f"%(
            nm,s,d[m].mean(),d[t1].mean(),d[t2].mean(),d[t3].mean(),d[mE].mean(),d[m24].mean()))
