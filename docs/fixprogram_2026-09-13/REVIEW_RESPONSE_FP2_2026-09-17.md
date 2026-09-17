# FP2 独立复审(a5a596fe, F01–F10)的逐条代码级回应与修复 — 2026-09-17

> **创建:** 2026-09-17 10:5xZ | **Session:** b9646a9e(主研究员) | **状态:** 修复全部落地(提交链见 §0), 真实数据门已重跑 PASS, 全链运行器已从 mwf 重启在飞; 书层数字尚未产出 | **作废条件:** 独立研究员对本回应的再复审推翻任一修复, 或 FP2-8 链出数后判据被改写(不允许)
> **复审件:** `codex/fullchain-continuation-20260914` @ a5a596fe `docs/fixprogram_2026-09-13/REVIEW_FP2_codex_independent_2026-09-17.md`(本仓 `git show a5a596fe:…` 可读)。用户指令:「深入逐代码辩证分析排查」+ 常设规则「所有已知问题的修复不用等我裁定 … 最严谨的修复 … 完整的提交链和报告, 独立研究员复审」。
> **原则:** 每条先说复审是否成立(逐代码核), 再说修了什么、怎么证明(同输入前后对照 + 红能力), 再说真实数据上的结果。判据只收紧不放宽; 任何 UNAVAILABLE 不推断为 PASS。

## 0. 提交链(研究分支 `research/book-uplift-2026-09-11`, 全部显式 pathspec 提交)

| # | 提交 | 内容 |
|---|---|---|
| c1 | `516ae6b1` | F01 `run_v4_arms.sh` + 冻结缺陷副本 + 套件 5/5 |
| c2 | `87708c1e` | F02/F07 控制收据身份链 + F06 成员规则 + 合同变体刷新 + 套件夹具改每根独立装置目录(17/17) |
| c3 | `6fca442c` | F06(续)`build_dev_v4` 复用同一成员规则实现 |
| c4 | `61ddb1ab` | F09/F10 逐年表(11/11) |
| c5 | `918bea5f` | F03 决策装置 `fp2_decision.py`(14/14)+ 运行器 `per_year`/`decision` 阶段 |
| c6 | `a1444008` | F05 FP2-1 面板重建无源名(20/20) |
| c7 | `ac762661` | F08 暴露测量装置 + 真实读数收据 + 清单 |
| c8 | `4905cbd7` | F07(续)preflight 绑定改为真实收据布局(首版在真实数据上判 UNAVAILABLE, 收据保留)+ 合同再刷新 + 套件 18/18 + pipeline 482/482 |
| c9 | `88e9a726` | 设计 AMENDMENT 9 + 验收表 C6 降级 + 错题 E-0917-A |
| c10 | (本文件 + 真实数据门收据) | |

装置 sha(pod2 `devices_v4chain` == 研究仓, 逐文件核过): `fp2_gate_lib.py c7e6b76a` · `fp2_gate_step1.py 3ad3a6c6` · `fp2_gate_step2.py bd8e04c7` · `fp2_controls.py e89dcc7d` · `ELIGIBILITY_CONTRACT.json 8060222f` · `build_dev_v4.py e05f6ab8` · `fp2_per_year_table.py 7a248df5` · `fp2_decision.py fd270e9e` · `chain_fp2_run.sh d79d1b5d` · `run_v4_arms.sh dc9835dc`。

## 1. 逐条回应

### F01 · P1 · A0 臂用了新 King(赋值行尾注释吞掉 K3/K4/K4E)— **成立, 已修**
- **逐代码核**: `run_v4_arms.sh` 原行 `K3=$KD/SLOW_v3_on_v4axis.npy; K4=…; K4E=…   # …` 中 `#` 之后的 `K4=`/`K4E=` 是注释 ⇒ 未定义; A0 分支 `SL=$K3` 取到空 ⇒ 下游回退到默认 king 文件 = 新 King。复审对。
- **修**: 三个赋值各占一行; 每臂 `[ -n "$SL" ] && [ -f "$SL" ] || { echo "ARMS_FAIL missing SLOW_NPY for arm $ARM"; exit 3; }`; 缺陷版冻结为 `run_v4_arms.r1_de4ed666.sh`。
- **证**: `tests_run_v4_arms.py` 5/5 —— W1 A0 → `SLOW_v3_on_v4axis.npy` + umask 覆盖; W2 A1 → `SLOW_v4.npy`; W3 默认 umask; **W4 红能力: r1 副本上 A0 的 SLOW_NPY 为空**(基线绿, 变异红, 两值同报); W5 缺 king 文件 ⇒ `ARMS_FAIL` rc 3。
- **工件影响**: 无。本根 arms 阶段尚未跑过(GPU 阶段之后); 九月 review_scratch 的 A0 是另一套装置。

### F02 · P1 · VERIFY_ONLY 对改动过的产物重发 PASS — **成立, 已修**
- **逐代码核**: 原 verify-only 只读旧收据的 VERDICT 与产物路径, 不比对输入/产物 sha ⇒ 产物被改后仍可「验证通过」。
- **修**(`fp2_controls.py` e89dcc7d): verify-only 必须 (a) 前次收据 runs=={king,dl} 且 rc 0; (b) **`verify_only_binding`: 当前输入 sha 与前次 `inputs_sha256` 逐项相等, 产物 sha 与前次 `outputs_sha256` 逐项相等**, 任一不等 ⇒ UNAVAILABLE(不是 FAIL, 因为它不是判词而是不可验证)。
- **证**: 套件 G1c(verify-only 在 rc-0 产物上 PASS, 记 previous_receipt, build.log 未动)+ G4 红(产物改后 ⇒ 门 UNAVAILABLE「changed since the receipt」)。真实数据: 10:29:58Z 新装置 verify-only 于旧产物 ⇒ **PASS**(`regate_f0x_CONTROLS.json` 5058f5f9, mode verify_only, self e89dcc7d)。

### F07 · P1 · 门与控制之间只有「路径」没有「身份」 — **成立, 已修(两轮)**
- **修**(`fp2_gate_lib.py` c7e6b76a + 两门): `bind_controls` 现在校验 **盘上 `fp2_controls.py` sha == 收据 self_sha256**、**每项 check ok==True**、**runs 恰为 {king, dl} 且 rc 0**、产物在本根内且 sha 未变、构建器 sha == 合同所选; `check_scope`: 门变体只在合同 `approved_variants[me].scope{V4_MONTH,R}` 指定的月与根下运行(realpath 比较); `bind_inputs_to_preflight`: 控制收据的 cache/panel_splice/panel_king/raw_patch 与 preflight `inputs` **同 realpath + 同字节数 + 盘上现 sha == 控制收据 sha**。
- **首版错误(如实记)**: 首版按 preflight 不存在的 `external_sha256[CACHE…]` 键绑定, 真实数据上把 STEP1/STEP2 判成 UNAVAILABLE(`regate_f0x_f0x_regate_attempt2_preflight_keys.log`)。这正是「合成夹具没按真实收据布局造」一族(AMENDMENT 6/8 同型), 修法 = 夹具 `preflight_for` 改写成真实布局(path+bytes, 无 sha), 再加红格 G10。
- **证**: 套件 18/18 —— G7 红(他根收据 ⇒ 「control output outside this root」)、G4 红、G5 红(preflight 钉了另一个构建器 sha)、**G10 红(preflight 声明另一份 CACHE 路径 ⇒ UNAVAILABLE 且点名 CACHE)**。真实数据(10:30Z): STEP1 **PASS** self 3ad3a6c6 · STEP2 **PASS** self bd8e04c7, `REFUSED` 为空(`regate_f0x_step1.json` 0d99769f / `step2` 62bdb51a)。
- **合同**: 变体 sha 每改一次刷新一次(9410a403 → 47717230 → 3ad3a6c6; a4cda6db → 984053e8 → bd8e04c7), **被取代的 sha 从批准列表移除**(缺 F06/F07 的旧门不得再被批准)并记 `superseded_variant_sha256`; `requires.fp2_gate_lib.py` = c7e6b76a。pipeline 套件 482/482(含 r1 前身 1188267a 的字节重建格 [T]/[U] 与归档合同自洽格 [r5→r6])。

### F03 · P1 · 判官没有实现新的非劣性判据 — **成立, 已实现为独立装置**
- **辩证**: `judge_v4.py` 的 (A)/(B)/(C) 规则与 2025-03→2026-08 冻结窗是另一道题(r20 出口门体系), 改写它会破坏其收据链; 正确做法是**在其上加决策装置**, 判官只作信息。
- **修**: `fp2_decision.py` fd270e9e, AMENDMENT 7 逐字: G1′ 四格(W_ALPHA/KING_LIVE × s42/s2027, dyn)—— 任一上界 < −δ ⇒ WORSE; 四格下界 > 0 ⇒ BETTER; 四格下界 > −δ ⇒ NONINFERIOR; 其余 UNDECIDED; **缺任一格 ⇒ UNAVAILABLE, 不从三格推断**。G2 机器规则(复审 Q9 要求): 对每个种子分别取「dg < −δ 的年」, 两种子都须「年数 ≤ 1 且不含 2026」。G3: 出口门 v2 收据 PASS 且 `arm == EXPORT_ARM`。建议 = G1′∈{NONINFERIOR,BETTER} ∧ G2 ∧ G3; 逐年表 VERDICT≠PASS 或出口收据缺 ⇒ UNAVAILABLE。δ 为参数(默认 0.05)。
- **证**: `tests_fp2_decision.py` 14/14 —— **T1 [−0.01,+0.10] ⇒ NONINFERIOR; T2 [−0.06,−0.01] ⇒ UNDECIDED; T3 [−0.04,−0.01] ⇒ NONINFERIOR**(复审三例)+ WORSE/BETTER/缺种子 UNAVAILABLE/G2 两劣年/劣年为 2026/出口 PASS=false/出口缺/出口绑他臂/逐年表 PARTIAL/δ 参数化。
- **接线**: 运行器 `chain_fp2_run.sh` 新增 `per_year`(前置 A0 同掩码重跑收据 PASS + A1 ARMS_DONE)与 `decision` 阶段; 本次重启的运行器已带这两个阶段。
- **δ 的经济意义(复审 Q9)**: 0.05 bps/锚/gross × 2190 锚 × 2 gross ≈ 2.2% NAV/年的容忍带; 这是 SPEC §7 既定值, 本轮不改; 是否收紧待用户裁定, 且必须在看数字前。

### F05 · P1 · 面板重建把「无源名照抄旧面板」也标成 REPRODUCED — **成立, 已修**
- **逐代码核**: `fx_fnd_hol_rebuild_v2.build_funding` 里 `out` 以 INC 副本初始化, `if ft is None: continue` 留下副本; 随后 `c2_compare_columns(..., rebuilt_from_stream=set(FUND))` 对全列判 REPRODUCED。复审对: 一个「全拷贝」也能读成「全部复现」。
- **修**: `fnd_hol_checks.c2_compare_columns_sourced(…, has_source)` 只在有源名上比较; 无源名计数、列名(≤200)并判 `COPIED_NO_SOURCE`, `independent_rebuild_partial=True`; 全无源 ⇒ 每列 `UNAVAILABLE_NO_SOURCED_SYMBOL`。调用方记录 `has_source` 掩码, 新增检查 C2b。
- **证**: `tests_fnd_hol_checks.py` 20/20 —— 三反例(无源名拷贝相同 / 有限改值 / 全 NaN)均: 有源名 REPRODUCED、3 名 COPIED_NO_SOURCE、比较只在 3 名上; 有源名差 1e-7 ⇒ DIFFERS(无源拷贝掩不住); 全无源 ⇒ UNAVAILABLE。**注**: 真实 FP2-1 重建尚未用新装置重跑; 其收据里的 REPRODUCED 判词在重跑前**降级为「有源名部分未知」**(验收表另记)。

### F06 · P2 · 「子集 + 被删者掩码 False」放过「掩码根本没应用」的产物 — **成立, 已修**
- **辩证**: 复审的正负控是对的: 成员集与控制**完全相同**的构建满足「子集」且「无被删者」⇒ 旧规则 PASS。同时复审也指出「简单要求 = 参照 ∩ mask」也不成立(先 mask 再 top-400 与 MIN_MEM 使正确对象不是交集)—— 与 AMENDMENT 8 一致。
- **修**(`members_subset_check`): 新增 (i) **保留成员全为掩码 True**(`retained_not_mask_true_rows/cells`); (ii) **被删锚可解释**: 控制行掩码 True 成员数 < MIN_MEM(50), 否则 `dropped_unexplained_rows`; 无控制轴掩码行 ⇒ `dropped_unverified_rows`(FAIL, 不假定可解释)。两门传 `MASK_c`; `build_dev_v4` 自检改为**复用同一实现**(其原「子集」规则会把真实 109 个截断补位行在 arms 阶段判 FAIL)。
- **证**: 套件 F06-0(基线绿)/F06-1 红(忽略掩码 ⇒ retained 3 行 30 格 FAIL)/F06-2 红(丢锚而控制行有 50 个掩码 True ⇒ FAIL)/F06-3(只 10 个 True ⇒ 可解释 PASS)/F06-4(无控制轴掩码 ⇒ UNVERIFIED FAIL)。真实数据(10:30Z, 10,212 锚同轴): 减 1,338 行/2,377 格全掩码 False; 增 109 行/146 格全在截断行且掩码 True; **retained_not_mask_true 0 行 0 格; dropped 0**; STEP1/STEP2 PASS。

### F08 · P2 · 「C1/C3/C6 不在我方数据」超出三探针能证明的范围 — **成立(作为范围反例), 已量化并降级**
- **辩证**: 复审给的是形式反例(改旧代区间 15 列特征), 不是真实污染的确认; 复审自己也写「真实命中与经济影响 UNAVAILABLE」。我方的正确回应是**测量**而不是争辩。
- **装置**: `fp2_open_window_exposure.py`(只读): 对 13 个 OPEN 事件 × 48h/7d/30d 窗口, 数「该名在 OPEN 后 H 内是训练成员的锚数」(king meta 与 DL targets 两套成员集)。**首版错误(如实记)**: king meta 无 symbols 轴, 首版取了它的 82 个特征 `names` 当符号轴 ⇒ 13 名全「不在轴上」; 修为借 DL targets 的缓存轴并记来源、越界拒绝(套件 E1/E5)。
- **真实读数**(`FP2_receipts/OPEN_WINDOW_EXPOSURE_2026-09-17.json`): 48h 内 **0**; 7d 内 **40** 锚; 30d 内 **1,771** 锚(占 2,751,058 成员格 **0.064%**); 首次入成员 ≈161h(≈6.7 d, 成员规则的 7 日尾窗所致; PUMPUSDT 104.5h, 7d 内 16); king 与 DL 读数相同(同成员规则)。
- **结论与登记**: §2.2「C6 无需进链」降级为「首根不跳价已证; 7d/30d 窗口暴露已量化(0.064% 成员格); **经济影响 UNAVAILABLE**」; 计划 = 十月链成员掩码加 **OPEN 后 30 天屏蔽**(预注册, 另一次干预, 不在本链改)。

### F09 · P2 · maxDD 日末采样漏掉日内亏损 — **成立, 已修**
- **修**: 主口径 `maxdd_L` = 逐锚复利 NAV(L=2)的 min(NAV/cummax−1); 日末采样降为 `maxdd_L_dayend` 次口径; md 表两列并列。
- **证**: Y2b —— 1 → 1.1 → 1 在一个 UTC 日内: 逐锚 **−9.0909%**, 日末 **0.00%**(复审反例逐位复现); Y2 常数序列闭式仍通过。

### F10 · P2 · 逐年表输入门与 W_ALPHA 定义 — **成立, 已修**
- **修**: 输入门 —— 两臂 `UMASK_NPZ` 同路径且文件 sha 相同(且 == 合同 umask sha 若给出)、`gross_total` 有限正、symbols 轴相同、4h 无缝网格; W_ALPHA 起点钉 **2022-06-30 00Z**(ts[900] 必须等于它, 否则 UNAVAILABLE; 「第 900 行」不再是定义)。
- **证**: Y6(不同 umask 文件 ⇒ A1 UNAVAILABLE 点名 UMASK_NPZ)、Y7(gross −2 ⇒ UNAVAILABLE)、Y8(钉错时间 ⇒ UNAVAILABLE; Y8b 钉对 ⇒ PASS 基线)。

### 复审 Q1–Q10 表中其它判定(简答)
- Q6 `run_arm.sh` 应入装置并由 D 分发 — 成立; 本轮未做(FP2 副本 f30b2c7c 仍是发布闭包外部件), 登记为 FP2-8 后续项。
- Q8 K3 判据 — 复审「新 K3 整体跳过 fund 列不能区分预期 NaN 与异常缺失」成立; 本轮未再改判据(会再动合同), 登记: 十月链前把 fund 列的 NaN 限定在「面板首行之前」的行, 其它行仍要求有限。
- Q10 king pin 部署 — 「160/1/0 不能改称全绿」成立; 本方从未称全绿; 1 红 = `tests_entrypoint_wiring`(生产与克隆同红, 树外), 见 §3。

## 2. 事故(如实): E-0917-A
10:26:35Z 我在 pod2 用按脚本名的 `pgrep … | kill -KILL` 清理复门残留, 模式 `chain_v4_monthly` 命中了在飞运行器的 mwf 阶段驱动 ⇒ 运行器 `FAIL_stage_mwf_rc_137`。实际代价小(运气): RAW s42 四分片已于 10:24:36–10:26:37Z 全部 `END rc=0`, 训练器按折续跑; 10:45:14Z 从 `mwf` 重启运行器(pid/pgid 941438, `$R/RUNNER2.pgid`), 10:46:01Z s42 秒级跳过并 MERGE_DONE, s2027 开始训练(GPU 82%)。分片日志重启前已复制保留。规则入错题与记忆: 只按记录的 PGID 杀, 禁止按驱动名扫杀。

## 3. 当前状态与还差什么
- **在飞**: 运行器 2 阶段 `mwf(s2027) → refit → np_export → arms(A1, 修复版 run_v4_arms.sh) → a0rerun(A0 同掩码) → judge → export → per_year → decision`; 预计 s2027 ≈40 min, 其后各阶段合计 1–2 h。**书层数字尚未产出, 本文不含任何 Δg。**
- **判据冻结**: G1′/G2/G3 已实现为装置且套件化(先于数字); 出数后只读 `$R/v4_gates/DECISION_FP2.{json,md}`, 不改判据。
- **未完成(登记)**: FP2-1 真实重建用 F05 新装置重跑; Q6 `run_arm.sh` 入装置; Q8 K3 判据细化(十月链前); 十月链 OPEN 后 30 天屏蔽(预注册); FP2-6b(DL F10 sha 钉)三步仍按 12:24Z 锚后部署读者 → 生产者补丁排练 → 设钉。
- **请独立研究员复审**: 本文 §1 每条的「证」与真实数据收据(`FP2_receipts/regate_f0x_*`), 特别是 F07 的两轮(首版为何错、修后为何对)与 F08 的读数解释。
