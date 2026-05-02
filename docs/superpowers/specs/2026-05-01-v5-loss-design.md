# V5 损失子方向设计 (2026-05-01)

> **创建:** 2026-05-01 16:30 UTC+8 | **Session:** v5-loss-exploration
> **关键事件:** y_600 production 已交付 (baseline_plus EMA/SWA),探索 loss 改进作为下一步突破方向。
> **状态:** in-progress (设计 + 本地 smoke test 阶段) | **作废条件:** pod 训练验证完成后归档为 final 或 reject

## 目标

设计独立的 V5 损失探索分支,验证 3 个候选改进点能否突破 baseline_plus 的 dense raw P=0.050 上限,而不影响 V4 production 框架。

## 改进点(优先级降序)

### 1. Vol-adaptive label normalization
**问题**: V4 用 fold-static σ_train (≈ 9.5 bps),无法响应 vol regime 切换。high-vol 段实际 σ_local ≈ 30 bps,模型 ŷ magnitude 锁死在 σ_train 标度,**无法在高 vol 时放大 trade size**。

**机制**:
```
σ_local[t] = MAD(returns[t-720..t-1])    # 仅过去 720 条,严格无 look-ahead
y_normed[t] = y[t] / σ_local[t]          # 局部 z-score
推理: ŷ_raw = ŷ_z × σ_local              # 自动伸缩
```

**预期收益**: regime-stratified 显示 high-vol IC=0.075 (低 vol 0.035),adapt 后 high-vol PnL 应能放大 ~2×。

**风险**: σ_local 估计偏差 → ŷ_raw 偏差累计;train/test σ_local 分布漂移 → magnitude 不 transfer。

### 2. Dual-head 解耦(direction + magnitude)
**问题**: 单 q50 head 同时承担 direction + magnitude,低 SNR 下两者都被 shrink。bin-plot 显示 b8 (y=+25 bps) ŷ_mean=-0.08 bps。

**机制**:
```
dir_logit = head_dir(emb)        # 任意实数,sign 决定方向
mag_pre = head_mag(emb)
mag = softplus(mag_pre)          # ≥ 0
ŷ = tanh(dir_logit) × mag        # soft sign × magnitude
```

**Loss 三件套** (避免 ESMM-style 概率乘法的误差累计):
```
loss_dir = softplus(-y × dir_logit).mean()  # margin loss,鼓励同号
loss_mag = SmoothL1(|y|, mag, β=δ)          # Huber on |y|
loss_joint = MSE(ŷ, y)                       # 端到端校准两 head 的乘积
total = loss_dir + 0.5 loss_mag + 0.5 loss_joint
```

**关键**: `loss_joint` 强制端到端 calibration,**消除独立训练的 bias 累计**(这是与 ESMM 不同的关键 — ESMM 没有 joint 项)。

**预期收益**: |y| 比 y 信号强(R² 可能 0.05-0.10 vs y 0.002),decouple 后 mag head 更易训。

**风险**: 过 head 可能 overfit train,joint loss 权重 tune 不当会让 dir/mag 一边倒。

### 3. Cross-sectional IC loss (multi-asset hook)
**问题**: 当前单 asset (S=1),CS-IC loss 不可用。但要为多 asset 留口子。

**机制**:
```
shape: (B, T, S, H)
if S < 2: return 0   # 自动 noop,不影响 single asset
else: per-(B, T, H) demean across S, compute Pearson, loss = 1 - mean(ic)
```

**预期收益**: 单 asset 时无效;后续多 asset 时可拉 IC-IR 1.5+(per CLAUDE.md 突破方向)。

**风险**: 单 asset 时纯 dead code,但开销可忽略。

## 不在范围

- ❌ 修改 V4 production 任何文件 (`src/training/dataset.py`, `src/training/trainer_v2.py`, `src/training/dul_loss.py`, `src/training/losses.py`)
- ❌ 修改 baseline_plus / phase3c configs
- ❌ 触碰 production CSV (`exports/y600_*_3seed_median.csv`)
- ❌ Replace utility_rank with diff_spearman (anti-pattern #15 explicitly forbids)
- ❌ Tail-focal loss (anti-pattern #12 P/S divergence)
- ❌ σ-anchor learnable scalar (anti-pattern #13 catastrophic drift)

## 文件结构(全部新建,不动 V4)

```
src/training/v5_losses/
  __init__.py                 # 包标识
  vol_adaptive.py             # σ_local computation (numpy, offline-deterministic)
  dual_head.py                # DualHead nn.Module
  components.py               # loss 函数集合 (dir_margin, mag_huber, joint_mse, cs_ic)
  loss_assembly.py            # 配置驱动的 loss 组装

scripts/
  v5_loss_smoke_test.py       # 本地 smoke test (无需 pod, 无需 npz)

docs/superpowers/specs/
  2026-05-01-v5-loss-design.md  # 本文件
```

## 实施阶段

### Phase 0: 设计 + 本地 smoke test (现在)
- 写 spec (本文件) + 4 个 v5_losses 模块
- 写 smoke test:合成数据,验证 forward/backward/grad 正常,loss 不 NaN
- 试一个 toy training loop (1000 epochs on synthetic y=sign(x1)|x2|+noise) 看 dual head 能否恢复 ground truth
- **不依赖 data/npz_v4 / pipeline_v3 / pod**

### Phase 1: Pod 端 NPZ 升级 (待开 pod)
- 修改 `data/npz_v4_v5/` (新目录,不覆盖 npz_v4) — 加 `sigma_local` 字段
- 写 `scripts/build_v5_npz_overlay.py`:从 npz_v4 读 timestamps + mid_returns,算 σ_local,新 npz 只存 `sigma_local`
- 验证: σ_local 分布合理 (4-30 bps range, no NaN/inf, no look-ahead)

### Phase 2: V5 Trainer (新文件,不动 trainer_v2)
- `src/training/trainer_v5.py` — 复用 V4 model,加 dual head 替换 q50 head,使用 v5_losses
- Config: `configs/y600_v5_loss/dual_head_voladapt.json`
- Fold-0 single-seed screen (50 min on pod) → 出 IC + bin plot
- 比较 baseline_plus EMA fold-0 raw P 0.044 → V5 fold-0 raw P 是否 ≥ +0.005

### Phase 3: 验证或 retract
- 如 Phase 2 ΔP ≥ +0.005 + bin 单调性更好 + DirAcc_tail ≥ 0.55 → multi-seed × 3-fold 验证
- 否则 reject,记录 anti-pattern,V4 production 不变

## 验证 gate (anti-pattern #17)

每个 phase 必须满足才进入下一 phase:

- **Phase 0 → Phase 1**: smoke test 全部通过,toy training loop 在合成数据上 P > 0.5
- **Phase 1 → Phase 2**: σ_local 在 train 段分布 sane (median 5-15 bps), no future leak
- **Phase 2 → Phase 3**: V5 fold-0 raw P ≥ baseline_plus EMA fold-0 raw P + 0.005 (=0.049+),且 σŷ/σy ≥ 0.04 (无 variance collapse)
- **Phase 3 (final)**: V5 multi-seed pooled raw P ≥ baseline_plus EMA pooled raw P + 0.005 (= 0.055+),且 95% CI 不含 0

## 与 anti-pattern 一致性核对

- ✅ #11 (variance collapse): 监控 σŷ/σy ≥ 0.04
- ✅ #12 (tail-focal P/S 分歧): 不用 tail-focal,改 Huber + joint MSE
- ✅ #13 (σ-anchor val drift): vol-adaptive 用 batch-statistics (rolling MAD from past),非 free Parameter
- ✅ #14 (multi-seed 不可省): Phase 3 必须 multi-seed
- ✅ #15 (diff_spearman replace risk): 不 replace utility_rank,可考虑 ADD 弱 weight
- ✅ #16 (β measurement): 报告 β_y_on_ŷ 同时报 σ_ŷ/σ_y
- ✅ #17 (anchor discipline): Phase 0/1/2/3 gate 已显式给出
- ✅ #18 (raw eval): 全部 evaluation 在 raw y_600 上 (test_preds.npz 的 targets 仅供 sanity, 不作为 ground truth)
- ✅ #19 (methodology consistency): 用 dense + per-fold-aware breakdown + raw

## 时间预算

- Phase 0: 2-3h (今天)
- Phase 1: 8h pod (NPZ rebuild)
- Phase 2: 6-8h pod (3 single-fold screens)
- Phase 3: 18h pod (3-seed × 3-fold 完整 train + eval + report)
- **总计 pod: ~32-34h**(分多次开 pod 摊销)

## 失败时的清理

- V5 完全独立目录 `src/training/v5_losses/`, `data/npz_v4_v5/`, `experiments/y600_v5_*/`
- 失败时直接 `git rm -r src/training/v5_losses/ data/npz_v4_v5/` + 删 v5_loss configs
- V4 框架与 production CSV 0 影响

## 后续扩展(out of scope, 留 hook)

- Multi-asset support: dual head 输出已带 S 维度,加 ETH/SOL 时只需 dataset 改
- 渐进训练 (warm-up dir → mag → joint): 在 trainer_v5 留 schedule 钩子
- Per-symbol embedding: dual head 设计时已支持 symbol_id input(未启用)
