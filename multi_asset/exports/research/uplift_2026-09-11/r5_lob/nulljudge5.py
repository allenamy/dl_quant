"""Turnover-matched nulls: does the real arm beat SHIFT101/503/1009 and RELAB on BOTH pnl_ex (gross)
and g (net)? Nulls preserve the per-anchor rank distribution and the lag-1 persistence exactly."""
import numpy as np, calendar, json, glob, os
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
 "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
R="/workspace/uplift_2026-09-11/r5_lob"; END=T(2026,8,10,20)+1
tA=np.round(np.asarray(np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz",allow_pickle=True)["rec"],float)[:,0]).astype(np.int64)
POSTWARM=tA[900]
def getF(tg):
    A=np.load(R+"/out/%s.npz"%tg,allow_pickle=True); Rr=np.asarray(A["rec"],float)
    t=np.round(Rr[:,0]).astype(np.int64); F=np.full((len(tA),Rr.shape[1]),np.nan)
    F[np.searchsorted(tA,t)]=Rr; return F
tags=[os.path.basename(p)[:-4] for p in glob.glob(R+"/out/*.npz")]
live=np.ones(len(tA),bool)
for tg in tags:
    if tg.startswith("NULL_"): continue
    F=getF(tg); live&=np.isfinite(F[:,C["net_ex"]])&(np.nan_to_num(F[:,C["gross_total"]],nan=0.0)>1e-9)
M=live&(tA>=POSTWARM)&(tA<END)
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
def boot(v,d,seed,B=2000):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5))
day=tA[M]//86400
out={}
print("COMMON n=%d   (nulls evaluated on the SAME anchors as the real arm)"%M.sum())
for real in ["R5_PSKEW__m","R5_BLEAD__p"]:
    FR=getF(real); gR=FR[:,C["net_ex"]]/FR[:,C["gross_total"]]; pR=FR[:,C["pnl_ex"]]/FR[:,C["gross_total"]]
    print()
    print("%-30s %9s %9s %8s %8s"%("arm / null","pnl_ex","g(net)","SR(net)","turn"))
    print("%-30s %+9.4f %+9.4f %+8.3f %8.4f"%("REAL "+real,pR[M].mean(),gR[M].mean(),sh(gR[M]),FR[M,C["turnover"]].mean()))
    rec={"real":{"pnl_ex":round(float(pR[M].mean()),4),"g":round(float(gR[M].mean()),4),
                 "SR":round(float(sh(gR[M])),3),"turn":round(float(FR[M,C["turnover"]].mean()),5)},"nulls":{}}
    beats_p=True; beats_g=True
    for nl in ["SHIFT101","SHIFT503","SHIFT1009","RELAB1"]:
        tg="NULL_%s_%s"%(real,nl)
        FN=getF(tg); gN=FN[:,C["net_ex"]]/FN[:,C["gross_total"]]; pN=FN[:,C["pnl_ex"]]/FN[:,C["gross_total"]]
        mm=M&np.isfinite(gN)
        d=gR[mm]-gN[mm]; ci=boot(d,tA[mm]//86400,hash(tg)%9973)
        print("%-30s %+9.4f %+9.4f %+8.3f %8.4f   dG %+0.4f CI95[%+0.4f,%+0.4f]"%(
          "  null "+nl,pN[mm].mean(),gN[mm].mean(),sh(gN[mm]),FN[mm,C["turnover"]].mean(),d.mean(),ci[0],ci[1]))
        rec["nulls"][nl]={"pnl_ex":round(float(pN[mm].mean()),4),"g":round(float(gN[mm].mean()),4),
            "SR":round(float(sh(gN[mm])),3),"turn":round(float(FN[mm,C["turnover"]].mean()),5),
            "dG_real_minus_null":round(float(d.mean()),4),"dG_ci95":[round(ci[0],4),round(ci[1],4)],
            "real_beats_on_g_CI_excludes_0":bool(ci[0]>0)}
        beats_p&= (pR[mm].mean()>pN[mm].mean()); beats_g&= (ci[0]>0)
    rec["beats_all_nulls_pnl_ex_point"]=bool(beats_p)
    rec["beats_all_nulls_g_CI95"]=bool(beats_g)
    print("  -> beats all 4 nulls on pnl_ex (point): %s | on g with CI95 excluding 0: %s"%(beats_p,beats_g))
    out[real]=rec
json.dump(out,open(R+"/NULLS_r5.json","w"),indent=1)
