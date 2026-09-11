"""Round-2 sleeve judge. Statistic copied from judge_v4: g = net_ex/gross_total, bps per anchor per unit
gross; UTC-day block bootstrap, rng default_rng([20260905,k]). Gates frozen in PREREG_r2_sleeve_family."""
import numpy as np, calendar, os, sys, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
R="/workspace/uplift_2026-09-11/r2_sleeve"; OUT=R+"/out"
FULL=(T(2022,1,31),T(2026,8,31)+1)          # device-native axis, n=10039
R1FULL=(T(2022,1,1),T(2026,8,10,20)+1)      # round-1 comparability window, n=9918
FROZ=(T(2025,3,1),T(2026,8,10,20)+1)
EXT=(T(2026,8,11),T(2026,8,31)+1)
YR={y:(T(y,1,1),T(y+1,1,1)) for y in [2022,2023,2024,2025,2026]}
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); Rr=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(Rr[:,0]).astype(np.int64),Rr
def boot(v,d,seed,B=2000,K=16):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    a=0.05/K
    return (np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,100*a/2),np.percentile(mn,100*(1-a/2)),(mn>0).mean())
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
t0,A0=load(R+"/pa/w10_ablation_series_GATEP_A0_dyn_s42.npz","d30_n2_c42_rec")
g0=A0[:,C["net_ex"]]/A0[:,C["gross_total"]]
def rows(tags,seedbase=101):
    res={}
    print("%-22s %8s %7s %8s %8s %8s %7s %7s %7s | %s"%("arm","mean","Sharpe","CI95lo","CI95hi","BONF16lo","corrA0","carry/net","turn","per-year bps"))
    for i,(nm,p) in enumerate(tags):
        if not os.path.exists(p): print("%-22s MISSING"%nm); continue
        ts,Rr=load(p); g=Rr[:,C["net_ex"]]/Rr[:,C["gross_total"]]
        m=(ts>=FULL[0])&(ts<FULL[1])
        lo,hi,blo,bhi,pp=boot(g[m],ts[m]//86400,seedbase+i)
        _,ia,ib=np.intersect1d(t0,ts,return_indices=True)
        mm=(t0[ia]>=FULL[0])&(t0[ia]<FULL[1])
        cor=np.corrcoef(g0[ia][mm],g[ib][mm])[0,1]
        car=Rr[m,C["carry_ex"]].sum()/Rr[m,C["gross_total"]][m*0+np.arange(len(ts))[m]].sum() if False else (Rr[m,C["carry_ex"]]/Rr[m,C["gross_total"]]).mean()
        net=g[m].mean()
        yrs=[]; npos=0
        for y in YR:
            k=(ts>=YR[y][0])&(ts<YR[y][1])
            if k.sum()>50: yrs.append(g[k].mean()); npos+= (g[k].mean()>0)
        res[nm]=dict(mean=float(net),sharpe=float(sh(g[m])),ci=[float(lo),float(hi)],bonf=[float(blo),float(bhi)],
                     corrA0=float(cor),carry_frac=float(car/net) if net!=0 else float("nan"),
                     turn=float(Rr[m,C["turnover"]].mean()),years=[float(x) for x in yrs],npos=int(npos),
                     froz=float(g[(ts>=FROZ[0])&(ts<FROZ[1])].mean()),
                     ext=float(g[(ts>=EXT[0])&(ts<EXT[1])].mean()),
                     r1full=float(g[(ts>=R1FULL[0])&(ts<R1FULL[1])].mean()),
                     r1sharpe=float(sh(g[(ts>=R1FULL[0])&(ts<R1FULL[1])])))
        print("%-22s %+8.3f %7.2f %+8.3f %+8.3f %+8.3f %+7.3f %7.2f %7.4f | %s  %d/5+"%(
            nm,net,sh(g[m]),lo,hi,blo,cor,res[nm]["carry_frac"],res[nm]["turn"],
            " ".join("%+.2f"%x for x in yrs),res[nm]["npos"]))
    return res
if __name__=="__main__":
    tags=sorted([(f[:-4],OUT+"/"+f) for f in os.listdir(OUT) if f.endswith(".npz")])
    r=rows(tags)
    json.dump(r,open(R+"/RESULT_r2_screen.json","w"),indent=1)
    print()
    print("A0 reference: FULL(n=%d) %+0.3f Sharpe %.2f | R1FULL %+0.3f Sharpe %.2f"%(
      ((t0>=FULL[0])&(t0<FULL[1])).sum(), g0[(t0>=FULL[0])&(t0<FULL[1])].mean(), sh(g0[(t0>=FULL[0])&(t0<FULL[1])]),
      g0[(t0>=R1FULL[0])&(t0<R1FULL[1])].mean(), sh(g0[(t0>=R1FULL[0])&(t0<R1FULL[1])])))
