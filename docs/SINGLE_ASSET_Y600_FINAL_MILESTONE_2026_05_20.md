> **★★★ 已归档为历史基线 (2026-08-12, 本文件自带的作废条件已触发: multi-asset production 于 2026-08-05 上线)。**
> **单资产权威终版 = `docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md`**(Run1 双盘口 REG_arch @2026-06-13 修正后 spot+perp 数据, 诚实口径 P≈0.049, maker-only ≤0.76bps/side)。
> **本文头条数字已被后续更正**: P=0.0646 系 ±5σ-clip + EMA-demean 口径(诚实 raw-y 0.037 pooled/0.043 folds, memory `single_asset_record_caliber_correction`); retail-maker Sharpe 4.4 / taker 2.8 系强月+clip+低费构造(07-05 taker 审计判非 taker 可交易, 见 07-06 收官 §2.3)。**本文仍是 anti-patterns #1-#29 与 V5 时代记录的权威出处。**

> **创建:** 2026-05-20 UTC+8 | **Session:** single-asset y_600 conclude + backtest + pre-multi-asset cleanup
> **目的:** 单资产 BTCUSDT y_600 工作的**最终里程碑记录** — REG_arch winner 完整规格 + CSH 回测结果 + 可复现路径 + multi-asset 传承。本文件是单资产阶段的权威收尾文档。
> **上一版本:** docs/V5_TO_PRODUCTION_ITERATION_2026_05_15.md (2026-05-15) — 迭代路径; 本文件补充 REG_arch standalone 确认 + 回测 (回测内容首次记录)
> **状态:** final | **作废条件:** multi-asset 工作产生新 production 后此文件归档为单资产历史基线
> **关联 memory:** [[v5push_5way_ensemble_reg_arch_2026_05_14]] [[v5_singh_alpha0_huber_winner_2026_05_05]] [[y600_milestone_summary_2026_05_08]] [[feedback_v6_design_discipline_2026_05_14]]

# 单资产 BTCUSDT y_600 — 最终里程碑 (REG_arch + CSH 回测)

---

## 0. TL;DR — 单资产阶段成果

经过 V4 → V5 SINGH → Track A/P3/T → **REG_arch** → 5-way ensemble 的完整迭代，单资产 BTCUSDT 10-min 收益率预测达到：

| 层级 | 模型 | Pool Pearson | Pool Spearman | β | σŷ/σy | 备注 |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **最佳单模型** | **REG_arch** | **+0.0646** | **+0.0723** | +1.05 | 0.058 | FiLM γ+β multi-stage |
| **Production** | 5-way ensemble | **+0.0667** | **+0.0733** | +1.10 | 0.058 | R40/P20/A15/V25 |
| Baseline | V5 SINGH α=0+Huber | +0.0589 | +0.0686 | +1.06 | 0.057 | 单模 production 前身 |
| 参照 | Ridge walk-forward | ~0.033 | — | — | — | 线性基线 (DL +75%) |

**回测 (CSH 策略, 7 个月 OOS, 普通用户费率):**

| 费率情景 | RT fee | Sharpe (年化) | 年化收益 | 单笔净 PnL | 评价 |
|:---|---:|---:|---:|---:|:---|
| Pure maker BNB | 3.6 bps | **+5.20** | **+53.1%** | +13.97 bps | 理想被动挂单 |
| Realistic maker USDT (70/30 fill) | 5.8 bps | **+4.38** | **+44.7%** | +11.77 bps | 实操锚点 |
| Pure taker USDT | 10.0 bps | **+2.81** | **+28.8%** | +7.57 bps | 最差情景仍盈利 |
| + Quantile-aware exit (V7) | 5.8 bps | +4.45 | +46.7% | — | 当前能榨出的全部 quantile 价值 |

**核心结论:** 单资产 y_600 在 σŷ/σy≈0.058 (Bayes ceiling 附近) 已收敛。alpha ≈ 1.5-2 bps/笔，在 VIP9/普通用户 **maker 费率**下可盈利，纯 taker 普通费率仍 Sharpe 2.8。瓶颈不是 model alpha，而是 **maker fill quality + 跨资产广度缺失**。下一步 = multi-asset。

---

## 1. REG_arch 架构完整规格

### 1.1 数据流 (block-by-block)

```
输入:
  X            (B, 600, 64)    64 手工特征 (Path A)
  X_raw        (B, 600, 20, 4) 20-level LOB tensor [bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt] (Path B)
  regime_prior (B, 6)          per-sample hourly-scale regime 特征

Path A: X → RevIN → GDCN → input_proj ──┐
Path B: X_raw → channel-mix conv(4→16,1x1) → spatial conv → level attention pool ──┤
                                                                                    ▼
                                              concat + linear fuse
                                                       ▼
                              Conformer block 1 (kernel=15, d_model=32, 2 heads)
                                                       ▼
                              ★ FiLM₁(regime_prior): h = γ₁⊙h + β₁       [REG_arch 创新]
                                                       ▼
                              Conformer block 2 (kernel=15)
                                                       ▼
                              ★ FiLM₂(regime_prior): h = γ₂⊙h + β₂
                                                       ▼
                              last-token slice (pool over time)
                                                       ▼
                              ★ FiLM₃(regime_prior): h = γ₃⊙h + β₃
                                                       ▼
                              DAQH: q50 = tanh(sign_logit) × softplus(mag_logit)
                                                       ▼
                              MonotonicQuantileHead: q10 ≤ q50 ≤ q90 (incremental softplus deltas)
                                                       ▼
                              输出 quantiles (B, 3) z-space
```

### 1.2 REG_arch 三个核心创新 (vs V5 SINGH)

**(1) FiLM γ+β multi-stage gating (3 个门)** — 核心架构创新
- V5 production: regime 只在 output-level PPNet 单点注入
- REG_arch: regime 在 Conformer block1 后 / block2 后 / pool 后**三处**注入
- FiLM: `γ = MLP_γ(regime)`, `β = MLP_β(regime)`, `h_new = γ⊙h + β` (逐通道仿射)
- **Identity init**: γ≈1, β≈0 → 训练初期等价 V5 baseline，逐步学 regime-conditional 调制
- 机制: regime 信息触达中间表示，前面 layer 不再"瞎做"

**(2) DAQH (Direction-Aware Quantile Head)** — 方向/幅度解耦
- `q50_signed = tanh(sign_logit) × softplus(mag_logit)`
- tanh∈(-1,1) 决定方向 + 强度；softplus>0 决定幅度
- 解耦后 sign_logit 可接 BCE 直接监督，mag_logit 可接 focal Huber 监督

**(3) 5-component loss (新增 sign BCE + mag focal Huber)**
```
L = 0.10·pinball
  + 0.50·utility_rank(α=0)         # α=0 修复 #21 bias artifact
  + 0.50·plain Huber(δ=2, w_wrong=0) # plain Huber 避 #20 σ collapse
  + 0.10·sign BCE(tail_focal_1p5)  # 方向头独立监督, weight=clip(|y|/σ,0.3,3.0)^1.5
  + 0.30·mag_focal_Huber AUX       # 幅度头独立监督 (AUX 不 REPLACE — 安全, #25)
```

### 1.3 容量 & 超参
- ~118K params, single horizon y_600, single asset
- d_model=32, d_raw=16, dropout=0.20, 2 Conformer blocks, kernel=15
- params:sample ≈ 1:6 (健康区间)

---

## 2. 训练 Recipe (可复现)

| 项 | 值 |
|:---|:---|
| train_days / val_days / test_days | 700 / 60 / 90 |
| fold_test_starts | 2025-02-09 / 2025-04-10 / 2025-06-11 (3-fold walk-forward) |
| fold_stride | 60 days |
| input_len / stride / horizon | 600s / 180s / 600s |
| batch_size | 1024 |
| lr | 6e-4 cosine warmup |
| weight_decay | 0.001 |
| patience | 4 |
| EMA decay | 0.999 (dual best: raw + EMA) |
| val_metric | composite (0.5·P + 0.5·S) |
| embargo_days | 1 |
| **σ-gate BEST checkpoint** | σŷ/σy ≥ 0.02 required (anti-pattern #24 fix) |

**关键纪律:** stride ≥ horizon 用于 clean eval (anti #2)；BEST checkpoint 必须过 σ_ratio gate (anti #24)；y 除以 MAD-σ 归一 (anti #7)。

---

## 3. Ensemble + Live Calibration

### 3.1 5-way value-blend (NOT rank-blend, anti #16)
```
W = {REG_arch: 0.40, Track_P3: 0.20, Track_A: 0.15, V5_prod: 0.25}  # Pareto-optimal on val
ensemble_q50_live = Σ W[m] · q50_bps_live[m]        # value space, 不是 rank
ensemble_q10/q90  = Σ W[m] · q10/q90[m]             # 同权重 blend
ensemble_q50_final = causal_ema_demean(ensemble_q50_live)  # 再一层 live cal
```
- REG_arch 40% 但非 100%: 4 模型 corr 0.61-0.79, 留 60% 给正交 alpha
- Ensemble +0.002 Pearson over best single → diversity 价值 > 单一最佳

### 3.2 Causal EMA-demean live calibration
```
q50_live[i] = q50[i] - EMA_lag1(q50[0..i-1]; α=0.01)   # halflife≈70, warmup=50
```
- 严格 causal: sample i 只用 [0..i-1]
- Spearman invariant, Pearson -0.0006, DA|y|>σ +0.6pp
- Production 用 live 列交易

---

## 4. CSH 回测 (Confident Sticky Hold) — 完整记录

> **首次记录。** 回测在 REG_arch standalone test 预测上 (50,846 windows, 3 folds, 2025-02-09→2025-09-09)。

### 4.1 策略逻辑
状态机 state ∈ {flat, long, short}，决策网格 12-min (每 4 bars 子采样，非重叠 10-min 标签):
- **门控**: 只在 `|q50_live| ≥ T_open` 开仓 (T_open=2.0 bps ≈ P99 of |q50_live|, 只 trade top ~1%)
- **不对称 hysteresis**: T_open=2.0 进, T_close=-2.0 才平 (允许漂移), T_flip=3.0 才翻仓
- **Sticky hold**: 持仓期间信号仍弱正则不动 (fee=0), max_hold=120min 强制平
- **Fee 摊销**: 一笔 trade 跨多个 10-min 段, round-trip fee 被分摊

### 4.2 关键参数 (所有 fee level 通用最优)
```
T_open = 2.0 bps   T_close = -2.0 bps   T_flip = 3.0 bps   max_hold = 10 bars (120 min)
```

### 4.3 全费率谱结果 (普通用户费率, USDT maker 0.02% / taker 0.05%)

| 场景 | RT fee | Sharpe | Ann.Ret | Total bps | Max DD | Trades | PnL/trade |
|:---|---:|---:|---:|---:|---:|---:|---:|
| Pure maker BNB | 3.6 | +5.20 | +53.1% | +1509 | 385 | 108 | +13.97 |
| Pure maker USDT | 4.0 | +5.05 | +51.6% | +1466 | 390 | 108 | +13.57 |
| Realistic maker BNB | 5.2 | +4.60 | +47.0% | +1336 | 406 | 108 | +12.37 |
| **Realistic maker USDT** | **5.8** | **+4.38** | **+44.7%** | **+1271** | 415 | 108 | +11.77 |
| 1m+1t USDT | 7.0 | +3.93 | +40.2% | +1142 | 432 | 108 | +10.57 |
| Pure taker USDT | 10.0 | +2.81 | +28.8% | +818 | 475 | 108 | +7.57 |

### 4.4 Per-fold breakdown (稳定性 — 重要 caveat)
@ realistic maker USDT (RT=5.8):

| Fold | 时段 | Total PnL | Sharpe |
|:---:|:---|---:|---:|
| 0 | Feb-May | +1174 bps | +8.47 |
| 1 | Apr-Jul | **-34 bps** | -0.37 |
| 2 | Jun-Sep | +131 bps | +5.98 |

⚠️ **~92% 盈利来自 fold 0**。fold 1 (May-Jul regime) 接近 break-even。是 "lucky early run" 成分，不是均匀稳健 alpha。实盘保守期望 25-35% 年化。

### 4.5 Quantile 使用结论 (16 变体测试)
- **q10/q90 几乎是 q50 的常数 shift** (≈±13 bps = σ_y)，per-sample 变化主要来自 σ_y regime drift 而非 sample confidence
- Narrow-band filter / confidence-ratio / Bayes-EV 全部**劣于** baseline (过滤掉正信号)
- **诊断**: 强信号样本里 wide-band 反而 edge 最大 (wide ≈ high-vol ≈ alpha 多)
- **唯一有效用法 (V7)**: quantile-aware EXIT (q90>0 时延迟平多仓) → +0.07 Sharpe (微小但真实)
- **根因**: MonotonicQuantileHead 在 low-SNR + homoscedastic P(y|x) 下学常数 band。要解锁 quantile 价值需改 model (heteroscedastic head + vol predictors)，非 strategy 能榨出

### 4.6 实盘 shrinkage 估算 (informed judgment, 未跑)
- 回测 → 现实: -30% (maker fill 50-65%, vol-period spread, latency, funding 跨期)
- + 全套风控 (stop-loss/daily-DD/vol-pause/IC-monitor): 再 -15%
- **诚实预算: 实盘 Sharpe 2.5-3.0 / Ann 25-35%** (含风控)
- ⚠️ **当前策略无黑天鹅防护** (无 absolute stop-loss / daily DD 熔断 / vol surge pause / IC monitor / funding avoidance) — production 前必须补

---

## 5. 可复现路径 (精确文件清单)

### 5.1 REG_arch 模型
- Config: `configs/v5push/singh_alpha0_huber_track_reg_arch.json`
- Checkpoints: `experiments/v5push/singh_daqh_lambda0/fold_{0,1,2}/best_model.pt` (+ ema_best.pt)
- Traced (推理用): `~/Desktop/reg_arch_inference/checkpoints/fold_{0,1,2}/model_traced.pt`
- Standalone test preds (回测源): `exports/reg_arch_standalone_eval/fold_{0,1,2}_test_preds.npz`

### 5.2 V5 SINGH production (baseline 前身)
- Config: `configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json`
- Preds: `experiments/v5_final/singleh_alpha0_huber/fold_{0,1,2}/test_preds.npz`
- Production CSV: `exports/v5_singh_alpha0_huber/y600_predictions_live.csv`
- Strict eval: `exports/v5_singh_alpha0_huber/STRICT_EVAL.md`

### 5.3 5-way ensemble production
- CSV: `exports/v5push_5way_ensemble_reg_arch/y600_5way_predictions_2025_04_01_to_07_29_RAW.csv`
- Weights CSV: `exports/v5push_5way_ensemble_reg_arch/y600_predictions_5way_R40_P20_A15_V25.csv`

### 5.4 回测
- 预测重建: `backtest_reg_arch/build_preds_csv.py` (NPZ → de-norm → live cal → CSV)
- 回测引擎: `backtest_reg_arch/backtest_csh_v4_retail.py` (普通用户费率 sweep)
- Quantile 变体: `backtest_reg_arch/backtest_csh_v5_quantile.py`
- 结果: `backtest_reg_arch/backtest_headline_v4_retail.csv`, `backtest_sweep_v4_retail.csv`

### 5.5 推理交付包 (给同事/部署)
- `~/Desktop/reg_arch_inference/` — 自含 TorchScript + 特征 pipeline + live cal + README
- 端到端验证: book+trades CSV → 预测 CSV (14 天测过, P/S 与 production 一致)

### 5.6 核心代码 (src/)
- 模型: `src/model/dual_path_model_v3.py` (主), `film_gate.py`, `direction_aware_quantile_head.py`, `monotonic_quantile.py`, `raw_lob_encoder.py`, `backbones/conformer_backbone.py`
- 训练: `src/training/trainer_v2.py` (σ-gate BEST + EMA), `dataset.py`, `dul_loss.py`
- 特征: `src/features/{pipeline,microstructure,derived_features,raw_lob,trade_features,regime_prior_features,ridge_informed_features,resample,multi_day_pipeline}.py`
- 入口: `run_pipeline_v3.py`

---

## 6. 关键 anti-patterns (单资产血泪, 详见 CLAUDE.md #1-26)

最相关的:
- **#16** ensemble 必须 value-blend 非 rank-blend (rank 丢 magnitude → β crash)
- **#18** label engineering 必须在 raw y 上 eval (smooth target 是 measurement artifact)
- **#20** dir_huber w_wrong>0 + L2 primary 在低 SNR σ collapse → 用 plain Huber
- **#21** utility_rank α=1 + softplus head → q50 偏负 bias, surgical α=1→0 修复
- **#22** MRP replace last-token 在 y_600 上 NULL
- **#23** decoupled (2σ-1)×softplus head σ collapse → 保留 tanh×softplus DAQH
- **#24** σ-gate BEST checkpoint (TV channels init noise → illusory high-P broken checkpoint)
- **#25** tail-focal/mag-focal 作 AUX (≤0.30) 安全, REPLACE primary 危险
- **#26** regime-aware ensemble 必须 causal indicator 评估 (future-|y| stratification 不可交易)

**9 次 NEG 迭代确认 REG_arch 是单资产 y_600 local optimum** (v3 cross-attn / v4 3-block / v5 seq-dir BCE / v6a deeper trunk / v6b-v8 channel adds / A1 SE-block — 全 NEG, 详见各 NEG memory)。

---

## 7. 传承到 Multi-Asset (哪些 carry over)

### 7.1 直接复用 (asset-agnostic)
- DAQH + MonotonicQuantileHead (价格预测无关 asset)
- FiLM γ+β multi-stage gating (per-asset regime conditioning)
- σ-gate BEST + EMA + composite metric (训练纪律通用)
- Value-blend ensemble (anti #16 永不用 rank-blend)
- 64-feature pipeline + 20-level raw LOB encoder
- CSH 回测框架 (改 cross-sectional 即可)
- Anti-patterns #1-26 (大部分 horizon/asset 无关)

### 7.2 必须 re-think
- **Cross-asset attention layer** (新模块, `src/model/cross_asset.py` 已有 starter)
- **Cross-sectional IC loss** (单资产用 pool P; multi-asset 需横截面 rank loss)
- **Regime_prior per-asset vs shared**
- **Pool aggregation**: 单资产 last-token; multi-asset 可 attend over assets
- **TV/feature scale 跨资产归一** (BTC vs SOL volume scale 不同)
- **Per-asset 数据量** → 重估 params budget
- **已有 multi-asset 基础设施**: `tf_train_hrt_rnn_v1.py` (RNN TBPTT, symbols as batch dim, Parquet ingest) — 不同 model line, 可参考

### 7.3 Multi-asset 提升 hypotheses (per CLAUDE.md priority)
- Portfolio IR 0.6 → 1.5+ (正交 alpha 聚合)
- Cross-sectional ranking 是天然 alpha source
- Funding rate / OI / basis / on-chain 作正交特征

---

## 8. 一句话收尾

单资产 BTCUSDT y_600 工作**圆满收敛**: REG_arch standalone P=+0.0646 / 5-way ensemble P=+0.0667，σŷ/σy=0.058 紧贴 Bayes ceiling；CSH 回测在普通用户 maker 费率下 Sharpe 4.4 / 年化 45%，纯 taker 仍 Sharpe 2.8。模型、特征、loss、架构、ensemble、回测、推理交付包全部完成且可复现。瓶颈已从"找信号"转移到"跨资产广度 + 执行质量"。**下一站: multi-asset。**
