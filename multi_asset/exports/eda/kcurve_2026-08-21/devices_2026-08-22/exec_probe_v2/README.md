> **创建:** 2026-08-22 00:4xZ | **Session:** probe-v2(子代理, team-lead 派工) | **状态:** 已交付, **未启动**(启动与否由用户决定) | **作废条件:** 探针 14 天读数完成并 RESULT 收口, 或被 v3 取代

# 执行探针 v2 — 只动自己建的仓 / 排除整个实盘宇宙 / 每轮对账收据

**位置**: `~/exec_probe/v2/`(研究仓副本 `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-22/exec_probe_v2/`)。
**背景**: `docs/INCIDENT_daily_loss_trip_2026-08-21.md` §S + `docs/ERROR_LEDGER_2026-08-20.md` E-0821-C —— v1 轮末 `if s in syms and |amt|>0: 市价平` 不分仓位归属, 16:23Z 把书的 ATOM 237.72 / SNX −806.5 平掉 ⇒ 看门狗 5b/5e 真触发 ⇒ 20:16Z 整书平仓。v1 已停(`~/exec_probe/KILL` 在, 进程已结束), **v1 不要再启动**。

## 1. 改了什么 / 为什么(三条硬规则 + 防御)

| # | 规则 | 实现(`exec_probe.py`) | 为什么 |
|---|---|---|---|
| 1 | **只平自己建的仓** | `finalize_orders` 对本轮每张自家 orderId 查状态/撤单/取最终 `executedQty`; `own_net_from_fills` 累计净量; `flatten_own` 只对本轮名字、只按 `min(|自己净量|, |账户持仓|)` 发 reduceOnly 市价单, 且必须与持仓同号; 账户持仓 ≠ 自己净量 ⇒ 事件 `foreign_position_detected` **只记不动**; 自己净量 0 的名字(哪怕有仓)不发任何单 | 事故直接根因。08-21 的 BANK 2362(自己买成卖拒) 会被平, ATOM/SNX(自己零成交) 不会 |
| 2 | **排除整个实盘宇宙, 每轮重选** | `load_universe`: 权威 = `~/dl_quant_live/config/funding_span_table.json["table"]` 的键(**140** = 面板列集 = `live_panel.panel_symbols()`, 月度成员 110 在其内选) ∪ `state/live/preds_latest.json["symbols"]`(当月 110) ∪ `checkpoints/MANIFEST.json["training_member_union"]["symbols"]`(140, 与权威逐位相同, 2026-08-22 核) ∪ 账户当前持仓名; 权威读不到/<100 名 ⇒ `universe_unreadable` 跳轮; 候选为空 ⇒ `skip_round_no_candidates`; `PROBE_SYMS` 钉名同样过滤 | v1 只排"当时持有名", 15:15Z 书空仓 ⇒ ATOM/SNX 进了名单。v2 空跑时书也是空仓(00:37Z), 仍排掉段内 29 个宇宙名 |
| 3 | **对账收据 + 停机守卫** | 每轮 `state/receipt_<round>.json`: 下单集/成交/自己净量/平仓/轮末持仓/foreign 列表/`assert_touched_disjoint_universe`/`assert_flatten_only_own`/`assert_round_syms_disjoint_universe`/宇宙来源(路径+n+sha256)/守卫读数/盈亏估算; 守卫 `live_halted`: `state/live/watchdog/state.json` 的 reduce_only/tripped_at/open_orders_halted **或** `last_eval.json` tripped **或** last_eval 过期 >6h **或** 读不到 ⇒ 跳轮(保守方向) | 5b/5e 的"未授权"在探针侧留收据; 守卫按看门狗自身语义(state.json 不在 = 已 resume 归档)但不只看存在 |
| 防御 | (i) 轮必须在 [锚+20, 锚+40min] 内开始, 否则 `skip_round_off_slot`(机器睡醒不越锚) (ii) 下单即落盘 `state/pending_round.json`, 被杀后下次启动 `recover_pending` 只对账本里的 orderId 对账并只平自己净量(写 `receipt_recovery_*.json`) (iii) 单日估算净损 < −$10 ⇒ 当日余轮跳过(PREREG 安全线, **估算值**: 成交价×量±费率 0.02%/0.05%) (iv) 候选名上有非 `probe*` 前缀挂单 ⇒ 该名跳过; 自家 `probe*` 孤儿单轮首撤 (v) 非 COIN 标的/非永续/非 TRADING 合约用 exchangeInfo 数据排除(空跑首轮 USARUSDT=EQUITY 穿过了 v1 静态股票名单; 交易所有 173 个非 COIN perp) (vi) 无 `run` 动词不启动; KILL 每 30s 检查(v1 要等到下一轮) | 同账户辅助进程铁律(E-0821-C): 下单/平仓集合与书宇宙不相交且只动自己建的仓 |

不变: 形态(T2 段[130,200) 取 3 + T3 段[300,380) 取 2, base $15-26 + xl $75 对, GTX, k=180s), 锚+20min 错峰, 事件字段(`place/status/cancel/flatten/round_end_mid` 与 v1 兼容, `flatten.amt` 现在 = 自己净量), 读数器 `analyze.py`(v2 副本读 `~/exec_probe/v2/events.jsonl`)。

## 2. 测试(mock 账户/mock 下单接口, 不联网)

`python3 tests_exec_probe_v2.py` ⇒ **89/89 PASS**(`tests_green_run.txt`)。场景: (a) 账户有非本轮仓位(书的 ATOM/SNX)⇒ 不平、记 foreign(单元 + 08-21 集成重放 + 轮中他人仓位出现在本轮名字上) (b) 候选 ∩ 宇宙 ⇒ 排除(含钉名、含只在 preds 里的名、含 exchangeInfo 非 COIN) (c) 停机 8 例(reduce_only/tripped_at/open_orders_halted/last_eval tripped/过期/缺失 ⇒ 跳; 健康两例 ⇒ 跑) (d) 收据字段齐全 + 断言 (e) 08-21 形态记账(买成卖拒 ⇒ 平自己净量 2362) (f) 同名自家+他人混合: 只平自己/封顶/反号不动 (g) 宇宙读不到 ⇒ 跳 (h) 被杀后账本恢复只平自己 (i) 候选为空 ⇒ 跳 (j) 越槽跳 (k) 日亏停 (l) 他人挂单名跳/自家孤儿单撤 (m) 无动词不启动/KILL (n) `--dry` 零写操作 (o) 槽计算。

**"会红"证据**(`tests_mutation_evidence.txt`, 把旧逻辑装回去): `PROBE_V2_MUTANT=legacy_flatten`(v1 轮末全平)⇒ **11 红**(a1/a3/f: ATOM 237.72/SNX 806.5 被平); `no_universe`(只排持仓名)⇒ **20 红**(b 等: ATOM/SNX 被选中); `no_halt`(去守卫)⇒ **12 红**(c 全部)。

## 3. 空跑(`dry_run_2026-08-22.txt`, 两次, 只读 GET, 零下单零撤单)

00:37Z/00:39Z: 守卫 halted=False(state.json absent; last_eval 00:16:10Z tripped=False); 宇宙 140(三源一致, 无不一致); **账户 0 持仓**(书 00:22Z resume 后空仓, = 事故前提)仍排掉段内 29 宇宙名(含 ATOMUSDT/SNXUSDT); 第二次另排 20 个非 COIN perp(USAR/TSM/COPPER/OPENAI…); 选出 **AKEUSDT / PIEVERSEUSDT / USELESSUSDT(T2) + 4USDT / ARXUSDT(T3)**, `picked ∩ universe = ∅: True`; 收据 `state/receipt_dry_20260822T003947Z.json` ok=True。(首次选中的 USARUSDT 是 EQUITY, 由此加了第 (v) 条防御。)

## 4. 怎么启动(用户裁定后; 本交付**没有**启动)

```bash
cd ~/exec_probe/v2
python3 tests_exec_probe_v2.py                      # 必须 89/89
python3 exec_probe.py --dry                         # 看选币/守卫/宇宙三行, ok=True
rm ~/exec_probe/KILL                               # v2 同时认 ~/exec_probe/KILL 与 ~/exec_probe/v2/KILL, 任一存在即拒启/停
nohup python3 exec_probe.py run > probe.out 2>&1 &  # 必须显式 run; 首行打印 halt_guard / universe / pinned
tail -f probe.out   # 每轮一行 "round <slot> ok=... skipped=... symbols=[...]"; 收据 state/receipt_<slot>.json
# 停: touch ~/exec_probe/v2/KILL (≤30s 生效, 轮中则轮末收口后退出); 读数: python3 analyze.py
```

### 启动前核查清单(逐条打勾)
1. **KILL 文件**: `ls ~/exec_probe/KILL ~/exec_probe/v2/KILL` —— 要启动就删; v1 进程必须不在(`pgrep -fl "exec_probe.py"` 只允许看到 v2 或空)。
2. **看门狗状态**: `~/dl_quant_live/state/live/watchdog/state.json` 不存在或 reduce_only=false 且 tripped_at=null; `last_eval.json` 的 evaluated_utc 在 6h 内且 tripped=false(空跑第一行会打印读数)。书处于 reduce-only/停机 ⇒ 不启动。
3. **宇宙清单路径**: `~/dl_quant_live/config/funding_span_table.json`(140, sha256 b4d23440… 2026-08-22) / `state/live/preds_latest.json`(110) / `checkpoints/MANIFEST.json`(140) 三者可读, 空跑 `inconsistencies=[]`; 若书宇宙扩容(span 表加名 ⇒ universe_guard 会报), v2 自动吸收, 无需改码。
4. **空跑选出的名字全部不在宇宙**(`assert picked ∩ universe = ∅ : True`), 且不含股票/商品代币(`excluded_meta` 已排)。
5. 账户: `held (acct)` 行的数量 ≈ 书当前持仓数(书满仓时 ~100; 为 0 说明书空仓, v2 仍安全, 但确认这是预期状态)。
6. 时间: `date -u` 对表; 启动后首轮 = 下一个锚+20min(打印 "next round …")。
7. 启动后第一轮看收据: `ok=True`, `foreign_positions=[]`, `flattens` 每条 `qty ≤ |own_net|`; 有 `foreign_position_detected` 即停并查。

## 5. 未被断言覆盖的风险点(只有执行者知道的)
- **盈亏估算是估算**(费率按 VIP0 maker 0.02%/taker 0.05% 近似; 未读 userTrades 佣金), 日停线 −$10 可能早/晚触发; 方向只会是"多跳一轮"。
- **halt 期间不做 recovery**: 书停机时即使有自己的残留仓也不动(保守); 残留仓 ≤ $75×5, 解除后首轮收口。
- 自家订单状态两次都拿不到 ⇒ 该名不平、账本保留到下轮; 期间该名有自己的小仓(已在事件与收据里点名)。
- 宇宙只在轮首加载; 书月度换成员发生在宇宙(140 列集)内, 但若换成员把 span 表改成 >140 名且正好在探针轮中间, 下一轮才吸收(轮中名字不相交由轮首断言保证)。
- mock 不模拟 Binance 限速/部分成交后撤单的竞态(撤单回执 executedQty 视为最终值, 与 v1 一致); hedge(双向持仓)模式未测, 账户为单向。
- 非 COIN 排除依赖 exchangeInfo 的 `underlyingType` 字段语义不变。
