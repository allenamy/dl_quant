> **创建:** 2026-07-14 | **Session:** 0C suppl-factor S1 评分 | **状态:** final | **作废条件:** king 部署实现变更或 panel 重建

# ARM-S1(4h 王座残差再挖)验收判词 (0C)

**裁决: CLOSE 4h-再挖轴 + 存档。非第五腿(冗余、伤书);仅边际王座增强(+0.0006 IC,不值第二个 4h 模型)。王座已饱和 4h horizon —— 同架构残差再挖递减回报。**

arm = wideA_s1_yr4k_c1(YR4K 目标 = YR4 逐 ts 对 OOS king-pred 残差化,32ch,lam_orth=0+xattn,te 2023-2026 4 fold)。base = king_pred_panel(ts 对齐)。

## 门

- **(a)增量 = IC vs YR4K: +0.0181**(CI[.016,.021],逐年 2023 +.018/2024 +.020/2025 +.015/2026 +.022 全正)。**★corr(YR4K,YR4)=0.989 → 近全量纲(无残差空间打折,你的换算对)** —— **但不转化为书级价值(见下)**。
- (b)pred-corr vs king **0.36**(<0.7 但中等)—— S1(同架构/4h)**部分再学回 king**,故多数"增量"冗余。

## ★ 王座增强(king-merge)—— 边际

50/50 blend **伤书**(king 0.0913→0.0841,显著负)。小权重 boost: w0.05 +0.0004 / **w0.1 +0.0006** / w0.2 +0.0006(全显著)/ w0.3 ns。⇒ **小权重给微小但显著 +0.0006 IC(+0.7%),真实但无关紧要 —— 不值第二个 4h 模型;若要,王座 seed-ensemble 更便宜。**

## ★ 五腿-分散 —— FAIL

S1↔king **book-corr 0.477**(高,同 4h horizon + 同执行画像)。腿间: funding 0.13 / king 0.48 / size −0.15 / s2 0.22。**加 S1 作第五腿伤书: 4-leg Sh 8.06 → 7.63(Δ −0.43)。** 与主导 king 腿冗余,非分散。

## 机制

**xattn 王(seed-robust)已饱和 4h horizon。** 同架构残差再挖找到统计-真实 +0.0181,但**大部分冗余**(pred-corr 0.36,book-corr 0.48)—— 真正正交部分只贡献 +0.0006 IC。**同 horizon 同执行再挖 = 递减回报。**

## 与 S2 对照(关键教训)

| | horizon | corr to king | 书级 | 判 |
|--|--|--|--|--|
| S2 | 24h(慢) | 0.22 | 改善+最差年保护 | **ACCEPT** |
| S1 | 4h(同 king) | 0.48 | 伤书 −0.43 | **ARCHIVE** |

**★教训: HORIZON 多样性(+不同执行画像)才使补充因子进书;对饱和 king 的同-horizon 再挖不加值,即便有统计-真实残差增量。**

## 建议

**存档 ARM-S1;关 4h-再挖轴。** 边际 +0.0006 4h 提升若要,靠**王座 seed-ensemble**(非独立残差-拟合模型)。**补充因子阶段: S2(24h)=1 ACCEPT;S1(4h 再挖)=存档;metrics 输入轴=关。剩余 EV: 只投真正不同-horizon 或不同-机制的因子。**

---
**产物:** `arm_s1_verdict.json` · `arm_s1_score.json` · `score_arm_s1.py`/`score_arm_s1_book.py`
