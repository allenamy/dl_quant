#!/usr/bin/env python3
"""m2_lib.py — Stage 2 "M2" (BTC-beta overlay) of docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md (commit 8530d2b7f,
sha256 1217d786b29cf8bc…). Library only (numpy; no I/O at import). Two pure pieces: the beta calculator and the target transformer.

FORMULA (prereg Stage 2, frozen, zero free parameters — reproduced here, NOT re-decided):
  at anchor A, for a PUBLISHED target w (gross units):
  1. beta_i = OLS slope of name i's 4h log return on BTCUSDT's 4h log return over the most recent 180 4h bars COMPLETED at A
     (the bar ending at A is completed at A: the decision reads the target at A + 24 min); >= 120 valid observations, otherwise
     beta_i = 1.0; clipped to [-1, 4]; BTCUSDT's own beta = 1. Price source: the certified price_full_raw_x0918r table; missing
     intervals are NOT counted (never zero-filled).
  2. beta_book = sum_i w_i * beta_i.
  3. BTCUSDT target weight += -beta_book; every other name's weight unchanged; the total gross changes (reported per anchor).
  4. HOLD anchors (nothing published) get no hedge.

OPERATIONAL READINGS OF THE FORMULA (written before any number; each is the literal reading, not a choice among alternatives):
  * "OLS slope" = the slope of the ordinary least-squares line WITH intercept (the textbook simple-regression slope
    sum (x - xbar)(y - ybar) / sum (x - xbar)^2 over the valid pairs). A zero denominator (BTC flat on every valid pair) raises.
  * "4h log return" of bar k = LP[T_k] - LP[T_{k-1}] on the certified 5-minute log-price grid (price = ref_px * exp(LP - cref), so
    differences of LP are log returns), T on the UTC 4h grid.
  * "valid observation" (pairwise: the name AND BTC must both be valid on that bar) for name j and bar (T_{k-1}, T_k]:
      - both endpoint prices exist in the certified FullPanel sense: T_{k-1} >= first_fin[j] (first_fin >= 0);
      - the name was not past its last finite bar: T_k <= last_fin[j];
      - no UNAVAILABLE 5-minute bar of j closes in the CLOSED interval [T_{k-1}, T_k] (the certified UA-FREEZE-EXCLUDE rule of
        bt_hist_sim31: "any UA bar closing in [A, A+4h], the endpoint bar included"; a UA bar at the start boundary makes the start
        price stale). Gap-FILLED bars are restored official returns (bt_prices_full_x0918r.py: log1p(gap_raw)) and count as observed.
    Invalid bars are excluded from the regression (never entered as zero returns).
  * "the most recent 180 4h bars" = the 180 bar SLOTS ending at A (calendar), of which the valid ones form the sample; bars before
    the start of the price grid do not exist and count as invalid.
  * Clipping is applied to the estimated slope; the fallback 1.0 is inside [-1, 4] anyway.
Everything that is not computable raises (unknown is not zero): an anchor off the 4h grid, an anchor past the price grid's last
4h boundary, a non-finite price at a valid bar, an empty series.
"""
import hashlib
import json

import numpy as np

H4 = 14400
ROW = 300
N_WIN = 180
N_MIN = 120
CLIP_LO, CLIP_HI = -1.0, 4.0
FALLBACK = 1.0
BTC = "BTCUSDT"


class M2Error(Exception):
    pass


def _fail(reason, **kw):
    raise M2Error(reason + ("" if not kw else " " + json.dumps(kw, default=str)[:400]))


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ───────────────────────── beta calculator ─────────────────────────
def bars_4h(LP, grid, first_fin, last_fin, ua_rows, ua_cols):
    """certified 5-minute log-price grid → 4h bars.
    LP: (n_grid, n_sym) array-like (memmap ok); grid: (n_grid,) int64 boundary times (5-minute step); first_fin / last_fin: (n_sym,);
    ua_rows / ua_cols: the UNAVAILABLE cells as grid-row / column pairs (the 5-minute bar CLOSING at grid[row]).
    Returns T (n_T,) 4h boundaries on the grid, R (n_T, n_sym) log return of the bar ENDING at T[k] (row 0 and invalid bars = NaN),
    V (n_T, n_sym) bool validity (row 0 False)."""
    grid = np.asarray(grid, np.int64)
    if grid.ndim != 1 or len(grid) < 2: _fail("grid_empty_or_not_1d", n=int(grid.size))
    if not np.all(np.diff(grid) == ROW): _fail("grid_not_5min_contiguous")
    n_sym = LP.shape[1]
    first_fin = np.asarray(first_fin, np.int64); last_fin = np.asarray(last_fin, np.int64)
    if len(first_fin) != n_sym or len(last_fin) != n_sym: _fail("fin_length", n_sym=n_sym)
    g0 = int(grid[0]); t0 = -(-g0 // H4) * H4
    T = np.arange(t0, int(grid[-1]) + 1, H4, dtype=np.int64)
    if len(T) < 2: _fail("fewer_than_two_4h_boundaries")
    rows = (T - g0) // ROW
    L4 = np.asarray(LP[rows, :], np.float64)
    nT = len(T)
    V = np.zeros((nT, n_sym), bool)
    st = T[:-1][:, None]; en = T[1:][:, None]
    V[1:] = (first_fin[None, :] >= 0) & (st >= first_fin[None, :]) & (en <= last_fin[None, :])
    ua_rows = np.asarray(ua_rows, np.int64); ua_cols = np.asarray(ua_cols, np.int64)
    if len(ua_rows) != len(ua_cols): _fail("ua_length_mismatch")
    if len(ua_rows):
        tc = g0 + ua_rows * ROW                               # close time of the UA 5-minute bar
        # bar k covers the CLOSED interval [T[k-1], T[k]]: a UA close at tc invalidates bar k with T[k-1] <= tc <= T[k]
        k_hi = -(-(tc - t0) // H4)                            # smallest k with T[k] >= tc
        on_b = (tc - t0) % H4 == 0                            # tc on a boundary ⇒ also the bar that STARTS there (k_hi + 1)
        for k, c, ob in zip(k_hi.tolist(), ua_cols.tolist(), on_b.tolist()):
            for kk in ((k, k + 1) if ob else (k,)):
                if 1 <= kk < nT: V[kk, c] = False
    R = np.full((nT, n_sym), np.nan)
    d = L4[1:] - L4[:-1]
    R[1:] = np.where(V[1:], d, np.nan)
    if not np.all(np.isfinite(R[V])): _fail("non_finite_return_at_a_valid_bar", n=int((~np.isfinite(R[V])).sum()))
    return T, R, V


def betas_at(T, R, V, anchors, btc_j):
    """beta_i per anchor (formula steps 1). anchors: int array on the 4h grid, each <= T[-1].
    Returns B (n_a, n_sym) float64 (clipped; fallback 1.0; BTC = 1.0), NOBS (n_a, n_sym) int32 valid pairs, EST (n_a, n_sym) bool
    (True = estimated, False = fallback), RAW (n_a, n_sym) unclipped slope (NaN where fallback)."""
    anchors = np.asarray(anchors, np.int64)
    if anchors.ndim != 1 or len(anchors) == 0: _fail("anchors_empty")
    if np.any(anchors % H4 != 0): _fail("anchor_off_4h_grid", n=int(np.sum(anchors % H4 != 0)))
    if int(anchors.max()) > int(T[-1]): _fail("anchor_after_last_price_boundary", last=int(T[-1]), got=int(anchors.max()))
    nA, nS = len(anchors), R.shape[1]
    B = np.full((nA, nS), FALLBACK); NOBS = np.zeros((nA, nS), np.int32); EST = np.zeros((nA, nS), bool); RAW = np.full((nA, nS), np.nan)
    t0 = int(T[0])
    for a_i, A in enumerate(anchors.tolist()):
        k = (A - t0) // H4                                    # index of the bar ending at A (negative ⇒ A before the price grid)
        if k < 1:
            B[a_i, btc_j] = 1.0; continue                     # no completed bar on the grid: every name falls back (formula), BTC = 1
        lo = max(1, k - N_WIN + 1)
        Rw = R[lo:k + 1]; Vw = V[lo:k + 1]
        vb = Vw[:, btc_j]
        M = Vw & vb[:, None]
        n = M.sum(0)
        NOBS[a_i] = n
        ok = n >= N_MIN
        ok[btc_j] = False
        if ok.any():
            x = np.where(vb, Rw[:, btc_j], 0.0)
            cols = np.nonzero(ok)[0]
            Mc = M[:, cols]; nc = n[cols].astype(np.float64)
            X = np.where(Mc, x[:, None], 0.0); Y = np.where(Mc, Rw[:, cols], 0.0)
            mx = X.sum(0) / nc; my = Y.sum(0) / nc
            dx = np.where(Mc, X - mx[None, :], 0.0); dy = np.where(Mc, Y - my[None, :], 0.0)
            sxx = (dx * dx).sum(0); sxy = (dx * dy).sum(0)
            if np.any(sxx <= 0): _fail("zero_btc_variance_on_valid_pairs", anchor=A, n_cols=int(np.sum(sxx <= 0)))
            b = sxy / sxx
            if not np.all(np.isfinite(b)): _fail("non_finite_slope", anchor=A)
            RAW[a_i, cols] = b
            B[a_i, cols] = np.clip(b, CLIP_LO, CLIP_HI); EST[a_i, cols] = True
        B[a_i, btc_j] = 1.0
    return B, NOBS, EST, RAW


# ───────────────────────── target transformer ─────────────────────────
def beta_book_rows(kind, off, idx, val, B):
    """beta_book per anchor = sum_i w_i beta_i over the row's entries (formula step 2); 0.0 on HOLD rows (kind 0, empty by format)"""
    n = len(kind)
    if B.shape[0] != n: _fail("beta_rows_vs_anchors", beta_rows=B.shape[0], anchors=n)
    bb = np.zeros(n)
    for r in range(n):
        a, b = int(off[r]), int(off[r + 1])
        if b > a:
            bb[r] = float(np.dot(val[a:b], B[r, idx[a:b]]))
    return bb


def transform(kind, off, idx, val, hedge, btc_j):
    """formula step 3/4 on one CSR reading. hedge (n,) = -beta_book per anchor; applied only where kind > 0 (published) —
    a HOLD row (kind 0) is copied unchanged whatever hedge says. BTC present in the row ⇒ its value += hedge (every other entry
    bitwise unchanged); absent and hedge != 0 ⇒ inserted at its sorted column position (rows are column-sorted; asserted);
    hedge == 0 ⇒ the row is copied unchanged (adding 0 creates no entry). Returns (kind, off, idx, val, stats)."""
    kind = np.asarray(kind); off = np.asarray(off, np.int64); idx = np.asarray(idx); val = np.asarray(val, np.float64)
    n = len(kind); hedge = np.asarray(hedge, np.float64)
    if len(hedge) != n: _fail("hedge_length", hedge=len(hedge), n=n)
    if len(off) != n + 1 or off[0] != 0 or off[-1] != len(idx) or len(idx) != len(val): _fail("csr_offsets")
    if not np.all(np.isfinite(hedge)): _fail("non_finite_hedge")
    o_idx, o_val, o_off = [], [], [0]
    st = {"rows": n, "hold_rows": 0, "hold_rows_with_nonzero_hedge_ignored": 0, "btc_added_to_existing": 0, "btc_inserted": 0,
          "zero_hedge_rows_copied": 0, "btc_weight_exactly_zero_after": 0}
    for r in range(n):
        a, b = int(off[r]), int(off[r + 1])
        ri = idx[a:b]; rv = val[a:b]
        if len(ri) > 1 and not np.all(np.diff(ri.astype(np.int64)) > 0): _fail("row_not_column_sorted", row=r)
        h = float(hedge[r])
        if int(kind[r]) == 0:
            st["hold_rows"] += 1
            if h != 0.0: st["hold_rows_with_nonzero_hedge_ignored"] += 1
            o_idx.append(ri); o_val.append(rv); o_off.append(o_off[-1] + len(ri)); continue
        if h == 0.0:
            st["zero_hedge_rows_copied"] += 1
            o_idx.append(ri); o_val.append(rv); o_off.append(o_off[-1] + len(ri)); continue
        pos = np.nonzero(ri == btc_j)[0]
        if len(pos):
            nv = rv.copy(); nv[pos[0]] = nv[pos[0]] + h
            if nv[pos[0]] == 0.0: st["btc_weight_exactly_zero_after"] += 1
            st["btc_added_to_existing"] += 1
            o_idx.append(ri); o_val.append(nv); o_off.append(o_off[-1] + len(ri))
        else:
            p = int(np.searchsorted(ri.astype(np.int64), btc_j))
            ni = np.concatenate([ri[:p], np.array([btc_j], dtype=idx.dtype), ri[p:]])
            nv = np.concatenate([rv[:p], np.array([h]), rv[p:]])
            st["btc_inserted"] += 1
            o_idx.append(ni); o_val.append(nv); o_off.append(o_off[-1] + len(ni))
    out_idx = np.concatenate(o_idx).astype(idx.dtype) if o_idx else np.zeros(0, idx.dtype)
    out_val = np.concatenate(o_val).astype(np.float64) if o_val else np.zeros(0)
    return np.asarray(kind).copy(), np.array(o_off, np.int64), out_idx, out_val, st


def row_l1(off, val):
    return np.array([float(np.abs(val[int(off[r]):int(off[r + 1])]).sum()) for r in range(len(off) - 1)])


def row_net(off, val):
    return np.array([float(val[int(off[r]):int(off[r + 1])].sum()) for r in range(len(off) - 1)])
