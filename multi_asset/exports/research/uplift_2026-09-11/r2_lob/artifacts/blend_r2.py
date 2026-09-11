"""Paired in-book delta: blend a sleeve into A0 at weight w (equal-gross), measure d = g_blend - g_A0
per anchor on the LOBFULL span, day-block bootstrap CI (judge_v4 rng). Also the out-of-fit stress window."""
import numpy as np, json, calendar, glob, os, sys
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL=(T(2022,1,1),T(2026,8,10,20)+1); STRESS=(T(2026,8,11),T(2026,8,24))
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],R
def boot(v,days,k):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
J=json.load(open("/workspace/uplift_2026-09-11/r2/JUDGE_r2.json")); sp=J["span"]
A0P="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A0P2="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz"
res={}
k=500
for A0p,seed in [(A0P,"s42"),(A0P2,"s2027")]:
    t0,g0,R0=load(A0p,"d30_n2_c42_rec")
    for tag in sys.argv[1:]:
        f="/workspace/uplift_2026-09-11/r2/arms/%s.npz"%tag
        if not os.path.exists(f): f="/workspace/uplift_2026-09-11/trackD_v4/%s.npz"%tag
        ts,g,R=load(f)
        keep=(R[:,C["w3_fund"]]>0.999)&(R[:,C["gross_total"]]>1e-12)
        ts=ts[keep]; g=g[keep]
        ca,ia,ib=np.intersect1d(ts,t0,return_indices=True)
        m=(ca>=FULL[0])&(ca<FULL[1])
        gs=g[ia[m]]; ga=g0[ib[m]]; days=ca[m]//86400
        e={"n":int(m.sum()),"A0_sharpe":float(ga.mean()/ga.std(ddof=1)*np.sqrt(APY)),
           "sleeve_sharpe":float(gs.mean()/gs.std(ddof=1)*np.sqrt(APY)),
           "corr":float(np.corrcoef(gs,ga)[0,1])}
        for w in (0.25,0.5):
            gb=(1-w)*ga+w*gs; d=gb-ga
            lo,hi,p=boot(d,days,k); k+=1
            e["w%.2f"%w]={"blend_sharpe":float(gb.mean()/gb.std(ddof=1)*np.sqrt(APY)),
                          "d_mean":float(d.mean()),"ci95":[round(lo,4),round(hi,4)],"p_pos":p}
        ms=(ts>=STRESS[0])&(ts<STRESS[1])
        e["stress"]={"n":int(ms.sum()),"mean":float(g[ms].mean()) if ms.sum() else None}
        res.setdefault(tag,{})[seed]=e
        print("%-28s %-6s n=%d sleeveSh %+.2f corr %+.3f | w.25 Sh %+.2f d %+.4f %s | w.50 Sh %+.2f d %+.4f %s | stress n=%d %s"%(
            tag,seed,e["n"],e["sleeve_sharpe"],e["corr"],
            e["w0.25"]["blend_sharpe"],e["w0.25"]["d_mean"],e["w0.25"]["ci95"],
            e["w0.50"]["blend_sharpe"],e["w0.50"]["d_mean"],e["w0.50"]["ci95"],
            e["stress"]["n"],("%+.3f"%e["stress"]["mean"]) if e["stress"]["mean"] is not None else "na"),flush=True)
json.dump(res,open("/workspace/uplift_2026-09-11/r2/BLEND_r2.json","w"),indent=1)
