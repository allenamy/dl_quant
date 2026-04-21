# Y600 Autonomous 10H Push — Report (2026-04-21)

## TL;DR — 目标未达成

**Target:** P AND S ≥ 0.10, production-suitable, generalizable.

**Achieved:** V4 baseline 保持 pooled clean P=0.074 S=0.087 (no improvement). V5-LH 架构尝试**完全失败** (fold 0 clean P=-0.061).

**Conclusion:** 单资产 BTC y_600 信号天花板 ~0.074 P / 0.087 S 是结构性的, 不是特征或架构问题。

---

## 实验矩阵

### 特征工程 (全部 Ridge 验证 null — 详见 feedback_ridge_walkforward_before_pod.md)

| 特征族 | Feats | Ridge ΔP (3-fold) | ΔS | 结论 |
|---|---:|---:|---:|---|
| TradeFlow (signed volume imbalance) | 5 | −0.001 | +0.002 | REJECT |
| Long context (lr, rv, hurst, mz) | 6 | −0.002 | +0.002 | REJECT |
| InfoFlow (VPIN, large-order, time-since) | 4 | −0.000 | −0.002 | REJECT |

**共性:** V4 64 特征空间已包含这些 time-aggregated 模式。更长尺度版本与现有特征强 collinear, 不增新信号。

### V5-LH 架构 (Mamba-2 + side-aware + cross-path fusion)

| Config | Val peak C (P/S) | Test CLEAN P/S | 结果 |
|---|---|---|---|
| default (focal=2.0) | 0.048 (0.075/0.020) | killed ep 7 | P/S divergence (tail overfit) |
| balanced (no focal) | 0.060 (0.066/0.056) | **−0.028 / −0.008** | Variance collapse (yp std 0.08 vs y std 1.9, 23× compression) |
| simple (V4-recipe loss) | ABORT ep 0 | — | Grad explosion |
| simple_stable (LR 3e-4, clip 0.5) | 0.070 (0.072/0.068) | **−0.061 / +0.008** | Worse variance collapse (30× compression) |

**失败模式一致:** Val metrics 看似好 (0.060-0.070 composite), test clean 崩溃到 negative P 或 near-zero S。

**核心问题:** Val→test 迁移崩坏。Mamba state 追踪 30-min 长上下文, 拟合了 30-day val window 的 local regime pattern, 但未泛化到 90-day 跨 regime 的 test。预测 std 塌缩 (全部样本输出接近 median) 是症状。

---

## 诚实结论

1. **V4 ~0.074/0.087 pooled clean 是真实信号天花板** (单资产, 现有特征集, 非 Mamba 架构)。
2. **架构突破在此数据规模上不成立** — Mamba 的 long-range advantage 在 y_600 (10-min horizon) 上反而引入 regime 噪音。
3. **特征工程方向已饱和** — trade/book 数据的 time-aggregation 信号都被 V4 覆盖。

## 真正能突破的方向 (研发方向建议)

1. **多资产 breadth** — 单资产 BTC IC 约 0.08-0.10 是学术和工业共识; 多资产 portfolio IC-IR 能显著提升 (reusable 预测, diversification)。
2. **不同数据源** — 资金费率 (funding rate), 持仓量 (open interest), 期现基差。这些是真正与 LOB 正交的信号。
3. **不同 horizon** — y_180 pooled clean P=0.094 已证, y_600 本身可能信号密度更低; 优化 y_180 可能比硬推 y_600 更实用。

**Production-readiness:** V4 final_stack (0.5·SWA + 0.5·Block-B-EMA) 已 production-ready (CoV 0.12, DA 0.539 clean). P=0.074 < 0.10 但 stable, generalizable, low-variance across folds.
