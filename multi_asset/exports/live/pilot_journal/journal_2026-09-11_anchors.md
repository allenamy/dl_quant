# 2026-09-11 逐锚记录(只追加)

### 2026-09-11 01:4xZ · 每锚深查 00Z 锚(结算锚, rid A1789086240, 00:24Z 执行; 首次触发; 只读, 实盘零接触)· 书 98.8%, net/gross 回带内, maker 占比 0.643 第六锚带外
- **① 守护(VERIFIED 01:39Z)**: 生产者 10900 = shadow.lock; sidecar 30943; combo 30944 = pid 文件; 沙盒 shadow_loop 50689 仍在(非生产者, 记录不动作)。
- **② 信号六项(VERIFIED)**: 生产者 00Z status OK / fund_updates **457**(结算锚稳态 ~453 ✓)/ **forced_exit_n 1**(gross 0.0018 ≈ 0.2%; 连续第二锚, 20Z 0.0009; 名不在日志字段中; 记录级)/ sel 260 / coverage 1.0 / w3 [0.3174, 0.0825, 0.6001] / runtime 284s / exinfo_ok / members 400 ✓ / turnover 2.0% / carry 1.25 bps; combo 1789084800 rc=0 00:21:22Z, n 259, gross 0.8668, kc/fc own, w3_masked [0.346, 0, 0.654] = 0.3174/(0.3174+0.6001) ✓, 读者验收 ok(0.3s); FTRIM kc 10 / fc 10(20Z 7); ρ(f10,king) −0.030。**反事实改写 0.234**(近八锚 0.218/0.223/0.226/0.232/0.228/0.230/0.231/0.234: 近三锚增量 +0.2/+0.1/+0.3 pp 不满足「连续三锚 > +0.2」, 水平未再升档; 不升级, 无动作)。
- **③ 执行漏斗(anchor_ts ∈ [00:00, 04:00)Z 09-11, 账本目录 20260911, VERIFIED)**: orders 478 = maker 282(partial_expired 161 / venue_reject **70**(-5022 58 + 重挂 -5022 11 + PIEVERSE -2027 1)/ skipped_min 51)+ topup 196(filled 53 / skipped_min 131 / no_chase_arm 12); k-cancel cancelled 30 / already_terminal 131 / unresolved 0 / errors 0; fills 361 去重(maker 229 / topup 132), Σ|成交| 8,844U; **maker 占比 0.643**(带 ≥0.90 之下第六锚: 0.623 / 0.817 / 0.696 / 0.693 / 0.762 / 0.643; 拒单反而减少 70 张, 是补单腿名义占比升), 费 2.72U = **3.07 bps**(带 1.8–2.3 之上, 六锚最高), 换手 **3.9%** of gross(稳态 ✓); chase 76 / no_chase 85 / 无 35; placement behind **0.493** ✓; -5022 拒单率按臂 behind 19% / join 25%(20Z 24% / 35%, 回落); -4400 0 张。
- **④ 记账(VERIFIED)**: realized_gross **228,447 / target 231,160(98.8%)**; NAV 115,663 × 2.0 = 231,326 ≈ target ✓, 场所杠杆 1.97; **net/gross −0.74%**(回到带内; 20Z −1.05%), net −1,696U; readback 248 行 246 非零; daily_nav 09-11 首行: **FUNDING_FEE −13.26**(00Z 结算 245 行 Σ **−13.26U** ≈ −0.58 bps/gross: 8h 名 65 + 4h 名 177 + 1h 名 3)/ REALIZED −12.73 / 费 −1.33; 未实现 −175; prev_nav 115,127 → nav 115,663(+536U, +0.47%, external_flow 0); guard_twin 01:35Z AGREE(lev 1.973, day_twin −0.41% 日内, cum_twin −2.76%); phase_C anchors_row ✓ readback 248 ✓ per_name_stop stopped [IOSTUSDT](cooldown 10 名); anchor done rc=0 00:58:30Z; **LIVE 看门狗 00:46:09Z tripped=False, blind [], partial [cond2, cond4]**(同前), n_days 42; 限流窗高水位 **965/2400**(近日最高, 0 等待; 观察)。
- **⑤ 执行质量**: 尺寸三桶 <500: 0.573(n=268; 20Z 0.620)/ <1500: 0.0(n=1)/ ≥1500: 0.0(n=1, PIEVERSE -2027)非负 ✓; markout 回填 00:50–00:58Z: day 09-09 写 116, 09-10 写 42(pending 308), 09-11 写 256(pending 361→104, deadline 截断; 累计 pending 2034 / 写 414)—— 在追; chase 单名连抽 20Z∩00Z 23 名(16Z∩20Z 27)。
- **⑥ 异常处置**: 无需动作(无回滚 / 无重启 / 无 PushNotification)。观察项: maker 占比第六锚带外且为六锚最低(0.643)、费 3.07 bps 六锚最高 —— 与 -5022 拒单数(70, 减少)方向相反, 机制转为补单腿名义占比升(53 张补单 / 132 笔 taker 成交), 04Z 再看; 生产者 forced_exit 连续两锚各 1 名(0.1–0.2% gross); 限流窗高水位 965; IOSTUSDT 名级止损持续; PIEVERSE 仍 -2027(截断修复在分支 b681ca5 未部署)。-5022 数据缺口(拒单行不带提交时点差/中价)已于 09-10 16Z 登记, 不重复。

### 2026-09-11 02:2xZ · 复审 b0a573a1 十五轮收口: 合并已执行, 部署未执行(实盘零接触)
- **研究员第十五轮(b6ad2c40, RESULT.json 01:15Z)**: APPROVE_CODE_MERGE_ONLY, new_confirmed_P1 0, checks 396 / full_chains 26 / consumer_readbacks 80; limits: 无独立 132 电池、无场所认证、Q6 与部署积压仍开、合并不含生产检出更新、无 alpha 主张。
- **合并(VERIFIED 02:04Z)**: 实盘 `origin/main` d040c74 → b681ca5(`git push origin review/b0a573a1-executor:main`, FF, 19 提交 27 文件 +5,098/−280, 无 state 文件); 研究 `multi-asset-v2` d8fcba06(no-ff 合并 3603ad6d)已推送。运行树 `~/dl_quant_live` HEAD = main = d040c74, 代码文件零改动, 落后 19; 五个从该树执行的 launchd 作业无一自动拉取。
- **部署前验收三件(02:07–02:12Z, 账本副本)**: (1) 三日 12 锚 `neutrality_price` 旧/新逐锚相等 12/12(两个 None 两侧同: 09-09 20Z、09-10 00Z 无该侧补单 taker 成交); 467 笔 taker 成交缺价 0 / 缺费 0 / 非 USDT 费 0; `chase_readout.collect` 共有键 0 差; (2) `watchdog.evaluate()` 42 日全量副本旧/新逐键 0 差, tripped False; (3) 回滚排演 revert d040c74..b681ca5 ⇒ 树 = d040c74(0 文件差)。
- **清理**: scratch `r9_red…r15_red` 7 份(≈1 GB)已删; worktree `~/dl_quant_live_wt/b0a573a1` 与 `quant_research_wt/b0a573a1` 已 remove + prune(分支保留); 研究员工作树未动。
- **部署 = 用户裁定**: `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`(前提五条 / 一条 pull --ff-only / 锚前核 / 首锚验收 / 回滚)。⚠ 运行目录 safe_commit 自带 rebase = 隐式部署, 部署前禁用。每锚深查新增: 运行树 HEAD vs origin/main。
- **量化结论**(`docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md`): 正常态零差; 差别只在异常态; 不改回测 / 效果预估 / 在役书; 无收益主张。

### 2026-09-11 05:4xZ · 每锚深查 04Z 锚(rid A1789100640, 04:24Z 执行; 首次触发; 只读, 实盘零接触)· 书 99.1%, net/gross −1.20% 首次越过 ±1% 观察带(执行器 1.5% 中性带内未动作), maker 占比 0.843 / 费 2.47 bps 回向带内但第七锚带外
- **① 守护(VERIFIED 05:39Z)**: 生产者 10900 = shadow.lock; sidecar 30943; combo 30944 = pid 文件; 沙盒 shadow_loop 50689 仍在(非生产者, 记录不动作)。
- **② 信号六项(VERIFIED)**: 生产者 04Z status OK / fund_updates **358**(4h 锚稳态 ~353 ✓)/ **forced_exit_n 2**(gross 0.0068 ≈ 0.7%; 连续第三锚 1 / 1 / 2, 名不在日志字段; 记录级)/ sel 259 / coverage 1.0 / w3 [0.3227, 0.0868, 0.5905] / runtime 232s / exinfo_ok / members 400 ✓ / turnover 2.4% / carry 1.22 bps; combo 1789099200 rc=0 04:20:55Z, n 259, gross 0.8606, kc/fc own, w3_masked [0.3534, 0, 0.6466] = 0.3227/(0.3227+0.5905) = 0.3534 ✓, 读者验收 ok(0.1s); FTRIM kc 9 / fc 9(00Z 10 / 10)。**反事实改写 0.234**(近八锚 0.223/0.226/0.232/0.228/0.230/0.231/0.234/0.234: 近三锚增量 +0.1/+0.3/0.0 不满足「连续三锚 > +0.2」, 水平未升档; 不升级, 无动作)。
- **③ 执行漏斗(anchor_ts ∈ [04:00, 08:00)Z 09-11, 账本目录 20260911, VERIFIED)**: orders 470 = maker 276(partial_expired 164 / venue_reject **57**(-5022 56 = 首挂 52 + 重挂 4; PIEVERSE -2027 1)/ skipped_min 55)+ topup 194(filled 42 / skipped_min 136 / no_chase_arm 16); k-cancel cancelled 28 / already_terminal 136 / unresolved 0 / errors 0; fills 283 去重(maker 204 / topup 79), Σ|成交| 10,998U; **maker 占比 0.843**(带 ≥0.90 之下第七锚: 0.623 / 0.817 / 0.696 / 0.693 / 0.762 / 0.643 / 0.843, 从最低点回升; 补单 taker 名义占比 15.7%), 费 2.72U = **2.47 bps**(带 1.8–2.3 之上, 从 3.07 回落), 换手 **4.8%** of gross(稳态 ✓); chase 臂 91 / no_chase 73(随机化 164; 治疗集 = skipped_no_chase_arm 16 行 / 残差 1,212U); placement behind 134 / join 136 / exempt 6 ⇒ **behind 0.496** ✓; -5022 拒单率按臂 behind 20% / join 33%(00Z 19% / 25%); -4400 0 张。
- **④ 记账(VERIFIED)**: realized_gross **228,340 / target 230,304(99.1%)**; NAV 114,949 × 2.0 = 229,897 ≈ target ✓, 场所杠杆 1.986; **net/gross −1.20%**(观察带 ±1% 之外, 三锚 −1.05 / −0.74 / −1.20; 执行器自身 neutral_only 中性带 1.5% = 3,412U, 书 net −2,881U 在带内 ⇒ fill [] 未动作, 按设计), net −2,741U, net/equity −2.38%; 旧码 neutrality_price 买侧 16 笔 27.36 bps ⇒ 补平价 ≈ 7.5U(下界); readback 250 行 246 非零; reshape: net −11,725 → 0, gross 215,378 → 230,314, 过底 3 名(IOSTUSDT / KSMUSDT / SAHARAUSDT), popped 13; daily_nav 04:44Z: **nav 114,949**(00Z 115,663 ⇒ 日内 −714U, −0.62%), realised +58.3(FUNDING −25.62 = 00Z −13.26 + 04Z **-12.40**(180 行, 4h / 1h 名)/ REALIZED +86.66 / COMMISSION −2.74), 未实现 −971, wallet 115,920; guard_twin 04:55Z DISAGREE(anchor_age 0.17h, n_inc_new 120)→ 05:15Z / 05:35Z **AGREE**(ledger-only; nav row stale; eq 115,263, day_twin −0.62%, cum_twin −2.97%, lev 1.976)—— 锚后首读 DISAGREE 与 09-10 00Z / 09-11 00Z 同型(收入行到达滞后), 非异常; phase_C anchors_row ✓ readback 250 ✓ per_name_stop stopped [IOSTUSDT](cooldown 10 名); anchor done rc=0 04:58:02Z; **LIVE 看门狗 04:45:37Z tripped=False, blind [], partial [cond2, cond4]**, n_days 42, public_path alive 214 ms; 限流窗高水位 **812**(00Z 965), 订单 427; funding_span STALE(07-25 表, 已告警不重复, 老项)。**运行树 d040c74 vs origin/main b681ca5: 落后 19 提交 = 未部署(用户裁定中), 照常报不动作。**
- **⑤ 执行质量**: 尺寸三桶 <500: 0.623(n=217; 00Z 0.573)/ <1500: 0.50(n=2)/ ≥1500: 0.447(n=2)非负 ✓; markout 回填 04:58Z: pending 1,716 / written 382 / requests 347 / budget 728s(00Z pending 2,034 / 414)—— 在追, 缺口收窄 318; chase 单名连抽 00Z∩04Z **39** 名(20Z∩00Z 23; 分配为每锚哈希, 76 × 0.5 ≈ 38 为随机预期, 非异常)。
- **⑥ 异常处置**: 无需动作(无回滚 / 无重启 / 无 PushNotification)。观察项: **net/gross −1.20% 首次越过 ±1% 观察带**(执行器 1.5% 带内未 fill; 08Z 再看: 若连续两锚 |net/gross| > 1.5% 且 neutral_only 仍 fill [] ⇒ 查 C 臂); 生产者 forced_exit 连续三锚 1 / 1 / 2 名(0.7% gross, 名待查); maker 占比 / 费回向带内但第七锚带外; IOSTUSDT 名级止损持续; PIEVERSE 仍 -2027(截断修复在 b681ca5 未部署); 09-09 12Z 52 行写回等部署。-5022 数据缺口已登记不重复。

### 2026-09-11 09:4xZ · 每锚深查 08Z 锚(结算锚, rid A1789115039, 08:23Z 执行; 首次触发; 只读, 实盘零接触)· ★ E-0910-A 场所量化规则锁**复发**(第二次), 补单腿零成交; net/gross −1.44% 逼近执行器 1.5% 动作带
- **① 守护(VERIFIED 09:39Z)**: 生产者 10900 = shadow.lock; sidecar 30943; combo 30944 = pid 文件; 沙盒 shadow_loop 50689 仍在(非生产者, 记录不动作)。
- **② 信号六项(VERIFIED)**: 生产者 08Z status OK / fund_updates **457**(结算锚稳态 ~453 ✓)/ **forced_exit_n 2, gross 0.0095**(连续第四锚 1/1/2/2, gross 0.0018→0.0068→0.0095 递增; 名不在日志字段; 记录级)/ sel 261 / coverage 1.0 / members 400 ✓ / w3 [0.3262, 0.0920, 0.5818] / runtime 263s / exinfo_ok / turnover 3.2% / carry 1.169 bps / gross_pos 0.8947; combo 1789113600 rc=0 08:21:12Z, n 260, gross 0.8541, **kc/fc own** ✓, 读者验收 ok(0.9s), f10 打分 **400** ✓, phi 0.45, net_after_reshape −0.0; **w3_masked [0.359218, 0, 0.640782] = 0.3262/(0.3262+0.5818) = 0.3593 逐位相符** ✓; rho_kc_fc 0.9424(近 10 锚单调缓降 0.9582→0.9424, **非跳变**, 记录级)。**反事实改写 0.2403 为近八锚新高**(0.226/0.2323/0.2281/0.2300/0.2310/0.2341/0.2340/0.2403; 近三锚增量 +0.31/−0.01/+0.63 pp, 不满足「连续三锚 >+0.2pp」⇒ **不升级, 无动作**)。
- **③ 执行漏斗(anchor_ts ∈ [08:00, 12:00)Z, VERIFIED)**: orders **502** = maker 282(partial_expired 184 / venue_reject **68**(-5022 67 + PIEVERSE -2027 1)/ skipped_min 30)+ topup 220(skipped_min 125 / **abandoned_max_attempts 73** / skipped_no_chase_arm 22 / **filled 0**); k-cancel cancelled 59 / already_terminal 125 / unresolved 0 / errors 0; fills **179 去重**(原始 358 行, **50% 重复 trade_id** —— 已知缺陷, 任何费用/名义求和必须先按 trade_id 去重), Σ|成交| 9,459U, **maker 占比 1.000**(无 taker 成交), 费 1.89U = **2.00 bps**(带 1.8–2.3 **带内** ✓, 近八锚首次回带); 换手 3.2%(稳态 ✓); placement behind 137 / join 139 / exempt 6 ⇒ **behind 0.492** ✓; -5022 拒单率 behind 23% / join 30%; chase 87 / no_chase 81 / chase_forced 16(随机化 168)。
- **★ ③-异常 E-0910-A 复发(VERIFIED, 逐行核回执)**: 73 张 `abandoned_max_attempts` 补单**全部**带 `[-4400] Futures Trading Quantitative Rules violated, only reduceOnly order is allowed`, attempt_idx 全为 2(即每张都重试到上限), Σ|意图| **4,014U**(均 55U/张), 成交 0。与 **09-10 00Z 那次(71 张, 同一文案)同型, 为该错误自登记以来第二次**。全史 `abandoned_max_attempts` 仅出现在这两个锚。本次**无 -4400 以外的新错误码**, 且 maker 腿正常成交 ⇒ 书仍建到 98.2%(对比 09-10 00Z 只建到 67%), 影响远小。**未动作**(只读)。⚠ 执行器的 -4400 熔断(`skipped_venue_lock`: 首张 -4400 后不再发后续开仓单)**已在 b681ca5 合并进 origin/main 但未部署**; 现网仍逐张重试到上限, 本锚即产生约 146 次对场所违规计数器的无谓请求。**本锚是该修复的一次实盘证据, 部署仍归用户裁定。**
- **④ 记账(VERIFIED)**: realized_gross **227,251 / target 231,427(98.2%)**; 场所杠杆 1.958–1.964; **net/gross −1.4447%**(近八锚 −1.08/−0.96/−1.00/−0.92/−1.05/−0.74/−1.20/**−1.44**, **连续第二锚在 ±1% 观察带外且继续恶化**), net −3,283U, net/equity −2.84%。**执行器自身 neutral_only 中性带 1.5% ⇒ 约 3,409U, 当前 net 已达其 96%** —— 12Z 若跨线, 执行器将按设计填 neutral_only 集合(行为变化, 属设计内, 非异常)。reshape: net −14,166 → 1.6e-12, gross 216,103 → 231,446, 过底 1 名(IOSTUSDT), popped 13, max_name_delta 0.107pp。**neutrality_price: n_fills_basis 0, bps None** —— 与"补单腿零成交"一致, 非缺陷。daily_nav 08:44Z: nav **115,462**(prev_day 115,127, +336U), realised −69.19(**FUNDING −39.20** = 00Z −13.26 + 04Z −12.40 + 08Z **−13.52**(245 行)/ REALIZED −26.40 / COMMISSION −3.60), 未实现 −327.87; readback 251 行 247 非零; per_name_stop / phase_C 三件齐; **anchor done rc=0 08:56:03Z**; **LIVE 看门狗 08:46:28Z tripped=False, triggers [], metric_errors [], blind [], partial [cond2, cond4], n_days 42**; guard_twin 09:16Z / 09:36Z **AGREE**(ledger-only; nav row stale; lev 1.958–1.964, day_twin −0.24%, cum_twin −2.59%); 限流窗高水位 **1065**(近日最高, 04Z 812 / 00Z 965; 订单 252)。
- **⑤ 执行质量**: 尺寸三桶 <500 **0.522**(n=247; 04Z 0.623)/ <1500 0.501(n=2)/ ≥1500 0.303(n=3), **非负 ✓** 但三桶均低于 04Z; markout 回填 08:50–08:56Z: day 09-10 写 17(pending 195), 09-11 写 186(pending 223), **累计 pending 1,358 / 写 291**(04Z pending 1,716)—— **在追, 缺口收窄 358**。
- **⑥ 异常处置**: **无需动作**(无回滚 / 无重启 / 无 PushNotification —— 书建到 98.2%, 看门狗未触发, guard_twin AGREE, 本次 -4400 影响被 maker 腿吸收, 与 09-10 00Z 那次不同级)。观察项按优先级: (1) **net/gross −1.44% 已达执行器 1.5% 动作带的 96%**, 12Z 跨线则触发 neutral_only 填充; (2) **E-0910-A 第二次复发**, 锁的解除时点未知(需签名端点 `apiTradingStatus`, 本轮按纪律未调), 12Z 看是否仍在; (3) forced_exit 连续四锚且 gross 递增至 ~1.0%; (4) 反事实改写 0.2403 新高但判据未满足; (5) 限流窗高水位 1065 近日最高; (6) IOSTUSDT 名级止损持续并再次过底; (7) PIEVERSE 仍 -2027(截断修复在 b681ca5 未部署)。-5022 数据缺口已登记不重复。
- **⑦ 分栏**: **已验证** = ①②③④⑤ 全部读数与 -4400 回执逐行核对; **待验证** = -4400 锁的解除时点(需签名端点)、forced_exit 涉及的具体名(日志字段不含); **推断** = 「maker 腿吸收了补单腿缺口故影响小」(由 98.2% 建仓率与 maker 占比 1.000 推断, 未做反事实)。

### 2026-09-11 13:4xZ · 每锚深查 12Z 锚(rid A1789129439, 12:20Z 执行; 首次触发; 只读, 实盘零接触)· ★ E-0910-A 锁**已解除**; 当日转正 +0.95%; 反事实改写 0.246 新高且连续第二次增量 >+0.2pp
- **① 守护(VERIFIED 13:39Z)**: 生产者 10900 = shadow.lock; sidecar 30943; combo 30944 = pid 文件; 沙盒 50689 仍在(非生产者, 记录不动作)。
- **② 信号六项(VERIFIED)**: 生产者 12Z status OK / fund_updates **356**(4h 锚稳态 ~353 ✓)/ forced_exit_n 2, **gross 0.0016**(08Z 0.0095 ⇒ **幅度回落一个量级**, 连续第五锚有名但已非递增)/ sel 259 / coverage 1.0 / members 400 ✓ / w3 [0.3246, 0.0902, 0.5852] / runtime 234s / exinfo_ok / turnover 2.5%(稳态 ✓)/ carry 1.314 bps / cost 0.082 / gross_pos 0.8971; combo 1789128000 rc=0 12:20:45Z, n 258, gross 0.8582, **kc/fc own** ✓, 读者验收 ok(0.1s), f10 打分 **400** ✓, phi 0.45, net_after_reshape 0.0; **w3_masked [0.356752, 0, 0.643248] = 0.3246/(0.3246+0.5852) = 0.3568 逐位相符** ✓; rho_kc_fc 0.940(延续单调缓降 0.9582→0.940)。**★ 反事实改写 0.2460 为新高**(近八锚 0.2323/0.2281/0.2300/0.2310/0.2341/0.2340/0.2403/**0.2460**; 近三锚增量 **−0.01 / +0.63 / +0.57 pp** ⇒ **连续两次 >+0.2pp, 差一次满足「连续三锚」判据**)。**本锚不升级; 16Z 若再出一次 >+0.2pp 的增量则判据触发, 按预注册升级并报。**
- **③ 执行漏斗(anchor_ts ∈ [12:00, 16:00)Z, VERIFIED)**: orders **511** = maker 294(partial_expired 174 / venue_reject **87**(-5022 86 + PIEVERSE -2027 1)/ skipped_min 32 / filled 1)+ topup 217(skipped_min 174 / **filled 43**); **`abandoned_max_attempts` = 0, 无任何 -4400 回执 ⇒ ★ E-0910-A 场所量化规则锁已解除**(08Z 那次 73 张全被 -4400 拒, 本锚补单腿恢复正常成交 43 张)。fills **435 去重**(原始 798, **45% 重复 trade_id**), Σ|成交| 13,850U, **maker 占比 0.816**(08Z 1.000 是因补单腿归零, 本锚恢复常态), 费 3.54U = **2.55 bps**(带 1.8–2.3 之上, 08Z 曾回带内); placement behind 140 / join 147 / exempt 7 ⇒ **behind 0.488** ✓; **-5022 拒单升至 87**(08Z 68), 分臂 behind 28% / **join 39%**(08Z 23%/30%, 两臂同步上升); chase 93 / no_chase 81(随机化 174)。
- **④ 记账(VERIFIED)**: realized_gross **236,345 / target 234,259 = 100.9%**(略超, 记录); 场所杠杆 ≈2.03; **net/gross −1.304%**(08Z −1.4447% ⇒ 略有收敛, 仍在 ±1% 观察带外), net −3,082U, net/equity −2.65%。**★ 中性带未被跨越**: `neutral_only` 记录 band 1.5% / tolerance 3,469U / **book_net_usdt −2,201 / net_over_gross_before −0.952%** ⇒ **补单前书的净额在带内**, `band_reached=True`, `fill` 空, `filled_notional_usdt` 0, `n_worsening_skipped` 61。**⇒ 我在 08Z 报的「12Z 可能跨线触发 neutral_only 填充」没有发生; 原因是该判据用的是补单前的 book_net(−0.95%), 而不是我引用的场所 readback 后的 net/gross(−1.44%), 两者不是同一个量 —— 此处更正我自己的口径。** reshape: net −13,945 → −1.6e-12, gross 218,666 → 234,280, **过底 2 名(IOSTUSDT + KSMUSDT)**(08Z 1 名), popped 12。**★ `neutrality_price` = 235.46 bps(n_fills_basis 36)** —— 较常态 ~2–3 bps 高约 100 倍; 该字段**仅测量不驱动任何动作**, 且现网代码无三桶/覆盖率字段(在 b681ca5 未部署), 故无法判断分母是否含未定价成交 ⇒ **记录级异常, 16Z 复看**。daily_nav 12:46Z: **nav 116,220**(prev_day 115,127, **+1,093U = +0.95%**, external_flow 0)⇒ **当日转正**; realised −20.08(**FUNDING −52.62** = 00Z −13.26 + 04Z −12.40 + 08Z −13.52 + 12Z 段 −13.44 / REALIZED **+38.69** / COMMISSION −6.15); **未实现 +387.82**(08Z −327.87); readback 251 行 248 非零; phase_C 三件齐; **anchor done rc=0 12:58:28Z**; **LIVE 看门狗 12:46:23Z tripped=False, triggers [], metric_errors [], blind [], partial [cond2, cond4]**, n_days 42; guard_twin 13:16Z / 13:36Z **AGREE**(day_twin **+0.292 → +0.571**, cum_twin −1.804, wd_cum −2.444); 限流窗高水位 **1045**(08Z 1065, 订单 480)。
- **⑤ 执行质量**: 尺寸桶 <500 **0.694**(n=261; 08Z 0.522, **明显改善**)/ ≥1500 0.0(n=1), 非负 ✓(本锚无 <1500 桶样本); markout 回填 12:50–12:58Z: day 09-10 pending 165 写 13; day 09-11 pending 464 写 325 **CAPPED(deadline)**, 二次 pending 139 写 0 **CAPPED** ⇒ **连续两次撞到截止预算上限**, 队列在增长, 观察。
- **⑥ 异常处置**: **无需动作**(无回滚 / 无重启 / 无 PushNotification)。观察项按优先级: (1) **反事实改写连续两次增量 >+0.2pp 且创新高 0.246 —— 16Z 再出一次即触发升级判据**; (2) `neutrality_price` 235 bps 的 100 倍离群(仅测量); (3) -5022 拒单 87 张、join 臂拒单率升至 39%; (4) markout 连续两次撞 deadline 上限; (5) 过底名增至 2 个(IOSTUSDT + KSMUSDT); (6) 费 2.55 bps 再次带外; (7) net/gross −1.30% 仍带外但在收敛。**已解除**: E-0910-A -4400 锁。
- **⑦ 分栏**: **已验证** = ①②③④⑤ 全部读数, 含 `neutral_only` 字段逐项与 -4400 回执计数; **待验证** = `neutrality_price` 235 bps 的分母构成(现网缺三桶字段)、forced_exit 的具体名(日志不含)、markout 队列增长是否会自愈; **推断** = 「maker 占比回到 0.816 是因补单腿恢复」(由 abandoned=0 与 topup filled 43 推断)。**更正**: 08Z 报告中「net/gross 已达执行器 1.5% 动作带的 96%」口径有误 —— 动作判据用的是补单前的 `book_net_usdt`(本锚 −0.952%), 非场所 readback 后的 net/gross。

### 2026-09-11 17:2xZ · 每锚深查 16Z 锚(结算锚, rid A1789143840, 16:21Z 执行; 首次触发; 只读, 实盘零接触)· 两个观察项均已结; ★ 新趋势: -5022 拒单单调恶化, maker 占比跌至 0.665
- **① 守护(VERIFIED 17:22Z)**: 生产者 10900 = shadow.lock; sidecar 30943; combo 30944 = pid 文件; 沙盒 50689 仍在(非生产者)。
- **② 信号六项(VERIFIED)**: 16Z status OK / fund_updates **454**(结算锚稳态 ~453 ✓)/ **forced_exit_n 0, gross 0**(前五锚 1/1/2/2/2, **连续序列中断**)/ sel 262 / coverage 1.0 / members 400 ✓ / w3 [0.3245, 0.0982, 0.5773] / runtime 288s / turnover 2.9%(稳态 ✓)/ carry 1.023 / gross_pos 0.8999; combo rc=0 16:21:33Z, n 260, gross 0.8604, **kc/fc own** ✓, 读者验收 ok(0.4s), f10 **400** ✓, net_after_reshape 0.0; **w3_masked [0.359851, 0, 0.640149] = 0.3245/(0.3245+0.5773) = 0.3598 逐位相符** ✓; rho_kc_fc 0.9398(延续缓降)。**★ 观察项①已结: 反事实改写 0.2453(12Z 0.2460, 回落), 近三锚增量 +0.63 / +0.57 / −0.07 pp ⇒ 「连续三锚 >+0.2pp」判据未满足, 连升中断, 不升级。**
- **③ 执行漏斗(anchor_ts ∈ [16:00, 20:00)Z, VERIFIED)**: orders **525** = maker 301(partial_expired 168 / venue_reject **105**(-5022 **104** + PIEVERSE -2027 1)/ skipped_min 28)+ topup 224(skipped_min 153 / **filled 64** / no_chase 7); **`abandoned_max_attempts` = 0 ⇒ E-0910-A 锁持续解除** ✓。fills **421 去重**(原始 766, 45% 重复 trade_id), Σ|成交| 13,705U, **maker 占比 0.665**(12Z 0.816, 08Z 1.000 ⇒ **明显下滑**), 费 4.12U = **3.01 bps**(带 1.8–2.3 之上, 近日最高)。**commission_asset 421/421 全为 USDT ⇒ E-0911-C 的 BNB 换算问题本锚不适用**(记录: 该缺陷只在含 BNB 行的锚上咬)。
- **★ ③-新趋势(VERIFIED, 需跟踪)**: **-5022 拒单单调上升 57 → 70 → 68 → 87 → 104**(近五锚); 分臂拒单率 **join 25% → 30% → 39% → 45%**, behind 20% → 23% → 28% → **29%**。**placement behind 占比 0.403**(设计点 ≈0.50; 前三锚 0.492 / 0.488 / 0.496)—— **首次明显低于 0.50**。机制链: post-only 被拒 ⇒ 量被推到补单 taker 腿(filled 43 → 64)⇒ maker 占比跌、费用升(2.00 → 2.55 → 3.01 bps)。**三条读数同向, 不是噪声。20Z 必须复看。**
- **④ 记账(VERIFIED)**: realized **232,155 / target 232,417 = 99.9%**; 场所杠杆 2.001; **net/gross −1.122%**(近三锚 −1.44 → −1.30 → **−1.12**, 在收敛但仍带外), net −2,605U, net/equity −2.24%。**neutral_only: band 1.5% / tolerance 3,487U / book_net −3,024U / net_over_gross_before −1.3009% ⇒ 已达动作带的 86.7%**(12Z 为 63.4%)—— 仍 `band_reached=True` 且 `fill` 空。reshape: net −13,176 → 0.0, gross_after 232,435, **过底 5 名**(1000SHIB / HOLO / IOST / KSM / MET; 12Z 2 名, 08Z 1 名 ⇒ **递增**), popped 11。**★ 观察项②有进展: `neutrality_price` = 70.717 bps(n_fills_basis 49, 买侧, 需 2,605U, 价 18.42U)—— 较 12Z 的 235.46 大幅回落, 说明那次是瞬态; 但仍约为常态 2–3 bps 的 25 倍。现网无三桶字段故仍不能定因, 继续跟踪。** daily_nav 16:46Z: **nav 116,322**(prev_day 115,127, **+1,195U = +1.04%**)⇒ **连续第二个正日**; realised **+84.86**(FUNDING −68.00 / **REALIZED +160.14** / COMMISSION −7.28); 未实现 **+365.35**; readback 253 行 250 非零; **anchor done rc=0 16:57:10Z**; **LIVE 看门狗 16:46:36Z tripped=False, triggers [], metric_errors [], blind [], partial [cond2, cond4]**, n_days 42; guard_twin 16:57Z DISAGREE(anchor_age 0.18h, 锚后首读同型)→ 17:17Z **AGREE**(lev 2.001, day_twin +0.277, cum_twin −2.092)。
- **⑤ 执行质量**: 尺寸桶 <500 **0.517**(n=272; 12Z 0.694 ⇒ 回落)/ ≥1500 0.0(n=1), 非负 ✓; markout 回填 16:57Z: day 09-11 pending 516 写 321; 累计 **pending 1,292 / 写 332**(12Z 1,358), **未撞 deadline 上限**(12Z 连撞两次)⇒ 队列在收窄。
- **⑥ 异常处置**: **无需动作**(无回滚 / 无重启 / 无 PushNotification)。观察项按优先级: (1) **★ -5022 / join 拒单率 / behind 占比 三条同向恶化**, 20Z 复看, 若继续则查 post-only 定价与盘口的关系; (2) net/gross 虽收敛但补单前 book_net 已达动作带 86.7%; (3) 过底名 1 → 2 → 5 递增; (4) maker 占比 0.665 与费 3.01 bps 均为近日最差; (5) `neutrality_price` 仍 25 倍于常态; (6) IOSTUSDT 名级止损持续。**已结**: 反事实改写升级判据(未触发); E-0910-A(持续解除); forced_exit 连续序列(中断)。
- **⑦ 分栏**: **已验证** = ①②③④⑤ 全部读数, 含 -5022 逐锚计数与 commission_asset 全量分布; **待验证** = `neutrality_price` 25 倍离群的分母构成(现网缺三桶字段)、-5022 恶化的机制(需 post-only 提交价对盘口的逐单数据, 而拒单行不带 spread/mid —— 即已登记的 -5022 数据缺口); **推断** = 「maker 占比下滑与费用上升由 -5022 推量到 taker 腿所致」(由拒单数与 topup filled 同向变化推断, 未做反事实)。

---

## 2026-09-11 20:00Z 锚 · 全深度深查(只读, 实盘零接触)

**锚**: canonical 1789156800 (20:00Z) / 执行器 anchor_ts 1789158241.472 (20:24:01Z)。**结论: 无异常处置需求; 此前三项恶化指标全部反转。**

### ① 三守护(按句柄验) — 全绿
| 守护 | 句柄文件 | PID | launchd | 运行时长 |
|---|---|---|---|---|
| shadow_loop_v3 | `~/wide_shadow/shadow.lock` = 10900 | 10900 ✓ | com.hsy.shadowloop 10900 | 6d 08:57 |
| sidecar_daemon.sh | — | 30943 | com.hsy.sidecar 30943 ✓ | 12d 16:41 |
| combo_live_daemon.sh | `~/wide_shadow/fea171/combo_live_daemon.pid` = 30944 | 30944 ✓ | com.hsy.combolive 30944 ✓ | 12d 16:41 |

注: `~/cc_tmp/exec_n6_sandbox/shadow_loop_v3.py` (PID 50689) 是研究沙箱副本, 非在役链路。

### ② 信号六项 — 全部在带
- **生产者**: status OK, coverage 1.0, members 400, sel 261, **fund_updates 355**(4h 非 8h 结算锚稳态 ~353 ✓), forced_exit_n 2 (gross 0.0024), turnover 0.03215, gross_pos 0.899, carry 1.08 bps, cost 0.111 bps, runtime 230.4s, missing 0, future_dropped 0, data_max_ts 匹配。
- **w3** = [0.3227, 0.0973, 0.58] ⇒ **w3_masked king = 0.3227/0.9027 = 0.3575**, 与 target_combo 自报 [0.357498, 0.0, 0.642502] 一致 ✓
- **combo_live_status**: anchor 1789156800 匹配 ✓, ok true, step done, **reader_ok true**, n 259, gross 0.8599, age_s 0.9
- **target_combo**: phi 0.45, book_form combo_v2main_norev24, **kc_state_source/fc_state_source 均 own** ✓, **n_f10_scored 400** ✓, rho_kc_fc 0.9401, net_after_reshape −0.0
- **反事实改写幅度 = 24.50%** (L1 差 / L1_king; n_live 259 vs n_king 261)。上一锚 24.53% ⇒ **增量 −0.03pp, 未触发升级**(判据: level 再升一档 或 连续 3 锚增量 > +0.2pp)

### ③ 执行漏斗(按执行器 anchor_ts 归属)
**★ 方法更正(我方本轮自犯)**: fills.jsonl 的重复 trade_id **不是脏数据** —— `ops/backfill_markout.py` 以**同 trade_id 追加新行**的方式回填 mark, 由 `pilot_metrics.dedupe_fills` **后写胜出**合并。我首跑写成先写胜出, 把带 mark 的行全丢了, 误读出 "markout 回填 0%"。已改正。

| 项 | 读数 | 带 | 判 |
|---|---|---|---|
| orders | 497 (= anchors.rows_persisted 497 ✓) | — | ✓ |
| fills 原始 / 去重(后写胜出) | 666 / 346 | — | ✓ |
| 终态 | skipped_min_notional 222, partial_expired 193, venue_reject 50, filled 27, skipped_no_chase_arm 5 | — | — |
| order_type | maker 280, topup_taker 217 | — | — |
| **maker 占比** | 行 **0.8237** / 名义 **0.8846** | ≥0.90 | **带外(名义差 1.5pp)** |
| **费** | **2.3463 bps** (maker **2.0000** / taker **5.0000**, 全 USDT 计价) | maker 1.80–2.3 | maker 在带上沿 |
| 换手(生产者权重口径) | 3.215% | 2–5.5% | ✓ |
| 换手(执行器 traded/gross) | **8.9%** | — | **口径差 2.77×, 见下** |
| chase 分臂 | requote 50 / direct 21 / 其余 None | — | — |
| **behind 占比** | **0.5584** (maker 腿排除 exempt) | ≈0.50 | ✓ |

**venue_reject 50 明细**: **−5022** (post-only 会立刻成交) **49**(46 首发 + 3 重挂), **−2027**(超场所仓位上限) **1**。
分臂拒单率: **join 0.2479** (30/121) / **behind 0.1307** (20/153) / exempt 0。合计 maker 拒单率 0.1786。

### ④ 记账
| 项 | 值 | 判 |
|---|---|---|
| venue_gross_usdt | 233,032.85 | target 234,906.53 ⇒ realized/target **0.9920** ✓ |
| NAV | 117,515.79 | gross/NAV = **1.9993** ≈ 2.00 ✓ |
| venue_net_usdt | −1,670.62 | — |
| **net_over_gross** | **−0.7169%** | ±1% 带内 ✓ (1.5% 动作带的 47.8%) |
| net_over_equity | −1.4216% | — |
| opening_halted | False | ✓ |
| 20:00Z 结算 FUNDING_FEE | **−13.90 USDT** (183 行, interval_h: 4h×181 / 1h×2) | 20Z 对 4h 周期名是结算锚 |
| 当日 Σfunding_paid | −81.64 USDT | — |
| phase_C readback | 255 行 ✓ | — |
| per_name_stop | **无命中** | ✓ |
| `state/anchor_runs.log` 末行 | `2026-09-11T20:58:06Z anchor done rc=0` | ✓ |
| **guard_twin** | **AGREE** (ledger-only; nav 行 stale) eq=117,549.52 | ✓ |
| known_gaps | 6 名, gross 2,614.92U, net 1,727.56U, venue_cap = PIEVERSEUSDT | — |
| reshape | net_before −11,644.14 → net_after ~0 ✓; gross 221,073 → 234,946 | ✓ |
| regime_at_anchor | normal | — |

**当日 NAV**: 前日 115,126.80 → **117,515.79**, **+2,388.98 = +2.075%**(外部划转 0)。已实现 +124.73(REALIZED_PNL +215.43 / FUNDING_FEE −81.81 / COMMISSION −8.89), 未实现 +1,519.58。**连续第三个正日。**

### ⑤ 执行质量
- **尺寸梯度三桶**(我方自建: 已下单腿按 intended_notional 三分位): small 0.7676 / mid 0.8063 / **large 0.6707** ⇒ **非负性不成立**(大桶比中桶低 13.6pp)。**标 待验证** —— 分桶是我自己构造的, 非既有仪器。
- **markout 回填**: 本锚 **320/346 = 92.5%**; 近八日 85.0%–100.0%。**健康。**
- **本锚名义加权 60s markout = +3.9732 bps**(正 = 价格朝我们走, n=320, 覆盖名义 12,979.70)。**与 r11 全窗均值 −2.66 bps 反号** —— 单锚读数, 不外推。
- **chase 单名连抽**: 25 个名字有 2 次 requote, 无 3 次及以上。

### ⑥ 异常处置 — **无需处置**
本锚告警 4 条, 全部为已知形态:
1. INFO/HIGH: 8 个持仓名被场所扣住(maxNotionalValue=0), reduce-only。add_blocked=[MANAUSDT, IOSTUSDT], flatten_only=[OPENUSDT, ZBTUSDT, EVAAUSDT, MMTUSDT]
2. HIGH: **−2027** 场所仓位上限拒单 PIEVERSEUSDT +2,171U, 规划器只截断
3. INFO/HIGH: 24 个 maker 被 −5022 拒, 残差按全额进 taker 补单
4. INFO/HIGH: 限流计数差值, 场所记的用量比本进程高 940 权重/分(公布限额 2400/分)。**该文件自陈归属未定**(被封 IP 是 CloudFront 边缘 130.176.187.x, 非本方出口 103.252.201.68), 不喂任何决策。

### ⑦ 与前几锚对比 — **三项恶化全部反转**
| 指标 | 04Z→16Z 轨迹 | **本锚 20Z** | 判 |
|---|---|---|---|
| −5022 拒单数 | 57→70→68→87→**104** | **49** | **反转** |
| join 臂拒单率 | 25%→30%→39%→**45%** | **24.8%** | **反转** |
| behind 占比(设计点 0.50) | **0.403** | **0.5584** | **回到设计点上方** |
| maker 占比 | 0.816→**0.665** | 0.8237 行 / 0.8846 名义 | **回升, 仍差 1.5pp 到 0.90** |
| 费 bps | 2.55→**3.01** | **2.3463** | **回落** |
| net_over_gross | −1.20% / −0.952% / −1.304% | **−0.7169%** | **收窄** |

### 待验证 / 推断分栏
**已验证(本机第一手)**: ①②③④ 全部读数; markout 回填率; 分臂拒单率; NAV 与当日损益分解; guard_twin AGREE; anchor done rc=0。
**待验证**: (a) 尺寸梯度三桶非负性 —— 分桶为我方自建, 需与既有仪器口径对齐后再判; (b) **执行器换手 8.9% vs 生产者 3.215% 的 2.77× 口径差** —— r11 已将其登记为"书里最大的未归因口径差, 且正压在每一条成本判决下面", 未闭合; (c) 告警 3 的 24 名 vs 账本 49 单, 分母不同(名 vs 单), 属已知形态([[reject_rate_alarm_denominator]])。
**推断**: 三项恶化反转的**原因**未测 —— 可能是场所侧点差/深度状态变化, 也可能是 behind 占比回到 0.50 带来的一阶效应。本文不下因果结论。

### 与研究线的交叉(只记, 不动)
本锚费 maker **恰好 2.0000 bps**、taker **恰好 5.0000 bps**、346 笔 commission_asset **全部 USDT** —— **独立再证 r11 的发现: BNB 手续费折扣自 2026-09-07 起已断, 账户在 VIP0 底档**。恢复折扣值约 +1.5% NAV/年(r11 定价)。**属 sizing/运维裁定域, 本文只报不动。**

---

## 2026-09-12 00:00Z 锚 · 全深度深查(只读, 实盘零接触)

**锚**: canonical 1789171200 (00:00Z, **8h 结算锚**) / 执行器 anchor_ts 1789172641.107 (00:24:01Z)。**结论: 无异常处置需求; 但有四项要跟踪, 其中两项本锚新出现。**

### ① 三守护 — 全绿(句柄为准)
| 守护 | 句柄 | PID | launchd | 运行时长 |
|---|---|---|---|---|
| shadow_loop_v3 | `shadow.lock` = 10900 | 10900 ✓ | shadowloop 10900 | 6d 12:51 |
| sidecar_daemon.sh | — | 30943 | sidecar 30943 ✓ | 12d 20:35 |
| combo_live_daemon.sh | `fea171/combo_live_daemon.pid` = 30944 | 30944 ✓ | combolive 30944 ✓ | 12d 20:35 |

`shadowloop` 的 last_exit = −15 是**历史退出码**(进程已连续运行 6d12h), 非本锚事件。PID 50689 = `cc_tmp/exec_n6_sandbox` 研究沙箱, 非在役。

### ② 信号六项 — 全部在带
status OK / coverage 1.0 / members 400 / sel 262 / **fund_updates 454**(8h 结算锚稳态 ~453 ✓) / forced_exit_n **0** / turnover 0.02404 / gross_pos 0.8968 / carry 1.065 bps / cost 0.079 bps / runtime 275.9s / missing 0 / future_dropped 0 / data_max_ts 匹配。
w3 = [0.3185, 0.1048, 0.5768] ⇒ **w3_masked king = 0.3557**, 与 target_combo 自报 [0.355733, 0.0, 0.644267] 一致 ✓
combo_live_status: anchor 匹配 ✓ / ok / done / **reader_ok true** / n 261 / gross 0.8635 / age_s 0.8
target_combo: phi 0.45 / combo_v2main_norev24 / **kc·fc 均 own** ✓ / **n_f10_scored 400** ✓ / net_after_reshape 0.0 / rho_kc_fc 0.9369
**反事实改写 = 24.52%**。序列 24.53(16Z) → 24.50(20Z) → **24.52**(本锚), 增量 **+0.02pp**, **未触发升级**。

### ③ 执行漏斗(按执行器 anchor_ts 归属; fills 去重=**后写胜出**)
orders **458**(= rows_persisted 458 ✓) / fills 原始 547 → 去重 **285**
终态: skipped_min_notional 211 · partial_expired 148 · **venue_reject 56** · filled 35 · skipped_no_chase_arm 8
order_type: maker 278 / topup_taker 180
**venue_reject 56** = **−5022 五十五单**(47 首发 + 8 重挂) + **−2027 一单**(PIEVERSEUSDT)
分臂拒单率: join **0.2148**(29/135) / behind **0.1825**(25/137) / exempt 0.3333(2/6, n 太小)
**behind 占比 = 0.5037**(排除 exempt) — 设计点 0.50 ✓
requote 44 / direct 24 / exempt 2

### ④ 记账
| 项 | 值 | 判 |
|---|---|---|
| venue_gross_usdt | 234,372.22 | target 236,408.84 ⇒ **0.9914** ✓ |
| NAV | 118,120.06 | gross/NAV = **1.9842** ≈ 2.0 ✓ |
| **net_over_gross** | **−1.0192%** | **★ 略越 ±1% 观察带**(上锚 −0.7169%) |
| net_over_equity | −2.0222% | — |
| opening_halted | False | ✓ |
| **00:00Z 结算 FUNDING_FEE** | **−14.7963 USDT**(252 行; interval_h 4h×182 / 8h×68 / 1h×2) | 8h 名出现, 与 fund_updates 454 自洽 ✓ |
| phase_C readback | 255 行 ✓ | — |
| per_name_stop | **无命中** | ✓ |
| `state/anchor_runs.log` 末行 | `2026-09-12T00:53:53Z anchor done rc=0` | ✓ |
| **guard_twin** | **AGREE**(ledger-only; nav 行 stale) eq=118,129.68, day_twin 0.023 | ✓ |
| n_names_skipped | 91(上锚 55) | ★ 上升 |
| known_gaps | 9 名, gross 2,613.81U, net 2,334.97U, venue_cap = PIEVERSEUSDT | — |
| reshape | net_before −11,395.49 → net_after 9.84e-12 ✓; gross 222,484 → 236,443 | ✓ |

**当日 NAV**: 前日 117,515.79 → **118,120.06**, **+604.28 = +0.514%**(外部划转 0, 当日仅 00Z 一锚)。已实现 +57.47(REALIZED_PNL +73.29 / FUNDING_FEE −14.80 / COMMISSION −1.03), 未实现 +2,065.34。**连续第四个正日。**

### ⑤ 执行质量
- **maker 占比 行 0.7579 / 名义 0.7738** — 带 ≥0.90, **带外, 且较上锚(0.8237/0.8846)下滑**
- **费 2.6786 bps** — maker 恰 **2.0000** / taker 恰 **5.0000**, 285 笔 commission_asset **全 USDT**。混合费升高是 **taker 占比升到 23%** 所致(上锚 12%)
- **markout 回填 261/285 = 91.6%** ✓
- **尺寸梯度三桶**: small 0.6200 / mid 0.7813 / **large 0.5661** ⇒ **非负性不成立, 连续第二锚同一形状**
- **chase 单名连抽**: 23 个名字 2 次, **最大 2**, 无 3 次及以上 ✓

### ⑥ 异常处置 — **无需处置**; 本锚告警 7 条, 两条本锚新出现
1. ★**新**: `position reconcile: 5 个名字与场所的差异超出重估范围(符号翻转/单边/>5%) — 采用场所真值`
2. ★**新**: `撤名残差 −11,395.49 USDT = 目标 gross 的 −4.82%(>2% 门), 由 10 个撤下的名字造成`(含 BTCUSDT)。告警自陈"这一撤幅本身是个发现"
3. 重整后 3 个名字跨过 min_notional 门槛(ETCUSDT / IOSTUSDT / MANAUSDT), `floor_set_changed: true`, 只报告不迭代
4. 7 个持仓名被场所扣住(maxNotionalValue=0), reduce-only
5. **−2027** PIEVERSEUSDT +2,124U(上锚 +2,171U), 每锚重现直到目标回落; 候选修复需用户字
6. 32 个 maker 被 −5022 拒, 残差按全额进 taker 补单
7. 限流计数差值 731 权重/分(上锚 940), 归属未定, 不喂决策

### ⑦ 与上一锚(20Z)对比
| 指标 | 20Z | **00Z** | 向 |
|---|---|---|---|
| venue_reject(−5022) | 50 (49) | **56 (55)** | ↑ 恶化 |
| join 臂拒单率 | 0.2479 | **0.2148** | ↓ 改善 |
| behind 臂拒单率 | 0.1307 | **0.1825** | ↑ 恶化 |
| **maker 占比(名义)** | 0.8846 | **0.7738** | **↑ 恶化** |
| **费 bps** | 2.3463 | **2.6786** | **↑ 恶化** |
| taker 占比 | 12% | **23%** | ↑ |
| net_over_gross | −0.7169% | **−1.0192%** | ↑ 略越带 |
| behind 占比 | 0.5584 | **0.5037** | → 贴设计点 |
| 生产者 turnover | 3.215% | 2.404% | ↓ |
| markout 回填 | 92.5% | 91.6% | → |
| neutrality 同侧 taker bps | −7.7646 | **+17.3848** | ★ 大幅摆动 |

### 待验证 / 推断分栏
**已验证(本机第一手)**: ①②③④⑤ 全部读数; 分臂拒单率; 00Z 结算资金费分解; NAV 与损益分解; guard_twin AGREE; anchor done rc=0; 七条告警原文。
**待验证**: (a) **尺寸梯度非负性连续两锚不成立** —— 分桶仍为我方自建, 需与既有仪器对齐口径后再判, 但**连续两锚同形状已值得立项**; (b) **撤名残差 −4.82%** 是否为常态, 需回溯 20 锚基率(本锚未做); (c) `position reconcile 5 名超重估范围`是否首次, 需回溯; (d) 执行器换手 6.7% vs 生产者 2.404% 的 2.79× 口径差, 与上锚 2.77× 一致 —— r11 已登记为"书里最大的未归因口径差", 未闭合。
**推断**: maker 占比下滑与费升高**同源于 taker 占比 12%→23%**, 而 taker 占比上升由 −5022 拒单增加驱动(32 名残差全额进 taker); 但 −5022 增加的**外因**(场所点差/深度状态)本锚未测, 不下因果结论。

### 与研究线的交叉(只记, 不动)
本锚 maker 费**恰 2.0000** / taker **恰 5.0000** / 285 笔 commission_asset **全 USDT** ⇒ **BNB 折扣自 2026-09-07 断, 至本锚已第 6 天**, 账户仍在 VIP0 底档。r11 定价 ≈ +1.5% NAV/年。**属运维裁定域, 只报不动。**
