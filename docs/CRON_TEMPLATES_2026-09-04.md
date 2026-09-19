> **创建:** 2026-09-04 14:0xZ | **更新:** 2026-09-05 14:1xZ(/login 与 /model 切换再次清空会话 cron, 三项按本文逐字重建: 47686c87 / 538814c5 / 48a8bb77) | **状态:** 在用 | **用途:** 会话内定时任务是内存态, /model 切换或退出会清空(09-04 实测), 需要时按此逐字重建

> ⚠ **更正 CRON-09 · P3 · AUD-KB K4 2026-09-16**(原行字节保留, 不改写): **状态更正** —— 本文 §「每锚深查 prompt(逐字)」的模板文本自 09-05 起未变, 而在役 cron 已两次重建并**带更正附注**: job `41df7caa`(09-09 00:24Z 起, 会话级 7 天过期)→ `46dd536b` → **`a84f2bd4`**(2026-09-16, 同排程 `9 1,5,9,13,17,21`)。在役 cron = **本文模板逐字 + 「lead 更正附注」块**, 附注全文见本文末 §「深查模板更正附注」与 `docs/audit_pipeline_2026-09-13/AUDIT_KB.md` §5。其余三项: jpline 2h 重连 = **09-06 按用户字停止**(且 jpline 自 09-04 11:47Z 不可达); combo 84 锚二读 = **09-09 已完成**(判据① 不过), 下一窗归用户; 口径复核工作流 = **09-05 已收口**。


# 会话定时任务模板(重建时逐字复制 prompt)

| 任务 | cron(本地) | recurring |
|---|---|---|
| 每锚深查 | `9 1,5,9,13,17,21 * * *` | true |
| combo 84 锚前向门二读 | `57 12 9 9 *` | false |
| bandit eps0.50 稳定性复读 | 已于 09-04 13:3xZ 完成(安全线 PASS 57.5%; 价格分量 0.50 窗点估计 −2.63 bps, 3 日块 CI 含 0, 待积累) | — |
| jpline 每 2 小时重连 | `23 */2 * * *` | true(用户 09-05 令恢复; prompt 逐字见本文末) |

## 每锚深查 prompt(逐字)
每锚深查(锚收尾后固定触发, 全深度模板不缩水; 实盘书零接触, 只读排查): 当前锚 = 本地时刻整点减53分对应的 UTC 4h 锚(北京-8h)。按序 —— ① date -u + 三守护 PID 按内容验(shadow_loop_v3 run/sidecar_daemon.sh/combo_live_daemon.sh 进程在 + shadow.lock 与 fea171/combo_live_daemon.pid 句柄一致; E-0829-B 后 PID 会变, 以句柄文件为准)。② 信号六项: 生产者 shadow_log 行(fund_updates 稳态: 4h整点~353 / 8h结算整点00·08·16Z~453; forced_exit_n; sel/coverage; w3 三腿)+ combo_live_status(anchor 匹配+ok+读者验收)+ target_combo(w3_masked 掩码算术=w3[0]/(w3[0]+w3[2]); kc/fc 状态=own; f10 打分 400)+ 反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级)。③ 执行漏斗: orders.jsonl / fills.jsonl 按 **anchor_ts 归属**(不要按 rebalance_id, 日文件按 UTC 日切会漏)+ 终态分布, fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带), chase_arm_assigned 分臂计数, placement behind 占比≈0.50。④ 记账: venue_gross≈NAV×2.0, net/gross 带内(±1%), 实收 FUNDING_FEE(00/08/16Z 结算锚), phase_C anchors_row+readback+per_name_stop, `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE。⑤ 执行质量: 尺寸梯度三桶非负; markout 回填累计; chase 单名连抽标注。⑥ 异常处置: 回滚缺省=king形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(E-0904-A, 禁 nohup 裸 env); 整体回滚=kill combo_live_daemon.pid 内 PID。⑦ 全深度详表发用户(已验证/待验证/推断分栏); 同锚重复触发只报增量; 重大异常同时 PushNotification。

> ⚠ **更正 CRON-01(P0)/CRON-02/CRON-03/CRON-04/CRON-05/CRON-06/CRON-07/CRON-08/CRON-10/DEV-12 · AUD-KB K4 2026-09-16**(上面这段是**用户模板逐字**, 一字不改, 亦不得改): 其中十处基线 / 动词 / 读法已陈旧或指错文件, 逐条更正见本文末 §「深查模板更正附注(2026-09-16)」。**在役 cron `a84f2bd4` 执行的就是「本模板逐字 + 该附注」这个组合**; 重建 cron 时必须把附注一并带上, 否则 ⑥ 的回滚动词在 launchd KeepAlive 下**不构成回滚**(P0)。


## combo 84 锚前向门二读 prompt(逐字)
combo 84 锚前向门二读(CANDIDATE_wide_v2main_norev24_2026-08-26 §6 同判据, 判据冻结不改; 首读 09-02 的正裕量全在 E-0826-F 停机期未交易的前 4 锚, 故本次为首个有效读数): 取 08-26 04Z 起满 84 个配对锚的 combo vs 反事实 king 形态净额(实盘 target_live vs target_live_king, 逐锚 Σ|Δw| 与 sleeve 归因), 按 §6 冻结判据判 PASS/FAIL, 写 docs/RESULT_combo_forward_gate_84_2026-09-09.md 并 git -C 提交研究仓。口径纪律 E-0904-B: 逐年/逐段表, 负段显式, 单位链由脚本打印(每 gross → 年化 → 2×NAV)。同时复核 E-0904-F 口径结论是否已由第二仪器确认。实盘书零接触。

# 口径复核工作流(wf_80bb7b7c-ef0)续跑(额度用尽切模型后)
- 脚本: `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/caliber-final-review.js`(原件 `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/workflows/scripts/caliber-final-review-wf_80bb7b7c-ef0.js`)。
- 代理转录: `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/subagents/workflows/wf_80bb7b7c-ef0/agent-*.jsonl`(每个代理的最终返回在其 jsonl 末尾); 代理暂存产物: `~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/<label>/` 与 pod `/workspace/review_scratch/`。
- 同一会话内切模型后: `Workflow({scriptPath, resumeFromRunId: "wf_80bb7b7c-ef0"})` 续跑, 已返回的代理直接用缓存, 只重跑被额度中断的那几个。若换了会话(resumeFromRunId 失效): 读各 agent-*.jsonl 末尾的结构化返回, ≥15 个已返回则只起综合+缺口审查两代理, 不重跑 21 个。
- 设计: 6 路追溯(pod 面板/DL 与 king 目标/实盘链路/装置史/导出器与 bundle/真钱)+ 6 论断 × 2–3 证伪者(代码/实证/史料三镜)+ 综合 + 缺口审查 + 补证 + 终稿; 判据: 证伪票过半 ⇒ 论断不成立。


## jpline 每 2 小时重连 prompt(逐字, 用户 09-05 令)
jpline 每 2 小时重连(用户令 2026-09-05; 只读研究, 实盘零接触): `ssh -o ConnectTimeout=10 jpline 'echo up; cd /mnt/storage/private/work_hsy && cat probe_artifacts/callog_run.out; grep -v Warning probe_artifacts/callog_judge.out | cut -c1-700; ls jp_callog_m1_isolate.sh probe_artifacts/callog_m1iso_judge.out 2>/dev/null'`。① 不可达 ⇒ 只在 multi_asset/exports/live/pilot_journal/journal_2026-09-04_caliber_E0904F.md 追加一行"jpline 第 N 次超时 <UTC>", 不做其他事。② 可达 ⇒ (a) 读上述输出并与 pod 仪器(docs/RESULT_caliber_revalidation_2026-09-04.md, retrain_2026-09/review_caliber_wf/)逐年对账; (b) 立即在 jpline 后台起三臂(均 LOOK=900 WRULE=msharpe CAL=log, 装置 w10_universe.py 当前 jpline 副本, 用 jpline 自带的 hist king slow_pred_hist_oos.npy 与 pod_backup_2026-08-21 面板): `LEGS=111 PHI=0 OUT_TAG=w10_A3_hist_callog`(三腿, 对照 08-21 净额序列 nets_histv2_-30_2_42 与 pod 三腿 A), `LEGS=101 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero FSEED=42 OUT_TAG=w10_livefix_hist_callog_s42`(在役固定席位形态), 同上 FSEED=2027; 若 jp_callog_m1_isolate.sh 不存在则按 docs/CRON_TEMPLATES_2026-09-04.md 重建并起; (c) 出结果后写 docs/RESULT_caliber_revalidation_2026-09-04.md §"第二仪器(jpline, hist king)": 逐年表(2022–2026, 负年显式)、与 pod 与 08-21 序列的差、单位链由脚本打印, git -C 提交研究仓, 并向用户报告(E-0904-B 口径规则)。不改任何实盘文件。


---

## 深查模板更正附注(2026-09-16, AUD-KB K4)

> **用法**: 重建每锚深查 cron 时, prompt = 上面 §「每锚深查 prompt(逐字)」**原文一字不改** + 本节全文。这与在役 job `a84f2bd4` 同构。本节只更正事实、补盲态、记部署状态; **不改用户的任何判据**, 需要改判据的一律列在 ⑩ 作提案。受据逐条具名; 登记行见 `docs/audit_pipeline_2026-09-13/AUDIT_KB.md` §5(CRON-01..CRON-14, DEV-12)。

**结构 = 在役 cron a84f2bd4 同构: 用户模板逐字(`docs/CRON_TEMPLATES_2026-09-04.md` L13, 一字不改)+ 下面这一块「lead 更正附注」。附注只更正事实与补盲态, 不改用户的任何判据。**

—— lead 更正附注(2026-09-13 / 2026-09-16 受据; 深查只读, 实盘书零接触)——

**〇 盲态条(最高优先, 逐字取自 CFG-06 冻结版 AMENDMENT 1 与 CFG-04 AMENDMENT 1)**: 到 CFG-06 §3 读数产出前, 分臂**只报臂平衡**(各臂计数 / behind 占比 / 必要时逐臂**残差名义**作成本上界), **不报任何逐臂结果量**(拒单率 / 成交率 / markout / 成本 / 价差 / H 或 X 的任何形式)。用户模板 ③ 原文要求的「`chase_arm_assigned` 分臂计数, placement behind 占比≈0.50」**就是**臂平衡, 照做; **不得**在其上自行追加逐臂拆读。maker 份额、费 bps、−5022 首拒率**一律只报书级合计**。安全线 SL1/SL3 照评, 但只输出布尔与触发日, 不附逐臂数值。

**① 守护进程的权威是 launchd, 不是 PID 句柄**(同 ⑥ 的 08-30 KeepAlive 事实): 用 `launchctl print gui/$(id -u)/com.hsy.{shadowloop,combolive,sidecar}` 读 state / pid / runs / last exit code —— **runs 较上锚增长 = 被重启过**, 报; 句柄文件(shadow.lock、fea171/combo_live_daemon.pid)降为交叉核对。另核 `launchctl print-disabled gui/$(id -u)` 中 `com.hsy.sigma_ladder` 仍 disabled(OPS-01 退役, 6cc95943)、`com.hsy.execprobe2` 仍 disabled(OPS-02 退役, b63a0144)。

**② 反事实改写幅度的基线数字更正**: 模板写「09-03 08Z 起新台阶 19–20%」已陈旧 —— 该幅度随 king 席位滚动, **现水平 ≈25–27%**(09-13 16Z 实测 **27.90%**; 归因 = V2MAIN 链离开 king 书, AUDIT_PROD PROD-26 11/11 值)。**判据不变, 仍用用户原文**: level 再升一档, 或连续 3 锚增量 > +0.2pp 才升级。越界时把归因写清(席位 / FTRIM 名数 / rho_kc_fc 三者之一)。

**③ maker 份额与费用带的基线数字更正**: 模板写「maker ≥90% / 费 1.80–2.3 bps」已陈旧 —— **现水平 maker ≈74–78%, 费 ≈2.4–2.7 bps**(X-COST fdee4894 桶恒等分解 93.1253% → 73.9049%, −19.2204 pp; 驱动 = requote 实验 direct 臂 + chase 实验臂 + 存款后 chase_forced + from_reject)。**只报合计**(见〇)。换手稳态 2–5.5% 不变。⚠ 引用 X-COST 时按 FXR-DOC-2: 「执行成本侧没有隐藏缺陷」一句**已作废**, 11.3831 pp 依赖可交换性假设(不作该假设时 [−0.4178, +15.5642] pp), chase 4.3531 / forced 2.4401 pp 是**已成交桶份额**非反事实, 首拒 −5022 由 14.3% → 23.0% 的原因**未测**。

**④ guard_twin 判词读对文件**: 模板的「guard_twin AGREE」不在它读的那个文件里 —— 判词读 `~/guard_twin/state/latest.json` 的 `status` / `comparable` / `disagreements`, 明细读 `~/guard_twin/state/compare.jsonl`, 告警读 `~/guard_twin/state/alerts.log`; **只有 `comparable=true` 且 `disagreements` 为空才记 AGREE**。

**⑤ 实收资金费按名的当前结算间隔核**: 模板的「实收 FUNDING_FEE(00/08/16Z 结算锚)」会漏掉大多数结算 —— 书内多数名现为 4h / 1h 间隔, 每锚(或锚内)结算, 只有 8h 名落在 00/08/16Z。逐锚按名的当前 `fundingInfo` 间隔核, 并把间隔一并记录(P9: 间隔切换行会把 rn 放大 2–4×)。

**⑥ net/gross 必须点名是哪个量**: 模板的「net/gross 带内(±1%)」没说是哪一个。分两列报, **不得互换**: (i) **补单前 `book_net`** = 执行器 1.5% 中性带的判据量; (ii) **readback 后 net/gross** = 观察带 ±1%。

**⑦ 回滚动词(P0, 与 STATE §1 同, b63a0144 已更正)**: 回滚缺省 = king 形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(E-0904-A, 禁 nohup 裸 env); **整体回滚(临时)= `launchctl bootout gui/$(id -u)/com.hsy.combolive`** —— 08-30 起 combo 守护由 launchd KeepAlive 管理, **`kill $(cat …/combo_live_daemon.pid)` 会在 1 s 内被拉起, 不构成回滚**(同形哑任务演练收据 `docs/fixprogram_2026-09-13/receipts/OPS_rollback_verb_drill2_20260913T144746Z.log`; 第 1 次 3 s 演练读「未重生」是错的, 收据保留标错)。持久回滚(跨重登)再加 `launchctl disable gui/$(id -u)/com.hsy.combolive`; 恢复 = `launchctl enable …` + `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`; 执行后核 `launchctl print gui/$(id -u)/com.hsy.combolive` 与下一锚 target_live 的 producer 字段。

**⑧ 已知实盘假阳性(见到即按仪器处理, 不得触发全书级动作)**: E9 `NO_PRODUCER` 产物断言误报 · EXE-03 / PROD-25 reshape 去均值把小空头翻多(109 个 combo 锚中 99 个)后「撤名残差」告警归错因 · E-0912-A reduce-only 截量 × 身份核对 1e-6 假阳性 · E-0909-G 账本缺口触发的逐名门。**用户规则**: 仪器疑问不得触发全书级响应(`feedback_no_book_level_response_to_instrument_doubt`); 在役看门狗**任何触发仍整书平仓**(EXE-01, 比例响应在克隆未部署)。

**⑨ 部署状态(每次深查都要说)**: 本修复纲领**没有任何修复已部署**, 执行器运行树仍 `ef60f85`; 深查**只读**, 不动任何实盘文件、不改配置、不发信号给在役 PID。核 `git -C ~/dl_quant_live rev-parse --short HEAD` 并报, 与 origin/main 不一致时**照报不动作**。

**⑩ 未获批准的增查提案(不在本 cron 内执行; 随复审包上交用户后才可加)**: (a) 反事实改写幅度改用近 42 锚 p5–p95 动态带、升级步长 +0.2pp→+0.5pp、带外连续 3 锚才升级(FXR-KB-1 判为新监控政策); (b) 补查 per_name_stop 的「已停名当锚 readback 是否归零」(W9 缺陷 08-20..09-12 未被看见); (c) 补查本 rid `orders.jsonl` 行数 > 0(E-0909-G); (d) 补查 `request_ledger` 四类不一致与 capacity_conflict / reduce-only 截量 UNKNOWN 事件数(E-0912-A 前兆); (e) 补查 `apiTradingStatus` 与 −4400 / −2027 计数(E-0910-A / E-0909-E); (f) 当日 `daily_nav.external_flow ≠ 0` 时标注日损守卫盲区; (g) 读 `~/regime_dash/REGIME_DASH.md` 的席位 / FTRIM 名单 / 旗标。**(b)–(f) 各自对应一个当前无人守的在役盲区, 建议优先批。**

---

## 抛物线起始前向日志 更正附注(2026-09-16, AUD-KB K4)

> 同上: 用户文本逐字 + 本节。登记行 CRON-11(提交须显式 pathspec)/ CRON-12(前向值取自 ±0.30 硬裁 float16 缓存)。

**结构 = 在役 cron 同构: 用户文本逐字 + 下面这一块「lead 更正附注」。**

—— lead 更正附注(aud-kb CRON-11 / CRON-12; 只读研究, 实盘零接触, 不调 API)——

**① 提交必须带显式 pathspec(CRON-11)**: 用户文本的「然后 git add/commit(无新增则不提交)」在一个多代理并发暂存的仓库里会把别人的暂存改动扫进一次 `parabolic_onset_forward` 提交。改为: 仅在有新增时 `git -C /Users/haosiyu/Desktop/quant_research add -- multi_asset/exports/live/parabolic_onset_forward/events.jsonl multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl`, 然后 `git -C … commit -m "parabolic_onset_forward: 每日追加 <UTC 日期>" -- <同两个路径>`; 提交后 `git -C … show --name-only --format= HEAD` 核**只含这两个文件**, 否则报告不修; git 锁被占用则本日不提交并报告。**不得裸 `commit`, 不得静默 git stderr。**

**② 前向值的口径标注(CRON-12 / DEV-08)**: 本日志的 onset 与前向收益取自生产者 5m 缓存 `ret5` 通道(**float16, 硬裁 ±0.300048828125**, E-0908-B 同族), 一切读数标「**裁剪缓存口径, 尾部为下界**」。若本批新增事件的 onset 或前向窗内出现 |ret5| 顶到界的饱和格, 报其事件数(装置未输出则报「未测」)。**规则(r18)**: 任何装置不得从缓存 `ret5` 重算收益; 记账正典是未裁剪的 `meta_newprod_v4` y4 = Π(1+r)−1。

**③ 复判门的措辞更正(CRON-12)**: 用户文本的「当 P 层 θ8 已填事件 ≥ 200 且距 2026-09-06 ≥ 14 天时, 向用户报『可复判』」改为报: 「**计数已达复判门, 但前向值取自裁剪 ±0.30 的 float16 缓存口径**; 复判前须先按记账口径(未裁剪原始收盘价)重算 onset 与前向收益, 或预注册该口径偏差的处理」。复判仍按 `PREREG_crash_continuation_parabolic_stratum_2026-09-06` §2 六条另起。

**④ 盲态不变**: 累计读数**只报计数**(θ8 P 层已填前向事件数 / 距 200 门), **不看均值、不比 P 与 Q、不做 CI、不判**(门未到按设计保持盲态; r11_verdict §「唯一还活着、但门没开的 alpha 线索」)。运行失败(rc≠0 或断言)**只报不修**。

---

## 深查模板更正附注 · 2026-09-19 修订(取代上面 2026-09-16 附注的 ⑨ 与 ⑩; 其余各条原样继续适用)

> **用法**: 重建每锚深查 cron 时, prompt = §「每锚深查 prompt(逐字)」原文一字不改 + §「深查模板更正附注(2026-09-16)」〇–⑧ 全文 + 本节全文。2026-09-19 本会话按此重建(旧 job 随会话更替丢失, CronList 为空)。依据: 裁定 #8(`RULINGS_best_recommendation_2026-09-19.md`, 用户字「待我裁定的按最佳建议来调整」)与第五轮复审 §6-8。

**⓪ 第一条命令(先于 ①)**: `python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py <anchor_ts>`(只读)。它已内置成交按 (symbol, trade_id) 坍缩(LED-01)、分臂计数每名一行、**告警段**; 现写脚本只补它没覆盖的项, 补之前先查它是否已算过。其告警段必须原样摘入报告(条数 + HIGH 条数), 不得报「无告警」而不看它。

**⑨′ 部署状态(每次深查都要说; 取代 ⑨)**: 执行器运行树 = **`409ea16`**(2026-09-18 02:46Z, NOSLEEP R7-K1); 生产者 combo_stage = `3520d363`(自 09-17 16Z)。第五轮复审后在执行器克隆里做的改动(重建锚全部追单 —— **部署推迟到 CFG-04 与 CFG-06 两个实验都到停止点之后**; 看门狗划转盲区)**均未部署**。核 `git -C ~/dl_quant_live rev-parse --short HEAD` 并报, 与 409ea16 或 origin/main 不一致时**照报不动作**。深查只读, 发现问题只报不修。

**⑩′ 增查(裁定 #8 已采纳, 全部只读, 本 cron 执行; (a) 仍只是提案不执行)**:
- (b) per_name_stop: 本锚已停名在锚后 readback 是否归零; 未归零的名单与名义。
- (c) 本锚 rid 在 `orders.jsonl` 的行数 > 0(E-0909-G); 为 0 且非停机锚 ⇒ 报。
- (d) `request_ledger` 四类不一致计数与 capacity_conflict / reduce-only 截量 UNKNOWN 事件数(E-0912-A 前兆); 找不到文件 ⇒ 报「未测」并写明找过的路径, 不得报 0。
- (e) `apiTradingStatus` 与 −4400 / −2027 计数 —— **只从执行器自己已写的日志读; 深查不得调用任何交易所 API**(只读密钥规则: 不得用带交易权限的生产密钥, GET 也不行); 日志里没有 ⇒ 「未测」。
- (f) 当日 `daily_nav` 的 external_flow ≠ 0 时, 标注「日损守卫盲区(划转当日)」。
- (g) 读 `~/regime_dash/regime_dash.jsonl`(追加式, 按 `anchor_utc` 取本锚行)的席位 w3_masked / FTRIM 名单 / 旗标; `REGIME_DASH.md` 每锚整份重写, 只作展示, 不作收据(DEV-14)。
- 整书平仓后的停机锚(open_orders_halted)单列: 本锚是否整锚被拦、距上次平仓多少小时。
- 新增读数一律沿用 ⓪ 的成交去重与完整人口; 不得把新增面板当主链修复(复审 §6-8)。

**盲态补充(AMENDMENT 2, 2026-09-19)**: lead 在两实验停止点之前**不计算任何逐臂结果量**; 深查报告里出现的分臂量只能是臂平衡(计数 / behind 占比 / 残差名义上界)。
