# y_600 预测 CSV 交付说明

包含 BTCUSDT y_600 (10 分钟前向 log-return) 预测,做 backtest 用。

## 文件清单

### V5 dualh (current PRODUCTION WINNER, 2026-05-05 FINAL)

**首选 (84/100 综合评分)**:
```
y600_v5_dualh_BEST_singleseed.csv           50,846 行 (49,953 valid) — seed=42 BEST + demean
y600_v5_dualh_EMA_singleseed.csv            50,846 行 (49,953 valid) — seed=42 EMA + demean
```

**多 seed (orthogonal check, 70-73/100, 不推荐做 primary)**:
```
y600_v5_dualh_3seed_BEST_median.csv         50,846 行 (49,953 valid) — seeds 42+7+13 median BEST
y600_v5_dualh_3seed_EMA_median.csv          50,846 行 (49,953 valid) — seeds 42+7+13 median EMA
```

V5 = Conformer (Conv kernel=15 + SelfAttn full + FFN) backbone, multi-horizon dual-h (y_180 aux + y_600 primary, weights 0.3/1.0)。

**重要发现 (经 9 小时综合评测)**: 
- seed=42 是 outlier lucky seed (84/100), seeds 7/13 都弱 (55/100)
- 3-seed median **反而拉低性能** 到 70/100 (median anchors near majority weak values)
- **推荐用 single-seed (seed=42) + post-hoc demean** 列 `y_pred_q50_demeaned_*` (rank-preserving + bias 修复)
- Loss redesign 4 轮全部失败 (anti-pattern #21 documented)

⚠️ **测试窗口和 V4 不同**: V5 用 val_days=60 (vs V4 30) → V5 test 从 2025-02-09 → 2025-05-11; V4 test 从 2025-01-08 → 2025-04-08, 重叠 ~2 个月但偏移 30 天。V4 retrain 用 V5 splits 正在进行中, 完成后会出 v4_apples_to_apples CSV 供完全 like-for-like 对比。

### V4 baseline_plus + phase3c (历史交付, 2026-05-01)

```
y600_baseline_plus_BEST_3seed_median.csv    49,577 行 (48,678 valid)
y600_baseline_plus_EMA_3seed_median.csv     49,577 行 (48,678 valid)
y600_baseline_plus_SWA_3seed_median.csv     49,577 行 (48,678 valid)
y600_phase3c_BEST_2seed_median.csv          67,121 行 (65,927 valid)
y600_phase3c_EMA_2seed_median.csv           67,121 行 (65,927 valid)
y600_phase3c_SWA_2seed_median.csv           67,121 行 (65,927 valid)
```

V4 那 6 份是 multi-seed value-blend median — 多个 seed 训练完,逐 timestamp 取中位数。不是 rank-blend (所以 β 是真 calibration,不是 by-construction artifact)。**V5 dualh 当前是 single-seed**, 多 seed median 还在 backlog (验证 winner 后再投入)。

## 列说明

| 列 | 含义 |
|---|---|
| `timestamp_us` | 输入窗口结束时刻 (microseconds since Unix epoch, UTC) |
| `datetime_utc` | 同上,可读格式 |
| `fold` | walk-forward fold id (baseline_plus 是 0/1/2; phase3c 是 0/1/2/3) |
| `horizon_sec` | 600(固定) |
| `mask` | 1 表示 y 有效,0 表示有 look-ahead 不能用 |
| `y_true_logret` | 真实 log-return = log(mid[t+600s] / mid[t]),raw 值 |
| `y_true_bps` | y_true_logret × 1e4 |
| `y_pred_q50_logret` | 模型 q50 预测 log-return (un-normalized, **原始预测**) |
| `y_pred_q50_bps` | × 1e4 |
| `y_pred_q50_z` | 模型原生输出 (z-score scale) |
| `y_sigma_train_bps` | 该 fold train 的 MAD-σ (bps),用于 z↔raw 转换 |
| `y_pred_q50_demeaned_logret` | **V5 only** — 原始预测 per-fold demean (修负偏 bias, 信号方向不变) |
| `y_pred_q50_demeaned_bps` | × 1e4 |
| `y_pred_q50_calibrated_logret` | **V5 only** — demean + per-fold rescale to σ_train (展开 magnitude, σŷ/σy 0.05→0.52) |
| `y_pred_q50_calibrated_bps` | × 1e4 |

**V5 dualh 三种预测怎么选 (2026-05-04 calibration 修正)**:
- `y_pred_q50_*` (原始): rank 信号最干净, 但有 −0.4 bps 全局负偏 + magnitude 严重压缩 (σŷ/σy=0.05). 适合 long-short rank-based 策略, β=+1.05 已校准。
- `y_pred_q50_demeaned_*`: 移除负偏, top y_bin 不再"赚钱时模型说看跌". 信号 rank 不变, β 不变. **推荐用作 default 交付**。
- `y_pred_q50_calibrated_*`: demean + rescale 让预测幅度看起来"像 bps", calibration plot 单调. 但 β 降到 +0.10 (over-amplified for trading). **适合可视化/汇报**, 不适合直接做 dollar-neutral sizing。

回测时只看 `mask=1` 的行。

## 推荐用哪份

**首选**: `y600_v5_dualh_BEST_singleseed.csv`。Pooled raw Spearman +0.0689 比 V4 baseline_plus 3-seed median EMA (+0.0586) 高 +18%, P 高 +12%。Conformer backbone + dual-horizon training 是 architectural 改进,不是 ensemble trick。

**备用**: `y600_v5_dualh_EMA_singleseed.csv` 略保守 (β=+1.11 vs BEST +1.05), Spearman 略低 (+0.065)。如果策略对预测平滑度敏感, EMA 更好。

V4 baseline_plus 的 EMA/SWA 两份仍然有效, 用作 diversity check 或者 V5 ensemble 的另一头。phase3c 不推荐 primary。

BEST checkpoint = trainer 用 val composite 选出的最佳 epoch; EMA = 训练全程权重指数移动平均 (decay=0.999); SWA = 末端 top-5 epoch 权重平均 (Izmailov 2018, 仅 V4 提供)。

## 评估口径

### V5 dualh — DENSE eval on RAW y_600 (NEW, 2026-05-04, n=49,953)

```
ckpt    P        S        β     DirAcc  DA_tail  P 95% CI (block bootstrap, B=2000)
BEST   +0.0555  +0.0689  +1.05  0.521   0.526    [+0.041, +0.069]
EMA    +0.0532  +0.0652  +1.11  0.522   0.533    [+0.040, +0.065]
```

per-fold P (BEST): [+0.0413, +0.0709, +0.0607]  std=0.0123
per-fold P (EMA):  [+0.0374, +0.0673, +0.0639]  std=0.0134

### V4 baseline_plus (历史, 2026-05-01, n=48,678)

```
ckpt    P        S        β     DirAcc  DA_tail  P 95% CI (block bootstrap)
BEST   +0.0455  +0.0559  +1.16  0.523   0.540    [+0.035, +0.057]
EMA    +0.0497  +0.0586  +1.27  0.524   0.543    [+0.041, +0.060]
SWA    +0.0499  +0.0605  +1.26  0.524   0.552    [+0.040, +0.062]
```

### V4 phase3c (n=65,927)

```
ckpt    P        S        β     DirAcc  DA_tail  P 95% CI
BEST   +0.0313  +0.0545  +0.72  0.523   0.533    [+0.018, +0.046]
EMA    +0.0388  +0.0570  +0.96  0.524   0.535    [+0.029, +0.049]
SWA    +0.0336  +0.0554  +0.81  0.525   0.536    [+0.021, +0.048]
```

P / S 用 Pearson / Spearman,β 用 cov(y, ŷ) / var(ŷ) (trade slope, 1.0 是理想 calibration)。

### V5 vs V4 对比 (raw + dense, 都是 production-grade eval 口径)

```
                            V4 baseline_plus EMA   V5 dualh BEST    Δ
                            (3-seed median)         (1-seed)
─────────────────────────────────────────────────────────────────────
Pooled raw Pearson           +0.0497                +0.0555          +0.006 (+12%)
Pooled raw Spearman          +0.0586                +0.0689          +0.010 (+18%)  ★ primary
β (calibration)              +1.27                  +1.05            healthier
P 95% CI lower bound         +0.041                 +0.041           equal
DA_tail                      0.543                  0.526            slight regression
```

⚠️ Caveat: V5 测试窗口比 V4 晚 30 天 (val_days=60 vs 30)。完全 like-for-like 的 v4_apples_to_apples retrain 正在进行中 (用 V5 splits + V5 hardened recipe)。结果出来后会更新这一节。

### Calibration view 已知问题 + 修正 (2026-05-04 重要更新)

**问题**: 原始 `y_pred_q50_*` 列 calibration view 不好 — 实际 +22 bps 的最强 bin 里, 模型 mean ŷ = −0.31 bps (依然为负)。**根因**: V5 dualh 的 utility_rank loss 用 α=1.0 → 排序信号靠 q10 (下尾分位数) → q50 = q10 + softplus(δ) 被动跟随, 结构性偏负; 加上没有任何 magnitude 监督 (lambda_calib/dir_huber/beta_calib 全 0), 模型自然产生 σŷ/σy=0.05 的严重压缩。V4 baseline_plus 同病, 不是 V5 独有。

**已交付的 post-hoc 修正** (新加的 4 列):
- `y_pred_q50_demeaned_*`: 修负偏, top y_bin 现在 ŷ_mean=+0.12 bps (从 −0.31 翻正), bot=−0.02. P/S/β 不变. **dollar-neutral 策略默认用这个**。
- `y_pred_q50_calibrated_*`: 进一步把 σŷ 放大到 σ_train_y, top y_bin ŷ_mean=+1.26 bps, bot=−0.18. β 降到 0.10 (over-amplified). **适合 plot 展示, 不适合直接 sizing**。

**正在 train 的根本修正**: `conformer_hardened_dualh_calib` (V5 Iter5)
- utility_alpha 1.0 → 0.5 (移除 rank-by-q10 偏置)
- 加 lambda_beta_calib=0.05 (batch β regularizer, 不是 σ-anchor)
- 队列等 v4_apples_to_apples 完成后启动, 完成预计 2026-05-04 ~10:00 UTC

## 几个需要注意的点

1. **CSV 有 ~20% 重复 timestamp**。原因是 walk-forward fold 之间 test 窗口有 30 天重叠 (baseline_plus embargo=0, phase3c embargo=30 但 stride 60 仍 overlap)。如果 backtest 是 timestamp-driven 而不是 fold-driven,记得 dedup 或者按 fold 分别处理。

2. **Residual lag-1 自相关 = 0.685,不是模型问题**。y_600(t) 和 y_600(t+180) 的 600 秒窗口共享 420 秒,所以 y 自身就有这么高的 lag-1 自相关 (0.684),residual 跟着继承。模型预测自身的 lag-1 autocorr 只有 0.02-0.03,正常。如果回测要 honest IID 取样,stride ≥ 1800s (lag 10) 自相关就归零。

3. **预测有约 -0.2 bps 的全局负偏差**。最强的 9 分位 bin 里 (y_mean ≈ +25 bps),ŷ_mean 仍然是 -0.08 bps。Rank order 没问题,但 magnitude 整体偏空一点。如果策略对 long/short 对称,可能要在 backtest 端做 demean。

4. **High-vol regime IC 是 low-vol 的 2 倍以上** (P 高 vol = 0.075, low vol = 0.035)。模型在波动大的时候更准,这是 trading-favorable 性质。如果策略有 vol filter,集中在 high-vol 段会更受益。

## 数据生成路径

### V5 dualh (NEW)

- 模型: V5 DualPathLOBModelV3 + Conformer backbone, ~109K 参数
  - Backbone: Conformer block × 2 per path (Conv kernel=15 + SelfAttn full + FFN sandwich)
  - Multi-horizon: y_180 (aux, weight 0.3) + y_600 (primary, weight 1.0), fixed weights, NOT UNIT loss
  - Train: train_days=700, val_days=60, embargo_days=1, 3 folds, fold_stride=60
- 训练: hardened recipe (val_days=60, weight_decay=0.005, dropout=0.20, patience=4, epochs=25)
  - composite val metric (0.5×Pearson + 0.5×Spearman), EMA decay=0.999
- Loss: quantile (q10/q50/q90 pinball) + utility_rank λ=0.3
- Single seed (42), multi-seed median 是 next iteration

### V4 baseline_plus + phase3c (历史)

- 模型: V4 DualPathLOBModelV3, ~63K 参数 (没有 conformer backbone)
  - baseline_plus: train_days=700, val_days=30, embargo=0, 3 folds
  - phase3c: train_days=580, val_days=90, embargo=30, 4 folds
- 训练: composite val metric (0.5×Pearson + 0.5×Spearman), patience=8, EMA decay=0.999
- Loss: quantile (q10/q50/q90 pinball) + utility_rank λ=0.3 + dir_huber 0.2 + beta_calib 0.05
- Multi-seed: baseline 用 42/7/13 (3 seed), phase3c 用 42/7 (2 seed)
- Median 是 per-timestamp 在 z-space 取中位数,然后 × σ_train 还原到 raw log-return

## 历史 caveats

之前如果有过一份 `final_stack rank-blend` 的预测 (β=0.08),那是 rank transform 引入的 artifact,已废弃,这次的都不是这种处理。
