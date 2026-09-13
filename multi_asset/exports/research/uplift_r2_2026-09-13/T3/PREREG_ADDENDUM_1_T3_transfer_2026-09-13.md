> **创建:** 2026-09-13 05:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 T3)| **状态:** 冻结, 先于本文所列量的任何计算(sha256 见 `receipts/PREREG_ADDENDUM_1_FREEZE_sha.txt`) | **作废条件:** 同 `PREREG_T3_markout_curve_2026-09-13.md`
> **母文件:** `PREREG_T3_markout_curve_2026-09-13.md` sha256 `c7be850055160d7eeafe10fb859470f442d3f0552333ba290d9496357be8f8f6` | **纲领:** `../PROGRAM_uplift_r2_2026-09-13.md` AMENDMENT 1(commit `447f5853`)与 AMENDMENT 2(commit `83579437`)

# PREREG ADDENDUM 1 — lead 的迁移要求与「引用 r11, 不重算」

## §0 为什么有这份补充, 以及它**不改**什么
lead 的消息(在母文件冻结之后才送达)补了四项要求: 引用 r11 的期限结构而不重算; 用 orders.jsonl 终态标出反转方向名字上「挂了没成交」的 maker 单; 报告子集规模以及它与一本 REV_SHORT 书会发出的单在**方向、大小、流动性分档、距离那段走势多久**上的差别; 写出迁移失效的条件; 并接受「下一锚场所中价」作为不经缓存的第二仪器。

**如实声明时序:** 母文件的主估计量、门、判决(UNDECIDABLE)与事后分析**在本文之前已经算出并写进 RESULT 初稿**。本文只定义新增的描述性诊断与一个仪器对账, **不改**估计量、门槛 1.6、判决规则、任何已分配的 k, 也不改已报的判决。

## §1 A0 — 描述性 markout 从 RESULT 正文撤下
期限结构是 r11 的结果, 引用 `uplift_2026-09-11/r11_costtruth/out/r11_term_structure.json` sha256 `5c8e472fc666e781e29a97567980c816f643977235b901accc57a59e1921705e`(maker 组含 CI)。`receipts/MARKOUT_desc.json` 只保留为门 G3 的仪器核对: P1 标记与账本 60 s 标记是同一笔成交, 且本线装置对 r11 maker 组点估计逐位复现。正文不再报切分表。

## §2 A1 — 反转方向名字上挂了没成交的 maker 单(orders.jsonl 终态)
总体 = 母文件 R1(ERA2)。每个计划按 maker 腿的订单行归类:
- `first_send` 计划: 已发 maker 行的 `terminal_reason`(filled / partial_expired / 其它)× 成交是否为零;
- `requote` 计划(同组有 attempt-1 `venue_reject -5022` 且有已发 maker 行): 重挂行的 `terminal_reason` × 成交是否为零;
- `refused_no_requote` 计划: 按同组 attempt-2 maker 行的 `terminal_reason`(venue_reject / transport_error / blocked_by_halt / 无行)与 `requote_arm`(direct / 其它)。
每类报: 计划数、意图名义、成交名义、未成交名义、占 R1 未成交名义的份额、对 R1 机会成本的贡献 `Σ U·s·y4_E / Σ I_R1`(bps, 只报点估计, 无 CI)。

## §3 A2 — 与一本 REV_SHORT 书会发出的单对照(同一批 ERA2 锚, 同一份资本)
- **REV_SHORT 假想单:** 每个 R1 所在锚 E, 可分类名上 `w_E = r̃/Σ|r̃|`, `Δw = w_E − w_{E−4h}`; 单子名义 `q = |Δw|·G_E`, `G_E` = 该锚 anchors.jsonl `target_gross`(USDT); 方向 = sign(Δw); `q <` 执行器 `exchange_info_cache.json`(拷贝 `private/exchange_info_cache_live_20260913.json`, sha256 `405cf828454c84881c83059d04a85f6da117b8b8dd2ab485f8bef4a348d893bb`)该名 `min_notional` 的单剔除(同执行器的灰尘规则), 计数。
- **对照维度(两边都按名义加权, 另报按单数):**
  1. 方向: 买方名义份额。
  2. 大小: 单子名义的 p25 / p50 / p75 / p90 / p99; 固定区间 [5,10) [10,25) [25,50) [50,100) [100,250) [250,500) [500,1000) [1000,∞) USDT 的份额与总变差距离; 每锚总名义。
  3. 流动性分档: tier0 / 1 / 2 份额(qv4h 于 E, 同母文件)。
  4. 走势离下单多久:
     - `m_1h = −s·r[E−1h, E]`: 缓存 ret5 行 E−55m..E 连乘(守卫同 G5: 任一根非有限或 |ret5| ≥ 0.2999 则该格记为不可用并计数);
     - `m_early = −s·((1 + y4[E−4h]) / (1 + r[E−1h, E]) − 1)`: 上一锚 4 h 走势里前 3 小时那段(y4 取记账 meta);
     - `m_prev = −s·y4[E−8h]`: 再往前一个锚的走势;
     - `m_lat = −s·r[E, 运行起点]` 不在此处重算(母文件的 b 已给出 R1 的值)。
     报两边的名义加权均值(bps, 正 = 名字在下单前朝与单子相反的方向走过), 以及聚合的「最后一小时份额」`Σ q·|m_1h| / Σ q·(|m_1h| + |m_early|)`。
- 两边都只报点估计, 无 CI(描述性)。

## §4 A3 — 机会成本项的第二仪器(不经缓存)
R1 计划中, 下一锚行(`anchor_ts ≥ 运行起点 + 60 s` 的第一行, 间隔 ∈ [3 h, 5 h])含该名中价者:
- `o_next = s·(M_next/M_run − 1)`(两端都是执行器记录的场所中价);
- `o_run = s·((1 + y4_E)·P_E/M_run − 1)`(母文件口径: 运行中价 → E+4h 收盘, 用 meta 与 G5 守卫下的回推);
- 同一计划集上两个**运行钟**估计量(都不含 E→运行起点延迟, 与门所用的 E 钟不同):
  `c_run_cf = [Σ fee + Σ N_f·a + Σ U·o_next] / Σ I`, `c_run_meta = [Σ fee + Σ N_f·a + Σ U·o_run] / Σ I`;
- UTC 日块自举 2000, `default_rng([20260905, 401])`, 两者与其差用同一组日索引联合重抽; 报覆盖(计划数与意图名义份额)。
- 读法先写下: 两者之差的 CI 含零 ⇒ 两台仪器对机会成本项一致; 不含零 ⇒ 写进局限并说明钟差(运行钟终点 E+4h+24m vs E+4h)。**不进门。**

## §5 迁移失效条件
RESULT 必须把 A2 的读数逐条对到母文件 T-A2 / T-A3 / T-A6, 并写成「若……则迁移失效」的句式。
