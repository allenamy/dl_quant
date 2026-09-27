> **创建:** 2026-09-27 05:2xZ(原写 05:3xZ,时间写错,以提交 aa6269556 05:23Z 为准) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** **已冻结(lead 2026-09-27 07:0xZ,见文末「用户裁定」节)**;原状态为「草稿,待 lead 冻结」 | **作废条件:** lead 冻结时改写;或 `DECISION_RULE_D10_stage2_2026-09-26.md`、DL 书层门修订 4/5、用户 D10 裁定(`RULING_user_D10_funding_interval_truth_2026-09-25.md`)任一被改写

# 十月重建 runbook(D10 资金费规则):九月归档 → D10 特征 → King 与 F10 重训并与生产者切换同一次发布 → 平价门 → 归档核对

**这份文件是什么**:按交接说明 `docs/HANDOFF_news2_2026-09-27.md` §2 的依赖顺序,把每一步的装置、门、收据、谁执行、谁安装写在一处。**不含阈值的新判据**:书层判据沿用已冻结的 DL 书层门修订 4/5(`docs/DECISION_RULE_dl_program_book_gate_2026-09-25.md` §9/§11),资金费侧沿用 `docs/DECISION_RULE_D10_stage2_2026-09-26.md`(含修订 1–3)。§7 列出文档之间的冲突与未定项,**冻结前必须由 lead 逐条裁定**。

**为什么必须一次发布**:线 D「只换资金费特征、不重训」对照格(s42,`ab8fc621e`,判据 R1.3 冻结于 `c5cfeb5e5`)2026 段 D = −0.173 bps/日,MBB95 [−0.36, −0.03],上界 < 0 ⇒ R1.3 预先声明的含义成立:**生产者改用 D10 规则与按新特征重训必须在同一次发布里上,不允许先换特征**。另见用户裁定:「离线训练与线上推理必须用同一条规则……任何一侧单独改动都不允许」(`RULING_user_D10_…` L11–14)。

**机器可查的部分**:本文件点名的、位于 `multi_asset/exports/research/news2_2026-09-23/devices/` 或 `multi_asset/exports/research/common/` 的每一个装置,都受 `tests_october_chain_contract.py` 约束(从本文件自动派生清单):不许裸写文件(一律经 `common/durable_write.py`),跑拉取器的驱动必须用 `p9_pull_verdict.py` 判定、带 `P9_RUN_NONCE`。**每一步起跑前先跑一次这个测试,红即停。**不在这两个目录里的装置(生产者、训练器、nc_* 复制件)不在它的范围内,测试收据里按名列出。

---

## 0. 全局约定(每一步都适用)

| 项 | 约定 | 依据 |
|---|---|---|
| 主机(§7 裁定 11) | 实盘主机为 arm64 Mac mini(09-27 起);`SHADOW_OFFSET_MIN = 12`(旧 runbook L168 写 16,已过期) | STATE 09-27 迁移条目 |
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
- **F10**(§7 裁定 1):dlarch 的训练器 `multi_asset/exports/research/dlarch_2026-09-24/devices/dlarch_train_f10.py`,在役 NC 配方(`--no-mask`;G1 恒等已证与在役 F10 OOF 逐位相同,DL 书层门修订 5(b)),输入换成 §2 的 D10 特征。种子 42 / 2027 / 7;部署永远用 s42(书层门 L48)。owner:dlarch。按完整路径点名,契约测试就能自动派生到它和它 import 的本地模块;dlarch 改装置之前,测试结果见契约收据。方案 (ii) 的训练必须显式截在切点 2026-09-01T02:00Z 以内。
- **King**(§7 裁定 1、4;lead 06:4xZ 确认):在役 fold 2026 服务模型的配方(A0 形态、年折),训练窗不变(标签到 2025-12-22),只把特征换成 D10;rs = 0。训练器 `multi_asset/exports/research/king_oct_2026-09-27/devices/king_oct_train.py`(fresh2,入库于 8dd1a0068),控制装置 `multi_asset/exports/research/king_oct_2026-09-27/devices/king_oct_check.py` 与 `multi_asset/exports/research/king_oct_2026-09-27/devices/king_oct_controls.sh`(收据 5078fd402,KOC_DONE all_pass=True)。服务运行必须带 `--keep-models`:fold 2026 的 king_2026.txt 就是要服务的 booster。成员 m0–m7 只作描述列(裁定 2)。A1 不采用(d585e1792)。截到切点的全量拟合是配方改动,另立判据(DECISION_RULE_king_serving_refresh_2026-09-27.md,dlarch),十月不做。控制:C1 在役特征上 A0 m0 逐位等于 `KING_OOF a10b8725`;C2 D10 上重复训练逐位相同。
- **书层判据**(§7 裁定 2):联合臂按 DL 书层门修订 4 判(DR10 §4)。修订 4 的内容:双主判据,2026 段为主、pre-2026 不得变差。再加修订 5:基线 = 在役 NC,同种子配对;回撤护栏对 NC,3pp,pre-2026,固定 2× 逐锚复利。种子配对只用在 F10 上(s42 / s2027 / s7),King 固定 rs = 0。「2026」段到延长轴末锚 09-18T20Z,冻结截断版并排报。判的对象是**联合臂**:King 与 F10 都在 D10 特征上重训,喂同一条 combo 与引擎(与线 D 同链,32 路径,冻结 `dbar`)。09-18T20Z 之后的九月段单独报,不并入。**RECOMMEND_TO_USER 不是部署授权**(书层门 L49)。
- **收据**:训练器自报 config、self_sha 与输入 sha;OOF 与模型文件的 sha;书层读数的逐种子双列表(对 NC、对 T0)。

### 3b 生产者切换(实盘侧;**news2 不写 `~/wide_shadow`**)
- **改哪里**:`nc_contract.py` L77 `iv = snap_interval(ft - int(led[-1][0])) if led else None` 改为调 `funding_interval.interval_d10(prev_ft, ft, declared_iv)`(研究仓快照 `nc_2026-09-23/devices/nc_contract.py`,sha `316a0b9b…`,与已部署的 `fea171/nc_contract.py` 相同,见 `DEPLOY_producer_new_contract_2026-09-23.md` L37)。实盘调用点 `shadow_loop_v3.py:654 NC.ingest_settlements(...)`。
- **同一棵树里必须一起改的调用方**(§7 裁定 7:都改):`nc_prep.py:116`(训练侧 fund_state)、`nc_seed_state.py:121,193,195`(安装时播种)、`nc_derive_producer.py:280`。否则训练侧与服务侧会再次分叉。
- **常量只写一处**:生产者树里带一份 `funding_interval.py`,其 sha 必须等于研究仓 `common/funding_interval.py`;找不到就抛错,不许回落到本地常量(DR10 §1 末条)。平价门核这个 sha。
- **状态**(§7 裁定 6):切换时从归档**按毫秒键整体重新播种**(`nc_seed_state.py`),播种来源与 §2 的特征同源;九月的 API 源同样按毫秒重取。**回滚 = 按字节恢复切换前的状态快照**,快照的 sha 在窗口开始前写进收据。
- **声明间隔 declared_iv**(§7 裁定 5,lead 06:5xZ 终裁):主源 `/fapi/v1/fundingInfo`;premiumIndex 的 nextFundingTime 作交叉核对。**不启用「缺名 ⇒ 8h」**:缺名一律 UNRESOLVED,该名在该锚记为资金费未知并具名告警,不许默认成 8。依据见 §3c 的取证:当前 570 个 TRADING 永续全部在 fundingInfo 里,缺名为 0,所以这条规则今天的成本为 0。生产者树只实现 UNRESOLVED 这一个分支。fundingInfo 间隔与归档末行不一致的 14 个名交给 4a/4b 平价门处理,名单见取证收据。
- **一个行为改动**(§7 裁定 3):生产者 + King + F10 = 一个窗口、一套回滚、一次首锚验收;冻结前向用户报告。
- **钉的是被判定的那个模型文件**(lead 06:5xZ,依据 fresh2 5078fd402):King 与 F10 的模型文本 sha 每次重训都会变(ulp 级),但分数不变。所以执行器钉的必须是**被判定的那一次运行写出的模型文件**;判定之后不许重训再换上去。装包时逐字节核对该文件与判定收据里的 sha,不一致即停。
- **执行器侧**:King booster 与 F10 模型换装,`booster_sha_pin` 与 `f10_sha_pin` 在同一静默窗里改,回滚时一起回退(RUNBOOK_monthly_retrain_2026-10 L270;STATE L373)。
- **部署协议**:执行器走隔离检出 → 拷实盘状态 → `ops/safe_commit.sh` 离线全电池 → 推送 → 在 `anchor.lock` 下于静默窗内快进(`DEPLOY_new_servable_models_2026-09-23.md` L5);生产者照 09-24 先例:代码、状态格式、模型、钉在同一窗口 W = [N+1:00, N+3:40] 内改,A3(生产者)与 A4(执行器快进)落在同一对锚之间,且早于 N+4:12;回滚 R-A/R-B(`nc_install.py rollback`、`nc_downgrade_state.py`、`book.json` 逐字节恢复)(`DEPLOY_producer_new_contract_2026-09-23.md` L9–13、L219–233、L492–515)。
- **谁装**(§7 裁定 9):integ 执行,lead 监督。**需要用户确认**,与 §6 的时间选项一并请示;用户最终确认之后才可安装(用户裁定 L14;书行为改动)。
- **发布后首锚验收**:判据由 lead 在读数之前冻结(同 09-26 20Z 验收的做法,`6b238f24d`);至少包含 §4 的 4b。

### 3c declared_iv 取证(owner:news2;§7 裁定 5 的前置,**未完成前 3b 不得使用「缺名 ⇒ 8h」**)
1. 交易所文档快照:`/fapi/v1/fundingInfo` 的官方说明原文,存入收据,记录抓取时间与内容 sha。
2. 当前 fundingInfo 响应:从 pod2 取一次(公共行情端点,不走 Mac 的实盘出口),存原始字节与 sha。
3. 逐名核对:不在响应里的每个名,在归档 zip 最近 N 个月里,`funding_interval_hours` 应全部等于 8。期望 0 例不符。不符的逐名列出,这条规则即不成立。
4. 反向核对:在响应里的每个名,其 `fundingIntervalHours` 与归档最近一行的间隔应一致。
5. 结果:三项全过才写「取证成立」;否则按 UNRESOLVED 路径处理,由 lead 另裁。

**结果(2026-09-27,收据 `news2_2026-09-23/receipts/declared_iv_2026-09-27/`)**:
- 文档原文不含「缺名 ⇒ 8h」。原文只经 WebFetch 转述取得;页面对 curl 返回 202 空内容,**没有字节快照,不作字节证据**。
- 当前 fundingInfo 共 791 名,570 个 TRADING 永续全部在内。
- 2026-08 归档里的 11 个缺名全部已下架 ⇒ 这条回落在在役人口里没有适用对象。
- **lead 终裁:不启用回落,缺名 ⇒ UNRESOLVED。**

## 4. 平价门(线 B;owner:news2 跑,lead 读)

装置 `d10_parity_gate.py --a … --b … --features … --columns fund_now,fund_ema,rn8,iv --out … [--positive-control] [--anchor-max-utc …]`。顺序固定:**基线为绿 → 每个 dtype 的正控(目标数组自身 dtype 的 1 ULP 必须被检出,否则门作废)→ 正式判定**。人口 = 当锚书成员;原始格数与书触及格数都报,以后者为影响口径。两侧必须调同一个函数(DESIGN_D10_lineD_prep L71–79)。**红即停,不许放宽容差**(DR10 §2)。

| 时点 | a | b | 红了怎么办 |
|---|---|---|---|
| 4a 发布前(研究侧;§7 裁定 8 已确认) | §2 的 D10 特征 | **候选生产者树**(经 `H.set_tree` 指向候选树,不是在役生产者)在同一本账本上重算 | 不重训 / 不发布 |
| 4b 发布后首锚(实盘侧) | 在役生产者当锚输出 | 研究侧在同一锚的实盘账本上重算 | 按 3b 的回滚走 |

另核:生产者树里 `funding_interval.py` 的 sha = 研究仓 `common/funding_interval.py`。

## 5. 归档核对(线 C;owner:news2)

- **每日(源 1,「相对事后已知账本」)**:归档作业 `com.hsy.funding_ledger_archive`,每天 09:30Z(本机时区 +08,plist 写 17:30),解释器 `/usr/bin/python3`,装置 `~/funding_ledger_archive/archive_live_ledger.py`(sha `a71c2a22…`,守卫为同目录副本 `venue_quiet_window.py` `4e008f48…`)。每次运行都在 `~/funding_ledger_archive/runs/RUN_<utc>.json` 留收据。**每天核**:status OK、conflicts 0、守卫为同目录副本且退出 0/3、`~/wide_shadow/state` 枚举数 > 0、`launchd.err` 为空。
- **每月(源 2,「相对交易所真值」)**:九月 zip 到了之后,`d10_live_ledger_vs_archive.py` 跑九月,±24h 切换窗;数据源 = 保留的 `aux.json` 快照 + 归档作业自 2026-09-26T21:01Z 起的账本。覆盖起点按名取各自最早一行,起点之前的事件记 `OUT_OF_LIVE_TAIL_WINDOW`,不算缺失(RUNBOOK_monthly_retrain_2026-10 L223–229)。**已知不可恢复**:09-11 到 09-17T12Z 没有实盘快照(DESIGN_D10_stage2 L102–105)。
- **告警**(DR10 §3):书成员上任意 1 格陈旧或不等 ⇒ 当锚验收 warn,具名到(锚, 名, used, correct, 落后秒数, 书权重);同日 ≥ 3 格或任意 1 格 |书权重| ≥ 0.002 ⇒ 红项报 lead。九月若也缺结算:报用户与 lead,不自行改书(同 runbook L231)。
- **十月发布之后**:同一作业继续跑;第一份十月收据与第一份在 D10 规则下的对账,是 4b 之外的第二道验收。

## 6. 时间线:两个选项各自的实际最早可发布日(§7-10,news2 2026-09-27 06:5xZ;待 lead 带推荐请示用户)

**共同约束**(lead 裁定与 owner 实测/估计,标注来源):
- 发布窗只用 13:00–15:40Z(N = 12Z),避开 09:30Z 的归档作业;16Z 锚做首锚验收。上一次发布的首锚验收通过之前,不叠新的发布。
- 包必须在窗前的克隆里演练到全绿。每个执行器提交约 25 分钟(integ 实测:arm64 电池约 12 分钟 × 2);如果 pin 类套件要同步改,再加 30–60 分钟。包要建在含 A10 的运行树上。
- `common/funding_interval.py` 已冻结:sha 5d5bf20797ca41c0…,冻结于 09-27 06:45Z,提交 2864babfd,契约测试 C6 守着它。
- 用户裁定的时点记为 U,不可预测。下表假设 U 在读数与 lead 判词之后、下一个 13Z 窗之前。

### 选项 (ii):训练截到 2026-09-01T02:00Z(输入现在就有)

| # | 项 | owner | 预计完成(UTC) | 依据 |
|---|---|---|---|---|
| 1 | D10 输入:NEWS_FEATURES_D10 f1cd3fa2 + legs_d10 104af853(线 D) | news2 | **已有** | 今天干跑 D3 逐位复现 |
| 2 | King 训练器改好入库 + 控制 C1/C2/C3 | fresh2 | 09-27 10:00Z + 15 分钟 | fresh2 估;控制 15 分钟 |
| 3 | King 训练(rs=0 + m0–m7 + 复核) | fresh2 | 训练器就绪后 7 分钟 | 09-27 A0 臂实测 5 分 25 秒 |
| 4 | F10 训练器改好入库 + 契约测试 | dlarch | 开工后约 3 小时(估) | dlarch 估;G1 两折约 5 分钟为实测 |
| 5 | F10 三个种子训练 | dlarch | 训练器就绪后约 3 小时 | F10_FULL 实测 66–68 分钟/种子;0.85 配方估 57–60 |
| 6 | 书层格(联合臂,对 NC 同种子) | dlarch | 最后一个种子训完后 15 分钟 | 实测 12–15 分钟/格,可与训练并行 |
| 7 | lead 判词(修订 4/5,冻结在先) | lead | 读数出来后 | — |
| 8 | 候选生产者树(UNRESOLVED 分支、毫秒重新播种、字节快照回滚、nc_* 全改) | integ | **最早 09-28 18Z / 中位 09-29 06Z / 保守 09-29 18Z** | integ 估(NC 先例约 1.5 天) |
| 9 | 平价门 4a(对候选树) | news2 | 树就绪后约 1 小时 | 本日装置实测为分钟级 |
| 10 | 电池演练(克隆)+ 窗内 safe_commit | integ | 窗前 25–85 分钟 | integ 实测 |
| 11 | 发布窗 → 16Z 首锚验收 | integ 执行 / lead 监督 | **最早 09-29 13:00Z;保守 09-30 13:00Z** | 由 #8 决定 |

- 关键路径是 **#8 候选生产者树**。#2–#7 在 09-27 到 09-28 就能完成,只要 dlarch 的 GPU 在 09-27 有空。
- (ii) 满足用户「10-01 或更早」的目标。

### 选项 (i):等九月 zip(训练多一个月,并有九月归档核对)

| # | 项 | owner | 预计完成(UTC) | 依据 |
|---|---|---|---|---|
| 0 | 选项 (ii) 的 #2–#10 全部先做一遍,作为演练 | 同上 | 09-28 至 09-29 | 同上 |
| 1 | 九月 zip 发布 | 交易所 | **10-01 约 08–10Z** | 实测 9/9 个月都在次月 1 日 07:59–09:42Z 发布 |
| 2 | 九月 API 源(毫秒键)拉取 | news2 | 10-01 00:00Z 后约 15 分钟 | 装置 d10_pull_api_funding_ms.py,测试 4/4 |
| 3 | 拉取 + 校验(1b)→ ledger_ms rev 2(1c)→ 复审计(1d) | news2 | 10-01 约 11Z | 拉取约 20–60 分钟;1c 实测约 3 分钟;复审计分钟级 |
| 4 | **NC 轴延长到 09-30(价格、标签、King 特征、成员)** | **未指派** | **未知** | 不只是资金费;**必须先指派 owner** |
| 5 | D10 特征 2a–2d | news2 | 10-01 约 13Z | pass1 上次 69 分钟;其余是分钟级 |
| 6 | F10 三个种子 + 书层格 | dlarch | 10-01 约 16:15Z | 同 (ii) #5–#6 |
| 7 | King | fresh2 | 与 #6 并行(约 2.5 分钟) | 训练窗不随选项变 |
| 8 | lead 判词 → 用户裁定 U | lead / 用户 | 10-01 晚 → U | 用户时区 +08 |
| 9 | 平价门 4a(对用九月数据重跑后的候选树)+ 电池演练 | news2 / integ | U 之前 | — |
| 10 | 发布窗 → 16Z 首锚验收 | integ / lead | **最早 10-02 13:00Z;保守 10-03 13:00Z** | 10-01 的 13Z 窗在读数之前,赶不上 |

- **(i) 最早 10-02**,晚于用户「10-01 或更早」的目标。另有一项 #4 未指派,工期未知;不先指派,(i) 就没有可信的日期。
- (i) 与 (ii) 的差别:约 3 天(或 1 天,取决于 integ 的树用的是中位还是保守估计),换来 F10 多一个月的训练数据和九月归档核对。
- **King 两种选项没有区别**(fresh2;lead 06:4xZ 确认 A0 形态 = 年折 + 服务用 fold 2026,训练窗截在 2025-12-22):King 不在任何一个选项的关键路径上。截到切点的全量服务模型另立判据,十月不做。

## 7. 冲突与未定项(冻结前请 lead 逐条裁定)

> **状态(news2 06:4xZ)**:11 条 lead 已逐条裁定,见文末「§7 裁定」。第 1–8 条和第 11 条已改进上文(§0、§3a、§3b、§3c、§4);第 9、10 条待用户确认;第 10 条的两个日期见 §6。下列原文保留,作为出处。

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

---
## 用户裁定(2026-09-27 07:0xZ,lead 以 AskUserQuestion 请示,用户选择)
- **第 10 条(时间)**:用户选「**训练截到 09-01,约 09-29 发布**」,即方案 (ii)。最早窗 09-29 13:00Z,保守 09-30 13:00Z。发布前仍须满足三条:通过冻结的书层判据(DL 书层门修订 4/5)、平价门 4a、电池全绿,并**再请用户最后确认**。
- **第 9 条(安装人)**:用户选「**integ 执行,lead 监督**」。
- 至此 §7 全部裁定完毕。lead 冻结本 runbook:以 §7 裁定、本节与 §6 的 (ii) 表为执行依据。方案 (i) 与「NC 轴延长到 09-30」那项未指派前置,不再列入十月。

## §6 追加(news2,冻结后;原文不动)

### 更正 1:「10-01 或更早」不是用户原话(lead 07:0xZ 指出)
§6 与 §7-10 里写的「用户『10-01 或更早』的目标」,出处是 `RULING_user_D10_…` §4「执行(lead 安排)」,是 **lead 的排期目标**,不是用户的原话。用户的原话是该文 §1 那句,以及「尽快上线 = 修完已知缺陷后以最佳效果尽快上线,不上过渡版」。上文原句保留,以本条为准。

### 更正 2:(ii) 表第 1 行,legs 不能沿用线 D 的 legs_d10(dlarch 查出,lead 裁定)
- **问题**:`legs_d10 104af853` 是用**在役** King booster 在 D10 特征上重新预测建出来的(King OOF `ac2fad4d`),King 并没有重训。十月联合臂里的 King 是 fresh2 重训的,分数不同,所以 legs 也会不同。
- **新增一步 1b(2d 重建 legs)**:
  - 执行:news2 用 `d10_stage2_legs_oct.sh` 运行,即 `--king-oof <fresh2 十月 King OOF> --king-oof-sha <其 sha> --out <新目录>`。
  - 与 d10_stage2_legs.sh 的 d10 模式相同的部分:nc_legs.py 代码不改,fund_state_d10 用 f07e4ebd,NEWS_FEATURES_D10 用 f1cd3fa2。
  - 不同的部分:King OOF 由参数传入,并先核对 sha;输出目录必须是新的。
  - 产物交给 dlarch 训练 F10。收据写明所用 King OOF 的 sha。
- **前置控制**:用线 D 的 King OOF(`ac2fad4d`)跑这个脚本,产物必须逐位重现 `104af853`。已于 06:53:42Z 起跑。
- **时间线**:fresh2 的十月 King OOF 预计约 07:00Z 出(看它的 MANIFEST_RELEASE)。legs 重建约 20 分钟。之后 dlarch 开工。**不改变 09-29 这个日期**,因为关键路径仍是 #8 候选生产者树。

### 执行记录(news2 为关键路径协调人;按实际完成时刻追加,每项核对收据;任一项滑期超过 6 小时立即报 lead)
| # | 项 | owner | 计划 | 实际完成(UTC) | 收据 |
|---|---|---|---|---|---|
| — | `common/funding_interval.py` 冻结 | news2 | 树开工前 | **09-27 06:45Z** | 2864babfd,契约 C6 |
| 2 | King 训练器入库 + 装置控制 | fresh2 | 09-27 10:00Z 前 | **09-27 06:40Z / 06:45Z** | 8dd1a0068;5078fd402(KOC_DONE all_pass=True 06:44:21Z) |
| 3 | 十月 King 训练(服务运行 --keep-models)+ OOF | fresh2 | 约 07:00Z | **09-27 06:58:08Z**(KOR_DONE release_ok=True) | e7181349d;MANIFEST_RELEASE 2d0fa3f9;OOF 274ba08a;要钉的 king_2026.txt 8534e56b(news2 在 pod2 实测 sha 一致) |
| 1b | legs 重建(2d),用十月 King OOF | news2 | #3 之后约 20 分钟 | **09-27 07:32:51Z**(控制 07:14Z 逐位重现 104af853;交付检查 L1–L4 PASS) | legs 383e3ddc;NC_LEGS_RECEIPT 390a860e;King OOF 274ba08a;只有 KZ/LR/WL 与线 D 不同 |
| 4 | F10 训练器入库 + 契约测试 | dlarch | 开工后约 3 小时 | **09-27 07:13:48Z**(G1 run 3 两折对在役 NC s42 逐位 IDENTICAL,19785f3c1;书层格装置 eb22eeb52、run_f10d10.sh rev 3 deffd121d 均写于读数之前;契约 35/35) | 19785f3c1;cc5b392d3;9fc2c664a |
| 5 | F10 三个种子 | dlarch | #4 之后约 3 小时 | 起跑 **07:37:13Z**;**s42 训完 08:36:12Z**(59 分钟,OOF 82db26dfa124);s2027、s7 进行中,预计约 10:45Z 全部训完 | registry dlarch_f10d10_train;/dev/shm/dlarch_f10d10/f10d10.log |
| 6 | 书层格(联合臂) | dlarch | #5 之后 15 分钟 | 起跑 07:37:38Z;**s42 格 08:51:33Z 完成**(RETAIN,ALL_PRECONDITIONS_PASS=True);s2027、s7 格随训练;预计最后一格约 11:00Z | registry dlarch_f10d10_cells |
| 7 | lead 判词(修订 4/5) | lead | 读数之后 | 待 | — |
| 8 | 候选生产者树 | integ | 最早 09-28 18Z / 中位 09-29 06Z(以开工时点顺延) | **开工待定,最早 09-27 17Z**(lead 09:2xZ:integ 先交事故恢复方案 → 用户裁定 → 恢复 → 恢复后首锚验收通过 → 才开工;开工时点由 lead 告知) | — |
| 9 | 平价门 4a | news2 | #8 之后约 1 小时 | 待 | — |
| 10 | 电池演练 + 窗内 safe_commit | integ | 窗前 | 待 | — |
| 11 | 用户最后确认 → 09-29 13:00Z 窗 → 16Z 首锚验收 | lead / integ | 09-29 | 待 | — |

### §3a 追加(news2,冻结后;fresh2 20b2b3619 入库,晚于上次点名)
- 十月候选 King 的发布运行驱动:`multi_asset/exports/research/king_oct_2026-09-27/devices/king_oct_release.sh`(pod2,PGID 3418054)。
- 写 MANIFEST_RELEASE.json 的装置:`multi_asset/exports/research/king_oct_2026-09-27/devices/king_oct_manifest.py`。integ 装包时,按它核对要钉文件的 sha(§3b「钉被判定的模型文件」)。

### 发布前提追加(lead 09:1xZ;实盘事故,见 STATE.md 顶部 09-27 09:1xZ 条目)
- **09-29 发布新增前提**:双执行器事故已结案,实盘已恢复,并通过验收。已有前提不变:书层门修订 4/5、平价门 4a、电池全绿、用户最后确认。
- 事故经过:旧机锁屏状态下仍在运行,两台机器同时跑执行器;08:31:12Z 旧机的 watchdog 平掉了整本书。新机现处于 reduce_only,**今天的发布全部冻结**。恢复方案由 integ 只读起草,经用户裁定后才执行。
- 研究侧照常进行:F10 训练与书层格(#5/#6)。**#8 候选生产者树的开工时间取决于 integ 的事故处置排期**:integ 原计划约 17Z 开工,如果顺延,#8 的「最早 09-28 18Z」随之顺延。滑期超过 6 小时,按规则报 lead。
