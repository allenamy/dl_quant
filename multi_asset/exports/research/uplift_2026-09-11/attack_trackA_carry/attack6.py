import numpy as np, calendar
P="/workspace/uplift_2026-09-11/probe_artifacts/"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def L(nm):
    A=np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
    return np.round(R[:,0]).astype(np.int64),R,A
SH=lambda a: a.mean()/a.std(ddof=1)*np.sqrt(2190)
def bstat(fn,ga,gb,days,k,nb=2000):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud); pos=[np.where(inv==i)[0] for i in range(nd)]
    rng=np.random.default_rng([20260905,k]); out=np.empty(nb)
    for i in range(nb):
        sel=np.concatenate([pos[p] for p in rng.integers(0,nd,nd)]); out[i]=fn(ga[sel],gb[sel])
    return float(out.mean()),float(np.percentile(out,2.5)),float(np.percentile(out,97.5)),float((out>0).mean())

print("### 1. IS THE DYNAMIC SEAT AFFECTED BY THE ARM? (candidate's risk (a) says it is)")
for s in ("42","2027"):
    ta,Ra,_=L(f"A0_dyn_s{s}"); tb,Rb,_=L(f"FT00S_dyn_s{s}")
    for w in ("w3_king","w3_rev24","w3_fund"):
        print(f"  s{s} {w}: bitwise identical A0 vs FT00S = {np.array_equal(Ra[:,C[w]],Rb[:,C[w]])}   max|d|={np.abs(Ra[:,C[w]]-Rb[:,C[w]]).max():.3e}")
print()
print("### 2. WHERE DOES THE REPLAY'S 'DYNAMIC SEAT' SIT vs THE LIVE SEAT 0.21 king / 0.79 fund?")
ta,Ra,_=L("A0_dyn_s42")
for y,(lo,hi) in {"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),4e9),"frozen":(T(2025,3,1),T(2026,8,10,20)+1)}.items():
    m=(ta>=lo)&(ta<hi)
    print(f"  {y:8s} w3_king={Ra[m,C['w3_king']].mean():.4f}  w3_fund={Ra[m,C['w3_fund']].mean():.4f}  (live seat = 0.21 / 0.79)")
print()
print("### 3. FT00 (the one-constant arm): full-history + pre-2025 dG and dSharpe with CI")
for s in ("42","2027"):
    ta,Ra,_=L(f"FT00_dyn_s{s}"); tb,Rb,_=L(f"A0_dyn_s{s}")
    ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
    for w,(lo,hi) in {"FULL":(0,4e9),"pre2025":(T(2022,1,1),T(2025,1,1)),"frozen":(T(2025,3,1),T(2026,8,10,20)+1)}.items():
        m=(ta>=lo)&(ta<hi)
        _,l1,h1,p1=bstat(lambda x,y:(y-x).mean(),gb[m],ga[m],ta[m]//86400,9)
        _,l2,h2,p2=bstat(lambda x,y:SH(y)-SH(x),gb[m],ga[m],ta[m]//86400,9)
        print(f"  s{s} {w:8s} n={m.sum():5d}  dG={(ga-gb)[m].mean():+.4f} CI[{l1:+.4f},{h1:+.4f}] P>0={p1:.3f} | dSharpe={SH(ga[m])-SH(gb[m]):+.3f} CI[{l2:+.3f},{h2:+.3f}] P>0={p2:.3f}")
print()
print("### 4. IDENTITY CHECK on the candidate's reported decomposition (prereg GATE C says 'identity asserted')")
for s in ("42","2027"):
    ta,Ra,_=L(f"FT00S_dyn_s{s}"); tb,Rb,_=L(f"A0_dyn_s{s}")
    m=(ta>=T(2025,3,1))&(ta<T(2026,8,10,20)+1)
    d=((Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]])-(Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]))[m].mean()
    th={n:((Ra[:,C[c]]-Rb[:,C[c]])/Rb[:,C["gross_total"]])[m].mean() for n,c in (("pnl","pnl_ex"),("carry","carry_ex"),("cost","cost_ex"))}
    print(f"  s{s}: reported delta={d:+.4f}  but reported dpnl-dcarry-dcost = {th['pnl']-th['carry']-th['cost']:+.4f}  => RESIDUAL {th['pnl']-th['carry']-th['cost']-d:+.4f} ({100*abs(th['pnl']-th['carry']-th['cost']-d)/abs(d):.1f}% of the claimed effect)")
print()
print("### 5. COST RE-CHARGE at the re-audited 3.52 bps/unit-intent vs the device's fee-only blend")
ta,Ra,_=L("FT00S_dyn_s42"); tb,Rb,_=L("A0_dyn_s42")
m=(ta>=T(2025,3,1))&(ta<T(2026,8,10,20)+1)
cA=Rb[m,C["cost_ex"]].sum()/Rb[m,C["turnover"]].sum(); print(f"  device implied blended cost = {cA:.4f} bps per unit turnover (fee-only COSTB)")
dcost=((Ra[:,C["cost_ex"]]/Ra[:,C["gross_total"]])-(Rb[:,C["cost_ex"]]/Rb[:,C["gross_total"]]))[m].mean()
for mult,lab in ((1.0,"device"),(3.52/cA,"3.52 bps/unit-intent"),(2.39,"live realized-notional multiple 2.4x"),(4.9,"forensic 11.3%/2.31% = 4.9x")):
    print(f"    dcost x{mult:.2f} ({lab}) = {dcost*mult:+.4f}  =>  dG = {0.2346 - (dcost*mult-dcost):+.4f}")
