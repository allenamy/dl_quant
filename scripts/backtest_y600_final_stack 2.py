"""Backtest y_600 final_stack predictions — cost-aware Sharpe + holding strategy.

Loads test predictions from experiments/y600_push/final_stack/fold_{0,1,2}/,
pools across folds, and runs:
  1. Always-trade baseline (every prediction triggers a position)
  2. Confidence-gated (|pred| > tau)
  3. Holding strategy (EMA smooth + hysteresis + min_hold)

Reports: gross/net PnL, Sharpe, trade count, max DD.
Trading cost model: 2 bps per trade round-trip (Binance futures taker-ish).
"""
from __future__ import annotations

import json
import pathlib
import numpy as np
from scipy.stats import pearsonr, spearmanr


COST_BPS_PER_TRADE = 2.0     # round-trip fee + slippage (bps)
HORIZON_SEC = 600
SAMPLES_PER_DAY = 144         # if stride=600 effective (clean)


def load_preds():
    preds, ys, ts = [], [], []
    for f in range(3):
        p = pathlib.Path(f"experiments/y600_push/final_stack/fold_{f}/test_preds.npz")
        if not p.exists():
            continue
        d = np.load(p)
        yp_all = d["predictions"]
        yp = yp_all[:, 1] if yp_all.ndim == 2 else yp_all
        y = d["targets"].squeeze()
        m = d["mask"].astype(bool).squeeze()
        t = d["timestamps"].astype(np.int64)
        preds.append(yp[m]); ys.append(y[m]); ts.append(t[m])
    return np.concatenate(preds), np.concatenate(ys), np.concatenate(ts)


def simple_backtest(yp, y, gate=None, label=""):
    """Position sign = sign(yp). Optional |yp| > gate filter."""
    if gate is not None:
        trade = np.abs(yp) > gate
    else:
        trade = np.ones_like(yp, dtype=bool)
    pos = np.sign(yp) * trade
    gross_bps = pos * y                        # y already scaled by sigma ~10 bps
    sigma_y = 9.5
    gross_bps = gross_bps * sigma_y            # now in bps
    trade_edges = (np.diff(np.concatenate([[0], pos])) != 0).astype(np.float32)
    n_trades = int(trade_edges.sum())
    cost_bps = trade_edges * COST_BPS_PER_TRADE
    net_bps = gross_bps - cost_bps
    trades_per_year = n_trades / len(yp) * SAMPLES_PER_DAY * 365
    mean_net = float(net_bps.mean())
    std_net = float(net_bps.std())
    sharpe_ann = mean_net / (std_net + 1e-9) * np.sqrt(SAMPLES_PER_DAY * 365)
    eq = np.cumsum(net_bps)
    mdd = float(np.min(eq - np.maximum.accumulate(eq)))
    win_rate = float((net_bps > 0).mean())
    return {
        "label": label,
        "gate": gate,
        "n_samples": int(len(yp)),
        "trade_rate": float(trade.mean()),
        "n_trades": n_trades,
        "trades_per_year": trades_per_year,
        "gross_pnl_bps_total": float(gross_bps.sum()),
        "net_pnl_bps_total": float(net_bps.sum()),
        "mean_net_bps": mean_net,
        "sharpe_ann": float(sharpe_ann),
        "max_dd_bps": mdd,
        "win_rate": win_rate,
    }


def holding_strategy_backtest(yp, y, ema_k=5, tau_entry=0.1, tau_exit=0.05, min_hold=10):
    """EMA signal + hysteresis + min holding."""
    alpha = 2.0 / (ema_k + 1)
    smoothed = np.zeros_like(yp)
    smoothed[0] = yp[0]
    for i in range(1, len(yp)):
        smoothed[i] = alpha * yp[i] + (1 - alpha) * smoothed[i-1]
    pos = np.zeros_like(yp)
    state = 0
    hold_counter = 0
    for i, s in enumerate(smoothed):
        if state == 0:
            if s > tau_entry: state, hold_counter = +1, 0
            elif s < -tau_entry: state, hold_counter = -1, 0
        elif state == +1:
            hold_counter += 1
            if s < tau_exit and hold_counter >= min_hold: state = 0
        elif state == -1:
            hold_counter += 1
            if s > -tau_exit and hold_counter >= min_hold: state = 0
        pos[i] = state
    sigma_y = 9.5
    gross_bps = pos * y * sigma_y
    trade_edges = (np.diff(np.concatenate([[0], pos])) != 0).astype(np.float32)
    n_trades = int(trade_edges.sum())
    cost_bps = trade_edges * COST_BPS_PER_TRADE
    net_bps = gross_bps - cost_bps
    mean_net = float(net_bps.mean())
    std_net = float(net_bps.std())
    sharpe_ann = mean_net / (std_net + 1e-9) * np.sqrt(SAMPLES_PER_DAY * 365)
    eq = np.cumsum(net_bps)
    mdd = float(np.min(eq - np.maximum.accumulate(eq)))
    return {
        "label": f"holding(ema={ema_k},in={tau_entry},out={tau_exit},hold={min_hold})",
        "trade_rate": float((pos != 0).mean()),
        "n_trades": n_trades,
        "trades_per_year": n_trades / len(yp) * SAMPLES_PER_DAY * 365,
        "gross_pnl_bps_total": float(gross_bps.sum()),
        "net_pnl_bps_total": float(net_bps.sum()),
        "mean_net_bps": mean_net,
        "sharpe_ann": float(sharpe_ann),
        "max_dd_bps": mdd,
        "win_rate": float((net_bps > 0).mean()),
    }


def main():
    yp, y, ts = load_preds()
    print(f"Loaded {len(yp)} samples across 3 folds")
    print(f"yp std={yp.std():.4f}, y std={y.std():.4f} (both z-scored)")
    print(f"pred range: {yp.min():.3f}..{yp.max():.3f}")

    # IC (sanity check)
    p, s = pearsonr(yp, y)[0], spearmanr(yp, y)[0]
    print(f"\nIC: P={p:+.4f} S={s:+.4f} DA={(np.sign(yp)==np.sign(y)).mean():.4f}")

    # Clean (stride 10)
    ix = np.arange(0, len(yp), 10)
    pc, sc = pearsonr(yp[ix], y[ix])[0], spearmanr(yp[ix], y[ix])[0]
    print(f"CLEAN (N={len(ix)}): P={pc:+.4f} S={sc:+.4f} DA={(np.sign(yp[ix])==np.sign(y[ix])).mean():.4f}")

    results = []
    # 1) Always-trade
    r = simple_backtest(yp, y, gate=None, label="always_trade")
    results.append(r)
    # 2) Confidence gating
    for tau in [0.1, 0.2, 0.3, 0.5]:
        r = simple_backtest(yp, y, gate=tau, label=f"gate_tau={tau}")
        results.append(r)
    # 3) Holding strategy
    for ema_k in [5, 10, 20]:
        for min_hold in [5, 10, 30]:
            r = holding_strategy_backtest(yp, y, ema_k=ema_k, min_hold=min_hold)
            results.append(r)

    # Print + save
    print(f"\n{'Strategy':<45} {'Trades/yr':>10} {'Rate':>6} {'NetPnL(bps)':>12} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>8}")
    print("-" * 110)
    for r in results:
        print(f"{r['label']:<45} {r.get('trades_per_year',0):>10.0f} {r.get('trade_rate',1):>6.2f} "
              f"{r['net_pnl_bps_total']:>12.1f} {r['sharpe_ann']:>8.2f} {r['max_dd_bps']:>10.1f} {r['win_rate']:>8.4f}")

    out = pathlib.Path("experiments/eval_y600_final_stack/backtest_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
