import numpy as np, calendar, time
P="/workspace/uplift_2026-09-11/probe_artifacts/"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
WIN={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1),"frozen":FROZEN}
def L(nm):
    A=np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64),R,A
def boot_pairs(v,days,k,nb=2000):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    rng=np.random.default_rng([20260905,k]); idx=rng.integers(0,nd,size=(nb,nd))
    mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def boot_sharpe(ga,gb,days,k,nb=2000):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    rng=np.random.default_rng([20260905,k]); out=np.empty(nb)
    pos={d:np.where(inv==i)[0] for i,d in enumerate(ud)}
    for i in range(nb):
        pick=rng.integers(0,nd,nd); sel=np.concatenate([pos[ud[p]] for p in pick])
        a=ga[sel]; b=gb[sel]
        out[i]=a.mean()/a.std(ddof=1)*np.sqrt(2190)-b.mean()/b.std(ddof=1)*np.sqrt(2190)
    return float(out.mean()),float(np.percentile(out,2.5)),float(np.percentile(out,97.5)),float((out>0).mean())

print("="*100)
print("ATTACK: judge-consistent component decomposition (each arm divided by its OWN gross, as g is)")
print("="*100)
for arm in ("FT00S","FT00","FT00S3","FT00S12"):
    for s in ("42","2027"):
        ta,Ra,_=L(f"{arm}_dyn_s{s}"); tb,Rb,_=L(f"A0_dyn_s{s}")
        assert np.array_equal(ta,tb)
        m=(ta>=FROZEN[0])&(ta<FROZEN[1])
        ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
        d=(ga-gb)[m]
        # correct decomposition
        comp={}
        for nm,col in (("pnl","pnl_ex"),("carry","carry_ex"),("cost","cost_ex")):
            comp[nm]=((Ra[:,C[col]]/Ra[:,C["gross_total"]])-(Rb[:,C[col]]/Rb[:,C["gross_total"]]))[m].mean()
        # THEIR decomposition (both over A0 gross)
        theirs={}
        for nm,col in (("pnl","pnl_ex"),("carry","carry_ex"),("cost","cost_ex")):
            theirs[nm]=((Ra[:,C[col]]-Rb[:,C[col]])/Rb[:,C["gross_total"]])[m].mean()
        lo,hi,p=boot_pairs(d,ta[m]//86400,20)
        ds,slo,shi,sp=boot_sharpe(ga[m],gb[m],ta[m]//86400,20)
        print(f"\n{arm} s{s}: delta={d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] P>0={p:.3f}")
        print(f"   CORRECT decomp (own-gross): dpnl {comp['pnl']:+.4f}  dcarry {comp['carry']:+.4f}  dcost {comp['cost']:+.4f}  -> sum {comp['pnl']-comp['carry']-comp['cost']:+.4f}")
        print(f"   THEIR   decomp (A0-gross) : dpnl {theirs['pnl']:+.4f}  dcarry {theirs['carry']:+.4f}  dcost {theirs['cost']:+.4f}  -> sum {theirs['pnl']-theirs['carry']-theirs['cost']:+.4f}")
        print(f"   gross_total A0 {Rb[m,C['gross_total']].mean():.5f} -> arm {Ra[m,C['gross_total']].mean():.5f}  ({100*(Ra[m,C['gross_total']].mean()/Rb[m,C['gross_total']].mean()-1):+.2f}%)")
        print(f"   dSharpe={ds:+.3f} CI[{slo:+.3f},{shi:+.3f}] P>0={sp:.3f}")
        print("   per-window d: "+"  ".join(f"{w} {((ga-gb)[(ta>=a)&(ta<b)]).mean():+.3f}" for w,(a,b) in WIN.items()))
