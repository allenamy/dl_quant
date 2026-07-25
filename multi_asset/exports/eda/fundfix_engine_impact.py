"""Engine impact of the funding settlement-interval fix: old vs corrected factor, same everything else.

★ CALIBER — read before comparing to 0C's numbers:
This replay's P&L is PRICE-ONLY (Y4 is a forward price return; funding carry is NOT credited).
0C's "+8.48%/yr, solo Sharpe 0.83" is the CARRY-INCLUSIVE economic caliber. Both are correct and
they answer different questions:
    price-only  -> does the funding factor predict PRICE moves?  (this file)
    with carry  -> is holding the funding leg profitable overall? (0C)
The funding leg is a carry harvester, so the price-only view is expected to look weaker.

Out: exports/eda/fundfix_engine_impact.json
"""
import os
import json, sys
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource

PANELS = {"shipped_broken": MA + "/exports/wide_dl_full.npz",
          "fundfix": MA + "/exports/wide_dl_full_fundfix.npz"}
BOOKS = {"full_book": None,
         "funding_leg_only": {"king": 0.0, "s2": 0.0, "funding": 1.0, "size": 0.0}}


def main():
    out = {"caliber": ("PRICE-ONLY replay (Y4 = forward price return; carry NOT credited). 0C's "
                       "+8.48%/yr / solo Sharpe 0.83 is the CARRY-INCLUSIVE caliber -- different "
                       "question, both correct. The funding leg is a carry harvester, so the "
                       "price-only view understates it by construction."),
           "engine": "canonical rank + shaping='cap', 1.9 bps, MEMBER110",
           "results": {}}
    ref_anchors = None
    for pname, path in PANELS.items():
        src = PanelSource(panel=path)
        z = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
        DV = z["DVOL30"].astype(np.float64)
        anchors, _ = U._all_anchors(src)
        if ref_anchors is None:
            ref_anchors = anchors
        else:
            assert np.array_equal(anchors, ref_anchors), "anchor grid differs between panels"
        for bname, w in BOOKS.items():
            U.COST_BPS = 1.9
            r = U.replay_for_universe(src, DV, anchors_fixed=ref_anchors, weights=w)
            r.pop("_daily", None)
            out["results"].setdefault(bname, {})[pname] = {
                "avg_net_sharpe": r["avg_net_of_cost_sharpe"],
                "avg_gross_sharpe": r["avg_gross_sharpe"],
                "avg_rank_ic": r["avg_mean_rank_ic"],
                "per_year_net": {y: r["per_year"][y]["net_of_cost_sharpe"] for y in r["per_year"]},
                "per_year_ic": {y: r["per_year"][y]["mean_rank_ic"] for y in r["per_year"]},
                "funding_concentration_max": r["funding_concentration"]["max"]}
            print(f"[{bname:17s} {pname:15s}] net {r['avg_net_of_cost_sharpe']:6.2f} "
                  f"gross {r['avg_gross_sharpe']:6.2f} IC {r['avg_mean_rank_ic']:+.5f}", flush=True)
    for bname in BOOKS:
        a = out["results"][bname]["shipped_broken"]; b = out["results"][bname]["fundfix"]
        out["results"][bname]["delta_fix_minus_broken"] = {
            "net_sharpe": round(b["avg_net_sharpe"] - a["avg_net_sharpe"], 2),
            "rank_ic": round(b["avg_rank_ic"] - a["avg_rank_ic"], 5)}
        print(f"[delta {bname}] net {out['results'][bname]['delta_fix_minus_broken']['net_sharpe']:+.2f} "
              f"IC {out['results'][bname]['delta_fix_minus_broken']['rank_ic']:+.5f}", flush=True)
    json.dump(out, open(MA + "/exports/eda/fundfix_engine_impact.json", "w"), indent=1)
    print("-> fundfix_engine_impact.json")


if __name__ == "__main__":
    main()
