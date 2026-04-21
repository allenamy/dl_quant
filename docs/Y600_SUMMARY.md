# Y600 Prediction — Thinking, Best Practices & Metrics

**Project scope:** Binance BTCUSDT y_600 (10-minute forward log-return) prediction.  
**Session window:** 2026-04-19 to 2026-04-21 (multiple push attempts).  
**Current best model:** V4 final_stack (0.5·SWA + 0.5·Block-B-EMA blend of V4 DualPathLOBModelV3 predictions).

---

## 1. 思路演进

### Phase A: V4 baseline 迁移 (2026-04-19)
从 V4 y_180 (P=0.094) 迁移到 y_600。V4 架构直接 train, composite val gate + EMA + SWA 组合。  
**结果:** pooled clean P≈0.062-0.074 — 显著低于 y_180 但 stable。

### Phase B: 特征工程攻关 (2026-04-20 → 2026-04-21)
3 条独立路径尝试 factor discovery:

| 特征族 | 信号理论 | Ridge 3-fold ΔP | 结论 |
|---|---|---:|---|
| TradeFlow (5 feats) | signed volume imbalance 60/300/1800s + VWAP drift + intensity | −0.001 | REJECT |
| Long-context (6 feats) | past-day lr/rv/hurst/mz at 1800/3600s | −0.002 | REJECT |
| InfoFlow (4 feats) | VPIN + large-order footprint | −0.000 | REJECT |

**共同发现:** V4 64 个现有特征已覆盖 time-aggregated 信号。更长尺度/不同变换版本与现有特征 collinear, 不增新边际。

### Phase C: Loss engineering (multi-horizon + tail-focal)
3 次尝试均失败:

1. **Multi-horizon UNIT (Kendall 2018)** — UNIT σ 自适应机制**反向工作**: y_600 primary 噪声大 → σ_600 增 → weight 降, y_180 反主导。Kill ep 5 (val C=0.015).
2. **Multi-horizon 固定权重 (y_600=1.0, y_180=0.3) + tail-focal** — P/S 分歧 + val→test 迁移崩。
3. **LC + raw y (单 horizon, 无 focal)** — val C 持续降, 同 overfit pattern。

### Phase D: V5-LH 架构突破尝试 (2026-04-21)
Mamba-2 backbone + side-aware bid/ask + cross-path fusion + 1800s 长上下文:

| Config | Val peak C | Test CLEAN P/S | 结果 |
|---|---|---|---|
| default (focal=2.0) | 0.048 | killed ep 7 | P/S 分歧 |
| balanced (no focal) | 0.060 | **−0.028 / −0.008** | Variance collapse |
| simple (V4 loss) | ABORT ep 0 | — | Grad explode |
| simple_stable (LR 3e-4, clip 0.5) | 0.070 | **−0.061 / +0.008** | 更严重 collapse |

**诊断:** Mamba SSM state + 30-min 长上下文记忆 val-specific regime patterns, 不泛化到 2025 test 分布。Prediction variance 塌缩到 y std 的 3-4% (yp std 0.06-0.08 vs y std 1.9)。

### Phase E: 当前最佳 + comprehensive eval (2026-04-21)
确认 V4 final_stack 是项目最佳, 无法突破。完成 12-category eval + backtest。

---

## 2. 当前最佳模型 (V4 final_stack)

### 配置
- **架构:** V4 DualPathLOBModelV3 (`configs/y600_push/baseline_plus.json`)
- **参数量:** 59,315
- **训练:** 700d train / 30d val / 90d test, 3-fold walk-forward, fold_stride=60d
- **Loss:** DUL (pinball q10/q50/q90 + utility_rank η=0.3)
- **Val gate:** composite (0.5·Pearson + 0.5·Spearman)
- **组合:** 0.5 × SWA(top-5 by composite) + 0.5 × EMA(Polyak decay 0.999)

### Pooled 3-fold Clean IC (N=4,868)

| Metric | Value | 95% CI (stationary bootstrap) |
|---|---:|---|
| Pearson | **0.062 – 0.074** | [0.030, 0.090] |
| Spearman | **0.056 – 0.087** | [0.022, 0.089] |
| DirAcc | **0.518 – 0.539** | — |

### Per-fold breakdown

| Fold | Clean P | Clean S | Clean DA | Test dates |
|---|---:|---:|---:|---|
| 0 | 0.083 | 0.109 | 0.543 | 2025-01-08 → 2025-04-08 |
| 1 | 0.078 | 0.068 | 0.532 | 2025-02-07 → 2025-05-07 |
| 2 | 0.061 | 0.086 | 0.541 | 2025-03-09 → 2025-06-06 |

### 对比 baseline 模型

| Model | Pooled Clean P | Pooled Clean S | DL uplift |
|---|---:|---:|---|
| Ridge | 0.0348 | 0.0474 | — |
| TemporalRidge | 0.0347 | 0.0475 | ≈ Ridge |
| XGBoost | 0.0341 | 0.0504 | ≈ Ridge |
| **V4 final_stack** | **0.0540** | **0.0591** | **+0.019 P, +0.012 S over Ridge** |

### 诊断指标

| Metric | Value | Interpretation |
|---|---:|---|
| Daily IC-IR | 0.79 | Stable (>0.5 tradeable) |
| % days positive IC | 78.4% | Strong directional |
| Residual AC(1) | 0.67 | = target AC(1) → 无 label leakage |
| Decile monotonicity (Spearman) | 0.988 | 排序近完美 |
| L-S spread (normalized bps) | 2207 | 最高 (vs Ridge 1724) |
| q10 coverage | 0.128 (nominal 0.10) | 略 over, 可接受 |
| q50 coverage | 0.501 (nominal 0.50) | 完美 |
| q90 coverage | 0.889 (nominal 0.90) | 略 under, 可接受 |
| q-cross violations | q10>q50: 6%, q50>q90: 4% | 可接受 |
| R²(simple factors → V4 q50) | 0.001 | V4 独立非线性信号 |
| Ensemble w/ Ridge/XGB lift | +0.003 IC | Marginal (已触顶) |
| Monthly IC std | 0.016 | 分散, 不集中 |
| Tail calibration (bin 0-2 / OLS) | 79.9% | 比 V4 y_180 (36%) 好 |
| Bin plot monotonicity | 0.909 | 单调过原点 ✓ |

### Sharpe / 回测 (仅信号质量, 未扣成本)

| Model | Sharpe (ann) | Max DD | Calmar |
|---|---:|---:|---:|
| V4 final_stack | 169.4 | −124 bps | 25.9 |
| XGBoost | 118.0 | −163 bps | 17.5 |
| Ridge | 89.1 | −261 bps | 8.5 |

### Cost-aware backtest (2 bps/trade round-trip)

| Strategy | Trades/yr | Net bps total | Sharpe | 结论 |
|---|---:|---:|---:|---|
| Always trade | 26,332 | −18,087 | −6.48 | 严重亏损 |
| Gate τ=0.1 | 30,216 | −24,857 | −9.31 | 更差 |
| **EMA=20, hold=30 (最佳)** | **2,817** | **−559** | **−0.21** | **接近 break-even** |

**结论:** 单资产 y_600 IC 0.06 不足以覆盖 bps 级交易成本。实盘需配合 breadth (多资产) 或 maker-only 订单。

---

## 3. 最佳实践 (Lessons learned)

### 3.1 Ridge walk-forward 先于 DL pod 训练

**规则:** 任何新特征族, 必须先在 500+ 天 3-fold walk-forward Ridge 证明 mean ΔP ≥ +0.005 再投入 pod 训练。

**依据:** 本次 session 验证 3 次特征失败 (tradeflow, long_context, infoflow) 全部死于 Ridge 验证阶段前就应该 reject。但最初错误以 fold-0 DL 单次结果作信号 ("LC fold 0 +0.014 P") 导致 3h pod 浪费。

### 3.2 P/S 分歧 = 危险信号

**规则:** 若 Pearson 高但 Spearman 低 (或反之), **不要**接受。要求两者同步改善。

**依据:** V5-LH focal=2.0 在 ep 5 P=0.075 S=0.020 — tail-driven Pearson, 无 rank 提升。CLAUDE.md 已有此 anti-pattern。

### 3.3 Val→test ratio 是迁移健康指标

**规则:** V4 val→test ratio 约 1×-1.5× (val C=0.029 → test clean P≈0.074)。任何 val/test 比 > 3× 的模型都在 overfit val。

**依据:** V5-LH val C=0.070 → test P=−0.061 = 崩坏。配合 **prediction variance 检查** (yp std 应不低于 y std 的 30%) 可快速识别 collapse。

### 3.4 Post-hoc 技巧 NOT fundamental

**规则:** Seed ensemble, val-weight tuning, SWA blending 等是 noise averaging, 不是真 signal gain。只在真实 feature/architecture 提升基础上使用。

**依据:** 用户明确 feedback — 这些技巧面对 distribution shift 脆弱。

### 3.5 UNIT loss 不适合 primary/secondary asymmetric tasks

**规则:** UNIT (Kendall 2018) 自适应 σ 假设所有 task 同等重要。若 y_600 是 primary 且噪声大, UNIT 会降低其 weight → 反向 sabotage。用固定权重 (primary=1.0, aux=0.3) 或 PCGrad。

### 3.6 Prediction variance 检查是 overfit 的早期诊断

**规则:** 对任何 model, 计算 `yp_std / y_std`。若 < 20%, 模型大概率在输出近常数 q50, IC 是噪音。

**依据:** V5-LH 两次都 <5%, val IC 0.06-0.07 完全不可迁移。

---

## 4. 单资产 y_600 天花板分析

### 结构性限制

| 约束 | 数值 | 影响 |
|---|---|---|
| 单资产 BTC 信号密度 | IC ≤ 0.10 | 多年学术/工业共识 |
| 10-min horizon 噪声比 | SNR < 1% | 限制模型容量可用性 |
| V4 64 feature space 完备性 | time-aggregated 已覆盖 | 新特征必 collinear |
| 2024→2025 distribution shift | Non-stationary | 长上下文模型脆弱 |

### 突破方向 (已明确, 未实施)

| 方向 | 机制 | 状态 |
|---|---|---|
| **多资产 breadth** | ETH/SOL portfolio, IC-IR 可 1.5+ | 用户当前排除 |
| **不同数据源** | Funding rate, OI, basis (orthogonal to LOB) | 未尝试 |
| **缩短 horizon** | y_180 pooled P=0.094, 更实用 | V4 y_180 已生产化 |

---

## 5. 代码资产 (本次 session 新增)

### 特征提取脚本 (本机)
- `scripts/build_tradeflow_overlay.py` — 5 trade flow features
- `scripts/build_infoflow_overlay.py` — VPIN + large-order footprint
- `scripts/build_smoothed_target_overlay.py` — 6 long-context features (之前 session, 复用)

### Loss modules
- `src/losses/multi_horizon_dul.py` — MultiHorizonDulFocalUnit composite
- `src/losses/crps_loss.py`, `decorrelation_loss.py`, `focal_weighting.py`, `unit_loss.py`, `dul_plus_loss.py` — 已存在, V5-LH 用

### V5-LH 架构 (`src/model_v5_lh/`)
- `side_encoder.py`, `cross_path_fusion.py`, `mamba_backbone.py`, `v5_lh_model.py`

### 配置 (configs/y600_push/*.json)
- `tradeflow_feats.json`, `mh_unit_focal.json`, `mh_fixed_focal.json`, `lc_raw_clean.json`

### Configs (configs/v5_lh/*.json)
- `v5_lh_base.json`, `v5_lh_balanced.json`, `v5_lh_simple.json`, `v5_lh_simple_stable.json`, `v5_lh_rank_strong.json`, `v5_lh_bigger.json`

### 评估 + 回测
- `scripts/comprehensive_eval.py` — 12 categories
- `scripts/bin_plot_diagnostic.py` — reverse calibration plot
- `scripts/backtest_y600_final_stack.py` — cost-aware holding strategies

### 结果目录
- `experiments/y600_push/` — V4 y600 experiments + final_stack blend
- `experiments/eval_y600_final_stack/` — 12-category eval + bin plot + backtest
- `experiments/v5_lh_balanced/`, `experiments/v5_lh_simple_stable/` — V5-LH fold-0 artifacts
- `data/npz_v4_smooth/`, `data/npz_v4_tradeflow/`, `data/npz_v4_infoflow/` — 特征 overlay NPZ

---

## 6. 下一步 (如果有新 session)

1. **生产部署 V4 final_stack** — 当前成熟, 不追求 breakthrough
2. **多资产 pivot** — ETH/SOL data collection + cross-asset feature engineering
3. **不同数据源探索** — Funding rate, OI, basis 的 orthogonality 测试
4. **缩短 horizon 深耕** — y_180 已 P=0.094, 可能 y_120/y_300 也值得
5. **实盘 paper trading** — 即使 single-asset 亏损, 框架搭建有价值

### 明确不做
- ❌ 继续 V5-LH 变种 (架构已证不适合)
- ❌ 更多 single-asset 特征 (3 次 Ridge 验证 null)
- ❌ Multi-horizon UNIT variants (机制错配)
- ❌ 更激进 post-hoc blending (用户规则)
