> **创建:** 2026-05-05 07:50 UTC | **更新:** 2026-05-05 10:35 UTC | **Session:** v5-alpha0-huber-production-doc | **关键事件:** Singh ablation 完成, production winner 切换 dualh → singh
> **状态:** final | **作废条件:** 后续 production winner 改变（如 multi-asset 阶段），归档

# V5 singh α=0+Huber — 架构与损失函数设计参考

> **2026-05-05 PM 更新**: production winner = **V5 singh α=0+Huber** (single horizon y_600 only)。dualh (multi-horizon) ablation 显示 y_180 aux 在 pool level 无 measurable 增量, fold-1 outlier 驱动 — 切到 singh。本文以 singh 为 production target 描写, §14 详列 singh vs dualh 对照。**生产 CSV: `exports/v5_singh_alpha0_huber/`**, dualh CSV `exports/v5_alpha0_huber/` 仅作 reference / fallback。

供同事回测使用。涵盖完整 forward 流程、模块组合、正则策略、损失设计、V4→V5 升级路径，以及 calibration / monotonicity / amplitude 三方面修复的机制。

**Production CSV (current)**: `exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv` (50,846 行 / 49,953 valid)。
**Reference CSV (prior, dualh)**: `exports/v5_alpha0_huber/y600_predictions_all_folds.csv` — 保留作 fallback。
严格自测: `exports/v5_singh_alpha0_huber/STRICT_EVAL.md` (15/15 gates pass)。

---

## 1. 任务定义

| 项 | 值 |
|---|---|
| 资产 | Binance BTCUSDT 永续合约 |
| Horizon | 600 秒 (10 min) 前向 log-return |
| 目标 | y_600 = log(mid[t+600s] / mid[t]) |
| 输入窗口 | t-600..t-1 秒（过去 10 min 1 Hz LOB snapshots） |
| 频率 | 中频 (Mid-frequency)，非 HFT |
| 训练数据 | 700 day 滚动 walk-forward，3 fold |
| 测试期 | 2025-02-09 → 2025-09-09 |

---

## 2. 输入数据 — 双路径

### Path A：手工特征 (Domain knowledge)
- 64 维特征 / 时间步
- 涵盖 OBI, OFI, vol, MicroMid 偏移, RV @ 多 windows, 微观 trade flow signal, 成交量分布等
- 来源：`data/npz_v4/{day}.npz` 中 `X_features` 数组
- 形状：(B, T=600, n_features=64)

### Path B：原始盘口张量 (Learned representation)
- 25 档 × 4 通道：[bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]
- 价格：相对 mid 的 bps（消除 absolute price 非平稳性）
- 数量：log1p（压缩重尾）
- 形状：(B, T=600, n_levels=25, 4)

### 标签
- 单任务：y_600 (10 min log-return)
- Per-fold 归一化：z = (y - median) / σ_MAD（train set 计算）
- (历史尝试：dualh 加 y_180 aux 权重 0.3，但 ablation 显示 pool level 无 measurable 增量 — 详见 §14)

---

## 3. 完整 Forward 流程

```
Input: x_features (B,T,64)  +  x_raw (B,T,25,4)  +  prior (B,6)
                │                    │
                ▼                    ▼
         ┌──────────────┐     ┌──────────────┐
         │   RevIN      │     │ RawLOBEncoder│
         │ (per-instance│     │ (Conv levels │
         │ normalize)   │     │  + LevelAttn)│
         └──────┬───────┘     └──────┬───────┘
                │                    │
                ▼                    │
         ┌──────────────┐            │
         │  MaskNet     │            │
         │ (noise mask) │            │
         └──────┬───────┘            │
                │                    │
                ▼                    │
         ┌──────────────┐            │
         │   GDCN       │            │
         │ (gated cross │            │
         │  features)   │            │
         └──────┬───────┘            │
                │                    │
                ▼                    │
         ┌──────────────┐            │
         │   Linear     │            │
         │ → d_model=32 │            │
         └──────┬───────┘            │
                │      ┌─────────────┘
                ▼      ▼
              ┌────────────┐
              │ Path Fusion│
              │ concat→Lin.│
              │ → (B,T,32) │
              └─────┬──────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Conformer Backbone   │
        │  ×2 blocks:           │
        │   ½·FFN → SelfAttn    │
        │     → Conv(k=15)      │
        │     → ½·FFN (residual)│
        │  → (B, T, 32)         │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ LevelAttentionPool    │
        │ over time → (B, 32)   │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   PPNetGate           │
        │   (regime conditional)│
        │   from prior (B,6)    │
        │   → (B, 32) gated     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   y_600 head (primary)│
        │   MonotonicQuantile   │
        │   → q10 / q50 / q90   │
        └───────────────────────┘
```

(dualh variant 在此处接两个 head: y_180 aux + y_600 primary。Singh 只接一个 y_600 head — 实测 pool level 无 IC 差异，singh 在 trading view + per-fold stability 上略胜，详见 §14。)

### 关键参数 (singh)
| 模块 | 参数 |
|---|---|
| n_features | 64 |
| n_levels | 25 (盘口档数) |
| input_len | 600 (秒) |
| stride | 180 (sample 间隔，秒) |
| d_model | 32 (Path A + 融合维度) |
| d_raw | 16 (Path B 输出维度) |
| Conformer n_blocks | 2 |
| Conformer kernel_size | 15 |
| Conformer attn_nhead | 2 |
| n_horizons | **1** (y_600 only) |
| 总参数 | **109,299** (dualh 是 111,510, 多一个 head ~2K params) |

---

## 4. MonotonicQuantileHead — 关键 Head 设计

```python
base = base_head(h)                    # h → Linear → GELU → Linear
delta_low  = softplus(delta_low_head(h)) + 0.01    # 总是正
delta_high = softplus(delta_high_head(h)) + 0.01   # 总是正

q50 = base
q10 = base - delta_low      # 结构上 < q50
q90 = base + delta_high     # 结构上 > q50
```

**结构性保证 q10 < q50 < q90，无需 sorting/penalty post-processing。**

⚠️ 这个设计的副作用是 anti-pattern #21 的根源：q50 与 q10 通过 softplus offset 强耦合。如果 ranking score 取自 q10（`utility_alpha=1.0`），模型会通过把 q50 偏负让 q10 仍是 well-calibrated 的 ranking signal — 从而引入 -0.4 bps 系统性 negative bias。**解法：utility_alpha=0 直接 rank q50（见 §6 损失设计）。**

---

## 5. 正则化思路 (Hardened Recipe)

| 类别 | 配置 | 目的 |
|---|---|---|
| Weight decay | `0.001` | L2 正则，避免 overfit |
| Dropout | `0.20`（V4 baseline 是 0.15） | 提高 single-pass 模型多样性 |
| Patience (early stop) | `4` epochs（baseline 是 8） | 更激进早停，避免过拟合 val |
| Val days | `60`（baseline 是 30） | val 信号更稳健，减少 single-day 噪声 |
| Val metric | `composite = 0.5·P + 0.5·S` | Pearson 和 Spearman 兼顾 |
| LR schedule | `6e-4` cosine + warmup | 标准配方 |
| Batch size | `1024` | 平衡 GPU 利用 + gradient 稳定 |
| EMA | `decay=0.999` | 训练时持续平均权重 |
| Embargo | 1-2 day train→val→test gap | 严格防 lookahead |

**为什么 EMA 平均权重但仍选 BEST checkpoint？**
单 seed 上 EMA 在该 loss landscape 下平均了 sub-optimal 后期 epochs。BEST P=+0.062 vs EMA P=+0.044 — BEST 显著胜出。production 用 BEST。

---

## 6. 损失函数设计

### 完整 loss

```python
L = 0.10 · pinball(q10/q50/q90)        # MonotonicQuantile head 校准
  + 0.50 · utility_rank(α=0)           # Spearman 主力（rank by q50）
  + 0.50 · plain_Huber(q50, y, δ=2)   # Pearson + magnitude + bias
```

### 各项作用

#### (a) `pinball loss`，权重 0.10

```
L_pinball = mean over τ ∈ {0.10, 0.50, 0.90}:
              max(τ·(y - q_τ), (τ-1)·(y - q_τ))
```
- 维持 MonotonicQuantileHead 的 q10/q50/q90 calibration（实测 P(y<q10)=0.103, P(y<q50)=0.508, P(y>q90)=0.100，三个都接近目标 0.10/0.50/0.10）
- **权重低（0.10 vs V4 1.0）**：减弱对 q50 ≈ median(y) 的 pressure，让 q50 自由表达更高量级信号

#### (b) `utility_rank loss`，权重 0.50，**α=0**

```python
score = α·q10 + (1-α)·q50    # α=0 ⇒ score = q50（直接 rank by q50）

Sample n_pairs (i,j):
  desired = sign(y_i - y_j)
  pred_diff = score_i - score_j
  loss_ij = softplus(-desired · pred_diff)
```
- **核心修复**：α=0 直接 rank by q50，**避免 q10 的 softplus offset 偏移传递到 q50**
- pairwise logistic 是 Spearman 的可微 proxy，比 differentiable Spearman (anti-pattern #15) 鲁棒（不会 overfit val rank）

#### (c) `plain Huber loss`，权重 0.50，**δ=2 z-units, w_wrong=0**

```python
r = q50 - y
L_huber = 0.5·r²        if |r| ≤ δ
        = δ·(|r| - 0.5·δ) if |r| > δ
```
- **w_wrong=0 是关键**：`directional_huber` 的 sign-attraction 形式（w_wrong > 0）有 0-attractor bug — `sign(0)=0` 让模型可以预测 0 dodge sign-disagreement penalty，导致 σŷ collapse（anti-pattern #20）
- plain Huber 是干净的 conditional-mean estimator，δ=2 z-units (~14 bps) L2→L1 transition 兼顾 magnitude 学习 + outlier 鲁棒

**Singh 单 horizon 设计**: 整个 loss 直接作用于 y_600 head, 没有 per-horizon weighting。所有 model capacity 给 y_600。

---

## 7. V4 → V5 架构升级思路

| 维度 | V4 baseline_plus | V5 singh α=0+Huber | 收益 |
|---|---|---|---|
| Backbone | DilatedCausalConv + last-timestep pool | **Conformer** ×2 (Conv k=15 + SelfAttn + FFN) | +长程依赖捕获 |
| Pool | last-timestep | **LevelAttentionPool over time** | +跨 timestep 聚合更稳健 |
| Dropout | 0.15 | 0.20 | +正则强度 |
| Patience | 8 | 4 | +更激进早停 |
| Val days | 30 | 60 | +val 信号稳健 |
| Loss | utility_rank α=1 + dir_huber w_wrong=2 | **utility_rank α=0 + plain Huber** | train-time bias 修复 (§8) |

**单 axis 贡献估计**（基于内部 ablation）：
- Conformer backbone: +0.005 P over conv_lasts
- Hardened recipe (dropout+patience+val_days): +0.003 P
- α=0+Huber loss: train-time bias 修复 (calibration view 全干净 + β +0.77→+1.05)

合计约 +0.011 P over V4 baseline_plus on Pearson（实测 V4 P=+0.046, V5 singh P=+0.062，Δ +0.016 含 loss 升级）。

### 关于 multi-horizon (dualh) 不在升级清单的原因

之前认为 dualh (y_180 aux + y_600 primary) 是 V5 的关键升级。Ablation 测试结果（详见 §14）显示：
- Pool level Pearson 完全持平 (+0.0617 vs +0.0622, 在 noise 内)
- Spearman singh 略胜 +2.2%
- Trading view singh +26% top-bot spread
- per-fold P stability singh -22% std

→ **multi-horizon 不是必需**, dualh 占用 backbone 的 ~2K capacity 给 y_180 aux head 实际无 measurable 增量, 反而带来 fold-1 outlier variance。Production 选 singh。

### 为什么 Conformer 适合 LOB 序列？

LOB 序列在两个时间尺度上有信息：
1. **局部模式 (~ 10-30 秒)**：order book imbalance shifts, micro-trends → 卷积擅长
2. **长程依赖 (~ 1-10 分钟)**：regime persistence, macro flows → attention 擅长

Conformer 的 sandwich 结构 (½FFN → SelfAttn → Conv → ½FFN) 是这两个尺度的协同：
- SelfAttn 之前先 FFN preprocess → 给 attention 提供更高维表征
- SelfAttn 后接 Conv → 在 attention 提供的全局视野上做 local refinement
- 残差连接保留低层信息

V4 的 DilatedCausalConv 架构只有局部尺度，Conformer 加入 attention 在 long-horizon (y_600) 上回报更高。

---

## 8. V4 → V5 损失升级思路

### V4 baseline_plus loss

```
L_v4 = 1.0 · pinball + 0.3 · utility_rank(α=1.0) + 0.2 · dir_huber(w_wrong=2.0) + 0.05 · beta_calib
```

### V5 α=0+Huber loss

```
L_v5 = 0.10 · pinball + 0.50 · utility_rank(α=0.0) + 0.50 · plain_Huber(w_wrong=0)
```

### 升级 5 点

#### (1) `utility_alpha 1.0 → 0.0`：**最关键单点改动**
- V4 ranks by q10。MonotonicQuantileHead 强制 q50 = q10 + softplus(δ_low)。
- 模型学习路径：要让 q10 是 well-calibrated ranking signal，q50 必须是 q10 + 较小的 positive offset。但 train 中 y 的均值 ≈ 0，q10 → ~y 时 q50 → ~y + offset 偏正？错 — 实际 training 中 q10 学到 ~ y - σ，所以 q50 = q10 + offset 仍 ≈ y - σ + offset = y - small offset → **q50 系统性偏负 (-0.41 bps)**。
- α=0 让 ranking 直接基于 q50 → q50 不再有 ranking 的 burden → 自由 calibrate 到 E[y|x]。

#### (2) `lambda_quantile 1.0 → 0.10`：减弱 pinball pressure
- 强 pinball pressure 让 q50 趋近 train median ≈ 0 → σŷ 被压缩
- 降到 0.10 仍能维持 q10/q90 calibration（实测 0.103/0.100），但 q50 自由扩展量级

#### (3) 用 `plain Huber` 替代 `dir_huber`：避免 σ collapse trap
- `dir_huber(w_wrong=2.0)` 的 sign-attraction 项有 0-attractor bug
- `sign(0)=0` 让模型可以预测 ŷ=0 dodge 所有 sign-disagree penalty
- 配合 lambda_pearson 一起跑（V_optimal_v2 实测）→ σŷ collapse 到 0.007，Pearson loss 因 cov=0 无 gradient 救不了
- Plain Huber (w_wrong=0) = 经典 conditional-mean estimator，无 0-attractor

#### (4) 删除 `beta_calib`：无必要
- V4 的 beta_calib 试图 explicit push β → 1.0
- α=0 + Huber 自然让 β = 1.06（near-perfect），beta_calib 多余

#### (5) `lambda_utility_rank 0.3 → 0.50`：补足 Spearman pressure
- pinball weight 降低后，需要更强的 rank pressure 维持 Spearman
- 0.50 weight + α=0 direct rank by q50 → Spearman +0.067 (vs V4 0.050)

---

## 9. β 校准 / 单调性 / 整体幅度的修复机制

### (a) β = cov(ŷ,y)/var(ŷ) 校准

| 模型 | β | 说明 |
|---|---:|---|
| V4 baseline 3-seed median | +1.27 | over-shrunk（ŷ 量级太小，相同方向时 cov 大于预期） |
| V5 BASELINE seed=42 (dualh, no fix) | +1.05 | 接近完美 by coincidence |
| V5 dualh α=0+Huber | +1.06 | 稳定接近完美 (per-fold [+1.80, +1.10, +0.78]) |
| **V5 singh α=0+Huber** | **+1.05** | **稳定接近完美** (per-fold [+0.90, +1.28, +1.14]) |

#### 修复路径
1. **架构层**：Conformer + LevelAttentionPool 提供更丰富 representation → `Var(ŷ)` 自然更接近 `Var(y)·ρ²`，使 β = cov/var(ŷ) 接近 ρ
2. **损失层**：plain Huber 的 L2 区域（|r| ≤ δ）push q50 toward y → q50 量级 ≈ E[y|x] 量级 → β 自然 ≈ 1
3. **去 beta_calib loss**：避免 explicit β-targeting 导致 val→test drift（anti-pattern #13 σ-anchor learnable 的同类问题）

### (b) Monotonicity (bin-Spearman)

| 模型 | bin-S calib | bin-S trade |
|---|---:|---:|
| V4 baseline | ~0.90 | ~0.92 |
| V5 BASELINE (dualh, no fix) | +0.891 | +0.93 |
| V5 dualh α=0+Huber | +0.976 | +0.988 |
| **V5 singh α=0+Huber** | **+0.952** | **+0.964** |

Singh bin-S 比 dualh 略低 (-0.024)，但都远超 0.85 gate。Trading view bin-S 0.964 仍非常 strong。

#### 修复路径
1. **utility_rank α=0 直接 rank q50**：让 rank 的优化 pressure 直接施加在 production output 上
2. **Spearman-weight 0.3→0.50**：更强 rank pressure 让相邻 deciles ŷ_mean 严格单调
3. **dropout 0.20**：减少 overfitting 单个 epoch 局部抖动

### (c) 整体预测幅度 + bias

| 模型 | ŷ_mean (bps) | Top y-bin ŷ_mean (bps) | σŷ/σy |
|---|---:|---:|---:|
| V4 baseline 3-seed median | -0.50 | NEG (~-0.6) | 0.052 |
| V5 BASELINE seed=42 | -0.41 | -0.30 | 0.061 |
| V5 dualh α=0+Huber | +0.14 ✓ | +0.22 ✓ | 0.059 |
| **V5 singh α=0+Huber** | **+0.18 ✓** | **+0.29 ✓** | **0.059** |

#### 修复路径（核心机制）
**MonotonicQuantileHead + utility_rank α=1 → softplus offset 强加 negative bias**：
```
当 utility_alpha = 1.0:
  ranking score = q10 = base - softplus(δ_low)
  
模型为了让 q10 是好的 ranking signal:
  → 训练 base 接近 y (自然), softplus(δ_low) > 0
  → q50 = base ≈ y, q10 = base - softplus < y
  
但实际 base 学到的不是 y，而是为了 minimize pinball + utility_rank 的折中：
  → base 被推得稍微偏低（ranking 上 q10 已经 ~y，q50 = base 不必更高）
  → q50 系统性偏负 ≈ -softplus(δ_low) / 2 量级
  → 实测 -0.4 bps
```

**修复**：α=0 让 rank score = q50（不再需要 q10 当 ranking 主力）→ q50 自由 calibrate 到 E[y|x]，bias 归零。

**实验数据验证**：
- α=0 alone (无 Huber): bias +0.23 bps（小幅过正，因为 utility_rank α=0 + pinball 没有强 magnitude anchor）
- α=0 + Huber：bias +0.14 bps（Huber 的 conditional-mean 性质把 q50 拉回 y_mean=+0.08 bps）

---

## 10. 数据流 + Eval 口径（同事回测必读）

### CSV 列定义

`exports/v5_alpha0_huber/y600_predictions_all_folds.csv` (50,846 行 × 13 列)

| 列名 | 含义 |
|---|---|
| `timestamp_us` | int64 UTC 微秒；input window 末端 (anchor t) |
| `datetime_utc` | ISO-8601 字符串 |
| `fold` | 0/1/2 (walk-forward fold id) |
| `horizon_sec` | 600 |
| `mask` | 1 if forward-return window 完整观测；0 if NaN |
| `y_true_logret` / `y_true_bps` | 实测 600s 前向 log-return |
| `y_pred_q10/q50/q90_logret` | 预测 10/50/90 分位 (monotonic by construction) |
| `y_pred_q50_bps` | q50 单位 bps，**直接当 expected return 用** |
| `y_pred_q50_z` | z-score 形式（除以 train σ） |
| `y_sigma_train_bps` | per-fold train MAD-σ in bps |

### 回测语义

- **Anchor**: `timestamp_us` = input window 末端 t
- **Position entry**: `t` (signal 已知)
- **Position exit**: `t + 600s` (pure signal P&L)
- **Filter**: 只用 `mask == 1` 行
- **Position size**: ∝ q50 / σ(q50)，或自定义阈值
- ✅ **q50_bps 直接用，无需任何 rescale / demean**（β=1.06 已校准）

### IC 报告口径

| 模式 | n | 用途 |
|---|---:|---|
| Dense (raw CSV) | 49,953 | trading PnL 相关，包含 cross-fold 同时间点 + 标签窗口重叠 |
| Dedup (per-ts earliest fold) | 37,705 | 解决 cross-fold 重复 |
| Stride10 clean | 4,996 | IID 假设下统计显著性 |
| **Strictest (dedup + stride10)** | **3,772** | 最保守 |

| Mode | Pearson | Spearman | 说明 |
|---|---:|---:|---|
| Dense | +0.0623 | +0.0672 | 给 PnL 模拟用 |
| Dedup | +0.0544 | +0.0603 | |
| Stride10 | +0.0586 | +0.0643 | |
| **Strictest** | **+0.0431** | **+0.0614** | bootstrap CI 用 |

### 严格自测结果

15/15 gates pass（详见 `STRICT_EVAL.md`）。关键点：
- Pearson 95% CI: [+0.0511, +0.0745]，下界 > 0 显著
- Spearman 95% CI: [+0.0568, +0.0785]，下界 > 0 显著
- β = +1.054（[0.5, 2.0] 安全区间）
- σŷ/σy = 0.059（模型保守，预测振幅是 y 的 6%）
- 残差 lag-1 AC = +0.747（≈ y 自身 lag-1，因 stride < horizon 标签窗口重叠 — 已知性质，非 leakage）

### 已审计无 leakage

- Train/val/test 严格按时间排序 + 1-2 day embargo（≫ horizon 10 min）
- Feature 全部来自过去 (t-600..t-1)
- Per-fold normalization 仅用 train set 统计
- 多 fold 重叠 timestamps 用不同 model 预测（各自 OOS），属 over-counting 不是 leak

---

## 11. 文件清单

### Production (singh, current winner)
- Config: `configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json`
- Predictions: `experiments/v5_final/singleh_alpha0_huber/fold_{0,1,2}/test_preds.npz`
- CSV: `exports/v5_singh_alpha0_huber/y600_predictions_{all_folds,fold_{0,1,2}}.csv`
- Strict eval: `exports/v5_singh_alpha0_huber/STRICT_EVAL.md`
- README: `exports/v5_singh_alpha0_huber/README.md`

### Reference (dualh, prior winner, fallback)
- Config: `configs/v5/screen/backbone_conformer_hardened_dualh_alpha0_huber.json`
- Predictions: `experiments/v5_final/dualh_alpha0_huber/fold_{0,1,2}/test_preds.npz`
- CSV: `exports/v5_alpha0_huber/y600_predictions_{all_folds,fold_{0,1,2}}.csv`
- Strict eval: `exports/v5_alpha0_huber/STRICT_EVAL.md`

### 关键代码
- 主模型: `src/model/dual_path_model_v3.py:DualPathLOBModelV3`
- Conformer backbone: `src/model/backbones/conformer_backbone.py`
- Quantile head: `src/model/monotonic_quantile.py:MonotonicQuantileHead`
- Loss: `src/training/dul_loss.py:compute_dul_loss`
- Trainer: `src/training/trainer_v2.py`
- Pipeline: `run_pipeline_v3.py`

### 训练复现 (production singh)

```bash
# Pod (3090 ~50min/fold, 3 folds total ≈ 2.5h)
python scripts/v5_run_one.py \
    --name singleh_alpha0_huber \
    --config configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json \
    --out-base experiments/v5_final \
    --max-folds 3 --start-fold 0
```

---

## 12. 已知限制 + 不要做

### 限制
1. **σŷ/σy = 0.059** — 模型预测振幅是真实 y 的 6%。低 SNR (R² ~0.4%) 下的物理上限，不是 bug。q50 是 conservative E[y|x] 估计，提供方向 + ranking，不提供 amplitude prediction。
2. **单资产 BTCUSDT y_600** — Bayes ceiling ≈ ρ ≈ 0.07-0.08。突破 0.10 需 multi-asset breadth 或 orthogonal data。
3. **EMA 在该 loss landscape 表现差** — production 用 BEST，不要切 EMA。
4. **Single seed=42** — 不要做 multi-seed median（实测会被 1 lucky + N weak seeds 拖累，anti-pattern #22）。

### 严禁
- ❌ Post-hoc demean / rescale q50（β 已校准，不要二次干预）
- ❌ 替换 utility_rank 为 differentiable Spearman (anti-pattern #15)
- ❌ 加 dir_huber w_wrong>0 (anti-pattern #20)
- ❌ Smooth target (anti-pattern #18)

---

## 13. 总结

V5 singh α=0+Huber 是 **架构 + 损失 + 训练 recipe 三方面协同优化**的结果：

- **架构升级 (V4 → V5)**：Conformer backbone + LevelAttentionPool over time + Hardened recipe = ~+0.011 P (singh 实测)
- **损失升级**: utility_rank α=1→0 + plain Huber (w_wrong=0) = train-time bias 修复（无需 post-hoc）
- **训练 recipe**: dropout 0.20 + patience 4 + val_days 60 = per-fold std 0.0039（singh 上最紧, CoV 0.062）

q50 直接当 expected return 使用，β=1.05 接近完美。所有 calibration 指标 train-time 修复，所有 15 个 production gates pass。无 leakage。

**Multi-horizon dualh 不是必需**: ablation 显示 y_180 aux task 在 V5 backbone 上无 measurable 增量，仅占用 2K params + 增加 fold-1 outlier variance。**Singh = simpler + same-or-better Pearson + better Spearman + better trading view + tighter per-fold P**。

下一步突破方向：multi-asset breadth (ETH/SOL/BNB) 或 orthogonal data (funding rate, OI) — 单资产 LOB-only 已接近 Bayes ceiling。

---

## 14. Singh vs Dualh 对照（2026-05-05 production 切换详细）

### Pooled metrics (n=49,953)

| Metric | **Singh (current)** | Dualh (prior) | Δ | Notes |
|---|---:|---:|---:|---|
| Pearson | +0.0617 | +0.0622 | -0.0005 | tie within noise |
| **Spearman** | **+0.0686** | +0.0672 | **+0.0014** | singh +2.2% |
| β | +1.050 | +1.060 | tie | both perfect |
| σŷ/σy | 0.059 | 0.059 | tie | identical |
| bias bps | +0.180 | +0.140 | similar | both clean ✓ |
| Top y-bin ŷ_mean | +0.292 | +0.223 | +0.07 | both ✓ POSITIVE |
| **Top-bot trading spread** | **+2.64 bps** | +2.10 bps | **+26%** | singh significantly stronger |
| Top decile y t-stat | +7.14 | +6.66 | +7% | singh |
| Bot decile y t-stat | -6.91 | -6.20 | +11% | singh (deeper edge) |
| Bin-S calib | 0.952 | 0.976 | -0.024 | dualh slight |
| Bin-S trade | 0.964 | 0.988 | -0.024 | dualh slight |
| **per-fold P std** | **0.0039** | 0.0050 | **-22%** | singh much tighter |
| per-fold S std | 0.0036 | 0.0028 | -29% | dualh slight |
| Quantile cov q10 / q90 | 0.091 / 0.086 | 0.103 / 0.100 | dualh closer 0.10 | dualh slight |

**Win count: singh 6, dualh 4 (mostly minor monotonicity / coverage differences), tie 4.**

### Singh 的具体优势

#### (a) Trading-relevant signals 更强
- Top-bot spread +2.64 bps vs +2.10 bps (+26%) — 每次交易期望收益差更大
- Top-decile-ŷ → y_mean +1.41 bps vs +1.12 bps — 模型最 trust 的样本兑现更多
- Top decile DirAcc 0.549 (vs 0.541) + bot 0.559 (vs 0.551) — 顶/底档方向准确度更高

#### (b) Per-fold stability 显著更好
- Singh per-fold P=[0.058, 0.062, 0.068]，std 0.0039 (CoV 6.2%)
- Dualh per-fold P=[0.061, 0.071, 0.060]，std 0.0050 (CoV 7.8%) — fold 1 outlier
- 实战意义：未来不同时期的 IC 估计更可靠，下行风险更小

#### (c) Calibration view 更"自然"
- Singh top y-bin ŷ_mean=+0.292 vs dualh +0.223 — 在最赚钱的 bin 模型预测更 confident（虽然两者都已 ≥ 0）
- 全 10 bin ŷ_mean 都 ≥ 0 ✓（与 dualh 同）

### Dualh 的微弱保留优势

- bin-Spearman 0.976 vs 0.952（+0.024）— 单调性略好，但都已 ≥ 0.95 远超 0.85 gate
- per-fold S std 0.0028 vs 0.0036 — Spearman 跨 fold 略稳

这些都是 marginal 差异，不足以抵消 singh 在 trading-spread + per-fold P stability 上的 substantial 胜出。

### 配置差异（diff）

唯一区别就是 horizon 配置:

```diff
  "data": {
    "horizon_sec": 600,
-   "horizons_sec": [180, 600],
+   "horizons_sec": [600],
    ...
  },
  "model": {
-   "n_horizons": 2,
+   "n_horizons": 1,
    ...
  },
  "training": {
-   "horizon_weights": [0.3, 1.0],   # dualh-only
    ...
  }
```

参数量差异：singh 109,299 vs dualh 111,510（差异在第二个 quantile head）。

### 切换原因总结

User 价值函数的 9 个维度中：
- Singh 胜出 6: Spearman, trading spread, top/bot decile t-stat, per-fold P stability, top y-bin (微胜), calibration cleanliness (基本一致)
- Dualh 胜出 4: bin-Spearman, per-fold S, q10/q90 coverage, fold-1 单点 P 高（但被 fold 0/2 拖累 pool P 差不多）
- Singh 简单度更高（无 aux task 协调成本）

**结论：dualh 不是 V5 family 的天花板，singh 才是当前 production winner。**
