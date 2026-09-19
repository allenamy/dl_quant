#!/usr/bin/env python3
"""rp_lib.py — pure functions of the R5-02 raw 5m price restore (numpy only, no I/O). Imported by rp_restore.py, r_prices_raw.py and
tests/test_rp_counterexamples.py, so the regression test runs the same code the production device runs.

Cache conventions (read from the builders holefix2_build.py / holefix2_daily.py / build_raw_channel.py and verified bar by bar in
rp_restore.py control (b)):
  row ts = bar CLOSE time = kline open_time + 300 s;
  ret5[ts] = close(bar closing at ts) / close(bar closing at ts - 300) - 1, then np.clip(., -0.3, 0.3), then stored as float16
  (the bound value float16(0.3) = 0.300048828125); NaN when either close is missing;
  a 4h cell (E, E+4h] = the 48 rows with ts in (E, E+4h]; its compound return = close(E+4h) / close(E) - 1.

What the old device did (r_prices.py L143-150, sha 3614558d...): set every bound / NaN bar of a mismatching cell to the same log return so the
cell compounds to meta y4. That fixes the endpoint only. This module replaces it with:
  * apply_patch(): the exact official return on every bound bar (status RESTORED); a bound bar with no official value is REFUSED, never
    guessed; the patch may only touch bound bars (NaN bars stay 0, the same convention as the accounting meta y4).
  * feasible_band(): when official bars are missing, the exact range of the cumulative log price at every bar boundary inside the cell
    that is consistent with the clip side of each unknown bar and the known endpoint (bounds may be infinite; that is reported, not hidden).
  * extreme_paths(): the lowest / highest admissible path (each is itself a valid path), or None when that side is unbounded.
"""
import math

import numpy as np

BOUND16 = float(np.float16(0.3))                                   # 0.300048828125, the value a clipped bar holds
_BELOW16 = float(np.nextafter(np.float16(0.3), np.float16(0.0)))   # 0.2998046875, the next float16 toward zero
EDGE = 0.5 * (BOUND16 + _BELOW16)                                  # 0.2999267578125: |true r| >= EDGE is stored as the bound
LOG_UP_MIN = math.log1p(EDGE)                                      # a +bound bar has log(1+r) >= this
LOG_DN_MAX = math.log1p(-EDGE)                                     # a -bound bar has log(1+r) <= this

NONE, RESTORED, NOT_CLIPPED, UNAVAILABLE, CONFLICT = 0, 1, 2, 3, 4
STATUS_NAME = {NONE: "NONE", RESTORED: "RESTORED", NOT_CLIPPED: "NOT_CLIPPED", UNAVAILABLE: "UNAVAILABLE", CONFLICT: "CONFLICT"}


class UnavailablePath(Exception):
    """a bound bar has no exact official return: the price path through it is not identified, only bounded"""


class InfeasibleCell(Exception):
    """no path satisfies the clip sides and the endpoint: the inputs contradict each other"""


class PatchError(Exception):
    """the patch table does not fit the cache (entry off a bound bar, or a bound bar without an entry)"""


def is_bound(r16):
    r = np.asarray(r16, np.float64)
    return np.isfinite(r) & (np.abs(r) == BOUND16)


def builder_ret16(c_now, c_prev):
    """the cache builder's channel math for one bar: float16(clip(c_now / c_prev - 1, -0.3, 0.3))"""
    return np.float16(np.clip(np.float64(c_now) / np.float64(c_prev) - 1.0, -0.3, 0.3))


def classify(cache16, c_now, c_prev):
    """one bound cache bar against the official closes -> (status, exact raw return)"""
    if c_now is None or c_prev is None:
        return UNAVAILABLE, math.nan
    c_now = float(c_now); c_prev = float(c_prev)
    if not (math.isfinite(c_now) and math.isfinite(c_prev) and c_prev > 0 and c_now > 0):
        return UNAVAILABLE, math.nan
    raw = c_now / c_prev - 1.0
    if builder_ret16(c_now, c_prev) != np.float16(cache16):
        return CONFLICT, raw                                   # the official closes do not reproduce the cached value
    return (RESTORED if abs(raw) > 0.3 else NOT_CLIPPED), raw


def base_logs(r16):
    """the replay convention: log(1 + ret5), NaN bar => 0"""
    r = np.asarray(r16, np.float64)
    return np.log1p(np.where(np.isfinite(r), r, 0.0))


def apply_patch(L, r16, rows, cols, status, raw):
    """In place on L (float64 log returns, same shape as r16, = base_logs(r16) on entry).
    rows / cols / status / raw: the patch entries that fall inside this array (row, column indices into r16).
    Contract (each violation raises, nothing is guessed):
      (i)  every entry sits on a bound bar of r16 (the patch never touches an unclipped or a missing bar);
      (ii) every bound bar of r16 has exactly one entry (a bound bar with no entry is refused, not left clipped);
      (iii) every entry is RESTORED or NOT_CLIPPED; UNAVAILABLE / CONFLICT entries raise UnavailablePath (the caller may then use
           feasible_band / extreme_paths for a scenario, never a point path).
    RESTORED => L = log1p(exact official return); NOT_CLIPPED => the cache value is an ordinary float16 rounding, L unchanged.
    Returns the number of bars whose log return was replaced."""
    r = np.asarray(r16, np.float64)
    rows = np.asarray(rows, np.int64); cols = np.asarray(cols, np.int64); status = np.asarray(status, np.int64); raw = np.asarray(raw, np.float64)
    if r.ndim == 1:
        assert np.all(cols == 0), "1-D input takes cols == 0"
        r2 = r[:, None]; L2 = L.reshape(-1, 1)
    else:
        r2 = r; L2 = L
    bnd = is_bound(r2)
    if len(rows):
        if not bnd[rows, cols].all():
            raise PatchError("patch entries off a bound bar: %d" % int((~bnd[rows, cols]).sum()))
        key = rows * r2.shape[1] + cols
        if len(np.unique(key)) != len(key):
            raise PatchError("duplicate patch entries")
    covered = np.zeros_like(bnd)
    if len(rows):
        covered[rows, cols] = True
    miss = bnd & ~covered
    if miss.any():
        raise PatchError("bound bars without a patch entry: %d (first row %d col %d)" % (int(miss.sum()), *np.argwhere(miss)[0]))
    bad = ~np.isin(status, [RESTORED, NOT_CLIPPED])
    if bad.any():
        raise UnavailablePath([(int(a), int(b), STATUS_NAME.get(int(s), str(s))) for a, b, s in zip(rows[bad], cols[bad], status[bad])])
    use = status == RESTORED
    if use.any():
        if not np.all(np.isfinite(raw[use])) or np.any(raw[use] <= -1.0):
            raise PatchError("RESTORED entry with a non-finite or <= -100% return")
        s_cache = np.sign(r2[rows[use], cols[use]]); s_raw = np.sign(raw[use])
        if np.any(s_cache != s_raw) or np.any(np.abs(raw[use]) <= 0.3):
            raise PatchError("RESTORED entry inconsistent with the clip side")
        L2[rows[use], cols[use]] = np.log1p(raw[use])
    return int(use.sum())


def feasible_band(known, sign, total):
    """Bounded scenario for one cell with unknown bars.
    known: (n,) float64 log returns of the cell's bars with NaN at the unknown bars;
    sign:  (n,) +1 / -1 at the unknown bars (the clip side of the cache value), ignored elsewhere;
    total: log(1 + y4) of the cell endpoint, or NaN when no endpoint is known.
    Constraints: an unknown +bar has log(1+r) >= LOG_UP_MIN (no upper limit), an unknown -bar has log(1+r) <= LOG_DN_MAX (no lower limit
    beyond price > 0), and the bars sum to total. Returns (lo, hi): (n+1,) bounds of the cumulative log price at every boundary relative
    to the cell start; +-inf where the data do not bound it. Raises InfeasibleCell when no path satisfies the constraints."""
    known = np.asarray(known, np.float64); sign = np.asarray(sign, np.float64); n = len(known)
    unk = np.isnan(known)
    if np.any(unk & ~np.isin(sign, [1.0, -1.0])):
        raise ValueError("every unknown bar needs its clip side (+1 / -1)")
    a = np.where(unk, np.where(sign > 0, LOG_UP_MIN, -np.inf), 0.0)       # per-bar lower bound (unknown bars only; known bars are 0-width)
    b = np.where(unk, np.where(sign > 0, np.inf, LOG_DN_MAX), 0.0)        # per-bar upper bound
    K = np.concatenate([[0.0], np.cumsum(np.where(unk, 0.0, known))])
    Apre = np.concatenate([[0.0], np.cumsum(a)]); Bpre = np.concatenate([[0.0], np.cumsum(b)])
    Asuf = np.concatenate([np.cumsum(a[::-1])[::-1], [0.0]]); Bsuf = np.concatenate([np.cumsum(b[::-1])[::-1], [0.0]])
    if not math.isfinite(total):
        return K + Apre, K + Bpre
    S = total - K[-1]
    if not (Apre[-1] <= S <= Bpre[-1]):
        raise InfeasibleCell("endpoint %.6g outside the admissible sum [%.6g, %.6g]" % (S, Apre[-1], Bpre[-1]))
    lo = K + np.maximum(Apre, S - Bsuf)
    hi = K + np.minimum(Bpre, S - Asuf)
    return lo, hi


def extreme_paths(known, sign, total):
    """the lowest and the highest admissible cumulative paths (n+1,), each a valid path (its increments satisfy every bar constraint),
    or None for a side that is unbounded. Returned as (lo_path, hi_path)."""
    lo, hi = feasible_band(known, sign, total)
    known = np.asarray(known, np.float64); sign = np.asarray(sign, np.float64); unk = np.isnan(known)
    out = []
    for p in (lo, hi):
        if not np.all(np.isfinite(p)):
            out.append(None); continue
        d = np.diff(p)
        ok_known = np.allclose(d[~unk], known[~unk], rtol=0, atol=1e-12)
        ok_up = np.all(d[unk & (sign > 0)] >= LOG_UP_MIN - 1e-12); ok_dn = np.all(d[unk & (sign < 0)] <= LOG_DN_MAX + 1e-12)
        assert ok_known and ok_up and ok_dn, "envelope is not a valid path"
        out.append(p)
    return out[0], out[1]
