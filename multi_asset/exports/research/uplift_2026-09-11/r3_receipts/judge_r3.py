"""Round-3 judge. Statistic copied verbatim from judge_r2.py / judge_v4.py:
g = net_ex/gross_total [bps/anchor/unit gross]; UTC-day block bootstrap 2000, rng default_rng([20260905,k]).
PAIRING RULE (PREREG_r3 S1): the arm at seed s is ALWAYS paired against A0 at the SAME seed s.
POST-WARM (E-0911-A): the first LOOK=900 anchors have w3 forced to [1/3,1/3,1/3] with the LEGS mask
bypassed; they are not the arm under test. full_nowarm drops them. The warm ts set is taken from the
A0 rec itself and applied to BOTH sides so the two series are on identical anchors.
Bootstrap sub-stream key = sha1(name) (round-2 self-declared defect: traversal-order keys make a CI
depend on which other arms are in the directory). K declared = 2 (PREREG_r3 S1)."""
import numpy as np, json, calendar, os, glob, sys, hashlib
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
      "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190; WARM_COL=15
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
FULL  =(T(2022,1,1),T(2026,8,10,20)+1)
F23   =(T(2023,1,1),T(2026,8,10,20)+1)
EXT   =(T(2026,8,11),T(2026,9,1))
YRS={"2022H2":(T(2022,6,26),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
WINS=[("frozen",FROZEN),("full",FULL),("f23",F23),("ext",EXT)]+list(YRS.items())
R3="/workspace/uplift_2026-09-11/r3_resid"
def load(p,key=None):
    A=np.load(p,allow_pickle=True)
    R=A[key] if key and key in A.files else (A["rec"] if "rec" in A.files else A["d30_n2_c42_rec"])
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    return ts,g,R
def key(name): return int(hashlib.sha1(name.encode()).hexdigest()[:6],16)
def boot(v,days,name,n=2000):
    rng=np.random.default_rng([20260905,key(name)])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean()),mn
def bootSR(a,b,days,name,n=2000):
    rng=np.random.default_rng([20260905,key(name)+1])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]
    ib=rng.integers(0,nd,size=(n,nd)); out=[]
    for r in range(n):
        sel=np.concatenate([grp[z] for z in ib[r]])
        x=a[sel]; y=b[sel]
        if x.std(ddof=1)>0 and y.std(ddof=1)>0:
            out.append(x.mean()/x.std(ddof=1)*np.sqrt(APY)-y.mean()/y.std(ddof=1)*np.sqrt(APY))
    out=np.array(out)
    return out
def bonf(mn,K):
    a=100.0*(0.05/K)/2.0
    return float(np.percentile(mn,a)),float(np.percentile(mn,100-a))
def SR(v): return float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else None
def stats(ts,g,R,lo,hi,keep=None):
    m=(ts>=lo)&(ts<hi)
    if keep is not None: m=m&keep
    if m.sum()<3: return None
    v=g[m]; c=np.concatenate([[0.0],np.cumsum(v)])
    gt=R[m,C["gross_total"]]; net=R[m,C["net_ex"]]; pnl=R[m,C["pnl_ex"]]
    car=R[m,C["carry_ex"]]; cst=R[m,C["cost_ex"]]
    return {"n":int(m.sum()),"mean":round(float(v.mean()),4),"sharpe":round(SR(v),3) if SR(v) is not None else None,
            "se_sharpe":round(float(np.sqrt(2190.0/m.sum())),3),
            "maxdd":round(float(np.max(np.maximum.accumulate(c)-c)),1),
            "turnover":round(float(R[m,C["turnover"]].mean()),5),
            "pnl_bps":round(float((pnl/gt).mean()),4),"carry_bps":round(float((car/gt).mean()),4),
            "cost_bps":round(float((cst/gt).mean()),4),
            "carry_frac_of_net":round(float((car/gt).mean()/v.mean()),3) if abs(v.mean())>1e-9 else None,
            "identity_maxabs":round(float(np.abs(net-(pnl-car-cst)).max()),9),
            "gross_mean":round(float(gt.mean()),4),"nsel_mean":round(float(R[m,C["nsel"]].mean()),1)}
if __name__=="__main__":
    K=int(os.environ.get("K","2"))
    A0P="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s%s.npz"
    A0={s:load(A0P%s,"d30_n2_c42_rec") for s in ("42","2027")}
    WARMTS={s:set(A0[s][0][np.abs(A0[s][2][:,WARM_COL])>1e-9].tolist()) for s in ("42","2027")}
    res={"K_declared":K,"warm_n":{s:len(WARMTS[s]) for s in WARMTS},"baseline":{},"arms":{}}
    for s in ("42","2027"):
        ts,g,R=A0[s]; keep=np.array([t not in WARMTS[s] for t in ts])
        res["baseline"]["A0_s"+s]={w:stats(ts,g,R,lo,hi) for w,(lo,hi) in WINS}
        res["baseline"]["A0_s"+s]["full_nowarm"]=stats(ts,g,R,FULL[0],FULL[1],keep=keep)
        res["baseline"]["A0_s"+s]["frozen_nowarm"]=stats(ts,g,R,FROZEN[0],FROZEN[1],keep=keep)
    # arm tag -> seed it is paired with
    PAIR=json.load(open(R3+"/pairing.json"))
    for f in sorted(glob.glob(R3+"/out/SL_*.npz")):
        tag=os.path.basename(f)[:-4]
        nm=tag[3:]
        s=PAIR.get(nm)
        if s is None: print("no pairing for",nm); continue
        t0,g0,R0=A0[s]
        ts,g,R=load(f)
        keepA=np.array([t not in WARMTS[s] for t in ts])
        e={w:stats(ts,g,R,lo,hi,keep=keepA) for w,(lo,hi) in WINS}   # ALL windows post-warm
        e["_paired_with"]="A0_s"+s
        e["full_withwarm"]=stats(ts,g,R,FULL[0],FULL[1])
        ca,ia,ib=np.intersect1d(ts,t0,return_indices=True)
        for nmw,(lo,hi) in (("full",FULL),("f23",F23),("frozen",FROZEN)):
            sel=(ca>=lo)&(ca<hi)&np.array([t not in WARMTS[s] for t in ca])
            gg=g[ia[sel]]; g00=g0[ib[sel]]
            ok=np.isfinite(gg)&np.isfinite(g00)
            e["corr_"+nmw]=round(float(np.corrcoef(gg[ok],g00[ok])[0,1]),4) if ok.sum()>10 else None
        for nmw,(lo,hi) in (("full",FULL),("f23",F23),("frozen",FROZEN)):
            m=(ts>=lo)&(ts<hi)&keepA
            if m.sum()>50:
                lo_,hi_,p_,mn=boot(g[m],ts[m]//86400,tag+"_lvl_"+nmw)
                bl,bh=bonf(mn,K)
                e["ci_"+nmw]={"n":int(m.sum()),"ci95":[round(lo_,4),round(hi_,4)],"p_pos":p_,"bonf%d"%K:[round(bl,4),round(bh,4)]}
        # ---- PAIRED contrast: equal-gross 50/50 blend with A0 AT THE SAME SEED ----
        for nmw,(lo,hi) in (("full",FULL),("frozen",FROZEN),("f23",F23)):
            sel=(ca>=lo)&(ca<hi)&np.array([t not in WARMTS[s] for t in ca])
            gb=0.5*g[ia[sel]]+0.5*g0[ib[sel]]; ga=g0[ib[sel]]
            ok=np.isfinite(gb)&np.isfinite(ga)
            if ok.sum()<50: continue
            gb=gb[ok]; ga=ga[ok]; dts=ca[sel][ok]
            d=gb-ga
            lo_,hi_,p_,mn=boot(d,dts//86400,tag+"_dmean_"+nmw)
            bl,bh=bonf(mn,K)
            dsh=bootSR(gb,ga,dts//86400,tag+"_dSR_"+nmw)
            a_,b_=bonf(dsh,K)
            e["paired_"+nmw]={"n":int(ok.sum()),
                "A0_sharpe":round(SR(ga),3),"blend_sharpe":round(SR(gb),3),
                "A0_mean":round(float(ga.mean()),4),"blend_mean":round(float(gb.mean()),4),
                "dmean":round(float(d.mean()),4),"dmean_ci95":[round(lo_,4),round(hi_,4)],
                "dmean_bonf%d"%K:[round(bl,4),round(bh,4)],"dmean_p_pos":p_,
                "dSharpe":round(SR(gb)-SR(ga),3),
                "dSharpe_ci95":[round(float(np.percentile(dsh,2.5)),3),round(float(np.percentile(dsh,97.5)),3)],
                "dSharpe_bonf%d"%K:[round(a_,3),round(b_,3)],
                "dSharpe_p_pos":round(float((dsh>0).mean()),4)}
        res["arms"][tag]=e
    json.dump(res,open(R3+"/out/JUDGE_r3.json","w"),indent=1)
    print("%-24s %6s %8s %7s %8s %7s %7s %9s"%("arm","pair","full_mean","full_SR","froz_SR","corrF","turn","dSR_full"))
    for tag,e in sorted(res["arms"].items()):
        a=e.get("full") or {}; fz=e.get("frozen") or {}
        pf=e.get("paired_full") or {}
        print("%-24s %6s %8s %7s %8s %7s %7s %9s"%(tag,e["_paired_with"][-4:],a.get("mean"),a.get("sharpe"),
              fz.get("sharpe"),e.get("corr_full"),a.get("turnover"),pf.get("dSharpe")))
    for s in ("42","2027"):
        bb=res["baseline"]["A0_s"+s]
        print("A0_s%-20s %6s %8s %7s %8s"%(s,s,bb["full_nowarm"]["mean"],bb["full_nowarm"]["sharpe"],bb["frozen_nowarm"]["sharpe"]))
