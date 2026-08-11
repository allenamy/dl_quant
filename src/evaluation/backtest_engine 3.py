"""Phase C backtest engine — production-grade realism for V4+XGB ensemble.

Design principles (see docs/superpowers/specs/2026-04-18-phase-c-backtest-design.md):
  - No look-ahead: τ*, weights calibrated only on past data
  - Realistic costs: maker/taker fees + orderbook-depth slippage where available
  - Latency: signal at t applied at t + latency_ms
  - Proper crypto annualization: √(31,536,000 / avg_interval_sec)
  - Walk-forward τ*: each fold's test uses its own prior-data-calibrated threshold

Naming: DL model referred to as "V4". Backtest engine has no version suffix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------

@dataclass
class CostModel:
    """Transaction cost model for Binance Futures BTCUSDT perpetual.

    All rates in bps (basis points, 1 bps = 0.01% = 1e-4 fractional).

    Default rates reflect VERIFIED Binance Futures regular-user schedule
    (2026-04, 30d vol < $5M, no BNB discount):
        maker = 0.0200%  = 2.0 bps
        taker = 0.0500%  = 5.0 bps

    With BNB 9折 (10% discount):
        maker = 0.0180%  = 1.8 bps
        taker = 0.0450%  = 4.5 bps
    """
    maker_fee_bps: float = 2.0          # 0.0200%
    taker_fee_bps: float = 5.0          # 0.0500% — VERIFIED, was 4.0 (too optimistic)
    slippage_bps: float = 1.5           # Conservative flat slippage (bps)
    maker_fill_prob: float = 0.60       # P(limit order fills within t_cancel)
    t_cancel_sec: int = 60              # Seconds before canceling unfilled limit
    funding_rate_bps_per_day: float = 0.3  # ~0.03% / 8h × 3 = ~0.09%/day flat
    # TODO (future): order-book depth slippage using X_raw

    @classmethod
    def binance_regular(cls) -> "CostModel":
        """Standard Binance Futures regular user — no BNB discount."""
        return cls(maker_fee_bps=2.0, taker_fee_bps=5.0)

    @classmethod
    def binance_bnb_discount(cls) -> "CostModel":
        """Binance Futures with 10% BNB holding discount."""
        return cls(maker_fee_bps=1.8, taker_fee_bps=4.5)

    def roundtrip_cost_bps(self, is_maker: bool = True) -> float:
        """Full enter+exit cost in bps."""
        fee = self.maker_fee_bps if is_maker else self.taker_fee_bps
        return 2 * fee + 2 * self.slippage_bps

    def expected_cost_bps(self) -> float:
        """E[cost] under maker-first, taker-fallback strategy."""
        maker_total = 2 * self.maker_fee_bps + 2 * self.slippage_bps
        taker_total = 2 * self.taker_fee_bps + 2 * self.slippage_bps
        return self.maker_fill_prob * maker_total + (1 - self.maker_fill_prob) * taker_total


# ---------------------------------------------------------------------------
# Execution model: signal → position → P&L
# ---------------------------------------------------------------------------

@dataclass
class ExecutionConfig:
    """How to translate signal into positions.

    position_mode:
      - "always_on":            position[t] = sign(signal[t])
      - "confidence_gated":     only trade when confidence[t] >= tau
      - "holding_strategy":     EMA-smooth signal + hysteresis entry/exit + min hold
    """
    signal_delay_sec: int = 1
    position_mode: str = "confidence_gated"
    tau: float = 0.0                        # Gate threshold (confidence)
    max_position: float = 1.0

    # --- holding_strategy params ------------------------------------
    ema_k: int = 5                          # EMA smoothing window on signal
    tau_entry: float = 0.1                  # Confidence required to open position
    tau_exit: float = 0.03                  # Confidence below = go flat
    min_hold_samples: int = 3               # Min samples to hold before allowing flip
    max_hold_samples: int = 300             # Force exit after N samples


@dataclass
class BacktestResult:
    """Container for one backtest run."""
    pnl_per_trade_bps: np.ndarray       # (N,) per-sample net P&L in bps
    position: np.ndarray                # (N,) position at each sample (-1 to +1)
    trade_flag: np.ndarray              # (N,) 1 if traded, 0 if skipped
    gross_pnl_bps: float                # sum of gross returns when traded
    cost_bps: float                     # sum of costs
    net_pnl_bps: float                  # = gross - cost
    trade_rate: float                   # frac of samples traded
    sharpe_ann: float                   # annualized Sharpe (crypto 24/7)
    sortino_ann: float                  # annualized Sortino
    max_dd_bps: float                   # max drawdown
    calmar: float                       # net_pnl / |max_dd|
    cvar_95: float                      # 95% CVaR of per-trade P&L
    win_rate: float                     # frac of winning trades
    turnover: float                     # avg |Δposition| per sample
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core backtest
# ---------------------------------------------------------------------------

def _compute_position(
    signal: np.ndarray,
    mask: np.ndarray,
    confidence: Optional[np.ndarray],
    exec_cfg: ExecutionConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Convert signal → position, respecting τ-gating and masks.

    Returns (position, trade_flag) both (N,).
    """
    n = len(signal)
    position = np.zeros(n, dtype=np.float32)
    trade_flag = np.zeros(n, dtype=np.int8)

    if exec_cfg.position_mode == "always_on":
        sign = np.sign(signal)
        position = np.clip(sign, -exec_cfg.max_position, exec_cfg.max_position)
        trade_flag = (mask & (signal != 0)).astype(np.int8)
    elif exec_cfg.position_mode == "confidence_gated":
        assert confidence is not None, "confidence_gated mode requires confidence array"
        take = mask & (confidence >= exec_cfg.tau)
        sign = np.sign(signal)
        position[take] = np.clip(sign[take], -exec_cfg.max_position, exec_cfg.max_position)
        trade_flag[take] = 1
    elif exec_cfg.position_mode == "holding_strategy":
        assert confidence is not None, "holding_strategy requires confidence"
        position, trade_flag = _holding_strategy_position(
            signal=signal, mask=mask, confidence=confidence,
            ema_k=exec_cfg.ema_k,
            tau_entry=exec_cfg.tau_entry,
            tau_exit=exec_cfg.tau_exit,
            min_hold=exec_cfg.min_hold_samples,
            max_hold=exec_cfg.max_hold_samples,
            max_position=exec_cfg.max_position,
        )
    else:
        raise ValueError(f"Unknown position_mode: {exec_cfg.position_mode}")
    return position, trade_flag


def _holding_strategy_position(
    signal: np.ndarray,
    mask: np.ndarray,
    confidence: np.ndarray,
    ema_k: int,
    tau_entry: float,
    tau_exit: float,
    min_hold: int,
    max_hold: int,
    max_position: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """EMA-smooth signal + hysteresis holding strategy.

    Rules:
      1. When flat (position = 0):
         - Enter LONG if smoothed_signal > 0 AND confidence >= tau_entry
         - Enter SHORT if smoothed_signal < 0 AND confidence >= tau_entry
      2. When in position (long or short):
         - HOLD if |time_held| < min_hold samples (regardless)
         - Allow exit/flip only after min_hold elapses
         - EXIT to flat if confidence < tau_exit
         - FLIP if smoothed_signal reverses AND confidence >= tau_entry
         - FORCE EXIT if time_held >= max_hold
      3. trade_flag[t] = 1 whenever position changes
    """
    n = len(signal)
    position = np.zeros(n, dtype=np.float32)
    trade_flag = np.zeros(n, dtype=np.int8)

    # EMA-smooth signal
    alpha = 2.0 / (ema_k + 1)
    smoothed = np.zeros(n)
    smoothed[0] = signal[0] if mask[0] else 0.0
    for i in range(1, n):
        if mask[i]:
            smoothed[i] = alpha * signal[i] + (1 - alpha) * smoothed[i - 1]
        else:
            smoothed[i] = smoothed[i - 1]

    entry_idx = -max_hold  # allow immediate entry
    current_pos = 0.0

    for i in range(n):
        if not mask[i]:
            # Propagate previous position
            position[i] = current_pos
            continue

        time_held = i - entry_idx
        sig_sign = np.sign(smoothed[i])
        conf_ok_entry = confidence[i] >= tau_entry
        conf_ok_hold = confidence[i] >= tau_exit

        if current_pos == 0.0:
            # Flat → check entry
            if conf_ok_entry and sig_sign != 0:
                current_pos = float(np.clip(sig_sign, -max_position, max_position))
                entry_idx = i
                trade_flag[i] = 1
        else:
            # In position
            if time_held >= max_hold:
                # Force exit
                current_pos = 0.0
                trade_flag[i] = 1
            elif time_held < min_hold:
                # Must hold, no action
                pass
            else:
                # Can exit/flip
                if not conf_ok_hold:
                    # Weak signal → exit
                    current_pos = 0.0
                    trade_flag[i] = 1
                elif sig_sign != 0 and sig_sign != np.sign(current_pos) and conf_ok_entry:
                    # Signal reversal → flip (counts as 2 position-change units)
                    current_pos = float(np.clip(sig_sign, -max_position, max_position))
                    entry_idx = i
                    trade_flag[i] = 1
                # else: same-side signal, keep position

        position[i] = current_pos

    return position, trade_flag


def _per_sample_pnl(
    position: np.ndarray,
    returns_bps: np.ndarray,
    trade_flag: np.ndarray,
    cost_model: CostModel,
    signal_delay_steps: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute per-sample net P&L.

    Logic:
      - position[t] decided at t but applied from t+delay (no lookahead)
      - pnl_gross[t] = position[t-delay] × returns[t]
      - cost[t] = expected roundtrip cost × |trade_flag[t] - trade_flag[t-1]|
        Approximation: charge cost on every position *change*, not just open/close.
    """
    # Shift position by delay (lookahead-free)
    pos_delayed = np.zeros_like(position)
    if signal_delay_steps > 0:
        pos_delayed[signal_delay_steps:] = position[:-signal_delay_steps]
    else:
        pos_delayed = position

    gross_bps = pos_delayed * returns_bps

    # Cost: charge on position-change magnitude
    # Rational: each position change requires offsetting trade cost
    position_change = np.abs(np.diff(pos_delayed, prepend=0))
    cost_per_round_trip = cost_model.expected_cost_bps()
    # position change of 1 = full roundtrip. 2 = reversal (costs 2 roundtrips).
    cost_bps = position_change * (cost_per_round_trip / 2.0)  # Divide by 2 because each "change" is only one side

    net_bps = gross_bps - cost_bps
    return net_bps, cost_bps


def run_backtest(
    *,
    signal: np.ndarray,               # (N,) prediction scores (z-score or raw)
    returns_bps: np.ndarray,          # (N,) actual per-sample returns in bps
    mask: np.ndarray,                 # (N,) validity mask (bool)
    confidence: Optional[np.ndarray] = None,  # (N,) confidence (|q50|/IQR or abs-signal)
    sample_interval_sec: int = 60,    # avg gap between samples
    cost_model: Optional[CostModel] = None,
    exec_cfg: Optional[ExecutionConfig] = None,
) -> BacktestResult:
    """Run backtest given predictions + realized returns.

    Parameters
    ----------
    signal : (N,) prediction series (signed).
    returns_bps : (N,) realized log returns at each sample, in BPS.
    mask : (N,) 1 where sample is valid (not NaN/missing).
    confidence : (N,) optional, used for τ-gating. If None, |signal| is used.
    sample_interval_sec : average time between samples. Affects annualization.
    """
    cost_model = cost_model or CostModel()
    exec_cfg = exec_cfg or ExecutionConfig()

    n = len(signal)
    assert len(returns_bps) == n and len(mask) == n, "size mismatch"
    mask = mask.astype(bool)

    if confidence is None:
        confidence = np.abs(signal)

    # Handle NaN/inf
    signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
    returns_bps = np.nan_to_num(returns_bps, nan=0.0, posinf=0.0, neginf=0.0)
    confidence = np.nan_to_num(confidence, nan=0.0, posinf=0.0, neginf=0.0)

    # Position sizing
    position, trade_flag = _compute_position(signal, mask, confidence, exec_cfg)

    # Per-sample P&L (with signal delay)
    signal_delay_steps = max(1, int(round(exec_cfg.signal_delay_sec / sample_interval_sec)))
    net_bps, cost_bps = _per_sample_pnl(
        position, returns_bps, trade_flag, cost_model, signal_delay_steps
    )

    # Funding: charge for held positions (applied smoothly per-sample)
    funding_per_sample = (
        cost_model.funding_rate_bps_per_day * sample_interval_sec / 86400.0
    )
    # Take absolute position because funding applies to long AND short (longs pay
    # when funding >0; shorts receive; for a neutral average we assume funding
    # is a drag on both sides — simplification)
    net_bps = net_bps - np.abs(position) * funding_per_sample

    gross_bps = np.sum(position * returns_bps * mask)
    total_cost = np.sum(cost_bps * mask) + np.sum(np.abs(position) * funding_per_sample * mask)
    total_net = np.sum(net_bps * mask)
    trade_rate = float(np.mean(trade_flag))

    # Sharpe (HAC Newey-West style with crypto 24/7 annualization)
    net_series = net_bps[mask]
    sharpe = _sharpe_ann(net_series, sample_interval_sec, lags=5)
    sortino = _sortino_ann(net_series, sample_interval_sec)

    # Drawdown + Calmar
    equity = np.cumsum(net_bps * mask)
    peak = np.maximum.accumulate(equity) if len(equity) > 0 else equity
    dd = equity - peak
    max_dd = float(dd.min()) if len(dd) > 0 else 0.0
    calmar = total_net / abs(max_dd) if max_dd < 0 else float("inf")

    # CVaR-95% of per-trade P&L
    traded = net_bps[trade_flag.astype(bool)]
    if len(traded) > 0:
        cvar_95 = float(np.percentile(traded, 5))  # 5th percentile = 95% CVaR on loss side
        win_rate = float((traded > 0).mean())
    else:
        cvar_95 = 0.0
        win_rate = 0.0

    # Turnover: avg |Δposition|
    turnover = float(np.mean(np.abs(np.diff(position, prepend=0))))

    return BacktestResult(
        pnl_per_trade_bps=net_bps,
        position=position,
        trade_flag=trade_flag,
        gross_pnl_bps=float(gross_bps),
        cost_bps=float(total_cost),
        net_pnl_bps=float(total_net),
        trade_rate=trade_rate,
        sharpe_ann=sharpe,
        sortino_ann=sortino,
        max_dd_bps=max_dd,
        calmar=calmar,
        cvar_95=cvar_95,
        win_rate=win_rate,
        turnover=turnover,
        metadata={
            "sample_interval_sec": sample_interval_sec,
            "signal_delay_steps": signal_delay_steps,
            "cost_model": cost_model.__dict__,
            "exec_cfg": exec_cfg.__dict__,
        },
    )


# ---------------------------------------------------------------------------
# Sharpe / Sortino — correct crypto annualization
# ---------------------------------------------------------------------------

def _sharpe_ann(net_series: np.ndarray, sample_interval_sec: int, lags: int = 5) -> float:
    """Annualized Sharpe with HAC (Newey-West) correction.

    Crypto: 24/7 trading. Samples/year = 31,536,000 / sample_interval_sec.
    """
    r = net_series[np.isfinite(net_series)]
    if len(r) < 30 or r.std() < 1e-12:
        return float("nan")

    mean_r = r.mean()
    gamma0 = np.var(r)
    hac_var = gamma0
    max_k = min(lags, len(r) // 4)
    for k in range(1, max_k + 1):
        w = 1 - k / (lags + 1)
        gk = ((r[:-k] - mean_r) * (r[k:] - mean_r)).mean()
        hac_var += 2 * w * gk
    hac_var = max(hac_var, gamma0 * 0.1)

    samples_per_year = 31_536_000 / sample_interval_sec
    ann_factor = np.sqrt(samples_per_year)
    return float(mean_r / np.sqrt(hac_var) * ann_factor)


def _sortino_ann(net_series: np.ndarray, sample_interval_sec: int) -> float:
    """Sortino (downside deviation only)."""
    r = net_series[np.isfinite(net_series)]
    if len(r) < 30:
        return float("nan")
    mean_r = r.mean()
    downside = r[r < 0]
    if len(downside) == 0 or downside.std() < 1e-12:
        return float("inf") if mean_r > 0 else float("nan")
    downside_std = downside.std()
    samples_per_year = 31_536_000 / sample_interval_sec
    ann_factor = np.sqrt(samples_per_year)
    return float(mean_r / downside_std * ann_factor)


# ---------------------------------------------------------------------------
# τ* calibration (walk-forward)
# ---------------------------------------------------------------------------

def calibrate_tau_on_val(
    val_signal: np.ndarray,
    val_returns_bps: np.ndarray,
    val_mask: np.ndarray,
    val_confidence: Optional[np.ndarray] = None,
    sample_interval_sec: int = 60,
    tau_candidates: Optional[np.ndarray] = None,
    cost_model: Optional[CostModel] = None,
    metric: str = "sharpe_ann",
) -> Tuple[float, List[Dict]]:
    """Sweep τ on validation set, pick argmax of metric. Returns (τ*, sweep_results).

    NOTE: Never call this with test data — would leak future into signal.
    """
    if val_confidence is None:
        val_confidence = np.abs(val_signal)

    if tau_candidates is None:
        # 11 quantiles of the confidence distribution, plus τ=0 (always trade)
        valid_conf = val_confidence[val_mask & np.isfinite(val_confidence)]
        if len(valid_conf) < 50:
            return 0.0, []
        qs = np.linspace(0, 0.95, 11)
        tau_candidates = np.array([0.0] + list(np.quantile(valid_conf, qs)))

    cost_model = cost_model or CostModel()
    sweep = []
    for tau in tau_candidates:
        exec_cfg = ExecutionConfig(position_mode="confidence_gated", tau=float(tau))
        r = run_backtest(
            signal=val_signal, returns_bps=val_returns_bps, mask=val_mask,
            confidence=val_confidence, sample_interval_sec=sample_interval_sec,
            cost_model=cost_model, exec_cfg=exec_cfg,
        )
        sweep.append({
            "tau": float(tau),
            "trade_rate": r.trade_rate,
            "sharpe_ann": r.sharpe_ann,
            "sortino_ann": r.sortino_ann,
            "net_pnl_bps": r.net_pnl_bps,
            "max_dd_bps": r.max_dd_bps,
            "win_rate": r.win_rate,
        })

    # Pick τ* by metric (default sharpe_ann)
    finite_rows = [s for s in sweep if np.isfinite(s[metric])]
    if not finite_rows:
        return 0.0, sweep
    best = max(finite_rows, key=lambda s: s[metric])
    return float(best["tau"]), sweep


# ---------------------------------------------------------------------------
# Block bootstrap for confidence intervals
# ---------------------------------------------------------------------------

def block_bootstrap_metrics(
    net_series: np.ndarray,
    mask: np.ndarray,
    sample_interval_sec: int = 60,
    block_len: int = 60,
    n_resample: int = 1000,
    seed: int = 42,
) -> Dict[str, Tuple[float, float, float]]:
    """Block bootstrap 95% CI on Sharpe, Max DD, Net PnL.

    Returns dict keyed by metric name with (mean, low_95, high_95).
    """
    rng = np.random.RandomState(seed)
    active = net_series[mask]
    if len(active) < block_len * 2:
        return {}

    n_blocks = len(active) // block_len
    sharpes, dds, pnls = [], [], []

    for _ in range(n_resample):
        start_idx = rng.randint(0, n_blocks, size=n_blocks)
        blocks = [active[s * block_len:(s + 1) * block_len] for s in start_idx]
        sample = np.concatenate(blocks)

        # Sharpe
        s = _sharpe_ann(sample, sample_interval_sec, lags=5)
        if np.isfinite(s): sharpes.append(s)

        # Max DD
        eq = np.cumsum(sample)
        peak = np.maximum.accumulate(eq)
        dd = float((eq - peak).min())
        dds.append(dd)

        # Net PnL
        pnls.append(float(sample.sum()))

    def ci(arr: List[float]) -> Tuple[float, float, float]:
        if not arr:
            return (float("nan"), float("nan"), float("nan"))
        a = np.array(arr)
        return (float(a.mean()), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))

    return {
        "sharpe_ann": ci(sharpes),
        "max_dd_bps": ci(dds),
        "net_pnl_bps": ci(pnls),
    }
