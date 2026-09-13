> **创建:** 2026-09-13 05:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 T3 t3-markout-economics)| **状态:** 判据冻结, 冻结于本线任何新统计量之前(sha256 见 `receipts/PREREG_FREEZE_sha.txt`) | **作废条件:** 实盘账本 schema 改; `costb_PWR_G230k.json`(295b4e7b…)换代; `meta_newprod_v4_x0910.npz`(a8eb3597…)被重建; r11 `marks_multilag.json`(26ca67c9…)被重算; PROGRAM AMENDMENT 1 被撤回
> **分支:** `research/book-uplift-2026-09-11` | **纲领:** `../PROGRAM_uplift_r2_2026-09-13.md` §2 T3 + **AMENDMENT 1**(lead, 05:2xZ)
> **实盘零接触:** `~/dl_quant_live` / `~/wide_shadow` 只读; 账本快照拷到 `T3/private/ledger_snap_20260913T0455Z/`(`MANIFEST_sha256.txt`, 219 个文件)后只读副本; 零网络, 零交易端点。pod2 只 CPU, 隔离目录 `/workspace/uplift_r2_2026-09-13/T3/`, `nvidia-smi` 前后 0 % / 2 MiB, PID 333197 / 339489 不碰。
> **ENV 白名单(E-0826-D):** 全部装置 = **显式空集**, 运行时断言, 装置自报 `self_sha256` 与本文 sha 并写进产物。

# PREREG T3 — 被动执行的反转书: 有效每单位换手成本(含 markout 曲线的描述性复核)

## §0 范围与已读过的东西(先交代, 再定判据)

**范围以 AMENDMENT 1 为准。** 原任务书的 (a)「成本模型是否便宜」已删除; 原 4 h markout 判据的后件「CI 上界 < −2.0 ⇒ 重算全部成本判决」已撤回。理由在三份收据里, 本线打开核实过:
- `uplift_2026-09-11/r11_verdict/RESULT_r11_verdict_2026-09-12.md` §2 与 `r14_estimand/RESULT_r14_cost_estimand_2026-09-12.md` §1: 回放 `w10_sleeve.py` L312–329 用成交后权重乘整段 [E, E+4h] 的 y4。成交之后的价格路径全部在 y4 里, 把 markout 当成本再扣一次是重复计账。
- `r21_nulls_costbridge/RESULT_r21_nulls_costbridge_2026-09-12.md`: 成本模型相对它自己的参照价不偏便宜。

**T3 现在只回答一个问题:** 用在役执行器被动(post-only maker)执行一本 4 h 截面反转书, 它的**有效每单位换手成本**能否 CI 上界 < 1.6 bps(P6 EMA a=0.5 的盈亏平衡 1.6036)。

**写本文之前已经看过的数字(如实声明, 本文不是对它们盲写的):**
- r11 已发表的 markout 期限结构(全部成交平衡面板 +60s −3.2026 … +4h −6.1359 [−16.94, +3.94]; maker 组点估计 +1h −11.8949 / +4h −11.3625)。
- r21 已发表的同事件桥(maker 成交相对锚运行中价 slip −4.867, E→E+24m 漂移在成交子集 −7.28、全部意图 −2.28)。
- r14 的一句: 墙贵了 2.20 bps/单位成交, 其中 1.6457 是 maker 价优, 另一半是 45.48 % 的成交率。
- REV_SHORT 收据的逐年表: 原速 a=1 在 2026 年毛 +0.4356、盈亏平衡 0.3362。
本线在冻结前**只做过结构性计数**: 行数、去重、join 覆盖、锚偏移、类别计数。没有算过任何成交率、执行差、markout 或收益。

## §1 数据与装置(每件绑 sha256)

| 件 | 路径 | 用途 |
|---|---|---|
| 账本快照 | `T3/private/ledger_snap_20260913T0455Z/2026MMDD/{fills,orders,anchors,position_readback}.jsonl`, 拷贝于 2026-09-13T04:53:06–08Z | 成交、订单、锚中价 |
| r11 多滞后标记 | `uplift_2026-09-11/r11_costtruth/out/full/marks_multilag.json` sha256 `26ca67c969ec1e3f968c1506c61d0eb246b935317046519f401a38e86d5f58ac` | 描述性 markout 的价格源 P1 |
| 记账 meta | pod2 `/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz` sha256 `a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245` | y4(E)、qvk、members; E 至 2026-09-10 20Z |
| 5m 缓存 | pod2 `/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz`(sha 由导出装置记) | 只用于 E→锚运行起点那 20 分钟的回推, 且带裁剪守卫(门 G5) |
| 成本件 | `r3k_impact/costb_PWR_G230k.json` sha256 `295b4e7b…` | 分档边界(tier0 ≥ 5e6, tier1 ≥ 1e6) |
| trackB 行件 | `uplift_2026-09-11/trackB_realized_cost_rows.json` sha256 `8ae867eb3c1e47cf…` | 复现门 G1 的对照 |

**价格源的选择(为什么不用缓存算 markout):** 生产者缓存 `rolling.npz` 与 pod 缓存都只有 7 个通道(ret5/range/cpos/log_qv/log_cnt/log_avgsz/tbf), 没有价格水平通道; ret5 是 float16 且硬裁剪 ±0.30。markout 需要成交价之后某一时刻的价格水平, 用缓存只能从某个记录中价按收益链推, 会引入最多 5 分钟的错位, 且错位段落在成交之后, 与成交条件相关。r11 的 `marks_multilag.json` 是从 data.binance.vision 日度 aggTrades 归档算出的逐笔标记: 「T ≥ fill_ts + D 且 T ≤ fill_ts + D + 60 s 的第一笔 aggTrade 的价格」, 每个归档带 sha256(`archives.json` sha256 `dfe68e72…`)。它因果、不经裁剪、逐成交对齐。本线不重新拉取(无网络豁免)。

装置(全部在 `T3/devices/`, 运行前断言本文 sha256):
- `t3_export_pod2.py` — pod2 导出 meta 切片(E ∈ [2026-07-31 20Z, 2026-09-10 20Z] 的 E_ts / y4 / qvk / members)、缓存 ret5 按名切片(行 [2026-08-22 08:00Z, 2026-09-11 00:00Z])、符号轴(缓存 = panel = dlw 断言相等, 同 r21)。
- `t3_gate_repro.py` — 门 G1 / G2。
- `t3_markout_desc.py` — 描述性 markout(§4)与门 G3。
- `t3_passive_rev.py` — 主估计量(§3)、门 G4–G6、迁移诊断、判决。

## §2 门(先于任何新数字, 按顺序; G1 不过则停)

- **G1 账本读取复现(任务书指定, 不过即停):** 按 `trackB_realized_cost_2026-09-11.py`(sha256 `9eb531f4…`)逐字逻辑, 在快照上以 trackB 行件写出时刻 **T_cut = 2026-09-11T07:32:03Z** 截断重建账本状态(fills 行: 有 `backfilled_utc` 者取 ≤ T_cut, 否则取 `fill_ts` ≤ T_cut; orders / anchors / position_readback 行: `anchor_ts` ≤ T_cut)。去重规则用 trackB 自己的(键 `(symbol, trade_id)`, 保留带 `mid_at_fill_plus_60s` 的行)。
  通过条件: 与行件 243 行的 `ts` 集合相同; 逐行 `traded_notional` / `fee_usdt` / `adv_cost_usdt` 的 |Δ| ≤ 1e-6 USDT, `mo_cov` 的 |Δ| ≤ 1e-9; 批评者聚合 `round(−Σadv/Σtraded·1e4, 4) = −2.6573` 且 `round(100·#(markout60>0)/#finite, 1) = 27.5`(即 72.5 % 不利)。
  不过 ⇒ 输出逐行差异表, **停止一切新统计量**, 先报差异。
- **G2 去重规则对照:** 同一截断状态上, 执行器 `collapse_supersedes`(按 `trade_id` 末行胜, 文件位置即时序)与 trackB 规则选中的行, 在 `mid_at_fill_plus_60s` / `fill_notional` / `commission` 上不同的 trade 数; 报两规则下的 −2.6573。另报快照全量(不截断)的原始行数 → 折叠后行数。只报, 不门。
- **G3 价格源 P1 对账(只管辖 §4 描述性 markout):** 折叠后 maker 成交中, P1 的 60 s 标记与账本记录的 `mid_at_fill_plus_60s` 选中同一笔 aggTrade(`mark_ts` 相差 ≤ 1 ms)的份额 ≥ 99.0 %, 且名义加权 60 s markout 之差 |Δ| ≤ 0.10 bps。不过 ⇒ §4 照报并标红, 不影响 §3。
- **G4 计划构造对账:** ERA2 窗内, 每个计划的 maker 腿成交名义(折叠后 fills 求和)与 orders 同计划 maker 行 `filled_notional` 之和, 总额相对差 ≤ 0.5 %; 计划 `mid_at_anchor` 与 anchors 行 `mid_at_anchor_vector[symbol]` 逐位相等的计划份额 ≥ 99 %。不过 ⇒ §3 停, 先诊断。
- **G5 回推守卫:** 回推所用 4 根 bar 中任一根非有限或 |ret5| ≥ 0.2999 的计划剔除并计数; 剔除额占 R1 意图名义 > 5 % ⇒ 写进局限, 不停。
- **G6 恒等式:** 逐计划 `s·(F/P_E − 1) ≡ a + b + s·a·b`(a、b 见 §3.2), maxabs ≤ 1e-12(分数单位)。

## §3 主估计量: 被动反转书的有效每单位换手成本

### 3.1 计划(意图)总体
- **计划** = 账本中一个 `(rebalance_id, symbol)`。**入选** = 该组有 maker 行 `submit_ts` 非空, 或有 attempt-1 maker 行 `terminal_reason == venue_reject` 且 note 含 `-5022`(即 post-only 被拒, 后续走重挂或补单)。只有 `skipped_min_notional` / `blocked_by_halt` / 其它未发送 maker 行的组不入选, 按原因计数。
- **主窗 ERA2:** 锚运行起点相对 4 h 网格偏移 ∈ [22, 30] 分钟, 且 E = floor(anchor_ts/14400)·14400 ≤ 2026-09-10 20:00Z(meta y4 的上界)。实测对应 2026-08-22 08Z 起(该锚偏移 25.8 min, 其后 23.0 → 24.0)。**敏感性 ERA1:** 偏移 ≤ 3 分钟(2026-08-01..08-22 04Z, 140 名旧书), 单独报, 不参与判决。偏移落在两者之外的锚(08-01 06Z 150 min、08-02 92 min)剔除并计数。
- 逐计划量:
  - `s` = +1 买 / −1 卖(maker 行 `side`)。
  - `I` = 首个 attempt-1 maker 行的 |`intended_notional`|(maker 腿 = 整个 Δ, 见执行器 `_order_row` 注释)。同组多行不一致时计数并取最早一行。
  - `M_run` = 该 maker 行 `mid_at_anchor`(执行器锚运行起点的场所中价)。
  - maker 腿成交 = 折叠后 fills 中该组 `order_type == maker` 的全部行(首发与重挂都算): `N_f = Σ fill_notional`, `F = N_f / Σ(fill_notional/fill_px)`, 费 = Σ commission(BNB 行 × 同锚 `mid_at_anchor_vector["BNBUSDT"]`, 无则取时间最近有 BNB 的锚)。
  - `U = max(I − N_f, 0)`; `N_f > 1.02·I` 的计划计数。
  - `y4_E` = meta `y4[E, sym]`(记账口径 Π(1+r)−1, [E, E+4h], 未裁剪); 非有限则剔除并计数。
  - **E 价回推:** `P_E = M_run / Π_{j=1..K}(1 + ret5[E + 5j min])`, **K = floor(偏移/5 min)**(ERA2 = 4, 即回推到 E+20m 收盘 bar, 全部在锚运行起点之前, 与成交条件无关; ERA1 = 0 ⇒ P_E = M_run)。敏感性 K = round(偏移/5 min)(ERA2 = 5, 同 r21 主口径)。

### 3.2 估计量(冻结)
单位: bps / 单位意图换手。聚合 = 比值的和(分子分母分别在计划上求和)。

```
c_eff = [ Σ fee_usdt  +  Σ N_f · s·(F/P_E − 1)  +  Σ U · s·y4_E ] / Σ I      (×1e4 换 bps)
```
- 第一项 = 费; 第二项 = 成交部分相对决策价(E 收盘)的执行差, 含 E→锚运行起点的延迟; 第三项 = 未成交部分的机会成本, 按该名在本锚 [E, E+4h] 实际实现的收益计(AMENDMENT 1 第 3 条)。
- 为什么是这三项: 回放对每个意图记 `I·s·y4_E`(成交后权重乘整段 y4)。被动书只在成交部分拿到 `N_f·s·(P_{E+4h}/F − 1)` 并付费, 未成交部分什么都没有。两者之差按一阶展开正是上式。
- 报告的分解: `a = s·(F/M_run − 1)`(相对锚运行中价的成交价差), `b = s·(M_run/P_E − 1)`(E→运行起点延迟), 交叉项 `s·a·b`; 机会成本再拆成延迟部分与运行钟部分; 成交率 `Σ N_f / Σ I`; 子集自身的回放毛额 `Σ I·s·y4_E / Σ I`(与 P6 的 1.6 同量纲的对照)。
- 近似与它们会怎样错: 一阶展开丢掉 `s·(F/P_E−1)·y4_E` 的二阶项(报其大小); 未成交意图只按一个锚计机会成本, 不考虑下一锚重试(对 EMA a=0.5 持仓约 2 锚的形态偏保守还是偏乐观, 取决于第二锚的反转收益, 本文不测)。

### 3.3 反转方向分类(迁移的核心)
- **反转分数** 与 REV_SHORT 收据同定义: `score = −y4[E−4h]`(上一锚 [E−4h, E] 的收益, 在 E 已完全观测)。
- **可分类名:** `members[E]` 内, `y4[E−4h]` 有限, 且 `qv4h = expm1(clip(qvk[E], 0, 30))·48 ≥ 2.5e5`(REV_SHORT 的资格门, 收益有限性改用 E−4h 行以保因果)。
- `r̃ = rankdata(score)/(n−1) − 0.5`(同生产者 `xz`)。
- **R0** = 全部入选计划(无条件迁移)。
- **R1(主)** = 反转方向一致的计划: `s·r̃ > 0`(买上一锚输家, 卖上一锚赢家)。
- **R2** = 极端一致: `s·r̃ ≥ 0.3`(输家/赢家各最外五分之一)。
- **R1c** = 反转方向相反的计划(`s·r̃ < 0`), 作对照。
- 不可分类的计划计数, 只进 R0。

### 3.4 置信区间与判决(冻结)
- UTC 日块自举(按 E 的 UTC 日), 2000 次, `np.random.default_rng([20260905, k])`, 百分位 2.5 / 97.5; 同一族内各分量用**同一组**日索引联合重抽, 比值在每次重抽上重算。
- k 分配: R1 主 = 201; R0 = 202; R2 = 203; R1 剔除 `opening_halted` 锚 = 204; R1 剔除 `requote_arm == direct` 计划 = 205; R1 join = 206; R1 behind = 207; R1 tier0+1 = 208; R1 tier2 = 209; R1 买 = 210; R1 卖 = 211; ERA1 R1 = 212; R1c = 213; R1 以 K=round 回推 = 214。
- **判决规则(门槛引自 PROGRAM §2 T3 与 AMENDMENT 1 第 3 条, 逐字: 「反转书的活路门: 有效成本 CI 上界 < 1.6 bps/单位换手」), 施于 R1 主估计:**
  - CI 上界 < 1.6 ⇒ **PASS**(被动执行的有效成本低于 P6 盈亏平衡)。
  - CI 下界 > 1.6 ⇒ **FAIL**(有效成本以 95 % 置信高于盈亏平衡)。
  - 其余 ⇒ **UNDECIDABLE**, 报所需样本量: `n_days_req = n_days · (1.96·SE_boot / |c_eff − 1.6|)²`, SE_boot = 自举分布标准差; 点估计恰在 1.6 附近(|c_eff − 1.6| < 0.05)时写「点估计落在门上, 任何样本量都判不出」。
  - R0 / R2 / 其它切分只报, 不改判决; R2 与 R1 落在不同判区时必须在 RESULT 首段写出。
- **一句必须同页写的话:** 1.6 是 2022-06..2026-08 全史 EMA a=0.5 的盈亏平衡。REV_SHORT 在 2026 年原速盈亏平衡只有 0.3362。PASS 是必要条件, 不是充分条件。

### 3.5 迁移假设(先写下; RESULT 逐条给读数或写「不可测」)
| # | 假设 | 什么会让它失效 | 本线怎么查 |
|---|---|---|---|
| T-A1 | 反转书由同一台执行器执行: 运行起点 E+23/24 min、post-only、k_seconds 900(实际驻留 k+46 s)、placement ε 0.5 join/behind、-5022 后重挂(09-05 起 p 0.5 随机)、VIP0 + 当前 BNB 覆盖 | 换执行器、换驻留、换费率档 | 读 `config/book.json` 在役值写进收据 |
| T-A2 | 成交概率与成交条件下的价格路径只取决于名字、上一锚的走势与方向, 与是哪本书下的单无关 | 反转书把全部单同时压在极端涨跌名上: 自身冲击、与其他反转交易者抢队列 | 报 R1/R2 与真实反转书在 |r̃|、分档、方向上的换手分布差异(§3.6) |
| T-A3 | 每单位成本不随单子大小变化 | 反转书每锚换手 0.79–1.32 × gross, 约为在役书(0.1086)的 7–12 倍, 单子更大 ⇒ 冲击更大, 成交率更低 | 报 R1 按意图名义三分位的 c_eff; 超出样本范围的规模**不可测**, 写明方向是乐观 |
| T-A4 | 未成交意图按一个锚的实现收益计机会成本, 不重试、不补单 | 形态持仓 > 1 锚; 或补单比放弃便宜 | 报在役书 topup 腿实付(描述性, 同窗) |
| T-A5 | 20 个 UTC 日(2026-08-22..09-10)代表反转书将面对的状态 | 状态迁移; 2026 年反转 alpha 已衰减 | 报窗内 REV_SHORT 原速书自身的毛额/换手(§3.6) |
| T-A6 | 在役书的反转方向计划是反转书下单分布的无偏样本 | 在役书按资金费信号选名, 该子集的 |r̃| 分布、名字与反转书不同 | 同 T-A2 的分布对照 |
| T-A7 | 延迟与执行差用同一 E 钟计 | E 收盘价回推有 ≤4 分钟错位噪声 | K=round 敏感性(k=214) |

### 3.6 迁移诊断(只报)
在同一 ERA2 窗、同一 meta 切片上构造 REV_SHORT 原速书: 可分类名上 `w = r̃ / Σ|r̃|`(Σ|w| = 1), `Δw = w_E − w_{E−4h}`(上锚不可分类名 w = 0)。报: 每锚换手 Σ|Δw|; 窗内毛额 `Σ_E Σ_i w_E,i·y4_E,i / 锚数` 与每单位换手毛额; 换手名义在 |r̃| 五分位 × 分档 × 买卖上的份额; 与 R1 / R2 的意图名义在同一格上的份额对照(总变差距离)。

## §4 描述性 markout(保留原任务书的曲线, AMENDMENT 1 之后**无判决角色**)
- 总体: 快照上执行器规则折叠后的 maker 成交(`order_type == maker` 且 `venue_maker_flag == True`), `trade_id` 在 P1 中, 且 60 s / 5 min / 15 min / 1 h / 4 h 五个滞后状态全为 ok(平衡面板)。`protective_flatten` 剔除并计数; `topup_taker` 单列。
- `MO_F(D) = s·(P_D/F − 1)·1e4`, 负 = 对我方不利(与 −2.6573 同号约定)。`MO_M(D) = s·(P_D/M_sub − 1)·1e4`, `M_sub` = 父订单 `mid_at_submit`。**账本没有成交瞬间的中价**; `M_sub` 是成交前最近一次记录的场所中价(首发 maker 在挂单时刻, 重挂在重读时刻, 补单在发送前一刻)。逐成交恒等式 `(1+s·MO_M) ≡ (1+s·MO_F)(1+s·e_sub)`, `e_sub = s·(F/M_sub − 1)`。
- 另一列「到下一锚」: 价格 = 第一个 `anchor_ts ≥ fill_ts + 60 s` 的锚行 `mid_at_anchor_vector[symbol]`, 只取间隔 ∈ [3 h, 5 h] 者。
- 名义加权均值; 日块自举同 §3.4(按成交 UTC 日), 五个滞后与下一锚同族联合重抽; k: maker 全体 101、买 102、卖 103、首发 join 104、首发 behind 105、首发 106、重挂 107、topup_taker 108、成交名义三分位 109/110/111。首发 / 重挂: 同组存在 attempt-1 maker `venue_reject -5022` 行者为重挂, 否则为首发(结构审计: 带标记的 3,116 行全部有 -5022 同组行)。placement_arm 取首发父订单, 只 2026-08-12 起有值。
- 另报每个滞后「不利锚份额」: 按 `anchor_ts` 聚合的名义加权 markout < 0 的锚占比(与 72.5 % 同口径另报 ≤ 0)。
- **不下判决**: 原「4 h CI 下界 > −1.0 / 上界 < −2.0」规则按 AMENDMENT 1 撤回, 本节只报数。

## §5 产物
`T3/RESULT_T3_markout_curve_2026-09-13.md`(先写判据表再填数)、`T3/SHA256SUMS.txt`、`T3/receipts/{PREREG_FREEZE_sha.txt, PRE_RUN_ENV.txt, POST_RUN_ENV.txt, EXPORT_T3.json, GATE_repro.json, MARKOUT_desc.json, PASSIVE_REV.json}`、`T3/devices/*.py`。复跑命令逐字写进 RESULT。
