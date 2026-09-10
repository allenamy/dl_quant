# HANDOFF · 2026-09-09 全日完整转述(给独立研究员复审)

> **创建:** 2026-09-09 23:4xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 复审中(两条分支已推送, 主树未动, 书 23:22Z 已复场) | **作废条件:** 两条分支分别合并后本文降为历史记录; 若 00Z 复场锚看门狗再触发, §2 末段与 §5 需重写
> **配套:** `docs/HANDOFF_round2_b0a573a1_closure_2026-09-09.md`(§0–§5, 逐项技术细节)· `docs/PREREG_king_clock_E_2026-09-09.md`(+AMENDMENT 1/2/3)· `multi_asset/exports/live/pilot_journal/journal_2026-09-09_anchors.md`(逐锚原始记录, 只追加)· `STATE.md` 横幅
> **数字标签:** 每个数字带 VERIFIED(收据可查)/ INFERRED(由收据推出)/ UNRESOLVED(未证)。回测类数字本文不引用。

---

## §0 一句话状态与复审对象

- **实盘**: 2026-09-09 16:45Z 看门狗保护性平仓(E-0909-G, 非市场事件, 见 §2), 23:22:53Z 按用户字复场, **00Z 锚(00:24Z 执行器)从零重建全书** ≈232k gross。运行树 `~/dl_quant_live` main = **d040c74**(E-0909-D 修复, 14:07Z 入主树, 电池 129/129), 之后未动。
- **复审对象(两条分支, 分别复审, 分别合并, 合并 ≠ 部署)**:
  | 仓 | 分支 | 提交(相对基线) | worktree | 内容 |
  |---|---|---|---|---|
  | 实盘 `dl_quant_live` | `review/b0a573a1-executor` | **961a858 → e1c4c87**(基 d040c74; 9 文件 +812/−51) | `~/dl_quant_live_wt/b0a573a1` | 执行器 UNKNOWN/幂等加固 + E-0909-E 有限上限截断 + **E-0909-H 收入账本去重键** |
  | 研究 `quant_research` | `review/b0a573a1-pipeline` | **ca7c5816 … 6d894476**(基 multi-asset-v2; 12 提交) | `/Users/haosiyu/Desktop/quant_research_wt/b0a573a1` | v4 链失败阻断加固 + E-0909-F king 时钟一致性(G1–G4)+ HANDOFF round-2 §0–§5 |
- **协议(用户 09-09 15:4xZ 定)**: 修复在分支 → 独立研究员复核 → 通过后分别合入研究主线 `multi-asset-v2` 与实盘 `main` → **部署(pull 进运行树 + 电池全绿)是另一个决定** → 是否重训 / 换装 bundle / 重启执行器另按验收裁定。两仓分别复审、分别合并。
- **你的权限边界(与 09-06 ONBOARDING 同)**: 实盘书零接触 —— 不下单、不撤单、不改运行树、不改生产者 `~/wide_shadow`; 只读签名 GET 可用但**只在锚窗外**(锚 00/04/08/12/16/20Z: 生产者 N+16 写文件、执行器 N+24 起交易至 ~N+57 收尾, 故 HH:00–HH:57 全段禁用), 批量 ≤4 req/s; 凭证由 `live/envfile.py` 从仓库根 `.env` 读取, 本文只给路径与变量名的出处, 不给值; worktree 里 `.env` 是指向运行树的符号链接(git 忽略)。pod2: `ssh -p 55572 root@157.157.221.29`, `/workspace/venv/bin/python`, 脚本在 `/workspace/review_scratch/`。

---

## §1 你上一轮复审(b0a573a1)六项的处置结论(全部接受, 全部落码)

| # | 你的发现 | 我方处置 | 落点 |
|---|---|---|---|
| P1-EXEC #1 | 下单 POST 应答丢失后可能重发 ⇒ 重复成交风险 | **POST 任何非定论失败一律不重发**; 只按 clientOrderId 查场所记录: 存在→采纳; -2013 两次(间隔 `ORDER_QUERY_PAUSE_S`=1.0s)→记「未发」; 其余→歧义(视为可能在挂) | live 961a858 `_settle_order_post` |
| P1-EXEC #2 | HTTP 5xx / 200 非 JSON 被当作「未执行」 | `_execution_unknown`: 5xx 或非 JSON 应答 = **执行未知**, 走歧义路径 | 同上 |
| P1-EXEC #3 | 重挂/补单把 UNKNOWN 成交当 0 | 重挂歧义 = 在挂(不重发); 补单保留已确认块, UNKNOWN 永不写 0, 新列 `filled_known_notional` / `filled_unknown_residual` | 同上 |
| P2 | 崩溃收尾一个计划失败拖垮全部 | 收尾逐计划独立 try + `rows_failed` 计数 | 同上 |
| P1-PIPE / R4 / R7 / P1-REGEN | 门失败不阻断子链; 生成器覆盖真基底 | `v4_gate_common.finalize/require`(收据含输入 sha, FAIL 退 3, require 只认 PASS+新鲜 sha); `chain_lib.sh` 按 PID 等分片 + `check_marker` + `die`; 判官必需臂/覆盖 3168/A0p 复现容差 1e-6(退 2/3); 生成器 `BUNDLE_BASE` 与 `GEN_*` env 参数化, 从真基底逐位再生 | research 620db83c |
| P1-CONTRACT | king 特征训练窗 [E−w, E−1] vs 生产 [E−w+1, E], 标签 [E, E+47] vs 生产 [E+1, E+48] | E-0909-F: 新构建器 `pod_fea_ext_e.py`(窗止于 E, 标签 [E+1,E+48]); **G1 平价门 PASS**(生产 `wstat` AST 逐字提取, 六锚, 阳性对照 ≥1000 格); G2 导出守卫 **FAIL by rule**; G3 信息读数四格 (C); G4 量化 | research ca7c5816 … 85a0eb70 |

**你的 URLError 夹具**: 我方判定为合成场景, 但原则(请求相/应答相分相处理)已采纳进 d040c74 与 961a858; 请用你的 `audit_transport.py` 对 961a858 重跑六场景。

---

## §2 2026-09-09 时间线(UTC; 全部 VERIFIED, 收据在 journal 同时刻节)

1. **12:24–12:34Z · E-0909-D 执行器崩溃**。12Z 锚 `submit_maker` 内 SSL 握手超时未被捕获, 进程死于**任何 orders 行落盘之前**; 场所已落 66 笔成交(income 行)+ 4 张孤儿 GTX 挂单(CLO/ANKR/CHZ 于 13:36–14:01Z 成交, HUSDT 14:16:33Z 用户字后手动撤, exec 0)。用户发现「此时此刻有五笔委托」。
2. **14:07Z · 修复入主树 d040c74**(电池 129/129): `VenueTransportError` 分相位(请求相有界重发 `TRANSPORT_RETRY_MAX`=3, 退避 0.5/1.5s; **应答相 POST 只查不重发**), `submit_maker` 记 transport 行 + 熔断 `SUBMIT_TRANSPORT_ABORT_N`=5, `submit_with_cleanup`(撤在飞 → 补行 → CRITICAL 页 → 原样重抛), `run_anchor._page_phase_crash`; 新终态 `transport_error` / `skipped_transport_outage`。套件 `tests_transport_resilience`(主树 69 项; 分支 89 项)。
3. **14:3xZ · 12Z 记账回填**(用户字「确保无误按照最佳路径实施」): 69 条 fills 行按 income 逐分对账回填(Σ fee 0.5072 = 场所; gross 2,536U)。读账本时注意: fills.jsonl **每笔两行**(原行 + 16:48Z markout 回填写的 `supersedes_trade_id` 行), 所以该 rid 现为 138 行、fee 合计 1.0145, 折叠后仍是 69 笔 / 0.5072(09-08、09-09 所有 rid 同样 2×, 家族「fills 重复 trade_id」)。**未回填 orders 行**(该 rid 零行) —— 这是 §4 第一条错误的起点。
4. **E-0909-E · 场所有限上限拒单**: PIEVERSEUSDT 20x 名义上限 2,000U, 持 1,890, 目标 ≈2,330 ⇒ -2027 六锚连续拒单无主; 处置 = 账本 gap 具名 `venue_cap_usdt/venue_cap_names` + 处置尺子第五次重标定(带退役条款)+ `_trade` 按名 HIGH 页(主树 d040c74); **候选截断 `clamp_venue_cap`**(缩不放、签号保持、cap 0/无配置不动, `VENUE_CAP_MARGIN`=0.02)在分支 961a858, `_CAP_CLAMP_DEPLOYED_TS=None` 部署时填。套件 `tests_venue_cap_clamp` 22 项。
5. **15:0xZ–16:0xZ · 你的复审六项接受并落分支**(§1)。E-0909-F 链在 pod2 跑(§3-D)。
6. **16:24–16:57Z · 16Z 锚 = d040c74 首锚**: phase A/B/C 三行齐, `transport` 键 {transport_error 0, ambiguous 0, aborted False}, 扫单 CLEAN, 无 Traceback, -2027 按名页送达; orders 471 行(skipped_min_notional 175 / partial_expired 169 / venue_reject 59 / filled 47 / no_chase 21), fills 去重后 288(maker 187 / topup 101, maker 占比 0.649, Σ 13,579U, 费 2.82 bps); anchor done rc=0 16:56:54Z。**修复路径在首锚零异常。**
7. **16:45:36Z · 🛑 E-0909-G 看门狗触发**(锚内阶段 C 后): §4-5b 9 名仓位异常 + **§4-5e 仓位断裂 split_unauth 3,951U = 目标 gross 232,746 的 1.7%, 其中未授权 1.09%** + §4-7。**更正(2026-09-10, 复审 31fa3e4e A4)**: §4-5e 由**逐名未授权门**触发(任一名的未授权量 ≥ 该名自身 min_notional; 本次 50+ 名), **整书线 `PB_UNAUTH_PORTFOLIO_FRAC=0.05` = 5%, 1.09% 未越过**; 原文「1.09% vs 线 0.05」把百分数与比例并排, 读作越线是错的。未授权名单 = 12Z 崩溃锚的成交名。机制: `reconcile._between` 的 expected_qty = qty(T1) + Σdq **只从 orders 行授权**, fills 行不算 ⇒ 12Z 那批成交在账本里无授权 ⇒ 4 小时后触线。动作(执行器自动): halt_opening → flatten 243 张 reduce-only(16:45:37→16:47:20Z, Σ 232,757U)→ HIGH 页 16:47:23Z DELIVERED; reduce_only + open_orders_halted。
   - **平仓代价(VERIFIED)**: 账本 avg_fill_px vs mid_at_submit 名义加权滑点 **4.14 bps ≈ 96U**; 场所 income 窗内 COMMISSION 3,049 笔 / 240 名 / **−114.77U = 4.93 bps**; 合计 ≈211U ≈ 9.1 bps/gross ≈ 0.18% NAV(INFERRED 相加)。同窗 REALIZED_PNL −1,210.75U 是仓位盈亏兑现, 不是执行成本。
   - **账本缺口再现**: 243 张平仓行 `fee_paid` 全空, fills.jsonl 该窗 **0 行**(场所 3,049 笔)—— 与你上轮登记的「平仓锚 fills 缺失」同族; daily_nav(按 income)与看门狗(按场所复读)不受影响。
8. **17:1xZ · 修复件**: `pilot_journal/tools/reconstruct_orders_12Z.py` 从场所 allOrders 按 `A1788956640-` 前缀重建 **52 条** orders 行(全 FILLED, Σ 2,536U, note=RECONSTRUCTED_FROM_VENUE, 意图字段 None), 52/52 过架构校验; 在看门狗同一代码路径(copytree → `watchdog_inputs.collect` → `watchdog.run(MockBroker)`)的账本副本上 tripped **True→False**。干跑收据 `pilot_journal/e0909g_repair_dryrun_2026-09-09.json` + 行文件 `e0909g_reconstructed_orders_12Z_DRYRUN.jsonl`。**未落盘**(等字)。
9. **20:24–20:42Z · 20Z 锚(停机首锚)**: orders 236 = blocked_by_halt 231 + skipped_min_notional 5, fills 0, 复读 236 名全 0 仓, rc=0; 锚内看门狗 **tripped=False**; `LIVE_MODE=LIVE ops/resume_from_trip.sh --check` = **RESUMABLE**(「no condition currently fires, and none was blind」)。机制: 平仓阶梯 243 行是有授权的 orders 行, 最新对账锚 T1 = 平仓后全 0 快照 ⇒ §4-5e/§4-5b 条件自行清零 ⇒ **52 行重建不再是恢复前置, 降为账本真值项**。新页: per_name_stop XANUSDT 由保护性平仓完成出场 → 7 天禁入(至 09-16 20:39Z)。更正(23:5xZ 复核): XAN 自 ≥04Z 起就在 per_name_stop 的 `stopped` 名单(逐名止损 flatten_only 出场中, 04Z/08Z/16Z phase_C 均记 stopped=[XANUSDT]), 12Z/16Z 另被场所列 add_blocked(maxNotionalValue=0); 保护性平仓把它的仓位归零, 20Z 评估按条款「已停名平仓 → 进冷却」写入。禁入表 12 名(EGLD 09-10 08Z … XAN 09-16)。
10. **21:5xZ · E-0909-H 收入账本缺陷**(§3-B)。分支 e1c4c87, 电池 131/131 绿。
11. **23:22:53Z · 用户字「恢复！」→ 复场**: `resume_from_trip.sh` 四步: 硬门无条件触发、`conditions_blind=[]` ✓(「无盲区」仅指 blind 字段为空; 同一评估 `conditions_partial=[cond2_day_loss, cond4_drawdown]`, 复审 31fa3e4e A4 更正) → 证据隔离 `state/live/watchdog/quarantine/state_20260909T232253Z_resumed.json` → 移除 `watchdog/state.json`(harvest_ema.json 本就不在)→ 「no halt/reduce-only state remains」✓。核对: 场所挂单 0、仓位 0、钱包 116,127.98; 00Z launchd 作业在。脚本自述: **若下一锚看门狗再触发 = 原因未修, 不得重跑 resume**。00Z 锚结果由监视器与每锚深查补记(本文写作时未到 00:24Z)。

用户批评(原话要旨, 23:2xZ): 「为什么又犯这种错误了! 又要损失上百美金的一次性建仓成本! 不要再犯任何这种低级错误了, 非常失望!」

---

## §3 复审对象逐项(改了什么 / 怎么证的 / 请你看什么)

### A. 实盘分支 961a858 · 执行器 UNKNOWN/幂等 + E-0909-E 截断(详 round-2 HANDOFF §1)
- 改动: `live/binance_broker.py`(`_settle_order_post`, `_execution_unknown`, `VenueTransportError(..., resolved=None)`, `ORDER_QUERY_PAUSE_S`), `live/binance_executor.py`(重挂歧义=在挂; 补单保留已确认块; 收尾逐计划; `clamp_venue_cap`), `scheduler/anchor_loop.py`(E-0909-E 截断接入计划器, +82 行: 场所 `symbolConfig.maxNotionalValue` 有限上限, 715/897 名在 20x 下 cap 2,000–5,000U, NAV×2 时 1% 权重 ≈2,300U ⇒ 常设约束; 只缩不放, cap 0 仍走 withheld 路径), `live/tests_transport_resilience.py`(69→89 项, 含真 `do_open` 夹具 [P1]–[P6]), `live/tests_venue_cap_clamp.py`(22 项), `tests_disposition_matrix.py`(-2027 类退役条款: `_CAP_CLAMP_DEPLOYED_TS` 为 None 时跳过, 部署后其后锚 -2027 残差必须为零, 历史行不改写)。
- **请看**: (1) `absent` 判定边界: -2013 两次之间 1.0s 是否足以覆盖场所写入延迟(UNRESOLVED, 我方无场所延迟分布数据); (2) 歧义=在挂后, 下一锚 `stale_order_sweep` 是否必然覆盖该 clientOrderId(我方: 是, 扫单按 openOrders 全量); (3) 截断 `clamp_venue_cap` 只缩不放的方向是否有反向风险(持仓超 cap 时缩到 cap 是减仓动作, 请核 reduce-only 语义)。

### B. 实盘分支 e1c4c87 · E-0909-H 收入账本去重键过粗(详 round-2 HANDOFF §5)
- **事实(VERIFIED, 只读)**: 20Z daily_nav 行 `realised_by_type` COMMISSION −5.54 / REALIZED_PNL −685.54 / FUNDING −87.04; 场所分型分页汇总 COMMISSION **−125.69**(4,219 行)/ REALIZED_PNL **−696.74**(3,496 行)。用主树 d040c74 的 `BinanceBroker.income_since(day_start)` 直接跑, 逐位复现账本三数(5,351 行, truncated=False)⇒ 不是分页截断。3 秒窗 134 行 / 67 tranId / **67 个 tranId 各含 COMMISSION 与 REALIZED_PNL 两种 incomeType** ⇒ 同一笔成交两行共 tranId, 只按 tranId 去重丢第二行。方向系统性: 只少记亏损。
- **影响面**: cond2 日损判据自 [B32] 起 = 权益日变化(`watchdog.py` L983; L1262-1268 的 realised+unrealised 视图已退役为只记录), 止损判决未读错数; 受影响 = daily_nav 实现盈亏分解、报表、guard_twin 的 arith 项; M6 资金费账本走 `binance_funding.py` 自己的分页(只取 FUNDING_FEE), 不经此函数(请确认)。
- **修复**: 键 `(tranId, incomeType, symbol, asset)`; 无 tranId 回退整行。套件 `live/tests_income_twin_rows.py` 11 项: 平仓日复刻(3,049 笔 × 2 + 248 funding, 50 行/毫秒, 7 页)/ 旧键阳性对照 / 翻页复送仍一次 / 无 tranId 回退 / 小页重叠幂等; **同一套件对主树模块跑 3 项变红**。三件套登记(SUITES + `ops/gate_coverage.py` 盲区自述)。
- **请看**: (1) 用你自己的方式取一个短窗确认「一笔成交 = 两行同 tranId」; (2) 是否存在第三种共享 tranId 的行型; (3) asset 入键对多币种手续费的正确性; (4) 部署后历史 daily_nav 行不自动重算, `ops/reprice_day.py` 按日重算路径由 `tests_reprice_day` 覆盖 —— 是否需要对 09-09 重算一次。

### C. 研究分支 620db83c · v4 链失败阻断(详 round-2 HANDOFF §2)
- 归档 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`: `v4_gate_common.py`, 加固后的 `v4_gate_closure/step1/step2.py`, `stable_trend.py`, `judge_v4.py`(A1e 臂, `JUDGE_OUT/JUDGE_HC` env, 必需输入), `make_v4_scripts.py`(`GEN_*` env, `BUNDLE_BASE` 行), `chain_lib.sh`, 重写的四条链驱动, `tests_pipeline_gates.py`(21 项, pod2 ALL PASS `receipts/tests_pipeline_gates_pod2.log`), 真基底 `base_pod_f10_train_monthly_earlystop.py` / `base_pod_f10_refit_ext.py`, 快照 `*.r1_*/r2_*/r0_bb7f14ac`(每个收据配它当时的源码)。同步收据 c12c60dc(`receipts/v4_scripts_sha_full.json`, 17:1xZ 更新): 清单 75 脚本, 50 件与 pod2 逐位、0 件不同、r1 快照 6 份; 加固脚本与 E-0909-F 装置 17:0xZ 同步 pod2(提交信息记 23 件)。
- **请看**: `chain_lib.sh` 的 `run_shards` 对 4 个分片的 PID 等待是否覆盖你复现的「子进程失败未传到父链」; 生成器从真基底再生的三份脚本 sha 是否与你手上的一致(55ee8382 / ea3675b8 / c210bac6 前缀)。

### D. 研究分支 ca7c5816 … 85a0eb70 · E-0909-F 训练—生产特征一致性(详 round-2 HANDOFF §3 + PREREG_king_clock_E)
- **G1 平价门 PASS**(run-2): 新构建器 vs 生产 `wstat`(从只读生产者副本 AST 提取, sha 记录)六锚 80 列 float16 逐位: float32 通道差异格 0.009–0.047%(≤0.1% 线), float64 参照 0 格; 阳性对照(旧构建器 vs 生产)≥1000 格。**AMENDMENT 1**(run-1 FAIL 后): 参照的 float64 求和先转 float32 再排序 —— 这是参照伪影(两个实现都在 float32 上排序), 判据不变; run-1 收据保留 `G1_king_clock_parity_run1_FAIL.json`。
- **G2 导出守卫 FAIL by rule**: 2.26 < 带下沿 2.27(门②③绿)。**AMENDMENT 2**: 守卫书标签窗随 meta 变([E,E+47]→[E+1,E+48]), 带须在 v3 E 标签参照上重定基; 六格分解(`guard_decompose_v4e.py`, `GUARD_PANEL`=v3splice; 首跑误用 v2ext 面板不能复现 2.284, 已修): 标签窗非因(v3 −0.003, v4 +0.023), 预测效应 ±0.07 反号 = 守卫噪声; 重定基带 [2.267, 2.567] 仍差 0.007 ⇒ **FAIL 维持**。发现: 守卫带宽 0.3 vs 年化 Sharpe SE ≈ √(2190/5839) ≈ 0.6 —— 这是复现门不是判别门(已登记, 不改本轮判据)。
- **G3 信息读数(AMENDMENT 3, 不作候选)**: A1e−A1 动态 −0.041/−0.055、固定 +0.050/+0.052; A1e−A0 动态 +0.019/−0.007、固定 +0.055/+0.042; 四格 (C)「在本合同与窗内未检出差异」。
- **G4 量化**: float16 往返对 king 分数无影响(Spearman 1.0000, 顶十分位 100%); 时钟差一 bar Spearman 0.976–0.990, 顶十分位重叠 78–93% ⇒ 对齐是实质纠正(分数层), 但书层未转成可测净额。
- **结论**: 训练/生产合同可以同定义(G1 PASS 的构建器); **v4e 不具备换装资格**(G2 红); 若要把纠正带上线需 DL 全链重跑 + 换装预注册 + 用户字。
- **请看**: 六锚 G1 结果与你 `clamp_clock/FEATURES.npz` 的 live 数组对照; G4 是否支持「送 booster 前 float16 往返」作生产候选; `JUDGE_v4e_hardened.json` 四格与 56 个 CI 复算。

### E. 主树 d040c74 · E-0909-D(已部署, 供信息)
16Z 首锚零异常(§2-6)。**注意**: `submit_with_cleanup` 只保护未来崩溃; 12Z 这种历史缺口要从场所重建。

---

## §4 我方承认的错误(供你独立判断, 不替我们下结论)

1. **处置错误(造成平仓与重建, ≈400U 量级)**: 12Z 崩溃后我只回填 fills 行, 明知该 rid 的 orders 行为零(重建工具 docstring 明写), 却没有在 16Z 看门狗评估前(两小时窗)用看门狗自己的判定路径在账本副本上跑一次。验证方法就是后来证明修复件的方法。规则已固化(反馈记忆): 锚中途死第一步查 rid 的 orders 行数; 任何账本修补在下一锚前先在副本上过看门狗, 拿到 tripped=False 收据才算完成。
2. **E-0909-H 是 09-07 分页修复引入的粗键**: 修「一次请求截断」时用了比行更粗的去重键(tranId = 事务身份非行身份), 修一个截断制造另一个截断, 与 `tests_numerator_honesty` 自述的方向性错误同型。
3. **G1 run-1 参照伪影**(AMENDMENT 1, 判据不变)与 **G2 分解首跑误用面板**(不能复现已发表 2.284 才发现)—— 均已收据化。
4. **平仓阶梯 fills 缺失**是你上轮登记的家族, 本次再现; 尚无修复(protective_flatten 路径不写 fills 行), **未在本轮分支内**, 需要另开。

---

## §5 未决与不在本次范围

- **账本真值三件(等用户字, 不阻塞交易)**: ① 12Z 52 行 orders 重建 `--apply`; ② 平仓阶梯 3,049 笔 fills 只读回填; ③ E-0909-H 分支合并→部署(部署后 09-09 daily_nav 是否重算)。
- **长期盲区(HEALTHCHECK 09-06 §6 未变)**: factor_health UNKNOWN(影子监控报告不可读, episode 68f039b2); funding_span STALE(ours 140 vs venue 782, episode 80c1c1db); 限流差值归属; 划转日 cond2 盲区。
- **不在范围**: N+6 执行换装(Phase 2 条件 GO, 建议 offset 7, 排在执行器分支合并之后); 是否重训 / 换装 bundle(v4e 无资格; v4/v4s 候选见 RESULT_v4 与 CALIBER_STATUS)/ 重启执行器 —— 另按验收裁定。
- **00Z 复场锚**: 验收带 = phase A/B/C 三行齐, transport 0/歧义 0, 看门狗 tripped=False, realized_gross 进目标 ±5%, 复读非 0 仓 ≈ 目标名数, 无 §4-5e; 建仓成本预期 ≤ 平仓同量级。结果见 journal 09-10 节。

---

## §6 复核清单(命令级; 全部只读)

```bash
# 实盘分支(worktree 已配 .env 符号链接与 pilot_log 夹具)
git -C ~/dl_quant_live_wt/b0a573a1 log --oneline main..review/b0a573a1-executor      # 961a858, e1c4c87
git -C ~/dl_quant_live_wt/b0a573a1 diff --stat main..review/b0a573a1-executor         # 9 files
cd ~/dl_quant_live_wt/b0a573a1 && bash run_acceptance.sh                              # 131 套件, ~10 分钟, /usr/bin/python3 (3.9)
/usr/bin/python3 live/tests_transport_resilience.py   # 89
/usr/bin/python3 live/tests_venue_cap_clamp.py        # 22
/usr/bin/python3 live/tests_income_twin_rows.py       # 11; 对主树模块: PYTHONPATH=~/dl_quant_live/live 在别目录跑 ⇒ 3 项红
/usr/bin/python3 ops/gate_coverage.py                 # 131 套件全有盲区自述

# 研究分支
git -C /Users/haosiyu/Desktop/quant_research_wt/b0a573a1 log --oneline multi-asset-v2..review/b0a573a1-pipeline   # 12 提交
cd /Users/haosiyu/Desktop/quant_research_wt/b0a573a1/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09
/usr/bin/python3 tests_pipeline_gates.py              # 21(pod2 上 ALL PASS 收据在 receipts/)
# 收据: receipts/G1_king_clock_parity.json (+_run1_FAIL) · G2_closure_stable_hardened.json · G4_king_quant.json ·
#       guard_decompose_v4e.json (+_v2extpanel) · JUDGE_v4e_hardened.json · JUDGE_v4e_informational.json · align_v4e.json ·
#       export_v4e.log · v4_scripts_sha_full.json · tests_pipeline_gates_pod2.log

# 实盘账本(只读; 锚窗外)
~/dl_quant_live/state/live/pilot_log/20260909/{orders,fills,anchors,daily_nav,position_readback}.jsonl
~/dl_quant_live/state/anchor_runs.log                 # 注意 state/ 不是 state/live/
~/dl_quant_live/state/live/watchdog/quarantine/state_20260909T232253Z_resumed.json   # 触发状态原件
~/dl_quant_live/state/notify_audit.jsonl              # 16:47:23Z HIGH 触发页 / 20:39:02Z XAN 页
```

**主树不动的证据**: `git -C ~/dl_quant_live log --oneline -1` = d040c74; `git -C ~/dl_quant_live status --short -- live ops scheduler run_acceptance.sh` 空。

---

## §7 受据索引(提交号)

- 研究主线 multi-asset-v2(今日, 时间序): 82eebd97 / 3e76fb35(E-0909-D 定位)→ 21cccd93(d040c74 入主树记录)→ 8a768a94 / 5b8a7a1e(孤儿撤 + 12Z fills 回填)→ 6630b002(两分支推送)→ 7ff4be77(🛑 E-0909-G)→ fd7cfa3d(修复件干跑)→ ed8beb75(16Z 增量: 平仓代价)→ b30bd028(20Z: RESUMABLE 翻转 + E-0909-H)→ 4e5bbdf0(e1c4c87 收据)→ 9b8962be(23:22Z 复场)。
- 研究复审分支 review/b0a573a1-pipeline: ca7c5816(PREREG E)→ 8e7908e2(装置)→ 620db83c(失败阻断)→ a36f61d8 → 893f1461(G4)→ 776d7802(G1 run-1 FAIL + AMD1)→ c10660ce / 5d214260(G2 + AMD2)→ 298383f6 → 85a0eb70(G3)→ c12c60dc(pod2 同步收据)→ **6d894476**(§5 附录)→ 5f9b8f4b(本文初版)→ 1b606aaf(复核更正: XAN 机制 / 分支 anchor_loop 与 disposition 改动描述 / fills 每笔两行 / 锚窗口径)→ 本分支 HEAD(sha 清单计数更正)。
- 实盘: main **d040c74**; review/b0a573a1-executor **961a858 → e1c4c87**。
- 本文: 研究复审分支(与 round-2 HANDOFF 同分支)。
