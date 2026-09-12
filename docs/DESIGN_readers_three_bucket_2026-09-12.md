# DESIGN · 下游读者三桶迁移: daily_summary / first_anchor_review / score_post_fix (事实表先于代码)

> **创建:** 2026-09-12 10:1xZ | **Session:** W2 (team lead 派单; 隔离克隆 `/Users/haosiyu/cc_tmp/exec_w2`, 分支 `fix/readers-three-bucket`, 基线 `origin/main` = 918559f) | **状态:** 完成(码在克隆分支 `fix/readers-three-bucket`, 未提交/未推送/未部署; 电池 132/133, 唯一红 = 克隆无 .env); §6 RESULT 含收据 | **作废条件:** 收入载体(`binance_broker.income_since`)改变 `by_type_asset` / `non_usdt_assets` 合同, 或 `anchor_loop.neutrality_price` 的三桶规则改变(本文 §3.2 的相等断言会先红)

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
| A2 | 已实现**不可观测** | `realised_pnl is None`(inc None) | `or 0.0` ⇒ realised_today=0.0, observable=True, **且**同日残差用 0 算出一个数 | `realised.observable=False`, `realised_today=None`, `unexplained_computable=False` + why 指明「已实现不可观测」; 文案「不可观测 —— <realised_pnl_source>」 | 研究员反例: realised_pnl=None ⇒ 旧 0.0/True; 新 None/False; 反向: 有数的行 observable True; 邻格: 只有 n0 不可观测时增量也不算 |
| A3 | 已实现**不完整**(分页截断) | `realised_truncated is True` | 未读 | `realised.complete=False`, 数字保留但标「不完整读取(下界), 非当日总额」 | 截断行 ⇒ complete False + 文案; 反向 False ⇒ complete True; None ⇒ complete None(未知) |
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

## 6. RESULT (2026-09-12 10:3xZ; 克隆 `/Users/haosiyu/cc_tmp/exec_w2` 分支 `fix/readers-three-bucket`, 基线 origin/main 918559f; **未提交, 未推送, 未部署**)

### 6a. 变更 (file:line, 克隆内; diff = `docs/receipts/w2_readers_three_bucket.diff`, 8 文件 +1013/−72, 排除 state/)
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

### 6e. sha256 (最终, 与 6d 电池所跑代码一致)
```
414606eef2852d381e7fbd5ff07b9a7c194ec5b7eedaba60603952016341ee7b  live/cost_buckets.py            (新)
46c25bb28306255e5666c3b4f5fa309037a1bb8adb124c69182d537b4c99d11b  live/tests_readers_three_bucket.py (新)
c297b8f9fbe7ea40153ba3bc95b0bca02dec22289550ce8a72e21aa086fbd6a2  live/tests_daily_summary.py     (origin/main f53a5bf1…)
20b2d73602bb0720f129ab2a1b98db7fc8a356a253c5e0815277bd4fca0fead9  ops/daily_summary.py            (origin/main 263e7635…, = 研究员 RESULT.md 冻结 sha)
a538ef25096de6c3c0417fbaf1c3bcc384dd60f343a8eefc67e4104a2865a894  ops/first_anchor_review.py      (origin/main e80cc0e5…)
1e402279c142cb9a45ae5df5423329e9b06a84177746621f7b0f441639ef279b  ops/score_post_fix.py           (origin/main c4b8eeaf…)
9b17dc70c619034613ab3c8505241270a840311e2fcf2565d6f968e796922012  ops/gate_coverage.py            (origin/main 49b357d8…)
4a0e7ec0d9851b52ea22815c016c974dc865967cf0b8a58ec0213437af3b7ce1  run_acceptance.sh               (origin/main da9ac302…)
fded2c21809601a3460456fe89ec11d53ec6cfd785b85ed5cb4a620231ce129f  docs/receipts/w2_readers_three_bucket.diff
```

### 6f. 未闭合 / 明写
- pyflakes 对 `ops/first_anchor_review.py:35` `typing` 未用、`ops/score_post_fix.py:23` `List` 未用、`ops/gate_coverage.py:212-213` 重复键、`ops/daily_summary.py:194` `ext` 未用: **全部 origin/main 既有**, 本轮不动(`tests_static_names` 只查未定义名, 绿)。
- `pilot_metrics.m1` 分母含费未知行(E6 / §4-1 口径)未改 —— 判据, 需预注册; E6 的 `buckets` 使分叉可见。
- `ops/first_real_anchor.py:81` 仍打印 `realised_by_type` 原数 —— 未派单, 登记。
- 非 USDT 换算不在读者层; 读者只列原币种数量。
- 旧码红收据里 `tests_daily_summary` 是 KeyError 中止(rc=1), 不是逐条 FAIL 列表; 逐条数字对照由套件内联 MUTATION check 承担(旧公式在同夹具上的值: −0.31 / 0.0 / −1.00 / +6.50 / −3.70)。
