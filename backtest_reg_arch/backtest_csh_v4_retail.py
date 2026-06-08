"""CSH v4 — RETAIL user fee schedule (普通用户, 非 VIP).

USDT-margined futures:
  Maker 0.0200% = 2.0 bps  /  Taker 0.0500% = 5.0 bps
With BNB 10% discount:
  Maker 0.0180% = 1.8 bps  /  Taker 0.0450% = 4.5 bps

Realistic execution scenarios (round-trip bps):
  3.6  pure maker, BNB,  100% fill (ideal)
  4.0  pure maker, USDT, 100% fill (ideal)
  5.2  realistic maker, BNB, 70/30 fill
  5.8  realistic maker, USDT, 70/30 fill
  6.3  mixed (1 maker + 1 taker), BNB
  7.0  mixed (1 maker + 1 taker), USDT
  9.0  pure taker, BNB
  10.0 pure taker, USDT

Sweep wider thresholds since high fee needs P99+ signal:
  T_open  ∈ {1.0, 1.5, 2.0, 2.5, 3.0}     [σ_q50_live = 0.74, so P95=1.4, P99=2.0, P99.5=2.4]
  T_close ∈ {-2.0, -1.0, -0.3, 0.0, 0.5}
  max_hold ∈ {5, 10, 20, 30}              [60 - 360 min]
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

    fee_scenarios = [
        (3.6, "pure maker BNB (ideal)"),
        (4.0, "pure maker USDT (ideal)"),
        (5.2, "realistic maker BNB (70/30 fill)"),
        (5.8, "realistic maker USDT (70/30 fill)"),
        (6.3, "1maker+1taker BNB"),
        (7.0, "1maker+1taker USDT"),
        (9.0, "pure taker BNB"),
        (10.0, "pure taker USDT"),
    ]
    fee_names = dict(fee_scenarios)
    fees = [f for f, _ in fee_scenarios]

    print("="*100)
    print("CEILING / BASELINE")
    print("="*100)
    y = df["y_true_bps"].values
    abs_y = np.abs(y)
    print(f"  Oracle (sign(y) hindsight, NO fee):  mean={abs_y.mean():+.3f}  Sharpe={abs_y.mean()/abs_y.std()*np.sqrt(DECISIONS_PER_YEAR):.2f}  "
          f"total={abs_y.sum():+.0f} bps  ann_ret={abs_y.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.0f}%")
    for fee_rt, name in fee_scenarios:
        net = abs_y - fee_rt
        print(f"  Oracle, fee_rt={fee_rt:>4} ({name:35s}): mean={net.mean():+.3f}  total={net.sum():+8.0f} bps  ann_ret={net.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")
    print()
    print("  Always-long (BTC beta, no fee):")
    print(f"    total={y.sum():+.0f} bps  ann_ret={y.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%  "
          f"Sharpe={y.mean()/y.std()*np.sqrt(DECISIONS_PER_YEAR):+.2f}")
    print()
    print("  Naive sign(q50_live) every bar:")
    for fee_rt, name in fee_scenarios:
        nv = np.sign(df["y_pred_q50_bps_live"].values) * y - fee_rt
        m, s = nv.mean(), nv.std()
        print(f"    fee_rt={fee_rt:>4} ({name:35s}): mean={m:+.3f} Sharpe={m/s*np.sqrt(DECISIONS_PER_YEAR):+.2f} "
              f"total={nv.sum():+.0f} bps  ann_ret={nv.sum()/1e4/(len(df)/DECISIONS_PER_YEAR)*100:+.1f}%")
    print()

    grid = list(itertools.product(
        [1.0, 1.5, 2.0, 2.5, 3.0],
        [-2.0, -1.0, -0.3, 0.0, 0.5],
        fees,
        [5, 10, 20, 30],
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
    res.to_csv("backtest_sweep_v4_retail.csv", index=False)
    print(f"=== Sweep: {len(grid)} combos done ===\n")

    cols = ["T_open", "T_close", "T_flip", "fee_rt", "max_hold",
            "sharpe", "ann_return_pct", "total_pnl_bps", "max_dd_bps",
            "win_rate", "n_trades", "pnl_per_trade", "time_in_mkt_pct"]

    print("="*100)
    print("BEST OPERATING POINT PER FEE LEVEL (by Sharpe, must have ann_ret > 0)")
    print("="*100)
    pos = res[res["ann_return_pct"] > 0]
    for fee_rt, name in fee_scenarios:
        sub = pos[pos["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).head(2)
        if len(sub) == 0:
            print(f"\n  fee_rt={fee_rt:>4} ({name}): ⚠️ no positive-return combinations")
        else:
            print(f"\n  fee_rt={fee_rt:>4} ({name}):")
            print(sub[cols].to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

    print("\n" + "="*100)
    print("HEADLINE TABLE (best Sharpe per fee scenario)")
    print("="*100)
    rows = []
    for fee_rt, name in fee_scenarios:
        sub_pos = res[(res["fee_rt"] == fee_rt) & (res["ann_return_pct"] > 0)]
        if len(sub_pos) == 0:
            best = res[res["fee_rt"] == fee_rt].sort_values("sharpe", ascending=False).iloc[0]
        else:
            best = sub_pos.sort_values("sharpe", ascending=False).iloc[0]
        rows.append({
            "Scenario": name, "fee_rt": fee_rt,
            "T_open": best["T_open"], "T_close": best["T_close"],
            "max_hold": best["max_hold"],
            "Sharpe": best["sharpe"], "Ann.Ret%": best["ann_return_pct"],
            "Total bps": best["total_pnl_bps"], "DD bps": best["max_dd_bps"],
            "Trades": best["n_trades"], "PnL/trade": best["pnl_per_trade"],
            "TimeInMkt%": best["time_in_mkt_pct"],
        })
    hl = pd.DataFrame(rows)
    print(hl.to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
    hl.to_csv("backtest_headline_v4_retail.csv", index=False)
    print()

    # Per-fold breakdown for the best at "realistic maker USDT" (RT=5.8)
    realistic_rt = 5.8
    realistic_subset = res[(res["fee_rt"] == realistic_rt) & (res["ann_return_pct"] > 0)]
    if len(realistic_subset) > 0:
        best = realistic_subset.sort_values("sharpe", ascending=False).iloc[0]
        print("="*100)
        print(f"DEEP DIVE: realistic maker USDT (RT={realistic_rt} bps) best operating point")
        print(f"  T_open={best['T_open']}  T_close={best['T_close']}  T_flip={best['T_flip']}  max_hold={best['max_hold']}")
        print("="*100)
        pnl, slog, flog, tlog = run_strategy(df, T_open=best["T_open"], T_close=best["T_close"],
                                              T_flip=best["T_flip"], fee_per_leg=best["fee_rt"]/2.0,
                                              max_hold_bars=int(best["max_hold"]))
        df_d = df.copy()
        df_d["pnl_bps"] = pnl; df_d["state"] = slog; df_d["fee_bps"] = flog
        df_d["cum_pnl_bps"] = np.cumsum(pnl)
        print(f"  Total PnL:      {pnl.sum():+.1f} bps ({pnl.sum()/100:+.2f}%)")
        print(f"  Ann. return:    {best['ann_return_pct']:+.2f} %")
        print(f"  Ann. Sharpe:    {best['sharpe']:+.2f}")
        print(f"  Max DD:         -{best['max_dd_bps']:.1f} bps")
        print(f"  Trades:         {int(best['n_trades'])} ({best['n_trades']/(len(df)/DECISIONS_PER_YEAR*365):.2f}/day)")
        print(f"  Win rate:       {best['win_rate']*100:.1f}%")
        print(f"  Time in mkt:    {best['time_in_mkt_pct']:.1f}%")
        print(f"  PnL/trade:      {best['pnl_per_trade']:+.2f} bps")
        print(f"\n  Per-fold:")
        for fold in [0, 1, 2]:
            sub = df_d[df_d["fold"]==fold]
            if len(sub) == 0: continue
            ds = sub["pnl_bps"].values; m, s = ds.mean(), ds.std()
            sh = m/s*np.sqrt(DECISIONS_PER_YEAR) if s>0 else 0
            d0, d1 = sub["datetime_utc"].iloc[0][:10], sub["datetime_utc"].iloc[-1][:10]
            print(f"    Fold {fold} ({d0}→{d1}):  total={ds.sum():+7.1f}bps  Sharpe={sh:+.3f}  n_trades_approx={int(sub['fee_bps'].sum()/(best['fee_rt']/2))}")
        df_d.to_csv("backtest_best_v4_retail.csv", index=False)


if __name__ == "__main__":
    main()
