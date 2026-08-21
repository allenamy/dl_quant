"""Phase-0b/A — FUNDING/OI/POSITIONING cross-sectional factors on the 14-asset panel (180s grid).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The DIFFERENTIATED bet (research top-1/2): funding + positioning are slow, persistent,
latency-tolerant, and orthogonal to the (null) price factors. Since B≈0, these standalone
xsec rank-ICs ≈ incremental orthogonal alpha.

Align to the panel 180s grid (from mid_panel.npz), CAUSAL ffill ≤t:
- funding (8h settlements, calc_time = when the rate is settled/known) → last settlement ≤t.
- metrics (5m, create_time = when the snapshot is published) → last snapshot ≤t.

FACTORS (per-asset, RAW; xsec_ridge_h xsec-z's per ts). ★ = prime:
  ★ funding_carry   last settled funding rate (rank: short high / long low = crowding reversion)
    funding_ema     ~24h (3-settlement) EMA of funding (slower)
  ★ pos_divergence  log(top-trader ACCOUNT ls) − log(GLOBAL ACCOUNT ls)  (smart vs crowd; fade)
    toptrader_pos   log top-trader POSITION ls ratio
    global_account  log global account ls ratio
    oi_mom_24h      ΔlogOI over 24h (open-interest momentum)
    taker_ratio     log taker buy/sell vol ratio

Output: funding_factor_cache/<sym>.npz {X (nT,F) raw, ts, day, factor_names}.
"""
from __future__ import annotations
import argparse, datetime as dt, os, os.path as p
import numpy as np, pandas as pd

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
FUND = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/funding"
MIDCACHE = ROOT + "/mid_panel.npz"
OUT = ROOT + "/funding_factor_cache"
NS = 1_000_000_000
STRIDE = 180
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]


def _ffill_to_panel(src_ts_ns, src_vals, panel_ts):
    """Causal as-of: for each panel ts, the last src value with src_ts ≤ panel_ts (≤t ffill)."""
    order = np.argsort(src_ts_ns)
    st = src_ts_ns[order]; sv = src_vals[order]
    pos = np.searchsorted(st, panel_ts, side="right") - 1     # last index ≤ panel_ts
    out = np.full(len(panel_ts), np.nan)
    ok = pos >= 0
    out[ok] = sv[pos[ok]]
    return out


def build():
    z = np.load(MIDCACHE, allow_pickle=True)
    panel_ts = z["ts"].astype(np.int64); day = z["day"].astype(np.int64)
    nT = len(panel_ts)
    os.makedirs(OUT, exist_ok=True)
    # BTC OI for reference not needed; each asset independent
    per_factor_names = None
    covs = {}
    for si, s in enumerate(SYMBOLS):
        ff = p.join(FUND, f"{s}_funding.csv"); mf = p.join(FUND, f"{s}_metrics_5m.csv")
        if not (p.exists(ff) and p.exists(mf)):
            print(f"  [warn] {s}: missing csv"); continue
        fd = pd.read_csv(ff)
        fts = (fd["fundingTime_ms"].values.astype(np.int64)) * 1_000_000     # ms -> ns
        frate = fd["fundingRate"].values.astype(np.float64)
        # ~24h EMA on the funding settlement series (span=3 settlements)
        fema = pd.Series(frate).ewm(span=3, adjust=False).mean().values
        md = pd.read_csv(mf)
        mts = (pd.to_datetime(md["create_time"], utc=True).astype("int64").values)   # ns
        oi = md["sum_open_interest"].values.astype(np.float64)
        tt_acc = md["count_toptrader_long_short_ratio"].values.astype(np.float64)   # top-trader ACCOUNT
        tt_pos = md["sum_toptrader_long_short_ratio"].values.astype(np.float64)     # top-trader POSITION
        glob = md["count_long_short_ratio"].values.astype(np.float64)              # global ACCOUNT
        taker = md["sum_taker_long_short_vol_ratio"].values.astype(np.float64)

        f_carry = _ffill_to_panel(fts, frate, panel_ts)
        f_ema = _ffill_to_panel(fts, fema, panel_ts)
        loi = _ffill_to_panel(mts, np.log(np.where(oi > 0, oi, np.nan)), panel_ts)
        ltt_acc = _ffill_to_panel(mts, np.log(np.where(tt_acc > 0, tt_acc, np.nan)), panel_ts)
        ltt_pos = _ffill_to_panel(mts, np.log(np.where(tt_pos > 0, tt_pos, np.nan)), panel_ts)
        lglob = _ffill_to_panel(mts, np.log(np.where(glob > 0, glob, np.nan)), panel_ts)
        ltaker = _ffill_to_panel(mts, np.log(np.where(taker > 0, taker, np.nan)), panel_ts)

        pos_div = ltt_acc - lglob
        # OI momentum 24h on the ffilled panel-grid loi (searchsorted ts-24h, exact)
        tgt = panel_ts - 24 * 3600 * NS
        j = np.searchsorted(panel_ts, tgt); jj = np.clip(j, 0, nT - 1)
        okm = (j >= 0) & (np.abs(panel_ts[jj] - tgt) < 2 * STRIDE * NS)
        oi_mom = np.full(nT, np.nan); oi_mom[okm] = loi[okm] - loi[jj[okm]]

        names = ["funding_carry", "funding_ema", "pos_divergence", "toptrader_pos",
                 "global_account", "oi_mom_24h", "taker_ratio"]
        X = np.column_stack([f_carry, f_ema, pos_div, ltt_pos, lglob, oi_mom, ltaker]).astype(np.float32)
        per_factor_names = names
        np.savez(p.join(OUT, f"{s}.npz"), X=X, ts=panel_ts, day=day,
                 factor_names=np.array(names, dtype=object))
        covs[s] = np.isfinite(X).mean(0)
    print(f"[funding] {len(per_factor_names)} factors, nT={nT} -> {OUT}")
    if covs:
        avg = np.mean(np.stack(list(covs.values())), 0)
        for k, nm in enumerate(per_factor_names):
            print(f"   {nm:15s} avg-coverage={avg[k]:.3f}")
        print(f"   assets built: {len(covs)}/14")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.parse_args()
    build()
