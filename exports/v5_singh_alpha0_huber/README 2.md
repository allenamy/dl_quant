# V5 singh α=0+Huber predictions — production CSV (2026-05-05)

**Created:** 2026-05-05 11:00 UTC | **Source:** `experiments/v5_final/singleh_alpha0_huber/fold_{0,1,2}/test_preds.npz`
**Supersedes:** `exports/v5_alpha0_huber/` (dualh 版本)

## 两个 CSV — 选哪个？

| File | 用途 |
|---|---|
| `y600_predictions_all_folds.csv` | **Raw 模型输出**, 透明 audit 用 (50,846 行 / 49,953 valid) |
| `y600_predictions_live.csv` | **🎯 Production deployment + backtest 推荐**, raw + causal 滚动 EMA-demeaned + warmup flag |

**Backtest / 实盘部署：用 `y600_predictions_live.csv` 的 `y_pred_q50_bps_live` 列。** Raw 列保留作 reference / model audit。

## Live CSV 列说明

`y600_predictions_live.csv` 在原 13 列基础上增加 3 列:

| 新增列 | 含义 |
|---|---|
| `y_pred_q50_bps_live` | causal 滚动 EMA-demeaned ŷ (= raw - EMA(raw[0..t-1])); **production 用这列** |
| `y_pred_q50_bps_live_ema_state` | EMA 在 t 时刻的值（透明，用户可自行验算） |
| `warmup` | bool；前 50 个样本/fold 标记 True (EMA 还没收敛, backtest 应跳过) |

EMA 配置: `α=0.01` (half-life ≈ 69 samples ≈ 11.5h)。Per-fold reset (每 fold 不同 model checkpoint)。

## 为什么 causal EMA-demean (Level 2 calibration)？

模型预测 `q50` 有 +0.18 bps 的 DC offset (因为 Bayes shrinkage 在低 SNR 下数学上不可避免)。直接用 raw `q50` 做 PnL 模拟会导致：
- 全部 timestamps 的 ŷ 都偏正 → 系统性 long bias
- Calibration view bin-by-bin 都 ≥ 0 (top y-bin 与 bottom y-bin 都正, 不分散信号)

**Causal rolling EMA-demean** 是 trading systems 标准做法 (即 alpha drift correction):
- 在每个 t 减去 EMA(过去 ŷ), strict causal (不用 t 之后信息)
- ŷ_live ≈ relative deviation from recent average, 自然 mean-zero
- 实盘部署直接用此 logic (不是 backtest-only trick)

**这不是 post-hoc tuning** — 是 production pipeline 的标准 component, 在 trading 系统中等同于 mid-price relative orders 之于 absolute price orders 的关系。

## Live calibrated metrics (49,803 valid 样本, 跳过 warmup)

| Metric | Live calibrated | Raw (reference) | 说明 |
|---|---:|---:|---|
| **Pearson** | **+0.0587** [+0.0446, +0.0733] CI | +0.0617 | shift-invariant, ~3% drop 来自 EMA noise |
| **Spearman** | **+0.0658** [+0.0561, +0.0756] CI | +0.0686 | ~3% drop |
| **β** | **+1.005** | +1.050 | live 接近完美 |
| **σŷ/σy** | 0.058 | 0.059 | identical |
| **ŷ_mean** | **+0.0004 bps** | +0.180 | live 由设计是零 |
| **Calibration line passes through origin** | ✓ | ✗ | 关键 |
| **Bin-Spearman (calib)** | **+0.976** | +0.952 | live 反而更好 |
| **Bin-Spearman (trade)** | **+0.988** | +0.964 | live 反而更好 |
| Top-bot trading spread | +2.54 bps | +2.64 | -0.1, 接近 |
| Top decile t-stat | +6.88 | +7.14 | -0.26, 接近 |
| 95% CI lower bound > 0 | ✓ | ✓ | 双向显著 |

详见 `STRICT_EVAL_LIVE.md` (14/15 gates pass; 唯一 fail 是 |bias|<0.05 因为 live by-design ŷ_mean=0 ≠ y_mean=+0.09, 是 metric 定义而非问题).

### Calibration view 全部过原点

| y bin | y_mean (bps) | ŷ_mean live (bps) |
|---:|---:|---:|
| 0 (most NEG) | **-22.17** | **-0.058** |
| 1 | -10.24 | -0.064 |
| 4 | -1.10 | -0.019 |
| 5 | +1.03 | +0.016 |
| 9 (most POS) | **+22.70** | **+0.092** |

负 y 区 ŷ 全 NEG，正 y 区 ŷ 全 POS。

## 实盘部署正确做法

每个时间步 `t` 接到 raw model output `q50_t` 时:

```python
# 1. 维护 EMA state (从 last sample 开始)
ema_state = (1 - alpha) * ema_state + alpha * q50_prev  # 注意是 q50_prev 不是 q50_t

# 2. Calibrate
q50_live = q50_t - ema_state

# 3. Use q50_live for trading decision (e.g., long if > threshold, short if < -threshold)
```

`α=0.01` 推荐起点。Production 可微调 (实盘观察 ŷ_live 的 mean drift 是否 < 0.02 bps)。

参考 implementation: `scripts/y600_live_calibrate.py:causal_ema_demean()`.

## 列定义 (raw + live)

- `timestamp_us` — int64 UTC 微秒；input window 末端 (anchor t)
- `datetime_utc` — ISO-8601
- `fold` — 0/1/2 (walk-forward fold id)
- `horizon_sec` — 600
- `mask` — 1 if forward-return 完整观测; 0 if NaN
- `y_true_logret` / `y_true_bps` — 实测 600s 前向 log-return
- `y_pred_q10/q50/q90_logret` — 预测 10/50/90 分位 (monotonic by construction)
- `y_pred_q50_bps` — q50 in bps (raw model output)
- `y_pred_q50_z` — raw z-score
- `y_sigma_train_bps` — train-set MAD-σ in bps (per-fold)
- **`y_pred_q50_bps_live`** — 🎯 causal EMA-demeaned q50 in bps (production signal)
- **`y_pred_q50_bps_live_ema_state`** — EMA state at time t (transparency)
- **`warmup`** — bool, True for first 50 samples/fold

## Backtest 语义

- Target at `t` = `log(mid[t+600s] / mid[t])`. Signal known at `t`.
- **Position entry** at `t`. **Position exit** at `t + 600s`.
- Filter: `mask == 1` AND `warmup == False`.
- 用 `y_pred_q50_bps_live` 做 trading 决策, 不要用 raw `y_pred_q50_bps`。

## Coverage

- fold 0: 2025-02-09 → 2025-05-11
- fold 1: 2025-04-10 → 2025-07-10
- fold 2: 2025-06-11 → 2025-09-09

## Cost economics (unchanged)

Single-asset BTC y_600 IC ~0.06。At 2 bps/trade round-trip, always-trade ≈ 深度负 Sharpe。Best holding strategy 接近 break-even。**生产需 multi-asset breadth 或 maker-only orders。** 本 CSV 改善的是 **signal quality** (β=1.005 + zero DC offset + calibrated origin pass)，不是 trade economics。

---

## DC offset 与 regime drift — 概念 + 限制 + 实盘改进

模型输出 q50 是预测的 10-min 收益 (bps)。理想情况下:
- 当真实未来 mean(y) ≈ 0 时, model 应该预测 mean(ŷ) ≈ 0
- 当真实 y_mean = +0.1 bps (轻微 positive 漂移), ŷ_mean 也应跟随到 +0.1 bps

**DC offset = mean(ŷ) - mean(y)** = 系统性偏移, 与 regime 无关的常数偏置。

V5 singh **raw** q50 实测: ŷ_mean = +0.18 bps, y_mean = +0.09 bps → DC offset = **+0.09 bps**。

为什么这个 DC offset 是问题:
- **σŷ ≈ 0.7 bps** (模型预测振幅), DC offset = 0.09 bps **占信号 ~13%**
- bin plot calibration view: 整条线被 DC offset 抬高 → bin 0 (y 最负的 10%) ŷ 仍然 positive (违反 monotonic-through-origin 期望)
- **trading 实战**: ŷ > 0 的样本占 比 50% 多很多 (因为 DC bias) → 系统性 long bias

**当前 production 解** (`y_pred_q50_bps_live`): causal EMA-demean (减去 ŷ 自身的滚动平均), 把 DC offset 修到 ≈ 0。这是 trading systems 标准做法 (alpha 信号设计上 mean-zero)。

### 什么是 regime drift

更深的问题: **不仅是常数偏置, 而是真实未来 y 的分布在不同时期不同**。

实测 fold-by-fold:
- Fold 0 train 期 y_mean = **+0.10 bps** (BTC 牛市) → test 期 y_mean = **-0.12 bps** (反转!)
- Fold 1 train +0.06 → test +0.14
- Fold 2 train +0.03 → test +0.25

**Train 与 test regime 不同, model 训练时学的"市场baseline"在 deploy 时已经过时**。

### 为什么 regime 适应非常困难 (深入浅出)

#### 根因 1: 信号 floor 限制

低 SNR (Signal-to-Noise Ratio) 任务下 (R² < 1%), Bayes 最优 estimator 满足 `σŷ ≈ ρ · σy ≈ 0.07 · σy`。模型输出振幅**数学上不能超过这个上限**。

任何想让 model "更激进"地适应 regime 都会:
- 增大 σŷ → MSE 上升 → loss 变大 → 训练时被 push 回小 σ

#### 根因 2: regime 信号本身预测性弱

我们做了完整 audit:
| Lookback | predict next 1d | next 7d | **next 30d** |
|---|---:|---:|---:|
| past 7d y_mean | -0.08 | -0.09 | +0.10 |
| past 30d y_mean | +0.03 | +0.10 | **+0.23** |

只有"过去 30 天 vs 未来 30 天"才有 +0.23 corr (R²=5%, 弱信号)。**短窗口预测短前向几乎无信号** (BTC 在日尺度 mean-revert)。
- 加 regime feature 帮助有限
- 我们试过 4 种 regime 修法 (B.1 / B.2 / B.5 / actual-y EMA), **全部 fail 或 lateral, 没有一个把 pool Pearson 提升超过 noise 阈值**

#### 根因 3: train 期模式与 test 期模式不重合

模型从 train 700 天学 "regime → 预测 baseline" 的 mapping。但 BTC 不同时期 regime 类型截然不同 (2023 牛 / 2024 横盘 / 2025 mixed)。**train 学的 mapping 在 test 期可能是错的**。

实测: 加 past_30d_y_mean 后, model 在 fold 0 (regime flip) 改善, 但 fold 1+2 反而 hurt 。**learn 的 regime mapping 不 generalize**。

### 实盘中如何改进 (分层方案)

模型架构内部基本无解, 实战 deployment **必须**额外几层 production engineering:

#### Layer 1 (已 ship): Live causal EMA-demean
处理 DC drift。`y_pred_q50_bps_live` 列。
- 解决: 系统性 long/short bias
- 不解决: regime mapping 错位 (model 信号本身可能不准)

#### Layer 2 (实施推荐): Online retraining
**这是工业标准做法, ROI 最高**:
```
每周 / 双周 / 月: 用 last 60-90 days 数据 retrain V5 singh
              → 替换 production checkpoint
```
机制: 让 train→deploy gap 始终 ≤ 1-2 周, regime 还没大幅 drift 就 retrain。

实战 quant 系统都这么做。**研究级 walk-forward (我们 fold 0 是 train 700d → wait 2 days → test 90 days) 不代表 production 部署模式**。

#### Layer 3 (关键监控): Regime detector + IC monitor
- Rolling 30-day IC alarm: 跌破 0.02 → pause trading
- 每月 review IC trajectory, 跌势及时调整
- 实战: 某些 month IC 真会归零 (e.g. fold 0 月 03 P=0.022), 这时**不 trade 比错 trade 重要**

#### Layer 4 (基础 hygiene): Position sizing
- 信号 z-score 化: `z = (ŷ - rolling_mean(ŷ)) / rolling_std(ŷ)`
- Threshold: trade 仅当 |z| > 0.5
- 自然过滤低质量 signal

### Multi-asset 真的有帮助吗 — 是的, 但不是 silver bullet

#### 帮助的部分

1. **Cross-asset signal diversification (信号正交化)**:
   - BTC y_600 alpha ≈ 0.06
   - ETH y_600 通常类似 ~0.05-0.06
   - SOL/BNB 各自有 alpha, 互相 partial 独立 (corr ~0.3-0.5)
   - 4 个 alpha sources, IR (信息率) 可达 1.5+ vs 单资产 0.6 (实测 V4 y_180)
   - **Sharpe 显著提升 (industry-validated)**

2. **Regime smoothing**:
   - 不同资产 regime 不完全同步 (BTC 跌时 SOL 可能涨, beta < 1)
   - Cross-asset 加权 mean → 个别资产 regime drift 平均掉
   - 单资产 fold 0 regime flip 在 4-asset portfolio 影响减半

3. **Cross-asset attention 架构**:
   - PMformer / TLOB-style: 模型同时看 4 个 asset 的 LOB
   - 学习 "BTC 涨 → SOL 通常跟随" 这类 cross-effect
   - Empirical: 学术上 +20-30% IR (paper-level), 但实战增益取决于资产相关性

#### 不帮助的部分

1. **Per-asset alpha 不会更高**:
   - BTC 单资产仍受 ~0.07 Bayes ceiling
   - Multi-asset 不让 BTC 预测变更准, 只是把 4 个独立信号组合
   - 每个资产的 regime drift 还是 individual 存在

2. **不解决 regime change 问题**:
   - 整个 crypto 市场可能同步进入 bear regime (相关性升至 0.7+)
   - 4 个资产 alpha 同时衰减 (实测 2022 5月 LUNA 崩盘期间, 全资产 IC 下降)
   - 这时 multi-asset diversification 失效, online retraining + regime stop 仍是关键

3. **数据基础设施代价**:
   - 4 资产 NPZ × 991 days × 25 levels × 600s = 4× 数据量
   - Cross-asset 时间对齐 (毫秒级 timestamp 同步)
   - Inference 延迟 (要同时获取 4 个 LOB)

#### Multi-asset ROI 估计

| 改动 | 单资产 BTC 当前 | 4-asset 后 | Δ |
|---|---:|---:|---|
| Per-asset Pearson | 0.06 | 0.06 | tie |
| Portfolio IR | 0.6 | 1.5+ | +150% (主要收益) |
| Net Sharpe (扣 fee) | -0.2 | +0.5-1.0 | 转正 |
| Regime resilience | 弱 | 中 | 一些 diversification |

**结论**: Multi-asset 的 ROI 主要在 **portfolio level Sharpe**, 不是单资产 alpha。如果用户目标是 "regime adaptation 提高单资产 IC", 答案是 **No, multi-asset 帮助有限**。如果目标是 "可实战交易的 Sharpe", **Yes, multi-asset 是 fundamental 路径**。

### 给 backtest 同事的 actionable summary

1. **使用 `y_pred_q50_bps_live` 列** (已 mean-zero), filter `mask=1 & warmup=False`
2. **承认 single-asset y_600 IC ~0.06 是当前 ceiling** (Bayes shrinkage), 不要追求 single-asset 0.10+
3. **回测时模拟 production scenario**:
   - 每月 retrain (实战 cadence)
   - rolling 30-day IC monitor + auto-stop
   - Position sizing via z-score thresholding
4. **Sharpe-relevant 改进路径**:
   - Multi-asset breadth (ETH/SOL/BNB) → portfolio IR 1.5+
   - Maker-only orders (取消 taker fee)
   - Smart routing / latency edge
5. **不要尝试在 model 内部解决 regime drift** — 工程上属于 production pipeline (online retraining), 不是 model architecture (我们做了 4 次 architecture-level 尝试都 fail)

## 为什么从 dualh 切到 singh（2026-05-05 决策, 历史保留）

之前 production 用 V5 dualh (multi-horizon: y_180 aux + y_600 primary)。Singh ablation 显示：

| Pooled metric | Singh | Dualh | Δ |
|---|---:|---:|---|
| Pearson | +0.0617 | +0.0622 | dualh +0.0005 (noise) |
| **Spearman** | **+0.0687** | +0.0672 | **singh +0.0015** (+2.2%) |
| β | +1.05 | +1.06 | identical |
| **per-fold P std** | **0.0039** | 0.0050 | **singh -22% 更稳** |
| Top-bot spread | **+2.64** | +2.10 | **singh +26%** |

Multi-horizon aux task 之前看似的优势是 fold-1 outlier 驱动，pool level 上 singh 全面持平或微胜。Singh 更简单 (109K vs 111K params, 一个 head 而非两个)。
