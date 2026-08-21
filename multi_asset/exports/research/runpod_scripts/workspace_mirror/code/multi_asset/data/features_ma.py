"""Per-asset, strictly-causal feature builder for multi-asset y_600 (Phase 2).

`build_features(panel, sym) -> (F: (T, n_feat) float32, names: list[str])`.
Every feature at row t uses ONLY bars <= t (no centered/forward rolling, no
reverse cumsum, no peeking at y). This feeds the per-asset Ridge SNR gate and,
later, the DL panel.

DESIGN — STRONG signal first, no over-normalization (2026-06-09 rebuild).
The previous cut shrank the order-flow / reversal signal by dividing flows by a
causal *expanding-window RMS* (`_causal_expanding_scale`). Diagnostics on BTC
y_600 (clean 20-day sample, `eda/_deep_flow_probe.py`) showed RAW rolling-sum
flows / reversal carry ~0.055 univariate Spearman, but the expanding-RMS-scaled
versions decayed to ~0.037 — a third of the signal lost to a normalizer that
injects its own (noisy, drifting) denominator.

ROOT-CAUSE FIX, applied here:
  - Order-flow features are LEFT AS RAW ROLLING SUMS. We do NOT divide by any
    causal expanding RMS / std / MAD. The downstream per-fold standardizer owns
    final scaling — it z-scores each column on the train fold, which is the only
    place a scale should be estimated (and the only leak-free place to do it).
    A raw rolling sum is strictly causal and preserves the signal exactly.
  - Ratio / imbalance features (OBI, depth ratios, spread bps) are naturally
    bounded or already in interpretable units, so they pass through as-is.

What the diagnostics said about WHICH signals matter (BTC y_600, clean):
  ret_300s  (5-min mid reversal)        Spearman -0.058   <- strongest
  midchg_300s (midChgUp-midChgDn 300s)            -0.055
  dollarflow_300s (tdQtyPx buy-sell 300s)         -0.054
  tradeflow_300s  (tdQty buy-sell 300s)           -0.053
  dollarflow_30s / tradeflow_30s (short)  Pearson +0.04   (continuation)
  OFI (level-by-level CKS)                          0.016  <- WEAK, deprioritized
The dominant structure is REVERSAL at the 5-min scale + order flow. OFI is kept
as a single low-priority summary, not a per-window block.

Columns are consumed BY NAME via `panel.cols.index(name)` — never by position.
QTY columns arrive already scaled by the loader. nan_to_num is applied AFTER a
short warmup; all rows are kept finite.

NOT included here (per task scope): cross-asset / BTC features. Those land in a
later task. This module is strictly per-asset.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np

# Window lengths (seconds == bars on the 1s grid).
RET_WINDOWS = (30, 60, 120, 300, 600)   # reversal lives at 300; 600 = horizon-scale
FLOW_WINDOWS = (30, 60, 300)            # 30 = continuation, 300 = reversal-scale
VOL_WINDOWS = (60, 300)                 # regime conditioner
HORIZON = 600  # y_600 forward seconds

# 5-level LOB column suffixes (level 0 has no suffix in the schema).
_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]

# Cumulative-depth buckets used for depth-ratio + book-slope (suffix == bps).
_DEP_RATIO = ["1.0", "3.0", "10.0", "30.0", "100.0"]
_DEP_SLOPE = ["0.1", "0.3", "1.0", "3.0", "10.0", "30.0", "100.0", "300.0", "1000.0"]

_EPS = 1e-9
# Generous finite clips per unit-group. These bound pathological outliers only;
# they are NOT a scaler (the per-fold standardizer scales). Flows are clipped at
# a wide band relative to their typical rolling-sum magnitude so the signal-
# carrying body is untouched.
_CLIP_RET_BPS = 1000.0   # multi-scale mid log-ret in bps; |1000bps|=10% cap
_CLIP_VOL_BPS = 2000.0
_CLIP_RATIO = 1.0        # bounded imbalances / ratios
_CLIP_FLOW = 1e7         # raw rolling-sum flows: wide guard, signal body untouched
_CLIP_SLOPE = 50.0       # OLS book-slope


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

    out[t] = sum_{j=t-w+1..t} x[j]. For t < w the window is partial (sum from 0).
    Matches the diagnostics probe's `roll_sum` exactly, so flow features are the
    SAME construction the 0.053-0.055 Spearman was measured on.
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
    """Causal k-step log return in bps: 1e4*(log mid[t] - log mid[t-k]).
    Sign-equivalent to the diagnostics probe's `logm[t]-logm[t-k]` (bps scaling
    is monotone, so Spearman is identical)."""
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

    def add(name: str, vals: np.ndarray, clip: float):
        v = np.asarray(vals, dtype=np.float64)
        v = np.clip(v, -clip, clip)
        feats.append(v)
        names.append(name)

    # =====================================================================
    # GROUP 1 — Multi-scale returns / reversal (THE strongest signal).
    # Mechanism: at the 5-min scale crypto mid mean-REVERTS into the next 10 min
    # (recent up-move -> next-10min down). ret_300s carried Spearman -0.058 in
    # diagnostics — the single strongest univariate feature. The {30,60,120,600}
    # scales give the model the timescale basis to pick the sign-coherent horizon
    # (short scales can show continuation, long scales reversal).
    # vwap/twap-vs-mid = execution-price pressure: where prints clustered vs the
    # quote midpoint, a leading sign of order-flow direction.
    # =====================================================================
    for w in RET_WINDOWS:
        add(f"ret_{w}s", _log_ret(mid, w), _CLIP_RET_BPS)
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap_press = (vwap - mid) / mid * 1e4
        twap_press = (twap - mid) / mid * 1e4
    add("vwap_press_bps", vwap_press, _CLIP_RET_BPS)
    add("twap_press_bps", twap_press, _CLIP_RET_BPS)
    add("vwap_press_60s", _causal_roll_mean(vwap_press, 60), _CLIP_RET_BPS)
    add("twap_press_60s", _causal_roll_mean(twap_press, 60), _CLIP_RET_BPS)

    # =====================================================================
    # GROUP 2 — Order flow, ROLLING SUMS (2nd strongest). NO expanding-RMS.
    # Mechanism: aggressive (taker) and book-build flow = informed/directional
    # pressure. At 300s these REVERSE with y_600 (-0.053/-0.054 Spearman); at 30s
    # they CONTINUE (+0.04 Pearson). Five flow primitives, three windows each.
    #   tradeflow = tdQtyBuy - tdQtySell          (signed taker quantity)
    #   dollarflow= tdQtyPxBuy - tdQtyPxSell       (signed taker notional)
    #   cntflow   = tdCntBuy - tdCntSell           (signed taker count, outlier-robust)
    #   bookflow  = (bkAddBid-bkDelBid)-(bkAddAsk-bkDelAsk)  (net depth build)
    #   midchg    = midChgUp - midChgDn            (uptick-downtick asymmetry)
    # SCALING CHOICE: leave as raw rolling SUMS. The per-fold standardizer
    # z-scores each column on the train fold (the only leak-free place to set a
    # scale). This is exactly the construction the diagnostics measured the
    # 0.053-0.055 Spearman on, so the signal is preserved bit-for-bit (vs the old
    # expanding-RMS which shrank it to ~0.037).
    # =====================================================================
    tq_buy = _col(panel, sym, "tdQtyBuy")
    tq_sell = _col(panel, sym, "tdQtySell")
    tpx_buy = _col(panel, sym, "tdQtyPxBuy")
    tpx_sell = _col(panel, sym, "tdQtyPxSell")
    tc_buy = _col(panel, sym, "tdCntBuy")
    tc_sell = _col(panel, sym, "tdCntSell")
    add_bid = _col(panel, sym, "bkAddBid")
    add_ask = _col(panel, sym, "bkAddAsk")
    del_bid = _col(panel, sym, "bkDelBid")
    del_ask = _col(panel, sym, "bkDelAsk")
    chg_up = _col(panel, sym, "midChgUp")
    chg_dn = _col(panel, sym, "midChgDn")

    tradeflow = tq_buy - tq_sell
    dollarflow = tpx_buy - tpx_sell
    cntflow = tc_buy - tc_sell
    bookflow = (add_bid - del_bid) - (add_ask - del_ask)
    midchg = chg_up - chg_dn

    flow_series = [
        ("tradeflow", tradeflow),
        ("dollarflow", dollarflow),
        ("cntflow", cntflow),
        ("bookflow", bookflow),
        ("midchg", midchg),
    ]
    for nm, series in flow_series:
        for w in FLOW_WINDOWS:
            add(f"{nm}_{w}s", _causal_roll_sum(series, w), _CLIP_FLOW)

    # =====================================================================
    # GROUP 3 — Realized volatility (regime conditioner).
    # Mechanism: vol regime conditions signal strength (alpha lives mostly in the
    # calmer tape) and short-horizon RV is weakly predictive of |y_600|. Rolling
    # std of 1s mid log-returns over {60,300}s.
    # =====================================================================
    r1 = _log_ret(mid, 1)  # 1s log-ret in bps
    for w in VOL_WINDOWS:
        add(f"rv_{w}s", _causal_roll_std(r1, w), _CLIP_VOL_BPS)

    # =====================================================================
    # GROUP 4 — Book imbalance / depth ratios (STATE context).
    # Mechanism: queue imbalance = instantaneous pressure; size resting on each
    # side biases the next mid tick. L1 + multi-level OBI capture near-touch
    # pressure; cumu-depth ratios capture it across price-distance buckets. These
    # are STATE (snapshot) features — context, weaker than the FLOW group above.
    # =====================================================================
    bidsz = [_col(panel, sym, c) for c in _BID_SZ]
    asksz = [_col(panel, sym, c) for c in _ASK_SZ]
    add("obi_L1", _imbalance(bidsz[0], asksz[0]), _CLIP_RATIO)
    cum_b = np.zeros(T)
    cum_a = np.zeros(T)
    for lvl in range(5):
        cum_b = cum_b + bidsz[lvl]
        cum_a = cum_a + asksz[lvl]
        if lvl >= 1:  # L1 already added as obi_L1
            add(f"obi_L{lvl + 1}", _imbalance(cum_b, cum_a), _CLIP_RATIO)
    for dx in _DEP_RATIO:
        cb = _col(panel, sym, f"cumu_bidsz_dep_{dx}")
        ca = _col(panel, sym, f"cumu_asksz_dep_{dx}")
        add(f"depth_ratio_{dx}bps", _imbalance(cb, ca), _CLIP_RATIO)

    # Book SLOPE: OLS of log(cumu_sz) on log(bps-distance) per side, per row
    # (causal — each row uses only that bar's snapshot). Steep curve = deep book
    # = small impact; flat = fragile. Asymmetry = directional liquidity skew.
    log_bps = np.log(np.array([float(x) for x in _DEP_SLOPE]))   # (9,)
    log_bps_c = log_bps - log_bps.mean()
    denom_slope = float(np.sum(log_bps_c ** 2))
    bid_cumu = np.stack([_col(panel, sym, f"cumu_bidsz_dep_{dx}") for dx in _DEP_SLOPE], axis=1)
    ask_cumu = np.stack([_col(panel, sym, f"cumu_asksz_dep_{dx}") for dx in _DEP_SLOPE], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        lb = np.log(np.maximum(bid_cumu, _EPS))   # (T,9)
        la = np.log(np.maximum(ask_cumu, _EPS))
    bid_slope = (lb - lb.mean(axis=1, keepdims=True)) @ log_bps_c / denom_slope
    ask_slope = (la - la.mean(axis=1, keepdims=True)) @ log_bps_c / denom_slope
    add("book_slope_bid", bid_slope, _CLIP_SLOPE)
    add("book_slope_ask", ask_slope, _CLIP_SLOPE)
    add("book_slope_asym", bid_slope - ask_slope, _CLIP_SLOPE)

    # =====================================================================
    # GROUP 5 — Spread (cost / adverse-selection / vol proxy).
    # Mechanism: wide spread = uncertain / expensive regime where y_600 sign is
    # noisier and trades are uneconomic. Level + short rolling mean (denoised).
    # =====================================================================
    bid0 = _col(panel, sym, "bid")
    ask0 = _col(panel, sym, "ask")
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_bps = np.where(mid > _EPS, (ask0 - bid0) / mid * 1e4, np.nan)
    add("spread_bps", spread_bps, _CLIP_VOL_BPS)
    add("spread_bps_60s", _causal_roll_mean(spread_bps, 60), _CLIP_VOL_BPS)

    # =====================================================================
    # GROUP 6 — VPIN-style toxicity (informed-flow / regime flag).
    # Mechanism: |signed taker qty| / total taker qty over a window = fraction of
    # one-sided (toxic/informed) flow. High VPIN flags adverse-selection regimes
    # where the sign is sharper but also riskier. Bounded [0,1].
    # =====================================================================
    total_qty = tq_buy + tq_sell
    for w in (60, 300):
        absnum = _causal_roll_sum(np.abs(tradeflow), w)
        sden = _causal_roll_sum(total_qty, w)
        with np.errstate(divide="ignore", invalid="ignore"):
            add(f"vpin_{w}s", np.where(sden > _EPS, absnum / sden, 0.0), _CLIP_RATIO)

    # =====================================================================
    # GROUP 7 — OFI summary (DEPRIORITIZED — diagnostics: ~0.016 Spearman).
    # Mechanism: Cont-Kukanov-Stoikov order-flow imbalance (signed per-level queue
    # change) is the classic microstructure predictor, but on BTC y_600 it was
    # WEAK (much weaker than trade/dollar/book flow). Kept as a SINGLE 60s summary
    # for completeness / non-linear interactions, NOT as a per-window block.
    # =====================================================================
    bid_px = [_col(panel, sym, c) for c in _BID_PX]
    ask_px = [_col(panel, sym, c) for c in _ASK_PX]
    ofi_per_bar = np.zeros(T)
    for lvl in range(5):
        bp, bpz = bid_px[lvl], bidsz[lvl]
        ap, apz = ask_px[lvl], asksz[lvl]
        bp_prev, bpz_prev = _causal_lag(bp, 1), _causal_lag(bpz, 1)
        ap_prev, apz_prev = _causal_lag(ap, 1), _causal_lag(apz, 1)
        with np.errstate(invalid="ignore"):  # NaN comparisons in warmup -> False
            bid_term = np.where(bp > bp_prev, bpz,
                       np.where(bp < bp_prev, -bpz_prev, bpz - bpz_prev))
            ask_term = np.where(ap < ap_prev, apz,
                       np.where(ap > ap_prev, -apz_prev, apz - apz_prev))
        ofi_per_bar = ofi_per_bar + np.where(np.isfinite(bid_term), bid_term, 0.0) \
                                  - np.where(np.isfinite(ask_term), ask_term, 0.0)
    add("ofi_60s", _causal_roll_sum(ofi_per_bar, 60), _CLIP_FLOW)

    # ---------------------------------------------------------------------
    # Assemble, sanitize: nan_to_num after warmup so rows >= warmup are finite.
    # ---------------------------------------------------------------------
    F = np.stack(feats, axis=1).astype(np.float64)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    return F.astype(np.float32), names


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
