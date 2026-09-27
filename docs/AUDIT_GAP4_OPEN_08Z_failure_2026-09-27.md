> **创建:** 2026-09-27 17:36 UTC | **Session:** acting-lead/live_recovery_audit_0927 | **状态:** final | **作废条件:** 找到具名 OPENUSDT 场所/旧机原始订单成交证据推翻以下顺序；来源文件 SHA 改变；发布门经独立授权重新制定

# GAP4 08Z 历史失败：独立只读诊断

**结论：165/166 的唯一红项是真实历史发送质量缺口，不是 GAP4 计量 bug。保持 FAIL；此次没有发布。** RID `A1790497440` 的 644 行 orders 中，全部未豁免缺口 `667.0389 USDT` 来自 OPENUSDT 一笔 `topup_taker / abandoned_max_attempts / -2022`。16Z 恢复锚通过不能消去这项历史失败。资金费 RED 与 GAP4 分开保留。

## 可复核的本地链

发布候选根：`/Users/haosiyu/cc_tmp/gapfix_release_20260927T1700Z`。以下时间均 UTC，证据只取订单/仓位身份，不读臂结局。

| 时间 | 证据 |
|---|---|
| 00:44:56.094642 | `state/live/pilot_log/20260927/position_readback.jsonl:201`：OPEN 仓位 +4708，名义657.4722。 |
| 08:24:02.165321 | 08Z capture；订单计划目标权重0、拟卖667.03895016。RID minted 08:24:00。 |
| 08:25:00.383942 | broker `submit_failed`：maker client `A1790497440-OPENUSDT-1`，SELL4708、reduce_only=true，-5022。 |
| 08:25:11.917863 | maker-requote client `...-2`，场所返回 orderId910475678，NEW、executedQty0、origQty4708、reduceOnly=true；exchange updateTime08:25:11.875。 |
| 08:43:43.253014 | 同一 maker 撤单为 `cancel_noop / -2011 Unknown order sent`。这条本身不是“已确认撤单”。最终 request ledger 另记 confirmed_qty=0、terminal=true。 |
| 08:44:53.882659 | client `...-3` IOC，SELL4709、reduce_only=true，明确 `submit_failed / -2022 / reduce_only_rejected_verify_position`。 |
| 08:46:44.639903 | `position_readback.jsonl:515`：OPEN qty0/notional0；本机当日 fills 没有08Z OPEN成交。 |
| 08:47:50 | 本机 watchdog 事件封存上述 actions；随后本机平掉剩余全池仓位。 |

精确 broker 证据来自 `/Users/haosiyu/cc_tmp/recovery_check_20260927T0909Z/state/live/watchdog/events.jsonl:17`，actions索引269/326/534/545，SHA256 `dd910a0684456e05d13c3081ca8ed89572cccc3daf707433f2c3255b0d6ed578`。已提取到同主题收据 `multi_asset/exports/research/acting_lead_2026-09-27/receipts/GAP4_OPEN_local_sequence_20260927T1736Z.json`，保留原路径/行号/索引，不复制其它名或臂数据。

订单源 `orders.jsonl:1136–1137` SHA256 `81537081bb0962942ce3e9a7be0684d66df20aa0ef7095be06e3c9cba5d12464`；row1137 SHA256 `6d34877773a77dba265805d967760f26226ccc574a595deed617c4f2fac55fbb`；仓位源 SHA256 `e4f1561bef98de6da90be50e590551d739ae19c336ea1b1202ddc13f5ef71930`。缺口分解另见 root 收据 `GAP4_ROOT_gap_source_20260927T1728Z.json`。

## 为什么是真红；因果边界

候选 `live/order_disposition.py:359–374` 只按既有合同排除重构授权行、maker -5022、topup -4164；-2022不在豁免域。`live/tests_disposition_matrix.py:651–665` 从总 gap 中扣具名政策延迟和场所额度限制；`:692–725` 中08Z不属于 rebuild/resize/venue-locked，因而适用 `<200`。`:825–831` 明定 protective flatten 不移除所在交易锚。不得为了这667U临时把整锚改类。

`live/binance_executor.py:1932–1938` topup继承计划reduce_only，`:1969–1973` 只有 broker.submit 成功返回才增加 `_n_sent`；`:2094–2115` 拒单会记 ledger rejected，`submitted=bool(_n_sent)` 因而产生 submit_ts=null。**这里null不表示没发HTTP请求**，精确broker action已证明交易所拒绝。无本机成交且后读仓位为0，说明本地执行没有兑现原计划；当前“最终已平仓”不等于本机667U已成交。

旧机08:31:12全池市价reduce-only事故见 `docs/PLAN_recovery_after_double_executor_2026-09-27.md:5`，其时间位于本机maker与topup之间，能解释 maker消失/RO拒单/最终零仓。**但尚未独立证明 OPEN 的具体外来订单就是 `F20260927083112*`**：现有repo仅Q1Q4，Q5/Q6在PLAN与handoff仍为forensic TODO；未找到OPEN旧机allOrders/userTrades原始收据。故“旧机导致本名拒单”是强一致推断，不写成已完成逐订单归因。也不能排除其它未归档外来平仓来源。

## 现存风险与最小合法下一步

1. 先保留历史红项、原行和本次165/166输出。发布门现在没有可诚实生成的GREEN；GAP4本身不解决双执行者，不能以恢复通过替代它。原生产d01e35d、四生产者17:19:56恢复属root已记录事实，本次audit没有服务变更。
2. 最小补证只需要 OPEN 的旧机订单/成交（symbol、无损orderId、clientId、side、reduceOnly、orig/executedQty、交易时间）及旧机watchdog事件，绑定本机 `910475678` 的终态与上述0仓回读。优先取现有旧机离线归档；若必须venue只读查询，由root在授权窗口另排。**本审计没有API调用。** 此证据用来归因，不能回填本机filled或豁免历史缺口。
3. 恢复收据是边界明确的独立事实：`ACCEPT_16Z.json` SHA256 `66ececa6acd6dd43e63b975055582074445b450dcfa9db1d0027ac1b349e5365`，观察17:02:55，9/9PASS。K1用symbol-bound身份检查 `[16:14:00,17:00:07.242]`、301个COMMISSION发现symbol、1718 fills，外来0；不覆盖无手续费名、未成交订单、窗间隙，也不证明全局单写者。因旧key未轮换，旧机未来仍有凭据这一风险仍由人工关机与后续有界监测承接，不能称彻底根除。
4. 最小非绕门处理：本次GAP4保持未发布，完成逐订单归因与独立恢复监测。若负责人要建立“已具名历史事故与候选回归分别判定”的发布合同，需另行明确授权、预先固定证据/失败条件并复审，而不是在这轮把 `<200` 提高、删除08Z、flatten豁免或手工盖绿；且不能借此起草F7禁期中的停机/恢复协议v2。本次不实现任何分类/门变更。

## 未验证点

OPEN旧机原始成交/旧maker终态未取得；当前归档无法排除其它外来平仓来源；16Z收据不证明全时段单写者；未重新调用venue、未运行任何执行器测试、未独立重新检查当前生产服务。funding clone及其已留档RED由root串行运行，未在此诊断期间改动。


## 17:41Z 追加：Q5/Q6 场所原文已补齐逐 OPEN 归因

本节更新上文“缺OPEN原始订单/终态”的未验证点；原审计与当时的UNKNOWN保留。root在安静窗用固定已审装置SHA `3c81186d87a41ac61800752aa7f83ade2c011bdfe5f3e42503388fcae05ee692`只GET两次，固定OPENUSDT、08:20–08:47、limit1000；allOrders2行、userTrades5行，未饱和。原文和manifest保存在private `/Users/haosiyu/.codex/tmp/acting_lead_20260927/OPEN_Q5Q6_20260927T173935Z`。本子任务只离线读它们，未调用API。

- 本机 order910475678 / `A1790497440-OPENUSDT-2`：SELL LIMIT RO，orig4708、executed0、CANCELED；exchange time08:25:11.875，update08:31:10.485。
- 外来 order910476907 / `F20260927083112-OPENUSDT-106`：SELL MARKET RO、FILLED，orig=executed4708；time=update08:31:51.518。
- 五笔symbol-bound独立tradeId127677736–127677740，全归910476907，数量576+429+1271+179+2253=4708，时间均08:31:51.518；本机maker没有成交。交易时间严格在本机maker接受与08:44:53.882659 topup -2022之间，恰好解释先前+4708到后读0。

因此“F前缀外来订单实际平掉本名”的订单级归因已闭合；本机maker在F单成交前约41秒被取消。谁发出了cancel、F订单的物理主机是哪台，单靠交易所载荷不能认证；旧机归属另依赖用户确认及事故记录。**这加强真实历史失败的解释，不把本机gap改0、不改steady人口、不使发布绿。**

独立17项纯数据检查（原文SHA/计数、请求边界、symbol、无损ID、唯一成交ID、范围、联结、有限正数、成交数量总和、终态、精确时间顺序）均通过；字段白名单收据 `GAP4_OPEN_Q5Q6_attribution_20260927T1741Z.json` 只保存身份/时间/数量，未保存P&L或臂结果。allOrders SHA `b87bf71acac323838534673948955facf89c35a835707247d55a316b980809ac`，userTrades SHA `4a0591f5323b888a02a7609a4bb0b17455189b20f25c6787b614651f7f2a313e`。当前/未来全局单写者仍未由此证明；没有GAP4部署或门变更。
