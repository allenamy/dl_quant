# DESIGN · 下游读者三桶迁移: daily_summary / first_anchor_review / score_post_fix (事实表先于代码)

> **创建:** 2026-09-12 10:1xZ | **Session:** W2 (team lead 派单; 隔离克隆 `/Users/haosiyu/cc_tmp/exec_w2`, 分支 `fix/readers-three-bucket`, 基线 `origin/main` = 918559f) | **状态:** 第四轮(研究员第三轮 monitoring NAV-R3-1 权益端点 0/None/NaN + 同族 `x or 回退` 审计)收口, 见 §9; 第三轮见 §8; 码在克隆分支, 未提交/未推送/未部署; 本轮未跑全电池(lead 跑叠层) | **作废条件:** `daily_nav` 的 `nav` / `wallet_balance` / `unrealised_pnl` / `external_flow_usdt` 载体合同改变(§9b), 或收入载体(`binance_broker.income_since`)改变 `by_type_asset` / `non_usdt_assets` / `truncated` 合同, 或 `external_flow_usdt` 不再是当日累计, 或 `anchor_loop.neutrality_price` 的三桶规则改变, 或 `pilot_metrics.py` 解冻(§8 的载体一致门会先红)

## 0. 范围与硬约束
- **只改读者, 不改生产者与守卫**: `ops/daily_summary.py` / `ops/first_anchor_review.py` / `ops/score_post_fix.py` + 一个新的纯函数模块 `live/cost_buckets.py` + 测试 + 注册(`run_acceptance.sh` SUITES, `ops/gate_coverage.py` SUITE_SCOPE)。
- **不动**: `live/pilot_metrics.m1_effective_cost`(看门狗 §4-1 输入; 改它 = 改书行为的判据 ⇒ 预注册 + 用户裁定), `scheduler/anchor_loop.neutrality_price`(在役三桶正典), `binance_broker.income_since`(载体), `docs/POST_FIX_EXPECTATIONS.md`(E6 预注册合同)。
- 运行目录 `~/dl_quant_live` 与 `~/wide_shadow` 只读; 无场所 / Telegram 调用; 无 pod2。合入由 lead 经 `safe_commit.sh`。

## 1. 事实表 (事实 × 来源 × 读者 × 旧读法 × 新读法 × 测试)

### 1a. 账户「当日已实现」—— nav 行 (`daily_nav.jsonl`)
载体: `anchor_loop.py:2804-2810` 写 `realised_pnl`(载体的**跨币种原数和**, USDT 假定) / `realised_by_type`(同, 分类型) / `realised_by_type_asset`(round 4, 09-12 06:05Z 起: 类型 × 币种 原数) / `realised_non_usdt_assets`(非 USDT 币种名列表) / `realised_truncated`(分页截断) / `realised_pnl_source`。`inc is None` ⇒ 以上全部 None(载体自己拒绝写 0)。

| # | 事实 | 载体字段取值 | 旧读法 `account_facts`(L81/L110-111) | 新读法 | 反例 / 反向 / 邻格测试 |
|---|---|---|---|---|---|
| A1 | 已实现总额, **USDT 口径** | `realised_by_type_asset` 存在 | `float(realised_pnl or 0)` = 跨币种原数和 | Σ_{type∈{REALIZED_PNL,COMMISSION,FUNDING_FEE}} `by_type_asset[type]["USDT"]`; 非 USDT 条目**逐条列出**为 UNCONVERTED(type, asset, 原数), **永不相加** | 研究员反例: USDT −0.30 + BNB −0.01 ⇒ 旧 −0.31 标 USDT; 新 usdt=−0.30, unconverted=[(COMMISSION,BNB,−0.01)]; 反向: 全 USDT 行 usdt == realised_pnl 且 unconverted=[]; 邻格: 真账本 09-12 08Z 行(有 by_type_asset, 全 USDT) |
| A2 | 已实现**不可观测** | `realised_pnl is None`(inc None) **或非有限数(NaN/inf, 复审 W2-R2)** | `or 0.0` ⇒ realised_today=0.0, observable=True, **且**同日残差用 0 算出一个数 | `realised.observable=False`, `realised_today=None`, `unexplained_computable=False` + why 指明「已实现不可观测」; 文案「不可观测 —— <realised_pnl_source>」 | 研究员反例: realised_pnl=None ⇒ 旧 0.0/True; 新 None/False; 反向: 有数的行 observable True; 邻格: 只有 n0 不可观测时增量也不算 |
| A3 | 已实现**不完整**(分页截断) | `realised_truncated is True` | 未读 | `realised.complete=False`, 数字保留但标「只是已读部分, 非当日总额, 也非任何一侧边界」(复审 W2-R2: 漏行带符号, 「下界」不成立); 残差与轮换增量**要求两端 complete is True**, None(标记缺失)= 完整性未知, 同样不算 | 截断行 ⇒ complete False + 文案 + 残差 None; 反向 False ⇒ complete True; None ⇒ complete None(未知) ⇒ 残差 None(另一条理由) |
| A4 | 旧格式行(无 `realised_by_type_asset`) | 键缺失(09-12 06:05Z 前) | 同 A1 | 不能拆币种 ⇒ **不发明**: usdt = 载体和, `caliber="legacy_carrier_sum_usdt_assumed"` 明标假定 | 旧格式夹具 ⇒ caliber legacy 且 usdt == realised_pnl; 新格式 ⇒ caliber usdt_only |
| A5 | 载体和是否混币 | `realised_pnl` vs USDT 切片 | — | `carrier_sum_mixes_assets = (unconverted 非空)`; 渲染时**不打印载体和**为 USDT | A1 夹具 True; 全 USDT False |
| A6 | 「一换手就降」增量(main L289-298) | 两行 realised | `float(r.get("realised_pnl") or 0)` 两次 | 任一行不可观测 ⇒ 不算增量, 打「不可观测」 | 由 A2 覆盖(同一 `_realised_usdt` 助手) |

顶层 `observable` 的语义**不变** = 「窗口内有 nav 行」(门住 wallet / unrealised / equity 三样可观测量)。已实现的可观测性是它自己的字段 `realised.observable`(顶层镜像 `realised_observable`), 因为 wallet/equity 在 inc None 时仍然可观测(它们来自 /fapi/v3/account, 不是 income)。研究员反例中「observable=True」指的正是这个混用, 新记录把两者分开。

### 1b. 成交成本 —— 订单行三桶 (`orders.jsonl`)
正典规则 = `scheduler/anchor_loop.py:160-216`(round 13/14/14b, 研究员 R12/R13 复审通过): 一笔成交是 **measured** 当且仅当 价格可用(`avg_fill_px` 与 `mid_at_anchor` 皆有限正数) **且** 费已知(`fee_paid` 非 None 且有限, 且不是「`fee_all_usdt is False` 且无 `fee_conversion`」的原币种混和)。桶: `unpriced`(价不可用) / `fee_unknown`(有价, 费未知) / `measured`; bps 只在 measured 上算(费 + 有符号逆价), 无 measured ⇒ **None, 不是 0**; 覆盖 = measured 名义 / 全部成交名义, 与计数覆盖。

| # | 事实 | 行取值 | 读者与旧读法 | 新读法 | 测试 |
|---|---|---|---|---|---|
| B1 | 费未知(混币, 未换算) | `fee_paid=0.0, fee_all_usdt=False, fee_conversion=None`(真账本 2026-08-05 A1785931245 **103/103** 成交, A1785945696 **100/100**) | `daily_summary` L263 `fee_paid or 0` ⇒ 费=0 进分子, 名义进分母 ⇒ 08-05 12Z **−3.70 bps**, 16Z **−1.68 bps**(0 笔已测算出的「成本」); `first_anchor_review` L363 同; 只数 `fee_paid is None` 的 `n_nofee`, 对 False/无换算**视而不见** | 三桶: n_measured=0 ⇒ bps None, 打「已测 0/103 笔, 费未知 103」; 覆盖 0 | 真账本正例(读只读副本; 日文件缺 ⇒ NOT EXERCISED); 合成夹具; **旧读法内联突变**必须给出数字而新读法 None |
| B2 | 费缺(None) | `fee_paid=None`(真账本 1494 笔, 几乎全是 protective_flatten) | 同上, `or 0` | fee_unknown 桶 | 夹具 |
| B3 | 价不可用 | `mid_at_anchor` None/0 (1476 笔, 全 flatten) 或非有限 | `daily_summary` L258-259 用真值过滤**静默丢弃**; `first_anchor_review` L339 同, 仅在**全部**缺时说 UNMEASURED | unpriced 桶, 计数 + 名义打印 | 夹具: NaN / inf / 负 / 0 / None 皆 unpriced |
| B4 | 成交金额未知 | `filled_notional=None`(round 7+: 477 行有 `filled_known_notional`/`filled_unknown_residual`) | `abs(float(o.get("filled_notional") or 0)) > 0` ⇒ 当「没成交」; 成交率分子 `or 0.0` ⇒ 率被压低但不说 | `n_unknown_fill` 单列; 成交率标「≥」(下界) 并打未知笔数 | 夹具: 一行 None ⇒ n_unknown_fill 1, fill_rate_is_lower_bound True |
| B5 | 全部已测 | 真账本 09-11/09-12 九锚 **185/185, 193/193 …** 覆盖 1.0; 08-05 A1785888079 79/79 | 数字正确(偶然: 无未测行) | 新旧**相等**(7.8069 bps on A1785888079) | 相等断言 = 反向对照: 修复不改变干净锚的读数 |
| B6 | 符号约定 | 逆价符号 | `daily_summary` 用 `filled_notional` 符号; `first_anchor_review` 用 `side` 字串 | 统一为 `filled_notional` 符号(正典 `anchor_loop` / `chase_readout` 皆如此) | 与 `neutrality_price` 相等断言 |

### 1c. score_post_fix E6 (成本可比性)
E6 读 `pilot_metrics.m1_effective_cost`: m1 已把 None 费 / 混币费记 `n_unmeasured_fee`(L156-165), 无 mid / 无 px 记排除; **但** m1 把费未知行以 fee=0 **留在分母**(`den += f`, L167-170) ⇒ `c_bps_overall` 在费未知时是**下界** —— 这正是 E6 预注册的规则(「measurement_complete 非 True ⇒ c 是下界, 不与 9.0 比」, `POST_FIX_EXPECTATIONS.md` L132-151)。
**判定: E6 的判决与 `c_bps_overall` / `measurement_complete` / `counters` 合同不改**(预注册, 改 = 重写判据)。**只加**键: `E6.buckets`(三桶 + 覆盖 + `bps_measured`)与 `E6.bucket_rule`。全测时 `buckets.bps_measured == m1.c_bps_net_overall` 且 `buckets.abs_bps_measured == m1.c_bps_overall`(相等断言); 费未知时两者分叉且分叉方向明写(m1 含零费分母 ⇒ 数字; 桶 ⇒ None)。
其余判据(E1 residual / E2 net / E3 reject / E4 self-consistency / E5 ratio)不算费与价, 且已用 `is not None` 门; 不动。

## 2. 读者逐个
| 读者 | 改 | 不改 | 契约钉子(其它套件) |
|---|---|---|---|
| `ops/daily_summary.py` | `account_facts` 加 `realised` 子记录(1a); `render_account` 按事实渲染(不可观测 / 未换算 / 不完整三种句子); 新纯函数 `anchor_cost_facts(orders_of_anchor)`(1b/B4) 供逐锚表; 逐锚表加「覆盖」列, bps 无 measured ⇒ n/a; 轮换块用同一 `_realised_usdt` 助手 | `observable` 顶层语义; 外部资金流逻辑; alarm 分类; 窗口自报 | `tests_daily_summary` 全部既有 check(字段 + 少量文案: 「浮动」「仓位还开着」「目标敞口」「TRANSFER」「看不见现货」「一换手就降」「落袋」「入场成本」「跨越 00:00Z」「同日内权益变动」「不跨 00:00Z」「不足以给出」「RESETS AT 00:00Z」「A COLUMN NAME IS NOT A CALIBER」「被记录但未推送」「需要决定的」「逐锚」「import alarm_policy」「AP.classify」; `render_account` 单参数 `f`) |
| `ops/first_anchor_review.py` | §3 加「未知成交」计数; §3c `_leg` 走三桶(打印已测/未定价/费未知 + 覆盖; 0 已测 ⇒ UNMEASURED 不打 bps); vs-limit 用可用价; maker 成交率标下界 | 选锚 / 作用域行(`rb = [r for r in rb_all if …]` 逐字不动) / `_estimable` 与 `_MIN_N, _MAX_SHARE = 5, 0.50` / 「NOT ESTIMABLE」「largest is」/ `collapse_supersedes` + `backfill` / 净敞口块 / 守卫块 | `tests_review_anchor_scoping`(逐字注入靶), `tests_reject_topup [J]`(`_estimable(` ≥3 处, 常量行), `tests_fills_supersede`, `tests_rehearsal_anchor` 注册文案 |
| `ops/score_post_fix.py` | E6 加 `buckets` / `bucket_rule` | 选主体 / E1–E5 / E6 判决与旧键 | `tests_score_anchor_selection`, `tests_rehearsal_anchor _v4`, 无 FLATTEN 字面 |
| `live/cost_buckets.py`(新) | 纯函数: `usable_px` / `known_fee` / `filled_abs` / `bucket_fills(rows)` / `coverage_note(b)` | — | 文件内**不得**出现 `rebalance_id` 字串(`tests_rehearsal_anchor` 全仓 grep 普查)与 `/fapi/` 字串; pyflakes 清洁(`tests_static_names`); 不在 run_anchor 可达图 ⇒ 不进 `PRODUCTION_MODULES` |

## 3. 结构性保证
1. **一份规则, 两处相等断言**: `cost_buckets` 复刻 `anchor_loop.neutrality_price` 的 `_pos`/`_fee`, 测试对同一夹具断言 bps(4 位)/计数/名义逐键相等(`duplication_with_equality_assertion` 族)。全测夹具上再对 `pilot_metrics.m1` 断言 `abs_bps == c_bps_overall`, `bps == c_bps_net_overall`。
2. **渲染器只吃事实**: `render_account(f)` 仍单参数; 新句子全部由 `f["realised"]` 字段驱动。逐锚表由 `anchor_cost_facts` 字典驱动。
3. **None 三态**: 每个数量 (值 / None=未测 / 覆盖) 三件同行; 「已测 0 笔」与「费为 0」不同印。
4. **每修一格三测**: 反例格 + 同夹具反向(干净行读数不变) + 邻格(同事实的另一读者 / 另一出口); 旧码红: 新套件复制到 `origin/main` worktree 跑 ⇒ 必红(收据 §6)。

## 4. 测试矩阵
| 套件 | 段 | 断言 | 突变(必红) |
|---|---|---|---|
| `tests_daily_summary` | [E1] | A1 反例: usdt −0.30 / unconverted BNB −0.01 / 文案含 BNB 且不把 −0.31 印成 USDT | 内联旧读 `float(realised_pnl or 0)` = −0.31 ≠ 新 |
| 同 | [E2] | A2: None ⇒ realised.observable False / realised_today None / unexplained_computable False / 文案「不可观测」 | 内联旧读 0.0 与 True |
| 同 | [E3][E4][E5] | A3 截断; A4 旧格式 caliber; A5 真账本最新行(有 by_type_asset)全 USDT | — |
| 同 | [F] | B1 真账本 08-05 A1785931245: n_fee_unknown 103, bps None; 旧公式 −3.70(内联); B5 09-12 A1789201439 新==旧 覆盖 1.0; B4 夹具 | 旧公式给数字 |
| `tests_readers_three_bucket`(新) | [A] | `cost_buckets` 各桶 / 非有限价 / 混币费 / 换算完成 ⇒ 已测 / 0 已测 ⇒ None | — |
| 同 | [B] | 与 `anchor_loop.neutrality_price` 逐键相等 | 改符号约定 ⇒ 红(内联) |
| 同 | [C] | 与 `pilot_metrics.m1` 全测相等; 费未知分叉方向 | — |
| 同 | [D] | `first_anchor_review` 夹具树(exec 同 `tests_review_anchor_scoping` 法): 全费未知 ⇒ 「UNMEASURED」且无 bps; 全测 ⇒ bps + 覆盖 100%; 混合 ⇒ 排除数被说出 | 内联旧 `_leg` 公式在费未知夹具给数字 |
| 同 | [E] | `score_post_fix` E6: 夹具树 buckets 键; 旧键不变; 全测相等 | — |
| 同 | [F] | 真账本只读正例(同上两锚; 缺文件 ⇒ NOT EXERCISED) | — |

## 5. 明写不做 / 未闭合
- `ops/first_real_anchor.py:81` 打印 `realised_by_type` 原数(一次性工具; 未在派单; 登记)。
- `live/pilot_metrics.m1` 分母含费未知行 = §4-1 判据的一部分, 不在本任务; E6 的 `buckets` 使分叉可见但不裁定。
- `watchdog` 内 11 处 unpriced/fee_unknown 已是三桶(复审 R14), 不动。
- 非 USDT 的**换算**(BNB→USDT 价格)不在读者层做: 读者只列原数; 换算治理 = POSTMORTEM §5 独立项。
- `daily_summary --since` 窗口跨 09-12 06:05Z 时, 旧格式与新格式 nav 行并存: 增量的口径混合由 `realised_increment_caliber` 明标, 不合成。

## 7. 独立研究员复审 W2-R1 / W2-R2 收口 (2026-09-12 14:3xZ; 复审 `codex_batch_incident_review_2026-09-12/monitoring/RESULT.md`, 探针 `probe_review.py`)

### 7a. 事实表补格 (每格: 复现 → 新读法 → 测试 → 修前红)
| # | 研究员反例 | 我方复现(冻结 m1 sha 5ac7b16d…, 克隆) | 新读法 | 测试(新码绿 / 修前读者红) |
|---|---|---|---|---|
| R1-a | `fee_paid=NaN` ⇒ m1 `measurement_complete=True`, `c_bps_overall=NaN`; E6 据 m1 位判 PASS | 复现: complete True, c_bps nan, n_unmeasured_fee 0 | `cost_buckets.bucket_fills` 新增 `measurement_complete`(三态, 只由桶推: 费非有限 / 混币未换算 / 价不可用 / 成交未知 ⇒ False); E6 的 `measurement_complete` 与 verdict **改由桶位**推, m1 的位保留为 `m1_measurement_complete`, `completeness_disagrees_with_m1` 明写, `c_bps_overall` 仍是 m1 原数 + `c_bps_overall_is_finite` | RTB [E-R1]: NaN 费树 ⇒ m1 True / 桶 False / verdict FAIL / disagree True; MUTATION: `_verdict(m1 位)` = PASS。修前读者(pre-review)上 KeyError `measurement_complete` ⇒ 红 |
| R1-b | protective_flatten 行 `fee_paid=0, fee_all_usdt=False, 无 conversion` ⇒ m1 退出费块 `fee_paid 0 / n_measured_fee 1 / complete True`(「测得免费」) | 复现: 同 | E6 加 `protective_flatten_buckets`, `protective_flatten_fee_known_by_buckets`(用 `known_fee`), `protective_flatten_fee_disagrees_with_m1`; m1 块原样保留 | RTB [E-R1]: 同 rid 的 flatten 行 ⇒ m1 n_measured_fee 1 vs 桶 0 ⇒ disagree True; 主判决不受 flatten 行影响(PASS) |
| R1-c | daily_summary / first_anchor_review 是否也依赖 m1 位 | 两者从不读 m1(§1b); 完整性已由桶推 | `anchor_cost_facts.cost_measurement_complete`; 复审屏「measurement complete: yes/NO」 | RTB [A] 三态; [D] 文案 |
| R2-a | 末行 `realised_truncated=True` 仍算数值残差 −10 | 复现: −10.0 | `unexplained_computable` 要求两端 `complete is True`; 截断 ⇒ None + 「不完整(分页截断, 只是已读部分)」; 标记缺失 ⇒ None + 「完整性未知」; 轮换增量同规则 | DS [R2-a] 同对 ⇒ None; MUTATION 旧规则 −10.0; [R2-b] 缺标记 ⇒ None; 反向: 完整 ⇒ 算。修前读者: 8 条 FAIL |
| R2-b | 「不完整读取(下界)」措辞错: 收入带符号 | — | 文案改「只是已读部分, 不是当日总额; 漏掉的行带符号, 所以它也不是任何一侧的边界」; docstring / DESIGN A3 同改 | DS [E3]: 「已读部分」在, 「下界」不在 |
| R2-c | `realised_pnl=NaN` 仍 observable True | 复现(探针 L180) | `_finite()`: None / NaN / inf / 文本 ⇒ 不可观测 + why「not a finite number」; 分币种切片含 NaN 同判 | DS [R2-c]: NaN / inf / 切片 NaN ⇒ observable False; MUTATION 旧判据 `is not None` 放过 NaN |
| R2-d | `coverage_measured_notional` 先 round(4) ⇒ 9999.6/0.4 读 1.0, 表印 100%, `_cov_short` 不计 | 复现 | 覆盖改**精确比值**(round 只在显示: `pct_floor` 向下取整, 0.99996 ⇒ 99); `_cov_short` 按**计数**(已测 < 成交); 复审屏同用 `pct_floor` | DS [R2-d]: 比值 < 1.0 / complete False / 99%; MUTATION round(…,4)==1.0。RTB [B] 相等断言改在比较点上 round 到 4 位(与 `neutrality_price` 的记录精度一致) |

### 7b. 裁定项 R-12b: `pilot_metrics.py` 冻结 vs 完整性位错误
- `live/pilot_metrics.py` sha 5ac7b16d0f97f2f8013da728ab18f4f3787bc17c2192c1dba63e64e637c08f1f = `ops/check_metrics_freeze` FROZEN_MATCH; 电池套件 `metrics_freeze` 会因任何字节改动而红, 且它是 §4-1 判据的来源。**本轮不改它。**
- 已知它的两处「已测」语义错误(R1-a NaN 费; R1-b 退出费块混币费计为已测)在冻结源码上**成立且保留**; 读者层已全部改由 `cost_buckets.known_fee` 推完整性, 并在 E6 输出里把 m1 的位与分歧明写。
- **需裁定**: 是否解冻 m1 修这两处(改变 §4-1 看门狗输入的 completeness 语义 ⇒ 需预注册 + 用户裁定 + 重新冻结), 或长期接受「m1 位只作旁注」。研究员意见: 「E6 判据无需变更; 应先让『已测』含义一致再维持原判据」—— 本轮做法与此一致(判据不变, 位的来源换成一致的那个)。

### 7c. 真账本核对 (只读副本 10:0xZ 同步)
- 副本内 protective_flatten 行 **1453**(7 日: 08-01 105 / 08-02 83 / 08-05 210 / 08-21 210 / 08-26 334 / 09-06 268 / 09-09 243), 桶: 1453 unpriced(无 `mid_at_anchor`) / 0 measured / bps None; 研究员在其 13:57Z 冻结输入上对 E-0912-A 事故的 **255** 行 `FLATTEN-20260912T124737Z`(全 `fee_paid=None`, 键缺失)得到同形态 255 unpriced / 0 measured / bps None, `first_anchor_review._leg` 印 UNMEASURED。本副本不含 09-12 flatten 行(同步早于事故), 255 数字引自研究员 `INCIDENT_FEE_POPULATION.md`, 未独立重算。**退出费人口的修复属 W6, 不在本任务。**
- `ops/first_real_anchor.py:81` 仍是旧格式读者(打印 `realised_by_type` 载体原数); **登记为开放项, 本轮未改**(未派单)。

## 6. RESULT (2026-09-12 10:3xZ; 克隆 `/Users/haosiyu/cc_tmp/exec_w2` 分支 `fix/readers-three-bucket`, 基线 origin/main 918559f; **未提交, 未推送, 未部署**)

### 6a. 变更 (file:line, 克隆内; diff = `docs/receipts/w2_readers_three_bucket.diff`, 限 ops/ live/ run_acceptance.sh; 第二轮(§7)后行号见 6a-2)
| 文件 | 行 | 变更 |
|---|---|---|
| `live/cost_buckets.py`(新, 175 行) | 47 `usable_px` / 56 `known_fee` / 74 `filled_abs` / 86 `partition` / 106 `bucket_fills` / 154 `coverage_note` | 三桶纯函数; 规则逐字复刻 `anchor_loop.py:160-180` 的 `_pos`/`_fee`; 文件内无 `rebalance_id` / `/fapi/` 字串; 不在 run_anchor 可达图(`tests_imports` 通过) |
| `ops/daily_summary.py` | 47-97 `realised_facts` (新) | 1a: USDT 切片 / UNCONVERTED 列表 / observable / complete / caliber |
| 同 | 100-128 `anchor_cost_facts` (新) | 1b/B4: 逐锚三桶 + 成交率下界 |
| 同 | 166-172, 200-211, 231-250 (`account_facts`) | `real = realised_facts(n1)["usdt"]`(None 不再 → 0); 新字段 `realised` / `realised_observable` / `realised_by_type_usdt` / `realised_unconverted` / `realised_increment_caliber`; `unexplained_computable` 加「两端已实现可观测」条件, 不可观测 ⇒ None + why |
| 同 | 271-290 (`render_account`) | 三种句子: 不可观测 / 未换算(逐条) / 不完整; 口径标签 |
| 同 | 371-408 (`main` 逐锚表) | 走 `anchor_cost_facts`; 新「覆盖」列(向下取整); n/a = 未测; 备注写「未测 k/n(费未知 a 未定价 b)」「成交未知 k 行」; 尾行汇总覆盖 < 100% 的锚数 |
| 同 | 413-426 (`main` 轮换块) | 两端用 `realised_facts`; 任一端不可观测 ⇒ 不打增量; 口径不同 ⇒ 明标 |
| `ops/first_anchor_review.py` | 216-221 (§3) | 「order rows with UNKNOWN fill」行 |
| 同 | 355-402 (§3c `_leg`) | 三桶: 0 已测 ⇒ 「cost UNMEASURED — 0 of n fills measured (fee-unknown a, unpriced b)」不打 bps; 否则 measured 名义 + 覆盖 + 「excluded from numerator AND denominator」 |
| 同 | 475-495 (vs-limit) | 价不可用行计数排除, 全排除 ⇒ UNMEASURED |
| 同 | 502-512 (maker fill-rate) | 未知成交腿排除 + `>=` 下界 + 计数 |
| `ops/score_post_fix.py` | 374-400 (E6) | **只加** `buckets` / `bucket_rule`; verdict / `c_bps_overall` / `measurement_complete` / `counters` 原样 |
| `live/tests_daily_summary.py` | 221-424 (新 [E][F]) | 26 新 check(27 → 53) |
| `live/tests_readers_three_bucket.py`(新, 384 行) | [A]-[F] | 31 check |
| `run_acceptance.sh` | 189-195 | 注册 `tests_readers_three_bucket`(注释不含 `.py` 后缀: `tests_imports` 的脚本扫描会把它读成调用 —— 第一次跑就红了, 已改) |
| `ops/gate_coverage.py` | 156-160 | SUITE_SCOPE 新条目 + `tests_daily_summary` 条目追加本轮盲区 |

### 6a-2. 第二轮(复审 W2-R1/R2)增量变更
| 文件 | 变更 |
|---|---|
| `live/cost_buckets.py` | `coverage_measured_*` 改精确比值; 新键 `measurement_complete`(三态); 新函数 `pct_floor`; `coverage_note` 用 `pct_floor` |
| `ops/daily_summary.py` | `_finite()`; `realised_facts` NaN/inf ⇒ 不可观测(载体和与分币种切片); docstring/文案「已读部分」; `account_facts` 残差要求两端 `complete is True`(两条理由: 截断 / 标记缺失); `anchor_cost_facts.cost_measurement_complete`; 逐锚表 `CB.pct_floor` 显示 + `_cov_short` 按计数; 轮换块同完整性规则 |
| `ops/first_anchor_review.py` | §3c measured 行用 `pct_floor` + 「measurement complete: yes/NO」 |
| `ops/score_post_fix.py` | E6: `measurement_complete` 与 verdict 由桶推; `measurement_complete_source` / `m1_measurement_complete` / `completeness_disagrees_with_m1` / `c_bps_overall_is_finite` / `protective_flatten_buckets` / `protective_flatten_fee_known_by_buckets` / `protective_flatten_fee_disagrees_with_m1`; `rule` / `bucket_rule` 措辞更新 |
| `ops/gate_coverage.py` | `tests_readers_three_bucket` 盲区 (b) 改述(m1 冻结, E6 位由桶推) |
| `live/tests_daily_summary.py` | 53 → **64** checks: `_NAV` / `_INCIDENT` 夹具补 `realised_truncated: False`(生产者必写); [E3] 措辞; [R2-a..d] + 三条 MUTATION |
| `live/tests_readers_three_bucket.py` | 31 → **42** checks: [A] `measurement_complete` 三态 / NaN 费 / `pct_floor`; [B] 比较点 round(4); [D] 文案; [E] 一致性断言; [E-R1] NaN 费树 + flatten 混币费树 + MUTATION |

### 6b. 每测证明什么 (收据 `docs/receipts/w2_readers_three_bucket/newcode_*.log`; 旧码红 `oldcode_918559f_*_RED.log`)
| 测试 | 证明 | 旧码(918559f + 新测试) |
|---|---|---|
| DS [E1]×4 | USDT −0.30 + BNB −0.01 ⇒ usdt −0.30, unconverted [(COMMISSION, BNB, −0.01)], 文案不印 −0.31 为 USDT; 内联旧读 = −0.31 | KeyError `realised_observable` 于第一个新 check ⇒ 套件 rc=1 |
| DS [E2]×6 | None ⇒ realised.observable False / realised_today None / 残差 None + why「不可观测」/ 文案引用 source; wallet/equity 仍可观测; 内联旧读 = 0.0; 邻格(仅首行 None) | 同上 |
| DS [E3][E4][E5] | 截断 ⇒ complete False + 文案; 旧格式 ⇒ caliber legacy + 假定文案; 混窗 ⇒ MIXED; 真账本 09-12 08Z 行 usdt 218.4401 == 载体 218.4401, unconverted [] | 同上 |
| DS [F1]-[F4] | 费未知 ⇒ None / 桶 2 / 覆盖 0; **旧公式 −1.00 bps**; 全测 +3.00 == 旧; 邻格 fee None ⇒ 排除(旧 +6.50); 无 mid ⇒ unpriced; 成交 None ⇒ 下界 ≥50% | 同上 |
| DS [F5][F6] 真账本 | 08-05 12Z A1785931245: 103/103 费未知, None; **旧 −3.70 bps**; 09-12 08Z A1789201439: 185/185 已测, 新 == 旧 (+1.4917) | 同上 |
| RTB [A]×10 | `usable_px`/`known_fee`/`filled_abs` 边界; 8 行夹具四桶计数/名义/覆盖/bps; 0 已测 ⇒ 全 None; JSON 安全; 符号约定 | ImportError 前已复制模块, [A] 绿 |
| RTB [B]×4 | 与 `anchor_loop.neutrality_price` 三夹具逐键相等(bps 4 位); 旧读法 +10.00 vs 规则 None | 绿(规则本身没变) |
| RTB [C]×2 | 全测: `abs_bps == m1.c_bps_overall`, `bps == m1.c_bps_net_overall`; 费未知: m1 = 10.00 (含零费分母) vs 桶 None, `n_unmeasured_fee` 2 | 绿 |
| RTB [D]×7 | 复审屏 (exec 同 `tests_review_anchor_scoping` 法): 全费未知 ⇒ UNMEASURED 且无 TOTAL adverse(旧 `_leg` = −1.00); 全测 ⇒ +3.00 / 100% / 2/2; 混合 ⇒ +3.00 / 44% / 「fee-unknown 1 / $200.00, unpriced 1 / $50.00」; 未知成交腿 ⇒ §3 计数 + `>=` 下界; 其它套件钉的 5 个字串仍在 | **FAIL**: 旧屏印 `TOTAL adverse -1.00bps` / `+6.50bps ★ 1 row(s) carry NO fee`(费未知桶对旧码不可见) |
| RTB [E]×4 | E6 预注册键齐全, verdict 规则不变(False ⇒ FAIL), `c_bps_overall` 仍是数(1.8); `buckets` 费未知 3 / None; 全测树 verdict PASS 且 `bps_measured == m1.c_bps_net_overall`; JSON 往返 | KeyError `buckets` ⇒ rc=1 |
| RTB [F]×3 | 真账本 08-05: 12Z 103 费未知 None; 16Z 100 费未知 None; 04Z 79/79 已测 +7.8069 覆盖 1.0 | 绿(纯模块) |

### 6c. 真账本上的量化影响 (`receipts/w2_readers_three_bucket/real_ledger_profile.{py,out}`, `newcode_daily_summary_LIVE_960h.log`)
- 40 日窗 (`--since 960h`) 内 **19 锚**成本覆盖 < 100%: 2 锚(08-05 12Z / 16Z)覆盖 0 ⇒ 旧印 −3.70 / −1.68 bps, 新印 n/a + 「未测 103/103 (费未知 103)」; 其余 17 锚各含 1-5 笔未定价成交(覆盖 68%-99%), **数字与旧相同**(旧公式对未定价行也是双边排除), 只是覆盖第一次可见。
- 09-11/09-12 九锚全部 185/185 类 100% 覆盖, 新 == 旧 到 1e-9 (`real_ledger_profile.out`)。
- nav 行: 251 行中 realised None 0 行, 非 USDT 非空 0 行, 有 `realised_by_type_asset` 1 行(09-12 08Z) ⇒ 两个反例在真账本尚未发生(与研究员一致: 「本锚全 USDT」), 修的是能力不是既成事故。09-12 00Z/04Z 行是旧格式, 08Z 是新格式 ⇒ 24h 摘要的轮换增量现在明标「两端口径不同」。

### 6d. 电池 (克隆, `state/_w2_battery.log`; 摘要 `receipts/w2_readers_three_bucket/battery_summary.txt`)
| 项 | 值 |
|---|---|
| 运行 | 克隆 `/Users/haosiyu/cc_tmp/exec_w2`, `bash run_acceptance.sh`, 2026-09-12 **10:36:00Z → 10:51:26Z**(锚外, 避开 HH:20–35) |
| 结果 | **133 套件, 132 exit 0, 1 红 = `tests_env_loading`**(rc 1) ⇒ 脚本判 `ACCEPTANCE: NOT GREEN` |
| 唯一红的原因 | 克隆无 `.env`(派单明说不拷): 四个入口 `TELEGRAM_*` 在导入时未被填充(`ic_monitor` / `redeliver_alarms` / `unseed_rehearsal_halt` / `run_anchor`), 与本改动无关; 收据 `battery_20260912T103600Z_tests_env_loading_RED_no_env.log` |
| 本轮两套件在电池内 | `tests_daily_summary` ALL PASS 53 checks; `tests_readers_three_bucket` ALL PASS 31 checks(`battery_20260912T103600Z_tests_*.log`) |
| 电池所跑代码 | 与 6e sha 逐位相同(电池开跑前最后一次改动 = 覆盖列向下取整, 10:27:59Z; 电池后复核 8 文件 sha 不变) |
| 日志 | 逐套件 `exec_w2/state/acceptance/20260912T103600Z_*.log`(133 件); 表 `receipts/w2_readers_three_bucket/battery_summary.txt` |
| 电池外补跑(10:1x-10:3xZ, 新码) | `tests_review_anchor_scoping` 8/8 · `tests_reject_topup` 40 · `tests_fills_supersede` 19/19 · `tests_score_anchor_selection` ALL PASS · `tests_rehearsal_anchor` ALL PASS · `tests_static_names` ALL PASS · `tests_imports` ALL PASS · `gate_coverage` 133 套件全部有边界自述 |

### 6d-2. 电池 第二轮(复审收口后)
| 项 | 值 |
|---|---|
| 运行 | 克隆 `bash run_acceptance.sh`, 2026-09-12 **14:36:04Z → 14:52:42Z**(锚外, 避开 HH:20–35); 代码 = 6e 最终 sha, 电池后复核 6 文件 sha 不变 |
| 结果 | **133 套件, 132 exit 0, 1 红 = `tests_env_loading`**(克隆无 `.env`, 同第一轮; 收据 `battery_r2_20260912T143604Z_tests_env_loading_RED_no_env.log`) |
| 本轮两套件 | `tests_daily_summary` ALL PASS **64**; `tests_readers_three_bucket` ALL PASS **42** |
| 冻结 | `metrics_freeze` FROZEN_MATCH(`live/pilot_metrics.py` 未改) |
| 修前读者红 | 新测试 × 复审前读者(`exec_w2_prev`, 6e 第一轮 sha): `tests_daily_summary` rc 1, 8 条 FAIL(E3 措辞 / R2-a 残差 / R2-a MUTATION / R2-b 缺标记 / R2-c NaN / R2-c MUTATION / 两邻格) 后 `pct_floor` AttributeError; `tests_readers_three_bucket` rc 1, 覆盖精确性 FAIL 后 KeyError `measurement_complete`; 收据 `prereview_readers_tests_*_RED.log` |
| 日志 | 逐套件 `exec_w2/state/acceptance/20260912T143604Z_*.log`(133 件); 表 `receipts/w2_readers_three_bucket/battery_r2_summary.txt` |

### 6e. sha256 (最终 = 第二轮复审收口后; 与 6d-2 电池所跑代码一致; 第一轮的 sha 见 receipts/w2_readers_three_bucket/battery_summary.txt 同目录第一轮日志)
```
0d31d10a1353f4ba36702b22b8d0db94551f81dc884055ceb7b52e5e2375dfda  live/cost_buckets.py            (新)
f62e1f3beebd727cb55aeac8aa0036189a6ffe174804af394a90254d8be3e2d1  live/tests_readers_three_bucket.py (新)
c59971d33ce0697dd912553021fb9f370367a4c53d499f47ebe14c99c5bd2d71  live/tests_daily_summary.py     (origin/main f53a5bf1…)
2cead2155f855026dccac7ad5e83d80a9b8755f5fbfe0d6f321a90f20d8fc52b  ops/daily_summary.py            (origin/main 263e7635…, = 研究员 RESULT.md 冻结 sha)
147bff8afad605a8bae9488096f1e08baa930d6ece8863845c4194ae24f88f6b  ops/first_anchor_review.py      (origin/main e80cc0e5…)
35edf62b46ab7c20e6243648942b09bb401a58db962f446711d1c81d85b4824f  ops/score_post_fix.py           (origin/main c4b8eeaf…)
31106d2d839307120e0cbb55099ac3f671cf259ddebf1e1f59be4141bc1a1ed3  ops/gate_coverage.py            (origin/main 49b357d8…)
4a0e7ec0d9851b52ea22815c016c974dc865967cf0b8a58ec0213437af3b7ce1  run_acceptance.sh               (origin/main da9ac302…)
5ac7b16d0f97f2f8013da728ab18f4f3787bc17c2192c1dba63e64e637c08f1f  live/pilot_metrics.py           (未改; = check_metrics_freeze FROZEN_MATCH)
3794ecfda3d7a8398a8dda40c967c7dafc8aa42d66651a762017ed1b254a2de7  docs/receipts/w2_readers_three_bucket.diff (第三轮: 两测试文件 SKIP 改造后重生成)
```

### 6g. 第三轮 (2026-09-13, lead 新鲜克隆叠层落地测试 `exec_land_stack_20260912T162534Z`): 账本依赖格 ⇒ 声明 SKIP
- 复现(只读副本 `exec_land_copy`): 该树 pilot_log 只有 20260801(跟踪快照), W2 六文件与本克隆逐位相同 ⇒ **非代码交互**; 唯一红 = 既有格「per-anchor table … one row per anchor」(`OUT.count("Z ") >= 3` 代理, 需 24h 窗内 ≥3 锚), 59 checks 1 FAIL。
- 改法(W1 T9g 规则): 两套件加 `skip(name, why)` — 打「SKIP … no/short real ledger in this tree (clone): … — passes only in the run tree. This is NOT a pass.」, 不计入 checks 也不计 FAIL, 汇总行单列 SKIP 数。逐锚表格改为: 工具自报 `covered: N anchor(s)`; N ≥ 1 ⇒ 断言表行数**恰等于** N(比旧代理更强); N = 0 ⇒ SKIP。既有 NOT EXERCISED 格(Q2 / [C] 残差 / E5 / F5 / F6; RTB [F] ×3)统一为 SKIP。
- 计数: 本克隆(有账本, 09-13 跑): DS **64 checks + 1 SKIP**(Q2: 24h 窗内同日 nav 行 < 2) ALL PASS; RTB **42 + 0 SKIP**。新鲜克隆副本(无账本): DS **58 checks + 6 SKIP** ALL PASS(改前 59 checks 1 FAIL); RTB **39 + 3 SKIP** ALL PASS。收据 `newcode_tests_*.log` / `freshclone_noledger_tests_*.log` / `freshclone_noledger_tests_daily_summary_BEFORE_skip_RED.log`。
- 读者代码未动(6e 四个读者 sha 不变); 只改两个测试文件; `tests_static_names` / `gate_coverage` / `tests_imports` 复跑绿; 按 lead 指示未重跑全电池。

### 6f. 未闭合 / 明写
- pyflakes 对 `ops/first_anchor_review.py:35` `typing` 未用、`ops/score_post_fix.py:23` `List` 未用、`ops/gate_coverage.py:212-213` 重复键、`ops/daily_summary.py:194` `ext` 未用: **全部 origin/main 既有**, 本轮不动(`tests_static_names` 只查未定义名, 绿)。
- `pilot_metrics.m1` 分母含费未知行(E6 / §4-1 口径)未改 —— 判据, 需预注册; E6 的 `buckets` 使分叉可见。
- `ops/first_real_anchor.py:81` 仍打印 `realised_by_type` 原数 —— 未派单, 登记。
- 非 USDT 换算不在读者层; 读者只列原币种数量。
- 旧码红收据里 `tests_daily_summary` 是 KeyError 中止(rc=1), 不是逐条 FAIL 列表; 逐条数字对照由套件内联 MUTATION check 承担(旧公式在同夹具上的值: −0.31 / 0.0 / −1.00 / +6.50 / −3.70)。

## 8. ROUND 3 — 独立研究员 2026-09-13 §3.C 三缺陷收口 (W2b; 事实表先于代码)

> **命名对账**: §6g 的「第三轮」= 同日早些时候的 **SKIP 改造**(只动两个测试文件, 读者码 sha 不变)。本节 = 派单口径的 **round 3**, 即研究员 `REVIEW_code_and_research_2026-09-13` §3.C + 专项 `codex_followup_code_review_2026-09-13/monitoring/RESULT.md`(W2-N1/N2/N3)三条缺陷的收口。两者互不覆盖。
> **入口**: 复现装置 `docs/receipts/w2_readers_three_bucket/round3_defect_probe.py`(同一批夹具跑任意树, 自身不断言), 修前输出 `round3_defect_probe_PREROUND3_RED.out`, 修后 `round3_defect_probe_FIXED.out`。

### 8a. 事实表补格 (每格: 复现 → 新读法 → 测试 → 修前红)

| # | 研究员反例 | 我方复现(克隆, 冻结 m1 sha 5ac7b16d…) | 新读法 | 测试 / 修前红 |
|---|---|---|---|---|
| N1-a | `score_post_fix.py:404/414` —— 一行 `side=None`(schema 合法: `orders.required` 有 `side`, `not_null` 没有): 桶判完整 ⇒ **PASS**, 而 m1 因读不出 side 排空人口 ⇒ `c_bps_overall=None`。**PASS 旁边没有成本** | 复现: verdict PASS / complete True / m1 bit None / c None(`round3_defect_probe_PREROUND3_RED.out` DEFECT 1) | E6 新增**载体一致门**: PASS 必须同时满足 ① 人口同集 ② 两个口径的 bps 在**明写容差**内一致。此例 ①② 皆破 ⇒ **FAIL**, `why_not` 逐条点名 | RTB [E-R3] 4 格 + MUTATION R3(i): 轮二规则 `_verdict(complete_b)` 在同一棵树读 PASS。修前读者 KeyError `carrier_consistency` ⇒ rc 1 |
| N1-b | 再加一行正常行, 缺 side 那行滑点更大: m1 只测 1 行报 **3.0bps**, 同人口桶 **52.5bps**, E6 仍 **PASS** | 复现: 逐位相同的 3.0 / 52.5(同上) | 同上 ⇒ FAIL; 且**页面展示的数字换成桶的** `cost_bps_displayed`(与判决同人口), m1 的数留在 `c_bps_overall` 并标 `c_bps_overall_source` | RTB [E-R3]: 3.0/52.5 双数复现 + 展示位断言 + MUTATION R3(ii) |
| N1-c | 「加 finite 检查」不够 | 复现: 单行例 `c_bps_overall_is_finite=False`(finite 门能挡), 混合例 c=3.0 有限(挡不住) | 门 = **人口同集 + 值一致**, 不是 finite 检查 | RTB [E-R3] 显式断言这一点 |
| N1-d | (我方补) 人口相同而**符号约定**不同也不该 PASS: m1 按 `side` 定号, 桶按 `filled_notional` 符号 | 构造 `side='sell'` 而 `filled_notional>0`: 计数/名义/逐 regime 全同, `abs` 口径全同, **net 口径 +3.0 vs +1.0** | 值一致门对**两个口径**分别判 ⇒ FAIL | RTB [E-R3]: 证明值门不是人口门的推论 |
| N2 | `first_anchor_review.py:368` —— `ex` 先删掉未知成交行, `_leg` 再算完整性 ⇒ 屏上 **100% / 1/1 / measurement complete: yes**, 而全人口不完整 | 复现: 全人口桶 complete **False**, `ex` 过滤后 **True**; 屏幕逐字打 `measurement complete: yes`(`round3_defect_probe_PREROUND3_RED.out` DEFECT 2) | `_leg` 改收**全量行**(`mine`, 不是 `ex`)。`bucket_fills` 本就把未知成交行放在**任何桶之外**(分子分母都不进), 所以**已测数字逐位不变**, 变的只是 `n_unknown_fill` ⇒ `measurement_complete` False, 且同一行点名未知行 | RTB [D](iv) + MUTATION R3(iii): 同一批行在 `ex` 过滤下 complete True / 全量下 False。修前读者 2 格红 |
| N2-b | (我方补, 同形态低一层) taker `from_partial/from_reject` **分裂**也用 `ex`, 各自打自己的完整性标签 | 复现: 5 已测 + 1 未知成交 ⇒ 旧屏 `5/5 … complete: yes` | 分裂保留**两个人口且各自具名**: `_estimable` 仍吃已知成交行(它 `float(filled_notional)`, 吃不了 None), `_leg` 吃全量子人口 | RTB [D](v) 2 格; 修前读者 2 格红 |
| N3 | `daily_summary` —— 末日**当日累计**外部流直接去减**区间**权益变动: 同日两行, 权益/已实现未变, 两端 `external_flow_usdt` 都 1000(转账发生在窗口开始前) ⇒ 残差 **−1000** | 复现: `unexplained_computable=True`, 残差 −1000.0(`round3_defect_probe_PREROUND3_RED.out` DEFECT 3) | 残差的资金流项改为**区间差** `e1 − e0`。残差本就只在**同日**计算, 同日两端同一个 00:00Z 原点 ⇒ 差值精确。任一端非有限 ⇒ 区间流 UNKNOWN, **拒算**并说明。窗口口径(P0 的当日总额 + 覆盖天数)原样保留为**另一个事实** | DS [R3] 8 格: R3-a 反例(0.0 而非 −1000)+ MUTATION R3-a(旧式 −1000)+ R3-b 正控(真在窗口内的入金仍净 0, 且真有 +500 未归因时仍抓到)+ R3-c 非有限端拒算 + R3-d 跨日。修前读者 KeyError `external_flow_interval_usdt` ⇒ rc 1 |

**为什么两端 income 完整就够管住流的完整性**: `external_flow` 与 `realised_pnl` 出自同一次分页 `binance_broker.income_since`(L1996 `by_type.get("TRANSFER")`), 共用同一个 `truncated` 标记 —— 复审 W2-R2 已经要求两端 `complete is True`, 这一条同时覆盖本载体。**这不是「账户恒等式已证」**: 残差为 0 只说明我们能读的三项互相抵消, 任何这三项都不承载的movement(不在 `realised_components` 里的收入类型 / 现货划转)对它不可见。

### 8b. 载体一致门的定义(明写, 可复算)

`ops/score_post_fix.py` 模块级常量: `E6_CARRIER_BPS_TOL_BPS = 5e-4`, `E6_CARRIER_NOTIONAL_TOL_USDT = 0.01`, `E6_CARRIER_NOTIONAL_TOL_REL = 1e-9`。

| 门 | 断言 | 为什么是这个数 |
|---|---|---|
| 人口·计数 | `buckets.n_fills == m1.n_filled_orders` | 两个载体各自**自报**的人口大小; 不在读者层重写 m1 的筛选(冻结规则的第二份拷贝 = 第二个会漂移的东西) |
| 人口·质量 | `|buckets.notional_usdt − m1.filled_notional_total| ≤ max(0.01, 1e-9·max)` | m1 的分母 `round(...,2)`, 桶 `round(...,4)`; 0.01 = m1 的舍入步长 |
| 人口·逐 regime | 对 `m1.by_regime ∪ 桶分组` 的每个 regime 断言计数与名义 | 一进一出的**补偿性互换**能骗过池化计数, 骗不过逐 regime |
| 值·`abs` 口径 | `|buckets.abs_bps_measured − m1.c_bps_overall| ≤ 5e-4` | m1 的 bps `round(...,4)`(最大 5e-5) + 除法顺序差的 ulp; 5e-4 = 10×, 且比要抓的分歧(52.5 vs 3.0)小四个数量级 |
| 值·`net` 口径 | `|buckets.bps_measured − m1.c_bps_net_overall| ≤ 5e-4` | 符号约定分歧只在 net 口径显形(N1-d) |
| 三态 | 桶 `measurement_complete is None`(无成交)⇒ 一致性 = None ⇒ verdict UNDETERMINED, **不是 PASS** | 「两边都没测到」不是一致 |

`None`/`NaN` **永不**与任何值「一致」(`_agree` 先过 `_fin`) —— `None == None` 读成一致正是单行反例。判据本身没变(complete ⇒ 可比; 不 complete ⇒ 下界, 不比 9.0bps): 完整性从**必要且充分**降为**必要**, 这是**收紧**, 只能把 PASS 变成非 PASS。

### 8c. 真账本正控(最强的反向对照)

`ops/score_post_fix.score(root=state/live/pilot_log, day=20260912)` on A1789201439(收据 `round3_newcode_score_post_fix_LIVE_20260912.json`):

| 量 | cost_buckets | pilot_metrics.m1 | 判 |
|---|---|---|---|
| 成交笔数 | 185 | 185 | 同 |
| 名义 USDT | 11,883.468 | 11,883.47 | 差 0.002, 在 0.01 容差内 |
| `abs` 口径 bps | 11.794527851 | 11.7945 | 一致 |
| `net` 口径 bps | 1.491695638 | 1.4917 | 一致 |
| verdict | — | — | **PASS**(`consistent: True`, `why_not: []`) |

即: 在役形态的干净锚上, 新门**不改判**, 且真实舍入差(0.002 USDT)确实落在容差内 —— 容差是按真数据校准的, 不是猜的。`ops/first_anchor_review.py` 在同一锚上成本段**逐字不变**(diff 0 行; 该锚 0 个未知成交行); `ops/daily_summary.py --since 24h` 同窗残差 **+705.2366 与修前逐位相同**(该日当日累计 = 0, 区间 = 0), 新增的只是「区间内资金流」那一行。

### 8d. 变更 (file:line, 克隆内)

| 文件 | 变更 |
|---|---|
| `ops/score_post_fix.py` 33-72 | 新: `E6_CARRIER_*` 三个容差常量 + `_fin()` + `_agree()`(None/NaN 永不一致) |
| 同 428-517 | E6: `_legs` 具名; 载体一致门(人口计数/名义/逐 regime + 两口径值); `why_not` 逐条文案 |
| 同 输出键 | verdict 加与门; 新 `cost_bps_displayed` / `cost_bps_net_displayed` / `cost_bps_displayed_source` / `carrier_consistency{consistent,why_not,population,values,tolerance,rule}` / `c_bps_overall_source`; 旧键与 `rule` 文案更新(**预注册键一个没删**) |
| `ops/first_anchor_review.py` 367-386 | 全人口注释 + `_unk_rows`; 无已知成交时也点名未知成交行 |
| 同 `_leg` | 收全量行; `_unks` 文案; 未知行在三条打印路径上都点名 |
| 同 438-440 | 三条腿改从 `mine` 取(数字不变) |
| 同 474-492 | taker 分裂: `_tk_full` 与 `_tk` 两个人口各自具名; 子人口全未知时明说 |
| `ops/daily_summary.py` 218-239 | `_e0/_e1/_ext_iv/_ext_iv_why`(区间资金流) |
| 同 facts | 新 `external_flow_carrier` / `external_flow_interval_usdt` / `external_flow_interval_computable` / `external_flow_interval_why_not`; `unexplained_computable` 加区间可算条件; 残差改用区间流; 新拒算分支 |
| 同 `render_account` | 区间流一行(可算/UNKNOWN 两种); 残差句点名**区间**外部资金流 |
| `ops/gate_coverage.py` | 两个套件盲区各加 round 3 段(含 (g) 冻结 watchdog 未迁移) |
| `live/tests_readers_three_bucket.py` | 42 → **60** checks: [D](iv)(v) 5 格 + [E-R3] 13 格; `build_review_tree` 加 `sides=` 与未知 taker 腿 |
| `live/tests_daily_summary.py` | 64 → **73** checks(本树): [R3] 8 格 |
| `live/cost_buckets.py` | **未改**(规则没动; sha 与轮二相同) |
| `live/pilot_metrics.py` | **未改**, `check_metrics_freeze` = FROZEN_MATCH |

### 8e. 收据与计数

| 项 | 值 |
|---|---|
| 有真账本(克隆 `exec_w2`) | `tests_daily_summary` **73 checks / 0 SKIP** rc 0; `tests_readers_three_bucket` **60 checks / 0 SKIP** rc 0 |
| 无真账本(新鲜克隆形态 `exec_w2_noledger`) | DS **66 checks + 6 SKIP** rc 0; RTB **57 checks + 3 SKIP** rc 0(SKIP 机制原样保留, 2 check ↔ 1 SKIP 的条件格是差值来源) |
| 修前读者 × 新测试(`exec_w2_prev3` = 轮二 sha, 同一份账本副本) | RTB **rc 1**, 4 条 FAIL(全部 N2/N2-b 的屏幕文案)后 KeyError `carrier_consistency`; DS **rc 1**, KeyError `external_flow_interval_usdt`。收据 `round3_prereaders_tests_*_RED.log` |
| 邻格套件(新码) | `tests_review_anchor_scoping` 8/8 · `tests_reject_topup` 40 · `tests_fills_supersede` 19/19 · `tests_score_anchor_selection` ALL PASS · `tests_rehearsal_anchor` ALL PASS · `tests_static_names` ALL PASS · `tests_imports` ALL PASS · `gate_coverage` 133 套件全部有边界自述 · `check_metrics_freeze` FROZEN_MATCH |
| 研究员探针(回归; 跑在**他们的冻结副本**上, 看不到本轮改动) | `probe_followup.py` **rc 0** · `probe_causal_events.py` **rc 0**。二者仍断言旧行为(`no_side` PASS / `'measurement complete: yes'` / 残差 −1000), 因为它们读 `private/inputs/w2` 的冻结快照; 跑完把 `probe_results.json` 的时间戳还原(`git checkout --`), 研究员工作树净 |
| 全电池 | **未跑**(派单明说 lead 跑叠层电池) |

### 8f. sha256 (最终)
```
0d31d10a1353f4ba36702b22b8d0db94551f81dc884055ceb7b52e5e2375dfda  live/cost_buckets.py            (未改, = 轮二)
d0295d41dca149866fa785d0b3f9b5049ac85decbe0132c15985903b866c9d6e  live/tests_readers_three_bucket.py
79554aa9620e73a141bfe2c861417867280e6cf8182236c6910e644e40e8d13e  live/tests_daily_summary.py
e39689b56d1d79ead7415e1002529b1433c9d84790badfc2330fe22eed17371f  ops/daily_summary.py
9b51db9e5f6659e0040b8fde8ed58cfed5a6bd9e89456ffa5a572fd63f59dc43  ops/first_anchor_review.py
3c307356e8c6eeecec5ac3b21546fe5abf124839a36d3047aac71e51c0341277  ops/score_post_fix.py
1e8b0077fa428fe8b932b85338b955aa7a2fd8b35cbb1a06234cf2748c3b5965  ops/gate_coverage.py
4a0e7ec0d9851b52ea22815c016c974dc865967cf0b8a58ec0213437af3b7ce1  run_acceptance.sh               (未改)
5ac7b16d0f97f2f8013da728ab18f4f3787bc17c2192c1dba63e64e637c08f1f  live/pilot_metrics.py           (未改; FROZEN_MATCH)
6b9e5e86381a22bc43df40bf38b595b372424edeabbf91fbeea530ad8a0439fd  docs/receipts/w2_readers_three_bucket.diff  (ops/ live/ run_acceptance.sh only)
```

### 8g. R-12b 现状 —— **不得**写成「所有消费者已统一」

| 消费者 | 路径 | 本轮后 |
|---|---|---|
| `daily_summary` 成本列 | 全量行 → 桶 | 已迁移(轮一/轮二) |
| `first_anchor_review` §3c + taker 分裂 | 全量行 → 桶 | **本轮关闭**(N2 / N2-b) |
| `score_post_fix` E6 | 桶判位 + 桶展示数 + 对 m1 的载体一致门 | **本轮关闭**(N1): 不一致 ⇒ 不 PASS 且点名 |
| `watchdog` §4-1 | 直接吃 `m1.c_bps_net_overall` | **未迁移, 本轮未改, 且我方一手复现**: `watchdog.py:1188` 的 priced 掩码是 `[c is not None …]`, 阈值比较是 `c > C_LIMIT_BPS` —— `NaN is not None` 为真、`NaN > 9.0` 为假, 所以一个 NaN 成本被算作**已定价且未越线**, `blind` 仍是 False。改它 = 改 §4-1 判据输入 ⇒ 需预注册 + 用户裁定 |
| `check_prewindow_state` / `first_real_anchor` | 直接展示 `m1.c_bps_overall` / 完整性位 | **未迁移**(未派单, 登记) |

⇒ R-12b 的正确表述: **「入判的三个读者已绕开冻结 m1 的完整性位, 并且 E6 现在拒绝为不同人口的数字背书」**; 冻结看门狗与两个遗留入口**仍直接吃 m1**。

### 8h. 本轮明写不做 / 未闭合
- `pilot_metrics.m1` 的两处「已测」语义错(NaN 费 / 退出块混币费)与分母含费未知行: **未改**(冻结 + 判据)。
- `live/pilot_log.py` 的 orders schema 允许 `side: None`(`required` 有、`not_null` 无), `binance_executor.py:2148` 用 `p.get('side')` 写它 —— 这是 N1 反例的**生产者侧**成因。本轮**未改生产者**(改 schema = 改写入合同, 需另行派单); 读者层现在会因此拒绝 PASS 并点名。**没有证据说明真实计划产生过缺 side 的行**(研究员同结论)。
- 载体人口同集是按**两个载体各自自报的计数与名义质量**(池化 + 逐 regime)断言的, 不是按行 id: 计数与名义在每个 regime 都相等的两个不同行集合仍会通过。
- 区间资金流的正确性依赖「`external_flow_usdt` 是当日累计」这一载体事实(`anchor_loop.py:2822` ← `binance_broker.income_since` L1996); 读者层不重新推导它, 载体一改本文首行的作废条件生效。

## 9. ROUND 4 — 独立研究员第三轮 monitoring「NAV-R3-1」(继承, P2) + 同族 `x or 回退` 审计 (X2, 2026-09-13; 事实表先于代码)

> **入口**: `.claude/worktrees/codex-independent-20260907/docs/REVIEW_round3_code_and_research_2026-09-13.md` §3 W2 段 + `…/codex_round3_code_review_2026-09-13/monitoring/RESULT.md` §5 NAV-R3-1; 探针 `probe_w2_round3.py` sha `efcddf72…`, `audit_common.py` sha `c82ed83f…`。
> **命名对账**: 本节 = 派单口径 round 4。§8 (round 3) 的「日累计 → 区间流」修复不被本节撤销; 本节补的是 §8 没覆盖的**权益端点**与同族读法。
> **本节 9a–9c 写于改码之前**; 9d 起为结果。

### 9a. 复现 (改码前)
- 研究员探针原样拷到 scratchpad, **只改路径**(读研究员冻结输入, 收据写 scratchpad; 两处 diff 共 7 行, 全是 `OUT → OUT_SRC` 与 `W2` 可由环境变量改指)。冻结快照上 **rc 0**, 本克隆修前 **rc 0**; 两次 stdout 与研究员 `probe_w2_round3_success.log` **逐字节相同**。研究员工作树 `git status` 净。
- 同一输出里 NAV 四格: `equity_nan` 残差 NaN 且 computable True / `equity_none` −100 / `start_equity_none` 0.0 / `valid_zero_start_deposit` **−100**。
- 修前 7 个文件 sha 与 §8f 逐位相同; 修前树快照 `/Users/haosiyu/cc_tmp/exec_w2_prev4`(布局同 `exec_w2_prev3`)。

### 9b. 事实表 · 账户端点 (`ops/daily_summary.account_facts`, 行号 = 修前 e39689b5)

**载体核对**(读码 + 数只读账本副本 `exec_w2/state/live/pilot_log`, 251 nav 行 / 250 anchor 行 / 74,860 order 行 / 49,117 readback 行):

| 字段 | 生产者 | schema (`live/pilot_log.py`) | 可达取值 | 账本副本实测 |
|---|---|---|---|---|
| `nav` | `anchor_loop.py:2794` `nav=snap["equity"]` | daily_nav `not_null` | None 写不进(validate 拒); **NaN 写得进**(validate 只查 None, `json.dumps` 允许 NaN); **0 写得进**(空账户) | 有限 251 / 零 0 / None 0 / 非有限 0 |
| `wallet_balance` | `:2811` | 不在 `required` | 缺键 ⇒ `.get` 为 None | 有限 251 |
| `unrealised_pnl` | `:2810` | `required`, 可空 | None | 有限 237 / 零 14 |
| `external_flow_usdt` | `:2822` `None if inc is None` | 不在 `required` | None(income 读失败, 生产者同时发 HIGH) | 有限 26 / 零 225 |

⇒ **本轮每一格都是能力修复, 账本副本上没有一行触发**; 不把它写成已观察到的事故。

| # | 事实 | 取值 | 旧读法 | 新读法 | 测试(修前读者红 / 新读者绿) |
|---|---|---|---|---|---|
| N4-a | 首端权益**合法为 0** | 研究员夹具 `valid_zero_start_deposit`: nav 0→100, flow 0→100, 同日, 收入完整 | L217 `float(n0.get('nav') or eq)` ⇒ 首端被末端替换 ⇒ Δ权益 0 ⇒ 残差 **−100**, computable True; 渲染「非交易原因的权益变化 −100.0000」 | `_finite(0.0) = 0.0` 是值; Δ权益 +100; 区间流 +100; 残差 **0.0**, computable True; 不渲染残差句 | DS [R4] 格 + MUTATION(旧式同行 −100) |
| N4-b | 末端权益 NaN | `equity_nan` | L189 NaN 保留 ⇒ 残差 NaN, computable True; 渲染 `nan` | `equity` None, `equity_observable` False, 残差 None, computable False, why 点名「末行」+ `nan` + 不是有限数; `target_exposure` None; 恒等式 None; 渲染无 `nan` | DS [R4] + MUTATION(旧式 NaN 真值保留) |
| N4-c | 末端权益 None | `equity_none` | L189 `or 0.0` ⇒ 权益 0 ⇒ 残差 −100, computable True | 同 N4-b, why 带 `None` | DS [R4] + MUTATION |
| N4-d | 首端权益 None | `start_equity_none` | L217 首端被末端替换 ⇒ 残差 0.0 (一个不是测量的 0), computable True | computable False, 残差 None, why 点名「首行」 | DS [R4] + MUTATION |
| N4-e | 首端权益 ±inf | 邻格 | 残差 ∓inf / NaN | 同 N4-d | DS [R4] 邻格 |
| N4-f | 正常行 | [B] `_NAV` 与研究员 `prior_1000_both` / `same_day_transfer_20` | — | **逐字段不变**: `equity` / `wallet` / `unrealised` / `equity_change` / `target_exposure` / 恒等式 / 残差 = 旧公式在同行上的值 | DS [R4] 反向对照 |
| N4-g | 末端 wallet None | `wallet_balance=None`, nav 有限 | L187 `or 0.0` ⇒ 恒等式残差 = nav ⇒ `holds` False ⇒ 渲染「这个恒等式不该被破坏」(假警报) | `wallet` None; 恒等式 `holds` None + `equity_identity_why_not`; 渲染「无法核对」; 残差不依赖 wallet, 照算 | DS [R4] + MUTATION |
| N4-h | 末端 unrealised 合法 0 | 账本 14 行 | `0.0 or 0.0` 碰巧对 | 0.0 是值, 恒等式照算 | DS [R4] 反向 |
| N4-i | 某日**末行**资金流 NaN | 单行 NaN | L211 `is not None` 放过 ⇒ 窗口总额 NaN ⇒ `external_flow_state` **outflow**(NaN 与 0/1e-9 比较皆假), 渲染 `+nan` | 该日未知 ⇒ 窗口总额 None ⇒ `not_observable`; 新键 `external_flow_unknown_days` | DS [R4] + MUTATION |
| N4-j | 某日末行资金流 None, **前面有有限行** | 同日 [36.82261, None] | L212 跳过 None ⇒ 早先一行的累计**代替整日** ⇒ inflow 36.82261 | 当日累计由**末行**决定 ⇒ 该日未知 ⇒ 总额 None; 已知日照列 | DS [R4] + MUTATION |
| N4-k | 前面 None, 末行有限 | 同日 [None, 36.82261] | 36.82261 | 36.82261(末行是 00:00Z 起累计, 前面的缺口不丢东西) | DS [R4] 反向 |
| N4-l | 跨日, 后一日末行 None | [D1: 36.82261, D2: None] | 36.82261 inflow(整日被静默丢掉) | 总额 None; `external_flow_by_day` = {D1: 36.82261}; unknown [D2] | DS [R4] 邻格 |

**分支顺序**(残差拒算理由只点名第一条): 跨 00:00Z → **权益端点不可观测(新)** → 已实现不可观测 → 已实现不完整 → 区间流未知 → 计算。权益放第二, 因为残差的第一项就是 Δ权益。**不变式**: `unexplained_computable is True` ⇒ 残差是有限数(每个 [R4] 格断言)。

### 9c. 同族审计 (AST 扫描两文件每个 `a or b` 与裸真值判断; 扫描器 `receipts/w2_readers_three_bucket/round4_or_truthiness_scan.py`)

**改(数值字段: 费 / 名义 / NAV / 流, 与同行权益分量)**, 全部在基线 918559f 已存在(继承):

| # | 位置(修前行号) | 旧读法 | 旧读法的错 | 新读法 | 测试 |
|---|---|---|---|---|---|
| N4-a..e | `daily_summary.py` L187-189, L217, L246-247, L261, L285-290 | `or 0.0` / `or eq` | 见 9b | 见 9b | DS [R4] |
| N4-i..l | `daily_summary.py` L209-214 | `is not None` + 早行代替 | 见 9b | 末行决定, 非有限 = 未知 | DS [R4] |
| N4-m | `daily_summary.py` L136 `anchor_cost_facts` maker `intended_notional or 0` | None ⇒ 分母变小 ⇒ 成交率偏高且不标; NaN ⇒ 率 NaN 印 `nan%` | 任一 maker 行意图非有限 ⇒ `maker_fill_rate_pct` None(n/a) + `maker_n_unknown_intended`; 合法 0 仍是值 | DS [R4] + MUTATION |
| N4-n | `daily_summary.py` L492 逐锚表 `target_gross or 0` | None ⇒ 印 0; NaN ⇒ 印 nan | 印 n/a | DS [R4-E2E] 原链 |
| N4-o | `daily_summary.py` L521-522 轮换块 `unrealised_pnl or 0` | None ⇒ 印 +0.0000 | 印 不可观测 | DS [R4-E2E] 原链 |
| F4-a | `first_anchor_review.py` L299 §3b `venue_position_notional or 0.0` | None(裸行)⇒ 未知仓位当平; NaN ⇒ net/gross NaN, net/equity NaN ⇒ 带宽「★★ ABOVE 15%」**假警报** | 非有限行排除并计数; VENUE 行只覆盖已知行并点名; 有未知行 ⇒ 带宽 NOT JUDGED | RTB [D-R4] |
| F4-b | 同 L302/L310 §3b `nav` 真值 | 0 ⇒ 说成「cannot be formed」(理由像缺失); NaN ⇒ 真值通过 ⇒ 带宽「★★ ABOVE 15%」**假警报** | None/NaN/inf ⇒ NOT OBSERVABLE(带 repr); 0 ⇒ 除以零无定义; 有限非零不变 | RTB [D-R4] |
| F4-c | 同 L320/L338/L343 §3b INTENT `target_gross or 0.0`, `if tg`, `tg or 1` | NaN ⇒ INTENT `nan`; None(裸行)⇒ INTENT +0.00 且 VENUE−INTENT = 整个 venue net; 0 ⇒ 比率印 +0.00%(0/0) | 非有限 ⇒ INTENT UNKNOWN, 不印差; 0 ⇒ INTENT 0.00, 比率 n/a | RTB [D-R4] |
| F4-d | 同 L241 §3 每名名义 `target_gross or 0` | NaN ⇒ `~$nan`; None ⇒ `~$0.00` | UNKNOWN | RTB [D-R4] |
| F4-e | 同 L214/L219 §3 `filled_notional not in (None, 0, 0.0)` / `is None` | NaN ⇒ 记为非零成交且不记为未知; §3c 的 `CB.filled_abs` 把同一行记为未知 —— 一件事实两种读法 | 两行都用 `CB.filled_abs` | RTB [D-R4] |
| F4-f | 同 L545 §3c maker 成交率分母 `intended_notional or 0.0` | None ⇒ 分母变小 ⇒ 率偏高不标; NaN ⇒ 分母 NaN ⇒ 印「no maker leg was submitted」(理由错) | 任一已提交 maker 腿意图非有限 ⇒ UNMEASURED + 计数; 合法 0 是值 | RTB [D-R4] |
| F4-g | 同 L263/L270-272 §3 有效下限表 `mid_at_anchor` 真值 / `min_notional or 0` / `min_qty or 0` / `intended_notional or 0` | min_qty 缺 ⇒ 0 ⇒ binding「min_notional」; min_notional 缺 ⇒ declared $0.0; NaN mid 过真值 ⇒ binding「min_notional」; 意图 None ⇒ `$0.00` —— 皆为**像真的错数** | mid 走 `CB.usable_px`; 过滤器 / 意图非有限 ⇒ n/a, binding UNKNOWN。缓存副本 658/658 symbol 两过滤器有限 | RTB [D-R4] |
| F4-h | 同 L282 §3 持仓名数 `venue_position_qty or 0` | NaN / None ⇒ 记为未持仓 | 未知数量单列计数 | RTB [D-R4] |

**不改(看过, 理由逐条)**:
- 容器 / 文本回退(`or {}` / `or []` / `or ""` / `src or 'not stated'` / `realised_components or _REALISED_TYPES`): 非数值。
- `daily_summary` L98 / L106 / L107 / L253 与渲染 L356-358 的 `by_type` / `by_type_asset` 缺键取 0: 载体 `binance_broker.py:1977-1986` 按**观测到的收入行**累加成**稀疏**和, 缺键 = 该类型/币种无收入行 = 真 0; 其前提(读取完整)由 `realised_truncated` 另行承载。不是回退。
- `daily_summary` L137 `CB.filled_abs(o) or 0.0` 与 L146 `if want`: 未知成交已由 `maker_n_unknown_fill` 计数并把率标成下界(轮一); want 为 0 ⇒ 率 None(除零无定义)。有意且有标。
- `daily_summary` L391 `abs(f["unexplained_equity_change"] or 0)`: 只在 `unexplained_computable` 为真时执行; 本轮使 computable ⇒ 残差有限(每格断言), `or 0` 无从替换。保留。
- 时间戳 `anchor_ts or 0` / `nav_ts or 0` / `ts or 0`(`daily_summary` L425 L428 L442 L466)、`anchor_ts or -1`(`first_anchor_review` L165, **tests_review_anchor_scoping [B] M1 逐字注入靶**): 窗口 / 锚选择, 非金额量。
- **登记, 不改**: `daily_summary` L428 `[...] or nav_all[-1:]` —— 窗口内无 nav 行时, 账户段显示账本最新一行却不说它在窗口外。这是「过期行代替窗口」, 与数值三态不同族, 超出本派单; 登记待 lead 裁定。
- `first_anchor_review` L461 `_estimable` 的 `or 1.0`: 行来自 `ex`(已知非零成交), 和恒 > 0, 死回退; 常量行被 `tests_reject_topup [J]` 钉住。
- `first_anchor_review` L505 `if r.get("intended_limit_px")`: 价格字段; 选中行随后都过 `CB.usable_px` 并计数未定价(轮一); 无限价行不进「vs OUR OWN LIMIT」表是显式范围, 不产出假数。
- `first_anchor_review` L584 停机态 `tripped_at or reduce_only`: 时间戳 / 布尔, 且不可读按 HALTED; 非金额。L663 `weight or 0`: 限频权重, 非金额。
- **登记, 不改**: §3b INTENT 的 `target_w`(L323-324 `is not None` 后 `float`): 非 `or`/真值位点, 也不是费/名义/NAV/流; NaN 权重印出可见的 `nan` 而非像真的数; 账本副本 74,860/74,860 有限。

### 9d. 变更 (file:line = 克隆 `/Users/haosiyu/cc_tmp/exec_w2` 最终版; diff 限 ops/ live/ run_acceptance.sh)

| 文件 | 行 | 变更 | 格 |
|---|---|---|---|
| `ops/daily_summary.py` | 136-155 | `anchor_cost_facts`: maker 意图逐腿 `_finite`; 任一非有限 ⇒ `maker_fill_rate_pct` None、`maker_intended_usdt` None; 新键 `maker_n_unknown_intended` | N4-m |
| 同 | 195-221 | `account_facts`: `wal` / `unr` / `eq` / `eq0` 走 `_finite`; `_not_finite` 理由(行位 + 键 + repr); `_eq_why`(Δ权益理由)、`_snap_whys`(末行快照理由) | N4-a..e, g |
| 同 | 241-253 | 当日资金流: `_day_last` 末行决定, `_flow_unknown_days`; 任一未知日 ⇒ `ext_f` None; `d_eq` 两端有限才算 | N4-i..l |
| 同 | 281-291, 305, 315, 331-335 | 新键 `equity_observable` / `equity_start` / `equity_start_observable` / `account_snapshot_why_not` / `equity_identity_why_not` / `external_flow_unknown_days` / `equity_change_why_not`; `equity_identity_residual` / `holds` / `target_exposure` / `equity_change` 三态; `unexplained_computable` 加 `d_eq is not None` | N4-a..l |
| 同 | 344-349 | 新拒算分支(权益端点不可观测), 排在跨日之后、已实现之前 | N4-b..e |
| 同 | 391-409, 430-440 | `render_account`: `_num` 印「不可观测」; 快照理由逐条; 恒等式 None ⇒「无法核对」; 目标敞口 None 句; not_observable 资金流附未知日与已知日 | N4-b, c, g, l |
| 同 | 542, 554-555, 564 | `main` 逐锚表: gross 非有限 ⇒ n/a; 备注「意图未知k行」 | N4-m, n |
| 同 | 593-596 | `main` 轮换块: 浮动两端非有限 ⇒「不可观测」 | N4-o |
| `ops/first_anchor_review.py` | 97-108 | 新 `_fin()`(与 `daily_summary._finite` 同式) | — |
| 同 | 228-237 | §3: `cost_buckets` 导入上移到 §3; 非零成交 / 未知成交两行都用 `CB.filled_abs`(§3c L458 留注释) | F4-e |
| 同 | 258-268 | §3 每名名义: target_gross 非有限 ⇒ UNKNOWN | F4-d |
| 同 | 286-319 | §3 有效下限表: mid 走 `CB.usable_px`; 过滤器 / 意图非有限 ⇒ n/a + binding UNKNOWN; 已知意图在前; **自审追加**: 未入表的 skipped maker 行计数(L315-319) | F4-g |
| 同 | 324-330 | §3 持仓名数: 数量非有限单列计数 | F4-h |
| 同 | 346-386 | §3b: readback 名义非有限行排除并计数; 权益三态(None/NaN/inf、0、有限非零); 有未知行 ⇒ 带宽 NOT JUDGED | F4-a, b |
| 同 | 388-420 | §3b INTENT: target_gross 非有限 ⇒ UNKNOWN 且不印差; 0 ⇒ 比率 UNDEFINED | F4-c |
| 同 | 622-642 | §3c maker 成交率: 已提交腿意图非有限 ⇒ UNMEASURED + 计数; **自审追加**: 已提交腿意图全为 0 ⇒ UNDEFINED(旧式印「no maker leg was submitted」) | F4-f |
| `ops/gate_coverage.py` | 159, 160 | 两个套件的盲区自述各加 round 4 段: DS (g) 能力格 / (h) 过期 nav 行回退登记; RTB (h) not_null 列的 None 由共用读法覆盖、非夹具行 / (i) `target_w` 登记 | — |
| `live/tests_daily_summary.py` | 451-806 [R4] / 807-832 [R4-F] / 833-918 [R4-E2E] | **+35 格**: 25 单元格(研究员 nav 夹具原样 + 邻格 + 反向 + 不变式) / 4 成交率分母格 / 6 原链格(`main` 在两棵临时账本树上, 子进程) | 9b 全部 |
| `live/tests_readers_three_bucket.py` | 404-608 [D-R4] | **+15 格**: 8 棵临时树 × `first_anchor_review` 全文件 exec(同 [D] 的 `run_review`) | F4-a..h |
| `live/cost_buckets.py` / `ops/score_post_fix.py` / `run_acceptance.sh` / `live/pilot_metrics.py` | — | **未改**(sha 同 §8f; `check_metrics_freeze` = FROZEN_MATCH) | — |

**两处自审追加的来由**(事实表之后、按「列出每个 continue/return 出口并问它丢了哪件事实」): ① 下限表的 `continue` 本来就会静默丢掉无缓存条目的名字, 本轮让 NaN mid 也走这条出口 —— 而本文件自己的首条原则是「IT REPORTS ABSENCE AS ABSENCE」, 所以计数; ② 成交率的 `else` 把「有已提交腿但意图全为 0」也说成「没有提交」—— 0 是值, 不是缺席。二者皆有红-绿格(F4-g (ii) / F4-f (ii))。

**测试装置的两点说明**: round-4 格经 `_ok` / `_ex` 求值 —— 单格异常只记该格 FAIL 并在段尾点名, 不中止套件, 所以「新测试 × 修前读者」给出逐格红表而不是停在第一个 KeyError; 每格先断言**两版读者都写的键**上的实质量, 新记录字段单独成「(new record field)」格, 反向格只读旧键、必须在两版上都绿。

### 9e. 计数与版本配对 (收据 `receipts/w2_readers_three_bucket/round4_*`; 汇总 `round4_run_summary.txt`, 07:54:20Z → 07:55:22Z, 跑前跑后 9 文件 sha 相同)

| 树 | `tests_daily_summary` | `tests_readers_three_bucket` |
|---|---|---|
| 克隆 `exec_w2`(有账本副本) | **106 checks + 2 SKIP, rc 0** | **75 checks + 0 SKIP, rc 0** |
| `exec_w2_noledger`(新鲜克隆形态, 无账本) | **101 checks + 6 SKIP, rc 0** | **72 checks + 3 SKIP, rc 0** |
| 修前读者 `exec_w2_prev4` × 新测试 | **rc 1, 29 FAIL**(全在 [R4] / [R4-F] / [R4-E2E]), 77 OK | **rc 1, 12 FAIL**(全在 [D-R4]), 63 OK |

- **有账本的 2 个 SKIP 是墙钟, 不是本轮**: 同一时刻修前树跑 round-3 测试也是 71 checks + 2 SKIP(收据 `round4_prereaders_round3tests_tests_daily_summary_wallclock_SKIP.log`) —— 账本副本最新 nav 行 09-12 08:45Z 已滑出 24h 窗, Q2 与 [C] 残差格按 SKIP 机制声明。§8e 的 73/0 取于 09-13 更早时刻。71 + 35 = 106。
- 修前读者上 **只有两格抛异常**(两个 `(new record field)` 格, KeyError `equity_start`), 其余 27 个红格按**值**判红; 两版皆绿的是 6 个反向/原链格(R4-f ×2、R4-h、R4-k、意图 0、E2E-1 exit 0)与 RTB 的 3 格(全有限 §3b、全有限下限表行、钉住字串)。

| 格 | 修前读者实际输出(红格收据里的 extra) | 新读者 |
|---|---|---|
| R4-a 研究员 0→100 | computable True, 残差 **−100.0**, Δ权益 0.0 | True, **0.0**, Δ权益 +100.0 |
| R4-b 末端 NaN | True, **NaN** | False, None, 理由「窗口末行的 `nav` 不是有限数 (nan)」 |
| R4-c 末端 None | True, **−100.0** | False, None, 理由带 `None` |
| R4-d 首端 None | True, **0.0** | False, None, 理由「窗口首行」 |
| R4-e ±inf | (True, −inf) ×2 | False ×2 |
| R4-g 末端 wallet None | holds **False**, 恒等式残差 100.0, wallet 0.0 | holds None「无法核对」, wallet None, 残差照算 0.0 |
| R4-i 流 NaN | state **outflow**, NaN | not_observable, None |
| R4-j [36.82261, None] | **36.82261 inflow** | None, not_observable |
| R4-l 跨日 D2 末行 None | 渲染「+36.82 [覆盖 1 天]」 | None; 页面 UNKNOWN + D2 未知 + D1 已知 |
| R4-m 意图 None | 成交率 **100.0**, 意图 100.0 | None, None, 计数 1 |
| 意图 NaN 邻格 | 率 **nan** | None |
| E2E-1 原链 | 「★★ 非交易原因的权益变化 **−100.0000**」; gross 列 **nan**; 「浮动 +0.0000 → **+0.0000**」 | 无残差句; gross **n/a**; 「+0.0000 → 不可观测」 |
| E2E-2 原链末端 NaN | 「权益 (equity/nav) **nan**」「目标敞口 = nan × 2.00 = nan」; **无**拒算句 | 两行「不可观测」; 拒算句点名末行 nav |
| F4-a readback NaN | 「VENUE net **+nan** / gross nan」「net/equity +nan% => **★★ ABOVE 15%**」 | 排除并计数; −100 / 900; NOT JUDGED |
| F4-h 数量 NaN | 「2 of 3 read back」无注 | 附「1 row(s) with UNKNOWN venue_position_qty」 |
| F4-b 权益 NaN | 「net/equity +nan% (equity nan) => **★★ ABOVE 15%**」 | NOT OBSERVABLE (nan) |
| F4-b (ii) 权益 0 | 「daily_nav.nav — net/equity cannot be formed」(缺席措辞) | 「is 0 — UNDEFINED (division by zero), so no band is judged」 |
| F4-c target_gross NaN | 「INTENT net **+nan**」「VENUE minus INTENT: **+nan**」 | INTENT UNKNOWN, 不印差 |
| F4-c (ii) target_gross 0 | 「( **+0.00%** of target_gross)」 | 「ratio UNDEFINED — target_gross is 0」, 差照印 −100.00 |
| F4-d 每名名义 | 「**~$nan**」 | UNKNOWN |
| F4-e 成交 NaN | 非零 **3** / 未知 **0** | 2 / 1(与 §3c 同读法) |
| F4-f 意图 None | 「maker fill-rate (notional) **>= 75.00%**」 | UNMEASURED: 1 of 3 |
| F4-f (ii) 意图全 0 | 「**no maker leg was submitted**」 | 「intended notional of 0 — fill-rate UNDEFINED」 |
| F4-g 下限表 | YYY「min_qty x px $ **0.00** binding: **min_notional**」; VVV「$ **nan** binding: min_notional」; WWW「intended $ **0.00**」 | YYY n/a + UNKNOWN; VVV 不入表并计数; WWW n/a |

**邻格套件(最终码)**: `tests_review_anchor_scoping` 8/8(逐字注入靶未动)· `tests_reject_topup` 40 · `tests_fills_supersede` 19/19 · `tests_score_anchor_selection` ALL PASS · `tests_rehearsal_anchor` ALL PASS · `tests_static_names` ALL PASS · `tests_imports` ALL PASS · `check_metrics_freeze` FROZEN_MATCH · `gate_coverage` 133 套件全部有边界自述。**全电池未跑**(派单: lead 跑叠层)。

### 9f. 研究员探针回归 (收据 `receipts/w2_readers_three_bucket/round4_probe_regression/`, 逐字命令与 rc 见其 `COMMANDS.txt`)

原探针**不在原地跑**: 它把 `w2_receipt.json` 写进研究员证据目录。拷贝只改路径 —— `audit_common.py` 7 行(`OUT_SRC` = 研究员 monitoring 目录, 冻结输入与清单 sha 校验照旧; `OUT` = 收据目录; `W2` 可由 `REGRESS_W2` 改指), 探针 2 行(两处 `C.OUT/private/...` → `C.OUT_SRC/private/...`), 断言逐字节不变。

| # | 探针 | 被测树 | rc | 结果 |
|---|---|---|---|---|
| 1 | 原断言 | 研究员冻结快照 | **0** | stdout 与 `probe_w2_round3_success.log` 逐字节相同 |
| 2 | 原断言 | 修前树 `exec_w2_prev4` | **0** | 同上, 逐字节相同 |
| 3 | 原断言 | **修后克隆** | **1** | 第 121 行 `assert nav['equity_nan']['unexplained_computable'] and math.isnan(...)` 失败 —— 之前全部断言(E6 旧例、容差边界、两个载体 mock、1,200 人口成员检查、真锚 185 笔、255 行事故、首锚屏、四个资金流格)在修后克隆上通过 |
| 4 | 合同式(第 121-122 行两条编码缺陷的断言换成 round-4 合同 + 版本配对: 918559f 与 0158f5d1 仍须复现缺陷) | **修后克隆** | **0** | stdout 与研究员日志只差 `nav_residuals` 四行: equity_nan / equity_none / start_equity_none → null, valid_zero_start_deposit −100.0 → **0.0** |
| 5 | 合同式 | 研究员冻结快照 | **1** | 第 122 行失败(负控) |
| 6 | 合同式 | 修前树 `exec_w2_prev4` | **1** | 第 122 行失败(负控) |

研究员工作树跑后 `git status --short` 0 行。

### 9g. sha256 (最终; = `round4_sha_after.txt`)
```
0d31d10a1353f4ba36702b22b8d0db94551f81dc884055ceb7b52e5e2375dfda  live/cost_buckets.py            (未改)
e4e57b5beb8fb34201733cb335a58ae50408bec081b085a39e71712f73be7f3f  live/tests_daily_summary.py
0bb56e0cabdd7030d84274001a7e90c4da7c5835d63b35d8b8583c9e60317813  live/tests_readers_three_bucket.py
bf4151a8365c3c8224842c0fb00aae658332e20020d1792b9419afbe7d9eea8f  ops/daily_summary.py
18e8ad8cdfb978fbd819262b964293289adb56a72a6fef4be0596fdec4d54a70  ops/first_anchor_review.py
cee4a48cd963487900c625e094170438144b0275eb53842dcf44af86b21e64e6  ops/gate_coverage.py
3c307356e8c6eeecec5ac3b21546fe5abf124839a36d3047aac71e51c0341277  ops/score_post_fix.py           (未改)
4a0e7ec0d9851b52ea22815c016c974dc865967cf0b8a58ec0213437af3b7ce1  run_acceptance.sh               (未改)
5ac7b16d0f97f2f8013da728ab18f4f3787bc17c2192c1dba63e64e637c08f1f  live/pilot_metrics.py           (未改; FROZEN_MATCH)
2ad1c27203b5726aecd0feb3add9ffb7b865168d5ebb674208e72d6ad3ce802c  docs/receipts/w2_readers_three_bucket.diff  (ops/ live/ run_acceptance.sh only)
```
diff 校验: 三个未改文件的 diff 段与上一版 diff(`6b9e5e86…`)逐字节相同(生成命令一致); `git archive 918559f` 解出基线 + `git apply` 本 diff ⇒ 8 个文件与克隆逐字节相同。

### 9h. 本轮明写不做 / 未闭合
- **能力修复, 非既成事故**: 账本副本 251 nav 行 / 250 anchor 行 / 74,860 order 行 / 49,117 readback 行里, nav、wallet、target_gross、readback 名义与数量、意图名义均无 None 与非有限值, 无 0 权益(收据 `round4_ledger_numeric_census.out`); 交易所缓存副本 658/658 symbol 两个过滤器有限。未观察到任何一格在真实日发生。
- **影响面**: 两个只读报表(每日摘要、首锚复审屏); 未发现交易处置或看门狗读取这些字段(与研究员 monitoring §5 的消费者搜索一致, 本轮未另做全仓消费者普查)。
- **登记, 未改**: `daily_summary` 窗口内无 nav 行时 `or nav_all[-1:]` 回退到账本最新行且不声明在窗外(过期行, 不同族); §3b INTENT 的 `target_w` `is not None` 跳过(NaN 印可见 nan); 两者见 9c 与 `gate_coverage` 盲区。
- **不变的保留项**(§8g/§8h 原样): 冻结 `pilot_metrics.m1` 与看门狗 §4-1 仍直接吃 m1 —— 「所有消费者已统一」仍然**不得**写。
- 未提交 / 未推送 / 未部署; 运行目录 `~/dl_quant_live` 与 `~/wide_shadow` 未写; 未读 `.env`; 无网络。
