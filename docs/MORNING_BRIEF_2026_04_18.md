# Morning Brief — 2026-04-18

## TL;DR

V4 overnight run is **in progress**. Fold 0 completed with **test Pearson 0.061 (h=180), rank 0.089**.

- **Primary criterion (Pearson ≥ 0.12 on h=180): NOT cleared** on fold 0.
- Rank correlation 0.089 is roughly V3-baseline-level (V3 was 0.082 Pearson).
- 3 more folds to run; pooled IC across all 4 will be the final verdict.

## What happened overnight

Five rounds of bug-hunting, all now fixed:

| # | Bug | Impact before fix |
|--|-----|-------------------|
| 1 | preload=True OOM at 125 GB cgroup | first launch froze before first epoch |
| 2 | Single-thread compute_stats on 700 FUSE NPZs | 72 min pre-training overhead per fold |
| 3 | `horizons_sec` not plumbed into LOBDatasetV2 common_kwargs | model trained on y_60 while config said y_180 |
| 4 | `stats_ds` used 'y' alias = y_60 | y_sigma 3× wrong → normalized targets collapsed near zero |
| 5 | Single-element horizons list gave (B,1) not (B,) shape | single-horizon path gave nonsense correlations |

After fix 5, training finally produced honest numbers. Memory entries in `.claude/projects/.../memory/` document each root cause.

## Fold 0 results

```
best_epoch=10 val_loss=0.596 val_corr=0.0383 (early-stopped @18)
test Pearson corr = 0.0609   (target 0.12, V3 baseline 0.082)
test Rank corr    = 0.0893   (competitive with V3)
```

Raw files: `experiments/v4_full/fold_0/`.

## Still running on pod

- **V4 training**: PID 22897, fold 1 in progress. ETA ~10:00-10:30 local for all 4 folds.
- **V4 baselines (Ridge+XGB on V4 features @ h=180)**: PID 24902, CPU-only. ETA ~08:30 local.
- **Local orchestrator**: `wait_and_postprocess.sh` polls pod every 5 min, auto-runs `aggregate_folds.py` when 4 test_results.json files exist, overwrites `docs/V4_RESULTS_AUTO.md` with complete table.
- **Local monitor**: `scripts/overnight_monitor.sh` writes 5-min snapshots to `logs/overnight_monitor.log`.

## Decision tree for morning

### If pooled Pearson IC ≥ 0.12 (unlikely based on fold 0):
→ Launch 8-ablation sweep via `./scripts/launch_ablations.sh` (has safety gate that checks for "PRIMARY PASS: YES").

### If 0.08 ≤ pooled Pearson < 0.12 (possible):
→ V4 beats Ridge but misses spec target. Discuss whether to:
  - Accept Pearson ≥ 0.08 as a pragmatic bar (V4 > V3 → real improvement)
  - Invest in tuning iteration: lower LR + longer training, or drop utility-rank loss
  - Regenerate NPZ with stride=60 (3× windows, matches V3 training density)

### If pooled Pearson < 0.08 (likely based on fold 0):
→ V4 as configured underperforms V3. Two paths:
  1. **Research path**: dig into why (feature noise? DUL loss hurting? stride too sparse?)
  2. **Production path**: revert signal to Ridge baseline, document V4 as negative learning

### Reviewer feedback status (from last night's code review)
- I1 fixed (commit 5201292) — `horizons_sec` in single-CSV path
- M2 fixed (commit e9dd576) — explicit TCN causality test
- I5 partial — `evaluate_baselines --horizon-key` added (commit 0af3106), but `run_baselines.py` and `LOBDatasetV2` default y still loose; defer.

## Quick commands for the morning

```bash
# Status
ssh -i ~/.ssh/runpod_ed25519 -p 40087 root@213.192.2.108 \
  "cd /workspace/quant_research && grep '^Epoch' logs/train_v4_full.log | tail -5 && ls experiments/v4_full/fold_*/test_results.json"

# Pooled IC from whatever folds finished
python scripts/aggregate_folds.py --exp-dir experiments/v4_full --out experiments/v4_full/SUMMARY.json --baseline-corr 0.099

# Baseline results (once complete)
cat experiments/baselines_v4/*.json  # on pod
```

## Honest take

V4 training loop is now correct, but the architecture + feature set as currently configured is NOT hitting the spec target on fold 0. That is the single most important fact. The 0.061 is a measured result, not a bug.

Whether to keep iterating on V4 vs cut our losses is a judgment call — one I deliberately did NOT make autonomously tonight.
