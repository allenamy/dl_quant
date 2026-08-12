"""Synthesis of (1) and (3d): trim the HL universe to its most liquid names.

(1) said the book is statistically intact down to ~40-50 names. (3d) said HL execution cost is
dominated by wide-spread small names. So trimming should buy a large cost reduction for little
alpha. This prices that trade-off jointly: for each N, the engine's net Sharpe AT THE COST THAT
SUBSET ACTUALLY COSTS.

Ranking = HL 24h notional volume (current snapshot). ⚠ applied over all history -> liquidity-
ranking survivorship, same caveat class as the roster caveat. Direction is optimistic.

Slippage EXCLUDES venue fees. Add HL's published taker/maker fee on top; the reported
dSharpe/dbps slope lets any fee be plugged in.

Out: exports/eda/hl_trim.json
"""
import os
import json, sys
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.vol_gate import VolGate
from engine.netting import CrossLegNetting
import hl_capacity as HC

NS = [20, 30, 40, 50, 60, 87]
GROSSES = [50_000, 150_000, 500_000]


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def eff_slip(src, curves, hl_vol, mask, G):
    """netted-book effective one-way taker slip (bps) at gross G on the given universe mask."""
    saved = src.member.copy()
    src.member = mask
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=None, pos_cap_pct=99.0)
    last_t = int(np.where(src.member.any(1))[0][-1])
    anchors = np.array([t for t in range(last_t - 90 * 24, last_t + 1)
                        if src.member[t].any() and src.CL4[t].any()
                        and np.isfinite(src.king[t]).any() and np.isfinite(src.s2[t]).any()])[::4]
    rn = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=1.9).run(anchors, src.ts)
    src.member = saved
    prev = None; eff = []; part = []
    for (t, m, p) in rn["net_positions"]:
        g = np.abs(p).sum()
        if g < 1e-12:
            continue
        full = np.zeros(src.N); full[m] = p / g
        if prev is not None:
            d = np.abs(full - prev); nz = np.where(d > 1e-9)[0]
            tn = 0.0; tc = 0.0
            for j in nz:
                cur = curves.get(src.symbols[j])
                if cur is None:
                    continue
                n = d[j] * G
                s, _ = HC.slip_at(cur[0], cur[1], n)
                tn += n; tc += n * s
                v = hl_vol.get(src.symbols[j])
                if v:
                    part.append(d[j] * G * 6 / v)
            if tn > 0:
                eff.append(tc / tn)
        prev = full
    return (float(np.median(eff)) if eff else np.nan,
            float(np.percentile(part, 95)) if part else np.nan)


def main():
    l2 = json.load(open(MA + "/exports/eda/hl_l2_snapshot.json"))
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    curves = {r["binance"]: HC.slip_curve(r) for r in l2["by_coin"].values() if "err" not in r}
    hl_vol = {hl_to_binance(d["name"]): d["dayNtlVlm"] for d in meta["markets"]
              if not d["isDelisted"]}

    src = PanelSource()
    z = np.load(U.WIDE_PANEL, allow_pickle=True)
    DV = z["DVOL30"].astype(np.float64)
    syms = src.symbols
    base = src.member.copy()
    anchors, _ = U._all_anchors(src)

    # rank HL-overlap names by HL 24h volume
    ov = [(s, hl_vol.get(s) or 0.0) for s in syms if s in curves]
    ov.sort(key=lambda x: -x[1])
    out = {"ranking": "HL 24h notional volume (current snapshot, applied historically)",
           "caveat": ("liquidity-ranking + roster survivorship, both OPTIMISTIC; slippage excludes "
                      "venue fees"),
           "by_topn": {}}
    for N in NS:
        keep = set(s for s, _ in ov[:N])
        on = np.array([s in keep for s in syms])
        mask = base & on[None, :]
        src.member = mask
        U.COST_BPS = 1.9
        r = U.replay_for_universe(src, DV, anchors_fixed=anchors)
        r.pop("_daily", None)
        src.member = base
        row = {"n_names": N, "median_breadth": r["median_breadth"],
               "sharpe_at_1.9bps": r["avg_net_of_cost_sharpe"],
               "gross_sharpe": r["avg_gross_sharpe"], "rank_ic": r["avg_mean_rank_ic"],
               "per_year_at_1.9": {y: r["per_year"][y]["net_of_cost_sharpe"] for y in r["per_year"]},
               "at_gross": {}}
        # dSharpe/dbps is linear -> derive from gross(0) and net(1.9)
        slope = (r["avg_gross_sharpe"] - r["avg_net_of_cost_sharpe"]) / 1.9
        row["dSharpe_per_bps"] = round(float(slope), 3)
        row["break_even_bps"] = round(float(r["avg_gross_sharpe"] / slope), 1) if slope > 0 else None
        for G in GROSSES:
            s, p95 = eff_slip(src, curves, hl_vol, mask, G)
            row["at_gross"][str(G)] = {
                "eff_taker_slip_bps": round(s, 2),
                "net_sharpe_at_that_slip": round(float(r["avg_gross_sharpe"] - slope * s), 2),
                "daily_participation_p95_pct": round(p95 * 100, 2)}
        out["by_topn"][str(N)] = row
        print(f"[N={N:3d}] breadth={r['median_breadth']:5.1f} gross={r['avg_gross_sharpe']:5.2f} "
              f"net@1.9={r['avg_net_of_cost_sharpe']:5.2f} BE={row['break_even_bps']}bps | " +
              " | ".join(f"${G//1000}k: slip {row['at_gross'][str(G)]['eff_taker_slip_bps']:5.2f} "
                         f"-> Sh {row['at_gross'][str(G)]['net_sharpe_at_that_slip']:5.2f}"
                         for G in GROSSES), flush=True)
    U.COST_BPS = 1.9
    json.dump(out, open(MA + "/exports/eda/hl_trim.json", "w"), indent=1)
    print("-> hl_trim.json")


if __name__ == "__main__":
    main()
