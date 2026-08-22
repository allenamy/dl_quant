> **创建:** 2026-08-22 04:5xZ | **Session:** 6737834a-WA | **状态:** 提案(**未应用, 未触碰运行中的 ~/wide_shadow 进程/文件**; 两份 diff 对运行中 `shadow_loop.py`(SHA `445a9870e555…`)干跑可应用; 测试 14/14 PASS) | **作废条件:** 任一修法被采纳落盘 ⇒ 本文改"已应用"并互链 RUNBOOK; 影子 bundle/引导逻辑重做 ⇒ 重新生成 diff

# 影子记分缺陷修法提案: 数据宇宙外的冻结尾巴(gross 18%)记 0 盈亏 —— (a) 记分修正 / (b) 出宇宙即平

## 0. 缺陷本体(WA 受据 `RESULT_wide_full_caliber_audit_2026-08-22.md` §3; 数字对最新权重文件 `1787356800.npz`)

- **机制**: 影子启动时 `aux["H"]` 从 bundle `parity_signals_aug.json`(pod 链在 829 名面板上的持仓)引导 ⇒ 带入 **296 个不在 `symbols_live`(450)里的名**, 合计 gross **0.2502**(= 总 gross 1.38 的 18%); 影子只为 450 名拉 K 线 ⇒ 这些名永远无数据 ⇒ 目标恒 0, 而 EMA 步长 |0.1·H| < 带 2.5e-4(|H| ≤ 2.5e-3, 实测最大 0.002499)⇒ **永不交易、永不衰减、score 行按 `y4v=NaN→0` 记 0 盈亏**。同机制在 450 内产生 50 个非成员尾巴(gross 0.08, 有数据会记分, 只是同样冻结)。
- **量级**: 27 个已记分锚上, 这 0.25 gross 的真实价格盈亏 **+2.23 bps/锚(sd 4.1, Σ +60 bps)**, 符号随机; 296 名中 270 名仍在 fapi 可交易(gross 0.210), 26 名已退市/无 K 线(gross 0.040, 真实结果不可知)。影子 27 锚净 −222 vs 本装置(含尾巴真实盈亏)−172。
- **为什么是设计缺陷而非数据噪声**: 纸面书持有它们、gross/集中度统计含它们, 但盈亏/carry/成本三项都不记; 实盘适配器(`external_book`)会 **pop 宇宙外名** ⇒ 纸面书 ≠ 可执行书, 差 18% gross。

## 1. 两种修法(文件在本目录; 生成器 `make_patches.py` 从 `shadow_loop.orig.py` 确定性生成)

| | (a) 记分修正 `a_tail_scoring.diff` → `shadow_loop_a_tail_scoring.py` | (b) 出宇宙即平 `b_exit_on_leave.diff` → `shadow_loop_b_exit_on_leave.py` |
|---|---|---|
| 改什么 | **只改 score 行**: 结账时对 `prev["sm_idx"]` 中 ∉ `symbols_live` 的名, 逐名拉 fapi 1h K 线(startTime T−1h, limit 5 ⇒ 首 bar 收盘 = P(T), 末 bar 收盘 = P(T+4h))与 `fundingRate`(窗 (T,T+4h] 内实际结算), 新增字段 `tail_gross_bps / tail_carry_bps / tail_n / tail_unknown_gross / tail_gross_pos / gross_bps_total / net_bps_total`; **原字段 `gross_bps/net_bps/carry_bps/cost_bps` 逐字不变**; 退市/缺 bar 的名记 `tail_unknown_gross`, 不记 0 也不猜 | **改书**: 步 8 带判定之后、记账之前, `exit_out_of_universe(sm, H, keep_mask)` 把 ∉ `symbols_live` 的名 **强制置 0(不受带约束)**, 强制交易计入 `turnover`, 成本按最差档 4.7 bps/单位(`FORCED_EXIT_COST_BPS`); 引导时 `aux["H"]` 同样过滤; signal 行新增 `forced_exit_n / forced_exit_gross`; 可选开关 `EXIT_NON_MEMBERS=True`(默认关)把"离开 K400 成员集"的名也即平(= 在役 forced-exit 语义) |
| 改动面 | +23 行常量/纯函数 + score 行 10 行(2 hunks) | +9 行常量/纯函数 + 引导 1 行 + live_mask 1 行 + 步 8 约 10 行 + signal 行 1 行(5 hunks) |
| 运行代价 | 每锚多 ≤ 2×296 个 weight-1 请求(节流 150/60s ⇒ **+3~4 min/锚**, 现 runtime ~340 s ⇒ ~580 s, 仍远小于 4h 节奏; `TAIL_SCORE_MIN_W` 可缩小集合); 退市名每锚各一次失败请求 | 激活锚一次性平掉 gross 0.25(换手 +0.25, 成本一次性 ≈ 0.25×4.7 = **1.2 bps**), 之后 gross 1.38→1.13; 26 个退市名在 fapi 上本就不可交易 ⇒ 真实书里它们是"早已被交易所结算"的仓位, 置 0 正是真相 |
| 不改什么 | 书/权重文件/H/PASS 读的字段 | score 行字段名不变(数值因书变而变) |

## 2. 对 PASS 测试(PREREG_wide_book_assembly §4: ≥84 锚 净额 ≥0 且 与离线同锚差 |Δ| 中位 <30%)的影响

- **(a)**: 判据读的 `net_bps` **逐位不变** ⇒ PASS 计时与口径不受影响; 若裁定改读 `net_bps_total`: 迄今 +2.2 bps/锚(sd 4.1)会进入, 84 锚上尾巴项的噪声 ≈ ±38 bps, 与离线比较方(pod 链, 没有"数据宇宙外"概念, 它的尾巴是退市幻影记 0)不同构 ⇒ |Δ| 中位判据多一个噪声项。**建议: (a) 只作证据采集(知道纸面书真实值), PASS 仍读 `net_bps`。**
- **(b)**: 激活锚起 `net_bps` 是**真持有书**的净额(再无"持有但不记分"的仓位); 一次性 −1.2 bps 成本进入净额; 之后逐锚 net 与原版只差"尾巴本应记的盈亏"(均 +2.2/锚, 符号随机)—— 即 **原版对 PASS 的净额读数在尾巴上是有偏的(系统记 0), (b) 去掉这个偏**; 与离线比较: 离线链的宇宙是全 829 名, 其非 450 名上的持仓是有收益数据的真仓位 ⇒ (b) 后影子与离线的差 = "影子可交易宇宙 450 vs 离线 829"的真实差, 不再混入记账缺陷。**84 锚计时**: (b) 改书行为 ⇒ 按 PREREG 字面应 **重新起算或在裁定里登记"第 N 锚起书定义变更"**(一锚一变更); 我的建议是后者并在 RESULT 里把激活前后分段报。

## 3. 对外部书模式(DESIGN_wide_live_deployment / `shadow_loop_v2.diff` 的 `write_target_live`)的影响

- 适配器 `dl_quant_live/live/external_book.py` 读 `target_live/<anchor>.json`, 对 ∉ 实盘宇宙的名 **pop** ⇒ **原版/(a) 下: 纸面书 gross 1.38 的 18% 被适配器静默丢弃**, 实盘执行的是 1.13 gross 的书, 而影子 PASS 判据评估的是含尾巴(记 0)的纸面书 —— 两者差 = 尾巴真实盈亏(±)。**(b) 使影子纸面书 ≡ 适配器可执行书**(`wnz` 里不再有宇宙外名, pop 成为空操作), 这是 (b) 的主要价值。
- hunk 交叉: v2 的两个 hunk 在原 L43(纯追加函数块)与 L379-384(savez 之后调用 `write_target_live`); (b) 的第 5 个 hunk 改 L384 附近 signal 行(`"turnover"` 行后加一行)—— **上下文相邻, 建议先应用 v2 再应用 (b)**(或用 `make_patches.py` 对 v2 文件重生成; 生成器按锚文本替换, 对 v2 同样适用: 断言见脚本内 `must_replace`)。(a) 与 v2 无交叉。
- v2 写出的 `weights` 是"carried-forward 向量的非零名" ⇒ (b) 激活后 target 文件天然只含 450 内名; 若先上 v2 后上 (b), 激活锚的 target 文件会出现 296 个 0 权重的"平仓指令"? 否 —— (b) 置 0 后 `wnz = |sm|>1e-9` 不含它们, 适配器看不到这些名(它们在实盘里本就不存在仓位, 无需平)。

## 4. 建议与顺序(裁定属主线, 本文只给谓词)

1. **先 (a) 后 (b) 不互斥**: (a) 立即可上(只加字段, 零行为改动, 不动 PASS); 它同时给出 (b) 的"反事实账"(尾巴若继续持有会赚/亏多少), 是 (b) 激活的证据基础。
2. **(b) 是换装前置**(WA D-9): 任何把影子权重接到实盘的路径都要求"纸面书 = 可执行书"; 激活一次性成本 1.2 bps; 建议同时把 `EXIT_NON_MEMBERS` 留关(K400 离开者仍按 EMA 衰减 = 宽书自有语义, 否则换手升、且与离线链不同构), 仅对"数据宇宙外"即平。
3. 退市名(26 名 gross 0.04): (a) 记 `tail_unknown_gross`; (b) 直接置 0 —— 两者都承认"影子不知道它们的结算价"; 真实书中它们早已被交易所结算, 置 0 更接近真相。
4. 根因第二处: 引导 `aux["H"]` 不应带入数据宇宙外名 —— (b) 的引导 hunk 处理; 若未来 bundle 重做, 生成器 `must_replace` 断言会在锚文本漂移时拒绝生成, 不会静默错配。

## 5. 最小测试 `test_shadow_tail_fix.py`(只读 ~/wide_shadow, 无网络, 不写任何影子文件; 实跑 14/14 PASS, 2026-08-22 04:5xZ)

| 测试 | 断言 | 结果 |
|---|---|---|
| T1 纯函数 `exit_out_of_universe` | 只清 keep_mask=False 的名; 其余逐位不动; 强制量 = 被清 |w| 和; 默认开关 (EXIT_ON_LEAVE=True / EXIT_NON_MEMBERS=False / 4.7) | PASS ×3 |
| T2 纯函数 `score_tail_positions`(注入假 fetch) | 5 根 1h bar 100→110, w=0.002 ⇒ tail_gross 2.0 bps; 窗内结算 1e-4 ⇒ carry 0.002 bps, 窗外(=T)结算不计; 只 1 根 bar 的名记 unknown 不记 0 | PASS ×3 |
| T3 存档权重机制事实 | 最新 `1787356800.npz`: 宇宙外 296 名 / gross 0.2502; 最大 |w| 0.002499 ≤ 带冻结上界 2.5e-3; 对存档权重施 (b) ⇒ 恰清 296 名、宇宙内逐位不变 | PASS ×3 |
| T4 可应用性 | 运行中 `shadow_loop.py` SHA 445a9870 = 提案所对; 两份 diff `patch --dry-run -p1` 干跑成功; 两个变体 `py_compile` 通过 | PASS ×5 |

**未覆盖(提案方自报)**: (a) 真实 fapi 端到端(提案禁止起进程, 只用假 fetch 测了算术; 端点/参数与运行中 `fx.get` 同形, `limit=5` 的 1h K 线 weight=1 已在 Fetcher 节流模型内); (b) 激活锚的一次性换手对 `cost_bps` 的实际数值(按 0.25×4.7 估); 与 v2 同时应用时的 hunk 相邻(建议顺序见 §3); `EXIT_NON_MEMBERS=True` 分支只有纯函数测试、未做换手量化(需离线链重放, 非本提案范围)。

## 6. 文件清单
`shadow_loop.orig.py`(运行中副本, SHA 445a9870) · `make_patches.py`(生成器, 锚文本断言) · `shadow_loop_a_tail_scoring.py` + `a_tail_scoring.diff` · `shadow_loop_b_exit_on_leave.py` + `b_exit_on_leave.diff` · `test_shadow_tail_fix.py`。同目录的 `shadow_loop_v2.*` / `tests_target_live_output.py` 属外部书模式(commit 38826c5), 本提案未改动。
