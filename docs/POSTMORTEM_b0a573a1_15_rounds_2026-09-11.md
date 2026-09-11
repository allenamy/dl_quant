# POSTMORTEM · 复审 b0a573a1 十五轮(执行器请求事实模型)· 合并收据 · 量化影响 · 再犯预防

> **创建:** 2026-09-11 02:2xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 代码已合并远端(实盘 `origin/main` = **b681ca5**; 研究 `multi-asset-v2` = d8fcba06 + 本文提交), **未部署**(运行树 d040c74; 部署 = 用户裁定后按 `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`) | **作废条件:** 部署后首锚验收出具后 §4a 由部署后对照替代; Q6 落码后 §5 重写
> **研究员第十五轮(工作树 b6ad2c40, `codex_round15_review_2026-09-11/RESULT.json` 01:15Z, VERIFIED 读原文):** verdict **APPROVE_CODE_MERGE_ONLY**; new_confirmed_P1 **0**; remaining_R14_blockers **0**; checks 396 / full_chains 26 / consumer_readbacks 80 / cost_cases 37(35 对照不变)/ primary_identity_checks 378; merge_executed false, deployment_executed false; limits: 无独立 132 套电池、无场所/API/schema/生产进程认证、Q6 与部署积压仍开、合并建议不含生产检出更新或自动部署、**无 alpha 或利润提升主张**。我方接受全部, 按其建议执行(§1)。
> **前十四轮处置:** `docs/REVIEW_ACCEPT_round{2..14}_codex_*.md`; 事实表 `docs/DESIGN_request_fact_model_2026-09-10.md`; 交接全史 `docs/HANDOFF_round3_b0a573a1_closure_2026-09-10.md` §EXECUTOR 第三 → 第十五轮; Q6 合同 `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md`。

---

## §0 一句话

十五轮改的是**执行器在故障路径上对「场所到底做了什么」的记账真实性**, 不是策略。在过去三天 12 个真实锚上, 新旧代码的每一个可比数字逐锚相等(成本诊断 12/12; 看门狗 42 日副本 0 差)—— **正常态零差**。差别只存在于反例夹具覆盖的**异常态**: 旧码在那里会把未知写成 0、把拒单当授权、用错配快照造均价、把 2⁵³ 附近两个订单号合并; 新码在那里报未知、拒绝造数、按事实带区间给风控。它**不改变**任何回测数字、任何收益预估、任何在役书权重; 它改变的是「异常时账本能否被相信」这一评价前提。没有收益改善可主张, 也不主张。

---

## §1 合并收据(VERIFIED 02:04Z)

| 件 | 前 | 后 | 方式 |
|---|---|---|---|
| 实盘远端 `origin/main` | d040c74 | **b681ca5**(19 提交, 27 文件, +5,098 / −280; 提交内无 `state/` 文件) | 从复审工作树 fast-forward push(`review/b0a573a1-executor:main`), **未经运行目录** |
| 实盘运行树 `~/dl_quant_live` | d040c74 | **d040c74**(HEAD = main; 代码文件零改动; 落后 origin/main 19) | 零接触(研究员建议: pull/merge 在运行目录 = 上线) |
| 研究主线 `multi-asset-v2` | c9b438ad | **d8fcba06**(no-ff 合并 `review/b0a573a1-pipeline` 3603ad6d)+ 本文提交 | 已推送 origin |
| 自动拉取 | — | **无**: 从 `~/dl_quant_live` 执行的 5 个 launchd 作业(anchor / anchor_report / backfill_markout / notarize_ledgers / ic_monitor)无一 `git pull`; `ops/safe_commit.sh` 只在**运行目录里被调用时** fetch + rebase ⇒ 下一次在运行目录跑 safe_commit 就会把 b681ca5 一并带入 = **隐式部署**, 部署前禁在运行目录 safe_commit(RUNBOOK §0) | VERIFIED(plist + 脚本逐读) |
| 复审工作树 | `~/dl_quant_live_wt/b0a573a1`, `quant_research_wt/b0a573a1` | 已删(分支 `review/b0a573a1-executor` / `-pipeline` 保留作历史指针); 研究员工作树 `codex-independent-20260907` @ b6ad2c40 未动 | `git worktree remove` |
| 中间文件 | 7 份旧码红检副本 `r9_red…r15_red` ≈ 1 GB(scratch) | 已删(scratch 2.2 G → 1.2 G); 研究仓无本轮数据文件(改动只有 docs / STATE / journal, VERIFIED `git diff --name-only 478c5b50..HEAD`) | — |

**「正确逻辑全面生效」靠什么(不靠记忆)**: (a) 远端 main = b681ca5, 任何新克隆 / pull / safe_commit 的 rebase 都拿到新逻辑; (b) 逻辑被 378 项 `tests_request_identity_unknown` + 13 套更新套件 + `ops/gate_coverage.py` 盲区自述锁住, 回退任何一格电池红; (c) 运行树何时切换只剩一个动作(RUNBOOK §1), 前提五条写死; (d) STATE.md 首行 + 每锚深查新增「运行树 HEAD vs origin/main」一项, 落后就报。

---

## §2 十五轮到底改了什么(27 文件; 按层, 不按轮)

| 层 | 轮 | 改动(合同) | 主要位置 |
|---|---|---|---|
| 传输与身份 | 09-09 E-0909-D/E + 复审 1–3 | 下单 POST 任何非定论失败**永不重发**, 只按我方 clientOrderId 查场所记录; 5xx = 执行未知; UNKNOWN 永不写 0; 收尾逐计划容错; 有限上限截断 | `binance_broker._request` / `_settle_order_post`, `binance_executor` |
| 请求账本 | 3–6 | 每张请求一条记录 {Q, L(已确认下界), F(数量终值), T, N, N_final, N_lower, inconsistent}; 余量 = F ? 0 : Q − \|L\|; 拒单 / 未发 = 确定 0; 看门狗读区间(Minkowski 和); 阶段 B 满页 ⇒ UNKNOWN; 先撤后查 | `binance_executor` 请求账本, `reconcile._exec_qty`, `venue_fills.settle_ambiguous_legs` |
| 方法: 事实表 | 7 | 事实 × 来源 × 出口, 每格一测; 读者在行发出时**最后重算**, 分支不能改列 | `DESIGN_request_fact_model` §1–§4, `_order_row` / `ledger_row_columns` |
| 来源 → 记录集合 | 8–9 | `merge_order_records`: 派生只在同一快照内、C / N 单调、终态常量; 撤单回包 / 提交回包 / allOrders 行入同一集合; 身份门管事实; 每个 UNKNOWN 出口先折叠已有记录 | `binance_broker.merge_order_records` / `_snapshot`, `venue_fills._records` / `_carry` |
| 完整性类型 | 10–12 | 数量(F/L)与金额(N_final/N_lower)各自证明; `_final_known` 无 terminal 回退; 有场所事实的 maker 行带账本; 子成交只抬下界; 合同 §3f.6「金额已知数量未知 = [0, Q]」; 读者只认完整性字段(DESIGN §5 全表) | `_final_known`, `ledger_known_qty`, `_settle_leg_by_identity` |
| 表示与边界 | 13–15 | 身份字段四态(缺 / 畸形 / 值)一个实现贯穿三处门; orderId 可接受输入合同(int 任意大 / 数字串精确 / 浮点仅 < 2⁵³ 整数 / 其余畸形); 非有限金额不因邻字段缺失免检 | `order_id_value` / `order_id_int`, `identity_field` / `_ident_check` |
| 成本口径 | 13–15 | `neutrality_price` / `chase_readout`: **已测 = 价 + 中价 + 费**(费非 USDT 且未换算 = 未知); 三桶(unpriced / fee_unknown / measured)+ 两种覆盖率; 无已测 ⇒ None 不是 0; `verify_reshape_anchor` 读者引用已测; 费用标记一次写入 | `scheduler/anchor_loop.neutrality_price`, `ops/chase_readout.collect`, `ops/verify_reshape_anchor.neutrality_lines` |
| 账本类型 | 3 | `reconstructed` 行类型(E-0909-D 52 行写回等部署); `skipped_venue_lock`(E-0910-A) | `live/pilot_log.py` |
| 电池 | 全程 | 新套件 `tests_request_identity_unknown.py` [1]–[82] **378 检查**; 13 套件版本配对更新; 电池 132 套; 每轮旧码红证 | `run_acceptance.sh`, `ops/gate_coverage.py` |

---

## §3 为什么要十五轮(错误形态, 不是事件清单)

研究员判决序列: 第 2–11 轮 REQUEST_CHANGES(每轮都有承重项被原链实达); 第 12–14 轮「未确认新 P1, 仅 P2」; 第 15 轮 APPROVE。承重项耗了十轮, 形态只有七种(逐轮证据在各 REVIEW_ACCEPT 的 §「我方承认的错」):

1. **同一事实多种读法** —— orderId 九处 `int()`, 身份门三处各写各的, 成本分母两处各自 `or 0`。修一处, 研究员在另一处实达。
2. **两件事一个字段** —— C 既当「已知量」又当「终值」; `filled_notional` 既是金额又是「已成交」标签; 数量终值与金额终值共用一个 `terminal`。
3. **只测修的那格** —— 不测反向(同夹具持仓不变必须 CLEAN)与邻格(同名第二张请求、部分成交、−2013)。第 3 轮的修复因此**扩大**了看门狗接受域(拒单当授权、丢卖出负号、已知未知双计)。
4. **来源层「替换」当合并** —— 第 8 轮把补查整条替换提交回包(缺字段抹掉已确认 C20); 第 9 轮改成字段合并又跨快照拼接(40/3 = 13.33 均价); 第 10 轮才把对象定为「记录集合」。
5. **意图当授权 / 缺席当零** —— 满页判 0、未看到 open 当已证终态、查单答非对象出口不带事实(CANCELED 4 退成 0–10)。
6. **交接措辞比代码好听** —— 「已验证」实为「假定」(第 13 轮三处口径、`attribute_trades` 费用来源写反、官方页面示例未列 cumQuote); 自报边界没写「观测到 / 未观测到」。
7. **改生产者形状不 grep 读者** —— 第 14 轮改了两个诊断的输出键, 第 15 轮研究员发现 `verify_reshape_anchor` 仍按旧键打印。

**结构性原因一句话**: 第 7 轮之前没有写事实表就写码 —— 每轮修反例, 反例的邻格就是下一轮的 P1。第 7 轮起先写表(DESIGN §1–§4), 第 12 轮起交**全表**让研究员按表核而不是按反例核, 之后三轮只剩表示 / 边界 / 口径 P2, 第 15 轮 0 P1。**研究员的方法之所以每轮都能抓到**: 原链端到端 + 同夹具正反两向 + 邻格 + 旧码红 + 按码写口径; 这四件从第 7 轮起我也做, 轮数才收敛。

---

## §4 量化影响

### 4a 部署前对照: 旧码 d040c74 vs 新码 b681ca5, 同一账本副本(三日 09-09 → 09-11; 副本 02:07:54Z; 全量 42 日副本 02:08:24Z; 脚本 scratch `cmp_old_new.py`, 收据 `cmp_old_new.json` / `wd_eval_{old,new}_tree.json`)

行数: `orders.jsonl` **5,653**, `anchors.jsonl` **12**(09-09 12Z 崩溃锚无 anchors 行, 不在表内)。`neutrality_price` 逐锚:

| 锚(UTC) | rid | 旧 bps | 新 bps | 补单 taker 笔(基数 = 已测) | 未定价 / 费未知 | 覆盖率 |
|---|---|---|---|---|---|---|
| 09-09 00Z | A1788913440 | 6.6121 | 6.6121 | 36 | 0 / 0 | 1.0 |
| 09-09 04Z | A1788927840 | −11.6884 | −11.6884 | 20 | 0 / 0 | 1.0 |
| 09-09 08Z | A1788942240 | 3.5548 | 3.5548 | 30 | 0 / 0 | 1.0 |
| 09-09 16Z | A1788971040 | 74.4142 | 74.4142 | 28 | 0 / 0 | 1.0 |
| 09-09 20Z | A1788985440 | None | None | 0 | — | None |
| 09-10 00Z | A1788999840 | None | None | 0 | — | None |
| 09-10 04Z | A1789014240 | −3.4919 | −3.4919 | 29(名义 23,383) | 0 / 0 | 1.0 |
| 09-10 08Z | A1789028640 | 107.2102 | 107.2102 | 9 | 0 / 0 | 1.0 |
| 09-10 12Z | A1789043040 | −40.905 | −40.905 | 50 | 0 / 0 | 1.0 |
| 09-10 16Z | A1789057440 | −69.8349 | −69.8349 | 16 | 0 / 0 | 1.0 |
| 09-10 20Z | A1789071839 | −6.2798 | −6.2798 | 49 | 0 / 0 | 1.0 |
| 09-11 00Z | A1789086240 | −15.5005 | −15.5005 | 31 | 0 / 0 | 1.0 |

- **12/12 相等**(含两个 None: 两侧都没有该侧补单 taker 成交 —— 09-09 20Z 为 E-0909-G 平仓后停开仓, 09-10 00Z 为 E-0910-A −4400 锁 71 张补单全拒; 归因 INFERRED 自时间线)。
- 行普查(新码自己的键): 467 笔补单 taker 成交中 `avg_fill_px` None **0**、`fee_paid` None **0**、`fee_all_usdt` False **0** ⇒ 三桶全在「已测」, 覆盖率 1.0 ⇒ 新分母 = 旧分母。5,653 行里 `request_ledger` / `filled_amount_unknown` / `inconsistent` / `unknown_qty>0` / `reconstructed` 全为 **0** —— 因为这些行是旧码写的; 新键只在部署后出现。
- `ops/chase_readout.collect`: 两侧各 12 锚记录, 共有键逐键 0 差, 新版只多三桶 / 覆盖率键。(VERIFIED 02:1xZ: 12 / 12 记录, 共有键 diff **0**; 新键 12 个: `chase_n_measured` / `chase_notional_measured` / `chase_n_unpriced` / `chase_n_fee_unknown` / `chase_fee_unknown_notional` + 七个 `chase_forced_*` 同名桶)
- `watchdog.evaluate()` 全量 42 日(08-01 → 09-11)副本: 两树输出**逐键 0 差**(`evaluated_utc` 除外); `tripped` False; triggers / metric_errors 空; `cond7_ops` 两侧同为 blind(离线未注入 ops_stats 的装置效应, 不是差异); 七条件阈值(`limit_*`)两侧同值。
- 回滚排演: scratch 共享克隆 `revert --no-commit d040c74..b681ca5` ⇒ 27 文件 +280 / −5,098, `git diff d040c74` **0 文件**。

### 4b 会变的评价口径(部署后; 按码写, VERIFIED)

| 读者 | 旧 | 新 | 何时读数不同 |
|---|---|---|---|
| `neutrality_price` / `chase_readout` 的 bps | 分母 = 全部成交, 缺价 / 缺费按 0 | 分母 = **已测**成交(价 + 中价 + 费), 新增 `n_fills_measured` / `notional_measured_usdt` / `coverage_priced`(名义)/ `coverage_measured_notional` / `coverage_measured_count` / `measured_over`; 无已测 ⇒ **None** | 只在有成交缺价 / 缺费 / 费非 USDT 未换算的锚(三日样本 0 个); **跨部署边界比较 bps 必须同引覆盖率** |
| `verify_reshape_anchor` neutrality 行 | 按旧键打印 | 引用已测口径, None 按三桶解释(旧记录标「旧记录」) | 部署后每锚 |
| reconcile / 看门狗 §4-5b/5e | 账本行按 `filled_notional` 走 | 账本行走带分支 [Σ\|L\|, Q], 与 N 无关; 拒单 / 未发 = 确定 0; 矛盾 ⇒ 不可测 ⇒ 任何持仓皆异常 | 只在异常态: 少误触发(拒单 × 持仓不变 = CLEAN, 第 6 轮 6 格), 多真捕获(CANCELED 4 金额不可读 × 持仓 10 ⇒ 异常 6) |
| `pilot_metrics`(字节冻结, **未改**)M1 / M4 | — | 行为不变; 但新码在金额未知时写 `filled_notional=None` ⇒ M1 排除该行, M4 按 0 计 realized 换手(第 14 轮按码写清) | 只在异常态; 是口径不是数字变化 |
| `orders.jsonl` 行 | 六列手写 | 新列 `request_ledger` / `confirmed_*` / `filled_amount_unknown` / `ledger_label_mismatch` / `avg_fill_px_children` / `inconsistent`; 新类型 `reconstructed` / `skipped_venue_lock` | 部署后每锚; 旧行无这些键 ⇒ 读者走旧读法(未闭合项「来源前提」) |

### 4c 不变的东西(明写)

生产者 `~/wide_shadow`(king / combo_stage / FTRIM / 席位 / target_live)一字未动; 在役书权重、gross 2.0×、maker-only、挂单窗、重挂随机实验、看门狗七条件阈值(4a 逐键相等)、费用 / markout 写入者(除费用标记一次写入)、`daily_nav`(场所权益)、回放引擎与全部年表 / 回测数字、ic_monitor。研究复审分支合并进主线的是门 / 收据 / HANDOFF 文档, 不含任何数字产物。

### 4d 「会不会颠覆之前的效果预估」—— 否, 三条理由

1. 之前的效果预估(全周期年表 / 回放 / 口径终审 / v4 主判 / 回吐根因 DIAG)全部来自研究引擎与场所权益, **不经过这 27 个文件里的任何函数**。
2. 实盘 76 锚的执行成本 / 回吐归因用的是 `orders.jsonl` 的成交列, 正常态下新码写同样的值(4a 12/12)。
3. 唯二会改历史读数的地方都已登记且都要裁定: (i) 09-09 12Z 崩溃锚 52 行 `reconstructed` 写回后, 09-09 当日 M1 / M4 分母改变(写回等部署 + 裁定); (ii) 历史上若有混合可读性的锚, 新口径给 None + 覆盖率而不是一个数 —— 三日样本内 0 个, 更早账本未回扫(待查, 可在部署后用同一脚本扫 08-01 起)。

### 4e 风险面的收益(定性, 只列反例夹具证明过的; 不给收益数字)

| 异常态 | 旧码(d040c74) | 新码(b681ca5) |
|---|---|---|
| POST 传输 / 5xx 后再发 | 可能双发(E-0909-D 后已改一半) | 永不重发, 只按 cid 查; 查不到 = 歧义留阶段 B |
| 拒单 / 未发 × 持仓不变 | 6 格看门狗误触发(第 5→6 轮) | CLEAN |
| CANCELED 4, 金额不可读, 持仓 10 | 带 0–10 CLEAN(漏报 6) | filled_qty 4 / 异常 6 |
| 开单快照 20 + 终态 30(择大)/ 40 ÷ 3 跨快照均价 | 造出 30 / 13.33 | 单调合并, 派生只在同快照; 子集均价不冒充整单 |
| 补查缺字段 | 抹掉已确认 C20 ⇒ 补单双计 | 集合合并, 可读事实不被缺字段撤销 |
| 撤单回包 C4 + 稀疏查单 | 抹成 0 再补 10 | 撤单回包入集合, −2013 在有证据后 = 矛盾 |
| orderId 2⁵³ ± 1 / 小数 / ±Inf | 舍入合并 ⇒ 外来成交归入我方; OverflowError 穿出主链 | 精确文本合同; 畸形 = 矛盾, 不崩 |
| 补单成交无价 / 费非 USDT | bps 按 0 成本 | 桶内报未知, 分母只含已测 |

---

## §5 未闭合(明写; 与研究员 limits 合并)

Q6 恢复政策(PREREG 修订 4, 数学已接受, **未落码**, 41 日回放待做; 研究员称之「重要开放风险项」); R6-MARK 不可定价数量的动作合同; 币种换算治理; 下游成本读者(`daily_summary` / `first_anchor_review` / `score_post_fix`)未继承三桶; 无场所事实 maker 行走旧读法(来源前提); `_seen_syms > 1` 与 settle 整体异常出口; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行; 物理 BUNDLE_export 门; 52 行写回等部署; −5022 数据缺口(拒单行缺 spread / mid); 研究员无独立 132 电池(部署时在运行目录补跑一次 = RUNBOOK §2-6); 08-01 起更早账本的混合可读性回扫(4d-ii)。

---

## §6 部署与验收

部署 = 用户裁定; 动作、前提、首锚验收、回滚全部在 `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`。研究员要求的部署前三件(账本副本旧 / 新对照、历史行兼容、回滚排演)已做(4a)。推荐窗口: 锚小时之外的 HH+1:00 → HH+3:30Z。

---

## §7 再犯预防(已入持久记忆 `feedback_fact_table_before_code_review_method` + `review_b0a573a1_closure_and_merge_deploy_protocol`)

1. **先写事实 × 来源 × 出口 × 读者表, 再写码**; 表里的空格就是下一轮的 P1; 交全表让复审按表核。
2. **一件事实一个字段, 一个字段一个实现**; 新规则落地 grep 该事实的每个解析点, 用一个实现替换。
3. **每修一格测三格**(反例 / 反向 / 邻格)+ 原链端到端(未改的 `complete_anchor` 跑真 broker + FakeNet 到 reconcile)+ 旧码红证 + 版本配对表。
4. **改生产者输出形状先 grep 读者**(含 `ops/` 报表), 逐个列进交接。
5. **自报只写 观测到 / 未观测到 / 待查**; 概括一段代码前先读它(冻结件也读); 口径写「代码实际做 X」。
6. **合并 ≠ 部署**; 运行目录只经明做的 `pull --ff-only` 或 safe_commit 切换; safe_commit 自带 rebase = 隐式部署 ⇒ 部署未裁定期间禁在运行目录 safe_commit。
7. **每锚深查加一项**: 运行树 HEAD vs origin/main; 落后 = 未部署改动存在, 照常报。
8. 电池环境三则: 跑前刷新 `notify_audit.jsonl` 副本并记时间; 避开锚小时 HH:20–HH:35; `gate_coverage.py` 文案内引号用单引号, 改完 `ast.parse`。

---

## §8 数字标签
提交号 / 文件数 / 行数 / 12 锚 bps / 行普查 / 42 日 0 差 / 排演数字 / 研究员 RESULT.json 各计数 = **VERIFIED**(本机 02:04–02:12Z 直接计算或读原文); 两个 None 锚的原因归因 = **INFERRED**(时间线一致, 未逐行核); 「旧码读者忽略新键」= 按码读 INFERRED; `reconstructed` 行回滚兼容 / 08-01 起混合可读性回扫 = **UNRESOLVED**。本文不含任何收益 / alpha 数字, 亦无此主张。
