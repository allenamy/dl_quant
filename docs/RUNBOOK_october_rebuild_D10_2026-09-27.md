> **创建:** 2026-09-27 05:2xZ(原写 05:3xZ,时间写错,以提交 aa6269556 05:23Z 为准) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** **草稿,待 lead 冻结**;冻结前不得据此起任何作业 | **作废条件:** lead 冻结时改写;或 `DECISION_RULE_D10_stage2_2026-09-26.md`、DL 书层门修订 4/5、用户 D10 裁定(`RULING_user_D10_funding_interval_truth_2026-09-25.md`)任一被改写

# 十月重建 runbook(D10 资金费规则):九月归档 → D10 特征 → King 与 F10 重训并与生产者切换同一次发布 → 平价门 → 归档核对

**这份文件是什么**:按交接说明 `docs/HANDOFF_news2_2026-09-27.md` §2 的依赖顺序,把每一步的装置、门、收据、谁执行、谁安装写在一处。**不含阈值的新判据**:书层判据沿用已冻结的 DL 书层门修订 4/5(`docs/DECISION_RULE_dl_program_book_gate_2026-09-25.md` §9/§11),资金费侧沿用 `docs/DECISION_RULE_D10_stage2_2026-09-26.md`(含修订 1–3)。§7 列出文档之间的冲突与未定项,**冻结前必须由 lead 逐条裁定**。

**为什么必须一次发布**:线 D「只换资金费特征、不重训」对照格(s42,`ab8fc621e`,判据 R1.3 冻结于 `c5cfeb5e5`)2026 段 D = −0.173 bps/日,MBB95 [−0.36, −0.03],上界 < 0 ⇒ R1.3 预先声明的含义成立:**生产者改用 D10 规则与按新特征重训必须在同一次发布里上,不允许先换特征**。另见用户裁定:「离线训练与线上推理必须用同一条规则……任何一侧单独改动都不允许」(`RULING_user_D10_…` L11–14)。

**机器可查的部分**:本文件点名的、位于 `multi_asset/exports/research/news2_2026-09-23/devices/` 或 `multi_asset/exports/research/common/` 的每一个装置,都受 `tests_october_chain_contract.py` 约束(从本文件自动派生清单):不许裸写文件(一律经 `common/durable_write.py`),跑拉取器的驱动必须用 `p9_pull_verdict.py` 判定、带 `P9_RUN_NONCE`。**每一步起跑前先跑一次这个测试,红即停。**不在这两个目录里的装置(生产者、训练器、nc_* 复制件)不在它的范围内,测试收据里按名列出。

---

## 0. 全局约定(每一步都适用)

| 项 | 约定 | 依据 |
|---|---|---|
| 解释器 | pod2:资金费特征/腿用 venv314(`/root/news_2026-09-23_env/venv314/bin/python`,3.14.4);F10、combo、引擎、拉取器与核对装置用 `/workspace/venv/bin/python`(3.11.10)。Mac(arm64):执行器相关用 `/usr/bin/python3`(3.9.6);生产者用 `~/wide_shadow/venv/bin/python`(3.14.7) | HANDOFF §4;STATE 09-27 04:1xZ 迁移条目 |
| 复跑 | 每个装置的 argv 逐字抄自上一次的收据或提交信息;装置自报 sha 写进产物 | CLAUDE.md 约束 6 |
| 本机重活 | 只在 [N+1:00, N+3:40];启动脚本第一行调 `venue_quiet_window.py --json` | 团队规则 |
| pod2 长作业 | 整个循环在 pod2 上 `setsid nohup`,记录 PGID,登记 `INFLIGHT_REGISTRY.json`(terminal/success 正则锚定行首);只杀自己记录的 PGID | 05-06-07 拉取在 ssh 前台随连接死(rc 255)的教训 |
| 写文件 | 一律 `common/durable_write.py`(临时文件 → fsync → 回读比对 → replace → fsync 目录;失败时删临时文件、旧文件不动);收据里的 sha 取自它的返回值 | 本文件 §0.1 |
| 拉取判定 | 驱动不得按拉取器退出码分支;只认 `p9_pull_verdict.py` 打印的锚定行 `^P9_VERDICT (OK|MISMATCH|FAILED)`,没有这一行也算 FAILED | 本文件 §0.1 |
| 产物 | 大件放 pod2 `/workspace/`(`/dev/shm` 可能被清);旧产物一律不覆盖,新产物用新名 | HANDOFF §1 |
| 判词 | 研究侧读数只作描述;「采纳/上线/PASS」只出现在用户裁定之后 | 线 D 方案 §4 第 5 条 |

### 0.1 拉取器两处缺陷的类修复(2026-09-27,news2;本 runbook 依赖它)
- **退出码**:旧驱动把退出码 1 读成「CHECKSUM 不符」,随后删 zip 重取。但 Python 在拉取器的 excepthook 生效之前抛出的任何异常(import、语法错)也退出 1。实测:旧驱动(只作历史,不要再跑)`d10_pull_resume_pod2.sh` 的离线副本在一个 import 即崩的拉取器上,按上一次运行留下的旧 manifest **删掉了 BUSDT 的 zip,并以 0 退出**(`d10_pull_driver_selftest.py` 的 OLD 控制)。修法:拉取器 rev 2 在 manifest 里写 `run_nonce` 与 `intended_rc`;新驱动 `d10_pull_months_pod2.sh` 只在「本次运行的 manifest 明确写出 ≥1 个 checksum_match False,且退出码与之一致」时才修复,其余一律 FAILED、什么都不动。
- **持久写**:rev 1 手写的 temp → fsync → 回读 → replace 在 replace 失败时留下 `.tmp`(它自己的收据 `P9_PULLER_SELFTEST_rev1.json` 列着 `MANIFEST_2026-05.json.tmp`,而提交信息写「no .tmp left」,自测没有断言这一项),也没有 fsync 目录。修法:共用 `common/durable_write.py`,拉取器的 zip 与 manifest 都经它写。
- 历史驱动 `d10_pull_driver_mac.sh`、`d10_pull_may_to_july.sh`、`d10_pull_resume_pod2.sh`、`d10_census_driver.sh` 只作历史,不要再跑;它们的 sha 钉在 `tests_october_chain_contract.py` 里,改动任何一个都会让测试变红。

### 0.2 装置上 pod2(每一步之前)
把本仓库 `news2_2026-09-23/devices/` 中本步点名的装置,与 `common/durable_write.py`、`common/funding_interval.py`、`common/fund_replay_guard.py` 同步到 pod2 `$EXP/devices/`、`$EXP/common/`(`EXP=/dev/shm/d10_2026-09-25`,或本次新建的 `/workspace/d10_oct_<日期>/`),然后**三方比 sha**:仓库 HEAD 的 blob = 工作树 = pod2 上的文件。不一致即停。执行:news2。

---

## 1. 九月归档(owner:news2;不碰实盘主机)

**前置**:交易所发布 2026-09 的月度 zip,通常在 10 月初;截至 09-25 还不存在(RUNBOOK_monthly_retrain_2026-10 L212)。

| 子步 | 装置与 argv 形状 | 门(红即停) | 收据 |
|---|---|---|---|
| 1a 盘点 | `d10_archive_inventory.py`(832 次请求,只列目录不下载)→ `d10_make_symlists.py <inventory.json> <outdir>` 生成 `symlists/2026-09.txt` | 2026-09 在盘点中出现且名数 > 0;名数与 2026-08 相比的增减按名列出 | `D10_S1_ARCHIVE_INVENTORY_2026-09.json` |
| 1b 拉取 | pod2 上 `setsid nohup bash d10_pull_months_pod2.sh 2026-09 </dev/null >/dev/null 2>&1 &`(拉取器 `p9_pull_monthly_funding_zips.py` rev 2,判定 `p9_pull_verdict.py`,修复 `d10_drop_mismatched.py`,状态 `d10_month_state.py`) | 日志末行锚定 `COMPLETE all_verified=yes` 且退出 0;`d10_manifest_gate.py <zipdir> 2026-09` 首行以 `2026-09 VERIFIED ` 开头。`all_verified=no` 或 `FAILED` ⇒ 停,按名上报 lead | `zips/2026-09/MANIFEST_2026-09.json`(含 run_nonce)+ 驱动日志 |
| 1c 账本延长 | `d10_build_ledger_ms.py` **需出 rev 2(未写,owner news2)**:现版把 zip 源写死为 P2 的 `/workspace/wide_multisrc/funding`、API 源写死为 `/workspace/fund_aug.json.gz`(L46–47),两者都止于 2026-09-01T02:00Z。rev 2 增加:九月 zip 根目录(只接受 manifest 门 VERIFIED 的月份);九月的 API 源(需定,见 §7-6);输出新产物 `ledger_full_ms_2026-09.npz`,**不覆盖** `e179071d` | (i) 在旧 P2 覆盖窗内,折叠到秒后与旧 P2 逐位相同,差异集合 = 由数据派生的同秒多余事件集合(DR10 修订 2/3,原控制,限定窗口);(ii) 在同一窗口内与 `e179071d` 逐位相同(前缀恒等);(iii) 九月每一个归档事件都在新账本里(由 1d 核) | `D10_LEDGER_MS_BUILD_2026-09.json` |
| 1d 复审计 | 新驱动 `d10_reaudit_months_pod2.sh` **需写(owner news2)**,形状同 `d10_reaudit_jan_to_aug_pod2.sh`,但月份来自 argv、输出后缀 `_JAN_SEP`,不覆盖旧收据;跑 `d10_p2_ledger_vs_archive.py`(新旧两本账本)与 `d10_legs_rn8_vs_archive.py` | 九月切换窗事件缺失 0;真实分歧 0(与 1–8 月同一口径,`f66b286de`);不是 VERIFIED 的月份按名排除并上报 | `reaudit_jan_sep/` |

**安装**:无(纯研究侧)。

## 2. 按 D10 规则重建特征(owner:news2;pod2 CPU)

**轴**:十月重训的锚轴由重训 owner 给出(见 §3 与 §7-4);本步所有恒等控制都在「新轴与旧轴的公共前缀」上判。

| 子步 | 装置 | 恒等控制(先跑,红即停) | 正式产物 |
|---|---|---|---|
| 2a fund_state | `d10_build_fund_state.py --mode {snap,d10} --ledger-ms <1c 产物> --ledger-ms-sha <sha> --axes <新轴> --out … [--compare <NC fund_state> --compare-sha a12a8ed3…]` | snap 模式在公共前缀上逐位重现 NC 的 fund_state(`a12a8ed3`;上次:2,583,575 个切点前事件、6,953,000 个 as-of 索引 PREFIX_BITWISE,`2da5d051a`) | `fund_state_d10_oct.npz` + 收据(tier 计数,含 `UNRESOLVED_*` 与截断到 [1,8] 小时的逐事件具名计数,DR10 §1) |
| 2b pass1 | `d10_stage2_pass1.sh`(调 NC 生产派生的 `nc_p2_build.py p1`,**代码不改**;需按新轴改路径参数) | 恒等分片逐位重现 NEWS_FEATURES(上次 `7fe5b3473`) | 24 个分片 + merge1 |
| 2c 装配 | `d10_stage2_assemble.py --features … --features-sha … --r0 … --r2 … --rebuilt … --cut … --out …` | G2 与 XCHECK 全绿,否则写 STOP 退出 3 | `NEWS_FEATURES_D10_OCT.npz` |
| 2d 腿 | `d10_stage2_legs.sh {identity|d10}`(调 `nc_legs.py`,代码不改) | identity 模式逐位重现 legs 的每个键(KZ、Z24、ZFD、WL、ready、LR、QV、RN8;上次 `dacd303af`) | `legs_d10_oct.npz` |

**必报**:按月的 `src` 构成并标「独立 / 循环」;输入侧差异画像按书成员拆开(原始格数与书触及格数并报,以后者为影响口径)(DESIGN_D10_stage2 L132–133)。
**研究侧平价门**在本步之后、重训之前跑一次(§4 的 4a)。**红 ⇒ 不重训**(DR10 §2)。
**安装**:无。

## 3. King 与 F10 重训,与生产者切换同一次发布

### 3a 训练(研究侧)
- **F10**:dlarch 的训练器,在役 NC 配方(`--no-mask`;G1 恒等已证与在役 F10 OOF 逐位相同,DL 书层门修订 5(b)),输入换成 §2 的 D10 特征。种子 42 / 2027 / 7;部署永远用 s42(书层门 L48)。owner:dlarch(**待 lead 指派确认**)。
- **King**:**十月配方未定**(§7-4)。月度重训族已于 09-26 01:31Z 停止,且按设计用的是 snap_interval(`DECISION_RULE_king_monthly_retrain_2026-09-26.md` L46、L65);KN/A1 族在 IC 层判。草案建议:在役 NC 的 King 配方,只把特征换成 D10;控制照月度族的做法:确定性、A0 逐位重现 `KING_OOF a10b8725`、legs 逐位重现 `9ee5886f`。owner:fresh / fresh2(**待 lead 指派**)。
- **书层判据**:DL 书层门修订 4(双主判据,2026 段为主、pre-2026 不得变差)+ 修订 5(基线 = 在役 NC,同种子配对 s42/s2027/s7;回撤护栏对 NC,3pp,pre-2026,固定 2× 逐锚复利);「2026」段到延长轴末锚 09-18T20Z,冻结截断版并排报。判的对象是**联合臂**:King 与 F10 都在 D10 特征上重训,喂同一条 combo 与引擎(与线 D 同链,32 路径,冻结 `dbar`)。九月段(09-18T20Z 之后)单独报,不并入。**RECOMMEND_TO_USER 不是部署授权**(书层门 L49)。
- **收据**:训练器自报 config、self_sha 与输入 sha;OOF 与模型文件的 sha;书层读数的逐种子双列表(对 NC、对 T0)。

### 3b 生产者切换(实盘侧;**news2 不写 `~/wide_shadow`**)
- **改哪里**:`nc_contract.py` L77 `iv = snap_interval(ft - int(led[-1][0])) if led else None` 改为调 `funding_interval.interval_d10(prev_ft, ft, declared_iv)`(研究仓快照 `nc_2026-09-23/devices/nc_contract.py`,sha `316a0b9b…`,与已部署的 `fea171/nc_contract.py` 相同,见 `DEPLOY_producer_new_contract_2026-09-23.md` L37)。实盘调用点 `shadow_loop_v3.py:654 NC.ingest_settlements(...)`。
- **同一棵树里必须一起改的调用方**(否则训练侧与服务侧再次分叉):`nc_prep.py:116`(训练侧 fund_state)、`nc_seed_state.py:121,193,195`(安装时播种)、`nc_derive_producer.py:280`。
- **常量只写一处**:生产者树里带一份 `funding_interval.py`,其 sha 必须等于研究仓 `common/funding_interval.py`;找不到就抛错,不许回落到本地常量(DR10 §1 末条)。平价门核这个 sha。
- **状态**:fund_ema 状态是按 snap 规则累积的,切换时要用 D10 规则重新播种(`nc_seed_state.py`),播种来源与 §2 的特征同源;播种方式、以及 ledger_tail 按秒存储而 DR10 修订 1 要求毫秒键,这两点见 §7-5/§7-6。
- **执行器侧**:King booster 与 F10 模型换装,`booster_sha_pin` 与 `f10_sha_pin` 在同一静默窗里改,回滚时一起回退(RUNBOOK_monthly_retrain_2026-10 L270;STATE L373)。
- **部署协议**:执行器走隔离检出 → 拷实盘状态 → `ops/safe_commit.sh` 离线全电池 → 推送 → 在 `anchor.lock` 下于静默窗内快进(`DEPLOY_new_servable_models_2026-09-23.md` L5);生产者照 09-24 先例:代码、状态格式、模型、钉在同一窗口 W = [N+1:00, N+3:40] 内改,A3(生产者)与 A4(执行器快进)落在同一对锚之间,且早于 N+4:12;回滚 R-A/R-B(`nc_install.py rollback`、`nc_downgrade_state.py`、`book.json` 逐字节恢复)(`DEPLOY_producer_new_contract_2026-09-23.md` L9–13、L219–233、L492–515)。
- **谁装**:草案建议 integ 执行、lead 监督(09-24 先例,同文 L66);**用户最终确认后才可安装**(用户裁定 L14;书行为改动)。
- **发布后首锚验收**:判据由 lead 在读数之前冻结(同 09-26 20Z 验收的做法,`6b238f24d`);至少包含 §4 的 4b。

## 4. 平价门(线 B;owner:news2 跑,lead 读)

装置 `d10_parity_gate.py --a … --b … --features … --columns fund_now,fund_ema,rn8,iv --out … [--positive-control] [--anchor-max-utc …]`。顺序固定:**基线为绿 → 每个 dtype 的正控(目标数组自身 dtype 的 1 ULP 必须被检出,否则门作废)→ 正式判定**。人口 = 当锚书成员;原始格数与书触及格数都报,以后者为影响口径。两侧必须调同一个函数(DESIGN_D10_lineD_prep L71–79)。**红即停,不许放宽容差**(DR10 §2)。

| 时点 | a | b | 红了怎么办 |
|---|---|---|---|
| 4a 发布前(研究侧) | §2 的 D10 特征 | **候选生产者树**(经 `H.set_tree` 指向候选树,不是在役生产者)在同一本账本上重算 | 不重训 / 不发布 |
| 4b 发布后首锚(实盘侧) | 在役生产者当锚输出 | 研究侧在同一锚的实盘账本上重算 | 按 3b 的回滚走 |

另核:生产者树里 `funding_interval.py` 的 sha = 研究仓 `common/funding_interval.py`。

## 5. 归档核对(线 C;owner:news2)

- **每日(源 1,「相对事后已知账本」)**:归档作业 `com.hsy.funding_ledger_archive`,每天 09:30Z(本机时区 +08,plist 写 17:30),解释器 `/usr/bin/python3`,装置 `~/funding_ledger_archive/archive_live_ledger.py`(sha `a71c2a22…`,守卫为同目录副本 `venue_quiet_window.py` `4e008f48…`)。每次运行都在 `~/funding_ledger_archive/runs/RUN_<utc>.json` 留收据。**每天核**:status OK、conflicts 0、守卫为同目录副本且退出 0/3、`~/wide_shadow/state` 枚举数 > 0、`launchd.err` 为空。
- **每月(源 2,「相对交易所真值」)**:九月 zip 到了之后,`d10_live_ledger_vs_archive.py` 跑九月,±24h 切换窗;数据源 = 保留的 `aux.json` 快照 + 归档作业自 2026-09-26T21:01Z 起的账本。覆盖起点按名取各自最早一行,起点之前的事件记 `OUT_OF_LIVE_TAIL_WINDOW`,不算缺失(RUNBOOK_monthly_retrain_2026-10 L223–229)。**已知不可恢复**:09-11 到 09-17T12Z 没有实盘快照(DESIGN_D10_stage2 L102–105)。
- **告警**(DR10 §3):书成员上任意 1 格陈旧或不等 ⇒ 当锚验收 warn,具名到(锚, 名, used, correct, 落后秒数, 书权重);同日 ≥ 3 格或任意 1 格 |书权重| ≥ 0.002 ⇒ 红项报 lead。九月若也缺结算:报用户与 lead,不自行改书(同 runbook L231)。
- **十月发布之后**:同一作业继续跑;第一份十月收据与第一份在 D10 规则下的对账,是 4b 之外的第二道验收。

## 6. 时间线草案(以九月 zip 的实际发布日 P 为基准)

| 日 | 事项 |
|---|---|
| P | 1a–1b(拉取约 1 小时量级,按 05–07 月的速率估) |
| P+1 | 1c–1d |
| P+1..P+3 | 2a–2d,4a |
| P+3..P+6 | 3a 训练与书层读数(GPU 排队按 dlarch 的队列) |
| 读数后 | lead 出判词 → 用户裁定 → 3b 在一个静默窗内发布 → 4b 首锚验收 |

用户裁定的目标是「10-01 或更早,无过渡版」(`RULING_user_D10_…` L24)。**用真实九月数据做不到 10-01**,见 §7-10。

## 7. 冲突与未定项(冻结前请 lead 逐条裁定)

1. **现有月度重训 runbook 不适用**:`RUNBOOK_monthly_retrain_2026-10.md` §0★ 是 v4 bundle 链(`chain_v4_monthly.sh`),而该形态已被裁定「现形态不建」(`RULINGS_best_recommendation_2026-09-19.md` L11);在役是 NC(booster `700d9e7b`、F10 `3d7d050f`)。NC/news2 链上没有月度重训 runbook,本文件 §3 只写到「谁、用什么判」,训练装置本身需要各 owner 补。
2. **书层门对 King 的适用范围**:书层门 L9 写「不适用于 King 改动」,而 DR10 §4 把修订 4 用于 King+F10 联合重训;F10 的种子配对也对不上 King 的 `random_state`。需要裁定:联合臂按修订 4 判,King 的种子怎么配。
3. **一次发布 vs 每锚一个改动**:`RUNBOOK_monthly_retrain_2026-10` L121 把 King 与 F10 写成两个版本事件、各占一个静默窗;团队协议 §6 要求每锚只一个行为改动;而 D10 要求生产者 + King + F10 一次发布。建议:把三者定义为**一个**行为改动(一个窗口、一套回滚),写进冻结版。
4. **King 十月配方未定**(见 3a)。
5. **`declared_iv` 在实盘没有来源**:`interval_d10` 在一个名的第一笔、或与上一笔相隔 > 24h 时要用交易所声明的间隔,但 `ingest_settlements` 的事件只有 `(ft, rate)`(`nc_contract.py` L67–68),实盘取数是 `/fapi/v1/fundingRate`(`shadow_loop_v3.py:645`),不带间隔。候选来源:`/fapi/v1/fundingInfo`,或 premiumIndex 的下次结算时间。缺失时 `interval_d10` 返回 `UNRESOLVED_DECLARED_UNAVAILABLE`,不许默认为 8;实盘侧怎么处理这一类,需要裁定。
6. **秒 vs 毫秒**:实盘 `ledger_tail` 按秒存(`DEPLOY_funding_ledger_archive_2026-09-26.md` L99),DR10 修订 1 要求毫秒键;账本里已存的 iv 是 snap 值。切换时状态要不要整体重新播种、回滚怎么回,都没写。九月的 API 源(1c)同理。
7. **改动范围**:`nc_prep.py`、`nc_seed_state.py`、`nc_derive_producer.py` 是否都随生产者一起改。本草案的主张是**都改**(3b),否则 2a 的 snap 恒等控制在新树上无意义,训练与服务会在播种处再次分叉。
8. **发布前平价的对象**:发布前实盘仍是 snap(按设计),所以 4a 必须对**候选树**跑,不能对在役生产者跑。本草案已这样写,请确认。
9. **安装人**:十月的生产者切换没有具名安装人。本草案建议 integ 执行、lead 监督;需要用户最终确认与 RULINGS L5 的完整协议。
10. **时间**:九月 zip 在 10 月初才有,且 09-11 到 09-17T12Z 的实盘账本不可恢复。选项:(i) 等九月 zip,发布日晚于 10-01(本草案默认);(ii) 训练截到 `e179071d` 的末端(09-01T02:00Z),在九月 zip 到来之前发布。(ii) 训练窗比 (i) 少一个月,但不是过渡版(规则与服务一致)。按「尽快上线 = 修完已知缺陷后以最佳效果尽快上线」这一条,由 lead 与用户选。
11. **旧文档细节已过期**:`RUNBOOK_monthly_retrain_2026-10` L168 的 `SHADOW_OFFSET_MIN=16` 现在是 12(STATE L241);主机已是 arm64。

## 8. 这份草稿没有覆盖的风险(执行者视角)
- 1c 与 1d 的两个新装置还没写;它们落地时必须先过 `tests_october_chain_contract.py`,并各自带正控/红控。
- 2b 与 2d 调用的 `nc_p2_build.py`、`nc_legs.py` 是生产派生的「代码不改」复制件,不在契约测试范围内;它们写文件的方式没有经过持久写检查。
- 3a 的训练器与 3b 的生产者树都不在本仓库这两个目录里,契约测试看不到它们;它们的持久写与退出码约定由各自 owner 负责。
- 归档作业 `archive_live_ledger.py` 的写入由它自己手写的 helper 完成,契约测试按「已知违例」钉住计数(改它等于重新部署,由 lead 走部署协议)。

---
## §7 裁定(lead,2026-09-27 06:3xZ;逐条。本节给出后,文件仍是草稿;第 9 条与第 10 条要用户确认后才冻结)
1. **同意**:NC/news2 链没有月度重训 runbook。十月的训练装置由 owner 补:King 由 fresh2/dlarch 沿 kingfam 系的 kf_train_king;F10 由 dlarch。装置入库并过契约测试之后,才写进 §3。
2. **联合臂按书层门修订 4 判**(DR10 §4)。King 固定为在役的 random_state(rs=0),F10 按修订 4 的种子配对;King 的成员离散度(m0–m7)只作描述列报告,不作门。
3. **同意**:生产者 + King + F10 定义为**一个**行为改动:一个窗口、一套回滚、一次首锚验收。这仍在用户 D10 裁定(训练与服务同一规则)的范围内,但作为书行为改动,冻结前向用户报告。
4. **King 十月配方 = 在役配方(A0 形态),用 D10 特征重训**。A1(按月重训)按冻结判据 FAIL(d585e1792),不采用。dlarch L5 的年龄发现(A0 模型老化后 ΔIC 升高)另立一条预注册再议,不在十月内顺带改。
5. **declared_iv**:主源是 `/fapi/v1/fundingInfo`。「名字不在 fundingInfo 响应里 ⇒ 默认 8h」**必须先证明**:取交易所文档快照作收据,并对历史结算间隔做逐名核对(期望 0 例不符),证明之后才可用。premiumIndex 的 nextFundingTime 作交叉核对。两个来源都拿不到 ⇒ UNRESOLVED:该名在该锚记为资金费未知,具名告警,**不许默认成 8**。
6. **秒 vs 毫秒**:切换时从归档整体重新播种状态(毫秒键)。回滚 = 按字节恢复切换前的状态快照(快照 sha 在窗前写进收据)。九月的 API 源同样按毫秒重取。
7. **同意都改**:nc_prep、nc_seed_state、nc_derive_producer 随生产者一起改。
8. **确认**:发布前的平价门对**候选树**跑,不对在役生产者跑。
9. **安装人**:integ 执行,lead 监督。**需要用户确认**(发布前随第 10 条一并请示)。
10. **时间:需要用户选**。先请 news2 给出 (i) 与 (ii) 各自**实际最早可发布日**:列出关键路径上每一项(1c/1d 装置、训练器、平价门、电池)的预计完成时间。拿到日期后,lead 带推荐请示用户。
11. **同意**:过期细节(SHADOW_OFFSET_MIN = 12、arm64 主机)在冻结版里更新。
