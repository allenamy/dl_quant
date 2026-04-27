# DL Quant — Project Guidance

## Project Identity

**Goal:** Binance BTCUSDT 永续合约中频交易预测。给定过去盘口序列，预测未来 1-10 min 收益率。不同 horizon (y_60 / y_180 / y_300 / y_600 / y_1800) 在不同 trade-off 下创新性地持续提高模型表现。

**Who:** 个人或极小团队。追求理论深度 + 工程质量的平衡，不追求工业级规模。

**Vision:** 创新、稳定、综合性能兼备。mid-frequency alpha，不是 HFT。用更聪明的模型、特征、训练策略弥补基础设施不足。

**Benchmark 实力参照：**
- V4 y_180 已达 clean Pearson 0.09 / Spearman 0.099（已证 solid, production）
- V4 y_600 final_stack (0.5·SWA + 0.5·EMA blend) pooled clean P=0.054-0.074, S=0.056-0.087 (95% CI [0.03, 0.09])
  - fold 0 最强 P=0.083 S=0.109; fold 2 P=0.061 S=0.086; 跨 fold CoV 0.12
- Ridge y_180 baseline ≈ 0.05 Pearson，DL uplift 约 2×

**当前状态 (2026-04-21)：** y_600 pooled clean S=0.087 已接近 0.10 stretch, 但天花板受限于**单资产 + 现有特征空间**。以下路径已**全部验证 null**:
- 特征工程 (tradeflow / long_context / infoflow): 978-day Ridge 3-fold 全部 mean ΔP≈0
- V5-LH 架构 (Mamba + side-aware + cross-path): test variance collapse, clean P=-0.06
- Multi-horizon UNIT: 机制与 primary/secondary asymmetric 错配
- Tail-focal loss: P/S 分歧 (P 被极值带飞)

**下一步方向 (突破 0.10 只剩):** 多资产 breadth, 正交数据源 (funding/OI/basis), 缩短 horizon (y_180 更实用).

---

## Behavioral Guidelines (CRITICAL — 避免常见 LLM 错误)

这些原则存在偏差到谨慎而非速度。对 trivial 任务用判断力。

### 1. Think Before Coding

- 明确说出假设。不确定就问。
- 存在多种解读时，列出来让用户选，**不要静默决定**。
- 若简化方案存在，先提出。必要时 push back。
- 有困惑就停。说出困惑点。问问题。

### 2. Simplicity First

解决问题的最小代码，没有投机性扩展。

- 不写未请求的功能
- 单次使用代码不抽象
- 未请求的"灵活性 / 可配置性"——不加
- 不可能场景的 error handling——不加
- 200 行能 50 行搞定，就 50 行

自检："资深工程师会说这过于复杂吗？" 是 → 简化。

### 3. Surgical Changes

只改必须改的。只清理自己的垃圾。

- 不改邻近代码 / 注释 / 格式
- 不 refactor 没坏的东西
- 匹配现有风格，即使我会换种写法
- 发现无关 dead code → 提一下，不删
- 当自己的改动制造 orphans → 清理掉（imports / vars / funcs）
- 预先存在的 dead code → 不删除除非被要求

测试：每一行变更都要能追溯到用户的请求。

### 4. Goal-Driven Execution

把任务变成可验证的 goal：

- "加校验" → "写 invalid input 的测试，让它们 pass"
- "修 bug" → "写能复现 bug 的测试，让它 pass"
- "refactor X" → "refactor 前后测试都 pass"

多步任务先给简短计划：
```
1. [步骤] → 验证：[check]
2. [步骤] → 验证：[check]
3. [步骤] → 验证：[check]
```

成功标准越强 → 越能独立 loop，越少 clarification 反复。

### 5. 不偷懒、反复调研、精准改进

- 看到异常结果必须深入 root-cause，不接受"玄学"
- 遇到 ceiling 时先挑战数据假设，再挑战模型假设——可能是 window size / 数据 slice / loss 配置的问题
- 失败实验 ≠ 失败项目。失败经验和成功经验同等重要，必须记录根因
- 鼓励创新：在验证信号存在的前提下，尝试新架构 / 新 loss / 新特征

---

## Core Constraints (不可违反)

1. **信号极弱 (R² < 1%)** — 任何设计决策都必须尊重这个物理事实。模型容量必须匹配信号强度，不能用复杂度"强行拟合"噪声。
2. **非平稳性** — 金融序列的分布和特征-收益关系持续漂移。任何"在训练集上很好"的结论都必须在多日时序 CV 上验证。不同时期 y 和特征的关系可能**反号**。
3. **预处理 > 架构** — 特征工程的优先级永远高于模型创新。简单 Ridge 在某些 slice 能匹配 DL，说明特征本身承载主要信号。
4. **个人/小团队** — 不追求工业级规模，追求理论深度 + 实践效果的平衡。

### 决策检查清单

每次做出架构、特征、训练策略的改动，必须回答：

- [ ] **信号验证**：改动解决的是"找到信号"还是"拟合噪声"？用 Ridge/XGBoost 对比了吗？
- [ ] **复杂度预算**：新增多少参数？`params/unique_samples` 比是否合理（目标 1:5 以上）？
- [ ] **理论依据**：有论文 / 工业验证吗？在低 SNR 环境下测试过吗？
- [ ] **噪声鲁棒性**：输入纯噪声时这个组件会不会"学到"虚假模式？
- [ ] **时间尺度匹配**：特征/模型的时间尺度与预测 horizon 匹配吗？
- [ ] **OOS 验证**：时间上严格隔离的测试集验证了吗？不是同一天的不同时段。

### 禁止事项

- **禁止**单日数据上声称模型有效
- **禁止** `stride < horizon`（会导致标签重叠，虚假低 loss）
- **禁止**不经 baseline 对比就采用复杂架构
- **禁止**引用过时/未验证的方法
- **禁止**盲目乐观地描述数据源/方法的可用性（必须实际验证）

---

## Metric Discipline (标准化评估口径)

**所有训练/评估实验必须同时报告 Pearson + Spearman。** 详细规则见 `docs/METRIC_DISCIPLINE.md`。

### 指标分层（从首选到辅助）

1. **Spearman rank IC** — **交易侧首选**。金融收益重尾，Spearman 更稳。
2. **Pearson corr** — 规格合规 + 幅度校准。
3. **Direction accuracy** — 卫生检查，必须 > 50%。
4. **Weighted Sharpe (Newey-West HAC)** — 回测后最终答案。
5. **Clean vs Dense evaluation** — Clean 用 `stride ≥ horizon` 的 subsample（非重叠标签）；dense 是 overlap-inflated。**报告必须同时给 clean + dense**，clean 才是 honest measure。

### 分歧处理

| Pearson | Spearman | 判定 |
|:-:|:-:|:-|
| ✅ | ✅ | 通过 |
| ❌ | ✅ | 交易可用但不合规，记录 + 诊断极端值 |
| ✅ | ❌ | **危险信号** — Pearson 被极端值带飞 |
| ❌ | ❌ | 不合规，继续迭代或记录为负面结果 |

### 不可做

- 不可只报 Pearson 或只报 Spearman
- 不可为 Pearson 达标牺牲 Spearman（"游戏规格"）
- 不可在单指标上做 early stop / checkpoint
- 不可用 R² 作为替代——R² < 1% 噪声主导，数值波动无意义

---

## Documentation Discipline (避免文档迭代混乱)

**所有 Claude 生成的 docs / notes / summaries 必须在文件首行附带元信息**,格式:

```markdown
> **创建:** 2026-04-27 21:30 UTC+8 | **Session:** y1800-track-AB | **关键事件:** Track A V1 fold 1 mid-train, Track B NPZ build 启动
> **上一版本:** docs/Y600_TRACK_A_V1_INTERIM.md (2026-04-26 18:00) — V1 fold 0 finished, ema_test_preds 已存
> **状态:** in-progress | **作废条件:** Track A V2/V3 启动后此文件归档
```

**字段:**
- **创建** — `YYYY-MM-DD HH:MM TZ` 必须精确到分钟,不可省略时区
- **Session** — 一句话标识当时上下文 (e.g. `y600-calib-V1-launch`, `y1800-NPZ-build`)
- **关键事件** — 1-3 个 bullet 总结当时 pod/local 在做的事 (帮助未来 LLM 理解时序)
- **上一版本** — 若有迭代关系,指明前一份相关文档路径 + 时间
- **状态** — `draft | in-progress | final | superseded | archived`
- **作废条件** — 何时此文档应被新文档取代或归档

**禁止:**
- 创建无元信息的 status / interim / progress 类文档
- 用 `_v2` `_final` `_final_v2` 之类后缀替代日期标识
- 同主题多份文档不互相 cross-reference (留下 orphan docs)

**目的:** 跨会话 / 跨 LLM 迭代时不混淆"现在"与"昨天",避免基于过期文档做决策。

---

## Technical Defaults

- **Python**: 3.9+
- **Framework**: PyTorch 2.0+
- **Testing**: pytest, 新组件必须有单元测试
- **Stride**: ≥ 60；eval subsample 到 stride ≥ horizon
- **Loss**: Quantile (q10/q50/q90) 为主，单任务稳定后再考虑多任务
- **Checkpoint selection**: Pearson + Spearman composite，不是单一指标
- **CV**: 多日时序 walk-forward，train/val/test 严格按时间顺序
- **目标 normalization**: y 除以 train 的 MAD-σ，统一量级（避免 MonotonicQuantileHead 等组件的常量假设失效）

### 模型容量指南

- Low SNR + 小数据 → 小模型 + 强正则
- `params:sample` 合理区间 1:5 到 1:30
- 超过 1:2 几乎必定过拟合
- 同等数据下，小模型 seed 方差大，多 seed ensemble 可显著提升

---

## Architecture Philosophy

### 双路径输入原则 (Domain Knowledge + Learned Representation)

核心理念：**"手工特征 AND 原始盘口"**，不是 OR。

- **Path A (领域知识)**：手工特征编码已知有效信号（OBI, vol, flow）
- **Path B (学习表示)**：原始盘口张量让模型发现人未想到的结构

Raw LOB 张量设计：
- 每档 4 值：`[bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]`
- 价格：相对 mid 的 bps（消除非平稳性）
- 数量：log1p（压缩重尾）

### 递进验证原则

```
Layer 1: 特征 + 线性/树模型 → 证明信号存在
Layer 2: 双路径 NN → 证明 raw path + 非线性有价值
Layer 3: 创新组件 → 证明每个组件贡献正向
```

**不跳层**。如果 Layer 1 失败，不进入 Layer 2。

---

## Development Process

### Review Gates

每完成一个 Phase / 重要改动后：

1. **目标对齐**：改动是否让我们更接近"稳定可观的决策收益"？
2. **理论验证**：改动每部分是否经得起第一性原理？
3. **指标检查**：clean Spearman / Pearson / DirAcc / 残差自相关是否改善？
4. **复杂度审计**：参数量、训练时间、推理时间是否在预算内？
5. **失败分析**：指标没改善 → 根因是什么？数据？特征？模型假设？

### Documentation

- **每次实验**记录：假设 → 改动 → 结果 → 结论
- **失败经验** = 成功经验，必须记录根因
- **Plan 文档**保持更新（`docs/superpowers/plans/`）
- **Memory** 记录跨会话需要保留的洞察

---

## Anti-Patterns (从失败经验中总结)

1. **单日数据验证** — Val corr +0.088 → Test corr -0.102。时段差异 = regime 差异。无效。
2. **`stride < horizon`** — 标签共享导致残差自相关 0.94，模型学到"延续上一个预测"。
3. **多 loss 同时训练** — 梯度冲突导致模型输出近常数，DirAcc < 随机（V5-LH 实测）。
4. **Regime 从 5min 窗口推断** — 时间尺度不匹配。Regime 变化在小时到天尺度。
5. **过大 params/samples 比** — V4 219K 参数 / 6K 样本 = 36:1 过拟合。
6. **测错了 slice** — V5-LH 在 late-2024/2025 val (days 700+) Spearman 0.073，早期测试在 100 天切片只到 0.013。time slice 影响极大，换几个 slice 再下定论。
7. **y 量级不归一** — MonotonicQuantileHead 的 `MIN_DELTA=0.01` 假设 z-score 目标。用 raw log return (σ≈10bps) 会让 softplus 被 clamp 钉死、梯度消失、q50 负偏，val Pearson 变负。
8. **V4 验证 vs V5-LH 验证** — 换架构前必须先用 **V4 proven 架构在新 horizon 跑一遍**作为 fair baseline。直接 V5-LH 跑 y_600 得 0.01，切到 V4 同 horizon 可得 0.07，证明 architecture 是 bottleneck 而非数据。
9. **Fold-0 DL 单次结果当 feature 信号** — 2026-04-21 session: LC feature "fold 0 +0.014 P" 被当 breakthrough, 投入 3h pod 训练, 但 978-day Ridge 3-fold 其实是 mean ΔP=-0.002 (null)。**规则:** 新特征必须先 Ridge walk-forward (500+ days, 3+ folds) ΔP ≥ +0.005 才上 pod DL。
10. **UNIT loss 用于 primary/secondary asymmetric tasks** — UNIT (Kendall 2018) 假设所有 task 同等重要, σ 大的被降 weight。若 primary task 噪声更大 (y_600 vs y_180), UNIT 会**反向** sabotage primary。用固定权重 (primary=1.0, aux=0.3) 或 PCGrad。
11. **Prediction variance collapse** — V5-LH test yp_std / y_std < 5% = 模型输出近常数 q50, 任何 val IC 都是 spurious。**规则:** 每次 test eval 检查 `yp_std / y_std`, 低于 20% 直接 reject, 无论 val 好坏。
12. **Tail-focal 在低 SNR 上 P/S 分歧** — focal_weight=2.0 (tail 3× 权重) 让模型过度拟合 |y|>2σ 极值, Pearson 被极值带飞而 Spearman 不升。低 SNR 场景 focal 未证有效。
13. **Learnable scalar α (σ-anchor) 引入 val-tunable 自由度** — 2026-04-27 y_1800 Phase 1.2 实测: σ-anchor (output_scale_init=1.0, β_calib=0.1) val EMA P=0.060, S=0.068 → test EMA P=-0.003, S=0.000 (β=-0.11 翻负)。**catastrophic val→test drift**。机制: α 是单一标量,被 val 调到一个让 val ranks 对齐的特定值,但 test 是不同 vol regime 不 transfer。EMA 平均 *权重* 但 α *本身* 是同一标量,平均后没有平滑效果。**规则:** 不在低 SNR 上加 unconstrained learnable scalar, 任何"in-graph β scaling" 必须用 batch-statistics anchor (e.g. σ_y / σ_ŷ_running 而非 free Parameter)。
14. **单 fold + 单 seed 在 y_1800 上完全不可靠 (cudnn 非确定性 + EMA 路径分歧)** — 2026-04-27 实测: 同 config (Phase 1.1 diff_spearman) 同 seed 两次 run 结果 EMA P 从 +0.036 翻到 -0.017,**β 从 +0.94 翻到 -0.49**。单次 run 的"赢/输"判断 100% 是 noise。**规则:** 任何 y_1800 实验 conclusion 必须基于 (a) 3-fold pooled 或 (b) ≥3 seed 平均。新加的 cudnn determinism (commit 待加) 只 partial 解决,multi-seed 是必须。下游影响: 历史所有 single-fold 0 screen 结果都需重新评估 (Phase 1.1 "winner", Phase 1.2 "fail", Phase 1.1b "fail" 都是 single-run 噪声)。

---

## Current Priority

**主线：** y_180 和 y_600 的 V4 final_stack 已到单资产 ceiling。下一阶段突破需要跳出"单资产 + LOB-time-aggregated"特征空间。

**完成状态：**
1. ✓ **Validate**：V4 架构 y_180 (P=0.094) / y_600 (P=0.074) 建立 baseline
2. ✓ **Innovate 实验**：特征 × 3, 架构 V5-LH × 4 全部 null
3. ~ **Ensemble**：final_stack (SWA + EMA) 完成; seed ensemble 被 user 排除 (post-hoc, non-fundamental)
4. 待办 **Execute**：回测 + holding strategy 已完成 eval (cost-aware break-even); paper trading 未启

**下一步 (突破 0.10 的 fundamental 路径):**
1. **多资产 breadth** — ETH/SOL/BNB data, cross-asset factor, IC-IR 可 1.5+
2. **正交数据源** — Funding rate, open interest, basis, on-chain (非 LOB aggregation)
3. **缩短 horizon 深耕** — y_180 P=0.094 已生产化, y_120 / y_300 可能性
4. **实盘 paper trading** — 单资产即使亏损, 基础设施搭建有价值

**每个创新前必须 (硬门槛):**
- 用 Ridge walk-forward (500+ days, 3+ folds) 验证 mean ΔP ≥ +0.005 才上 DL pod
- 用 V4 proven 架构在同 slice 跑一遍做公平对照
- 每次 test eval 检查 `yp_std / y_std` 不低于 20%
- P 和 S 同时报告且同向改善, 不接受 P/S 分歧
- 验证多个时间 slice 而非单一 slice

**明确不做 (已证无效):**
- ❌ V5-LH Mamba 变种 (test variance collapse)
- ❌ 单资产 V4 特征空间新扩展 (3 次 Ridge null)
- ❌ Multi-horizon UNIT (机制错配)
- ❌ 过激进 post-hoc blending (user 排除)

**关键工具:**
- `scripts/comprehensive_eval.py` — 12-category eval + 图
- `scripts/bin_plot_diagnostic.py` — E[ŷ|y_bin] 反向校准
- `scripts/backtest_y600_final_stack.py` — cost-aware holding strategies
- `docs/Y600_SUMMARY.md` — 完整 y_600 findings 参考
