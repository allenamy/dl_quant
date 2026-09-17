# FP2 独立复审三轮(75f0035b: F1/F2/F3)的回应与修复 — 2026-09-17

> **创建:** 2026-09-17 13:0xZ | **Session:** b9646a9e(主研究员) | **状态:** F1/F2/F3 已修并提交(943887eb), 终端收据用稳定源码重新形成(表 84fe0906 / 决策 b408617e); 结论不变: G1′ UNDECIDED, G3 FAIL(E8), **不换装** | **作废条件:** 独立研究员再复审推翻任一修复; 或出数后判据被改写(不允许)
> **复审件:** `git show 75f0035b:docs/fixprogram_2026-09-13/REVIEW_FP2_ROUND2_RESPONSE_codex_independent_2026-09-17.md`。复审总判「多数旧问题确实修好, 但不能接受『R01–R11 全部验收完成』, 也不支持现在换装」——**接受**; 本文只处理三处残余, 不重述已关项。

## 0. 提交

| # | 提交 | 内容 |
|---|---|---|
| r3-c1 | `943887eb` | 决策装置 v4(F2/F3)+ 套件 30/30 + F1 补丁单独归档 + 错题 E-0917-C |
| r3-c2 | 本文 + 终端收据 `*_final_v2.*` | |

## 1. F1 [P1] 送审表不写 n_days, 决策却要求 — **成立; 如实分期归档**
- 三个源码分开记: 送审表 c34db786(无 n_days)→ 真实首跑 12:06:37Z 四格被拒(收据 `DECISION_FP2_2026-09-17_run4.json` 保留); 现场补丁 21a38721(只补 n_days)→ 12:10:29Z G1=UNDECIDED; 现盘 84fe0906(再改脚注语义)。补丁单独归档 `FP2_receipts/patch_F1_per_year_n_days_and_note_d1af114f.diff`, 错题 E-0917-C(夹具两边各造 n_days, 真实收据布局未对齐; 与 AMENDMENT 6/8、F07 首版同族)。
- 终端收据按复审要求**用同一稳定源码重新形成**(12:56Z, runner 7): 表由现盘 84fe0906 生成(receipt.self_sha256 == 现盘), 决策 v4 b408617e; 不改历史票据。
- 未做「原表 → 原决策」集成正控的夹具化(表装置真跑出的收据直接喂决策): 真实 runner 7 的 per_year → decision 就是这条链, 但套件层面仍是两边夹具; 登记为后续项(需要把逐年表的合成臂夹具与决策夹具合一)。

## 2. F2 [P1] 终端未核完全部依赖 — **成立; 已按「复用链自己的 require」关闭**
决策 v4(`fp2_decision.py` b408617e):
- **出口收据**: `v4_gate_common.require(receipt, inputs=receipt.inputs_path, gate=BUNDLE_export, self_sha=D 内出口门 sha, recorded_extras=True)`——门名、D 内门源及其在**该模块旁合同**里的批准、PASS、28 名登记底线、收据记录的**每个**输入现盘复哈希(bundle/slow2026.txt、模型件、四书四基线、umask、合同 …)。复审反例「改 slow2026.txt 字节, 四书不变」⇒ `input 'bundle/slow2026.txt' changed since the receipt`(F2a)。
- **STEP1 收据**: 同一 require(gate STEP1, profile v4, D 内 FP2 变体 sha, recorded_extras)+ 必须在 `R/v4_gates` 下。反例「盘上 targets 换、两票旧 sha」⇒ STEP1 require 拒 + 成员规则输入复哈希拒(F2b); 「根外、gate=NOT_STEP1、全零源、PASS=false、VERDICT=PASS」⇒ 拒(F2c)。
- **成员规则收据**: D 内装置身份 + 全部记录输入现盘复哈希 + **语义键**绑定: MASKED_KING_META == 出口 `wide_fea_v4_meta`(不再「命中任意 key」, F2d 反例拒); MASKED_DL_TARGETS / CACHE / MEMBER_MASK / RAW_PATCH == STEP1 同名输入(F2e 异 cache 拒); CONTROL_KING_META / CONTROL_DL_TARGETS == 控制收据产物(控制收据由 STEP1 的 inputs_path 定位, 已被 require 复核)。
- 真实数据(12:56Z): STEP1 require **PASS**(12 输入复核); 语义绑定 6/6 True; 出口 require 拒于 `receipt says PASS=False`(E8)—— 与实际一致。

## 3. F3 [P2] formal 钉了窗口名字没钉取数窗 — **成立; 已关闭**
- formal 常量: WA_START 2022-06-30 00Z, UB 2026-08-30 20Z, KING_LIVE 自 2024-01-01, 年集恰为 2022…2026, L=2; 覆盖 ⇒ REFUSED_PROFILE(F3e)。
- 表的 env(UB/WA_START/LEV/SEATS/SEEDS/ARMS)必须等于正式值(F3b 反例拒); coverage 的 UB/WA_START/年集/锚数(9,138 / 5,838)必须等于冻结值(F3a「2025-06→2026-01、只留 2026」拒; F3d 锚数错拒)。
- **窗口从书文件自身的 ts 轴重导**: 每条臂记录现盘复哈希后 `np.load` 其 ts 列, 要求 ts[900] == WA_START、轴覆盖 UB、冻结窗内锚数 == 9,138 / 5,838(F3c「书轴止于 2026-03、表自称冻结窗」拒)。每格 n 也必须等于冻结锚数。
- 真实数据: 四书轴 9,138 / 5,838, 全部相符。

## 4. 复审 §6 关于 PROPOSED4 — **接受其限定**
PROPOSED4 只把出口身份钉到预注册的「两臂同 tradable 掩码」对象, 未放宽任何数值阈值(复审已逐项核对); 标为**事后身份合同更正**, 不称原冻结合同当初就通过; 「every later chain」一句撤回——十月链与其它根需各自的身份合同与验收(已在合同 PROPOSED4.scope 文本中改为只对本月本根)。

## 5. 结论(不变)与仍开清单
- G1′ UNDECIDED(四格中只 W_ALPHA s42 下界 > −δ), G2 True, G3 FAIL(E8 fix 席位 K6) ⇒ **不换装**; 决策收据 `DECISION_FP2_2026-09-17_final_v2.json`。
- 仍开(与复审 §7 一致): 原表→原决策集成正控夹具化; FP2-1 真实重建; preflight 钉 controls/helper、K3 细化、run_arm.sh 入装置; 生命周期现金核账、F08 经济影响与代际状态隔离、生产路径与真实书平价; 出口门 fix 席位问题的处置(用户已表态「回测应只看动态席位」⇒ 拟做新出口门变体只核在役席位 dyn, 需审批新门 sha, 未开始)。
