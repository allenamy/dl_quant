> **创建:** 2026-08-21 16:5xZ | **Session:** 6737834a(G2 测试工程师子线程) | **状态:** 草稿(研究仓), 等主线审后移入 `~/dl_quant_live/live/` 并登记进 `run_acceptance.sh` 电池 | **作废条件:** 任一守卫口径再被裁定改变(届时对应性质/手推值须同步重写, 不得只改数字)

# 守卫口径性质测试草稿(DESIGN_optimization_path_2026-08-21 §2.2 C)

- 文件: `tests_guard_calibers.py`(单文件, 可直接放进 `live/` 运行: 与现有套件同样的 `import watchdog as WD` / `import pilot_log as PL`)
- 运行证明: `RUN_2026-08-21.txt`(`/usr/bin/python3` = 电池钉定解释器; 默认 `python3`=anaconda 3.7.6 亦通过)— **97 检查全绿, 33 个变异体全红, 0 存活**
- 硬约束遵守: 实盘仓只读(源码 sha 前后一致 + `live/__pycache__` 列表不变, 由套件自己的 [Z] 节断言; `sys.dont_write_bytecode` 在首个 import 之前置位); 临时树全在 tempfile 下并于结束时删除

## 一句话方法

夹具不再"把亏损写进盈亏列、nav 不动"(E-0821-A 五套件同脑错误), 而是由**账户恒等式**生成: `nav_t = nav_{t−1} + Δrealised + Δunrealised + Δflow`(`truth_tree()`; realised/flow 为自午夜累计、unrealised/nav 为水平 — 与生产写入器 `anchor_loop.py` daily_nav 同义); 期望值是断言旁的**显式算式**, 不是守卫的第二份拷贝; 每条性质配一个在内存里改生产源码的变异体(`mutant()`, 学 numerator_honesty, 推广到多处替换), 必须变红。

## 逐条清单(保护什么 / 变异体 / 是否全绿)

| # | 节 | 守卫 | 测试保护的不变量 | 变异体(必须红) | 绿/红 |
|---|---|---|---|---|---|
| 1 | A | cond2 | 5 日账户路径手推: worst=−2.00%(D2), 入金日 D1/D3 与截断日 D4 **点名排除**, 2/5 定价, 不触发不告警 | (由 #8/#11 的变异体覆盖) | 绿 |
| 2 | A | cond2 | 逐日读数 = 手推(2 日探针: [前日末行, 当日]): −2.00 / 0.0 / 盲(入金→截断) / −1.00 | 同上 | 绿 |
| 3 | A | cond2 | 08-21 事故重放: 15889.5→15418.6 = **−2.9636%** ⇒ 告警不停机 | `cond2_retired_caliber_E0821A` ⇒ 读 −4.52 并触发 | 绿/红 |
| 4 | B | cond2 P1 | 同一路径 1/3/6 行/日读数相同(worst −1.35, 4 定价日) | `cond2_first_row_B31`(读日首行); `cond2_sum_rows`(同日各行相加) | 绿/红红 |
| 5 | B | cond2 P2 | 收益路径插入 +5000 入金: D3 UNKNOWN 并点名, 其他日不变, 5→4 定价 | `cond2_transfers_ignored`(入金日被定价 +51% 且不点名) | 绿/红 |
| 6 | B | cond2 P2 | 插入 −2955 出金(−30%): 同上; 次日以出金后 nav 为基 | `cond2_transfers_ignored`(读 −29.2% **并触发**); `cond2_prev_not_advanced_on_transfer`(次日 −29.5%) | 绿/红红 |
| 7 | B | cond2 P2b | 记录的 flow 金额只有真值一半: 读数不变(金额永不进公式) | — (cond4 侧有 #16) | 绿 |
| 8 | B | cond2 P3 | 昨日未实现 −300 带入、今日不动 ⇒ 0.0; 今日平掉它(realised −300, unreal 0)⇒ 0.0 | `cond2_retired_caliber_E0821A`(读 −3.09) | 绿/红 |
| 9 | C | cond4 | 同路径手推: cum = 0.98×1.01×14454/14898−1 = −3.9699%; 覆盖 4/5; 截断日点名; 链未断 | (由 #12-#17 覆盖) | 绿 |
| 10 | D | cond4 P1 | 同一路径切成 [9]/[3,3,3]/[1]×9/[4,5]/[2,2,2,2,1] 日界, 起点日固定 ⇒ 累计同为 −1.95%(望远镜恒等) | `cond4_level_sum_accumulator`(退役累加器: 水平重复计入 ⇒ −1.99~−12.7 随切法变) | 绿/红 |
| 11 | D | cond4 P1 | 1/3/6 行/日 ⇒ 累计相同 | `cond4_first_row_per_day` | 绿/红 |
| 12 | D | cond4 P2 | 入金/出金插入 ⇒ cum 不变(−3.2848%), 入金日自身 +0.8% 按盈亏定价 | `cond4_nav_ratio_on_transfer_day`(+51.6%); `cond4_transfer_day_skipped`(该日盈亏蒸发) | 绿/红红 |
| 13 | D | cond4 P2b | flow 金额写错一半 ⇒ cum 不变 | `cond4_flow_amount_enters`(金额进公式 ⇒ +21%) | 绿/红 |
| 14 | D | cond4 P3 | −300 未实现跨 4 个平日 ⇒ −3.0%, 不是 ×5 | `cond4_level_sum_accumulator`(−14.5%) | 绿/红 |
| 15 | D | cond4 | 手推路径下变异体亦红 | level_sum / nav_ratio | 红红 |
| 16 | D | cond4 | 截断日扣留 | `cond4_truncation_ignored` — **只由覆盖率抓到**(0.8→1.0): 该路径截断日 nav 精确, 链条跨洞望远镜 ⇒ 累计数不变, 这是设计而非漏洞; 诚实记录 | 红 |
| 17 | E | cond4b | 手推: 44800/14000 = 3.2×, 告警线 2.0×1.5=3.0 / 停机线 5.0; 取日**末行**(2.069 非 2.0); 恒定 gross 旧行按政策戳排除并点名; 71400/14000=5.1 触发且只它触发 | `cond4b_scope_dropped`; `cond4_first_row_per_day` | 绿/红红 |
| 18 | E | cond4b 性质 | **单位不变**: nav 与 gross 同乘 1e−3 / 1e3 读数不变 | `cond4b_gross_from_retired_P0_constant`(用退役常量 25000 当 gross ⇒ 毫单位下读 1786×) | 绿/红 |
| 19 | F | per_name_stop | 手推: 深度=unreal/\|notional\|; 空头 −20% 不计、dust 不计、**−25.0% 恰好计**(≤); 连 2 锚停; 回浅归零; 空头 −26% 也停; 出场 ⇒ 冷却 = now+7×86400 精确; active_sets | `pns_signed_notional`(空头永不停) | 绿/红 |
| 20 | F | per_name_stop 性质 | 单针不触发且回浅**归零**; 只有连续才触发(恰在第 2 锚); 缺读回打断连续 | `pns_sticky_counter`; `pns_single_anchor_trigger`; `pns_unseen_not_reset` | 绿/红红红 |
| 21 | G | cond1 | 逐日净成本手推 10.0/4.0/9.0 bps(卖高于中价=credit; 分散度 6.0); 5×10 触发; 恰 9.0 不算越线; 末尾未定价日不清 streak | `cond1_ge_at_limit`; `cond1_calendar_streak` | 绿/红红 |
| 22 | H | cond3 | stress 锚 maker 成交金额加权 adverse markout 手推 15.0/17.5(calm 日 100bps 不算), 覆盖 4/5, 27.5 触发 | `cond3_min_selector`(07-29 缺陷: 良性日解除止损) | 绿/红 |
| 23 | I | cond5a | outage 触发; public_path_unreachable 警告不触发 | — | 绿 |
| 24 | I | cond5b | 数量残差手推: 卖 600 ⇒ 残差 0 CLEAN; 卖 590 ⇒ 10U ≤ max(10%×410, 5) 容差内; 卖 300 ⇒ 300U 异常(expected 700/observed 400/frac 0.4286) | `reconcile_sign_on_expected`(符号再施加 ⇒ 干净卖单读 16 vs 4) | 绿/红 |
| 25 | I | cond5c | 拒单率只对**已发送**单: 6/10 与 5/10 连 2 锚 ⇒ 触发; 6/10,4/10 否; T-F-T 否; 20 条未发送 venue_reject 不进分母 | `cond5c_never_sent_in_denominator`; `cond5c_gt_at_half` | 绿/红红 |
| 26 | I | cond5e | 手推: dev=100/1000=10%, 4/4 比对, 拆分可言(unauth 0 / underfill 10%), gate=split_unauth, CLEAN; 幽灵仓 330 对 150 成交 ⇒ unauth 180=18%>5% ⇒ 平仓(旧规则 8% 不会), 5b 同见 180 | — (5e 归 tests_break_* 套件, 本稿仅手推) | 绿 |
| 27 | J | cond6 | corr=1−mawe×100 逐**合格锚**: N=40 [1.0, 0.8, 0.8, 0.8], 混合日 pooled −0.35 并列报告, 3 日 underfill 越线 = 告警不停机(发射顺序前提 0.06>0.05 成立) | `cond6_every_anchor_eligible`(停机锚 1/N 被并入 ⇒ 第 2 日 −0.35) | 绿/红 |
| 28 | K | cond7 | [.06,.051,.05] 不触发(0.05 非 >); [.06,.051,.0501] 触发; drift True 触发; None=UNKNOWN/盲 | `cond7_ge_at_limit` | 绿/红 |
| 29 | K | cond7 | derive_ops_stats: 20 已发送中 2 拒 = 0.10; 未发送与 skipped_min_notional 不算 | `ops_stats_never_sent_in_denominator`(7/25=0.28) | 绿/红 |
| 30 | Z | 基建 | 四源码磁盘 sha 不变; `live/__pycache__` 列表不变 | — | 绿 |

## 未覆盖项(明说, 不硬写)

1. **§4-5d**(出金冻结)— 设计上不在实时层, 仅存在性断言已在 tests_watchdog; 本稿不写。
2. **§4-5c 错误码快路径** — 生产无 producer(watchdog 自述), 仅 tests_watchdog 的注入测试; 本稿不重复。
3. **cond5e 无变异体** — position_break 的拆分归 tests_break_decomposition / split_gate / split_wiring 三套; 本稿只做"手推 = 读数"。
4. **cond2 逐日值只能经 2 日探针读** — `cond2_day_loss` 只发布 `worst_day_pct`; 正收益日只能证到"≥0"。**建议主线**: 在 detail 里加 `per_day_loss`(纯增字段, 不改行为), 逐日断言即可直接化。
5. **cond4 跨转账日的切分不变性不成立且不主张** — B33 对转账日取"当日盈亏/前日末 nav"(日内金额加权近似); 入金若在日中且随后有行情, 不同日界读数不同。这是口径设计后果, 记录供主线知悉。
6. **cond4 起点日的日内变化不计入** — 起点 = 首个可定价日的**收盘**(`_prev` 在首日只赋值不累乘)。实盘首日 08-01 是入金日无碍; 但"起点=首日收盘"应被看作规格的一部分(本稿 P1 因此把起点日钉死后再切分)。
7. **`cond4_truncation_ignored` 只由覆盖率抓到**(见 #16): 非转账的截断日 nav 精确, 定价它不改累计; 若要让数字本身变红, 需"截断 + 转账"同日夹具(那是链断/盲的情形, tests_watchdog [4] 已钉)。

## 移入电池的步骤(主线执行)

1. 复制为 `~/dl_quant_live/live/tests_guard_calibers.py`(文件头 `sys.path.insert(0, HERE)` 已按电池布局写好);
2. `run_acceptance.sh` SUITES 追加 `"tests_guard_calibers:$_SELF/live/tests_guard_calibers.py"`(注册守卫会因漏登记而红);
3. `ops/safe_commit.sh` 走电池(约 +20s: 每次 evaluate 全七条, 本稿约 60 次)。
