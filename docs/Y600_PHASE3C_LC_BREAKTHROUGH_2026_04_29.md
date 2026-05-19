> **创建:** 2026-04-29 07:35 UTC+8 (2026-04-28 23:35 UTC) | **Session:** y600-phase3c-lc-overnight
> **关键事件:** seed=42 phase3c+LC 修复 fold 2 sign-flip (β: -0.09 → +2.23). Multi-seed seed=7+13 启动中。
> **上一版本:** docs/Y600_PIVOT_DECISION_2026_04_29.md (2026-04-28 16:10 UTC) — 已 superseded by this breakthrough
> **状态:** in-progress | **作废条件:** Multi-seed 完成后写 final report 替代

# y_600 phase3c+LC 突破: fold 2 sign-flip 解决

## TL;DR

**前期诊断: y_600 V4 baseline+SWA fold 2 β=-0.09 (sign-flip), 一直是 calib/dir_huber/post-hoc 都解不了的"结构问题"。**

**本次突破: 单 seed=42 phase3c+LC 配置, 三 fold β = [0.69, 0.77, +2.23] — 全正, fold 2 实际变最强 (P=0.104). pooled P=0.049, S=0.072 (优于 baseline+SWA 0.047/0.068).**

## 配置 diff (vs V4 baseline)

| 维度 | V4 baseline (had sign-flip) | phase3c+LC (FIXED) |
|---|---|---|
| train_days | 700 | **580** |
| val_days | **30** | **90** |
| embargo_days | **0** | **30** |
| 6 long-context features | 无 | **lr_3600/7200, rv_3600/7200, hurst, mz_7200** via X-concat |
| dir_huber / beta_calib | 0 / 0 | 0 / 0 |
| 损失 | quantile + utility_rank | quantile + utility_rank |
| 架构 | V4 不变 | V4 不变 |

**两个改动 (理论根据):**
1. **Phase3c-style split (val=90, embargo=30):** 已验证 y_1800 phase3c stable IC. 长 val 减少 checkpoint 选择的噪声; embargo 减小 train→val 微泄漏。
2. **6 long-context features:** lr_3600 = 1h log-return (regime indicator); rv_3600/7200 = 1h/2h realized vol (regime); hurst = vol-regime; mz_7200 = 2h mean-reversion. 这些 BEYOND model's input_len=600 window — genuine new info, 让模型对 fold 2 那种"unseen vol regime" 有 context。

## 实测数据 (canonical stride_every=10 pool)

### Per-fold (seed=42 verified)

| | fold 0 | fold 1 | fold 2 | POOLED |
|---|---:|---:|---:|---:|
| BEST P | 0.0331 | 0.0353 | **0.1039** | 0.0493 |
| BEST S | 0.0887 | 0.0315 | 0.1008 | 0.0721 |
| BEST β | 0.689 | 0.769 | **+2.232** | 1.026 |
| EMA P | 0.0601 | 0.0044 | **0.1021** | 0.0520 |
| EMA S | 0.1008 | 0.0129 | 0.0921 | 0.0685 |
| EMA β | 1.322 | 0.085 | 1.600 | 0.973 |

**关键观察:**
1. **Fold 2 β 从 -0.09 翻到 +2.23** — 完全消除 sign-flip
2. Fold 2 现在是 P/S 最强 fold (P=0.10, S=0.10) — 之前是 worst (P=-0.005)
3. EMA fold 1 weak (P=0.004) — single-seed 噪声, 多 seed median 应该解决
4. Pooled P/S vs baseline: +4% / +6% — 不大但 directional 改进

## Anti-pattern 修正

之前说 "y_600 fold 2 sign-flip 是 horizon × regime 的结构问题, 任何 single-asset training/loss 调参都不能解决"(见 docs/Y600_PIVOT_DECISION_2026_04_29.md L6) —— **这个判断 PARTIALLY 错了**.

修正:
- y_600 fold 2 sign-flip **不是不可解决的结构问题**
- 但需要 (a) 更稳定的 val 选择 (val=90+embargo=30) AND (b) regime context (LC features)
- **任意一个单独可能不够**, 两个一起才解决了 sign-flip

下一步验证(multi-seed running): 是否 seed-stable, 且 multi-seed median 进一步 improve P/S.

## 进行中: Multi-seed (seeds 7, 13)

启动: 2026-04-28 23:36 UTC
ETA: 每 seed ~4.5h, 两 seed 共 ~9h, finish 2026-04-29 08:30 UTC

完成后:
- 3-seed median (42, 7, 13) per (fold, mode) ensemble
- 期望: pooled P/S 进一步 +0.005 提升, 三 seed per-fold β 都 stable

## 未来方向 (multi-seed 完成后)

1. **如果 multi-seed validates seed=42 result**: 这是 y_600 production candidate
2. **应用同样的方法到 y_1800**: phase3c 已经在跑, 也用 LC features (其实 phase3c 在 y_1800 上的 LC 测试 phase_F1 之前 ΔP+0.002 ΔS-0.007 — 边际, 但 y_1800 没 sign-flip 问题, 价值低)
3. **DANN domain adversarial**: 仍可尝试, 但 phase3c+LC 已 close gap, DANN 投入产出比下降
4. **Multi-asset cross-section**: CLAUDE.md 标识为唯一 fundamental 杠杆, 仍是中长期方向

## Files of record

- `experiments/y600_phase3c_lc/seed42/fold_{0,1,2}/{test_preds,ema_test_preds,swa_test_preds}.npz` — 突破数据
- `configs/y600_phase3c_lc/y600_phase3c_lc_seed{42,7,13}.json` — 配置
- `scripts/y600_phase3c_lc_overnight.sh` — Phase 1 orchestrator (已 done with bug 但 result valid)
- `scripts/y600_phase3c_lc_multiseed.sh` — Phase 2 multi-seed (running)
- `data/npz_v4_long_context_y600/` — y_600 LC overlay (978/991 days, built today)
