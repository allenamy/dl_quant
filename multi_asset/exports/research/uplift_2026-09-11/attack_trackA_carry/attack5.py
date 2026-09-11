import numpy as np, calendar, json
P="/workspace/uplift_2026-09-11/probe_artifacts/"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def L(nm):
    A=np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64),R,A
SH=lambda a: a.mean()/a.std(ddof=1)*np.sqrt(2190)
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
    "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-31":(T(2026,1,1),4e9),"FULL":(0,4e9),"pre2025":(T(2022,1,1),T(2025,1,1))}
print("="*110)
print("PER-REGIME SHARPE, every Track-A arm vs A0 (dyn, s42/s2027). Sharpe SE per year ~1.00, FULL ~0.47")
print("="*110)
arms=["FT00S","FT00","FT00S3","FT00S12","FT05","FT30","NOFTRIM","LT10","CD1","FTPOS"]
hdr="%-9s %-5s "%("arm","seed")+" ".join("%14s"%y for y in YR)
print(hdr)
for a in arms:
    for s in ("42","2027"):
        try: ta,Ra,_=L(f"{a}_dyn_s{s}")
        except Exception: continue
        tb,Rb,_=L(f"A0_dyn_s{s}")
        ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
        row="%-9s %-5s "%(a,s)
        for y,(lo,hi) in YR.items():
            m=(ta>=lo)&(ta<hi)
            row+="%14s"%("%.2f->%.2f"%(SH(gb[m]),SH(ga[m])))
        print(row)
print()
print("baseline A0 Sharpe: "+" ".join("%s=%.2f"%(y,SH((lambda m: (lambda R: R[m,C['net_ex']]/R[m,C['gross_total']])(L('A0_dyn_s42')[1]))((L('A0_dyn_s42')[0]>=lo)&(L('A0_dyn_s42')[0]<hi)))) for y,(lo,hi) in YR.items()))
print()
print("="*110)
print("CANDIDATE-3 FALSIFIER (they declined to run it): the 6.3x short/long sleeve efficiency, PER YEAR")
print("  efficiency = sleeve net (pnl-carry-cost, bps per unit TOTAL gross) / sleeve gross share")
print("="*110)
for s in ("42","2027"):
    ts,R,A=L(f"A0_dyn_s{s}")
    nm=[str(x) for x in A["d30_n2_c42_SLV_names"]]
    gt=R[:,C["gross_total"]]
    G=A["d30_n2_c42_SLV_gross"]/gt[:,None]; Pn=A["d30_n2_c42_SLV_pnl"]/gt[:,None]
    K=A["d30_n2_c42_SLV_carry"]/gt[:,None]; Q=A["d30_n2_c42_SLV_cost"]/gt[:,None]
    NET=Pn-K-Q
    # find indices: names
    print(f"\n--- seed {s} --- sleeve names: {nm}")
    want=[i for i,x in enumerate(nm)]
    print("%-12s %-10s "%("sleeve","stat")+" ".join("%12s"%y for y in YR))
    for i in want:
        gs=[]; ef=[]
        for y,(lo,hi) in YR.items():
            m=(ts>=lo)&(ts<hi)
            gsh=G[m,i].mean(); net=NET[m,i].mean()
            gs.append(gsh); ef.append(net/gsh if gsh>1e-4 else float('nan'))
        print("%-12s %-10s "%(nm[i],"gross%")+" ".join("%12.2f"%(x*100) for x in gs))
        print("%-12s %-10s "%("","eff bps")+" ".join("%12.2f"%x for x in ef))
