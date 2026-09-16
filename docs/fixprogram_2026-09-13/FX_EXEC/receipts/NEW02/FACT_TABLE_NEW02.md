> **创建:** 2026-09-16 | **Session:** FX-EXEC(teammate fx-exec) | **状态:** 事实表(先于代码), NEW-02 | **作废条件:** 执行器基底 ef60f85 以外的运行树被部署; 或本表任一 F 行被逐字复跑推翻

# 事实表 · NEW-02 · `live/venue_fills.py:1179` 平仓 fills 行 attempt_idx

登记: FIXPROGRAM §8「**NEW-02** `venue_fills.py:1179` 平仓 fills attempt_idx 2 对订单行 1」。
基底 = 执行器克隆 `/Users/haosiyu/cc_tmp/fx_exec` @ 48e9938(祖先 ef60f85 = 运行树)。
真数据 = 只读副本 `/Users/haosiyu/cc_tmp/fx_exec_census_new02`(逐文件 sha 见 `census_input_SHA256SUMS.txt`, 复制时刻见 `census_input_COPY_META.txt`)。
**未冻结的一项**: `census_alldays.log` / `census_e0909g_control.log` 直接只读扫描 `~/dl_quant_live/state/live/pilot_log`(全天普查, 无法预先冻结全部日目录); 其结论中落在 09-09 / 09-12 两日的部分与冻结副本一致。

## A. 写者合同(读码)

| id | 事实 | 出处 |
|---|---|---|
| F1 | fills 表 `attempt_idx` 在 `not_null` 列表, 理由逐字: 「Kept not_null: anchor_ts / rebalance_id / attempt_idx / symbol / order_type — **ours**」⇒ 它是我方标识符, 不是场所观察量 | `live/pilot_log.py` SCHEMA["fills"]["not_null"] 及其上方注释 |
| F2 | orders 表同列同理由(「our clock, our identifiers」), 同为 not_null | `live/pilot_log.py` SCHEMA["orders"]["not_null"] |
| F3 | **梯子行合同**: 「★ attempt_idx ON A LADDER ROW MEANS "WHICH ATTEMPT", not the rebalance leg's 1=maker/2=topup」 | `live/tests_flatten_rows.py:30`(套件文档) |
| F4 | 同合同在写者处逐字重述, 并记录它曾被硬编码为 1 的缺陷: 「★★ [b] ON A LADDER ROW, attempt_idx IS *WHICH ATTEMPT* — not the rebalance leg's 1=maker / 2=topup. It was hardcoded to 1, so 208 rows under one FLATTEN- id could not answer "what did each attempt do"」; 取值 `attempt_idx=int(o.get("attempt_idx") or 1)` | `live/watchdog.py:2386-2390` |
| F5 | 梯子把「第几次尝试」盖在每张单上: `_attempt = out["stage1_flatten_attempts"]`; `_x.setdefault("attempt_idx", _attempt)`(正常返回路径与异常路径各一处) | `live/watchdog.py:630, 669` |
| F6 | 07-26 真形态的承重断言: 梯子三次尝试 103/103/2, 订单行 attempt 分布必须 `{1: 103, 2: 103, 3: 2}` | `live/tests_flatten_rows.py:106-125` |
| F7 | **rebalance 行的 attempt 也是「第几次」**, 不是腿序: 重挂重试写 `p["attempt_idx"] = 2` 而 order_type 仍为 `maker`; 补单腿 attempt 2 | `live/binance_executor.py:1307`(重挂)· `live/tests_binance_executor.py:97-98, 307-308`(补单/重挂承重断言) |
| F8 | **缺陷行**: fills 写者由 order_type 反推 attempt —— `"attempt_idx": 1 if otype == "maker" else 2`; `otype` 可取 `maker` / `topup_taker` / `protective_flatten` ⇒ 平仓一律落 2 | `live/venue_fills.py:1165, 1179` |
| F9 | 该行自 `6594b77`(佣金按腿归属)起为现形; 更早 `1c93e10` 写作 `1 if t.get("maker") else 2`(按场所 maker 旗)。`protective_flatten` 进入 otype 是 E-0912-A (b), 随 ef60f85 落地 ⇒ **09-12 之前不存在「平仓 fills 由本写者落 2」的行** | `git log -L 1175,1182:live/venue_fills.py` |
| F10 | 树内每个 attempt_idx 读者的缺省都是 **1**(`int(x.get("attempt_idx") or 1)`), 且有承重断言「rows without attempt_idx count as attempt 1」 | `live/reject_rate.py:45` + `live/tests_reject_rate.py:87`; `live/watchdog.py:2390`; `live/tests_disposition_matrix.py:786`; `scheduler/anchor_loop.py:855` |

## B. 平仓腿的 attempt 从哪里来(读码; 决定修法)

| id | 事实 | 出处 |
|---|---|---|
| F11 | rebalance 单的 client id = `f"{rebalance_id}-{symbol}-{int(pl.get('attempt_idx') or 1)}"[:36]` ⇒ **后缀就是 attempt**(重挂 attempt 2 的 id 以 `-2` 结尾) | `live/binance_executor.py:1408, 1814`; `live/venue_fills.py:399` |
| F12 | **平仓单的 client id 后缀不是 attempt**: `_seq = next(_FLATTEN_SEQ)`, 注释逐字「a process-wide counter, never the per-symbol chunk index」; 形如 `F<yyyymmddHHMMSS>-SYM-<seq>` | `live/binance_broker.py:1805-1812`; `live/venue_fills.py:1285` |
| F13 | F12 经真数据确认: 09-12 平仓 255 张单的 client id 后缀取值 **1..255 两两不同**, 而 255 行 order 行 attempt_idx **全为 1** ⇒ 按后缀解析 attempt 会得到 1..255, 是比现缺陷更坏的错 | `census_client_ids.log` |
| F14 | 平仓单在 09-09 **完全没有 client id**(场所自铸), 09-12 起 255/255 都有; `client_id_dropped`(>36 字符)分支存在, 两日均为 0 | `census_client_ids.log`; `live/binance_broker.py:1814-1820` |
| F15 | 腿身份图 `submitted_order_legs` / `order_legs_from_venue` 的值只带 `symbol` / `client_id` / `leg` / `tif`, **不带 attempt**; `attribute_trades` 只把 `leg` 抄到成交行(`row = dict(t); row["leg"] = leg`) | `live/venue_fills.py:880-935, 949-998, 1263-1320` |
| F16 | 平仓 fills 的生产路径是 `ops/backfill_fills.py`(gap kind=flatten ⇒ `order_legs_from_venue(..., client_ids=_cids, leg="protective_flatten")` → `fill_rows_from_trades`); 逐锚路径 `scheduler/anchor_loop.py:2492` 走 `submitted_order_legs`(只有 maker/topup 腿) | `ops/backfill_fills.py:110-121`; `scheduler/anchor_loop.py:2492` |

## C. 真账本(两日冻结副本 + 全天普查)

| id | 事实 | 出处 |
|---|---|---|
| F17 | **09-12**: 平仓 order 行 255, attempt 全 1; 平仓 fill 行 7,312, attempt **全 2** ⇒ 与订单行不一致 | `census_attempt_idx.log` |
| F18 | **09-09**: 平仓 order 行 243, attempt 全 1; 平仓 fill 行 6,190, attempt **全 1** ⇒ 一致。两批互相矛盾 | `census_attempt_idx.log` |
| F19 | 矛盾之因 = **两个写者**: 09-09 行带 `rebuilt_from_venue`(一次性修复脚本 `multi_asset/exports/live/pilot_journal/tools/backfill_flatten_fills_20260909.py`, 它调用 `VF.fill_rows_from_trades` 后**逐行覆写** `r["order_type"]="protective_flatten"; r["attempt_idx"]=1`); 09-12 行带 `backfilled_utc=2026-09-13T13:13:12Z`(E1 回填走 `ops/backfill_fills.py` ⇒ 本写者) | `census_provenance.log`; 脚本 L13, L85-86 |
| F20 | ⇒ **两个写者都是硬编码**(一个钉 1、一个钉 2); 它们与真相一致只是因为在役 8 批梯子**每一批都在第 1 次尝试成功**(order 行 1,708/1,708 全 attempt 1) | `census_alldays.log` |
| F21 | **缺陷的可观测后果**: 按 `(rebalance_id, symbol, order_type, attempt_idx)` 联接 orders↔fills 时, 09-12 的 **7,312 行全部联接不上**(09-09 的 6,190 行全部联上) | `census_family.log`, `census_alldays.log` |
| F22 | 全史普查: 有平仓 order 行的日共 8 天(1,708 行), 有平仓 fill 行的只有 09-09 与 09-12; 联接失败总计 **7,312**, 全在 09-12 | `census_alldays.log` |
| F23 | **同族第二位点(潜在, 未观测)**: 重挂后的 maker 单 order 行 attempt=2(09-09 16 行 / 09-12 21 行), 而本写者对 maker 腿一律落 1 ⇒ 若其成交则 fills 说 1、orders 说 2。真数据: 两日这些行 `filled_notional` **全为 0** ⇒ 至今**未发生** | `census_family.log` |
| F24 | 仪器正控: 同一联接在 09-09 报出 138 行 maker fills 联接不上, 全部属 rid `A1788956640`(2026-09-09T12:24:00Z), 该 rid 在任何一天的 orders.jsonl / anchors.jsonl 中都是 **0 行** —— 即已登记的 **E-0909-G 账本缺口**(12Z 锚无 orders 行 ⇒ 看门狗逐名门平仓), 不是新缺陷, 也不是 NEW-02 | `census_e0909g_control.log`; 记忆 `watchdog_trip_from_ledger_gap_e0909g_2026_09_09.md` |

## D. 读者普查(「谁按 attempt_idx 联接或分桶」)

**执行器树内**(`live/` `ops/` `scheduler/` `signal/`, 非 tests):

| 读者 | 表 | 用法 | 受本缺陷影响? |
|---|---|---|---|
| `live/pilot_log.py` validate | **fills** + orders | `not_null` 要求非 None | 是(约束修法: 不能写 None) |
| `live/pilot_metrics.py` `m2_markout` | **fills** | 分桶按 `order_type`, **不读 attempt_idx** | 否 |
| `live/pilot_metrics.py` `dedupe_fills` / `pilot_log.collapse_supersedes` | **fills** | 键 = `trade_id` | 否 |
| `live/pilot_metrics.py` `m3_fill_rate` L352,360 | orders | `int(o["attempt_idx"]) == 1` 作分母 | 否(只读 orders) |
| `live/watchdog.py` L1381-1387 | **fills** | 计数 / `m2_markout` / 按 `anchor_ts` 过滤 | 否 |
| `live/reject_rate.py` L45 | orders | attempt 1 与 2 分桶 | 否 |
| `ops/score_post_fix.py` L348 | orders | `!= 1 ⇒ continue` | 否 |
| `scheduler/anchor_loop.py` L855 | orders(`executor.rows_orders`) | `(symbol, attempt)` 去重 | 否 |
| `ops/assert_anchor_artifacts.py` | orders(逐列) / fills(**仅整表在否**) | 恒定列判定只对 `orders[0].keys()` 迭代(L465); fills 只判整表(L552) | 否 |
| `live/tests_disposition_matrix.py` `_flat_key` L785,841 | orders ↔ 事件日志 | 联接键 `(symbol, side, attempt_idx)` | 否 —— **但它是「若改 orders 侧就会红」的承重读者**(见修法范围) |
| `ops/backfill_fills.py` `existing_trade_ids` | **fills** | 键 = `trade_id` | 否 |
| `ops/backfill_markout.py` · `ops/import_markout_marks.py` · `ops/first_anchor_review.py` · `ops/first_real_anchor.py` · `live/reconcile.py` | fills | 不含 attempt_idx(逐文件 grep 为空) | 否 |

**研究仓消费者**(`multi_asset/`; 按是否 orders↔fills 联接分类):

| 读者 | 用法 | 受本缺陷影响? |
|---|---|---|
| `retrain_2026-09/health_check_2026-09-05/calib/markout_diag.py` L16,24 | **orders↔fills 联接**: `SPR[(rid, symbol, order_type, attempt_idx)]` 由 orders 建, 由 **fills 行**查 | **是** —— 平仓 fill 查不到 `spread_at_submit_bps`。该装置窗 = 20260826..20260905, 其中无整书平仓 ⇒ 已发表数字不受影响, 缺陷在码 |
| `retrain_2026-09/health_check_2026-09-05/calib/cost_calib.py` L118,120 | **orders↔fills 联接**: `PX[(rid, symbol, order_type, attempt_idx)]` 由 orders 建, 由 **fills 行**查; 未命中 ⇒ `_fee_usdt = NaN` 并计入 `nofee` | **是** —— 平仓 fill 的 BNB 费不可归属 |
| `r11_costtruth/scripts/export_fills_for_markout.py` L104 | 原样导出 fills 的 `attempt_idx` 列 | 传播(下游按该列分桶即受影响) |
| `retrain_2026-09/.../calib/survey_keys.py` L9 | 把 attempt_idx 列为 fills 的分类列做取值普查 | 传播(普查会看到 1 与 2 两制) |
| `trackB_realized_cost` L105 · `trackB_churn_decomp` L42 · `r14_{intent,nulls,gap}` · `infra1_cost/extract_fill_costs` L88 · `r11_{quoting,financing}_arith` · `r17_fillmodel` · `r21_bridge` · `T3/t3_*` · `T5b/t5b_exec` | 只按 orders 行的 attempt 过滤 / 分桶(多为 `order_type=="maker" and attempt_idx==1`) | 否 |

## E. 结论(先于修码)

1. **哪一侧是对的**: **orders 侧**。两表同一列同一合同 = 「我方标识符 · 第几次尝试」(F1/F2/F3/F4/F7); orders 侧由梯子/执行器**记录**真实尝试号(F5/F7), fills 侧由 order_type **反推**(F8)。反推在三处不成立: 平仓(F17, 已发生 7,312 行)、重挂 maker(F23, 潜在)、以及任何未来第 3 次尝试(F6 的 07-26 形态)。
2. **不可采的修法**: 按 client id 后缀取 attempt —— 对 rebalance 单成立(F11), 对平仓单是进程级序号(F12), 真数据会给出 1..255(F13)。
3. **可采的修法**: 让腿身份图携带 attempt, 由 `attribute_trades` 抄到成交行, `fill_rows_from_trades` 优先用它; 只在 **形如 `{rid}-{symbol}-<digits>`** 时才由 client id 解析(F11 成立域), 平仓批由调用方从该批 order 行建 `{client_id: attempt_idx}` 传入(F16 已有 `gap["client_ids"]`)。这同时按构造修掉 F23 的潜在位点。
4. **不可解析时**: 不得沿用 2(由不适用的腿序规则得出)。树内每个读者对缺失 attempt 的缺省都是 1 且有承重断言(F10), 在役 1,708 行平仓 order 行也全是 1(F20) ⇒ 落 1 并在行上**具名**来源, 使「联接得到的」与「按缺省落的」可区分。
5. **不在本项内**(交 lead): 已写下的 7,312 行历史 fills 行不由本修复改写(fills 表只追加; 改写实盘账本属 LED-04 族修订记录, 且本工作者对实盘只读)。在存在修订记录之前, 按该键联接的读者仍会漏掉这 7,312 行。
