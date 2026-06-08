"""Per-asset, strictly-causal feature builder for multi-asset y_600 (Phase 2).

`build_features(panel, sym) -> (F: (T, n_feat) float32, names: list[str])`.
Every feature at row t uses ONLY bars <= t (no centered/forward rolling, no
reverse cumsum, no peeking at y). This feeds the per-asset Ridge SNR gate and,
later, the DL panel.

DISCIPLINE — mechanism over stacking. Each GROUP below carries a one-line
mechanism: WHY it should carry y_600 signal in low-SNR crypto microstructure.
We do not add a feature without a stated reason.

Columns are consumed BY NAME via `panel.cols.index(name)` — never by position.
QTY columns arrive already scaled by the loader. Values are clipped/winsorized
to stay finite; the warmup region (rolling not yet filled) is nan_to_num'd to 0.

NOT included here (per task scope): cross-asset / BTC features. Those land in a
later task. This module is strictly per-asset.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np

# Window lengths (seconds == bars on the 1s grid).
RET_WINDOWS = (1, 5, 30, 60, 300)
VOL_WINDOWS = (30, 60, 300)
FLOW_WINDOWS = (30, 60, 300)
HORIZON = 600  # y_600 forward seconds

# 5-level LOB column suffixes (level 0 has no suffix in the schema).
_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]

# Cumulative-depth buckets that exist in the schema (suffix == bps distance).
_DEP_ALL = ["0.1", "0.3", "1.0", "3.0", "10.0", "30.0", "100.0", "300.0", "1000.0"]
# Buckets used for the depth-ratio group (mid-book, where the snapshot is liquid).
_DEP_RATIO = ["1.0", "3.0", "10.0", "30.0", "100.0"]

_EPS = 1e-9
# Winsorize most features to a generous band (units differ per group, so we
# clip ratios in [-1,1] explicitly and clip the rest to a wide z-ish band after
# scaling). Returns are in bps; rolling sums are robust-scaled per their group.
_CLIP_RET_BPS = 500.0     # 1s..300s mid log-ret in bps; |500bps|=5% cap
_CLIP_VOL_BPS = 1000.0
_CLIP_GENERIC = 20.0      # for already-normalized (ratio / robust-scaled) feats


# ---------------------------------------------------------------------------
# Strictly-causal primitives
# ---------------------------------------------------------------------------

def _col(panel, sym: str, name: str) -> np.ndarray:
    """Column `name` for `sym` as float64 (consumed by name, never position)."""
    return panel.data[sym][:, panel.cols.index(name)].astype(np.float64)


def _causal_lag(x: np.ndarray, k: int) -> np.ndarray:
    """x shifted forward by k: out[t] = x[t-k], out[<k] = NaN. Backward-only."""
    out = np.full_like(x, np.nan)
    if k < x.shape[0]:
        out[k:] = x[:-k]
    return out


def _causal_roll_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing-window sum over [t-w+1, t] (inclusive of t). NaN-safe: NaNs count
    as 0 in the sum. Backward-only via cumulative sum.

    out[t] = sum_{j=t-w+1..t} x[j]. For t < w-1 the window is partial (sum from 0).
    """
    xf = np.where(np.isfinite(x), x, 0.0)
    cs = np.cumsum(xf)
    out = cs.copy()
    if w < x.shape[0]:
        out[w:] = cs[w:] - cs[:-w]
    return out


def _causal_roll_count(x: np.ndarray, w: int) -> np.ndarray:
    """Count of finite entries in trailing window [t-w+1, t]. For mean/std denom."""
    f = np.isfinite(x).astype(np.float64)
    cs = np.cumsum(f)
    out = cs.copy()
    if w < x.shape[0]:
        out[w:] = cs[w:] - cs[:-w]
    return out


def _causal_roll_mean(x: np.ndarray, w: int) -> np.ndarray:
    s = _causal_roll_sum(x, w)
    n = _causal_roll_count(x, w)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(n > 0, s / n, np.nan)


def _causal_roll_std(x: np.ndarray, w: int) -> np.ndarray:
    """Population std over trailing window [t-w+1, t], NaN-safe. Backward-only."""
    n = _causal_roll_count(x, w)
    s1 = _causal_roll_sum(x, w)
    s2 = _causal_roll_sum(np.where(np.isfinite(x), x, 0.0) ** 2, w)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(n > 0, s1 / n, np.nan)
        var = np.where(n > 0, s2 / n - mean ** 2, np.nan)
    var = np.maximum(var, 0.0)  # guard tiny negatives from float cancellation
    return np.sqrt(var)


def _log_ret(mid: np.ndarray, k: int) -> np.ndarray:
    """Causal k-step log return in bps: 1e4*(log mid[t] - log mid[t-k])."""
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(mid)
    out = lm - _causal_lag(lm, k)
    return out * 1e4


def _imbalance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(a-b)/(a+b), bounded in [-1,1]; 0 where denom ~ 0."""
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(np.abs(denom) > _EPS, (a - b) / denom, 0.0)
    return out


# ---------------------------------------------------------------------------
# Feature builder
# ---------------------------------------------------------------------------

def build_features(panel, sym: str) -> Tuple[np.ndarray, List[str]]:
    """Per-asset causal features for `sym`. Returns (F (T,n_feat) float32, names)."""
    mid = _col(panel, sym, "mid")
    vwap = _col(panel, sym, "vwap")
    twap = _col(panel, sym, "twap")
    T = mid.shape[0]

    feats: List[np.ndarray] = []
    names: List[str] = []

    def add(name: str, vals: np.ndarray, clip: float = _CLIP_GENERIC):
        v = np.asarray(vals, dtype=np.float64)
        v = np.clip(v, -clip, clip)
        feats.append(v)
        names.append(name)

    # =====================================================================
    # GROUP 1 — Multi-scale returns.
    # Mechanism: momentum/reversal operate at different horizons; a multi-scale
    # return basis lets the model pick the sign-coherent timescale for y_600.
    # vwap/twap-vs-mid = execution-price pressure (where prints clustered vs the
    # quote midpoint), a leading sign of order-flow direction.
    # =====================================================================
    for w in RET_WINDOWS:
        add(f"ret_mid_{w}s", _log_ret(mid, w), clip=_CLIP_RET_BPS)
    # execution-price pressure: (vwap-mid)/mid and (twap-mid)/mid in bps
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap_press = (vwap - mid) / mid * 1e4
        twap_press = (twap - mid) / mid * 1e4
    add("vwap_press_bps", vwap_press, clip=_CLIP_RET_BPS)
    add("twap_press_bps", twap_press, clip=_CLIP_RET_BPS)
    # short rolling mean of the pressure (denoise the 1s print noise)
    add("vwap_press_mean_30s", _causal_roll_mean(vwap_press, 30), clip=_CLIP_RET_BPS)
    add("twap_press_mean_30s", _causal_roll_mean(twap_press, 30), clip=_CLIP_RET_BPS)

    # =====================================================================
    # GROUP 2 — Realized volatility.
    # Mechanism: vol regime conditions signal strength (alpha lives mostly in
    # calm tape) and short-horizon RV is itself weakly predictive of |y_600|.
    # =====================================================================
    r1 = _log_ret(mid, 1)  # 1s log-ret in bps
    for w in VOL_WINDOWS:
        add(f"rv_{w}s", _causal_roll_std(r1, w), clip=_CLIP_VOL_BPS)

    # =====================================================================
    # GROUP 3 — Order-book imbalance / depth ratios (STATE).
    # Mechanism: queue imbalance = instantaneous pressure; size resting on each
    # side biases the next mid tick. Multi-level OBI captures pressure deeper
    # than L1; cumu-depth ratios capture it across price-distance buckets.
    # NOTE: OFI (GROUP 5) is the FLOW counterpart and is the *primary* pressure
    # signal (CKS-2014). These STATE ratios are retained as complementary
    # context (level-of-book), not as the primary driver.
    # =====================================================================
    bidsz = [_col(panel, sym, c) for c in _BID_SZ]
    asksz = [_col(panel, sym, c) for c in _ASK_SZ]
    # L1 OBI
    add("obi_L1", _imbalance(bidsz[0], asksz[0]), clip=1.0)
    # multi-level OBI: cumulative depth over levels 0..n
    cum_b = np.zeros(T)
    cum_a = np.zeros(T)
    for lvl in range(5):
        cum_b = cum_b + bidsz[lvl]
        cum_a = cum_a + asksz[lvl]
        if lvl >= 1:  # L1 already added as obi_L1
            add(f"obi_L{lvl + 1}", _imbalance(cum_b, cum_a), clip=1.0)
    # cumu-depth ratio at bps buckets
    for dx in _DEP_RATIO:
        cb = _col(panel, sym, f"cumu_bidsz_dep_{dx}")
        ca = _col(panel, sym, f"cumu_asksz_dep_{dx}")
        add(f"depth_ratio_{dx}bps", _imbalance(cb, ca), clip=1.0)

    # =====================================================================
    # GROUP 4 — Cumulative-depth book SLOPE / shape.
    # Mechanism: the liquidity curve's shape (how fast cumulative size grows
    # with price distance) = resilience / price-impact. A steep curve = deep
    # book = small impact; a flat curve = fragile. bps-normalized so the slope
    # is cross-asset comparable (a property single-asset never used).
    # We regress log(cumu_sz) on log(bps-distance) per side (causal: each row
    # uses only that bar's snapshot).
    # =====================================================================
    log_bps = np.log(np.array([float(x) for x in _DEP_ALL]))   # (9,)
    log_bps_c = log_bps - log_bps.mean()
    denom_slope = float(np.sum(log_bps_c ** 2))
    bid_cumu = np.stack([_col(panel, sym, f"cumu_bidsz_dep_{dx}") for dx in _DEP_ALL], axis=1)
    ask_cumu = np.stack([_col(panel, sym, f"cumu_asksz_dep_{dx}") for dx in _DEP_ALL], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        lb = np.log(np.maximum(bid_cumu, _EPS))   # (T,9)
        la = np.log(np.maximum(ask_cumu, _EPS))
    # OLS slope of log(size) ~ log(bps) per row = cov(x,y)/var(x)
    bid_slope = (lb - lb.mean(axis=1, keepdims=True)) @ log_bps_c / denom_slope
    ask_slope = (la - la.mean(axis=1, keepdims=True)) @ log_bps_c / denom_slope
    add("book_slope_bid", bid_slope, clip=_CLIP_GENERIC)
    add("book_slope_ask", ask_slope, clip=_CLIP_GENERIC)
    add("book_slope_asym", bid_slope - ask_slope, clip=_CLIP_GENERIC)

    # =====================================================================
    # GROUP 5 — True multi-level OFI (FLOW) — PRIMARY pressure signal.
    # Mechanism: Order-Flow Imbalance is a FLOW not a STATE. Cont-Kukanov-
    # Stoikov (2014): per-level OFI explains the majority of short-horizon mid
    # variance — the strongest known microstructure predictor. e_n compares the
    # current snapshot to the previous (causal 1s diff):
    #   bid side: +bidsz_n if bid_n rose, -bidsz_n_prev if bid_n fell, else
    #             (bidsz_n - bidsz_n_prev) if price unchanged (queue replenish).
    #   ask side: mirror (a rising ask = liquidity added against buyers).
    # OFI_n = bid_term - ask_term; sum over 5 levels; rolling sums {30,60,300}.
    # This REPLACES static OBI as the primary directional feature (OBI kept as
    # complementary state context, see GROUP 3 note). Robust-scaled per asset.
    # =====================================================================
    bid_px = [_col(panel, sym, c) for c in _BID_PX]
    ask_px = [_col(panel, sym, c) for c in _ASK_PX]
    ofi_per_bar = np.zeros(T)
    for lvl in range(5):
        bp, bpz = bid_px[lvl], bidsz[lvl]
        ap, apz = ask_px[lvl], asksz[lvl]
        bp_prev, bpz_prev = _causal_lag(bp, 1), _causal_lag(bpz, 1)
        ap_prev, apz_prev = _causal_lag(ap, 1), _causal_lag(apz, 1)
        with np.errstate(invalid="ignore"):  # NaN price comparisons in warmup -> False
            # bid contribution
            bid_term = np.where(bp > bp_prev, bpz,
                       np.where(bp < bp_prev, -bpz_prev, bpz - bpz_prev))
            # ask contribution (a rising ask price withdraws sell liquidity => +)
            ask_term = np.where(ap > ap_prev, apz_prev,
                       np.where(ap < ap_prev, -apz, apz - apz_prev))
        ofi_per_bar = ofi_per_bar + np.where(np.isfinite(bid_term), bid_term, 0.0) \
                                  - np.where(np.isfinite(ask_term), ask_term, 0.0)
    # CAUSAL scale: expanding-window RMS (uses only bars <= t). A whole-series
    # MAD/std would leak the future into past rows (it changes when a future bar
    # changes) — the downstream per-asset Ridge standardizes anyway, so we only
    # need a stable, strictly-causal unit here.
    ofi_scale = _causal_expanding_scale(ofi_per_bar)
    add("ofi_1s", ofi_per_bar / ofi_scale, clip=_CLIP_GENERIC)
    for w in FLOW_WINDOWS:
        rs = _causal_roll_sum(ofi_per_bar, w)
        add(f"ofi_{w}s", rs / (ofi_scale * np.sqrt(w)), clip=_CLIP_GENERIC)

    # =====================================================================
    # GROUP 6 — Deep-book OFI proxy (bkAdd/bkDel).
    # Mechanism: bkAdd/bkDel ARE the order-flow primitives at depth that the
    # 5-level snapshot misses — net liquidity added/pulled beyond L5. Net bid
    # build vs net ask build = directional depth pressure.
    # net = (bkAddBid - bkDelBid) - (bkAddAsk - bkDelAsk).
    # =====================================================================
    add_bid = _col(panel, sym, "bkAddBid")
    add_ask = _col(panel, sym, "bkAddAsk")
    del_bid = _col(panel, sym, "bkDelBid")
    del_ask = _col(panel, sym, "bkDelAsk")
    deep_ofi = (add_bid - del_bid) - (add_ask - del_ask)
    deep_scale = _causal_expanding_scale(deep_ofi)
    add("deep_ofi_1s", deep_ofi / deep_scale, clip=_CLIP_GENERIC)
    for w in FLOW_WINDOWS:
        rs = _causal_roll_sum(deep_ofi, w)
        add(f"deep_ofi_{w}s", rs / (deep_scale * np.sqrt(w)), clip=_CLIP_GENERIC)

    # =====================================================================
    # GROUP 7 — Signed trade flow.
    # Mechanism: aggressive (taker) trade imbalance = informed pressure; the
    # side that lifts/hits pushes mid. Quantity, dollar, and count imbalances
    # are three views (count robust to size outliers). VPIN-style toxicity
    # (|signed| / total over a window) flags informed/adverse regimes where
    # signal direction is sharper.
    # =====================================================================
    tq_buy = _col(panel, sym, "tdQtyBuy")
    tq_sell = _col(panel, sym, "tdQtySell")
    tpx_buy = _col(panel, sym, "tdQtyPxBuy")
    tpx_sell = _col(panel, sym, "tdQtyPxSell")
    tc_buy = _col(panel, sym, "tdCntBuy")
    tc_sell = _col(panel, sym, "tdCntSell")
    # instantaneous imbalances
    add("tflow_qty_imb", _imbalance(tq_buy, tq_sell), clip=1.0)
    add("tflow_dollar_imb", _imbalance(tpx_buy, tpx_sell), clip=1.0)
    add("tflow_cnt_imb", _imbalance(tc_buy, tc_sell), clip=1.0)
    # rolling signed-qty imbalance over windows (smoother informed-flow estimate)
    signed_qty = tq_buy - tq_sell
    total_qty = tq_buy + tq_sell
    for w in FLOW_WINDOWS:
        snum = _causal_roll_sum(signed_qty, w)
        sden = _causal_roll_sum(total_qty, w)
        with np.errstate(divide="ignore", invalid="ignore"):
            add(f"tflow_qty_imb_{w}s",
                np.where(sden > _EPS, snum / sden, 0.0), clip=1.0)
    # VPIN-style toxicity: |signed| / total over a window (bounded [0,1])
    for w in (60, 300):
        absnum = _causal_roll_sum(np.abs(signed_qty), w)
        sden = _causal_roll_sum(total_qty, w)
        with np.errstate(divide="ignore", invalid="ignore"):
            add(f"vpin_{w}s",
                np.where(sden > _EPS, absnum / sden, 0.0), clip=1.0)

    # =====================================================================
    # GROUP 8 — Mid-change asymmetry.
    # Mechanism: up-tick vs down-tick count asymmetry within a bar = directional
    # microstructure drift (the tape "wants" to go one way) — a sign-only,
    # size-agnostic momentum proxy that is robust to size outliers.
    # =====================================================================
    chg_up = _col(panel, sym, "midChgUp")
    chg_dn = _col(panel, sym, "midChgDn")
    add("midchg_asym", _imbalance(chg_up, chg_dn), clip=1.0)
    for w in (30, 60, 300):
        up_s = _causal_roll_sum(chg_up, w)
        dn_s = _causal_roll_sum(chg_dn, w)
        add(f"midchg_asym_{w}s", _imbalance(up_s, dn_s), clip=1.0)

    # =====================================================================
    # GROUP 9 — Spread.
    # Mechanism: spread = adverse-selection / vol proxy AND a cost gate — wide
    # spread = uncertain / expensive regime where y_600 sign is noisier and
    # trades are uneconomic. Level + short rolling mean (denoised).
    # =====================================================================
    bid0 = bid_px[0]
    ask0 = ask_px[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_bps = np.where(mid > _EPS, (ask0 - bid0) / mid * 1e4, np.nan)
    add("spread_bps", spread_bps, clip=_CLIP_VOL_BPS)
    add("spread_bps_mean_60s", _causal_roll_mean(spread_bps, 60), clip=_CLIP_VOL_BPS)

    # ---------------------------------------------------------------------
    # Assemble, sanitize: nan_to_num after warmup so rows >= warmup are finite.
    # ---------------------------------------------------------------------
    F = np.stack(feats, axis=1).astype(np.float64)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    return F.astype(np.float32), names


def _causal_expanding_scale(x: np.ndarray, floor: float = 1.0) -> np.ndarray:
    """Strictly-causal per-row scale: sqrt of the EXPANDING mean of x^2 over
    bars [0, t] (RMS). out[t] uses ONLY bars <= t, so a future perturbation can
    never change a past row's scale — this is exactly what the causality test
    enforces (no backward-in-time dependency either: we never index a future
    row to fill an earlier one).

    RMS (not expanding-MAD) is chosen because it's O(T) via cumsum and stable;
    exact per-asset scaling is the downstream Ridge standardizer's job — here we
    only need a finite, causal unit so OFI magnitudes don't saturate the clip.
    `floor` (=1.0) guards the tiny-n early region and near-constant series from
    dividing by ~0."""
    xf = np.where(np.isfinite(x), x, 0.0)
    n = np.arange(1, x.shape[0] + 1, dtype=np.float64)
    ms = np.cumsum(xf ** 2) / n                      # expanding mean of squares
    scale = np.sqrt(np.maximum(ms, 0.0))
    return np.maximum(scale, floor)


# ---------------------------------------------------------------------------
# Target + validity
# ---------------------------------------------------------------------------

def compute_y600(panel, sym: str) -> np.ndarray:
    """Forward 600s log-return of mid: y[t] = log(mid[t+600]) - log(mid[t]).
    The last 600 rows have no forward window => NaN. (Forward-looking BY DESIGN
    — this is the label, NOT a feature; never feed it into build_features.)"""
    mid = _col(panel, sym, "mid")
    h = HORIZON
    y = np.full(mid.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(mid)
    y[:-h] = lm[h:] - lm[:-h]
    return y


def valid_mask(panel, sym: str) -> np.ndarray:
    """Tradeable-bar mask: finite mid AND nonzero top-of-book size on both sides
    (a bar with zero/NaN size is an unquoted/degenerate book we must not trade
    or train on)."""
    mid = _col(panel, sym, "mid")
    bidsz = _col(panel, sym, "bidsz")
    asksz = _col(panel, sym, "asksz")
    finite = np.isfinite(mid) & np.isfinite(bidsz) & np.isfinite(asksz)
    with np.errstate(invalid="ignore"):  # NaN > 0 -> False (handled by `finite`)
        return finite & (bidsz > 0.0) & (asksz > 0.0)
