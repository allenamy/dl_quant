import json
P = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/universe_shrink_sensitivity.json"
j = json.load(open(P)); B = j["by_topn"]
YS = ["2022", "2023", "2024", "2025", "2026"]
NS = ["110", "80", "60", "50", "40", "30", "20"]

print("=== net-of-cost Sharpe by year ===")
print("N    " + "".join(f"{y:>9}" for y in ["2022", "2023", "2024", "2025", "2026H1"]) + "      avg   d_vs110")
for n in NS:
    py = B[n]["per_year"]
    d = B[n]["avg_net_of_cost_sharpe"] - B["110"]["avg_net_of_cost_sharpe"]
    print(f"{n:<5}" + "".join(f'{py[y]["net_of_cost_sharpe"]:>9.2f}' for y in YS)
          + f'{B[n]["avg_net_of_cost_sharpe"]:>9.2f}{d:>+10.2f}')

print("\n=== gross Sharpe by year ===")
for n in NS:
    py = B[n]["per_year"]
    print(f"{n:<5}" + "".join(f'{py[y]["gross_sharpe"]:>9.2f}' for y in YS)
          + f'{B[n]["avg_gross_sharpe"]:>9.2f}')

print("\n=== mean xsec rank-IC by year ===")
for n in NS:
    py = B[n]["per_year"]
    print(f"{n:<5}" + "".join(f'{py[y]["mean_rank_ic"]:>9.4f}' for y in YS)
          + f'{B[n]["avg_mean_rank_ic"]:>9.4f}')

print("\n=== IC-IR by year ===")
for n in NS:
    py = B[n]["per_year"]
    print(f"{n:<5}" + "".join(f'{py[y]["ic_ir"]:>9.3f}' for y in YS))

print("\n=== breadth / effective breadth (1/HHI) / turnover ===")
for n in NS:
    py = B[n]["per_year"]; nt = B[n]["netting"]
    br = [py[y]["mean_breadth"] for y in YS]
    eff = [1.0 / py[y]["mean_hhi"] for y in YS]
    tpa = [py[y]["turn_per_anchor"] for y in YS]
    print(f"N={n:<4} breadth={['%.0f' % v for v in br]} effbr={['%.1f' % v for v in eff]} "
          f"turn/anchor={['%.3f' % v for v in tpa]} hedge={nt['hedge_rate']:.3f} "
          f"netturn={nt['net_turn_ann']:.0f} save={nt['savings_bps_yr']:.0f}")

print("\n=== capacity: max deployable GROSS book, USD (5% of 4h $vol per name) ===")
for n in NS:
    py = B[n]["per_year"]
    s = [py[y]["cap_usd_strict_median"] for y in YS]
    r = [py[y]["cap_usd_p05relax_median"] for y in YS]
    print(f"N={n:<4} strict={['%.1fM' % (v / 1e6) for v in s]}  p05relax={['%.1fM' % (v / 1e6) for v in r]}")

print("\n=== funding-leg concentration ===")
for n in NS:
    fc = B[n]["funding_concentration"]
    print(f"N={n:<4} mean={fc['mean']:.3f} p99={fc['p99']:.3f} max={fc['max']:.3f}")
