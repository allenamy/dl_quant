import numpy as np, calendar, time, json
P="/workspace/uplift_2026-09-11/probe_artifacts/"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def L(nm):
    A=np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64),R,A
def bstat(fn,ga,gb,days,k,nb=2000):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    pos=[np.where(inv==i)[0] for i in range(nd)]
    rng=np.random.default_rng([20260905,k]); out=np.empty(nb)
    for i in range(nb):
        pick=rng.integers(0,nd,nd); sel=np.concatenate([pos[p] for p in pick])
        out[i]=fn(ga[sel],gb[sel])
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5)),float((out>0).mean())
SH=lambda a: a.mean()/a.std(ddof=1)*np.sqrt(2190)
WINS={"FULL 2022-01-31->2026-08-31":(0,4e9),
      "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
      "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-31":(T(2026,1,1),4e9),
      "frozen":(T(2025,3,1),T(2026,8,10,20)+1),
      "pre-2025 (2022-2024)":(T(2022,1,1),T(2025,1,1))}
print("="*118)
print("ATTACK: CROSS-REGIME READ. The user's goal is Sharpe >> 3.0 IN DIFFERENT REGIMES.")
print("        The frozen window is 64% 2026. Here is A0 and FT00S on every window, both seeds.")
print("="*118)
print("%-28s %5s | %8s %8s %7s | %8s %8s %7s | %9s %22s %6s"%("window","n","A0 g","A0 Sh","A0 SE","FT g","FT Sh","FT SE","dG","dG CI95","P>0"))
for s in ("42","2027"):
    print(f"--- seed {s} ---")
    ta,Ra,_=L(f"A0_dyn_s{s}"); tb,Rb,_=L(f"FT00S_dyn_s{s}")
    ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
    for w,(lo,hi) in WINS.items():
        m=(ta>=lo)&(ta<hi); n=int(m.sum())
        if n<50: continue
        a=ga[m]; b=gb[m]; se=np.sqrt(2190/n)
        clo,chi,p=bstat(lambda x,y:(y-x).mean(),a,b,ta[m]//86400,7)
        print("%-28s %5d | %+8.4f %8.2f %7.2f | %+8.4f %8.2f %7.2f | %+9.4f [%+8.4f,%+8.4f] %6.3f"%(
            w,n,a.mean(),SH(a),se,b.mean(),SH(b),se,(b-a).mean(),clo,chi,p))
    # dSharpe full history
    for w in ("FULL 2022-01-31->2026-08-31","pre-2025 (2022-2024)"):
        lo,hi=WINS[w]; m=(ta>=lo)&(ta<hi)
        clo,chi,p=bstat(lambda x,y:SH(y)-SH(x),ga[m],gb[m],ta[m]//86400,8)
        print("   dSharpe %-24s = %+.3f  CI95[%+.3f,%+.3f] P>0=%.3f"%(w,SH(gb[m])-SH(ga[m]),clo,chi,p))
