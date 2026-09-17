# FP2 独立复审五轮(7e3eb927: P2-R4-A 路径别名 / P2-R4-B K6 豁免过宽)的回应与修复 — 2026-09-17

> **创建:** 2026-09-17 14:5xZ | **Session:** b9646a9e(主研究员) | **状态:** 两处 P2 已修, 真实终端收据重新形成(`FP2_receipts/*_r5.*`); 结论不变 **NO_SWAP** | **作废条件:** 独立研究员再复审推翻任一修复
> **复审件:** `git show 7e3eb927:docs/fixprogram_2026-09-13/REVIEW_FP2_ROUND4_RESPONSE_codex_independent_2026-09-17.md`。接受的部分(三处旧反例关闭、29 装置一致、八书未变、四格只一格过 ⇒ 不换装)不重述。

## 1. P2-R4-A 路径别名绕过批准范围 — **成立, 已在三层关闭**
- 决策: `EXPORT_GATE` 必须是裸 basename(含 `/`、`.` 前缀、绝对路径 ⇒ UNAVAILABLE「must be a bare basename」); 变体条目按 basename 查, 查不到再**按文件 sha 查**——字节是某批准变体的文件, 无论叫什么名都绑定到该条目并拒绝(不再由「字典查不到」推出「这是基础门」)。反例: `./v4e_gate_export_v2.py` ⇒ 拒; STEP1 字节在合同里登记为另一名 ⇒ 拒(R5-1 / R5-2; 套件 41/41)。
- 驱动: `GATE_EXPORT` 含 `/` 或 `.` 前缀 ⇒ `die export_gate_not_a_basename`。
- 装载器: GATE_STEP1 / GATE_STEP2 / GATE_EXPORT / BUILDER_TARGETS / BUILDER_KING_FEA 的值非裸 basename ⇒ `month_env_not_a_basename_<KEY>` rc 4(套件新格 [R5])。

## 2. P2-R4-B rev2 豁免整个复合 K6 — **成立, 已收窄(rev3)**
K6 拆为 `K6_positivity_ok`(冻结窗非空、窗内 gross > 0、全轴 gross ≥ 0)与 `K6_ceiling_ok`(gross ≤ 1.000001); 非在役席位的 `identities_ok` 现在包含 positivity, **只有 ceiling 为信息项**。反例: fix 席位冻结窗内一整行平仓(gross = 0, 恒等式保持一致)⇒ v2 与变体皆红(S6; 套件 7/7)。真实数据(14:40Z): fix 两书 positivity True / ceiling False ⇒ 变体 PASS, 决策 NO_SWAP。

## 3. 收据与版本
变体 rev3 `16e9cc32`(diff 收据 60 行), 合同 `753f9752`(PROPOSED5 rev3 条目, 旧 sha 记 superseded), 决策 `14fc96e5`; preflight 29 件 PASS; 出口 require 28 输入; 决策 NO_SWAP(G1′ UNDECIDED, G2 True, G3 True)。

## 4. 未关(不变)
原表→原决策集成夹具; FP2-1 真实重建; K3 细化; run_arm.sh 入装置; 现金核账; F08 影响与代际隔离; 生产平价。FP2-6b 的 16Z 首次 f10_sha 产出/消费/设钉另交收据。
