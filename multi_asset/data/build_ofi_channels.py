"""BATCH-0 raw-LOB stationary-transform channels for the Ridge pre-gate (v2 axis-1+5).

Builds, per asset on the 487-day production window, the microstructure channels the
44-feature baseline collapses away — as STATIONARY transforms (the horizon literature's
winning move: OFI/depth-shape, not end-to-end raw ladder nets). Aligned to the
panel_cache stride-180 pred grid by ts so they concat 1:1 with the 44-feat baseline for
a cross-sectional Ridge walk-forward gate (ΔP>=+0.005, per-fold sign, shuffle-null).

Channel families (all strictly causal, reuse features_ma primitives):
  A. MULTI-LEVEL OFI LADDER — per-level Cont-Kukanov-Stoikov signed queue change,
     NOT summed (our ofi_60s sums all 5 into one). 5 levels x {300,600,1800}s rolls.
  B. DECOMPOSED AGGRESSIVE/PASSIVE OFI (Sitaru ICAIF'23) — aggressive = taker signed
     volume (tdQtyBuy-tdQtySell); passive = book add/del signed by side
     ((addBid-delBid)-(addAsk-delAsk)) — the add/del event data we've never used as a
     signed signal. Each at EMA half-lives {60,300,600,1800}s.
  C. VOLUME-AT-DISTANCE MAP (Lucchese'24) — the 4 cumulative-depth buckets the 44-feat
     depth_ratio never uses (0.1/0.3/300/1000 bps) as imbalances + near-vs-far depth
     concentration per side.
The per-asset aggressive-OFI columns (B) also serve the LAGGED CROSS-ASSET OFI gate
(Cont'23) — assembled at gate time (BTC/ETH aggressive-OFI lagged, >=t, shuffle-null),
no extra build here.

Usage: PYTHONPATH=. python multi_asset/data/build_ofi_channels.py [--win_start .. --win_end ..]
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402
from multi_asset.data.features_ma import (  # noqa: E402
    _col, _causal_lag, _causal_roll_sum, _imbalance, _EPS, HORIZON,
)

SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
WIN_START = 20240601
WIN_END = 20250930
PRED_STRIDE = 180

_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]
_DEP_UNUSED = ["0.1", "0.3", "300.0", "1000.0"]     # buckets the 44-feat depth_ratio omits
_DEP_NEAR = "1.0"
_DEP_FAR = "100.0"

OFI_WINS = (300, 600, 1800)
EMA_HL = (60, 300, 600, 1800)                        # half-lives (seconds)
CLIP_FLOW = 1e7
CLIP_RATIO = 1.0
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/ofi_channels")


def list_days(start, end):
    return sorted(int(n) for n in os.listdir(_BAR_PATH)
                 if n.isdigit() and len(n) == 8 and start <= int(n) <= end)


def _ema_causal(x, half_life):
    """Causal EMA with the given half-life (seconds==bars), vectorized via a first-
    order IIR filter: ema[t]=alpha*x[t]+(1-alpha)*ema[t-1], ema[-1]=0. NaN->0 increment.
    alpha = 1 - 2^(-1/hl). Strictly backward (no future leakage)."""
    from scipy.signal import lfilter
    alpha = 1.0 - 2.0 ** (-1.0 / half_life)
    xf = np.where(np.isfinite(x), x, 0.0)
    return lfilter([alpha], [1.0, -(1.0 - alpha)], xf)


def _per_level_ofi(panel, sym):
    """(T,5) per-level Cont-Kukanov-Stoikov signed queue change (same construction as
    features_ma.ofi_per_bar but NOT summed across levels)."""
    bid_px = [_col(panel, sym, c) for c in _BID_PX]
    ask_px = [_col(panel, sym, c) for c in _ASK_PX]
    bid_sz = [_col(panel, sym, c) for c in _BID_SZ]
    ask_sz = [_col(panel, sym, c) for c in _ASK_SZ]
    T = bid_px[0].shape[0]
    ofi = np.zeros((T, 5))
    for lvl in range(5):
        bp, bpz = bid_px[lvl], bid_sz[lvl]
        ap, apz = ask_px[lvl], ask_sz[lvl]
        bp_prev, bpz_prev = _causal_lag(bp, 1), _causal_lag(bpz, 1)
        ap_prev, apz_prev = _causal_lag(ap, 1), _causal_lag(apz, 1)
        with np.errstate(invalid="ignore"):
            bid_term = np.where(bp > bp_prev, bpz,
                       np.where(bp < bp_prev, -bpz_prev, bpz - bpz_prev))
            ask_term = np.where(ap < ap_prev, apz,
                       np.where(ap > ap_prev, -apz_prev, apz - apz_prev))
        ofi[:, lvl] = (np.where(np.isfinite(bid_term), bid_term, 0.0)
                       - np.where(np.isfinite(ask_term), ask_term, 0.0))
    return ofi


def build_channels(panel, sym):
    """Per-asset (T, n_new) causal channels + names."""
    feats, names = [], []

    def add(nm, v, clip):
        feats.append(np.clip(np.asarray(v, np.float64), -clip, clip)); names.append(nm)

    # A. multi-level OFI ladder
    ofi5 = _per_level_ofi(panel, sym)                # (T,5)
    for lvl in range(5):
        for w in OFI_WINS:
            add(f"ofiL{lvl}_{w}s", _causal_roll_sum(ofi5[:, lvl], w), CLIP_FLOW)

    # B. decomposed aggressive / passive OFI, EMA half-lives
    aggr = _col(panel, sym, "tdQtyBuy") - _col(panel, sym, "tdQtySell")
    pas = ((_col(panel, sym, "bkAddBid") - _col(panel, sym, "bkDelBid"))
           - (_col(panel, sym, "bkAddAsk") - _col(panel, sym, "bkDelAsk")))
    for hl in EMA_HL:
        add(f"aggrofi_ema{hl}", _ema_causal(aggr, hl), CLIP_FLOW)
        add(f"passofi_ema{hl}", _ema_causal(pas, hl), CLIP_FLOW)

    # C. volume-at-distance map — the 4 omitted buckets + near/far concentration
    for dx in _DEP_UNUSED:
        cb = _col(panel, sym, f"cumu_bidsz_dep_{dx}")
        ca = _col(panel, sym, f"cumu_asksz_dep_{dx}")
        add(f"depth_ratio_{dx}bps", _imbalance(cb, ca), CLIP_RATIO)
    near_b = _col(panel, sym, f"cumu_bidsz_dep_{_DEP_NEAR}")
    far_b = _col(panel, sym, f"cumu_bidsz_dep_{_DEP_FAR}")
    near_a = _col(panel, sym, f"cumu_asksz_dep_{_DEP_NEAR}")
    far_a = _col(panel, sym, f"cumu_asksz_dep_{_DEP_FAR}")
    with np.errstate(divide="ignore", invalid="ignore"):
        add("depth_conc_bid", np.where(far_b > _EPS, near_b / far_b, np.nan), 50.0)
        add("depth_conc_ask", np.where(far_a > _EPS, near_a / far_a, np.nan), 50.0)

    F = np.stack(feats, axis=1).astype(np.float64)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    return F.astype(np.float32), names


def build(win_start=WIN_START, win_end=WIN_END, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    days = list_days(win_start, win_end)
    print(f"[ofi] window {win_start}..{win_end}: {len(days)} days, {len(SYMBOLS)} symbols "
          f"-> {out_dir}", flush=True)
    acc = {s: {"X": [], "ts": [], "day": []} for s in SYMBOLS}
    names = None
    t0 = time.time(); n_fail = 0
    for di, d in enumerate(days):
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            n_fail += 1; print(f"  [warn] day {d}: {e}", flush=True); continue
        ts_day = dp.ts.astype(np.int64)
        T = ts_day.shape[0]
        base_idx = np.arange(0, T - HORIZON, PRED_STRIDE)     # same pred grid as panel_cache
        for s in SYMBOLS:
            Fc, nm = build_channels(dp, s)
            if names is None:
                names = nm
            acc[s]["X"].append(Fc[base_idx])
            acc[s]["ts"].append(ts_day[base_idx])
            acc[s]["day"].append(np.full(base_idx.shape[0], d, np.int32))
        if (di + 1) % 25 == 0 or di == len(days) - 1:
            el = time.time() - t0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  {el/60:.1f}min "
                  f"ETA {(len(days)-di-1)/((di+1)/el)/60:.1f}min", flush=True)
    for s in SYMBOLS:
        if not acc[s]["X"]:
            print(f"  [warn] {s}: no rows"); continue
        X = np.concatenate(acc[s]["X"]).astype(np.float32)
        ts = np.concatenate(acc[s]["ts"]).astype(np.int64)
        day = np.concatenate(acc[s]["day"]).astype(np.int32)
        np.savez(p.join(out_dir, f"{s}.npz"), X=X, ts=ts, day=day,
                 names=np.array(names, dtype=object))
        print(f"  saved {s}: n={X.shape[0]} n_ch={X.shape[1]}", flush=True)
    with open(p.join(out_dir, "channel_names.json"), "w") as f:
        json.dump(names, f, indent=2)
    print(f"[ofi] done in {(time.time()-t0)/60:.1f}min ({len(names)} channels, "
          f"fail={n_fail}) -> {out_dir}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--win_start", type=int, default=WIN_START)
    ap.add_argument("--win_end", type=int, default=WIN_END)
    ap.add_argument("--out_dir", default=OUT_DIR)
    args = ap.parse_args()
    build(win_start=args.win_start, win_end=args.win_end, out_dir=args.out_dir)
