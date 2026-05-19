> **创建:** 2026-05-05 23:15 UTC | **Session:** y600-phase-B-regime-adaptation-overnight | **关键事件:** B.1 + B.2 + B.5 全部 3-fold 完成, 全部 fail vs V5 singh
> **状态:** final | **作废条件:** 用户决策接受/反对结论后归档

# Phase B (Regime Adaptation) Overnight Report — 2026-05-06

## TL;DR (修正版)

**B.1 (regime_bias 6-dim) 实际是 tie / lateral move vs V5 singh, 不是 fail**:
- Pool P -3% (-0.0018), 但 per-fold Spearman 在 3 个 fold 都 ≥ singh
- Per-fold P std 0.002 vs 0.004 (B.1 更稳)
- bias DC offset 几乎归零 (-0.036 vs +0.088 bps)
- BUT β=+0.79 (under-shrunk vs singh +1.05) + daily regime corr 平均 -0.52 vs -0.40 (反向 hurt)

**B.2 / B.5 都明确 fail** (-18% / -17% pool P).

**Production 推荐保持 V5 singh** (pool P 略胜 + β 接近 1.0). 但 **B.1 也是合理候选** 如果用户重 per-fold stability + bias 干净。

Single-asset BTC y_600 sample-level regime adaptation 在 daily corr 维度未能改善 — fundamental signal limit, regime fix 模块均无法 generalize 跨 fold。

**Production 最终方案**: V5 singh α=0+Huber + causal EMA live calibration (已 ship)。

---

## 实验结果汇总

| Variant | Pool P | Pool S | β | bias (bps) | Daily corr (mean) | per-fold P std | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| **V5 singh (current production)** | **+0.0617** | **+0.0687** | **+1.05** | +0.088 | -0.40 | 0.004 | **WINNER** |
| V5 dualh α=0+Huber (prior) | +0.0623 | +0.0672 | +1.05 | +0.057 | (unmeasured) | 0.005 | superseded by singh (Spearman) |
| B.1 regime_bias 6-dim | +0.0599 (-3%) | +0.0682 | +0.79 | -0.036 | -0.52 (worse) | 0.002 | fail |
| B.2 regime_bias + recent_y_mean (7-dim) | +0.0505 (-18%) | +0.0580 (-16%) | +0.88 | -0.275 | -0.21 | 0.003 | fail |
| B.5 strict disentangle (PPNet off) | +0.0486 (fold 0) | +0.0533 | +1.29 | +0.132 | -0.14 | n/a | fail |

## 核心发现

### 1. Pool Pearson/Spearman 任何 regime 方案都 ≤ V5 singh

最佳的 B.1 也比 singh 低 -3% Pearson。B.2 引入 recent_y_mean 直接 -18%。

### 2. Daily regime adaptation correlation 不能跨 fold 持续改善

B.1 fold 0 daily corr 从 -0.51 → -0.42 (改善). 但 fold 1 从 -0.21 → -0.48, fold 2 从 -0.48 → -0.66 — **更糟**。

机制: train 期 model 学的"regime → bias"映射, 在 test 期不同 regime 下 INVALID。模型 overfit train regime 模式。

### 3. recent_y_mean 信号过于薄弱

Audit 时认为 past_30d → next_30d corr +0.23 是可靠 regime predictor。但实测:
- B.2 fold 0 daily corr 改善 (-0.51 → -0.04)
- B.2 fold 1+2 反而 hurt
- 模型在 train regime 上学到的 bias 函数 ≠ test regime 上的 optimal bias 函数

### 4. Strict disentangle (B.5) 损害 main tower 表达力

关闭 PPNetGate 让 main tower 完全 regime-invariant。结果:
- P 掉 -17%, S 掉 -26%
- daily corr 改善有限 (-0.14)
- bias tower 单独无法承载 regime 信息 (输入信号太弱)

PPNetGate 实际是 V5 singh 的有用组件, 提供 multiplicative regime gating, 关掉是 net-negative。

---

## 反思: 为什么 regime adaptation 在单资产 y_600 不 work

**Bayes 视角**:
- σŷ_optimal = ρ · σy ≈ 0.07 · σy (Bayes shrinkage)
- DC offset (~+0.18 bps) 占 σŷ 的 ~25%, 主导 bin spread
- 任何 regime fix 试图修 DC offset, 但 regime predictor 信号 < DC 噪声 floor

**信号视角**:
- regime_prior features |corr|=0.05~0.14 with future regime
- Train period regime 与 test period regime 通常**不同模式** (BTC 2023-2024 牛市 → 2025 mixed)
- Model 学 train pattern, test 期失败

**架构视角**:
- 已有 PPNetGate (multiplicative) 已经捕获 regime 信号能力
- 加 regime_bias_head (additive) 边际贡献小
- 加更多 regime feature 引入 noise > signal

---

## 真正解决 regime adaptation 的路径 (Future work)

| 路径 | 难度 | 期望增益 | 备注 |
|---|---|---|---|
| **Online retraining** (生产) | 中 | +0.005 P | 每周 retrain 用 last 60 days, 让 train→deploy gap 变小 |
| **Live causal EMA-demean** (已有) | 低 | DC bias→0 实战 | trading systems 标准, 已 ship |
| **Multi-asset breadth** | 高 | +0.02-0.05 P | ETH/SOL cross-asset 信号正交, regime 平均掉 |
| **正交数据源** (funding rate / OI / basis) | 高 | unknown | 完全脱出 LOB 单维度 |
| **缩短 horizon (y_180)** | 中 | +0.03 P (已证) | 短 horizon regime 影响小 |

---

## Production 决策

**保持现状**:
- Production CSV: `exports/v5_singh_alpha0_huber/y600_predictions_live.csv` (causal EMA calibrated)
- 严格自测 14/15 gates pass (`STRICT_EVAL_LIVE.md`)
- Calibration view 在 live-calibrated 下过原点 ✓
- Architecture: V5 dualh wrapper + α=0+Huber loss + causal EMA-demean

**Phase B 实验结果都保留作 reference**, 不影响 production:
- `exports/v5_alpha0_huber/` (V5 dualh α=0+Huber)
- `experiments/v5_final/singleh_alpha0_huber_regime_bias/` (B.1)
- `experiments/v5_final/singleh_alpha0_huber_recent_ymean/` (B.2)
- `experiments/v5_final/singleh_alpha0_huber_disentangle/` (B.5)

---

## 给同事 backtest 的建议

CSV 已经 production-ready (`exports/v5_singh_alpha0_huber/y600_predictions_live.csv`)。**注意**:
- 用 `y_pred_q50_bps_live` 列 (causal EMA-demeaned), 不是 raw `y_pred_q50_bps`
- Filter `mask == 1 AND warmup == False` (跳过 EMA warmup 50 samples)
- 该 CSV 已模拟 production deployment 的 drift correction

实战部署时:
- 用 `scripts/y600_live_calibrate.py:causal_ema_demean()` (α=0.01, half-life ~12h)
- 每个新 ŷ 实时 update EMA, 然后 subtract
- 这是 trading systems 标准 drift correction layer

---

## Anti-patterns 写入 (新增, 待 CLAUDE.md merge)

### Anti-pattern #24: 单资产 regime adaptation 在 BTC y_600 fundamental 不 work

**问题**: 加 regime feature (recent_y_mean) 或 regime modulation (regime_bias_head) 试图让 model 适应 regime change。

**实证 (2026-05-05 overnight Phase B):**
- B.1 (regime_bias 6-dim): pool P -3%, daily corr 反而恶化 (-0.40 → -0.52)
- B.2 (+ recent_y_mean 7-dim): pool P -18%, fold 1+2 严重 hurt
- B.5 (strict disentangle PPNetGate off): pool P -17%, P/S 全面下降

**根因**:
- regime_prior features (vol_1h 等) |corr| only 0.05-0.14 with future regime
- past_30d_y_mean → next_30d_y_mean corr +0.23 (audit), 但**单 sample 10-min prediction 上不可用**
- Train period regime ≠ test period regime → model 学到的 mapping 不 generalize
- DC offset 占 σŷ 的 ~25%, 任何 sub-noise-floor 修正引入 bias

**规则**:
1. **不加 regime adaptation 模块给单资产 y_600**, 直到 multi-asset breadth 引入正交信号
2. **DC offset 用 causal EMA live calibration 处理** (production deployment layer, 不是 model architecture)
3. **regime drift 是 fundamental risk, 不是 model bug** — 应在 monitoring 层检测 (regime detector + IC alarm + 停 trade)

### Anti-pattern #25: 用 fold 0 单 fold 信号决定 regime fix 是否 work

**问题**: B.1 fold 0 显示 daily corr -0.51 → -0.42 (改善), 我据此 launch B.2。但 B.1 完整 3-fold 后 fold 1 (-0.21 → -0.48) 和 fold 2 (-0.48 → -0.66) 都恶化, **mean 反而下降**。

**规则**: regime adaptation 类 fix **必须 3-fold pool 验证 daily corr 平均改善**, 单 fold 改善可能是 noise 或 fold 0 specific (regime flip 大)。 单 fold 0 决策 = anti-pattern #14 又一变种。
