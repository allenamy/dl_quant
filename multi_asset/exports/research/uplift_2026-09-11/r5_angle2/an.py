"""ANGLE 2 analyser. Statistic VERBATIM from r4_p1/b1c_analyze.py:
g = net_ex/gross_total (bps/anchor/unit gross); Sharpe = mean/sd*sqrt(2190);
UTC-day block bootstrap 2000, rng numpy.default_rng([20260905,k]).
E-0911-A: first LOOK=900 device rows dropped from every reading.
DIFFERENCES from round 4, stated: (i) MY OWN bootstrap substream k'=5000+j (round 4 used j=0..4);
(ii) PAIRWISE common support (arm vs A0) instead of all-arm common support, so a long shift does not
shrink the sample of a short one. The headline cell is also reported on round-4's all-arm support.
Component identity CHECKED per anchor: net_ex == pnl_ex - carry_ex - cost_ex."""
import numpy as np, json, os, sys
R=os.path.dirname(os.path.abspath(__file__)); OUT=R+"/arms"
def rd(p):
    Z=np.load(p,allow_pickle=True); Rr=np.asarray(Z["rec"],float); cols=[str(c) for c in Z["cols"]]
    ix={c:i for i,c in enumerate(cols)}; ts=Rr[:,ix["ts"]].astype(np.int64)
    d={c:Rr[:,ix[c]] for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","turnover",
                               "w3_king","w3_rev24","w3_fund")}
    id_err=float(np.max(np.abs(d["net_ex"]-(d["pnl_ex"]-d["carry_ex"]-d["cost_ex"]))))
    g=np.where(d["gross_total"]>0,d["net_ex"]/np.maximum(d["gross_total"],1e-12),np.nan)
    return ts,g,d,id_err
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
SPANS={"FULL_pw":(ep("2022-01-01T00:00"),ep("2026-08-10T20:00")),
       "2024on_pw":(ep("2024-01-01T00:00"),ep("2026-08-10T20:00")),
       "FROZEN_pw":(ep("2025-03-01T00:00"),ep("2026-08-10T20:00"))}
sr=lambda x: float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190))
def dayblocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot(dg,ts,k,B=2000):
    bl=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl)
    mo=np.empty(B)
    for b in range(B):
        ix=np.concatenate([bl[i] for i in rng.integers(0,nb,nb)]); mo[b]=dg[ix].mean()
    return [round(float(np.percentile(mo,2.5)),4),round(float(np.percentile(mo,97.5)),4)]
def sub(ts,g,d,span):
    lo,hi=SPANS[span]; m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:900]=False
    return ts[m],g[m],{k:v[m] for k,v in d.items()}
def load(tag): return rd(OUT+"/%s.npz"%tag)

KS=[1,3,6,12,25,50,101,150,200,300,400,503,750,1009,1500,2000]
LEADS=[6,101,503]
ARMS=["APAR"]+["ASHIFT%d"%k for k in KS]+["ALEAD%d"%k for k in LEADS]+["A0"]
def main():
    RES={"identity_max_abs_err":{},"cells":{},"seat_weights":{}}
    D={}
    for a in ARMS:
        for st in ("dyn","fix"):
            for sd in ("42","2027"):
                p=OUT+"/R5A2_%s_%s_s%s.npz"%(a,st,sd)
                if not os.path.exists(p): continue
                D[(a,st,sd)]=load("R5A2_%s_%s_s%s"%(a,st,sd))
    RES["identity_max_abs_err"]={"%s|%s|s%s"%k:round(v[3],10) for k,v in D.items()}
    # PARITY GATE: APAR (injected unshifted) must equal A0 (knobs-off) BITWISE
    par={}
    for st in ("dyn","fix"):
        for sd in ("42","2027"):
            if ("APAR",st,sd) in D and ("A0",st,sd) in D:
                x=np.load(OUT+"/R5A2_APAR_%s_s%s.npz"%(st,sd))["rec"]; y=np.load(OUT+"/R5A2_A0_%s_s%s.npz"%(st,sd))["rec"]
                nx=np.isnan(x); ny=np.isnan(y)
                par["%s_s%s"%(st,sd)]=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
    RES["GATE_APAR_eq_A0_bitwise"]=par
    for st in ("dyn","fix"):
        for sd in ("42","2027"):
            if ("A0",st,sd) not in D: continue
            ts0,g0,d0,_=D[("A0",st,sd)]
            for span in SPANS:
                t0,gg0,dd0=sub(ts0,g0,d0,span)
                RES["seat_weights"]["%s|%s|s%s"%(span,st,sd)]={
                    "w3_king_mean":round(float(dd0["w3_king"].mean()),4),
                    "w3_fund_mean":round(float(dd0["w3_fund"].mean()),4),
                    "w3_king_p05":round(float(np.percentile(dd0["w3_king"],5)),4),
                    "w3_king_p50":round(float(np.percentile(dd0["w3_king"],50)),4),
                    "w3_king_p95":round(float(np.percentile(dd0["w3_king"],95)),4),
                    "frac_anchors_king_le_0.21":round(float((dd0["w3_king"]<=0.21).mean()),4)}
                rows={}
                for j,a in enumerate(ARMS):
                    if a=="A0" or (a,st,sd) not in D: continue
                    ts1,g1,d1,_=D[(a,st,sd)]
                    t1,gg1,dd1=sub(ts1,g1,d1,span)
                    tc=np.intersect1d(t0,t1)
                    i0=np.searchsorted(t0,tc); i1=np.searchsorted(t1,tc)
                    assert np.array_equal(t0[i0],tc) and np.array_equal(t1[i1],tc)
                    A=gg0[i0]; Bv=gg1[i1]
                    gr=lambda dd,ii,c: dd[c][ii]/dd["gross_total"][ii]
                    dp=gr(dd1,i1,"pnl_ex")-gr(dd0,i0,"pnl_ex")
                    dc=gr(dd1,i1,"carry_ex")-gr(dd0,i0,"carry_ex")
                    dk=gr(dd1,i1,"cost_ex")-gr(dd0,i0,"cost_ex")
                    dg=Bv-A
                    rows[a]={"n":int(len(tc)),
                             "g_arm":round(float(Bv.mean()),4),"g_A0":round(float(A.mean()),4),
                             "SR_arm":round(sr(Bv),4),"SR_A0":round(sr(A),4),
                             "d_g":round(float(dg.mean()),4),"d_g_CI95":boot(dg,tc,5000+j),
                             "d_pnl":round(float(dp.mean()),4),"d_carry":round(float(dc.mean()),4),
                             "d_cost":round(float(dk.mean()),4),
                             "d_grossofcost":round(float((dg+dk).mean()),4),
                             "pct_grossofcost":(round(float((dg+dk).mean()/dg.mean()*100),1) if abs(dg.mean())>1e-9 else None),
                             "turnover_arm":round(float(dd1["turnover"][i1].mean()),4),
                             "turnover_A0":round(float(dd0["turnover"][i0].mean()),4)}
                RES["cells"]["%s|%s|s%s"%(span,st,sd)]=rows
                print("done",span,st,sd,flush=True)
    json.dump(RES,open(R+"/A2_LADDER.json","w"),indent=1)
    print("ANALYSE_DONE")
if __name__=="__main__": main()
