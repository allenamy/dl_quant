"""CSH v3 — Binance VIP9 fee schedule (maker 0%, taker 0.017% USDT / 0.0153% BNB).

Fee scenarios (round-trip bps):
  0.0  pure maker, idealized
  0.5  pure maker + tiny slippage
  1.0  pure maker realistic (~ miss handling)
  1.5  mostly maker
  1.7  ~ USDT VIP9 1 taker + 1 maker (BNB)
  2.0  USDC est (taker-side, promotional)
  3.0  USDT VIP9 BNB pure taker (1.53×2)
  3.4  USDT VIP9 pure taker

Sweep:
  T_open  ∈ {0.3, 0.5, 0.8, 1.2, 1.7, 2.2}
  T_close ∈ {-1.0, -0.3, 0.0, 0.3}
  max_hold ∈ {3, 5, 10, 20}
  fee_rt  ∈ {0.0, 0.5, 1.0, 1.5, 1.7, 2.0, 3.0, 3.4}
"""
import numpy as np
import pandas as pd
import itertools
from pathlib import Path

CSV = Path("predictions_all_folds.csv")
SUBSAMPLE_K = 4
DECISIONS_PER_YEAR = 365 * 24 * 60 / 12

def run_strategy(df, T_open, T_close, T_flip, fee_per_leg, max_hold_bars=20):
    n = len(df)
    q50 = df["y_pred_q50_bps_live"].values
    y = df["y_true_bps"].values
    state = 0; held_bars = 0
    pnl = np.zeros(n); slog = np.zeros(n, dtype=np.int8); flog = np.zeros(n); tlog = np.zeros(n, dtype=np.int8)
    for i in range(n):
        cl = q50[i] >= T_open; cs = q50[i] <= -T_open
        wl = q50[i] > T_close; ws = q50[i] < -T_close
        fl = q50[i] >= T_flip; fs = q50[i] <= -T_flip
        ns = state
        if state == 0:
            if cl: ns = +1; flog[i] += fee_per_leg; tlog[i] += 1
            elif cs: ns = -1; flog[i] += fee_per_leg; tlog[i] += 1
        elif state == +1:
            if fs: ns = -1; flog[i] += 2*fee_per_leg; tlog[i] += 2
            elif (not wl) or held_bars >= max_hold_bars:
                ns = 0; flog[i] += fee_per_leg; tlog[i] += 1
        elif state == -1:
            if fl: ns = +1; flog[i] += 2*fee_per_leg; tlog[i] += 2
            elif (not ws) or held_bars >= max_hold_bars:
                ns = 0; flog[i] += fee_per_leg; tlog[i] += 1
        if ns != state and ns != 0: held_bars = 1
        elif ns == state and ns != 0: held_bars += 1
        else: held_bars = 0
        pnl[i] = ns * y[i] - flog[i]; slog[i] = ns
        state = ns
    return pnl, slog, flog, tlog


def evaluate(pnl, slog, tlog):
    n = len(pnl); total = pnl.sum(); m, s = pnl.mean(), pnl.std()
    sh = m/s*np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
    cum = np.cumsum(pnl); dd = (np.maximum.accumulate(cum)-cum).max() if n else 0
    yrs = n/DECISIONS_PER_YEAR
    ann = total/1e4/yrs*100 if yrs > 0 else 0
    nt = int(np.ceil(tlog.sum()/2))
    in_mkt = slog != 0
    wr = (pnl[in_mkt] > 0).mean() if in_mkt.sum() else 0
    return dict(total_pnl_bps=total, ann_return_pct=ann, sharpe=sh, max_dd_bps=dd,
                win_rate=wr, n_trades=nt, time_in_mkt_pct=100*in_mkt.mean(), n_bars=n,
                pnl_per_trade=total/max(1,nt))


def main():
    df_raw = pd.read_csv(CSV)
    valid = df_raw[df_raw["mask"].astype(bool) & ~df_raw["warmup"].astype(bool)].copy()
    valid = valid.sort_values("timestamp_us").reset_index(drop=True)
    df = valid.iloc[::SUBSAMPLE_K].reset_index(drop=True)
    print(f"Decisions: {len(df)} ({len(df)/DECISIONS_PER_YEAR*365:.1f} days)")
    print(f"Period: {df['datetime_utc'].iloc[0][:10]} → {df['datetime_utc'].iloc[-1][:10]}")
    print()

    fees = [0.0, 0.5, 1.0, 1.5, 1.7, 2.0, 3.0, 3.4]
    fee_names = {
        0.0: "pure maker (ideal)", 0.5: "maker+slip 0.5",
        1.0: "maker realistic", 1.5: "maker++miss",
        1.7: "USDT VIP9 mixed (1m+1t-BNB)", 2.0: "USDC est",
        3.0: "USDT VIP9 BNB pure taker", 3.4: "USDT VIP9 pure taker",
    }

    grid = list(itertools.product(
        [0.3, 0.5, 0.8, 1.2, 1.7, 2.2],
        [-1.0, -0.3, 0.0, 0.3],
        fees,
        [3, 5, 10, 20],
    ))
    results = []
    for T_open, T_close, fee_rt, max_hold in grid:
        T_flip = max(T_open*1.5, T_open+0.5)
        pnl, slog, flog, tlog = run_strategy(df, T_open=T_open, T_close=T_close,
                                              T_flip=T_flip, fee_per_leg=fee_rt/2.0,
                                              max_hold_bars=max_hold)
        m = evaluate(pnl, slog, tlog)
        m.update(T_open=T_open, T_close=T_close, T_flip=round(T_flip, 2),
                 fee_rt=fee_rt, max_hold=max_hold)
        results.append(m)
    res = pd.DataFrame(results)
    res.to_csv("backtest_sweep_v3.csv", index=False)
    print(f"Sweep: {len(grid)} combos done\n")

    cols = ["T_open", "T_close", "T_flip", "fee_rt", "max_hold",
            "sharpe", "ann_return_pct", "total_pnl_bps", "max_dd_bps",
            "win_rate", "n_trades", "pnl_per_trade", "time_in_mkt_pct"]

    print("="*100)
    print("BEST OPERATING POINT PER FEE LEVEL (by Sharpe, ann_return_pct > 0)")
    print("="*100)
    pos = res[res["ann_return_pct"] > 0]
    for fee_rt in fees:
        sub = pos[pos["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).head(2)
        if len(sub) == 0:
            print(f"\n  fee_rt={fee_rt:>4} bps RT ({fee_names[fee_rt]}):  ⚠️ no positive return")
        else:
            print(f"\n  fee_rt={fee_rt:>4} bps RT ({fee_names[fee_rt]}):")
            print(sub[cols].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    # Headline tradeable table for user
    print("\n" + "="*100)
    print("HEADLINE TABLE (best Sharpe per fee scenario)")
    print("="*100)
    rows = []
    for fee_rt in fees:
        sub = res[res["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).iloc[0]
        rows.append({
            "Scenario": fee_names[fee_rt],
            "fee_rt": fee_rt,
            "T_open": sub["T_open"],
            "T_close": sub["T_close"],
            "max_hold": sub["max_hold"],
            "Sharpe": sub["sharpe"],
            "Ann.Ret%": sub["ann_return_pct"],
            "Total bps": sub["total_pnl_bps"],
            "DD bps": sub["max_dd_bps"],
            "Trades": sub["n_trades"],
            "PnL/trade": sub["pnl_per_trade"],
            "TimeInMkt%": sub["time_in_mkt_pct"],
        })
    hl = pd.DataFrame(rows)
    print(hl.to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
    hl.to_csv("backtest_headline_v3.csv", index=False)
    print("\nSaved: backtest_sweep_v3.csv  backtest_headline_v3.csv")

    # ============================================================
    # Deep dive on best Sharpe overall
    # ============================================================
    best = res.sort_values("sharpe", ascending=False).iloc[0]
    print("\n" + "="*100)
    print(f"DEEP DIVE: best overall (T_open={best['T_open']}, T_close={best['T_close']}, "
          f"fee_rt={best['fee_rt']}, max_hold={best['max_hold']})")
    print("="*100)
    pnl, slog, flog, tlog = run_strategy(df, T_open=best["T_open"], T_close=best["T_close"],
                                          T_flip=best["T_flip"], fee_per_leg=best["fee_rt"]/2.0,
                                          max_hold_bars=int(best["max_hold"]))
    df_d = df.copy()
    df_d["pnl_bps"] = pnl; df_d["state"] = slog; df_d["fee_bps"] = flog
    df_d["cum_pnl_bps"] = np.cumsum(pnl)

    print(f"  Total PnL:           {pnl.sum():+.1f} bps  ({pnl.sum()/100:+.2f}%)")
    print(f"  Ann. return:         {best['ann_return_pct']:+.2f} %")
    print(f"  Ann. Sharpe:         {best['sharpe']:+.2f}")
    print(f"  Max DD:              -{best['max_dd_bps']:.1f} bps")
    print(f"  Trades:              {int(best['n_trades'])} ({best['n_trades']/(len(df)/DECISIONS_PER_YEAR*365):.2f}/day)")
    print(f"  Time in market:      {best['time_in_mkt_pct']:.1f}%")
    print(f"  Win rate:            {best['win_rate']*100:.1f}%")
    print(f"  PnL/trade:           {best['pnl_per_trade']:+.2f} bps")
    print()
    print(f"  Per-fold:")
    for fold in [0, 1, 2]:
        sub = df_d[df_d["fold"]==fold]
        if len(sub) == 0: continue
        ds = sub["pnl_bps"].values; m, s = ds.mean(), ds.std()
        sh = m/s*np.sqrt(DECISIONS_PER_YEAR) if s>0 else 0
        d0, d1 = sub["datetime_utc"].iloc[0][:10], sub["datetime_utc"].iloc[-1][:10]
        print(f"    Fold {fold} ({d0}→{d1}):  total={ds.sum():+7.1f}bps  Sharpe={sh:+.3f}")

    df_d.to_csv("backtest_best_v3.csv", index=False)

    # ============================================================
    # 7%/day cumPnL trajectory
    # ============================================================
    cum = df_d["cum_pnl_bps"].values
    n = len(cum)
    print("\n  Cumulative PnL trajectory:")
    for pct in [0, 10, 25, 50, 75, 90, 100]:
        idx = min(n-1, int(pct * n / 100))
        print(f"    day {pct:>3}%  {df_d['datetime_utc'].iloc[idx][:10]}  cum = {cum[idx]:+8.1f} bps")


if __name__ == "__main__":
    main()
