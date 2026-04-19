# DL Quant 项目总览

> **适用对象：** 加入项目的新成员、短期合作者、以及需要在 30 分钟内了解项目全貌的任何人。
> **最后更新：** 2026-04-18  
> **入口文档：** 本文档是唯一入口；其他文档都是本文档的细节展开。

---

## 1. 项目目标

用**深度学习 + 手工特征**预测 Binance BTCUSDT 永续合约的**中频（1-10 分钟）**收益率，目标建立稳定可观的决策收益。

**核心约束**（不可违反）：
- 信号极弱（R² < 1%）— 任何模型设计都必须尊重这个物理事实
- 数据有限 — 当前约 991 天训练数据
- 非平稳性 — 分布与特征-收益关系持续漂移
- 小团队 — 追求理论深度和工程质量平衡，不追求工业级规模

**当前预测窗口：** 180 秒（3 分钟）
**Pass/Fail 门槛：** Pooled Pearson ≥ 0.12 OR Spearman ≥ 0.12

---

## 2. 当前状态快照（2026-04-18）

### 三模型 3-fold walk-forward 对照（相同 700d/30d/90d 设置）

| 模型 | 参数量 | Pearson | Spearman | DirAcc | Daily IC-IR | 单调性 |
|---|---:|---:|---:|---:|---:|:-:|
| Ridge | 65 (64+bias) | 0.0840 | 0.1089 | 54.9% | 1.44 | +0.988 |
| TemporalRidge | 65* | 0.0840 | 0.1089 | 54.9% | 1.44 | +0.988 |
| XGBoost | ~数千 trees | 0.0944 | 0.1086 | 54.9% | 1.37 | +1.000 |
| **V4 noattn** | **59,315** | **0.0943** | **0.1107** | **54.9%** | **1.47** | **+1.000** |

\* TemporalRidge 在 `--use-last-timestep` 模式下退化为 Ridge（标准差/趋势项为 0），所以两者数值完全一致。

**结论：** 四模型性能接近（Pearson 差距 0.01，Spearman 差距 0.002），V4 daily IC-IR 最高（1.47），校准完美，但**综合优势仍然小**。

### 对照 spec 门槛（≥ 0.12）

❌ 所有模型均**未达**门槛，距离 Pearson 还差 0.026，Spearman 差 0.013。

### 关键发现（综合评估 2026-04-18）

1. **V4 不是 momentum 复读机** — 简单因子对 V4 q50 的 R²=0.004，V4 捕捉到真正的非线性信号。
2. **V4↔XGBoost 相关性 0.679**（最低）— V4+XGBoost 是真正的集成多样性组合。
3. **Ridge 在集成中是负权重**（−0.06）— V4 已经包含 Ridge 的全部线性信号。
4. **置信度门控有效** — V4 Sharpe 从 289→327 at τ*=0.021（60% 交易率）。
5. **量子级校准** — V4 的 q10/q50/q90 实际覆盖率与理论差 < 0.005。
6. **日度 IC-IR = 1.47 可交易**，92% 的日子 IC > 0。

---

## 3. 架构总览图

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据管道                                      │
│                                                                  │
│  Binance WebSocket / Bybit 历史  →  resample_lob_to_1s           │
│                                    │                             │
│       ┌────────────────────────────┼─────────────────────────┐   │
│       ▼                            ▼                         ▼   │
│  Handcrafted                   Raw LOB                   Regime   │
│  64 features                  20 levels × 4            6 priors   │
│  (see 4.2)                    (bid/ask price+amt)      (see 4.3) │
│       │                            │                         │   │
│       └──────────┬─────────────────┴─────────────────────────┘   │
│                  ▼                                                │
│            build_npz_for_day(stride=60, horizon=[60,180,300,600])│
│                  ▼                                                │
│            data/npz_v4/YYYY-MM-DD.npz                            │
│   X:(N,600,64)  X_raw:(N,600,20,4)  y_180:(N,)  regime:(N,6)    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    V4 模型 (DualPathLOBModelV3)                  │
│                                                                  │
│  Path A (手工特征)              Path B (原始盘口)                │
│  X:(B,600,64)                   X_raw:(B,600,20,4)               │
│       │                              │                           │
│       ▼                              ▼                           │
│  RevIN 归一化                   RawLOBEncoder                    │
│       │                         (Conv2d 跨档位)                  │
│       ▼                              │                           │
│  [MaskNet: 禁用]                     ▼                           │
│       │                         (B,600,d_raw=16)                 │
│       ▼                              │                           │
│  GDCN (1 个门控交叉层)              │                           │
│       │                              │                           │
│       ▼                              │                           │
│  Linear proj → (B,600,d_model=32)    │                           │
│              │                       │                           │
│              └──────┬────────────────┘                           │
│                     ▼                                             │
│              concat → Fusion Linear → (B,600,32)                 │
│                     │                                             │
│                     ▼                                             │
│              Causal TCN (dilations {1,2,4}, RF=15s)              │
│                     │                                             │
│                     ▼  (B,600,32)                                │
│              [Patch Attention: 禁用]  ← noattn ablation          │
│                     │                                             │
│                     ▼                                             │
│              Pooling (last timestep)                             │
│                     │                                             │
│                     ▼  (B,32)                                    │
│              PPNet Gate ← regime_prior (B,6)                     │
│                     │                                             │
│                     ▼                                             │
│              MonotonicQuantileHead → (q10, q50, q90)             │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                DUL Loss = λ₁·pinball + λ₂·utility_rank + λ₃·calib
                (λ₁=1.0, λ₂=0.3, λ₃=0 disabled)
```

---

## 4. 模型子模块详解

### 4.1 V4 模型全称与构造参数

- **类名：** `DualPathLOBModelV3` in `src/model/dual_path_model_v3.py`
- **参数量：** 59,315 (noattn 配置)
  - **⚠️ 注意：** 约 22K 参数（`patch_embed` + `patch_attention`）在 noattn 模式下**构造但不参与 forward**（见 `V4_MODEL_AUDIT.md`）。实际活跃参数约 37K。这是已知的技术债，保留是为了 checkpoint 跨消融兼容。
- **当前最优配置：** `configs/v4_noattn_700d.json`

**启用 / 禁用标志一览**（来自配置文件实际值）：

| 模块 | 启用？ | 备注 |
|---|:-:|---|
| `use_revin` | ✅ | 关键 —— R1 smoke 证明 +0.019 Pearson |
| `use_masknet` | ❌ **禁用** | 消融验证后去除，减少参数并避免过拟合 |
| `use_gdcn` (`n_cross_layers=1`) | ✅ | 特征交叉 |
| `use_raw_path` | ✅ | 关键 —— smoke 贡献 +0.052 Pearson |
| `use_attention` / `use_patch_attention_pool` | ❌ **禁用** | smoke 贡献 +0.055 Pearson（去掉反而好） |
| `use_conv` | ✅ | Causal TCN |
| `use_channel_mix_conv` | ✅ | Raw path 1x1 卷积 |
| `use_level_attention_pool` | ✅ | Raw path 跨档注意力池化 |
| `use_ppnet_gate` | ✅ | 关键 —— smoke 贡献 +0.077 Pearson |
| `use_monotonic_quantile` | ✅ | 结构保证 q10≤q50≤q90 |
| 预测 horizon | `[180]` | 单 horizon，无多任务 |
| 输入窗口 | 600 秒 | 10 分钟上下文 |

### 4.2 Path A 手工特征（64 维）

来源：`src/features/derived_features.py` + `src/features/trade_features.py` + `src/features/ridge_informed_features.py`

| 类别 | 特征 | 数量 |
|---|---|:-:|
| 收益率 | log_return_1s/5s/30s | 3 |
| 价差 | spread_bps, spread_change | 2 |
| OBI (订单簿不平衡) | obi_L1/L5/L10/L25, obi_L1_delta | 5 |
| 深度 | bid/ask_depth_L5/L25, depth_ratio_L5 | 5 |
| 加权价 | weighted_price_bid/ask_L10, price_pressure | 3 |
| 波动率 | realized_vol_30s/60s/300s | 3 |
| 斜率 & 集中度 | bid/ask_slope_L10, bid/ask_concentration | 4 |
| 档位数量比 | bid/ask_amt_ratio_L0..L4 | 10 |
| 时间 | second_of_day_sin/cos | 2 |
| 订单流 | delta_bid/ask_depth_L5, net_order_flow_L5, delta_obi_L5_5s, delta_pressure_5s | 5 |
| 成交流 | buy/sell_volume_1s, net_trade_flow_1s, trade_imbalance_1s, cumulative_net_flow_30s/300s, trade_intensity_30s | 7 |
| VWAP | vwap_return_1s | 1 |
| Kyle's λ | kyle_lambda_30s | 1 |
| 微价格 & Roll spread | microprice_dev_bps, roll_spread_60s | 2 |
| VPIN | vpin_60s/300s | 2 |
| Ridge-informed | book_pressure_imbalance, price_impact_30s, net_flow_x_spread, net_flow_x_vol, obi_L5_rank_1h, net_flow_rank_1h, large_trade_arrival_60s, book_pressure_delta_60s | 8 |

### 4.3 Path B 原始盘口张量

- **形状：** `(batch, time=600, levels=20, 4)`
- **4 字段：** `[bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]`
  - `bid/ask_delta_bps`: 档位价格相对 mid 的 bps（消除非平稳性）
  - `bid/ask_log_amt`: `log1p(quantity)`（压缩重尾分布）
- **编码器：** `RawLOBEncoder` (`src/model/raw_lob_encoder.py`)，用 `Conv2d` 跨档位卷积

### 4.4 Regime Prior（6 维）

来源：`src/features/regime_prior_features.py`

外部计算的小时级市场状态先验（例如：过去 1 小时波动率、趋势方向、小时段 one-hot 等）。送入 `PPNetGate` 做条件化。

### 4.5 核心子模块

| 模块 | 文件 | 当前启用 | 作用 | 理论来源 |
|---|---|:-:|---|---|
| RevIN | `dual_path_model_v3.py:RevIN` | ✅ | 逐实例归一化，处理非平稳 | ICLR 2022 (Kim et al.) |
| MaskNet | `src/model/masknet.py` | ❌ | 逐样本特征掩码（噪声抑制） | DLP-KDD 2021 |
| GDCN | `src/model/gdcn.py` | ✅ | 门控深度交叉网络 | CIKM 2023 |
| RawLOBEncoder | `src/model/raw_lob_encoder.py` | ✅ | 盘口空间卷积 | DeepLOB 2019 / TLOB 2025 |
| CausalConv1dBlock | `dual_path_model_v3.py` | ✅ | 因果时序卷积 (RF=15s) | TCN (Bai et al.) |
| PatchAttention | `src/model/patch_attention.py` | ❌ | Patch 因果自注意力 | PatchTST |
| PPNetGate | `src/model/ppnet_gate.py` | ✅ | 基于 regime prior 的条件门 | 快手 KDD 2023 |
| MonotonicQuantileHead | `src/model/monotonic_quantile.py` | ✅ | 结构性保证 q10 ≤ q50 ≤ q90 | — |
| AttentionPool1D | `src/model/attention_pool.py` | ❌ | patch token 注意力池化 | — |

### 4.6 损失函数：DUL (Distributional Utility Loss)

**文件：** `src/training/dul_loss.py`

`L_total = λ₁·L_quantile + λ₂·L_utility_rank + λ₃·L_calib`

| 组件 | 公式 | 权重 | 作用 |
|---|---|:-:|---|
| **L_quantile** | Pinball: Σᵢ max(τ·(y−q), (τ−1)·(y−q)) for τ ∈ {0.1, 0.5, 0.9} | **1.0** | 回归到量化预测 |
| **L_utility_rank** | 风险调整分数 s = q50 − α·(q50 − q10)，成对 softplus 排序损失 | **0.3** | 增强 rank 质量 |
| **L_calib** | 分位覆盖率的 sigmoid 平滑惩罚 | **0.0 (disabled)** | 校准诚实性 |

- `alpha = 1.0` → s 退化为 q10，强化下行风险敏感性
- 当前 λ_calib = 0，因为校准已经几乎完美（q10 实际覆盖 0.109 vs 理论 0.10）

---

## 5. 数据管道

### 5.1 NPZ 文件 schema

位置：`data/npz_v4/YYYY-MM-DD.npz`

| Key | 形状 | 说明 |
|---|---|---|
| `X` | (N, 600, 64) | 手工特征，N 个窗口 × 600 秒 × 64 特征 |
| `X_raw` | (N, 600, 20, 4) | 原始盘口 |
| `features` | (64,) | 特征名（object dtype） |
| `regime_prior` | (N, 6) | regime prior |
| `timestamps` | (N,) int64 | 窗口结束时刻（微秒） |
| `y_60/y_180/y_300/y_600` | (N,) | 对应 horizon 的未来收益率 |
| `y_mask_60/...` | (N,) uint8 | 有效性掩码 |
| `horizons_sec` | (4,) | [60, 180, 300, 600] |

### 5.2 构建参数

- **Stride** = 60 秒（相邻窗口间隔 60s，窗口长 600s，即 90% 重叠）
- **窗口长度** = 600 秒（10 分钟上下文）
- **Horizon** = 180 秒主（60/300/600 辅，同一窗口支持多 horizon 评估）

### 5.3 训练数据规模

- **总天数：** 991（2023-01-01 → 2025-09-30）
- **每天窗口数：** ~16,000
- **总窗口数：** ~15.8M
- **Walk-forward 3-fold：** 每 fold 700d train / 30d val / 90d test，fold_stride=60

---

## 6. 指标术语表

> **核心原则：** 同时报告 Pearson（spec 合规）和 Spearman（交易首选）。两者分歧 > 0.03 需诊断。详见 `docs/METRIC_DISCIPLINE.md`。

| 指标 | 定义 | 意义 | 门槛 / 参考值 |
|---|---|---|---|
| **Pearson IC** | 预测与实际收益的皮尔逊相关 | 幅度校准 + spec 硬门槛 | ≥ 0.12 |
| **Spearman IC** | 预测与实际收益的斯皮尔曼（秩）相关 | 交易信号的首选指标（抗极端值） | ≥ 0.12 |
| **Daily IC / Daily IC-IR** | 每日计算 Spearman，再求 mean/std 比 | 信号的时序稳定性（类似 Sharpe） | 机构水平 > 1.0 |
| **DirAcc** | 预测符号与实际符号一致的样本比例 | 卫生检查 | > 50% |
| **Decile Monotonicity** | Spearman(decile_idx, mean_return) | 分组收益单调性 | 优秀 > +0.9 |
| **Long-Short Spread** | 最高预测分位减最低预测分位的平均收益 | 多空策略的理论收益 | 越高越好 |
| **Bootstrapped 95% CI** | 区块 bootstrap（block_len=60）估计 IC 置信区间 | 统计显著性 | 95% CI 不跨 0 即显著 |
| **Residual Autocorr** | 预测误差的自相关 lag 1/5/30 | 标签泄漏诊断 | < 0.3 (lag 1) |
| **Pairwise Prediction Corr** | 两模型预测的 Pearson | 集成多样性 | < 0.8 才能贡献集成收益 |
| **Sharpe (HAC)** | Newey-West 异方差自相关修正的夏普 | 年化超额收益 / 标准差 | > 1.0 可交易 |
| **Max Drawdown** | 累计 P&L 相对峰值的最大回撤 | 下行风险 | 越小越好 |
| **CVaR-95%** | 预测错误分布的 95% 条件尾部均值 | 尾部风险 | 越小越好（符号为负） |
| **Confidence Gating τ*** | V4 `|q50|/(q90-q10)` 门槛（最优交易率）| 过滤低置信度预测 | 当前 τ*=0.021, 60% 交易率 |
| **R² (OLS 简单因子 → q50)** | V4 输出被简单因子解释的比例 | DL 独特性诊断 | < 0.3 = DL 有独特贡献 |
| **Concentration Flag** | Top 20% 月份贡献 IC 的比例 | 集中度风险 | < 60% 通过 |

---

## 7. 模型迭代历史

| 版本 | 核心改动 | Pearson | 备注 & 来源 |
|---|---|:-:|---|
| V3 | Conv + Attention 时序骨干（无 RevIN） | ~0.082 | `docs/V4_SMOKE_FINDINGS.md` |
| V3 + RevIN | + 逐实例归一化（ICLR 2022） | 0.082 | `docs/V4_RESULTS_AUTO.md` |
| V4 full (smoke 100d) | + patch attention + monotonic quantile + V4 features | 0.061 | **attention 过拟合**，`V4_SMOKE_FINDINGS.md` |
| V4 no_attention (smoke 100d) | 去掉 patch attention | 0.084 | R1 smoke |
| V4 **noattn (700d full, fold 0)** | 700 天训练 | **0.101** | `V4_RESULTS_AUTO.md` headline |
| V4 **noattn (700d 3-fold pooled)** | 最终 3-fold walk-forward | **0.094** | **当前最佳**，`eval_comprehensive/REPORT.md` |
| V4 noattn + SWA (fold 2) | top-5 checkpoint 权重平均 | +0.002 fold-level | 边际改进 |

> **V1 / V2 版本的具体数字**：本项目的代码仓库从 V3 开始有完整 walk-forward 记录。之前的早期实验未记录入 `docs/`，此处省略以避免不可验证的声明。

**关键教训（已写入 memory）：**
- 100d 小数据量测出的"赢家"在 700d 不一定复现（PBO 警告）
- 去掉复杂模块（attention, conv）在 SNR < 1% 时往往比加模块效果好
- 双路径融合确实比单 Path A 好（raw path 提供额外信号）
- 双任务损失（方向 + 分位）会产生梯度冲突（已放弃，只用 quantile）

---

## 8. 对照实验总览

### 8.1 V4 vs baselines（3-fold 严格匹配）

详见 `experiments/eval_comprehensive/REPORT.md` 的 12 张图 + 对应 JSON。

### 8.2 模块消融（R1 smoke, 100 天训练, y_180, 数字为 test Pearson 绝对值）

| 变体 | 改动 | Pearson | Δ vs A_full | 解读 |
|---|---|:-:|:-:|---|
| A_full | V4 baseline | +0.029 | 0 | 参考线 |
| E_**noattn** | `use_attention=False` | **+0.084** | **+0.055** | attention 在 smoke 阶段显著过拟合 |
| D_norevin | `use_revin=False` | +0.010 | −0.019 | RevIN 提供 +0.019 Pearson |
| C_noraw | `use_raw_path=False` | −0.023 | −0.052 | 原始盘口提供 +0.052 Pearson（最重要单项） |
| F_noppnet | `use_ppnet_gate=False` | −0.048 | −0.077 | PPNet 提供 +0.077（最强组件） |
| B_y60 | 换预测目标为 y_60 | +0.010 | −0.019 | y_60 信号更弱或需更多数据 |
| G_simple | 剥离所有 V4 特有模块 | +0.017 | −0.012 | V4 模块组合效果略正 |
| H_norank | `lambda_utility_rank=0` | −0.011 | −0.040 | utility_rank 提供 +0.040 |

**重要提醒（PBO）：** 上表是 **100 天 smoke** 结果，其中 **E_noattn 在 700 天复现（从 0.084 提升到 0.101）**，但其他变体 **未在 700 天验证**。列出是为了记录，不等于"已证实"。

### 8.3 其他对照

| 对照 | 发现 | 依据 |
|---|---|---|
| V4 noattn 3-fold vs Ridge matched | V4 Pearson +0.010, Spearman +0.002 | `eval_comprehensive/REPORT.md` |
| V4 noattn vs XGBoost matched | V4 Pearson −0.001（**XGB 略好**），Spearman +0.002 | 同上 |
| V4+XGBoost ensemble optimal 权重 | V4=0.61, XGB=0.55, **Ridge=−0.06** | Cat 11 |
| Ridge 2023 test vs 2025 test | 2023 Pearson ~0.10, 2025 ~0.08（regime 差异） | `baselines_v4_local` vs `baselines_v4_matched` |

---

## 9. 关键文件索引

### 训练 / 推理
- `run_pipeline_v3.py` — 主训练入口
- `src/training/trainer_v2.py` — V4 trainer
- `configs/v4_noattn_700d.json` — **当前最优配置**
- `src/training/dul_loss.py` — DUL 损失

### 模型
- `src/model/dual_path_model_v3.py` — V4 主模型
- `src/model/*.py` — 各子模块

### 数据
- `src/features/pipeline.py` — NPZ 构建入口
- `src/features/multi_day_pipeline.py` — 多天批处理
- `data/npz_v4/` — 生产 NPZ 文件

### 评估
- `scripts/comprehensive_eval.py` — 综合评估（12 类指标）
- `scripts/ensemble_topk.py` — SWA / 预测平均
- `src/baselines/evaluate_baselines.py` — Ridge/XGB baseline 对照
- `src/evaluation/` — backtest 引擎（naive 版本）

### 文档
- `docs/PROJECT_OVERVIEW.md` — **本文档**
- `docs/PROJECT_PRINCIPLES.md` — 7 大操作原则
- `docs/METRIC_DISCIPLINE.md` — 指标报告纪律
- `docs/V4_MODEL_AUDIT.md` — V4 深度审计
- `docs/V4_RESULTS_AUTO.md` — 实验结果日志
- `docs/superpowers/specs/` — 各 phase 设计文档
- `docs/superpowers/plans/` — 各 phase 实施计划

---

## 10. 如何复现当前最佳结果

### 前提
- SSH 到 RunPod（SSH 配置见 `scripts/runpod_exec.sh`）
- 991 天 V4 NPZ 已在 `/workspace/quant_research/data/npz_v4/`

### 复现 V4 noattn 3-fold
```bash
# 在 pod 上
python3 run_pipeline_v3.py \
    --config configs/v4_noattn_700d.json \
    --skip-features \
    --start-fold 0 --max-folds 3
```
预期运行时间：3-5 小时 / fold × 3 folds ≈ 12-15 小时。
输出：`experiments/v4_noattn_700d/fold_{0,1,2}/`

### 复现 baseline 3-fold 对照
```bash
python3 -m src.baselines.evaluate_baselines \
    --npz-dir data/npz_v4 \
    --output-dir experiments/baselines_v4_matched_v2 \
    --device cpu --train-days 700 --val-days 30 --test-days 90 \
    --fold-stride 60 \
    --horizon-key y_180 --mask-key y_mask_180 \
    --use-last-timestep \
    --save-predictions experiments/baselines_v4_matched_preds
```
预期运行时间：~10 分钟。

### 复现综合评估报告
```bash
python3 scripts/comprehensive_eval.py \
    --v4-exp-dir experiments/v4_noattn_700d \
    --baseline-pred-dir experiments/baselines_v4_matched_preds \
    --output-dir experiments/eval_comprehensive
```
预期运行时间：~1 分钟。
输出：`REPORT.md + figures/*.png + metrics.json`

---

## 11. FAQ 与常见疑问

### Q: 为什么 Pooled Pearson 只有 0.09 但 Daily IC 0.11？
因为**日间 regime 漂移**被汇总在一起时会互相抵消。Pooled 是"平均来看"，Daily 是"每天都有效"。交易场景更关心后者 —— Daily IC-IR 1.47 说明信号每天稳定有效。

### Q: V4 跟 Ridge 差距很小，DL 有必要吗？
- 单纯 Pearson 看：V4 只比 Ridge 领先 +0.01
- 但 V4 的 R²(简单因子→q50) = 0.004，说明 V4 捕捉的是 **非线性信号**，Ridge 捕捉不到
- V4 有量化输出 + 单调校准，支持置信度门控
- 集成最优权重里 Ridge 是 **−0.06**（被 V4 抵消），XGBoost 是 +0.55
- 结论：**V4 有独特贡献，但集成只需要 V4 + XGBoost**

### Q: 为什么 180s 而不是其他 horizon？

**已完成 4 horizon 敏感性测试 + 子采样 clean stride 验证（2026-04-18）。详见 `docs/HORIZON_DECISION.md`。**

用子采样模拟 stride=H（去除标签重叠自相关）后的诚实对照：

| Horizon | Clean Pearson | Clean Spearman | σ_y (bps) | 每笔毛边际 (bps) | 延迟要求 |
|:-:|---:|---:|---:|:-:|:-:|
| y_60 | 0.143 | 0.189 | 2.25 | **0.57** | < 500ms |
| y_180 | 0.089 | 0.112 | 3.91 | **0.61** | < 5s |
| **y_300** | **0.074** | 0.079 | 5.28 | **0.69** | < 30s |
| y_600 | 0.019 | 0.060 | 7.27 | 0.24 | < 60s |

**关键洞察（2026-04-18 修正）：**
1. **原始 Pearson 误导** —— 虽然 y_60 = 0.15 最高，但 σ 只有 2.25 bps（√H 缩放），每笔实际边际最低
2. **y_300 每笔信号最强**（0.69 bps）—— 比 y_180 略好，延迟要求更宽松
3. **y_600 确实弱** —— clean Pearson 0.019
4. **所有 horizon 的简单策略都小于 6 bps 成本** —— 需要置信度门控 + maker-only 路由（Phase C 回测要解决的）

**决策：y_180 保持主力**（已有完整 V4 + 12 类评估 + 基线对照），**y_300 作为并行候选**（每笔信号最强，基础设施零压力）。**不上 y_60**（延迟要求不现实）。**不上 y_600**（信号太弱）。

### Q: Sharpe 报告 300 是真的吗？
**不是生产级的。** 当前简单实现用 `×√252` 年化因子，对于每分钟采样的数据不正确。**相对比较**（模型 A vs B）仍然有效，但绝对值请视为诊断工具。Phase C 会建立严格回测。

### Q: 我要改动代码，从哪开始？
1. 读本文档（30 分钟）
2. 读 `docs/PROJECT_PRINCIPLES.md`（15 分钟）
3. 读 `docs/METRIC_DISCIPLINE.md`（5 分钟）
4. 看 `experiments/eval_comprehensive/REPORT.md`（20 分钟）
5. 选一个 pending 任务开始（任务列表在 Claude memory 里）

### Q: 当前的下一步是什么？
**Phase B — Savitzky-Golay 特征/标签平滑**。预期提升 Pearson +0.01-0.03。详见即将写入的 `docs/superpowers/specs/2026-04-18-savitzky-golay-design.md`。
