> **创建:** 2026-09-12 10:1xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 用户字「按照最正确的逻辑全部做，修复所有漏洞」的执行计划; 每项先事实表再动手; 实盘树只经 safe_commit 由 lead 亲手落地; 研究员逐项复核 | **作废条件:** 任一项落地后以其收据为准更新本表

# 修复所有漏洞 — 计划、事实表、门

## §0 原则
1. 实盘零接触: 所有工程在克隆/研究目录做; 落地 = `ops/safe_commit.sh`(电池全绿)由 lead 在非锚小时、避 HH:20–35 亲手执行; 生产者(`~/wide_shadow`)任何改动 = 换装事件, 需用户字。
2. 每项: 事实表 → 判据冻结 → 实现 → 正控 + 负控(红能力) → 收据 → 研究员复核。声明必须带收据; 不用"逐位"形容 < 1e-6 的一致。
3. 裁定项(性质而非动作)单独列给用户: R6-MARK 动作合同、Q6 恢复政策的落码优先级、杠杆、XIB 影子臂、BNB 抵扣(运维)。

## §1 项目表
| # | 漏洞(来源) | 事实 | 修法 | 门 / 负控 | 落地路径 | 负责 |
|---|---|---|---|---|---|---|
| G1 | #55 IC 告警对象/阈值/恢复/新鲜度(研究员 §4) | `ops/ic_monitor.py` 255 行: 测持仓排序 vs 下锚价格排序; 阈值标定 α .05/band .002 vs 在役 .1/.00025; OK 不发恢复通知; 缺失观测拉窗无新鲜度门; 09-12 01:30Z 已 OK(+.00472/−.01104) | 正文命名对象("持仓排序 IC, 非模型 IC 非净收益"); 标定身份写进每条消息与 state; DECIDE/ALERT→OK 发一次"RECOVERED(≠alpha 恢复)"; 新鲜度门(窗内应有 vs 实有观测数; 不足 ⇒ 标 INCOMPLETE 只报不判); 阈值重标留待平价装置 Phase 2 | `tests_ic_monitor.py` 扩: 文案/恢复转移/新鲜度/标定身份 各一条 + 突变红; 克隆电池 132 全绿 | safe_commit(lead) | W1 |
| G2 | 下游读者未继承三桶: `daily_summary.account_facts` 非 USDT 混加、None→0; `first_anchor_review` / `score_post_fix`(POSTMORTEM §4d) | AST 反例: −.30 USDT + −.01 BNB 汇成 −.31; realised_pnl=None ⇒ realised_today=0, observable=True | 只加 USDT, 非 USDT 单列未换算; None ⇒ observable=False; 三桶键读者化 | `tests_daily_summary.py` 扩 + 突变红; 电池 | safe_commit(lead) | W2 |
| G3 | 十月链不可执行(研究员 R1–R5) | 训练器/merge 月白名单硬编码 ≤202608; 导出器 generation 写死; 链根硬编码; legs env 未写 | (a) 月集合 env/数据导出; (b) generation 从 env + 记训练末锚; (c) 本月配置文件 `v4_month.env` 驱动链根 + `chain_v4_monthly_dryrun.sh` | 正控: 九月配置复现九月门收据; 负控: 空本月目录第一道门 rc≠0; tests_pipeline_gates 扩 | 研究仓提交 + 研究员复核; pod2 CPU 只跑门, 不训练 | W3 |
| G4 | judge 输入底 11 名(扩底 diff 未应用) | v2 门 require 强制 28; judge 自己只查 11 | 应用 `v4_gate_common.PROPOSED.diff` + 扩 tests_pipeline_gates 夹具到 28 输入 | 自检全绿; pod2: 真 A1 v2 收据 ⇒ judge 认合格(A1 (C) 不晋级) + 缺一输入 ⇒ 不合格 | 研究仓提交 + 复核 | W4 |
| G5 | 生产者平价 combo 段历史窗残差(≤2.5e-4, DL 腿) | king 段 41/41 ≤1e-9; combo 最新 3 锚 0.0; 早锚 ρ(f10) 差 ≤3e-4; EMA/缓存复用假说已排除 | 12Z 用 08Z/12Z 两份 rolling.npz 快照直接量"事后回填"格数; 若成立 ⇒ 前向门用快照起步 | G-P2 前向: 快照起步锚 L∞ ≤1e-6 | 本仓 | lead |
| G6 | 平价装置 Phase 2(折外历史水平) | 在役模型训练到 08-31 ⇒ 直接回放样本内 | 折外预测按**月度重训节奏**生成; king 梯度截止 = 训练末锚; 装置 = 生产代码路径 | PREREG 另立 | 本仓 | lead |
| G7 | Q6 跨锚未解释量继承(PREREG 修订 4 未落码) | 数学已接受; 0→100→100 反例可达 | 落码 + 41 日回放验收(PREREG §3) | PREREG 判据 | safe_commit + 15 轮式复审 | 待用户裁定优先级 |
| G8 | R6-MARK 不可定价量动作合同 | 记录 unknown, 无动作 | 合同选项: 停开新仓 / 缩仓 / 只记录 | 裁定 | — | 用户 |
| G9 | factor_health UNKNOWN(影子监控报告 ssh 不可读) | **诊断(11:4xZ, 只读)**: `ops/check_factor_health.py` L343 自述——jpline 影子监控 cron 于 2026-08-06 经用户裁定退役(服务器只训练+采集), 上游**不存在**, UNKNOWN 是预期态而非故障; 且它监控的对象本就是 3 腿 `A_provisional_3leg` 曲线(无 funding 腿, 非在役书)。⇒ 这是一台指向已退役上游、且口径错误的仪器, 每锚发 INFO | **W5**(W1 落地后): 把消费者改指本地源 = #55 的 `state/live/ic_monitor_evals.jsonl`(实盘书实现 rank-IC), 或明确退役该消费者; 不再 ssh | 首锚 factor_health 读到本地源且 `frontier_judged=True`; 旧码在新套件下红 | 执行器读者(safe_commit) | lead |
| G10 | BNB 手续费抵扣断(09-07 起, ≈+1.5% NAV/年) | 全 USDT 费, VIP0 | 运维: 充 BNB/开抵扣 | 首锚 commission_asset 出现 BNB | 用户 | 用户 |
| G11 | 生产者 paper 计分器给退役书计分 | `combo_stage` 不写 aux.json | 改生产者 = 换装事件 | 用户字 | — | 待裁定 |

## §2 顺序
G5(12Z 测量)→ G1/G2 落地(下一非锚窗)→ G3/G4 复核后提交 → G6 PREREG → 裁定项(G7/G8/G10/G11)。

## §3 状态(2026-09-12 11:2xZ)
| # | 状态 | 收据 |
|---|---|---|
| G1 | **W1 交付**: 合同/恢复/新鲜度门/只读门 + 52 检查 + 突变红; 克隆电池 131/132(红 = 无 .env); 待 13:36Z 窗 safe_commit 落地 | `docs/DESIGN_ic_monitor_contract_2026-09-12.md`, `docs/receipts/w1_*` |
| G2 | **W2 交付**: daily_summary / first_anchor_review / score_post_fix 三桶 + 非 USDT 单列 + None≠0; 新纯模块 cost_buckets(规则逐字抄 anchor_loop 并逐键钉住); 53+31 检查; 旧码红; 克隆电池 132/133; 待 13:00Z 窗 safe_commit 落地 | `docs/DESIGN_readers_three_bucket_2026-09-12.md`, `docs/receipts/w2_*` |
| G3 | **W3 交付并入库 15941da7**: 驱动 + 41 键合同 + 空根负控; pod2 正控/负控收据; 仍开 = STEP1/STEP2 门九月专用(用户裁定) | `docs/DESIGN_v4_monthly_chain_2026-09-12.md`, `v4_chain…/receipts/monthly_chain_2026-09-12/` |
| G4 | **W4 入库 15941da7** + 第七轮 F9(判官自绑合同, 旧码红); 链自检 228 ALL PASS(lead 复跑) | `docs/DESIGN_judge_floor_28_2026-09-12.md`, `v4_chain…/receipts/judge_floor_2026-09-12/` |
| G5 | king 段 PASS 41/41; combo 段按字面 FAIL(机理待 12Z 快照回填测量) | `parity_replay_2026-09-12/RESULT_parity_phase1_2026-09-12.md` |
| G6 | PREREG 已立; G2-A 通道平价 PASS | `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md` |
| G7–G11 | 待裁定 | `docs/RULINGS_requested_2026-09-12.md` |
新增待裁定(W1 发现): #55 同级 24h 冷却与 01:30Z 抖动(86,398.51 s 压掉了 09-11 的 DECIDE 重发)—— 一处常量 COOLDOWN_S, 建议 23h; 新鲜度门 MAX_MISSING={r24:2, r48:4} 使 09-07..09-12 五次判级全部 INCOMPLETE(事实: 窗被平仓掏空), 是否维持该门待裁定。
新增(11:4xZ): F9 已落(15941da7); R-9/R-10/R-11 入 RULINGS。
新增(13:0xZ): G5 机理 —— 08Z→12Z 缓存回填探针 0/0/0(11,472 行×829 名), 4h 尺度回填假说不成立; 12Z 快照种子平价 king/combo L∞ 0.0 精确(前向 1/3); 机理裁定按 PREREG AMENDMENT 3 序列(3 对快照 + 3 次快照种子平价)。G2(W2)safe_commit 12:59:19Z 启动(电池中)。

## §4 事故改序(2026-09-12 13:2xZ, E-0912-A)
- G1/G2(W1/W2)落地**暂停**: 事故期间不落任何执行器改动; W2 safe_commit 12:59Z 启动、13:04Z 停止并复原(运行树 918559f 逐字节)。两者与 W6 同批复审、同批落地。
- **W6**(新, 最高优先): E-0912-A 修复 (a) clamped 态 (b) 全退出按持仓张数 [(c) 比例响应 = R-14 裁定]; 克隆 exec_w6; 设计 `docs/DESIGN_reduce_only_clamp_identity_2026-09-12.md`。
- **W7**(新, 用户 13:1xZ「重训卡的那项可以推动解决吗」): STEP1/STEP2 月度通用门源码 + PREREG + pod2 九月正控(字段全等), 合同批准 = 用户字。
- 恢复交易 = R-13(用户字)。

