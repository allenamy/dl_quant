"""Build the per-day BTC 25-level RAW LADDER cache from the CALIBER-CORRECT
PERP book (binance-futures) — the corrected twin of ``build_btc25_raw.py``.

WHY THIS FILE EXISTS
--------------------
``build_btc25_raw.py`` built ``exports/btc25_raw/`` from the SPOT book
(``/mnt/storage/share/23-25-BTCUSDT/book_snapshot_25``, exchange='binance').
That SPOT book does NOT match our prediction target — bar_1s mid_bnfbtc is the
binance-FUTURES (perp) mid. The instrument mismatch crippled the original B25
leader-enrichment experiment (its FAIL was a wrong-instrument artifact, not a
real null on deep-book alpha). The perp book was just verified to match the bar
perp target at corr 1.000, so the B25 line deserves a clean re-test on the
CORRECT instrument.

This builder is byte-for-byte identical to ``build_btc25_raw.py`` in every
transform (104 channels, identical clips, identical causal 1s ffill, identical
ts-alignment-to-seq_cache HARD assert, identical atomic tmp-then-rename writes)
EXCEPT the source is repointed to the PERP book and the output goes to a NEW
directory so the old SPOT cache survives for A/B comparison.

SOURCE (NEW, READ-ONLY — schema proven identical to the spot book)
------------------------------------------------------------------
    /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/
        book_snapshot_25/YYYY-MM-DD/binance-futures/BTCUSDT.csv.gz

Same Tardis 25-level schema (exchange='binance-futures', symbol='BTCUSDT',
timestamp in MICROSECONDS, asks[0..24].price/.amount, bids[0..24].price/.amount).
Covers 2023-01-01 .. 2026-05-31 — fully spans the panel window 20240601..20250930.

OUTPUT (NEW DIR — old btc25_raw is NOT touched)
-----------------------------------------------
    <OUT_DIR=exports/btc25_raw_perp>/<day>.npz
        ts       (T,)      int64    ns, IDENTICAL to seq_cache/<day>.npz ts
        R25      (T, 104)  float16  raw ladder channels (same order as spot build)
        ch_names (104,)    str
    plus channel_names.json + build_meta.json at the cache root.

The transform math, channel order, clips, NaN policy, alignment contract are
all inherited UNCHANGED from build_btc25_raw (the functions are imported, not
re-implemented). Only the file reader and the cache directory differ.

GATES (--validate): identical 1/2/3/5 to the spot build, PLUS:
  GATE 4  — deep_imb SELF-consistency on the PERP ladder (f64-book vs
            fp16-recompute vs stored channel agree). NOT compared against
            btc25_state.f0 — that cache is SPOT, so an equality check there
            would (correctly) fail on instrument mismatch and tells us nothing.
  GATE 4b — CALIBER (the whole point): perp-book L1 mid == bar_1s mid_bnfbtc
            to ~0 bps at matching ts.
  GATE 4c — old-SPOT vs new-PERP feature diff (deep_imb, spread_bps) to
            quantify how materially the corrected features moved.

CPU-only, single process (run under nice -n 10). Read-only over the source.

Usage
-----
    python multi_asset/data/build_btc25_raw_perp.py --validate 20250210 20250512 20250811
    setsid nohup nice -n 10 python multi_asset/data/build_btc25_raw_perp.py --all \
        >> multi_asset/exports/btc25_raw_perp/build.log 2>&1 &
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
import pandas as pd

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))

# Inherit EVERY transform UNCHANGED from the spot build + state module.
from multi_asset.data.btc25_state import (  # noqa: E402
    N_LVL, SEQ_DIR, _calendar_dates, _last_per_second, list_days, _TICK_COLS,
)
from multi_asset.data.build_btc25_raw import (  # noqa: E402
    channel_names, build_channels, N_CH, SEED_S,
    _CLIP_PX_BPS, _CLIP_LOG_NTL, _CLIP_IMB,
    _gate2_finite_and_clips, _gate3_ladder, _seq_ts,
)

# -------- the ONLY two repointed constants ---------------------------------
PERP_ROOT = ("/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/"
             "book_snapshot_25")                                 # READ-ONLY
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/btc25_raw_perp")
SPOT_OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
                "multi_asset/exports/btc25_raw")  # old cache, gate-4c A/B only
_BAR_PATH = "/mnt/storage/share/bar_data/bar_1s"  # gate-4b caliber, READ-ONLY


def _read_day_file_perp(date_str: str) -> pd.DataFrame:
    """PERP twin of btc25_state._read_day_file — same usecols/engine, perp path.
    READ-ONLY (pandas opens the gz read-only)."""
    path = p.join(PERP_ROOT, date_str, "binance-futures", "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    try:
        return pd.read_csv(path, usecols=_TICK_COLS, engine="pyarrow")
    except Exception:
        return pd.read_csv(path, usecols=_TICK_COLS, engine="c")


# ----- per-calendar-file reduction cache, identical logic to the spot build
# but reading the PERP file (cannot reuse _spot._reduced_calendar because it
# closes over the spot reader). Reduce-then-window is bit-identical to
# window-then-reduce: every window edge is a whole second.
_REDUCED_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 2


def _reduced_calendar(date_str: str):
    hit = _REDUCED_CACHE.get(date_str)
    if hit is not None:
        return hit
    got = _last_per_second(_read_day_file_perp(date_str), 0, 2 ** 62)
    if got is None:
        raise RuntimeError(f"{date_str}: PERP calendar file has no ticks")
    _REDUCED_CACHE[date_str] = got
    while len(_REDUCED_CACHE) > _CACHE_MAX:
        _REDUCED_CACHE.popitem(last=False)
    return got


def _load_book_1s(grid_secs: np.ndarray):
    """Identical to build_btc25_raw._load_book_1s but uses the PERP
    _reduced_calendar above. (Copied verbatim — only the reduction source
    differs.)"""
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


# ------------------------------------------------------------------- build
def build_one_day(day: int, out_path: str, keep_book: bool = False) -> dict:
    """PERP twin of build_btc25_raw.build_one_day. Same alignment contract,
    same atomic write. Uses the PERP _load_book_1s + the SHARED build_channels.
    """
    t0 = time.time()
    ts = _seq_ts(day)                                  # (T,) ns, 1s grid
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {day}: seq_cache ts grid is not contiguous 1s")

    book, diag = _load_book_1s(grid_secs)
    R64 = build_channels(book["bp"], book["bq"], book["ap"], book["aq"])
    n_nan_rows = int((~np.isfinite(R64).all(axis=1)).sum())
    R16 = np.nan_to_num(R64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    if not np.isfinite(R16).all():
        raise RuntimeError(f"day {day}: non-finite values after fp16 cast")

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
        "source": PERP_ROOT,
        "source_instrument": "binance-futures (PERP) — caliber-correct vs bar mid_bnfbtc",
        "twin_of": "build_btc25_raw.py (SPOT) -> exports/btc25_raw",
        "n_days_listed": len(days),
        "n_days_built": n_done, "n_days_skipped": n_skip,
        "n_days_failed": n_fail, "failed_days": failed_days,
        "n_channels": N_CH, "dtype": "float16", "seed_s": SEED_S,
        "clips": {"px_bps": _CLIP_PX_BPS, "log_ntl": _CLIP_LOG_NTL,
                  "imb": _CLIP_IMB},
        "schema": {
            "ts": "(T,) int64 ns, IDENTICAL to seq_cache <day>.npz ts",
            "R25": f"(T,{N_CH}) f16 BTC 25-level raw ladder channels (PERP)",
            "ch_names": f"({N_CH},) str channel names",
        },
        "note": ("per-channel train-stat standardization is DOWNSTREAM; only "
                 "pathological clips applied here (fp16-safe); NaN->0 like "
                 "raw_cache (missing level => off 0 + ntl 0). PERP book."),
    }
    with open(p.join(OUT_DIR, "channel_names.json"), "w") as f:
        json.dump(channel_names(), f, indent=2)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(force: bool = False, days_subset: list | None = None):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset or list_days(SEQ_DIR)
    print(f"[btc25_raw_perp] {len(days)} day(s), {N_CH} ch -> {OUT_DIR}",
          flush=True)

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
    print(f"[btc25_raw_perp] done in {(time.time()-t0)/60:.1f} min: "
          f"built={n_done} skip={n_skip} fail={n_fail}"
          + (f"  FAILED DAYS: {failed_days}" if failed_days else "")
          + f" -> {OUT_DIR}", flush=True)


# ------------------------------------------------------------ quality gates
def _gate4_self_consistency(day: int, ts: np.ndarray, R16: np.ndarray,
                            book: dict, n_pick: int = 5) -> bool:
    """deep_imb SELF-consistency on the PERP ladder. The spot build's gate4
    compared against btc25_state.f0, but that cache is SPOT — comparing perp
    deep_imb to spot f0 would (rightly) fail on instrument mismatch and proves
    nothing about THIS cache. Instead we verify the THREE internal estimators
    of deep_imb agree on randomly-picked QUOTED rows:
      - f64 from the pre-quantization book (ground truth);
      - fp16-recompute  w = expm1(ntl_log)/(1+off_bps*1e-4) = amount*mid (mid
        cancels in the ratio) from the stored level channels;
      - the stored deep_imb_l1_25 summary channel.
    Tolerances are the spot build's analytic fp16 quantization bounds.
    """
    have = np.isfinite(book["bp"][:, 0]) & np.isfinite(book["ap"][:, 0])
    idx_have = np.flatnonzero(have)
    if idx_have.size < n_pick:
        print("  [gate4] FAIL: too few quoted rows", flush=True)
        return False
    rng = np.random.default_rng(42 + day)
    rows = np.sort(rng.choice(idx_have, size=n_pick, replace=False))
    ok = True
    for r in rows:
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
        d16, dst = abs(imb16 - imb64), abs(stored - imb64)
        row_ok = (d16 < 4e-3) and (dst < 1e-3)
        ok &= row_ok
        print(f"  ts={int(ts[r])}  f64-book={imb64:+.6f}  "
              f"fp16-recompute={imb16:+.6f} (|d|={d16:.2e})  "
              f"stored-ch={stored:+.6f} (|d|={dst:.2e})  "
              f"{'PASS' if row_ok else 'FAIL'}", flush=True)
    print(f"  [gate4] PERP deep_imb self-consistency  fp16<4e-3 / stored<1e-3 "
          f"(analytic fp16 quantization bounds)  {'PASS' if ok else 'FAIL'}",
          flush=True)
    return ok


def _gate4b_caliber(day: int, ts: np.ndarray, book: dict) -> bool:
    """CRITICAL caliber check — the WHOLE POINT of this rebuild. The perp-book
    L1 mid (0.5*(bid0+ask0) from the new ladder) must match the bar_1s perp
    mid_bnfbtc to ~0 bps at matching ts. (The old spot build would show a large
    spot-vs-perp basis here.)"""
    import h5py
    s = str(day)
    f = p.join(_BAR_PATH, s, f"data_{s[:4]}-{s[4:6]}-{s[6:]}.hdf5")
    if not p.exists(f):
        print(f"  [gate4b] SKIP: bar file missing {f}", flush=True)
        return False
    with h5py.File(f, "r") as cf:
        bts = cf["time64"][:].astype(np.int64)
        bmid = cf["mid_bnfbtc"][:].astype(np.float64)
    # bar ts should equal seq ts grid (both 1s); align by exact ts match
    pos = np.clip(np.searchsorted(ts, bts), 0, ts.shape[0] - 1)
    match = ts[pos] == bts
    book_mid = 0.5 * (book["bp"][:, 0] + book["ap"][:, 0])
    book_mid = np.where(book_mid > 0, book_mid, np.nan)
    bm = book_mid[pos]
    good = match & np.isfinite(bm) & np.isfinite(bmid) & (bmid > 0)
    if good.sum() < 1000:
        print(f"  [gate4b] FAIL: only {int(good.sum())} aligned finite rows",
              flush=True)
        return False
    dev_bps = (bm[good] - bmid[good]) / bmid[good] * 1e4
    med = float(np.median(np.abs(dev_bps)))
    p99 = float(np.percentile(np.abs(dev_bps), 99))
    mean_signed = float(np.mean(dev_bps))
    corr = float(np.corrcoef(bm[good], bmid[good])[0, 1])
    # ~0 bps: median abs dev under 1 bps and corr ~1.0
    ok = (med < 1.0) and (corr > 0.9999)
    print(f"  [gate4b] CALIBER perp-book-mid vs bar mid_bnfbtc on "
          f"{int(good.sum())} rows:", flush=True)
    print(f"    median |dev|={med:.4f} bps   p99 |dev|={p99:.4f} bps   "
          f"mean signed dev={mean_signed:+.4f} bps   corr={corr:.6f}",
          flush=True)
    print(f"    gate: median|dev|<1bps AND corr>0.9999  "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def _gate4c_spot_vs_perp_diff(day: int, ts: np.ndarray, R16: np.ndarray):
    """Quantify how materially the corrected PERP features differ from the old
    SPOT cache (deep_imb_l1_25, spread_bps, microprice_dev_bps). NOT a pass/fail
    gate — a magnitude report that tells us whether the B25 re-test is
    well-motivated (large diff) or likely to FAIL again (tiny diff)."""
    sf = p.join(SPOT_OUT_DIR, f"{day}.npz")
    if not p.exists(sf):
        print(f"  [gate4c] SKIP: old spot cache missing {sf}", flush=True)
        return
    with np.load(sf) as z:
        sts, Rs = z["ts"].astype(np.int64), z["R25"].astype(np.float32)
    if not np.array_equal(sts, ts):
        print("  [gate4c] SKIP: spot ts != perp ts (cannot align)", flush=True)
        return
    Rp = R16.astype(np.float32)
    names = channel_names()
    idx = {n: i for i, n in enumerate(names)}
    print("  [gate4c] old-SPOT vs new-PERP channel diffs (matched ts):",
          flush=True)
    print(f"    {'channel':<22}{'spot_mean':>11}{'perp_mean':>11}"
          f"{'spot_std':>10}{'perp_std':>10}{'corr':>8}{'med|d|':>10}"
          f"{'RMSdiff':>10}", flush=True)
    for nm in ("deep_imb_l1_25", "spread_bps", "microprice_dev_bps",
               "total_depth_ntl_log"):
        i = idx[nm]
        a, b = Rs[:, i], Rp[:, i]
        g = np.isfinite(a) & np.isfinite(b)
        if g.sum() < 100:
            continue
        c = float(np.corrcoef(a[g], b[g])[0, 1]) if a[g].std() > 0 and b[g].std() > 0 else float("nan")
        medad = float(np.median(np.abs(a[g] - b[g])))
        rms = float(np.sqrt(np.mean((a[g] - b[g]) ** 2)))
        print(f"    {nm:<22}{a[g].mean():>11.4f}{b[g].mean():>11.4f}"
              f"{a[g].std():>10.4f}{b[g].std():>10.4f}{c:>8.4f}"
              f"{medad:>10.4f}{rms:>10.4f}", flush=True)
    # also: deep-ladder shape diff — mean RMS over the 50 offset + 50 ntl chans
    off_rms = float(np.sqrt(np.mean((Rs[:, :100] - Rp[:, :100]) ** 2)))
    print(f"    [ladder] RMS diff over 100 level channels "
          f"(off_bps + ntl_log) = {off_rms:.4f}", flush=True)


def validate(days: list):
    os.makedirs(OUT_DIR, exist_ok=True)
    n_total = len(list_days(SEQ_DIR))
    per_day_secs, per_day_mb = [], []
    gates = {1: True, 2: True, 3: True, 4: True, "4b": True}

    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        st = build_one_day(d, out, keep_book=True)     # force rebuild: honest timing
        per_day_secs.append(st["secs"])
        per_day_mb.append(st["mb"])
        ts, R16, book = st["ts"], st["R16"], st["book"]
        print(f"\n================ day {d}: T={st['T']} R25={R16.shape} "
              f"{st['mb']:.1f} MB  {st['secs']:.1f}s (PERP) ================",
              flush=True)

        # GATE 1: ts identity vs seq_cache
        with np.load(out) as z:
            ts_saved, R_saved = z["ts"].astype(np.int64), z["R25"]
        sts = _seq_ts(d)
        g1 = (np.array_equal(ts_saved, sts)
              and R_saved.shape == (sts.shape[0], N_CH)
              and R_saved.dtype == np.float16)
        gates[1] &= g1
        print(f"[GATE 1] ts==seq_cache ts: {np.array_equal(ts_saved, sts)}  "
              f"T={ts_saved.shape[0]} (85800 expected)  dtype={R_saved.dtype}  "
              f"{'PASS' if g1 else 'FAIL'}", flush=True)

        # GATE 2: all-finite fp16 + clip bounds
        print(f"[GATE 2] per-channel finite% + clip bounds "
              f"(no-book rows zero-filled: {st['n_nobook']}, "
              f"NaN rows zero-filled: {st['n_nan_rows']}, "
              f"max ffill gap: {st['max_ffill_gap_s']}s, "
              f"p99.9 gap: {st['p999_ffill_gap_s']:.1f}s)", flush=True)
        g2 = _gate2_finite_and_clips(R_saved)
        gates[2] &= g2
        print(f"[GATE 2] {'PASS' if g2 else 'FAIL'}", flush=True)

        # GATE 3: ladder monotonicity
        print("[GATE 3] ladder ordering (f64 source book)", flush=True)
        gates[3] &= _gate3_ladder(book, R_saved)

        # GATE 4: PERP deep_imb self-consistency (NOT vs spot btc25_state)
        print("[GATE 4] deep_imb self-consistency on the PERP ladder", flush=True)
        gates[4] &= _gate4_self_consistency(d, ts, R_saved, book)

        # GATE 4b: CALIBER — perp book mid vs bar perp mid_bnfbtc
        print("[GATE 4b] CALIBER: perp-book L1 mid vs bar_1s mid_bnfbtc",
              flush=True)
        gates["4b"] &= _gate4b_caliber(d, ts, book)

        # GATE 4c: old-spot vs new-perp feature diff magnitude (report)
        print("[GATE 4c] old-SPOT vs new-PERP feature diff (report only)",
              flush=True)
        _gate4c_spot_vs_perp_diff(d, ts, R_saved)

    s, mb = float(np.mean(per_day_secs)), float(np.mean(per_day_mb))
    print(f"\n[GATE 5] avg {s:.1f} s/day, {mb:.1f} MB/day; full build est "
          f"({n_total} days): {n_total*s/3600:.1f} h, "
          f"{n_total*mb/1000:.1f} GB", flush=True)
    print("\n[validate] " + "  ".join(
        f"GATE{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + "  GATE4c=report  GATE5=reported", flush=True)
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
