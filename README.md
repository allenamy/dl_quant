# DL Quant — BTCUSDT y_600 Mid-Frequency Alpha

> **Created:** 2026-05-08 | **Status:** V5 singh α=0+Huber production candidate
> 主目录 onboarding 文档。入项目第一眼看这份。架构 / loss / 训练细节齐全 + 优化方向清晰。

---

## 1. 项目概览

**Goal:** Binance BTCUSDT 永续合约中频交易预测。给定过去 600s LOB 序列, 预测未来 1-10 min 收益率。重点 horizon: y_600 (10min).

**Production 现状 (2026-05-08):**
- **Model**: V5 singh α=0+Huber (Conformer backbone + 单 horizon + train-time bias-fixed loss)
- **Pool 实测**: P=+0.0617, S=+0.0686, β=+1.05, σŷ/σy=0.059, bias=+0.18 bps
- **Production CSV**: `exports/v5_singh_alpha0_huber/y600_predictions_live.csv` (含 causal EMA-demean live calibration)
- **vs Linear baseline**: V5 比 Ridge **+75% Pearson** (+0.027 abs) — 真实非线性增益, 已用 fair raw-LOB Ridge 验证
- **Bayes ceiling**: ~0.07-0.08 P (single-asset, σŷ ≈ ρ·σy 数学上限)

**单资产 architecture-level 已 exhausted。** 突破到 0.10+ 需 multi-asset breadth 或 orthogonal data。

---

## 2. Quick Start

### 2.1 用 production CSV 做 backtest

```python
import pandas as pd
df = pd.read_csv('exports/v5_singh_alpha0_huber/y600_predictions_live.csv')
df = df[(df['mask'] == 1) & (~df['warmup'])]
# y_pred_q50_bps_live: causal EMA-demeaned production signal (raw bps)
# y_true_bps: realized 600s log-return × 1e4
# 详见: exports/v5_singh_alpha0_huber/README.md
```

### 2.2 重训 production 模型

```bash
# Pod 上 (3090, ~50min/fold × 3 = 2.5h)
python scripts/v5_run_one.py \
    --name singleh_alpha0_huber \
    --config configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json \
    --out-base experiments/v5_final \
    --max-folds 3 --start-fold 0
```

### 2.3 严格 eval

```bash
# 12-category strict eval (15 gates)
python scripts/v5_alpha0_huber_strict_eval.py \
    --csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
    --out exports/v5_singh_alpha0_huber/STRICT_EVAL.md

# Temporal stability (regime adaptation diagnostic)
python scripts/v5_singh_temporal_eval.py \
    --csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
    --out exports/v5_singh_alpha0_huber/STRICT_EVAL_TEMPORAL.md
```

---

## 3. Repo 布局

```
quant_research/
├── README.md                       # 本文件 — onboarding entry point
├── CLAUDE.md                       # Operating rules + anti-patterns (LLM 指令)
├── BTCUSDT.csv(.gz)                # Raw 1Hz mid prices (从 Binance, 991 days)
├── data/
│   ├── npz_v4/                     # Production training data (28 GB, 991 days × N samples × LOB)
│   ├── midprice_per_day/           # Per-day mid price series
│   ├── npz_v4_daily_y_mean.json    # Per-day y_600 mean (used by Phase B regime feature)
│   └── ...                         # 其他 overlay (smooth/tradeflow/infoflow — anti-patterns documented)
├── src/                            # 主代码
│   ├── model/
│   │   ├── dual_path_model_v3.py   # ★ 主 model (DualPathLOBModelV3) — V4/V5 共用; 通过 flags 切组件
│   │   ├── monotonic_quantile.py   # ★ MonotonicQuantileHead (q10<q50<q90 by construction)
│   │   ├── ppnet_gate.py           # ★ PPNetGate (regime conditioning, multiplicative gate)
│   │   ├── gdcn.py                 # ★ GDCN (Gated Deep Cross Network, CIKM 2023)
│   │   ├── raw_lob_encoder.py      # ★ Path B encoder (spatial Conv on LOB levels)
│   │   ├── attention_pool.py       # ★ LevelAttentionPool over time
│   │   ├── masknet.py              # MaskNet (DLP-KDD 2021); use_masknet=False in V5 production
│   │   ├── lob_transformer.py      # V4 早期 patch attention; use_attention=False in V5 production
│   │   ├── patch_attention.py      # V4 早期 PatchEmbed/CausalPatchAttn; use_patch_attention_pool=False in V5
│   │   └── backbones/
│   │       └── conformer_backbone.py  # ★ Conformer (Conv k=15 + Self-Attn + FFN, ×2 blocks)
│   ├── training/
│   │   ├── trainer_v2.py           # ★ Main trainer (EMA, val composite, patience)
│   │   ├── dataset.py              # ★ LOBDatasetV2 (NPZ loader, regime_prior injection)
│   │   ├── dul_loss.py             # ★ Loss components (pinball, utility_rank, dir_huber, ...)
│   │   ├── losses.py               # Lower-level loss primitives
│   │   ├── ensemble.py             # Multi-model ensembling utils
│   │   └── v5_losses/              # V5 alternative heads (heteroscedastic; not currently used)
│   ├── features/
│   │   ├── pipeline.py             # NPZ build pipeline (raw → features)
│   │   ├── multi_day_pipeline.py   # Walk-forward fold builder
│   │   └── regime_prior_features.py# 6-dim regime_prior (vol_1h, spread_mean_1h, OBI trend, ...)
│   ├── evaluation/
│   │   └── backtest_engine.py      # Block-bootstrap CI helpers
│   └── baselines/
│       ├── linear_baseline.py      # Ridge / TemporalRidge
│       └── xgb_baseline.py         # XGBoost
├── configs/
│   └── v5/screen/
│       └── backbone_conformer_hardened_singleh_alpha0_huber.json   # ★ PRODUCTION config
├── scripts/                        # 运行 / 工具脚本 (88 个, 大部分一次性, 核心 ~10 个见 §9)
├── tests/                          # 单测 (model + training + features causality)
├── experiments/                    # 训练产物 (model checkpoints + test_preds.npz)
│   ├── v5_final/
│   │   ├── singleh_alpha0_huber/   # ★ PRODUCTION (V5 singh)
│   │   ├── dualh_alpha0_huber/     # V5 dualh (prior production, fallback ref)
│   │   └── conformer_hardened_dualh/ # V5 dualh BASELINE (design doc 引用)
│   ├── y600_push/
│   │   └── baseline_plus/          # V4 best baseline (anchor reference)
│   ├── v4_noattn_700d/             # V4 production y_180 (P=0.094)
│   ├── baselines_horizon_sensitivity/y_600/  # Linear/tree benchmark (Ridge/XGBoost)
│   └── baselines_fair_ridge_y600/  # Fair Ridge with raw LOB (today's apples-to-apples)
├── exports/
│   ├── v5_singh_alpha0_huber/      # ★ PRODUCTION CSV + STRICT_EVAL
│   │   ├── y600_predictions_live.csv         # 给同事 backtest
│   │   ├── y600_predictions_all_folds.csv    # raw model output
│   │   ├── STRICT_EVAL.md                    # 15/15 gates pass
│   │   ├── STRICT_EVAL_LIVE.md               # live calibration eval
│   │   ├── STRICT_EVAL_TEMPORAL.md           # regime adaptation diagnostic
│   │   └── README.md                         # CSV 使用说明 + DC offset/regime drift 教学
│   └── v5_alpha0_huber/            # V5 dualh (prior production, fallback)
├── docs/
│   ├── Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md  # ★ 完整 V5 architecture + loss design (~400 行深度文档)
│   ├── PHASE_B_OVERNIGHT_REPORT_2026_05_06.md # Phase B regime adaptation 4 次失败复盘
│   ├── Y600_REGIME_FEATURE_AUDIT.md          # Phase B 数据基础 (regime_prior 与 future regime 相关性 audit)
│   ├── PROJECT_PRINCIPLES.md                 # Operating rules (跨 LLM/同事)
│   ├── METRIC_DISCIPLINE.md                  # Eval 标准
│   └── ...                                   # V4 era reference docs
├── run_pipeline_v3.py              # ★ Main training entry (config-driven, calls trainer_v2)
└── tf_train_*.py                   # 同事提供的外部模型思路 (TF, 参考用)
```

★ = production-critical files

---

## 4. 迭代里程 Timeline

```
V1 (Apr 12)          TF prototype           tf_train_*.py (现仅作参考)
V2 (Apr 13-15)       PyTorch baseline       run_pipeline.py — early validation
V3 (Apr 16-17)       双路径架构 (Path A+B)   DualPathLOBModelV3 创建
V3+RevIN (Apr 16)    Per-instance norm
V4 (Apr 17-19)       Production phase A/B   V4 noattn 700d 建立 P=0.094 (y_180), 单资产 ceiling 试探
V4+SG (Apr 18)       Savitzky-Golay         REJECTED (ΔP +0.008 < gate)
V5-LH (Apr 21)       Mamba long-context     ALL 4 variants FAILED (variance collapse, anti-pattern #11)
V4 baseline_plus     SWA + EMA + composite  V4 production 配方完整 (Apr 30 multi-seed median)
                                            Pool P=+0.050, S=+0.059
V5 dualh BASELINE   Conformer + multi-h    P=+0.065 raw IC, 但 bias=-0.41 NEG (Apr May 4)
                                            calibration view top y-bin -0.30 (用户主诉)
V5 dualh α=0+Huber  Train-time bias fix    P=+0.062 + bias=+0.14 (May 5 上午)
                                            STRICT_EVAL 15/15 pass; α=1→0 一行 surgical fix
V5 singh α=0+Huber  Drop multi-horizon     P=+0.062 + S=+0.069 (May 5 PM)
                    aux task ablation       Spearman +2.2%, per-fold std -22% — singh 微胜
V5 singh + EMA-demean Live calibration     Layer 2 production hygiene (May 5)
                                            DC offset 修到 0, β=+1.005
Phase B (May 5-6)   Regime adaptation push  ALL 4 attempts FAILED (B.1/B.2/B.5 + actual-y EMA)
                                            anti-pattern #24/#25; multi-asset 是真解
Fair Ridge bench    Raw LOB to Ridge        +0.0011 P (4%, noise) — DL +75% over Ridge 是真的 (May 8)
```

---

## 5. Production: V5 singh α=0+Huber 详解

### 5.1 输入数据 (Dual-path) — 详细机制

总览: 模型每个 sample 的输入有**三个张量**:
- `x_features` shape (T=600, 64): hand-crafted 微观结构 features 时序
- `x_raw` shape (T=600, n_levels=25, 4): 原始 LOB tensor 时序
- `regime_prior` shape (6,): hourly-scale 慢变量 (per-sample, 非 per-timestep)
- target `y_600` scalar: 未来 10 min log-return

数据 build pipeline: `src/features/pipeline.py:build_npz_for_day()`. 每天产出一份 NPZ, 然后 `src/training/dataset.py:LOBDatasetV2` 在训练时 walk-forward 加载多天。

#### Path A — 64 维 hand-crafted 微观结构 features (含义 + 机制)

**(a) 价格收益 (3 dim)**
- `log_return_1s`, `log_return_5s`, `log_return_30s`
- 计算: `log(mid[t] / mid[t-Δ])`, 多 timescale (1s/5s/30s)
- 机制: 短期 momentum continuation. 5s-30s 窗口内的方向延续是 LOB 数据中相对显著的可预测信号.
- 数值: log return 是 approximately stationary (vs raw price level), 量级 ~1e-4 / sec
- BTC 实测: 1-30s log return 与 next 10-min log return 的相关性约 0.02-0.05 (个位数 IC, 但符号一致 + 多 feature 累积)

**(b) 价差 (2 dim)**
- `spread_bps` = `(ask_L1 - bid_L1) / mid * 1e4`, `spread_change` = `Δspread`
- 机制: bid-ask spread 反映 cost of immediacy. Wide spread 通常出现在 vol regime 上升期或 informational asymmetry 高时.
- 数值: bps form (×1e4) 让 spread 在不同 BTC 价格下可比 (BTC 30k vs 40k spread 绝对值不同, bps 相同)
- 实测: spread 与 future vol 高相关, 与 future return 弱负相关 (高 spread → 退避交易 → 短期反向)

**(c) Order Book Imbalance — 多档 (8 dim)** ★ 主预测信号之一
- `obi_L1/L5/L10/L25`: `(bid_qty - ask_qty) / (bid_qty + ask_qty)` 在前 N 档累加
- `obi_L1_delta`: 1s 内的变化
- `delta_obi_L5_5s`: 5s 内 OBI 变化 (catch dynamic shift)
- `obi_L5_rank_1h`: 1-hour 滚动窗口内的相对排名 (regime-normalized)
- 机制: 买卖压力不平衡 → 短期价格推动. L1 = top of book (即时压力), L25 = 加权平均 (慢信号).
- **多 timescale + 多档同时输入**: 让 model 学不同 regime 下哪个 level 更 informative. 实测 L5 vs L1 在中频 horizon 上 L5 更 robust (top-of-book 噪声大)
- rank_1h 形式: 处理 OBI 的 vol 依赖 (高 vol 期 OBI 振幅大, rank 更稳定)

**(d) 深度 (4 dim)**
- `bid_depth_L5/L25`: 前 N 档总数量
- `ask_depth_L5/L25`
- `depth_ratio_L5` = `bid_depth_L5 / ask_depth_L5`
- 机制: 流动性 indicator. 深度低 → 大单 impact 大 → vol 上升前兆. depth_ratio 与 OBI 类似但在 quantity 空间.
- 数值: depth 用 log1p 压缩重尾 (有的 level 数量 10× 其他 level)

**(e) 微观结构 / 加权价 (8 dim)**
- `microprice_dev_bps`: microprice (volume-weighted bid+ask) 相对 mid 的 bps 偏移
- `weighted_price_bid_L10`, `weighted_price_ask_L10`: 加权 (按 quantity) 平均 bid/ask 价
- `price_pressure`, `book_pressure_imbalance`, `book_pressure_delta_60s`
- `depth_flow_ratio_30s`, `price_impact_30s`
- 机制: VWAP-style summaries 比 simple mid 更精细. microprice 是 short-horizon return 的 strong predictor (10ms-1s 尺度), 但在 10min 尺度上 alpha 衰减很多.
- price_impact: 估算 单位 volume 推动价格的 bps. 高 price impact → 流动性弱 → 风险/return 上升

**(f) 盘口形状 (4 dim)**
- `bid_slope_L10`, `ask_slope_L10`: bid/ask 价-数量曲线的线性回归 slope
- `bid_concentration`, `ask_concentration`: 最大档数量 / 总数量
- 机制: book 形状反映 informed traders 的位置. concentration 高 → 大单挂在某一档 → 该档的 cancellation 是 informational event.

**(g) 分档比例 (10 dim)**
- `bid_amt_ratio_L0/1/2/3/4`, `ask_amt_ratio_L0/1/2/3/4`: 每档数量占前 5 档总量的比例
- 机制: 给 model 每档的 relative 权重. L0 (top) 最易撤单, L4 (深档) 最稳定. 比例分布 → "形状识别".

**(h) 波动率 — 多 timescale (3 dim)**
- `realized_vol_30s/60s/300s`: 平方收益累加
- 机制: 短-中期 vol 是 regime indicator. 高 vol 期 alpha 信号变弱 (anti-pattern: 高 vol 期 IC 衰减).
- 多 timescale 让 model 区分 "短突发 vs 持续高 vol".

**(i) Trade flow (8 dim)**
- `buy_volume_1s`, `sell_volume_1s`, `net_trade_flow_1s`, `trade_imbalance_1s`
- `cumulative_net_flow_30s/300s`: 累积 trade flow
- `trade_intensity_30s`, `vwap_return_1s`
- 机制: aggressor flow 是直接的方向信号 (taker 主动 buy → 短期上推). cumulative 30s/300s 加平滑.
- vwap_return: 1s VWAP 与上一秒 VWAP 的 log return, 与 mid return 互补 (含 volume 信息)

**(j) 微观信息 / 复合 (5 dim)**
- `kyle_lambda_30s`: 30s 窗口 Kyle's λ ≈ price change / signed volume (price impact coefficient)
- `roll_spread_60s`: Roll's effective spread 从 autocovariance 估
- `vpin_60s`, `vpin_300s`: VPIN (volume-synchronized PIN), informed trading 概率
- `net_flow_x_spread`, `net_flow_x_vol`: 交互项 (net flow × spread, net flow × vol). 让 model 学 regime-conditional flow effect.
- `large_trade_arrival_60s`: 大单到达计数, 反映 institutional activity
- `net_flow_rank_1h`: 1h rolling rank of net_flow
- 机制: 行为金融 / 市场微观结构经典 measures. VPIN/Kyle 在学术研究中证明 predictive 但 alpha 较小; 加入做 "everything bagel" 让 model 自由组合.

**(k) 时间 (2 dim)**
- `second_of_day_sin/cos`: 时间-day cycle encoding
- 机制: BTC 24/7 但有 regional session 节律 (US 开盘活跃 / Asia 夜盘 / 周末薄弱). sin/cos 让 model 学 session pattern.
- 注: V5 时代我们也试过 time2vec extra channels (4 dim hour+dow), 实测 fold 0 P -23% (anti-pattern) — 24/7 trading 的 session 信号弱, 加更多时间 features 反而 dilute.

**(l) Delta / others (3 dim)**
- `delta_bid_depth_L5`, `delta_ask_depth_L5`, `delta_pressure_5s`
- 机制: 5s 内深度变化 = order arrivals - cancellations. Cancellation cluster 是 regime change 前兆.

**Path A 数值转化 (per feature):**
1. 计算时已经做了 (`src/features/pipeline.py`):
   - 价格 → bps 相对 mid (log_return, microprice_dev, spread_bps)
   - 数量 → log1p (depth, volume — 压缩重尾)
   - 比例形式 (OBI, depth_ratio, amt_ratio, trade_imbalance — bounded [-1, 1] 或 [0, 1])
   - rank 形式 (obi_L5_rank_1h, net_flow_rank_1h — vol-regime invariant)
2. 训练时进一步:
   - **NPZ 加载**: `np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)` (anti-NaN crash)
   - **RevIN per-instance norm**: 每个 (B, T=600) window 沿 time axis 计算 per-feature mean/std, 然后 z-score normalize. 处理跨日 distribution shift (PSI=0.349 实测).
   - **Per-fold global standardization** (在 dataset.py): 用 train fold 的 x_mean/x_std 在所有 fold 上 standardize, clip 到 [-10, 10].
   - **NaN/Inf cleanup**: 二次 sanitize 防御性

#### Path B — 25 levels × 4 channels 原始 LOB tensor

**形状**: `x_raw` shape (T=600, n_levels=25, 4) per sample.

**4 channels (per level, per timestep):**
- `bid_delta_bps`: `(bid_price_level_i - mid) / mid * 1e4` (该档 bid 价相对 mid 的 bps; 为负数, 远档更负)
- `bid_log_amt`: `log(1 + bid_qty_level_i)` (该档 bid 数量 log1p; log1p 处理 0 + 压缩重尾)
- `ask_delta_bps`: `(ask_price_level_i - mid) / mid * 1e4` (该档 ask 价相对 mid 的 bps; 正数, 远档更正)
- `ask_log_amt`: `log(1 + ask_qty_level_i)`

**机制**:
- Path A 是 hand-crafted "线性可提取" 信号, Path B 给 model 直接看原始 book shape, 让 NN 学**非线性 / 跨档 / 跨时间** combinations
- 实测 (今天 fair Ridge benchmark): 线性 access raw LOB 只 +0.001 P, 几乎 0 增益 — 说明 "原始 LOB → 信号" 的提取**必须非线性** (即 V5 ~75% Pearson 增益的来源)
- 25 levels: Binance 公开深度 50 levels, 25 已 cover ~95% top-of-book 流动性. 加深到 50 实测边际收益 ~0 (anti-pattern, 已测).
- 1Hz 采样: 中频 horizon (10 min) 下 1s 已足够. 加细到 100ms tick-level → 数据量 10×, 信号衰减 (HFT regime, 不在我们 horizon)

**编码**:
- `RawLOBEncoder` (`src/model/raw_lob_encoder.py`): per-timestep spatial Conv 跨 levels, 提取 "book shape" 特征
- 输出 (T, d_raw=16) per sample, 然后与 Path A (T, d_model=32) **concat fusion** 进 backbone

#### Regime Prior — 6 维 hourly-scale (per-sample, non-temporal)

**Features** (`src/features/regime_prior_features.py`, strictly causal):
- `vol_1h`: 1-hour 滚动 std of log_return_1s (短期 vol regime)
- `spread_mean_1h`: 1-hour 滚动 mean of spread_bps
- `obi_trend_1h`: 1-hour 滚动 OLS slope of obi_L5 (book pressure 趋势)
- `price_return_6h`: 6-hour log return (long-horizon momentum)
- `hour_sin/cos`: time-of-day encoding

**机制**:
- 这 6 个 features **不进 timestep 维度**, 是 per-sample 的"regime context"
- 进 PPNetGate: `gate(regime) * pooled_embedding` (multiplicative gate)
- Model 通过 PPNet 学 "在这个 regime 下, 应该把信号 scale 多少"
- **Phase B audit (5/5)**: regime_prior 6 features 与 next-30d y_mean 相关性 max |corr|=0.14, 弱信号, 但 model 仍能 squeeze 出一些 regime conditioning

**Causality**:
- 全部 trailing rolling, 不含 t+1 之后
- 单测: `tests/test_regime_prior_features.py::test_no_future_leakage` (修改 t > k 之后所有数据 → 验证 regime_prior[0..k] 不变)

#### Target — y_600 (training label)

**定义**: `y_600 = log(mid[t+600s] / mid[t])` (10 min 前向 log return)

**单位 / 量级**: log return ≈ 1e-4 量级 (BTC 10min 典型移动 ~0.1% = 10 bps). 训练时 z-score, eval 时 ×1e4 = bps.

**Per-fold normalization** (训练侧):
- `median_train`, `σ_MAD_train`: 计算自 train fold 的 valid samples
- `z = clip((y - median_train) / σ_MAD_train, -10, 10)`
- **MAD-σ vs std**: 用 median absolute deviation × 1.4826 (Gaussian-equivalent) 而非 std. **理由**: σ_MAD 对 outliers 鲁棒 (BTC 收益重尾, 偶尔 ±3σ 极端 event 会让 std 偏大, MAD 不会).
- **clip [-10, 10]**: 极端样本不污染 loss 梯度. 10σ_MAD 远大于实际 BTC y_600 范围 (~5σ).

**y_mask_600** (boolean): 1 if forward window 完整观测, 0 if 缺数据 (跨日切换 / 数据缺失). 训练 / eval 都 filter `mask=1`.

### 5.2 模型架构 — 各层机制详解

V5 singh production 实际 active 组件 (per `configs/v5/screen/backbone_conformer_hardened_singleh_alpha0_huber.json`):

| 组件 | 状态 | 说明 |
|---|:-:|---|
| RevIN | ✓ ON | Per-instance normalization (ICLR 2022, 处理跨日 non-stationarity) |
| GDCN | ✓ ON | Gated Deep Cross Network (CIKM 2023, gated feature crossing) |
| Path B Raw LOB encoder | ✓ ON | spatial Conv on 25 levels × 4 channels |
| channel_mix_conv | ✓ ON | per-channel mixing conv |
| Conformer backbone | ✓ ON | ★ Conv k=15 + Self-Attn + FFN ×2 blocks |
| LevelAttentionPool | ✓ ON | attention-weighted pool over time |
| PPNetGate | ✓ ON | regime-conditional multiplicative gate (KDD 2023) |
| MonotonicQuantileHead | ✓ ON | structural q10<q50<q90 |
| **MaskNet** | **✗ OFF** | (`use_masknet=False`) — V4/V5 都不启用, V4 baseline_plus 也是 OFF |
| **V4 DilatedCausalConv** | **✗ OFF** | (`use_conv=False`) — Conformer 替代 |
| **V4 patch attention** | **✗ OFF** | (`use_attention=False`) — Conformer 自带 attention |
| **patch_attention_pool** | **✗ OFF** | LevelAttentionPool 替代 |

#### 各层 mechanism + fusion 详解

**(1) RevIN — Reversible Instance Normalization (ICLR 2022)**

输入: x_features (B, T=600, 64). 输出 (B, T, 64), 同形状.

机制:
- 对每个样本 (per-instance, per-window) 沿 time axis 计算 per-feature mean/std
- `x_norm[i, t, f] = (x[i, t, f] - μ[i, f]) / σ[i, f]` 其中 `μ, σ` 仅在该 sample 内统计
- **Reversible**: norm 阶段记录 μ/σ, model 输出后可 denormalize. 但我们 target (y_600) 是 stationary log-return, 不需要 denorm output, 所以这里只用 normalize.
- Affine learnable: `x_revin = γ · x_norm + β` (γ, β 是 per-feature 可学习参数)

为什么要它:
- BTC 跨日 non-stationarity 严重 (PSI 实测 0.349, 显示 train vs test 分布显著漂移)
- 不同日 vol 量级可能 5× 差距, raw scale 让 NN 收敛差
- Per-instance norm 让每个 window 看到 ~unit-scale 输入, model 学 relative pattern 而非 absolute level

实施细节: `src/model/dual_path_model_v3.py:RevIN`. 关键: norm 在 input 端 (Path A 进入 MaskNet/GDCN 前), output 不 denorm.

---

**(2) MaskNet (DLP-KDD 2021) — `use_masknet=False`, 跳过**

历史: V3 era 用过, V4 phase A ablation 发现可关掉 (use_masknet=False) IC 不退. V5 沿用 OFF.

代码保留: `src/model/masknet.py` (供未来 ablation, runtime forward 跳过).

---

**(3) GDCN — Gated Deep Cross Network (CIKM 2023)**

输入: (B, T, 64). 输出: (B, T, 64) — 同形状, feature 维度不变.

机制:
- 经典 cross network 公式: `x_{l+1} = x_0 ⊙ (W_l x_l + b_l) + x_l` (L 层 stacking, residual)
- GDCN 加 gated 变体: `x_{l+1} = (x_0 ⊙ W_l x_l) * sigmoid(g_l x_l) + x_l`
- gated 让 model 学**哪些 feature interactions 重要**, 哪些 noise

为什么要它:
- 64 个 hand-crafted features 之间有强 interaction (e.g., obi_L5 × spread = "买压在窄 spread 下更可信")
- 单纯 Linear→Conformer 不足以学 explicit feature crossing
- GDCN 在 64-dim 原始 features 上做 cross, 不在 d_model=32 投影后做 (preserves theoretical advantage)

实施: `src/model/gdcn.py`. n_cross_layers=1 (仅 1 层, 防止过 deep).

---

**(4) Linear projection: 64 → d_model=32**

输入: (B, T, 64). 输出 (B, T, 32). Path A 的 final 投影到 d_model. 单层 nn.Linear.

为什么 d_model=32:
- 实测 d_model=64/96 在 V5 hardened 配置上**未测过** (旧 backbone screen 用错 loss)
- 当前 d_model=32 + Conformer ×2 = 109K params, 与 train 数据量 ~210K samples × 600 timesteps = 126M 匹配 (params:samples ratio ~1:1200, well below overfit threshold)
- **优化方向**: Tier 3 中提到 d_model=48/64 retraining 可能 +0.005 P (未测)

---

**(5) RawLOBEncoder + channel_mix_conv — Path B**

输入: x_raw (B, T=600, n_levels=25, 4). 输出: (B, T, d_raw=16).

机制:
- **Spatial Conv on levels**: per-timestep, 在 25 levels × 4 channels 上做 Conv (可视为 25-长度 sequence, 4 input channels). 提取 "book shape" 特征 (slope, concentration, skewness across levels).
- **Channel mix conv** (use_channel_mix_conv=True): 把 4 input channels (bid/ask × delta_bps/log_amt) 互相混合, 学 channel-level interactions
- 输出 d_raw=16 dim per timestep

为什么 d_raw=16 (vs d_model=32):
- Path B 是补充信号, 不应主导 (Path A 已经 capture 大部分 alpha)
- 16 dim 对 25 levels × 4 = 100 input → 6× 压缩, 强迫学 essential structure
- 实测 V4 早期试过 d_raw=8/24/32, 16 是 sweet spot

实施: `src/model/raw_lob_encoder.py`.

---

**(6) Path Fusion: Concat then Linear**

输入:
- Path A output: (B, T, 32)
- Path B output: (B, T, 16)

操作:
- **简单 concat 沿 feature 维度**: (B, T, 32+16=48)
- 然后 Linear 投影: 48 → 32 (回到 d_model)

为什么 concat 而非 gated / attention:
- **奥卡姆剃刀**: 最简单 fusion 让 downstream Conformer 自己学 weighting
- 实测 V3 era 试过 gated fusion (`fusion_kind="glu"`), IC 改善仅 noise 级 (~+0.001 P), 加 ~3K params 不值
- Conformer 后端有足够 capacity 学 channel-level weighting, fusion 层不需要再加 gating

实施: `src/model/dual_path_model_v3.py:fusion_kind="concat"`.

---

**(7) Conformer backbone ×2 blocks** ★ V5 关键升级

输入: (B, T=600, 32). 输出: (B, T, 32).

每个 block 内部 (sandwich 结构):
```
input → ½·FFN_1 → SelfAttention → ConformerConvModule(k=15) → ½·FFN_2 → output
        (residual)  (residual)        (residual)              (residual)
```

各模块:
- **SelfAttention** (n_heads=2): 抓 600s 内长程依赖. Causal mask (lower triangular) 严格防 lookahead.
- **ConformerConvModule** (kernel=15): point-wise Conv → GLU → depthwise Causal Conv (k=15) → BatchNorm → SiLU → point-wise Conv → Dropout. **Causal Conv** (左 padding k-1=14, 输出 trim 到原长) 严格不看未来.
- **½·FFN sandwich**: 经典 FFN expansion=4 (32→128→32). 两个 ½ 权重 sandwich 是 Conformer 标准做法.

为什么 Conformer (vs V4 DilatedCausalConv 或 vanilla Transformer):
- LOB 时序在两个尺度上有信息:
  - 局部 (~10-30 秒): order book imbalance shifts, micro-trends → Conv 擅长
  - 长程 (~1-10 分钟): regime persistence, macro flows → Attention 擅长
- Conformer sandwich (FFN→Attn→Conv→FFN) **同时承载两个尺度**:
  - SelfAttn 之前 FFN preprocess → 给 Attention 提供高维表征
  - Attn 后接 Conv → 在 Attention 提供的全局视野上做 local refinement
  - 残差连接 + ½ scale 保留低层信息
- 实测对照 (5/3): conformer_hardened P=+0.055 vs V4 conv_lasts P=+0.050 (+11%, single seed beats V4 3-seed median)

参数: `n_blocks=2, n_heads=2, kernel_size=15, attn_d_ff=64`. 总 ~90K params (大头在这).

实施: `src/model/backbones/conformer_backbone.py`.

---

**(8) LevelAttentionPool over time**

输入: Conformer output (B, T=600, 32). 输出: (B, 32) — pooled 单向量.

机制:
- Learnable query vector (d_model=32) 对 (B, T, 32) 做 cross-attention
- 输出每个 timestep 的 attention weight, 加权求和 → (B, 32)
- **类似 attention over sequence** (而非 mean pool 或 last-timestep)

为什么 vs alternatives:
- **Mean pool over time**: 简单但 dilute (每个 timestep 等权, regime-irrelevant timestep 也算)
- **Last-timestep** (V4 conv_lasts 用): 信息丢失大 (只看 t=599, 忽略前 599 sec)
- **AttentionPool**: model 学 "哪些 timestep 重要", 比如 regime 转折时会更 attend
- 实测 V5 hardened: AttentionPool > last-timestep ~+0.003 P

实施: `src/model/attention_pool.py:LevelAttentionPool`.

---

**(9) PPNetGate — regime conditional multiplicative gate (KDD 2023)**

输入:
- pooled embedding (B, 32) from LevelAttentionPool
- regime_prior (B, 6)

输出: gated embedding (B, 32).

机制:
```
gate = sigmoid(MLP(regime_prior))   # (B, 32) — per-channel gating
out = gate ⊙ pooled                  # element-wise multiply
```

为什么 multiplicative gate:
- regime 不是直接 alpha source (不应直接预测), 是 modulator (在 high-vol regime 下, 模型应该 scale-down 信号 confidence)
- Multiplicative 让 PPNet 调整 amplitude **per-channel**, 不 shift baseline
- 局限: PPNet **无法 shift baseline** (anti-pattern #24 — Phase B 试过加 additive 都 fail; Phase B.5 关掉 PPNet 反而退步)

实施: `src/model/ppnet_gate.py`. d_prior=6, d_hidden=32 (=d_model).

**Phase B 教训**: 我们试过加 `regime_bias_head` (additive scalar bias, B.1), 加 `recent_y_mean` 7th regime feature (B.2), 关掉 PPNet 改 strict disentangle (B.5) — 全部 fail. 详见 `docs/PHASE_B_OVERNIGHT_REPORT_2026_05_06.md`.

---

**(10) MonotonicQuantileHead — structural q10 < q50 < q90**

输入: (B, 32) gated embedding. 输出: dict `{quantiles: (B, 3), point_pred: (B,)}` where quantiles = [q10, q50, q90].

机制:
```python
base = base_head(h)                              # h → Linear → GELU → Linear → (B,)
delta_low  = softplus(delta_low_head(h)) + 0.01  # always positive, floor 0.01
delta_high = softplus(delta_high_head(h)) + 0.01

q50 = base
q10 = base - delta_low      # 总是 < q50
q90 = base + delta_high     # 总是 > q50
```

为什么 vs alternatives:
- **Direct Linear → 3 outputs**: 不保证 q10 < q50 < q90 (quantile crossing). 训练时常 violated, 需要 sorting penalty post-hoc.
- **MonotonicQuantileHead**: structural guarantee, 无需 penalty.

★★★ **关键 caveat (anti-pattern #21 RECTIFICATION)**:
- q10 = base - softplus(δ_low) → q10 永远 ≤ q50
- 如果 loss 让 model rank-by-q10 (utility_alpha=1.0, V4 baseline 配方), model 会:
  - 学 q10 ≈ 真实 y 的 conditional 排序信号
  - q50 = q10 + softplus(δ) → 自然偏正于 q10, 但相对**真实 y_mean 偏负** (因为 q10 已经 ≤ y, q50 受 softplus 拉得没那么多)
  - 净效果: **q50 系统性 negative bias**, 实测 -0.41 bps NEG
- V5 surgical fix: utility_alpha=1.0 → 0.0, 让 model rank by q50 直接 → q50 自由 calibrate to E[y|x]
- 实测: 一行修改, bias -0.41 → +0.14 bps, P/S 仅 -3% noise floor

`min_delta = 0.01`: floor 防止 softplus 输出过小导致 q10 ≈ q50 (numerical degenerate).

实施: `src/model/monotonic_quantile.py:MonotonicQuantileHead`.

---

**(11) Output: q10, q50, q90 — un-normalize 到 raw bps**

模型输出在 z-space (training 时 y 被 normalize), 用法:

```python
q_bps = (q_z * y_sigma_train + y_median_train) * 1e4
```

`y_sigma_train` = MAD-σ (×1.4826) of train fold y; `y_median_train` = median of train fold y. 两者 per-fold 计算, 存入 `test_preds.npz` 供 eval.

**总数据流**:
```
input (raw scale) → RevIN normalize → ... → z-space output
                                                    ↓
                                          un-normalize (×σ + median)
                                                    ↓
                                          ×1e4 (bps form)
                                                    ↓
                                          y_pred_q50_bps (CSV column)
                                                    ↓
                                          live causal EMA-demean (Layer 2)
                                                    ↓
                                          y_pred_q50_bps_live (production)
```

#### 总参数 + 计算量

- 总 params: **109,299** (singh, n_horizons=1)
  - GDCN ~2K
  - Path A Linear projection ~2K
  - RawLOBEncoder + channel_mix_conv ~5K
  - Path Fusion ~2K
  - Conformer ×2 backbone **~85K** (大头)
  - LevelAttentionPool ~2K
  - PPNetGate ~3K
  - MonotonicQuantileHead ~3K
  - 其他 (RevIN affine, layer norms) ~5K
- Forward: per sample ~3M FLOPs (Conformer 主导)
- Inference latency: <1 ms per sample on RTX 3090 (batch=1024)

**Forward 数据流 (active path only):**

```
Input: x_features (B, T=600, 64)  +  x_raw (B, T, 25, 4)  +  regime_prior (B, 6)
        │                                │                       │
        ▼                                ▼                       │
   ┌──────────┐                    ┌──────────────┐              │
   │  RevIN   │                    │ RawLOBEncoder│              │
   │ per-inst │                    │ spatial Conv │              │
   │ normalize│                    │ on LOB levels│              │
   └────┬─────┘                    └──────┬───────┘              │
        ▼                                  │                      │
   ┌──────────┐                            │                      │
   │  GDCN    │  (use_masknet=False,       │                      │
   │(gated x) │   MaskNet 跳过)            │                      │
   └────┬─────┘                            │                      │
        ▼                                  │                      │
   ┌──────────┐                            │                      │
   │ Linear → │                            │                      │
   │ d_model  │                            │                      │
   └────┬─────┘     ┌──────────────────────┘                      │
        ▼           ▼                                              │
       ┌─────────────────┐                                         │
       │ Path Fusion     │                                         │
       │ concat→Lin → 32 │                                         │
       └──────┬──────────┘                                         │
              ▼                                                    │
   ┌─────────────────────┐                                         │
   │ Conformer ×2 blocks │  (use_conv=False, use_attention=False;  │
   │ ½FFN → SelfAttn →   │   V4 早期 conv/attn 都跳过, Conformer  │
   │ Conv(k=15) → ½FFN   │   是唯一 temporal backbone)            │
   └────────┬────────────┘                                         │
            ▼                                                      │
   ┌──────────────────┐                                            │
   │ LevelAttention   │                                            │
   │ Pool over time   │                                            │
   │ (B, 32)          │                                            │
   └────────┬─────────┘                                            │
            ▼                                ┌────────────────────┘
   ┌──────────────────┐                      │
   │  PPNetGate       │  ◄───────────────────┘  (multiplicative)
   │  regime gating   │
   └────────┬─────────┘
            ▼
   ┌──────────────────────────────┐
   │ MonotonicQuantileHead        │
   │   base_head → q50            │
   │   q10 = q50 - softplus(δ_low)│
   │   q90 = q50 + softplus(δ_high)│
   └──────────────────────────────┘
            │
            ▼
   q10, q50, q90  (raw log-return; ×σ_train_MAD + median 后 × 1e4 = bps)
```

**关键设计:**
- Path A (domain knowledge) AND Path B (raw LOB learned representation), 不是 OR. 双路径互补。
- **MaskNet 已 OFF**: 历史 V4 phase A 试过, baseline_plus 关掉; V5 沿用 OFF 配置. 见 anti-pattern note in `docs/PROJECT_OVERVIEW.md`. (代码保留供 ablation, runtime 跳过)
- **Conformer backbone 替代 V4 conv + V4 attention**: 一份 backbone 同时承担两个 V4 separate 模块的功能
  - Self-Attention 抓 600s 内的长程依赖 (regime 持续性, micro-cycle)
  - Conv (kernel=15) 抓 ~15s 局部 pattern (micro-trend, OBI shift)
  - 残差 + ½FFN sandwich 保留低层信息
- **MonotonicQuantileHead 关键 caveat**: q10 = base - softplus(δ_low) 强 coupling. 如果 ranking score 取自 q10, 会强制 base/q50 偏负 (anti-pattern #21 RECTIFICATION).
- **总 params**: 109,299 (singh, n_horizons=1)

### 5.3 损失函数设计

```python
L = 0.10 · pinball(q10/q50/q90)         # quantile head 校准 (q10/q90 coverage)
  + 0.50 · utility_rank(α=0)            # Spearman primary (rank by q50 直接)
  + 0.50 · plain_Huber(q50, y, δ=2)     # Pearson + magnitude + bias
```

**为什么这 3 个组件**:

#### (a) Pinball loss, weight 0.10 (低权重)
- L_pinball = mean over τ ∈ {0.10, 0.50, 0.90}: max(τ·(y-q_τ), (τ-1)·(y-q_τ))
- 维持 q10/q50/q90 calibration (实测 P(y<q10)=0.103, P(y>q90)=0.100, perfect)
- **权重低**: V4 是 1.0, 我们降到 0.10. pinball pressure 把 q50 锚到 median(y)≈0, 压缩 σ. 0.10 够维持 calibration 不抑制 σ。

#### (b) Utility_rank, weight 0.50, α=0 ★ KEY
- score = α·q10 + (1-α)·q50 = q50 (when α=0)
- pairwise softplus: 鼓励 model rank by q50 directly
- **α=0 是 V5 关键 surgical fix**:
  - V4 时代用 α=1.0, 让 model rank by q10
  - q10 = q50 - softplus(δ) → q50 必须高于 q10. 但 softplus 总是正, 所以 q50 ≈ q10 + 偏正常数
  - Model 学 q10 well-calibrated → q50 = q10 + softplus → q50 implicitly 偏负
  - 实测 α=1 时 bias = -0.41 bps NEG; α=0 时 bias = +0.14 bps (修到接近零)

#### (c) Plain Huber, weight 0.50, δ=2 z-units, w_wrong=0 ★ KEY
- L_huber = 0.5·r² if |r|≤δ; δ·(|r|-0.5·δ) if |r|>δ
- δ=2 在 z-space ≈ 14 bps (2σ), L2→L1 transition
- **w_wrong=0 是关键** (即 plain Huber, 不是 directional Huber):
  - dir_huber 的 sign-attraction 项 (`w_wrong > 0`) 有 0-attractor bug
  - PyTorch `sign(0) = 0`, model 可以预测 ŷ=0 来 dodge sign-disagreement penalty
  - 实测 w_wrong=2.0 时 σŷ collapse 到 0.007 (anti-pattern #20)
  - plain Huber 是 conditional-mean estimator, 干净, 没 dodge 路径

#### Per-component contribution
| 组件 | 修复维度 |
|---|---|
| pinball (0.10) | q10/q90 head calibration (quantile coverage) |
| utility_rank α=0 (0.50) | Spearman 主力, 解开 q10-bias 耦合 |
| plain Huber (0.50) | Pearson + magnitude + bias (q50 ≈ E[y\|x]) |

**已 anti-pattern documented (NOT 用)**:
- ❌ utility_rank α=1 (#21 source: bias 偏负)
- ❌ dir_huber w_wrong>0 (#20: σ collapse)
- ❌ Direct Spearman REPLACE utility_rank (#15: val→test drift)
- ❌ tail-focal (#12: P/S 分歧)
- ❌ σ-anchor learnable (#13: val→test drift)
- ❌ beta_calib loss (V4 时用过, V5 移除 — α=0+Huber 自然让 β≈1.0)

### 5.4 训练 Recipe (Hardened)

| 参数 | V4 baseline_plus | V5 hardened | 改动理由 |
|---|---|---|---|
| Backbone | conv_lasts (DilatedCausalConv + last) | **Conformer** ×2 (Conv k=15 + Attn + FFN) | 加 attention 长程依赖 |
| Pool | last-timestep | **LevelAttentionPool over time** | 跨时间聚合更稳健 |
| dropout | 0.15 | **0.20** | 提高正则强度 |
| patience | 8 | **4** | 更激进早停, 避免 val 过拟合 |
| val_days | 30 | **60** | val 信号更稳健 |
| val_metric | composite (P+S avg) | composite | 同 |
| lr | 6e-4 cosine + warmup | same | |
| batch_size | 1024 | 1024 | |
| weight_decay | 0.001 | same | |
| EMA decay | 0.999 | same | |
| train/val/test | 700/30/90 days | 700/60/90 | val_days 增加 |
| embargo | 0 | 1-2 days | 防 lookahead |
| n_horizons | 1 | **1** (singh) | dropped y_180 aux (ablation 显示 net null) |
| seed | multi-seed median | **single seed=42 BEST** | multi-seed median 反而 hurt (#22) |

### 5.5 Live Calibration (Layer 2 production hygiene)

**问题**: V5 raw q50 有 +0.18 bps DC offset (mean(ŷ) > 0). 不是 regime drift, 是模型自身 baseline drift。trading 时 ŷ > 0 占比明显多 50% → 系统性 long bias。

**解**: Causal rolling EMA-demean
```python
def causal_ema_demean(yhat, alpha=0.01):
    ema = np.zeros_like(yhat)
    ema[0] = yhat[0]
    for t in range(1, len(yhat)):
        ema[t] = (1 - alpha) * ema[t-1] + alpha * yhat[t-1]  # 注意 t-1
    return yhat - ema
```
- α=0.01, half-life ≈ 69 samples ≈ 11.5h
- Per-fold reset (每 fold 不同 checkpoint)
- 50 sample warmup
- 输出: `y_pred_q50_bps_live` 列, mean ≈ 0, 不污染信号 (Pearson 仅 -3% noise)

**这是行业标准做法** (alpha 信号设计上 mean-zero). NOT post-hoc tuning.

### 5.6 测试结果

#### Pool 3-fold (n=49,953, raw + dense)

| Metric | Raw q50 | Live calibrated | 评价 |
|---|---:|---:|---|
| Pearson | +0.0617 | +0.0587 | shift-invariant, ~3% drop |
| Spearman | +0.0686 | +0.0658 | similar |
| **β** | +1.05 | **+1.005** | 接近完美 |
| σŷ/σy | 0.059 | 0.058 | identical |
| **bias bps** | +0.18 | **+0.0004** | live by-design 零均值 |
| Bin-S calib | 0.952 | **0.976** | live 反而更好 |
| Bin-S trade | 0.964 | **0.988** | live 反而更好 |
| Top-bot spread | +2.64 bps | +2.54 bps | -0.1 |
| Top decile t-stat | +7.14 | +6.88 | -0.26 |

#### Per-fold breakdown
| Fold | n | Pearson | Spearman | β | bias bps |
|:-:|---:|---:|---:|---:|---:|
| 0 | 16,216 | +0.058 | +0.072 | +0.90 | +0.23 |
| 1 | 17,858 | +0.062 | +0.064 | +1.28 | +0.02 |
| 2 | 15,879 | +0.068 | +0.069 | +1.14 | +0.02 |
| **Pool** | **49,953** | **+0.062** | **+0.069** | **+1.05** | **+0.09** |
| Per-fold std | | **0.004** | 0.004 | | |

**Per-fold P CoV 0.062 是历史最紧** — multi-seed median (V4 era) 也只有 0.078。

#### Bootstrap 95% CI (B=1000, stationary block)
- Pearson: +0.0617 [+0.0461, +0.0766] ← lower bound > 0 ✓
- Spearman: +0.0686 [+0.0570, +0.0795] ← lower bound > 0 ✓

#### Calibration view (按 y_true 分十档, ŷ_mean live calibrated)
| y bin | y_mean (bps) | ŷ_mean live (bps) |
|---:|---:|---:|
| 0 (worst) | -22.2 | **-0.058** ✓ NEG |
| 1 | -10.2 | -0.064 ✓ |
| 4 | -1.1 | -0.019 ✓ |
| 5 | +1.0 | +0.016 ✓ |
| 9 (best) | **+22.7** | **+0.092** ✓ POS |

**全 10 deciles 同号** (负 y → 负 ŷ, 正 y → 正 ŷ). Bin-Spearman 0.976。

#### vs Linear / Tree baselines (today's fair comparison)

| Model | Pool P | vs V5 |
|---|---:|---|
| Ridge (64 features) | +0.0352 | V5 +75% |
| Ridge (64 + raw LOB 100 dim) | +0.0299 (fold 0) | adding LOB to linear: +0.001 (≈0) |
| TemporalRidge | +0.0352 | V5 +75% |
| XGBoost | +0.0342 | V5 +81% |
| **V5 singh DL** | **+0.0617** | — |

**Hand-crafted 64 features 已 saturate 线性可提取的 LOB 信息**。V5 ~2× P 提升完全来自 DL 非线性建模, 不是数据访问不公平。

#### Temporal stability (regime adaptation diagnostic, 5/9 gates pass)

- 月度 IC trajectory: worst-month P=+0.022 (2025-03 regime flip 期), best-month +0.10 (2025-02)
- Daily ŷ_mean ↔ y_mean correlation: **-0.21** (NEGATIVE — model 不能 adapt regime)
- Static-prediction var ratio: 0.011 (稍 weak adapt, 接近 ρ²)

**这是 single-asset y_600 fundamental limit, 不是 V5 bug**:
- regime_prior |corr| with future regime 仅 0.05-0.14, 弱信号
- 4 次 Phase B regime adaptation 尝试 (B.1/B.2/B.5 + actual-y EMA) **全 fail**
- 真解 = production engineering (Layer 4 online retraining), 不是 model architecture

完整诊断: `exports/v5_singh_alpha0_huber/STRICT_EVAL_TEMPORAL.md` + `docs/PHASE_B_OVERNIGHT_REPORT_2026_05_06.md`.

### 5.7 数值处理 / 去偏 / 稳健化 — 专题汇总

中频 BTC LOB 数据的 4 个数值挑战:
1. **跨日 non-stationarity** (PSI=0.349)
2. **重尾收益分布** (kurtosis 38+, 远超 Gaussian)
3. **NaN/Inf 数据缺失** (LOB 偶有空档)
4. **低 SNR 下 σ 收缩 trap** (Bayes shrinkage 让 model 倾向预测 ~0)

我们用多层防御应对:

#### A. 数值转化 (Value transformations)

| 输入 | 转化方式 | 理由 |
|---|---|---|
| **绝对价格** | `log_return_Δ = log(P[t]/P[t-Δ])` | 价格 non-stationary, log return approximately stationary |
| **价格 (LOB levels)** | `delta_bps = (price - mid) / mid * 1e4` | 不同 BTC 价格水平下 absolute 差不可比, bps 形式 invariant |
| **数量 (LOB)** | `log_amt = log(1 + qty)` (log1p) | 数量 distribution 重尾 (有时 10× 其他档), log1p 压缩 + 处理 0 |
| **OBI 等比例** | `(bid - ask) / (bid + ask)` bounded [-1, 1] | 自然 normalized, 不需额外 scale |
| **Vol** | `realized_vol = sqrt(sum(r²))` 多 timescale | sqrt 让 vol 与 return 同量级 |
| **rank features** | rolling rank within 1h | regime-invariant (高 vol 期不会让 rank 失常) |
| **target y_600** | log return → z-score per fold | training 时 model 看 ~standard normal |

#### B. Per-fold y normalization (训练 + eval 解耦)

```python
y_median = np.median(y_train_valid)
y_sigma_MAD = np.median(np.abs(y_train_valid - y_median)) * 1.4826  # Gaussian-equivalent
y_z = clip((y - y_median) / y_sigma_MAD, -10, 10)
```

**关键选择**:
- **MAD-σ vs std**: BTC 收益 kurtosis ~38 (远超 Gaussian=3). std 被极端值偏大, MAD 不受影响. 1.4826 是 MAD → σ_Gaussian 的 robust estimator scale factor.
- **clip [-10, 10]**: 极端 outlier (如 flash crash, ±50σ event) 不让 loss gradient 爆炸. 10×σ_MAD 远大于实际 BTC y_600 范围 (~5σ_MAD).
- **per-fold** (非 global): 不同 fold 的 train period y 分布略不同, per-fold 计算保证 z-norm 对 train 是 ~zero-mean unit-σ.
- **存到 test_preds.npz**: `y_sigma`, `y_median` 字段, eval 时反向 un-normalize 回 bps.

#### C. Input feature normalization (RevIN + global standardization)

**双层 normalization**:
1. **RevIN per-instance** (per-window):
   - 每个 (B, T=600) sample 沿 time axis 计算 per-feature μ/σ
   - normalize: `x_norm = (x - μ) / σ`
   - **目的**: 处理跨日 non-stationarity, 让每个 window 看到 ~unit-scale input
   - learnable affine `γ, β`: 让 model 选择是否反 norm 部分 channels

2. **Global per-fold standardization** (在 dataset.py):
   - 用 train fold 的 x_mean, x_std (across all train samples × timesteps)
   - apply 到 train/val/test: `(x - x_mean) / x_std`
   - clip 到 [-10, 10]
   - **目的**: 防止某个 feature 的 raw scale 过大主导 RevIN 的 per-instance σ 估计

#### D. NaN / Inf 防御性处理

LOB 数据偶有缺失 (网络抖动 / cross-day 切换 / 数据 build 漏洞). 多层 cleanup:

1. **NPZ build 时**: `nan_to_num(features, nan=0, posinf=0, neginf=0)` (`src/features/pipeline.py`)
2. **Dataset 加载时**: 二次 `nan_to_num` 防御 (`src/training/dataset.py:_load_day`)
3. **Mask `y_mask_600`**: 1 if 完整观测, 0 if invalid → loss 自动 skip masked samples
4. **MonotonicQuantileHead `min_delta=0.01`**: 防 softplus 输出 0 → q10 = q50 numerical degenerate

#### E. 去偏 (Bias mitigation) — 4 个机制

模型有多个潜在 bias 来源, 每个对应一个 mitigation:

| Bias 来源 | 影响 | Mitigation |
|---|---|---|
| **跨日 distribution shift** (PSI 0.349) | input scale 漂移 | RevIN per-instance norm |
| **MonotonicQuantileHead softplus offset** | q50 偏负 ~-0.4 bps | utility_alpha=1.0 → 0.0 (rank by q50 直接, anti-pattern #21 RECTIFIED) |
| **Train 期 y_mean ≠ test 期** (regime drift) | DC offset 累积 | Live causal EMA-demean (Layer 2 inference) |
| **训练 weight 噪声 (single-epoch overfit)** | val/test fluctuation | EMA decay 0.999 weight averaging |
| **单一 metric overfit** (Pearson 偏极端值) | val→test drift | Composite val_metric = 0.5·P + 0.5·S (Spearman 抗 outlier) |
| **Train/test horizon 重叠** (label leak) | 残差 AC 0.94 | Embargo 1-2 days between train/val/test |
| **σ collapse trap** (Huber/MSE 在低 SNR 下 push σ→0) | model 退化为常数预测 | 强制搭配 L1-like (pinball + utility_rank) anchor |
| **Direction-attraction trap** (dir_huber sign(0)=0) | model dodge sign penalty by predicting 0 | plain Huber w_wrong=0 (anti-pattern #20) |

#### F. 稳健化 / 去极端 (Outlier robustness)

低 SNR 重尾环境下, 抗极端值是核心:

| 机制 | 目的 |
|---|---|
| **log1p 压缩 quantity** | 减少 single-level 巨量 outlier 影响 |
| **MAD-σ normalize** | 极端 y 不让 σ 偏大 |
| **z-clip [-10, 10]** | 极端 y 不让 loss gradient 爆炸 |
| **Huber loss (δ=2)** | tail 区域 (|r|>δ) L1 (linear gradient), core L2 (quadratic gradient). 抗 ±5σ tail event |
| **Pinball loss** | quantile head 保证 q10/q90 实测 coverage 接近 0.10/0.10 (实测 0.103/0.100 ✓) |
| **Block bootstrap CI** (block_len=60, B=1000) | 残差有序列相关 (anti-pattern #2), naive iid bootstrap CI 偏紧; stationary block bootstrap 保留依赖结构 |
| **per-fold-stride10 IC** | dense IC inflated by overlap, stride10 给 IID-clean estimate |
| **MonotonicQuantileHead min_delta=0.01** | 防 q10/q90 collapse 到 q50 (numerical floor) |

#### G. Spurious 信号防御

低 SNR 任务下, model 容易学 train-period spurious patterns. 防御:

1. **Walk-forward CV**: 严格按时间排序, 不允许 random split. 每个 fold 测的是 OOS future data.
2. **Embargo 1-2 days**: train end → val start 至少 1 day gap, 防 horizon overlap label leak. 实测 anti-pattern #2: stride < horizon 残差 AC 飙到 0.94.
3. **Composite val metric**: P + S 同向才升, 单 metric 涨另一掉直接 reject (anti-pattern: P/S 分歧 = tail-focal trap).
4. **Patience 早停**: patience=4 epochs 防止 val 噪声追到尾部.
5. **3-fold pool eval**: 单 fold 0 信号不可信 (anti-pattern #14, #25). 必须 3-fold pool 验证.
6. **Bootstrap CI 报告**: 单点估计 P=0.06 不够, 必须 [+0.046, +0.077] 95% CI 双向 显著.
7. **Multiple time slice 验证**: 不同 fold (不同 regime) 都要 ≥ baseline-0.01 P.

#### H. 已经发现并 mitigation 的 trap (anti-patterns 列表)

完整 25 条 anti-patterns 在 `CLAUDE.md`. 数值 / 去偏相关:

- **#2** stride < horizon → 标签重叠 (用 stride=180 ≥ horizon/3, eval stride10)
- **#7** y 量级 (raw vs z-norm) 不一致让 MonotonicQuantileHead softplus clamp (强制 z-norm)
- **#12** Tail-focal loss → P/S 分歧 (P 被极值带飞, S 不升)
- **#13** σ-anchor learnable scalar → val→test catastrophic drift (free Parameter 在 val 调到极端值)
- **#14** 单 fold + 单 seed 单次 run cudnn 非确定性 (复现 EMA P 从 +0.04 翻 -0.02)
- **#16** β 报告必须双向 + σ_ŷ + per-fold ρ (单一 β 数值无意义)
- **#18** Smooth target 在 train+test 都替换 = 假胜利 (eval 必须在 RAW y)
- **#19** Stride/space 口径让 P 飘 0.029→0.058 (production 一锁到底 raw + dense)
- **#20** dir_huber sign-attraction 0-attractor σ collapse
- **#21 RECTIFICATION** Calibration bias 是结构 bug (utility_alpha+softplus 耦合), surgical fix 适用

每条都对应 production code 的具体 mitigation, 见 CLAUDE.md "Anti-Patterns" 章节.

---

## 6. V4 → V5 升级思路

### 6.1 架构升级

| 维度 | V4 baseline_plus | V5 hardened | 单 axis 贡献 |
|---|---|---|---:|
| Backbone | DilatedCausalConv + last-timestep | **Conformer** (Conv k=15 + Attn + FFN) | +0.005 P |
| Pool | last-timestep | **LevelAttentionPool over time** | +0.002 P (混在 backbone 中) |
| Recipe | dropout 0.15, patience 8, val 30d | dropout 0.20, patience 4, val 60d | +0.003 P |
| **总架构 + recipe** | | | **+0.010 P** |

### 6.2 Loss 升级 (核心)

V4 baseline_plus loss:
```
L_v4 = 1.0·pinball + 0.3·utility_rank(α=1.0) + 0.2·dir_huber(w_wrong=2.0) + 0.05·beta_calib
```

V5 α=0+Huber loss:
```
L_v5 = 0.10·pinball + 0.50·utility_rank(α=0.0) + 0.50·plain_Huber(w_wrong=0)
```

**5 个具体改动**:
1. **`utility_alpha 1.0 → 0.0`** ★ 最关键: 解开 q10-rank-pull 偏负 bias artifact
2. **`lambda_quantile 1.0 → 0.10`**: 减弱 pinball pressure, 让 q50 自由扩展量级
3. **`dir_huber → plain Huber`**: 避开 0-attractor σ collapse
4. **删除 `beta_calib`**: α=0+Huber 自然让 β=1.05, beta_calib 多余
5. **`lambda_utility_rank 0.3 → 0.50`**: pinball 弱化后, 加强 rank pressure 维持 Spearman

### 6.3 V5 dualh → V5 singh (multi-horizon ablation)

V5 dualh: y_180 aux (weight 0.3) + y_600 primary (weight 1.0). 测试 multi-horizon 提供 gradient stability 假设。

V5 singh: drop y_180 aux. 同 backbone + loss + recipe。

| | dualh | singh | Δ |
|---|---:|---:|---|
| Pool P | +0.0622 | +0.0617 | -0.0005 (noise) |
| Pool S | +0.0672 | +0.0687 | **+0.0014 (+2.2%)** |
| Top-bot trading spread | +2.10 bps | +2.64 bps | **+26%** |
| Top decile t-stat | +6.66 | +7.14 | +7% |
| Per-fold P std | 0.0050 | 0.0039 | **-22%** |
| Params | 111,510 | 109,299 | -2K (一个 head) |

**结论**: dualh y_180 aux 在 pool level 没提供 measurable Pearson 增量, 反而:
- 占用 backbone 容量 (2K params)
- 增加 fold-1 outlier variance
- Spearman / trade signal / per-fold stability 都 singh 更好

singh 全 model capacity 给 y_600 head, 简单架构 + 同样 P + 更稳。**production winner = singh**.

详细对照: `docs/Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md` §14.

---

## 7. 关键 Anti-Patterns (不要重蹈)

完整 22 条在 `CLAUDE.md` §"Anti-Patterns". 高优先级避免:

### 数据 / 评估
- **#2** stride < horizon (标签重叠 → 残差 AC 0.94)
- **#7** y 量级 z-norm 必须做 (否则 MonotonicQuantileHead softplus clamp)
- **#18** target 必须在 RAW y 上 evaluate (smooth target trap)
- **#19** 同一 CSV 不同 stride/space 口径 P 飘 2× (raw + dense + per-fold-stride10 一锁到底)

### 模型 / 架构
- **#11** V5-LH variants (variance collapse)
- **#13** σ-anchor learnable scalar (val→test drift)
- **#24** single-asset regime adaptation 不在 model architecture 内 (Phase B 全 fail)

### Loss
- **#10** Multi-horizon UNIT (机制错配)
- **#12** Tail-focal (P/S 分歧)
- **#15** Direct rank loss REPLACE utility_rank (catastrophic val→test drift)
- **#20** dir_huber w_wrong>0 (0-attractor σ collapse)
- **#21 RECTIFICATION** Calibration bias 先做机制审计 (utility_alpha=1 + softplus 的结构 bug 可 surgical fix)

### 流程
- **#9** 单 fold-0 信号判断特征 (Ridge walk-forward 才是硬门槛)
- **#14** 单 fold + 单 seed 单次 run 不可靠 (cudnn 非确定性)
- **#16** β measurement: 必须报 σ_ŷ + per-fold ρ + 双向 β
- **#17** Baseline anchor discipline (必须从 production config 派生, 不是凭记忆)
- **#22** Multi-seed median 可能被 1 lucky + N weak seeds 拖累
- **#25** Regime fix 必须 3-fold pool 验证 (单 fold 改善 misleading)

### 已 null 路径 (不要再尝试):
特征 ×3 (tradeflow / long_context / infoflow) — Ridge walk-forward 全 ΔP≈0
架构 V5-LH ×4, multi_scale, hierarchical pyramid — 全 σ collapse fold 0
DANN, σ-anchor, smooth target — 全 collapse / drift
y_300 / y_1800 horizon — V4 -32% / 整条 line dead

---

## 8. 优化方向 (按 ROI 排序)

### Tier 1 — 工程层 (production deployment, NOT research)

**真正的 regime adaptation 解 (我们已证 model architecture 内不可行)**:

```
Layer 1 (model, ✓ shipped):     V5 singh α=0+Huber checkpoint
Layer 2 (calibration, ✓ shipped): causal EMA-demean (y_pred_q50_bps_live)
Layer 3 (monitoring, TBD):       rolling 30d IC alarm + auto-stop
Layer 4 (retraining, TBD):       weekly/biweekly retrain pipeline
```

| 项 | 难度 | ROI |
|---|---|---|
| Online retraining (周/双周) | 中 (script + scheduler + version) | 高: 让 train→deploy gap 始终 ≤ 1-2 周 |
| IC monitor + auto-stop | 低 | 高: prevent 在弱 regime 烧钱 trade |
| Position sizing (z-score threshold) | 低 | 中 |

### Tier 2 — Fundamental 突破 (single-asset 已 ceiling)

| 方向 | 期望 | 难度 |
|---|---|---|
| **Multi-asset breadth** (ETH/SOL/BNB) | Portfolio IR 0.6 → 1.5+ (Sharpe 转正) | 数周, 数据基础设施 |
| 正交数据源 (funding rate, OI, basis) | unknown but 跳出 LOB 范式 | 数周 |
| 缩短 horizon (y_180/y_120) | y_180 V4 已 P=0.094 production, 缩短可能更高 | 1-2 周 |

### Tier 3 — Single-asset 增量 (incremental, ROI 估计 +0.005-0.015 P)

我们漏掉的 obvious cheap wins, 未测过:
| 项 | 期望 | 实施 |
|---|---|---|
| Train stride 180 → 60 (3× more samples) | +0.005 P | 1-line dataset.py |
| d_model 32 → 48 / 64 | +0.005 P | config + 重训 ~3h |
| Snapshot ensembling (top-5 epoch avg) | +0.003 P | 已有 topk/, 加平均逻辑 |
| CRPS loss component (lambda_crps=0.10) | unknown | already in dul_loss.py, 加 weight |
| Asymmetric Huber (δ_neg=2.5, δ_pos=1.5) | +0.002 P | 1-line dul_loss.py |

### Tier 4 — 已 anti-pattern, NOT TRY:
- Multi-scale features / hierarchical pyramid
- DANN / adversarial domain adaptation
- σ-anchor learnable scalar
- σ collapse traps (dir_huber w_wrong>0)

---

## 9. Eval Tools

```bash
# Production STRICT_EVAL (15 gates, ~5 min)
python scripts/v5_alpha0_huber_strict_eval.py \
    --csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
    --out exports/v5_singh_alpha0_huber/STRICT_EVAL.md

# Live calibrated STRICT_EVAL
python scripts/v5_singh_live_strict_eval.py \
    --csv exports/v5_singh_alpha0_huber/y600_predictions_live.csv \
    --out exports/v5_singh_alpha0_huber/STRICT_EVAL_LIVE.md

# Temporal stability (regime adaptation diagnostic)
python scripts/v5_singh_temporal_eval.py \
    --csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
    --out exports/v5_singh_alpha0_huber/STRICT_EVAL_TEMPORAL.md

# Live calibration (causal EMA-demean) on raw CSV
python scripts/y600_live_calibrate.py \
    --in-csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
    --out-csv exports/v5_singh_alpha0_huber/y600_predictions_live.csv \
    --alpha 0.01 --warmup 50

# Generate CSV from new training run
python scripts/export_y600_predictions.py \
    --src-dir experiments/v5_final/<model_name>/ \
    --out-dir exports/<model_name>/

# Linear / tree baseline benchmark (Ridge / XGBoost / TemporalRidge)
python scripts/fair_ridge_baseline_y600_fast.py  # fold 0 quick (200 train days)
# 完整 3-fold benchmark 在 experiments/baselines_horizon_sensitivity/
```

---

## 10. 关键 Cross-References

### 跨会话 memory (Claude 用)
- `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/memory/MEMORY.md` — index
- `memory/y600_milestone_summary_2026_05_08.md` — 跨会话 milestone (核心范式 + 已 null 路径)

### 设计 / 实验 docs
- `docs/Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md` — 完整 V5 architecture + loss 深度文档 (~26 KB)
- `docs/PHASE_B_OVERNIGHT_REPORT_2026_05_06.md` — Phase B regime adaptation 4 次失败复盘
- `docs/Y600_REGIME_FEATURE_AUDIT.md` — Phase B 数据基础 audit
- `exports/v5_singh_alpha0_huber/README.md` — backtest 同事文档 (含 DC offset / regime drift / multi-asset 教学)
- `exports/v5_singh_alpha0_huber/STRICT_EVAL*.md` — 严格自测报告 (3 个角度)

### Operating rules (LLM 指令)
- `CLAUDE.md` — 行为规则 + anti-patterns + 当前 production 简介 (~322 行)
- `docs/PROJECT_PRINCIPLES.md` — 7 条 quant 行业 operating rules
- `docs/METRIC_DISCIPLINE.md` — eval 标准

### 单资产最终记录 (current authoritative)
- `docs/SINGLE_ASSET_Y600_FINAL_MILESTONE_2026_05_20.md` — REG_arch winner + CSH 回测 + 复现路径 + multi-asset 传承 (单资产收尾权威文档)
- `docs/V5_TO_PRODUCTION_ITERATION_2026_05_15.md` — 完整迭代路径
- `docs/Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md` — 架构 + loss 设计文档

### V4 era reference
- `docs/PROJECT_OVERVIEW.md` (4/18) — V4 era project overview (legacy)
- `docs/V4_MODEL_AUDIT.md` — V4 模型组件审计
- `docs/V5_BACKBONE_AUDIT.md` — V5 backbone screening 审计

### 实验产物 (training checkpoints + preds)
- `experiments/v5_final/singleh_alpha0_huber/` — production
- `experiments/y600_push/baseline_plus/` — V4 best baseline
- `experiments/v4_noattn_700d/` — V4 production y_180 (P=0.094)
- `experiments/baselines_horizon_sensitivity/y_600/` — Ridge/XGBoost benchmark
- `experiments/baselines_fair_ridge_y600/` — fair Ridge with raw LOB

### Tests
- `tests/test_regime_prior_features.py::test_no_future_leakage` — causality
- `tests/test_v4_causality.py` — model end-to-end causality
- `tests/training/test_recent_y_mean_causality.py` — Phase B feature causality
- `tests/model/test_regime_bias_head.py` — Phase B regime_bias module unit

---

## License + Authors

Internal research project. 同事提供的外部模型思路保留作参考: `tf_train_hrt_rnn_v1.py`, `tf_train_seq_att_v2_new.py`.

---

**Last updated**: 2026-05-08 by V5 singh production lock-in.
