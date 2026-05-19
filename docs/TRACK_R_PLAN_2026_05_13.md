> **创建:** 2026-05-13 22:35 UTC+8 | **Session:** v5push-track-r-end-to-end-optimization | **关键事件:** Track Q v2 完成 (low vol stratified +12% conditional, 不可交易), regime-aware blend +0.004 P; user directive: 端到端 features+fusion+loss+architecture 不停迭代
> **上一版本:** docs/V5PUSH_OVERNIGHT_BRIEF_2026_05_13.md (3-way ensemble 完整范式)
> **状态:** in-progress | **作废条件:** Track R 完成且 ablation 后用 Track R_final 报告取代

# Track R: 端到端综合优化计划

## 目标 (用户 hard requirements)
- **P** 0.07-0.08+ (越高越好) — 当前 3-way ensemble 0.0645, gap -0.005-0.015
- **β slope** 接近 1 — 当前 1.10 ✓
- **No long-short bias** — bias_bps 接近 0
- **Trading view & calibration view** 单调良好过原点

## 当前 baseline (LOCK 不动)
- CSV: `exports/v5push_3way_ensemble_p3_a_v5/y600_predictions_3way_p3_35_a_30_v5_35.csv`
- Pool: P=+0.0645 S=+0.0723 β=+1.10 σŷ/σy=0.058 DA=0.5288 DA|y|>σ=0.5485 BinMono=+0.988

## Track R combo (3-axis 同时改, 1 个 training run)

### Axis 1: Feature — 长程 RV 通道补 regime info
**问题**: 现有 TV channels 时间尺度最长 300s (5 min), 缺少 1h+ 时间尺度的 regime indicator. PPNetGate 用 regime_prior (d=6) 但内容是短期, 没有长程 vol state.

**实现**: 在 TV v2 (14 ch) 之上加 3 个新 channels = TV v3 (17 ch):
- `rv_1h_bps2` — 1-hour realized variance of 1s mid log returns (bps²), broadcast constant across T within sample (regime indicator)
- `rv_4h_bps2` — 4-hour
- `rv_24h_bps2` — 24-hour (daily vol regime)

数据源: `data/midprice_per_day/` 上有 per-second mid 序列.

**预期 ROI**: low vol regime 真改进 (Q v2 stratified +12% 证明信号在), 长程 RV 是 transferable causal indicator (vs Q v2 的 short-term features).

### Axis 2: Fusion — GLU 替换 concat-Linear
**问题**: 当前 fusion = `concat([h_craft, h_raw]) → Linear(d_model+d_raw → d_model)` — 极简, 无 data-dependent 选择能力. Path A (hand-craft) 和 Path B (raw LOB) 信息互补但当前融合方式让 model 完全 self-discover 该如何 mix.

**实现**: 1-line config `fusion_kind: "glu"` — 已有 `src/model/gated_fusion.py` GLU implementation, 从未在 production 用过.

GLU 公式: `out = (W1·x) ⊙ sigmoid(W2·x)` — sigmoid gate per-channel 由 input 决定哪些维度激活.

**预期 ROI**: +0.005 P (数据依赖 fusion 而非静态 linear); 在低 vol 时 sigmoid 可能 down-gate noisy Path B 通道, 高 vol 时 up-gate.

### Axis 3: Loss — β-calib loss 显式拉 β→1
**问题**: 当前 β=1.10 (3-way blend) 接近 1, 但 Track Q v2 standalone β=1.05 也接近, 但 P 标准 dir_huber 训练后 β 一般偏 (Track A β=0.82, P3 β=0.87 等). β 偏离 1 = σŷ 偏离 σy = 校准缺失.

**实现**: 1-line config `lambda_beta_calib: 0.10` — 已写, 从未启用. 

β-calib loss (from `compute_dul_loss` 已实现): minimize `(β − 1)²` where β = cov(ŷ, y) / var(ŷ). 直接梯度推 σŷ → σy 与 cov 同方向.

**预期 ROI**: β 直接到 0.95-1.05, σŷ/σy 上升, P 边际 +0.002-0.005.

## 不改的 (保持 Track P3 proven baseline)
- DAQH 头 (tanh × softplus, 不 decouple — #23 教训)
- λ_dir_huber=0.50 (plain Huber on q50, w_wrong=0 — #20)
- λ_utility_rank=0.50 α=0 (#21)
- λ_cls=0.05 sigmoid weighting (#23)
- λ_mag_focal_huber=0.30 clip [0.3, 3.0] (#25 — AUXILIARY safe)
- Conformer kernel=15, 2 blocks
- Path B raw LOB encoder + level attention pool
- last-token slice (#22)

## 预期 (希望 break)
- Pool P: 0.0645 → **0.068-0.075** (+0.005-0.010)
- Pool S: 0.0723 → 0.075+
- β: 1.10 → 0.95-1.05 (更接近 1)
- DA: 0.5288 → 0.535+
- BinMono: 0.988 → 0.99+

## 验证 protocol (anti-pattern #17)
- Baseline (3-way ensemble): P=+0.0645 不动, CSV 不覆盖
- Track R 新 output_dir: `experiments/v5push/singh_track_r`
- 用 same `scripts/v5push_track_eval.py` (raw+dense+per-fold+live-cal)
- 失败 reject 不污染 baseline

## 后续 (Track R 完成后)
- Track R 单独表现 + 加入 ensemble 测试
- 若 Track R 突破: 进入 PPNet enhancement (multi-stage gating, intermediate Conformer block 后加 regime gate)
- 若 Track R 不破: 转向 patch attention pool / 长程 PPNet input 增强 / wider kernel (Track H k=31)
