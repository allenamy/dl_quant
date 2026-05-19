> **创建:** 2026-05-14 06:25 UTC+8 | **Session:** track-r-t-overnight | **关键事件:** Track R NULL/NEG (β-calib reverse-fired), Track T mixed (DA|y|>σ +0.005)
> **上一版本:** docs/V5PUSH_OVERNIGHT_BRIEF_2026_05_13.md (3-way ensemble baseline)
> **状态:** final | **作废条件:** 用户选择 production CSV (3-way vs 4-way DA-opt)

# 早间报告 — Track R / Track T 实验结果

## TL;DR
- **Track R (GLU + β-calib + TV v3 长程 RV)**: NULL/NEG, 全方位 -10% vs P3, β-calib loss 反向 (推 σ_ŷ 过高)
- **Track T (Track P3 + tail-focal BCE)**: 混合, **DA|y|>σ standalone 最高 0.5473**, ensemble 后 DA|y|>σ +0.005 over 3-way
- **两个 production CSV 可选** (按目标取舍):
  - **3-way P3+A+V5 (P/S-optimal)**: P=+0.0648 DA|y|>σ=0.5485 — 现 baseline
  - **4-way T+P3+V5 (DA-optimal, 新)**: P=+0.0630 DA|y|>σ=**0.5539**, DA=0.5288 tied

## 详细结果

### Standalone (live-cal pool 3-fold, n=49,953)
| Model | P | S | β | σŷ/σy | DA | DA\|y\|>σ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| V5 prod (baseline) | +0.0589 | +0.0661 | 1.010 | 0.058 | 0.5241 | 0.5434 |
| Track A | +0.0579 | +0.0690 | 0.822 | 0.070 | 0.5271 | 0.5446 |
| Track P3 | +0.0582 | +0.0655 | 0.866 | 0.067 | 0.5262 | 0.5429 |
| **Track T (NEW)** | **+0.0548** | **+0.0628** | **+0.816** | **0.067** | **0.5251** | **0.5473** ✓ |
| Track R (REJECTED) | +0.0519 | +0.0590 | 0.684 | 0.076 | 0.5232 | 0.5400 |

**Track T standalone DA|y|>σ=0.5473 — 最高** (vs P3 0.5429, +0.004). Tail-focal BCE 在 tradeable subset 真改 direction acc.

### Ensemble sweeps

**4-way (T+P3+A+V5) by (P+S)/2 best**: wT=0.00, 3-way unchanged
**4-way by DA|y|>σ best (NEW)**: **wT=0.40 wP=0.35 wV=0.25 wA=0.00** (Track A drops!)

| Ensemble | P | S | β | DA | DA\|y\|>σ |
|:---|:---:|:---:|:---:|:---:|:---:|
| 3-way (P+S-opt, w_P3=0.35, w_A=0.30, w_V5=0.35) | **+0.0648** | **+0.0725** | 1.10 | 0.5288 | 0.5485 |
| **4-way (DA-opt, w_T=0.40, w_P3=0.35, w_V5=0.25)** | +0.0630 | +0.0696 | 1.08 | 0.5288 | **0.5539** |

Pareto: 3-way Pearson +0.0018 higher; 4-way DA|y|>σ +0.0054 higher.

## Track R 失败教训 (新 anti-pattern 候选)

`lambda_beta_calib=0.10` 在低 SNR 上反向推 β:
- 期望: 推 β=cov/var(ŷ) → 1
- 实际: 推 σ_ŷ 上升 (0.067 → 0.076), cov 跟不上, β 反而下降 (0.87 → 0.68)
- 类似 anti-pattern #13 (learnable scalar drift) — free Parameter 在低 SNR 找不到 β=1 的 minimum
- **规则**: 不用 free `lambda_beta_calib` 在低 SNR. β 校准用 post-hoc demean (proven) 或 batch-statistics anchor.

GLU fusion 也未独立证明 benefit (与 β-calib 同时改 axis, 不可分离贡献).
TV v3 长程 RV channels (rv_1h/4h/24h) 是 per-sample constant, 信息可能 minimal.

## Track T 成功要素

- **Pure DA axis ablation** (= Track P3 + 1-line change cls_weight_mode=tail_focal_1p5 + lambda_cls 0.05→0.10)
- Tail-focal weight `clip(|y|/σ, 0.3, 3.0)^1.5` 把 BCE 梯度集中到 tail samples (|y|>σ 真方向区)
- **不 REPLACE 原 ranking loss** (utility_rank + dir_huber 不变)
- 与 #25 一致 (focal 作 AUXILIARY 是安全的)

## Deliverables

并存, 选 production 看目标:

- 📦 **3-way P3+A+V5 (P-optimal, 旧 baseline)**: `exports/v5push_3way_ensemble_p3_a_v5/y600_predictions_3way_p3_35_a_30_v5_35.csv`
- 🆕 **4-way T+P3+V5 (DA-optimal)**: `exports/v5push_da_optimal_4way_t_p3_v5/y600_predictions_da_optimal.csv`

## User 目标达成度 (current vs 3-way / 4-way)

| 指标 | 目标 | 3-way | 4-way (DA-opt) |
|:---|:---:|:---:|:---:|
| Pearson | 0.07-0.08+ | +0.0648 (-0.005) | +0.0630 (-0.007) |
| β slope | ~1.0 | +1.10 ✓ | +1.08 ✓ |
| bias | low | -0.094 bps ✓ | (similar) |
| Trading/Calib monotonic | ✓ | BinMono +0.988 ✓ | (similar) |
| **DirAcc** | **0.58+** | 0.5288 | 0.5288 (tied) |
| **DirAcc\|y\|>σ** (tradeable) | — | 0.5485 | **0.5539** ✓ better |

**P 0.07 gap**: 仍 -0.005, single-asset y_600 Bayes ceiling 附近. 不进 multi-seed (user 指示).

**DA 0.58 gap**: pool DA still 0.5288, 但 high-vol regime 已 0.55+, trust-gated top 20% 已 0.56+. 实操可用.

## 接下来 (建议)

1. **决定 production**: 3-way (P-opt) 或 4-way (DA-opt)? 取决于交易目标主要看 IC 还是 hit rate
2. **若继续 push**: 
   - Track U: 序列级 direction supervision (predict sign at 6 anchor timesteps) — 没做过
   - Track V: Confidence head 训练时 weight by predicted IQR (inverse) — 没做过
3. **跨资产** (CLAUDE.md priority 1): ETH/SOL data 是真正物理上限上调途径
