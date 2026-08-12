> **创建:** 2026-07-12 | **Session:** 0C independent scorer/auditor | **状态:** final | **作废条件:** xattn2 补 seed 电池(若要翻案需 seed 带越过单层 seed 上沿)

# xattn2 深度臂裁决 (0C) — 边界案例

**裁决: FAIL / TIE → CLOSE(不排 5yr,省槽)。** 你的先验(平局偏 FAIL)被数据确认。panel byte-check PASS(39f5cc4e)。

xattn2(n_xattn=2): [0.0841/0.1030/0.1079] mean **0.0983** vs 单层王 [0.0718/0.0988/0.1138] mean 0.0948。mean Δ +0.0035(恰过 +0.003 线)。

## 1. 逐 fold 配对显著性(per-ts + day-block bootstrap 3000×)

| fold | x2 | king | Δ | CI95 | 显著 | dyn-share |
|--|--|--|--|--|--|--|
| 0 | .0841 | .0718 | **+.0123** | [+.0029,+.0214] | **是(+)** | 0.961 |
| 1 | .1030 | .0988 | +.0042 | [−.0029,+.0118] | 否 | 0.90 |
| 2 | .1079 | .1138 | **−.0059** | [−.0176,+.0052] | 否 | 0.98 |

**只有 fold0 显著**(+.0123,CI 排除 0),且**恰在过拟合征兆位**(最早/最小 test 块)。fold1/fold2 均不显著。**fold2 −.0059 是名义劣但不显著(噪声抖动,非真降级)。**

## 2. 过拟合三项检查

- **fold0 反常高?** 是 —— fold0 是唯一显著增益且在小 test 块。**params:sample +13% → 深度把 fold0 拟合更好但不迁移到 fold1/fold2 = 教科书过拟合征兆。**
- **dyn-share 掉没?** 没 —— ~0.95(同单层 0.949),深度**未引入静态结构**。不是静态灌水。
- **逐 fold 抖动 vs 单层?** 反而**更小**(disp 0.0103 vs 0.0174)——深度把低 fold(0)抬、高 fold(2)压,向中间压缩(仍是过拟合模式,非"更抖")。

## 3. 对照单层三 seed 带(决定性)

单层王 seed 带 {0.0948, 0.0910, 0.0973},mean 0.0944,std 0.0026,**上沿 0.0973**。xattn2 = **0.0983 = +1.53σ 上,仅比单层 seed 上沿高 +0.001**。⇒ **一个走运的单层 seed 就能到 0.0983;xattn2 单跑 +1.53σ 不足以证明越过 seed 带。** mean 边际 +0.0035 < 单层 seed spread 半宽(0.0032)——落在 seed 噪声内。

## 判词

**FAIL / TIE → CLOSE。**
1. 预注册"逐 fold 不劣"违反(fold2 −.006,虽不显著)。
2. mean 边际 +.0035 落在单层 seed 噪声内(z +1.53,仅 +.001 越上沿)——非可分辨真边际。
3. 增益是**单 fold 尖峰**(fold0,唯一显著,在过拟合位),不均匀不 regime-robust —— 深度-2 refinement 未交付真增量。
4. dyn/dispersion 正常 → 臂"没坏",只是**单层等价+过拟合味 fold0 尖峰**。

**⇒ 一次 message-passing(n_xattn=1)足够;第二次不加 regime-robust alpha 却 +13% params。关闭,不排 5yr。队列 → ARM-MIX/FinPFN 评估(需 builder,你决策)。** 若要翻案:补 xattn2 3-seed 电池,若 seed 带整体越过单层 0.0973 上沿再议。

---
**产物:** `xattn2_adjudication.json` · `adjudicate_xattn2.py`(可复算)
