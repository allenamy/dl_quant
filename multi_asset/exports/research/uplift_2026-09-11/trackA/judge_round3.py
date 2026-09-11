"""round 3: FT00S (AMENDMENT 2) and the fixed-seat robustness read. Statistics identical to judge_uplift.py / judge_v4.py."""
import numpy as np, json, calendar, time
U="/workspace/uplift_2026-09-11"; PA=f"{U}/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
WIN={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1),"frozen":FROZEN,"2024-01->08-10":(T(2024,1,1),T(2026,8,10,20)+1)}
def boot(v,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def load(tag):
    A=np.load(f"{PA}/w10_ablation_series_{tag}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64); return ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],R,A
OUT={}
print("%-10s %-4s %-5s %9s %22s %6s %9s %9s %9s %8s %8s" % ("arm","seat","seed","D bps","CI95","P>0","Dpnl","Dcarry","Dcost","turn%","Sharpe"))
for ci,(arm,base,seat) in enumerate([("FT00S","A0","dyn"),("FT00","A0","dyn"),("FT00_fix","A0_fix","fix")]):
    for s in ("42","2027"):
        ta,ga,Ra,_=load(f"{arm}_{'dyn_s' if seat=='dyn' else 's'}{s}" if arm!="FT00_fix" else f"FT00_fix_s{s}")
        tb,gb,Rb,_=load(f"{base}_dyn_s{s}" if seat=="dyn" else f"A0_fix_s{s}")
        assert np.array_equal(ta,tb)
        m=(ta>=FROZEN[0])&(ta<FROZEN[1]); d=(ga-gb)[m]
        lo,hi,p=boot(d,ta[m]//86400,np.random.default_rng([20260905,20+ci]))
        dp=((Ra[:,C["pnl_ex"]]-Rb[:,C["pnl_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        dk=((Ra[:,C["carry_ex"]]-Rb[:,C["carry_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        dq=((Ra[:,C["cost_ex"]]-Rb[:,C["cost_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        tu=float(Ra[m,C["turnover"]].mean()/Rb[m,C["turnover"]].mean()-1)*100
        shA=float(ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(APY)); shB=float(gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(APY))
        yr={w:float((ga-gb)[(ta>=a)&(ta<b)].mean()) for w,(a,b) in WIN.items() if ((ta>=a)&(ta<b)).sum()>10}
        lv={w:float(ga[(ta>=a)&(ta<b)].mean()) for w,(a,b) in WIN.items() if ((ta>=a)&(ta<b)).sum()>10}
        mdd=lambda v:(lambda c:float(np.max(np.maximum.accumulate(c)-c)))(np.concatenate([[0.],np.cumsum(v)]))
        OUT[f"{arm}|{seat}|s{s}"]={"delta":float(d.mean()),"ci95":[lo,hi],"p_gt0":p,"d_pnl":float(dp),"d_carry":float(dk),"d_cost":float(dq),
            "turnover_pct":tu,"sharpe_arm":shA,"sharpe_base":shB,"level_arm":float(ga[m].mean()),"level_base":float(gb[m].mean()),
            "maxdd_arm":mdd(ga[m]),"maxdd_base":mdd(gb[m]),"delta_by_window":yr,"levels_arm":lv,"rng":[20260905,20+ci]}
        print("%-10s %-4s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f %+9.4f %+9.4f %+9.4f %+7.1f%% %.2f->%.2f" % (arm,seat,s,d.mean(),lo,hi,p,dp,dk,dq,tu,shB,shA))
print("\n== per-window Dg, s42/s2027 ==")
hdr=["2022","2023","2024","2025","2026->08-10","frozen","2024-01->08-10"]
print("%-10s "%"arm"+" ".join("%16s"%h for h in hdr))
for arm,seat in [("FT00S","dyn"),("FT00","dyn"),("FT00_fix","fix")]:
    print("%-10s "%arm+" ".join("%16s"%("%+.3f/%+.3f"%(OUT[f"{arm}|{seat}|s42"]["delta_by_window"].get(h,float('nan')),OUT[f"{arm}|{seat}|s2027"]["delta_by_window"].get(h,float('nan')))) for h in hdr))
print("\n== levels: A0 vs FT00S (dyn), bps/anchor/gross ==")
for w in hdr:
    a=OUT["FT00S|dyn|s42"]["levels_arm"].get(w); b=a-OUT["FT00S|dyn|s42"]["delta_by_window"].get(w,0) if a is not None else None
    if a is not None: print("%-16s A0 %+7.4f -> FT00S %+7.4f" % (w,b,a))
print("\nfrozen maxDD bps gross: A0 %.0f -> FT00S %.0f (s42); Sharpe %.2f -> %.2f" % (OUT["FT00S|dyn|s42"]["maxdd_base"],OUT["FT00S|dyn|s42"]["maxdd_arm"],OUT["FT00S|dyn|s42"]["sharpe_base"],OUT["FT00S|dyn|s42"]["sharpe_arm"]))
json.dump(OUT,open(f"{U}/RESULT_trackA_round3.json","w"),indent=1); print("written RESULT_trackA_round3.json")
