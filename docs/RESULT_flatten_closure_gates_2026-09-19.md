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
