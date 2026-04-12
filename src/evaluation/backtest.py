"""Simple PnL backtest for LOB Transformer V2 signals."""

import numpy as np


def backtest_signal(
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    fee_bps: float = 4.0,
    threshold_bps: float = 2.0,
    position_sizing: str = "binary",
) -> dict:
    """Run a backtest of a prediction signal against realised returns.

    Parameters
    ----------
    pred : (N,) predicted returns (in the same unit as target, e.g. bps).
    target : (N,) realised returns.
    mask : (N,) boolean; True = valid observation.
    fee_bps : round-trip fee in bps (half charged per side per trade).
    threshold_bps : minimum absolute prediction to trigger a position.
    position_sizing : 'binary' or 'proportional'.

    Returns
    -------
    dict with backtest summary statistics.
    """
    pred = np.asarray(pred, dtype=np.float64).ravel()
    target = np.asarray(target, dtype=np.float64).ravel()
    mask = np.asarray(mask, dtype=bool).ravel()

    p = pred[mask]
    t = target[mask]
    n = len(p)

    result: dict = {"n_periods": n}

    if n == 0:
        for key in [
            "n_trades", "trade_rate", "gross_pnl_bps", "total_cost_bps",
            "net_pnl_bps", "sharpe_annual", "max_drawdown_bps",
            "win_rate", "avg_pnl_per_trade_bps",
        ]:
            result[key] = np.nan
        return result

    # --- Position sizing ---
    if position_sizing == "binary":
        position = np.where(p > threshold_bps, 1.0,
                            np.where(p < -threshold_bps, -1.0, 0.0))
    elif position_sizing == "proportional":
        position = np.clip(p / threshold_bps, -1.0, 1.0)
        position[np.abs(p) < threshold_bps] = 0.0
    else:
        raise ValueError(
            f"Unknown position_sizing: {position_sizing!r}. "
            "Use 'binary' or 'proportional'."
        )

    # --- PnL ---
    gross_pnl = position * t  # per-period gross pnl

    # --- Transaction costs ---
    # position_change at period i: position[i] - position[i-1]
    # First period: assume flat coming in, so change = position[0]
    position_change = np.empty_like(position)
    position_change[0] = position[0]
    position_change[1:] = position[1:] - position[:-1]

    costs = np.abs(position_change) * (fee_bps / 2.0)  # half fee per side

    net_pnl = gross_pnl - costs

    # --- Trade count (a trade occurs when position changes) ---
    trades = position_change != 0
    n_trades = int(np.sum(trades))
    trade_rate = float(n_trades / n) if n > 0 else 0.0

    # --- Aggregates ---
    gross_pnl_total = float(np.sum(gross_pnl))
    total_cost = float(np.sum(costs))
    net_pnl_total = float(np.sum(net_pnl))

    # --- Sharpe ratio (annualised) ---
    # 3-minute periods; periods per year = 365.25 * 24 * 60 / 3
    periods_per_year = 365.25 * 24 * 60 / 3.0
    net_mean = np.mean(net_pnl)
    net_std = np.std(net_pnl, ddof=1) if n > 1 else np.nan
    if net_std is np.nan or net_std == 0:
        sharpe_annual = np.nan
    else:
        sharpe_annual = float((net_mean / net_std) * np.sqrt(periods_per_year))

    # --- Max drawdown ---
    cumulative = np.cumsum(net_pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_drawdown = float(np.max(drawdown)) if n > 0 else 0.0

    # --- Win rate (on periods with non-zero position) ---
    active = position != 0
    n_active = int(np.sum(active))
    if n_active > 0:
        win_rate = float(np.mean(net_pnl[active] > 0))
    else:
        win_rate = np.nan

    # --- Avg PnL per trade ---
    if n_trades > 0:
        avg_pnl_per_trade = net_pnl_total / n_trades
    else:
        avg_pnl_per_trade = np.nan

    result.update({
        "n_trades": n_trades,
        "trade_rate": trade_rate,
        "gross_pnl_bps": gross_pnl_total,
        "total_cost_bps": total_cost,
        "net_pnl_bps": net_pnl_total,
        "sharpe_annual": sharpe_annual,
        "max_drawdown_bps": max_drawdown,
        "win_rate": win_rate,
        "avg_pnl_per_trade_bps": avg_pnl_per_trade,
    })

    return result
