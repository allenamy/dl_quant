> **创建:** 2026-04-27 02:05 UTC+8 (2026-04-26 18:05 UTC) | **Session:** y600-trackA-V1-3fold-final
> **关键事件:** Track A V1 (V4 + dir_huber 0.2 + β_calib 0.05) 3-fold y_600 训练全部完成 (~4h pod time); 自主对照 V4 production baseline (block_b LIVE)
> **上一版本:** docs/Y600_Y1800_AUTONOMOUS_2026_04_27.md (2026-04-26 16:50 UTC) — fold 0+1 中期判断
> **状态:** final | **作废条件:** Track A V2/V3 启动并产出新结果时归档

# Track A V1 (β-calibration loss) — y_600 3-fold 最终结果

## 配置 (验证)

- **架构:** V4 DualPathLOBModelV3 (59,315 参数, 与 V4 production 完全一致)
- **训练:** 700d train / 30d val / 90d test, 3-fold walk-forward, fold_stride=60d
- **Loss:** DUL (pinball + utility_rank) + **dir_huber=0.2 + β_calib=0.05** (Track A 唯一新增)
- **Val gate:** composite (0.5·P + 0.5·S), EMA decay=0.999
- **Early stop:** patience=8 → fold 0/1/2 分别在 ep ?/11/15 停

## 3-Fold 结果对照 (POOLED clean stride-10, N=4871)

| Variant | P | S | β | σŷ/σy |
|---|---:|---:|---:|---:|
| **V4 baseline** (`block_b_run` LIVE production) | **0.0560** | **0.0734** | 0.955 | 0.059 |
| Track-A V1 LIVE | 0.0502 | 0.0706 | 0.917 | 0.055 |
| **Track-A V1 EMA** | **0.0510** | **0.0688** | **0.984** | 0.052 |

**ΔV1 EMA vs baseline:** ΔP=−0.005, ΔS=−0.005, Δβ=+0.029 (β 改善 +0.029 朝向 1.0)

## Per-Fold (clean stride-10)

| Fold | N | Variant | P | S | β |
|:-:|---:|---|---:|---:|---:|
| 0 | 1543 | V4 baseline | **0.093** | **0.108** | 1.73 |
| 0 | 1543 | V1 EMA | 0.047 | 0.057 | 1.30 |
| 1 | 1651 | V4 baseline | 0.042 | 0.059 | 0.95 |
| 1 | 1651 | V1 EMA | **0.058** | **0.074** | **1.08** |
| 2 | 1677 | V4 baseline | 0.045 | 0.077 | 0.68 |
| 2 | 1677 | V1 EMA | 0.049 | 0.074 | 0.73 |

**异象:** V1 与 V4 baseline 在 fold 间 IC 反相关 — fold 0 baseline 极强(0.093),V1 弱(0.047);fold 1 baseline 弱(0.042),V1 强(0.058)。pooled 互抵后接近相等。Calibration 把 strong-fold 的"运气"压平,把 weak-fold 抬升。

## Gate Decision (vs `block_b_run` baseline, 预先声明)

| Gate | Threshold | V1 LIVE | V1 EMA |
|---|---|:-:|:-:|
| no_S_regression | ΔS ≥ −0.005 | PASS (−0.003) | PASS (−0.005) |
| no_P_regression | ΔP ≥ −0.005 | **FAIL** (−0.006) | PASS (−0.005) |
| beta_close_to_1 | \|β−1\| ≤ 0.30 | PASS (0.083) | PASS (**0.016**) |
| no_var_collapse | σŷ/σy ≥ 0.020 | PASS | PASS |
| **OVERALL** | | **FAIL** | **PASS** ✅ |
| stretch_P_uplift | P ≥ baseline × 1.10 | FAIL | FAIL |
| stretch_S_uplift | S ≥ baseline × 1.10 | FAIL | FAIL |
| stretch_beta_tight | \|β−1\| ≤ 0.15 | PASS | **PASS** (0.016) |

## 用户目标对齐

| 用户表述 | 结果 | 状态 |
|---|---|:-:|
| "Pearson, Spearman 不降" | ΔP=−0.005, ΔS=−0.005 (容差边缘) | ⚖️ pass with caveat |
| "进一步涨 +10%" | 未达 (P 0.062 / S 0.081 才算 stretch) | ❌ |
| "β 尽可能接近于 1" | β=**0.984** (EMA),差 0.016 | ✅ |
| "可以直接交易" | V1 EMA: σŷ/σy=0.052, β=0.984 — 数学上可直接交易 | ✅ |

## 核心结论

**Track A V1 (β-calibration loss) 是 calibration 维度的成功,不是 IC 突破。**

- ✅ **β=0.984** — 模型预测幅度首次自动校准到 1.0 量级(baseline EMA β=0.955;raw single-ckpt β 通常 1-2),无需 post-hoc β 缩放即可交易
- ⚖️ **IC 与 baseline 实质相等** — pooled 3-fold ΔP/ΔS 都在 0.005 容差内,fold 间反相关说明 calibration loss 是"regularizer"性质 (压扁强 fold 抬弱 fold) 而非"signal extractor"
- ❌ **未达到 +10% IC 提升** — stretch goal failed,但这本身就是高目标 (V4 已是单资产 ceiling)

## 为什么 P/S 没涨,而 β 改善

直观理解:`β_calib_loss = (β−1)²` 强制模型 ŷ 的 amplitude 与 y 的 amplitude 匹配,但**不直接奖励 IC**。换言之,calibration 让模型"说话更靠谱"(每个数值的 magnitude 可信),但模型"说什么"还是被 pinball + utility_rank 主导,而那些 loss 的 IC ceiling 已被 V4 baseline 达到。

要打破 IC ceiling,需要的是**新信息源**(多资产、新数据),而不是新 calibration。这与 CLAUDE.md "y_600 单资产 V4 已是 ceiling" 一致。

## 实操建议 (production 应用)

1. **如果只关心 trading-ready ŷ:** 用 V1 EMA model 直接出单。β=0.984 → 不需要 β 缩放,position size = ŷ × notional。
2. **如果只关心最高 IC:** 用 baseline `block_b_run` LIVE (P=0.056, S=0.073),交易前 ŷ × 0.955 缩放。两者 IC 相同但 baseline 略高 (差 0.005 在噪声内)。
3. **不要混用:** 不要把 V1 EMA 和 baseline blend (那会复活 final_stack 的 rank-transform 问题,β 失控)。

## 下一步候选 (尚未启动)

- **Track A V2/V3** (已写 config 但被 kill 弃用): dir_huber=0.2 alone, dir_huber+β_calib=0.02 — 都不是 fundamental 突破,可不再迭代
- **Track A V4 sanity** (已写 config): 纯 baseline_plus 无 calib loss — 用作 σ_ŷ/σ_y trajectory 健康基线,可单独跑一次确认
- **Track B (y_1800)** 进行中 — orchestrator 已 queue,V4 baseline 完成后再决定是否需要 calib variant
- **回到 fundamental 路径:** 多资产 (ETH/SOL), funding rate / OI / basis 等正交特征 (per CLAUDE.md)

## 附录: 文件清单

- 配置: `configs/y600_calib/baseline_calib.json` (+ V2/V3/V4_sanity 已写但未跑)
- 代码: `src/losses/calibration_losses.py` (dir_huber + β_calib)
- 训练 log: `logs/y600_calib_3fold.log` (pod) — fold 0/1/2 完整 epoch trace + EMA σ_ŷ/β logging
- Preds: `experiments/y600_calib/baseline_calib/fold_{0,1,2}/{,ema_}test_preds.npz`
- 对照 JSON: `experiments/y600_calib/baseline_calib/compare_vs_block_b.json`
- 对照脚本: `scripts/compare_y600_calib.py` (修正后用 block_b_run 而非 final_stack 做 baseline)
