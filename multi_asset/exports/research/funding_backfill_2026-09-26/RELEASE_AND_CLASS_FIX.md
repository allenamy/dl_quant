> **创建:** 2026-09-26 21:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 交 lead 安装;类修复部分是交给 integ 的设计,未实现 | **作废条件:** 执行器 `binance_funding.py` / `pilot_log.py` / `binance_broker.py` 的 sha 与 `window/gates_plan_template.json` 中 G1 的不一致

# 资金费缺口回填:安装包 + 类修复设计

判据:`CRITERIA.md`。装置:`devices/funding_gap_backfill.py`。自测 9/9:`receipts/SELFTEST.json`。

## 1. 普查结果(只读,21:0xZ,`receipts/CENSUS_20260926.json`)
- **缺口**:08:44:51Z 回读 → 20:45:24Z 回读,是 2 天内唯一一对间隔超过 4.5h 的相邻回读。可回填窗口 = [12:44:51.182Z, 20:24:04.731Z)。起点是 A + 4h + 1ms,终点是 20Z 那一锚的第一笔成交。
- **成交**:两次回读之间折叠后共 335 笔,全部属于 20Z 那一锚的再平衡(A1790454240,20:24:04Z 起);**再平衡之外 0 笔**。
- **逐名数量**:318 个名全部满足「A 数量 = B 回读 − 20Z 净成交」,容差为半个 stepSize;**排除 0 个**。
- **普查装置第一版错了,已作废**:它没有按执行器的读者约定折叠 supersede 行。20Z 再平衡有 291 笔成交写了 mark 回填的 supersede 行,于是每名的成交被数了两次,233 个名被误判为「数量变了」,每一个恰好偏差净成交量的一半。作废件留在 `CENSUS_20260926_rev0_DOUBLECOUNT_void.json`。修法是调用执行器自己的 `pilot_log.collapse_supersedes`;P0 控制现在断言:未改动的那一天必须 0 排除。
- **逐笔金额**(settlement_ts、名、交易所 income)只能在 fetch 之后列出:执行器在 20:46 跳过这些行时没有保存金额,本地没有任何副本。fetch 是唯一需要联网的步骤。

## 2. 安装(lead 执行,静默窗内)
1. `window/gates_plan_template.json` → release_gates:G0 静默窗、G1 执行器三个模块的 sha、G2 普查(裁决要求 `excluded 0`)、G3 **fetch**(只读 GET:income 带签名、fundingRate 与 fundingInfo 为公开接口;需要与执行器 plist 相同的环境变量 `BINANCE_KEY/SECRET/BINANCE_LIVE_CONFIRM`,并在装置内部再调一次 `require_quiet_window`)、G4 plan。
2. **人工核 PLAN.json**:`n_rows_planned` = `n_income_in_window` − `n_already_present_skipped` − `n_excluded_rows`,预计约 545。`writer_report.skipped_no_position` = 0;`alarms_during_replay` 为空;逐行的 `position_read_age_s` 记录 A 的真实陈旧时长,最长约 11.6h。
3. `window/gates_apply_template.json`,把 PLAN 的 sha 填进 `<PLAN_SHA>`:G0、G5 apply(只追加进 `20260926/funding.jsonl`,旧文件先备份为 `.pre_gap_backfill_<STAMP>`)、G6 verify 必须为 VERIFIED。
4. **回滚**:`funding_gap_backfill.py rollback --root … --apply-receipt …/APPLY_<STAMP>.json`。如果 apply 之后该文件又被追加过字节,回滚会拒绝(截断会顺带删掉别人的行)。
- **时机提醒**:执行器下一次拉取的续跑点是「磁盘上最新的结算」。
  - 如果回填**早于** 00Z 那次拉取:续跑点是 20:00Z,缺口不会被再拉一遍。
  - 如果**晚于**它:00Z 会从 12:00Z 重拉,对缺口里的结算再报一次 HIGH 跳过,然后写入 21Z–00Z 的行,并写进 `20260927`。这对回填无害,因为回填写的是 `20260926`,计划时的幂等检查按键判断。

## 3. 类修复设计(交 integ,排进下一个执行器包)
**缺陷有两半,各自单独就足以丢行**:
- (a) **定价**:`positions_at` 只要回读老于一个锚间隔就拒绝。停机之后没有新鲜回读,缺口里的每一笔结算都被跳过。
- (b) **续跑点**:`write_funding_rows` 从「磁盘上最新的结算 + 1ms」续拉。被跳过的行既不写盘,也不保存交易所给的金额;一旦后来的结算写进去,续跑点就越过了缺口,这些行**再也不会被重试**。具体到这次:00Z 那次拉取从 12:00Z 续拉,会把缺口再拉一遍,但仍然因为没有新鲜回读而再次跳过;它写入 21Z–00Z 的行之后,续跑点就越过了缺口,再也不会回头。所以本次回填只能靠显式按窗口 fetch。

**修法**:
1. **待定价队列**(补 b):被跳过的 income 行按交易所原样(含 tranId)持久化到 `funding_pending.jsonl`,写法走 durable_io。每次拉取先重试队列,再拉新的。队列里的行只有两个出口:成功定价写入,或者超过 90 天保留期被具名标为永久缺口。**任何一行都不能无声消失。**
2. **跨缺口定价规则**(补 a):结算 t 的最新回读 A 已经陈旧时,只有同时满足以下三条,才用 A 定价;否则留在队列里,每锚具名告警:
   - A 之后已经有下一次回读 B,即 B 在 t 之后;
   - 该名在 (A, t) 之间,折叠 supersede 后的成交为 0;
   - 该名 qty(A) = qty(B) − (A, B) 之间所有成交的净量,容差为半个 stepSize。这一条抓的是我们成交表之外的变化:强平、ADL、人工下单。
   定价仍用 A 的 `venue_position_notional`,与现行规则同口径。行上记下 `position_read_age_s` 与 `pricing_rule="carried_across_gap"`。
3. **验收问句「明天再停机一次,还会不会漏行」写成测试**:
   - 模拟 12h 无回读,缺口里有 4h 和 1h 两种结算。停机后第一锚、有 B 之后,所有缺口行都写入;
   - 在缺口内给某一名注入一笔成交,或改动 B 的数量,那一名必须留在队列里并具名告警,不得写入、不得丢失;
   - 续跑点越过缺口之后,队列依然保留并继续重试;
   - 队列文件写入失败时,本锚的拉取按失败处理并告警,不能当作没有待定价的行。
   - 另外**把本次停机当回归样本**:用 20260926 的真实日文件跑一遍,必须得到 545 行、0 永久缺口。integ 提到的 1788033600 和 1790006400 两处缺锚,也用作正控样本。
