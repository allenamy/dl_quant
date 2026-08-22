> **创建:** 2026-08-22 00:4xZ | **更新:** 00:5xZ(team-lead 更正: 排除集合并上宽书 400/450 宇宙) | **Session:** probe-v2(子代理, team-lead 派工) | **状态:** 已交付, **未启动**(启动与否由用户决定) | **作废条件:** 探针 14 天读数完成并 RESULT 收口, 或被 v3 取代

# 执行探针 v2 — 只动自己建的仓 / 排除在役 140 ∪ 宽书 400/450 ∪ 持仓名 / 每轮对账收据

**位置**: `~/exec_probe/v2/`(研究仓副本 `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-22/exec_probe_v2/`)。
**背景**: `docs/INCIDENT_daily_loss_trip_2026-08-21.md` §S + `docs/ERROR_LEDGER_2026-08-20.md` E-0821-C —— v1 轮末 `if s in syms and |amt|>0: 市价平` 不分仓位归属, 16:23Z 把书的 ATOM 237.72 / SNX −806.5 平掉 ⇒ 看门狗 5b/5e 真触发 ⇒ 20:16Z 整书平仓。v1 已停(`~/exec_probe/KILL` 在, 进程已结束), **v1 不要再启动**。

## 1. 改了什么 / 为什么(三条硬规则 + 防御)

| # | 规则 | 实现(`exec_probe.py`) | 为什么 |
|---|---|---|---|
| 1 | **只平自己建的仓** | `finalize_orders` 对本轮每张自家 orderId 查状态/撤单/取最终 `executedQty`; `own_net_from_fills` 累计净量; `flatten_own` 只对本轮名字、只按 `min(|自己净量|, |账户持仓|)` 发 reduceOnly 市价单, 且必须与持仓同号; 账户持仓 ≠ 自己净量 ⇒ 事件 `foreign_position_detected` **只记不动**; 自己净量 0 的名字(哪怕有仓)不发任何单 | 事故直接根因。08-21 的 BANK 2362(自己买成卖拒) 会被平, ATOM/SNX(自己零成交) 不会 |
| 2 | **排除集合 = 在役书数据宇宙 ∪ 宽书成员宇宙 ∪ 账户当前任何持仓名, 每轮重选**(team-lead 2026-08-22 更正版) | `load_live_universe`: 权威 = `~/dl_quant_live/config/funding_span_table.json["table"]` 的键(**140** = 面板列集 = `live_panel.panel_symbols()`, 月度成员 110 在其内选) ∪ `state/live/preds_latest.json["symbols"]`(110) ∪ `checkpoints/MANIFEST.json["training_member_union"]["symbols"]`(140, 与权威逐位相同); `load_wide_universe`: 权威 = `~/wide_shadow/state/weights/<最新 anchor>.npz["members"]`(**400** 个 int32 下标)→ `~/wide_shadow/shadow_bundle/config.json["symbols_panel"]`(829, 符号轴)映射成符号, 并上 `config.json["symbols_live"]`(**450** = 宽书每锚抓取/选员全集; 2026-08-22 核: 400 ⊂ 450 ⊂ 829, 29 个权重文件成员并集 421 ⇒ 成员在 450 内轮换, 故排除 450); `one_round` 再并上账户持仓名。任一组读不到/下标越界/成员 <50 ⇒ `universe_unreadable` 跳轮; 宽书权重文件 >30h 旧只记 `wide_universe_stale` 仍用于排除; 候选不足 5 取能取到的, 为空 ⇒ `skip_round_no_candidates`; `PROBE_SYMS` 钉名同样过滤; 收据 `exclusion_set`={n_live,n_wide,n_held,n_total} 与 `excluded_universe_by`(live/wide/live+wide 归因) | v1 只排"当时持有名", 15:15Z 书空仓 ⇒ ATOM/SNX 进了名单。★ 宽书并入后的发现: **v1 探针 08-16 起交易过的全部名字(TAG/DEXE/RARE/PARTI/JASMY/BANK/BERA/DODOX)都是宽书 400 成员**, v2 首版空跑选出的 AKE/PIEVERSE/USELESS/4 也是 ⇒ 宽书一旦实盘, 旧探针必撞; 并入后候选只剩 top-450 之外的新上市/放量名 |
| 3 | **对账收据 + 停机守卫** | 每轮 `state/receipt_<round>.json`: 下单集/成交/自己净量/平仓/轮末持仓/foreign 列表/`assert_touched_disjoint_universe`(**本轮触碰名 ∩ (在役 140 ∪ 宽书 400/450 ∪ 持仓名) = ∅**, 带 n_set)/`assert_flatten_only_own`/`assert_round_syms_disjoint_universe`/宇宙来源(路径+key+n+sha256, 宽书权重文件带 anchor_ts/age_h)/`exclusion_set`/守卫读数/盈亏估算; 守卫 `live_halted`: `state/live/watchdog/state.json` 的 reduce_only/tripped_at/open_orders_halted **或** `last_eval.json` tripped **或** last_eval 过期 >6h **或** 读不到 ⇒ 跳轮(保守方向) | 5b/5e 的"未授权"在探针侧留收据; 守卫按看门狗自身语义(state.json 不在 = 已 resume 归档)但不只看存在 |
| 防御 | (i) 轮必须在 [锚+20, 锚+40min] 内开始, 否则 `skip_round_off_slot`(机器睡醒不越锚) (ii) 下单即落盘 `state/pending_round.json`, 被杀后下次启动 `recover_pending` 只对账本里的 orderId 对账并只平自己净量(写 `receipt_recovery_*.json`) (iii) 单日估算净损 < −$10 ⇒ 当日余轮跳过(PREREG 安全线, **估算值**: 成交价×量±费率 0.02%/0.05%) (iv) 候选名上有非 `probe*` 前缀挂单 ⇒ 该名跳过; 自家 `probe*` 孤儿单轮首撤 (v) 非 COIN 标的/非永续/非 TRADING 合约用 exchangeInfo 数据排除(空跑首轮 USARUSDT=EQUITY 穿过了 v1 静态股票名单; 交易所有 173 个非 COIN perp); 非 ASCII 符号名排除(空跑 #3 选中 `币安人生USDT`, clientOrderId/签名编码路径未测, 保守不碰) (vi) 无 `run` 动词不启动; KILL 每 30s 检查(v1 要等到下一轮) | 同账户辅助进程铁律(E-0821-C): 下单/平仓集合与书宇宙不相交且只动自己建的仓 |

不变: 形态(T2 段[130,200) 取 3 + T3 段[300,380) 取 2, base $15-26 + xl $75 对, GTX, k=180s), 锚+20min 错峰, 事件字段(`place/status/cancel/flatten/round_end_mid` 与 v1 兼容, `flatten.amt` 现在 = 自己净量), 读数器 `analyze.py`(v2 副本读 `~/exec_probe/v2/events.jsonl`)。

## 2. 测试(mock 账户/mock 下单接口, 不联网; 含 mock `~/wide_shadow` 形态: config.json 符号轴 580 + 成员下标 npz)

`python3 tests_exec_probe_v2.py` ⇒ **102/102 PASS**(`tests_green_run.txt`)。场景: (a) 账户有非本轮仓位(书的 ATOM/SNX)⇒ 不平、记 foreign(单元 + 08-21 集成重放 + 轮中他人仓位出现在本轮名字上) (b) 候选 ∩ 宇宙 ⇒ 排除(在役名/**宽书 400 成员名 W001/W002/宽书 450 独有名 W300 归因 'wide'**/钉名含宽书名/只在 preds 里的名/exchangeInfo 非 COIN/非 ASCII 名; picked ∩ (live ∪ wide) = ∅; exclusion_set=480) (c) 停机 8 例 (d) 收据字段齐全(含 exclusion_set)+ 断言 (e) 08-21 形态记账(买成卖拒 ⇒ 平自己净量 2362) (f) 同名自家+他人混合: 只平自己/封顶/反号不动 (g) 在役宇宙读不到 ⇒ 跳 (p) **宽书宇宙读不到(无 npz/无 config/下标越界)⇒ 跳; 权重文件 40h 旧 ⇒ 仍排除+记 stale+照跑; 持仓名在两宇宙之外也被排除并计数** (h) 被杀后账本恢复只平自己 (i) 候选为空 ⇒ 跳 (j) 越槽跳 (k) 日亏停 (l) 他人挂单名跳/自家孤儿单撤 (m) 无动词不启动/KILL (n) `--dry` 零写操作 (o) 槽计算。

**"会红"证据**(`tests_mutation_evidence.txt`, 把旧逻辑装回去): `PROBE_V2_MUTANT=legacy_flatten`(v1 轮末全平)⇒ **11 红**(a1/a3/f: ATOM 237.72/SNX 806.5 被平); `no_universe`(只排持仓名)⇒ **17 红**; **`no_wide`(排除集合不含宽书宇宙)⇒ 17 红**(b: W001/W002 被选中、n_wide=0、exclusion_set 错; p 全部); `no_halt`(去守卫)⇒ **12 红**(c 全部)。

## 3. 空跑(`dry_run_2026-08-22.txt`, 四次, 只读 GET, 零下单零撤单; 最终形态 = #4)

- **#4 00:48Z(最终)**: 守卫 halted=False(state.json absent; last_eval 00:16:10Z tripped=False); 排除集合 = **在役 140 ∪ 宽书 450(成员 400, 权重文件 `state/weights/1787356800.npz` age 0.4h) ∪ 持仓 0 = 467 名**(在役∩宽书 123, inconsistencies=[]); 段内排掉 116 个宇宙名(87 宽书独有 + 29 在役∩宽书, 含 ATOM/SNX/AKE/PIEVERSE/USELESS/4/BANK/BERA/DODOX/PARTI/JASMY) + 9 静态/非 ASCII + 20 非 COIN perp; 选出 **CAPUSDT / GRVTUSDT(T2 段仅剩 2 个) + ARXUSDT / GOATUSDT(T3)= 4 名(不足 5 取能取到的)**, `picked ∩ universe = ∅: True`; 收据 `state/receipt_dry_20260822T004827Z.json` ok=True。
- #1 00:37Z / #2 00:39Z(只排在役 140): 书空仓(00:22Z resume 后, = 事故前提)仍排 29 在役名; #1 选中 USARUSDT(EQUITY)⇒ 加防御 (v); #2 选 AKE/PIEVERSE/USELESS/4/ARX —— **其中 4 个是宽书成员**(team-lead 更正的现实依据)。
- #3 00:47Z(并入宽书): 选中 `币安人生USDT` ⇒ 加非 ASCII 排除。

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
3. **宇宙清单路径**: 在役 `~/dl_quant_live/config/funding_span_table.json`(140, sha256 b4d23440… 2026-08-22) / `state/live/preds_latest.json`(110) / `checkpoints/MANIFEST.json`(140); 宽书 `~/wide_shadow/state/weights/<最新>.npz`(members 400, 每锚 :21 写, 空跑显示 age_h) / `~/wide_shadow/shadow_bundle/config.json`(symbols_live 450 / symbols_panel 829) —— 全部可读, 空跑 `inconsistencies=[]`, `wide_stale=False`, `exclusion set … = 467 names`(数量级对: 140+450−123)。若任一宇宙扩容, v2 每轮重读自动吸收, 无需改码; 宽书影子进程若停, 权重文件变旧 ⇒ 仍排除但会记 `wide_universe_stale`。
4. **空跑选出的名字全部不在排除集合**(`assert picked ∩ universe = ∅ : True`), 且不含股票/商品代币(`excluded_meta` 已排)、非 ASCII 名; 候选可能只有 2-4 个(top-450 之外的名本来就少), 这是设计后果不是故障。
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
- 宽书宇宙读的是**上一锚**的权重文件(探针轮 :20, 影子写 :21), 成员轮换 ~4 名/锚, 但已并上 450 抓取全集, 轮换在其内; 若宽书将来换 bundle(symbols_live 变), 路径不变即自动跟随, `symbols_panel` 轴若重排而旧 npz 未重写会映射错名 ⇒ 该情形靠 `wide_stale`/`inconsistencies` 看不出来, 换 bundle 当天需人工核一次。
- 候选稀少(本轮 T2 仅 2 名): 读数样本量比 v1 低, 14 天判定表的 CI 会更宽; 是否放宽段位由用户/team-lead 定, v2 不自行放宽。
