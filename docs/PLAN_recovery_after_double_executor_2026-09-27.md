> **创建:** 2026-09-27 09:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(integ,lead 指派,只读起草) | **状态:** rev 1(09:2xZ):加入最终步骤单 §7 与 12Z 加查清单 §8;装置已离线测试,未对场所运行,没碰凭据,没联网 | **作废条件:** 旧机状态与本文假设不符;执行器运行树不再是 d01e35d;lead / 用户另行裁定

# 双执行器事故后的恢复方案(2026-09-27)

事故:2026-09-27 08:31:12Z,旧机(Intel,锁屏,launchd 照跑)上的 watchdog 用市价 reduce-only 平掉了整本书,clientOrderId 前缀 `F20260927083112`。本机 watchdog 于 08:47:50Z 跟着跳闸,平掉剩余约 2k。本文回答 lead 的四个问题,并给出一份按顺序执行的恢复步骤单(§5)。

所有数字都是**合池口径**(盲态纪律,不分臂)。收据在 `multi_asset/exports/research/recovery_2026-09-27/`。

## 0. 结论摘要
1. **本机的放行门现在已经是 RESUMABLE。**
   - 09:09Z,在隔离克隆上跑 `resume_from_trip.sh --check`:克隆 = 运行树 d01e35d + 当时 state 的完整拷贝,sandbox-exec 禁网、生产目录不可读。
   - 结果:所有条件都未触发,也没有盲区。
   - 原因是本机 08:47:50Z 的平仓阶梯写了**有授权的** orders 行,外加一份平仓后的回读快照;§4-5b / §4-5e 都是状态门,只看最近一次对账(M=1),所以触发条件已被本机平仓自己清掉。与 E-0909-G 同理。
   - **但这道门只看本机账本,看不见第二个执行者。** 它能放行,不代表可以放行。真正的前提是 §3 的场所收据和 §4a 的密钥轮换,这两件都要人来做。
2. **重建**:从 0 到约 21.5 万(2.0× NAV),按历史 3 次整书平仓后的重建:
   - 第一锚到目标的 62%–97%,最近一次(09-13 12Z)是 97%;第二锚 ≥98%。**1–2 锚建满。**
   - 成本约 **110–290 USDT**:
     - 下限按近 42 锚基线,手续费 2.77 + 滑点 2.28 ≈ 5.1 bps;
     - 上限按 09-13 12Z 重建锚,手续费 2.94 + 滑点 9.41 ≈ 12.4 bps。
   - 按今晨账户读数 NAV 约 107.9k 算,约占 0.10–0.27%。
3. **「整书平仓后 8–20 小时不再平衡」这次会咬,但方式不同。**
   - 这是 open_orders_halted 的设计行为:默认不交易,要人手动恢复。
   - 这次书是**全平**的,不存在持有过期书带来的漂移;代价是空仓期间放弃的期望收益。
   - 停机时长完全取决于 §3 和 §4a 多快做完。
4. **§9-F7 冷静期**(`eda/pilot_protocol_prereg.md` L499,`cooling_off_hours = 72`):到 **2026-09-30 08:47Z** 为止,不得起草协议 v2。
   - 用原参数复场**不属于**这条禁止项。
   - 但 §4 的类修法只能写成提案。
   - **十月 D10 发布窗(09-29 13:00Z)落在冷静期内**,它算不算「调参重启」,请 lead / 用户裁定。

## 1. 本机执行器的现状与放行条件
### 1.1 现状(实测,只读,09:0xZ)
`~/dl_quant_live/state/live/watchdog/state.json`:
- `reduce_only: true`,`open_orders_halted: true`;
- `tripped_at: 2026-09-27T08:47:50Z`,`flatten_ok: true`;
- `degradation`:stage1 平仓 1 次成功,stage1b 撤单时场所 0 张挂单,stage2 已告警;
- `resume_requires`:「a deliberate manual action — the default is now NOT TRADING. Per §9-F7 no protocol v2 may be drafted for >=72h」。
- 无 KILL_SWITCH.json。

`trip_receipt.json` 的触发原文(节选):
- §4-5b:最近一次对账锚上 310 个名位置异常(本窗历史共 326);
- §4-5e split_unauth:原始偏离 215,247 USDT,是目标 gross 214,728 的 100.2%,其中**未授权部分 100.75%**,线为 0.05。

本机账本今天的回读(合池,`pilot_log/20260927/position_readback.jsonl`):

| 回读 | 名数(非零) | Σ\|名义\| |
|---|---|---|
| 00Z 锚后(读于 00:44:56Z) | 315(314) | 216,428 |
| 08Z 锚后(读于 **08:46:44Z**,已在旧机平仓之后) | 317(70) | 2,073 |
| 平仓阶梯之后(读于 08:48:10Z) | 70(0) | 0 |

- 本机没有 04Z 锚(迁移中漏跑)。
- 本机 08Z 锚的 rebalance_id 是 `A1790497440`(644 行 orders);本机平仓为 `FLATTEN-20260927T084…`(70 行)。

### 1.2 `ops/resume_from_trip.sh` 的放行条件(逐条,出自脚本原文)
| 步 | 条件 | 这次的状态 | 旧机停下后会自然清掉吗 | 需要人工吗 |
|---|---|---|---|---|
| 0/4 模式 | 所要求的模式确实处于跳闸;若别的模式跳闸而本模式没有,则拒绝 | LIVE 跳闸 ✓ | — | 调用时必须带 `LIVE_MODE=LIVE`(否则默认 DRY_RUN,会被拒并点名 LIVE) |
| 0/4 路由 | 不是演练植入的停机(`_seeded_by_rehearsal`),否则改用 unseed 工具 | 不是 ✓ | — | 否 |
| 1/4 硬门 | 在账本**副本**上重跑 `WD.run(MockBroker)`,喂入与生产相同的 ops_stats / venue_events:① tripped 为假;② conditions_blind 为空;③ 不会有局部响应触发 | **全部通过**(09:09Z,收据 `GATE_CONDITIONS_clone_0909Z.txt`):§4-1、§4-2(最近已定价日 20260927,−0.77%)、§4-3、§4-4、§4-4b、§4-5(5b CLEAN,5e CLEAN,偏离 0)、§4-6、§4-7 都未触发,无盲区 | **已经清掉**,靠的是本机平仓阶梯 + 平仓后快照(见下) | 否,但见 1.3 |
| 2/4 | 把 state.json 复制进 quarantine,附上原因(不删除证据) | — | — | 要一句恢复原因 |
| 3/4 | 删除 state.json;harvest_ema.json 进 quarantine 后删除(整书平仓 ⇒ 不保留 EMA 记忆,下一锚从原始目标重新平滑) | — | — | 否 |
| 4/4 | 核实不再有 halt / reduce-only | — | — | 否 |

**lead 点名的两项:**
- **expected_qty 的基线**:
  - §4-5b 的对账是 `expected_qty = qty(T1) + Σdq(有授权 orders 行)`,拿它与 `qty(T2)` 比。
  - 现在最近的对账对是「08:46:44 回读 → 08:48:10 平仓后快照」。这一对之间只有本机平仓阶梯的有授权 orders 行,所以是 CLEAN。
  - 旧机那约 3,479 笔成交发生在「00Z 快照 → 08:46 回读」这一对里。那一对已经不是最近状态,只计入历史计数(326),不触发。
  - **所以 expected_qty 的基线不需要人工处理。**
- **split_unauth 的来源**:
  - §4-5e 以最近一次对账锚衡量书与意图的偏离。现在读数为 portfolio_dev 0,anchor 为平仓后快照,判 CLEAN。
  - 未授权部分的「来源」(旧机的单)**不影响放行**;但它影响**账本真值**,见 1.3 第 3 条。

### 1.3 门看不到、必须由人确认的(放行前提)
1. **旧机真的不再下单。** 门只读本机账本,第二个执行者在它眼里只是「未授权偏离」。一旦旧机再下单,下一锚本机 watchdog 会再次平仓。证明方法见 §3,根除方法见 §4a。
2. **轮换 API 密钥**(§4a)。
   - 两台机器共用同一个公网出口 IP 103.252.201.68,**交易所的 IP 白名单区分不了这两台机器**。
   - 在密钥轮换之前,「旧机已关」只是一个人工断言。
3. **账本真值(不是放行前提)**:
   - 旧机的 orders / fills 不在本机的 fills.jsonl 里。daily_nav 按 income 记,不受影响;受影响的是 fills 层的成本与费率统计,今天的会少记。
   - 修补分两步:
     - 旧机关机前(或断网启动后),拷出它的 `~/dl_quant_live/state/live/pilot_log/20260927/`、`watchdog/`、`state/anchor_runs.log` 作证据;
     - 用 E-0909-G 的做法(`pilot_journal/tools/reconstruct_orders_12Z.py` 同族),从场所 allOrders 重建为 `RECONSTRUCTED_FROM_VENUE` 行,并具名标注「外来执行者」。
   - 这一项不阻塞恢复,由 lead 排期。
4. **恢复当天全天禁止合约钱包转入转出。** 这是 live_stop_loss_2026_09_06 缺陷 2 的处置:有划转的一天记为未定价,§4-2 会回退到上一个已定价日。本文没有核实这个缺陷此后是否已修,按未修处理。
5. **iCloud 研究仓**:
   - 旧机开着时,iCloud 桌面仍在同步。旧机上写研究仓的作业(日志、仪表盘、journal 之类)可能把文件写进了本机看到的 `~/Desktop/quant_research`。
   - 恢复前在本机跑一次 `git status`,对 04:00–09:00Z 期间出现的非预期改动逐个认领。
   - 旧机的 pod2 ssh 作业(如果有)也要在 pod2 上核对。

## 2. 重新建仓:从约 0 到 2.0× NAV
**依据**:实盘账本里所有「上一锚 realized_gross < 1,000,本锚 > 1,000」的锚。
- 收据:`REBUILD_STATS_pooled.txt`,装置 `devices/rebuild_stats.py`。
- 用的是属主读取函数:`pilot_log.read_fills` 已经 collapse_supersedes。
- 合池口径。

| 重建 | 目标 gross | 第一锚到位 | 第一锚 taker 份额 | 手续费 bps | 滑点 bps(对下单时 mid) | 第二锚到位 |
|---|---|---|---|---|---|---|
| 09-07 04Z(§4-2 止损后) | 164,451 | 62.2% | 0.0% | 2.00 | −2.25 | 98.4% |
| 09-10 00Z(E-0909-G 后) | 232,259 | 66.7% | 0.0% | 2.00 | −2.91 | 98.2% |
| 09-13 12Z(E-0912-A 后) | 235,111 | **96.8%** | 31.4% | 2.94 | 9.41 | 100.4% |
| **近 42 锚基线**(09-19 16Z .. 09-27 00Z,正常调仓) | — | — | 25.6% | 2.77 | 2.28 | — |

- **一锚能建多少**:
  - 执行器对全书 delta 一次下单:maker 优先,加上 chase 50/50,chase 臂的残差用 MARKET 补。**执行器没有逐锚的建仓上限**,每锚都朝完整目标走。
  - 09-07 和 09-10 两次,第一锚只到 62–67%,taker 份额为 0;09-13 第一锚到 97%,taker 份额 31%。
  - 这一差异的原因**本文没有测**。三次重建都是 chase 50/50,方案同为 `chase_arm_v2`。有待查明的是 09-12 前后执行器的改动。
  - 在役执行器 d01e35d 比这三次都新,最接近的参照是 09-13。
- **要几锚**:1–2 锚。第一锚 62–97%,第二锚在三次历史里都 ≥98%。
- **成本**:目标约 214,728(08Z 锚的 target_gross)。
  - 按近 42 锚基线:(2.77 + 2.28) bps × 21.5 万 ≈ **109 USDT**;
  - 按 09-13 重建锚:(2.94 + 9.41) bps × 22.8 万 ≈ **282 USDT**,第二锚另加约 3.6 万名义,成本可忽略;
  - 区间约 **110–290 USDT**。
  - 滑点以下单时 mid 为参照,噪声大(09-07 和 09-10 为负);这只是量级,不是预测。
- **EMA 平滑**:恢复脚本会删除 harvest_ema.json,所以第一锚按原始目标下单,不会从 0 缓慢爬升。combo 的 kc/fc 状态在生产者侧,不受执行器停机影响。每锚照常产出目标,停机期间执行器写的是 blocked_by_halt 行。
- **会不会被「平仓后 8–20 小时不再平衡」咬**:
  - 会。它不是独立缺陷,而是 open_orders_halted「默认不交易、要人恢复」的设计。历史上 19 个锚被拦,都发生在人工恢复之前(记忆 halt_after_every_flatten)。
  - 这次书是全平的,不存在「持有一本不再调仓的旧书」带来的漂移;代价是空仓期间放弃的期望收益,本文没有估算。
  - 停机时长 = §3 与 §4a 的完成时间。每跨过一个锚,就多一个 blocked_by_halt 锚。
  - 若在 12:24Z 之前恢复,12Z 锚就开始重建。

## 3. 旧机不再下单的收据(只读查询,lead 在静默窗执行)
**先认清本机自己的单长什么样**(`live/rebalance_id.py` L53–60、`live/watchdog.py` L3068 / L3099):
- 锚单的 clientOrderId = `A<开跑秒>-<SYMBOL>-<k>`,开跑秒是 `int(now)`。今天本机 08Z 锚的前缀是 `A1790497440`。
- 平仓单的 clientOrderId = `F<YYYYMMDDHHMMSS>`,rebalance_id 为 `FLATTEN-<trip_key>`。
- ⚠ 两台机器都在 08:24:00 由 launchd 触发时,**开跑秒可能相同**,于是 clientOrderId 也会相同。交易所只要求挂单之间 clientOrderId 唯一。**所以归属必须按 orderId 判**,不能只看前缀。
- 本机下过的每一张单,其 orderId 都在 `orders.jsonl` 的 `request_ledger[].order_id` 里。

查询(全部为 GET 只读签名请求;时间窗 T0 = 2026-09-27T03:59:00Z,即 lead 拦截新机作业的时刻;T_off = 用户确认旧机断网的时刻):

| # | 请求 | 期望 | 说明什么 |
|---|---|---|---|
| Q1 | `GET /fapi/v1/openOrders`(不带 symbol) | `[]` | 此刻没有任何挂单(本机处于停机状态,不会挂单) |
| Q2 | `GET /fapi/v3/account`(或 positionRisk) | 所有 positionAmt 为 0,与本机 08:48:10 的平仓后快照一致 | 平仓后没有人再建仓 |
| Q3 | `GET /fapi/v1/income?incomeType=COMMISSION&startTime=<T_off>`(分页到底) | **0 行**;本机停机期间也不产生任何佣金 | 自 T_off 起没有任何成交。这是全账户的检测,不需要逐个 symbol 查。**这是「旧机不再下单」的主收据**,每锚前重跑一次,直到密钥轮换完成 |
| Q4 | 与 Q3 同,把 incomeType 换成 `REALIZED_PNL` | 0 行 | Q3 的旁证 |
| Q5(取证) | 先用 `GET /fapi/v1/income?incomeType=COMMISSION&startTime=<T0>&endTime=<T_off>` 得到有成交的 symbol 集合;再对每个 symbol 调 `GET /fapi/v1/allOrders?symbol=S&startTime=<T0>&endTime=<T_off>` | 把每张单归到三类之一:(a) orderId ∈ 本机 request_ledger;(b) clientOrderId 以 `F2026092708311` 开头,即旧机平仓单;(c) 其余全部。(c) 按 clientOrderId 前缀合池计数:`A17904824xx`(04Z)、`A1790497440` 但 orderId 不在本机(旧机的 08Z 锚)、其他 | 旧机在 04Z / 08Z 是否也跑了正常锚;若跑了,它对本机状态的影响范围有多大 |
| Q6(取证) | 对 Q5 的 symbol 集合调 `GET /fapi/v1/userTrades?symbol=S&startTime&endTime`,按 orderId 连到 Q5 的分类 | (b) 类的成交约 3,479 笔(lead 已计);(c) 类合池计笔数与名义 | 外来成交的规模。只报合池 |

- **判据**:恢复的前提是 Q1 为空、Q2 全 0、Q3 与 Q4 自 T_off 起为 0。Q5 和 Q6 是取证,不阻塞恢复。
- 频率与代价:Q3 按全账户分页,单次权重 30;Q5 按 symbol 逐个查(allOrders 权重 5),约 320 个 symbol × 5 ≈ 1,600 权重,分钟上限 2,400,要分两分钟跑。都放在静默窗里执行,并避开 N+24 到 N+29。
- **密钥轮换(§4a)做完之后,Q3 由「持续监视」降级为一次性核对。**

## 4. 类修法提案(不实施;§9-F7 冷静期到 09-30 08:47Z)
### 4a. 迁机时轮换 API 密钥(并把它写进迁移清单的硬前提)
- **缺陷的类**:「任何时刻只有一台机器在跑执行器」这条约束,只靠人断言「旧机已关」来保证。交易所能识别的只有密钥和 IP,而两台机器的 IP 相同。
- **修法**:
  - 迁移时,在新机上启用任何实盘作业**之前**,先在交易所新建密钥,绑定同一 IP 白名单,只开期货交易权限,写入新机 `.env`;再**删除旧密钥**。
  - 删除之后,旧机即使开着、launchd 照跑,下单也只会被拒(-2015)。
- **验收**:
  - 旧密钥调 `GET /fapi/v3/account` 返回 -2015;
  - 新密钥上的 Q1–Q3 通过;
  - 迁移清单里「轮换密钥」一项要带交易所的密钥列表截图或 API 回执,在「启用实盘作业」之前勾选。
- **这次也适用**:恢复之前先轮换一次。这是 §1.3 第 2 条。需要用户在交易所界面操作。

### 4b. 执行器锚前预检:「上一锚以来有没有我不认识的单或成交」
- **修法**:
  - 在 run_anchor 的 phase A 之前、任何下单之前,查询 `income(COMMISSION, startTime = 上一锚的 read_ts)`;
  - 把有成交的 symbol 用 userTrades / allOrders 取出 orderId,与本机账本(`request_ledger[].order_id` ∪ 平仓阶梯的 orders 行)比对;
  - 出现任何未知 orderId ⇒ **本锚 HOLD(不交易,不平仓)**,发 HIGH 页报,写一行具名的 `foreign_activity` 事件,列出合池笔数、名义和 clientOrderId 前缀;
  - 读不到(网络或权限问题) ⇒ 判为 UNKNOWN,同样 HOLD,不当作「没有」处理。
- **为什么是 HOLD 而不是平仓**:
  - 外来执行者也可能在平仓(今天旧机正是这样)。两边都平仓,只会放大成本。
  - 按 E-0912-A 的教训,对「我方看不懂的东西」做全书级响应是比例失当的。
- **配套 1:clientOrderId 带主机标签**。rid 改成 `A<开跑秒><主机短码>`,彻底消除两台机器的 id 碰撞,让外来单**按前缀**一眼可辨。需要同步改 §4-5b 的授权连接;授权现在按 client_id 与 orderId 两条连接,需要核查。
- **配套 2:watchdog 的归因**。§4-5b 能区分「外来执行者」(orderId 未知但场所自洽)和「我方账本缺行」,前者 HOLD 加页报,后者照现规。**这是书行为改动,需要预注册和用户裁定。**
- **验收(先写测试)**:
  - 合成场景:外来 orderId 出现在窗内 ⇒ HOLD 且不下单;
  - 本机平仓阶梯的单 ⇒ 不误报;
  - 读取失败 ⇒ HOLD;
  - 两台机器同一秒开跑 ⇒ 带主机标签后 id 不碰撞;
  - 回放:今天 08Z 的真实账本加上 Q5 的场所记录 ⇒ 预检在 08:24 本应触发(前提是旧机在 04Z 也下过单;这一点有待 Q5 证实)。
- 它能不能拦住今天这种顺序(旧机在 08:31 下单,而本机 08:24 的预检已经做完),**不能**。所以 4a 才是根除,4b 只防下一锚。

### 4c. 迁移清单的顺序约束(文档修正)
把「旧机断网,disable 旧机 launchd,旧机关机」和「轮换密钥」放在「启用新机实盘作业」**之前**,作为硬前提。今天的实际顺序是拦截新机作业 → 重建环境 → 05:01Z 重新启用,而当时旧机「是否已关」**未经证实**(迁移收据原话是「当时旧机是否已关尚不确定」)。

## 5. 建议的恢复步骤单(交 lead 定;每一步都报判词行和真实退出码)
1. 用户完成:旧机断网 → bootout 并 disable 全部 com.hsy.* 与 com.dlquant.* → 关机。若能在断网状态下启动一次,先拷出 §1.3 第 3 条的证据目录。
2. 用户在交易所轮换密钥(§4a);新机 `.env` 换成新密钥(lead 执行)。
3. lead 在静默窗(不在 N+24 到 N+29 之间)执行 Q1–Q4。**任何一项不符 ⇒ 停下,不恢复。**
4. 在本机 `git status` 认领 04:00–09:00Z 期间研究仓的非预期改动(§1.3 第 5 条)。
5. 在隔离克隆上重跑 `LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check`(装置 `devices/offline_clone.sb` 与 `devices/gate_conditions.py`),应为 RESUMABLE。
6. 恢复当天全天冻结合约钱包的转入与转出。
7. **用户字**:以原参数恢复,原因写成一句话(例如「双执行器事故:旧机已关机且密钥已轮换,Q1–Q4 于 <时间> 通过」)。然后执行 `LIVE_MODE=LIVE bash ops/resume_from_trip.sh "<原因>"`,期望 4/4 输出 ✓。
8. 下一锚:
   - 按标准首锚验收;
   - 另外核对:realized_gross 占目标 ≥ 60%;无 blocked_by_halt;Q3 在锚后仍为 0(只有本机的佣金行,orderId 全部 ∈ request_ledger);
   - 第二锚 ≥ 95%。
9. 事后:
   - Q5 / Q6 取证;
   - 旧机账本证据入库;
   - 用 `RECONSTRUCTED_FROM_VENUE` 行补记外来成交;
   - 在错题本立案;
   - §4 的提案在 09-30 08:47Z 之后按预注册流程起草。

## 6. 未知与风险(具名)
- 旧机在 04Z 和 08Z 是否也跑了正常锚,**未知**,要等 Q5。
  - 如果跑了:本机 08Z 锚开始时看到的持仓,已经被旧机 04Z 改过。本机按自己的回读规划,这本身自洽;但本机 04Z 的缺锚桥接只是状态桥接,与旧机下的单无关。
- 09-07 / 09-10 与 09-13 三次重建的第一锚到位率差异(62–67% 对 97%)的原因没测;§2 的成本区间因此偏宽。
- §4-2 的划转缺陷是否已修,本文没核实,按未修处理(§1.3 第 4 条)。
- 本文所有读数取自 09:0xZ 的 state 拷贝。12Z 锚会在停机状态下再写一轮回读和 blocked_by_halt 行;执行第 5 步时以当时重跑的结果为准。

## 收据
- `receipts/RESUME_CHECK_clone_0909Z.log`:`resume_from_trip.sh --check` 在隔离克隆上的全文输出,RESUMABLE,rc 0。克隆 HEAD 见 `RESUME_CHECK_clone_HEAD.txt`(d01e35d)。
- `receipts/GATE_CONDITIONS_clone_0909Z.txt`:同一评估路径的逐条件判词(装置 `devices/gate_conditions.py`)。
- `receipts/REBUILD_STATS_pooled.txt`:§2 的表格(装置 `devices/rebuild_stats.py`,运行树只读)。
- `devices/offline_clone.sb`:沙箱配置,禁网、生产目录不可读、只允许写克隆目录与系统临时目录。

---
## 7. 恢复步骤单·最终版(2026-09-27 09:2xZ,依据用户裁定 ①②③)
- 用户裁定:① 轮换 API 密钥,由用户操作,新密钥只写入新机 `.env`;② 前提齐备就以原参数复场,赶得上 12Z 就从 12Z 开始,否则 16Z;③ D10 顺延到 09-30 13Z 窗。§4 的类修法 a–d 在 09-30 08:47Z 之后再预注册。
- 以下 `DEV` = `/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/recovery_2026-09-27/devices`,`RCP` = 同目录下的 `receipts`。
- **截止时间**:第 8 步必须在 **12:20Z 之前**完成,12Z 才能交易;否则顺延,第 8 步在 16:20Z 之前完成,首锚改为 16Z。任何一步都不要在 N+24 到 N+30 之间做。

| # | 谁 | 做什么(命令) | 期望 | 不符时 |
|---|---|---|---|---|
| 1 | 用户 | 旧机:断网 → `launchctl bootout` 并 `disable` 全部 com.hsy.* / com.dlquant.* → 关机。报出**断网时刻 T_off**(UTC,精确到秒) | 用户口头或书面确认,附 T_off | 不往下走 |
| 2 | 用户 | 在交易所界面:新建 API 密钥(只开期货交易,禁止提币,IP 限定 103.252.201.68)→ **删除旧密钥**。报出轮换时刻,并截图密钥列表(只剩新的一把) | 截图入库 | 不往下走 |
| 3 | 用户(lead 核对) | 用户把新密钥写进 `~/dl_quant_live/.env`:只换 `BINANCE_KEY` 和 `BINANCE_SECRET` 两行,其余保留;然后 `chmod 600`。lead 不经手密钥,只核对指纹:第 4 步首行打印的 `KEY fingerprint sha256[:10]` 必须**不等于**旧实盘密钥的指纹 `88d264fe14`。`~/.quant_readonly.env` 是另一把单独的只读密钥(指纹 `f952dbea01`),不在这次轮换范围内,研究侧拉取器不受影响(lead 09-27 核实) | 指纹已变 | 指纹仍为 88d264fe14 ⇒ 不往下走 |
| 4 | lead | 在静默窗执行 `/usr/bin/python3 $DEV/venue_readonly.py q1q4 --t-off <T_off> --out $RCP/Q1Q4_<UTC时刻>.json` | 首行 `KEY fingerprint sha256[:10] = …` 不等于 `88d264fe14`(旧密钥);末行 **`VENUE_Q1_Q4 PASS`**,rc 0 | FAIL(rc 1)或 UNKNOWN(rc 2)⇒ **停,不恢复** |
| 5 | integ | 认领研究仓在 03:59Z 之后的未提交改动 | **已完成(09:22Z)**:只有 lead 的 `ACCEPT_08Z_1790496000_arm64_first.txt` 和 integ 的恢复装置,没有来路不明的写入(收据 `REPO_UNCOMMITTED_TOUCHED_after_0359Z.txt`)。第 8 步前再跑一次 | 出现来路不明的文件 ⇒ 报 lead |
| 6 | lead | `bash $DEV/recheck_clone.sh`:新建隔离克隆 + 完整 state 拷贝,在沙箱里跑 `resume --check` 和逐条件判词 | 末行 **`RECHECK RESUMABLE`**,rc 0;tripped False,无 blind,5b 与 5e 都为 CLEAN。09:23Z 实测已是如此 | NOT_RESUMABLE ⇒ 停,交 lead |
| 7 | 用户 | 今天全天冻结合约钱包的转入与转出(§1.3 第 4 条) | 用户确认 | — |
| 8 | lead(以用户字为前提) | `cd ~/dl_quant_live && LIVE_MODE=LIVE bash ops/resume_from_trip.sh "双执行器事故 09-27 08:31Z:旧机于 <T_off> 断网关机、旧密钥于 <T_rot> 删除;Q1–Q4 于 <时刻> PASS;克隆 --check RESUMABLE"` | 依次出现:`✓ LIVE is the tripped mode` → `1/4 … ✓ no condition currently fires …` → `2/4 … -> …/quarantine/state_<stamp>_resumed.json` → `3/4 removed …/state.json`,以及 `removed …/harvest_ema.json`(整书平仓,不保留 EMA 记忆)→ `4/4 ✓ no halt/reduce-only state remains` → `✓ resumed (reason: …)`;rc 0 | 任何一步 ✗ ⇒ 脚本自己拒绝、不改状态;交 lead,**不要重跑到绿** |
| 9 | lead | 恢复后立即只读核对:`python3 -c "import os;print(os.path.exists(os.path.expanduser('~/dl_quant_live/state/live/watchdog/state.json')))"` | `False` | 交 lead |
| 10 | lead + integ | 首锚:N+30 之后按 §8 的加查清单执行 | §8 全部通过 | 按 §8 的处置 |

## 8. 12Z 首锚加查清单(16Z 同理,A 换成 1790524800)
在 lead 的标准首锚验收(inspect_anchor / VERSION_PROBE / M3_SELFCHECK / parity / B4_POOLED / report / watchdog)之外,加查以下几项:

| # | 查什么 | 命令 | 判据 |
|---|---|---|---|
| K1 | **外来 orderId = 0** | `/usr/bin/python3 $DEV/venue_readonly.py anchor --anchor 1790510400 --out $RCP/ANCHOR_1790510400.json`(N+30 之后,静默窗内) | `n_foreign_order_ids == 0`。窗口 = [rid − 600 s, 现在],范围是有佣金行的所有 symbol。归属按 orderId ∈ 本机 `request_ledger` 判;没有记 orderId 的本机行(平仓阶梯)才按 clientOrderId 判。所以即便两台机器同一秒铸出相同的 rid,外来单仍会被判为外来(已有测试) |
| K2 | **建仓到位率** | 同上(`fill_ratio_realized_over_target` = anchors 行的 realized_gross / target_gross) | **≥ 0.60**(装置判据);参照区间 0.62–0.97(§2)。第二锚(16Z)另查 ≥ 0.95 |
| K3 | **taker 份额**(合池) | 同上:`taker_share_venue_pooled`(userTrades.maker)与 `taker_share_ledger_pooled`(fills.venue_maker_flag)两边都报 | 只作描述,不作门。参照:近 42 锚 0.256,09-13 重建锚 0.314。两边相差 > 0.05 ⇒ 具名记下(说明账本与场所口径不一致) |
| K4 | 没有被停机拦下的行 | 同上(`blocked_by_halt_rows`) | == 0 |
| K5 | 看门狗没有再次跳闸 | 读 `state/live/watchdog/state.json` 是否存在,以及 `ALARM.log` 的末行 | 不存在 state.json;锚内的 watchdog `tripped=False` |
| K6 | 旧机依然静默 | 重跑第 4 步的 `q1q4`,T_off 不变 | Q1 可以有本机的挂单(chase 阶段结束后应为 0);Q3/Q4 的行数 = 本机本锚的成交所产生的行。这一项由 K1 按 orderId 覆盖,**以 K1 为准** |
| K7 | 成本 | `/usr/bin/python3 $DEV/rebuild_stats.py ~/dl_quant_live` 的 REBUILD 行 | 只作描述,参照 5.1–12.4 bps |

- **VENUE_ANCHOR 的末行**:PASS(rc 0)= K1、K2、K4 全部成立;FAIL(rc 1)列出失败项;UNKNOWN(rc 2)= 查不到,**不等于通过**。
- **处置**:K1 > 0 ⇒ 立即交 lead,视为第二个执行者仍在;K2 < 0.60 ⇒ 交 lead,不自动处置;下一锚会继续朝目标建仓。
- **装置测试**(离线、禁网、无凭据):`tests_venue_readonly.py` **ALL PASS**,收据 `TESTS_venue_readonly.txt`。覆盖:只读白名单拒绝下单路径、Q1–Q4 各自的红格、翻页边界不丢行也不重复计数、真实相同的两行都保留、读取失败判 UNKNOWN、收据不覆盖、外来单即使 clientOrderId 与本机相同仍被判为外来、平仓行按 clientOrderId 认领、到位率与停机行的红格、userTrades 页饱和判 UNKNOWN。
- `local_ledger` 已在真实账本上离线跑过(00Z / 08Z 两锚,rid 能找到,本机 orderId 共 1,437 个)。**这两个装置从没对真实场所跑过**;第一次联网运行就是第 4 步,由 lead 执行。
