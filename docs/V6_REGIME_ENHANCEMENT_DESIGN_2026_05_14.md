> **创建:** 2026-05-14 23:30 UTC+8 | **Session:** v5push autonomous v6 design
> **上一版本:** docs/MORNING_BRIEF_2026_05_14.md (2026-05-14 早间 — 记 4-way/3-way 结果, 不含 5-way/v3)
> **状态:** in-progress | **作废条件:** v6a/v6b 训练完成后归档 (replaced by morning brief)

# Track REG_arch v6 设计 — Regime info bottleneck attack

## 触发原因 (problem statement)

2026-05-14 PM 用户 push 目标 Pearson 0.07→0.08+, 同时发现 mid/lo regime 占 ~67% 数据但 cov 贡献接近 0 (信号被 |y| 小 + 噪声主导)。

诊断: regime_prior 6 维 (vol_1h, spread_mean_1h, obi_trend_1h, price_return_6h, hour_sin, hour_cos) 是 **information bottleneck** — 无长程 regime context, 无 mid/lo regime 显式 distinguisher。

## 设计纪律 (来自用户 directive 2026-05-14 PM)

- 模块融合精细, 不堆叠 (anti v2 教训)
- 特征要深度设计, 不是"发现概念→粗糙数值"
- 严格 causal, 无泄漏
- 不重 post-hoc fitting
- 不轻易 "ceiling"
- 单 axis ablation (不要 multi-axis)

## v6a — 架构轴 (Architecture-only single-axis)

**Hypothesis:** FiLM 1-layer trunk (`Linear(6, 32) → GELU → Dropout`) 难以表达 regime 组合 (e.g. "低 vol + 趋势" vs "低 vol + 反转")。+1 hidden non-linear layer 解锁 non-linear regime embedding capacity, 不增加 input info, 只增加 expressiveness。

**Diff vs REG_arch baseline:** `film_gate_deeper_trunk=True` → trunk 成为 `Linear(6,32) → GELU → Dropout → Linear(32,32) → GELU → Dropout`。+3168 params (3 gates).

**Files:**
- `src/model/film_gate.py` (FiLMGate `deeper_trunk` 参数)
- `src/model/dual_path_model_v3.py` (`film_gate_deeper_trunk` flag + plumbing)
- `run_pipeline_v3.py` (whitelist)
- `configs/v5push/singh_alpha0_huber_track_reg_arch_v6a.json`

**Smoke test verification (2026-05-14 23:25):**
- Baseline (default flag=False): params=118,452, strict-load REG_arch fold 0 ckpt PASS
- v6a (flag=True): params=121,620 (+3,168), trunk 是 2-layer Sequential

**Risk:** 低 (additive layer, identity-init friendly, baseline 完全保留)

## v6b — 数据轴 (Feature-only single-axis)

**Hypothesis:** 6 维 regime input 缺 (1) 长程 (24h+ / weekly) regime context, (2) regime stability / transition indicators, (3) mid/lo regime 的显式 distinguisher。补 6 维 daily y-statistics aggregation 给 model 看到"过去 N 天 y 分布长什么样"。

**新增 6 维 (regime_prior d=6 → 12):**

| 新 dim | 含义 | 时间尺度 | 解决 |
|---|---|---|---|
| `(30, "mean")` | 过去 30d daily mean of y_600 | month | regime drift level |
| `(30, "std")` | 过去 30d std of daily means | month | drift instability / regime transition |
| `(30, "vol_mean")` | 过去 30d mean of daily std | month | vol regime level (long) |
| `(30, "vol_std")` | 过去 30d std of daily std | month | vol-of-vol regime |
| `(7, "mean")` | 过去 7d daily mean | week | recent regime drift |
| `(7, "vol_mean")` | 过去 7d mean of daily std | week | recent vol level |

**为什么这 6 个不是"粗糙数值"** (user 关心点):
- 这是 first-principles regime descriptors (Markov-switching / regime model 经典 indicator), 不是 ad-hoc
- 每个 dim 编码 distinct regime aspect (drift / vol / drift_stability / vol_stability / 时间尺度对比)
- 7d vs 30d 双时间尺度 — 让模型对比"recent vs base regime", 检测 regime change
- mid/lo regime 在 (30, "vol_mean") + (30, "vol_std") + (30, "mean") 三 dim 联合上有 distinct cluster (低 vol_mean + 低 vol_std + ~0 mean = 真静)

**Causality + leakage 审计:**
- Daily stats 来自 NPZ y_600 (mask=1) 仅该天数据
- past N-day aggregation 用 [D-N, D-1] strictly 排除 D
- JSON 一次性 build, 全 991 days valid; dataset.py 加载时按 day_str 索引

**Files:**
- `scripts/build_daily_y_stats_json.py` (offline JSON builder, run once)
- `data/v6b_daily_y_stats.json` (991 days × {mean, std, n}, 86.6 KB)
- `src/training/dataset.py` (fix latent bug: `_compute_past_y_stat` was referenced but undefined; now implemented with kinds {mean, std, sharpe, vol_mean, vol_std})
- `run_pipeline_v3.py` (pass `recent_y_stats_path` + `recent_y_features` to LOBDatasetV2)
- `configs/v5push/singh_alpha0_huber_track_reg_arch_v6b.json` (d_prior=12, recent_y_features list)

**Smoke test verification (2026-05-14 23:28):**
- Dataset loads, `regime_prior` tensor shape = `(12,)` per sample ✓
- has_regime_prior=True, no errors

**Risk:** 中 (新 6 dim 可能被 fold-norm 压平为常数;若 daily stat 变化太慢, 实际 entropy 低)

## Sequencer 执行计划

当前进行中: v4 (n_blocks=3 + 4 FiLM, GPU). 估剩 ~2h.

队列 (机器自动):
1. v4 → v5 (seq direction BCE) [main sequencer PID 71985]
2. v5 → v6a (deeper FiLM trunk) [main sequencer]
3. v6a → v6b (enhanced regime features) [独立 sequencer PID 72454]

预计完成时间 (单 fold ~45min, 3 folds ~2h15m / track):
- v4 done ≈ 2026-05-15 01:30
- v5 done ≈ 2026-05-15 03:45
- v6a done ≈ 2026-05-15 06:00
- v6b done ≈ 2026-05-15 08:15

## 评估流程 (每 track 完成后)

1. 自动 pull preds 到 local
2. 加进 5-way / 6-way ensemble grid search
3. 单独 standalone P/S/DA 测 (RAW + LIVE)
4. 若 P > 5-way pool +0.003 → 加入 production ensemble
5. 若 NEG 显著 (-0.01+) → memory + skip
6. Morning brief 时间顺序汇总
