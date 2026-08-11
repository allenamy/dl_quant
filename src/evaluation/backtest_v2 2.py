"""Production-grade backtesting engine for quantile-based trading signals.

Simulates a single-asset long/short strategy on BTCUSDT perpetual:
- Opens positions based on q50 prediction vs threshold
- Uses q10/q90 spread for position sizing (wider spread = less confident = smaller size)
- Tracks P&L per trade, cumulative P&L, drawdown
- Accounts for: taker fees, slippage model

This is NOT a full order-book simulator -- it uses mid-price fills with
configurable slippage. Sufficient for mid-frequency (3-min) validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# 3-minute prediction: periods per year
PERIODS_PER_YEAR = 365.25 * 24 * 60 / 3.0  # 175_320


@dataclass
class BacktestResult:
    """Comprehensive, self-contained backtest result container.

    All P&L values are in the same unit as the input predictions/targets
    (typically normalized units or bps, depending on caller context).
    """

    # Summary metrics
    n_periods: int = 0
    n_trades: int = 0
    trade_rate: float = 0.0  # fraction of periods with active position

    # P&L
    gross_pnl_bps: float = 0.0
    total_cost_bps: float = 0.0
    net_pnl_bps: float = 0.0
    avg_pnl_per_trade_bps: float = 0.0

    # Risk metrics
    sharpe_annual: float = 0.0
    max_drawdown_bps: float = 0.0
    calmar_ratio: float = 0.0  # annual return / max drawdown
    win_rate: float = 0.0  # fraction of profitable periods with position
    profit_factor: float = 0.0  # sum(winning) / sum(losing)

    # Time-based arrays
    pnl_timeseries: np.ndarray = field(default_factory=lambda: np.array([]))
    drawdown_timeseries: np.ndarray = field(default_factory=lambda: np.array([]))
    position_timeseries: np.ndarray = field(default_factory=lambda: np.array([]))

    # Trade log
    trade_log: pd.DataFrame = field(default_factory=pd.DataFrame)

    def summary(self) -> str:
        """Pretty-print summary table."""
        lines = [
            "=" * 60,
            "BACKTEST RESULTS",
            "=" * 60,
            f"  Periods:            {self.n_periods}",
            f"  Trades:             {self.n_trades}",
            f"  Trade rate:         {self.trade_rate:.4f}",
            "-" * 60,
            f"  Gross P&L:          {self.gross_pnl_bps:.4f}",
            f"  Total cost:         {self.total_cost_bps:.4f}",
            f"  Net P&L:            {self.net_pnl_bps:.4f}",
            f"  Avg P&L/trade:      {self.avg_pnl_per_trade_bps:.4f}",
            "-" * 60,
            f"  Sharpe (annual):    {self.sharpe_annual:.4f}",
            f"  Max drawdown:       {self.max_drawdown_bps:.4f}",
            f"  Calmar ratio:       {self.calmar_ratio:.4f}",
            f"  Win rate:           {self.win_rate:.4f}",
            f"  Profit factor:      {self.profit_factor:.4f}",
            "=" * 60,
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict (for saving).

        Excludes large timeseries arrays and DataFrame; includes all scalar
        metrics.
        """
        return {
            "n_periods": int(self.n_periods),
            "n_trades": int(self.n_trades),
            "trade_rate": float(self.trade_rate),
            "gross_pnl_bps": float(self.gross_pnl_bps),
            "total_cost_bps": float(self.total_cost_bps),
            "net_pnl_bps": float(self.net_pnl_bps),
            "avg_pnl_per_trade_bps": float(self.avg_pnl_per_trade_bps),
            "sharpe_annual": float(self.sharpe_annual),
            "max_drawdown_bps": float(self.max_drawdown_bps),
            "calmar_ratio": float(self.calmar_ratio),
            "win_rate": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
        }


class BacktestEngine:
    """Event-driven backtester for quantile-based trading signals.

    Simulates a single-asset long/short strategy on BTCUSDT perpetual:
    - Opens positions based on q50 prediction vs threshold
    - Uses q10/q90 spread for position sizing (wider spread = less
      confident = smaller size)
    - Tracks P&L per trade, cumulative P&L, drawdown
    - Accounts for: taker fees, slippage model

    This is NOT a full order-book simulator -- it uses mid-price fills with
    configurable slippage. Sufficient for mid-frequency (3-min) validation.

    Parameters
    ----------
    fee_bps : float
        Round-trip taker fee in bps. Default 4.0 (Bybit/Binance: 0.02% per
        side = 4 bps round-trip).
    slippage_bps : float
        Estimated slippage per side in bps (already per-side, not
        round-trip). Default 1.0.
    max_position : float
        Max position size (normalized, 1.0 = full allocation).
    signal_threshold : float
        Minimum |q50| to trade (in the same unit as predictions).
    confidence_sizing : bool
        When True, position_size = clip(|q50| / (q90 - q10), 0, max_position).
        Wider quantile spread = less confidence = smaller position.
        When False, positions are binary (direction only, size = max_position).
    """

    def __init__(
        self,
        fee_bps: float = 4.0,
        slippage_bps: float = 1.0,
        max_position: float = 1.0,
        signal_threshold: float = 0.0,
        confidence_sizing: bool = True,
    ) -> None:
        if fee_bps < 0:
            raise ValueError(f"fee_bps must be >= 0, got {fee_bps}")
        if slippage_bps < 0:
            raise ValueError(f"slippage_bps must be >= 0, got {slippage_bps}")
        if max_position <= 0:
            raise ValueError(f"max_position must be > 0, got {max_position}")
        if signal_threshold < 0:
            raise ValueError(
                f"signal_threshold must be >= 0, got {signal_threshold}"
            )

        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.max_position = max_position
        self.signal_threshold = signal_threshold
        self.confidence_sizing = confidence_sizing
        # Total cost per side: fee is round-trip (divide by 2);
        # slippage is already per-side (no division).
        self._cost_per_side = fee_bps / 2.0 + slippage_bps

    def run(
        self,
        predictions: np.ndarray,
        targets: np.ndarray,
        mask: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        overlap_ratio: int = 1,
    ) -> BacktestResult:
        """Run backtest on a sequence of predictions vs realized returns.

        Parameters
        ----------
        predictions : (N, 3) array
            Quantile predictions [q10, q50, q90] per period.
        targets : (N,) array
            Realized returns per period.
        mask : (N,) array
            Boolean mask; True = valid observation.
        timestamps : (N,) array, optional
            Microsecond timestamps for the trade log.
        overlap_ratio : int
            Ratio of horizon to stride (e.g., horizon=180, stride=60 -> 3).
            When >1, each realized return is "shared" across overlap_ratio
            consecutive samples. Sharpe is corrected using Newey-West HAC
            and per-period PnL is divided by overlap_ratio to avoid
            triple-counting. Default 1 (non-overlapping labels).

        Returns
        -------
        BacktestResult
            Self-contained result with all metrics and timeseries.
        """
        predictions = np.asarray(predictions, dtype=np.float64)
        targets = np.asarray(targets, dtype=np.float64).ravel()
        mask = np.asarray(mask, dtype=bool).ravel()

        if predictions.ndim == 1:
            # Single column prediction -- treat as q50 with no spread info
            predictions = np.column_stack([
                predictions - 1.0,  # synthetic q10
                predictions,        # q50
                predictions + 1.0,  # synthetic q90
            ])

        if predictions.shape[0] != targets.shape[0]:
            raise ValueError(
                f"predictions ({predictions.shape[0]}) and targets "
                f"({targets.shape[0]}) must have same length"
            )
        if mask.shape[0] != targets.shape[0]:
            raise ValueError(
                f"mask ({mask.shape[0]}) and targets ({targets.shape[0]}) "
                f"must have same length"
            )

        # Apply mask: keep only valid observations
        valid_idx = np.where(mask)[0]
        n = len(valid_idx)

        if n == 0:
            return self._empty_result()

        q10 = predictions[valid_idx, 0]
        q50 = predictions[valid_idx, 1]
        q90 = predictions[valid_idx, 2]
        t = targets[valid_idx]
        ts = timestamps[valid_idx] if timestamps is not None else None

        # --- Compute positions ---
        position = self._compute_positions(q10, q50, q90)

        # --- Gross P&L: position * realized return ---
        gross_pnl = position * t

        # --- Transaction costs ---
        # Position change at each period (assume flat at start)
        position_change = np.empty_like(position)
        position_change[0] = position[0]
        position_change[1:] = position[1:] - position[:-1]
        # Cost = |position_change| * cost_per_side (half of round-trip per side)
        costs = np.abs(position_change) * self._cost_per_side

        # --- Net P&L ---
        # When overlap_ratio > 1 (e.g., stride=60, horizon=180 -> ratio=3),
        # each realized return is shared across overlap_ratio consecutive
        # windows. Dividing gross_pnl by overlap_ratio prevents triple-counting.
        if overlap_ratio > 1:
            gross_pnl = gross_pnl / float(overlap_ratio)
        net_pnl = gross_pnl - costs

        # --- Trade count ---
        trades_mask = position_change != 0
        n_trades = int(np.sum(trades_mask))
        trade_rate = float(np.sum(position != 0)) / n if n > 0 else 0.0

        # --- Aggregates ---
        gross_pnl_total = float(np.sum(gross_pnl))
        total_cost = float(np.sum(costs))
        net_pnl_total = float(np.sum(net_pnl))

        # --- Avg P&L per trade ---
        # A "trade" is a period with non-zero position
        active_periods = np.sum(position != 0)
        avg_pnl_per_trade = (
            net_pnl_total / active_periods if active_periods > 0 else 0.0
        )

        # --- Win rate (on periods with active position) ---
        active_mask = position != 0
        n_active = int(np.sum(active_mask))
        if n_active > 0:
            win_rate = float(np.mean(net_pnl[active_mask] > 0))
        else:
            win_rate = np.nan

        # --- Profit factor ---
        winning_sum = float(np.sum(net_pnl[net_pnl > 0]))
        losing_sum = float(np.abs(np.sum(net_pnl[net_pnl < 0])))
        if losing_sum > 0:
            profit_factor = winning_sum / losing_sum
        else:
            profit_factor = float("inf") if winning_sum > 0 else np.nan

        # --- Cumulative P&L and drawdown ---
        cumulative_pnl = np.cumsum(net_pnl)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = float(np.max(drawdown)) if n > 0 else 0.0

        # --- Sharpe ratio (annualized, HAC-corrected) ---
        # When overlap_ratio > 1, per-period PnL is autocorrelated (each
        # realized return is shared across overlap_ratio samples). Naive
        # Sharpe is inflated by approximately sqrt(overlap_ratio).
        # Newey-West HAC correction with lag = overlap_ratio - 1 gives
        # the correct standard error for autocorrelated samples.
        net_mean = np.mean(net_pnl)
        if n <= 1:
            sharpe_annual = np.nan
        else:
            net_std = np.std(net_pnl, ddof=1)
            if not np.isfinite(net_std) or net_std == 0:
                sharpe_annual = np.nan
            else:
                if overlap_ratio > 1:
                    # Newey-West: variance = γ_0 + 2*Σ_{l=1..L} (1 - l/(L+1)) * γ_l
                    L = overlap_ratio - 1
                    residuals = net_pnl - net_mean
                    var_nw = np.mean(residuals ** 2)
                    for lag in range(1, L + 1):
                        cov_l = np.mean(residuals[lag:] * residuals[:-lag])
                        weight = 1.0 - lag / (L + 1.0)
                        var_nw += 2.0 * weight * cov_l
                    var_nw = max(var_nw, 1e-20)
                    se_hac = float(np.sqrt(var_nw))
                    sharpe_annual = float(
                        (net_mean / se_hac) * np.sqrt(PERIODS_PER_YEAR / overlap_ratio)
                    )
                else:
                    sharpe_annual = float(
                        (net_mean / net_std) * np.sqrt(PERIODS_PER_YEAR)
                    )

        # --- Calmar ratio (annualized return / max drawdown) ---
        annual_return = net_mean * PERIODS_PER_YEAR
        if max_drawdown > 0:
            calmar_ratio = float(annual_return / max_drawdown)
        else:
            calmar_ratio = float("inf") if annual_return > 0 else np.nan

        # --- Trade log ---
        trade_log = self._build_trade_log(
            position, net_pnl, costs, q50, ts, valid_idx
        )

        return BacktestResult(
            n_periods=n,
            n_trades=n_trades,
            trade_rate=trade_rate,
            gross_pnl_bps=gross_pnl_total,
            total_cost_bps=total_cost,
            net_pnl_bps=net_pnl_total,
            avg_pnl_per_trade_bps=avg_pnl_per_trade,
            sharpe_annual=sharpe_annual,
            max_drawdown_bps=max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            pnl_timeseries=cumulative_pnl,
            drawdown_timeseries=drawdown,
            position_timeseries=position,
            trade_log=trade_log,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_positions(
        self,
        q10: np.ndarray,
        q50: np.ndarray,
        q90: np.ndarray,
    ) -> np.ndarray:
        """Compute position array from quantile predictions.

        Entry signal:
          Long  if q50 > +threshold
          Short if q50 < -threshold
          Flat  otherwise

        Position sizing (when confidence_sizing=True):
          size = clip(|q50| / (q90 - q10), 0, max_position)
          Wider spread -> less confidence -> smaller position

        When confidence_sizing=False:
          size = max_position (binary direction)
        """
        n = len(q50)
        position = np.zeros(n, dtype=np.float64)

        # Direction: +1 long, -1 short, 0 flat
        direction = np.where(
            q50 > self.signal_threshold, 1.0,
            np.where(q50 < -self.signal_threshold, -1.0, 0.0)
        )

        if self.confidence_sizing:
            # Quantile spread (ensure > 0 to avoid division by zero)
            spread = q90 - q10
            spread = np.maximum(spread, 0.01)  # minimum spread of 0.01 in normalized units
            # Confidence: ratio of signal strength to uncertainty
            size = np.abs(q50) / spread
            size = np.clip(size, 0.0, self.max_position)
            position = direction * size
        else:
            position = direction * self.max_position

        return position

    def _build_trade_log(
        self,
        position: np.ndarray,
        net_pnl: np.ndarray,
        costs: np.ndarray,
        q50: np.ndarray,
        timestamps: Optional[np.ndarray],
        valid_idx: np.ndarray,
    ) -> pd.DataFrame:
        """Build a DataFrame of trade events."""
        n = len(position)
        records: List[Dict[str, Any]] = []

        for i in range(n):
            if position[i] == 0.0:
                continue
            record: Dict[str, Any] = {
                "period_idx": int(valid_idx[i]),
                "direction": "long" if position[i] > 0 else "short",
                "size": float(abs(position[i])),
                "signal_q50": float(q50[i]),
                "net_pnl": float(net_pnl[i]),
                "cost": float(costs[i]),
            }
            if timestamps is not None:
                record["timestamp"] = int(timestamps[i])
            records.append(record)

        if records:
            return pd.DataFrame(records)
        return pd.DataFrame(
            columns=["period_idx", "direction", "size",
                      "signal_q50", "net_pnl", "cost"]
        )

    @staticmethod
    def _empty_result() -> BacktestResult:
        """Return a result for empty/invalid input."""
        return BacktestResult()
