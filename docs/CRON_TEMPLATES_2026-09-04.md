> **创建:** 2026-09-04 14:0xZ | **更新:** 2026-09-05 14:1xZ(/login 与 /model 切换再次清空会话 cron, 三项按本文逐字重建: 47686c87 / 538814c5 / 48a8bb77) | **状态:** 在用 | **用途:** 会话内定时任务是内存态, /model 切换或退出会清空(09-04 实测), 需要时按此逐字重建

# 会话定时任务模板(重建时逐字复制 prompt)

| 任务 | cron(本地) | recurring |
|---|---|---|
| 每锚深查 | `9 1,5,9,13,17,21 * * *` | true |
| combo 84 锚前向门二读 | `57 12 9 9 *` | false |
| bandit eps0.50 稳定性复读 | 已于 09-04 13:3xZ 完成(安全线 PASS 57.5%; 价格分量 0.50 窗点估计 −2.63 bps, 3 日块 CI 含 0, 待积累) | — |
| jpline 每 2 小时重连 | `23 */2 * * *` | true(用户 09-05 令恢复; prompt 逐字见本文末) |

## 每锚深查 prompt(逐字)
每锚深查(锚收尾后固定触发, 全深度模板不缩水; 实盘书零接触, 只读排查): 当前锚 = 本地时刻整点减53分对应的 UTC 4h 锚(北京-8h)。按序 —— ① date -u + 三守护 PID 按内容验(shadow_loop_v3 run/sidecar_daemon.sh/combo_live_daemon.sh 进程在 + shadow.lock 与 fea171/combo_live_daemon.pid 句柄一致; E-0829-B 后 PID 会变, 以句柄文件为准)。② 信号六项: 生产者 shadow_log 行(fund_updates 稳态: 4h整点~353 / 8h结算整点00·08·16Z~453; forced_exit_n; sel/coverage; w3 三腿)+ combo_live_status(anchor 匹配+ok+读者验收)+ target_combo(w3_masked 掩码算术=w3[0]/(w3[0]+w3[2]); kc/fc 状态=own; f10 打分 400)+ 反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级)。③ 执行漏斗: orders.jsonl / fills.jsonl 按 **anchor_ts 归属**(不要按 rebalance_id, 日文件按 UTC 日切会漏)+ 终态分布, fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带), chase_arm_assigned 分臂计数, placement behind 占比≈0.50。④ 记账: venue_gross≈NAV×2.0, net/gross 带内(±1%), 实收 FUNDING_FEE(00/08/16Z 结算锚), phase_C anchors_row+readback+per_name_stop, `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE。⑤ 执行质量: 尺寸梯度三桶非负; markout 回填累计; chase 单名连抽标注。⑥ 异常处置: 回滚缺省=king形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(E-0904-A, 禁 nohup 裸 env); 整体回滚=kill combo_live_daemon.pid 内 PID。⑦ 全深度详表发用户(已验证/待验证/推断分栏); 同锚重复触发只报增量; 重大异常同时 PushNotification。

## combo 84 锚前向门二读 prompt(逐字)
combo 84 锚前向门二读(CANDIDATE_wide_v2main_norev24_2026-08-26 §6 同判据, 判据冻结不改; 首读 09-02 的正裕量全在 E-0826-F 停机期未交易的前 4 锚, 故本次为首个有效读数): 取 08-26 04Z 起满 84 个配对锚的 combo vs 反事实 king 形态净额(实盘 target_live vs target_live_king, 逐锚 Σ|Δw| 与 sleeve 归因), 按 §6 冻结判据判 PASS/FAIL, 写 docs/RESULT_combo_forward_gate_84_2026-09-09.md 并 git -C 提交研究仓。口径纪律 E-0904-B: 逐年/逐段表, 负段显式, 单位链由脚本打印(每 gross → 年化 → 2×NAV)。同时复核 E-0904-F 口径结论是否已由第二仪器确认。实盘书零接触。

# 口径复核工作流(wf_80bb7b7c-ef0)续跑(额度用尽切模型后)
- 脚本: `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/caliber-final-review.js`(原件 `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/workflows/scripts/caliber-final-review-wf_80bb7b7c-ef0.js`)。
- 代理转录: `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/subagents/workflows/wf_80bb7b7c-ef0/agent-*.jsonl`(每个代理的最终返回在其 jsonl 末尾); 代理暂存产物: `~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/<label>/` 与 pod `/workspace/review_scratch/`。
- 同一会话内切模型后: `Workflow({scriptPath, resumeFromRunId: "wf_80bb7b7c-ef0"})` 续跑, 已返回的代理直接用缓存, 只重跑被额度中断的那几个。若换了会话(resumeFromRunId 失效): 读各 agent-*.jsonl 末尾的结构化返回, ≥15 个已返回则只起综合+缺口审查两代理, 不重跑 21 个。
- 设计: 6 路追溯(pod 面板/DL 与 king 目标/实盘链路/装置史/导出器与 bundle/真钱)+ 6 论断 × 2–3 证伪者(代码/实证/史料三镜)+ 综合 + 缺口审查 + 补证 + 终稿; 判据: 证伪票过半 ⇒ 论断不成立。


## jpline 每 2 小时重连 prompt(逐字, 用户 09-05 令)
jpline 每 2 小时重连(用户令 2026-09-05; 只读研究, 实盘零接触): `ssh -o ConnectTimeout=10 jpline 'echo up; cd /mnt/storage/private/work_hsy && cat probe_artifacts/callog_run.out; grep -v Warning probe_artifacts/callog_judge.out | cut -c1-700; ls jp_callog_m1_isolate.sh probe_artifacts/callog_m1iso_judge.out 2>/dev/null'`。① 不可达 ⇒ 只在 multi_asset/exports/live/pilot_journal/journal_2026-09-04_caliber_E0904F.md 追加一行"jpline 第 N 次超时 <UTC>", 不做其他事。② 可达 ⇒ (a) 读上述输出并与 pod 仪器(docs/RESULT_caliber_revalidation_2026-09-04.md, retrain_2026-09/review_caliber_wf/)逐年对账; (b) 立即在 jpline 后台起三臂(均 LOOK=900 WRULE=msharpe CAL=log, 装置 w10_universe.py 当前 jpline 副本, 用 jpline 自带的 hist king slow_pred_hist_oos.npy 与 pod_backup_2026-08-21 面板): `LEGS=111 PHI=0 OUT_TAG=w10_A3_hist_callog`(三腿, 对照 08-21 净额序列 nets_histv2_-30_2_42 与 pod 三腿 A), `LEGS=101 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero FSEED=42 OUT_TAG=w10_livefix_hist_callog_s42`(在役固定席位形态), 同上 FSEED=2027; 若 jp_callog_m1_isolate.sh 不存在则按 docs/CRON_TEMPLATES_2026-09-04.md 重建并起; (c) 出结果后写 docs/RESULT_caliber_revalidation_2026-09-04.md §"第二仪器(jpline, hist king)": 逐年表(2022–2026, 负年显式)、与 pod 与 08-21 序列的差、单位链由脚本打印, git -C 提交研究仓, 并向用户报告(E-0904-B 口径规则)。不改任何实盘文件。
