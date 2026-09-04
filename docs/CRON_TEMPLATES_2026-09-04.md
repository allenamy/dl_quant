> **创建:** 2026-09-04 14:0xZ | **状态:** 会话中断恢复用 | **用途:** 会话内定时任务是内存态(会话退出/模型切换即清空), 新会话按此逐字重建

# 会话定时任务模板(重建时逐字复制 prompt)

| 任务 | cron(本地) | recurring |
|---|---|---|
| 每锚深查 | `9 1,5,9,13,17,21 * * *` | true |
| combo 84 锚前向门二读 | `57 12 9 9 *` | false |
| bandit eps0.50 稳定性复读 | 已于 09-04 13:3xZ 完成(安全线 PASS 57.5%; 价格分量 0.50 窗点估计 −2.63 bps, 3 日块 CI 含 0, 待积累) | — |
| jpline 重连 | 用户 09-04 令"不要等 jpline", 不再排 | — |

## 每锚深查 prompt(逐字)
每锚深查(锚收尾后固定触发, 全深度模板不缩水; 实盘书零接触, 只读排查): 当前锚 = 本地时刻整点减53分对应的 UTC 4h 锚(北京-8h)。按序 —— ① date -u + 三守护 PID 按内容验(shadow_loop_v3 run/sidecar_daemon.sh/combo_live_daemon.sh 进程在 + shadow.lock 与 fea171/combo_live_daemon.pid 句柄一致; E-0829-B 后 PID 会变, 以句柄文件为准)。② 信号六项: 生产者 shadow_log 行(fund_updates 稳态: 4h整点~353 / 8h结算整点00·08·16Z~453; forced_exit_n; sel/coverage; w3 三腿)+ combo_live_status(anchor 匹配+ok+读者验收)+ target_combo(w3_masked 掩码算术=w3[0]/(w3[0]+w3[2]); kc/fc 状态=own; f10 打分 400)+ 反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级)。③ 执行漏斗: orders.jsonl / fills.jsonl 按 **anchor_ts 归属**(不要按 rebalance_id, 日文件按 UTC 日切会漏)+ 终态分布, fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带), chase_arm_assigned 分臂计数, placement behind 占比≈0.50。④ 记账: venue_gross≈NAV×2.0, net/gross 带内(±1%), 实收 FUNDING_FEE(00/08/16Z 结算锚), phase_C anchors_row+readback+per_name_stop, `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE。⑤ 执行质量: 尺寸梯度三桶非负; markout 回填累计; chase 单名连抽标注。⑥ 异常处置: 回滚缺省=king形态; 生产者重启动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(E-0904-A, 禁 nohup 裸 env); 整体回滚=kill combo_live_daemon.pid 内 PID。⑦ 全深度详表发用户(已验证/待验证/推断分栏); 同锚重复触发只报增量; 重大异常同时 PushNotification。

## combo 84 锚前向门二读 prompt(逐字)
combo 84 锚前向门二读(CANDIDATE_wide_v2main_norev24_2026-08-26 §6 同判据, 判据冻结不改; 首读 09-02 的正裕量全在 E-0826-F 停机期未交易的前 4 锚, 故本次为首个有效读数): 取 08-26 04Z 起满 84 个配对锚的 combo vs 反事实 king 形态净额(实盘 target_live vs target_live_king, 逐锚 Σ|Δw| 与 sleeve 归因), 按 §6 冻结判据判 PASS/FAIL, 写 docs/RESULT_combo_forward_gate_84_2026-09-09.md 并 git -C 提交研究仓。口径纪律 E-0904-B: 逐年/逐段表, 负段显式, 单位链由脚本打印(每 gross → 年化 → 2×NAV)。同时复核 E-0904-F 口径结论是否已由第二仪器确认。实盘书零接触。

# 口径复核工作流(wf_80bb7b7c-ef0)中断恢复
- 脚本: `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/caliber-final-review.js`(原件 `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/workflows/scripts/caliber-final-review-wf_80bb7b7c-ef0.js`)。
- 代理转录: `~/.claude/projects/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/subagents/workflows/wf_80bb7b7c-ef0/agent-*.jsonl`(每个代理的最终返回在其 jsonl 末尾); 代理暂存产物: `~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/<label>/` 与 pod `/workspace/review_scratch/`。
- **resumeFromRunId 只在同一会话有效**。新会话恢复法: 先读各 agent-*.jsonl 末尾的结构化返回(tracer: caliber/evidence; refuter: refuted/evidence), 若 ≥ 15 个已返回则直接手工做"综合→缺口审查"两步(可只起 2 个代理), 不要重跑全部 21 个; 若返回不足, 用脚本重跑缺的那几路(改 TRACERS/CLAIMS 列表)。
- 设计: 6 路追溯(pod 面板/DL 与 king 目标/实盘链路/装置史/导出器与 bundle/真钱)+ 6 论断 × 2–3 证伪者(代码/实证/史料三镜)+ 综合 + 缺口审查 + 补证 + 终稿; 判据: 证伪票过半 ⇒ 论断不成立。
