"""decomp_ftrim.py — FTRIM 机制三项分解(PREREG §5.2 B2)。
net_ex = pnl_ex − carry_ex − cost_ex(恒等由断言证实)。
Δnet_ex = Δpnl_ex − Δcarry_ex − Δcost_ex, 其中 Δ = 有FTRIM − 无FTRIM。
读法: Δcarry_ex < 0 = FTRIM 少付 carry(有利, 因为它进负号); Δpnl_ex < 0 = 放弃了价格 P&L。
自举同判官: UTC 日块 2000 种子 20260905。"""
import json, time, hashlib
import numpy as np
H="/workspace/review_scratch/health_check"; ARM="d30_n2_c42"; NB=2000; SEED=20260905
def load(tag, cal):
    d="dev" if cal=="log" else "dev_alt"
    p=f"{H}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz"
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z[f"{ARM}_rec"]
    return {c:R[:,i] for i,c in enumerate(cols)}
def boot(x,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    s=np.bincount(inv,weights=x,minlength=nd); c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); return s[idx].sum(1)/c[idx].sum(1)
OUT={"decomp":"Dnet = Dpnl - Dcarry - Dcost","cells":{}}
print("=== FTRIM 三项分解  Δ = 有FTRIM − 无FTRIM  (bps/锚 每 NAV)")
print("%-18s %-9s %9s %9s %9s %9s %10s" % ("格","窗","Dnet","Dpnl(价格)","Dcarry","Dcost","恒等残差"))
for cal in ("log","prod"):
    for seed in ("42","2027"):
        A=load(f"M1_UPIT_{cal}_s{seed}_ccal",cal); B=load(f"NOFTRIM_M1_UPIT_{cal}_s{seed}_ccal",cal)
        ts=A["ts"].astype(np.int64)
        assert np.array_equal(ts,B["ts"].astype(np.int64))
        # 恒等断言: net_ex == pnl_ex - carry_ex - cost_ex
        for X,nm in ((A,"on"),(B,"off")):
            r=np.abs(X["net_ex"]-(X["pnl_ex"]-X["carry_ex"]-X["cost_ex"])).max()
            assert r<1e-6, (nm,"identity residual",r)
        yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
        days=np.array([time.strftime("%Y-%m-%d",time.gmtime(int(t))) for t in ts])
        dn=A["net_ex"]-B["net_ex"]; dp=A["pnl_ex"]-B["pnl_ex"]; dc=A["carry_ex"]-B["carry_ex"]; dk=A["cost_ex"]-B["cost_ex"]
        cell={}
        for wn,m in (("2024->26",yrs>=2024),("2025->26",yrs>=2025),("2024",yrs==2024),("2025",yrs==2025),("2026",yrs==2026)):
            if m.sum()<10: continue
            rng=np.random.default_rng(SEED)
            bsc=boot(dc[m],days[m],rng); bsp=boot(dp[m],days[m],rng)
            resid=float(np.abs(dn[m]-(dp[m]-dc[m]-dk[m])).max())
            cell[wn]={"dnet":round(float(dn[m].mean()),4),"dpnl":round(float(dp[m].mean()),4),
                      "dcarry":round(float(dc[m].mean()),4),"dcost":round(float(dk[m].mean()),4),
                      "dcarry_ci":[round(float(np.percentile(bsc,2.5)),4),round(float(np.percentile(bsc,97.5)),4)],
                      "dpnl_ci":[round(float(np.percentile(bsp,2.5)),4),round(float(np.percentile(bsp,97.5)),4)],
                      "resid":resid}
            print("%-18s %-9s %+9.4f %+9.4f %+9.4f %+9.4f %10.1e" % (f"{cal}/s{seed}",wn,cell[wn]["dnet"],cell[wn]["dpnl"],cell[wn]["dcarry"],cell[wn]["dcost"],resid))
        OUT["cells"][f"{cal}/s{seed}"]=cell
json.dump(OUT,open(f"{H}/decomp_ftrim.json","w"),indent=1)
print()
print("=== carry 与价格的 CI(2024->26 与 2025->26)")
for k,c in OUT["cells"].items():
    for w in ("2024->26","2025->26"):
        v=c[w]; print("%-18s %-9s Dcarry %+.4f %s   Dpnl %+.4f %s" % (k,w,v["dcarry"],v["dcarry_ci"],v["dpnl"],v["dpnl_ci"]))
