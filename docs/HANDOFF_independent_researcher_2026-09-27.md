> **创建:** 2026-09-27 12:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 交接总账;写给接手的独立研究员 | **作废条件:** 被新的 STATE.md 顶部条目取代;引用前先读 STATE.md 顶部

# 交接总账(2026-09-27):实盘、进程、研究结论、在飞工作与提交链

> **读法**:先读 §0,再读 §1 和 §2。凡是写「(提交 xxx)」的地方都能在仓库里 `git show` 核对。**任何数字引用前,先打开它的收据**(团队协议 `docs/TEAM_PROTOCOL.md`)。本文是摘要,不是收据。

---

## 0. 一分钟版

- **系统**:Binance USDT 永续,宽宇宙(约 450 名)、4h 锚(00/04/08/12/16/20Z)、市场中性,在役书 = **NC combo**(King LGBM 腿 + F10 资金费腿,由生产者 `shadow_loop_v3` → `combo_stage` 写书,执行器 `~/dl_quant_live` 在 N+24 分钟读书交易),gross 2.0×NAV,maker 优先。
- **今天的主事件**:迁移到新 arm64 Mac 后,**旧 Mac 其实没关(锁屏下 launchd 照跑)**,两台机器同时跑执行器 ⇒ 08:31:12Z 旧机 watchdog 把整本书(315 名,约 21.5 万名义)市价平仓;新机 08:47Z 随之跳闸,进入 reduce_only。当日已实现约 −6,473 USDT,NAV 约 107,230。旧机已由用户全部停掉。**恢复正在进行**(见 §1.3)。
- **研究的主结论**:
  1. 资金费以外找截面增量(S1 逼空、S2、T7 韩元溢价)**全部 FAIL**;原因是「加强的基线 + 稀释代价」:新源要在全集上有约 0.02 的低相关 IC 才有增量。建议主力转向「组合/执行/风险」,只留 S3 前向与代币解锁可行性两条便宜线。
  2. **King 的问题是模型老化**:在役服务模型训练截止 2025-12-22,到 10-01 约 283 天;月训在 A0 老到 270 天以上时 IC 优势最大。但 IC 改进没有变成书层改进(pre-2026 走构成通道被吃掉,含多付资金费)。「King 服务模型换新」已预注册并在跑。
  3. **十月 D10(资金费间隔用交易所真值、训练=服务)** 联合臂书层判词 **UNDECIDED**;描述性重读(补齐切点之后的资金费)在跑;是否 09-30 发布需用户裁定。
- **今天冻结的发布**:GAP4(缺锚类修复)、M3 on(BTC beta 对冲,用户已批准)、前瞻影子 A/B。全部待恢复后重排。

---

## 1. 实盘

### 1.1 链路与版本(2026-09-27 12:28Z 实测)
| 组件 | 位置 | 版本/sha | 触发 |
|---|---|---|---|
| 生产者 | `~/wide_shadow/shadow_loop_v3.py`(非 git,快照入研究仓) | sha 52baf979 | launchd `com.hsy.shadowloop`,N+12 |
| combo | `~/wide_shadow/fea171/combo_stage.py` | sha 12a76de8 | `com.hsy.combolive`,N+17 |
| 执行器 | `~/dl_quant_live`(git,GitHub `allenamy/dl_quant_live`) | 运行树 HEAD **d01e35d**(= origin/main) | `com.dlquant.live.anchor`(launchd 按本地时间 +08) |
| 其余作业 | 21 个 `com.hsy.*` / `com.dlquant.*` | — | `launchctl list \| grep -E "hsy\|dlquant"` |
- **执行器改动只经 `ops/safe_commit.sh` + 电池全绿**;离线电池在隔离克隆里跑 `ops/run_acceptance_offline.sh`(完整 state 拷贝)。新机上旧 A10 测试必红(依赖旧机 pmset 日志),修复在 fix-pkg-e 克隆 `cea1e15`,**须随第一个执行器提交发布**(integ 手册 `docs/DEPLOY_gap_classfix_2026-09-26.md` rev 3)。
- 验收装置:`multi_asset/exports/research/nc_2026-09-23/receipts/anchor_accept_2026-09-25/accept_anchor_v2.sh <A> <out>`;逐锚深查第一条命令必须是 `inspect_anchor.py`。
- 场所只读查询:`multi_asset/exports/research/common/venue_quiet_window.py`(静默窗 [N+1:00, N+3:40],避开 N+24..N+30);恢复装置 `multi_asset/exports/research/recovery_2026-09-27/devices/venue_readonly.py`(GET 白名单)。

### 1.2 迁移与事故时间线(UTC)
- 09-26 12Z/16Z、09-27 04Z:三次缺锚(旧机停机 + 迁移)。combo 的前一锚状态按「恰好 A−4h」查找,缺锚 ⇒ 零状态 ⇒ gross 塌到约 0.07 ⇒ ABORT。实例修法 `combo_state_bridge.py`(rev 1 `bf02a7c3f`);**类修法 GAP4**(判官 PASS 25/25 于 x86,`99fd8f1c6`;arm64 复核 `dbe522c4d`,**未发布**)。
- 05:01Z 新机启用 21 个作业;迁移收据 `776526cef`。
- 08Z:新机第一锚。生产者/combo/parity 全绿(combo kc/fc 来源 own,gross 0.792)。
- **08:31:12Z 旧机 watchdog 平仓整书**(clientOrderId 前缀 `F20260927083112`);08:47:50Z 新机跳闸(§4-5b/§4-5e split_unauth 100.2%)。事故记录 STATE.md 顶部(`e754f1a5e`)。
- 12Z:新机照常出书(combo 318 名,gross 0.789,own/own),执行器 reduce_only、空书不交易。
- lead 的错:把「旧机已关」当事实,没实测单写者、没轮换密钥。类修法提案(未实施,受 §9-F7 冷静期约束到 09-30 08:47Z):迁机即轮换密钥;执行器锚前预检「上一锚以来的未知 orderId/成交 ⇒ HOLD」;rid 带主机短码(integ 恢复方案 §4)。

### 1.3 恢复(进行中)
- 用户 12:2xZ 裁定:**直接尽快恢复,不等密钥轮换**(旧机已全部停掉)。
- 步骤单:`docs/PLAN_recovery_after_double_executor_2026-09-27.md` §7(integ)+ 通用手册 `docs/RUNBOOK_post_trip_resume_generic_2026-09-27.md`(alloc)。要点:静默窗内 Q1–Q4 只读核验(无挂单、无持仓、平仓后无外来成交)→ 隔离克隆 `recheck_clone.sh` 跑 `resume_from_trip.sh --check` → `LIVE_MODE=LIVE bash ops/resume_from_trip.sh "<原因>"` → 首锚按 §8 加查(外来 orderId=0、到位率 ≥0.60、taker 份额、blocked_by_halt=0、无再跳闸)。历史重建 1–2 锚到位,成本约 110–290 USDT。
- **结果**:13:01Z 已恢复(`f332176c3`),首锚 16Z。用户裁定密钥暂不轮换;K1(外来 orderId = 0)只查恢复后的前几锚(16Z、20Z、09-28 00Z),见 STATE 顶部。
- **结果以 STATE.md 顶部最新条目为准。**

### 1.4 未发布的包(全部冻结,恢复后重排)
| 包 | 内容 | 状态 | 手册 |
|---|---|---|---|
| GAP4 | 缺锚后的前一状态回退与成员历史重算(类修法) | x86 25/25;arm64 判官 FAIL 仅在 beta_overlay 1–2 ulp(跨主机),第 5 轮(同主机 C0 current_vs_archived)按方案 B 待跑 | `docs/DEPLOY_gap_classfix_2026-09-26.md` rev 3 + P5 澄清 |
| M3 on | beta_overlay shadow→on,cap 2.5(用户 09-23 采纳、09-27 批准上线) | 电池 166/166(演练树) | `docs/DEPLOY_m3_on_2026-09-27.md` rev 1 |
| fix-pkg-e | 资金费类修复、发布边界 v2、per_name_stop(B)、anchor_report | 168/168(cea1e15);毛额守卫阈值待定,G-a 待用户 | integ 收据 `fixpkg_e_2026-09-27/` |
| 前瞻影子 A/B | NOKING/KHALF/FUNDONLY 对 LIVE_REPLAY,12 周不偷看 | 判据冻结 `7f47461e6`;arm64 复验 `203d77cd2`;GAP4 后重核挂钩再装 | `docs/DESIGN_forward_shadow_ab_2026-09-27.md` |

---

## 2. 研究结论(按线;每条带判据与收据)

### 2.1 资金费以外的收益源 —— 全部未过
| 线 | 判据 | 结论 | 收据 |
|---|---|---|---|
| S1 逼空状态(L2N) | `DECISION_RULE_nonfunding_sources_2026-09-27.md` | **FAIL**:8 段 IC 0.005–0.010、下界全 >0,无一 ≥0.015;σ 守卫对校准回归等于第二道 IC 门 | `af8d3b07e`,`docs/RESULT_S1_squeeze_gate_NC_2026-09-27.md`(06:5xZ harness 暴露过一格读数,已具名) |
| S2 | 同上 | FAIL | 同判据文件 |
| T7 韩元溢价 | PREREG_T7_S1 + AMENDMENT 1/2/3(`21ecc60f5` / `435559a61` / `70edf17ed`;G2 红后先写裁定 `9a3efb684`) | **四候选全 FAIL**;K1/K2 方向与假说相反;K3 单独 IC 为正但增量仅 +0.0009 | `be6c1b633`,`uplift_r2_2026-09-13/T7/RESULT_T7_S1_NC_2026-09-27.md` |
| XIB(Amihud) | — | 暂缓(不是独立源,ρ≈0.9) | — |
| S3 跨所 | — | 前向采集中(本机 launchd `com.hsy.xvenuecollector`),约 2027-03 评估 | registry |
| 代币解锁 | — | 只可能作多头风险闸;先做四步零收益可行性 | `bc7d022c3`,`docs/FEAS_token_unlock_2026-09-27.md` |
| **综述** | — | 停止大范围找新截面源;主力转「组合/执行/风险」,用高功效终点 | `b8233a187` + 更正 `12a3bbaaf`,`docs/SYNTHESIS_nonfunding_2026-09-27.md` |

### 2.2 King
- **改进族 IC 判词**(`d585e1792`):KN(扣资金费标签)FAIL;**A1 按月重训 FAIL(仅差 2026 点估计 16.9 vs 门 20;pre-2026 +73.3 8/8 为正)**。泄漏审计干净(`b1068aaf2`;L4c 保留已撤回,A0 同底 `6229e9c22`)。
- **机制**:A1 增益来自年折模型老化(A0 头 90 天 ΔIC≈0,270 天以上 +107~+164e-4);「数据更新」与「数据更多」分不开。
- **根因**(`446f4704b` / `c55a38816`):2026 King 伤害经席位而非构成(SEAT_ONLY +5.51、COMP_ONLY −1.12;4 月占 67%)。
- **A1 席位拆分判词**(`c381924f2`):pre-2026「经席位」**未被支持**(COMP 扛 −2.08/−2.45,含多付资金费 +0.85);2026 不可判(几乎全是交互项)。G4 终版已更正(`239bace3d`)。
- **King 服务模型换新(KSR)**:判据 `5b4fc6cda` + 修订 1 `c1f9571b5`(红控移到 IC 层);设计 `docs/DESIGN_king_serving_refresh_2026-09-27.md`;门 1、门 2 PASS(`de68ff03b03`);**arms 在跑(dlarch),书层 36 格由 fresh2 执行**。判词最高到 OPTION_FOR_USER。

### 2.3 F10 / DL / 十月 D10
- 用户裁定(09-25):资金费费率与结算间隔都按交易所真值,训练=服务(`docs/RULING_user_D10_funding_interval_truth_2026-09-25.md`)。
- 十月 runbook **已冻结**(`1fa4e3be5`),§7 十一条裁定、用户裁定 2 把发布顺延到 **09-30 13:00Z**(§9-F7 冷静期)。
- 十月 King:在役 A0 配方 + D10 特征(不改训练窗),产出 `8534e56b`(要钉的服务模型,fresh2 `e7181349d`)。F10 三种子 D10 训练(dlarch)。
- **书层判词 UNDECIDED**(`6838a219a`,`docs/VERDICT_D10_joint_arm_book_gate_2026-09-27.md`):2026 延长 +2.24(3/3)但主要来自切点后 19 天的伪影窗;截断版 +0.65(2/3);pre-2026 −0.95(1/3)使条件 3 不成立;s42 回撤深 3.33pp。
- **描述性重读(在跑)**:把 D10 账本延长过切点(`docs/PLAN_d10_reread_past_cut_2026-09-27.md`,修订 1 `7f2a559c4` 加 King 用冻结 booster 重预测)。R1–R5 已过(R2 的 V1 按 (a) 具名记录:比较器字面 DIFFERS,行为不变);R6 装配在跑,之后 fresh2 R6b → R7 legs → dlarch 重打分(恒等 PASS `f625e98973d`)+ 三格。**判词不改,只供用户裁定**。
- 早先 DL 结论:F10 满窗三次独立为负(F10_FULL、FRESH F10 臂、R1.4);DL 书层门修订 1–8 见 `docs/DECISION_RULE_dl_program_book_gate_2026-09-25.md`。

### 2.4 组合层 / 执行
- 组合层均值门在 pre-2026 无功效(在役书 t 1.6–1.9);改用 IC 层与风险终点(`docs/DECISION_RULE_combination_layer_2026-09-26.md`)。
- 「空头腿偏重」**撤回**:偏斜存在于组合层,但执行器下单前 `RESHAPE_REDEMEAN` 把净额中性化(09-25 已裁定;alloc 分解 `0b28d38a5`,更正 `12a3bbaaf`)。步 0 分解作为组合层事实保留(交易带为主,截断约一成)。
- 平仓后停机窗:设计 `4773a104b`(受 F7 约束只作分析;H1 自动恢复挂起,等锚前外来单预检),通用恢复手册 `63e878407`。
- 实盘书对 BTC 日 beta 约 −0.35 ⇒ M3 对冲(用户已采纳)。

### 2.5 数据链 / 十月重建装置
- 干跑 16 行全过(`209714e66`),途中抓到两个装置漏 import(`ac8960d8b`,加 C5 守卫);链上装置在干跑后又改过(durable_write、ledger_ms rev 2.x、d10_rebuild_funding_features)⇒ **rerun6(全部 16 行)待跑**(news2 在 D10 重读之后)。
- ledger_ms rev 2 验证(`e5605ab85`,读数后修订已标、三变异全红);rev 2.3(`bd6d2bdd7`)修 fold_removed 计数。
- 资金费归档作业新机首跑 6/6(`0c1394e52`)。

---

## 3. 在飞工作与负责人(12:3xZ)
| 负责人 | 在做 | 下一步 |
|---|---|---|
| news2 | D10 重读 R6 装配(pod2) | R6b(fresh2)→ R7 legs → 交 dlarch;然后 rerun6;十月关键路径协调(runbook §6) |
| dlarch | KSR arms(pod2);D10 重读的重打分与三格 | KSR IC read + H2 → 清单交 fresh2;D10 重读交表 |
| fresh2 | 待 news2 新特征做 King 重预测(恒等已 PASS);KSR 书层 36 格(等清单) | — |
| alloc | 空闲(S3 看守 cron) | 停机窗步 0(实盘恢复并首锚验收后由 lead 通知) |
| integ | 恢复方案已交 | 恢复后:GAP4 → M3 → D10 候选生产者树(关键路径,最早 09-28 18Z) |
| fresh | 空闲 | 影子 A/B 等 GAP4 后重核挂钩 |
- 在飞登记:`multi_asset/exports/research/loop_2026-09-26/INFLIGHT_REGISTRY.json`,**只许用 `registry_edit.py add|close|note` 修改**;巡检 `inflight_status.py`(pod2 + 本机)。
- 巡检日志:`docs/PROGRAM_loop_2026-09-26.md` §3。

## 4. 待用户/下一任 lead 裁定
1. 恢复后首锚验收通过 ⇒ 通知 alloc 起停机窗步 0;重排 GAP4 / M3 / 影子 A/B 的窗。
2. **D10 是否在 09-30 13Z 发布**(书层 UNDECIDED;看描述性重读)。
3. API 密钥轮换(用户暂缓);类修法 a–d 在 09-30 08:47Z 之后预注册。
4. KSR 判词出来后(OPTION_FOR_USER 或否)。
5. fix-pkg-e 毛额守卫阈值(G-b/G-d)与 G-a。

## 5. 代码版本与提交链
- **研究仓**:`~/Desktop/quant_research`(iCloud 桌面),分支 **`research/book-uplift-2026-09-11`**,HEAD 见 `git rev-parse HEAD`(本文写入时的前一提交 `99e384eca`)。**该分支没有推到 GitHub `allenamy/dl_quant`**;交给外部研究员前需要用户决定是否 `git push -u origin research/book-uplift-2026-09-11`。里程碑 tag:`milestone-2026-08-26`。
- **执行器仓**:`~/dl_quant_live`,`main` = origin/main = **d01e35d**。未发布候选克隆:`~/cc_tmp/gapfix4_exec_20260926T1911Z`(201188d)、`~/cc_tmp/m3on_exec_20260927T0059Z`(a6f8c21)、`~/cc_tmp/fixpkg_e_exec`(cea1e15)。
- **生产者**:`~/wide_shadow`(非 git);shadow_loop_v3 52baf979、combo_stage 12a76de8。
- **pod2**:`/workspace/`(研究产物;配额紧,大写入前先写探针)、`/dev/shm`(tmpfs,约 6 GB 余量)。
- 近 24 小时约 590 个提交;按主题查:`git log --since=2026-09-26T12:00Z --grep=<关键词>`。

## 6. 纪律(接手必读,全文见 `docs/TEAM_PROTOCOL.md` 与 `docs/ERROR_LEDGER_2026-08-20.md`)
- 判据先入库再出数;读数后修订必须标明,并用变异控制证明分辨力;**不许重跑到绿**。
- 盲态:实盘执行数据只报合池量与臂平衡。
- 提交必须带 pathspec;引用哈希只从当轮 git log 复制(E-0927-E)。
- 长作业必须带送达机制;标记写在与产物不同的卷;pod2 ≥1 GiB 写入先探针(E-0927-C/D)。
- 引用记忆要读到最后一节(含更正)。
- 任何时刻只能有一台机器跑执行器;迁机先轮换密钥(本次事故)。

---
## 7. 接手时刻的状态与首要动作(追加 2026-09-27 14:0xZ;lead 额度用尽,预计 09-30 接回)

**实盘**:13:01Z 已恢复,原参数(`f332176c3`)。16Z(1790524800)是恢复后的首锚:从空书重建,预计 1–2 锚建满。密钥按用户裁定暂不轮换。旧机实盘作业已停,**不要开旧机**。

**接手人要按时间做的事**
1. **16Z 首锚验收**(16:50Z 之后,执行器写出 `anchor done` 之后):
   - `zsh multi_asset/exports/research/nc_2026-09-23/receipts/anchor_accept_2026-09-25/accept_anchor_v2.sh 1790524800 <out>`
   - 静默窗内跑场所侧:`/usr/bin/python3 multi_asset/exports/research/recovery_2026-09-27/devices/venue_readonly.py anchor --anchor 1790524800 --out multi_asset/exports/research/recovery_2026-09-27/receipts/ANCHOR_1790524800.json`
   - 按 `docs/PLAN_recovery_after_double_executor_2026-09-27.md` §8 判:K1 外来 orderId = 0;K2 到位率 ≥ 0.60;K3 taker 份额(描述);K4 blocked_by_halt = 0;K5 没有再跳闸;K7 成本。integ 会离线独立算账本侧并对照。
   - K1 在 20Z 与 09-28 00Z 再各查一次(用户裁定只查前几锚)。
   - **K1 ≠ 0 或再跳闸** ⇒ 停止,不许再跑 resume;报用户。
2. 16Z 验收通过后:通知 **alloc** 起停机窗步 0;通知 **integ** 开工 D10 候选生产者树(关键路径,最晚完成 09-30 09:00Z)。
3. **D10 描述性重读已出(c44c56675)**:2026 仅 +0.67(原 +2.24 是伪影),pre-2026 −0.95,s42 回撤深 3.33pp;lead 倾向 09-30 **不发布**,见 VERDICT 文件附节。原文:数字出来后与判词 `6838a219a` 并排,**呈用户**,决定 09-30 13:00Z 发不发。冻结判词 UNDECIDED 不改。
4. **KSR 书层 36 格**(fresh2,预计 09-28 01–04Z 完成):按 `DECISION_RULE_king_serving_refresh_2026-09-27.md` §2 下书层判词;IC 层已 PASS(`82ce7fd13`)。判词最高只到 OPTION_FOR_USER。
5. **rerun6**(news2,排在 D10 重读之后):按预声明 `RERUN6_EXPECTED_DIFFS_2026-09-27.json`(c9765f2c3)机械判,预声明之外的差异一律 DIFFERS 并查原因。
6. **冻结中的发布**:GAP4 → M3 on → 影子 A/B,每个占一个静默窗 [N+1:00, N+3:40],都在 16Z 首锚验收通过之后;执行器改动只经 `ops/safe_commit.sh` 加电池全绿,A10 修复随第一个 W3 提交。手册见 §1.4。**这些属于书行为改动或发布,开窗前请先得到用户的同意。**
7. 巡检:`docs/PROGRAM_loop_2026-09-26.md` §0 的 30 分钟循环规则;在飞看 `inflight_status.py`,登记只用 `registry_edit.py`。

**代理**:dlarch、fresh2、alloc、integ、fresh、news2 都在本会话里。lead 离线后,它们只收尾在飞作业、提交收据,不开新的重作业、不做部署。它们的交接件是 `docs/HANDOFF_<名字>_2026-09-27.md`,以及各自给 lead 的最后一条消息(已写进仓库的收据)。
