> **创建:** 2026-09-27 02:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 交接(用户迁移到新电脑,lead 暂停令);§5 追加于 09-27 14:1xZ(lead 离线) | **作废条件:** 下一个接手的 news2 会话读完并在 STATE 记下接手

# news2 交接说明(2026-09-27)

## 0. 在飞:无
- 本机:没有我的等待器或驱动在跑(`ps` 查过,没有 ssh 或等待循环)。
- pod2:我记录过的 PGID 全部已经正常结束,各自的日志末行如下:
  - 拉取 3280773:`COMPLETE`,17:59:59Z
  - 复审计 3292937:`COMPLETE`,18:02:42Z
  - 段 2 pass1 3302530:`COMPLETE`,19:47:20Z
  - legs 恒等 3302957:`LEGS_IDENTITY BITWISE`
  - legs d10:`LEGS_D10 DONE`
  - 段 3:`F10_SWAP_DONE`
  - 段 4:`STAGE4_DONE`
  - 段 5 引擎:`STAGE5_DONE`,20:30Z
- **本会话内没有任何需要续跑的作业。**

## 1. 线 D(D10 资金费)状态
- **「只换资金费特征」对照格 s42:已读完**(`ab8fc621e`)。
  - 读数(只作描述):对在役 NC s42,2026 段 D = −0.173 bps/日,SE 0.086,95% 区间 [−0.36, −0.03],本段分辨不出;pre-2026 为 +0.073,分辨不出。损失几乎全在价格通道。
  - 预先声明的十月含义**成立**:生产者改用 D10 规则,必须和按新特征重训同一次发布。
  - 收据:`multi_asset/exports/research/news2_2026-09-23/receipts/d10_2026-09-25/lineD/LINE_D_READING.json`。
- **链路与恒等控制**,每段都逐位重现了已交付的产物:
  - 段 1 King 重推理:`2b5e790f0`
  - 段 2a fund_state:`2da5d051a`
  - 段 2b/2c pass1 → NEWS_FEATURES_D10 `f1cd3fa2`:`7fe5b3473`
  - 段 2d legs `104af853`:`dacd303af` / `4b341d7fd`
  - 段 3 F10 `18226f97`:`8852c2a90`
  - 段 4 combo:`2da5d051a` / `0bcf33735`
  - 段 5 adapter 恒等与引擎格:`8852c2a90` / `3b1b00131`
  - 读数装置:`dc004fd07`,闭合定义按 lead 09-27 02:2xZ 的裁定
  - 方案与判据:`docs/PLAN_funding_only_control_cell_2026-09-26.md`(修订 1 + lead 冻结的 R1.3)
- **产物位置**:
  - pod2 `/dev/shm/d10_2026-09-25/lineD/`:KING_OOF_SWAP、fund_state_d10、legs_d10、R0/R2 根目录
  - pod2 `/workspace/d10_lineD_2026-09-26/`:NEWS_FEATURES_D10、p1 分片、F10_OOF_SWAP、combo_d10、引擎格 runs 与 RETAIN
  - /dev/shm 上的大件已经用符号链接指向 /workspace。**/dev/shm 可能被清掉;/workspace 的件是 sha 核过的真身。**

## 2. 十月重建待办(线 D 余下部分,按依赖排序)
1. **九月归档**:交易所约在 10 月初发布 2026-09 的月度 zip。用 `d10_pull_resume_pod2.sh` 的形状拉取,把月份改成 2026-09;拉取器已是 rev 1(`b8ff40110`,出错退出码为 4,manifest 持久写)。拉完后用 `d10_reaudit_jan_to_aug_pod2.sh` 的形状把月份扩到九月,再把 `ledger_full_ms` 延长到九月底,这是新产物,不覆盖 e179071d。
2. **按 D10 规则重建特征**:`d10_build_fund_state.py --mode d10`(fund_state)→ `d10_stage2_pass1.sh`(pass1)→ `d10_stage2_assemble.py`。每步都有恒等控制:snap 模式必须逐位重现 NC 的 fund_state;pass1 恒等分片必须逐位重现 NEWS_FEATURES。
3. **重训 King 与 F10**(判据:DL 书层门修订 4),与生产者改用 interval_d10 同一次发布(线 D 的含义条款)。生产者侧:把 `ingest_settlements` 的 snap_interval 换成 `common/funding_interval.interval_d10`,走部署协议。
4. **线 B 平价门**:`d10_parity_gate.py`,逐列 dtype 逐位比较,红即停。在生产者发布前后各跑一次。
5. **线 C 的 T+1 对账**:归档作业 rev 1 已交 lead 安装(`72027a9b9`,文档 `docs/DEPLOY_funding_ledger_archive_2026-09-25.md`)。**是否已经安装,新会话要先查 `~/funding_ledger_archive/runs/`**。

## 3. 其它未结项
- **实盘 LR 空洞**:09-26 08Z 起缺 3 格,已在 STATE 具名,待路径 A 补。reseed build 已加窗口连续门(`reseed_2026-09-26` rev 1,23/23)。**路径 A 的前提,已点名但未实现**:下一次 build 要以 INSTALL 记录为带时间戳的基底,因为跨安装边界做快照差分量不出追加数。见 `reseed_2026-09-26/receipts/contiguity_gate_2026-09-26/RESULT.md`。
- **资金费缺口回填**:lead 已于 21:13Z 安装,545 行,VERIFIED。类修复由 integ 实现在 `~/cc_tmp/fixpkg_e_exec`(7ff6968,未推送),我的复审意见已全部关闭,待全电池。
- **按源普查**(`4aef8ef10`):受旧生产者规则污染的结论清单在收据里。**NEW_S / FRESH 的结论要按那份清单重判**,属于 fresh 与 lead 的事,我这边无动作。
- **小件,已点名、低优先级**:归档作业 rev 1 的 launchd 上下文实测留在安装第 5 步(kickstart);funding_gap_backfill 的键集合检查若复用,要改成读 SCHEMA 的 required+optional。

## 4. 新电脑上接手的步骤
1. 读 `STATE.md` 顶部、本文件、`docs/TEAM_PROTOCOL.md`。
2. 确认 pod2 可达,并核对 §1 所列 /workspace 下各产物的 sha,与各收据一致。
3. 所有装置的 argv 都在各自收据的 `argv` 或提交信息里,**逐字照抄复跑**;注意各装置所用的解释器:
   - pod2:pass1/legs 用 venv314;F10、combo、引擎用 `/workspace/venv`
   - Mac:执行器相关用 `/usr/bin/python3`
4. 本机的 scratchpad 路径(`~/cc_tmp/claude-501/...`)不会跟着迁移。其中需要长期保留的件都已入库:暂存的真实跑收据、自测收据、pre20Z 副本的 sha 都在收据里。

---

## 5. 追加(2026-09-27 14:1xZ,lead 额度用尽、预计 09-30 接回;接手人见 `HANDOFF_independent_researcher_2026-09-27.md` §7,d889e647c)

**本节之后 news2 不开新的重作业、不做部署。** 唯一例外是 lead 已排定的 rerun6(见 5.3),它排在 dlarch 的 D10 重读之后。

### 5.1 在飞
- news2 自己:无(截至 14:1xZ)。rerun6 已备好,尚未起跑,见 5.3。
- 挡在 rerun6 前面的是 dlarch 的 `dlarch_d10_reread`(pgid 3483262)。14:07Z 实测它在跑 s7 格。fresh2 的 `fresh2_ksr_book_cells` 为它暂停。

### 5.2 runbook §6 (ii) 时间线(执行记录在 `docs/RUNBOOK_october_rebuild_D10_2026-09-27.md` §6「执行记录」,news2 为关键路径协调人)
| # | 项 | 状态 |
|---|---|---|
| 1 | D10 输入 | 已有 |
| 2 / 3 | King 训练器 / 十月 King + OOF | 06:45Z / 06:58:08Z 完成(fresh2) |
| 1b | legs(十月 King OOF) | 07:32:51Z 完成,legs 383e3ddc |
| 4 / 5 / 6 | F10 训练器 / 三种子 / 书层格 | 07:13:48Z / 10:32:29Z / 10:47:17Z 完成(dlarch) |
| 7 | lead 判词 | **UNDECIDED**(6838a219a)。新前提:用户对 UNDECIDED 的发布裁定。描述性重读的数字(dlarch 交表)与判词并排呈用户(接手人 §7 第 3 条) |
| 8 | 候选生产者树(integ) | **未开工**。16Z 首锚验收通过后开工(接手人 §7 第 2 条通知 integ) |
| 9 | 平价门 4a(news2) | 待 #8;约 1 小时。lead 离线期间不开新重作业,**#8 完成后由接手人决定谁跑**。装置与判据见 runbook §4a |
| 10 / 11 | 电池演练 / 09-30 13:00Z 窗 | 待;窗是有条件的(用户对 UNDECIDED 的裁定 + 事故结案 + 实盘验收) |

**#8 的滑期基准(报给接手人,不再报 lead)**:
- 09-27 23:00Z 仍未开工 ⇒ 报。
- 09-29 12:00Z 仍未完成 ⇒ 报;这是中位 06Z + 6 小时,开工若晚于 17Z 则相应顺延。
- **最晚可接受完成 09-30 09:00Z**。依据:窗前还要依次做完 4a(约 1 小时)、电池演练(25–85 分钟)、用户最后确认。晚于这个时刻,09-30 窗就不可达。

巡检:我的 30 分钟 patrol 由本会话的 cron 驱动,会话结束即停(执行与监督分属不同所有者)。接手后请按 `PROGRAM_loop_2026-09-26.md` §0 自己巡检;巡检行在我的 scratchpad `patrol.log`,那不是正典。

### 5.3 rerun6(十六行干跑重跑,lead 排定)
- 目录 `/workspace/d10_dryrun_rerun6_20260927T133902Z`,从 HEAD 同步,`CHAIN_DEPLOY_VERIFY PASS=True`(a6f16c86a)。refs 12/12 与钉住的清单相同(`RERUN6_refs_sha256_20260927T133108Z.txt`)。
- 预声明 `news2_2026-09-23/prereg/RERUN6_EXPECTED_DIFFS_2026-09-27.json`(c9765f2c3,sha 0b514102…),只有三处:
  - D1 收据多出 `rows_in_old_window`,值 = rows_new_ms;
  - D2a、D2b 收据的 `rebuild_device_sha256` 从 98c6b105 变为 a1015980。
  - runner rev 4 用 `--expect` 机械判:差异集合必须**完全等于**声明;声明之外的差异,或声明了却没出现,一律 DIFFERS,按原规则停。控制见 `receipts/rerun6_prereg_2026-09-27/CONTROLS.txt`。
- 起跑命令(pod2,过资源门后;用 `registry_edit.py add` 登记):
  `W=/workspace/d10_dryrun_rerun6_20260927T133902Z; setsid nohup /workspace/venv/bin/python -B $W/devices/d10_dryrun_run.py $W --part rerun6 --expect $W/prereg/RERUN6_EXPECTED_DIFFS_2026-09-27.json --expect-sha 0b514102aa092f96e2f33c669381529a16365d00d904fef55d152298e88a4d71 </dev/null >/dev/null 2>&1 &`
  - 日志 `/dev/shm/news2_dryrun_2026-09-27/rerun6/dryrun.log`,末行锚定 `DRYRUN_DONE` 或 `DRYRUN_STOP`;
  - 结果 `$W/out/DRYRUN_RESULT.json`。
- 起跑前先只核对一次(不同步):`python3 -B news2_2026-09-23/devices/d10_deploy_verify_chain.py --exp $W --out <新收据>`。
- 结果:**待填**(本节在跑完后更新)。

### 5.4 今天 11:01Z 交接之后做完的事(收据均已入库)
- **D10 描述性重读输入**交付 dlarch(85f2a340b):R3–R8 控制全 PASS,features ad80d50d,legs 37c0b5d3。
- **nc 执行版入库**(a41fd2496、2468cb368、966ca3954):nc_legs 18387627 / nc_hist_features 3eee6e88 与 README,原文件不覆盖。
- **事项 D**(e7235d50d):契约规则 W 也扫描 durable_write.py 本身,钉 1 处(它自己的临时写入器)。契约 37/37。
- **事项 A**(61432f487,rev 1 4996097bc;验收 220eaf7d6):`d10_deploy_verify_chain.py`,每次 pod2 起跑前的三方同一性检查,用 fresh2 的 `pod2_deploy_verify.sh`。runbook §0.2 追加(5a5fd4d43)。
  - 首次派生就抓到:1d 的模板驱动把 EXP 写死为 09-25 的旧部署。
  - rev 1 修了检查器把自己纳入自身清单的缺陷,红收据保留。

### 5.5 未结(news2 名下,lead 离线期间不动)
- 1d 新驱动 `d10_reaudit_months_pod2.sh` 未写(仅选项 (i) 或九月归档核对需要)。
- 平价门 4a 等 #8。
- 早先两个 rerun6 暂存目录(`..._133108Z`、`..._133729Z`)同步于 rev 4 / rev 1 之前,不用,也不删。
- ERROR_LEDGER:检查器进入自身清单一事,只写了记忆,尚未起草账本条目。
