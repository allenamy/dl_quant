#!/usr/bin/env python3
"""tradability.py — tradability defined by actual trades (FIXPROGRAM 2026-09-13 TRD-01; FX-DATA).

Definition frozen in docs/fixprogram_2026-09-13/FX_DATA/SPEC_TRADABILITY_2026-09-13.md (sha256 SPEC_SHA256 below, commit 73b59ec0):
  bar state (s, t), t = bar close time      TRADED ⇔ log_cnt finite and > 0 · UNTRADED ⇔ log_cnt == 0 · NODATA ⇔ log_cnt NaN
  decision state at time A, window W        TRADABLE ⇔ ≥ 1 TRADED bar with close in (A − W, A] · UNTRADED ⇔ none TRADED, ≥ 1 UNTRADED · NODATA otherwise
  eligible ⇔ TRADABLE                        W24H (86400 s) is primary; W4H (14400 s) is a sensitivity that never sets a label
  a decision time after the last loaded bar raises (no carry-forward); a window starting before the first bar is flagged truncated
  a funding record at ft is payable ⇔ the decision state at ft is TRADABLE
  descriptive only (uses the future): dead_after(t) ⇔ t > last TRADED bar and that bar is more than 24 h before the data end

There is no default window anywhere: every entry point takes `window=` as a required keyword ("W24H" or "W4H").
Pure functions (bar_states / window_states / rolling_tradable) work on arrays in memory and are what the pod2 builder and the tests call.
`Artifact.load(path, expected_sha256=...)` reads the canonical built artifact and refuses a sha mismatch, a spec mismatch, or an evicted file.
"""
import hashlib, os
import numpy as np

SPEC_SHA256 = "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"
BAR_S = 300
WINDOWS = {"W24H": 86400, "W4H": 14400}
PRIMARY = "W24H"
NODATA, UNTRADED, TRADED = 0, 1, 2            # bar states
TRADABLE = 2                                  # decision state codes reuse the bar codes: 0 NODATA / 1 UNTRADED / 2 TRADABLE
LOG1P_ONE = float(np.log1p(1.0))
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TradabilityError(ValueError):
    """an input the definition refuses to evaluate"""


def _window_s(window):
    if window not in WINDOWS:
        raise TradabilityError("window must be one of %s (no default), got %r" % (sorted(WINDOWS), window))
    return WINDOWS[window]


def bar_states(log_cnt):
    """log_cnt [T, N] (log1p trade count; float16/32/64) -> int8 [T, N] of NODATA / UNTRADED / TRADED.
    Refuses negative values and values strictly between 0 and log1p(1) (a fractional trade count cannot be a kline count)."""
    x = np.asarray(log_cnt)
    if x.dtype.kind != "f":
        raise TradabilityError("log_cnt must be floating point, got %s" % x.dtype)
    fin = np.isfinite(x)
    xf = np.where(fin, x, 0).astype(np.float64)
    if (xf < 0).any():
        raise TradabilityError("log_cnt has negative values (%d cells)" % int((xf < 0).sum()))
    frac = (xf > 0) & (xf < LOG1P_ONE * 0.995)          # float16 rounds log1p(1)=0.693147 to 0.69287 at worst; 0.995 keeps that and rejects anything below
    if frac.any():
        raise TradabilityError("log_cnt has %d cells strictly between 0 and log1p(1): not a trade count" % int(frac.sum()))
    out = np.full(x.shape, NODATA, np.int8)
    out[fin & (xf == 0)] = UNTRADED
    out[fin & (xf > 0)] = TRADED
    return out


def _check_ts(ts5):
    t = np.asarray(ts5)
    if t.ndim != 1 or t.dtype.kind not in "iu":
        raise TradabilityError("ts5 must be a 1-d integer array of bar close times (s)")
    if len(t) == 0:
        raise TradabilityError("ts5 is empty")
    if len(t) > 1 and not (np.diff(t) > 0).all():
        raise TradabilityError("ts5 must be strictly increasing")
    return t.astype(np.int64)


def window_states(ts5, states, decision_ts, *, window, sym_chunk=64):
    """Decision state at each time in decision_ts for every column of `states` ([T, N] int8 from bar_states).
    Returns (state int8 [K, N], truncated bool [K]). Raises if any decision time is after ts5[-1]."""
    t = _check_ts(ts5); w = _window_s(window)
    S = np.asarray(states)
    if S.ndim != 2 or S.shape[0] != len(t):
        raise TradabilityError("states must be [len(ts5), N]")
    A = np.asarray(decision_ts, dtype=np.int64).ravel()
    if len(A) and A.max() > t[-1]:
        raise TradabilityError("decision time %d is after the last loaded bar %d: refusing to carry forward" % (int(A.max()), int(t[-1])))
    hi = np.searchsorted(t, A, side="right")            # rows with close <= A
    lo = np.searchsorted(t, A - w, side="right")        # rows with close <= A - W are excluded
    truncated = (A - w) < (t[0] - BAR_S)
    K, N = len(A), S.shape[1]
    out = np.zeros((K, N), np.int8)
    for c0 in range(0, N, sym_chunk):
        c1 = min(N, c0 + sym_chunk)
        blk = S[:, c0:c1]
        ctr = np.zeros((len(t) + 1, c1 - c0), np.int32); np.cumsum(blk == TRADED, axis=0, dtype=np.int32, out=ctr[1:])
        n_tr = ctr[hi] - ctr[lo]; del ctr
        cun = np.zeros((len(t) + 1, c1 - c0), np.int32); np.cumsum(blk == UNTRADED, axis=0, dtype=np.int32, out=cun[1:])
        n_un = cun[hi] - cun[lo]; del cun
        o = np.full((K, c1 - c0), NODATA, np.int8); o[n_un > 0] = UNTRADED; o[n_tr > 0] = TRADABLE
        out[:, c0:c1] = o
    return out, truncated


def rolling_tradable(ts5, states, *, window):
    """5m granularity: bool [T, N], True ⇔ ≥ 1 TRADED bar with close in (ts5[r] − W, ts5[r]] (SPEC §3). Same window rule as window_states."""
    t = _check_ts(ts5); w = _window_s(window)
    S = np.asarray(states)
    lo = np.searchsorted(t, t - w, side="right"); hi = np.arange(1, len(t) + 1)
    out = np.zeros(S.shape, bool)
    for j in range(S.shape[1]):
        c = np.concatenate([[0], np.cumsum(S[:, j] == TRADED, dtype=np.int32)])
        out[:, j] = (c[hi] - c[lo]) > 0
    return out


def last_traded(ts5, states):
    """close time of the last TRADED bar per column (int64; -1 if none) and of the first (int64; -1 if none)"""
    t = _check_ts(ts5); tr = np.asarray(states) == TRADED
    has = tr.any(0)
    last = np.where(has, t[len(t) - 1 - np.argmax(tr[::-1], 0)], -1)
    first = np.where(has, t[np.argmax(tr, 0)], -1)
    return last.astype(np.int64), first.astype(np.int64)


def descriptive_dead_after(decision_ts, last_traded_ts, data_end_ts):
    """NOT CAUSAL (reads whether a name ever trades again). bool [K, N]: t > last TRADED bar, and that bar is > 24 h before the data end.
    Only for counting contamination and choosing fixtures; never an eligibility input."""
    A = np.asarray(decision_ts, np.int64).ravel()[:, None]; L = np.asarray(last_traded_ts, np.int64)[None, :]
    return (L >= 0) & (A > L) & (L < int(data_end_ts) - 86400)


def guarded_sha256(path):
    """sha256 of a file whose bytes were all read; refuses an iCloud-evicted placeholder (bytes read != st_size, or the empty hash on a non-empty file)"""
    size = os.stat(path).st_size; h = hashlib.sha256(); n = 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    d = h.hexdigest()
    if n != size or (size > 0 and d == EMPTY_SHA256):
        raise TradabilityError("unreadable or evicted file %s (read %d of %d bytes, sha %s)" % (path, n, size, d[:16]))
    return d


class Artifact:
    """The canonical built tradability artifact (fx_trd_build.py). Keys: symbols, anchor_ts, state_W24H, state_W4H, truncated_W24H, truncated_W4H,
    last_traded_ts, first_traded_ts, data_end_ts, ts5, traded5_bits, tradable5m_W24H_bits, tradable5m_W4H_bits, spec_sha256."""

    def __init__(self, z, path, sha):
        self.path, self.sha256 = path, sha
        spec = str(z["spec_sha256"])
        if spec != SPEC_SHA256:
            raise TradabilityError("artifact was built under spec %s, module is %s" % (spec[:16], SPEC_SHA256[:16]))
        self.symbols = [str(s) for s in z["symbols"]]
        self.col = {s: j for j, s in enumerate(self.symbols)}
        self.anchor_ts = z["anchor_ts"].astype(np.int64)
        self._row = {int(a): k for k, a in enumerate(self.anchor_ts)}
        self._state = {w: z["state_" + w] for w in WINDOWS}
        self.last_traded_ts = z["last_traded_ts"].astype(np.int64)
        self.first_traded_ts = z["first_traded_ts"].astype(np.int64)
        self.data_end_ts = int(z["data_end_ts"])
        self._z = z

    @classmethod
    def load(cls, path, *, expected_sha256):
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
            raise TradabilityError("expected_sha256 must be the full 64-hex sha of the artifact (no default)")
        sha = guarded_sha256(path)
        if sha != expected_sha256:
            raise TradabilityError("artifact sha %s != expected %s" % (sha[:16], expected_sha256[:16]))
        return cls(np.load(path, allow_pickle=False), path, sha)

    def columns(self, symbols):
        miss = [s for s in symbols if s not in self.col]
        if miss:
            raise TradabilityError("symbols not on the artifact axis: %s" % miss[:10])
        return np.array([self.col[s] for s in symbols], np.int64)

    def rows(self, ts):
        ts = np.asarray(ts, np.int64).ravel()
        if len(ts) and ts.max() > self.data_end_ts:
            raise TradabilityError("decision time %d after data end %d: refusing to carry forward" % (int(ts.max()), self.data_end_ts))
        miss = [int(a) for a in ts if int(a) not in self._row]
        if miss:
            raise TradabilityError("%d decision times not on the artifact's 4h grid (first %d)" % (len(miss), miss[0]))
        return np.array([self._row[int(a)] for a in ts], np.int64)

    def state(self, ts, symbols, *, window):
        _window_s(window)
        return self._state[window][np.ix_(self.rows(ts), self.columns(symbols))]

    def tradable(self, ts, symbols, *, window):
        """bool [len(ts), len(symbols)]; the eligibility flag"""
        return self.state(ts, symbols, window=window) == TRADABLE

    def mask_values(self, values, ts, symbols, *, window):
        """values [len(ts), len(symbols)] float -> copy with non-tradable cells set to NaN (e.g. the fund rank base)"""
        v = np.array(values, dtype=np.float64, copy=True)
        v[~self.tradable(ts, symbols, window=window)] = np.nan
        return v

    def dead_after(self, ts, symbols):
        """descriptive, NOT causal"""
        return descriptive_dead_after(ts, self.last_traded_ts[self.columns(symbols)], self.data_end_ts)
