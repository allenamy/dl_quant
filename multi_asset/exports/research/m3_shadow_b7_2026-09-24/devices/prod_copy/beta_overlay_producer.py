"""beta_overlay_producer — M3 per-name BTC betas for target_live's `beta_overlay` field (the executor's overlay leg reads it).

Pre-registration: quant_research docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md (24c3f803f) §2 step 2 and §5
("生产者算 β_i 向量写进 target_live 的新字段"). The executor side is dl_quant_live live/beta_overlay.py (version VERSION;
it refuses any other version, any other declared parameter, a cut-off other than the file's anchor, and a fallback
inconsistency).

THE FORMULA (identical to M2's m2_lib.betas_at; reproduced, not re-decided)
    beta_i = OLS slope WITH intercept of name i's 4h log returns on BTCUSDT's 4h log returns over the most recent N_WIN = 180
             4h bars COMPLETED at the anchor A (the bar ending at A is completed at A); pairwise-valid bars only; >= N_MIN = 120
             valid pairs, else FALLBACK = 1.0; clipped to [-1, 4]; BTCUSDT's own beta = 1. A zero BTC variance raises.
THE DATA — the producer's own rolling cache (state/rolling.npz, the same generation combo_stage scores), and its NAMED
DIFFERENCES from M2's certified price table (price_full_raw_x0918r):
    * 4h log return of bar (T-4h, T] = sum of log1p(ret5) over the 48 rows whose 5-minute bar CLOSES in (T-4h, T]
      (rts are close times: shadow_loop_v3 writes row `close_s = open + 300 s`); ret5 = close/prev_close - 1, so the sum is
      log(P_T / P_{T-4h}) exactly, up to the two cache properties below.
    * a bar is VALID iff all 49 rows closing in the CLOSED interval [T-4h, T] are finite — the row closing AT the start
      boundary included: when that row is missing, the next row's ret5 was computed from a stale prev_close and spans the gap
      (the M2 / bt_hist_sim31 UA-FREEZE-EXCLUDE rule, same closed interval). Missing rows are never zero-filled.
    * ret5 is CLIPPED to +-0.30 per 5 minutes (shadow_loop_v3 CHN_CLIPS) and stored as float16 (relative rounding ~5e-4 per
      row). Neither exists in the certified table. A 5-minute move beyond 30% is the only way the clip binds.
    * bars that start before the cache's first row do not exist and are invalid (the cache holds 40 days; 180 bars = 30 days).
    * a name with no cache column has 0 valid pairs ⇒ FALLBACK (the formula's rule, not a special case).
CAUSALITY: only rows with close time <= A are read (the slice ends at A's row); `tests_beta_overlay_producer` perturbs every
later row and requires bitwise-identical betas, and perturbs the row closing AT A and requires a change.
Pure: numpy only, no file, no network, no clock.
"""
from __future__ import annotations

import math

import numpy as np

VERSION = "m3_beta_v1"
BTC = "BTCUSDT"
N_WIN = 180
N_MIN = 120
CLIP_LO, CLIP_HI = -1.0, 4.0
FALLBACK = 1.0
H4 = 14400
ROW = 300
ROWS_PER_BAR = H4 // ROW          # 48


class BetaOverlayError(Exception):
    pass


def _fail(msg):
    raise BetaOverlayError(msg)


def compute(rts, ret5, symbols, names, anchor_ts):
    """The `beta_overlay` field for anchor `anchor_ts`.

    rts: (n,) integer close times of the 5-minute rows, contiguous (step 300 s), containing anchor_ts;
    ret5: (n, n_sym) array-like of simple 5-minute returns (float16 ok; NaN = missing row), column order = `symbols`;
    names: the names to write betas for (the producer's universe list, in its order); BTCUSDT is always written.
    Raises BetaOverlayError on anything it cannot compute (never a default)."""
    rts = np.asarray(rts)
    if rts.ndim != 1 or len(rts) < 2 or not np.issubdtype(rts.dtype, np.integer):
        _fail("rts must be a 1-d integer axis")
    rts = rts.astype(np.int64)
    if not np.all(np.diff(rts) == ROW):
        _fail("rts not 5-minute contiguous")
    A = int(anchor_ts)
    if A % H4 != 0:
        _fail(f"anchor {A} not on the 4h grid")
    hit = np.nonzero(rts == A)[0]
    if len(hit) != 1:
        _fail(f"anchor {A} not in the cache axis exactly once")
    ai = int(hit[0])
    symbols = [str(s) for s in symbols]
    if len(set(symbols)) != len(symbols):
        _fail("duplicate symbols")
    if getattr(ret5, "ndim", None) != 2 or ret5.shape[0] != len(rts) or ret5.shape[1] != len(symbols):
        _fail(f"ret5 shape {getattr(ret5, 'shape', None)} != ({len(rts)}, {len(symbols)})")
    col = {s: j for j, s in enumerate(symbols)}
    if BTC not in col:
        _fail("BTCUSDT has no cache column")
    names = [str(n) for n in names]
    if len(set(names)) != len(names):
        _fail("duplicate names")
    want = list(dict.fromkeys([BTC] + names))            # BTC first, then the universe order, unique
    have = [n for n in want if n in col]
    need_rows = N_WIN * ROWS_PER_BAR + 1                  # 8641: the start-boundary row of the first bar + 180 x 48
    lo = ai - (need_rows - 1)
    # ── the causal slice: rows [lo, ai] — nothing after A is ever read ──
    cols = [col[n] for n in have]
    if lo >= 0:
        R = np.asarray(ret5[lo:ai + 1][:, cols], dtype=np.float64)
    else:                                                 # bars before the cache's first row do not exist
        R = np.full((need_rows, len(cols)), np.nan)
        R[-lo:] = np.asarray(ret5[0:ai + 1][:, cols], dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        L = np.log1p(R)
    fin = np.isfinite(L)
    body = L[1:].reshape(N_WIN, ROWS_PER_BAR, len(cols))
    body_ok = fin[1:].reshape(N_WIN, ROWS_PER_BAR, len(cols)).all(axis=1)
    start_ok = fin[0:N_WIN * ROWS_PER_BAR:ROWS_PER_BAR]  # the row closing AT each bar's start boundary
    V = body_ok & start_ok                                # (180, m)
    R4 = np.where(V, np.where(fin[1:].reshape(N_WIN, ROWS_PER_BAR, len(cols)), body, 0.0).sum(axis=1), np.nan)
    jb = have.index(BTC)
    vb = V[:, jb]
    x_all = R4[:, jb]
    betas, nobs = {}, {}
    n_est = n_fb = 0
    for k, n in enumerate(have):
        if n == BTC:
            betas[n] = 1.0
            nobs[n] = int(vb.sum())
            continue
        m = V[:, k] & vb
        cnt = int(m.sum())
        nobs[n] = cnt
        if cnt < N_MIN:
            betas[n] = FALLBACK
            n_fb += 1
            continue
        x = x_all[m]
        y = R4[m, k]
        dx = x - x.mean()
        dy = y - y.mean()
        sxx = float((dx * dx).sum())
        if not (sxx > 0.0):
            _fail(f"zero BTC variance on {n}'s {cnt} valid pairs")
        b = float((dx * dy).sum()) / sxx
        if not math.isfinite(b):
            _fail(f"non-finite slope for {n}")
        betas[n] = float(min(max(b, CLIP_LO), CLIP_HI))
        n_est += 1
    for n in want:
        if n not in col:                                  # no cache column ⇒ 0 valid pairs ⇒ the formula's fallback
            betas[n] = FALLBACK
            nobs[n] = 0
            n_fb += 1
    return {
        "version": VERSION, "anchor_ts": A, "data_cutoff_ts": A,
        "first_bar_end_ts": A - (N_WIN - 1) * H4,
        "n_win": N_WIN, "n_min": N_MIN, "clip": [CLIP_LO, CLIP_HI], "fallback": FALLBACK, "btc": BTC,
        "betas": {n: betas[n] for n in want}, "n_obs": {n: nobs[n] for n in want},
        "n_names": len(want), "n_estimated": n_est, "n_fallback": n_fb,
        "n_no_cache_column": len(want) - len(have),
        "method": ("OLS slope with intercept of 4h log returns (sum of log1p(ret5) over the 48 rows closing in (T-4h,T]; a "
                   "bar is valid iff the 49 rows closing in [T-4h,T] are finite) on BTCUSDT's, pairwise-valid bars only; "
                   ">=120 pairs else 1.0; clip [-1,4]; BTCUSDT = 1"),
        "source": "producer rolling cache state/rolling.npz channel ret5 (simple 5m return, clipped +-0.30, float16)",
        "prereg": "quant_research docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md (24c3f803f) §2 step 2",
    }
