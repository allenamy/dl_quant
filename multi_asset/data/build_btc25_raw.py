"""Build the per-day BTC 25-level RAW LADDER cache for the raw-path B-line
(leader-slot deep enrichment).

WHY: the B-line gives the BTC leader slot a deep-book raw path. raw_cache
already carries 5-level LOB + flow for every symbol; this cache materialises
the FULL 25-level price/size ladder for BTC only, lightly transformed (offsets
in bps + log-notional per level), so the temporal stem can learn its OWN
digestion of deep-book shape. Full 25-level granularity is kept — any pooling
is the model's decision, the cache must not destroy information.

Source data (READ-ONLY, schema proven by ``btc25_state.py``)
------------------------------------------------------------
    /mnt/storage/share/23-25-BTCUSDT/book_snapshot_25/YYYY-MM-DD/BTCUSDT.csv.gz

Tardis-style tick book snapshots, 25 explicit levels per side
(``asks[i].price/.amount``, ``bids[i].price/.amount``, i in 0..24),
``timestamp`` in MICROSECONDS. Calendar-UTC folders; the panel trading day d
spans UTC ~14:05 of d-1 .. 13:54:59 of d, so each build reads TWO calendar
files. Resampling REUSES the exact causal convention of ``btc25_state.py``
(imported, not re-implemented): floor tick ts to the second (never round),
keep the LAST tick per second, forward-fill onto the grid, with a SEED_S
ffill seed margin before the day's first bar.

Unlike btc25_state (180s prediction grid), the output here sits on the FULL
1s bar grid (T=85800) — ``ts`` is byte-identical to the seq_cache day file's
``ts`` so GPU windowing indexes line up exactly (hard-asserted at build time,
same contract as ``build_raw_cache.py``).

Output
------
    <OUT_DIR>/<day>.npz
        ts       (T,)      int64    ns, IDENTICAL to seq_cache/<day>.npz ts
        R25      (T, 104)  float16  raw ladder channels (order below)
        ch_names (104,)    str
    plus channel_names.json + build_meta.json at the cache root.

CHANNELS (104). Per-channel TRAIN-STAT standardization happens DOWNSTREAM
(per-fold, leak-free); here only generous pathological clips, fp16-safe
(fp16 max 65504; all clips << that). NaN policy mirrors build_raw_cache:
NaN propagated through the math, nan_to_num(0.0) at the very end (missing
level => offset 0 + notional 0; rows before the first tick are counted and
reported).

  GROUP 1 — price ladder offsets (50): ``bid_off_bps_l0..l24``,
    ``ask_off_bps_l0..l24`` = (px_l - mid)/mid * 1e4, clip +-1000. The SHAPE
    of the deep ladder (spacing, gaps, cliffs) is microstructure state that
    is invisible after scalar aggregation.

  GROUP 2 — size structure (50): ``bid_ntl_log_l0..l24``,
    ``ask_ntl_log_l0..l24`` = log1p(amount_l * price_l) (log-NOTIONAL at the
    level's own price), clip [0, 30]. WHERE liquidity sits in the deep ladder
    (front-loaded vs deep-stacked walls) is the resilience profile.

  GROUP 3 — 4 summary scalars (flow is NOT duplicated here — the BTC slot
    already gets flow from raw_cache):
    ``spread_bps``           (ask0-bid0)/mid*1e4, clip [-1000, 1000]
                             (negative = crossed book, kept as signature).
    ``microprice_dev_bps``   (micro-mid)/mid*1e4 with
                             micro=(ask0*bidsz0+bid0*asksz0)/(bidsz0+asksz0),
                             clip +-1000. Imminent tick-direction pressure.
    ``deep_imb_l1_25``       (sum bid sz - sum ask sz)/(sum+sum) over all 25
                             levels, bounded [-1,1] — EXACTLY btc25_state's
                             f0 formula (the gate-4 cross-check target).
    ``total_depth_ntl_log``  log1p(total 25-level notional, both sides),
                             clip [0, 30]. Overall liquidity regime.

Read-only over the share. Idempotent: skips existing day files unless
--force; writes tmp-then-rename so an interrupted background build never
leaves a corrupt file that skip-existing would trust. CPU-only, single
process (run under ``nice -n 10``; GPU training + the raw_cache build share
the box).

Usage
-----
    # quality-gate suite on 3 sample days (forces rebuild, prints all gates):
    python multi_asset/data/build_btc25_raw.py --validate 20250210 20250512 20250811
    # full batch build (detached):
    setsid nohup nice -n 10 python multi_asset/data/build_btc25_raw.py --all \
        >> multi_asset/exports/btc25_raw/build.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time
from collections import OrderedDict

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.btc25_state import (  # noqa: E402  (REUSE, not re-spec)
    BOOK25_ROOT, N_LVL, SEQ_DIR, _calendar_dates, _last_per_second,
    _read_day_file, list_days,
)
from multi_asset.data.btc25_state import OUT_DIR as STATE_DIR  # noqa: E402

OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/btc25_raw")

SEED_S = 600            # ffill seed margin before the day's first bar (s)

# Generous pathological clips ONLY (standardization is downstream, per-fold).
# All bounds far inside fp16 range (max 65504).
_CLIP_PX_BPS = 1000.0   # |offset| 10% from mid = unquoted/broken book
_CLIP_LOG_NTL = 30.0    # e^30 ~ 1e13 USDT notional
_CLIP_IMB = 1.0         # bounded by construction


def channel_names() -> list:
    """Channel names, axis-1 order of R25. Must match build_channels."""
    names = [f"bid_off_bps_l{i}" for i in range(N_LVL)]
    names += [f"ask_off_bps_l{i}" for i in range(N_LVL)]
    names += [f"bid_ntl_log_l{i}" for i in range(N_LVL)]
    names += [f"ask_ntl_log_l{i}" for i in range(N_LVL)]
    names += ["spread_bps", "microprice_dev_bps", "deep_imb_l1_25",
              "total_depth_ntl_log"]
    return names


N_CH = len(channel_names())  # 104

# ------------------------------------------------------------------- ticks
# Consecutive panel days share one calendar file (day d reads calendars
# [d-1, d], day d+1 reads [d, d+1]); cache the per-second REDUCTION of the
# last 2 calendar files so the sequential batch build reads each ~50 MB
# csv.gz once instead of twice. Reduce-then-window is bit-identical to
# btc25_state's window-then-reduce because every window edge here is a whole
# second (the ticks of one second are never split across an edge).
_REDUCED_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 2


def _reduced_calendar(date_str: str):
    """(secs (n,) int64 epoch-s ascending, mats dict bp/bq/ap/aq (n,25) f64)
    = last-tick-per-second reduction of one full calendar file, cached."""
    hit = _REDUCED_CACHE.get(date_str)
    if hit is not None:
        return hit
    got = _last_per_second(_read_day_file(date_str), 0, 2 ** 62)
    if got is None:
        raise RuntimeError(f"{date_str}: calendar file has no ticks")
    _REDUCED_CACHE[date_str] = got
    while len(_REDUCED_CACHE) > _CACHE_MAX:
        _REDUCED_CACHE.popitem(last=False)
    return got


def _load_book_1s(grid_secs: np.ndarray):
    """Causal 1s book series on grid_secs (epoch s, ascending): per-second
    reduce the needed calendar files (cached), window to
    [grid0-SEED_S, grid_end], forward-fill onto the grid (NaN before the
    first available tick). Returns (book dict bp/bq/ap/aq (T,25) f64, diag)."""
    lo = int(grid_secs[0] - SEED_S)
    hi = int(grid_secs[-1])
    secs_l, mats_l = [], []
    for ds in _calendar_dates(lo, hi):
        secs, mats = _reduced_calendar(ds)
        i0 = np.searchsorted(secs, lo, side="left")
        i1 = np.searchsorted(secs, hi, side="right")
        if i1 > i0:
            secs_l.append(secs[i0:i1])
            mats_l.append({k: v[i0:i1] for k, v in mats.items()})
    if not secs_l:
        raise RuntimeError("no ticks in range")
    secs = np.concatenate(secs_l)
    if not np.all(secs[:-1] < secs[1:]):
        raise RuntimeError("tick seconds not strictly increasing across files")
    # causal ffill: last available second at-or-before each grid second
    pos = np.searchsorted(secs, grid_secs, side="right") - 1
    have = pos >= 0
    book = {}
    for k in ("bp", "bq", "ap", "aq"):
        v = np.concatenate([m[k] for m in mats_l], axis=0)
        g = np.full((grid_secs.shape[0], N_LVL), np.nan)
        g[have] = v[pos[have]]
        book[k] = g
    gaps = grid_secs[have] - secs[pos[have]]
    diag = {
        "n_nobook": int((~have).sum()),
        "max_ffill_gap_s": int(gaps.max()) if gaps.size else -1,
        "p999_ffill_gap_s": float(np.percentile(gaps, 99.9)) if gaps.size else -1,
    }
    return book, diag


# ---------------------------------------------------------------- channels
def build_channels(bp, bq, ap, aq) -> np.ndarray:
    """(T, 104) float64 raw ladder channels, clipped, NaN KEPT (caller counts
    non-finite rows, then nan_to_num + fp16). Inputs (T,25) f64."""
    mid = 0.5 * (bp[:, 0] + ap[:, 0])
    mid = np.where(mid > 0, mid, np.nan)
    midc = mid[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        # GROUP 1: price ladder offsets (bps from mid)
        bid_off = np.clip((bp - midc) / midc * 1e4, -_CLIP_PX_BPS, _CLIP_PX_BPS)
        ask_off = np.clip((ap - midc) / midc * 1e4, -_CLIP_PX_BPS, _CLIP_PX_BPS)
        # GROUP 2: per-level log-notional at the level's own price
        bid_ntl = np.clip(np.log1p(np.maximum(bq * bp, 0.0)), 0.0, _CLIP_LOG_NTL)
        ask_ntl = np.clip(np.log1p(np.maximum(aq * ap, 0.0)), 0.0, _CLIP_LOG_NTL)
        # GROUP 3: summary scalars
        spread = np.clip((ap[:, 0] - bp[:, 0]) / mid * 1e4,
                         -_CLIP_PX_BPS, _CLIP_PX_BPS)
        q0 = bq[:, 0] + aq[:, 0]
        micro = (ap[:, 0] * bq[:, 0] + bp[:, 0] * aq[:, 0]) \
            / np.where(q0 > 0, q0, np.nan)
        micro_dev = np.clip((micro - mid) / mid * 1e4,
                            -_CLIP_PX_BPS, _CLIP_PX_BPS)
        # deep imbalance — EXACT btc25_state f0 formula (gate-4 target)
        bqz = np.where(np.isfinite(bq), bq, 0.0)
        aqz = np.where(np.isfinite(aq), aq, 0.0)
        bsum, asum = bqz.sum(1), aqz.sum(1)
        tot = bsum + asum
        deep_imb = np.clip(np.where(tot > 0, (bsum - asum) / tot, np.nan),
                           -_CLIP_IMB, _CLIP_IMB)
        ntl_b = np.where(np.isfinite(bq * bp), bq * bp, 0.0).sum(1)
        ntl_a = np.where(np.isfinite(aq * ap), aq * ap, 0.0).sum(1)
        tot_ntl = np.where(
            np.isfinite(mid),
            np.clip(np.log1p(np.maximum(ntl_b + ntl_a, 0.0)),
                    0.0, _CLIP_LOG_NTL),
            np.nan)
    R = np.concatenate(
        [bid_off, ask_off, bid_ntl, ask_ntl,
         spread[:, None], micro_dev[:, None], deep_imb[:, None],
         tot_ntl[:, None]], axis=1)
    assert R.shape[1] == N_CH, f"channel count {R.shape[1]} != {N_CH}"
    return R


# ------------------------------------------------------------------- build
def _seq_ts(day: int) -> np.ndarray:
    """ts of the seq_cache day file. REQUIRED (alignment is the contract)."""
    f = p.join(SEQ_DIR, f"{day}.npz")
    if not p.exists(f):
        raise FileNotFoundError(f"seq_cache day file missing: {f}")
    with np.load(f) as z:
        return z["ts"].astype(np.int64)


def build_one_day(day: int, out_path: str, keep_book: bool = False) -> dict:
    """Build <out_path> for one trading day. Returns a stats dict. Raises on
    any ts/alignment problem (fail loud — alignment is the contract)."""
    t0 = time.time()
    ts = _seq_ts(day)                                  # (T,) ns, 1s grid
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {day}: seq_cache ts grid is not contiguous 1s")

    book, diag = _load_book_1s(grid_secs)
    R64 = build_channels(book["bp"], book["bq"], book["ap"], book["aq"])
    n_nan_rows = int((~np.isfinite(R64).all(axis=1)).sum())
    R16 = np.nan_to_num(R64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    if not np.isfinite(R16).all():   # fp16 overflow guard (clips make this moot)
        raise RuntimeError(f"day {day}: non-finite values after fp16 cast")

    # HARD alignment assert vs a fresh seq_cache read (same contract as
    # build_raw_cache; here the grid is DERIVED from seq ts so this also
    # guards against any accidental reshuffle above).
    sts = _seq_ts(day)
    if R16.shape[0] != ts.shape[0] or not np.array_equal(ts, sts):
        raise RuntimeError(
            f"day {day}: ts mismatch vs seq_cache — alignment contract broken")

    tmp = out_path + ".tmp.npz"
    np.savez(tmp, ts=ts, R25=R16, ch_names=np.array(channel_names()))
    os.replace(tmp, out_path)

    stats = {"day": day, "secs": time.time() - t0,
             "mb": os.path.getsize(out_path) / 1e6,
             "T": int(ts.shape[0]), "n_nan_rows": n_nan_rows, **diag}
    if keep_book:
        stats.update(ts=ts, R16=R16, book=book)
    return stats


def _write_meta(days: list, n_done: int, n_skip: int, n_fail: int,
                failed_days: list):
    meta = {
        "source": BOOK25_ROOT,
        "n_days_listed": len(days),
        "n_days_built": n_done, "n_days_skipped": n_skip,
        "n_days_failed": n_fail, "failed_days": failed_days,
        "n_channels": N_CH, "dtype": "float16", "seed_s": SEED_S,
        "clips": {"px_bps": _CLIP_PX_BPS, "log_ntl": _CLIP_LOG_NTL,
                  "imb": _CLIP_IMB},
        "schema": {
            "ts": "(T,) int64 ns, IDENTICAL to seq_cache <day>.npz ts",
            "R25": f"(T,{N_CH}) f16 BTC 25-level raw ladder channels",
            "ch_names": f"({N_CH},) str channel names",
        },
        "note": ("per-channel train-stat standardization is DOWNSTREAM; only "
                 "pathological clips applied here (fp16-safe); NaN->0 like "
                 "raw_cache (missing level => off 0 + ntl 0)"),
    }
    with open(p.join(OUT_DIR, "channel_names.json"), "w") as f:
        json.dump(channel_names(), f, indent=2)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(force: bool = False, days_subset: list | None = None):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset or list_days(SEQ_DIR)
    print(f"[btc25_raw] {len(days)} day(s), {N_CH} ch -> {OUT_DIR}", flush=True)

    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed_days = []
    for di, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:           # missing/corrupt day -> keep going
            n_fail += 1
            failed_days.append(d)
            print(f"  [warn] day {d} failed: {e}", flush=True)
            continue
        n_done += 1
        if st["n_nobook"] or st["n_nan_rows"]:
            print(f"  [warn] day {d}: n_nobook={st['n_nobook']} "
                  f"n_nan_rows={st['n_nan_rows']} (zero-filled)", flush=True)
        if n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} "
                  f"skip={n_skip} fail={n_fail}  {el/60:.1f} min, "
                  f"~{rate*60:.2f} day/min, ETA {eta/60:.1f} min", flush=True)

    _write_meta(days, n_done, n_skip, n_fail, failed_days)
    print(f"[btc25_raw] done in {(time.time()-t0)/60:.1f} min: built={n_done} "
          f"skip={n_skip} fail={n_fail}"
          + (f"  FAILED DAYS: {failed_days}" if failed_days else "")
          + f" -> {OUT_DIR}", flush=True)


# ------------------------------------------------------------ quality gates
def _gate2_finite_and_clips(R16: np.ndarray) -> bool:
    """Per-channel finite%, stats, and clip-bound check on the STORED fp16."""
    names = channel_names()
    Rf = R16.astype(np.float32)        # stats in f32, no fp16 accumulation
    lo_hi = ([(-_CLIP_PX_BPS, _CLIP_PX_BPS)] * 100
             + [(-_CLIP_PX_BPS, _CLIP_PX_BPS)] * 2
             + [(-_CLIP_IMB, _CLIP_IMB)]
             + [(0.0, _CLIP_LOG_NTL)])
    lo_hi[50:100] = [(0.0, _CLIP_LOG_NTL)] * 50
    ok = True
    print(f"  {'channel':<22}{'finite%':>9}{'mean':>10}{'std':>10}"
          f"{'min':>10}{'max':>10}  in-clip")
    for ci, nm in enumerate(names):
        x = Rf[:, ci]
        ff = float(np.isfinite(x).mean())
        lo, hi = lo_hi[ci]
        inb = bool(np.isfinite(x).all() and x.min() >= lo and x.max() <= hi)
        ok &= (ff == 1.0) and inb
        print(f"  {nm:<22}{ff*100:>8.2f}%{x.mean():>10.3f}{x.std():>10.3f}"
              f"{x.min():>10.3f}{x.max():>10.3f}  {'OK' if inb else 'FAIL'}",
              flush=True)
    return ok


def _gate3_ladder(book: dict, R16: np.ndarray) -> bool:
    """Book-ladder ordering on the f64 PRE-quantization prices (the true
    book), >=99.9% of quoted bars must be clean. fp16 adjacent-level ties
    are reported separately (quantization info, not a data defect)."""
    bp, ap = book["bp"], book["ap"]
    have = np.isfinite(bp[:, 0]) & np.isfinite(ap[:, 0])
    with np.errstate(invalid="ignore"):
        bad_bid = (np.diff(bp, axis=1) >= 0).any(axis=1)   # NaN pair -> False
        bad_ask = (np.diff(ap, axis=1) <= 0).any(axis=1)
        crossed = have & ((ap[:, 0] - bp[:, 0]) <= 0)
    missing = have & ~(np.isfinite(bp).all(axis=1) & np.isfinite(ap).all(axis=1))
    bad = have & (bad_bid | bad_ask | crossed | missing)
    n_have = int(have.sum())
    frac_clean = 1.0 - bad.sum() / max(n_have, 1)
    full = have & ~missing
    ob = R16[:, :N_LVL].astype(np.float32)
    oa = R16[:, N_LVL:2 * N_LVL].astype(np.float32)
    ties = int((full & ((np.diff(ob, axis=1) == 0).any(axis=1)
                        | (np.diff(oa, axis=1) == 0).any(axis=1))).sum())
    ok = frac_clean >= 0.999
    print(f"  quoted bars={n_have}  no-book rows={int((~have).sum())}\n"
          f"  bid-order viol={int((have & bad_bid).sum())}  "
          f"ask-order viol={int((have & bad_ask).sum())}  "
          f"crossed-top={int(crossed.sum())}  missing-level bars={int(missing.sum())}\n"
          f"  clean ladder: {100*frac_clean:.4f}% (gate >=99.9%) "
          f"{'PASS' if ok else 'FAIL'}\n"
          f"  [info] fp16 adjacent-level ties (quantization, not a defect): "
          f"{ties} bars ({100*ties/max(int(full.sum()),1):.3f}%)", flush=True)
    return ok


def _gate4_crosscheck(day: int, ts: np.ndarray, R16: np.ndarray,
                      book: dict, n_pick: int = 3) -> bool:
    """Recompute deep_imb from R25 level channels at random btc25_state grid
    ts and compare with btc25_state f0 (same shared tick source).

    fp16 path: per-level weight w = expm1(ntl_log)/(1 + off_bps*1e-4)
    = amount*price/(px/mid) = amount*mid — the common mid cancels in the
    imbalance ratio, so this reproduces the SIZE imbalance exactly up to
    fp16 quantization. f64 path (pre-quantization book) must match f0 to
    float32 storage precision of btc25_state (<1e-6) — that is the
    "float precision of the shared source" criterion.

    fp16 tolerance is the ANALYTIC quantization bound, not a round number:
    ntl_log ~ [8,16) has fp16 ulp 2^-7, so stored ntl abs err <= 2^-8 and
    notional rel err = |d expm1| ~ ulp/2 <= 0.39%; worst-case (fully
    correlated within a side) imbalance err ~ (1-imb^2)*0.39% < 4e-3.
    """
    sf = p.join(STATE_DIR, f"{day}.npz")
    if not p.exists(sf):
        print(f"  [gate4] SKIP: btc25_state file missing for {day}", flush=True)
        return False
    with np.load(sf) as z:
        zts, Z = z["ts"].astype(np.int64), z["Z"]
    rng = np.random.default_rng(42 + day)
    pick = np.sort(rng.choice(zts.shape[0], size=n_pick, replace=False))
    idx = np.searchsorted(ts, zts[pick])
    if not np.array_equal(ts[idx], zts[pick]):
        print("  [gate4] FAIL: btc25_state ts not found in R25 ts", flush=True)
        return False
    ok = True
    for k, r in zip(pick, idx):
        f0 = float(Z[k, 0])
        bqz = np.where(np.isfinite(book["bq"][r]), book["bq"][r], 0.0)
        aqz = np.where(np.isfinite(book["aq"][r]), book["aq"][r], 0.0)
        imb64 = (bqz.sum() - aqz.sum()) / (bqz.sum() + aqz.sum())
        ob = R16[r, :N_LVL].astype(np.float64)
        oa = R16[r, N_LVL:2 * N_LVL].astype(np.float64)
        nb = R16[r, 2 * N_LVL:3 * N_LVL].astype(np.float64)
        na = R16[r, 3 * N_LVL:4 * N_LVL].astype(np.float64)
        wb = np.expm1(nb) / (1.0 + ob * 1e-4)
        wa = np.expm1(na) / (1.0 + oa * 1e-4)
        imb16 = (wb.sum() - wa.sum()) / (wb.sum() + wa.sum())
        stored = float(R16[r, 4 * N_LVL + 2])          # deep_imb_l1_25
        d64, d16, dst = abs(imb64 - f0), abs(imb16 - f0), abs(stored - f0)
        row_ok = (d64 < 1e-6) and (d16 < 4e-3) and (dst < 1e-3)
        ok &= row_ok
        print(f"  ts={zts[k]}  f0={f0:+.6f}  f64-book={imb64:+.6f} "
              f"(|d|={d64:.2e})  fp16-recompute={imb16:+.6f} (|d|={d16:.2e})  "
              f"stored-ch={stored:+.6f} (|d|={dst:.2e})  "
              f"{'PASS' if row_ok else 'FAIL'}", flush=True)
    print(f"  [gate4] tolerances: f64<1e-6 (f32 storage of btc25_state = "
          f"float precision of shared source), fp16<4e-3 / stored<1e-3 "
          f"(analytic fp16 quantization bounds)  "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def validate(days: list):
    """Force-build the sample days + run quality gates 1-5, print everything."""
    os.makedirs(OUT_DIR, exist_ok=True)
    n_total = len(list_days(SEQ_DIR))
    per_day_secs, per_day_mb = [], []
    gates = {g: True for g in (1, 2, 3, 4)}

    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        st = build_one_day(d, out, keep_book=True)     # force rebuild: honest timing
        per_day_secs.append(st["secs"])
        per_day_mb.append(st["mb"])
        ts, R16, book = st["ts"], st["R16"], st["book"]
        print(f"\n================ day {d}: T={st['T']} R25={R16.shape} "
              f"{st['mb']:.1f} MB  {st['secs']:.1f}s ================",
              flush=True)

        # GATE 1: ts identity vs seq_cache (re-read the SAVED file: end-to-end)
        with np.load(out) as z:
            ts_saved, R_saved = z["ts"].astype(np.int64), z["R25"]
        sts = _seq_ts(d)
        g1 = (np.array_equal(ts_saved, sts) and R_saved.shape == (sts.shape[0], N_CH)
              and R_saved.dtype == np.float16)
        gates[1] &= g1
        print(f"[GATE 1] ts==seq_cache ts: {np.array_equal(ts_saved, sts)}  "
              f"T={ts_saved.shape[0]} (85800 expected)  dtype={R_saved.dtype}  "
              f"{'PASS' if g1 else 'FAIL'}", flush=True)

        # GATE 2: all-finite fp16 + clip bounds (on the saved array)
        print(f"[GATE 2] per-channel finite% + clip bounds "
              f"(no-book rows zero-filled: {st['n_nobook']}, "
              f"NaN rows zero-filled: {st['n_nan_rows']}, "
              f"max ffill gap: {st['max_ffill_gap_s']}s, "
              f"p99.9 gap: {st['p999_ffill_gap_s']:.1f}s)", flush=True)
        g2 = _gate2_finite_and_clips(R_saved)
        gates[2] &= g2
        print(f"[GATE 2] {'PASS' if g2 else 'FAIL'}", flush=True)

        # GATE 3: ladder monotonicity on the pre-fp16 book
        print("[GATE 3] ladder ordering (f64 source book)", flush=True)
        gates[3] &= _gate3_ladder(book, R_saved)

        # GATE 4: deep_imb cross-check vs btc25_state f0
        print("[GATE 4] deep_imb recompute vs btc25_state f0 "
              "(3 random 180s-grid ts)", flush=True)
        gates[4] &= _gate4_crosscheck(d, ts, R_saved, book)

    # GATE 5: size / time / full-build estimate
    s, mb = float(np.mean(per_day_secs)), float(np.mean(per_day_mb))
    print(f"\n[GATE 5] avg {s:.1f} s/day, {mb:.1f} MB/day; full build est "
          f"({n_total} days): {n_total*s/3600:.1f} h, "
          f"{n_total*mb/1000:.1f} GB", flush=True)
    print("\n[validate] " + "  ".join(
        f"GATE{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + "  GATE5=reported", flush=True)
    if not all(gates.values()):
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every seq_cache day (skip existing)")
    g.add_argument("--days", type=int, nargs="+",
                   help="build only these YYYYMMDD days")
    g.add_argument("--validate", type=int, nargs="+",
                   help="force-build + full quality-gate suite on these days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        build(force=args.force, days_subset=args.days)
