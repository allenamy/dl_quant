"""(3a) Universe overlap: Hyperliquid's perp roster vs our MEMBER110 book universe.

Severity is measured three ways, weakest to strongest:
  (i)   plain name count
  (ii)  share of our universe's Binance dollar volume that sits in HL-missing names
  (iii) share of the BOOK'S ACTUAL GROSS POSITION in HL-missing names (recent anchors) -- the
        only one that answers "how much of what we actually trade can't be traded there"
Plus the reverse direction: HL names absent from our panel (expansion candidates).

Out: exports/eda/hl_overlap.json
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


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    active = [d for d in meta["markets"] if not d["isDelisted"]]
    hl_map = {hl_to_binance(d["name"]): d for d in active}

    src = PanelSource()
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    DV = W["DVOL30"].astype(np.float64)
    syms = src.symbols

    # ---- current book universe = latest anchor's tradeable set ----
    dt = pd.to_datetime(src.ts, unit="ms", utc=True)
    last_t = int(np.where(src.member.any(1))[0][-1])
    mem_idx = np.where(src.member[last_t])[0]
    cur = [syms[j] for j in mem_idx]
    have = [s for s in cur if s in hl_map]
    miss = [s for s in cur if s not in hl_map]

    dv = DV[last_t]
    dv_tot = float(np.nansum([dv[j] for j in mem_idx if np.isfinite(dv[j])]))
    dv_miss = float(np.nansum([dv[syms.index(s)] for s in miss
                               if np.isfinite(dv[syms.index(s)])]))

    out = {"as_of": str(dt[last_t]), "hl_active_perps": len(active),
           "member110_size": len(cur),
           "overlap_n": len(have), "missing_n": len(miss),
           "overlap_pct_by_count": round(100.0 * len(have) / len(cur), 1),
           "missing_pct_of_universe_binance_dvol": round(100.0 * dv_miss / dv_tot, 2),
           "missing_names": sorted(miss),
           "missing_detail": sorted(
               [{"sym": s, "binance_dvol_hourly_usd": (float(dv[syms.index(s)])
                                                       if np.isfinite(dv[syms.index(s)]) else None)}
                for s in miss], key=lambda d: -(d["binance_dvol_hourly_usd"] or 0))}

    # ---- (iii) share of ACTUAL BOOK GROSS in HL-missing names, over the last 90 days ----
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=None, pos_cap_pct=99.0)
    hl_ok = np.array([s in hl_map for s in syms])
    anchors = [t for t in range(last_t - 90 * 24, last_t + 1)
               if src.member[t].any() and src.CL4[t].any()]
    anchors = [t for t in anchors if np.isfinite(src.king[t]).any() and np.isfinite(src.s2[t]).any()]
    fr = []
    for t in anchors[::4]:
        tp = chain.target_position(int(t))
        p, m = tp["position"], tp["asset_idx"]
        g = np.abs(p).sum()
        if g > 1e-12:
            fr.append(float(np.abs(p[~hl_ok[m]]).sum() / g))
    out["book_gross_share_in_hl_missing_last90d"] = {
        "mean": round(float(np.mean(fr)), 4), "p90": round(float(np.percentile(fr, 90)), 4),
        "max": round(float(np.max(fr)), 4), "n_anchors": len(fr)}

    # ---- reverse: HL markets absent from our panel (expansion candidates) ----
    panel = set(syms)
    extra = [d for d in active if hl_to_binance(d["name"]) not in panel]
    extra.sort(key=lambda d: -(d["dayNtlVlm"] or 0))
    out["hl_names_not_in_our_panel"] = {
        "n": len(extra),
        "share_of_hl_24h_volume": round(100.0 * sum(d["dayNtlVlm"] or 0 for d in extra)
                                        / max(meta["total_dayNtlVlm_usd"], 1), 1),
        "top20": [{"name": d["name"], "dayNtlVlm_usd": d["dayNtlVlm"]} for d in extra[:20]]}

    # ---- HL volume concentration ----
    tot = meta["total_dayNtlVlm_usd"]
    vols = sorted([d["dayNtlVlm"] or 0 for d in active], reverse=True)
    out["hl_volume_concentration"] = {
        "total_24h_usd": tot,
        "top1_pct": round(100 * vols[0] / tot, 1), "top2_pct": round(100 * sum(vols[:2]) / tot, 1),
        "top5_pct": round(100 * sum(vols[:5]) / tot, 1),
        "top10_pct": round(100 * sum(vols[:10]) / tot, 1),
        "top40_pct": round(100 * sum(vols[:40]) / tot, 1),
        "n_over_10m": sum(1 for v in vols if v >= 1e7),
        "n_over_5m": sum(1 for v in vols if v >= 5e6),
        "n_over_1m": sum(1 for v in vols if v >= 1e6),
        "n_over_100k": sum(1 for v in vols if v >= 1e5)}
    # same for the overlap subset only (that's what the book could actually trade)
    ov = sorted([hl_map[s]["dayNtlVlm"] or 0 for s in have], reverse=True)
    out["hl_overlap_subset_volume"] = {
        "n": len(ov), "total_24h_usd": round(sum(ov)),
        "n_over_10m": sum(1 for v in ov if v >= 1e7), "n_over_5m": sum(1 for v in ov if v >= 5e6),
        "n_over_1m": sum(1 for v in ov if v >= 1e6), "n_over_100k": sum(1 for v in ov if v >= 1e5),
        "median_usd": round(float(np.median(ov))), "p25_usd": round(float(np.percentile(ov, 25)))}

    # ---- Binance-vs-HL volume ratio for the overlap names ----
    rat = []
    for s in have:
        j = syms.index(s)
        b24 = dv[j] * 24.0 if np.isfinite(dv[j]) else None       # DVOL30 is mean HOURLY
        h24 = hl_map[s]["dayNtlVlm"]
        if b24 and h24:
            rat.append({"sym": s, "binance_24h": b24, "hl_24h": h24, "hl_over_binance": h24 / b24})
    rat.sort(key=lambda d: -d["hl_over_binance"])
    rr = np.array([d["hl_over_binance"] for d in rat])
    out["hl_vs_binance_24h_volume_ratio"] = {
        "n": len(rr), "median": round(float(np.median(rr)), 4),
        "p25": round(float(np.percentile(rr, 25)), 4),
        "p75": round(float(np.percentile(rr, 75)), 4),
        "highest5": rat[:5], "lowest5": rat[-5:]}

    json.dump(out, open(MA + "/exports/eda/hl_overlap.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("missing_detail", "hl_names_not_in_our_panel",
                                   "hl_vs_binance_24h_volume_ratio")}, indent=1))
    print("\nmissing (top by Binance vol):",
          [d["sym"] for d in out["missing_detail"][:25]])
    print("\nHL-only top20:", [(d["name"], round((d["dayNtlVlm"] or 0) / 1e6, 1))
                               for d in out["hl_names_not_in_our_panel"]["top20"]])
    print("\nHL/Binance 24h vol ratio: median %.3f p25 %.3f p75 %.3f"
          % (out["hl_vs_binance_24h_volume_ratio"]["median"],
             out["hl_vs_binance_24h_volume_ratio"]["p25"],
             out["hl_vs_binance_24h_volume_ratio"]["p75"]))
    print("-> hl_overlap.json")


if __name__ == "__main__":
    main()
