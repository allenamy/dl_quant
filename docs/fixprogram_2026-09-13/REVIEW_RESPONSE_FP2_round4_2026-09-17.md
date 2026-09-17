# FP2 独立复审四轮(91968056: P2-1 / P2-2 / P2-3 + PROPOSED5 政策范围)的回应与修复 — 2026-09-17

> **创建:** 2026-09-17 14:4xZ | **Session:** b9646a9e(主研究员) | **状态:** 三处边界已修并在真实数据上重新形成终端收据(`FP2_receipts/*_r4.*`); PROPOSED5 收窄为 rev2 并如实改称「事后出口判定范围变更」; 结论不变: **NO_SWAP**(G1′ UNDECIDED) | **作废条件:** 独立研究员再复审推翻任一修复
> **复审件:** `git show 91968056:docs/fixprogram_2026-09-13/REVIEW_FP2_ROUND3_RESPONSE_codex_independent_2026-09-17.md`。复审接受的部分(F1 关闭; 上轮反例拦住; NO_SWAP 数字; 八书未变)不再重述。FP2-6b 实盘部署不在其验收范围——同意, 本方在 16Z 锚后另交读者/生产者/设钉三段收据。

## 1. P2-1 批准范围没有完整执行 — **成立, 已修(决策 v5)**
- 终端现在**执行**合同 `approved_variants` 条目, 不只读平坦名单: 变体文件盘上 sha == 条目 sha; `requires` 的每个 helper 盘上 sha == 记录值(反例「requires helper sha 全零、平坦名单不动」⇒ UNAVAILABLE); `scope` 的月 == preflight 收据的月、根 == R(反例 2026-10 / 他根 ⇒ UNAVAILABLE)。对 STEP1 的 fp2 变体与出口变体都执行。
- STEP1 变体的**必需键集固定**为 12 键(cache / control_dl_targets / controls_receipt / dlw_hf3_targets / dlw_v4raw_targets / fea82_hf3 / fea82_v4raw / fea89_f8v4 / fp2_gate_lib / hole_cells / member_mask / raw_patch), 从两个字典一起删键 ⇒ 逐键 UNAVAILABLE(反例删 3 键 ⇒ 3 条)。
- **控制链**: STEP1 消费的控制收据必须由 D 内 `fp2_controls.py` 写出(反例换掉 D 内文件 ⇒ UNAVAILABLE)、PASS, 其**全部**输入/产物现盘复哈希(反例改 cache 字节 ⇒ UNAVAILABLE, 同时 STEP1 require 与成员绑定也拒)。
- **preflight 钉**: 驱动 DEV_FILES 加入 fp2_gate_lib / fp2_controls / fp2_member_rule_check / fp2_per_year_table / fp2_decision(真实 preflight 29 件); 决策绑定 preflight 的 PASS、根、月与六个装置的 sha(反例改钉 ⇒ UNAVAILABLE)。登记项「preflight 独立钉 controls/helper」随此关闭。
- 套件 `tests_fp2_decision.py` 39/39(P2-1a…g + P2-3)。真实数据: 两个变体的 scope 均命中(2026-09 @ /workspace/fp2_2026-09), 控制链 PASS。

## 2. P2-2 省略 GATE_EXPORT 时选门受父环境影响 — **成立, 已修(装载器)**
`load_month_env` 装载前 **unset 全部可选键**(GATE_EXPORT / MEMBER_MASK / BUILDER_TARGETS / BUILDER_KING_FEA / PREV_*), 缺省只能来自驱动的字面默认; pipeline 套件加格「父 shell 带 GATE_EXPORT 与 MEMBER_MASK、月合同不含 ⇒ 装载后两者 UNSET」。本次 root 合同显式指定变体, 未受此缺口影响(与复审一致)。

## 3. P2-3 轴重导前强制取整 — **成立, 已修(两端)**
逐年表与决策在任何整数转换**之前**校验 ts: 有限、整数秒(`ts == round(ts)`)、4h 格点; 逐年表另要求四臂**原始浮点轴逐位相同**。反例「A1 原始 ts 全部 +0.5 s」⇒ 两端 UNAVAILABLE(Y14, P2-3 格)。真实八书原始轴为整数秒且相等(复审已独立核, 本方决策收据 `binding.arms` 亦记 9138/5838)。

## 4. PROPOSED5 政策范围 — **接受复审判断, 已收窄(rev2)并改措辞**
- 措辞: 「事后身份合同更正」改为「**事后出口判定范围变更**(接受域扩大: 同一批旧书 v2 FAIL / 变体 PASS)」; 旧 FAIL 收据保留; 批准时点 = 事后, 待复审。
- 范围: rev2(e55875d0)对 CHECK_SEATS 之外的席位**只**豁免 K6(gross ≤ 1.000001)与 E9 带宽; K1–K4/K7 恒等式与 E9 基线身份照旧折算(反例: fix K4 破坏 / fix 基线 sha 错 ⇒ v2 与变体皆红; fix gross 1.03 / fix 带外 ⇒ v2 红、变体绿且标 informational; dyn 任何破坏 ⇒ 皆红)。套件 `tests_v4e_gate_export_fp2dyn.py` 6/6, 与冻结 v2 在同一合成书上并排。
- 限定: 回放动态席位与实盘**水平**一致不是逐锚生产平价; fix 对照的旧角色被重新定义, 不是被认证消失。
- 真实数据(14:13Z): 变体 rev2 PASS(fix 两书恒等式与基线身份全过, 仅 K6 信息红), require 28 输入, judge-with-eligibility DONE; 决策 **NO_SWAP**(G1′ UNDECIDED, G2 True, G3 True)。

## 5. 未关(与复审 §6 一致)
原表→原决策集成夹具(复审已有真实入口正控, 待收入套件); FP2-1 新装置真实重建; K3 细化; run_arm.sh 入装置; 生命周期现金核账; F08 经济影响 / 代际状态隔离; 生产路径与连续状态平价。**换装认证在这些之前不成立**; 本轮结论 NO_SWAP。
