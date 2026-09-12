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
| G9 | factor_health UNKNOWN(影子监控报告 ssh 不可读) | 研究基建可达性, INFO | 修可达或改为本地报告源 | 首锚 report 可读 | 研究基建 | lead |
| G10 | BNB 手续费抵扣断(09-07 起, ≈+1.5% NAV/年) | 全 USDT 费, VIP0 | 运维: 充 BNB/开抵扣 | 首锚 commission_asset 出现 BNB | 用户 | 用户 |
| G11 | 生产者 paper 计分器给退役书计分 | `combo_stage` 不写 aux.json | 改生产者 = 换装事件 | 用户字 | — | 待裁定 |

## §2 顺序
G5(12Z 测量)→ G1/G2 落地(下一非锚窗)→ G3/G4 复核后提交 → G6 PREREG → 裁定项(G7/G8/G10/G11)。
