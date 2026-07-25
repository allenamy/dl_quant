"""HL funding-leg migration: which venue's funding should build the leg? (口径 A vs B)

THE REASONING CHAIN (lead): the funding leg's economics decompose into price drift + carry.
Move it to HL and:
  - price drift follows unchanged (4h return corr HL-vs-Binance is 0.998, already measured);
  - carry does NOT: you COLLECT HL's funding while the positions were CHOSEN by Binance's
    funding ranking, and the two cross-sections correlate only ~0.47.
=> naive migration might keep all of the negative price drift while collecting only part of the
   carry. BUT the counter-force: 0C found 76.6% of carry sits in the top |funding| decile, and I
   found agreement between venues is HIGHEST exactly where |funding| is large (TRX 0.895 /
   ALT 0.846) and near-zero where funding is small (BTC 0.050). So carry transfer could be far
   above the average 0.47. Both stories are coherent -- hence measure, don't reason.

  口径 A  (Binance signal / HL settlement): rank by BINANCE funding, collect HL funding
  口径 B  (HL native):                      rank by HL funding,      collect HL funding
  reference (Binance native):               rank by Binance funding, collect Binance funding

★ Runs on the CORRECTED (settlement-interval normalised) funding factor on the Binance side --
  the dimension ruling is settled, and computing this on the broken factor would inherit the bug.
  HL funding is hourly and needs the same treatment: rate * (8/1) to put it on the same per-8h
  basis before any cross-venue level comparison. Ranking is scale-free so this only matters for
  the carry ARITHMETIC, not the selection.

Out: exports/eda/hl_carry_ab.json
"""
import glob, json, os, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import _rank_centered, _l1
from engine.ic_monitor import xsec_rank_ic
from data.apply_funding_fix import load_corrected

ARC = MA + "/exports/hl_archive/funding"
HOURS_PER_YEAR = 24 * 365


def hl2b(n):
    return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")


def load_hl_funding(ts, symbols, verbose=True):
    """(T,N) HL funding on our hourly grid, as a PER-8H-EQUIVALENT rate (HL settles hourly).

    Uses the archive (deep, 1171d) and falls back to the 60d pull for anything missing.
    Returns both the EMA (for ranking) and the raw per-hour rate (for carry arithmetic).
    """
    T, N = len(ts), len(symbols)
    EMA = np.full((T, N), np.nan)
    RAW = np.full((T, N), np.nan)
    n = 0
    # Two sources: the deep archive (1171d, still backfilling) and the 60d targeted pull (89
    # coins). Merge so breadth is not hostage to the backfill; the archive wins where both exist.
    series = {}
    hh = MA + "/exports/eda/hl_hist.npz"
    if os.path.exists(hh):
        H = np.load(hh, allow_pickle=True)
        for c, arr in zip(H["fcoins"], H["funding"]):
            series[str(c)] = np.asarray(arr, float)
    for f in sorted(glob.glob(ARC + "/*.npz")):
        a = np.load(f)["a"]
        if len(a) >= 10:
            series[os.path.basename(f)[:-4]] = a          # archive overrides (deeper)
    for coin, a in series.items():
        s = hl2b(coin)
        if s not in symbols or len(a) < 10:
            continue
        a = a[np.argsort(a[:, 0])]
        j = symbols.index(s)
        rate_h = a[:, 1]
        # HL settles hourly -> per-8h equivalent is rate_h * 8. Same 24h-equivalent EMA span as
        # the Binance side uses for an hourly-settled coin (24/1 = 24).
        ema = pd.Series(rate_h * 8.0).ewm(span=24, adjust=False).mean().to_numpy()
        idx = np.searchsorted(a[:, 0], ts, side="right") - 1
        ok = idx >= 0
        EMA[ok, j] = ema[idx[ok]]
        RAW[ok, j] = rate_h[idx[ok]]                     # per-hour rate, for carry accrual
        n += 1
    if verbose:
        print(f"[hl] funding loaded for {n} coins from the archive", flush=True)
    return EMA, RAW


def main():
    src = PanelSource()
    ts, syms = src.ts, src.symbols
    T, N = src.member.shape

    BF = load_corrected(ts, syms, verbose=True)          # CORRECTED Binance funding (per-8h basis)
    HF, HR = load_hl_funding(ts, list(syms))
    # Binance per-8h rate for carry: de-EMA is not possible, so use the EMA level as the
    # prevailing per-8h rate (it is a 24h-equivalent smooth of it) -- applied identically to both
    # venues so the COMPARISON is fair even though the absolute level is smoothed.
    have_hl = np.isfinite(HF).any(0)
    print(f"[universe] coins with HL funding: {int(have_hl.sum())}", flush=True)

    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a_all = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
    anchors = np.array([t for t in a_all if np.isfinite(HF[t]).sum() >= 15])
    yrs = pd.to_datetime(ts[anchors], unit="ms", utc=True).year.to_numpy()
    print(f"[anchors] {len(anchors)} with >=15 HL-funded members "
          f"({pd.to_datetime(ts[anchors[0]], unit='ms', utc=True).date()} .. "
          f"{pd.to_datetime(ts[anchors[-1]], unit='ms', utc=True).date()})", flush=True)

    arms = {"A_binance_signal_hl_settle": ("BF", "HL"),
            "B_hl_native": ("HF", "HL"),
            "ref_binance_native": ("BF", "BN")}
    acc = {k: {"price": [], "carry": [], "ic": []} for k in arms}
    per_year = {k: {} for k in arms}

    for t, y in zip(anchors, yrs):
        m = np.where(src.member[t] & np.isfinite(HF[t]) & np.isfinite(BF[t])
                     & np.isfinite(src.Y4[t]))[0]
        if len(m) < 15:
            continue
        ret = src.Y4[t, m]
        for k, (sig_src, carry_src) in arms.items():
            f = BF[t, m] if sig_src == "BF" else HF[t, m]
            pos = _l1(-_rank_centered(f))                # crowding-reversion, unit gross
            price = float(np.nansum(pos * ret))
            # carry over the 4h holding period: long a negative-funding name RECEIVES funding.
            # per-8h rate -> per-4h = /2 for the Binance side; HL raw is per-hour -> x4.
            if carry_src == "HL":
                rate4 = HR[t, m] * 4.0
            else:
                rate4 = BF[t, m] / 2.0
            carry = float(np.nansum(-pos * np.where(np.isfinite(rate4), rate4, 0.0)))
            acc[k]["price"].append(price)
            acc[k]["carry"].append(carry)
            acc[k]["ic"].append(xsec_rank_ic(pos, ret))
            per_year[k].setdefault(int(y), {"price": [], "carry": []})
            per_year[k][int(y)]["price"].append(price)
            per_year[k][int(y)]["carry"].append(carry)

    n_per_year = 365 * 6                                  # 4h anchors per year
    out = {"scope": {"n_anchors": int(len(acc["A_binance_signal_hl_settle"]["price"])),
                     "window": f"{pd.to_datetime(ts[anchors[0]], unit='ms', utc=True).date()} .. "
                               f"{pd.to_datetime(ts[anchors[-1]], unit='ms', utc=True).date()}",
                     "binance_factor_version": "settlement-interval CORRECTED (normfix)"},
           "caveats": ["carry uses the 24h-equivalent EMA level as the prevailing rate on the "
                       "Binance side and the raw hourly rate on the HL side; applied identically "
                       "across arms so the COMPARISON is fair, but absolute carry is smoothed",
                       "HL history starts 2023-05 -> the window is shorter than the engine's",
                       "unit-gross single-leg book, no cost, no netting -- leg economics only"],
           "arms": {}}
    for k in arms:
        p = np.array(acc[k]["price"], float); c = np.array(acc[k]["carry"], float)
        ic = np.array([v for v in acc[k]["ic"] if np.isfinite(v)], float)
        tot = p + c
        out["arms"][k] = {
            "price_drift_pct_yr": round(float(np.nanmean(p) * n_per_year * 100), 2),
            "carry_pct_yr": round(float(np.nanmean(c) * n_per_year * 100), 2),
            "net_pct_yr": round(float(np.nanmean(tot) * n_per_year * 100), 2),
            "net_sharpe_daily_ann": round(float(np.nanmean(tot) / (np.nanstd(tot) + 1e-12)
                                                * np.sqrt(n_per_year)), 2),
            "mean_rank_ic_price": round(float(ic.mean()), 5),
            "per_year_net_pct": {y: round(float((np.nanmean(v["price"]) + np.nanmean(v["carry"]))
                                                * n_per_year * 100), 2)
                                 for y, v in sorted(per_year[k].items())}}
        print(f"[{k:28s}] price {out['arms'][k]['price_drift_pct_yr']:+7.2f}%/yr  "
              f"carry {out['arms'][k]['carry_pct_yr']:+7.2f}%/yr  "
              f"NET {out['arms'][k]['net_pct_yr']:+7.2f}%/yr  "
              f"Sh {out['arms'][k]['net_sharpe_daily_ann']:+5.2f}", flush=True)

    ref = out["arms"]["ref_binance_native"]["carry_pct_yr"]
    a_c = out["arms"]["A_binance_signal_hl_settle"]["carry_pct_yr"]
    b_c = out["arms"]["B_hl_native"]["carry_pct_yr"]
    out["carry_transfer_rate"] = {
        "A_over_reference": round(a_c / ref, 3) if ref else None,
        "B_over_reference": round(b_c / ref, 3) if ref else None,
        "xsec_funding_rank_corr_measured_earlier": 0.468,
        "interpretation": ("if A/reference >> 0.468 then carry transfers far better than the "
                           "average cross-sectional agreement suggests -- i.e. 0C's carry "
                           "concentration in the |funding| tail, which is exactly where the two "
                           "venues agree, does the work")}
    json.dump(out, open(MA + "/exports/eda/hl_carry_ab.json", "w"), indent=1)
    print(f"[transfer] carry A/ref = {out['carry_transfer_rate']['A_over_reference']} | "
          f"B/ref = {out['carry_transfer_rate']['B_over_reference']} "
          f"(xsec rank corr was 0.468)", flush=True)
    print("-> hl_carry_ab.json")


if __name__ == "__main__":
    main()
