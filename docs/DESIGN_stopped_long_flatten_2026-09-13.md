> **创建:** 2026-09-13 09:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate X1, 派工 W9) | **状态:** §1 事实表 + §2 设计先于代码 → §3 测试计划 → **§4 结果: W9 尖端 `2f2a63b`(栈基底 `2230307`), diff sha `026e872d…`, 4-diff 栈电池 rc 1(唯一红 tests_env_loading, 无 .env); 未部署** | **作废条件:** 执行器 `apply_withhold_and_reshape` / `clamp_held_untradable` / `reshape_after_withhold` / 逐名止损接线改动; 或用户裁定条款动作改为别的形态

# DESIGN W9: 已停名(逐名止损)的目标被 reshape 平移, 多头停不到 0

**一句话**: 条款 cf40ea21 的动作是「目标归零 ⇒ 既有 flatten_only 通道」。执行器在 `apply_withhold_and_reshape` **之前**把 stop 名目标置 0, 而该函数第 2 步 re-demean 对**包括这些 0 在内**的全部目标名统一平移 a, 第 3 步 clamp 看到的是 a 不是 0 ⇒ 与 a 同号的已停名被判 add_blocked(钉住)或 reduced(砍到 ≈ a)。修法: 让拥有「POP → RESHAPE → CLAMP 顺序」的那个函数也拥有「已停 ⇒ 恰为 0」。

证据来源: T5b `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/RESULT_T5b.md` §0 / §5.3、`receipts/RECEIPT_T5b_exec_posthoc.json`、`TABLES_T5b.md` T7(提交 `51b93969`); 本文新增三份第一手收据 `docs/receipts/w9_fact_*.{py,log}`。行号: 「@918559f」= 运行树; 「@栈」= 918559f + W6ab(259f50a6)+ W2(2ad1c272)+ W1(62a3032e)三个基底提交, 顶 `2230307`。

## §1 事实表(先于代码)

| # | 事实 | 在哪测的 | 后果 | 修哪一环 | 断言 |
|---|---|---|---|---|---|
| F1 | **执行顺序**(@栈): ① `_pns_sets = PNS.active_sets(load_state)`, stop ∪ cooldown 并入 `_untradable`(`scheduler/anchor_loop.py` L1607–1616)② `target = LG.to_notional(book, symbols, gross)`(L1770), `to_notional` **丢弃 \|w\| ≤ 1e-12 的名**(`signal/legs.py` L340)③ 外部书 2×minNotional 撤下名并入 untradable ④ `_pns_zero_targets`: stop 名若在 target 中则 `target[s] = 0.0`(L1811–1815)⑤ `apply_withhold_and_reshape`(L1816 → 定义 L334): POP 未持有的 untradable → RESHAPE 对 `sorted(target)` **全部键**做 `w − w.mean()` 再 L1 重标(`legs.py` L180)→ CLAMP(`clamp_held_untradable` L425)⑥ `plan(..., reduce_only_syms = reduced ∪ flatten_only ∪ cap, held_qty)`(L1935–1940) | 读码 @栈 | 置零(④)与 clamp(⑤-3)之间夹着 reshape(⑤-2) | 设计 | — |
| F2 | **各版本相同**: 自条款上线 `0bcc089`(2026-08-20 02:28Z)到 `c22ae49`(09-11)共 21 个改过 anchor_loop / legs / per_name_stop / external_book 的版本 + 上线前父版本: 置零循环 + 调用、stop 并入 untradable、`apply_withhold_and_reshape`、`clamp_held_untradable`、`withhold_pop`、`reshape_after_withhold`、`to_notional`、`active_sets` 的源码 sha: 条款引入的三件(置零循环 + 调用、stop 并入 untradable、`active_sets`)在 21 个版本里**逐字相同**, 其余五个函数在含父版本的 22 个版本里**逐字相同**; 只有 `external_book.target_vector`(cf3fd9f / 2652f95, 08-22)与 `held_not_in_target`(2652f95)变过。栈上 W6ab 的 anchor_loop 四个 hunk(L1088 / L1101 / L1929 / L2233)不碰这些行; W2 / W1 不改 anchor_loop | `w9_fact_stop_path_versions.log`(git 对象逐版 AST 取源 sha) | 缺陷自条款上线起**一直在**, 不是某次提交引入; 08-22 外部书只改变了人口与 a 的量级 | — | — |
| F3 | **机制**: ④ 插入的 0.0 是 reshape 前 target 里**唯一**的显式零(其余零权重名被 `to_notional` 丢掉; 外部书「持有但生产者不再目标」的名 `target_vector` 给 0 ⇒ 同样不进 target)。re-demean 给人口 P 里每个名同一个平移; 对 0 条目, 重整后值 = a = −S·mean(w)/L1。sign(a) = −sign(net_before) | 读码 + F4 数值 | 与 a 同号的已停持仓: \|a\| > \|持仓\| ⇒ add_blocked(target := 持仓, 零单); \|a\| ≤ \|持仓\| ⇒ reduced(target = a); 异号 ⇒ flatten_only(碰巧对) | **R**: 已停名移出重整人口, 重整后恰为 0 | §3 R 格 |
| F4 | **真账本可精确重建**: 三个真实锚(09-03 16Z A1788452640 / 09-10 12Z A1789043040 / 09-10 16Z A1789057440)上, 取 P = {本锚有订单行 ∧ 目标文件权重 ≠ 0}, stop 名置 0, 以 phase_A `sizing.gross` 与 `external_book.gross_in` 做 demean + L1, **217 / 243 / 243 个未 clamp 名的记录目标逐名相符, 最大差 6.8e-13 USDT**; 重建 net_before 与账本 `reshape.net_before` 相同(−9100.877 / −11201.631 / −11387.348); stop 名重建值 = a = +42.3950 / +49.6149 / +50.4765, 与记录桶一致(IOST 12Z reduced 记录 49.6149; 16Z add_blocked 记录 = 持仓 45.4169; CYS / MAGMA / RIVER / TRIA add_blocked 记录 = 持仓; ARB 空头 flatten_only 记录 0.0)。订单行 `prev_w × target_gross` 就是 clamp 用的持仓(add_blocked 行 `target_w == prev_w` 逐位相等) | `w9_fact_reconstruct.log`(读 T5b 冻结副本) | 测试夹具可以用**真锚原数**, 不是拟合 | — | §3 R0 夹具有效性格 |
| F5 | **自上线以来的全部实例**(08-20 16Z 首例 .. 09-12 12Z): 已停且持仓 157 例 = 多头 add_blocked **105** / 多头 reduced **39** / 多头 flatten_only 2 / 空头 flatten_only 5 / 空头 reduced **2** / 空头未列 4。**08-20..08-25(内部书为主)符号相反**: 空头 BOME(08-20 16Z −286.4)、ENA(08-21 12Z −302.1)被 reduced, 多头 MAGMA(08-23 12Z)、VELVET(08-25 00Z)反而 flatten_only。T5b 两窗 125 例(94 / 23 / 5 / 3)是其子集 | `w9_fact_census_since_live.log`(桶 = phase_A `untradable_names`, stop 集 = 上一锚 phase_C, 持仓 = 上一锚读回) | **缺陷对方向对称**: 被钉的是与 a 同号的一侧, 不是「多头」本身; 修法不得依赖 a 的符号 | R 不依赖符号 | §3 R9 镜像格 |
| F6 | **后果链**: 钉住的已停名永远到不了 \|notional\| < `min_notional_usdt`, `evaluate` 第 1 步不转冷却 ⇒ 冷却只在书级平仓后才开始(CYS / TRIA / MAGMA / RIVER 09-06 12:39Z、XAN 09-09 20:39Z、IOST 09-12 16:39Z); 每名 6..60 USDT 被钉; 大仓被砍到 ≈ a(HEMI 1424 → 57、XAN 2292 → 54、IOST 894 → 49)后再钉 | T5b §5.3 + notify_audit | 条款告警写「⇒ flatten_only(maker 出场, 不追)」, 实际多数已停多头没有出场 | R | — |
| F7 | **条款规格**: 冻结预注册(sha `cf40ea21…`, 研究仓 `06de7c55` L14)「动作: 该名置 flatten_only(既有 disposition 机制): 目标归零, maker-only 出场, 政策 A 不追 —— 不是市价平仓, 零新执行形态」; `live/per_name_stop.py` docstring L7–9 同义; anchor_loop L1811–1812 注释「置零后 clamp pass-2 的 tgt*cur>0 恒假 ⇒ 该名必落 flatten_only 桶」**与代码相反**(中间隔着 reshape) | 冻结文件 + 读码 | 注释说反话, 读注释的人会以为已覆盖 | 注释改为如实 | — |
| F8 | **既有覆盖**: `tests_per_name_stop` W4 只断言文本顺序(`_pns_zero_targets` 在 `apply_withhold_and_reshape(\n` 之前); `ops/gate_coverage.py` L138 盲区 (b) 说「does not prove the stopped name actually lands in the flatten_only bucket (spec_book_reshape owns that claim)」—— 而 `live/spec_book_reshape.py` @918559f **不含任何 stop 字样**(grep 0) | 读码 | 这条性质**无人拥有** | 本修复在 tests_per_name_stop 里拥有它 | §3 全部新格 |
| F9 | **谁该拥有「已停 ⇒ 恰为 0」**: `apply_withhold_and_reshape` 的 docstring 自述「THE ORDER IS THE DESIGN … A caller can get the sequence wrong; a caller cannot get this wrong without editing it」—— 本缺陷正是一个调用方步骤(置零)放在有序函数之外, 被其第 2 步撤销。`clamp_held_untradable` 不知道谁是 stop 名(只能事后改 target, 但重整已把 k·a 摊进其余名, 书净额偏 k·a); `reshape_after_withhold` 是无名字的向量函数, 自 08-02 未改且由 tests_book_reshape 规格化 | 读码 | 放在 clamp ⇒ 残留净额; 放在 legs ⇒ 纯函数要知道名字 | **R 放在 `apply_withhold_and_reshape`**(新关键字, 默认空 = 逐位旧行为) | §3 R7 中性格 |
| F10 | **人口**: P = POP 之后 target 的全部键 = 可交易名 ∪ 仍在 target 里的持仓 untradable(场所撤下但持有、冷却尘埃仓、外部书尘埃持仓、**已停持仓**)。不在 target 里的持仓 untradable(生产者不再目标的持有名、生产者权重为 0 的已停名)从不进 P, 已经恰为 0 落 flatten_only。net_before = Σ_P w, 0 条目不改变它 ⇒ 把已停名移出 P **不改 net_before 与撤名残差告警**, 只改均值的分母 \|P\| 与 L1 | 读码 + F4 | 修复只把「已停持仓」从 P 拿出来, 其余持仓 untradable 仍在 P 内并按 08-02 设计被 clamp(残差照旧记 `clamped_after_reshape`, 不摊给别人) | R 的范围 | §3 R5 / R6 邻格 |
| F11 | **与 W6 全退出数量规则的交互**: 目标恰为 0 且持仓 ≠ 0 ⇒ W6(b)`plan()` 以 −held_qty(交易所张数, `qty_source = venue_position_qty`)定量, flatten_only ∈ reduce_only_syms ⇒ reduce-only —— 正是 E-0912-A 的形态(全退出 + reduce-only), W6(a)(b) 已把它做安全。F5 的 144 例多头(105 + 39)修后都变成这种全退出 | 读码 @栈 `binance_executor.plan` L760–835 | **W9 不能先于 W6 落地**: 没有 W6(b) 时全退出按 mark≠mid 超量下单 ⇒ 场所截量 ⇒ E-0912-A 同一路径 | 栈顺序 W6 → W2 → W1 → W9 | §3 链格断言 reduce_only + 目标 0 |
| F12 | **flatten_only 通道实际执行**: 与已停空头今天走的是同一通道 —— maker reduce-only; maker 未成交的剩余量走补单腿与追单框架(已停空头记录行: PROMUSDT 08-26 00Z `topup_taker:filled`、LSKUSDT 09-12 12Z `topup_taker:filled`; flatten_only 持有退出名 ACUUSDT 09-03 16Z `topup_taker:skipped_no_chase_arm`)。条款原文「政策 A 不追」与该通道补单行为不一致 | T5b 实例订单行 + 读码 | W9 **不增加执行形态**(已停多头进入空头已在用的通道); 「不追」措辞与现通道的差异是既有事实, 本修复不改 | 不改; 列为具名差异交 lead | — |
| F13 | **读者 W1 / W2**: W1(`ops/ic_monitor.py`)与 W2(`live/cost_buckets.py`、`ops/daily_summary.py`、`ops/first_anchor_review.py`、`ops/score_post_fix.py`)不读 `untradable_names` / `clamped_after_reshape` / `per_name_stop`; `daily_summary` 读 `reshape.n_popped`、`first_anchor_review` 读 `untradable_disposition.popped`(计数); `ops/verify_reshape_anchor.py` 读 net_before / net_after / n_popped / popped_names / clamped_after_reshape。已停多头的出场行是普通 maker / topup 行, 无新 order_type 或 terminal_reason | git grep @栈 | 只要 POP 语义不变(未持有的已停名仍记 popped), 这些读者读数口径不变; 新增一个报告键是加法 | R 保持 POP 语义 | §3 R8 |
| F14 | **邻格人口(真锚 09-03 16Z)**: 同一锚的记录桶里 —— 已停空头 ARB(flatten_only); 冷却持仓 SKR(冷却 08-30 20:42Z..09-06)、BTR(09-02 08:41Z..09-09)、EGLD(09-03 08:41Z..09-10)为 add_blocked; 非止损 untradable KMNO / PYTH 为 add_blocked, ACU / AIA / ALICE / ARKM / BABY / BAS / BRETT / B / CROSS / DEEP / DODOX 为 flatten_only(名单截 12) | phase_A + notify_audit 冷却事件 | 三类邻格可以在**同一个真锚**上同时断言 | — | §3 R4 / R5 / R6 |

## §2 设计(由 §1 推出, 不由派工文字推出)

1. **拥有者**(F9): `apply_withhold_and_reshape(..., force_flat=())`。`force_flat` = 条款要求目标恰为 0 的名。函数内顺序变为 **POP → 移出 force_flat 持仓名 → RESHAPE(剩余人口)→ force_flat 持仓名恰为 0.0 → CLAMP**。未持有的 force_flat 名仍在 POP 里被撤并记入 `popped`(F13 读者口径不变); 持仓而不在 target 里的 force_flat 名照旧由 clamp 补 0(F10)。`force_flat` 名一律视为 untradable(不在 `untradable` 里也并入), 保证 clamp 一定处理它。默认空集 ⇒ 函数逐位旧行为(tests_book_reshape 全部不变)。
2. **接线**: anchor_loop 删掉调用前的置零循环(两处实现同一件事是本库反复吃亏的形态), 改为 `force_flat=self._pns_sets["stop"]`; `_pns_zero_targets` 标签留在调用前的注释里并改写为如实描述(W4 文本顺序断言逐字保留且仍成立)。
3. **中性**(F9/F10): 修后 Σ_{P∖stop} 重整目标 = 0、Σ|·| = S(clamp 之前); 已停名贡献恰 0; 其余持仓 untradable 的 clamp 残差仍按 08-02 设计报告, 不摊。旧码的残差里多出的「已停名 a 或持仓」部分消失。
4. **报告**: reshape 报告加 `forced_flat_names`(本锚移出重整人口并置 0 的持仓已停名), 其余键不变。
5. **不做**: 不改 `clamp_held_untradable`、`reshape_after_withhold`、执行器下单/补单/追单(F12)、冷却名与非止损 untradable 的处置(F14 邻格要求不变)、条款参数与告警文案(「不追」差异交 lead)。

## §3 测试计划(实现后以结果回填)

新格全部写进 `live/tests_per_name_stop.py`(条款套件; 既有 18 个断言逐字不动, AST 核对); 夹具 `live/tests_fixtures/w9_stopped_long/` = F4 三个真锚的逐名原数(文件权重、记录目标、prev_w、订单行类), 另存重建脚本与 sha。
- **R0 夹具有效性**(新旧代码皆绿): 按「置零 → 旧调用」重放三锚, 全部名的目标与记录逐名相符(≤ 1e-6 USDT), 记录桶全部复现(含已停多头 add_blocked / reduced)。
- **R1–R3 修复**(旧码红): 同三锚走修后调用 ⇒ 每个持仓已停名(CYS / MAGMA / RIVER / TRIA @09-03 16Z; IOST @09-10 12Z 与 16Z)落 flatten_only、目标 `== 0.0`、在 reduce_only 集合内。
- **R4 邻格 已停空头不变**: ARB @09-03 16Z 桶与目标(0.0)与记录相同。
- **R5 邻格 冷却不变**: SKR / BTR / EGLD @09-03 16Z 桶 add_blocked、目标 == 记录(= 持仓)。
- **R6 邻格 非止损 untradable 不变**: KMNO / PYTH add_blocked 目标 == 记录; 非止损 flatten_only 名目标 0.0 == 记录; 桶成员不变。
- **R7 其余书中性**: 修后 clamp 前 Σ_{P∖stop} = 0、Σ|·| = S(1e-6); 已停名贡献 0。
- **R8 POP 语义**: 未持有的已停名仍在 `popped`; 持仓但不在 target 的已停名仍 flatten_only 0。
- **R9 符号对称(F5)**: 09-03 16Z 夹具权重取负(a < 0 的时代镜像)⇒ 旧码钉已停空头、修后 flatten_only 0, 已停多头仍 flatten_only 0。
- **原链**: DRY_RUN `run_anchor` 外部书链(tests_external_book 同式装置): 生产者仍给已停持仓多头正权重、另有被撤名使 net_before < 0 ⇒ 锚 target 中该名 `== 0.0`、`untradable_names.flatten_only` 含它、plan 行 reduce_only; 旧码红。
- **静态**: 调用点把 stop 集以 `force_flat=` 传入(限定在 run_anchor 调用语句内, 不做全文件子串)。
- 旧码红证明: 同一测试文件放进栈基底 `2230307` 的干净工作树跑; 全电池在 4-diff 栈 + 真实 state 副本上跑(开跑时刻避开 HH:20–45)。

## §4 结果(X1, 2026-09-13 09:0x–10:0xZ; 克隆 `/Users/haosiyu/cc_tmp/exec_w9`, 分支 `fix/w9-stopped-long-flatten`; **未部署, 未 push, 无网络, 运行树与生产者只读**)

### 4.1 提交链与收据
| 件 | 值 |
|---|---|
| 基底 | `~/dl_quant_live` 无硬链接克隆 @ `918559f` → `8e9d126` W6ab(树 `5ba339fc…` == W6 克隆 `8113eed` 的树)→ `6e95570` W2 → **`2230307e0725ecfe7a6c3c6180c9406fef0d2ad6`** W1(三份 diff sha256 前缀 259f50a6 / 2ad1c272 / 62a3032e, 均 `git apply --check` 后 `git apply`) |
| **W9 尖端** | **`2f2a63bef33238c5542af4aae764c67bf780e1d8`**(8 文件 +7,251 −9: `scheduler/anchor_loop.py` +42/−8 · `live/tests_per_name_stop.py` +247 · `ops/gate_coverage.py` · `live/tests_fixtures/w9_stopped_long/` 三个真锚 JSON + build_fixture.py + MANIFEST.json) |
| `docs/receipts/w9_stopped_long_flatten.diff` | `git diff 2230307 2f2a63b`; sha256 **`026e872d0b30598f7dbd21ffd89626d1ab91ee7598d6ad110cb3305857f49028`** |
| 顺序可用性 | 新 918559f 工作树依次 `git apply` W6ab / W2 / W1 / W9 四份 diff 全部 rc 0, 结果树 `3004c58f…` == W9 尖端的树(`w9_apply_check.log`; 同日另一次尝试 W2 报过一次「No valid patches in input」, 未复现, 原因未查明, 已记在收据里) |
| 事实收据 | `w9_fact_stop_path_versions.{py,log}` · `w9_fact_census_since_live.{py,log}` · `w9_fact_reconstruct.{py,log}` |

### 4.2 测试
| 件 | 新码(2f2a63b) | 旧码(同一测试文件 + 夹具放进 2230307 干净工作树) |
|---|---|---|
| `tests_per_name_stop` | **61/61 ALL PASS**(18 个原断言 + 19 个新检查点在运行时展开为 43 格) | **33 PASS / 28 FAIL, rc 1**(`w9_oldcode_red_2230307.log`): 红的恰是缺陷格 —— R1–R3(CYS / MAGMA / RIVER / TRIA @09-03 16Z add_blocked, IOST @09-10 12Z reduced、16Z add_blocked; R3 在 12Z 因 reduced 本就 reduce-only 而绿)、R7 ×3、R8a/b、R9、RC2–RC5(SSS 钉在 40.0, 其余书净额 −140.85)、RS; 绿的是 18 个原断言、R0 有效性 ×7、已停空头 ARB 的 R1–R3、R4 / R5 / R6 邻格、RC1 |
| AST 逐字核对 | `tests_per_name_stop` 18 个原调用点(标签 / 条件 / 明细)逐字、同序; `tests_book_reshape` 40 / 40、`tests_external_book` 100 / 100 未改(`w9_ast_check.log`) | — |
| 真锚夹具有效性 | R0a: 三锚 253 / 244 / 244 个名的记录目标逐名复现 ≤ 1e-6 USDT; R0b: 复现桶 ⊇ phase_A 记录桶(新旧皆绿) | 同 |
| 邻格数(09-03 16Z) | 已停空头 ARB flatten_only 0.0 不变; 冷却持仓 BTR / EGLD / SKR add_blocked 目标逐位不变; 非止损 untradable 持仓 28 名桶与目标不变 | 同(邻格本就绿) |
| 修复过程中我自己引入又改掉的两处 | ① 调用前注释写了 `apply_withhold_and_reshape(force_flat=stop)` 字样, `tests_book_reshape` 两个「_trade 里只有一个调用点 / 第一个调用点传 sizing gross」的静态格按子串计数读成 2 个调用点 ⇒ 红, 改写注释措辞后 38/38; ② `gate_coverage.py` 该条长串在 Python 3.9 脚本模式下报 `Non-UTF-8 code … line 138`(文件本身是合法 UTF-8, `py_compile` 与 import 都过, HEAD 版脚本模式也过; 是长行 + 多字节字符在分词器读缓冲上的问题)⇒ 拆成相邻短字面量, 内容逐字相同, 脚本模式 `--verify` 135 套件全部有边界自述 | — |

### 4.3 电池(4-diff 栈 + 真实 state 副本)
`/Users/haosiyu/cc_tmp/w9_battery` @ `2f2a63b`; `rm -rf state` 后 `cp -R ~/dl_quant_live/state`(09:39:37–09:40:12Z), **未复制 `.env`**; 09:46:24Z 开跑(避开 HH:20–45), 10:03:05Z 结束; 起止 HEAD 均 `2f2a63bef33238c5542af4aae764c67bf780e1d8`, 状态外追踪改动 0。
**电池自报**: 135 行 = 130 个 tests_* 套件 + 5 个门; **134 行 rc 0; 1 行红 = `tests_env_loading`(rc 1, 四格 `ops/ic_monitor.py` / `ops/redeliver_alarms.py` / `ops/unseed_rehearsal_halt.py` / `scheduler/run_anchor.py` populates TELEGRAM_* on import —— 克隆无 `.env`)**; 末行 `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)`; **battery rc = 1**。不是全绿。`tests_per_name_stop` / `tests_book_reshape` / `tests_external_book` / `tests_reduce_only_clamp` / `tests_disposition_matrix` / `tests_readers_three_bucket` / `tests_daily_summary` / `tests_ic_monitor` 均 rc 0。收据 `w9_battery_2f2a63b.log`。

### 4.4 边界(未做 / 未证)
1. **执行侧未证**: 已停名的 maker reduce-only 出场是否成交、下一个终锚读回是否把它转冷却, 本轮没有场所侧证据(DRY_RUN 与纯函数); 首锚验收应核: 已停名 `untradable_names.flatten_only` 含它、plan 行 `reduce_only`、`qty_source = venue_position_qty`、次锚读回 \|notional\| < min_notional ⇒ 冷却事件。
2. **真锚夹具只覆盖外部书时代(a > 0)**; a < 0 由镜像夹具覆盖, 不是真锚。
3. **F12 具名差异不改**: 条款原文「政策 A 不追」, 现 flatten_only 通道的补单腿走执行器的追单框架(已停空头早有 `topup_taker:filled`)。W9 不改, 交 lead / 用户裁。
4. **告警文案**: anchor_loop 对 clamp 桶的 HIGH 告警写「withheld by the venue (maxNotionalValue=0)」, 对已停 / 冷却名同样这么写(既有文案, 未改)。
5. 旧码下 W9 修复会让已停多头变成全退出; **不得先于 W6 落地**(F11)。
