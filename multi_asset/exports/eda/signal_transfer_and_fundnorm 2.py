"""Two questions in one pass.

(A) ★ (3b) RE-FRAMED per lead: the signal is computed from BINANCE data either way; HL only
    supplies the EXECUTION price. So the question is not "can we rebuild the panel on HL" but
    "does a Binance-computed signal still predict HL's forward returns?" Test: rank-IC of the
    engine's actual book positions against HL 4h forward returns, vs against Binance's own,
    on the same anchors and names.

(B) The 4h-vs-8h funding settlement split. FUND_EMA stores the EMA of the PER-INTERVAL rate;
    55/140 coins settle 4h and 85 settle 8h, so the cross-section the engine ranks mixes units.
    Decisive test: rebuild the factor normalised to a per-8h equivalent (rate x 8/interval_h,
    using the PER-ROW interval so mid-history migrations are handled) and compare rank-IC.

Out: exports/eda/signal_transfer_fundnorm.json
"""
import json, glob, os, sys
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
REPO = os.path.dirname(MA)
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS, _rank_centered
from engine.vol_gate import VolGate
from engine.funding_risk import FundingLegRiskControl
from engine.ic_monitor import xsec_rank_ic

WIDE = REPO + "/data/wide"


def hl2b(n):
    return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")


def part_a(src):
    """Binance-computed signal scored on HL forward returns."""
    H = np.load(MA + "/exports/eda/hl_hist.npz", allow_pickle=True)
    ts = src.ts; syms = src.symbols; T, N = src.member.shape
    tpos = {int(t): i for i, t in enumerate(ts)}
    HC = np.full((T, N), np.nan)
    for c, arr in zip(H["coins"], H["candles"]):
        s = hl2b(str(c))
        if s not in syms:
            continue
        j = syms.index(s)
        for row in arr:
            i = tpos.get(int(row[0]))
            if i is not None:
                HC[i, j] = row[4]
    lh = np.log(np.where(HC > 0, HC, np.nan))
    hl_y4 = np.full((T, N), np.nan)
    hl_y4[:-4] = lh[4:] - lh[:-4]                       # HL forward 4h logret

    anchors, yr = [], []
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    a = np.array([t for t in a if np.isfinite(hl_y4[t]).sum() >= 20])

    disp = FundingLegRiskControl.calibrate_dispersion(src, a)
    frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3,
                                disp_ref=disp)
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_mode="rank", vol_gate=VolGate(src),
                        funding_risk=frc, pos_cap_pct=99.0)
    ic_b, ic_h, ic_king_b, ic_king_h = [], [], [], []
    for t in a:
        tp = chain.target_position(int(t))
        m, p = tp["asset_idx"], tp["position"]
        ok = np.isfinite(hl_y4[t, m]) & np.isfinite(src.Y4[t, m])
        if ok.sum() < 15:
            continue
        mm, pp = m[ok], p[ok]
        ic_b.append(xsec_rank_ic(pp, src.Y4[t, mm]))
        ic_h.append(xsec_rank_ic(pp, hl_y4[t, mm]))
        k = src.king[t, mm]
        if np.isfinite(k).sum() >= 15:
            ic_king_b.append(xsec_rank_ic(k, src.Y4[t, mm]))
            ic_king_h.append(xsec_rank_ic(k, hl_y4[t, mm]))

    def st(v):
        v = np.array([x for x in v if np.isfinite(x)])
        return {"mean_rank_ic": round(float(v.mean()), 5),
                "ic_ir": round(float(v.mean() / (v.std() + 1e-12)), 4),
                "t_stat": round(float(v.mean() / (v.std() + 1e-12) * np.sqrt(len(v))), 2),
                "n": int(len(v))}
    out = {"n_anchors": int(len(ic_b)),
           "window": "HL candle coverage (~210d ending 2026-06-30, panel-aligned)",
           "book_position": {"scored_on_binance_y4": st(ic_b), "scored_on_hl_y4": st(ic_h)},
           "king_leg": {"scored_on_binance_y4": st(ic_king_b), "scored_on_hl_y4": st(ic_king_h)}}
    out["book_position"]["hl_over_binance_ic_ratio"] = round(
        out["book_position"]["scored_on_hl_y4"]["mean_rank_ic"]
        / out["book_position"]["scored_on_binance_y4"]["mean_rank_ic"], 4)
    out["king_leg"]["hl_over_binance_ic_ratio"] = round(
        out["king_leg"]["scored_on_hl_y4"]["mean_rank_ic"]
        / out["king_leg"]["scored_on_binance_y4"]["mean_rank_ic"], 4)
    print(f"[A] book IC on Binance {out['book_position']['scored_on_binance_y4']['mean_rank_ic']:.5f} "
          f"vs on HL {out['book_position']['scored_on_hl_y4']['mean_rank_ic']:.5f} "
          f"(ratio {out['book_position']['hl_over_binance_ic_ratio']:.3f}, "
          f"n={out['n_anchors']})", flush=True)
    print(f"[A] king IC on Binance {out['king_leg']['scored_on_binance_y4']['mean_rank_ic']:.5f} "
          f"vs on HL {out['king_leg']['scored_on_hl_y4']['mean_rank_ic']:.5f} "
          f"(ratio {out['king_leg']['hl_over_binance_ic_ratio']:.3f})", flush=True)
    return out


def part_b(src):
    """Per-8h-equivalent funding vs the as-shipped per-interval funding."""
    ts = src.ts; syms = src.symbols; T, N = src.member.shape
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    FE_ship = W["FUND_EMA"].astype(np.float64)
    FE_norm = np.full((T, N), np.nan)
    n_built = 0
    for j, s in enumerate(syms):
        p = f"{WIDE}/{s}_funding.csv"
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        if "funding_interval_h" not in d or len(d) < 10:
            continue
        d = d.sort_values("fundingTime_ms")
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        rate = pd.to_numeric(d["fundingRate"], errors="coerce").to_numpy()
        iv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
        rate8 = rate * (8.0 / iv)                       # PER-ROW normalisation to a per-8h basis
        ih = float(np.median(iv))
        span = max(2, int(round(24.0 / max(ih, 1.0))))  # same 24h-equivalent smoothing as shipped
        ema = pd.Series(rate8).ewm(span=span, adjust=False).mean().to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        idx = np.searchsorted(fts, ts, side="right") - 1
        ok = idx >= 0
        FE_norm[ok, j] = ema[idx[ok]]
        n_built += 1
    print(f"[B] rebuilt normalised funding for {n_built} coins", flush=True)

    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    yrs = pd.to_datetime(ts[a], unit="ms", utc=True).year.to_numpy()
    rec = {"shipped": [], "normalised": []}
    yr_rec = {}
    for t, y in zip(a, yrs):
        m = np.where(src.member[t] & np.isfinite(FE_ship[t]) & np.isfinite(FE_norm[t])
                     & np.isfinite(src.Y4[t]))[0]
        if len(m) < 20:
            continue
        yv = src.Y4[t, m]
        s1 = xsec_rank_ic(-_rank_centered(FE_ship[t, m]), yv)
        s2 = xsec_rank_ic(-_rank_centered(FE_norm[t, m]), yv)
        rec["shipped"].append(s1); rec["normalised"].append(s2)
        yr_rec.setdefault(int(y), {"shipped": [], "normalised": []})
        yr_rec[int(y)]["shipped"].append(s1); yr_rec[int(y)]["normalised"].append(s2)

    def st(v):
        v = np.array([x for x in v if np.isfinite(x)])
        return {"mean_rank_ic": round(float(v.mean()), 5),
                "t_stat": round(float(v.mean() / (v.std() + 1e-12) * np.sqrt(len(v))), 2),
                "n": int(len(v))}
    # paired test on the per-anchor IC difference
    d = np.array(rec["normalised"], float) - np.array(rec["shipped"], float)
    d = d[np.isfinite(d)]
    out = {"n_anchors": len(rec["shipped"]),
           "shipped_per_interval": st(rec["shipped"]),
           "normalised_per_8h_equiv": st(rec["normalised"]),
           "paired_diff": {"mean": round(float(d.mean()), 6),
                           "t_stat": round(float(d.mean() / (d.std() + 1e-12) * np.sqrt(len(d))), 2),
                           "n": int(len(d))},
           "per_year": {y: {"shipped": round(float(np.nanmean(v["shipped"])), 5),
                            "normalised": round(float(np.nanmean(v["normalised"])), 5)}
                        for y, v in sorted(yr_rec.items())}}
    print(f"[B] shipped IC {out['shipped_per_interval']['mean_rank_ic']:+.5f} "
          f"(t {out['shipped_per_interval']['t_stat']:+.2f}) | "
          f"normalised {out['normalised_per_8h_equiv']['mean_rank_ic']:+.5f} "
          f"(t {out['normalised_per_8h_equiv']['t_stat']:+.2f}) | "
          f"paired diff {out['paired_diff']['mean']:+.6f} t={out['paired_diff']['t_stat']:+.2f}",
          flush=True)
    for y, v in out["per_year"].items():
        print(f"    {y}: shipped {v['shipped']:+.5f}  normalised {v['normalised']:+.5f}", flush=True)
    return out


if __name__ == "__main__":
    src = PanelSource()
    res = {"A_signal_transfer_to_hl_prices": part_a(src),
           "B_funding_interval_normalisation": part_b(src)}
    json.dump(res, open(MA + "/exports/eda/signal_transfer_fundnorm.json", "w"), indent=1)
    print("-> signal_transfer_fundnorm.json")
