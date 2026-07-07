# BTC y_600 backtest-ready dataset — λ0.1 EMA no-peek, 10-month rolling walk-forward

> Created 2026-06-29 | Source: REG_arch-lineage λ0.1 model (EMA checkpoint), btcusdt_copy perp book-mid (binance-futures venue).
> File: `y600_backtest_dataset.csv`

## What this is
One row per prediction node (10-min decision grid, ~600s spacing) for BTC USDT-**perp** 10-minute-ahead return prediction.
Rolling **walk-forward**: each month's predictions come from the model trained ONLY on the prior 450 days (→ 2-day embargo →
val → test). No fold sees its own future. The predictions are the **EMA checkpoint** under a **FIXED always-EMA rule**
(no per-month checkpoint selection by test metrics → no test-peeking; "no-peek" caliber).

**BEST model = λ0.1** (the default loss). The 2b λ0.5 variant was tested and confirmed a **wash** (same-checkpoint pooled
ΔP ≈ 0; helped 1 / hurt 2 of 3 months) — so λ0.1 is the deliverable.

## Columns
| column | units | meaning |
|---|---|---|
| `timestamp_ms` | ms epoch (UTC) | entry time of the decision (open a position here) |
| `datetime_utc` | ISO8601 Z | same, human-readable |
| `y_pred_raw` | std-units | model q50 prediction (standardized; sign + rank are what matter, β unstable so magnitude is not calibrated) |
| `y_pred_demeaned` | std-units | `y_pred_raw` − **causal trailing mean of y_pred_raw over the last 3600s (≤t)**. Bias-free tradeable signal (removes slow directional drift in the prediction). STRICTLY CAUSAL, no look-ahead. |
| `y_true_ret_bps` | bps | realized **600s forward PERP log-return** from REAL perp book-mid: `1e4·log(mid(t+600s)/mid(t))`. **This is the actual P&L basis** (what a position entered at t earns over the next 10 min). |
| `y_true_demeaned_bps` | bps | `y_true_ret_bps` − **causal trailing mean market drift over the last 3600s (≤t)**. Drift-neutral realized return → backtesting P&L on THIS measures **genuine alpha**, not the period's market drift (e.g. the 2025-08→2026-05 down-trend). |
| `month` | tag | rolling fold (`YYYY_MM`) the row belongs to |

**Demean windows:** both = **3600 seconds** trailing (causal, ≤t). `y_pred_demeaned` uses a trailing mean of the prediction;
`y_true_demeaned_bps` uses a trailing mean of the realized 600s return (market-drift proxy).

## ⚠️ CRITICAL — OVERLAPPING ROWS (stride 180s, horizon 600s)
Predictions are on a **180-second stride**, but `y_true_ret_bps` is a **600-second forward window**. So **consecutive rows
OVERLAP**: each row's realized return covers t→t+600s, and the next row is only 180s later → **~3-4 consecutive rows share
overlapping forward windows** and are strongly autocorrelated.

**DO NOT treat each row as an independent trade.** Doing so massively over-counts trades and inflates/distorts Sharpe
(overlap inflates apparent IC and breaks the iid assumption behind any Sharpe annualization).

Handle it ONE of two ways:
- **(a) Subsample to non-overlapping spacing (the CLEAN caliber):** keep rows ≥600s apart (≈ every 3rd–4th row; pick the
  first row of each non-overlapping 600s block). Gives honest, iid-ish per-trade stats. **This is the caliber all reported
  per-trade economics use.**
- **(b) Overlap-aware position backtest:** simulate ONE position at a time with explicit entry/hold/exit logic (a new signal
  while already in a position does not open a second overlapping trade). Holding naturally resolves the overlap.

**The per-trade economics we reported (~+2 bps clean per-horizon, drift-neutral net Sharpe ≤0 at taker, ~breakeven at maker)
were computed on the CLEAN NON-OVERLAPPING caliber (or via a one-position holding backtest) — reproduce with (a) or (b),
NOT with the raw dense rows.** Stride = **180s**, horizon = **600s**.

## How to backtest
1. **Signal** = `y_pred_demeaned` (bias-free). **Entry**: tail-gate — go LONG when it is in the top tail of its trailing
   distribution, SHORT when in the bottom tail (±2.5% tail was the tightest tested; ±5/10% also valid).
2. **Sizing**: **size on RANK / sign, NOT magnitude.** β (y on ŷ) is UNSTABLE across months (range 0.19–1.82), so a
   magnitude/β-scaled size mis-sizes month-to-month. Use sign or rank-bucket sizing.
3. **Exit**: horizon-matched is honest — close near the 10-min horizon (1 node) or on signal mean-revert through the
   trailing median. **Avoid long holds** (opposite-tail exit holds ~hours → rides market drift, not signal).
4. **P&L**:
   - For **realistic net-of-cost** P&L: accumulate `y_true_ret_bps` per held position, **minus round-trip cost** (maker
     ~2bps RT, taker ~3.4bps at 1.7/side, retail taker ~8–10bps RT).
   - For **genuine drift-neutral ALPHA** (regime-robust, removes the period trend): use `y_true_demeaned_bps` as the P&L
     basis. **This is the number that tells you if there's real edge** vs just riding the down-trend.

## Honest caveats (READ BEFORE TRADING)
- **Signal is real but WEAK and below cost.** Per-day-CLEAN IC ≈ 0.039 pooled (10 months); per-horizon clean edge ≈ **+2 bps**.
- **NOT robustly tradeable net-of-cost at any tested fee tier.** Drift-neutral net Sharpe is ≤0 at taker (3.4 & 8 bps RT)
  and ~breakeven-to-negative at maker (2 bps RT). The per-600s clean signal (~2bps) < taker cost (3.4bps).
- **Apparent positives are drift-riding and/or single-outlier-driven.** Raw (non-drift-neutral) short-only at 3.4bps shows
  Sharpe ~+0.66, but it is mostly the 2025-08→2026-05 down-trend harvest + one outlier month (2025-11); drift-neutral it is
  ~0, and bootstrap 95% CIs include 0 (within ~2σ). **Backtest on `y_true_demeaned_bps` to avoid being fooled by the trend.**
- **Signal is SYMMETRIC** (long ≈ short clean edge); short-only's apparent edge in this window was the down-period drift.
- **Regime-dependent**: strong months (2025-10/11) IC 0.06–0.08; drift months (2026-01→05) 0.012–0.031. All positive but weak.
- **β unstable → rank/sign sizing only.** **Front-loaded alpha** (latency-sensitive; ~−0.009 P per 2s entry delay).
- Status: **research-stage.** Tradeability would need lower fees (maker/VIP) AND a stronger signal (orthogonal data —
  liquidations is the only untested lever, infra-gated; funding/OI falsified) AND breadth (multi-asset).

## Provenance / reproduce
- Builder: `multi_asset/eval/build_backtest_dataset.py` (predictions `experiments/wfEMA/wf_<month>/fold_0/ema_test_preds.npz`,
  perp mid from `btcusdt_copy_*/dl-tardis/book_snapshot_25/<date>/binance-futures/BTCUSDT.csv.gz`).
- Full analysis: `docs/2026-06-28_FINAL_y600_deliverable.md` (trajectory, monotonicity, trading verdict, milestone-gap root-cause).
