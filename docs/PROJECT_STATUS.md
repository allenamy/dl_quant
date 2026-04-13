# LOB Transformer V2 - 项目进度与指标分析

**日期**: 2026-04-13  
**仓库**: https://github.com/allenamy/dl_quant

---

## 一、项目概述

目标：基于 Binance Futures BTCUSDT 25档 L2 订单簿数据，构建 structure-aware、probabilistic 的深度学习模型，预测 3 分钟中频收益率。

### 已完成的模块

| 模块 | 文件 | 状态 |
|------|------|------|
| 1s 重采样 | `src/features/resample.py` | Done |
| 40 维微观结构特征 | `src/features/microstructure.py` | Done |
| CSV→NPZ 管道 | `src/features/pipeline.py` | Done |
| Bid/Ask 空间编码器 | `src/model/side_encoder.py` | Done |
| 因果时序编码器 (RoPE) | `src/model/temporal_encoder.py` | Done |
| LOBTransformerV2 整合 | `src/model/lob_transformer.py` | Done |
| 多任务损失函数 | `src/training/losses.py` | Done |
| 数据集 + 折叠构建器 | `src/training/dataset.py` | Done |
| 训练循环 | `src/training/trainer.py` | Done |
| 评估指标 | `src/evaluation/metrics.py` | Done |
| PnL 回测 | `src/evaluation/backtest.py` | Done |
| 端到端入口 | `run_pipeline.py` | Done |
| 无穿越验证测试 | `tests/test_no_leakage.py` | Done |

### 架构图

```
Raw CSV (~57ms, 1.5M rows/day)
  │
  ▼
resample_lob_to_1s() ──→ 86,400 rows/day (1s bars)
  │
  ▼
compute_microstructure_features() ──→ 40 features per bar
  │                                    (price, spread, imbalance, depth,
  │                                     pressure, volatility, microstructure,
  │                                     slopes, concentration, level ratios,
  │                                     temporal cyclical)
  ▼
build_npz_for_day() ──→ Sliding windows (300 bars input, 180s horizon)
  │
  ▼
LOBTransformerV2 (219K params):
  ├── RegimeAwareFeatureGate (4 soft regimes)
  ├── SpatialLOBEncoder (bid/ask/global cross-attention)
  ├── CausalTemporalEncoder (Conv TCN + Transformer + RoPE)
  └── Multi-Head Output:
       ├── Quantiles (q10/q50/q90)
       ├── Direction (down/flat/up)
       └── Uncertainty (aleatoric)
  │
  ▼
Combined Loss:
  quantile(1.0) + asymmetric_huber(1.0) + direction_CE(0.3) + uncertainty_NLL(0.05)
  │
  ▼
Evaluation + Backtest
```

---

## 二、当前实验结果

### 实验配置

| 参数 | 值 |
|------|-----|
| 数据 | BTCUSDT 2024-10-10 (单日) |
| 预测 horizon | 180s (3 分钟) |
| 输入窗口 | 300 bars @ 1s = 5 分钟 |
| 滑窗步长 | 10s |
| 样本量 | 8,611 windows (train=6,027 / val=1,291 / test=1,293) |
| 模型 | d_model=64, depth=2, nhead=4, 219K params |
| 训练 | AdamW, lr=1e-3, wd=1e-3, batch=128, warmup_cosine |

### 训练指标

| 指标 | 训练集 | 验证集 (best epoch 6) | 测试集 |
|------|--------|----------------------|--------|
| Loss | 1.648 | 3.159 | - |
| **Correlation** | - | **+0.088** | **-0.102** |
| R2 | - | -0.0002 | -0.236 |
| Direction Accuracy | - | - | 40.7% |

### 测试集详细指标

```
Correlation:          -0.1015  (p=0.0003, 统计显著但方向错误)
Rank Correlation:     -0.0671
R2:                   -0.2362  (差于 naive 均值预测)
Residual Mean:        +0.4950  (系统性正偏)
Residual Std:          1.0204
Residual Skew:        +0.2341
Residual Kurtosis:    +1.1066
Residual Autocorr(1): +0.9393  (极高，预测序列过于平滑)
Direction Accuracy:    40.71%  (低于随机 50%)

Left Tail:
  Correlation:        +0.0275  (几乎无预测力)
  Bias:               +1.3164  (严重 overestimate，预测不够负)

Right Tail:
  Correlation:        -0.2359  (反向)
  Bias:               -2.3850  (严重 underestimate)

Quantile Calibration:
  q10 coverage:       5.6%   (期望 10%，偏低)
  q50 coverage:       28.3%  (期望 50%，严重偏低)
  q90 coverage:       89.0%  (期望 90%，基本校准)

Uncertainty-Error Correlation: -0.030 (不确定性与误差几乎无关)

Backtest:
  Trades: 0 (预测幅度未超过交易阈值)
```

---

## 三、问题诊断

### 问题 1: 训练-测试泛化失败 (最关键)

**表现**: Val corr +0.088 → Test corr -0.102

**根因**: 单日数据的时间段差异
- 训练集: 00:00-16:48 (亚洲+欧洲时段)
- 验证集: 16:48-20:24 (欧美交叉时段)
- 测试集: 20:24-24:00 (美洲时段)
- 不同时段的微观结构模式差异显著：波动率、流动性、参与者结构不同
- 模型在训练时段学到的特征-收益关系，在测试时段不成立

**解决方案**:
- **[必须]** 获取 30-90 天数据，使每个 fold 包含所有时段
- 多日滚动交叉验证（管道已支持 `build_time_series_folds`）
- 考虑按时段 (session) 做分层采样而非纯顺序切分

### 问题 2: 残差自相关过高 (0.94)

**表现**: 相邻预测几乎相同，模型输出一个缓慢漂移的序列

**根因**:
- stride=10 导致相邻窗口 97% 重叠 (290/300 共享)
- 模型学到"延续上一个预测"而非"重新评估当前状态"
- 输出头没有足够的正则化来鼓励预测独立性

**解决方案**:
- 加入残差自相关惩罚项到损失函数
- 增大 stride 减少重叠（但牺牲样本量）
- 在多日模式下，每天的窗口彼此独立，问题自然缓解
- 考虑对预测做差分后再评估

### 问题 3: 左尾 overestimate / 右尾 underestimate

**表现**: 市场下跌时模型预测不够负 (bias +1.32)，上涨时预测不够正 (bias -2.39)

**根因**:
- 模型预测趋向均值回归（regression to mean）
- 极端收益率样本少，模型没有学到尾部模式
- 虽然有 asymmetric Huber loss，但整体正则化过强，抑制了极端预测

**解决方案**:
- 更多数据让模型见到更多极端场景
- 可尝试 quantile-specific loss 加重尾部分位数权重
- 对极端收益率样本做 oversampling
- 降低 Huber delta (使 loss 在极端区域接近线性而非二次)

### 问题 4: 分位数校准偏差

**表现**: q50 coverage 仅 28.3% (应为 50%)

**根因**:
- 模型预测的 q50 系统性偏高 (residual_mean +0.495)
- 说明模型存在系统性正偏差
- 可能是训练集/测试集目标分布不一致导致

**解决方案**:
- 后处理校准 (isotonic regression / Platt scaling)
- 训练时加入 calibration loss 惩罚
- 更多数据使训练/测试分布趋于一致

### 问题 5: 不确定性估计无效

**表现**: uncertainty-error correlation -0.03 (应为正相关)

**根因**: uncertainty head 没有学到有意义的信号，可能因为权重过低 (0.05)

**解决方案**:
- 暂时移除 uncertainty head，专注于点预测和分位数
- 或使用 MC Dropout / Deep Ensemble 替代参数化不确定性
- 后期在有更多数据后重新引入

---

## 四、与参考模型 (tf_train_seq_att_v2_new.py) 的对比

| 维度 | 参考模型 | LOB Transformer V2 |
|------|---------|-------------------|
| 输入处理 | flatten S*F → D，丢失结构 | Bid/Ask/Global 分路 cross-attention |
| 位置编码 | Learned embedding (固定长度) | RoPE (支持外推) |
| 特征门控 | 全局静态 Parameter | Regime-aware 动态门控 |
| 输出 | 单点预测 (B,L,S) | 多头：quantiles + direction + uncertainty |
| 损失函数 | 对称 Huber | 非对称 Huber + Quantile + Direction CE + NLL |
| 目标归一化 | MAD sigma per symbol | MAD sigma (单日模式) |
| LR Warmup | 未实现 (只有 guard) | 真正的 linear warmup + cosine decay |
| 检查点选择 | val_loss | **val_correlation** |
| Correlation | ~0.05 (参考值) | +0.088 val / -0.10 test (单日) |

**结论**: 架构全面升级，但受限于单日数据无法验证泛化能力。

---

## 五、下一步计划

### P0: 获取更多数据 [阻塞项]

当前仅 1 天数据 (~86K 秒)，模型无法在 train/test 之间泛化。需要至少 30 天（理想 90 天）的 L2 订单簿数据。

**数据来源选项**:
- tardis.dev API (最全面的加密货币市场数据)
- Binance 历史数据下载
- Kaiko / CoinAPI 等数据供应商

**数据量估算** (90 天):
- 原始: 90 × 1.5M rows × 104 cols ≈ 135M rows → ~90GB CSV
- 1s resample: 90 × 86,400 = 7.78M rows
- NPZ windows (stride=60): 90 × 1,400 = 126K windows → 足够训练

### P1: 多日训练验证

数据就绪后：
```bash
# 数据放入多个 CSV 或一个大 CSV
python3 run_pipeline.py --config configs/default.json
# 自动进入多日模式: 14天训练 / 5天验证 / 5天测试，滚动交叉验证
```

预期：
- Correlation 从 0.088 提升到 0.12-0.18 (多日平均)
- 训练-测试 gap 从 0.19 缩小到 0.03-0.05
- 残差自相关从 0.94 降到 0.3-0.5

### P2: 模型调优

在多日数据上进行：
- 网格搜索: d_model ∈ {32, 64, 128}, depth ∈ {1, 2, 3}, dropout ∈ {0.1, 0.2, 0.3}
- 特征重要性分析: 使用 feature gate 权重排序，移除噪声特征
- 损失权重调优: 找到 quantile vs asymmetric 的最佳平衡
- 考虑移除 uncertainty head，简化模型

### P3: 高级优化

- 残差自相关惩罚
- 尾部样本 oversampling
- 后处理校准 (isotonic regression on quantiles)
- 多 horizon 联合训练 (MTL: 1min + 3min + 5min)
- 在线学习 / LoRA 适配新 regime

---

## 六、代码质量与测试

### 测试覆盖

| 测试文件 | 测试数 | 覆盖范围 |
|---------|--------|---------|
| tests/test_features.py | 4 | 重采样 + 特征工程 + 无穿越验证 |
| tests/test_model.py | 5 | 空间编码器 + 时序编码器 + 全模型因果性 |
| tests/test_training.py | 11 | 损失函数 + 数据集 + 折叠构建器 |
| tests/test_no_leakage.py | 11 | NPZ 管道 + 标签完整性 + 无穿越 |
| **总计** | **31 tests** | |

### 运行全部测试

```bash
python3 -m pytest tests/ -v  # 或
python3 tests/test_features.py && python3 tests/test_model.py && python3 tests/test_training.py && python3 tests/test_no_leakage.py
```

---

## 七、项目结构

```
dl_quant/
├── configs/
│   └── default.json              # 训练配置
├── docs/
│   ├── plans/
│   │   └── 2026-04-12-lob-transformer-v2.md  # 详细实施计划
│   └── PROJECT_STATUS.md         # 本文档
├── src/
│   ├── features/
│   │   ├── resample.py           # 原始 LOB → 1s bars
│   │   ├── microstructure.py     # 40 维微观结构特征
│   │   └── pipeline.py           # CSV → NPZ 完整管道
│   ├── model/
│   │   ├── side_encoder.py       # 空间编码 (bid/ask/global)
│   │   ├── temporal_encoder.py   # 时序编码 (Conv + Transformer + RoPE)
│   │   └── lob_transformer.py    # 完整模型 + RegimeGate
│   ├── training/
│   │   ├── dataset.py            # NPZ 数据集 + 折叠构建
│   │   ├── losses.py             # 多任务损失函数
│   │   └── trainer.py            # 训练循环
│   └── evaluation/
│       ├── metrics.py            # 评估指标 (corr, R2, tail, calibration)
│       └── backtest.py           # PnL 回测
├── tests/                        # 31 个单元测试
├── run_pipeline.py               # 端到端入口
└── .gitignore
```
