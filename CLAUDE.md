# DL Quant — Project Guidance

## Project Identity

**What:** 利用创新的深度学习模型，对 Binance BTCUSDT 永续合约进行中高频交易预测（过去若干时间步预测未来 1-10min 收益率）。

**Who:** 个人或极小团队。资源有限但追求理论深度和工程质量。

**Vision:** 创新、稳定、综合性能兼备的框架，实现稳定可观的决策收益。不是极限 HFT（不需要 co-location/FPGA），而是 mid-frequency alpha — 用更聪明的模型和特征工程弥补基础设施的不足。

---

## Core Constraints (不可违反)

1. **信号极弱 (R² < 1%)** — 任何设计决策都必须尊重这个物理事实。模型容量必须匹配信号强度，不能用复杂度"强行拟合"噪声。
2. **数据有限** — 当前仅 1 天数据，目标 30-90 天。在数据规模验证之前，不做超过 15K 参数的模型。
3. **非平稳性** — 金融序列的分布和特征-收益关系持续漂移。任何"在训练集上很好"的结论都必须在多日时序 CV 上验证。
4. **预处理 > 架构** — Wang et al. (2025) 在 crypto LOB 上验证：Savitzky-Golay/Kalman 滤波 + 简单模型 ≥ 复杂深度学习。特征工程的优先级永远高于模型创新。
5. **个人/小团队** — 不追求工业级规模（无 1B 参数模型），追求理论深度和实践效果的平衡。

---

## First Principles (所有决策的理论依据)

### 决策检查清单

每次做出架构、特征、训练策略的改动，必须回答：

- [ ] **信号验证：** 这个改动解决的是"找到信号"还是"拟合噪声"？用 Ridge/XGBoost 做 ablation 了吗？
- [ ] **复杂度预算：** 新增了多少参数？在当前数据规模下 params/unique_samples 比是否合理 (目标 < 1:10)？
- [ ] **理论依据：** 这个方法有论文验证吗？在低 SNR 环境下测试过吗？还是只在 high-SNR 场景（NLP/CV/RecSys CTR）验证过？
- [ ] **噪声鲁棒性：** 如果输入是纯噪声，这个组件会不会"学到"虚假模式？有没有过拟合的结构性风险？
- [ ] **时间尺度匹配：** 特征/模型组件的时间尺度和预测 horizon (3min) 匹配吗？不要用 5 分钟窗口推断小时级 regime。
- [ ] **OOS 验证：** 在时间上严格隔离的测试集上验证了吗？不是同一天的不同时段。

### 禁止事项

- **禁止** 在单日数据上声称模型有效
- **禁止** stride < horizon (会导致标签重叠，虚假低 loss)
- **禁止** 不经 baseline 对比就采用复杂架构
- **禁止** 引用方法时使用过时/未验证的来源
- **禁止** 盲目乐观地描述数据源/方法的可用性（必须实际验证）

---

## Architecture Philosophy

### 双路径输入原则 (Domain Knowledge + Learned Representation)

**核心理念：** 不是 "手工特征 OR 原始盘口"，而是 **"手工特征 AND 原始盘口"**。
- **Path A (Domain Knowledge):** 手工特征编码已知有效信号（OBI, volatility, flow），在有限数据下提供稳定锚点
- **Path B (Learned from Raw):** 原始盘口张量让模型发现人类没想到的结构（深度剖面形状、隐含支撑阻力、cross-level 相关性）
- **Deep learning 的正确使用方式是补充领域知识，而非替代领域知识**

```
Path A: 44 手工特征 → MaskNet + GDCN → h_craft (B, L, d_model)
Path B: Raw LOB (B, L, 20, 4) → Spatial Conv → h_raw (B, L, d_raw)
Fusion: concat → Linear → CausalConv → Temporal → Quantile Output
```

Raw LOB 张量设计：
- 每档 4 值: [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]
- 价格: 相对 mid 的 bps (消除非平稳性)
- 数量: log1p (压缩重尾分布)
- 用 Conv2d 跨档位卷积 (局部感受野匹配盘口的局部结构)

### 递进验证原则

```
Layer 1: 特征工程 + 线性/树模型     → 证明信号存在 (Ridge, XGBoost, FITS)
Layer 2: 双路径神经网络             → 证明 raw path 和非线性有价值
Layer 3: 创新组件 (有理论依据)      → 证明每个组件贡献正向
```

**不跳层。** 如果 Layer 1 失败，不进入 Layer 2。Layer 2 中 Path A 和 Path B 需独立验证各自贡献后再 fusion。

### 当前采纳的 SOTA 方法（每个都有论文和工业验证）

| 组件 | 来源 | 作用 | 验证 |
|---|---|---|---|
| Savitzky-Golay 滤波 | Wang 2025 (crypto LOB) | 输入预处理降噪 | BTC/USDT LOB 直接验证 |
| **Raw LOB Conv encoder** | DeepLOB 2019 + TLOB 2025 | 学习盘口空间结构 | **Bitcoin 直接验证** |
| GDCN 门控交叉层 | CIKM 2023 | 噪声门控的特征交叉 | Criteo #1 |
| MaskNet Instance-Guided Mask | DLP-KDD 2021 | 逐样本噪声抑制 | Twitter/X 生产 |
| PPNet Gate | KDD 2023 | Regime 条件化（显式先验） | 快手 300M DAU |
| FITS | ICLR 2024 Spotlight | 频域 baseline (10K params) | 多 benchmark SOTA |
| Masked MA Pre-training | arXiv 2506.16746 (2025) | 金融自监督 | 金融时序验证 |
| TLOB 双注意力 | Feb 2025 | LOB 空间+时序 | Bitcoin F1=74.7% |

### 已识别的当前架构缺陷

1. **SpatialLOBEncoder 分组语义错误** — `set_feature_groups()` 从未调用，三组按索引位置分割
2. **RegimeAwareFeatureGate 时间尺度错误** — 5 分钟窗口无法推断小时级 regime
3. **多任务损失梯度冲突** — 4 个 loss 导致 0.94 残差自相关（模型输出近常数）
4. **Direction loss 阈值单位不匹配** — 归一化后的 target 用了 raw bps 阈值
5. **分位数交叉未约束** — q10 可能 > q50 > q90
6. **标签重叠** — stride=10, horizon=180, 相邻 label 共享 170/180 秒

---

## Data Strategy

### 数据源（已验证，2026.4）

| 来源 | 状态 | 格式 | 成本 |
|---|---|---|---|
| Bybit 免费历史 (ob500/ob1000) | 已确认可用 | JSONL, 需适配器 | $0 |
| Binance WebSocket 自建采集 (20档 @100ms) | 可行 | JSON stream | $0-5/月 VPS |
| Crypto Lake | 已确认有免费样本 | API | $64/月 |
| tardis.dev | 已确认可用 | CSV (完美匹配) | ≥$300/月 |

### 数据递进策略（先小后大，逐步验证）

```
Step 1: 下载 3-5 天 Bybit 数据 → 截取 25 档 → 跑通完整 pipeline
        验证: 格式、特征计算、NPZ 生成、baseline 训练全链路通
        
Step 2: 扩展到 30 天 → 25 档
        验证: 多日 temporal CV, baseline 指标, 存储/内存可控
        
Step 3: (仅在 Step 2 证明信号存在后) 考虑是否需要更深档位
        大概率不需要 — 3min 预测深档信号极弱
```

Bybit 适配器已内置截取逻辑（从 500 档取前 25 档），无需额外代码。
不要一上来就用全量 500 档 — 数据量和处理复杂度会大 20x，且深档对 3min 预测贡献极小。

### 数据处理管道

```
Raw data (JSONL/CSV) → resample_lob_to_1s
  ├─ Path A: compute_microstructure_features → SG 滤波 → order flow 特征 → feat_matrix (N, 44+)
  ├─ Path B: extract_raw_lob_tensor → normalize (bps + log1p) → lob_tensor (N, n_levels, 4)
  └─ build_npz_for_day (stride ≥ 60): 保存 X_feat, X_raw, y, y_mask
```

---

## Development Process

### Review Gates

每完成一个 Phase 或重要改动后，执行全面 Review：

1. **目标对齐检查：** 这个改动是否让我们更接近"稳定可观的决策收益"？还是只是技术上的探索？
2. **理论验证：** 改动的每个部分是否经得起第一性原理的审视？
3. **指标检查：** OOS correlation、residual autocorrelation、left tail bias 是否改善？
4. **复杂度审计：** 总参数量、训练时间、推理时间是否在预算内？
5. **失败分析：** 如果指标没有改善，根因是什么？是数据不够、特征不对、还是模型假设错误？

### Documentation Requirements

- **每次实验** 记录：假设 → 改动 → 结果 → 结论
- **失败经验** 和成功经验同等重要，必须记录根因分析
- **Plan 文档** 保持更新 (`docs/superpowers/plans/`)
- **Memory** 记录跨会话需要保留的洞察

---

## Current Phase: Phase 0-1 (Parallel)

### Phase 0: Data Acquisition
- [ ] Bybit 历史数据下载 + JSONL→CSV 适配器
- [ ] Binance WebSocket 采集脚本 (后台持续运行)
- [ ] 数据质量验证（gap 检测、异常值、时间连续性）

### Phase 1: Signal Verification
- [ ] 添加 5 个 order flow 特征
- [ ] 添加 Savitzky-Golay 特征滤波
- [ ] 修复 SpatialLOBEncoder 特征分组
- [ ] 构建 Ridge / XGBoost / FITS baseline (手工特征)
- [ ] **构建 Raw LOB tensor 提取 + Conv baseline** (原始盘口)
- [ ] 在 30 天数据上运行多日时序 CV
- [ ] 对比: 手工特征 vs 原始盘口 vs 双路径融合
- [ ] **Gate Decision:** 任一路径 OOS corr > 0.03 → 进入 Phase 2

### Phase 2: Theory-Driven Innovation (Phase 1 通过后)
- [ ] **双路径融合架构**: Path A (MaskNet+GDCN) + Path B (Spatial Conv) → Fusion
- [ ] MaskNet instance-guided noise suppression (Path A)
- [ ] GDCN gated cross layers for feature interaction (Path A)
- [ ] Raw LOB Conv encoder with learned spatial features (Path B)
- [ ] PPNet-style regime gate with explicit hourly priors (Fusion层)
- [ ] Quantile head with monotonic constraint
- [ ] **Gate Decision:** 双路径显著优于单路径 baselines (p < 0.05)

### Phase 3: 回测验证 + 实盘对接
- [ ] 回测框架 (BacktestEngine, 分位数驱动仓位, 成本模型)
- [ ] 端到端: 模型 → 回测 → Sharpe/MaxDD 评估
- [ ] 实盘 paper trading 对接 (Bybit REST API)

### 观察项 (仅当 Phase 2 不达标时考虑)
- ~~Masked Moving Average pre-training~~ — 降级。理由: 26K params / 43K windows 数据不稀缺;
  额外复杂度 (两阶段训练、超参增多) 对小团队维护和线上稳定性是负面因素。

---

## Technical Defaults

- **Python**: 3.9+
- **Framework**: PyTorch 2.0+
- **Branch**: `siyu_dev`
- **Testing**: pytest, 每个新组件必须有单元测试
- **Stride**: ≥ 60 (最好 ≥ horizon=180)
- **Max model params**: Phase 1: <15K, Phase 2: <30K
- **Loss**: Quantile only (q10/q50/q90), 不做多任务直到单任务稳定
- **Checkpoint selection**: val_correlation, NOT val_loss
- **CV**: 多日时序 CV, train/val/test 严格按时间顺序

---

## Anti-Patterns (从失败经验中总结)

1. **单日数据验证** — Val corr +0.088 → Test corr -0.102。时段差异 = regime 差异。无效。
2. **Stride=10 + Horizon=180** — 标签共享 170/180 秒。残差自相关 0.94。模型学到"延续上一个预测"。
3. **4 个 loss 同时训练** — 梯度冲突 → 模型输出近常数。Direction accuracy 40.7% < 随机。
4. **Regime 从 5min 窗口推断** — 时间尺度不匹配。Regime 变化发生在小时到天的尺度。
5. **219K 参数 / 6K 样本** — 36:1 参数样本比，在 0.25% R² 的信号下 = 纯过拟合。
