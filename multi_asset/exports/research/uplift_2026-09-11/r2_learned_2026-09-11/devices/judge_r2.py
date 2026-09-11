"""Round-2 judge. Statistic copied verbatim from judge_v4 via round-1 judgeD.py:
g = net_ex/gross_total [bps/anchor/unit gross]; UTC-day block bootstrap 2000, rng default_rng([20260905,k]).
Learned sleeves have NO 2022 predictions (walk-forward cannot fit before the panel starts), so every
sleeve reading and every A0 comparison is ALSO reported on the common span 2023-01-01 -> 2026-08-10.
"""
import numpy as np, json, calendar, os, glob, sys
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
      "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
FULL  =(T(2022,1,1),T(2026,8,10,20)+1)
F23   =(T(2023,1,1),T(2026,8,10,20)+1)      # common span for walk-forward sleeves
W24   =(T(2024,1,1),T(2026,8,10,20)+1)
EXT   =(T(2026,8,11),T(2026,9,1))           # out-of-fit stress window
YRS={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
WINS=[("frozen",FROZEN),("full",FULL),("f23",F23),("2024on",W24),("ext",EXT)]+list(YRS.items())
def load(p,key=None):
    A=np.load(p,allow_pickle=True)
    R=A[key] if key and key in A.files else (A["rec"] if "rec" in A.files else A["d30_n2_c42_rec"])
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    return ts,g,R
def boot(v,days,k,n=2000):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean()),mn
def bonf(mn,K):
    a=100.0*(0.05/K)/2.0
    return float(np.percentile(mn,a)),float(np.percentile(mn,100-a))
WARM_COL=15   # w3_rev24 : non-zero <=> the LOOK=900 seat warm-up is still running and the leg mask is
              # OVERRIDDEN to [1/3,1/3,1/3]. Verified 2026-09-11: 900 anchors 2022-01-31..2022-06-29 in
              # EVERY arm incl. A0 and round-1 trackD sleeves. Those rows are NOT the arm under test.
def stats(ts,g,R,lo,hi,drop_warm=False):
    m=(ts>=lo)&(ts<hi)
    if drop_warm: m=m&(np.abs(R[:,WARM_COL])<1e-9)
    if m.sum()<3: return None
    v=g[m]; c=np.concatenate([[0.0],np.cumsum(v)])
    gt=R[m,C["gross_total"]]
    net=R[m,C["net_ex"]]; pnl=R[m,C["pnl_ex"]]; car=R[m,C["carry_ex"]]; cst=R[m,C["cost_ex"]]
    ident=float(np.abs(net-(pnl-car-cst)).max())
    return {"n":int(m.sum()),"mean":round(float(v.mean()),4),
            "sharpe":round(float(v.mean()/v.std(ddof=1)*np.sqrt(APY)),3) if v.std(ddof=1)>0 else None,
            "se_sharpe":round(float(np.sqrt(2190.0/m.sum())),3),
            "maxdd":round(float(np.max(np.maximum.accumulate(c)-c)),1),
            "turnover":round(float(R[m,C["turnover"]].mean()),5),
            "pnl_bps":round(float((pnl/gt).mean()),4),
            "carry_bps":round(float((car/gt).mean()),4),
            "cost_bps":round(float((cst/gt).mean()),4),
            "carry_frac_of_net":round(float((car/gt).mean()/(v.mean())),3) if abs(v.mean())>1e-9 else None,
            "identity_maxabs":round(ident,9),
            "gross_mean":round(float(gt.mean()),4)}
if __name__=="__main__":
    K=int(os.environ.get("K","8"))
    OUT="/workspace/uplift_2026-09-11/r2_learned/out"
    A0={s:load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s%s.npz"%s,"d30_n2_c42_rec") for s in ("42","2027")}
    res={"K_declared":K,"baseline":{},"arms":{}}
    for s in ("42","2027"):
        ts,g,R=A0[s]
        res["baseline"]["A0_s"+s]={w:stats(ts,g,R,lo,hi) for w,(lo,hi) in WINS}
        res["baseline"]["A0_s"+s]["full_nowarm"]=stats(ts,g,R,FULL[0],FULL[1],drop_warm=True)
        res["baseline"]["A0_s"+s]["2022_nowarm"]=stats(ts,g,R,YRS["2022"][0],YRS["2022"][1],drop_warm=True)
    t0,g0,R0=A0["42"]
    files=sorted(glob.glob(OUT+"/SL*.npz"))
    k=100
    for f in files:
        tag=os.path.basename(f)[:-4]
        ts,g,R=load(f)
        e={w:stats(ts,g,R,lo,hi) for w,(lo,hi) in WINS}
        e["full_nowarm"]=stats(ts,g,R,FULL[0],FULL[1],drop_warm=True)
        e["2022_nowarm"]=stats(ts,g,R,YRS["2022"][0],YRS["2022"][1],drop_warm=True)
        ca,ia,ib=np.intersect1d(ts,t0,return_indices=True)
        for nm,(lo,hi) in (("corr_full",FULL),("corr_f23",F23),("corr_frozen",FROZEN),("corr_2024on",W24)):
            sel=(ca>=lo)&(ca<hi)
            gg=g[ia[sel]]; g00=g0[ib[sel]]
            ok=np.isfinite(gg)&np.isfinite(g00)
            e[nm]=round(float(np.corrcoef(gg[ok],g00[ok])[0,1]),4) if ok.sum()>10 else None
        for nm,(lo,hi) in (("ci_full",FULL),("ci_f23",F23)):
            m=(ts>=lo)&(ts<hi)
            if m.sum()>50:
                lo_,hi_,p_,mn=boot(g[m],ts[m]//86400,k); k+=1
                bl,bh=bonf(mn,K)
                e[nm]={"ci95":[round(lo_,4),round(hi_,4)],"p_pos":p_,"bonf%d"%K:[round(bl,4),round(bh,4)]}
        # equal-gross 50/50 blend with A0 on the common span
        sel=(ca>=F23[0])&(ca<F23[1])
        gb=0.5*g[ia[sel]]+0.5*g0[ib[sel]]; ga=g0[ib[sel]]
        ok=np.isfinite(gb)
        e["blend50_f23"]={"mean":round(float(gb[ok].mean()),4),
                          "sharpe":round(float(gb[ok].mean()/gb[ok].std(ddof=1)*np.sqrt(APY)),3),
                          "A0_same_span_sharpe":round(float(ga[ok].mean()/ga[ok].std(ddof=1)*np.sqrt(APY)),3)}
        d=gb[ok]-ga[ok]
        dts=ca[sel][ok]
        lo_,hi_,p_,mn=boot(d,dts//86400,k); k+=1
        bl,bh=bonf(mn,K)
        e["blend50_delta_vs_A0_f23"]={"mean":round(float(d.mean()),4),"ci95":[round(lo_,4),round(hi_,4)],
                                      "bonf%d"%K:[round(bl,4),round(bh,4)],"p_pos":p_}
        rng=np.random.default_rng([20260905,k]); k+=1
        dd=dts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
        ib_=rng.integers(0,nd,size=(2000,nd))
        dsh=[]
        for r_ in range(2000):
            sel_=np.concatenate([np.nonzero(inv==z)[0] for z in ib_[r_]])
            a_=gb[ok][sel_]; b_=ga[ok][sel_]
            if a_.std(ddof=1)>0 and b_.std(ddof=1)>0:
                dsh.append(a_.mean()/a_.std(ddof=1)*np.sqrt(APY)-b_.mean()/b_.std(ddof=1)*np.sqrt(APY))
        dsh=np.array(dsh)
        e["blend50_dSharpe_vs_A0_f23"]={"point":round(float(gb[ok].mean()/gb[ok].std(ddof=1)*np.sqrt(APY)-ga[ok].mean()/ga[ok].std(ddof=1)*np.sqrt(APY)),3),
                                        "ci95":[round(float(np.percentile(dsh,2.5)),3),round(float(np.percentile(dsh,97.5)),3)],
                                        "p_pos":round(float((dsh>0).mean()),4)}
        res["arms"][tag]=e
    json.dump(res,open(OUT+"/JUDGE_r2.json","w"),indent=1)
    # compact print
    print("%-26s %8s %7s %8s %7s %7s %7s %7s"%("arm","f23_mean","f23_SR","full_SR","corr","carryfr","turn","ci95lo"))
    for tag,e in sorted(res["arms"].items()):
        a=e.get("f23") or {}; b=e.get("full") or {}
        ci=(e.get("ci_f23") or {}).get("ci95",[None,None])
        print("%-26s %8s %7s %8s %7s %7s %7s %7s"%(tag,a.get("mean"),a.get("sharpe"),b.get("sharpe"),
              e.get("corr_f23"),a.get("carry_frac_of_net"),a.get("turnover"),ci[0]))
    for s in ("42","2027"):
        bb=res["baseline"]["A0_s"+s]
        print("A0_s%-22s %8s %7s %8s"%(s,bb["f23"]["mean"],bb["f23"]["sharpe"],bb["full"]["sharpe"]))
