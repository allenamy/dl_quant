# DL Quant — Progress Log

## 2026-04-13: Phase 0-1 Infrastructure Build

### Session Summary

从第一性原理出发，全面审视并重建项目的数据管道、特征工程、模型架构。

### Completed Tasks

| # | Task | Tests | Status |
|---|---|---|---|
| 1 | Bybit 历史数据下载 + JSONL→CSV 适配器 | 21 pass | Done |
| 2 | Binance WebSocket 20档@100ms 采集器 | 23 pass | Done |
| 3 | Order Flow 特征 (5个) + Savitzky-Golay 滤波 | 8 pass | Done |
| 4 | SpatialLOBEncoder 语义特征分组修复 | 13 pass | Done |
| 5 | Progressive Baseline 框架 (Ridge, FITS) | 11 pass | Done |
| 6 | Raw LOB tensor 提取 + DualPathModel | 18 pass | Done |
| 7 | CLAUDE.md 项目指导文档 | — | Done |

**Total: 116 tests, all pass, zero regressions.**

### Key Decisions & Rationale

#### 1. 双路径架构 (而非纯手工特征 OR 纯 raw)
- **决策:** Path A (44 手工特征) + Path B (20档 raw LOB tensor) 并行
- **理由:** 手工特征提供稳定锚点，raw path 让模型发现人类没预设的结构。Deep learning 的价值在于补充领域知识，而非替代。
- **验证:** DualPathLOBModel 支持 fallback (Path A only)，可以 ablation 各路径贡献

#### 2. 参数量控制: 220K → 12.9K (17x 缩减)
- **决策:** DualPathLOBModel 12,891 params vs LOBTransformerV2 220,309 params
- **理由:** 信号 R² < 1%，219K params / 6K samples = 36:1 ratio 纯过拟合。即使 30 天数据 (43K windows)，12.9K params 给出 0.3:1 的健康比例。

#### 3. 单损失函数 (Quantile only)
- **决策:** 移除 direction CE + uncertainty NLL + asymmetric Huber，只保留 quantile loss
- **理由:** 0.94 残差自相关是 4 个 loss 梯度冲突的症状。Direction accuracy 40.7% < 随机。Uncertainty-error corr = -0.03。多任务在单任务都没做好时是纯负担。

#### 4. 数据递进策略: 先 3-5 天 × 25 档 → 30 天
- **决策:** 不一上来用 500 档全量数据
- **理由:** 500 档数据量 20x 大于 25 档，深档 (26-500) 对 3min 预测贡献极小。先小后大，验证 pipeline 后再扩展。

#### 5. 显式 regime 先验替代 learned regime gate
- **决策:** 用 PPNet-style gate（以小时级 vol, funding rate 为先验），替代 RegimeAwareFeatureGate
- **理由:** 5 分钟窗口的因果累积均值无法推断小时级 regime。Regime 检测的时间尺度应该匹配 regime 变化的时间尺度。

### Architecture Flaws Fixed

| 缺陷 | 修复 | 文件 |
|---|---|---|
| SpatialLOBEncoder 特征分组按索引分割 | 创建 feature_groups.py, run_pipeline.py 调用 set_feature_groups() | src/features/feature_groups.py |
| 无 order flow 特征 | 添加 5 个 delta/flow 特征 | src/features/microstructure.py |
| 无输入降噪 | 添加 SG 滤波 | src/features/microstructure.py |
| 无 raw LOB 路径 | 添加 extract_raw_lob_tensor + RawLOBEncoder + DualPathModel | src/features/raw_lob.py, src/model/ |

### Architecture Flaws NOT YET Fixed (Phase 2)

| 缺陷 | 计划修复方式 | Phase |
|---|---|---|
| RegimeAwareFeatureGate 时间尺度 | PPNet Gate (显式 regime 先验) | 2 |
| 多任务损失梯度冲突 | 已在新模型中用 quantile only 解决 | Done |
| Direction loss 阈值单位不匹配 | 新模型中已移除 direction head | Done |
| 分位数交叉未约束 | 待添加 monotonic constraint | 2 |
| stride=10 标签重叠 | Config 已改为 stride=60, 推荐 ≥180 | Done |

### New Files Created

```
scripts/
  download_bybit.py          # Bybit 历史数据下载
  bybit_to_csv.py            # JSONL→CSV 适配器 (截取 25 档)
  collect_binance_depth.py   # Binance WebSocket 实时采集器
  collected_to_csv.py        # 采集数据→CSV 转换
  collector_monitor.sh       # 采集器监控/重启

src/baselines/
  linear_baseline.py         # RidgeBaseline, TemporalRidgeBaseline
  fits_baseline.py           # FITSModel (ICLR 2024, ~26K params)
  evaluate_baselines.py      # 统一评估脚本

src/features/
  feature_groups.py          # 语义 bid/ask/global 分组
  raw_lob.py                 # Raw LOB tensor 提取

src/model/
  raw_lob_encoder.py         # Conv1d 空间编码器 (~2.8K params)
  dual_path_model.py         # 双路径融合模型 (~12.9K params)

tests/
  test_bybit_adapter.py      # 21 tests
  test_collector.py          # 23 tests
  test_baselines.py          # 11 tests
  test_raw_lob.py            # 18 tests

CLAUDE.md                    # 项目指导文档
docs/PROGRESS.md             # 本文档
```

### Next Steps

1. **获取数据:** 下载 3-5 天 Bybit 数据 → 跑通 pipeline → 扩展到 30 天
2. **Signal verification:** 在 30 天数据上运行 Ridge / FITS / DualPath baselines
3. **Gate decision:** OOS corr > 0.03 → 进入 Phase 2 (GDCN, MaskNet, PPNet)
