"""Is the HL top-40 trim's execution gain bigger than its funding-carry loss?

The tension: trimming to HL's 40 most-liquid names halves slippage (median spread 2.91 -> 1.00 bps)
but drops names whose funding carry the book was collecting. 0C found the small-cap carry share
rose 29.4% -> 34.8% after the dimension fix, so the loss is larger than first estimated.

★ Measured against the ACTUAL HL top-40 roster (by HL 24h notional), NOT a market-cap proxy --
  small-cap and not-on-HL-top-40 are different sets and the lead explicitly asked not to conflate
  them.

Method: run the canonical engine, take the REAL netted book positions, and accrue funding carry
per name using the CORRECTED (settlement-interval normalised) per-8h funding. Split the carry by
whether the name is in HL's top-40. Convert the lost carry to book %/yr and to Sharpe using the
book's own realised volatility, then set it against the execution gain (maker X=3: 11.53 vs 8.90).

Out: exports/eda/carry_venue_exposure.json
"""
import json, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
import universe_shrink_sensitivity as U
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from engine.vol_gate import VolGate
from engine.funding_risk import FundingLegRiskControl
from engine.netting import CrossLegNetting
from data.apply_funding_fix import load_corrected

ANCHORS_PER_YEAR = 365 * 6
EXEC_GAIN_SHARPE = 11.53 - 8.90        # maker, X=3 bps adverse: top-40 vs all-87 overlap


def hl2b(n):
    return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")


def main():
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    l2 = json.load(open(MA + "/exports/eda/hl_l2_snapshot.json"))
    tradeable = set(r["binance"] for r in l2["by_coin"].values() if "err" not in r)
    hl_vol = {hl2b(d["name"]): (d["dayNtlVlm"] or 0.0) for d in meta["markets"]
              if not d["isDelisted"]}

    src = PanelSource()
    syms = src.symbols
    ov = sorted([(s, hl_vol.get(s, 0.0)) for s in syms if s in tradeable], key=lambda x: -x[1])
    top40 = set(s for s, _ in ov[:40])
    on_hl = set(s for s, _ in ov)
    print(f"[universe] HL-tradeable overlap {len(on_hl)} | top-40 roster locked", flush=True)

    FE = load_corrected(src.ts, syms, verbose=False)      # per-8h equivalent, corrected
    anchors, yr = U._all_anchors(src)

    disp = FundingLegRiskControl.calibrate_dispersion(src, anchors)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp)
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=99.0)
    res = CrossLegNetting(chain, DEFAULT_WEIGHTS, cost_bps=1.9).run(anchors, src.ts, year_of=yr)

    idx_top40 = np.array([s in top40 for s in syms])
    idx_onhl = np.array([s in on_hl for s in syms])

    carry_all, carry_t40, carry_onhl, pnl = [], [], [], []
    for (t, m, p) in res["net_positions"]:
        ti = int(t)
        g = np.abs(p).sum()
        if g < 1e-12:
            continue
        q = p / g                                          # unit-gross deployment book
        rate8 = FE[ti, m]
        rate4 = np.where(np.isfinite(rate8), rate8, 0.0) / 2.0   # per-8h -> per-4h holding period
        c_i = -q * rate4                                   # long a negative-funding name RECEIVES
        carry_all.append(float(c_i.sum()))
        carry_t40.append(float(c_i[idx_top40[m]].sum()))
        carry_onhl.append(float(c_i[idx_onhl[m]].sum()))
        r = src.Y4[ti, m]
        pnl.append(float(np.nansum(q * np.where(np.isfinite(r), r, 0.0))))

    ca, ct, ch_ = np.array(carry_all), np.array(carry_t40), np.array(carry_onhl)
    pnl = np.array(pnl)
    # book volatility (annualised) from the unit-gross price P&L -> converts %/yr into Sharpe
    days = (src.ts[anchors] // 86400000).astype(np.int64)[:len(pnl)]
    dfp = pd.DataFrame({"day": days, "p": pnl}).groupby("day")["p"].sum()
    vol_ann = float(dfp.std() * np.sqrt(365))

    tot = float(ca.mean() * ANCHORS_PER_YEAR * 100)
    t40 = float(ct.mean() * ANCHORS_PER_YEAR * 100)
    onhl = float(ch_.mean() * ANCHORS_PER_YEAR * 100)
    lost_vs_full = tot - t40
    lost_vs_hl = onhl - t40

    out = {
        "caliber": ("canonical netted book at unit gross; carry accrued with the CORRECTED "
                    "(settlement-interval normalised) per-8h funding; price P&L used only to get "
                    "the book's realised vol for the %/yr -> Sharpe conversion"),
        "roster": {"basis": "actual HL top-40 by HL 24h notional volume (NOT a size proxy)",
                   "n_hl_tradeable_overlap": len(on_hl), "n_top40": len(top40)},
        "carry_pct_yr": {"full_member110_book": round(tot, 3),
                         "restricted_to_hl_overlap": round(onhl, 3),
                         "restricted_to_hl_top40": round(t40, 3)},
        "carry_share_from_names_outside_top40": {
            "vs_full_book": round((lost_vs_full / tot) if tot else float("nan"), 4),
            "vs_hl_overlap_book": round((lost_vs_hl / onhl) if onhl else float("nan"), 4)},
        "book_vol_annualised_unit_gross": round(vol_ann, 5),
        "carry_loss_in_sharpe": {
            "vs_full_book": round(lost_vs_full / 100.0 / vol_ann, 3) if vol_ann else None,
            "vs_hl_overlap_book": round(lost_vs_hl / 100.0 / vol_ann, 3) if vol_ann else None},
        "execution_gain_sharpe_top40_vs_all87_maker_X3": round(EXEC_GAIN_SHARPE, 3),
        "n_anchors": len(ca),
    }
    net = EXEC_GAIN_SHARPE - (lost_vs_hl / 100.0 / vol_ann if vol_ann else 0.0)
    out["net_tradeoff_sharpe_top40_minus_all87"] = round(net, 3)
    ratio = abs(EXEC_GAIN_SHARPE) / max(abs(lost_vs_hl / 100.0 / vol_ann), 1e-9)
    out["verdict"] = {
        "execution_gain_over_carry_loss_ratio": round(ratio, 2),
        "same_order_of_magnitude": bool(ratio < 3.0),
        "direction": ("execution gain dominates -> trim to top-40" if net > 0 else
                      "carry loss dominates -> do NOT trim"),
        "confidence_note": ("if the ratio is under ~3x the two are the same order of magnitude and "
                            "the sign should not be trusted from backtest alone -- pilot must "
                            "measure it"),
    }
    json.dump(out, open(MA + "/exports/eda/carry_venue_exposure.json", "w"), indent=1)
    print(f"[carry] full book {tot:+.3f}%/yr | HL-overlap {onhl:+.3f} | HL-top40 {t40:+.3f}",
          flush=True)
    print(f"[carry] share of carry from names OUTSIDE top-40: "
          f"{out['carry_share_from_names_outside_top40']['vs_hl_overlap_book']:.1%} "
          f"(of the HL-overlap book)", flush=True)
    print(f"[carry] carry loss in Sharpe (top40 vs HL-overlap) = "
          f"{out['carry_loss_in_sharpe']['vs_hl_overlap_book']}", flush=True)
    print(f"[carry] execution gain = {EXEC_GAIN_SHARPE:+.2f} Sharpe | NET = {net:+.3f} | "
          f"ratio {ratio:.2f}x", flush=True)
    print(f"[carry] verdict: {out['verdict']['direction']}", flush=True)
    print("-> carry_venue_exposure.json")


if __name__ == "__main__":
    main()
