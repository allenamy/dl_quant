"""0C — cost-crossover: the king-tilt buys Sharpe but costs +50% turnover. At what effective cost
does the current book overtake it? Flat-cost sweep, funding P&L on, canonical chain."""
import sys, json
import numpy as np, pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import leg_contribution_pass2 as P     # reuses HELD / RET / FRZ / day / anchors / run / sh

CFG = {"current": {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30},
       "king40_even": {"king": 0.40, "s2": 0.2, "funding": 0.2, "size": 0.2},
       "king50_even": {"king": 0.50, "s2": 1 / 6, "funding": 1 / 6, "size": 1 / 6},
       "king60_even": {"king": 0.60, "s2": 4 / 30, "funding": 4 / 30, "size": 4 / 30},
       "solo_king": {"king": 1.0}}
COSTS = [0.0, 1.9, 3.94, 6.0, 8.0, 10.0, 12.0]
YRS = (int(P.src.ts[P.anchors[-1]]) - int(P.src.ts[P.anchors[0]])) / (86400000 * 365.25)

res = {}
for name, w in CFG.items():
    r = P.run(w)
    turn = float(r["TU"].sum() / YRS)
    res[name] = {"turnover_ann": round(turn, 1), "by_cost": {}}
    for c in COSTS:
        net = r["R"] - r["TU"] * c * 1e-4 + r["F"]
        dl = pd.DataFrame(dict(day=P.day, x=net)).groupby("day")["x"].sum().values
        res[name]["by_cost"][str(c)] = dict(sharpe=round(P.sh(dl), 2),
                                            ann_return=round(float(dl.mean() * 365), 4))
    print(f"{name:14s} turn {turn:6.0f} | " +
          "  ".join(f"{c}bps:{res[name]['by_cost'][str(c)]['sharpe']:6.2f}" for c in COSTS), flush=True)

# crossover cost where 'current' overtakes each king-tilt (linear interp on the Sharpe gap)
cross = {}
for name in CFG:
    if name == "current":
        continue
    gap = [res[name]["by_cost"][str(c)]["sharpe"] - res["current"]["by_cost"][str(c)]["sharpe"] for c in COSTS]
    xc = None
    for a in range(len(COSTS) - 1):
        if gap[a] > 0 >= gap[a + 1]:
            xc = COSTS[a] + (COSTS[a + 1] - COSTS[a]) * gap[a] / (gap[a] - gap[a + 1]); break
    cross[name] = dict(gap_by_cost={str(c): round(g, 2) for c, g in zip(COSTS, gap)},
                       crossover_bps=round(xc, 2) if xc else None)
    print(f"  crossover {name:14s} -> {cross[name]['crossover_bps']}", flush=True)

json.dump(dict(sweep=res, crossover=cross,
               note=("flat-cost sweep, canonical chain + funding P&L. crossover_bps = effective cost/side "
                     "at which the CURRENT 30/10/30/30 book overtakes the king-tilted book. For context: "
                     "shipped assumption 1.9, Binance VIP0+BNB fill0.7 ~3.9, whole-book break-even ~12.2.")),
          open(MA + "/exports/eda/leg_cost_crossover.json", "w"), indent=1)
print("SAVED exports/eda/leg_cost_crossover.json", flush=True)
