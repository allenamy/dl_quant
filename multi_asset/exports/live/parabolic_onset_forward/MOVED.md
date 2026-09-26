> **创建:** 2026-09-26 21:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(dlarch) | **状态:** 迁移说明(本目录自此为**冻结快照**, 不再追加) | **作废条件:** 长队列再次迁移或退役

# 长队列已迁出研究仓: ~/pof_long(launchd com.hsy.onsetfwd_long)

- **现行位置**: `~/pof_long/multi_asset/exports/live/parabolic_onset_forward/{events.jsonl, run_log.jsonl}`; 脚本 `~/pof_long/multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py`, 与本仓 `pilot_journal/tools/` 那份**逐字节相同**(sha `47dca131`, 未派生、未改一字; REPO 由脚本自身路径推出, 所以输出自然落在 ~/pof_long 下)。
- **执行者**: launchd `com.hsy.onsetfwd_long`, 每日 07:27Z(本地 15:27, plist 用本地时间; 短队列 07:22Z 之后 5 分钟), stdout/stderr → 同目录 `launchd.log` / `launchd.err`。plist 副本: 本目录 `com.hsy.onsetfwd_long.plist.receipt`。
- **迁移时刻的逐字节交接**: 本目录 `events.jsonl`(`d0a54b74`)、`run_log.jsonl`(`4d69f1e9`, 18 行, 末行 2026-09-25T06:19:49Z)、`README.md` 复制到新位置, sha 逐一相同; **本目录这两份自此冻结**, 不再更新(「替换, 不两份并存」, 882a86576)。
- **launchd 实跑证明**(不是我的 shell): 2026-09-26 21:00:45Z `launchctl kickstart` ⇒ run_log 新增一行, anchors_new 8, total 144 → 152, launchd.err 空, 脚本 sha 47dca131; `nc_forward_freshness.py` 对新路径 FRESH。
- **停跑原因(09-22 → 09-26)**: 此前的执行者是**会话驱动的 cron**(CRON_TEMPLATES_2026-09-04;每日 07:22Z 跑并提交「每日追加」, 最后一次 09-22)。那个会话的 cron 随会话消失后无人接手; 09-25 06:19Z 的一次是 dlarch 手动补跑, 同时写下「T0 之后迁到 ~/pof_long」—— 这个未来动作**没有执行者也没有台账条目**, 于是没发生(协议 §10-f 同形)。迁移(11:14–16:58Z)不是原因: 停跑早于迁移。
- **读数盲态不变**(CRON_TEMPLATES ④): 只报计数, 不看均值、不比 P 与 Q、不判; 复判由 lead 按冻结规则执行。
