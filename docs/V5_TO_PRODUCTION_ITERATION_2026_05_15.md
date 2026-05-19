> **创建:** 2026-05-15 13:00 UTC+8 | **Session:** v5push iteration summary doc
> **目的:** 详细汇总 V5 SINGH α=0+Huber → 当前 5-way ensemble production 的完整迭代路径, 每一步的 hypothesis / rationale / 概念基础 / 结果. 用作未来 LLM session compact 后的恢复参考 + 团队新人 onboarding.
> **状态:** living — 随新迭代追加 (按时间顺序)
> **关联 memory:** [[v5_singh_alpha0_huber_winner_2026_05_05]] [[v5push_3way_ensemble_winner_2026_05_13]] [[v5push_track_r_t_findings_2026_05_14]] [[v5push_5way_ensemble_reg_arch_2026_05_14]] + 多个 NEG memory

# V5 SINGH α=0+Huber → 5-way Ensemble Production — 完整迭代路径

---

## 0. TL;DR 当前 production (2026-05-14)

**5-way value-blend ensemble (R40/P20/A15/V25 weights):**

| 指标 | 值 | vs V4 baseline (P=0.094 y_180) | 评价 |
|:---|:---:|:---|:---|
| **Pearson** | **+0.0667** | y_600 is harder horizon (longer noise integration) | 紧贴 σŷ/σy Bayes ceiling |
| **Spearman** | **+0.0733** | | Spearman > Pearson (typical for heavy-tail crypto) |
| **β (y on ŷ)** | +1.05 | ≈1 ideal | trading slope OK |
| **σŷ/σy** | 0.057 | low-SNR regime | model 自信度 |
| **DA pool** | 0.5310 | vs 0.5 random | weak edge, useful |
| **DA \|y\|>σ** | 0.5522 | tradeable subset | meaningful directional edge in tail |
| **Pool n** | 49,953 | 3-fold × ~16K each | sufficient sample for IC stability |

**Components (4 underlying models):**

| Component | Standalone P | Standalone S | Loss specialty | Architecture diff |
|:---|:---:|:---:|:---|:---|
| **V5 prod (single)** | +0.0589 | +0.0661 | utility_rank α=0 + plain Huber | DAQH + MonotonicQuantileHead, single-stage PPNet |
| **Track A** | +0.0579 | +0.0690 | + DAQH (sign×magnitude decoupled) | + TV overlay (proven NOT loaded — see 5.2) |
| **Track P3** | +0.0582 | +0.0655 | + mag_focal_huber AUX (0.30) | DAQH + tail-focused mag |
| **REG_arch** ★ | **+0.0646** | +0.0723 | + tail-focal BCE on sign_logit | + FiLM γ+β multi-stage (replaces PPNet) |

**Production CSV path:** `exports/v5push_5way_ensemble_reg_arch/y600_predictions_5way_R40_P20_A15_V25.csv`

---

## 1. Foundational Concepts (理论基础)

### 1.1 Quantile Regression + DAQH (Direction-Aware Quantile Head)

经典 pinball quantile loss:
```
L_pinball(y, q) = Σ_τ max(τ·(y−q_τ), (τ−1)·(y−q_τ))
```
y_600 用 q10 / q50 / q90 三个 quantile, 优化器自然 learn distribution.

**DAQH 分解 q50 为 sign × magnitude:**
```
q50 = tanh(sign_logit) × softplus(magnitude_abs)
```
- `sign_logit` ∈ ℝ → tanh ∈ [−1, +1] = direction prediction (与 BCE classification 直接对接)
- `magnitude_abs` ∈ [0, ∞) → softplus(.) = 距离 0 的绝对值
- q50 sign 与 magnitude 解耦 = 可分别用不同 loss 监督 (anti-pattern #11/#24 prevention)

**MonotonicQuantileHead 增量编码:**
- q10 = q50 − softplus(δ_low), q90 = q50 + softplus(δ_high)
- 自动保证 q10 ≤ q50 ≤ q90 (单调性 essential for trading view)

### 1.2 utility_rank α=0 (anti-pattern #21 RECTIFICATION)

经典 utility_rank loss (PEPNet KDD 2023):
```
u(q50, α) = (1 − exp(−α·q50))/α  if α>0  else  q50  (α=0 limit)
L_rank = −E[(u_i − u_j) · sign(y_i − y_j)]  (pairwise)
```

**为什么 α=0 (我们的选择):**
- α=1 让 utility = 1−exp(−q50) → 对负 q50 punishes 重, 推 q50 偏负 (calibration bias)
- α=0 让 u = q50 直接, 无 sign bias → bin-plot 干净过零
- 关键代价: α=0 削弱"风险厌恶"语义但 calibration 优先 ([[v5_alpha0_huber_winner_2026_05_05]])

### 1.3 Plain Huber (w_wrong=0, w_extreme=0) — anti-pattern #20 fix

直觉: `dir_huber` 是 sign-asymmetric Huber:
```
L = Huber(q50 − y) × {w_wrong if sign(q50) ≠ sign(y), w_extreme if |y| > threshold, 1 else}
```

**Anti-pattern: w_wrong > 0 + 低 SNR ⟹ σ collapse**
- sign(0) = 0 in PyTorch → 模型预测 q50 ≡ 0 完全规避 "wrong" penalty
- σŷ → 0, prediction variance collapse, IC nonsense

**Fix: w_wrong = 0 (plain Huber)** — 失去 sign-emphasis 但保持 σ 稳定。

### 1.4 FiLM (Feature-wise Linear Modulation)

Perez et al. 2018: per-feature affine modulation from external context:
```
h' = γ ⊙ h + β
γ = MLP_γ(regime_context),  β = MLP_β(regime_context)
```

**Identity-init for safe training:**
- Zero-init γ_proj.weight + γ_proj.bias → γ = 0 + 1.0 = 1.0 (identity scale)
- Zero-init β_proj.weight + β_proj.bias → β = 0.0 (no shift)
- 模型学到 deviation from baseline 而非从随机开始

**REG_arch innovation (Track REG_arch 2026-05-14):**
3 stages of FiLM gates:
- After Conformer block 1: regime ⟹ γ₁, β₁ on (B, T, d_model)
- After Conformer block 2: regime ⟹ γ₂, β₂
- After final pool (h_pred): regime ⟹ γ₃, β₃

**Why multi-stage > single-stage PPNet:**
- Single-stage gate (旧 PPNet) 只在 final pool 调制, regime info 没传到 backbone intermediate representations
- Multi-stage FiLM 让 Conformer 在每一层都看到 regime → 学到 regime-aware features (not just regime-aware decisions)

### 1.5 Tail-focal BCE (Track T innovation 2026-05-14)

BCE on `sign_logit` with weight:
```
weight(y) = clip(|y|/σ_y, 0.3, 3.0)^1.5
```

- 弱 |y| (~0.3σ) sample: BCE 权重 0.3^1.5 ≈ 0.16
- 强 |y| (~3σ) sample: BCE 权重 3^1.5 ≈ 5.2
- 中间线性插值

**Theory:** 弱 |y| sample 的 direction prediction inherently noisy (即使最优 model 准确率也接近 50%); 强 |y| sample 的 direction more determined. Focal weight 让 model 集中精力到可学的子集.

**Anti-pattern protection (#12):** 这是 AUXILIARY (与原 pinball/utility/Huber 共存), 不 REPLACE → 不引发 P/S 分歧 (anti-pattern #12 警告 focal weight=2 REPLACE 才危险).

### 1.6 Mag-focal Huber AUX (Track P3 innovation 2026-05-13)

```
L_mag = Huber(magnitude_abs - |y|) × clip(|y|/σ_y, 0.3, 3.0)
```

监督 `magnitude_abs` head 直接学 |y|, 与 sign 解耦.

**Why work:** DAQH 把 q50 = tanh×softplus 拆分后, magnitude_abs 是独立 head. 加 focal Huber 在 |y| 上 → model 学到 confident magnitude prediction, σŷ 上升.

### 1.7 Ensemble value-blend (NOT rank-blend) — anti-pattern #16

```
ŷ_ensemble = Σ_i w_i · ŷ_i  (in bps space)
```

**NOT:**
```
ŷ_ensemble = Σ_i w_i · rank(ŷ_i)  (rank-blend BAD)
```

Rank-blend 人为 inflates σŷ (rank uniform [0,1] vs original sparse) → β-calibration 失真. β might appear =1 but trading slope wrong.

**Live calibration (production hygiene):**
- Causal EMA-demean: `q50_live = q50 − EMA(q50_lag1, α=0.01)`
- 移除 q50 的 DC drift
- 不改变 cov(y, q50) (只 shift) → 不影响 Pearson, 但改善 bias
- Warmup 50 samples (early predictions zeroed out)

### 1.8 σ-gate BEST checkpoint (anti-pattern #24 fix)

Trainer 选 BEST 时硬过滤 `σŷ/σy ≥ 0.02`:
- 早期 epoch σŷ ≈ 0.001 (model 初始化 noise) — random correlation with y could give spurious high P
- σ-gate 拒绝 init-stage epoch 作 BEST → 必须 model 真 learn 到 σ_ŷ ≥ 0.02 后才合格

### 1.9 Bayes ceiling (Cauchy-Schwarz upper)

ρ(ŷ, y) = cov(ŷ, y) / (σŷ · σy) ≤ 1 (Cauchy-Schwarz).

**In low-SNR (σ_signal ≪ σ_target):**
- 假设 y = s + ε with ε ⊥ s, σ_ε ≈ σ_y
- 最优 estimator: ŷ = s (in the limit)
- ρ_optimal = σ_s / σ_y

**实际意义:** P=0.066 ≈ σŷ/σy=0.057 → REG_arch 已 extract ŷ 上几乎所有 cov given its σŷ. 要 P=0.08 必须先 σŷ/σy 上 0.08+.

### 1.10 Channel addition penalty (新发现 2026-05-15)

Empirical: 加 4 X channels 到 input → consistent -0.013 P 代价 (v6b/v7/v8 三 NEG 实验同向):

| 加什么 channels | Test P | Gap |
|:---|:---:|:---:|
| baseline (none) | +0.0649 | 0 |
| day-level y stats | +0.0527 | -0.012 |
| intraday regime context | +0.0518 | -0.013 |
| microprice trajectory | +0.0491 | -0.016 |

**Mechanism hypothesis:** RevIN affine + input_proj weight matrix 加 4 列 → 在 low-SNR 上 gradient noise 反向破坏 working 64-channel representation.

**Rule (硬约束):** 加 channel 必须每 channel 带 ≥+0.003 alpha 才能 net positive. 否则改 REPLACE / re-weight / architecture without addition.

---

## 2. Iteration Path — 时间顺序与每一步 rationale

### Step 1: V4 baseline → V5 (2026-04 之前, anti-pattern #8 V5-LH 失败教训)

**V4** (产品-验证): Conformer + GDCN + MaskNet + RevIN, n_features=64, train_days=400, 单一 horizon. y_180 P=+0.094, y_600 P=+0.058 (3-fold pool).

**V5-LH 尝试** (FAIL, anti-pattern #8): 加深 architecture, multi-resolution pyramid backbone, y_600 = 0.01 (worse than V4). Variance collapse.

**Lesson:** y_600 不是 V4 的 architecture 问题, 是 horizon noise integration 问题. Stop chasing architecture innovation without baseline parity.

### Step 2: V5 SINGH α=0+Huber (2026-05-05) 单模 production baseline

**配置:**
- Conformer 2 blocks, d_model=32, kernel=15
- DAQH + MonotonicQuantileHead (单模 q10/q50/q90 + DC sign-mag decomp)
- 单 PPNet gate (post-pool regime modulation)
- Loss:
  - lambda_quantile = 0.10 (pinball)
  - lambda_utility_rank = 0.50, α=0 (anti #21 RECTIFICATION)
  - lambda_dir_huber = 0.50, w_wrong=0, w_extreme=0 (anti #20 plain Huber)
  - lambda_cls = 0.10 (BCE on sign_logit, sigmoid weight mode)
  - lambda_mag_focal_huber = 0.30 (sigmoid weight)
- train_days=700, val_days=60, test_days=90
- batch=1024, lr=6e-4 cosine, dropout=0.20, patience=4
- σ-gate BEST (anti #24), composite metric (P+S)/2

**Result:** Pool P=+0.0589, S=+0.0661, β=+1.01, σŷ/σy=0.058 — 当时 production.

**Rationale:** α=0 + plain Huber 是 mechanism-grounded surgical fix on α=1 calibration bias + dir_huber σ collapse (anti-pattern #20+#21). 这个 config 通过 ~3 周 careful loss design 形成的 stable local optimum.

### Step 3: Track A (DAQH + TV) 2026-05-13 — 多模 ensemble 起点

**Hypothesis:** TV (time-varying) overlay 14 channels 是 alpha 信号 (sv_ewm/apb/ofi/depth_imbalance 等), 注入 X 应增 ρ.

**配置:** V5 SINGH + DAQH 优先开 (`use_direction_aware_head=true`) + TV overlay path 配置.

**重要发现 (2026-05-15 audit):** main() training path 实际**不 wire** tv_overlay_dir. n_features = 64 in saved ckpts. **TV overlay 实际上 NEVER 加载过.** Track A 与 V5 prod 差别就是 DAQH 优先 + minor 其他.

**Result:** Pool P=+0.058 — 与 V5 prod 接近.

**Rationale 改写:** Track A 提供 ensemble diversity (corr 0.79 with V5 prod) 不是因为 TV 信号, 而是 因 DAQH+seed+train order 引起的 model trajectory 差异。这是 ensemble 真正的 value source.

### Step 4: Track P3 (P3 = "Track A + mag_focal_huber AUX") 2026-05-13

**Hypothesis:** mag_focal_huber 在 magnitude_abs head 上加权 |y|>σ tail subset, 可改善 σŷ 同时不影响 sign head.

**配置:** Track A + `lambda_mag_focal_huber=0.30` + focal weight clip(|y|/σ, 0.3, 3.0).

**Why AUXILIARY (anti #25):** 加权 ≤0.30, 不 REPLACE 原 losses → 安全.

**Result:** Pool P=+0.058, corr(P3, V5)=0.61 (diversity), corr(P3, A)=0.79.

### Step 5: 3-way ensemble (P3 + A + V5) 2026-05-13 — 首个 production ensemble

**Weights:** w_P3=0.35, w_A=0.30, w_V5=0.35 (value-blend in q50_live_bps space).

**Result:** Pool P=+0.0648, S=+0.0725, DA=0.5288, DA|y|>σ=0.5485.

**Why ensemble works:** 3 components 各自 P ≈ 0.058-0.059, 但 prediction errors orthogonal subset → blend cov(y, ŷ_ensemble) 大于单 model cov. Trader's standard practice.

### Step 6: Track T (P3 + tail-focal BCE) 2026-05-14 — DA-focused

**Hypothesis:** sigmoid cls weight (default) 在 mid-|y| sample 上 BCE 信号弱; tail-focal 让 BCE concentrate on |y|>σ subset where direction more determined.

**配置:** P3 + `cls_weight_mode="tail_focal_1p5"` + `lambda_cls 0.05→0.10`.

**Result:**
- standalone DA|y|>σ = 0.5473 (highest single track)
- 4-way DA-opt ensemble (T+P3+V5, A drops): P=+0.0630 DA|y|>σ=**0.5539**
- Pareto trade vs 3-way P-opt: -0.002 P, +0.005 DA|y|>σ

### Step 7: Track REG_arch (FiLM γ+β multi-stage) 2026-05-14 — 架构突破

**Hypothesis:** 单 PPNet gate 只在 final pool 调制, regime info 没传到 backbone intermediate representations. FiLM γ+β 多阶段让 regime 注入到 Conformer 每个 block 之后.

**配置:** Track T baseline + `use_film_multistage=true`.
- 3 FiLM gates created in `__init__`:
  - film_gate_block1, film_gate_block2 (broadcast over T)
  - film_gate_final (post-pool, 2D)
- Identity init: γ→1, β→0
- Backbone forced `return_sequence=True` so we can iterate blocks manually

**改动 (model code):** Manual iteration through `self.backbone.blocks`:
```python
for i, blk in enumerate(self.backbone.blocks):
    h = blk(h)
    if i == 0: h = self.film_gate_block1(h, regime_prior)
    elif i == 1: h = self.film_gate_block2(h, regime_prior)
# pool
h_pred = h[:, -1, :]
h_pred = self.film_gate_final(h_pred, regime_prior)
```

**Result:**
- **Standalone Pool P=+0.0646** (highest single model!)
- 比 V5 prod +0.0058 (10% relative lift)

**Rationale:** Multi-stage gate 让 backbone 能 condition 中间 representations on regime, not just final adapter. 这是 anti-pattern #21 mechanism analysis 后, structural-fix rather than post-hoc patch.

### Step 8: 5-way ensemble (REG_arch+P3+A+V5) 2026-05-14 — 当前 production

**Weights:** w_REG=0.40, w_P3=0.20, w_A=0.15, w_V5=0.25.

**Result (authoritative recompute from CSV):**
- Pool P = **+0.0667**, S = **+0.0733**
- β (y on ŷ) = +1.17 (略高 ideal 1.0, 但 trading-side 可后处理 shrink)
- σŷ/σy = 0.057 (≈ P, Bayes ceiling)
- DA pool = 0.5310, DA|y|>σ = 0.5522 (tradeable subset)

**Pareto vs 3-way / 4-way:** Pareto 干净胜 (P/S/DA 全升 vs 3-way; DA|y|>σ 比 4-way 略低 -0.002 但 P 高 +0.0037).

### Step 9-15: NEG iterations (2026-05-14 PM → 2026-05-15) — exhausted single-axis

| Step | Track | Axis | Pool P | Mechanism failure |
|---:|:---|:---|:---:|:---|
| 9 | v3 cross-attn regime gate | Architecture: gate expressiveness | aborted ep5 P=+0.031 | cross-attn 容量远超 6-dim regime info, low-SNR 收敛慢 |
| 10 | v4 deeper Conformer (3-block + 4 FiLM) | Architecture: backbone depth | aborted ep7 P=+0.028 β=+0.58 | +25% params + 6-dim regime 不变 → 4 FiLM 竞争同 input → ep 7 β crash |
| 11 | v5 seq direction BCE @ 6 anchors | Loss: deep supervision | aborted ep5 P=+0.027 | per-timestep direction BCE 污染 backbone (anti-pattern 候选 #27) |
| 12 | v6a deeper FiLM trunk | Architecture: gate non-linearity | aborted ep7 β crash | 同 v4 pattern, 6-dim regime 不变就没用 |
| 13 | v6b day-level y stats | Data: regime context (day-level constant) | pool P=+0.049 -0.018 | trained out clean, 但 standalone NEG + ensemble blend incremental +0.0004 noise |
| 14 | v7 intraday regime overlay | Data: regime context (per-timestep) | pool P=+0.052 -0.013 | 4 channel addition penalty |
| 15 | v8 microprice trajectory | Data: alpha mechanism (per-timestep) | pool P=+0.049 -0.016 | 4 channel addition penalty (强化 Step 13 pattern) |

**联合诊断 (2026-05-15):** v6b/v7/v8 三个不同 content 的 4-channel additions 都 ~-0.013 P penalty. **Channel addition has intrinsic cost regardless of content.** New rule: 不再 add channels; 只 REPLACE / re-weight / architecture without addition.

### Step 16 (current): Track A1 SE-block (running) — bottom-up no-add

**Hypothesis:** 既然加 channel 有 penalty, 不加 dim 而 re-weight 现有 64 channels per-sample.

**配置:** REG_arch + Squeeze-Excitation block on X input (Hu 2018):
- Squeeze: avg(X over T) → (B, 64)
- Excitation: MLP(64→16→64) + sigmoid → (B, 64) per-sample channel gates ∈ [0, 1]
- Scale: X *= gate.unsqueeze(1)
- Identity init: bias_init=+5 → sigmoid(5)=0.993 (near-identity start)

**Currently training (fold 0).** Decision criteria same as previous NEG: ep 5 P<0.045 + EMA P<0.045 → abort.

---

## 3. Anti-patterns 总览 (from CLAUDE.md + 新 discover)

### Loss 设计 anti-patterns

| # | Anti-pattern | Mechanism |
|:---:|:---|:---|
| #10 | Multi-loss UNIT weighting | 梯度冲突 → σ collapse |
| #12 | Tail-focal REPLACE in low-SNR | P/S 分歧 |
| #15 | Direct rank loss REPLACE | val→test drift |
| #20 | dir_huber w_wrong>0 | sign(0)=0 attractor → σ=0 |
| #21 | utility_rank α=1 + softplus | q50 negative bias |
| #25 | Mag-focal AUXILIARY | safe (vs REPLACE which is risky) |

### 架构 anti-patterns

| # | Anti-pattern | Mechanism |
|:---:|:---|:---|
| #2 | stride < horizon | label leakage |
| #5 | params/sample > 1:5 | overfit |
| #11 | Variance collapse | σŷ/σy < 0.20 reject |
| #22 | MRP replace last-token | dilutes attention |
| #23 | Decoupled (2σ−1)×softplus head | low-SNR multiplicative attractor |
| #24 | σ-gate BEST checkpoint | TV channels non-zero mean cause init noise BEST |
| #26 | Causal indicator ≠ stratified | future-conditional metric not transferable |

### 评估 anti-patterns

| # | Anti-pattern | Mechanism |
|:---:|:---|:---|
| #6 | Test 错 slice | val→test divergence |
| #14 | 单 fold / 单 seed | conclusion 不稳 |
| #16 | β measurement | rank-blend inflates σŷ |
| #17 | Baseline anchor discipline | mis-reference → wasted compute |
| #18 | Label engineering on raw y | smoothing 循环论证 |
| #19 | Eval methodology consistency | scale/stride/origin/source 4-axis |

### Multi-axis anti-patterns

| # | Anti-pattern | Mechanism |
|:---:|:---|:---|
| #13 | learnable scalar α (σ-anchor) | val→test drift |
| Track R style | multi-axis simultaneous change | 责任不可分离 |

### 2026-05-15 新发现

| # (proposed) | Anti-pattern | Mechanism |
|:---:|:---|:---|
| #27 | per-timestep deep supervision BCE | pollutes backbone, β=+0.82 < 1 |
| #28 | Stack FiLM + TV-FiLM gates | double modulation nested gradient noise |
| #29 | Channel addition penalty | +4 X channels ≈ -0.013 P regardless of content |

---

## 4. 当前 best 完整 spec (2026-05-15 production)

### 4.1 Inputs

**X (B, 600, 64) — 64 hand-crafted microstructure features:**
- 0-2: log_return_1s/5s/30s
- 3-4: spread_bps, spread_change
- 5-9: obi_L1/L5/L10/L25, obi_L1_delta
- 10-14: bid/ask depth L5/L25, depth_ratio_L5
- 15-17: weighted_price_bid/ask_L10, price_pressure
- 18-20: realized_vol_30s/60s/300s
- 21-35: depth_flow_ratio_30s, bid/ask slope+concentration, bid/ask amt ratio L0-L4
- 36-37: second_of_day_sin/cos
- 38-42: delta_bid_depth_L5, delta_ask_depth_L5, net_order_flow_L5, delta_obi_L5_5s, delta_pressure_5s
- 43-51: buy/sell_volume_1s, net_trade_flow, trade_imbalance, cumulative_net_flow 30s/300s, trade_intensity_30s, vwap_return_1s, kyle_lambda_30s
- 52-57: microprice_dev_bps, roll_spread_60s, vpin 60s/300s, book_pressure_imbalance, price_impact_30s
- 58-63: ridge-informed (net_flow_x_spread, net_flow_x_vol, obi_L5_rank_1h, net_flow_rank_1h, large_trade_arrival_60s, book_pressure_delta_60s)

**注**: `tv_overlay_dir` in REG_arch config 是 dead config — main() training path 不 wire (验证 via ckpt input_proj.weight=(32,64)).

**X_raw (B, 600, 25, 4):** 25-level LOB tensor — [bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt] per level.

**regime_prior (B, 6) — per-sample constant:**
1. vol_1h (1h rolling vol of log_return_1s)
2. spread_mean_1h
3. obi_trend_1h (1h OBI L5 linear slope)
4. price_return_6h
5. hour_sin
6. hour_cos

### 4.2 Architecture (REG_arch, 118,452 params)

- **RevIN normalization** (Kim 2022): input shift+scale to be regime-invariant
- **Path A** (hand-crafted features):
  - X (B, T, 64) → input_proj Linear(64, 32) → h_craft (B, T, 32)
  - GDCN (gated deep cross-network for feature interactions)
  - (MaskNet off in current config)
  - channel_mix_conv applied during fusion stage
- **Path B** (raw LOB tensor):
  - X_raw (B, T, 25, 4) → raw_encoder → h_raw (B, T, 16)
  - level_attention_pool over levels → spatial aggregation
- **Fusion:** h = concat(h_craft, h_raw) projected to (B, T, 32)
- **Conformer backbone** (2 blocks, 2 heads, kernel=15):
  - Each block: FFN (×0.5) → multi-head attention → conv module → FFN (×0.5) → norm
- **REG_arch FiLM γ+β gating:**
  - After block 1: γ₁⊙h + β₁ (regime → (B, 32) per-sample)
  - After block 2: γ₂⊙h + β₂
  - After final pool: γ₃⊙h_pred + β₃ (post-pool 2D)
- **DAQH (Direction-Aware Quantile Head):**
  - sign_logit = MLP(h_pred) → tanh ∈ [−1, 1]
  - magnitude_abs = MLP(h_pred) → softplus ∈ [0, ∞)
  - q50 = sign_logit_tanh × magnitude_abs
- **MonotonicQuantileHead:** q10 = q50 − softplus(δ_low), q90 = q50 + softplus(δ_high)

### 4.3 Loss (REG_arch dul_config)

| Component | Weight | Formula | Why |
|:---|:---:|:---|:---|
| Pinball | 0.10 | Σ_τ max(τ(y−q_τ), (τ−1)(y−q_τ)) | quantile fit |
| Utility rank (α=0) | 0.50 | pairwise rank loss with u=q50 | trading ranking (α=0 anti #21) |
| Direction Huber (plain) | 0.50 | Huber(q50, y), δ=2, w_wrong=0 | magnitude penalty without σ collapse (anti #20) |
| BCE on sign_logit (tail-focal) | 0.10 | weight=clip(\|y\|/σ,0.3,3.0)^1.5 | direction supervision on tail subset (Track T innovation) |
| Mag-focal Huber AUX | 0.30 | Huber(magnitude_abs, \|y\|) × focal_weight | magnitude head specialization (Track P3 innovation, anti #25 safe) |

**Not used (intentionally):** lambda_calib, lambda_pearson, lambda_beta_calib (anti #13), lambda_diff_spearman, lambda_crps, lambda_mean_zero, lambda_signcorr, lambda_unc, lambda_pearson_tail.

### 4.4 Training (REG_arch)

- 700d train, 60d val, 90d test (3 folds, test starts 2025-02-09 / 04-10 / 06-11)
- batch=1024, lr=6e-4 cosine warmup+decay
- weight_decay=0.001, dropout=0.20, patience=4
- EMA (decay=0.999), val_metric = composite (0.5·P + 0.5·S)
- **σ-gate BEST selection** (σŷ/σy ≥ 0.02, anti #24)

### 4.5 Ensemble (5-way value-blend)

```python
q50_ensemble_bps = (
    0.40 * q50_REG_arch_bps_live  +
    0.20 * q50_P3_bps_live         +
    0.15 * q50_A_bps_live          +
    0.25 * q50_V5_prod_bps_live
)
```

Where `_live` = causal EMA-demean'd q50 (production hygiene, anti-pattern #16-aligned).

---

## 5. Outstanding hypotheses (still to try)

按 ROI 排序 (bottom-up only per user discipline, no multi-seed):

1. **A1 SE-block channel attention** (RUNNING) — re-weight existing 64 channels per-sample
2. **A2 Skip-connection in Conformer** — restructure info flow without adding channels
3. **Channel REPLACE (not add)** — Identify weakest of 64 via Ridge ablation, replace with v8 best microprice trajectory feature. Net 0 channel change.
4. **L1 λ_pearson AUX** — direct Pearson(q50, y) maximization as aux loss (用户说 loss 最后)
5. **L2 λ_diff_spearman AUX** — soft Spearman aux
6. **L3 λ_mean_zero AUX** — anti-bias regularizer

---

## 6. Production deployment hygiene (生产层)

### 6.1 Live calibration layer

`scripts/y600_live_calibrate.py` 实现 causal EMA-demean:
- α=0.01, halflife ~70 samples
- Warmup 50 samples (predictions zeroed)
- Surgical fix for q50 DC drift

### 6.2 CSV format (供同事 backtest)

`exports/v5push_5way_ensemble_reg_arch/y600_predictions_5way_R40_P20_A15_V25.csv` 列:
- timestamp_us, datetime_utc (time index)
- fold (which test slice; 0/1/2)
- horizon_sec = 600
- mask (1 if valid sample, 0 if NaN/masked)
- y_true_logret, y_true_bps (target in log-return + bps)
- y_pred_q10_logret, y_pred_q50_logret, y_pred_q90_logret (raw quantiles)
- **y_pred_q50_bps (RAW signal — for colleague backtest)**
- y_pred_q50_bps_live (live-calibrated, EMA-demean'd)
- y_pred_q50_bps_live_ema_state (rolling EMA value, diagnostic)
- y_sigma_train_bps (per-fold σ_y for normalization context)
- warmup (True for first 50 samples of each fold)
- w_reg_arch, w_track_p3, w_track_a, w_v5_prod (ensemble weights)

### 6.3 Backtest period

**Production fold ranges:** 2025-02-09 → 2025-08-29 (3 non-overlapping 90-day folds).

**Filtered CSV for colleague backtest** (2025-04-01 → 2025-07-29): `exports/v5push_5way_ensemble_reg_arch/y600_5way_predictions_2025_04_01_to_07_29_RAW.csv` (35,085 rows, 8.6 MB).

---

## 7. 用户硬约束 (operational)

- ❌ Multi-seed ensemble (post-training trick; [[feedback_no_multi_seed_2026_05_15]])
- ❌ SWA across seeds
- ❌ Post-hoc fitting test (anti-pattern #19)
- ❌ Channel addition without ≥+0.003 alpha per channel (anti-pattern #29)
- ❌ Multi-axis simultaneous change (Track R failure)
- ❌ Single-fold / single-seed conclusion (anti-pattern #14)
- ✅ Single-axis change with mechanism rationale
- ✅ Causal + stationary + bounded features
- ✅ Identity-init friendly architecture additions
- ✅ Anti-pattern #25 AUXILIARY pattern (≤0.30 weight, original losses preserved)

---

## 8. 关键文件路径

### Memory (cross-session continuity)
- `~/.claude/projects/.../memory/v5_singh_alpha0_huber_winner_2026_05_05.md`
- `~/.claude/projects/.../memory/v5push_3way_ensemble_winner_2026_05_13.md`
- `~/.claude/projects/.../memory/v5push_5way_ensemble_reg_arch_2026_05_14.md`
- `~/.claude/projects/.../memory/feedback_v6_design_discipline_2026_05_14.md`
- `~/.claude/projects/.../memory/feedback_no_multi_seed_2026_05_15.md`
- 各 NEG memory: v3/v4/v5/v6a/v6b/v7/v8 同名 `_failed_2026_05_*.md`

### Code (model + training)
- `src/model/dual_path_model_v3.py` — main model (DAQH, FiLM gates, all flags)
- `src/model/film_gate.py` — FiLM gate impl
- `src/training/trainer_v2.py` — train loop, σ-gate BEST, all loss components
- `src/training/dul_loss.py` — pinball/utility_rank/Huber/CRPS components
- `src/training/dataset.py` — LOBDatasetV2 with all overlay loaders
- `run_pipeline_v3.py` — main entry point + flag whitelisting

### Configs (REG_arch chain)
- `configs/v5push/singh_alpha0_huber_track_reg_arch.json` — REG_arch standalone baseline

### Production exports
- `exports/v5push_5way_ensemble_reg_arch/y600_predictions_5way_R40_P20_A15_V25.csv`
- `exports/v5push_5way_ensemble_reg_arch/y600_5way_predictions_2025_04_01_to_07_29_RAW.csv`

### Docs
- `docs/V5_TO_PRODUCTION_ITERATION_2026_05_15.md` (this file)
- `docs/OVERNIGHT_BRIEF_2026_05_15.md` (most recent overnight)
- `docs/MORNING_BRIEF_2026_05_14.md` (4-way / 3-way ensemble)

---

## 9. 服务器 + 环境 (operational)

- Server: `ssh jpline` (NOT RunPod; see [[infra_server_jpline]])
- Workdir: `/mnt/storage/private/work_hsy/quant_research`
- Conda env: `hsy_v5push`
- GPU: RTX 3090 (24 GB VRAM, shared with other users)
- Data: `data/npz_v4/` (per-day NPZ, 991 days 2023-01-01 → 2025-09-30)

---

## End — living doc, append on new iterations
