> **创建:** 2026-09-26 19:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** FROZEN 判据(写于任何实现代码之前;设计 = news2 RELEASE_AND_CLASS_FIX.md §3,7f08ff7cb / 515b3fb8c) | **作废条件:** lead 裁定;只追加 AMENDMENT

# 资金费账本类修复(fix-pkg-e 第 1 项)验收判据
验收问句:**明天再停机一次,还会不会漏行?**
被修对象:执行器 `live/binance_funding.py`(d01e35d):`positions_at` L270 回读老于一个锚间隔即拒绝;`write_funding_rows` L463 续跑点 = 盘上最新结算 + 1ms,跳过的行不落盘 ⇒ 永不重试。

## 规格(实现前冻结)
1. **待定价队列** `funding_pending.json`(执行器 state 根,与 funding_last_pull.json 同目录),内容为交易所原样 income 行(含 tranId)+ 首次入队时间 + 原因;写法 durable_io。每次拉取:候选 = 队列 ∪ 新拉的 income(按 (symbol, time, tranId) 去重);盘上已有 (symbol, settlement) 的行视为已写、出队不重写。出口只有两个:定价写入;或结算早于交易所 90 天保留期 ⇒ 具名移入 `permanent_gaps` 并 HIGH。
2. **顺序(不丢行)**: ① 先把「全部未写候选 + 本次要写的行」写入队列(durable);失败 ⇒ 本次拉取不写任何行、HIGH、返回失败;② 写行;③ 队列更新为「仍未写」;③ 失败 ⇒ HIGH(下次按盘上去重,不会重复写)。队列文件不可读 / 损坏 ⇒ 不写任何行、HIGH(fail-closed)。
3. **跨缺口定价**(现行 positions_at 拒绝时才尝试,逐名判): A = 结算 t 之前最新回读;三条同时满足才用 A 的 `venue_position_notional` 定价:(i) 存在 t 之后的回读 B;(ii) 该名在 (A, t) 之间经 `pilot_log.collapse_supersedes` 折叠后的成交为 0(有 fill_ts 缺失的成交 ⇒ 不满足);(iii) |qty(A) − (qty(B) − (A,B) 内净成交)| ≤ 0.5 × stepSize(stepSize 取执行器过滤器缓存 / broker.qty_steps;取不到 ⇒ 不满足)。A 中无该名或 qty(A)=0 ⇒ 不满足。行上加 `pricing_rule="carried_across_gap"`,`position_read_age_s` 记 A 的真实陈旧。不满足 ⇒ 留队,逐名具名原因,每锚 HIGH。
4. 正常路径(回读不陈旧)**行为与现码逐字段相同**,行上不加任何新字段。

## 测试(新套件 live/tests_funding_gap.py;先在现码上测出红)
| # | 构造 | 现码必须 RED(否则该测试无分辨力,作废) | 新码 PASS |
|---|---|---|---|
| G1 | 12h 无回读,缺口含 4h 名与 1h 名的结算;第 1 次拉取在缺口中(无 B),第 2 次在 B 之后,第 3 次在更晚 | 缺口行在第 3 次后仍缺 | 第 2 次拉取后缺口行全部写入,pricing_rule 正确,队列清空 |
| G2 | 同 G1,但缺口内给名 X 注入一笔成交 | —(现码本来不写) | X 的缺口行不写、在队列、告警点名 X;其它名照写 |
| G3 | 同 G1,但把 B 的名 Y 数量改掉 | — | Y 留队、点名;其它名照写 |
| G4 | G2/G3 之后续跑点越过缺口(写入更新的结算) | 现码:被跳过的行已不存在任何地方 | 队列仍保留 X/Y 并继续重试 |
| G5 | 队列文件写入失败(注入 DurableWriteError) | — | 本次拉取不写任何行、HIGH、报告 pending_write_failed |
| G6 | 队列文件损坏 | — | 不写任何行、HIGH(fail-closed) |
| G7 | 结算超过 90 天仍在队列 | — | 具名移入 permanent_gaps、HIGH、出队 |
| G8 | 幂等:队列里的行已由别处写上盘 | — | 出队、不重复写 |
| G9 | 正常路径(回读新鲜)同一输入,新码与现码写出的行逐字段相同 | 不适用(同一性控制) | 逐字段相同 |
| R1 | **回归**:20260926 真实日文件(回填前版本 `funding.jsonl.pre_gap_backfill_20260926T2111Z`)+ news2 录下的交易所答复 RAW.json,在 20:46Z 那次拉取的时刻重放 | 现码 545 行全部 skipped | 新码写入 **545** 行、0 留队、0 永久缺口,且每行 position_notional_at_settlement / funding_paid / funding_rate 与 news2 已安装的 PLAN 行逐字段相同 |
| R2 | 正控:1788033600、1790006400 两次缺锚附近的真实日文件,用盘上的 funding 行反推 income 重放 | 不适用 | 新码与现码写出的行逐字段相同(那两次执行器回读未断,不应触发跨缺口规则) |
全部经 `ops/run_acceptance_offline.sh` 在克隆里跑(新套件登记进 run_acceptance.sh 与 gate_coverage.py);判官 = 各测试自身的 check 计数,基线先绿(现码上 G9 / R2 必须绿)。
