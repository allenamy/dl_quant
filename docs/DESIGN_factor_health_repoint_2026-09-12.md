> **创建:** 2026-09-12 11:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 事实表 + 方案(W5, 未写码; 前置 = W1 落地并写出首条 evals 账本) | **作废条件:** W5 落地后本文转收据; 或用户裁定退役该消费者

# DESIGN: factor_health 消费者改指本地实盘书 rank-IC 账本(PLAN G9; 用户字 09-12「修复所有漏洞」)

**一句话**: `ops/check_factor_health.py` 每锚经 ssh 去读一台 2026-08-06 起按裁定不再发布的研究机报告, 读不到就记 INFO「UNKNOWN」; 即便读到, 它监控的也是已退役 3 腿影子书的曲线, 不是在役 combo 书。结果: **自 08-06 起, 「因子是否在衰减」这条路径上无人在看在役书**, 而产物断言 #9 因「上游缺席 = 已知缺口」子句而空过。正确对象已经存在: #55 `ic_monitor.py` 在真实持仓上算实现 rank-IC(W1 修复后逐次写 `state/live/ic_monitor_evals.jsonl`)。W5 = 把消费者的数据源从 ssh 远端换成这份本地账本, 不改任何阈值语义之外的东西。

## §1 事实表(2026-09-12 只读实测; 行号 = 运行树 918559f)
| # | 事实 | 位置 | 后果 |
|---|---|---|---|
| F1 | 步 9 每锚 `CFH.run(notifier, log)`; 抛异常 ⇒ INFO「研究机可达性问题」 | `scheduler/run_anchor.py` L772–787 | 每锚一次 ssh 尝试 |
| F2 | `fetch()` 经 `ssh -o BatchMode=yes` 读 jpline `exports/live/monitor/daily_report.json`(超时 25 s); `_upstream_attribution` 再 ssh 一次(20 s) | `ops/check_factor_health.py` L104–130, L54 | 研究机影子监控 cron **2026-08-06 经用户裁定退役**(L343 自述: server = 训练 + 采集)⇒ 报告永久缺席 |
| F3 | 缺席分支: findings=`UNREACHABLE … Factor health is UNKNOWN`, 严重度 INFO, `factor_health_last.json = {ok:false, reason:report_unreachable}`; 告警按 episode 去重(`state/alarm_episodes/factor_health.json` episode 68f039b2, 09-04 12:45Z 起) | L186–220; 运行树 `state/factor_health_last.json`(实读) | 每锚产出同一份「不知道」, 无人被叫醒, 也无人在看 |
| F4 | 即便可读, 监控对象 = `curve.A_provisional_3leg` 的滚动 rank-IC(3 腿, 无 funding 腿); 文件头自证「口径错的仪器」(修正 4 腿 0.0425 vs 3 腿 0.0344, 同 132 锚) | L9–20 | 在役 combo 书(≈77% funding)从未是它的对象 |
| F5 | 产物断言 #9「decay monitored on the deployable caliber」 = `decay_judged or _fh_absent`; `_fh_absent` ⇐ reason==report_unreachable | `ops/assert_anchor_artifacts.py` L284–299 | 08-06 起恒为真 = **空断言**(与 0dfc0d87 §3 指出的 −2027 空集同形) |
| F6 | 唯一在真实书上测实现 rank-IC 的仪器 = #55 `ops/ic_monitor.py`(launchd 每日 01:30Z; spearman(场所实持仓名义, 下锚 mid 收益), r24/r48 阈值); W1 修复后每次判级追加 `state/live/ic_monitor_evals.jsonl`(level / judged / r24 / r48 / trigger / judged_windows / incomplete_windows / contract) | `docs/DESIGN_ic_monitor_contract_2026-09-12.md`; diff L596、L909–915 | 正确对象 + 新鲜度门 + 合同已在 |
| F7 | 四个套件 import 该模块: `tests_factor_health`(7 检查: 错口径不判衰减 / 累积旗标忽略 / 阈下告警 / 陈旧告警 / 窗内不告警 / 不可读=finding) `tests_frontier_staleness`(前沿≠报告到达) `tests_book_weights_effective` L251–261 `tests_alert_tiers_live` | `live/tests_*.py` | 改源必须让这四套仍然逐条有对象, 否则电池在守旧对象 |

## §2 方案(W5; 不改阈值, 不改步 9 的接线, 不动 #55)
1. **数据源**: `fetch()` 改读本地 `state/live/ic_monitor_evals.jsonl` 最后一条(无 ssh, 无网络); 记 `source="ic_monitor_evals"`。账本不存在(W1 落地后首个 01:30Z 之前)⇒ 与今日同型 INFO「账本尚未写出」, 但 reason 改 `ledger_absent`(与 `report_unreachable` 区分, F5 子句同步收窄)。
2. **对象**: 衰减判据 = 账本 `level`(OK / ALERT / DECIDE)与 `judged`; `judged=False`(新鲜度门 INCOMPLETE)⇒ 「未判, 原因 = 缺锚列表」, INFO, `decay_judged=False` **且**记 `not_judged_reason`; ALERT/DECIDE ⇒ 与今日「上游在场且显示衰减」同级 HIGH(L343 下方分支不动)。口径行逐字抄 #55 合同块(书级实现 rank-IC, 非模型分数 IC)。
3. **前沿**: `frontier` = 账本 `at`(判级时刻)与其覆盖的最新锚; 报告年龄门沿用 `MAX_STALE_H`(F7 的 frontier 套件语义不变: 「判级到了」≠「数据前进了」, 前者看 `at`, 后者看 judged_windows 里的最新锚)。
4. **产物断言 #9**: `_fh_absent` 只对 `ledger_absent` 放行且限 ≤ 30 h(首日); 之后 `decay_judged=False` 仅当 `not_judged_reason` 非空才不算 REGRESSION(INCOMPLETE 是门在工作, 不是监视器坏了); 其他情况 REGRESSION 恢复承重。
5. **测试**: `tests_factor_health` 逐格改对象(mock 账本): 新鲜 OK ⇒ ok; ALERT ⇒ HIGH; `at` 超 MAX_STALE_H ⇒ STALE; INCOMPLETE ⇒ not judged + 原因; 账本缺 ⇒ INFO ledger_absent; **旧码红**(旧码对 mock 账本无反应, 仍报 report_unreachable); `tests_frontier_staleness` 的「报告到了≠数据前进」用账本字段重演; gate_coverage 条目改写。
6. **落地**: 非锚窗 safe_commit(步 9 接线不变 ⇒ 运行时改动只在 `ops/check_factor_health.py` + `ops/assert_anchor_artifacts.py` 一子句); 首锚验收 = `factor_health_last.json.source == "ic_monitor_evals"` 且 `decay_judged` 或 `not_judged_reason` 二者之一非空。

## §3 前置与顺序
W1 落地(13:36Z 窗)→ 09-13 01:30Z 首次写账本 → W5 写码 + 克隆电池 → 非锚窗落地(最早 09-13)。在此之前每锚仍 INFO UNKNOWN, 与今日相同; 不新增风险。

## §4 不做
不复活 jpline 影子监控(用户裁定 08-06); 不在步 9 里直接算 IC(#55 已是那台仪器, 两处算会分叉); 不改 #55 阈值(R-11 另裁)。
