> **创建:** 2026-09-16 | **Session:** FX-EXEC | **状态:** 交付(lead 两次要求的那一格) | **作废条件:** 克隆被重建或 state/ 再次被电池污染而未还原

# 继承克隆时 `state/` 不干净 — 逐项影响审计

交接文档称 **tree clean**。实测: **非 state 路径确实干净**(`git status --porcelain -- . ':(exclude)state'` 为空),
但 `state/` 有 **23 个被改动的跟踪文件**(22 M + 1 D)与大量未跟踪件, mtime **2026-09-13T18:01–18:03Z**
= 上一轮会话电池的残留。上一轮报告自称「已 `git checkout -- state` 还原」, **实际未还原**。

## 1. 被改动的跟踪文件(会话起始 `git status --porcelain -- state` 的 M / D 行, 23 项)
`_safe_commit_acc.log` · `alarm_episodes/artifacts.json` **(D)** · `alarm_episodes/factor_health.json` ·
`alarm_episodes/funding_span.json` · `anchor_runs.log` · `exchange_info_cache.json` · `factor_health_last.json` ·
`funding_last_pull.json` · `launchd_err.log` · `launchd_out.log` · `live/alarm_episodes/funding_span.json` ·
`live/exchange_info_cache.json` · `live/funding_last_pull.json` · `live/loop_state.json` ·
`live/nosleep_last_check.json` · `live/pilot_log/20260801/fills.jsonl` · `live/preds_latest.json` ·
`live/watchdog/last_eval.json` · `nosleep_last_check.json` · `notify_audit.jsonl` · `panel_cache/funding.npz` ·
`panel_cache/klines_1h.npz` · `watchdog/last_eval.json`

全部是**运行期产物**: 日志、缓存、告警发作记录、看门狗评估状态、面板缓存。没有一个是夹具或被冻结的输入。

## 2. 逐项: 有没有影响我已交付的红/绿判定

| 交付物 | 被测套件 | 读 `state/` 吗 | 结论 |
|---|---|---|---|
| NEW-02 | `live/tests_flatten_fee_backfill.py` | **否** —— 全文唯一命中是 docstring 里「nothing written under state/」那句; 夹具是 `live/tests_fixtures/e0912a_12z/`, 其余树由 `tempfile.mkdtemp` 造 | 不受影响 |
| NEW-02 真账本普查 | 六个普查脚本 | **否** —— 读的是 `~/dl_quant_live` 的**只读冻结副本**(逐文件 sha 在 `census_input_SHA256SUMS.txt`), 不读克隆 state | 不受影响 |
| gate_coverage | `live/tests_external_book.py` + `ops/gate_coverage.py` | **否**(0 处 state 引用) | 不受影响 |
| EXE-04 核 | `live/tests_reconcile_carry.py` | **否**(纯函数 + 一个 vendored JSON) | 不受影响 |
| TEST-01 | `live/tests_transport_resilience.py` 等四套 | **是, 且这正是被测对象** —— 但方向相反: 判定的是「套件**写**了 state 根什么」, 而红/绿两次探针都以 `rm -f state/venue_ban.json` 起步, 每次从同一起点测 | 不受影响(起点被显式归零) |
| 两条措辞更正 | 11 个邻格 | 部分读 | 见 §3: 全部已在**还原后的树**上重跑 |

## 3. 决定性的处置: 全部在还原后的树上重跑过
`git checkout -- state` 之后(2026-09-16T03:20Z, 事故清理时), 我在**还原后的树**上跑了 137 个套件中的 135 个
(干跑, 跳过两个只能在电池窗口跑的), 结果 **135/137 rc=0**。因此本轮任何绿判定都有一份「干净树」上的重跑背书, 不依赖残留。

## 4. 唯一一处 state **内容**真的决定了判词 —— 并且它与代码无关
`tests_alarm_digest` rc=1: 「only 0 readable alarms in 24h — NOT OBSERVABLE, not a pass」。
- 输入 `state/notify_audit.jsonl` 最新一条 = **2026-08-26T02:24:23Z**, 距今 **21.1 天**; 套件窗口是 24h ⇒ 窗口内 0 条。
- 该文件在 **ef60f85 与当前工作树逐位相同**(sha 5655d69347e57b92…) ⇒ **任何代码版本今天跑都红**, 与我的改动无关。
- 继承时它是 M 状态(最后写于 09-13T18:01Z), 那也早于 24h 窗 ⇒ **还原与否结论相同**。
- 这是「零分母必须红」的约定**正确工作**的样子, 不是缺陷。

## 5. 还原后的树
- `HEAD` = `3daa9786b3b873508ebf91bd2ff9979271e2f8b9`
- `git rev-parse HEAD:state` = **`38f4921dce2cca78cc173eb186ca89c07242219e`**
- 跟踪的 state 改动数 = **0**
- **未跑 `git clean -- state`**: 它会删掉既有的**未跟踪真实状态副本**(`state/live/pilot_log/202608*`、`rate_timeline/`、
  `fixtures/*.npz`), 而多个套件要读它们。还原 = 跟踪文件回 HEAD + 只删本次运行自己产生的件。

## 6. 给下一位的两条
1. **电池后还原 `state/` 是规则的一部分, 不是收尾礼节** —— 不还原, 下一位所有「修前/修后」对比都建立在被污染的树上, 而且没有任何东西会提示他。
2. **「tree clean」要按路径说清楚**: 本次交接说的是真的(非 state 干净), 但读者会读成整棵树干净。交接里写 `git status --porcelain -- . ':(exclude)state'` 与 `-- state` 两行, 比一句「clean」诚实。
