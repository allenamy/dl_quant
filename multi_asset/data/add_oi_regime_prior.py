"""OVERLAY: build a SEPARATE OI-augmented npz cache, extending each day's
``regime_prior`` (N,6) -> (N,14) with 8 DESIGNED, LEAK-SAFE OI/funding
positioning-regime descriptors. Writes to a SEPARATE ``--dst`` cache for a
``--start``..``--end`` date range; the source cache is NEVER modified.

Why
---
The model's regime-conditioning path (regime FiLM + regime_bias_head + ppnet /
multistage FiLM gates) currently sees only the 6 vol-flavoured descriptors in
``regime_prior``. This overlay appends 8 carefully-DESIGNED OI/funding
descriptors so positioning REGIME (open-interest flow, crowding, funding x OI
squeeze, taker/toptrader extremes) can modulate the predictions — the decisive
DL test the linear Ridge gate cannot settle. The plumbing already threads
``regime_prior`` dataset->model, so this reuses it (no new dataset tuple
element); the only model change is making the regime FiLM ALSO consume
``regime_prior`` (see ``multi_asset/model/dual_lob_regarch.py::use_oi_regime``).

DISK-SAFE SEPARATE CACHE (the IN-PLACE rewrite was REMOVED)
----------------------------------------------------------
A prior in-place edit contaminated the shared caches. This script now ONLY
writes a NEW cache (``--dst``), reading from ``--src`` mode="r" and never
touching it. It builds only the days in ``[--start, --end]`` (the fold's needed
range) so the two folds can run SEQUENTIALLY (build strong -> run -> delete ->
build choppy -> run -> delete), never holding both ~70G caches at once.

The 8 descriptors (reusing the VERIFIED math in
``multi_asset/data/oi_designed_ridge_gate.py::designed``)
------------------------------------------------------------------------------
  0. oi_flow_norm   dOI/OI over last 6 bars            (positioning flow)
  1. oi_zscore      72-bar z-score of OI               (crowding / OI extreme)
  2. oi_accel       2nd diff of OI, /|OI|              (flow acceleration)
  3. quad_sign      sign(dOI)*sign(dP)                 (4-quadrant divergence core)
  4. divergence     dOI_n * dP_n                       (signed divergence magnitude)
  5. fund_x_oi      funding_z * oi_z                   (squeeze risk / reversal)
  6. toptrader_ext  toptrader_ls - 1                   (smart-money crowding)
  7. taker_ls       taker_long_short_ratio            (aggressive flow)

Leak-safety (IDENTICAL to the verified Ridge gate)
--------------------------------------------------
For a window ending at timestamp ``t`` (MICROSECONDS):
  * 5m METRICS bars: index ``im = searchsorted(MT, t - 300s, 'right') - 1`` ->
    only bars whose ``create_time <= t - 300s`` (i.e. create_time + 300s <= t,
    the bar fully CLOSED before t) are used. Strictly causal.
  * 8h FUNDING settles: index ``iff = searchsorted(FT, t, 'right') - 1`` -> only
    settles with ``fundingTime <= t`` (already settled). Strictly causal.
Windows with no closed bar/settle (``im<0`` or ``iff<0``, e.g. pre-2023-02
metrics start) get an all-zero descriptor row (finite, no leakage).

Each descriptor is clipped to [-8, 8] and nan_to_num'd. NO batch z-scoring here
(the FiLM MLP handles scale, exactly as the rich extractor does in-model).

Output day
----------
For every src npz in [start,end] it loads ALL keys, REPLACES ``regime_prior``
with the (N,14) array, ADDS ``regime_prior_names`` (the 14 names), and writes a
NEW npz under ``data/<dst>/<day>.npz`` with EVERY other key byte-preserved
(``y_600``/``timestamps``/``X``/``X_raw``/``X_raw_perp_deep``/``X_long``/... ).
Idempotent: a dst day whose ``regime_prior`` is already width >=14 is skipped.
Atomic: writes ``<day>.npz.tmp`` then ``os.replace`` (no half-written npz). A
per-file check asserts y_600 and timestamps are BYTE-identical src->dst (only
regime_prior changes).

Run (LOCAL has no npz; this runs ON THE SERVER after sync). DRY-RUN inspects
the first ``--n-test`` days without writing; pass ``--apply`` to write:
  CUDA_VISIBLE_DEVICES="" PYTHONPATH=. python multi_asset/data/add_oi_regime_prior.py \
      --src npzv4_dual --dst npzv4_dual_oi --start 2023-02-15 --end 2025-05-12 --apply
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")

MET = "data/funding/btcusdt_metrics_5m.csv"
FUND = "data/funding/btcusdt_funding.csv"
BAR_US = 300 * 1_000_000  # one 5m metrics bar, in microseconds

# The 6 existing (vol-flavoured) prior columns are kept as-is in positions 0..5;
# these 8 names label the appended OI/funding descriptors (positions 6..13).
BASE_PRIOR_NAMES = [
    "vol_short", "vol_mid", "vol_long", "vol_accel", "obi_mean", "obi_ac",
]
OI_NAMES = [
    "oi_flow_norm", "oi_zscore", "oi_accel", "quad_sign",
    "divergence", "fund_x_oi", "toptrader_ext", "taker_ls",
]
PRIOR_NAMES_14 = BASE_PRIOR_NAMES + OI_NAMES
K_OI = len(OI_NAMES)  # 8
TARGET_WIDTH = 14


# --------------------------------------------------------------------------- #
# metrics / funding loaders (verbatim caliber from oi_designed_ridge_gate.py)  #
# --------------------------------------------------------------------------- #
def parse_us(s: str) -> int:
    """metrics create_time 'YYYY-MM-DD HH:MM:SS' (UTC) -> microseconds."""
    return int(
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    ) * 1_000_000


def load_metrics() -> np.ndarray:
    rows = []
    with open(MET) as f:
        for r in csv.DictReader(f):
            try:
                rows.append((
                    parse_us(r["create_time"]),
                    float(r["sum_open_interest"]),
                    float(r["sum_open_interest_value"]),
                    float(r["sum_toptrader_long_short_ratio"]),
                    float(r["sum_taker_long_short_vol_ratio"]),
                    float(r["count_long_short_ratio"]),
                ))
            except Exception:
                continue
    a = np.array(rows)
    a = a[np.argsort(a[:, 0])]
    return a  # cols: t, oi, oiv, tt, tk, rt


def load_funding() -> np.ndarray:
    rows = []
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try:
                rows.append((int(r["fundingTime_ms"]) * 1000, float(r["fundingRate"])))
            except Exception:
                continue
    a = np.array(rows)
    return a[np.argsort(a[:, 0])]


# Module-level metrics/funding tables (loaded once).
_M = load_metrics()
_F = load_funding()
MT, OI, OIV, TT, TK, RT = _M[:, 0], _M[:, 1], _M[:, 2], _M[:, 3], _M[:, 4], _M[:, 5]
PRICE = OIV / np.clip(OI, 1e-9, None)  # implied perp price (no window price needed)
FT, FR = _F[:, 0], _F[:, 1]


def oi_descriptors(win_ts_us: np.ndarray) -> np.ndarray:
    """Compute the (N,8) leak-safe OI/funding descriptors for window-end ts.

    ``win_ts_us`` : (N,) int64 microsecond timestamps (window END = label time t).
    Returns (N,8) float32. Rows whose newest CLOSED bar/settle does not exist
    (im<0 or iff<0) stay all-zero. Mirrors ``oi_designed_ridge_gate.designed``
    leak-safety exactly (bar fully closed <= t-300s; funding settled <= t).
    """
    win_ts_us = np.asarray(win_ts_us, dtype=np.int64)
    N = len(win_ts_us)
    out = np.zeros((N, K_OI), dtype=np.float64)

    cut = win_ts_us - BAR_US                                   # t - 300s
    im = np.searchsorted(MT, cut, side="right") - 1           # newest closed bar
    iff = np.searchsorted(FT, win_ts_us, side="right") - 1    # newest settle <= t
    valid = (im >= 0) & (iff >= 0)
    if not np.any(valid):
        return out.astype(np.float32)
    iv = im[valid]
    ifv = iff[valid]

    K = 6  # lookback bars for OI flow / price change
    iK = np.clip(iv - K, 0, None)
    dOI = OI[iv] - OI[iK]
    dP = PRICE[iv] - PRICE[iK]
    dOIn = dOI / (np.abs(OI[iv]) + 1e-9)
    dPn = dP / (np.abs(PRICE[iv]) + 1e-9)

    # OI 72-bar z-score (crowding) — past-only window per index.
    oiz = np.zeros(len(iv))
    for j, i in enumerate(iv):
        lo = max(0, i - 71)
        h = OI[lo:i + 1]
        oiz[j] = (OI[i] - h.mean()) / (h.std() + 1e-9)
    # funding 30-settle z-score — past-only window per index.
    fz = np.zeros(len(ifv))
    for j, i in enumerate(ifv):
        lo = max(0, i - 29)
        h = FR[lo:i + 1]
        fz[j] = (FR[i] - h.mean()) / (h.std() + 1e-9)

    oi_accel = (OI[iv] - OI[iK]) - (OI[iK] - OI[np.clip(iv - 2 * K, 0, None)])

    out[valid, 0] = dOIn                       # oi_flow_norm
    out[valid, 1] = oiz                        # oi_zscore
    out[valid, 2] = oi_accel / (np.abs(OI[iv]) + 1e-9)   # oi_accel (normalized)
    out[valid, 3] = np.sign(dOI) * np.sign(dP)  # quad_sign
    out[valid, 4] = dOIn * dPn                  # divergence
    out[valid, 5] = fz * oiz                    # fund_x_oi
    out[valid, 6] = TT[iv] - 1.0                # toptrader_ext
    out[valid, 7] = TK[iv]                      # taker_ls

    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    out = np.clip(out, -8.0, 8.0)
    return out.astype(np.float32)


# --------------------------------------------------------------------------- #
# per-file overlay (src -> dst, src never modified)                           #
# --------------------------------------------------------------------------- #
def process_file(src_path: str, dst_path: str, apply: bool,
                 verbose: bool = False) -> str:
    """Build one OI-augmented day. Returns 'skip' / 'ok' / 'would'.

    Reads ``src_path`` mode="r" (NEVER writes it). Writes ``dst_path`` atomically
    (.tmp + os.replace) only when ``apply`` and the dst is not already width>=14.
    """
    # idempotency: if a complete dst already has width>=14, skip (don't rebuild).
    if apply and os.path.exists(dst_path):
        try:
            with np.load(dst_path, allow_pickle=True) as dchk:
                rpd = dchk["regime_prior"]
                if rpd.ndim == 2 and rpd.shape[1] >= TARGET_WIDTH:
                    if verbose:
                        print(f"  SKIP {os.path.basename(dst_path)}: dst already "
                              f"regime_prior={rpd.shape}")
                    return "skip"
        except Exception:
            pass  # corrupt/partial dst -> rebuild below

    d = np.load(src_path, allow_pickle=True)
    keys = set(d.files)
    if "regime_prior" not in keys or "timestamps" not in keys:
        if verbose:
            print(f"  SKIP {os.path.basename(src_path)}: missing "
                  f"regime_prior/timestamps")
        d.close()
        return "skip"

    rp = d["regime_prior"]
    if rp.ndim != 2 or rp.shape[1] >= TARGET_WIDTH:
        if verbose:
            print(f"  SKIP {os.path.basename(src_path)}: src regime_prior "
                  f"shape={rp.shape} (need width 6 -> 14)")
        d.close()
        return "skip"
    if rp.shape[1] + K_OI != TARGET_WIDTH:
        d.close()
        raise AssertionError(
            f"{src_path}: src regime_prior width {rp.shape[1]} + {K_OI} != "
            f"{TARGET_WIDTH}. Expected a 6-wide base (caches were reverted to 6). "
            f"Refusing to build a mis-sized prior.")

    ts = d["timestamps"].astype(np.int64)
    oi = oi_descriptors(ts)                          # (N,8)
    assert oi.shape == (rp.shape[0], K_OI), (oi.shape, rp.shape)
    new_rp = np.concatenate([rp.astype(np.float32), oi], axis=1)  # (N,14)
    assert new_rp.shape == (rp.shape[0], TARGET_WIDTH)

    if verbose:
        cov = float(np.mean(np.any(oi != 0, axis=1)))
        finite = bool(np.all(np.isfinite(new_rp)))
        print(f"  {os.path.basename(src_path)}: N={rp.shape[0]} "
              f"prior {rp.shape}->{new_rp.shape} oi-cov={cov:.3f} finite={finite}")
        print(f"     base[0]={rp[0]}")
        print(f"     oi[0]  ={oi[0]}")
        if oi.shape[0] > 1:
            print(f"     oi[-1] ={oi[-1]}")

    if not apply:
        d.close()
        return "would"

    # ---- assemble ALL keys, replace regime_prior, add names; preserve rest ----
    save_kwargs = {}
    for k in d.files:
        if k == "regime_prior":
            continue
        save_kwargs[k] = d[k]
    save_kwargs["regime_prior"] = new_rp
    save_kwargs["regime_prior_names"] = np.array(PRIOR_NAMES_14, dtype=object)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    tmp = dst_path + ".tmp.npz"
    if os.path.exists(tmp):
        os.remove(tmp)
    np.savez(tmp, **save_kwargs)
    # ---- verify the tmp before replacing: y_600 + timestamps byte-identical ---
    chk = np.load(tmp, allow_pickle=True)
    for byte_key in ("y_600", "timestamps"):
        if byte_key in keys:
            a, b = d[byte_key], chk[byte_key]
            if not (a.shape == b.shape and np.array_equal(a, b)):
                chk.close()
                os.remove(tmp)
                d.close()
                raise AssertionError(
                    f"{src_path}: {byte_key} changed by overlay! "
                    f"shapes {a.shape} vs {b.shape}")
    if chk["regime_prior"].shape[1] != TARGET_WIDTH:
        chk.close()
        os.remove(tmp)
        d.close()
        raise AssertionError(f"{dst_path}: tmp regime_prior not width {TARGET_WIDTH}")
    # also confirm every src key survived (no dropped arrays)
    missing = keys - set(chk.files)
    if missing:
        chk.close()
        os.remove(tmp)
        d.close()
        raise AssertionError(f"{dst_path}: dropped keys {missing}")
    chk.close()
    d.close()
    os.replace(tmp, dst_path)  # atomic: .tmp -> final
    return "ok"


def _day_in_range(day: str, start: str, end: str) -> bool:
    return (start is None or day >= start) and (end is None or day <= end)


def run(src: str, dst: str, start: str, end: str, apply: bool, n_test: int) -> None:
    src_dir = f"data/{src}"
    dst_dir = f"data/{dst}"
    print(f"[add_oi_regime_prior] metrics={len(MT)} "
          f"({datetime.utcfromtimestamp(MT[0]/1e6)}.."
          f"{datetime.utcfromtimestamp(MT[-1]/1e6)}) funding={len(FT)}")
    print(f"[add_oi_regime_prior] mode={'APPLY' if apply else 'DRY-RUN'} "
          f"src={src_dir} dst={dst_dir} range=[{start}..{end}] prior 6->14")
    print(f"[add_oi_regime_prior] OI names={OI_NAMES}")

    src_files = sorted(glob.glob(f"{src_dir}/*.npz"))
    if not src_files:
        sys.exit(f"  no src npz under {src_dir} (wrong cwd? expected repo root)")

    sel = [f for f in src_files
           if _day_in_range(os.path.basename(f)[:-4], start, end)]
    print(f"  src has {len(src_files)} npz; {len(sel)} in range [{start}..{end}]")
    if not sel:
        sys.exit("  no src days in the requested range")

    if not apply:
        sample = sel[: n_test]
        for f in sample:
            day = os.path.basename(f)
            process_file(f, os.path.join(dst_dir, day), apply=False, verbose=True)
        print(f"  (dry-run inspected {len(sample)} files; "
              f"pass --apply to build all {len(sel)} -> {dst_dir})")
        return

    counts = {"ok": 0, "skip": 0}
    for idx, f in enumerate(sel):
        day = os.path.basename(f)
        st = process_file(f, os.path.join(dst_dir, day), apply=True,
                          verbose=(idx < n_test))
        counts[st] = counts.get(st, 0) + 1
        if (idx + 1) % 50 == 0:
            print(f"  ...{idx + 1}/{len(sel)} (ok={counts['ok']} "
                  f"skip={counts['skip']})")
    print(f"  DONE {dst_dir}: built={counts['ok']} skipped={counts['skip']} "
          f"total={len(sel)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Build a SEPARATE OI-augmented npz cache (src never modified).")
    ap.add_argument("--src", required=True,
                    help="source cache name under data/ (e.g. npzv4_dual)")
    ap.add_argument("--dst", required=True,
                    help="destination cache name under data/ (e.g. npzv4_dual_oi)")
    ap.add_argument("--start", default=None, help="first day YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", default=None, help="last day YYYY-MM-DD (inclusive)")
    ap.add_argument("--apply", action="store_true",
                    help="write the dst cache (default: dry-run on --n-test days)")
    ap.add_argument("--n-test", type=int, default=3,
                    help="number of files to inspect verbosely")
    args = ap.parse_args()
    if args.src == args.dst:
        sys.exit("--src and --dst must differ (this builds a SEPARATE cache)")
    if not os.path.exists(MET):
        sys.exit(f"metrics CSV not found: {MET} (run from repo root)")
    run(src=args.src, dst=args.dst, start=args.start, end=args.end,
        apply=args.apply, n_test=args.n_test)
