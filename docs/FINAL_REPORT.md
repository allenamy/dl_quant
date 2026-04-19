# DL Quant 项目最终报告（2026-04-19）

> **项目范围：** Binance BTCUSDT 永续合约，单资产，中频（1-30 分钟）收益率预测。
> **时间跨度：** ~2 个月迭代，V1 → V4 + Phase A-D 共 ~15 个核心实验。
> **最终状态：** 研究级 alpha 已建立，生产级盈利未达成。本报告归档所有关键发现。

---

## 一段话总结

**我们建立了一个统计上稳健的单资产中频预测模型（V4 ensemble，Pooled Pearson 0.096，Daily IC-IR 1.4，90% 正 IC 天数）。该信号在机构量化标准下是"好信号"。但由于在 3-10 分钟窗口上 σ × IC × 1.76 ≈ 0.7 bps < 实际成本 8 bps，该信号在现有 Binance Futures retail 费率下无法盈利。通过 Phase A-D 系统性验证，**所有成本/信号优化路径都已被明确否定**。项目已到"research milestone"定位；继续迭代边际递减。**

---

## 1. 最终技术栈（生产级已锁定）

### 1.1 最佳配置

**模型：V4 noattn**（DualPathLOBModelV3 类，见 `src/model/dual_path_model_v3.py`，类名是代码生成 artifact，此处一律叫 V4）

- 参数量：59,315（约 37K 活跃，22K 构造但未调用）
- Path A：64 手工特征 → GDCN (1 层) → Linear → d_model=32
- Path B：(600, 20, 4) 原始 LOB → Conv2d → d_raw=16
- Fusion：concat → Linear → Causal TCN (dilations {1,2,4}, RF=15s)
- PPNet Gate + MonotonicQuantileHead
- 无 MaskNet（已消融）、无 patch attention（关键：SNR<1% 时 attention 过拟合）

**损失：DUL** = 1.0 × pinball + 0.3 × utility_rank

**训练：** 700d train / 30d val / 90d test × 3 fold walk-forward

**执行（Path C 最优 holding strategy）：**
- EMA 平滑 k=10、τ_entry=0.15、τ_exit=0.02、min_hold=30min、max_hold=10h
- 集成：V4 + XGBoost 等权（相关性 0.68）

### 1.2 核心指标（真实成本下）

**信号质量（Phase A + Phase C）：**
| 指标 | V4 | Ridge | XGBoost | **集成** |
|---|---:|---:|---:|---:|
| Pearson | 0.0943 | 0.0876 | 0.0944 | **0.0968** |
| Spearman | 0.1107 | 0.1099 | 0.1099 | **0.1127** |
| Daily IC-IR | **1.47** | 1.44 | 1.37 | 1.41 |
| % 正 IC 天数 | 92.4% | 93.2% | 92.4% | 90.8% |
| Decile 单调性 | +1.000 | +0.988 | +1.000 | — |

**执行经济学（Phase C，真实 Binance 费率）：**

| Regime | Sharpe | Net P&L (bps) | Trade Rate | Win Rate |
|---|---:|---:|---:|---:|
| Always trade | −342 | −228,202 | 100% | 28.7% |
| Confidence-gated (τ=0.067) | −157 | −85,107 | 36.7% | 27.0% |
| **Holding strategy (best)** | **+0.07** | **+3.18** | **0.105%** | 28.8% |

**成本敏感性（4 scenarios）：** 即使最乐观的 HFT 级 1/2 bps 费用，Sharpe 仍 −90。**Signal 是瓶颈，不是 cost。**

---

## 2. 迭代旅程（诚实记录 — 哪些成功、哪些失败）

### 2.1 V1 → V4 模型演进（成功项）

| 阶段 | 核心改动 | Val Corr 峰值 | 状态 |
|---|---|:-:|:-:|
| V3 | Conv + Attention 骨干 | 0.082 | ✓ |
| V3 + RevIN | 逐实例归一化 | 0.082 | ✓ |
| V4 full (smoke 100d) | + patch attn + quantile head | 0.029 | ❌ attention 过拟合 |
| **V4 noattn (smoke 100d)** | 去掉 attention | **0.084** | ✓ +0.055 |
| **V4 noattn (700d 3-fold)** | 正式训练 | **0.094 pooled** | ✓ 当前最佳 |

### 2.2 Phase A — Comprehensive Evaluation

12 类指标 + 20 张图。**产出：** 信号质量确认（IC 0.1 级别，机构标准"好"），但 Sharpe 数字当时忽略成本。

### 2.3 Phase B — SG Feature Smoothing (GATE FAIL)

**假设：** Wang 2025 的 Savitzky-Golay 平滑可以从 0.088 → 0.11+ Ridge IC。  
**扫描：** w ∈ {5, 11, 21, 31, 51, 101}。  
**结果：** **最优 w=21 仅 +0.008 Pearson**（远低于 +0.02 门槛）。w=51 已跌破 baseline。  
**原因：** 现有 `compute_microstructure_features` 已做足预处理，SG 边际价值被吞噬。

### 2.4 Horizon Sensitivity (Option C)

**测试：** y_60, y_180, y_300, y_600 完整 4-horizon 对照。  
**结果：**
- y_60 原始 IC 最高（0.15）但 σ 小 → 每笔 gross 反而最低（0.57 bps）
- y_180 单笔最经济（0.69 bps）
- y_300/y_600 stride=60 label overlap 污染 → 通过 subsample 得 clean IC 分别 0.074/0.019
- **y_180 仍是最优 horizon**

### 2.5 V4 y_300 训练 (REJECTED)

**假设：** Ridge y_300 每笔边际略高（0.69 vs 0.61）是否在 V4 上复现？  
**结果：** V4 y_300 pooled Pearson **0.064 vs y_180 0.094**（−32%）。  
**原因：** V4 的 600s 输入窗口对 180s horizon 匹配（ratio 3.3×），对 300s（2.0×）信息不足。

### 2.6 Phase C — Comprehensive Backtest

**核心工程：** `src/evaluation/backtest_engine.py`（无版本后缀），realistic Binance 费率，walk-forward τ* 校准，crypto 24/7 年化。  
**8 个严谨性 Gate 全过。** 20 张图 + 4 个压力场景。  
**关键结果：**
- Always-trade Sharpe −342
- τ-gated Sharpe −157（bootstrap CI [−181, −157]）
- **每笔毛边际 0.6 bps << 成本 8 bps** — 这是项目的物理天花板

### 2.7 Path C — Holding Strategy (QUALIFIED SUCCESS)

**核心发现：** Sharpe 从 −156 → **+0.07**（+156 点改善）。  
**机制：** EMA 平滑 + hysteresis + min-hold，把 trade rate 从 37% 降到 0.1%。  
**caveat：** 净 P&L 仅 +3 bps / 82 天 = 0.04 bps/day，**统计不显著**。  
**意义：** 证明"成本是主要问题"，但绝对 P&L 微不足道。

### 2.8 Phase D Stage 1 — Long-Horizon Feature Probe (FAIL)

**假设：** 加多尺度聚合特征（5m/10m 滚动均值、vol、flow）能提升长 horizon IC。  
**结果：** 加后 Pearson **全下降 0.002-0.006**（所有 horizon）。  
**原因：** 现有 64 特征已含 `realized_vol_300s`/`cumulative_net_flow_300s` 等 —— 新特征冗余。  
**含义：** 长 horizon 不是"特征不匹配"问题，而是**信号本身衰减快于 σ 增长**。

---

## 3. 核心量化发现（可复用知识）

### 3.1 单资产中频预测的物理天花板

在 BTCUSDT perpetual + Binance retail 费率下：

$$\text{需要盈利} \Leftrightarrow \text{IC} \times \sigma_y(\text{bps}) \times 1.76 > \text{成本}(\approx 8 \text{ bps})$$

| Horizon | σ_y (bps) | 需最低 IC |
|---|---:|---:|
| 3 分钟 | 3.9 | **1.16（不可能）** |
| 10 分钟 | 7.3 | 0.63（不可能） |
| 30 分钟 | 13 | 0.35（很难） |
| 1 小时 | 18 | 0.25（很难） |
| 4 小时 | 36 | 0.13（理论可能） |
| 1 天 | 87 | 0.05（很可能） |

**观察到的 IC：** 3 分钟 0.10；衰减到 10 分钟 0.045。长 horizon 信号不是保持 0.10 级别。

### 3.2 成本经济学 vs 风险管理的区别

- **Grinold-Kahn（IR ∝ √N）：** 多信号降风险 → Sharpe 上升。**只在 net edge > 0 时有效**。
- **单资产负净边际场景：** 加资产（相同 IC、相同成本）= 亏更多。**不是盈利方案**。
- **真正破局路径：** 拉长 horizon 让 σ 增长超过 IC 衰减（但变成 swing trading 问题）。

### 3.3 Holding Strategy 的杠杆效应

**Path C 验证：** trade_rate 从 36.7% → 0.1% 把 Sharpe 从 −156 → +0.07。每减少 1 笔无效交易 = 净约 6 bps 减少亏损。**交易频率才是第一杠杆，不是信号强度**。

### 3.4 DL 相对线性模型的增量

- V4 比 Ridge Pearson +0.007，Spearman +0.001
- 每训练 1000× 计算成本，获得 7% 相对提升
- V4 捕捉独特非线性（R² 简单因子→q50 仅 0.004）
- 但**绝对收益差距**（V4 vs Ridge）**不值得**相差 1000× 计算成本

---

## 4. 方法论遗产（对未来项目有价值）

### 4.1 基础设施
- **`src/evaluation/backtest_engine.py`**（生产级回测）—— 真实费率、walk-forward τ*、crypto 24/7 年化、block bootstrap CI、holding strategy 模式
- **`scripts/comprehensive_eval.py`**（12 类指标 + 20 图）—— 可复用于任何 model
- **`scripts/ensemble_v4_xgb.py`** —— 模型集成模板
- **`scripts/phase_c_bnb_sensitivity.py`** —— 成本敏感性框架
- **Gate 式实验流水**（Phase D Stage 1 示范）—— 低成本快速验证假设

### 4.2 理论文档
- `docs/PROJECT_OVERVIEW.md` —— 项目入口（架构、特征、指标术语）
- `docs/PROJECT_PRINCIPLES.md` —— 7 条量化操作原则
- `docs/METRIC_DISCIPLINE.md` —— Spearman + Pearson 双指标规范
- `docs/V4_MODEL_AUDIT.md` —— V4 模型每模块深度审计
- `docs/HORIZON_DECISION.md` —— horizon 选择决策文档
- `docs/SG_GATE_RESULT.md` —— SG 假设否定记录
- 本文档 `docs/FINAL_REPORT.md`

### 4.3 反模式（避免未来重犯）
1. 用 `trade_rate=1.0` 评估信号（无成本 Sharpe 是骗局）
2. stride < horizon → 标签重叠污染 IC
3. 忽略 Python 输出缓冲（让训练"看起来"没进展）
4. 用 4 bps taker fee（实际 5 bps，差 25%）
5. 把 Cross-sectional 的 IR ≈ IC × √N 直接套用到 time-series 单资产

---

## 5. 未来可能路径（按可行性）

### ✅ 已验证不可行（别再做）
- 单资产中频预测性交易的任何细节优化（特征、模型、loss）
- 横向 horizon 切换（y_60/y_300/y_600 都被测过）
- 多资产同信号扩展（数学上不救命）

### ⚠️ 理论可能但成本极高
- **Swing trading（日级）：** 需完全不同的特征（日内累积、宏观、funding rate、BTC dominance）+ 重新训练。**相当于启动新项目**。
- **多资产不同信号：** 对每个资产找**各自**最优 alpha 源。工作量 = N × 当前项目。
- **新数据源（options flow, cross-exchange, funding curve）：** 可能突破 IC 上限，但采集 + 验证 1-3 个月。

### 🔄 不同 paradigm
- **Market making：** 不预测方向，赚 bid-ask spread + rebate。完全不同研究。
- **跨交易所 latency arb：** 需要低延迟基础设施，小团队不现实。
- **Funding rate arb：** 利用 perp vs spot 价差，完全不同策略。

---

## 6. 项目的最终定位建议

综合 Phase A-D 所有证据，以下是**严谨、诚实、不粉饰**的定位建议：

### 📌 建议 1：接受"研究级 alpha"定位
- 信号质量机构水平（IC-IR 1.4）但无法盈利（成本 > 单笔边际）
- 不是"差"的项目，是"到物理天花板"的项目
- 类似"我们发明了一个正确的实验装置但物理定律决定它不能 output free energy"

### 📌 建议 2：不继续投入当前方向
- Phase A-D 已系统性证伪所有 cost/signal 优化路径
- 继续迭代 = 边际递减工作

### 📌 建议 3：冷启动新方向（若要继续）
- 如果仍想继续：**放弃 "单资产中频预测性交易"** paradigm
- 选一个：swing trading、market making、跨交易所 arb 
- 新 paradigm 意味着**新项目**（重用工具但重建主路径）

### 📌 建议 4：知识沉淀重要
- 本文档 + `docs/PROJECT_PRINCIPLES.md` + memory 条目构成**可迁移的方法论资产**
- 未来启动任何量化项目（crypto、股票、futures）都可以复用这些严谨性框架

---

## 7. 数字汇总表（一图流）

| 维度 | 数值 | 评级 |
|---|---:|:-:|
| Pooled IC (Pearson) | 0.097 | ⭐⭐⭐ 机构水平 |
| Daily IC-IR | 1.47 | ⭐⭐⭐⭐ 强 |
| 信号稳定性（% 正 IC 天数） | 92% | ⭐⭐⭐⭐ 优 |
| Decile 单调性 | +1.000 | ⭐⭐⭐⭐⭐ 完美 |
| 量子校准（V4）| q10/q50/q90 coverage 误差 < 0.005 | ⭐⭐⭐⭐⭐ 完美 |
| 每笔毛边际 | 0.6 bps | ❌ 低于成本 |
| Maker-taker 回合成本 | 8.6 bps | 固定 |
| **净 P&L (always trade)** | **−228,201 bps** | ❌ 深度亏 |
| 净 P&L (holding strategy) | +3.18 bps | ⚠️ 不显著 |
| 跨 fold 稳定性（std）| 0.0023 | ⭐⭐⭐⭐⭐ 极稳 |

---

## 8. 一句话归档

> **"我们建立了一个 IC 0.1 机构级信号的单资产中频预测模型，但物理经济学决定它在当前 BTCUSDT retail 费率下无法盈利。方法论和工具链完整留档。"**

---

## 附：推荐给团队的阅读顺序

新人入项目 30 分钟即可理解全貌：

1. `docs/FINAL_REPORT.md` (本文档) — 10 min
2. `docs/PROJECT_OVERVIEW.md` — 10 min
3. `experiments/phase_c/REPORT_ZH.md` — 10 min（Phase C 的诚实回测数字）

深入细节：

4. `docs/PROJECT_PRINCIPLES.md`
5. `docs/HORIZON_DECISION.md`
6. `docs/SG_GATE_RESULT.md`

代码索引见 `docs/PROJECT_OVERVIEW.md` 第 9 节。
