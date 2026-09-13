> **创建:** 2026-09-13 13:1xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 已应用到实盘账本, 待独立研究员复审 | **作废条件:** 09-12 fills.jsonl 被再改写

# REPORT · E1 · 09-12 保护性平仓 fills 与佣金回填

## 问题
09-12 12:47:37Z 看门狗平仓批 `FLATTEN-20260912T124737Z`(255 名)的成交从未写入 `fills` 表, 订单行 `fee_paid` 为 None ⇒ 任何按账本统计 09-12 成本 / 成交的读者都缺这批数据(W6 §4.6 登记, 需凭据)。

## 事实(读码)
- `ops/backfill_fills.py`: `fills` 是场所事实日志, **只追加、按 trade_id 幂等**; `orders` 是「我们当时知道什么」的只追加日志, **不改写**(订单行 fee_paid 保持 None 是设计; 修复它需要带 supersedes 链接的更正行类型, 属模式变更, 不在本项)。
- 场所调用全部为 GET: `arm()`(持仓模式 / symbolConfig / leverageBracket / apiRestrictions / time)、`allOrders`、`userTrades`。
- 平仓批的腿按行自己的 client id 联接(E-0912-A (b) 的费用人口规则)。

## 演练(副本, 先于实盘)
装置 `devices/e1_backfill_rehearsal.py`(提交先于运行), 收据 `receipts/E1_rehearsal.json/.log`:
- pilot_log 副本上看门狗(MockBroker, 临时 state_dir): **回填前 tripped=False / 回填后 tripped=False, 盲区 []**。
- 唯一变化的条件 `cond3_crash_markout`: 仅成交计数 38,284 → 41,940(+3,656), 状态 NO_STRESS, 未触发。
- 二次 apply 写入 **0**(幂等); 实盘 fills 文件 sha 演练前后不变。

## 应用(实盘, 13:10:53–13:14:02Z, 非锚窗)
装置 `devices/e1_backfill_apply_live.py`(提交先于运行), 收据 `receipts/E1_apply_live.json/.log`:
- 先备份 `state/live/pilot_log/20260912/fills.jsonl` → `fills.jsonl.pre_e1_backfill_20260913`(sha 见收据)。
- 平仓批 255 名全部可达、255 腿从场所重建、看到 5,487 笔成交、**写入 3,656 行**(其余 1,831 笔不属于平仓腿, 未写); fills 行数 2,480 → 6,136; 读失败 {}。
- 应用后在**新副本**上复跑看门狗: tripped=False, 盲区 []。

## 未证 / 边界
1. 订单行 `fee_paid` 仍为 None(设计如此); 只读订单行汇总费用的读者仍会低估, W2 三桶读者把它们标为未知。当日另有 2 行订单成交量仍未知(工具如实报告)。
2. 1,831 笔未归属成交是否另有缺行: `find_gaps` 当日只报 1 个缺口批(即平仓批), 其余批次按其判据无缺行; 未逐笔核对。
3. 佣金金额以回填行为准; 与 12Z 深查推断的 ≈117.7U 平仓 taker 费未逐笔对账。
