"""Per-leg breadth sensitivity: which of the 4 legs loses most when the universe shrinks.
Companion to universe_shrink_sensitivity.py (same caliber, same point-in-time top-N rule)."""
import os
import sys, json, time
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource

NS = [110, 60, 40, 20]
LEGS = ["king", "s2", "funding", "size"]
OUT = MA + "/exports/eda/universe_shrink_by_leg.json"


def main():
    t0 = time.time()
    src = PanelSource()
    z = np.load(U.WIDE_PANEL, allow_pickle=True)
    DV = z["DVOL30"].astype(np.float64)
    T, Nsym = src.member.shape
    masks = U.build_topn_masks(T, Nsym, DV, NS)
    src.member = masks[110]
    anchors, _ = U._all_anchors(src)

    res = {}
    for leg in LEGS:
        w = {k: (1.0 if k == leg else 0.0) for k in ["king", "s2", "funding", "size"]}
        res[leg] = {}
        for n in NS:
            src.member = masks[n]
            r = U.replay_for_universe(src, DV, anchors_fixed=anchors, weights=w)
            py = r["per_year"]
            res[leg][n] = {"avg_net": r["avg_net_of_cost_sharpe"],
                           "avg_gross": r["avg_gross_sharpe"],
                           "avg_ic": r["avg_mean_rank_ic"],
                           "by_year_net": {y: py[y]["net_of_cost_sharpe"] for y in py},
                           "by_year_ic": {y: py[y]["mean_rank_ic"] for y in py},
                           "by_year_icir": {y: py[y]["ic_ir"] for y in py}}
            print(f"[{leg:8s} N={n:3d}] net={r['avg_net_of_cost_sharpe']:6.2f} "
                  f"gross={r['avg_gross_sharpe']:6.2f} IC={r['avg_mean_rank_ic']:.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("\n=== avg net Sharpe: leg x N (standalone single-leg book) ===")
    print(f"{'leg':10s}" + "".join(f"{n:>9d}" for n in NS) + "   ret@40/110")
    for leg in LEGS:
        v = [res[leg][n]["avg_net"] for n in NS]
        print(f"{leg:10s}" + "".join(f"{x:>9.2f}" for x in v) + f"{v[2]/v[0]:>12.2f}")
    print("\n=== avg rank-IC: leg x N ===")
    for leg in LEGS:
        print(f"{leg:10s}" + "".join(f"{res[leg][n]['avg_ic']:>9.4f}" for n in NS))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
