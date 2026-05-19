> **创建:** 2026-05-14 23:35 UTC+8 → 持续更新到 2026-05-15 早 | **Session:** v5push autonomous overnight
> **上一版本:** docs/MORNING_BRIEF_2026_05_14.md (2026-05-14 早, 记 3-way/4-way), docs/V6_REGIME_ENHANCEMENT_DESIGN_2026_05_14.md (v6 设计)
> **状态:** in-progress (autonomous overnight queue) | **作废条件:** 2026-05-15 用户 review 后归档为 final

# Overnight Brief 2026-05-14 → 2026-05-15

## TL;DR — **5/5 NEG, REG_arch baseline 是 local optimum**

| Track | Axis | Crash? | Pool P (test) | vs REG_arch +0.066 |
|:---:|:---:|:---:|:---:|:---:|
| v3 cross-attn | gate expr | ✗ ep 5 | aborted | — |
| v4 3-block | backbone depth | ✗ ep 7 β | aborted | — |
| v5 seq-dir BCE | aux loss deep sup | ✗ ep 5 P drag | aborted | — |
| v6a deeper trunk | gate non-lin | ✗ ep 7 β | aborted | — |
| **v6b regime feats** | **data axis (d=6→12)** | **✓ clean** | **+0.0486** | **-0.0178** |

**v6b 与其他 NEG 区别**: 唯一 train 出来 stable (没 β crash), 但 pool P 仍低 -0.018. ensemble blend with REG_arch peak at w_v6b=0.10 → P=+0.0668 (incremental +0.0004 ≈ noise). corr(REG_arch, v6b) = +0.65.

**关键结论:** 在当前 (700d-train + d_model=32 + DAQH+TV+tail-focal BCE + FiLM γ+β) 配置下, REG_arch (P=+0.0664) **是 local optimum**. 增加 model capacity / gate expressiveness / aux loss / deeper trunk / regime info 都 NEG. 必须换 **正交方向** 才能突破:
1. **Multi-seed REG_arch ensemble** (历史 +0.003-0.005 P 稳 gain)
2. **Intraday regime overlay (1s tick level)** — vol_pct_30d / KER_1h / autocorr_lag10 (需 NPZ rebuild)
3. **Loss weight sweep on REG_arch** — lambda_dir_huber / lambda_utility_rank 微调
4. **Multi-horizon meta** — y_180 production P=+0.094, combined with y_600

**Production 5-way ensemble 不变** (R40/P20/A15/V25 P=+0.0667 仍最佳)

## 时间顺序事件

### 2026-05-14 22:33 UTC+8 — Abort v2 (TV-FiLM)
- v2 fold 0 P=+0.0508 vs REG_arch baseline P=+0.0649 (-0.014, -22%)
- Fold 1 ep 8 P=+0.056 仍 -0.014 落后 baseline → confirmed NEG
- Memory: `v5push_track_r_t_findings_2026_05_14.md` + 新 `v5push_v3_xattn_failed_2026_05_14.md`
- **根因:** TV-FiLM 与 REG_arch FiLM stacked 嵌套乘性 → 梯度噪声放大

### 2026-05-14 22:43 UTC+8 — Launch v3 (cross-attn regime gate)
- Config: `singh_alpha0_huber_track_reg_arch_v3.json`
- 模型 params 129,972 (+11K vs baseline)
- 设计: 4 attention heads × 4 regime tokens REPLACE FiLM γ+β
- Fold 0 epoch trajectory:
  - ep 1: P=+0.028 σŷ/σy=0.001 init noise
  - ep 2: P=+0.013 σŷ/σy=0.034 ⚠️ regression
  - ep 3: P=+0.034 σŷ/σy=0.031
  - ep 4: P=+0.034 (flat) σŷ/σy=0.041
  - ep 5: P=+0.031 (slight regress) σŷ/σy=0.030
- vs REG_arch baseline 同期 ep 5 ≈ 0.052 → gap -0.021

### 2026-05-14 22:58 UTC+8 — Abort v3
- Gap stable through 5 epochs, no breakout signal
- 根因: cross-attn 容量 (2 heads × 4 tokens × 32 d) 远超 6 维 regime info, low SNR 收敛慢
- 决策: FiLM 简单+expressive 已足够; cross-attn 是 over-engineering
- Memory: `v5push_v3_xattn_failed_2026_05_14.md` ✓ 完成

### 2026-05-14 23:23 UTC+8 — Launch v4 (deeper Conformer 3-block + 4 FiLM)
- Config: `singh_alpha0_huber_track_reg_arch_v4.json`
- 模型 params 145,780 (+27K vs baseline, +25%)
- Fold 0 trajectory (epoch P / EMA P): 1: 0.025/0.026; 2: 0.017/0.030; 3: 0.046/0.032; 4: 0.033/0.036; 5: 0.041/0.039; 6: 0.046/0.040; **7: 0.028/0.039 β crash 1.20→0.58 r²<0**

### 2026-05-15 07:08 UTC+8 — Abort v4 (NEG)
- ep 7 P regress + β collapse → trigger abort threshold (P<0.045 + EMA<0.045)
- Max P=+0.046 (ep 6), EMA P=+0.040 (ep 6) → 永不破 baseline 0.05
- 根因: +25% params 但 6-dim regime info 不变 → 4 FiLM gates 在同一 input 上竞争 oscillation
- Memory: `v5push_v4_3block_failed_2026_05_15.md` ✓
- **关键推论**: 与 v3 联合证明 bottleneck = regime input info, 不是 capacity/depth

### 2026-05-15 00:08 UTC+8 — Launch v5 (seq direction BCE @ 6 anchors)
- Config: `singh_alpha0_huber_track_reg_arch_v5.json`
- DA-targeted aux loss, uniform-weighted (vs Track T tail-focal)
- Fold 0 ep 5 P=+0.027 (worse trajectory than other variants)

### 2026-05-15 00:42 UTC+8 — Abort v5 (NEG)
- ep 5 P=+0.027 EMA P=+0.027 触发 abort
- 根因: 6 anchor BCE 在 backbone 中间 h 序列上注入 sign-only gradient, 污染 magnitude 学习; β=+0.82
- **新 anti-pattern 候选 #27**: per-timestep direction supervision (deep sup) 即使 AUXILIARY 也危险 — Track T pool-level BCE 安全, sequence-level BCE 危险
- Memory: `v5push_v5_seqdir_failed_2026_05_15.md` ✓

### 2026-05-15 00:48 UTC+8 — Launch v6a (deeper FiLM trunk)
- 手动 launch (sequencer pgrep self-match bug)
- Config: `singh_alpha0_huber_track_reg_arch_v6a.json`
- Fold 0 trajectory: ep1=0.038, ep3=0.038, ep5=0.035, ep6=0.042, ep7=0.020 β=+0.44 r²<0
- ep 7 **β crash 同 v4 pattern** → abort 09:32

### 2026-05-15 09:33 UTC+8 — Launch v6b (enhanced regime features)
- Auto-launched via kill -0 fixed sequencer (pgrep self-match issue 已解)
- Config: `singh_alpha0_huber_track_reg_arch_v6b.json`
- d_prior 6→12, 6 new daily-y-stats dims
- Fold 0: BEST ep 4 val_C=0.045 → test P=+0.0527 σŷ/σy=0.043 (gap -0.012)
- Fold 1: BEST ep 8 val_C=0.064 → test P=+0.0642 σŷ/σy=0.055 (gap -0.010)
- Fold 2: BEST ep 16 val_C=0.071 → test P=+0.0425 σŷ/σy=0.096 over-fit (gap -0.015)
- **Pool P=+0.0486** (NEG -0.018 vs REG_arch +0.0664), corr(REG_arch,v6b)=+0.649
- Memory: `v5push_v6b_regime_features_2026_05_15.md` ✓
- **不进入 production ensemble** (blend incremental +0.0004 ≈ noise)

### 2026-05-14 23:25-23:30 UTC+8 — 实施 v6a + v6b 设计

**v6a (deeper FiLM trunk, architecture single-axis):**
- 改动: `src/model/film_gate.py` 加 `deeper_trunk` 参数; 加 1 个 Linear+GELU+Dropout hidden layer
- 模型 params 121,620 (+3,168 vs baseline)
- Smoke PASS: 默认 flag=False → baseline REG_arch fold 0 ckpt strict-load PASS (零 missing/unexpected)
- Config: `singh_alpha0_huber_track_reg_arch_v6a.json`

**v6b (enhanced regime features, data single-axis):**
- 改动: 修复 latent bug `_compute_past_y_stat` (referenced 但未定义); 加 5 个 kinds (mean/std/sharpe/vol_mean/vol_std)
- 6 个新 dim 来自 daily y_600 stats 聚合: (30,mean), (30,std), (30,vol_mean), (30,vol_std), (7,mean), (7,vol_mean)
- d_prior 6 → 12
- Daily stats JSON: `data/v6b_daily_y_stats.json` (991 days, 86.6 KB) — built once, strictly causal aggregation
- Config: `singh_alpha0_huber_track_reg_arch_v6b.json`
- Smoke PASS: dataset returns regime_prior shape (12,) ✓

**Leakage 审计 (v6b):**
- daily_y_stats[D] 来自 day D 的 y_600 (mask=1) 仅该天
- aggregation 用 [D-N, D-1] strict 排除 D
- 训练/测试都按 sample_day 索引 → 0 future contamination

### 2026-05-14 23:30 UTC+8 — Sequencer 状态

Main chain sequencer (PID 71985): v4 → v5 → v6a → v6b 等待 (将 wait_done v4)
v6b dedicated sequencer (PID 72454): wait_done v6a → launch v6b

### 后续填充模板

#### 2026-05-15 XX:XX — v4 fold 0 完成
- v4 fold 0 ep N peak P=+X.XXXX, σŷ/σy=X.XXX
- vs REG_arch baseline fold 0 P=+0.0649 → Δ?
- 决策: ✓ continue / ✗ abort + 跳 v5

#### 2026-05-15 XX:XX — v5 (seq direction BCE) 启动 / 结果
- ...

#### 2026-05-15 XX:XX — v6a 结果
- Pool 3-fold P/S/DA/DA|y|>σ
- vs REG_arch baseline pool (P=0.0646)

#### 2026-05-15 XX:XX — v6b 结果
- Pool 3-fold P/S/DA/DA|y|>σ
- vs REG_arch baseline pool
- 关键: 6 new regime dim 是否提升 mid/lo regime?

## 待用户 review 决策项 (morning)

1. 哪个 track (v4/v5/v6a/v6b) 进入 production ensemble?
2. ensemble weight 是否要 sweep (current 5-way 是 heuristic R40/P20/A15/V25)?
3. 下一步路径: 继续 v7+ 单 axis (Multi-asset ETH? Funding rate? Online retraining?)
