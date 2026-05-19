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

**当前 production (2026-05-08):** V5 singh α=0+Huber, single seed=42, BEST checkpoint。

- Production CSV: `exports/v5_singh_alpha0_huber/y600_predictions_live.csv` (含 causal EMA-demean live calibration)
- Config: `configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json`
- Preds: `experiments/v5_final/singleh_alpha0_huber/fold_{0,1,2}/test_preds.npz`
- Pool BEST (n=49,953, raw + dense): **P=+0.0617, S=+0.0686, β=+1.05, σŷ/σy=0.059, bias=+0.18 bps**
- Per-fold P=[0.058, 0.062, 0.068] std=0.004 (CoV 0.062, 历史最紧)
- Top-decile spread +2.64 bps, t-stat +7.14
- 严格自测 15/15 gates pass (`exports/v5_singh_alpha0_huber/STRICT_EVAL.md`)
- Production hygiene: live causal EMA-demean (Layer 2), `y_pred_q50_bps_live` 列

**Architecture**: Conformer (kernel=15, 2 blocks) + LevelAttentionPool over time + 64 hand-crafted Path A + 25-level raw LOB Path B + MonotonicQuantileHead. 109K params, single horizon y_600, d_model=32, d_raw=16, dropout=0.20.

**Loss**: `0.10·pinball + 0.50·utility_rank(α=0) + 0.50·plain Huber(δ=2, w_wrong=0)`. α=0 让 ranking by q50 直接 (避开 q10+softplus 偏负 artifact); plain Huber 避开 dir_huber 0-attractor σ collapse。

**Recipe**: train_days=700, val_days=60, patience=4, val_metric=composite (0.5·P+0.5·S), EMA 0.999, lr=6e-4 cosine warmup, batch=1024。

**完整 milestone + 下一步**: `~/.claude/projects/.../memory/y600_milestone_summary_2026_05_08.md`
**架构 + loss 设计文档**: `docs/Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md`
**Phase B regime adaptation 4 次失败复盘**: `docs/PHASE_B_OVERNIGHT_REPORT_2026_05_06.md`

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

1. **单日数据验证** — Val corr +0.088 → Test corr -0.102。时段差异 = regime 差异。规则: 多日多 fold 验证。
2. **`stride < horizon`** — 标签共享导致残差自相关 0.94, 模型学到"延续上一个预测"。规则: stride ≥ horizon, eval 用 stride10 IID clean.
3. **多 loss 同时训练梯度冲突** — V5-LH 实测输出近常数 DirAcc < 随机. 规则: loss 权重必须实测 σŷ/σy 不崩.
4. **Regime 从 5min 窗口推断** — 时间尺度不匹配, regime 变化在小时-天尺度. 长程 RV (rv_1h/4h/24h, Track R) 是正确方向.
5. **过大 params/samples 比** — V4 219K / 6K = 36:1 过拟合. 规则: params:sample 1:5 到 1:30.
6. **测错了 slice** — V5-LH late-2024 val Spearman 0.073 vs 100-day slice 0.013. 规则: 多 slice 验证再下定论.
7. **y 量级不归一** — MonotonicQuantileHead `MIN_DELTA=0.01` 假设 z-score; raw log return σ≈10bps 会让 softplus 钉死. 规则: y 除以 MAD-σ.
8. **V4 验证 vs V5-LH** — 换架构前必须 V4 proven 在新 horizon 跑一遍作 baseline. 直接 V5-LH y_600 = 0.01 但 V4 = 0.07.
9. **Fold-0 DL 单次结果当 feature 信号** — 规则: 新特征先 Ridge walk-forward (500+ days, 3+ folds) ΔP ≥ +0.005 才上 DL.
10. **UNIT loss 用于 asymmetric tasks** — 噪声大的 task 被降权 = 反向 sabotage primary. 规则: 固定权重 (primary=1.0, aux=0.3) 或 PCGrad.
11. **Prediction variance collapse** — 规则: 每次 test eval 检查 `yp_std / y_std`, 低于 20% 直接 reject 无论 val 多好.
12. **Tail-focal 在低 SNR 上 P/S 分歧** — focal_weight=2.0 让 Pearson 被极值带飞, Spearman 不升. 规则: REPLACE 原 loss 是危险的; AUXILIARY (≤0.30, 原 loss 不动) 是安全的 (#25 验证).
13. **Learnable scalar α (σ-anchor)** — val→test catastrophic drift (β=+0.94 → -0.49). 机制: free Parameter 被 val 调到特定值, test regime 不 transfer. 规则: in-graph β scaling 必须用 batch-statistics anchor 不是 free Parameter. 详 memory.
14. **单 fold/单 seed y_1800 完全不可靠** — 同 config 两次 run β=+0.94 → -0.49. 规则: y_1800 conclusion 必须 3-fold pooled 或 ≥3 seed 平均.
15. **Direct rank loss REPLACE utility_rank = val→test drift** — diff_spearman REPLACE 后 val C=0.067 → test P=-0.007. 机制: rank loss 直接 overfit val rank distribution, EMA 救不了 (问题在学习目标本身). 规则: 不 REPLACE proxy losses; ADD 直接 rank loss 必须 weight ≤ 0.1.
16. **β measurement discipline: provenance + dual formula + σ_ŷ check** — 之前"y_600 fold 2 β=-0.09 sign-flip"是测量错误 (rank-transformed blend 人为膨胀 σŷ). 规则: 报告 β 必须同时报 σ_ŷ/σ_y 和 per-fold ρ; 双向 β 命名明确 (β_y_on_ŷ trading slope vs β_ŷ_on_y shrinkage); npz provenance check (raw vs blend); rank 平均**禁用于** β-calibrated single-asset trading.
17. **Baseline anchor discipline (HARD GATE)** — 历史损失 2 天 / $100 GPU. **Pre-launch checklist**: (a) 明确 production baseline 文件路径并当场重算 (禁止凭记忆引用), (b) SAME script + mask + stride + fold 重算, 偏差 >0.005 STOP, (c) 新 config 从 PRODUCTION baseline 派生, (d) 显式写 `anchor_value` + `gate=anchor+0.005`, (e) "惊人提升"第一反应是 anchor 错. 违反此规则结果作废.
18. **Label engineering 必须在 RAW y 上 evaluate** — smooth_plus +22% P claim 是 *training on y_smooth, evaluating on y_smooth* 循环论证. 规则: evaluation target 必须是 raw production y; 跨 target distribution 不可比 (Pearson denominator var(y) 不同). Smoothing 即使 raw eval 仍可能 hurt tail events.
19. **Eval methodology consistency** — 同一 prediction 在不同 stride/space P 可飘 0.029→0.058 (两倍). 4 个 axis 互相组合 (scale: z vs raw, stride: dense vs stride10, stride origin: per-fold vs concat, target source). **Hard rule**: production 数字 = raw + dense + per-fold-aware. statistical comparison = raw + per-fold-stride10 + block bootstrap CI. CSV 给同事必须 raw y_600 全 mask=1.
20. **dir_huber sign-attraction 0-bug + L2 primary 在低 SNR 上 σ collapse** — `sign(0)=0` 让模型预测 ŷ≡0 dodge 惩罚, σŷ→0. L2-like primary 在 R²<1% 天然 push σ→0. 规则: (a) 不可单独用 L2 primary 在低 SNR; (b) dir_huber 必须 w_wrong=0 + w_extreme=0 (即 plain Huber). 详 `v5_dir_huber_pearson_collapse_2026_05_04.md`.
21. **Calibration bias 投诉先做机制审计** (#21 RECTIFICATION, 反前一版"don't iterate loss"过度概括) — bias 可能是 **结构性 bug** (loss/head 耦合) 而非低 SNR 限制. 案例: utility_rank α=1 + MonotonicQuantileHead `q50=q10+softplus(δ)` → q50 偏负, surgical α=1→0 一行修复 bias -0.41→+0.14bps. **判定 protocol**: (a) 哪个 loss 推哪个 head 输出, (b) head 是否有 monotonic constraint 强加 offset, (c) ranking score 是否取自 head 的 biased 子输出. 结构性根因 → surgical fix; 否则才 post-hoc demean. 详 `v5_alpha0_huber_winner_2026_05_05.md`.

22. **Multi-Resolution Pool (MRP) replace last-token slice 在 y_600 上 NULL (2026-05-13)** — Track E (MRP only) fold 0 P=+0.041 vs V5 prod 0.058 (-0.017); Track G (MRP+TV) fold 0 P=+0.034 更差。**根因**: V5 conformer 已有 2 blocks × kernel=15 effective RF ~30s 多尺度能力; 显式 3-window MRP (60/300/600) 稀释 attention 对 recent dynamics. **规则**: 不要 replace last-token slice with multi-window pool for y_600. 多尺度扩展应在 backbone 内 (dilation, kernel) 而非外部 pool.

23. **Decoupled multiplicative head 在低 SNR 不稳定 (2026-05-13 Track P v1/v2 NULL)** — 尝试 (2σ(s)−1) × softplus(m) 替换 DAQH 的 tanh(s) × softplus(m): σ collapse fold 0 (q50=0 multiplicative attractor). **根因**: (a) (2σ−1) 在 s=0 处导数=0.5 (vs tanh 0.5×, 即 tanh 在 s=0 处导数=1.0) — 弱梯度通过 sign axis; (b) `cls_weight_mode="uniform"` 在低 SNR 50/50 noisy sign 推 sign_logit→0 = q50=0 强吸引子; (c) 移除 lambda_dir_huber 后无强 signed q50 梯度. **规则**: 保留 DAQH 结构 (tanh×softplus + dir_huber > 0 + sigmoid BCE weighting). 不要追求"完全 decoupled" multiplicative head 在低 SNR.

24. **σ-collapse BEST checkpoint bug (trainer fix landed 2026-05-13)** — TV channels with non-zero mean (trade_rate, total_depth) cause epoch 1 init noise σ≈0.001 + spurious high P (random sign correlations). 早期"BEST"被 illusory init epoch 选中, 后续 healthy epochs (σ=0.03+, lower P) beat 不了, patience 早停 → broken checkpoint. **Fix**: trainer_v2.py 加 σŷ/σy ≥ 0.02 gate, 拒绝 init-noise epochs 入 BEST. 同时 gate EMA BEST. **规则**: 任何 BEST checkpoint selection 必须有 σ_ratio 阈值; 任何添加 TV channels 必须 zero-center 或确保 init-stage σ 不崩.

25. **Tail-focal magnitude loss as AUXILIARY ≠ REPLACE (Track P3 vs anti-pattern #12)** — Anti-pattern #12 警告 "tail-focal P/S 分歧" 是 focal_weight=2.0 REPLACE 原 loss 时的现象. **新发现**: 把 `mag_focal_huber` (focal weight clip [0.3, 3.0]) 作为 AUXILIARY 加在 Track A baseline 之上 (保留原 dir_huber=0.50 + pinball + utility_rank) 不引发 P/S 分歧, 反而是 ensemble diversity 关键 (corr(P3, V5)=0.61 vs corr(A, V5)=0.79). **规则**: focal/特化 loss 作 AUXILIARY 加权 (≤ 0.30, 原 loss 不动) 是安全的; REPLACE 原 primary loss 是危险的 (P/S divergence). 详 `v5push_3way_ensemble_winner_2026_05_13.md`.

26. **Causal regime indicator ≠ stratified regime — production-feasible 必须用 past-vol gating (2026-05-13)** — Track Q v2 在 stratified-by-|y| low vol regime P=+0.045 (vs P3 +0.039, +12%) — 真实改进. 但用 causal past-vol (HL=60 EWMA of |y|, lag-1) 分类 "lo regime", Q 优势完全消失 (Q P=+0.075 vs A P=+0.085, A 反而最强). **根因**: past-vol 预测 current-vol 准确度低; "causal lo regime" 样本实际包含 |y| jumps, 与真实 low |y| samples 不重合. **规则**: regime-aware ensemble 必须用 causal indicator 评估, 不可用 future-conditional |y| stratification 作为成功标准; conditional-on-future 的 P/DA 改进不可交易, 仅作 mechanism 验证.

---

## Current Priority

**当前 production (2026-05-13)**: **3-way ensemble (Track P3 + Track A + V5 prod)**
- Weights: w_P3=0.35, w_A=0.30, w_V5=0.35 (value-blend on live-calibrated q50)
- Pool P=+0.0645, S=+0.0723, β=+1.10, σŷ/σy=0.058, DA=0.5288, **DA|y|>σ=0.5485**, TopSpread=+1.58 bps
- vs V5 prod alone: +9.5% P, +9.4% S, +0.5% DA
- High-vol regime (|y|>σ, 33% 样本) P=+0.091 S=+0.094 DA=0.547 — tradeable subset 远超 0.07 目标
- CSV: `exports/v5push_3way_ensemble_p3_a_v5/y600_predictions_3way_p3_35_a_30_v5_35.csv`
- Memory: `v5push_3way_ensemble_winner_2026_05_13.md`

**Single-asset y_600 ceiling 待突破** (用户 push: P 0.07-0.08+, β~1, no bias, monotonic cal):
- Bayes ρ ≈ σŷ/σy ≈ 0.07 物理上限附近
- 3-way ensemble 已达 ρ ≈ 0.065, gap to 0.07 = -0.005
- 通过 fusion / loss / 长程 regime feature / 架构精细化 可能突破 (未 exhausted, 见 Track R plan)

**下一步突破 (按 ROI):**
1. **Track R (current iteration)**: GLU fusion + β-calib loss + 长程 RV TV channels — 3 axis 联合 ablation
2. **Multi-asset breadth (ETH/SOL/BNB)** — portfolio IR 0.6 → 1.5+, single-asset alpha ceiling 上的 Sharpe transformation
3. **正交数据源** — funding rate / open interest / basis / on-chain (脱出 LOB aggregation)
4. **缩短 horizon** — y_180 V4 已 P=0.094 production, y_120/y_300 可探
5. **Production engineering** (regime adaptation 真解): online retraining (周/双周) + IC monitor + auto-stop

**每个创新前必须 (硬门槛):**
- Ridge walk-forward (500+ days, 3+ folds) 验证 mean ΔP ≥ +0.005 才上 DL pod
- V4 proven 架构在同 slice 跑一遍做公平对照
- 每次 test eval 检查 `σŷ/σy ≥ 20%` (除非已证特定低 σ 仍 calibrated)
- P 和 S 同时报告且同向改善, 不接受 P/S 分歧
- 验证多个时间 slice 而非单一 slice
- Calibration bias 投诉先做**机制审计** (anti-pattern #21 RECTIFICATION) → 结构性根因 surgical fix vs fundamental low-SNR limit

**明确不做 (已证无效, 详见 anti-patterns):**
- ❌ V5-LH 系列 / multi_scale / pyramid backbones (variance collapse)
- ❌ 单资产 V4 特征空间扩展 (3 次 Ridge null: tradeflow/LC/infoflow)
- ❌ Multi-horizon UNIT (#10 机制错配)
- ❌ Direct rank loss REPLACE utility_rank (#15 val→test drift)
- ❌ dir_huber w_wrong>0 (#20 σ collapse)
- ❌ smooth target overlay (#18 measurement artifact)
- ❌ σ-anchor learnable scalar (#13)
- ❌ y_300 / y_1800 horizon (#8 V4 -32% / 整条 line dead)
- ❌ MRP (multi-resolution pool) replace last-token slice (#22)
- ❌ Decoupled (2σ−1)×softplus head (#23 σ collapse)
- ❌ TV channels REPLACE Track P3 (#25 — only AUXILIARY/ensemble)

**关键工具:**
- `scripts/v5_alpha0_huber_strict_eval.py` — 12-category strict eval + 15-gate scorecard
- `scripts/v5_singh_live_strict_eval.py` — live calibration eval
- `scripts/v5_singh_temporal_eval.py` — temporal stability + regime adaptation
- `scripts/y600_live_calibrate.py` — causal EMA-demean (production calibration layer)
- `scripts/export_y600_predictions.py` — CSV 生产
- `scripts/bin_plot_diagnostic.py` — E[ŷ|y_bin] calibration plot
