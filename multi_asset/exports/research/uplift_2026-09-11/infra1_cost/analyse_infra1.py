#!/usr/bin/env python3
"""INFRA-1 step 8: tables. Also recovers each arm's TIER TURNOVER COMPOSITION from the linearity
cost_ex(K) = sum_t turn_t * (blended_t(0) + K*I_t): three cost models -> 3x3 solve."""
import numpy as np, json, calendar
BASE="/workspace/uplift_2026-09-11/infra1_cost"
J=json.load(open(f"{BASE}/JUDGE_infra1.json"))
CB=json.load(open(f"{BASE}/costb_honest_H0.json")); H0=CB["blended_bps_per_unit_turnover"]
H1=json.load(open(f"{BASE}/costb_honest_H1.json"))["blended_bps_per_unit_turnover"]
STD=[2.20213,2.00264,2.01310]
print("cost model blends: STD",STD," H0",H0," H1",H1)
def show(seed=42):
    print("\n################ SEED %d ################"%seed)
    for cb in ("STD","H0","H05","H1","H15","H2","H3","H4","H6"):
        b=f"IB_PAR_{cb}_s{seed}"
        if b not in J.get("base",{}): continue
        print("\n--- cost model %s ---"%cb)
        print("%-10s %-8s %8s %8s %8s %8s %8s | %10s %20s %7s"%("arm","window","g","SR","pnl","carry","cost","D vs PAR","CI95","P(D>0)"))
        for arm in ("PAR","AM50","LAG50","D60","PERM50"):
            tag=f"IB_{arm}_{cb}_s{seed}"
            if tag not in J.get("arms",{}): continue
            e=J["arms"][tag]
            for w in ("full","frozen","oof_aug"):
                L=e["level"].get(w); P=e["paired_vs_PAR"].get(w)
                if L is None: continue
                d=("%+.3f"%P["D"]) if P else ""
                ci=("[%+.3f,%+.3f]"%tuple(P["ci"])) if P else ""
                pp=("%.3f"%P["p_pos"]) if P else ""
                print("%-10s %-8s %8.3f %8.2f %8.3f %8.3f %8.4f | %10s %20s %7s"%(
                    arm,w,L["mean"],L["sharpe"],L["pnl_bps"],L["carry_bps"],L["cost_bps"],d,ci,pp))
show(42); show(2027)
# tier turnover composition per arm (full window), from cost linearity
print("\n### recovered tier turnover composition (full window, per anchor, fraction of gross)")
A=np.array([STD,H0,H1])            # rows = models, cols = tiers
for seed in (42,2027):
    for arm in ("PAR","AM50","LAG50","D60","PERM50"):
        tags=[f"IB_{arm}_{c}_s{seed}" for c in ("STD","H0","H1")]
        if not all(t in J.get("arms",{}) for t in tags): continue
        y=np.array([J["arms"][t]["level"]["full"]["cost_bps"] for t in tags])
        # cost_bps is cost_ex/gross_total; turnover col is turnover/gross => same units
        turn=np.linalg.solve(A,y)
        tot=J["arms"][tags[0]]["level"]["full"]["turnover"]
        print("s%-5d %-8s tier turnover [%.5f %.5f %.5f] sum %.5f | rec turnover col %.5f | illiquid share %.3f"%(
            seed,arm,turn[0],turn[1],turn[2],turn.sum(),tot,turn[2]/turn.sum()))
# sleeves
print("\n### standalone orthogonalised sleeves (LEGS=001)")
print("%-16s %-8s %8s %8s %8s"%("sleeve","window","g","SR","cost"))
for k,v in sorted(J.get("sleeves",{}).items()):
    for w in ("full","frozen","oof_aug"):
        if v.get(w) is None: continue
        print("%-16s %-8s %8.3f %8.2f %8.4f"%(k,w,v[w]["mean"],v[w]["sharpe"],v[w]["cost_bps"]))
