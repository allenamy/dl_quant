"""CSH backtest v2 — thresholds in q50_live's actual scale (σ=0.74 bps).

Improvements over v1:
- T_open in {0.5, 0.8, 1.2, 1.7, 2.2} bps (P75-P99 of |q50_live|)
- T_close asymmetric (allow drift toward 0 before exit)
- C_band optional — q10/q90 raw scale is wide (±13 bps mean), not useful as bound,
  so we either drop it OR use sign-agreement (q10 same sign as q50).
- Added: Oracle backtest (perfect hindsight) as upper bound
- Added: Naive "trade every bar in sign(q50_live)" baseline
- Added: Annualized return + Sharpe in $ terms (assuming $10K notional/trade)
- Added: per-fold breakdown
"""
import numpy as np
import pandas as pd
import itertools
from pathlib import Path

CSV = Path("predictions_all_folds.csv")
SUBSAMPLE_K = 4
MIN_PER_DECISION = 12
DECISIONS_PER_YEAR = 365 * 24 * 60 / MIN_PER_DECISION  # 43,800


def run_strategy(df, T_open, T_close, T_flip, fee_per_leg,
                 require_q10_agree=False, max_hold_bars=20):
    """Confident Sticky Hold state machine."""
    n = len(df)
    q50 = df["y_pred_q50_bps_live"].values
    q10 = df["y_pred_q10_bps"].values
    q90 = df["y_pred_q90_bps"].values
    y = df["y_true_bps"].values

    state = 0
    held_bars = 0
    pnl_per_bar = np.zeros(n, dtype=np.float64)
    state_log = np.zeros(n, dtype=np.int8)
    fee_log = np.zeros(n, dtype=np.float64)
    trans_log = np.zeros(n, dtype=np.int8)

    for i in range(n):
        # Signal conditions
        cl = q50[i] >= T_open
        cs = q50[i] <= -T_open
        if require_q10_agree:
            cl = cl and (q10[i] > 0)
            cs = cs and (q90[i] < 0)
        weak_long = q50[i] > T_close
        weak_short = q50[i] < -T_close
        flip_long = q50[i] >= T_flip
        flip_short = q50[i] <= -T_flip
        if require_q10_agree:
            flip_long = flip_long and q10[i] > 0
            flip_short = flip_short and q90[i] < 0

        new_state = state
        if state == 0:
            if cl: new_state = +1; fee_log[i] += fee_per_leg; trans_log[i] += 1
            elif cs: new_state = -1; fee_log[i] += fee_per_leg; trans_log[i] += 1
        elif state == +1:
            if flip_short:
                new_state = -1; fee_log[i] += 2*fee_per_leg; trans_log[i] += 2
            elif (not weak_long) or held_bars >= max_hold_bars:
                new_state = 0; fee_log[i] += fee_per_leg; trans_log[i] += 1
        elif state == -1:
            if flip_long:
                new_state = +1; fee_log[i] += 2*fee_per_leg; trans_log[i] += 2
            elif (not weak_short) or held_bars >= max_hold_bars:
                new_state = 0; fee_log[i] += fee_per_leg; trans_log[i] += 1

        if new_state != state and new_state != 0:
            held_bars = 1
        elif new_state == state and new_state != 0:
            held_bars += 1
        else:
            held_bars = 0

        position_pnl = new_state * y[i]
        pnl_per_bar[i] = position_pnl - fee_log[i]
        state_log[i] = new_state
        state = new_state

    return pnl_per_bar, state_log, fee_log, trans_log


def evaluate(pnl_per_bar, state_log, trans_log):
    n_bars = len(pnl_per_bar)
    total = pnl_per_bar.sum()
    m, s = pnl_per_bar.mean(), pnl_per_bar.std()
    sh = m / s * np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
    cum = np.cumsum(pnl_per_bar)
    dd = (np.maximum.accumulate(cum) - cum).max() if n_bars > 0 else 0
    years = n_bars / DECISIONS_PER_YEAR
    ann_ret_pct = total / 1e4 / years * 100 if years > 0 else 0  # bps→fraction, ×100→%
    n_trades = int(np.ceil(trans_log.sum() / 2))
    in_mkt = state_log != 0
    win_rate = (pnl_per_bar[in_mkt] > 0).mean() if in_mkt.sum() else 0
    return {
        "total_pnl_bps": total,
        "ann_return_pct": ann_ret_pct,
        "sharpe": sh,
        "max_dd_bps": dd,
        "mean_pnl_per_bar_bps": m,
        "win_rate": win_rate,
        "n_trades": n_trades,
        "trades_per_day": n_trades / (years * 365) if years > 0 else 0,
        "time_in_mkt_pct": 100 * in_mkt.mean(),
        "n_bars": n_bars,
    }


def main():
    df_raw = pd.read_csv(CSV)
    valid = df_raw[df_raw["mask"].astype(bool) & ~df_raw["warmup"].astype(bool)].copy()
    valid = valid.sort_values("timestamp_us").reset_index(drop=True)
    df = valid.iloc[::SUBSAMPLE_K].reset_index(drop=True)
    print(f"Decisions: {len(df)}  ({len(df)/DECISIONS_PER_YEAR*365:.1f} days)")
    print(f"Test period: {df['datetime_utc'].iloc[0][:10]} → {df['datetime_utc'].iloc[-1][:10]}")
    print(f"σ_y = {df['y_true_bps'].std():.2f} bps   σ_q50_live = {df['y_pred_q50_bps_live'].std():.4f} bps")
    print()

    # ============================================================
    # CEILING: Oracle (perfect hindsight on direction)
    # ============================================================
    print("=" * 90)
    print("CEILINGS & BASELINES (informative)")
    print("=" * 90)
    # No fee oracle
    oracle_pnl = np.abs(df["y_true_bps"].values)
    print(f"  Oracle (sign(y), no fee):  mean={oracle_pnl.mean():+.3f}  total={oracle_pnl.sum():+.0f} bps  "
          f"ann_ret={oracle_pnl.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")
    for fee_rt in [4, 6, 9, 12]:
        oracle_net = np.abs(df["y_true_bps"].values) - fee_rt
        print(f"  Oracle, fee_rt={fee_rt:>2}:           mean={oracle_net.mean():+.3f}  total={oracle_net.sum():+.0f} bps  "
              f"ann_ret={oracle_net.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")
    print()
    print("  Always-long (BTC beta, no fee):")
    al = df["y_true_bps"].values
    print(f"    total={al.sum():+.0f} bps  ann_ret={al.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%  "
          f"Sharpe={al.mean()/al.std()*np.sqrt(DECISIONS_PER_YEAR):.3f}")
    print()
    print("  Naive sign(q50_live) every bar (no threshold, no hold):")
    for fee_rt in [4, 6, 9, 12]:
        nv = np.sign(df["y_pred_q50_bps_live"].values) * df["y_true_bps"].values - fee_rt
        m, s = nv.mean(), nv.std()
        print(f"    fee_rt={fee_rt}: mean={m:+.3f} Sharpe={m/s*np.sqrt(DECISIONS_PER_YEAR):+.2f} "
              f"total={nv.sum():+.0f} bps  ann_ret={nv.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")

    # ============================================================
    # Sweep
    # ============================================================
    print()
    grid = list(itertools.product(
        [0.5, 0.8, 1.2, 1.7, 2.2],          # T_open  (in q50_live scale, std≈0.74)
        [-1.0, -0.3, 0.0, 0.3],             # T_close (asymmetric)
        [4, 6, 9, 12],                       # fee_rt
        [False, True],                       # require_q10_agree
        [5, 10, 20],                         # max_hold_bars (60, 120, 240 min)
    ))
    results = []
    for T_open, T_close, fee_rt, agree, max_hold in grid:
        T_flip = max(T_open * 1.5, T_open + 0.5)
        fee_per_leg = fee_rt / 2.0
        pnl, state, fee, trans = run_strategy(
            df, T_open=T_open, T_close=T_close, T_flip=T_flip,
            fee_per_leg=fee_per_leg, require_q10_agree=agree, max_hold_bars=max_hold,
        )
        m = evaluate(pnl, state, trans)
        m.update({
            "T_open": T_open, "T_close": T_close, "T_flip": round(T_flip, 2),
            "fee_rt": fee_rt, "q10_agree": agree, "max_hold": max_hold,
        })
        results.append(m)
    res = pd.DataFrame(results)
    print(f"=== Sweep: {len(grid)} combos done ===\n")

    cols_show = ["T_open", "T_close", "T_flip", "fee_rt", "q10_agree", "max_hold",
                 "sharpe", "ann_return_pct", "total_pnl_bps", "max_dd_bps",
                 "win_rate", "n_trades", "time_in_mkt_pct"]

    print("=" * 90)
    print("TOP 10 BY SHARPE")
    print("=" * 90)
    print(res.sort_values("sharpe", ascending=False).head(10)[cols_show]
          .to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    print("\n" + "=" * 90)
    print("BEST POSITIVE-RETURN PER FEE LEVEL (by Sharpe, must have ann_ret > 0)")
    print("=" * 90)
    pos = res[res["ann_return_pct"] > 0]
    if len(pos) == 0:
        print("  ⚠️  NO combination achieves positive net return after fees.")
    else:
        for fee_rt in [4, 6, 9, 12]:
            sub = pos[pos["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).head(3)
            if len(sub) == 0:
                print(f"\n  fee_rt={fee_rt} bps round-trip:  ⚠️ no positive-return combos")
                continue
            print(f"\n  fee_rt={fee_rt} bps round-trip:")
            print(sub[cols_show].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    res.to_csv("backtest_sweep_v2.csv", index=False)

    # ============================================================
    # Deep dive on best
    # ============================================================
    best = res.sort_values("sharpe", ascending=False).iloc[0]
    print("\n" + "=" * 90)
    print("DEEP DIVE: best Sharpe operating point")
    print(f"  T_open={best['T_open']}  T_close={best['T_close']}  T_flip={best['T_flip']}")
    print(f"  fee_rt={best['fee_rt']}  q10_agree={best['q10_agree']}  max_hold={best['max_hold']}")
    print("=" * 90)

    pnl, state, fee, trans = run_strategy(
        df, T_open=best["T_open"], T_close=best["T_close"],
        T_flip=best["T_flip"], fee_per_leg=best["fee_rt"]/2.0,
        require_q10_agree=best["q10_agree"], max_hold_bars=int(best["max_hold"]),
    )

    df_d = df.copy()
    df_d["pnl_bps"] = pnl
    df_d["state"] = state
    df_d["fee_bps"] = fee
    df_d["cum_pnl_bps"] = np.cumsum(pnl)

    print(f"  Total PnL:              {pnl.sum():+.1f} bps over {len(df_d)} decisions "
          f"({len(df_d)/DECISIONS_PER_YEAR*365:.1f} days)")
    print(f"  Annualized return:      {best['ann_return_pct']:+.3f} %")
    print(f"  Annualized Sharpe:      {best['sharpe']:+.3f}")
    print(f"  Max drawdown:           -{best['max_dd_bps']:.1f} bps")
    print(f"  Number of trades:       {int(best['n_trades'])}")
    print(f"  Trades per day:         {best['trades_per_day']:.2f}")
    print(f"  Time in market:         {best['time_in_mkt_pct']:.1f}%")
    print(f"  Win rate:               {best['win_rate']*100:.1f}%")
    print(f"  Fee paid total:         {fee.sum():.1f} bps")
    print(f"  Mean PnL per trade:     {pnl.sum()/max(1, int(best['n_trades'])):+.2f} bps")
    print()
    print(f"  Per-fold breakdown:")
    for fold in [0, 1, 2]:
        sub = df_d[df_d["fold"] == fold]
        if len(sub) == 0: continue
        ds = sub["pnl_bps"].values
        m, s = ds.mean(), ds.std()
        sh = m/s * np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
        date_min, date_max = sub["datetime_utc"].iloc[0][:10], sub["datetime_utc"].iloc[-1][:10]
        print(f"    Fold {fold}: {date_min}→{date_max} n={len(sub):>4}  "
              f"total={ds.sum():+7.1f}bps  Sharpe={sh:+.3f}  fees={sub['fee_bps'].sum():.0f}bps")

    df_d.to_csv("backtest_best_v2.csv", index=False)
    print()

    # ============================================================
    # Cumulative PnL trajectory (text plot)
    # ============================================================
    cum = df_d["cum_pnl_bps"].values
    n = len(cum)
    print("=" * 90)
    print("CUMULATIVE PnL TRAJECTORY (sampled at 5% intervals)")
    print("=" * 90)
    for pct in [0, 5, 10, 25, 50, 75, 90, 95, 100]:
        idx = min(n - 1, int(pct * n / 100))
        print(f"  {pct:>3}%  {df_d['datetime_utc'].iloc[idx][:10]}  cum PnL = {cum[idx]:+8.1f} bps")


if __name__ == "__main__":
    main()
