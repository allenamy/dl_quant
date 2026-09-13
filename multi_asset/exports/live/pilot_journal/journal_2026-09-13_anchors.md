> **创建:** 2026-09-13 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 只追加 | 前一日 `journal_2026-09-12_anchors.md`

# 2026-09-13 逐锚日志(书自 09-12 12:47Z 起空仓 + 开仓停, 待用户恢复)

## 00:00Z 锚 · 停开仓第三锚(只读, 实盘零接触)
**锚** canonical 1789257600 / 执行器 anchor_ts 1789259039 / rid **A1789259039** / 运行树 918559f。**结论: 无处置。**
- **① 三守护** 全绿(10900 / 30943 / 30944, 句柄一致)。
- **② 信号六项** status OK / coverage 1.0 / members 400 / sel 256 / **fund_updates 454**(8h 结算整点稳态 ~453 ✓)/ forced_exit_n 3 / runtime 293.9 s / fetched 450 missing 0; w3 [0.3277, 0.1125, 0.5598]; 生产者 turnover 2.468%; carry 1.097 bps / cost 0.087 bps。
- **③ 执行漏斗** orders **243** = **240 `blocked_by_halt` + 3 `skipped_min_notional`**, **submit 0, fills 0** ⇒ 零下单; target_gross 235,275U 全被挡。
- **④ 记账** 新日文件 `pilot_log/20260913/`; anchors 1 行, `opening_halted` true; NAV **117,780.40**(20Z 117,779.56, +0.84); 当日 realised 0.0(新日起点); **00Z 是 8h 结算锚但 funding income=0 rows=0** —— 空仓即无 carry; `anchor done rc=0` 00:40:58Z; 看门狗 00:39:48Z tripped=False(n_days 44), state 仍 reduce_only/halted; 告警 raised 4 / delivered 2。
- **⑤ 执行质量** 无成交, 不适用。**⑥ 异常处置** 无。
- **⑦ 与 20Z 对比**: 订单 245→243, fills 0→0, NAV −7.47→+0.84, fund_updates 355(4h)→454(8h 结算)✓, 看门狗评估同。
### 空仓的机会成本(供恢复决策; 生产者自报 carry, 非已实现)
最近四锚 carry 均值 **1.15 bps/锚(单位 gross)** ⇒ 按当前目标 gross 235,275U: **每锚 ≈ 27 USDT**, **每日 6 锚 ≈ 162 USDT ≈ 0.138% NAV**。**口径警告**: 这是生产者对**目标书**的 carry 估计, 不是已实现值; 价格腿贡献未计(08-26→09-11 实测价格 alpha ≈ 0, t −0.01); 恢复后实际值由首锚验收实测。**已空仓 12h(3 个锚)**。

## 04:00Z 锚 · 停开仓第四锚 · 全深度深查(只读, 实盘零接触)
**锚** canonical 1789272000 / rid **A1789273440** / 运行树 918559f(代码与之逐字节同)。**结论: 无处置。**
### ① 三守护 全绿(句柄为准): shadow.lock 10900 / sidecar 30943 / combo_live_daemon.pid 30944。
### ② 信号六项 全在带
status OK / coverage 1.0 / members 400 / sel 254 / **fund_updates 355**(4h 稳态 ~353 ✓)/ forced_exit_n 5 / runtime 254.5 s / fetched 450 missing 0 / future_dropped 0 / exinfo_ok。w3 **[0.3454, 0.0956, 0.5590]** ⇒ 掩码算术 **0.381911** vs `w3_masked[0]` **0.381951**(差 4.0e-5, 日志 w3 取 4 位小数的舍入误差内 ✓)。combo_live_status 锚匹配 / ok / done / reader_ok / n 253 / gross 0.8191(04:21:34Z)。kc **own** / fc **own** / f10 **400** ✓ / rho_kc_fc **0.9202**。生产者 turnover 4.583%(带内), carry 1.196 bps, cost 0.176 bps。
**反事实改写 27.46%**(20Z 26.58 → 04Z 27.46, 两锚 +0.88pp; 自 09-12 起连升)。伴随 **rho_kc_fc 下行**(09-12 08Z 0.9349 → 20Z 0.9271 → 04Z 0.9202)—— 两模型腿分歧加大, combo 对 king 形态的改写随之变大, 机制上自洽。书空仓, 该量只描述生产者目标书与 king 形态之差, 与实际持仓无关 ⇒ **记待验证**, 恢复交易后首两锚复判(判据已达升级条件)。
### ③ 执行漏斗 orders **241** = **240 `blocked_by_halt` + 1 `skipped_min_notional`**, submit 0, fills 0 ⇒ 零下单; 成交类指标不适用。
### ④ 记账 anchors 2 行(00/04Z), `opening_halted` true, target_gross 235,193U 全被挡; readback 241 行 Σ|名义| **0.00**; **NAV 117,776.42**(00Z 117,780.40, −3.98); 04Z 非 8h 结算锚 funding 0 ✓; `anchor done rc=0` 04:40:50Z; 看门狗 04:39:45Z tripped=False 但 state 仍 halted/reduce_only; 告警 raised 4 / delivered 2, ALARM.log 末行仍为 09-12 12:50:01Z。
### ⑤ 执行质量 不适用。⑥ 异常处置 无。
### ⑦ 空仓期累计(自 09-12 12:47Z 平仓)
| 锚 | 订单行(挡/小额) | NAV | Δ | rho_kc_fc | 反事实改写 |
|---|---|---|---|---|---|
| 16Z | 243/2 | 117,787.02 | — | — | 25.36%(12Z) |
| 20Z | 243/2 | 117,779.56 | −7.47 | 0.9271 | 26.58% |
| 00Z | 240/3 | 117,780.40 | +0.84 | — | — |
| **04Z** | **240/1** | **117,776.42** | **−3.98** | **0.9202** | **27.46%** |
### 待验证 / 推断
**待验证**: (a) 空仓四锚 NAV 累计 −10.60U 的来源(无持仓、无成交; 可能是费用币 BNB 余额按市价重估或钱包计息, 需 API 确证); (b) 反事实改写连升 + 两腿相关下行, 恢复后首两锚复判; (c) 成交类指标自 09-12 12Z 起无观测。**推断**: 零下单与 `opening_halted` 及看门狗 state 一致。**空仓已约 16 小时 / 4 个锚**; 按生产者自报 carry(本锚 1.196 bps)估每锚机会成本约 28U(非已实现)。

