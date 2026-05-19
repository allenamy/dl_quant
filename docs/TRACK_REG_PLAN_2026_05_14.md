> **创建:** 2026-05-14 07:55 UTC+8 | **Session:** track-reg-arch-feat-loss-sequential | **关键事件:** Track R (3-axis combined) NULL 教训后, 改为 3 个 single-axis tracks. Track REG_arch 已 launched.
> **上一版本:** docs/TRACK_R_PLAN_2026_05_13.md (3-axis combined, NULL)
> **状态:** in-progress | **作废条件:** 3 tracks 全 finish + final ensemble report

# Track REG 计划 — 3 个独立 single-axis ablation

## 目标 (不变)
- Pool P 0.07+
- β slope ~1
- bias low
- monotonic calibration
- DA 0.58+

## 当前 baseline (LOCK)
- **P-opt**: 3-way (P3+A+V5 0.35/0.30/0.35), P=+0.0648 S=+0.0725 β=+1.10 DA=0.5288 DA|y|>σ=0.5485 — `exports/v5push_3way_ensemble_p3_a_v5/...`
- **DA-opt**: 4-way (T+P3+V5 0.40/0.35/0.25, A drops), P=+0.0630 DA|y|>σ=0.5539 — `exports/v5push_da_optimal_4way_t_p3_v5/y600_predictions_da_optimal.csv`

## 验证过 working 的点 (按时间顺序)
1. **DAQH structural head** (sign + magnitude 解耦, anti-pattern #23 后保留 tanh×softplus structure 不动)
2. **TV overlay** time-varying channels (v1 8ch validated, v2 14ch validated)
3. **Magnitude focal Huber as AUXILIARY** (λ=0.30 on DAQH magnitude_abs, anti-pattern #25 — ADD safe, REPLACE危险)
4. **Tail-focal BCE** (cls_weight_mode=tail_focal_1p5, λ_cls=0.10, Track T) — DA|y|>σ +0.005
5. **σ-gate trainer fix** (BEST checkpoint requires σŷ/σy ≥ 0.02, anti-pattern #24)
6. **Value-blend ensemble** (3-way / 4-way, diversity matters)

## 验证过 NOT working (反复教训)
- MRP (multi-resolution pool, anti-pattern #22)
- Decoupled (2σ-1)×softplus head (anti-pattern #23)
- `lambda_beta_calib` 直接 loss (anti-pattern candidate from Track R — 反向推 σ_ŷ)
- TV v3 长程 RV (rv_1h/4h/24h, with β-calib combined — 不可分离)
- GLU fusion 单独贡献 (Track R 多轴混合无法归因)

## 3 个 single-axis 实验

### Track REG_arch (running): FiLM γ+β multi-stage gating
- 替换 single-stage PPNetGate (γ-only) with **3 FiLM gates** (γ scale + β shift)
- Stage 1: after Conformer block 1
- Stage 2: after Conformer block 2  
- Stage 3: after pool (replaces PPNet, mutually exclusive)
- Init: γ→1.0, β→0.0 (identity start, learn only when useful)
- 理论: FiLM (Perez 2018) strictly more expressive than γ-only; multi-stage 让 regime info 影响 intermediate representations 而不只是 output adapter
- Cost: +~7K params (3 × ~2.3K each)
- 期望: +0.003-0.008 P, +0.003-0.005 DA over Track T baseline

### Track REG_feat (queued): TV v4 = TV v2 + 5 theory-motivated channels
1. **hawkes_intensity_60s**: Σ exp(-(t-t_i)/τ), τ=60s — self-exciting trade cluster intensity (Bacry-Muzy)
2. **kyle_lambda_60s**: |Δmid_bps|/(|signed_vol|+1) EWMA, hl=60s — price impact / liquidity (Kyle 1985)
3. **obi_bid_kurtosis**: kurtosis of bid_amt across 25 levels — depth concentration shape
4. **hour_sin**: sin(2π × hour_of_day / 24) — 24h cycle (Asia/US trading hours)
5. **day_sin**: sin(2π × day_of_week / 7) — weekly cycle (weekend low vol)
- Cost: +5 input channels at TV; input_proj +160 params
- 期望: low-vol regime P 改进 (transferable causal indicators, vs Track R rv_1h failed)

### Track REG_loss (queued): magnitude-conditional Pearson loss
- `lambda_pearson_tail=0.10` AUXILIARY
- 计算: `Pearson(q50[|y|>σ_y], y[|y|>σ_y])`, loss = (1 − corr)
- 理论: pool P 由 tail subset cov 主导, 直接最大化 tail Pearson = 直接 push pool P
- 不 REPLACE 原 loss (anti-pattern #15/#12 教训)
- Cost: 0 params, 1 loss term
- 期望: +0.005-0.010 P (最直接的 P-attack)

## 关键设计原则 (避免 Track R 教训)
- **单轴改动**: 每个 track 只改一个 axis. 多轴混合 (Track R) 无法归因.
- **AUXILIARY 而非 REPLACE**: 所有改动添加在 Track T baseline 之上, 原 loss/heads 不动.
- **逐个验证**: REG_arch 完成后才 launch REG_feat. 通过 sequencer 串行.
- **诚实接受 NULL**: 若某 track 失败 reject. 不强行加进 ensemble.

## 时间表 (sequential)
- 07:53: REG_arch launched
- ~11:30: REG_arch finish (3 folds × 70min)
- ~11:30 (parallel): TV v4 build 完成
- ~11:30: REG_feat launch
- ~15:00: REG_feat finish
- ~15:00: REG_loss launch
- ~18:30: REG_loss finish
- ~19:00: Final 6-way ensemble sweep + 报告

## 评估 protocol (per Track)
- 用 `scripts/v5push_track_eval.py` 3-fold pool + live-cal
- 与 Track T standalone 对比 (single axis 贡献)
- 加入 ensemble sweep — 检查 diversity benefit

## 失败标准 (避免 sunk cost)
- Standalone P < Track T - 0.005 AND ensemble wT=0 → REJECT
- σŷ/σy < 0.04 → σ collapse, REJECT
- 否则保留作 ensemble candidate
