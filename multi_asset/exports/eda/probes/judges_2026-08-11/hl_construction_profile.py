"""(3d) Construction comparison: all-87-overlap vs HL-own-volume top-40 / top-60.

Decision criterion per lead: the PARTICIPATION PROFILE and impact at $50k / $150k / $500k gross,
not just headline Sharpe. Participation = the fraction of a name's own 24h HL notional volume that
the book would trade in that name per day (6 x 4h rebalances), at constant deployed gross.

Reports the whole distribution, not a single number, plus how many names breach 5%/10%/25% -- a
book whose median name is fine but whose tail is at 40% participation is not deployable.

Out: exports/eda/hl_construction_profile.json
"""
import json, sys
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import hl_capacity as HC
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.vol_gate import VolGate
from engine.netting import CrossLegNetting

GROSSES = [50_000, 150_000, 500_000]
CONSTRUCTIONS = {"all_overlap_87": None, "hl_top60": 60, "hl_top40": 40, "hl_top20": 20}


def hl2b(n):
    return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")


def main():
    l2 = json.load(open(MA + "/exports/eda/hl_l2_snapshot.json"))
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    curves = {r["binance"]: HC.slip_curve(r) for r in l2["by_coin"].values() if "err" not in r}
    spread = {r["binance"]: r["top_spread_bps"] for r in l2["by_coin"].values() if "err" not in r}
    hl_vol = {hl2b(d["name"]): d["dayNtlVlm"] for d in meta["markets"] if not d["isDelisted"]}

    src = PanelSource()
    syms = src.symbols
    base = src.member.copy()
    ov = sorted([(s, hl_vol.get(s) or 0.0) for s in syms if s in curves], key=lambda x: -x[1])

    out = {"model": ("participation = |dq_i| * gross * 6 rebalances/day / that name's HL 24h "
                     "notional volume; positions from the real engine netting path over the last "
                     "90d, book at constant unit gross"),
           "caveat": "HL volumes are a current snapshot applied historically (optimistic)",
           "by_construction": {}}

    for cname, topn in CONSTRUCTIONS.items():
        keep = set(s for s, _ in (ov if topn is None else ov[:topn]))
        on = np.array([s in keep for s in syms])
        src.member = base & on[None, :]
        chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank",
                            vol_gate=VolGate(src), funding_risk=None, pos_cap_pct=99.0)
        last_t = int(np.where(src.member.any(1))[0][-1])
        anchors = np.array([t for t in range(last_t - 90 * 24, last_t + 1)
                            if src.member[t].any() and src.CL4[t].any()
                            and np.isfinite(src.king[t]).any()
                            and np.isfinite(src.s2[t]).any()])[::4]
        rn = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=1.9).run(anchors, src.ts)
        src.member = base

        prev = None
        deltas = []
        for (t, m, p) in rn["net_positions"]:
            g = np.abs(p).sum()
            if g < 1e-12:
                continue
            full = np.zeros(src.N); full[m] = p / g
            if prev is not None:
                d = np.abs(full - prev); nz = np.where(d > 1e-9)[0]
                deltas.append((nz, d[nz]))
            prev = full

        spreads = [spread[s] for s, _ in (ov if topn is None else ov[:topn]) if s in spread]
        vols = [hl_vol.get(s) or 0.0 for s, _ in (ov if topn is None else ov[:topn])]
        rec = {"n_names": len(keep),
               "hl_24h_vol_usd": {"median": round(float(np.median(vols))),
                                  "p25": round(float(np.percentile(vols, 25))),
                                  "min": round(float(np.min(vols)))},
               "top_spread_bps": {"median": round(float(np.median(spreads)), 2),
                                  "p90": round(float(np.percentile(spreads, 90)), 2),
                                  "max": round(float(np.max(spreads)), 2)},
               "by_gross": {}}
        for G in GROSSES:
            part, slips = [], []
            for nz, d in deltas:
                tn = tc = 0.0
                for j, dj in zip(nz, d):
                    s = syms[j]
                    v = hl_vol.get(s)
                    if v:
                        part.append(dj * G * 6.0 / v)
                    cur = curves.get(s)
                    if cur is not None:
                        n = dj * G
                        sl, _ = HC.slip_at(cur[0], cur[1], n)
                        tn += n; tc += n * sl
                if tn > 0:
                    slips.append(tc / tn)
            part = np.array(part) * 100.0
            rec["by_gross"][str(G)] = {
                "participation_pct": {
                    "median": round(float(np.median(part)), 3),
                    "p75": round(float(np.percentile(part, 75)), 3),
                    "p95": round(float(np.percentile(part, 95)), 3),
                    "p99": round(float(np.percentile(part, 99)), 3),
                    "max": round(float(np.max(part)), 2)},
                "share_of_name_days_over": {
                    "5pct": round(float((part > 5).mean()), 4),
                    "10pct": round(float((part > 10).mean()), 4),
                    "25pct": round(float((part > 25).mean()), 4)},
                "eff_taker_slip_bps": round(float(np.median(slips)), 2)}
        out["by_construction"][cname] = rec
        print(f"[{cname:16s}] n={rec['n_names']:3d} medVol=${rec['hl_24h_vol_usd']['median']/1e6:6.2f}M "
              f"medSpread={rec['top_spread_bps']['median']:5.2f}bps | " + " | ".join(
              f"${G//1000}k part med {rec['by_gross'][str(G)]['participation_pct']['median']:6.3f}% "
              f"p95 {rec['by_gross'][str(G)]['participation_pct']['p95']:7.3f}% "
              f">10%:{rec['by_gross'][str(G)]['share_of_name_days_over']['10pct']*100:5.2f}% "
              f"slip {rec['by_gross'][str(G)]['eff_taker_slip_bps']:5.2f}"
              for G in GROSSES), flush=True)
    json.dump(out, open(MA + "/exports/eda/hl_construction_profile.json", "w"), indent=1)
    print("-> hl_construction_profile.json")


if __name__ == "__main__":
    main()
