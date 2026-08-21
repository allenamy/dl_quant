"""Build the per-DAY all-asset RAW-channel cache for the multi-asset raw-path arm.

WHY (information-expansion lever): the current multi-asset model consumes only
the 44 hand features in seq_cache F, and its DL uplift over the linear ceiling
is just +7% at y_600 — the hand-feature signal is nearly all linear. On
single-asset BTC the raw dual-path (learned encoder over undigested LOB state)
beat hand-features-only by +30%. This cache materialises the lightly-transformed
RAW microstructure state per bar so a conv/attention stem can learn its OWN
nonlinear, temporal digestion instead of our fixed aggregations.

One file per trading day, same day iteration / bar loading / output conventions
as `build_seq_cache.py`, time-aligned bar-for-bar with the seq_cache day file
(SAME `ts`, same T — GPU windowing indexes line up exactly):

    <RAW_DIR>/<day>.npz
        R        (S=14, T, C=36)  float16  raw channels per bar (full day)
        ts       (T,)             int64    ns timestamps == seq_cache <day>.npz ts
        ch_names (C,)             str      channel names, axis-2 order of R

Plus channel_names.json + build_meta.json at the cache root.

CHANNEL DESIGN (36 channels, 4 groups). Per-channel TRAIN-STAT standardization
happens DOWNSTREAM (per-fold, leak-free); here we apply only generous
pathological clips in fp16-safe ranges (fp16 max 65504; all clips << that).

  GROUP 1 — Price structure (10): `bid_off_bps_l{0..4}`, `ask_off_bps_l{0..4}`
    (px_l - mid)/mid * 1e4 per LOB level. Mechanism: the SHAPE of the price
    ladder — spread, level spacing, gaps — is microstructure state (queue
    priority economics, sniping risk, tick-constrained vs sparse books) that is
    invisible after scalar feature aggregation. Clip ±1000 bps (10% from mid =
    pathological/unquoted book).

  GROUP 2 — Size structure (10): `bid_ntl_log_l{0..4}`, `ask_ntl_log_l{0..4}`
    log1p(size_l * mid) = log-NOTIONAL resting per level. Notional (not coin
    qty) makes magnitudes cross-asset comparable so one shared encoder serves
    all 14 symbols. Mechanism: WHERE liquidity sits in the ladder
    (front-loaded vs deep-stacked) predicts short-horizon resilience to flow.
    Clip [0, 30] (e^30 ~ 1e13 USDT, beyond pathological).

  GROUP 3 — Cumulative-depth imbalance (9): `cdi_{0.1..1000.0}bps`
    (cumu_bid_dep_x - cumu_ask_dep_x)/(bid+ask+eps) per distance bucket. The
    schema stores SEPARATE bid/ask cumulative-depth arrays (cumu_bidsz_dep_x /
    cumu_asksz_dep_x), so a true two-sided imbalance is computable — no
    adaptation needed. Mechanism: depth asymmetry at increasing price distances
    = the pressure PROFILE (near-touch pressure vs deep-book conviction), a
    9-point curve the encoder can read jointly. Bounded [-1, 1].

  GROUP 4 — Flow state (7): per-bar UNDIGESTED flow, log1p notionals.
    `td_buy_ntl_log` / `td_sell_ntl_log`   log1p(tdQtyPxBuy/Sell) — taker buy /
        sell notional this bar (tdQtyPx is already qty*px = notional).
    `bk_add_bid_ntl_log` / `bk_add_ask_ntl_log` / `bk_del_bid_ntl_log` /
    `bk_del_ask_ntl_log`   log1p(qty * mid) — book add/delete notional per side
        (schema carries the 4 separate add/del-by-side qty columns; converted
        to notional via mid for cross-asset comparability).
        SCHEMA ADAPTATION: bkDelBid/bkDelAsk are stored as NEGATIVE quantities
        (deletions <= 0, verified on raw HDF5 2025-05-12: 99% of bars < 0,
        max == 0). We take |qty| before the notional log1p so the channel is
        the deletion MAGNITUDE; the side is already encoded in the channel
        identity. (A naive max(qty,0) clamp would silently zero these.)
    `td_imb`   (tdQtyBuy - tdQtySell)/(buy+sell+eps) — signed per-bar taker
        imbalance, bounded [-1, 1].
    Mechanism: hand features fix 30/60/300s rolling sums; per-bar raw flow lets
    the conv stem learn its OWN temporal kernels (decay shapes, burst
    detection, add-vs-del cancellation dynamics). Clip log-notional [0, 30].

NaN policy (mirrors build_seq_cache.py / features_ma.py): channels computed
from raw columns with NaN propagated, then nan_to_num(0.0) at the end. Warmup /
unquoted rows are already excluded downstream by the seq_cache `mask`; no ffill
is needed (the 1s bar grid carries state forward by construction, and the
hand-feature path makes the identical NaN->0 choice).

Read-only over the share. Idempotent: skips a day file that already exists
unless --force; writes via tmp-then-rename so an interrupted background build
never leaves a corrupt file that skip-existing would trust.

Usage:
    python multi_asset/data/build_raw_cache.py                 # full build
    python multi_asset/data/build_raw_cache.py --days 20250210 20250512
    python multi_asset/data/build_raw_cache.py --validate 20250210 ...

PRETRAIN-period build (raw x pretraining compound lever): same channels, clips
and file format over the 2022-01..2024-05 pretrain window, ts-aligned to the
PRETRAIN seq_cache day files (those are fp16 F-only but carry the same `ts`
array). `--days_from_seq` derives the exact day set from the seq_dir's
<day>.npz listing — the pretrain seq_cache day set is the alignment contract,
not the bar-dir listing (a bar day the seq build skipped must not get an
unverifiable raw file):

    python multi_asset/data/build_raw_cache.py \
        --seq_dir .../exports/pretrain/seq_cache \
        --out_dir .../exports/pretrain/raw_cache \
        --start 20220101 --end 20240531 --days_from_seq
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
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402
from multi_asset.data.build_seq_cache import (  # noqa: E402  (REUSE, not re-spec)
    SYMBOLS, WIN_START, WIN_END, SEQ_DIR, list_days,
)

RAW_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/raw_cache")

# 5-level LOB column names (level 0 has no suffix in the bar schema).
_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]
# 9 cumulative-depth distance buckets (suffix == bps from mid).
_DEP_BUCKETS = ["0.1", "0.3", "1.0", "3.0", "10.0", "30.0",
                "100.0", "300.0", "1000.0"]

_EPS = 1e-9
# Generous pathological clips ONLY (standardization is downstream, per-fold).
# All bounds are far inside the fp16 representable range (max 65504).
_CLIP_PX_BPS = 1000.0   # |level px offset| 10% from mid = unquoted/broken book
_CLIP_LOG_NTL = 30.0    # e^30 ~ 1e13 USDT notional
_CLIP_IMB = 1.0         # imbalances are bounded by construction


def raw_channel_names() -> list:
    """Channel names, axis-2 order of R. Must match build_raw_channels."""
    names = []
    names += [f"bid_off_bps_l{l}" for l in range(5)]
    names += [f"ask_off_bps_l{l}" for l in range(5)]
    names += [f"bid_ntl_log_l{l}" for l in range(5)]
    names += [f"ask_ntl_log_l{l}" for l in range(5)]
    names += [f"cdi_{dx}bps" for dx in _DEP_BUCKETS]
    names += ["td_buy_ntl_log", "td_sell_ntl_log",
              "bk_add_bid_ntl_log", "bk_add_ask_ntl_log",
              "bk_del_bid_ntl_log", "bk_del_ask_ntl_log",
              "td_imb"]
    return names


N_CH = len(raw_channel_names())  # 36


def _log_ntl(qty: np.ndarray, mid: np.ndarray) -> np.ndarray:
    """log1p of notional (qty * mid), negatives clamped to 0, NaN propagated
    (np.maximum propagates NaN; np.fmax would fabricate 0 — see raw_lob_ma)."""
    return np.log1p(np.maximum(qty * mid, 0.0))


def _imb(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(a-b)/(a+b+eps); 0 where both ~0; NaN propagates for downstream mask."""
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.abs(denom) > _EPS, (a - b) / (denom + _EPS), 0.0)


def build_raw_channels(panel, sym: str) -> np.ndarray:
    """(T, N_CH) float32 raw channels for `sym`, clipped + nan_to_num'd,
    fp16-safe. Columns consumed BY NAME (never by position); QTY columns
    arrive already scaled by the loader."""
    arr = panel.data[sym]
    cols = panel.cols

    def col(name: str) -> np.ndarray:
        return arr[:, cols.index(name)].astype(np.float64)

    mid = col("mid")
    mid_col = mid[:, np.newaxis]

    out = []

    # --- GROUP 1: price ladder offsets (bps from mid), 5 levels x 2 sides ---
    bid_px = np.column_stack([col(c) for c in _BID_PX])   # (T,5)
    ask_px = np.column_stack([col(c) for c in _ASK_PX])
    with np.errstate(divide="ignore", invalid="ignore"):
        bid_off = (bid_px - mid_col) / mid_col * 1e4
        ask_off = (ask_px - mid_col) / mid_col * 1e4
    out.append(np.clip(bid_off, -_CLIP_PX_BPS, _CLIP_PX_BPS))
    out.append(np.clip(ask_off, -_CLIP_PX_BPS, _CLIP_PX_BPS))

    # --- GROUP 2: per-level log-notional, 5 levels x 2 sides ---
    bid_sz = np.column_stack([col(c) for c in _BID_SZ])
    ask_sz = np.column_stack([col(c) for c in _ASK_SZ])
    out.append(np.clip(_log_ntl(bid_sz, mid_col), 0.0, _CLIP_LOG_NTL))
    out.append(np.clip(_log_ntl(ask_sz, mid_col), 0.0, _CLIP_LOG_NTL))

    # --- GROUP 3: cumulative-depth imbalance per distance bucket (9) ---
    cdi = np.column_stack([
        _imb(col(f"cumu_bidsz_dep_{dx}"), col(f"cumu_asksz_dep_{dx}"))
        for dx in _DEP_BUCKETS
    ])
    out.append(np.clip(cdi, -_CLIP_IMB, _CLIP_IMB))

    # --- GROUP 4: per-bar undigested flow state (7) ---
    tq_buy = col("tdQtyBuy")
    tq_sell = col("tdQtySell")
    flow = np.column_stack([
        np.log1p(np.maximum(col("tdQtyPxBuy"), 0.0)),    # already notional
        np.log1p(np.maximum(col("tdQtyPxSell"), 0.0)),
        _log_ntl(col("bkAddBid"), mid),
        _log_ntl(col("bkAddAsk"), mid),
        # del columns are stored NEGATIVE in the schema -> use magnitude
        # (see module docstring, GROUP 4 schema adaptation).
        _log_ntl(np.abs(col("bkDelBid")), mid),
        _log_ntl(np.abs(col("bkDelAsk")), mid),
    ])
    out.append(np.clip(flow, 0.0, _CLIP_LOG_NTL))
    out.append(np.clip(_imb(tq_buy, tq_sell), -_CLIP_IMB, _CLIP_IMB)
               [:, np.newaxis])

    R = np.concatenate(out, axis=1)            # (T, 36) float64
    assert R.shape[1] == N_CH, f"channel count {R.shape[1]} != {N_CH}"
    # NaN policy mirrors build_seq_cache F: NaN/inf -> 0; downstream mask owns
    # warmup / unquoted rows.
    R = np.nan_to_num(R, nan=0.0, posinf=0.0, neginf=0.0)
    return R.astype(np.float32)


def list_days_from_seq(seq_dir: str, start: int, end: int) -> list:
    """Day set from the seq_cache's own <YYYYMMDD>.npz files within [start, end].
    Used when the seq_cache day set (not the bar-dir listing) is the contract."""
    days = []
    for name in os.listdir(seq_dir):
        stem = name[:-4]
        if name.endswith(".npz") and stem.isdigit() and len(stem) == 8:
            di = int(stem)
            if start <= di <= end:
                days.append(di)
    return sorted(days)


def _seq_ts(day: int, seq_dir: str = SEQ_DIR):
    """ts of the seq_cache day file (lazy per-key load), or None if absent."""
    f = p.join(seq_dir, f"{day}.npz")
    if not p.exists(f):
        return None
    with np.load(f) as z:
        return z["ts"].astype(np.int64)


def build_one_day(day: int, out_path: str, seq_dir: str = SEQ_DIR) -> float:
    """Build one day file. Returns build seconds. Raises on ts mismatch with
    the seq_cache day file (alignment is the contract — fail loud)."""
    t0 = time.time()
    dp = load_day_panel(day, SYMBOLS)
    ts_day = dp.ts.astype(np.int64)

    sts = _seq_ts(day, seq_dir)
    if sts is not None and not np.array_equal(ts_day, sts):
        raise RuntimeError(
            f"day {day}: ts mismatch vs seq_cache (T {ts_day.shape[0]} vs "
            f"{sts.shape[0]}) — raw/seq alignment contract broken")

    T = ts_day.shape[0]
    R_all = np.zeros((len(SYMBOLS), T, N_CH), dtype=np.float16)
    for si, s in enumerate(SYMBOLS):
        R_all[si] = build_raw_channels(dp, s).astype(np.float16)

    if not np.isfinite(R_all).all():  # fp16 overflow guard (clips make this moot)
        raise RuntimeError(f"day {day}: non-finite values after fp16 cast")

    tmp = out_path + ".tmp.npz"
    np.savez(tmp, R=R_all, ts=ts_day,
             ch_names=np.array(raw_channel_names()))
    os.replace(tmp, out_path)
    return time.time() - t0


def _list_window_days(start: int, end: int, seq_dir: str,
                      days_from_seq: bool) -> list:
    """Window day set: from the seq_dir's day files (--days_from_seq) or the
    bar-dir listing (default, == build_seq_cache convention)."""
    if days_from_seq:
        return list_days_from_seq(seq_dir, start, end)
    return list_days(start, end)


def build(force: bool = False, days_subset: list | None = None,
          seq_dir: str = SEQ_DIR, out_dir: str = RAW_DIR,
          start: int = WIN_START, end: int = WIN_END,
          days_from_seq: bool = False):
    os.makedirs(out_dir, exist_ok=True)
    days = days_subset or _list_window_days(start, end, seq_dir, days_from_seq)
    print(f"[raw] window {start}..{end}"
          f"{' (days from seq_dir)' if days_from_seq else ''}: "
          f"{len(days)} days, {len(SYMBOLS)} symbols, {N_CH} ch -> {out_dir}",
          flush=True)

    t0 = time.time()
    n_done = n_skip = n_fail = 0
    for di, d in enumerate(days):
        out = p.join(out_dir, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            build_one_day(d, out, seq_dir)
        except Exception as e:  # missing/corrupt day -> skip, keep going
            n_fail += 1
            print(f"  [warn] day {d} failed: {e}", flush=True)
            continue
        n_done += 1
        if n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} "
                  f"skip={n_skip} fail={n_fail}  {el/60:.1f} min, "
                  f"~{rate*60:.1f} day/min, ETA {eta/60:.1f} min", flush=True)

    meta = {
        "window": [start, end],
        "seq_dir": seq_dir,
        "days_from_seq": days_from_seq,
        "n_days_listed": len(days),
        "n_days_built": n_done,
        "n_days_skipped": n_skip,
        "n_days_failed": n_fail,
        "n_channels": N_CH,
        "symbols": SYMBOLS,
        "dtype": "float16",
        "clips": {"px_bps": _CLIP_PX_BPS, "log_ntl": _CLIP_LOG_NTL,
                  "imb": _CLIP_IMB},
        "schema": {
            "R": f"(S,T,{N_CH}) f16 raw channels (see channel_names.json)",
            "ts": "(T,) int64 ns shared grid == seq_cache <day>.npz ts",
            "ch_names": f"({N_CH},) str channel names",
        },
        "note": ("per-channel train-stat standardization is DOWNSTREAM; "
                 "only pathological clips applied here (fp16-safe)"),
    }
    with open(p.join(out_dir, "channel_names.json"), "w") as f:
        json.dump(raw_channel_names(), f, indent=2)
    with open(p.join(out_dir, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[raw] done in {(time.time()-t0)/60:.1f} min: built={n_done} "
          f"skip={n_skip} fail={n_fail} -> {out_dir}", flush=True)


def validate(days: list, seq_dir: str = SEQ_DIR, out_dir: str = RAW_DIR,
             start: int = WIN_START, end: int = WIN_END,
             days_from_seq: bool = False):
    """Build (if needed) + report per-channel stats, ts alignment, size/time."""
    os.makedirs(out_dir, exist_ok=True)
    names = raw_channel_names()
    per_day_secs, per_day_mb = [], []
    agg = {nm: [] for nm in names}

    for d in days:
        out = p.join(out_dir, f"{d}.npz")
        secs = build_one_day(d, out, seq_dir)  # rebuild -> honest timing
        mb = os.path.getsize(out) / 1e6
        per_day_secs.append(secs)
        per_day_mb.append(mb)

        with np.load(out) as z:
            R = z["R"]
            ts = z["ts"]
        sts = _seq_ts(d, seq_dir)
        ts_ok = sts is not None and np.array_equal(ts, sts)
        print(f"\n=== day {d}: T={ts.shape[0]} R{R.shape} {mb:.1f} MB "
              f"{secs:.1f}s  ts==seq_cache: {ts_ok} ===", flush=True)
        if not ts_ok:
            raise RuntimeError(f"day {d}: ts mismatch vs seq_cache")

        Rf = R.astype(np.float32)  # stats in f32 to avoid f16 accumulation
        print(f"{'channel':<22}{'finite%':>9}{'mean':>10}{'std':>10}"
              f"{'min':>10}{'max':>10}")
        for ci, nm in enumerate(names):
            x = Rf[:, :, ci]
            ff = float(np.isfinite(x).mean())
            print(f"{nm:<22}{ff*100:>8.2f}%{x.mean():>10.3f}{x.std():>10.3f}"
                  f"{x.min():>10.3f}{x.max():>10.3f}", flush=True)
            agg[nm].append(ff)

    n_total = len(_list_window_days(start, end, seq_dir, days_from_seq))
    s = float(np.mean(per_day_secs))
    print(f"\n[validate] avg {s:.1f} s/day, {np.mean(per_day_mb):.1f} MB/day; "
          f"full build est: {n_total} days -> {n_total*s/3600:.1f} h, "
          f"{n_total*np.mean(per_day_mb)/1000:.1f} GB", flush=True)
    bad = [nm for nm, fs in agg.items() if min(fs) < 1.0]
    print(f"[validate] all-finite-fp16: "
          f"{'PASS' if not bad else 'FAIL ' + str(bad)}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    ap.add_argument("--days", type=int, nargs="+", default=None,
                    help="build only these YYYYMMDD days")
    ap.add_argument("--validate", type=int, nargs="+", default=None,
                    help="build + per-channel stat report for these days")
    ap.add_argument("--seq_dir", default=SEQ_DIR,
                    help="seq_cache dir used as the ts-alignment reference")
    ap.add_argument("--out_dir", default=RAW_DIR,
                    help="output raw_cache dir")
    ap.add_argument("--start", type=int, default=WIN_START,
                    help="window start YYYYMMDD")
    ap.add_argument("--end", type=int, default=WIN_END,
                    help="window end YYYYMMDD")
    ap.add_argument("--days_from_seq", action="store_true",
                    help="derive the day set from seq_dir's <day>.npz files "
                         "(instead of the bar-dir listing)")
    args = ap.parse_args()
    if args.validate:
        validate(args.validate, seq_dir=args.seq_dir, out_dir=args.out_dir,
                 start=args.start, end=args.end,
                 days_from_seq=args.days_from_seq)
    else:
        build(force=args.force, days_subset=args.days,
              seq_dir=args.seq_dir, out_dir=args.out_dir,
              start=args.start, end=args.end,
              days_from_seq=args.days_from_seq)
