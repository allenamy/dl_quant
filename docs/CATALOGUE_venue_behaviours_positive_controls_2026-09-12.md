> **创建:** 2026-09-12 13:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 制度文件(E-0912-A 第四条整改: 新分类器/核对上线前逐条正控); 覆盖计数 = 运行树 918559f `live/tests_*.py` 128 套按关键词粗计, 只作缺口指引 | **作废条件:** 每次执行器落地后按新电池重算本表

# 交易所文档化行为 × 我方处置 × 正控是否存在(Binance USDT-M 期货, 在役路径)

**为什么要有这张表**: E-0912-A 的漏格不是「没测过历史」——历史账本里 reduce-only 截量 0 例, 回放抓不到; 是「交易所会这么做」这件事**写在文档里**而我们没有把它列成正控。今后任何触及回执/账本/对账/看门狗的改动, 上线前对本表逐行打勾: 有正控(合成回执按文档形状 + 真行若有)、处置是什么、假阳性时最大代价是什么。

| # | 行为(文档化) | 触发场景 | 现处置(918559f) | 正控? | 假阳性最大代价 | 处置 |
|---|---|---|---|---|---|---|
| V1 | **reduceOnly 单 qty > 持仓 ⇒ 截到持仓, origQty = 持仓, 不报错** | 全退出且数量由 notional/mid 算, mark≠mid | **第 12 轮身份核对判矛盾 ⇒ 未知 ⇒ §4-5b ⇒ 全书平仓**(E-0912-A) | **无**(今日前 0 例; 无合成正控) | 全书平仓 ≈ 5.4 bps + 5 bps ≈ 0.2% NAV/次 | **W6 (a)(b) + 本表新增 T1 真行正控** |
| V2 | -5022 post-only 会吃单 ⇒ 拒单, 不入订单史 | GTX 挂单价越过对手 | benign 无条件; 补单/重挂(phase 1.5) | 有(14 套) | 无 | — |
| V3 | -2027 超 maxNotional | 目标 > 名义上限 | E-0909-E 有限上限截断(b681ca5) | 有(3 套) | 残差告警 | — |
| V4 | -2022 reduceOnly 被拒(无仓/方向) | 我方以为持仓, 场所无仓 | 条件 benign(读回确认平才 benign), 否则计失败 | 有(4 套) | 失败计数 → §4-7 | — |
| V5 | -4189 账户限 reduce-only | 场所风控 | 单独类(保护仍可用), 告警 | 有(1 套) | 停开仓 | 覆盖薄, 加正控 |
| V6 | -4400 量化规则锁 | 大规模重建当天(E-0907-C/E-0910-A) | 拒全部补单; 复场前读 apiTradingStatus | 有(15 套) | 无成交 | — |
| V7 | -1111/-4024/-4164/-4005 我方请求错(精度/价带/最小名义/最大数量) | 取整/价带/小名 | 计失败, 不 benign | 有(12/1/5/7 套) | §4-7 失败率 | -4024 覆盖薄 |
| V8 | 部分成交后撤单: executedQty < origQty, status CANCELED | k 窗到期 | partial_expired + 补单; 请求账本 [L, Q] 带 | 有(11 套) | — | — |
| V9 | userTrades 孪生行(同 tranId/trade 复写) | 回填 | E-0909-H 去重键=行; supersedes_trade_id | 有(3 套) | 记账翻倍 | — |
| V10 | SSL/传输超时 ⇒ 单已到场所但我方无回执 | 网络 | E-0909-D/E 分相重发 + 崩溃收尾 | **0 套按 SSLError 命中**(可能以其他词测) | 孤儿单 | 核实覆盖词, 补正控 |
| V11 | **selfTradePreventionMode=EXPIRE_MAKER**(回执带; 我方 maker 与自家 taker 补单对手 ⇒ maker 被过期) | 同名 maker 挂单 + 补单 taker 同时在场 | **无处置, 无测试**(回执字段未读) | **无** | maker 被静默过期 ⇒ 补单以为 maker 仍在 | 登记; 读回执 STP 字段并写正控 |
| V12 | priceMatch / closePosition / positionSide(BOTH) 字段 | 单向模式 A1 前提 | positionSide 有 3 套; priceMatch/closePosition 无 | 部分 | 对冲模式下 reduceOnly 不可用(A1 前提) | 加 A1 前提断言正控 |
| V13 | origQty 精度: 回执以字符串给 origQty, 我方按 stepSize 取整 | 每单 | 身份核对 1e-6 相对容差 | 有(3 套) | 假矛盾 | 容差不动; V1 例外由 W6 (a) 给 |
| V14 | 撮合后价格保护 / 价带拒单(-4024)与 PERCENT_PRICE 变更 | 极端行情 | 计失败 | 1 套 | — | 覆盖薄 |

**规则(纳入 TEAM_PROTOCOL 候选)**: 触及 `binance_broker` / `binance_executor` 回执读取 / `reconcile` / `watchdog` 分类的任何提交, DESIGN 必须附本表的一份逐行勾选(有正控 / 新增正控 / 不适用并说明), 且每个「全书级」响应必须写出**假阳性最大代价**一栏 —— 代价 ≥ 0.1% NAV 的响应必须过比例门(R-14)。

## §更正(2026-09-12 14:4xZ, 独立研究员 563e3470 `incident/RESULT.md` §4; 全部接受)
本表首版按关键词命中数推断覆盖, 研究员指出四处错误, 逐条更正; **规则**: 每行须分列「官方文档承诺(附出处)/ 我方真实观察(附 wire 记录)/ 我方政策假设」, 不得合并。
- **V1/F3/F8 过度概括**: 本次事实只证明**两次**场所缩小 origQty(两份真实 POST + 子成交 + 前后读回); 官方 New Order 说明未证明「超持仓始终截量」「−2022 只可能无仓/错方向」; 官方失败订单 FAQ 另列 reduce-only 订单间优先级竞争。`differs from ours=0` 只证明此前没记录该诊断, 不证明从未发生「全退出 + mark/mid 差」。⇒ V1 改为: 官方=「reduceOnly 订单受持仓约束(出处待逐字引用)」; 观察=「2 例 origQty=持仓」; 政策=W6 (a) 的 clamped 态限定条件。
- **V8 错**: 在役合并器对 CANCELED 且最终 C 已证(C4/Q10)给 terminal=True、executed_qty_final=True ⇒ 数量精确 [4,4]; 只有终态但最终 C 未知才保留 [L,Q] 带。本表原文把已修数轮的 F 语义改回去了, 撤回。
- **V11 「STP 无处置」不成立**: 运行树 `ORDER_TERMINAL` 已含 `EXPIRED_IN_MATCH`, 合并器对该 status/C4 返回最终量 4 且无矛盾; 字段 `selfTradePreventionMode` 未被直接引用 ≠ status 无人处理。仍开: 完整 STP 竞争链(自家 maker vs 自家 taker 补单)未验证 ⇒ 改为「读者存在, 竞争链正控缺」。
- **V9 混了三类身份**: 官方 userTrades 以 `id/orderId/symbol` 归属; income 分页孪生行是 tranId 问题(E-0909-H); 本地 `supersedes_trade_id` 是存储修订关系。三者分别测, 不得合成「userTrades 孪生 tranId」。
- 覆盖计数列(「N 套」)只作缺口指引, 不是行为覆盖证据; 正式版本须以「是否存在按文档形状的合成正控 + 真行正控」两列替代。
