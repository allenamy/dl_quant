"""(3d) Capacity + impact re-estimated on HYPERLIQUID's own liquidity (not Binance's).

Two independent readings:
  A. VOLUME model -- same as the (1) study but with HL dayNtlVlm: max deployable gross such that
     each name's per-4h-rebalance trade stays under q% of that name's 4h HL volume.
  B. DEPTH model  -- from the live L2 snapshot: for a target gross G, price every name's actual
     per-rebalance trade by sweeping the real book, and aggregate to an effective bps cost.
     Reported against the engine's assumed 1.9 bps -- that assumption is what breaks or holds.

Positions come from the real engine chain restricted to the HL-overlap universe, so the |dp|
distribution is the book's actual one, not an assumption.

Out: exports/eda/hl_capacity.json
"""
import os
import json, sys
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.vol_gate import VolGate
from engine.netting import CrossLegNetting

GROSSES = [50_000, 150_000, 500_000, 1_500_000, 5_000_000]
PARTICIPATION = 0.05
REBAL_PER_DAY = 6          # 4h grid


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def slip_curve(rec):
    """(notional[], slip_bps[]) one-way taker sweep curve; anchored at 0+ by the half-spread."""
    xs = [1.0], [rec["top_spread_bps"] / 2.0]
    N, S = [1.0], [rec["top_spread_bps"] / 2.0]
    for k, v in sorted(rec["slip_bps"].items(), key=lambda kv: int(kv[0])):
        rt = v.get("roundtrip")
        if rt is not None:
            N.append(float(k)); S.append(rt / 2.0)          # one-way = roundtrip/2
    return np.array(N), np.array(S)


def slip_at(N, S, notional):
    """log-linear interp; beyond the deepest priced point -> extrapolate on the last slope,
    which understates a real sweep (books thin out), so flag saturation separately."""
    if notional <= N[0]:
        return S[0], False
    if notional >= N[-1]:
        if len(N) >= 2 and N[-1] > N[-2]:
            sl = (S[-1] - S[-2]) / (np.log(N[-1]) - np.log(N[-2]))
            return S[-1] + sl * (np.log(notional) - np.log(N[-1])), True
        return S[-1], True
    return float(np.interp(np.log(notional), np.log(N), S)), False


def main():
    l2 = json.load(open(MA + "/exports/eda/hl_l2_snapshot.json"))
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    hl_vol = {hl_to_binance(d["name"]): d["dayNtlVlm"] for d in meta["markets"]
              if not d["isDelisted"]}
    curves = {}
    for c, rec in l2["by_coin"].items():
        if "err" in rec:
            continue
        curves[rec["binance"]] = slip_curve(rec)
    print(f"[cap] usable L2 curves: {len(curves)}", flush=True)

    src = PanelSource()
    syms = src.symbols
    hl_ok = np.array([s in curves for s in syms])
    # restrict the universe to the HL-tradeable set, then run the SAME netting path the canonical
    # engine uses (leg cadence holds + cross-leg netting). Using chain.target_position() directly
    # would inflate turnover ~1.7x because every leg would retrade every 4h anchor.
    src.member = src.member & hl_ok[None, :]
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=None, pos_cap_pct=99.0)

    last_t = int(np.where(src.member.any(1))[0][-1])
    anchors = np.array([t for t in range(last_t - 90 * 24, last_t + 1)
                        if src.member[t].any() and src.CL4[t].any()
                        and np.isfinite(src.king[t]).any() and np.isfinite(src.s2[t]).any()])[::4]
    net = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=1.9)
    rn = net.run(anchors, src.ts)

    prev = None
    deltas = []          # (sym_idx, |dp|) per rebalance, book normalised to unit gross
    for (t, m, p) in rn["net_positions"]:
        g = np.abs(p).sum()
        if g < 1e-12:
            continue
        full = np.zeros(src.N); full[m] = p / g
        if prev is not None:
            d = np.abs(full - prev)
            nz = np.where(d > 1e-9)[0]
            deltas.append((nz, d[nz]))
        prev = full

    turn_per_reb = float(np.mean([d.sum() for _, d in deltas]))
    print(f"[cap] anchors={len(deltas)} mean turnover/rebalance={turn_per_reb:.4f} of gross",
          flush=True)

    out = {"as_of_l2": l2["pulled_at"], "n_names": int(hl_ok.sum()),
           "mean_turnover_per_rebalance": round(turn_per_reb, 4),
           "n_anchors": len(deltas),
           "caveat": ("L2 = single snapshot; taker-sweep cost is an UPPER bound (the book is "
                      "designed for maker execution). Half-spread is the maker-side reference "
                      "but ignores queue position and adverse selection, which a snapshot "
                      "cannot measure."),
           "engine_assumed_cost_bps": 1.9}

    # ---- A. volume model: max gross under q% of 4h HL volume ----
    volcap = []
    for nz, d in deltas:
        r = []
        for j, dj in zip(nz, d):
            v = hl_vol.get(syms[j])
            if v and dj > 1e-9:
                r.append(PARTICIPATION * (v / 6.0) / dj)
        if len(r) >= 5:
            volcap.append((np.min(r), np.percentile(r, 5)))
    volcap = np.array(volcap)
    out["volume_model"] = {
        "participation": PARTICIPATION,
        "max_gross_usd_strict_median": round(float(np.median(volcap[:, 0]))),
        "max_gross_usd_p05relax_median": round(float(np.median(volcap[:, 1]))),
        "note": "same model as the (1) study, but on HL dayNtlVlm instead of Binance DVOL30"}

    # ---- B. depth model: effective cost in bps at each target gross ----
    tab = {}
    for G in GROSSES:
        eff, sat_share, worst = [], [], []
        for nz, d in deltas:
            tot_notional = 0.0; tot_cost = 0.0; sat = 0.0
            for j, dj in zip(nz, d):
                cur = curves.get(syms[j])
                if cur is None:
                    continue
                notional = dj * G
                s, is_sat = slip_at(cur[0], cur[1], notional)
                tot_notional += notional
                tot_cost += notional * s
                if is_sat:
                    sat += notional
            if tot_notional > 0:
                eff.append(tot_cost / tot_notional)
                sat_share.append(sat / tot_notional)
        # daily participation per name at this gross
        part = []
        for nz, d in deltas:
            for j, dj in zip(nz, d):
                v = hl_vol.get(syms[j])
                if v:
                    part.append(dj * G * REBAL_PER_DAY / v)
        part = np.array(part)
        tab[str(G)] = {
            "eff_taker_slip_bps_oneway_median": round(float(np.median(eff)), 2),
            "eff_taker_slip_bps_oneway_p90": round(float(np.percentile(eff, 90)), 2),
            "vs_engine_1.9bps": round(float(np.median(eff)) / 1.9, 1),
            "notional_share_beyond_priced_depth": round(float(np.median(sat_share)), 3),
            "daily_participation_median_pct": round(float(np.median(part)) * 100, 3),
            "daily_participation_p95_pct": round(float(np.percentile(part, 95)) * 100, 3),
            "daily_participation_max_pct": round(float(np.max(part)) * 100, 2)}
        print(f"  G=${G:>9,}: taker slip {tab[str(G)]['eff_taker_slip_bps_oneway_median']:6.2f} bps "
              f"(={tab[str(G)]['vs_engine_1.9bps']:4.1f}x engine 1.9) | "
              f"daily participation med {tab[str(G)]['daily_participation_median_pct']:.3f}% "
              f"p95 {tab[str(G)]['daily_participation_p95_pct']:.3f}%", flush=True)
    out["depth_model"] = tab

    # ---- spread landscape of the tradeable set ----
    sp = sorted([(rec["binance"], rec["top_spread_bps"], rec["dayNtlVlm"])
                 for rec in l2["by_coin"].values() if "err" not in rec], key=lambda x: x[1])
    arr = np.array([s[1] for s in sp])
    out["top_spread_bps"] = {"median": round(float(np.median(arr)), 2),
                             "p25": round(float(np.percentile(arr, 25)), 2),
                             "p75": round(float(np.percentile(arr, 75)), 2),
                             "p90": round(float(np.percentile(arr, 90)), 2),
                             "tightest5": sp[:5], "widest5": sp[-5:]}
    json.dump(out, open(MA + "/exports/eda/hl_capacity.json", "w"), indent=1)
    print("\n" + json.dumps({k: v for k, v in out.items() if k != "depth_model"}, indent=1))
    print("-> hl_capacity.json")


if __name__ == "__main__":
    main()
