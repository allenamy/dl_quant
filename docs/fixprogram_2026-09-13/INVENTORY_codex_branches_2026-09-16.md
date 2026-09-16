> **创建:** 2026-09-16 | **Session:** codex-inventory | **状态:** final(只读清点, 无合并/无修改) | **作废条件:** 11 条分支任一 HEAD 移动、或 `.claude/worktrees/codex-independent-20260907/` 工作树内容变化、或本件所钉 sha 任一不再匹配。

# 独立研究员(codex)11 条分支只读清点

**清点方式**: 全程 `git log/show/diff/ls-tree` + 只读磁盘 `cat/sed/shasum`。**没有 checkout, 没有 add, 没有 commit, 没有跑任何装置。** 本仓分支 `research/book-uplift-2026-09-11` 全程未被切换(清点开始时 HEAD=`ff730bcb`;期间 HEAD 有前移, 是其他 agent 在并行提交, 不是我 —— 我没有 add/commit 过任何东西)。

**两栏纪律**: 「它声称」= 从它的提交信息/文档里抄的话。「我核实了」= 我打开源码或产物, 逐条对上的。没打开的一律进「它声称」。

---

## 0. 先说三件最要紧的

1. **11 条分支不是 11 条独立工作线, 是一条链上的 9 个书签 + 2 条支线。** 25,084 个文件 / 2,461 万行(占全部体量的 96%)是 **11 条分支共有的** trunk(`0c65883b..1fd02c7f`)。各分支自己新增的只有 24–2,636 个文件。
2. **608 天回放的证据链被切成三段, 分别落在三条互不包含的分支上, 而最关键的三样东西一条分支都没有。** 拿着 `codex/fullchain-continuation-20260914` 单独 checkout, **算不出它自己报的 2.523**: 统计内核在 #3、回放 runner 和现金引擎在 #2、**逐笔核算原件(报告唯一的数字来源)和定义交易宇宙的那本日历在 0 条分支上**, 只活在 `.claude/worktrees/codex-independent-20260907/` 的未跟踪文件里(§3.6 / §3.7, 实测目录计数, 不是推断)。那个 worktree 一清, 2.523 就再也对不回去。
3. **它自己没有把 2.523 说成实盘业绩。** `docs/RESULT_current_strategy_replay_2026-09-15.md` 第 8 行原话: 「**结果是盈利, 但目前不能称为"线上固定模型、全部真实执行与停复场动作的严格历史业绩"**」。它列了 5 条明确缺口。评估这批工作时, 争议点不在它有没有吹牛, 在于**这一格是从一个 126 格预注册网格里挑出来交付的唯一一格**(§4.3)。

---

## 1. 分支拓扑(实测, 不是推断)

与本仓 merge-base 一律是 `0c65883b`(2026-09-07 18:05 `RESULT §2.4 完成: M1/T400 功效补全`)。11 条分支彼此的 merge-base 全部落在同一条链上, 用 `git merge-base --is-ancestor` 逐对验过(14/14 与下图一致):

```
0c65883b  ← 我们的分叉点 (09-07)
   │
   ├── … 共享 trunk (25,084 files / 24,615,728+) …
   │
  ec16cbb0 (09-14 14:52  Bind raw targets to verified contract generations…)
   │     └──► 43643e83  codex/causal-producer-generation-20260914      [+12 commits]
   │
  cbd4a5ae (09-14 22:27  Bind official funding audit to fixed cash replay…)
   │     └──► fed0f391  codex/known89-data-20260914                    [+1 commit]
   │
  1fd02c7f (09-14 23:03  Bind isolated cash capsule paths…)
   │     └──► 8990ebd3  codex/fullchain-continuation-20260914          [+32 commits]  ★608 天回放报告
   │
  d0d82862 = agent/codex/QNT-2026-0907/onboarding-audit (09-14 23:28)  ← 本地 worktree 停在这
   │        (这是那个 codex 工作树当前的 HEAD; 也是下面两条支线的分叉点)
   │
   ├─► a90dc829  codex/raw-month-repair-20260915                       [+2]
   │      └─► 6e6f5dc6  codex/public-funding-evidence-20260915         [+30]  ★回放 runner + 现金引擎
   │
   └─► 5517eeeb  codex/f10-lifecycle-four-stage-20260915               [+1]
          └─► 9528b908  codex/f10-fullaxis-provider-controls-20260915  [+1]
                 └─► 86dd0c8f  codex/f10-fullaxis-conditional-20260915 [+1]
                        └─► 9fb7a527  codex/f10-assessment-review-20260915  [+1]
                               └─► 4dca09cf  codex/f10-fullaxis-readback-20260915  [+28]  ★统计内核 + 模型身份
```

关键: **`8990ebd3`(fullchain)不包含 `d0d82862`**(`git merge-base --is-ancestor d0d82862 8990ebd3` → 否)。即报告分支和 runner/统计所在的两条支线是**平行**的, 不是前后接续。

---

## 2. 逐条分支表

「独有」= 相对该分支自己的分叉点(上图), 不含共享 trunk。

| # | 分支 | HEAD | 总 commit<br>(vs 0c65883b) | 独有<br>commit | 独有 diffstat<br>(files / +) | 层 |
|---|---|---|---|---|---|---|
| 1 | `codex/fullchain-continuation-20260914` | 8990ebd3 | 243 | 32 | 973 / 530,383 | 评估·对账·文档 |
| 2 | `codex/public-funding-evidence-20260915` | 6e6f5dc6 | 244 | 30 | 1,762 / 1,218,795 | 数据·口径·serving(回放执行器) |
| 3 | `codex/f10-fullaxis-readback-20260915` | 4dca09cf | 244 | 28 | 2,636 / 1,968,294 | 训练·评估·对账 |
| 4 | `codex/f10-assessment-review-20260915` | 9fb7a527 | 216 | 1 | 24 / 927 | 对账 |
| 5 | `codex/f10-fullaxis-conditional-20260915` | 86dd0c8f | 215 | 1 | 433 / 23,545 | 特征·训练 |
| 6 | `codex/f10-fullaxis-provider-controls-20260915` | 9528b908 | 214 | 1 | 69 / 2,695 | 对账 |
| 7 | `codex/raw-month-repair-20260915` | a90dc829 | 214 | 2 | 190 / 45,117 | **数据(真值)** |
| 8 | `codex/f10-lifecycle-four-stage-20260915` | 5517eeeb | 213 | 1 | 461 / 43,807 | 训练 |
| 9 | `codex/causal-producer-generation-20260914` | 43643e83 | 171 | 12 | 1,212 / 200,872 | 数据·特征 |
| 10 | `codex/known89-data-20260914` | fed0f391 | 207 | 1 | 195 / 88,578 | **数据(人口)** |
| 11 | `agent/codex/QNT-2026-0907/onboarding-audit` | d0d82862 | 212 | 1 | 59 / 4,465 | 数据·基建 |

**目录热点**: 11 条分支的每一条, 独有改动都 **≥99% 落在 `multi_asset/exports/research/codex_causal_fullchain_2026-09-14/`** 一个目录下。`docs/` 下全部 11 条分支加起来**只新增了 1 个文件**: `docs/RESULT_current_strategy_replay_2026-09-15.md`(在 #1, 104 行)。其余 docs(`REPAIR_fixprogram_independent_2026-09-14.md`、`REVIEW_*`、`VALIDATION_*`、`HANDOFF_*` 共 24 个 + `AGENTS.md`)都在**共享 trunk** 里, 11 条分支全都有, 不是任何一条的新增。

### ⚠ `AGENTS.md`: 合并任何一条分支都会带进来的 59 行工作约定

共享 trunk 把 `AGENTS.md` 从旧的单资产/y600 版改成了 codex 独立分支版(**+59 / −1**, `git diff --stat 0c65883b..1fd02c7f -- AGENTS.md`)。**11 条分支全带这个改动。** 它在原文件顶部插入了一整套 codex 自己的工作约定, 并把原「当前进度(滚动更新)」改标题为「历史阶段进度(2026-05, 非当前)」。要点(**我读了 diff 全文**):

- **它给自己定的研究目标**: 「Binance USDT-perp **整书扣除实际费用后的跨历史 Sharpe >3**, 显著改善回撤、尾部风险与响应时效」;并写「用户报告现有整书 Sharpe 约 2」。⇒ **交付的 2.523 低于它自己的目标门, CI 上界 4.18 跨过门。** 这个背景对读 §4.3 很重要。
- **隔离硬约束**: 只在 `.claude/worktrees/codex-independent-20260907` 写;`~/wide_shadow`、`~/dl_quant_live`、guard_twin **只读**;禁止重训覆盖生产权重、重启服务、发交易指令、改杠杆/保证金、转账、自动合并/部署;实盘 API 必须用**交易所侧仅只读**的独立凭据。
- **它自己写下的、与 §4.3 直接冲突的两条**:
  - 「记录尝试总数, 使用配对时间块不确定性、**多重选择控制**和独立种子, **种子不是独立市场样本**」
  - 「**整月内抽近整月长块会形成过窄的条件区间, 必须解释**;探索后补的稳健性区间不能悄悄取代原登记主门」
  ⇒ **它的约定要求多重选择控制, 它交付的 CI 明写没有多重选择控制。** 这不是我扣它帽子, 是它自己两份文件对不上。
- 它还自行写进了几条与我们受据同源的纪律(可对照): 「当前缓存 **±30% 裁剪**可把实际暴跌写成上涨」(= 我们的 `[[cache_ret5_channel_clipped_at_0p30_2026_09_12]]` / E-0908-B)、「**档案覆盖不是交易资格**, 月 ZIP 或日 ZIP 的 404 不能推导整月不可交易」(= `[[dead_contracts_frozen_rows_in_research_data]]`)、「完成收据是判读的前置输入……留下部分 NPZ 不代表推理或训练成功」。

**结论**: `AGENTS.md` 不是无害的元数据。合并任一分支 = 把这份 59 行约定写进仓库根, 它与 `CLAUDE.md` 的关系(补充? 覆盖? 冲突?)**需要单独裁定, 不应随 exports 一起悄悄进来**。

### 它声称修了什么(引自它自己的提交信息 / 文档)

| # | 分支 | 它声称(带出处 sha) |
|---|---|---|
| 1 | fullchain-continuation | 「Complete current-model 608-day conditional replay report; **distinguish actual fees and deployed models**」(`8990ebd3`)。「Handle **E60 funding before reduce-only exits** with endpoint coverage guard」(`a23e37b3`)。「Confirm **legacy 0.02 IC** on matched repaired targets」(`8cda9c09`)。 |
| 2 | public-funding-evidence | 「Complete current main **mark valuation replay** and independent accounting evidence」(`6e6f5dc6`)。「**Preserve public funding evidence** and strict cash-only adapter」(`4d10a5e6`)。「Bind approved **E60 funding endpoint risk successor** to current cash runner」(`79affdab`)。「Preserve bounded AERGO static rechecks and **refusal to impute missing bars**」(`68db9d4f`)。 |
| 3 | f10-fullaxis-readback | 「Record actual current20 four-stage and full readback; deliver accepted **King0 seed42 prediction bridge**」(`4dca09cf`)。「**Pin current deployed model bytes** and distinguish current training policy from research folds」(`45b6051f`)。「Add **source-only compound NAV statistics**」(`ab3ebdb8`)。「Review actual executor source path and **publish isolated pure policy API**」(`493b7dec`)。 |
| 4 | f10-assessment-review | 「**Independently review** fullaxis cash assessment source admission」(`9fb7a527`)。 |
| 5 | f10-fullaxis-conditional | 「Bind approved fullaxis provider, **conditional F10 pipeline** and prediction reader」(`86dd0c8f`)。 |
| 6 | f10-fullaxis-provider-controls | 「**Freeze** fullaxis provider CPU controls and actual repaired-input WAIT」(`9528b908`)。 |
| 7 | raw-month-repair | 「Add **verified three-month raw repair** and immutable canonical closure」(`f849852e`)。「**Restore exact December2024 history archives** from verified local backup」(`a90dc829`)。报告原话: 「All **24,768 missing raw bars** and three next observed ret5 connections were repaired. Exactly **173,368 channel cells changed** inside declared support; every outside-support cell remains **bitwise equal**」(`REPAIR_REPORT_20260915.md`)。 |
| 8 | f10-lifecycle-four-stage | 「Add **lifecycle-bound F10 four-stage adapter** and actual CPU controls」(`5517eeeb`)。 |
| 9 | causal-producer-generation | 「**Repair producer generation and current-bar inputs** with bounded shared cache」(`6a8be1ba`)。「Repair **generation feature context** and bind expanded lifecycle registry」(`3c040da2`)。「**Audit unregistered held activity** against original public klines」(`d49cb9bf`)。「Audit **AERGO July funding and event-price archive gaps**」(`43643e83`)。 |
| 10 | known89-data | 「Bind **89 known instrument lifecycles** and rebuild raw targets and funding」(`fed0f391`)。计划书原话: 「公告核对发现旧构建器**仅提取旧审计人口中的名字**。同一十篇公告与完整 829 名轴的差集是 **30 名**: 先由**实际持仓尾部**发现 17 名, 再补 13 名同篇但不要求持有的名字」(`plans/LIFECYCLE_CORRECTION_2026-09-14.md`)。 |
| 11 | onboarding-audit | 「Add **causal lifecycle path state repair** and verified runtime hook」(`d0d82862`)。 |

### 有没有受据(独有范围内的文件计数, 我实测)

| 分支 | PREREG | 文件名含 RED | 含 GREEN | 零控制 | REPORT.md | RESULT.json |
|---|---:|---:|---:|---:|---:|---:|
| fullchain | 2 | 27 | 11 | 0 | 2 | 80 |
| public-funding | 0 | 73 | 18 | 3 | 6 | 53 |
| readback | 3 | 103 | 18 | 0 | 13 | 106 |
| causal-producer | 0 | 50 | 28 | 0 | 3 | 43 |
| raw-month | 0 | 4 | 4 | 0 | 0 | 5 |
| known89 | 0 | 0 | 0 | 0 | 0 | 2 |
| onboarding | 2 | 5 | 4 | 0 | 0 | 3 |
| f10-lifecycle | 0 | 1 | 0 | 0 | 0 | 28 |
| provider-ctl | 0 | 0 | 0 | 0 | 0 | 1 |
| conditional | 0 | 1 | 0 | 0 | 0 | 14 |
| assessment | 0 | 0 | 0 | 0 | 0 | 1 |

**读法警告**: 这是**文件名匹配的计数**, 不是「红测确实红过」的证明。我抽查了几组 `RED_EXIT.json` / `GREEN.log`(如 `integration/dynamic_nav_statistics_20260915/RED_EXIT.json` 与 `CONTROLS_EXIT.json`)确实是成对的先红后绿, 但**我没有逐个打开 300+ 个 RED 文件核对每个红都指向被修的那条路径**。按 `[[textual_instrument_for_a_behavioural_property]]`, 文件名不是行为证据。**`known89-data` 独有范围里 RED=0 / GREEN=0 / PREREG=0**——它是纯数据绑定提交, 没有自带红测。

**逐位控制**: 有, 而且是它们做得最扎实的一块。`raw-month-repair` 的 `REPAIR_REPORT_20260915.md` 报了「171,752,832 outside-support raw scalar cells were **bitwise equal**」;`fullchain` 的 `ACTUAL_HANDOFF.json` 报了 `prefix570.all_economic_fields_equal: true`(前 570 个日界经济字段与上一版逐字段相同)。**这两条我只读了它们的自报, 没有独立重算。**

### 分支之间的关系

- **同一条线的连续推进**: #8→#6→#5→#4→#3 是**严格线性**的五个书签(每步 1 个 commit, 最后 #3 加 28 个)。#7→#2 同理。这两条线只在 `d0d82862` 汇合。
- **互相冲突/重复**: 没有发现内容冲突——因为它们**几乎不改同一批文件**。#2(runner)、#3(统计内核)、#1(报告)三者的关键目录是**互斥**的(§3.6 表)。这不是巧合, 是同一个工作树按时间点打的书签, 每个书签只带走当时刚落盘的那一批。
- **#9 `causal-producer-generation` 是唯一真正的旁支**: 它从 `ec16cbb0`(09-14 14:52)分出, 内容一路到 09-14 23:17, 与 spine 上的 `cbd4a5ae`(22:27)/`1fd02c7f`(23:03)时间重叠但不互为祖先。**它有没有被 spine 收编, 我没能确定**(见 §6)。

---

## 3. A. 608 天回放到底用了什么输入

### 3.0 装置在哪

`docs/RESULT_current_strategy_replay_2026-09-15.md`(分支 #1, commit `8990ebd3`)引用的所有路径都指向
`/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/…`
——那是一个**真实存在的 git worktree**(`git worktree list` 确认), 停在 `d0d82862`。报告引的大部分文件**在该 worktree 里是未跟踪文件**, 不在任何分支上(§3.6 / §3.7)。

生成链(我逐层打开核实):

```
runner  = book/dynamic_frame_inputs_20260915/current_rule_mark_valuation_20260915/bootstrap_entry.py
          （argv 与 12 个源码 sha 钉死在 current_rule_mark_cash_audit_20260915/RUNNER_CONTRACT.json）
   ↓ 产出 completed/nohalt_current_main/audit1/{RESULT,DAILY_AGGREGATES,MARK_AGGREGATES}.json
报告  = integration/current_metrics_20260915/complete_report.py
   ↓ 载入 integration/current_metrics_20260915/current_metrics.py (sha 钉 cd3f4303…)
   ↓ 载入 integration/dynamic_nav_statistics_20260915/successor1/nav_statistics.py (sha 钉 6bd2e2c8…)
   ↓ 写出 complete_main_20260915/RESULT.json (sha 4c1ef4b2…)
```

**我核实了的 sha(逐个 `shasum -a 256` 跑过)**:

| 文件 | 声称 sha | 实测 | 结论 |
|---|---|---|---|
| `complete_main_20260915/RESULT.json`(git, 分支#1) | `4c1ef4b2…` | `4c1ef4b28ee6bbbd9ec7341005ea704710d915e1d8cfcaecf6759d32e96282db` | ✅ |
| `current_metrics.py`(git, 分支#1) | `cd3f4303…`(被 `complete_report.py:53` 钉) | `cd3f4303e92cb0e3db82d8754f3da622bc481cbc0966b2813233482661aa3ef9` | ✅ |
| `nav_statistics.py`(磁盘 worktree, **不在 git**) | `6bd2e2c8…`(被 `current_metrics.py:11` 钉) | `6bd2e2c8f0f0e3e6ed05b808d267721e67e6cc7dee2aa4ae1e775d766079f25d` | ✅ |
| `successor1/source/legacy_statistics.py`(磁盘, **不在 git**) | `2aaa51f1…`(被 `nav_statistics.py:25` 钉) | `2aaa51f142f6b2f86449e19ee2017748ed6d7450faa3bb5c80b5faa5aa46cd10` | ✅ |
| `current_plan.py`(磁盘 runner) | `25acf724…`(RUNNER_CONTRACT) | `25acf7245f42e8d6…`(前 16 位) | ✅ |
| `current_frames.py` / `current_consumer.py` / `current_modes.py` / `mark_valuation.py` | `3f8039be…` / `04099dd0…` / `27d43aa8…` / `7e9aa9b9…` | 全部前 16 位一致 | ✅ |
| `OBSERVED_FEES.json`(git, 分支#1) | `9ce2d8f2…` | `9ce2d8f2b4bf0e9fd801ad714c55490f8d8aa7b1793c75a944e82c343da5b5a1` | ✅ |
| `actual_nohalt_current_main1/RESULT.json`(git, 分支#1) | `171e050a…`(EVIDENCE.json) | `171e050a35fdbab123e4cd249c599f202804034d2ade5fd35cfbdf8fb97d9e6e` | ✅ |

**未能核实**: `audit1/RESULT.json`(`ce63354c…`)、`READBACK.json`(`f3de307a…`)、`completion1/RESULT.json`(`c42512c9…`)、`DAILY_AGGREGATES.json`(`a93d254f…`)——这些是报告的**唯一数字来源**, 在 worktree 磁盘上, 我没有逐个 shasum(见 §6)。

### 3.1 面板 / 缓存

| 用途 | 路径(pod2) | sha | 出处 |
|---|---|---|---|
| **特征面板** | `data/canonical3/channels7.npz` | `d689a7aab15488826da8c360fc12971016da56aebbcd1c5f77f87353eba86213` | `integration/FULL_FEATURES_VERIFIED_INPUTS.json`(git, 分支#1) |
| 轴 | `data/canonical3/{ts.npy, symbols.npy, anchors.npy}` | `09e156ef…` / `25626675…` / `1107253e…` | 同上 |
| 面板构建器 | `producer/build_features.py` | `f8d7e33fafb8d513902ac8822a79f690407bae19cb0929a73276a317685d7c10` | 同上 |
| 面板配置 | `producer/batch_config_canonical3.json` | `23c74f62…` | 同上 |
| **回放行情**(价格/成交量) | `book/stream_market_repaired_20260915/cash_market.npz` | 未在该文件中给 sha | `EVIDENCE.json:cash_binding.cfg.cash_market` |
| 资金费特征 | `book/funding_observation_1/SERVING_SECOND.npz` | `e58a4b8bffffd7edd4d6d406c819111f2d2d109dcb2694f1fa4d5a7d4fd8796c` | `FULL_FEATURES_VERIFIED_INPUTS.json` |
| 合约日历 | `book/full_axis_calendar_review_20260914/evidence1/calendar_candidate2/CONTRACT_LIFECYCLE…` | `5248d459…` | `EVIDENCE.json:cash_binding.cfg.calendar_sha256` |
| 结算假设 | `book/settlement_reference_20260915/formal1/SETTLEMENT_ASSUMPTIONS.json` | — | 同上 |

⚠ **`data/canonical3/channels7.npz` 的 sha `d689a7aa…` 是 `raw-month-repair` 覆盖之前的身份。** `REPAIR_REPORT_20260915.md` 明确写 repair 后「New channels SHA is `afd0ffa92a5fb47ba08b8bc90d150be7e4e84ecbbc4a773caf3d6e2c04311e23`; targets SHA is `f14f7007…`」。所以 `FULL_FEATURES_VERIFIED_INPUTS.json` 这份清单**是 09-14 那一代的**, 不是 608 天回放最终用的那一代。**608 天回放最终吃的是哪个 channels sha, 我没能从已提交文件里确认**(见 §6)。

它声称: 面板源是 Binance 官方月 ZIP。`training_input_scope1/REPORT.md` 原话: 「2021-11→2024-12 从 history1 官方月 ZIP/CHECKSUM 逐档解析, 验证 parsed SHA, raw64→7 通道 float16 按生产标量算术重算。2025→2026-07 采用已钉实际 raw 月产物, 2026-08 采用新月档。**RAW 标签在全 10224 锚直接使用原始 close(E+4h)/close(E)−1; 不是从 float16 收益反推**」。**我没有核这一段。**

### 3.2 模型权重 —— 是「修复后重训」的哪一批

**我核实了**(读 `integration/current_model_identity_20260915/addendum_current_rule_20260915/EVIDENCE.json`, git 在分支#1):

- **F10**: 2025-01 至 2026-08 共 **20 个月折**, 全部 **seed 42**, 每折从头训 15 epoch。`stages.train` = **2026-09-15T09:13:59 → 11:30:15 UTC**(8,176 s)。四阶段: train → torch_validate → numpy_export → numpy_validate, 最后一段 11:58:57 结束。`bridge.training_policy = "15best_train32_raw64_seed42"`。
- **King**: `king_records` 4 条(2023/24/25/26), `num_iterations=400, learning_rate=0.05, num_leaves=63, bagging_fraction=0.8, feature_fraction=0.8`, seed 0, 78 列。
- **不是线上权重**。`old_five_disk_files_unchanged` 把线上五件按 sha 钉住并声明**未使用**:
  - `~/wide_shadow/shadow_bundle/slow2026.txt` = `8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282`(King)
  - `~/wide_shadow/fea171/f10_live_s42_np.npz` = `351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4`(F10)
  - `~/wide_shadow/fea171/combo_stage.py` = `b5c698f9…`;`shadow_bundle/config.json` = `3a8422f3…`;`MANIFEST.json` = `af61d597…`
- **链路**(逐环 sha, 全在 EVIDENCE.json): 20 折 FOLD.json → King OOF `fc54e0a0b8a09865b9c70391dae8824e967ea8f537684f72dc4f7d89335c9cf5` → CN 权重 `dbfbcda0f0e9f4cee98d5f52fb40571bd26532878c7acf3e3ae7c10edf39bba6` → PF 发布 `90776bdc975367d5596fc4366d09576974d57fe4cc41515203cbf6bf5cf285e3` → cash `INPUT_BINDING` 所钉 PF RESULT `5f80ac12a3a225cb22dc13d47c5133d6b6a0b795d68593aad1e70c46160bf590`。
- **组合不是恒定 55/45**: `pf_record.choices = {COMBO: 3030, BASE_KING: 618}`, 共 3,648 锚。**618 次退回纯 King**。

**它自己的更正(重要)**: 同目录 `ADDENDUM_2026-09-15.md` 报的是 **2.62 / 569 日**(截至 2026-07-24), 而 `docs/RESULT_…md` 报 **2.523 / 608 日**。后者第 92 行明确写「其中 2.62/569 日段是当时阶段值, **当前完整值以本件 2.523/608 日为准**」。**引用时别混。**

**它声称、我没核实**: 「逐月训练和择优均不见测试月标签, 所有训练/验证 label_end ≤ 月首−4h; 例如 202501 实际参与 loss 的最晚标签为 2024-07-13 00:00 UTC, 验证最晚标签为 2024-12-31 20:00 UTC」(`ADDENDUM_2026-09-15.md`)。这是它对泄漏的核心断言, **我没有打开 20 个 FOLD.json 逐折验**。

### 3.3 成本怎么算的 —— 3.52 bps 是怎么进去的

**我核实了, 逐行**:

1. **常数在哪**:
   `…/current_rule_mark_valuation_20260915/current_plan.py` **第 15 行**
   ```python
   rows=[dict(id=…, book=book, mode=mode, delay_s=1500,
              ordinary_fee_bps=3.52, settlement_fee_bps=3.52,
              settlement_factor=1., step=1e-8, min_notional=5.) for mode in MODES for book in BOOKS]
   ```
   **硬编码字面量**, 对每个 scenario row 都一样。
2. **怎么传到引擎**: 同文件**第 28 行** `engine_config()` 把 `row['ordinary_fee_bps']` 原样写进 `DYNAMIC_EXECUTOR_CASH_CONFIG_1`。EVIDENCE.json 的 `cash_config` 回读: `ordinary_fee_bps: 3.52, settlement_fee_bps: 3.52, settlement_factor: 1.0, ladder_multiplier: 1.0, use_pns: true, attempt_offset_ms: 1500000`。
3. **引擎怎么用**: `integration/dynamic_executor_quantity_exact_20260915/dynamic_cash.py` **第 513 行**
   ```python
   fee = abs(delta * price) * self.config['ordinary_fee_bps'] / 10000.
   ```
   **按成交名义线性扣, 单边。不分 maker/taker, 不随日期变, 不随规模变, 没有 BNB 抵扣。**
4. **2.0 / 5.0 bps 那组数字从哪来**: `integration/current_fee_model_clarification_20260915/recompute_observed_fees.py` + `REPORT.md`。它是**独立只读 2026-09-11 冻结副本里 09-08/09/10 的真实 fills**(17,461 行去重成 9,419 笔)算出来的观测值: maker 2.000000/1.999999/2.000000 bps, taker 4.999999/5.000000/5.000000 bps。**这组数从未进入模拟。** 它是拿来跟 3.52 做对照的旁证。
5. **全期成本量级**(`complete_main_20260915/RESULT.json`): `ordinary_cost_usdt = 24,738.0357`, `settlement_cost_usdt = 26.0876`, `ordinary_filled_notional_usdt = 70,278,510.43`。24,738/70,278,510 = 3.52 bps ✅ 自洽。

⚠ **一处指错**: 费用 `REPORT.md` 的「复核入口」把「本次费用配置」指向
`book/dynamic_frame_inputs_20260915/**current_rule_e60_20260915**/current_plan.py:15`,
但 608 天那一跑的 `RUNNER_CONTRACT.json` 钉的是 **`current_rule_mark_valuation_20260915`/current_plan.py**(sha `25acf724…`, e60 那份是 `cc53703f…`)。**我 diff 过两份**: 第 15 行**逐字相同**(3.52 都在), 差异只在 schema 名和「只跑 nohalt 一格」的过滤(mark 版多一行 `rows=[row for row in rows if row['id']=='nohalt_current_main']`)。所以**数字结论不受影响, 但收据指向的是兄弟装置不是被跑的那个** —— 属于 `[[fact_table_must_cite_latest_receipt]]` 那一族。

### 3.4 资金费怎么算的 ★

**回放自己的资金费, 不是实盘观测的现金流。** 精确说法是: **真实历史结算率 × 模拟持仓 × 模拟 mark**。

**我核实了**:

- `dynamic_cash.py` **第 620 行**:
  ```python
  amount = -p['qty'] * e['mark'] * e['rate']
  ```
  `p['qty']` 是**模拟仓位**, `e['rate']`/`e['mark']` 来自 FUNDING 事件流。
- 事件流来源: `shared_inputs.py:45-57 funding_from_arrays()` 从 `FUNDING_FACTS.npz` 读, 每条事件带 `rate` / `mark` / `interval_hours` 三个字段, **各自配一个 `_known` 布尔位**, 未知一律写 `None`(第 55 行), 并且整批事件序列化后逐字节比对 `desc['original_event_jsonl_sha256']`(第 57 行)。
- 数量: `verify_independent_receipts.py:20` 断言 `source_funding_events == applied_original_funding_events == 1,637,915`;`current_consumer.py:65` 断言 FUNDING 事件计数 == `token.funding_descriptor['count']`。
- **缺失不补零**: `dynamic_cash.py:618-619` —— 持仓非零而 rate/mark 缺失 ⇒ `unknown('UNPRICED_HELD_FUNDING', …)`, 整条路径打成 `UNMEASURABLE`;`:612-614` —— 覆盖窗口有洞 ⇒ `MISSING_HELD_FUNDING_COVERAGE`。源码注释第 598-599 行原话:「**Unknown cash is never replaced by zero.**」
- **全期资金费**(`complete_main_20260915/RESULT.json`): `funding_cash_usdt = **−114,015.21**`。即这 608 天资金费是**净支出**, 靠 `price_and_settlement_pnl_usdt = +363,572.31` 覆盖。
- 恒等式: 363,572.31 − 114,015.21 − 24,764.12 = **224,792.97** = `net_pnl_usdt` ✅。`residual_usdt = 2.91e−11`。

⚠ **注意 `interval_hours` 读进来了但第 620 行没用它**。也就是说每条 FUNDING 事件被当作「一次完整结算」按 rate 原值计一次。这在每条事件确实对应一次结算时是对的; 如果事件流里混进了「按小时表述的费率」就会错。**我没有验证事件流的构造端**(`build_funding.py` 在 pod2)。这条正是 `[[funding_settlement_interval_unit_bug]]` 和 `[[x0910_fund_iv_interval_mismatch_2026_09_13]]` 咬过的位置, **值得单独派人看**。

### 3.5 止损 / 停机规则

**我核实了, 四处互相印证**:

| 项 | 证据 |
|---|---|
| 只跑一格 | `current_plan.py:16` `rows=[row for row in rows if row['id']=='nohalt_current_main']` —— 四格(2 book × 2 mode)里只留 nohalt+current_main |
| 全书停机被**从事件流里删掉** | `current_modes.py:24` `if kind!='RISK_ATTEMPT' or mode=='ECONOMIC_HALT': yield e` |
| 并且被**断言**为 0 | `current_consumer.py:66` `need(counts.get('RISK_ATTEMPT',0)==(3648 if mode=='ECONOMIC_HALT' else 0), …)` |
| 引擎也换了 | `current_consumer.py:22-23` —— ECONOMIC_HALT ⇒ `risk.RiskEngine`;否则 `base.Engine`(`dynamic_cash.py`), 且第 21 行断言 base config 里**没有** `economic_risk` 字段 |
| 停机确是「一停不复场」 | `risk_engine.py:40` `PERSISTENT_ECONOMIC_HALT_1`;`:90-91` `if new: r['halted']=True; r['first_trip_ms']=…` —— 只置位不复位;`:67` `halt_reason='PERSISTENT_ECONOMIC_HALT_RISK_EXIT_ONLY'` |
| 两个 mode **都**没有人工复场 | `current_modes.py:6` `manual_resume_events=[]`(不分 mode) |
| **逐名止损保留** | 计划 `use_pns=True`(`current_plan.py:17`);`dynamic_cash.py:436` `active = self.policy.pns['active_sets'](s['pns'], …) if self.config['use_pns'] else {'stop': set(), 'cooldown': set()}`;`:439` `force_flat=active['stop']`;`:681-688` readback 后 `evaluate_postreadback` 更新 PNS 状态 |
| PNS 策略来自哪 | `dynamic_cash.py:19-20` `POLICY_SHA='129479e610c501e865b6e01e7af31ed125c6902dd222438c29ca4e0cd0ca2c35'`, `POLICY_FILE=…/actual_executor_policy_review_20260915/pure_policy.py` |
| 引擎自报**不覆盖**什么 | `dynamic_cash.py:32-34` `'not_covered': ['fault_watchdog', 'daily_loss_halt_or_recovery', 'margin_liquidation', 'historical_sigma_ladder', 'venue_filter_PIT', 'queue_partial_fill', 'spread_or_impact', 'venue_caps_or_post_clamp_netbias', 'publisher_guard_or_fallback_admission', 'archive_PIT']` |

**停机臂的对照数字它也给了**(`EVIDENCE.json:halt_existing_2025`, 2025 全年): `daily_sharpe 0.7821`, `cumulative_return 0.06931`, **`daily_gross_nav_mean 0.2979`**, **`flat_daily_fraction 0.8493`** —— 保留永久停机的那条路 2025-02-25 停机后, **85% 的日子是空仓**。所以「关掉停机」不是微调, 是把 85% 的空仓日换成了带仓日。报告 §5.5 自己说了这一点。

### 3.6 ★ 证据链落在哪条分支上(我用 `git ls-tree` 逐目录数的)

| 目录 | #1 fullchain | #2 public-funding | #3 readback | 其余 8 条 | 磁盘 worktree |
|---|---:|---:|---:|---:|---|
| `book/…/current_rule_mark_valuation_20260915/`(**runner**) | 0 | **115** | 0 | 0 | 有 |
| `book/dynamic_frame_inputs_20260915/`(全) | 0 | **454** | 0 | 0 | 有 |
| `integration/dynamic_executor_quantity_exact_20260915/`(**现金引擎**) | 0 | **52** | 0 | 0 | 有 |
| `integration/dynamic_nav_statistics_20260915/`(**统计内核/自举**) | 0 | 0 | **140** | 0 | 有 |
| `integration/actual_executor_policy_review_20260915/`(**PNS 策略**) | 0 | 0 | **31** | 0 | 有 |
| `integration/current_model_identity_20260915/` | **2** | 0 | **28** | 0 | 有 |
| `integration/current_metrics_20260915/`(**报告器**) | **7** | 0 | 0 | 0 | 有 |
| `integration/current_fee_model_clarification_20260915/` | **3** | 0 | 0 | 0 | 有 |
| `integration/current_rule_mark_cash_audit_20260915/`(**逐笔核算原件**) | **0** | **0** | **0** | **0** | 有(未跟踪) |
| `producer/current_rule_publication_20260915/` | 0 | 0 | 0 | 0 | 有 |

**三条结论**:

1. **`complete_report.py` 在它自己的分支上跑不起来。** 它在 `current_metrics.py:10` 要 `../dynamic_nav_statistics_20260915/successor1/nav_statistics.py` —— 分支 #1 上那个目录 **0 个文件**。
2. **报告的唯一数字来源 `audit1/RESULT.json` 一条分支都不在。** 11 条分支对 `current_rule_mark_cash_audit_20260915/` 全部返回 0。`git check-ignore` 证实**不是被 .gitignore 挡的**, 就是**从来没提交**。它只存在于 `.claude/worktrees/codex-independent-20260907/` 的未跟踪文件里 —— 那个 worktree 一旦被 `git worktree remove` 或人工清掉, 2.523 就再也对不回去了。这正是 `[[silent_empty_result_traps_2026_09_16]]` / `[[git_add_directory_silently_drops_ignored_files]]` 那一族, 只是这次连目录都没 add。
3. **`producer/current_rule_publication_20260915/`(发布器, 618 次 King 回退的产生地)也是 0/11。**

### 3.7 ★ 回放到底在什么宇宙上交易(我追到了具体文件)

`EVIDENCE.json:cash_binding.cfg.calendar_sha256 = 5248d459…`。我在 worktree 磁盘上找到并**实测 sha 一致**:
`book/full_axis_calendar_review_20260914/evidence1/calendar_candidate2/CONTRACT_LIFECYCLE.json` = `5248d45950e68bd3f62d0829b99e8c4cacb16d59ebbf7d9f3339a16ac75842f8` ✅

同目录 `BUILD.json` / `VERIFY.json` / `COVERAGE.json` 给出这本日历的实际口径:

| 字段 | 值 |
|---|---|
| `symbols` | **166**(有生命周期条目的名字数) |
| `axis_size` | **829**(全轴) |
| `closes` / `opens` | 168 / 13 |
| `counts` | `OFFICIAL_CANDIDATE: 76`, `OFFICIAL_SOURCE_NOT_FOUND: 0`, `RAW_MONTH_HOLE_NOT_LIFECYCLE: 3` |
| `initial_79` / `additional_symbols` | 79 / 13(首个 `BNXUSDT`) |
| `remaining_unknown` | **5 条**, 首条「AKROUSDT official May26 close versus May27 final observed activity conflict」 |
| `completeness` | **`NOT_COMPLETE`**: 「>=7-day activity-gap inventory does not exhaust short suspension/settlement events, birth times, or full publication revision history」 |
| `status` | `PASS_ANC_APPEND_BOUND_SOURCE_AND_LOADERS` |

**血缘**: `CANDIDATE_DIFF.json:parent_calendar_sha256 = fb102c0e…`, 我实测 `book/calendar_expanded6/CONTRACT_LIFECYCLE.json` = `fb102c0ea5b1f07e…` ✅ 同一个。所以 **used calendar ← calendar_candidate1 ← calendar_expanded6**, 而 `calendar_expanded4/5` 按 `LIFECYCLE_CORRECTION_2026-09-14.md` 正是 known76 / known89 候选。**⇒ 608 天回放确实用上了 known89 那条人口修复, 不是停在 known59。** 这一条是对它的正面确认。

**但是**:
- `calendar_expanded4/5/6` **只存在于 `codex/known89-data-20260914` 一条分支**;`fullchain` / `public-funding` / `readback` / `onboarding` 上都只有 `calendar_expanded1/2/3`。
- `calendar_candidate2/`(实际被钉的那本)**11 条分支全部 0 文件**。
⇒ **定义「回放在哪些名字上交易」的那本日历, 一条分支都没有。** 和 §3.6 第 2 条同一个问题, 只是这次丢的是宇宙定义。

---

## 4. B. 夏普 CI [0.86, 4.18] 是怎么算的

### 4.1 具体做法(我读了源码)

装置: `integration/dynamic_nav_statistics_20260915/successor1/nav_statistics.py`(sha `6bd2e2c8…`, **磁盘, 不在 git**)。

| 项 | 值 | 出处 |
|---|---|---|
| 重采样对象 | UTC **日界 NAV 比率收益** `r = nav[1:]/nav[:-1] − 1` | `point_metrics`, 经 `complete_report.py:65-68` 独立复核到 1e−12 |
| 块长度 | **7 天和 30 天**两套 | `nav_statistics.py:21` `BLOCKS = (7, 30)` |
| 重采样次数 | **2000** | `:22` `REPS = 2000` |
| 随机种子 | **914** | `:23` `SEED = 914` |
| 抽样方式 | **循环移动块**(circular moving block), 有放回 | `legacy_statistics.py:46` `ix=((rng.integers(0,n,k)[:,None]+np.arange(block_length))%n).ravel()[:n]` |
| 块数 | `k = ceil(n/block_length)`, 拼接后截断到 n | `nav_statistics.py:91` |
| 区间 | **2.5% / 97.5% 分位**, `method='linear'` | `:239` |
| 有效副本门槛 | 有限值 ≥ 95% × REPS 才出区间, 否则 None | `:239` |
| 分支段 | `PERIODS = {'full':(0,608), '2025':(0,365), '2026_ytd':(365,608)}` | `:19` |

一个**罕见的好做法**: `draw_indices()`(`:77-92`)不直接写抽样表达式, 而是 **AST 解析冻结的 `legacy_statistics.py`, 抽出 `paired_blocks` 里唯一那条 `ix=` 赋值, 编译后 eval**(`:84-92`), 并先校验 legacy 文件 sha。这是为了保证「新统计器用的抽样表达式与旧的逐字节同一条」。同时 `_draws` 按 `(n, block)` 缓存, 所以 full/2025/2026 三段各自一套抽样表, 三段之间不共享。

### 4.2 数字对账(我从 git 里的 RESULT.json 直接读)

`complete_main_20260915/RESULT.json`(sha `4c1ef4b2…`):

| 段 | 日数 | 夏普点估计 | 7 日块 CI | 30 日块 CI | defined |
|---|---:|---:|---|---|---:|
| 2025 | 365 | 1.323948 | [−0.6149, 3.1513] | [−0.5544, 3.3000] | 2000/2000 |
| 2026 1–8 月 | 243 | 4.208019 | [1.3752, 7.2826] | [1.6396, 6.7729] | 2000/2000 |
| **full** | **608** | **2.522998** | **[0.9878, 4.1413]** | **[0.8582, 4.1845]** | 2000/2000 |

lead 引的 **[0.86, 4.18] 是 30 日块那一列**。文档表格两列都列了, 没有挑。

### 4.3 有没有校正选择偏差 —— 没有, 而且缺口比它承认的大

**它自己承认的**(逐条我都找到了源码里的对应字符串, 不是只有文档在说):

- `nav_statistics.py:36` `'bootstrap': 'Circular moving blocks of realized daily returns; no account/PNS rerun, **no multiple-selection correction**'`
- `current_metrics.py:63` `'…7/30-day return blocks **do not rerun stops** and **do not correct strategy-selection bias**'`
- 文档 §1 原话: 「这些区间没有修正历史策略选择偏差, 重采样没有重新执行止损。**不能据此宣称夏普显著超过 3**」

**它没说透的两点(我从预注册里看出来的)**:

1. **重采样不重跑止损**, 意味着 CI 只反映「同一条已实现日收益序列的顺序不确定性」, **不含**逐名止损在反事实路径上会触发/不触发的分支。对一本带路径依赖止损的书, 这个 CI 系统性偏窄。
2. **★ 交付的是 126 格里的 1 格。** `integration/dynamic_nav_statistics_20260915/source/PREREGISTRATION.md`(分支 #3, `4dca09cf`)原话:「主网格为 **六书 × 两延迟 × 两成本 × 五条件结算 = 120 格**, 加门槛六格共 **126 格**」。608 天报告交付的是: `current_main__main` 一本书、E+25 一个延迟、3.52 bps 一个成本、`settlement_factor=1.0` 一个结算 —— **一格**。再叠上预注册里没有的 halt/nohalt 轴, 它挑的是 nohalt 那一侧。
   预注册同时写了「**全部报告, 不能择优代主情景**」和「**不看初步盈亏增删臂**」。**我没有核实其余 125 格是否已跑完并落盘。** 如果没跑完, 2.523 就是「一个 126 格网格的首格」而不是「主情景」; 如果跑完了但没报, 那是另一回事。**这是我建议第一优先追的问题。**
3. 预注册还写了成本是「**3.52/7.04 bps**」两档, 报告只出现了 3.52。7.04 那一档去哪了, 我没找到。
4. **它自己的 `AGENTS.md` 要求「记录尝试总数, 使用配对时间块不确定性、**多重选择控制**和独立种子」**(共享 trunk 版本, §2 小节)。交付的 CI 明写 `no multiple-selection correction`。**两份它自己的文件对不上。**

另外 `nav_statistics.py:20` 定义 `ROLES = ('king_reference','f10_s42','f10_s2027')`, `:38` 写 `'seed_comparison': 'Two F10 seeds relative to the same-layer King'`, `:266` 的函数注释说「both F10 seeds paired separately to its King」——**装置是为「双种子 + King 配对」设计的**。但交付的 608 天报告只有一条路径, 文档 §1 自己也说「当前模型种子为 42; 旧的其他训练政策/种子结果不能当作本情景的第二种子确认」。**装置具备配对能力、预注册要求配对、交付物没有配对。**

---

## 5. C. 哪些是「数据/口径真值修复」, 哪些只是「人口敏感性」

判据(FXR-DATA-1): **一个修复如果改变的是被测量的真值(同一批样本上的数字变了), 它是真值修复; 如果改变的是进入测量的样本人口(哪些名字/哪些锚在分母里), 它是人口敏感性, 不能叫真值修复。** 两者混在一起报, 就没法归因。

| # | 修复项 | 分支 / 出处 | 改的是什么 | 判 |
|---|---|---|---|---|
| C1 | **三个月 raw 档缺失回填** —— 24,768 根缺失 raw bar, 173,368 个 channel cell 变化, 支撑区外 171,752,832 个 cell 逐位相等 | #7 `f849852e`, `REPAIR_REPORT_20260915.md` | **同一批 symbol-anchor 上的数值**从缺失/错误变正确, 支撑区外逐位不变 | **真值修复** ✅ 而且带逐位控制, 是这批里做得最干净的 |
| C2 | **2024-12 历史档还原** —— 370 个 symbol 的 740 个 ZIP/CHECKSUM, 120,092,987 字节, 与备份 TAR 逐成员 sha 相同 | #7 `a90dc829`, `RESTORE_REPORT_20260915.md` 原话「this is **restoration of identical bytes**, not a new download or revised data source」 | 恢复原字节, 不改数据源 | **真值修复** ✅(严格说是**可得性修复**: 它让原本无法计算的那部分变得可算, 本身不改任何已算出的数) |
| C3 | **BOB / BMT / MTL 三名的 raw 目标重算** —— 169/169/181 个锚, 每个 target 数组 519 个 cell | #7, 同上 | 三个具名标的在具名锚上的**标签值**变了 | **真值修复** ✅(范围窄且点名) |
| C4 | **known89: 补进 30 个此前漏掉的合约生命周期** | #10 `fed0f391` + `plans/LIFECYCLE_CORRECTION_2026-09-14.md`;**已确认进了 608 天回放的日历血缘**(§3.7) | **进入日历/宇宙的名字集合**变了(59 → 76 → 89 → 实际用的那本 166 名 / 829 轴) | **人口敏感性** ⚠ —— 而且它的**发现方式本身是人口条件化的**: 计划书原话「先由**实际持仓尾部**发现 17 名, 再补 13 名同篇但不要求持有的名字」。**从「我们持有过什么」反推「日历该有什么」, 这个方向本身会把人口选择写进日历。** 后 13 名是补救, 但补救的边界仍由「同十篇公告」定义, 不由完整 829 轴定义。计划书自己写了「不得事后只按观测完整成员改人口」——这条自律和它的发现路径是紧张的。它用的那本日历也自报 `completeness: NOT_COMPLETE` 且留了 5 条 `remaining_unknown`(§3.7)。 |
| C5 | **AERGO 4 个缺失估值点补齐** | #1 `8990ebd3`, `ACTUAL_HANDOFF.json:four_valuations`(4 个事件, ts 1784852400000/1784854500000/1784866800000/1784868900000) | 4 个此前为空的**日界估值点**被填上 | **边界情形**: 对这 4 个时点是真值修复; 但它同时把这条路径从 `UNMEASURABLE` 变成 `COMPLETE` —— **改变了"能不能进分母"**。报告 §5.4 自己标注「前 570 个独立日界经济字段完全相同」, 且 `funding_or_settlement_marks_changed: false` —— 这个自律做得对。**但 608 日窗口能报出来, 靠的就是这 4 个点。** 应当按「真值修复 + 一次可得性放宽」两件事分别记。 |
| C6 | **generation / HOLD 目标与资金费修复**(死合约冻结行) | #9 `6a8be1ba` / `3c040da2`;`training_input_scope1/REPORT.md` 称「generation/HOLD 目标修复在 build_targets.py, funding generation/HOLD 修复在 build_funding.py; 这些范围确实涵盖 2022 起」 | 改的是**死/冻结合约在标签与资金费上的取值** | **两者都是** —— 「HOLD 行该取什么值」是真值; 「HOLD 行算不算成员」是人口。**这两件在同一批提交里, 我没能分开。** 与 `[[dead_contracts_frozen_rows_in_research_data]]` 同一个病灶, 值得单独派人拆。 |
| C7 | **E60 资金费排在 reduce-only 退出之前** | #1 `a23e37b3` / #2 `79affdab` | 同一批事件的**处理顺序**变了 ⇒ 现金数字变 | **真值修复**(口径层) ✅ 顺序错会让持仓在结算瞬间被多算/少算一次 |
| C8 | **「关闭全书经济停机」** | `current_plan.py:16` + `current_modes.py:24` | **不是修复**。这是把一条风控从被测系统里拿掉 | **政策改动** ❌ 不属于任何一类。它把 85% 的空仓日(`flat_daily_fraction 0.8493`)换成带仓日。文档 §5.5 自己写「**不能把它和本件的差当作"修数据提升"或 F10 增量**」——这条自律是对的, 必须原样传下去 |
| C9 | **「重训 F10/King」** | `EVIDENCE.json:stages`(2026-09-15 09:13→11:58 UTC) | **不是修复**。这是换模型 | **干预** ❌ 与 C1–C7 混在同一个数字里。**没有「同窗口、同执行政策下 旧模型 vs 新模型」的配对** —— `RESULT.json:interpretation.strictly_causal_vs_deployed_same_window_difference = **null**`, `EVIDENCE.json:strict_causal_vs_current_fixed_weights_paired_estimate = **None**` |
| C10 | **fund NaN 中性编码** | `training_input_scope1/REPORT.md` 原话「fund NaN 中性编码仍是源码路径: King 两列 nan_to_num; F10 相关值可经编码为 0, 随后标准化成常数, **无显式 availability 列**」 | 把「没有资金费数据」和「资金费恰为 0」**编码成同一个值** | **两者都不是, 是一个未修的缺陷** ⚠ 它自己点名了, 没修 |

**总账**: C1 / C2 / C3 / C7 是干净的真值修复(4 项)。C4 是人口。C5 / C6 是混合。C8 / C9 是干预, 不是修复。C10 是已知未修。

**因此: 把 2.523 与任何旧数字相减, 得到的差里至少混了 4 类真值修复 + 1 类人口变化 + 1 次风控关闭 + 1 次模型重训, 没有一个配对估计能把它们拆开。** 报告 §5 结尾自己就是这么说的:「**不能从旧全周期 1.29 与本次 2.52 相减声称提升**」。

---

## 6. 我没能回答的问题

1. **608 天回放最终吃的 `channels7.npz` 是哪个 sha。** git 里那份清单(`FULL_FEATURES_VERIFIED_INPUTS.json`)给的是 `d689a7aa…`, 但 `REPAIR_REPORT_20260915.md` 说 repair 后应是 `afd0ffa9…`。两者哪个进了最终跑, 我没能从已提交文件里确定。**这是 A 问题里我最没把握的一格。**
2. **报告的四个数字来源文件我没有 shasum**: `audit1/RESULT.json`(`ce63354c…`)、`audit1/DAILY_AGGREGATES.json`(`a93d254f…`)、`READBACK.json`(`f3de307a…`)、`completion1/RESULT.json`(`c42512c9…`)。它们只在 worktree 磁盘上。我在核 `dynamic_cash.py` 时**撞上 iCloud 文件驻留问题**(一次 `grep` 39KB 文件超过 120 s 未返回), 之后改用 Read 分段读, 没有再对这几个大 JSON 做整文件哈希。**建议由能稳定读盘的人补。**
3. **预注册的其余 125 格跑了没有 / 报了没有。** 我只确认了交付的是 1 格, 没有去数已落盘的格数。这是我认为**最该先查的一件**。
4. **7.04 bps 那一档成本去哪了。** 预注册写了两档, 交付只有 3.52。
5. **`interval_hours` 在资金费里读了不用, 事件流的构造端(`build_funding.py`, pod2)我没看。** 这正是历史上咬过两次的位置。
6. **20 个 FOLD.json 的 label_end 我没有逐折验。** 「训练/验证标签 ≤ 月首−4h」是它对泄漏的核心断言, 目前只有它的自述。
7. **C6(generation/HOLD)里真值和人口我没能拆开。** 需要打开 `build_targets.py` / `build_funding.py` 的 diff 才行, 它们在 pod2。
8. ~~causal-producer 有没有被收编~~ —— **我补测了(按路径集合比对, 不是 patch-id)**:
   - `codex/causal-producer-generation-20260914` 独有 1,212 个文件, 其中 **920 个**也出现在 fullchain 上, **292 个不在** —— 包括整个 `producer/aergo_cash_gap_review_20260914/`(AERGO 资金费缺口审计, 正是报告 §5.4 那 4 个补点的上游诊断)。**部分孤儿。**
   - `codex/known89-data-20260914` 独有 195 个文件, **192 个不在 fullchain 上**(§3.7 已定位: `calendar_expanded4/5/6` 是其中核心)。**几乎完全孤儿。**
   ⚠ 但这只说明**文件路径**没出现在 fullchain 的树里, **不等于内容没有以别的路径进去**。要定论需要按内容 sha 而不是路径比对, **我没做**。
9. **300+ 个 RED 收据我只抽查了几组。** 「先红后绿」的成对关系是抽样看到的, 不是普查。
10. **`pure_policy.py`(PNS 策略, sha `129479e6…`)我没打开。** 所以「逐名止损保留」我核到了「开关是 on、`force_flat` 被传进去」, 但**止损的具体阈值/冷却规则是否与在役一致, 我没验**。按 `[[replay_seat_path_is_not_live_seat_path]]`, 这一步不能省。
11. **`AGENTS.md` 的 59 行新约定与 `CLAUDE.md` 是什么关系, 我没有裁定**(内容我读了, 见 §2 末尾)。它自称「在本独立分支内**优先于**下方历史阶段说明」, 但没说与仓库根 `CLAUDE.md` 的优先级。这是合并前要人裁的, 不是清点员能定的。

---

## 7. lead 复核: 清点员开放问题 #5(`interval_hours` 读了不用)—— **实测排除, 不是缺陷**

**复核于 2026-09-16 08:5xZ, lead。**

### 7.1 先更正清点员的一处定位
清点员称「`dynamic_cash.py` **第 620 行**」。树里有**三份** `dynamic_cash.py`:

| 路径 | 大小 | sha16 | `interval_hours` 出现 | 第620行含 rate |
|---|---|---|---|---|
| `integration/dynamic_executor_cash_20260915/` | 36K | `8ff0de33b5df05e4` | **0** | 否 |
| **`integration/dynamic_executor_quantity_exact_20260915/`** | 40K | **`8d8ddf8a002a9de7`** | **0** | **是** |
| `…/candidate_03bf/` | 40K | `03bf64c90c246c34` | 0 | 是 |

**第 620 行 `amount = -p['qty'] * e['mark'] * e['rate']` 在第二份里**, 引用该行必须带这个 sha。
且 **`interval_hours` 在三份里都出现 0 次** —— 它在 `shared_inputs.py` 被读进事件后**从未被任何消费者使用**。
清点员的描述方向正确, 但把文件认错了一份。

### 7.2 用实盘数据直接判「rate 是每次结算还是按小时」
若 rate 按小时表述, 则 `实付/(名义×rate)` 应**随 interval 成比例变化**(8h 档约为 1h 档的 8 倍)。
实测 `~/dl_quant_live/state/live/pilot_log/2026091*/funding.jsonl`, **6,900 笔**:

| `funding_interval_h` | n | 中位(实付/预测) | 均值 | p5..p95 |
|---|---|---|---|---|
| 1 | 213 | **1.0004** | 0.9972 | [0.949, 1.040] |
| 4 | 5,600 | **0.9968** | 0.9971 | [0.969, 1.029] |
| 8 | 1,087 | **0.9942** | 0.9937 | [0.970, 1.016] |

**三档全部 ≈ 1.00, 不随 interval 缩放。**

### 7.3 判决
**`rate` 是「每次结算」的口径, 回放的 `−qty × mark × rate` 公式正确,
`interval_hours` 本就不该进这个乘式。这一条不是缺陷, 排除。**

系统性偏低 0.3–0.6% 有解释, 不是符号或口径问题:
`position_notional_at_settlement` 取自 `position_read_ts`(实测最多早 3.3 h),
不是结算时刻的名义。**这是我方账本的读数时点问题, 与回放无关。**

### 7.4 仍然开着的(清点员列的其余两条, 我未动)
- 其余 **125 格**跑了没有 / 报了没有 —— **仍是第一优先。**
- 最终用的 `channels7.npz` 是哪个 sha(git 里那份清单 `d689a7aa…` 是 repair 前的,
  `REPAIR_REPORT` 说 repair 后应是 `afd0ffa9…`)。
