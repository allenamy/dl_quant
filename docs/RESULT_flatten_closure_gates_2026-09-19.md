> **创建:** 2026-09-19 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb | **状态:** 交独立研究员复审(第四轮 R4-C1 / R4-C2 / 输入有限性的装置修复; 研究验收器, 不涉实盘, 不是部署批准) | **作废条件:** v4 装置(sha `813501e1…`)在本文反例或新反例上判出 CLOSED; 或十窗复跑任一数与冻结 v3 收据不同而无解释; 或取数人口被证明不完整

# 平仓窗逐笔闭合 v4 —— 判词拆门: 归属、逐笔端点、取数人口、输入有限性

## 0. 一句话

十次平仓的**钱**没有变(十窗 A/C 各数与 v3 收据逐字段相同)。变的是**判词的资格**:
- v3 的 CLOSED 只核现金、数量和两端点的【窗口总额】。所以删光平仓单、全不匹配、全复制、tradeId 全换成不存在的值、两条已实现盈亏各 ±100 互相抵消、NaN 数量,这些输入全都照样判 CLOSED rc 0。
- v4 把归属、逐笔端点、取数人口、输入有限性各拆成一道门,缺一道就不给 CLOSED。
- 十个真实窗口的判词因此从 `CLOSED` 降为 **`CLOSED_POPULATION_UNPROVEN`(rc 5)**。原因是十份旧原始件都没存「当初查询了哪些品种」,只存了个数。离线无法证明取数人口完整,v4 不再把它写成已证。

## 1. 复审发现了什么(第四轮 §2 / §3,冻结 d661b587e)

| 编号 | 缺陷 | 复审在真实 09-06 输入上的反例 | v3 结果 |
|---|---|---|---|
| R4-C1 / P1 | `closed` 不要求订单归属成功;`matched[venue]=o` 让后来者覆盖前者,「每行恰好一个候选」≠ 双射 | 删光 protective_flatten 行 / 268 单金额各 +1e6 / 268 单全复制 | 全部 CLOSED rc 0 |
| R4-C2 / P2 | 两端点只比窗口总额,不比逐笔 | income 的 4,879 个 tradeId 全换成不存在值 / 两条 REALIZED_PNL 各 +100、−100 | CLOSED,C_closure 逐字不变 |
| R4-C2 / P2 | 旧原始件没有 `symbols_queried`,复用检查只比个数 | 零仓 QUSDT 换成从未查询的名,仍是 269 名 | CLOSED |
| 有限性 | NaN 进比较恒为假 ⇒ 静默通过 | (复审在 `cash_identity_usd.py` 上报的同类;本装置实测见 §3 M11: userTrades qty = NaN) | CLOSED rc 0 |
| 事实更正 | 报告写 1,508 张订单 | 105+83+108+102+108+102+334+268+243+255 | **1,708**(本文 §4 从 v4 收据重算,同为 1,708) |

复审明确说这是**验收器缺陷,不是说真实十次事件已经错配**。v4 复跑结果支持这一点(§4)。

## 2. 改了什么(`docs/fixprogram_2026-09-13/FP3_devices/flatten_window_closure.py` v4,sha `813501e1617216b0ee2d5735e2b638bb1060eca4b63201bf052b3b802b78024b`)

v3 原件先归档:`FP3_devices/archive/flatten_window_closure_v3_02418fdd.py`,sha `02418fddb5a466bcf2c9e5fcb04b6ec3ff1f839b5628d2a5bbd86df9d06442a9`(= HEAD 提交版)。

| 门 | 判什么 | 失败时 |
|---|---|---|
| **INPUT_FINITE** | 第一道:输入层按字段清单扫。过滤键(nav_ts / read_ts / fill_ts / settlement_ts / submit_ts / first_fill_ts)查【全部载入行】,值字段查【被用到的行】。userTrades(time, qty, quoteQty, commission, realizedPnl, price)与 income(income, time)全查。BNB 余额路径行、BNB 日收盘、四个指数价也查。第二道:装置里【所有】数值解析都改走 `fnum()`,读到非有限值抛具名异常。清单漏列的字段(例如明天新加的字段)照样被拒,不靠比较表达式 | `REFUSED_INPUT_FINITE`(rc 2),收据逐条列 (来源, 键, 字段, 值) |
| **POPULATION** | 应查品种集合 = 当初实际查询集合(**集合相等**)。原始件带清单 ⇒ `POPULATION_SET_EQUAL`。旧原始件无清单 ⇒ 个数不等照旧拒;个数相等只给 `POPULATION_UNPROVEN_COUNT_ONLY`,不改写历史去冒充已证。userTrades 出现未查询品种 ⇒ 拒 | `REFUSED_POPULATION`(rc 2) |
| **ATTRIBUTION**(硬门) | 本窗执行器 protective_flatten 订单集非空,且全部属于 `--event`;该事件在载入日内的平仓单全部落在窗内;场所订单键 = `(symbol, orderId)`;每张执行器单恰好一个候选;每个场所订单至多被消费一次;未匹配 = 歧义 = 执行器重复行 = 买卖混向 = 0;左右计数相等 | 门 FAIL ⇒ `OPEN`(rc 4),`fail_reasons` 逐条具名 |
| **ENDPOINT** | userTrades 与 income 逐 `(symbol, tradeId)` 相等:COMMISSION 连同资产比,REALIZED_PNL 也比,Decimal 差 ≤ 1e-8;两侧都不许有非零孤儿;无重复身份((symbol,id) / (incomeType,tranId) / 每键每类至多一行);无跨品种 orderId 碰撞;两端点的行都落在声明的窗口毫秒内 | 同上 |
| **CASH** | v3 的闭合条件原样保留(含 v3 的窗口总额交叉) | 同上 |

判词与退出码: `CLOSED`(rc 0)只在五门全过**且** `POPULATION_SET_EQUAL` 时给出。`CLOSED_POPULATION_UNPROVEN`(rc 5)表示其余全过,但人口只能按个数核。另有 `OPEN`(rc 4)、`REFUSED_<门>`(rc 2)、`UNAVAILABLE`(rc 3)。`VERDICT_v2_usdt_caliber` 同样受门约束。

其余不变:A/C/D 的计算与 v3 逐行同义。另有三处工程改动:
- `--event` 改为必填;
- 新增 `--ledger-root`(缺省为实盘账本,只读;电池用它读隔离副本);
- `--reuse-raw` 时指数价只读缓存(`offline=True`)且不回写。v3 在这条路径上缓存缺分钟时会联网补取并改写缓存文件。

收据新增 `gates` / `failed_gates` / `attribution` / `endpoint_per_trade` / `population`(含 `required_symbols` 与其 sha),以及 `deps_sha256`(fills_reader、usd_valuation、BNB 日收盘、BNB 行、指数缓存各自的 sha256)和 `ledger_root`。

## 3. 行为电池(`FP3_devices/tests_flatten_window_closure.py`,sha `7b3b114abb76c0e637e8359aa98cc99fb8254180f6d99065638fe755669c433b`)

**做法**:
- 输入是真实 09-06 窗口。另加 09-09 窗口,只为「账本成交价 = inf」那一条,因为 09-06 窗内账本成交为 0 笔。
- 账本日文件和原始件先复制进临时目录,变异只发生在副本上。
- 真实装置在子进程里按文件路径载入并调用 `main()`,运行在审计钩子下:禁网络、禁子进程、禁向临时目录以外写。
- 判「被拒」要四条同时成立:退出码 ∉ {0,5};判词不以 CLOSED 开头;预期那道门被点名 FAIL;失败原因里含预期机制词。因现金恰好算坏而停下,不算这道门通过。
- 先断言未变异基线为绿(判词接受,且各数与冻结 v3 收据逐字段相同)。基线红时,依赖它的变异检查判 FAIL,不给真空绿。
- 结束时核对 37 个真实输入文件的 sha256 在开跑前后逐一相同。

检查项:
- B1 / B2:09-06 / 09-09 基线。
- G1:旧原始件必须标 UNPROVEN。
- G2:带清单原始件给裸 CLOSED。
- M1–M4:归属。删光平仓单;+1e6;全复制;一张场所订单被两张非逐字重复的执行器单认领。
- M5–M7:逐笔端点。tradeId 全不存在;±100 抵消;userTrades 重复身份。
- M8–M10:人口。清单同个数换名;账本侧换名(复审原反例)配带清单件;同一换名配旧件时必须标 UNPROVEN。
- M11–M13:有限性。qty = NaN;09-09 账本 fill_px = inf;把输入层扫描整个关掉再注 NaN,计算路径守卫仍须具名拒绝。
- S1:真实输入未被改动。

**v4 判词行(逐字,收据 `FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_battery_2026-09-19.txt`):**

```
BATTERY VERDICT: ALL PASS — 18/18 checks passed | device=flatten_window_closure.py sha256=813501e1617216b0
exit=0
```

**会变红的自证:同一电池指向归档 v3(收据 `FLATTEN_CLOSURE_v4_battery_vs_v3_2026-09-19.txt`):**

```
BATTERY VERDICT: FAIL — 3/18 checks passed, 15 failed ['G1', 'G2', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11', 'M12', 'M13'] | device=flatten_window_closure_v3_02418fdd.py sha256=02418fddb5a466bc
exit=1
```

v3 的两条基线 B1 / B2 为绿,S1 为绿,所以下面这些红不是基线导致的真空红。15 条红分三类:
- **行为性假通过,9 条**:M1、M2、M3、M4、M5、M6、M10、M11、M13。变异输入上 v3 **rc 0 判 CLOSED**,与复审反例一致。M11 说明复审在 cash 装置上报的 NaN 问题,本装置的 v3 也有。
- **被拒但未点名,2 条**:M7、M12。v3 给 OPEN rc 4,但只是现金或数量恰好算坏,没有哪道门点名。M12 的 inf 价格把 cash 算成 NaN,v3 因 NaN 判 OPEN。在本装置上这不是假通过,但属于「理由不对的停」。
- **夹具 / 标签类,4 条**:G1、G2、M8、M9。v3 不导出应查集合,也没有人口档,带清单夹具建不起来,M8 / M9 因而判真空 FAIL。

v3 在旧装置适配下运行:子进程只改读根、BNB_P 与缓存位置,不改它的计算。输出行已标「旧装置适配」。

## 4. 真实十窗复跑(v4,离线复用原始件,rc 全部 = 5)

每窗 A_local_identity、inputs_sha16、raw_trades_sha256,以及 v3 收据 C_closure 的**每个字段**(判词两行除外),都与冻结 v3 收据逐字段相同。只有判词字符串变了。

| 事件 | v4 判词 | 执行器平仓单 | 被消费场所订单 | 未匹配/歧义/重复消费/重复行 | 逐笔端点(trade 键数;不符+孤儿) | 人口档(应查名数) | 残差 v3(USDT) / 容差 | v2 口径判词 v3→v4 |
|---|---|---:|---:|---|---|---|---|---|
| FLATTEN-20260801T201827Z | CLOSED_POPULATION_UNPROVEN | 105 | 105 | 0/0/0/0 | PASS(172;0) | UNPROVEN_COUNT_ONLY(111) | −0.0214 / 2.0 | CLOSED → CLOSED_POPULATION_UNPROVEN |
| FLATTEN-20260802T041821Z | CLOSED_POPULATION_UNPROVEN | 83 | 83 | 0/0/0/0 | PASS(129;0) | UNPROVEN_COUNT_ONLY(109) | −0.0146 / 2.0 | CLOSED → CLOSED_POPULATION_UNPROVEN |
| FLATTEN-20260805T001853Z | CLOSED_POPULATION_UNPROVEN | 108 | 108 | 0/0/0/0 | PASS(198;0) | UNPROVEN_COUNT_ONLY(109) | −0.0286 / 2.0 | CLOSED → CLOSED_POPULATION_UNPROVEN |
| FLATTEN-20260805T121829Z | CLOSED_POPULATION_UNPROVEN | 102 | 102 | 0/0/0/0 | PASS(337;0) | UNPROVEN_COUNT_ONLY(108) | +0.1505 / 2.0 | OPEN → OPEN |
| FLATTEN-20260821T121630Z | CLOSED_POPULATION_UNPROVEN | 108 | 108 | 0/0/0/0 | PASS(769;0) | UNPROVEN_COUNT_ONLY(113) | −0.5677 / 2.0 | CLOSED → CLOSED_POPULATION_UNPROVEN |
| FLATTEN-20260821T201600Z | CLOSED_POPULATION_UNPROVEN | 102 | 102 | 0/0/0/0 | PASS(525;0) | UNPROVEN_COUNT_ONLY(105) | +0.1427 / 2.0 | OPEN → OPEN |
| FLATTEN-20260826T124702Z | CLOSED_POPULATION_UNPROVEN | 334 | 334 | 0/0/0/0 | PASS(940;0) | UNPROVEN_COUNT_ONLY(337) | −0.2858 / 2.0 | OPEN → OPEN |
| FLATTEN-20260906T084608Z | CLOSED_POPULATION_UNPROVEN | 268 | 268 | 0/0/0/0 | PASS(2442;0) | UNPROVEN_COUNT_ONLY(269) | +2.2945 / 4.1186 | CLOSED → CLOSED_POPULATION_UNPROVEN |
| FLATTEN-20260909T164536Z | CLOSED_POPULATION_UNPROVEN | 243 | 243 | 0/0/0/0 | PASS(3095;0) | UNPROVEN_COUNT_ONLY(245) | −1.5362 / 5.814 | OPEN → OPEN |
| FLATTEN-20260912T124737Z | CLOSED_POPULATION_UNPROVEN | 255 | 255 | 0/0/0/0 | PASS(3656;0) | UNPROVEN_COUNT_ONLY(259) | +0.6584 / 5.8988 | OPEN → OPEN |
| **合计** | | **1,708** | **1,708** | 0 | 12,263 个成交键 | | | |

合计由十份 v4 收据的 `attribution.n_executor_flatten_orders_in_window` 相加得到:**1,708**(不是 1,508)。与十份 v3 收据的 `n_executor_flatten_orders` 之和相同。

另记:
- 10 窗全部 INPUT_FINITE / ATTRIBUTION / ENDPOINT / CASH = PASS。
- 每窗该事件的平仓单全部在窗内(`n_event_flatten_orders_in_loaded_days` = 窗内数)。
- 无跨品种 orderId 碰撞,无窗外行,无重复身份。
- 逐笔端点结论与复审独立 Decimal 核对一致:无 >1e-8 的费或盈亏差,无非零孤儿。
- 指数缓存 `INDEX_KLINES_1m_cache.json` 在复跑前后 sha 均为 `6a0fff31…`(未联网、未改写)。

## 5. 仍未证 / 边界(不静默)

1. **旧原始件的取数人口未证。** 十份原始件都只有 `n_symbols_queried`,没有 `symbols_queried` 清单,也没有逐页凭据。所以「零费用、零已实现盈亏的往返成交都已取全」离线无法独立证明。`COMPLETE` 标签是拉取时的自述。v4 如实标 `CLOSED_POPULATION_UNPROVEN`,不改写历史。要升到 `POPULATION_SET_EQUAL`,只能重拉:v4 新拉取会写 `symbols_queried`。但重拉要调交易所 API,本轮禁止,未做。
2. **新拉取路径未测。** `--reuse-raw` 以外的实时拉取分支本轮没有运行(禁止 API 调用)。v4 只改了该分支的人口档赋值;逐页凭据(pages)仍未落盘,复审 §3「冻结分页完整性」这一项尚未做到。
3. **「平仓集合」由执行器侧定义。** 场所订单没有我们的 clientOrderId。所以 ATTRIBUTION 证明的是「执行器记下的每张平仓单 ↔ 恰好一个场所订单,且无一被重复消费」,不能发现一张**执行器没记**的场所平仓单。这类单若不在账本,会进 `other_missing`;十窗中只有 08-21 12Z 有 20 笔 / 15 个场所订单。它们是 5 个名在 12:20–12:23Z 的往返(平仓在 12:16–12:17Z),v3 起已计入现金闭合,v4 不把它们当归属失败,也不对它们作解释。
4. **依赖在变。** 复跑时 `usd_valuation.py` 是另一代理正在编辑的工作副本(收据 `deps_sha256` 记为 `9287beeb…`,非 HEAD 提交版)。其 docstring 声明 `index_at / p_usdt / b_bnb / save / CACHE / BnbPath` 与 v1(`e892221f`)同义;十窗 D 段各数与用 v1 产生的 v3 收据逐字段相同。日后复跑若换了该模块,先比 `deps_sha256`。
5. `INCOME_ALL_20260731_now.json`(25 MB)未入库;已入库的 `.json.gz` 解压后 sha256 = `1ca73cd2…`,与复跑所用文件相同。
6. 执行器单**没有成交时刻**时计为未匹配,ATTRIBUTION 判 FAIL。这是保守一侧的假红,不是假绿;十窗中为 0。

## 6. 与复审的一致与补充

- 复审四条反例全部被 v4 拒(M1 / M2 / M3 / M5 / M6 / M9;同个数换名配旧件则按复审「保留限定」标 UNPROVEN,即 M10)。
- 复审说「真实十窗应保持原数」:实测保持,逐字段相同。
- 比复审多做的:有限性另加计算路径守卫(M13 证明:扫描清单漏列时仍具名拒绝);`(symbol, orderId)` 作场所订单键;事件包含性(该事件平仓单全部在窗内);重复身份与窗外行也进 ENDPOINT;离线复用不再联网补缺指数价。
- 一处说明:复审第四轮 §4 的有限性反例是在 `cash_identity_usd.py` 上做的,不属本装置,本件不改它(另有负责人)。本装置 v3 上同类问题的实测是 M11(NaN qty ⇒ CLOSED rc 0)。inf 价格在本装置 v3 上不是假通过,而是 NaN 现金导致 OPEN(M12)。

## 7. 复跑命令(逐字;在 `docs/fixprogram_2026-09-13/FP3_devices/` 下执行)

归档核对:

```
shasum -a 256 archive/flatten_window_closure_v3_02418fdd.py flatten_window_closure.py tests_flatten_window_closure.py
```

电池(v4 与 v3 自证):

```
/usr/bin/python3 -B tests_flatten_window_closure.py > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_battery_2026-09-19.txt 2>&1; echo "exit=$?" | tee -a ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_battery_2026-09-19.txt
/usr/bin/python3 -B tests_flatten_window_closure.py --device archive/flatten_window_closure_v3_02418fdd.py > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_battery_vs_v3_2026-09-19.txt 2>&1; echo "exit=$?" | tee -a ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_battery_vs_v3_2026-09-19.txt
```

(本次运行另带 `--tmp-root <scratchpad>`,只改临时目录位置;解释器 `/usr/bin/python3` → 3.9.6。)

十窗:

```
/usr/bin/python3 -B flatten_window_closure.py 1785615495.327172 1785629783.8997319 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260801T201827Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260801T201827Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260801T201827Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260801T201827Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1785644299.48212 1785649625.6190689 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260802T041821Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260802T041821Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260802T041821Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260802T041821Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1785889104.446205 1785903346.010344 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260805T001853Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260805T001853Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260805T001853Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260805T001853Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1785932306.207547 1785946762.351441 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260805T121829Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260805T121829Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260805T121829Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260805T121829Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1787314570.9543638 1787329180.200428 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260821T121630Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260821T121630Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260821T121630Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260821T121630Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1787343345.308213 1787357763.6213398 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260821T201600Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260821T201600Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260821T201600Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260821T201600Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1787748333.642869 1787762283.433176 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260826T124702Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260826T124702Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260826T124702Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260826T124702Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1788684263.67789 1788698342.895093 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260906T084608Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260906T084608Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260906T084608Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260906T084608Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1788972245.856354 1788986342.424868 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260909T164536Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260909T164536Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260909T164536Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260909T164536Z.log 2>&1; echo rc=$?
/usr/bin/python3 -B flatten_window_closure.py 1789217147.803424 1789231143.365168 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260912T124737Z.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_FLATTEN-20260912T124737Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260912T124737Z > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_FLATTEN-20260912T124737Z.log 2>&1; echo rc=$?
```

十窗 t0/t1 与 v3 收据 `argv[:2]` 相同。每条预期 `rc=5`。

## 8. 相关

- 上一版结论:`docs/RESULT_cash_closure_per_trade_2026-09-19.md`(v3;本文不改它,判词降档与 1,708 更正由负责人整合)。
- 复审:`.claude/worktrees/codex-independent-20260907/docs/REVIEW_cash_closure_and_blend_round4_codex_2026-09-19.md` §2 / §3;反例:同树 `…/round4_cash_blend_20260919/agents/flatten/`。
- 收据:`docs/fixprogram_2026-09-13/FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4_*.json|.log`、`FLATTEN_CLOSURE_v4_battery_2026-09-19.txt`、`FLATTEN_CLOSURE_v4_battery_vs_v3_2026-09-19.txt`。

## 9. 增补(2026-09-19 06:3xZ,同日第二轮):v4.1 新拉取落逐页凭据 / 十窗真实重拉 / 08-21 12Z 非平仓成交查明

> 本节只追加,§0–§8 原字节不改。§0「十窗判词降为 CLOSED_POPULATION_UNPROVEN」对**旧原始件**仍然成立。十个窗口用本节的**新拉取原始件**判为裸 `CLOSED`(rc 0)。
> 联网许可来自协调者本轮的明确授权:只经 `fetch_trades.fetch_trades` 与 `fetch_income_paged.run`(签名 GET,硬编码只读密钥文件)。实盘系统零写入。

### 9.1 改了什么(装置 v4.1,sha `fefa19af3ef7d2b51f60edcfc6a947d445854b59e09cd0279784f954f5b27afb`)

上一版 v4.0 已归档为 `FP3_devices/archive/flatten_window_closure_v4_813501e1.py`,§2–§4 的收据出自它,不重跑、不改写。

- **新拉取把证据落盘。** 原始件新增以下字段:
  - `symbols_queried`:实际查询过的品种清单。
  - `trades_pages_by_symbol`:每个品种 `fetch_trades` 返回的逐页凭据(mode / startTime / endTime / fromId / status / n / weight),外加 completeness / incomplete_reason / n_rows。
  - `income_pages` 与 `income_n_boundary_rows_subtracted`。
  - 两个取数器的 sha256、拉取起止时刻、页上限。

  另外两条规则:目标文件已存在 ⇒ 拒绝(拉取收据只追加,永不覆盖旧件);拉取不完整时也落盘,但标 `INCOMPLETE`,永远不能被复用。
- **复用与新拉取走同一条人口校验**:先比个数,再比集合,最后查逐页凭据(`page_receipt_problems`)。人口分三档:
  - `POPULATION_PASS`:清单 = 应查集合,且逐页凭据自洽。自洽指:全部页 200;首页 = 本窗口(毫秒级相同);非末页全满;单页必为短页;逐品种行数 = 凭据 n_rows;income 的 Σn − 边界扣除 = 行数。
  - `POPULATION_UNPROVEN_NO_PAGE_RECEIPTS`:有清单、无页凭据。
  - `POPULATION_UNPROVEN_COUNT_ONLY`:旧件,只有个数。

  出现非 200 页、声明 INCOMPLETE 的品种、查询品种缺凭据、计数不合,都判 `REFUSED_POPULATION`。
- **裸 `CLOSED`(rc 0)现在只在 `POPULATION_PASS` 时给出。** 与 v4.0 的行为差:v4.0 对「有清单、无页凭据」的原始件给 `CLOSED` rc 0,v4.1 给 `CLOSED_POPULATION_UNPROVEN` rc 5。
- **指数价永远只读缓存**(新拉取也一样)。装置里除两个只读取数器外不再有任何联网。
- 新增对照装置 `FP3_devices/compare_flatten_raw_old_vs_fresh.py`:只读,不联网。

### 9.2 电池(`tests_flatten_window_closure.py`,sha `96be35d6768fac9b0e8c629b36d877c59fb69224a627fda678d59cb6655fbfd5`,24 项)

新增和改动的检查:
- G2:只有清单 ⇒ `CLOSED_POPULATION_UNPROVEN` rc 5。
- B3:新格式夹具的基线,判词接受且各数与 v3 相同。这是 M8 / M9 / M14–M17 的前置条件,与装置版本无关。
- G3:新格式夹具到达 `POPULATION_PASS`,判裸 `CLOSED` rc 0。夹具由旧原始件改形,不联网,`raw_format` 如实写 FIXTURE;装置不信标签,只核凭据本身。
- M8 / M9 改在 G3 夹具上做。
- M14:某品种一页 status = 429,但声明仍写 COMPLETE。
- M15:某品种声明 INCOMPLETE。
- M16:某查询品种缺页凭据。
- M17:income 一页 status = 503。

M14–M17 都必须以 `REFUSED_POPULATION` 被拒,并点名具体原因。电池子进程对归档副本重定位 `BNB_P` 路径(归档件按自身目录找文件会落空),只改路径,不改计算,输出行标「BNB_P 路径重定位」;对在位的 v4.1 不触发。

判词行(逐字,收据 `FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery*_2026-09-19.txt`):

```
BATTERY VERDICT: ALL PASS — 24/24 checks passed | device=flatten_window_closure.py sha256=fefa19af3ef7d2b5
exit=0
BATTERY VERDICT: FAIL — 18/24 checks passed, 6 failed ['G2', 'G3', 'M14', 'M15', 'M16', 'M17'] | device=flatten_window_closure_v4_813501e1.py sha256=813501e1617216b0
exit=1
BATTERY VERDICT: FAIL — 3/24 checks passed, 21 failed ['G1', 'G2', 'B3', 'G3', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M14', 'M15', 'M16', 'M17', 'M10', 'M11', 'M12', 'M13'] | device=flatten_window_closure_v3_02418fdd.py sha256=02418fddb5a466bc
exit=1
```

对上一版 v4.0,恰好 6 条新检查变红。它的 B3 基线为绿,所以 M14–M17 的红是行为性的:页凭据显示 429、INCOMPLETE、缺凭据或 income 503 时,v4.0 仍判 `CLOSED` rc 0。这证明新增检查能变红。

### 9.3 联网前控制(`ro_controls.py`,输出逐字存 `FLATTEN_CLOSURE_v4fresh_ro_controls_2026-09-19.txt`)

```
[POSITIVE] GET /fapi/v3/account
  rc 200 OK | totalWalletBalance present: True | n positions: 245 | canTrade flag: None | canDeposit: None | canWithdraw: None
[NEGATIVE] POST /fapi/v1/order/test  (validates only, never sends)
  rc 401 | venue code -2015 | Invalid API-key, IP, or permissions for action
  OK: refused with -2015 (invalid API-key, IP, or permissions) — consistent with a read-only key
```

两点说明:
- 负对照本身就是一次只校验不下单的签名 POST(`/fapi/v1/order/test`)。它是协调者指定的前置控制,本轮除它之外没有任何 POST / PUT / DELETE。
- 复审第四轮 §9 已指出,−2015 同时涵盖密钥、IP、权限三种解释,只能说明「与只读密钥一致」,不能认证全部权限。

### 9.4 十窗新拉取判词(v4.1;拉取 2026-09-19 06:12:50Z–06:30:05Z,逐窗顺序执行)

| 事件 | 判词 / rc | 人口档(实际查询品种数) | 平仓单 ↔ 被消费场所订单 | 逐笔端点 | 残差 v3(USDT) / 容差 | 与 v3 收据 |
|---|---|---|---|---|---|---|
| FLATTEN-20260801T201827Z | CLOSED / 0 | POPULATION_PASS(111) | 105 ↔ 105 | PASS | −0.0214 / 2.0 | A、C 逐字段相同 |
| FLATTEN-20260802T041821Z | CLOSED / 0 | POPULATION_PASS(109) | 83 ↔ 83 | PASS | −0.0146 / 2.0 | 相同 |
| FLATTEN-20260805T001853Z | CLOSED / 0 | POPULATION_PASS(109) | 108 ↔ 108 | PASS | −0.0286 / 2.0 | 相同 |
| FLATTEN-20260805T121829Z | CLOSED / 0 | POPULATION_PASS(108) | 102 ↔ 102 | PASS | +0.1505 / 2.0 | 相同 |
| FLATTEN-20260821T121630Z | CLOSED / 0 | POPULATION_PASS(113) | 108 ↔ 108 | PASS | −0.5677 / 2.0 | 相同 |
| FLATTEN-20260821T201600Z | CLOSED / 0 | POPULATION_PASS(105) | 102 ↔ 102 | PASS | +0.1427 / 2.0 | 相同 |
| FLATTEN-20260826T124702Z | CLOSED / 0 | POPULATION_PASS(337) | 334 ↔ 334 | PASS | −0.2858 / 2.0 | 相同 |
| FLATTEN-20260906T084608Z | CLOSED / 0 | POPULATION_PASS(269) | 268 ↔ 268 | PASS | +2.2945 / 4.1186 | 相同 |
| FLATTEN-20260909T164536Z | CLOSED / 0 | POPULATION_PASS(245) | 243 ↔ 243 | PASS | −1.5362 / 5.814 | 相同 |
| FLATTEN-20260912T124737Z | CLOSED / 0 | POPULATION_PASS(259) | 255 ↔ 255 | PASS | +0.6584 / 5.8988 | 相同 |
| **合计** | 10/10 CLOSED | | **1,708 ↔ 1,708** | | | |

另记:
- 十份新收据的 `raw_trades_sha256` 与盘上原始件逐一相同。
- 离线复用新原始件(`--reuse-raw`,不联网)复跑 09-06,C_closure 与新收据逐字段相同,rc 0。
- 指数缓存 sha 在全程前后都是 `6a0fff31…`。
- `VERDICT_v2_usdt_caliber`(USDT 口径,仅作对照)与 v3 相同:五窗 CLOSED,五窗 OPEN。

### 9.5 旧原始件 vs 新拉取原始件(收据 `FLATTEN_CLOSURE_v4fresh_vs_old_raw_diff_2026-09-19.json`)

| | 旧件 | 新件 | 只在旧 | 只在新 | 同键字段 / 金额不同 |
|---|---:|---:|---:|---:|---:|
| userTrades,键 (symbol, id) | 12,263 | 12,263 | 0 | 0 | 0 |
| income 行,全字段多重集 | 24,032 | 24,032 | 0 | 0 | 0(按 (incomeType, tranId, asset) 键比金额) |

十窗逐窗全是 0 / 0 / 0。旧件声明的查询个数与新件实际查询清单的长度逐窗相同(111 / 109 / 109 / 108 / 113 / 105 / 337 / 269 / 245 / 259)。

含义:一次**独立的重拉**(存了查询清单和逐页凭据,并通过 `POPULATION_PASS`)在同一窗口、同一应查集合上,返回了与旧件**完全相同**的行集和金额。所以 §5-1 所说「旧件取数人口未证」,对这十个窗口现在由新拉取原始件兑现。旧件本身不改写,仍标 COUNT_ONLY;需要引用「已证」时,引用 `FLATTEN_CLOSURE_v4fresh_*`。

### 9.6 08-21 12Z 的 20 笔(15 个场所订单,5 个名,12:20–12:23Z):类别 (c),另一个交易进程在同一账户

证据(全部只读):
1. 执行器 `~/dl_quant_live/state/live/pilot_log/20260821/orders.jsonl` 与 `fills.jsonl` 里,DEXE / JASMY / PARTI / RARE / TAG 五个名当天为 **0 行**。12Z 锚(rebalance_id `A1787313646`)的价格向量里也没有这五个名;它们第一次出现在执行器锚日志 `state/anchor_runs.log`,是 08-22 08:25Z 宽宇宙切换之后。所以不是 (a)(该锚的常规订单)。
2. 15 个 orderId **全部**出现在 `~/exec_probe/events.jsonl`。那是薄币执行探针 v1 的事件日志(源码快照 `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/exec_probe_with_halt_guard.py`:「独立进程,不 import 在役代码;每 4h 锚 +20min 一轮;5 币各挂 post-only 买卖对 $15–25/单,180 s 窗;未成交撤单,残留仓 reduce-only 市价平」)。事件依次为:
   - 12:20:02–06Z,`place` 两臂:`base` 约 15 USDT,`xl` 约 75 USDT;
   - 12:23:06–11Z,`status` / `cancel`;
   - 12:23:15Z,`flatten`,即 5 张市价平仓单(orderId 8820960107 / 2303297004 / 755943040 / 4034295524 / 1933406910)。
3. `docs/INCIDENT_daily_loss_trip_2026-08-21.md` L29 自述:「停机窗内仅 12:20Z 一轮(守卫前)实际下单」。执行器 12:16Z 平仓并进入 reduce-only 之后,探针照常在锚 +20 min 下了这一轮。同日 20:16Z 的第二次整书平仓,根因正是这个探针(同文 L40–L44;错题 E-0821-C「账户里只有书引擎」)。探针 v1 于 08-21 20:19Z KILL;`~/exec_probe/KILL` 至今仍在。

结论:
- 这 20 笔**不是执行器账本的缺口**(b)。执行器从未下过这些单,它的账本按设计只记自己的单。
- 它们是**同一账户里另一个交易进程**(执行探针)的成交,属于 (c)。
- 现金足迹:成交额 899.2034 USDT,已实现 −0.7894 USDT,手续费 0.00041984 BNB,maker 占比 0.5。已在 v3 / v4 / v4.1 的现金闭合里,以 `other_missing`(20 笔 / 15 单)计入,窗口闭合。
- 对 ATTRIBUTION 门,这恰好是 §5-3 声明的边界:「平仓集合」由执行器侧定义。账户里另一个进程的单不会被当成平仓单,也不会让归属门失败,只在 `other_missing` 里具名出现。

### 9.7 仍未证 / 边界(追加)

1. **逐页凭据证明的是请求层。** 它证明每个请求都返回 200,且分页按取数器规则终止;不证明交易所返回了全部成交(交易所自答仍被信任)。
2. **应查集合的边界。** 应查集合 = 两端快照名 ∪ 账本成交名 ∪ income 里 COMMISSION / REALIZED_PNL 的名。有一类成交无法从这里发现:发生在这个集合之外,零手续费、零已实现盈亏,且两端都无持仓。
3. **取数器的 weight 字段全为 None。** 取数器用大写键 `X-MBX-USED-WEIGHT-1M` 读响应头,取不到值;大小写不匹配是推测,原因未查实。本轮的速率只能从耗时估:约 2.6 次/秒,userTrades 权重 5 ⇒ 约 780/分钟,低于 IP 上限 2,400/分钟。拉取时段 06:12:50–06:30:05Z,避开执行器锚窗(下一次读取在 08:24Z)。改取数器不在本件范围。
4. **09-09 窗的落盘延迟。** 原始件写盘比取数完成晚约 1.5 分钟,收据又晚约 2 分钟,原因未查实(研究仓在 iCloud 桌面,I/O 是候选)。与正确性无关:收据记的 raw sha 与盘上文件相同。
5. **新件与旧件的依赖不同。** v4.1 的新收据 `deps_sha256` 记的 `usd_valuation.py` 为当时的工作副本。十窗 D 段各数与 v3 收据逐字段相同。

### 9.8 复跑命令(逐字;在 `docs/fixprogram_2026-09-13/FP3_devices/` 下执行,除非另注)

联网前控制(在仓库根执行):

```
/usr/bin/python3 docs/fixprogram_2026-09-13/FP3_devices/ro_controls.py
```

电池 × 3(不联网):

```
/usr/bin/python3 -B tests_flatten_window_closure.py > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_2026-09-19.txt 2>&1; echo "exit=$?" >> ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_2026-09-19.txt
/usr/bin/python3 -B tests_flatten_window_closure.py --device archive/flatten_window_closure_v4_813501e1.py > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_vs_v4_813501e1_2026-09-19.txt 2>&1; echo "exit=$?" >> ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_vs_v4_813501e1_2026-09-19.txt
/usr/bin/python3 -B tests_flatten_window_closure.py --device archive/flatten_window_closure_v3_02418fdd.py > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_vs_v3_2026-09-19.txt 2>&1; echo "exit=$?" >> ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v41_battery_vs_v3_2026-09-19.txt
```

本次运行另带 `--tmp-root <scratchpad>`,只改临时目录位置。

十窗新拉取(联网,只读)。**目标文件已存在时装置会拒绝**,所以重跑须换新文件名;要复核不联网,改用下面的离线复用:

```
/usr/bin/python3 -B flatten_window_closure.py <t0> <t1> ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4fresh_<事件>.json ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4fresh_<事件>_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event <事件> > ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4fresh_<事件>.log 2>&1
```

十窗的 `<事件> <t0> <t1>` 与 §7 相同(逐字取自 v3 收据的 `argv[:2]`):

```
FLATTEN-20260801T201827Z 1785615495.327172 1785629783.8997319
FLATTEN-20260802T041821Z 1785644299.48212 1785649625.6190689
FLATTEN-20260805T001853Z 1785889104.446205 1785903346.010344
FLATTEN-20260805T121829Z 1785932306.207547 1785946762.351441
FLATTEN-20260821T121630Z 1787314570.9543638 1787329180.200428
FLATTEN-20260821T201600Z 1787343345.308213 1787357763.6213398
FLATTEN-20260826T124702Z 1787748333.642869 1787762283.433176
FLATTEN-20260906T084608Z 1788684263.67789 1788698342.895093
FLATTEN-20260909T164536Z 1788972245.856354 1788986342.424868
FLATTEN-20260912T124737Z 1789217147.803424 1789231143.365168
```

离线复核某窗的新拉取(不联网;预期 `VERDICT CLOSED`、rc 0、`POPULATION_PASS`):

```
/usr/bin/python3 -B flatten_window_closure.py 1788684263.67789 1788698342.895093 <任意临时目录>/reuse_fresh_0906.json --reuse-raw ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4fresh_FLATTEN-20260906T084608Z_venue_trades.json --bnb-rows ../FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json --event FLATTEN-20260906T084608Z; echo rc=$?
```

旧件 vs 新件对照(不联网):

```
/usr/bin/python3 -B compare_flatten_raw_old_vs_fresh.py ../FP3_receipts/venue_readonly_2026-09-19 ../FP3_receipts/venue_readonly_2026-09-19/FLATTEN_CLOSURE_v4fresh_vs_old_raw_diff_2026-09-19.json
```
