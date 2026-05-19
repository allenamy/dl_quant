"""Confident Sticky Hold (CSH) backtest with parameter sweep.

Strategy:
  state ∈ {flat=0, long=+1, short=-1}
  Per decision bar:
    conf_long  = (q50_live ≥ T_open) AND (q10_live ≥ -C_band)
    conf_short = (q50_live ≤ -T_open) AND (q90_live ≤ +C_band)
    weak_long  = q50_live > T_close   (asymmetric: easier to stay than to enter)
    weak_short = q50_live < -T_close

  Transitions:
    flat  + conf_long       → open long          [1 leg fee]
    flat  + conf_short      → open short         [1 leg fee]
    long  + conf_short_flip → flip to short      [2 legs fee]    (T_flip > T_open)
    long  + NOT weak_long   → close to flat      [1 leg fee]
    long  + weak_long       → hold               [0 fee]
    long  + held > max_hold → force close        [1 leg fee]
    (mirror for short)

PnL semantics:
  Bars subsampled to every K (default 4 = 12-min decision grid, non-overlapping
  10-min labels with 2-min gap).
  At decision time t: state[t] × y_true_bps[t] = realized PnL over next 10 min.
  Fees deducted on each transition leg.

Risk control:
  - max_hold:        decision bars  (force close)
  - max_streak_loss: N consecutive losing trades → cooldown C bars flat

Reports per (T_open, T_close, C_band, T_flip, fee_round_trip):
  - net_pnl_bps_total
  - annualized_return_pct  (assuming continuous compounding)
  - sharpe_annualized      (sqrt(decisions_per_year) × mean/std)
  - max_drawdown_bps
  - win_rate
  - trade_count
  - time_in_market_pct
"""
import numpy as np
import pandas as pd
from pathlib import Path
import itertools
import sys

CSV = Path("predictions_all_folds.csv")
SUBSAMPLE_K = 4              # every 4 bars = 12-min decision grid
MIN_PER_DECISION = 12        # 12 min per slot
DECISIONS_PER_YEAR = 365 * 24 * 60 / MIN_PER_DECISION  # ≈ 43,800


def run_strategy(df, T_open, T_close, T_flip, C_band, fee_per_leg,
                 max_hold_bars=5, max_streak_loss=5, cooldown_bars=10):
    """Run state machine on one DataFrame of decision bars."""
    n = len(df)
    q50 = df["y_pred_q50_bps_live"].values
    q10 = df["y_pred_q10_bps"].values
    q90 = df["y_pred_q90_bps"].values
    y = df["y_true_bps"].values

    state = 0                         # current position
    held_bars = 0                     # how long held in current state
    losing_streak = 0                 # consecutive losing trades
    cooldown = 0                      # bars remaining flat after streak

    pnl_per_bar = np.zeros(n, dtype=np.float64)
    state_log = np.zeros(n, dtype=np.int8)
    fee_log = np.zeros(n, dtype=np.float64)
    transition_log = np.zeros(n, dtype=np.int8)  # legs traded this bar

    for i in range(n):
        # Cooldown: forced flat
        if cooldown > 0:
            if state != 0:
                fee_log[i] += fee_per_leg
                transition_log[i] += 1
                state = 0
                held_bars = 0
            cooldown -= 1
            pnl_per_bar[i] = 0 - fee_log[i]
            state_log[i] = state
            continue

        # Decide on signals
        conf_long = (q50[i] >= T_open) and (q10[i] >= -C_band)
        conf_short = (q50[i] <= -T_open) and (q90[i] <= C_band)
        weak_long = q50[i] > T_close
        weak_short = q50[i] < -T_close
        flip_long = q50[i] >= T_flip and q10[i] >= -C_band  # stronger threshold for flip-from-short
        flip_short = q50[i] <= -T_flip and q90[i] <= C_band

        # Transitions
        new_state = state
        if state == 0:                      # flat
            if conf_long:
                new_state = +1
                fee_log[i] += fee_per_leg
                transition_log[i] += 1
            elif conf_short:
                new_state = -1
                fee_log[i] += fee_per_leg
                transition_log[i] += 1
        elif state == +1:                   # long
            if flip_short:
                # flip: close long + open short
                new_state = -1
                fee_log[i] += 2 * fee_per_leg
                transition_log[i] += 2
            elif (not weak_long) or held_bars >= max_hold_bars:
                # close to flat
                new_state = 0
                fee_log[i] += fee_per_leg
                transition_log[i] += 1
            # else: hold (weak_long still holds)
        elif state == -1:                   # short
            if flip_long:
                new_state = +1
                fee_log[i] += 2 * fee_per_leg
                transition_log[i] += 2
            elif (not weak_short) or held_bars >= max_hold_bars:
                new_state = 0
                fee_log[i] += fee_per_leg
                transition_log[i] += 1

        # Track held_bars
        if new_state != state and new_state != 0:
            held_bars = 1  # just entered (or flipped) — start counting from this bar
        elif new_state == state and new_state != 0:
            held_bars += 1
        else:
            held_bars = 0

        # Realize PnL for the 10-min hold from this decision point
        # Position during this decision bar = new_state (we set the position THIS bar)
        position_pnl = new_state * y[i]  # bps over 10-min hold
        bar_net = position_pnl - fee_log[i]
        pnl_per_bar[i] = bar_net
        state_log[i] = new_state

        # Trade outcome tracking (only on closed/flipped trades — i.e., transition counted at this bar)
        # For simplicity, count a "trade outcome" only when we EXIT a position (transition out of non-flat into flat OR flip).
        if state != 0 and (new_state == 0 or new_state == -state):
            # We just closed (or flipped) a position. The hold-period PnL is already in pnl_per_bar
            # but we want streak tracking based on whether the closed trade was profitable.
            # Approximation: use bar PnL of this transition as proxy for trade profitability.
            # (Sticky-hold PnL accumulation across multiple bars makes this approximate.)
            if bar_net < 0:
                losing_streak += 1
            else:
                losing_streak = 0
            if losing_streak >= max_streak_loss:
                cooldown = cooldown_bars
                losing_streak = 0

        state = new_state

    return pnl_per_bar, state_log, fee_log, transition_log


def evaluate(pnl_per_bar, state_log, transition_log):
    mean_per_bar = pnl_per_bar.mean()
    std_per_bar = pnl_per_bar.std()
    n_bars = len(pnl_per_bar)

    total_pnl_bps = pnl_per_bar.sum()
    cum_bps = np.cumsum(pnl_per_bar)
    running_max = np.maximum.accumulate(cum_bps)
    max_dd_bps = (running_max - cum_bps).max() if n_bars > 0 else 0.0

    # Annualized return (continuous compounding in bps)
    total_decisions = n_bars
    years = total_decisions / DECISIONS_PER_YEAR
    if years > 0:
        ann_return_pct = total_pnl_bps / 1e4 / years * 100  # in percent
    else:
        ann_return_pct = 0.0

    # Sharpe
    sharpe = mean_per_bar / std_per_bar * np.sqrt(DECISIONS_PER_YEAR) if std_per_bar > 0 else 0.0

    # Trade count: each new entry / flip counts as 1 trade (entry leg)
    # Approximation: # of transitions / 2 (each round-trip = 2 legs)
    n_trades = int(np.ceil(transition_log.sum() / 2))

    # Win rate: fraction of bars where pnl > 0 among in-market bars
    in_mkt = state_log != 0
    wins = (pnl_per_bar[in_mkt] > 0).sum() if in_mkt.sum() > 0 else 0
    win_rate = wins / in_mkt.sum() if in_mkt.sum() > 0 else 0.0

    time_in_mkt_pct = 100 * in_mkt.mean()

    return {
        "total_pnl_bps": total_pnl_bps,
        "ann_return_pct": ann_return_pct,
        "sharpe": sharpe,
        "max_dd_bps": max_dd_bps,
        "mean_pnl_per_bar_bps": mean_per_bar,
        "win_rate": win_rate,
        "n_trades": n_trades,
        "trades_per_day": n_trades / (years * 365) if years > 0 else 0.0,
        "time_in_mkt_pct": time_in_mkt_pct,
        "n_bars": n_bars,
    }


def main():
    print(f"Loading {CSV}...")
    df_raw = pd.read_csv(CSV)

    # Filter: drop mask=0 and warmup; sort by time
    valid = df_raw[df_raw["mask"].astype(bool) & ~df_raw["warmup"].astype(bool)].copy()
    valid = valid.sort_values("timestamp_us").reset_index(drop=True)
    print(f"After mask+warmup filter: {len(valid)} rows")

    # Subsample to every K bars (non-overlapping decision grid)
    df = valid.iloc[::SUBSAMPLE_K].reset_index(drop=True)
    print(f"After subsample (every {SUBSAMPLE_K} bars = {MIN_PER_DECISION}-min grid): {len(df)} decisions")
    print(f"Test period: {df['datetime_utc'].iloc[0]} → {df['datetime_utc'].iloc[-1]}")
    print(f"σ_y = {df['y_true_bps'].std():.2f} bps   σ_ŷ_live = {df['y_pred_q50_bps_live'].std():.4f} bps")
    print()

    # Parameter sweep
    grid = list(itertools.product(
        [3, 5, 7, 10],      # T_open
        [-3, 0, 3],         # T_close (negative = allow to drift through 0 before exiting)
        [5, 10, 15],        # C_band
        [6, 9, 12],         # fee_round_trip (bps)
    ))
    print(f"Sweep: {len(grid)} combos")

    results = []
    for T_open, T_close, C_band, fee_rt in grid:
        T_flip = T_open + 2  # flip requires +2 bps stronger
        fee_per_leg = fee_rt / 2.0
        pnl, state, fee, trans = run_strategy(
            df, T_open=T_open, T_close=T_close, T_flip=T_flip,
            C_band=C_band, fee_per_leg=fee_per_leg,
        )
        m = evaluate(pnl, state, trans)
        m.update({
            "T_open": T_open, "T_close": T_close, "T_flip": T_flip,
            "C_band": C_band, "fee_rt": fee_rt,
        })
        results.append(m)

    res = pd.DataFrame(results)

    # ============================================================
    # 1. Baseline: always-flat / always-long / sign(q50_live)-naive
    # ============================================================
    print("\n" + "=" * 80)
    print("BASELINES")
    print("=" * 80)
    # always long
    al_pnl = df["y_true_bps"].values
    print(f"Always-long (no fees):  mean={al_pnl.mean():+.3f} bps/bar  "
          f"Sharpe={al_pnl.mean()/al_pnl.std()*np.sqrt(DECISIONS_PER_YEAR):.3f}  "
          f"total={al_pnl.sum():+.0f} bps")

    # sign(q50_live), every bar, full round-trip fee
    for fee_rt in [6, 9, 12]:
        nv_pnl = np.sign(df["y_pred_q50_bps_live"].values) * df["y_true_bps"].values - fee_rt
        # in-market every bar
        n_t = (np.sign(df["y_pred_q50_bps_live"].values) != 0).sum()
        m = nv_pnl.mean()
        s = nv_pnl.std()
        sh = m/s * np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
        print(f"Naive sign(q50_live), fee_rt={fee_rt:>2}: total={nv_pnl.sum():+.0f} bps  "
              f"Sharpe={sh:+.3f}  ann_ret={nv_pnl.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")

    # ============================================================
    # 2. Top 10 by Sharpe
    # ============================================================
    print("\n" + "=" * 80)
    print("TOP 10 by Sharpe")
    print("=" * 80)
    top = res.sort_values("sharpe", ascending=False).head(10)
    cols = ["T_open", "T_close", "C_band", "fee_rt",
            "sharpe", "ann_return_pct", "total_pnl_bps",
            "max_dd_bps", "win_rate", "n_trades", "time_in_mkt_pct"]
    print(top[cols].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    # ============================================================
    # 3. Top 5 by total PnL (different criterion)
    # ============================================================
    print("\n" + "=" * 80)
    print("TOP 5 by Total PnL")
    print("=" * 80)
    top_p = res.sort_values("total_pnl_bps", ascending=False).head(5)
    print(top_p[cols].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    # ============================================================
    # 4. Best per fee level (so user sees fee sensitivity)
    # ============================================================
    print("\n" + "=" * 80)
    print("BEST PER FEE LEVEL (by Sharpe)")
    print("=" * 80)
    for fee_rt in [6, 9, 12]:
        sub = res[res["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).head(3)
        print(f"\n  fee_rt = {fee_rt} bps (round-trip):")
        print(sub[cols].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    # Save full results
    res.to_csv("backtest_sweep_results.csv", index=False)
    print(f"\nFull sweep written: backtest_sweep_results.csv ({len(res)} combos)")

    # ============================================================
    # 5. Deep dive on the OVERALL best
    # ============================================================
    best = res.sort_values("sharpe", ascending=False).iloc[0]
    print("\n" + "=" * 80)
    print(f"DEEP DIVE: best Sharpe operating point")
    print(f"  T_open={best['T_open']} bps, T_close={best['T_close']} bps, "
          f"T_flip={best['T_flip']} bps, C_band={best['C_band']} bps, "
          f"fee_rt={best['fee_rt']} bps")
    print("=" * 80)
    pnl, state, fee, trans = run_strategy(
        df, T_open=best["T_open"], T_close=best["T_close"],
        T_flip=best["T_flip"], C_band=best["C_band"],
        fee_per_leg=best["fee_rt"]/2.0,
    )

    df_dd = df.copy()
    df_dd["pnl_bps"] = pnl
    df_dd["state"] = state
    df_dd["fee_bps"] = fee
    df_dd["cum_pnl_bps"] = np.cumsum(pnl)

    print(f"  Total PnL:           {pnl.sum():+.2f} bps over {len(df_dd)} decisions "
          f"({len(df_dd)/DECISIONS_PER_YEAR*365:.1f} days)")
    print(f"  Annualized return:   {best['ann_return_pct']:+.2f} %")
    print(f"  Annualized Sharpe:   {best['sharpe']:+.3f}")
    print(f"  Max drawdown:        -{best['max_dd_bps']:.1f} bps")
    print(f"  Number of trades:    {int(best['n_trades'])}")
    print(f"  Trades per day:      {best['trades_per_day']:.2f}")
    print(f"  Time in market:      {best['time_in_mkt_pct']:.1f}%")
    print(f"  Win rate:            {best['win_rate']*100:.1f}%")
    print(f"  Fee cost total:      {fee.sum():.1f} bps")
    print()

    # Per-fold breakdown
    print("  Per-fold breakdown:")
    for fold in [0, 1, 2]:
        sub = df_dd[df_dd["fold"] == fold]
        if len(sub) == 0:
            continue
        ds = sub["pnl_bps"].values
        m, s = ds.mean(), ds.std()
        sh = m/s * np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
        print(f"    Fold {fold}: n={len(sub):>5} total={ds.sum():+7.1f} bps  "
              f"Sharpe={sh:+.3f}  fees={sub['fee_bps'].sum():.0f} bps")

    df_dd.to_csv("backtest_best_trades.csv", index=False)
    print(f"\nBest-strategy per-bar log: backtest_best_trades.csv")


if __name__ == "__main__":
    main()
