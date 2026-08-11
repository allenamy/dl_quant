"""Bottom line: HL-universe engine Sharpe as a function of the REAL per-trade cost.

The engine's shipped table assumes 1.9 bps per unit one-way turnover. The HL L2 snapshot says a
taker sweep of the book's actual per-rebalance clip costs 4.8-7.8 bps (spread+impact, EXCLUDING
venue fees) at $50k-$500k gross. P&L is linear in cost, so we can price each assumption exactly.

Out: exports/eda/hl_cost_sensitivity.json
"""
import os
import json, sys
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource

COSTS = [0.0, 1.9, 3.0, 4.8, 5.3, 7.8, 10.0, 14.0]


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    hl = set(hl_to_binance(d["name"]) for d in meta["markets"] if not d["isDelisted"])
    src = PanelSource()
    z = np.load(U.WIDE_PANEL, allow_pickle=True)
    DV = z["DVOL30"].astype(np.float64)
    on_hl = np.array([s in hl for s in src.symbols])
    base = src.member.copy()
    anchors, _ = U._all_anchors(src)

    out = {"note": ("net-of-cost Sharpe vs assumed per-unit-one-way-turnover cost. 1.9 bps is the "
                    "engine's shipped assumption; 4.8/5.3/7.8 are the HL L2 taker-sweep costs at "
                    "$50k/$150k/$500k gross (spread+impact only, venue FEES NOT included -- add "
                    "HL's taker fee on top for a true taker figure). Maker execution would sit "
                    "far below the taker numbers but cannot be priced from a book snapshot."),
           "universes": {}}
    for label, mask in (("member110", base), ("member110_x_hl", base & on_hl[None, :])):
        src.member = mask
        rows = {}
        for c in COSTS:
            U.COST_BPS = c
            r = U.replay_for_universe(src, DV, anchors_fixed=anchors)
            r.pop("_daily", None)
            rows[str(c)] = {"avg_net_sharpe": r["avg_net_of_cost_sharpe"],
                            "per_year": {y: r["per_year"][y]["net_of_cost_sharpe"]
                                         for y in r["per_year"]}}
            print(f"[{label}] cost={c:5.1f} bps -> avg net Sharpe {r['avg_net_of_cost_sharpe']:6.2f} "
                  f"| per-year {list(rows[str(c)]['per_year'].values())}", flush=True)
        out["universes"][label] = rows
    U.COST_BPS = 1.9
    src.member = base
    json.dump(out, open(MA + "/exports/eda/hl_cost_sensitivity.json", "w"), indent=1)

    print("\n=== break-even: cost at which avg net Sharpe hits 0 ===")
    for label, rows in out["universes"].items():
        cs = np.array([float(k) for k in rows]); sh = np.array([rows[k]["avg_net_sharpe"] for k in rows])
        o = np.argsort(cs); cs, sh = cs[o], sh[o]
        be = np.interp(0.0, sh[::-1], cs[::-1]) if sh.min() < 0 else np.nan
        slope = (sh[0] - sh[-1]) / (cs[-1] - cs[0])
        print(f"  {label}: gross(0bps)={sh[0]:.2f}, dSharpe/dbps={-slope:.3f}, "
              f"break-even~{be:.1f} bps" if np.isfinite(be) else
              f"  {label}: gross(0bps)={sh[0]:.2f}, dSharpe/dbps={-slope:.3f}, break-even >14 bps")
        out["universes"][label]["_break_even_bps"] = (round(float(be), 1) if np.isfinite(be)
                                                      else ">14")
    json.dump(out, open(MA + "/exports/eda/hl_cost_sensitivity.json", "w"), indent=1)
    print("-> hl_cost_sensitivity.json")


if __name__ == "__main__":
    main()
