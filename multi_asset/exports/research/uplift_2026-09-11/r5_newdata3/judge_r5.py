"""r5nd/judge_r5.py -- statistic and bootstrap VERBATIM from r4_p1/b1_analyze.py.
g = net_ex/gross_total (bps/anchor/unit gross); Sharpe = mean/sd*sqrt(2190);
UTC-day block bootstrap 2000, rng numpy.default_rng([20260905,k]); first 900 device rows dropped (E-0911-A).
Paired vs the A0 control on common support. Reports CI95 AND the Bonferroni CI (K declared in the PREREG).
Usage: python judge_r5.py <prefix> <baseline_tag> <arm1,arm2,...> <outname> [K]"""
import numpy as np, json, os, sys
R="/workspace/uplift_2026-09-11/r5nd"; OUT=R+"/arms"
def rd(p):
    Z=np.load(p,allow_pickle=True); Rr=np.asarray(Z["rec"],float); cols=[str(c) for c in Z["cols"]]
    ix={c:i for i,c in enumerate(cols)}; ts=Rr[:,ix["ts"]].astype(np.int64)
    d={c:Rr[:,ix[c]] for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","turnover")}
    g=np.where(d["gross_total"]>0,d["net_ex"]/np.maximum(d["gross_total"],1e-12),np.nan)
    return ts,g,d
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
SPANS={"FULL_pw":(ep("2022-01-01T00:00"),ep("2026-08-10T20:00")),
       "2024on_pw":(ep("2024-01-01T00:00"),ep("2026-08-10T20:00"))}
sr=lambda x: float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190))
def dayblocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot_paired(dg,ts,k,qlo,qhi,B=2000):
    bl=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl)
    mo=np.empty(B); so=np.empty(B)
    for b in range(B):
        ix=np.concatenate([bl[i] for i in rng.integers(0,nb,nb)]); x=dg[ix]
        mo[b]=x.mean(); so[b]=x.mean()/x.std(ddof=1)*np.sqrt(2190)
    q=lambda o,a,z:[round(float(np.percentile(o,a)),4),round(float(np.percentile(o,z)),4)]
    return q(mo,2.5,97.5),q(so,2.5,97.5),q(mo,qlo,qhi),q(so,qlo,qhi)
if __name__=="__main__":
    PRE,BASE,ARMSTR,ONAME=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
    K=int(sys.argv[5]) if len(sys.argv)>5 else 10
    alpha=0.05/K; qlo=100*alpha/2; qhi=100*(1-alpha/2)
    ARMS=ARMSTR.split(",")
    CELLS=[(st,sd) for st in ("dyn","fix") for sd in ("42","2027")]
    D={}
    for a in [BASE]+ARMS:
        for st,sd in CELLS: D[(a,st,sd)]=rd(OUT+"/%s_%s_%s_s%s.npz"%(PRE,a,st,sd))
    def series(key,span):
        ts,g,c=D[key]; lo,hi=SPANS[span]
        m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:900]=False
        return ts[m],g[m],{k:v[m] for k,v in c.items()}
    RES={"K":K,"bonferroni_alpha":alpha,"CI_bonf_pct":round(100*(1-alpha),4),"cells":{}}
    for span in SPANS:
        for st,sd in CELLS:
            S={a:series((a,st,sd),span) for a in [BASE]+ARMS}
            ts=S[BASE][0]
            for a in ARMS: ts=np.intersect1d(ts,S[a][0])
            G={};TO={};CO={};CA={}
            for a in [BASE]+ARMS:
                t,g,c=S[a]; ixx=np.searchsorted(t,ts); assert np.array_equal(t[ixx],ts)
                G[a]=g[ixx]; TO[a]=float(c["turnover"][ixx].mean())
                CO[a]=float((c["cost_ex"][ixx]/c["gross_total"][ixx]).mean())
                CA[a]=float((c["carry_ex"][ixx]/c["gross_total"][ixx]).mean())
            key="%s|%s|s%s"%(span,st,sd); rows={}
            rows[BASE]={"g_bps":round(float(G[BASE].mean()),4),"SR":round(sr(G[BASE]),4),
                        "turnover":round(TO[BASE],4),"cost_bps":round(CO[BASE],4),"carry_bps":round(CA[BASE],4)}
            for j,a in enumerate(ARMS):
                dg=G[a]-G[BASE]
                ci95m,ci95s,cibm,cibs=boot_paired(dg,ts,k=j,qlo=qlo,qhi=qhi)
                rows[a]={"g_bps":round(float(G[a].mean()),4),"SR":round(sr(G[a]),4),
                         "turnover":round(TO[a],4),"cost_bps":round(CO[a],4),"carry_bps":round(CA[a],4),
                         "dSR":round(sr(G[a])-sr(G[BASE]),4),
                         "d_g":round(float(dg.mean()),4),"d_g_CI95":ci95m,"d_g_CIbonf":cibm,
                         "paired_dSR":round(sr(dg),4),"paired_dSR_CI95":ci95s,"paired_dSR_CIbonf":cibs,
                         "rho_g_to_base":round(float(np.corrcoef(G[a],G[BASE])[0,1]),4),
                         "carry_frac_of_net":round(float(CA[a]/G[a].mean()) if G[a].mean()!=0 else float("nan"),4)}
            RES["cells"][key]={"n":int(len(ts)),"rows":rows}
            print(key,"n=%d"%len(ts),flush=True)
            for a in [BASE]+ARMS:
                r=rows[a]
                extra="" if a==BASE else "  dg %+.4f CI95 %s CIb %s  dSR %+.4f"%(r["d_g"],r["d_g_CI95"],r["d_g_CIbonf"],r["dSR"])
                print("   %-14s g %8.4f  SR %7.4f  to %.4f  cost %.4f%s"%(a,r["g_bps"],r["SR"],r["turnover"],r["cost_bps"],extra),flush=True)
    json.dump(RES,open(R+"/%s.json"%ONAME,"w"),indent=1)
    print("JUDGE_DONE ->",R+"/%s.json"%ONAME)
