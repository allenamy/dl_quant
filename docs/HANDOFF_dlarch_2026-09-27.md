> **创建:** 2026-09-27 03:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(dlarch) | **状态:** 交接(用户迁新电脑, lead 暂停令); dlarch 空闲待恢复 | **作废条件:** lead 通知恢复后由接手会话按 §5 续跑并更新本文

# 交接: dlarch(DL 架构线)2026-09-27 03:0xZ

## 1. 暂停时的动作(已做)
- 本地 Mac: dlarch 的后台等待器(Claude 后台任务 `btosm5o1i`, 一条 ssh 等待 `run_kic.sh`)已停。本地没有 dlarch 起的 cron。
- **本地 launchd 服务(不是作业, 按 lead 要求恢复的)**: `com.hsy.onsetfwd_long`(长队列前向日志, 每日 07:27Z, 目录 `~/pof_long/…`, plist `~/Library/LaunchAgents/com.hsy.onsetfwd_long.plist`, 仓库副本 `multi_asset/exports/live/parabolic_onset_forward/com.hsy.onsetfwd_long.plist.receipt`, 说明 `MOVED.md`, `17ad8b607`)。**迁机时要在新电脑上重建**(脚本、事件/运行日志复制到 `~/pof_long` 同路径, 装 plist, kickstart 实跑一次核 run_log 新增行), 否则 07:27Z 的 freshness 会 STALE。未卸载(当前不在运行, 只是排程)。
- 未提交的 dlarch 装置/收据: **无**(`git status` 核过)。pod2 上的大文件(T_NET.npz 等)不入库, 以收据 sha 钉。

## 2. pod2 上仍在跑的作业(自己跑完、自写终态)
| 作业 | PGID | 日志 | 终态标记(行首) | 登记名 |
|---|---|---|---|---|
| KN / A1 的 IC 读数执行者 `run_kic.sh 3366800`(`b81a5c63c` / sha eb9ad8f2) | **3366884** | `/workspace/dlarch_2026-09-24/king_fam_2026-09-27/kic.log` | `KIC_DONE rc=<n>` 或 `KIC_STOP <why>`; 收据 `/workspace/dlarch_2026-09-24/receipts/KING_IC_{KN,A1}_2026-09-27.json` | `dlarch_king_ic_readout` |
- 它等的上游: fresh2 的 `kf_manifest_ic3.sh`(PGID 3366800)写出 `/workspace/kingfam_2026-09-27/logs/kingfam.log` 行首 `KF_MANIFEST_IC_PAIRED_DONE <path> sha=<64>`(清单含 KN / A1 / A0 各 8 项)。fresh2 估 03:35–03:40Z。上游写 `KF_MANIFEST_IC STOP:` 或其 PGID 消失而无 DONE ⇒ 本执行者写 `KIC_STOP`, **不读任何数**。
- 它的 claim: `/workspace/dlarch_2026-09-24/CHAIN/.claim_KIC`(执行者结束时自删; 若恢复时仍在而 PGID 已不在, 先核 kic.log 末行再手删)。
- fresh2 侧(非 dlarch)仍在跑: KN/A1 训练(PGID 3365381)、King 根因 (3b) SEAT_ONLY / COMP_ONLY 四格 `rc_hybrid.sh`(PGID 3360754, 读数约 03:30Z)。

## 3. 在等的读数与下一步(lead 的优先级)
1. **(3b) 单条件格**(fresh2): 读 fresh2 的 `rc_read` 输出(路径待 fresh2 发), 逐月「总差 / 价格」对 RED 表; 与本线 `RED_SEATS_2026-09-27.json`(3–4 月 King 席位塌得最多)对照 ⇒ 写「经席位还是经构成」的逐月结论进 `docs/RESULT_dlarch_king_rootcause_2026-09-27.md`, 定稿(份额不可相加, 交互项照印)。
2. **KN / A1 的 IC 判词**: 读 `KING_IC_KN/A1_2026-09-27.json`(判据 `DECISION_RULE_king_improvement_family_2026-09-27.md` §3 + 补记 1 成员配对)。判词字段 `IC_LAYER_MAIN_PASS`、`segment_verdicts`; 参考列 `arm_dIC_vs_inservice_rs0_REFERENCE`。入库后报 lead。书层格(选 ΔIC 中位成员 × 2 F10 种子)由 lead 放行。
3. **King 根因终稿**: 合 (1)(2)(3a)(3a-2)(3b)(4)。
4. **候选(不跑, 等 KN)**: F10-N(F10 净额用 T_net 代替 y4s), 见 King 根因 RESULT 附录。
5. **D2**: 前置门 PASS(ridge), GPU 臂等 alloc A3 非劣 PASS 或 lead 裁。

## 4. 本会话的已交付(按主题, 提交号)
- F10_FULL 判词 REJECT `831d81a11`; R1.4 判词 REJECT `b94698283`(H-EP 不成立); G3 原因合成 `ff4daafcc` / `c02a4a008` / `e0383f41f` / `e3706b6ee`。
- D4 前置门 FAIL `4cbf1ee52`; D2 前置门 PASS `f337d696f`。
- 动量载荷 `28da4e143` / `786febf73` / `b84aa7e50` / `be5fb125a` / `3677a34b2`; M 族结果件附注 `eaf2b59de`。
- King 根因阶段 1 `dd1d5dae5` / `cb9c01510` / `ab9cea7b0` / `f4c3229b1` / `e0b5aa25c`。
- King 改进族装置: T_net + IC `1231f7f72` / `7e2ebafc7` / `6213fe12c` / `b81a5c63c`; T_net 收据与 IC 红控 PASS `621da7919`(T_NET.npz sha 929ff9f6)。
- 来源普查 `a40705c24`; 驱动完成性按类修 `3201239af`; 长队列恢复 `17ad8b607`; 协议 §10-f `8926b6245`、§10-g `ac7f92a88`。

## 5. 怎么续跑
- 若 `kic.log` 末行已是 `KIC_DONE rc=0`: 直接读 §3 第 2 条的两份收据, 入库(显式 pathspec), 报 lead。
- 若是 `KIC_STOP`(上游停了或超时): 等 fresh2 新的清单执行者, 取其 PGID, 在 pod2 上 `cd /workspace/dlarch_2026-09-24/king_fam_2026-09-27 && mv kic.log kic_runN.log && setsid nohup sh run_kic.sh <新 PGID> > kic.stdout 2>&1 < /dev/null &`, 登记 registry(已有条目 `dlarch_king_ic_readout`, 改 PGID 即可)。
- 若执行者仍在跑: 等其终态标记(绑 PGID 3366884 + kic.log 行首标记), 不要另起第二个(claim 会拒)。
- 团队规则照旧: 只杀自己记录的 PGID; 提交带 `-- <路径>`(§10-g); 判词装置先于读数入库; 「X 完成后做 Y」须有进程执行者(§10-f)。
