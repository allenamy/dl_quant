> **创建:** 2026-04-29 16:10 UTC+8 (00:10 UTC) | **Session:** y600-overnight-pivot
> **关键事件:** Adversarial review 揭示 calib + multi-seed 路径结构有问题; kill 当前 overnight; 证实 y_180 per-fold β 健康, y_600 fold 2 sign-flip 是结构问题。
> **上一版本:** docs/Y600_FUTURE_TESTS.md (2026-04-28 12:18 UTC) — 已 superseded
> **状态:** final | **作废条件:** 后续 multi-asset 或 y_180 productionization 启动后归档

# y_600 Path 决策: 终止 calib 探索, 转向 y_180 productionization

## TL;DR

**y_600 has a structural fold 2 sign-flip (β=-0.09).** No training tweak (calib, dir_huber, multi-seed) and no post-hoc fix (rolling β rescaling) can rescue it. The horizon × test-regime combination is fundamentally hard.

**y_180 does NOT have this problem.** Per-fold β [1.75, 0.95, 0.91], pooled β=1.19, all directionally correct, P/S 2× higher than y_600. 真正 production-ready, not a pooled-metric illusion.

**Decision:** Stop y_600 calib exploration. Pivot to y_180 productionization (paper trading, cost-aware backtest) and / or multi-asset cross-section (ETH/SOL/BNB) as documented in CLAUDE.md.

## 关键数据 (2026-04-29 重新计算)

### y_180 V4 baseline (canonical stride10 pool)

| | Pearson | Spearman | β | σŷ/σy |
|---|---:|---:|---:|---:|
| fold 0 | 0.110 | 0.114 | 1.75 | 0.063 |
| fold 1 | 0.082 | 0.084 | 0.95 | 0.086 |
| fold 2 | 0.076 | 0.106 | 0.91 | 0.084 |
| **POOLED** | **0.091** | **0.099** | **1.19** | — |

**β-stable, no sign-flip, IC consistent across folds.** This IS production-ready.

### y_600 V4 baseline + SWA (canonical stride10 pool)

| | Pearson | Spearman | β | σŷ/σy |
|---|---:|---:|---:|---:|
| fold 0 | 0.079 | 0.103 | 1.96 | 0.040 |
| fold 1 | 0.066 | 0.076 | 1.38 | 0.048 |
| fold 2 | -0.005 | 0.034 | **-0.09** | 0.057 |
| **POOLED** | **0.047** | **0.068** | **0.98** | — |

**fold 2 sign-flip.** Pooled β=0.98 is the average of {1.96, 1.38, -0.09}. Trading semantics meaningless — at any given time, real-time β is regime-dependent and could be negative.

### y_600 + calib + multi-seed (overnight kill 之前)

- seed=42 (Track-A2): per-fold β {1.73, 1.38, **0.16**}, pooled P=0.043 S=0.056 β=0.79
- seed=7: per-fold β {2.21, **0.16**, 0.27}, pooled P=0.039 S=0.054 β=0.87
- 所有 calib seed fold 2 都 β<0.3 — **calib 损失没解决 fold 2 问题**

### y_600 post-hoc affine rescaling (本地 2026-04-29 测试)

用 fold 内 test 第一半 fit β + α, 应用到第二半:

| Mode | fold 0 β (raw → calib) | fold 1 β | fold 2 β |
|---|---|---|---|
| BEST | 0.37 → 0.15 | 1.13 → 0.89 | -0.19 → **-0.36** |
| SWA | 1.27 → 0.46 | 1.24 → 0.82 | -0.39 → **-2.16** |

**Post-hoc 校准 amplify 了 fold 2 sign-flip** (-0.39 → -2.16). 因为 val 拟合的 β 系数是正,应用到 test 的负 β 数据上方向错乱。

**结论 (硬数据): fold 2 sign-flip 是 y_600 horizon × test regime 的结构性失效, NOT 模型问题, NOT 损失问题, NOT calibration 问题。**

## 为什么之前没看到这个

1. **错误 anchor:** 之前长期引用 "V4 baseline+SWA P=0.066 S=0.079 β=1.34" 作为 bar — 这其实是 fold 0 单独的指标, 不是 pooled。今天重算才发现 pooled 是 0.047/0.068/0.98 with fold 2 sign-flip。Anchor 错了导致所有比较 calibration 失败的 narrative 都错。
2. **Pool definition 混乱:** stride_every=3 vs canonical 10。导致中间 stage A/B "pass" 实际上没 pass。
3. **Aggregate metric 偏见:** Pooled β=0.98 看起来"接近 1.0" 是 fold 2 负 β 与 fold 0/1 高 β 抵消的算术假象, 不是真实可交易性质。这就是 anti-pattern #16 的原型。

## 9h pod time 烧掉换来的(也算)

虽然 calib + multi-seed 计划 abandoned, 但学到:

1. **pooled β 是 aggregation 假象** — 单独不可信, 必须 per-fold 配合
2. **dir_huber alone** 不行 (σ collapse, β=44)
3. **beta_calib alone** 不稳定 (single seed Track-A2 + seed=7 都 fold 2 β<0.3)
4. **post-hoc affine** 在 fold 2 sign-flip 时反而放大错误
5. **y_600 fold 2 是结构问题** — 任何 single-asset training/loss 调参都不能解决
6. **y_180 pooled metric 是真实的** (per-fold β stable, IC pooled 不是 average-cancel)

## 推荐下一步 (按优先级)

### P0: y_180 productionization (最高 ROI)

y_180 V4 baseline 已经 P=0.091 S=0.099 pooled, per-fold β stable, σŷ/σy ~ 0.07-0.09 (足够 trading sizing). 缺的是 production infrastructure:

- **Paper trading**: 单资产 BTCUSDT y_180 实盘模拟, real-time inference + position sizing
- **Cost-aware backtest**: 已有 final_stack 结果, 在 y_180 重新跑 holding strategies (EMA + hysteresis + min-hold) 用真实 BNB fee + slippage
- **Bin-plot 校准诊断** + tail DirAcc + regime-stratified IC

ETA: 1-2 日, 主要 local CPU work.

### P1: Multi-asset cross-section (CLAUDE.md "唯一 fundamental 杠杆")

per CLAUDE.md current priority: "**多资产 breadth — ETH/SOL/BNB data, cross-asset factor, IC-IR 可 1.5+**"

Cross-section setup:
- 4 asset (BTC + ETH + SOL + BNB) y_180 同时预测
- Daily 4-quintile rebalance (top quintile long, bottom short)
- Sharpe expected 1.0-1.5+ (cross-section IC-IR > single-asset IC due to risk diversification)

ETA: 需新数据 (3 asset NPZ build), 然后 retrain. 1 周.

### P2: y_600 重新评估 (但不是高 priority)

如果未来要回 y_600, 必须先解释 fold 2 sign-flip 机制:
- Fold 2 是哪个时段? 什么 vol regime?
- Train 期间 (2023-2024) 该 regime 见过吗? 还是 unseen?
- 如果是 unseen distribution shift: 需要 regime-conditioned 模型 / 更大训练窗口
- 如果是 seen 但权重低: 加 regime adversarial training

但这都不如 y_180 productionization 有杠杆。**不推荐 short-term。**

### Hard NO

- ❌ 继续 calib loss 变种 (V1/V2/V3 三轮失败 = 损失形式错, 不是参数问题)
- ❌ multi-seed 在 y_600 上更多 (median 修不了 fold-conditional sign-flip)
- ❌ post-hoc β rescaling 在 y_600 上 (会放大 fold 2 错误)

## Anti-pattern 更新 (已写入 CLAUDE.md)

**#16 (NEW): Pooled β masks per-fold sign-flip — 必须双轨报告 (pooled + per-fold β)**

详细见 CLAUDE.md.

## Files of record

- `experiments/v4_noattn_700d/fold_{0,1,2}/test_preds.npz` — y_180 baseline (production candidate)
- `experiments/v4_noattn_700d_y600/fold_{0,1,2}/{test_preds.npz, swa_test_preds.npz}` — y_600 baseline (rejected for production due to fold 2 sign-flip)
- `experiments/y600_calib/baseline_calib/fold_{0,1,2}/` — Track-A2 calib (rejected)
- `experiments/y600_multiseed_calib/calib_seed7/fold_{0,1,2}/` — seed=7 calib (rejected)
- `/tmp/y600_post_hoc/` — local post-hoc rescaling test data (transient)
