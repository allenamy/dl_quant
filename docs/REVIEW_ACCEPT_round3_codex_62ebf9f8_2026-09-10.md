# 独立研究员第三轮复审(62ebf9f8)· 辩证处置 + 第四轮修复

> **创建:** 2026-09-10 03:3xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第四轮修复已在两条复审分支落码(未合并未部署), 待研究员第四轮复核 | **作废条件:** 研究员第四轮复核出具后, 本文「已修」栏以其复核为准; 分支合并/部署另按验收裁定
> **复审件:** 研究员 worktree `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round3_review_2026-09-10/`(HANDOFF.md / RESULT.md / risk · executor · pipeline · account 四分册 + root 复执行; 提交 62ebf9f8)。**被审对象:** 实盘分支 d73b1b0(+3ff5e00 附加), 研究分支 fd50007c, 运行树 d040c74(研究员只读核验不变)。
> **研究员总判:** 多项修复有效, 仍有阻断; 暂不建议整体合并或部署。**我方总判: 同意, 且阻断项全部成立。** 下表逐项给出接受/收窄与证据; 第四轮修复对应到每一项; 未闭合的明写。

---

## §0 一句话

第三轮我把「UNKNOWN 请求」的上界写成了**意图减已知**(residual − known), 而不是**未决请求本身的数量**; 于是被拒的分块、没发出去的分块都被当成了「可能成交」的授权, 已知部分回填时还丢了卖出的负号, 已知与未知又双计。研究员用真实 broker/executor 生成行再喂给真实 reconcile → position_break → watchdog, 三组反例都让未授权仓位读成 CLEAN —— 这是**看门狗接受域被我的修复扩大了**, 比第二轮的缺陷更严重, 因为它是「修复」引入的。阶段 B 的「未在 allOrders 见到 ⇒ 成交 0」同样是我在 docstring 里断言、没有完整性证明的东西; 满 500 页(现 1000)时它就是错的。

**第四轮的形状按研究员 risk/REVIEW.md §2 的最小数量合同实现**: 每张真实请求一条账(id / 带号数量 / 终态 / orderId / 已确认数量), UNKNOWN 上界 = Σ 未决请求数量, 被拒/未发 = 0; 子成交按 orderId 身份结算, 只缩不扩, 超请求量 = 报不一致; reconcile 授权带 = 按名 Minkowski 区间 [L, U](合约数, 与 mark 无关), 区间外才用 mark 定价; 坏值一律不可测(异常, 非 CLEAN)。阶段 B: 满页 ⇒ UNKNOWN, 否则按自身 client id 查单, -2013 才是「未下达」; UNKNOWN 名写带请求量的 maker 行而不是留洞。

**没有任何一项让我们把「策略 alpha」或「已发表回测数字」判坏**(研究员本轮也未产生新收益结论; 28 书 + 2 参照 SHA 与上轮相同)。ic_monitor #55 的 DECIDE 处置与本文无关(用户 02:0xZ 裁定照常, 复核点 09-15 00Z)。

---

## §1 风险合同(risk 分册; R1–R3 P1 + 数值边界 + R7 P2)

| # | 研究员发现(真实 producer → RC/PB/WD 实达) | 我方复核 | 判定 | 第四轮修复(实盘分支 `review/b0a573a1-executor`) | 证据 |
|---|---|---|---|---|---|
| R1 | 买 100 分 50+50, 第一 50 未知, 第二 50 明确拒绝 ⇒ unknown 仍 100; 场所 +90 仍 5b/5e CLEAN(真正未决上限 50, 至少 40 未解释) | **VERIFIED**(封闭副本复现: 第三轮 `_rem = |residual| − |known|` = 意图减已知) | **接受, P1**。被拒请求「解释」了它没做过的事 | 补单腿逐请求账本 `request_ledger`: 每张真实请求 {client_id, qty(带号合约), notional_est, state ∈ not_sent/confirmed/unknown/rejected, order_id, confirmed_notional, confirmed_qty}; `ledger_totals` = 仅 unknown 请求入上界; 行列 `filled_unknown_qty`(合约) | 套件 [14]: 同夹具 ⇒ unknown_qty **50**, 场所 +90 ⇒ **anomaly 40**; +40 ⇒ 解释 |
| R2 | 已知卖 −50 + 未决卖 50, 收到第一请求 child fills ⇒ known 由 −50 变 +50; 合法 −80 报 BREAK, 反向 +20 CLEAN | **VERIFIED**(第三轮 `max(abs(_fn), abs(_prev))` 丢号) | **接受, P1**。「只抬下界」写成了「取绝对值」 | `_settle_leg_by_identity`: 按 orderId 联接子成交 → 该请求 confirmed(带号); 无账本的旧行走 `_sgn * max(|·|)` 保号 | 套件 [15]: 归属后 known **−50**; −80 解释 / +20 anomaly |
| R3 | 两个买请求各 50, 第一从未知回填为已知 50 ⇒ known 50 + unknown 仍 100(双计); 场所 +140 CLEAN | **VERIFIED** | **接受, P1** | 身份结算缩小 unknown 集(只对有 orderId 且子成交命中的请求); 全部请求结算才把腿关成 `filled`, 否则仍 `filled_amount_unknown` + 已知下界 | 套件 [16]: 归属后 known 50 / unknown **50**; +140 ⇒ anomaly 40; 第二请求 id 补齐后 ⇒ filled 100 关腿 |
| 合同 §2 | 授权带按 USDT 存、用 mark 换数量 ⇒ mark 1→1.1 合法 100 触 5e, 0.9 时超量 110 通过; 混方向 Σσr 对消; NaN/Inf/side None 通过为 CLEAN | **VERIFIED**(第三轮 `_band_usdt / mark`, `band[sym] += b`) | **接受**。数量是合同单位, USDT 是评价单位 | reconcile: `_unknown_interval` 买 [0,r] / 卖 [−r,0](合约); `_between` 按名 **Minkowski 相加** [L,U]; 残差 e = (ΔQ−K) − clip(ΔQ−K, L, U), 之后才乘 mark; 非有限数量 / 非有限已知部分 / side 非 buy·sell / 负价 ⇒ `unquantifiable`(execution_of_unknown_size 异常) | 套件 [17]: 买 50+卖 50 ⇒ ±40 解释、±60 异常; mark 1.1 持 100 解释、0.9 持 110 异常; NaN/Inf/side None/known NaN 四例全异常 |
| 合同 §2.1/2.2 | 新证据与旧界冲突须显式报; 已知部分应为带号数量, 名义/均价推数量须同一子集 | 同意(第四轮 a 版仍用 known_notional / avg_fill_px, 均价可能是最后一张请求的) | **接受**(第四轮 b 版) | 每张请求记 `confirmed_qty`(该请求自身 notional/avgPrice 恒等式); 行列 `filled_known_qty` = Σ; reconcile 优先取它; 子成交超请求量 ⇒ `ledger_inconsistent`(命名请求)⇒ 不可测 | 套件 [20]: 价 2 成 50U = 25 合约, 75 解释 / 100 异常; 60 合约对 50 请求 ⇒ inconsistent ⇒ 异常 |
| 合同 §2.4 | 未结请求应跨读数存在, 两次回读联合约束; 不能按 anchor_ts 一次消费后遗忘 | 同意。当前实现: 带只在含该行时间戳的窗口生效, 下一窗**不再**用它(不会重复解释), 但也不会去结算它 | **部分接受, 未闭合(明写)**。方向是 fail-closed: 晚到的成交在下一窗会读成未解释(可能误触发), 不会被隐藏 | 未做。需要「跨进程未决请求账本 + 下锚按 client id 查终态 + 追加修正行」, 触及 orders 只追加的账本形状与消费者(reconstructed 行与原 UNKNOWN 行的双计), 是预注册项 | 登记于 HANDOFF 第四轮 §未闭合 |
| R7 | 冻结 `_trade` L1835–1857 实跑: target NaN 保留进 planner ⇒ lot floor ValueError(整锚死); cap NaN 但 target 有限 ⇒ 按未校验 cap 规划 | **VERIFIED**(代码读: 第三轮只页不弹) | **接受, P2**。第三轮的「这些名未截断其余照常」在 target/held 非有限时是假话(整锚会死) | 规划前: field=target 且 held 有限 ⇒ target := held(delta 0 ⇒ skip 行, 不发单); held 非有限 ⇒ 弹出; **cap 非有限但 target 有限 ⇒ 仍不截断只页**(改成拒绝交易该名是书行为改动, 场所 -2027 是兜底; 归用户) | 套件 [18] wiring; 电池 tests_venue_cap_clamp 22 绿 |

## §2 执行器身份(executor 分册; EX-R3-1…4)

| # | 研究员发现 | 我方复核 | 判定 | 第四轮修复 | 证据 |
|---|---|---|---|---|---|
| E1 (P1) | 阶段 B: maker POST 未知 + −2013×2 + cancel −2011 后, 成功空 allOrders **或满 500 条无本请求**都得 `unknown=[]`, 原 maker 记 0, 再 POST 完整 10; 正控(终态 10)只发一次 | **VERIFIED**(`fill_details_for` HTTP 成功即 reached, 无页完整性; `_scan_orders` 无本 RID 成交即省略) | **接受, P1**。第三轮 absent→live 的修复**依赖**这个旧接口, 我在 docstring 里写「a never-placed order is simply absent there ⇒ filled 0」是没有完整性证明的断言 | `venue_fills`: limit **1000**(场所最大), 满页记 `_LAST_FULL_PAGES`; `_scan_orders` 记匹配到的 client id; 新 `settle_ambiguous_legs`: 对 `submit_ambiguous` 且 id 未见于 allOrders 的计划 —— 满页 ⇒ UNKNOWN; 否则 `GET /fapi/v1/order?origClientOrderId` —— 查到 ⇒ 其事实(含 0 成交), **−2013 ⇒ 未下达(0)**, 其它 ⇒ UNKNOWN; anchor_loop 把 UNKNOWN 并入 unknown_fills; `topup` 对 UNKNOWN 名写 maker 行 `filled_amount_unknown`(带 `filled_unknown_qty` = 所发数量)而非留洞 | 套件 [18]: 满页 ⇒ UNKNOWN 且 0 次 GET; 非满页 −2013 ⇒ absent 0; 查到 10 ⇒ 10; 查询失败 ⇒ UNKNOWN; UNKNOWN 名 maker 行 bounded |
| E2 (P1) | 平仓同秒重试复用 CID(prefix 按 UTC 秒, chunk 编号每次从 1); 第二请求按同 CID 查到第一次 order771, 两收据都记 −5/771 | **VERIFIED**(`flatten_all` `f"{prefix}-{s}-{_i}"`) | **接受, P1**。第三轮新功能引入的身份缺陷 | broker 进程内 `_flatten_seq` 计数, 不随符号/重试重置 | 套件 [19]: 同秒两次 ⇒ `…-HUSDT-1` / `…-HUSDT-2` |
| E3 (P2) | orderId 命名空间是 symbol; `int(orderId)` 作键 ⇒ BTC/ETH 同 id=77 被判冲突, ETH taker 费进 maker 桶, n_unattributed=0 | **VERIFIED** | **接受, P2** | `submitted_order_legs` / `order_legs_from_venue` / `attribute_trades` 全部 (symbol, orderId) 键; 冲突记录带 symbol | 套件 [19]: BTC/ETH 各自成腿, 无冲突, ETH 费落 ETH topup |
| E4 (P2) | `[:36]` 与「never truncates」注释相反: 15 字前缀 + 19 字符号 ⇒ 两分块同 id; 普通 maker/requote/topup 同 | **VERIFIED**(注释是我写的, 错) | **接受, P2**(防御边界) | 补单 `client_id_for` 超 36 ⇒ **拒绝**(该名记 abandoned_max_attempts 不发, 不中断循环); 平仓 ⇒ 弃 id 记 `client_id_dropped`(保护动作不因记账阻塞, orderId 仍是联接键) | 套件 [19]: 超长 ⇒ ValueError; 普通 id 不变 |
| EX-R3-4 表 | 无 TIF 回退只把 `-1` 当 maker(`-2` 重挂误分); `startswith(RID)` 无分隔符 | 同意(极低可达: RID 定宽 10 位纪元; 回退只在 allOrders 无 timeInForce 时) | **接受**(第四轮 b 版) | 回退 `-1`/`-2` 皆 maker; 全部读者 `startswith(RID + "-")` | 套件 [20] |
| 跨进程 UNKNOWN | `_pending` 不落日志, complete_anchor 从内存取计划, 上一锚已终结的未知请求不会被自动回收 | 同意(第三轮 HANDOFF 已披露) | **接受为披露, 不称闭环** | 未做(与 §1 合同 §2.4 同一项) | — |

## §3 账本(account 分册; A2–A4)

| # | 研究员发现 | 我方复核 | 判定 | 处置 |
|---|---|---|---|---|
| A2 | 平仓 3,095 笔真实费 **116.37847565**(3,094 非零 USDT + 1 零 BNB), 243 名名义逐名相等; 我方补录工具门算 `abs(正 fee + abs(负 income))` ⇒ 差 232.757 ⇒ 正确数据也拒 | **VERIFIED**(我 01:2xZ 已自查到同一缺陷并改比幅度; 用改后的门完成写回 02:16:00Z, 收据 reconciled/applied true; 工具修正入库 76d2d431) | **接受**; 门确实拦了一次错的写回(它该做的), 但错的是门 | 已修 + 已用; 研究员要求的「正费用/负收入、零费非 USDT、少一笔、重复一笔、错币种/错订单」拒绝用例 —— 工具是一次性脚本, 用例以其 dryrun 收据形式保留; 不再有第二次平仓补录时再套 |
| A3 | 12Z 新重建 52 行/fee 0.50724168 正确; 旧交付文件 fee 1.00970085; 新行放进冻结 M4 仍 `float(None)` 崩 | **VERIFIED**(旧形状 order_type=maker 下 m4 崩; 改 `reconstructed` 类型后, 冻结 `pilot_metrics` 现有 `order_type in ("maker","topup_taker")` 过滤即排除, **模块字节未动**) | **接受**; 旧交付件已用新工具再生(76d2d431) | 52 行写回**等实盘分支部署**(现网 pilot_log 不认新类型); 分支套件 [12] 证 m1/m3/m4 排除、reconcile 按量计入 |
| A4 | `by_type_asset`/`non_usdt_assets` 只到 broker 返回层; anchor_loop:2661 / reprice_day:164 仍只持久化混单位 `by_type` | **VERIFIED** | **接受为披露, 不称闭环** | 第四轮 a: daily_nav + reprice_day 持久化 `realised_by_type_asset` + `realised_non_usdt_assets`(可见性); **汇率换算未做**; 本账户 3,095 笔中非 USDT 费 = 0 BNB(研究员数, 我方未独立复算 → INFERRED) |

## §4 管线(pipeline 分册; P1–P2)

研究分支 `review/b0a573a1-pipeline` 第四轮由并行代理实施(判官逐臂身份绑定 / 链钉门源码 self_sha / require 全依赖登记 / RAW 参照全轴+有限+整数时戳+schema / f0fac5e3 收据来源 / 快照 22); 结果与提交见 HANDOFF 第四轮 §PIPELINE(其提交完成后补写于此: **已完成(并行代理, 提交 dcb01bcb → f4ba8765, 已推送; `tests_pipeline_gates` 65 → 117/117 本地 + pod2 117/117)**: r4-1 判官资格按臂经 `v4_gate_common.require` 绑定身份(`JUDGE_ELIGIBILITY`), `JUDGE_EXPORT_GATE` 降为只供参考的弃用别名(任意 `{PASS:true}` 不再 PROMOTE); r4-2 `require` 强制 `self_sha=`, 三条链运行时从所调门脚本算 sha 钉住门源码(合法但错误来源 SHA ⇒ rc 3); r4-3 `REQUIRED_INPUTS` 逐门必报输入登记(漏报 ⇒ rc 3); r4-4 RAW 参照先于复现验全冻结轴 3168 锚 + 有限 + schema + 整数秒时戳(两参照只 60 锚 / 重复 3167 / +.25 秒 ⇒ rc 2/3); r4-5 找回产生 G1 run-1 FAIL 收据的改前平价门 `v4e_gate_parity.r0_f0fac5e3.py`(sha 与收据相符), 清单工具拒绝 sha 不符映射, 快照计数更正 22→23; 研究员 `extra_checks.py` 12 例翻 10(2 例原已正确)、`audit_faults.py` 36 例 35 同 + 1 翻。**未闭合(其 HANDOFF R4 明写)**: 归档里没有门写 `BUNDLE_export` 收据(导出器只打印 PASS/FAIL), `chain_king_e.sh` 不传 `JUDGE_ELIGIBILITY` ⇒ 今日真实判官运行只能是参考态(与「v4e 非候选」一致, 新门 `v4e_gate_export.py` 未建); 15 份旧 schema 收据无 self_sha; pod2 现网 `v4_gates/*.json` 仍旧 schema。自报: pod2 同步时 ssh 引号错误跳过了 `.pre_r4` 备份步, 备份事后自 fd50007c 重建并逐 sha 核对(HANDOFF R5)。)。

## §5 研究员「五个重点」的回答 → 我方回应

1. **USDT/mark 授权带可否先接受? 研究员: 不同意。** 我方: 同意研究员。第四轮按 §2 数量合同实现, USDT 只在区间外定价。
2. **absent 等到阶段 B 只是多等 15 分钟? 研究员: 不同意这个读法。** 我方: 同意。阶段 B 原接口没有逐请求终态与完整性证明; 第四轮给了(满页/查单/−2013 三态)。仍未证: 场所在 k 窗后对一张从未接受的请求返回 −2013 是否终局(我们按终局处理; 请研究员判断是否需要第二次查询或更长等待)。
3. **所有 CID 消费者已适配? 研究员: 部分。** 我方: 第四轮补 E2/E3/E4 与回退/边界; **上一锚已终结未知请求的回收仍未做**(见 §1 合同 §2.4)。
4. **bounded vs unquantifiable? 研究员: 方向合理, 当前实现不接受。** 我方: 同意。现按请求合同给区间; 「区间相容 ≠ 已独立对账完成」在 reconcile 输出里以 `authorised_band_qty` + `residual_qty_raw` 并列保留, 不写「解释」二字。
5. **已披露未完成项如何读? 研究员: 接受披露, 不转成闭环。** 我方: 同意。income 缺行恢复未做; 币种换算未做; 跨进程未决账本未做 —— 三项在 HANDOFF 第四轮 §未闭合逐条列出, 不作为「风险接受域」的前提。

## §6 我方承认的新错误(第三轮引入, 供错题集)

1. **把意图当授权**: 第三轮 `_rem = |residual| − |known|` 用整笔意图定义未决上界 —— 恰是研究员第二轮警告过的「不要按 USDT/意图补大额度」。修复引入的缺陷扩大了看门狗接受域, 比它修的缺陷更危险。
2. **「只抬下界」写成取绝对值**: `max(abs, abs)` 丢卖出负号; 同一行注释说的是「raise the lower bound」。
3. **无证明的完整性断言**: `_settle_order_post` docstring 写「absent there ⇒ filled 0」; allOrders 的默认/最大页与「返回最近订单」的合同就在官方文档里, 我没读。
4. **注释与代码相反**: `[:36]` 旁写「always fits without truncation」。
5. **测试断言了错误合同**: 第三轮套件 [6] 把 unknown=10(意图减已知)写成期望; 第四轮改 5 并把原因写进断言文字。绿电池只证明代码等于我当时的理解。
6. **orderId 当全账户唯一**: 官方 Query Order 合同写明按 symbol 自增。

## §7 第四轮提交与验收状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第四轮 a(R1–R3 / 合同 / E1–E4 / R7 / A4 / 套件 [14]–[19]) | `review/b0a573a1-executor` **82e0cbf** | 132/132 全绿(safe_commit 20260910T030124Z) | 已推送, 待复核 |
| 实盘分支 第四轮 b(合同 §2.1/2.2 known_qty + inconsistent / `RID-` 边界 / `-2` 回退 / 套件 [20]) | **0d30095** | 132/132 全绿(safe_commit 20260910T031xZ) | 已推送, 待复核 |
| 研究分支 第四轮(管线) | `review/b0a573a1-pipeline` dcb01bcb…f4ba8765(6 提交) | tests_pipeline_gates 117/117 本地 + pod2 | 待复核 |
| HANDOFF | `docs/HANDOFF_round3_b0a573a1_closure_2026-09-10.md` 新增「第四轮」两节(研究分支) | — | — |

**协议不变**: 研究员第四轮复核 → 两仓分别合并 → 是否部署/何时部署另按验收裁定(用户字)。运行树 d040c74 本轮零接触(VERIFIED: `git -C ~/dl_quant_live rev-parse HEAD`)。

## §8 数字标签
- §1–§3 「研究员发现」列的数字来自其 RESULT/分册(VERIFIED by them, 我方封闭副本复现的标 VERIFIED); 套件计数 VERIFIED(本机运行); 电池计数以 safe_commit 日志为据; 「非 USDT 费 = 0 BNB」INFERRED(研究员数)。
