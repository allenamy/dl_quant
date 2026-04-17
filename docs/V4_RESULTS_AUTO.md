# V4 Results (PARTIAL — fold 0 only)

_Run aborted after fold 1 hung silently at epoch 2 for 23+ min. Training killed to stop GPU waste; baselines still running on pod CPU for fair comparison._

## Status

| Item | Status |
|---|---|
| V4 training | **Killed** — fold 0 done, fold 1 hung |
| V4 baselines (Ridge/XGB/FITS on V4 features @ h=180) | **Running** on pod CPU (~35 min elapsed of maybe 90 min needed) |
| Decision on retry / ablations | **Pending human review** |

## Fold 0 result (ONLY fold)

Config: single-horizon y_180, n_horizons=1, batch=1024, lr=6e-4, stride=180, 700 train days.

| Metric | Value |
|---|---:|
| Best epoch (val_corr) | 10 |
| Early-stopped at | epoch 18 (patience=8) |
| val_loss | 0.596 |
| **val_corr** | **0.0383** |
| val_r2 | 0.0011 |
| **test Pearson corr** | **0.0609** |
| test Spearman corr | 0.0893 |
| test R² | 0.0031 |
| Δ vs Ridge (0.099) | **−0.0381** |

Pooled backtest on fold 0 test set (15,605 samples):
- Gross PnL: +0.0 bps
- Costs: −139 bps
- Net PnL: **−139 bps**
- Weighted Sharpe: **−390** (signal too weak vs 4bps fee + 1bps slippage)

## Comparison to spec bars

| Target | Value | V4 fold 0 | Result |
|---|---:|---:|:-:|
| Primary: Pearson IC ≥ 0.12 on h=180 | 0.12 | 0.0609 | ❌ |
| V3+RevIN baseline on y_180 | 0.082 | 0.0609 | ❌ (below V3) |
| Ridge baseline on V3 features | 0.099 | 0.0609 | ❌ (below Ridge) |
| Weighted Sharpe > 1.0 on best horizon | 1.0 | −390 | ❌ |

**Bottom line: V4 as configured is worse than Ridge, worse than V3, and far below the target.**

## Why fold 1 hung

Unknown — both main and all 4 dataloader workers were alive (workers at ~92% CPU each) but no new epoch logged for 23 minutes. GPU at 0%. Baselines process was at 99% CPU in parallel but 256 cores are available so CPU contention should not matter.

Hypotheses for investigation:
- Infinite NaN loop (loss NaN → step skipped → never increments epoch counter)
- Dataloader queue deadlock between workers and main
- A particular training window in the fold-1 data subset triggers an exception that gets caught silently

Recommended next-try: re-run with `num_workers=0` (single-process) to see if deadlock disappears; or add `torch.autograd.set_detect_anomaly(True)` to catch NaN origin.

## Files

- `experiments/v4_full/fold_0/` — all fold 0 artifacts (best_model.pt, test_preds.npz, test_results.json)
- `experiments/v4_full/SUMMARY.json` — aggregate (only 1 fold so std/t-stat are NaN)
- `logs/train_v4_full.log` (on pod) — full training log including the hang
- `logs/overnight_monitor.log` (local) — 5-min snapshots across the whole session
- `docs/MORNING_BRIEF_2026_04_18.md` — commentary + decision tree

## Next actions (your call)

Three honest options:

1. **Declare V4 as configured a negative result.** Revert production signal to Ridge. V4 research artifacts are committed (architecture, data pipeline, features, 5 documented bugs fixed). Multi-horizon and other ablations are valid future research but won't flip this conclusion given fold 0 is already −0.04 below Ridge.

2. **Retry with config tweaks to address fold 1 hang AND low Pearson:**
   - `num_workers=0` to eliminate worker deadlock risk
   - Drop `lambda_utility_rank=0.3 → 0` (pure pinball) — rank loss may hurt Pearson
   - Re-run 4 folds (~4-6h of GPU)

3. **Audit why V4 underperforms V3.** V3 used stride=60 (3× more windows), possibly different feature set. Closer controlled comparison (same stride, same features except additions) would isolate which change hurt.

I would NOT auto-launch anything until you decide. Baselines finish autonomously (~50 more min) to give you the fair Ridge/XGB baseline on V4 features.
