import numpy as np, calendar, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1); EXT=(T(2025,3,1),T(2026,8,31,20)+1)
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
    "2025":(T(2025,1,1),T(2026,1,1)),"2026<=0810":(T(2026,1,1),T(2026,8,10,20)+1)}
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_%s.npz"
def ld(t):
    R=np.load(TB%t,allow_pickle=True)["d30_n2_c42_rec"]; ts=np.round(R[:,0].astype(np.float64)).astype(np.int64); return ts,R
print("=== per-YEAR dG and per-year SHARPE (arm vs BASE), both seeds ===")
for s in ("42","2027"):
    tb,Rb=ld(f"TB_BASE_dyn_s{s}"); gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
    for nm in ("TB_BAND5e4","TB_EMA005"):
        ta,Ra=ld(f"{nm}_dyn_s{s}"); ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]
        print(f"  {nm} s{s}")
        for y,(a,b) in YR.items():
            m=(ta>=a)&(ta<b)
            if m.sum()<10: continue
            sa=ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(2190); sbv=gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(2190)
            print(f"    {y:11s} n={m.sum():5d}  g base {gb[m].mean():+7.3f} -> arm {ga[m].mean():+7.3f}  dG {(ga-gb)[m].mean():+7.3f} | SR base {sbv:+6.2f} -> arm {sa:+6.2f}")
print("\n=== EXTENDED window 2025-03-01 -> 2026-08-31 20Z: levels & Sharpe ===")
for s in ("42","2027"):
    for nm in ("TB_BASE","TB_BAND5e4","TB_EMA005"):
        ta,Ra=ld(f"{nm}_dyn_s{s}"); g=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]
        for lab,(a,b) in (("FROZEN",FR),("EXTENDED",EXT)):
            m=(ta>=a)&(ta<b)
            print(f"  {nm:11s} s{s:5s} {lab:9s} n={m.sum():5d} g={g[m].mean():+7.4f} SR={g[m].mean()/g[m].std(ddof=1)*np.sqrt(2190):6.3f} SE_SR={np.sqrt(2190/m.sum()):.3f}")
print("\n=== FULL-HISTORY (2022-01 -> 2026-08-31) level, the cross-regime read ===")
for s in ("42",):
    for nm in ("TB_BASE","TB_BAND5e4","TB_EMA005","AT_FIXBASE","AT_FIXB5e4"):
        ta,Ra=ld(f"{nm}_dyn_s{s}"); g=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]
        print(f"  {nm:12s} allhist n={len(g)} g={g.mean():+7.4f} SR={g.mean()/g.std(ddof=1)*np.sqrt(2190):6.3f}")
