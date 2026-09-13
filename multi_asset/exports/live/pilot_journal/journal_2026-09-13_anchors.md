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
