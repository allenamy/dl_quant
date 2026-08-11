"""(3a, quantified) Run the canonical engine on the ACTUAL Hyperliquid-tradeable universe.

Universe = MEMBER110 (point-in-time) INTERSECT HL's current active perp roster. Same engine,
same anchors, same caliber as the universe-shrink study -- so this is directly comparable to
that study's top-N rows.

⚠ ROSTER SURVIVORSHIP: HL's roster is observed TODAY (2026-07-25) and applied over all history.
   Coins HL listed only recently are treated as if listed since 2022. The bias is OPTIMISTIC
   (we are using the set that got listed / survived). Point-in-time listing dates were descoped
   (API cost); the mitigation is that the (1) study already brackets this: an ~87-name subset
   sits between its N=80 and N=110 rows, both of which were statistically indistinguishable
   from the full N=110 book.

Out: exports/eda/hl_universe_replay.json
"""
import os
import json, sys
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    hl = set(hl_to_binance(d["name"]) for d in meta["markets"] if not d["isDelisted"])
    src = PanelSource()
    z = np.load(U.WIDE_PANEL, allow_pickle=True)
    DV = z["DVOL30"].astype(np.float64)
    syms = src.symbols
    on_hl = np.array([s in hl for s in syms])
    base = src.member.copy()
    anchors, _ = U._all_anchors(src)

    res = {}
    print(f"[hl-universe] HL roster covers {int(on_hl.sum())}/{len(syms)} panel symbols", flush=True)

    # arm 1: full MEMBER110 (reference)
    r0 = U.replay_for_universe(src, DV, anchors_fixed=anchors)
    r0.pop("_daily", None)
    res["member110"] = r0

    # arm 2: MEMBER110 ∩ HL roster
    src.member = base & on_hl[None, :]
    r1 = U.replay_for_universe(src, DV, anchors_fixed=anchors)
    d1 = r1.pop("_daily")
    res["member110_x_hl"] = r1

    # arm 3: the complement (names HL does NOT list) -- how much alpha lives in what we'd lose
    src.member = base & (~on_hl)[None, :]
    r2 = U.replay_for_universe(src, DV, anchors_fixed=anchors)
    r2.pop("_daily", None)
    res["member110_minus_hl"] = r2
    src.member = base

    # paired bootstrap on arm2 vs arm1
    r0b = U.replay_for_universe(src, DV, anchors_fixed=anchors)
    d0 = r0b.pop("_daily")
    rng = np.random.default_rng(20260725)
    A = np.array(d0["pnl_net"], float); B = np.array(d1["pnl_net"], float)
    nd = len(A); L = 20; nb = int(np.ceil(nd / L)); NB = 2000
    st = rng.integers(0, nd - L, size=(NB, nb))
    idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(NB, -1)[:, :nd]
    sa = A[idx].mean(1) / (A[idx].std(1) + 1e-12) * np.sqrt(365)
    sb = B[idx].mean(1) / (B[idx].std(1) + 1e-12) * np.sqrt(365)
    d = sb - sa
    res["bootstrap"] = {"sharpe_member110": round(float(U._dsharpe(A)), 2),
                        "sharpe_member110_x_hl": round(float(U._dsharpe(B)), 2),
                        "delta": round(float(U._dsharpe(B) - U._dsharpe(A)), 2),
                        "ci95": [round(float(np.percentile(d, 2.5)), 2),
                                 round(float(np.percentile(d, 97.5)), 2)],
                        "p_worse": round(float((d < 0).mean()), 3)}
    res["caveat"] = ("HL roster observed 2026-07-25 applied over all history -> OPTIMISTIC "
                     "roster survivorship. See module docstring.")
    json.dump(res, open(MA + "/exports/eda/hl_universe_replay.json", "w"), indent=1)

    for k in ("member110", "member110_x_hl", "member110_minus_hl"):
        v = res[k]
        py = v["per_year"]
        print(f"\n[{k}] breadth={v['median_breadth']:.0f} avgNet={v['avg_net_of_cost_sharpe']:.2f} "
              f"avgIC={v['avg_mean_rank_ic']:.4f}")
        print("   per-year net: " + " ".join(f"{y}={py[y]['net_of_cost_sharpe']:.2f}" for y in py))
    print("\n[bootstrap]", json.dumps(res["bootstrap"]))
    print("-> hl_universe_replay.json")


if __name__ == "__main__":
    main()
