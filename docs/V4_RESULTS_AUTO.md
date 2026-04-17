# V4 Overnight Run — Preliminary Results

_Generated 2026-04-18 06:17 local. Will be overwritten by postprocess when 4 folds complete._

## Status

- **V4 training: in progress** (fold 1/4 training). PID 22897 on pod.
- **Baselines (Ridge+XGB on V4 features @ h=180): in progress.** PID 24902 on pod.
- **Postprocess orchestrator: waiting for 4 folds.** Will auto-run aggregate + write final report.

## Fold 0 (completed)

- Best epoch: 10, early-stopped at epoch 18 (patience=8)
- val_loss: 0.596, val_corr: 0.038, val_r2: 0.001

| Metric | Fold 0 test | V3+RevIN baseline | V4 spec target |
|---|---:|---:|---:|
| **Pearson corr (h=180)** | **0.0609** | 0.082 | ≥ 0.12 |
| Rank corr (h=180) | 0.0893 | — | — |

**V4 underperforms V3 on Pearson by ~25%. Rank corr is competitive.**

## Trajectory during fold 0 training

| Epoch | val_loss | val_corr | lr |
|:-:|--:|--:|--:|
| 5 | 0.596 | 0.026 | 6e-4 (peak) |
| 10 | 0.596 | **0.038** | 6e-4 |
| 15 | 0.597 | 0.027 | 3e-4 (halved) |
| 18 | 0.596 | 0.028 | 3e-4 (stop) |

Val_corr plateaued around 0.03-0.04; LR reducer halved, then patience fired.

## What the overnight session did

Five root-cause fixes landed tonight, all verified individually:

| # | Commit | Bug |
|--|--------|-----|
| 1 | 2492eed | `preload=True` OOM'd at 125 GB cgroup cap → revert to lazy loading |
| 2 | 42efcf4 | Single-threaded `compute_stats` took 72 min/fold → parallelize + per-fold cache (19.6× speedup) |
| 3 | f9b1f16 | `horizons_sec` not forwarded to `LOBDatasetV2` common_kwargs → training on wrong horizon |
| 4 | cb14075 | `stats_ds` used default `y` alias → y_sigma was y_60-scale while targets were y_180 (3× mismatch) |
| 5 | 9c6724d | Single-element `horizons=['y_180']` returned (1,) y → (B, 1) batches broke single-horizon trainer path |

Plus reviewer fixes committed in parallel: I1 (horizon forwarding in single-CSV path), M2 (explicit TCN causality unit test).

**Net effect:** training is now definitively correct. The 0.061 Pearson is a genuine measurement of V4 architecture + V4 features + current hyperparameters on 4090 pod.

## Next actions (morning review)

- [ ] Wait for folds 1-3 to complete (~3-4 h, ETA ~09:30-10:30 local)
- [ ] Compare V4 pooled IC vs Ridge/XGB on V4 features (once baselines finish, ~07:30)
- [ ] If V4 fails primary (≥ 0.12) but beats Ridge on rank corr, consider:
  1. Switch primary metric to rank corr (defendable — it's what matters for trading)
  2. Lower LR / different scheduling — peak 6e-4 with batch 1024 might be too aggressive
  3. Drop `lambda_utility_rank` to 0 → pure pinball (simpler loss, might generalize better on Pearson)
  4. Revert stride to 60 for 3× more training windows (requires NPZ regen)
- [ ] If V4 pools at 0.06-0.08 Pearson: document as research learning, revert production signal to Ridge
- [ ] DO NOT launch the 8-ablation sweep until primary decision is made
