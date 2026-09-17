# FP2 独立复审二轮(e0ddd4cc, R01–R11)的逐条回应与修复 — 2026-09-17

> **创建:** 2026-09-17 11:5xZ | **Session:** b9646a9e(主研究员) | **状态:** R01–R11 全部修复并提交(§0); 真实数据: 成员规则精确核 PASS, 门重跑 PASS; 全链运行器 3 自 np_export 重启在飞; **书层数字仍未产出** | **作废条件:** 独立研究员再复审推翻任一修复; 或出数后判据被改写(不允许)
> **复审件:** `git show e0ddd4cc:docs/fixprogram_2026-09-13/REVIEW_FP2_RESPONSE_codex_independent_2026-09-17.md`。复审总判「不能接受『全部代码级修复并在真实数据上重验』这个总括」——**接受**: 上轮回应的总括句超出了其证据; 本文按复审 §7 的依赖顺序逐项收口, 每项给修前/修后同输入证据, 并标明真实数据上什么已验、什么仍 UNAVAILABLE。

## 0. 提交链(研究分支, 显式 pathspec)

| # | 提交 | 内容 |
|---|---|---|
| r2-c1 | `5a4abdbb` | R01/R02 FP2-1 面板重建(namedtuple + 按名×列×行实写掩码; 30/30) |
| r2-c2 | `2ae1a171` | R09 成员规则精确核 + 套件 MR1–MR7 + **真实收据 PASS** |
| r2-c3 | `f3037a89` | R05/R06/R08 逐年表(17/17) |
| r2-c4 | `4edb813d` | R04/R05/R06/R08 决策装置 formal profile + 身份闭包(33/33) |
| r2-c5 | `a49b92fe` | E-0917-B np 导出器临时名 + 回归 3/3 + 错题 |
| r2-c6 | `8c46eaeb` | R11(续) 陈旧断言 M4/M5 → 5/5 |
| r2-c7 | `1778ee0f` | AMENDMENT 10 + 验收表 + runbook 修订 11 |
| r2-c8 | `b48eac83` | R03/R07/R10/R11 lib/controls/runner/合同/清单(gates 25/25, pipeline 482/482) |
| r2-c9 | 本文 + 第二次门重跑收据 `FP2_receipts/regate2_*` | |
| 待提交 | `chain_v4_monthly.sh` require 加 `recorded_extras=1`(R03 第二入口) | pipeline 套件跑完且**在飞链结束后**再同步(后续阶段调用驱动) |

## 1. 逐条

### R01 [P1] p9 调用接错返回值 — **成立, 已修**
`build_funding` 返回 `FundBuild(out, agg, has_source, rebuilt)`; 两处调用改属性访问; 套件加 AST 消费者普查(恰 2 处调用, 无元组解包)。**限定**: 装置整件仍未在真实 FX 数据上重跑(需 pod2 FX 目录), FP2-1 真实收据保持降级(验收表注记)。

### R02 [P1] 有源无种子的 EMA 拷贝自比 — **成立, 已修(按名×列×行)**
逐字块语义核实(`r6_panel_splice.py` cccc5b6b L101–120): v1 种子缺 ⇒ `n_noseed += 1; continue`, 三列 EMA 一格不写; v0/v1 有种子则每尾行写; v2 无种子则按行部分写。修法: 块前把三列 EMA 尾格填非规范负载 NaN 哨兵, 块后读「实写格」得到 `rebuilt[col]`(尾行 × 名), 未写格恢复 INC 拷贝并**只在实写格上比较**; 有源无种子名在三列下记 `COPIED_NO_SEED`, v2 部分名记 partial。复审反例(两条 8h 事件、CAN 种子 NaN、INC 三 EMA 尾值改 0.001/0.004)现在: 该名三列不比较、被点名、partial=True; 有种子正控 80/80 格比较。30/30。

### R03 [P1] 批准依赖未消费 / preflight 未钉 helper / require 不复核控制收据 — **成立, 已修两处, 一处待同步**
- `check_scope` 现在**执行**批准: 运行中的门文件 sha == 合同变体 sha; 合同 `requires` 的每个 helper 盘上 sha == 记录值; 无 `requires` 拒跑。证据: 套件在陈旧合同(requires 仍记旧 lib)上先跑出 6 格拒绝「required helper fp2_gate_lib.py on disk e98b15b0 != contract requires c7e6b76a」, 合同刷新后 25/25 —— 这正是复审要的行为。
- 复审反例「门过后给 CONTROLS.json 加空格, require 仍 OK」: 修法 = 驱动 6 处 `require_gate` 加 `recorded_extras=1`(收据记录的全部输入按其 inputs_path 逐个复哈希); 已改本地 `chain_v4_monthly.sh` 并跑 pipeline 套件, **在飞链结束前不同步**(后续阶段调用驱动)。
- preflight 钉 controls/helper: 未改驱动 DEV_FILES(同上理由); 替代绑定 = 门收据记 lib 为输入 + `check_scope` 执行 requires + 决策装置绑定 D 内装置 sha。登记为链后项。

### R04 [P1] 决策接受裸 PASS — **成立, 已修(身份闭包)**
决策装置(`fp2_decision.py` 474c7969)现在要求: 逐年表在 `R/v4_gates` 下、由 D 内 `fp2_per_year_table.py` 写出(self_sha256)、VERDICT PASS、umask == `EXPECTED_UMASK`、每条臂记录 sha == 盘上现值; 出口收据在 `R/v4_gates` 下、臂 == A1、PASS 且无败项、由 D 内 `v4e_gate_export_v2.py` 写出且该 sha 在合同 `BUNDLE_export` 批准表、`contract_sha256` == D 内合同、其 `book_/base_` 输入与逐年表四书**同路径同 sha**; 成员规则收据 PASS 且其 masked king meta == 出口门哈希的 bundle meta、masked DL targets == STEP1 哈希; 判官只作信息。复审反例(裸 `{PASS,arm}`、伪表、错门源、错合同、他书、成员规则 FAIL…)12 格全 UNAVAILABLE, 正控 SWAP_RECOMMENDED。

### R05 [P1] Inf/NaN 沿表进决策变 BETTER — **成立, 已修两端**
逐年表: g/pnl/carry/cost/换手/净多任一格非有限 ⇒ 该臂 UNAVAILABLE(Y11: +Inf 一行 ⇒ 'g not finite on 1 rows'); 决策: 每格 dg/CI 有限、lo ≤ hi、n>0、n_days>0, 逐年 dg 有限(R05a Inf 格 / R05b NaN 2026 / R05c lo>hi ⇒ UNAVAILABLE)。

### R06 [P1] 缺整个 2026 仍「2026 不坏」 — **成立, 已修两端**
逐年表 `coverage`(ts_min/ts_max/UB/reaches_UB/years), 数据未达冻结 UB(默认 2026-08-30 20Z)⇒ UNAVAILABLE(Y9); 决策要求 `reaches_UB` 且 by_year 年份自首年到 CURRENT_YEAR **连续**(R06a 缺 2026 / R06c 缺 2023 ⇒ UNAVAILABLE)。

### R07 [P2] VERIFY_ONLY 漏第四个产物 — **成立, 已修**
按前次收据 `outputs_path` 的**全部**键复哈希(含 control_dl_report)。真实数据 11:46Z verify-only: `inputs_changed [] / outputs_changed []` ⇒ PASS(`regate2_CONTROLS.json`)。

### R08 [P2] 标签代替实物(种子/掩码/参数缩格) — **成立, 已修**
逐年表: cfg `FSEED` 必须等于文件名种子(Y10); 掩码符号轴**有序**相等且覆盖全部锚(Y12 反序 / Y13 缺行 ⇒ UNAVAILABLE)。决策: formal profile 冻结(种子 42,2027 / 窗 W_ALPHA,KING_LIVE / dyn / δ 0.05 / A1 / 2026), 任何覆盖 ⇒ `REFUSED_PROFILE`(R08a SEEDS=42, R08b DELTA=inf); exploratory 只能给 `EXPLORATORY_NO_RECOMMENDATION`(R08c)。

### R09 [P2] mask-True ≠ 应选 Top400; 少/多/错名、错删锚可过 — **成立, 已修; 真实数据 PASS**
新装置 `fp2_member_rule_check.py`(396f6a51): 从缓存按**两构建器各自公式**(king: n7=log_qv 有限数、y4 行 [E,E+48); targets: nfin=ret5 有限数、y4s=expm1Σlog1p 行 [E+1,E+48] 且应用原始返还补丁)重算资格与 qvm, 先要求无掩码复刻逐锚 == 控制构建(把复刻绑到真构建器), 再要求掩码构建逐锚 == 「规则∧掩码→top-400→≥50」精确集与锚轴。合成 430 名夹具: 少 1 名(399)/错 1 名(400)/多 1 名(401)/错删锚/控制被改 ⇒ 全 FAIL(MR3–MR7), 正控 PASS(MR1/MR2)。**真实数据(11:47Z, 423 s)**: king 与 DL 各 10,212 锚 —— 控制复刻精确(轴同、0 行异), 掩码集精确(0 行异), 截断行 2,887, 预期删锚 0, 最小掩码池 135。收据 `FP2_receipts/MEMBER_RULE_CHECK_2026-09-17.json`(9e2e1377)。⇒ 复审的「真实 109 个补位锚是否按确切排名正确」**已独立核对: 是**。运行器新增 `member_rule` 阶段, 决策绑定其收据与 bundle meta / STEP1 targets。

### R10 [P2] 默认 STAGES 不含 per_year/decision — **成立, 已修**
默认串以 `member_rule per_year decision` 结尾; runbook 修订 11。

### R11 [P2] A0 重跑收据拒绝幂等复跑; 陈旧测试 — **成立, 已修**
收据改为「rc 0 + ARMS_DONE + 每件工件由本次运行写出(mtime ≥ 起跑)且 cfg.UMASK_NPZ == 本掩码」, before/after sha 只作信息; `tests_build_dev_v4_mask` M4/M5 改共享收据键(5/5)。

### F08 读法(复审 §5) — **接受**
0.064% 是成员格频数, 不是影响上界; 30 天屏蔽不清 EMA 旧状态(原资金费 EMA 无 OPEN 重置)。登记: 十月链前按 generation 明确状态来源 + 旧代扰动 null; 经济影响 UNAVAILABLE 不变。

## 2. 运行中新事故 E-0917-B(与复审无关, 如实记)
11:42:58Z np_export s42 rc 1: 导出器原子写 `tmp = NP_OUT + ".tmp"` 被 numpy 补成 `.tmp.npz`, `os.replace` 失败(V1 谱相关已 PASS 之后); 九月链用 r0 版从未跑过此路径。修: 临时名 `<out>.tmp.npz` + 写后断言; 回归 `tests_np_export_tmpwrite.py`(AST 抽出写块逐字执行 + 修前语句红能力)3/3; 残留文件移作收据。

## 3. 真实数据现状(本文发出时)
- 门(第二次重跑, 装置最终版): controls verify-only PASS(d5672fc2, 全产物绑定); STEP1 PASS 11:46:55Z / STEP2 PASS 11:54:17Z(`regate2_*` 收据)。
- 成员规则精确核 PASS(上文)。
- 运行器 3 于 11:5xZ 自 `np_export` 重启, 阶段 `np_export arms a0rerun judge export member_rule per_year decision`(pgid 见 `$R/RUNNER3.pgid`)。**书层数字未产出**; 出数后只读 `DECISION_FP2.{json,md}`(formal profile), 其 UNAVAILABLE 原因逐条如实报。
- 仍未关: FP2-1 真实重建(新装置)、驱动 `recorded_extras` 同步与 preflight 钉 helper(链后)、K3 细化、`run_arm.sh` 入装置、生命周期现金核账、F08 经济影响。**换装认证在这些之前不成立**, 与复审一致。
