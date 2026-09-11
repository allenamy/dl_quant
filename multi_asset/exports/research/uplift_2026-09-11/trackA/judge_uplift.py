"""judge_uplift.py — Track A (PREREG_trackA_carry_sleeves_2026-09-11). Statistics copied VERBATIM from judge_v4.py:
g = net_ex/gross_total [bps/anchor per gross]; FROZEN = 2025-03-01 -> 2026-08-10 20Z; UTC-day block bootstrap 2000,
rng default_rng([20260905, k]). These arms are NOT ELIGIBILITY_CONTRACT candidates: every verdict is EXPLORATORY."""
import numpy as np, json, calendar, time, os, sys
U = "/workspace/uplift_2026-09-11"; PA = f"{U}/probe_artifacts"
HCV4 = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c:i for i,c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
FROZEN = (T(2025,3,1), T(2026,8,10,20)+1)
WIN = {"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
       "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1),
       "frozen":FROZEN,"2024-01->08-10":(T(2024,1,1),T(2026,8,10,20)+1)}
def boot(v, days, rng):   # verbatim judge_v4.boot
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"),)*3
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)), float(np.percentile(mn,97.5)), float((mn>0).mean())
def load(tag):
    A = np.load(f"{PA}/w10_ablation_series_{tag}.npz", allow_pickle=True)
    R = A["d30_n2_c42_rec"]; ts = np.round(R[:,0].astype(np.float64)).astype(np.int64)
    assert R.shape[1] == len(COLS) and [str(c) for c in A["cols"]] == COLS
    g = R[:,C["net_ex"]]/R[:,C["gross_total"]]
    return ts, g, R, A
OUT = {"prereg":"PREREG_trackA_carry_sleeves_2026-09-11.md","exploratory":True,"note":"arms are informational: no BUNDLE_export gate exists"}

# ---- re-parity: my A0 == the archived v4 A0 ----
for s in ("42","2027"):
    a = np.load(f"{HCV4}/w10_ablation_series_V4_A0_dyn_s{s}.npz", allow_pickle=True)
    b = np.load(f"{PA}/w10_ablation_series_A0_dyn_s{s}.npz", allow_pickle=True)
    eq = bool(np.array_equal(a["d30_n2_c42_rec"], b["d30_n2_c42_rec"]))  # W verified in round 1 and again in GATE P2 before compaction
    OUT.setdefault("gate_P",{})[f"A0_dyn_s{s}_bitwise_vs_V4"] = eq
    print(f"GATE P  A0_dyn_s{s} bitwise == archived V4_A0_dyn_s{s}: {eq}")
assert all(OUT["gate_P"].values()), "GATE P FAIL"

# ---- GATE A: sleeve decomposition on A0 ----
print("\n== GATE A: sleeve decomposition of the IN-SERVICE form (A0) on the frozen window, bps/anchor per unit TOTAL gross ==")
print("   (ex caliber = the judge's numerator; carry>0 = PAID; net = pnl - carry - cost)")
SL = {}
for s in ("42","2027"):
    ts,g,R,A = load(f"A0_dyn_s{s}")
    nm = [str(x) for x in A["d30_n2_c42_SLV_names"]]
    m = (ts>=FROZEN[0]) & (ts<FROZEN[1]); gt = R[:,C["gross_total"]]
    P = A["d30_n2_c42_SLV_pnl"]/gt[:,None]; K = A["d30_n2_c42_SLV_carry"]/gt[:,None]
    Q = A["d30_n2_c42_SLV_cost"]/gt[:,None]; G = A["d30_n2_c42_SLV_gross"]/gt[:,None]
    rows=[]
    if s=="42":
        print("%-14s %8s %9s %9s %9s %9s %24s" % ("sleeve","gross%","pnl","carry","cost","net","net CI95"))
    for k in range(14):
        net = (P[:,k]-K[:,k]-Q[:,k])[m]
        rng = np.random.default_rng([20260905, 500+k]); lo,hi,p = boot(net, ts[m]//86400, rng)
        row = {"sleeve":nm[k],"gross_share":float(G[m,k].mean()),"pnl":float(P[m,k].mean()),"carry":float(K[m,k].mean()),
               "cost":float(Q[m,k].mean()),"net":float(net.mean()),"net_ci":[lo,hi],
               "carry_negative_sleeve": bool(hi<0)}
        rows.append(row)
        if s=="42":
            print("%-14s %7.2f%% %+9.4f %+9.4f %+9.4f %+9.4f  [%+8.4f,%+8.4f]%s" % (nm[k],row["gross_share"]*100,row["pnl"],row["carry"],row["cost"],row["net"],lo,hi," <-- CI<0" if hi<0 else ""))
    tot = {"gross_share":float(G[m].sum(1).mean()),"pnl":float(P[m].sum(1).mean()),"carry":float(K[m].sum(1).mean()),"cost":float(Q[m].sum(1).mean()),"net":float(g[m].mean())}
    if s=="42": print("%-14s %7.2f%% %+9.4f %+9.4f %+9.4f %+9.4f   (g = %.4f)" % ("TOTAL",tot["gross_share"]*100,tot["pnl"],tot["carry"],tot["cost"],tot["net"],g[m].mean()))
    SL[s] = {"rows":rows,"total":tot}
OUT["gate_A_sleeves"] = SL
print("\nCARRY-NEGATIVE sleeves (CI<0 on BOTH seeds):",
      [SL["42"]["rows"][k]["sleeve"] for k in range(14) if SL["42"]["rows"][k]["carry_negative_sleeve"] and SL["2027"]["rows"][k]["carry_negative_sleeve"]] or "NONE")

# ---- GATE B/C: arm contrasts ----
ARMS = ["NOFTRIM","FT05","FT00","FT30","FTPOS","LT10","LT30","LT50","CD05","CD1","CD2"]
print("\n== GATE B/C: Dg (arm - A0), dynamic seat, frozen window; UTC-day block bootstrap 2000, rng [20260905, k] ==")
print("%-8s %-5s %9s %22s %6s %9s %9s %9s %8s" % ("arm","seed","D bps","CI95","P>0","Dpnl","Dcarry","Dcost","turn%"))
CON = {}
for ci,a in enumerate(ARMS):
    for s in ("42","2027"):
        ta,ga,Ra,_ = load(f"{a}_dyn_s{s}"); tb,gb,Rb,_ = load(f"A0_dyn_s{s}")
        assert np.array_equal(ta,tb), "axis mismatch"
        m = (ta>=FROZEN[0]) & (ta<FROZEN[1]); d = (ga-gb)[m]
        rng = np.random.default_rng([20260905, ci]); lo,hi,p = boot(d, ta[m]//86400, rng)
        dp = ((Ra[:,C["pnl_ex"]]-Rb[:,C["pnl_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        dk = ((Ra[:,C["carry_ex"]]-Rb[:,C["carry_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        dq = ((Ra[:,C["cost_ex"]]-Rb[:,C["cost_ex"]])/Rb[:,C["gross_total"]])[m].mean()
        tu = float(Ra[m,C["turnover"]].mean()/Rb[m,C["turnover"]].mean()-1)*100
        yr = {}
        for w,(lo_,hi_) in WIN.items():
            mm = (ta>=lo_)&(ta<hi_)
            if mm.sum()>10: yr[w] = float((ga-gb)[mm].mean())
        lvl = {w: float(ga[(ta>=lo_)&(ta<hi_)].mean()) for w,(lo_,hi_) in WIN.items() if ((ta>=lo_)&(ta<hi_)).sum()>10}
        shp = float(ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(APY))
        CON[f"{a}|s{s}"] = {"delta":float(d.mean()),"ci95":[lo,hi],"p_gt0":p,"n":int(m.sum()),
                            "level_arm":float(ga[m].mean()),"level_A0":float(gb[m].mean()),"sharpe_arm":shp,
                            "sharpe_A0":float(gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(APY)),
                            "d_pnl":float(dp),"d_carry":float(dk),"d_cost":float(dq),"turnover_pct":tu,
                            "delta_by_window":yr,"levels_arm":lvl,"rng":[20260905,ci]}
        print("%-8s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f %+9.4f %+9.4f %+9.4f %+7.1f%%" % (a,s,d.mean(),lo,hi,p,dp,dk,dq,tu))
OUT["contrasts"] = CON
print("\n== per-window Dg (arm - A0), dyn, s42 / s2027 ==")
hdr = ["2022","2023","2024","2025","2026->08-10","frozen","2024-01->08-10"]
print("%-8s " % "arm" + " ".join("%16s"%h for h in hdr))
for a in ARMS:
    print("%-8s " % a + " ".join("%16s" % ("%+.3f/%+.3f" % (CON[f"{a}|s42"]["delta_by_window"].get(h,float('nan')), CON[f"{a}|s2027"]["delta_by_window"].get(h,float('nan')))) for h in hdr))
print("\n== ADMISSION (GATE B: CI lower>0 BOTH seeds AND point>+0.23 AND per-year Dg>=-0.30 AND turnover<=+25%%; K=%d; +2 = AMENDMENT 1) ==" % len(ARMS))
adm=[]
for a in ARMS:
    c1 = all(CON[f"{a}|s{s}"]["ci95"][0] > 0 for s in ("42","2027"))
    c2 = all(CON[f"{a}|s{s}"]["delta"] > 0.23 for s in ("42","2027"))
    c3 = all(CON[f"{a}|s{s}"]["delta_by_window"].get(y,0) >= -0.30 for s in ("42","2027") for y in ("2023","2024","2025","2026->08-10"))
    c4 = all(CON[f"{a}|s{s}"]["turnover_pct"] <= 25 for s in ("42","2027"))
    v = "ADMITTED" if (c1 and c2 and c3 and c4) else ("(B) REJECTED" if all(CON[f"{a}|s{s}"]["ci95"][1] < 0 for s in ("42","2027")) else "(C) UNDECIDED")
    adm.append({"arm":a,"ci_lower_gt0":c1,"point_gt_res":c2,"per_year_ok":c3,"turnover_ok":c4,"verdict":v})
    print("%-8s CI>0 %-5s point>0.23 %-5s per-year %-5s turnover %-5s => %s" % (a,c1,c2,c3,c4,v))
OUT["admission"]=adm
json.dump(OUT, open(f"{U}/RESULT_trackA.json","w"), indent=1)
print("\nwritten", f"{U}/RESULT_trackA.json")
