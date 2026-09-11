#!/usr/bin/env python3
import json, numpy as np, time
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
P = {r["anchor"]: r for r in json.load(open(f"{OUT}/recon_anchor_table.json"))}
L = json.load(open(f"{OUT}/live_anchor_table.json"))
COMBO0 = 1787716800
J = []
for r in L:
    A = r["grid_anchor"]; p = P.get(A)
    if not p or "deployed_gross_bps" not in p: continue
    gn_k = p.get("king_gross_norm"); gn_d = p.get("deployed_gross_norm")
    J.append({"A": A, "utc": p["utc"], "dt_h": r["dt_h"], "gross": r["gross"],
              "paper_king_per_unit": p["logged_gross"] / gn_k if gn_k else None,
              "paper_dep_per_unit": p["deployed_gross_bps"] / gn_d if gn_d else None,
              "paper_carry_per_unit": p["carry"] / gn_k if gn_k else None,
              "paper_cost_per_unit": p["cost"] / gn_k if gn_k else None,
              "live_price_bps": r["price_bps_of_gross"],
              "live_fund_bps": r["funding_bps_of_gross"],
              "price_pnl": r["price_pnl"], "funding": r["funding"]})
J = [j for j in J if j["A"] >= COMBO0 and j["live_price_bps"] is not None]
print("joined combo-era anchors:", len(J), J[0]["utc"], "->", J[-1]["utc"])
def arr(k): return np.array([j[k] for j in J], float)
pk, pd_, lp, lf, pc, pcost, g = arr("paper_king_per_unit"), arr("paper_dep_per_unit"), arr("live_price_bps"), arr("live_fund_bps"), arr("paper_carry_per_unit"), arr("paper_cost_per_unit"), arr("gross")
def st(n, v, w=None):
    gw = float((v * g).sum() / g.sum())
    print(f"  {n:26s} mean {v.mean():8.4f}  sd {v.std(ddof=1):7.3f}  gross-wtd-mean {gw:8.4f}  sum {v.sum():9.2f}")
print("\n--- all per unit of GROSS, bps per anchor (combo era) ---")
st("paper king  (logged)", pk); st("paper deployed (recomp)", pd_); st("live price (ledger)", lp)
st("paper carry (COST,+)", pc); st("live funding (signed)", lf); st("paper cost_bps (COST,+)", pcost)
print(f"\n  corr(paper_dep, live_price)   = {np.corrcoef(pd_, lp)[0,1]:.4f}")
print(f"  corr(paper_king, live_price)  = {np.corrcoef(pk, lp)[0,1]:.4f}")
print(f"  corr(paper_king, paper_dep)   = {np.corrcoef(pk, pd_)[0,1]:.4f}")
b = np.polyfit(pd_, lp, 1); print(f"  OLS live_price ~ a+b*paper_dep : b={b[0]:.4f} a={b[1]:.4f}")
print(f"\n  paper NET king   (gross-carry-cost) mean = {(pk-pc-pcost).mean():.4f}")
print(f"  paper NET deployed(gross-carry-cost) mean= {(pd_-pc-pcost).mean():.4f}")
print(f"  live  NET (price+funding)           mean = {(lp+lf).mean():.4f}")
print("\n  DECOMPOSITION of paper_king_net -> live_net, bps/unit-gross/anchor")
print(f"   (a) scored-king -> deployed weights : {(pd_-pk).mean():+.4f}")
print(f"   (e) deployed paper -> live price    : {(lp-pd_).mean():+.4f}")
print(f"   (c) carry model -> venue funding    : {(lf+pc).mean():+.4f}   (model charged {pc.mean():.4f}, venue charged {-lf.mean():.4f})")
print(f"   (d) cost model removed              : {(pcost).mean():+.4f}")
print(f"   total                               : {((lp+lf)-(pk-pc-pcost)).mean():+.4f}")
json.dump(J, open(f"{OUT}/joined_combo_table.json", "w"), indent=1)
# cumulative USD view
print("\n  cumulative USD over joined anchors: live price %.1f  funding %.1f" % (sum(j['price_pnl'] for j in J), sum(j['funding'] for j in J)))
print("  implied USD if paper_king_net were realized: %.1f" % float(((pk-pc-pcost)/1e4*g).sum()))
print("  implied USD if paper_dep gross realized:     %.1f" % float((pd_/1e4*g).sum()))
