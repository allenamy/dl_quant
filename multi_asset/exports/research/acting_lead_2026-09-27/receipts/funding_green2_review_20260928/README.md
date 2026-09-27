> **创建:** 2026-09-28 02:37 SGT | **Session:** acting-lead/research_resume_0927 | **状态:** final（独立结构审查完成，完整wrapper验收归root） | **作废条件:** GREEN2两源SHA或append-only合同改变；不能替代全wrapper终态或历史disposition。

GREEN2相对 `eea02b2` 的四项已发现结构缺口均关闭；本轮无需因这四项继续修改实现。**实现审查可以结束，完整实现验收须等正在运行的同源wrapper给出完整终态并逐项处置原有历史disposition；此收据不授权上线。** 本件续接 `../funding_durable_review_20260928/README.md`，旧反例属旧SHA，不回写旧收据。

- **fresh/gap exact snapshot**：两条路径共用 `_strict_snapshot`，以精确 effective read_ts 选行。同精确时间同名冲突在两种行序都拒绝；完全相同重复仍成功；`nextafter(A,+inf)` 与 A 不再被 1e-6 容差合并。有限AST正反控已过。
- **损坏日条目**：strict `available_days` 对8位日期名的非目录显式拒绝；不再静默漏过。普通读者保留旧行为。
- **partial append与owner poison**：实际caller AST循环在第2笔部分写失败后保留第2/3笔原income并break；第1笔成功仍计1。`PilotLogger.funding` 自己记录失败，另一个直接调用也在物理写之前拒绝；实际最终 `_write_pending` 绑定 `still`。未复写坏尾或声称可自动恢复。
- **FD身份**：writer把原append fh传给ack，前后检查路径仍指同inode；dup reader检查stat/open FD/读取后路径一致，保存dev/inode，caller将此身份传给ack。路径在打开前、读中、读后确认前被换inode的有限反例都拒绝；成功分支fsync原fh及day/root。未把另open路径的FD当写入FD。

`ast_review.py` 只读取已pin源，抽取指定AST定义与一个实际caller写循环，在内存替代文件/日目录/状态；**没有import执行器模块、运行executor套件/变异进程、联网、访问真实状态或修改clone**。10项有限AST检查全部通过，stdout在 `AST_STDOUT.json`。既有新增E7–E9/D6–D7源码已只读核对：实际文件部分写、pending保留、owner poison、dup/新写者换inode均有对应控制；这些测试的真实执行结果仍由root的wrapper收据证明，不冒充我运行。

审阅冻结HEAD `056877397be50d8967452c30351451d41d347656`；funding源 `d96b377f86e9d55a1ddd7f63d94a60d872256b97d1b5cfa513c214292c9dfd69`；pilot源 `6e5ccf3ef25a190c8290a2e1058bfff9454e6e7f72fd1f6d48204e6ac48dd83a`。运行后再读SHA相同。精确行号、test源SHA、原样diff和工件SHA见 `MANIFEST.json` / `REVIEWED_DIFF.json`。

保留边界：dev/inode绑定不认证同inode内原地覆写或截断，也无法承诺ack后任意外部修改不丢记录；仍依赖append-only、维护互斥合同。新logger绕过funding caller直接续写损坏旧尾未作新增保证；正式重试caller会先strict读证据而拒绝。本轮不再扩展这个已注明的通用存储假设。历史disposition FAIL仍为FAIL；合法G/R完整回归及真实文件系统fsync仍须完整wrapper确认。

KSR在 `2026-09-27T18:33:59Z` reader DONE/FAILED均不存在，waiter18:33:02Z仍WAIT RUNNING，三准确PID/PGID/start_ticks存活（见 `KSR_STATUS.json`）。因此本次未读候选收益、未启动已批准终态后处理，也未增等待器。
