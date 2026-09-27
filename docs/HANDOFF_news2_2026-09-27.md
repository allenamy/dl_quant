> **创建:** 2026-09-27 02:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 交接(用户迁移到新电脑,lead 暂停令) | **作废条件:** 下一个接手的 news2 会话读完并在 STATE 记下接手

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
