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

---

## 2026-04-15/16: Phase 2 — DualPathLOBModelV3 + 多日数据管道 + 两轮代码审查

### Session Context

获得 **1004 天历史数据** (`crypto_data/book_snapshot_25/{YYYY-MM-DD}/BTCUSDT.csv.gz` + `crypto_data/trades/trades/{YYYY-MM-DD}/BTCUSDT.csv.gz`，覆盖 2023-01-01 ~ 2025-09-30)，触发从 Phase 1 signal verification 直接跨到 **Phase 2 全面训练+评估**。同时基于 V2 双路径基座完成 V3 架构升级。

### Work Branch

`siyu_dev_2` — 从 `siyu_dev` 拉出，目的是在不动现有工作的前提下做本次大规模训练准备。

### Completed Work (in this session)

#### A. V3 模型架构就绪（已从 siyu_dev 继承）
- `src/model/dual_path_model_v3.py` — **DualPathLOBModelV3** (MaskNet + GDCN + RawLOBEncoder + Conv TCN + Patch Attention + MonotonicQuantileHead)
- 7 个子模块: `masknet.py`, `gdcn.py`, `patch_attention.py`, `raw_lob_encoder.py`, `ppnet_gate.py`, `monotonic_quantile.py`, `cross_asset.py`
- `src/training/trainer_v2.py` — 单任务 quantile loss 训练循环；checkpoint by val corr；NaN 梯度跳过；warmup + ReduceLROnPlateau(mode="max")
- `src/evaluation/backtest_v2.py` — 置信度加权仓位、Newey-West HAC 纠正 overlapping labels
- `src/evaluation/walk_forward.py` — 多折前向验证
- `src/baselines/` — Ridge / TemporalRidge / FITS (26K params, ICLR 2024) / 4 个 naive baselines

#### B. 多日数据处理管道（本会话新建）
- `src/features/multi_day_pipeline.py` — `process_multi_day_crypto_folder()`：遍历日期目录、读 book+trades、resample、compute features、save 压缩 NPZ。按日错误隔离，skip_existing，磁盘地板保护 (500MB)。
- **关键修复**: `_read_gzipped_csv_robust()` 处理 iCloud 截断的 gzip (每个真实文件大约 ~14MB 被截断，实际含 3–14h 数据；原 `pd.read_csv(compression="gzip")` 抛 EOFError 丢弃所有已解压行)
- 交易数据 schema 规范化：`amount→size`, `id→exec_id`, lowercase side → "Buy"/"Sell"

#### C. 训练配置与 baseline runner
- `configs/full_run.json` — 180/30/30 天 walk-forward × fold_stride=60 → ~13 折，stride=180=horizon（无标签重叠）
- `run_baselines.py` — NPZ → 80/10/10 temporal split → Ridge/TemporalRidge/FITS + 4 naive baselines，JSON 汇总
- V3 small 配置: d_model=32, d_raw=16, patch_size=10, attn_nhead=2, depth=1 × 1 → ~58K params（1.6x 超 CLAUDE.md 30K ceiling，明确标为 Phase 2 探索配置）

#### D. 两轮代码审查 + 集中修复

**第一轮 (model/training/backtest)** — 1 个 Critical + 9 个 Important + 7 个 Minor  
**第二轮 (data pipeline)** — 1 个 Critical + 4 个 Important + 7 个 Minor

| # | 等级 | 文件 | 问题 | 修复 |
|---|---|---|---|---|
| C1a | Critical | `run_pipeline_v3.py` | 多日模式**从未归一化 y** — MonotonicQuantileHead.MIN_DELTA=0.01 假设归一化目标[-5,5]，实际收到原始对数收益率(~1e-5 to 1e-3)，每个分位区间大 1000× | 每折基于 train 计算 MAD σ，应用到 train/val/test，保存 `norm_params.npz`，传入 backtest 反归一化 |
| C1b | Critical | `src/features/resample.py` | `dropna(how="any")` 跨 100 LOB 列 — 任一档位持续 NaN 就静默抹掉整天 | 只对 top-of-book (L0 bid/ask price/amount) 做 dropna；深层缺失 price 填成同侧 L0 price（平墙），amount 填 0；>5% 掉行时 warning |
| I1 | Important | `src/features/pipeline.py` | `feature_clip=10.0` 压扁 bps-量级特征 (`weighted_price_*`, `*_slope_L10`, `microprice_dev_bps`)；压力时段常 >10 bps | 默认改 1000；LOBDatasetV2 的 z-score±10 仍然保证训练数值稳定 |
| I2 | Important | `src/features/pipeline.py` | 交易/derived 特征维度不匹配时**静默跳过 concat** (49 vs 58 feature inconsistency) | 改为 `raise ValueError` 带诊断 |
| I3 | Important | `run_pipeline_v3.py` | NPZ 被加载两次 (stats + normalize) — 与数据生产者竞态风险 | 一次加载，in-place normalize |
| I4 | Important | `src/features/trade_features.py` | NaN side 被判为 `~False = True` → 全归入卖方，系统性偏倚 `trade_imbalance` | `dropna(subset=["side","size","price","timestamp"])` 前置 |
| I5 | Important | `src/training/dataset.py` | X_raw 日间存在性不一致时静默降级 Path A | 检测到差异 → `raise ValueError` 列出异常天 |
| I5b | Important | `src/training/dataset.py` | features 列表日间漂移（同 count 不同序）会静默训练崩坏 | `raise ValueError` on drift |
| I7 | Important | `src/features/multi_day_pipeline.py` | `len(df_1s) < input_len` 太宽 → mask=0 垃圾窗口进入 NPZ | 改为 `input_len + horizon_sec` 下限 |
| I8 | Important | `run_baselines.py` | feature 列表不匹配只 warning，`np.concatenate` 仍然会 crash 或静默 corrupt | 改为 `raise ValueError` |
| M4 | Minor→执行 | `src/features/multi_day_pipeline.py` | 某些 CSV 文件首尾含隔日数据 | resample 后加文件夹日期范围过滤 |
| — | Fix | `src/baselines/naive_baselines.py` | 默认 feature 名为 V2 schema (`net_trade_flow_L5`, `microprice_deviation_bps`) 与 V3 canonical 不符 | 改 `net_trade_flow_1s`, `microprice_dev_bps` |

**已修复 commits**:
- `74c4cd1` fix: critical y-normalization gap + silent schema-drift holes
- `07d7024` fix: data pipeline audit — deep-level NaN void, silent fallbacks, clip, NaN-side  
- `2d46497` fix: correct canonical feature names in naive baselines

**测试状态**: 247/253 passing (6 个是 conda torch 版本问题的预存 errors，与本次修改无关)

#### E. 数据处理重启

**为什么重启**: Phase 2 轮处理到 184/1004 天时发现 I1 (feature_clip=10)，存在的 NPZ 与后续 NPZ 将有不一致的 tail 分布 → training 时 z-score mixed distribution。清理重启更干净。

**当前状态**: 9 / 1004 天 (restart 初期)，预估 4h 完成。

### Open Decisions (pending user input)

1. **参数预算**: 选择了 A (58K params) 而非 C (10K params)。若 Phase 2 训练 overfit 明显，回到 C。
2. **数据范围**: 处理全部 1004 天 vs 截取近 365 天。选前者（磁盘够，walk-forward 更有统计力）。

### Pending Verification Items (等数据处理完成后)

1. **Layer 1 — Signal verification 必须先过**
   - `run_baselines.py` 在至少 30-60 天 NPZ 上跑出 Ridge / FITS / naive 对比
   - 任一 baseline test correlation > 0.03 (CLAUDE.md gate) → 进入 Layer 2
   - 若全部失败 → 问题在特征或数据，不在模型复杂度

2. **V3 walk-forward 训练健康度**
   - 13 折每折 val_corr 均值 / std / min / max
   - 与单折 V2 基线对比 (差值 > 0 即为 V3 复杂度合理)
   - checkpoint-by-corr 是否比 checkpoint-by-loss 有显著差别
   - 残差 autocorrelation ≈ 0（之前 0.94 是多任务 bug 的副作用，现在单任务应该正常）

3. **回测现实性**
   - overlap_ratio=1 (stride=180=horizon) 所以 Newey-West HAC 不触发 — 需要一个 overlap>1 的对照跑确认 HAC 分支可用
   - 4bps taker fee + 1bps slippage 下的 Sharpe / Calmar / trade_rate
   - confidence_sizing = |q50|/(q90-q10) 的 distribution — 若 99% 下都极小，说明 threshold 需调

4. **分位数校准**
   - q10 coverage 应 ≈ 10%, q50 ≈ 50%, q90 ≈ 90% on OOS
   - 上一轮单日实验 q50 只覆盖 28%（系统性上偏），多日能否自动校准

5. **时段/波动率分层稳定性**
   - `stratified_metrics_by_hour` — 凌晨低流动性时段是否仍有信号
   - `stratified_metrics_by_vol_regime` — 高/低波动下相对表现

6. **特征重要性**
   - MaskNet 的 instance-guided mask 激活分布 — 哪些特征系统性被 gate 关掉
   - GDCN 交叉权重 — 哪些对交叉贡献最大
   - 若某些手工特征恒为 ~0，删掉减参

7. **数据文件完整性 (在 baseline 之前必查)**
   - 1004 天中实际被截断数分布
   - 每天 `n_win` 的分布：中位数 / 最小值 / 是否有日度级大异常
   - 如果 >30% 天 n_win < 100，说明截断太严重，考虑重新从 tardis.dev 补数据

### Known Open Risks (not yet addressed)

| 风险 | 严重度 | 缓解计划 |
|---|---|---|
| 58K params / ~100K samples = 1:1.7 (目标 1:10) | 中 | 如 OOS 表现差于 baseline 即降到 C (10K params) |
| Streaming inference 与 batch pipeline 一致性 | 中 | 运行现有 `tests/test_streaming_consistency.py` 确认；第一轮审查 I4 标记 — 尚未单独验证 |
| OnlineMetrics float64 精度在 >1e5 val 样本 | 低 | 当前每折 val ≈ 3K-4K 样本，未触及；若扩大 val window 需切换 Welford |
| 13 折训练预估时间 | 中 | 每折 ~20min on MPS × 13 = ~4.3h；接受 |
| `feature_clip=1000` 是否太松 | 低 | 第一轮训练后查看特征绝对值分位数；若 p99.9 远小于 1000 说明安全 |
| 跨日 `ffill` 的风险（多日 pipeline 按日处理，理论上隔离） | 已缓解 | 每日独立 load → resample → NPZ，不跨日 ffill |

### Artifacts Before Training

**Code branch**: `siyu_dev_2` (ahead of `siyu_dev` by 3 bug-fix commits)

**Available in repo**:
- `configs/full_run.json` — V3 训练配置
- `run_pipeline_v3.py` — 训练入口（--skip-features 跳过特征生成）
- `run_baselines.py` — Layer 1 signal verification
- `run_backtest.py` — 独立回测
- `data/npz_full/` — (progressing) 每天一个 NPZ

**Pending**:
- `data/npz_full/` 完整生成 (1004 天)
- `experiments/v3_full/` 训练产物 (每折 `best_model.pt`, `metrics.json`, `test_results.json`, `norm_params.npz`)

### Decision Gates 路线图

```
Data (1004 days processed)
  ↓
Data quality check (n_win 分布, NaN 审查)
  ↓
Layer 1 Gate: baseline (Ridge/FITS/naive) test_corr > 0.03?
  NO  → 回特征工程 (revisit microstructure/trade/derived)
  YES ↓
Layer 2 Train: V3 walk-forward 13 folds
  ↓
V3 vs baseline 差值 > 0 (每折平均)?
  NO  → 回到 model 简化 (降到 C 10K params)
  YES ↓
Backtest: Sharpe > 1, max_drawdown < 500bps?
  NO  → 回信号，改仓位，调阈值
  YES ↓
Phase 3 planning
```

