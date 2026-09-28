> **创建:** 2026-09-28 21:51 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** in-progress | **作废条件:** 固定事件窗、身份或有限性合同变化另记修订

# 09-27第二次平仓：从已有逐请求确认补充数量核账

接 RESULT_twenty_anchor_actual_cash_bridge_2026-09-28.md。已知该事件本地fills为空、70名残差；探查发现orders有70条topup_taker与70条protective_flatten，前者request_ledger有order_id/trade_qty/trade_quote和userTrades来源，后者另写平仓摘要。本件是见到缺口之后的取证，不是新策略预注册。

固定两回读时点09-27 08:46:44.639903→12:39:01.643611，不用事件±120秒或落盘时间。只收实际first_fill_ts与last_fill_ts全部落在(t0,t1]的订单。每条的非零确认量必须有限、terminal、按orderId有成交回读来源；请求数量与trade_qty、确认notional与trade_quote及行合计相等，unknown_qty或unknown_residual非零/未知则拒绝。

- 先按(symbol,order_id)对请求去重；重复行不重复计算，金额/数量/身份冲突拒绝。protective_flatten摘要只作交叉对照，不再相加；与topup请求client_id一一匹配才比较其数量/金额。
- 该窗本地规范fills必须确为0；非0且没有逐笔order_id联结则具名UNAVAILABLE，不猜两种人口互斥。不能把同一笔在两个接口的结果加两次。
- q0+signed confirmed_qty=q1，沿用0.01 USDT等价阈值。若数量全过才计算该窗USDT现金分量；实际成交时间只知first/last，二者均在同一窗可用于整窗总额，**不用于窗内路径、滑点或逐笔现金认证**。费用保留asset，与已捕获独立income核对。
- 任何行/请求不合格就拒绝整个补充人口。未知不补0；汇总条数不是证明。原16/19基线不覆盖、不回写生产账本。只出独立补充结果，仍缺315名旧机原件、STG结算价和USD计价/收入完整门。

控制：无终态拒、非有限拒、错误方向拒、记录重复只计一次、冲突订单拒、跨界成交拒、未知余量拒、摘要重复不加、改一请求的确认金额拒、规范成交已有重叠拒。静默窗读取已写订单一次封存字节和SHA；不读/输出CFG04/06逐臂结果、不调用API/执行套件/生产写。源码和计划先于实测汇总数字提交。

## 输入结构澄清（全量金额计算之前）

执行器原文 ledger_row_fields 将已证明无unknown的filled_unknown_qty/residual写为None；request qty及confirmed_qty/notional为带符号值，trade_qty/trade_quote为逐trade id的正数映射。因此本件不用None当0，而要求每个请求终态/双final、child id集合相同且和等于signed confirmed、所有行known/filled合计闭合，独立推导无未知；None只允许在这组正证据成立时出现。请求中保留子成交ID后，可检查与原fills的(symbol,id)全量互斥。没有每笔时间，仍仅认证整个first/last封闭区间金额，不生成伪精确成交时间。
