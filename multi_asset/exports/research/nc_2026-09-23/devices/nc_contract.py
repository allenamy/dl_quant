"""nc_contract — the ONE implementation of the data/state-layer rules of the new feature contract, imported unchanged by the producer
(serving, ~/wide_shadow/fea171/nc_contract.py) and by the history replay that builds the training features.

Frozen design: docs/DESIGN_producer_new_contract_2026-09-23.md (33ef8164) §A1 / §A4 / §A5 / §A6 and FREEZE amendment 1 (5c89f8d22) §2.
Researcher definitions reproduced here (file:line in combo_20260923/devices and uplift_20260922/devices):
  funding EMA        feature_contract.py L72-L93 funding_state (loop body L80-L88, as-of L89-L92)
  settlement interval DESIGN §A4-1 + lead ruling C-2: the adjacent-gap rule, nearest of {1,2,4,6,8} h, exact ties -> the LARGER,
                     gap > 24 h or <= 0 -> unknown, first event of a name -> unknown; unknown resets the EMA
  legality           tradability.py (SPEC_TRADABILITY, W24H) AND liveness (>= 1 real bar with finite log_qv in the same window)
  fund rank base     combo_legs.py L37-L39 (legal AND fresh known EMA) AND crypto (the one exception, DESIGN §0)
  return channel     FREEZE amendment 1 §2: rr = raw where the sparse boundary table has the cell, else float32(ch0); NaN stays NaN
Pure: numpy (+ tradability.py for legality); no file, no network, no clock.
"""
from __future__ import annotations

import math

import numpy as np

IV_GRID = (1.0, 2.0, 4.0, 6.0, 8.0)
FRESH_S = 43200                        # feature_contract.funding_state max_age (12 h)
HALF_LIFE_S = 3 * 86400                # feature_contract.py L87
W24H_S = 86400
BOUND16 = float(np.float16(0.3))       # 0.300048828125: the value a clipped (or bound-rounded) ret5 bar holds in float16


class ContractError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------- §A4 settlement interval
def snap_interval(dt_s):
    """Hours between two consecutive settlements of one name -> the settlement interval, or None (unknown).
    h = dt_s / 3600 (not pre-rounded); 0 < h <= 24 -> the nearest of IV_GRID, an exact tie -> the LARGER; otherwise None."""
    h = float(dt_s) / 3600.0
    if not (h > 0.0 and h <= 24.0):
        return None
    best = None
    bd = None
    for g in IV_GRID:
        d = abs(g - h)
        if bd is None or d < bd or (d == bd and g > best):
            best, bd = g, d
    return best


# ---------------------------------------------------------------------------------------------------- §A4 EMA (researcher loop body)
def ema_step(state, ft, rate, iv):
    """One settlement event through feature_contract.funding_state's loop body (L80-L88), verbatim arithmetic.
    state: {"acc": float | None, "last_ts": int | None}  (None/None = reset or never started). Returns (new_state, ema_at_event)
    where ema_at_event is NaN after a reset. An unknown interval (iv None / not > 0) or a non-finite rate resets."""
    acc = state.get("acc") if state else None
    prev = state.get("last_ts") if state else None
    acc = float("nan") if acc is None else float(acc)
    if rate is None or not math.isfinite(float(rate)) or iv is None or not math.isfinite(float(iv)) or float(iv) <= 0:
        return {"acc": None, "last_ts": None}, float("nan")
    rn = float(rate) * 8 / float(iv)
    if prev is None:
        acc = rn
    else:
        decay = 2 ** (-float(int(ft) - int(prev)) / (3 * 86400))
        acc = decay * acc + (1 - decay) * rn
    return {"acc": acc, "last_ts": int(ft)}, acc


def ingest_settlements(ledger, state, events):
    """Serving-side funding update for ONE name. ledger: list of [ft, rate, iv|None] (ascending ft, the producer's ledger_tail);
    events: iterable of (ft, rate) with ft strictly increasing and > the ledger's last ft (duplicates / out of order refuse).
    The interval of each event is snap_interval(ft - previous ledger ft); the first event of a name (empty ledger) is unknown.
    Returns (ledger, state, n_applied)."""
    led = list(ledger)
    n = 0
    for ft, rate in events:
        ft = int(ft)
        if led and ft <= int(led[-1][0]):
            raise ContractError(f"funding event {ft} not after the ledger's last {led[-1][0]}")
        iv = snap_interval(ft - int(led[-1][0])) if led else None
        led.append([ft, float(rate), iv])
        state, _ = ema_step(state, ft, float(rate), iv)
        n += 1
    return led, state, n


def funding_asof(state, last_row, anchor):
    """feature_contract.funding_state as-of (L89-L92) for one name at `anchor` given the state AFTER every event <= anchor and that
    name's last ledger row [ft, rate, iv]. Valid iff anchor - ft <= FRESH_S and the EMA is finite; otherwise all four are NaN.
    Returns (ema, rate, iv, rn8) with rn8 = rate*8/iv."""
    nan = float("nan")
    if not last_row or state is None or state.get("acc") is None:
        return nan, nan, nan, nan
    ft, rate, iv = int(last_row[0]), float(last_row[1]), last_row[2]
    if ft > int(anchor):
        raise ContractError(f"as-of row {ft} is after the anchor {anchor}")
    acc = float(state["acc"])
    if not (int(anchor) - ft <= FRESH_S) or not math.isfinite(acc) or iv is None:
        return nan, nan, nan, nan
    iv = float(iv)
    return acc, rate, iv, rate * 8 / iv


# ---------------------------------------------------------------------------------------------------- §A1 legality / candidates
def legal_live(ts5, log_cnt, log_qv, anchors, trad):
    """bool [K, N]: TRADABLE(W24H) at each anchor (tradability.window_states on bar_states(log_cnt)) AND >= 1 bar with finite log_qv
    and close in (A - 24h, A] (liveness; hole cells must already be NaN in every channel). `trad` = the imported tradability module."""
    t = np.asarray(ts5, np.int64)
    st, _trunc = trad.window_states(t, trad.bar_states(np.asarray(log_cnt)), anchors, window="W24H")
    tradable = st == trad.TRADABLE
    A = np.asarray(anchors, np.int64).ravel()
    hi = np.searchsorted(t, A, side="right")
    lo = np.searchsorted(t, A - W24H_S, side="right")
    fq = np.isfinite(np.asarray(log_qv, np.float32))
    c = np.zeros((len(t) + 1, fq.shape[1]), np.int32)
    np.cumsum(fq, axis=0, dtype=np.int32, out=c[1:])
    live = (c[hi] - c[lo]) > 0
    return tradable & live


def fund_base(names, legal, crypto, fe_asof):
    """combo_legs.py L37-L39 + crypto: {name: fe} over names with legal AND crypto AND a finite (fresh, known) as-of EMA."""
    out = {}
    for s, lg, cr, v in zip(names, legal, crypto, fe_asof):
        if bool(lg) and bool(cr) and v is not None and math.isfinite(float(v)):
            out[s] = float(v)
    return out


# ---------------------------------------------------------------------------------------------------- §A3 return channel (amendment 1)
def is_bound_f16(x16):
    """True where a float16 ret5 value sits on the clip bound (the value a clipped or bound-rounded bar holds)."""
    r = np.asarray(x16, np.float64)
    return np.isfinite(r) & (np.abs(r) == BOUND16)


def needs_boundary_raw(raw):
    """Serving ingestion: a bar whose stored float16 value lands on the bound keeps its exact raw return in the sparse table."""
    if raw is None or not math.isfinite(raw):
        return False
    return abs(float(np.float16(min(max(float(raw), -0.3), 0.3)))) == BOUND16


def rr_from_ch0(ts, ch0_f16, table_ts, table_col, table_raw):
    """float32 [T, N] return channel: float32(ch0); cells present in the sparse table take raw_f32; NaN ch0 stays NaN unless the table
    holds the cell (the deployment-time gap cells of amendment 1 §2.3). A table cell outside `ts` is ignored (the table rolls)."""
    rr = np.asarray(ch0_f16).astype(np.float32)
    t = np.asarray(ts, np.int64)
    if len(table_ts):
        r = np.searchsorted(t, np.asarray(table_ts, np.int64))
        inside = (r < len(t))
        inside[inside] &= (t[r[inside]] == np.asarray(table_ts, np.int64)[inside])
        rr[r[inside], np.asarray(table_col, np.int64)[inside]] = np.asarray(table_raw, np.float32)[inside]
    return rr
