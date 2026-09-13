> **创建:** 2026-09-13 15:3xZ | **更新:** v3.2 2026-09-13 17:0xZ(P2 回放装置认证闭合; 实盘写回类操作一律随复审包) | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME · https://claude.ai/code/session_01HLaR7r1Tyg5CoEsNgnNFkY | **状态:** 活文档; 修复纲领进行中, **本纲领代码修复一律未部署** | **作废条件:** 由最终合并复审包取代(FIXPROGRAM §5)

# 修复纲领 · 全面交接(给独立研究员接续与复审)

用户字(2026-09-13 16:1xZ):「用量又快到了, 先全面记录当前结论, 进度, 思考发现, 文档, 完整代码工作提交链, 我转交独立研究员」。本文件 + 下列提交 / 捆绑包即接续起点。**唯一现状源仍是 `STATE.md`**; 规程 / 登记 / 裁定全文 = `FIXPROGRAM_2026-09-13.md` §0–§8。

---
## 0 怎么接手(按顺序)
1. 读 `STATE.md` 顶部 3 条 → `FIXPROGRAM_2026-09-13.md` §0(规程)§3(main/secondary 定义与 71 项归属)§4–§8(逐批裁定)。
2. 读本文件 §2(结论与思考)与 §4(逐项状态)。
3. 代码: 四个克隆分支的提交链见 `receipts/HANDOFF_clone_heads_20260913T162850Z.txt`(最新; 16:09Z 版保留); **可离线复原**: `receipts/bundles/*.bundle`(执行器三包以 ef60f85 为前置, 在 `~/dl_quant_live` 或任一含 ef60f85 的克隆里 `git fetch <bundle> <branch>`; 生产者包为全量分支, 可 `git clone`)。
4. 研究仓本纲领提交全表: `receipts/HANDOFF_research_commits_since_20260913T1245Z.txt`(16:28Z 刷新, 154 条)。
5. 各工作者报告: `REPORT_E1.md` · `REPORT_FX_EXEC.md` · `REPORT_FX_EXEC2.md` · `REPORT_FX_W6C.md` · `REPORT_FX_PROD.md` · `REPORT_FX_EVAL.md` · `REPORT_FX_TRAIN.md`; 暂停者状态: `FX_{TRAIN,DATA,MODEL,EXEC2}/STATE_PAUSE.md` · `X_COST/STATE_PAUSE.md`。审计: `docs/audit_pipeline_2026-09-13/AUDIT_{EXEC,TRAIN,DATA,PROD}.md` + `AUDIT_KB_PARTIAL.md`。

---
## 1 实盘现状(只读核)
- 执行器运行树 `~/dl_quant_live` = **ef60f85**(= origin/main; 09-13 12:04Z 部署 W6ab+W2+W1+W9); 12Z 锚 rc=0; 16Z 锚进行中(深查 cron 约 17:09Z)。三守护 combolive 30944 / sidecar 30943 / shadowloop 10900。
- **lead 已直接应用、待复审**(均为已裁定撤回任务的持久关闭, 不触在役三守护): OPS-01 σ_fund 阶梯 launchd disable + plist 退役(6cc95943)· OPS-02 已 KILL 执行探针 bootout + disable + plist 退役(b63a0144)· E1 09-12 平仓批 fills 只追加回填(66de5b73)。
- **回滚动词更正**(STATE §1, b63a0144): `kill $(cat combo_live_daemon.pid)` 在 launchd KeepAlive 下**不是回滚**; 临时回滚 `launchctl bootout gui/$(id -u)/com.hsy.combolive`, 恢复 `bootstrap`(哑任务两次正控, 第 1 次结论错误留档)。深查模板 ⑥ 仍旧动词(K5 未做)。
- 在役已知风险(已登记未修): **EXE-01 任何看门狗触发仍整书平仓**(修复在克隆, 未部署)· **W6C-B13 全书读回缺失不判盲**(按陈旧状态判)· **W6C-I6 非计划运行平意图暴露**(未测)· **PROD-27 combo 重写最坏余量 9 s, 生产者迟到静默跳过**· **P9 资金费间隔切换行 rn 放大 2–4×**(修复在克隆)· P1/P2 第 80 列训练 v0 / 服务 v1(修复在克隆)。

---
## 2 结论与思考发现(本纲领产出; 未经独立复审)
**2.1 为什么「回测 3.0+、实盘很差」—— 目前有证据的部分(均为测量, 书层 P&L 影响多数未测)**
1. **回测高水平本身未被扣除选择与窗口**(T6, 前轮): 候选家族 N_eff ≈1.57; 在役 A0 冻结窗 2.94 的 P(真 SR>3) 按 N_eff 约 0.30; v4 全周期 Sharpe 1.29 [0.32, 2.28], 2023 −1.94, 复利 maxDD −42%(aud-kb 记忆扫描引用)。旧「2.7–3.0」「2.42」类数字多出自 CAL=simple 伪凸性口径(已作废)。
2. **研究回放 ≠ 生产路径**: king 研究特征 vs 服务特征分数 Spearman 中位 **0.935**(最小 0.760; AUDIT_PROD PROD-03), 来源 = 时钟错位(训练窗止于 E−1, 服务含 E; 0.984)+ 秩宇宙 829 vs 450(0.947)+ 第 80 列单位(0.994)+ f16(无影响)。V2MAIN 训练行 vs 服务 0.982(几乎全是成员宇宙)。**⇒ 所有「回放书」读数都带着一个未计量的模型输入差。**
3. **DL 训练资金费输入是前视名单**(AUDIT_DATA FEA-01): 2022–26 训练成员中 34/34/34/25/14% 的资金费特征为 0(只 2026-08 在役 450 名有值), 「有无特征」本身携带 +0.5..+3.2 bps/4h 前向收益差 ⇒ 在役 F10 与全部 F10 OOF 受影响; 模型 / 书效应未测。
4. **研究层可交易性按收盘价而非成交判定**(AUDIT_DATA TRD-01): 156 个已停交易合约写 1,377 万冻结行(收益恰 0), 60 个死后仍有资金费记录; 研究资金费腿秩基 0.7–5.3% 是死合约; 生产按 exchangeInfo TRADING 排除它们 ⇒ 研究与生产人口不同。L4b 的 carry 袖「存活」正是被这个吞掉(可执行标价后无臂存活)。
5. **生产路径回放装置在 41 锚窗已认证(17:0xZ 更新)**: king 链 41/41 与快照 3/3 逐位过, G2-C-BIND 过(lead 核验); 连续 combo 历史链残差(原 0/41 @1e-6)**已闭合 = 我方回放装置缺陷**: 生产 combo 段每锚在截至 A 的完整 11,520 行缓存上重跑 171 特征管线, Phase 1 链喂的是 09-12 08Z 缓存截到 A(早锚少 1,920 行)⇒ 只改 DL 腿(f10/fc)早段样本统计, 经 EMA 与 2.5e-4 带冻结沿链传递。新门 **G2-C-ASOF PASS: 41/41 锚 target_live / target_combo 恰 0.0**, king ≤9.3e-10, kc/fc 状态逐位(P2 prereg efda139f + AMENDMENT 1–3, 收据 9–14, 修正链装置 p2_attr_chain_asof.py c333b0e5; 原 G-P2 FAIL 标签逐字保留)。H-d 部分确认(缓存窗口长度; 非 btcv 回填本身)、H-a 窗内无可测效应、H-b 排除、H-c 死合约在生产窗不触 F10 横截面。**认证范围 = 41 锚 pod2 混合缓存**; S2 六臂的 171 管线从未运行(F10 为注入 OOF)⇒ 本缺陷不及 S2, 但 S2 作为历史书仍带 D1/D2(OOF ≠ 在役预测)· PROD-03(研究 king 特征 0.935)· D20 · D21(死合约)⇒ **S2「未认证 / 仅信息」标签维持**。12 个双种子对照无一 CI95 排零。
6. **九月实盘亏损的归因不能说成「策略自身」**: K2 等价带重标后 T5c/T5d = 「共同亏损, 差异不可判」(回放同锚也亏, 但 −4.15..+1.71 bps/锚 的部署 / 模型差排除不了)。
7. **结论措辞系统性过强**(K2): 347 行判词重标提案, 撤回 126(「NOT MATERIAL」「不可区分」「策略自身亏损」「不能预测」多由显著性门或点估计发出, 无经济等价带)。§0 第 8 条已采纳: 无差类判词只由冻结 δ 等价带发出(书层 0.05 bps/锚/gross)。
8. **执行成本侧没有隐藏缺陷**(X-COST): maker 占比 93.1% → 73.9% 精确分解 = requote 实验 direct 臂 ≈+11.4 pp + chase 实验臂 +4.4 + 存款后 chase_forced +2.4 + from_reject +1.0; 费侧约 5 USDT/日。首次 −5022 拒单率 14.3% → 23.0% 原因未测。
9. **实盘两次整书平仓(09-09 / 09-12)都是自家仪器假阳性**; 在役看门狗任何触发都整书平仓(EXE-01)。实盘 10 次整书平仓中 5 次为具名作用域事件。
10. **执行器 reshape 让书与生产者目标不一致**: 12Z 撤名残差 91% 是生产者自身净空 −8.46%; 再去均值在 109 个 combo 锚中 99 个翻转小空头(PROD-25 = EXE-03); 回测用同函数 ⇒ 回测已含此行为。

**2.2 思考(lead 判断, 供复审碰撞)**
- 「信号/方案欠缺」与「仪器 / 口径错误」目前纠缠在一起: 在训练/服务差(2)、前视输入(3)、死合约人口(4)、回放未认证(5)修完并重测之前, 任何「策略本身 Sharpe 多少」的数字都不可信, 包括正面与负面结论 —— 这是用户裁定「main 先于 secondary」的依据。
- 修完后的第一件研究事 = 在认证后的生产路径回放上, 用修正后的模型输入重跑 A0 形态, 得到**可信基线**; 然后 L2(挤空方向)/ T7(韩元溢价)/ L3(上下币事件)才有可比对象。
- 看门狗比例响应与 B13 应先于任何策略改动上线: 两次整书平仓的损失与停机都来自仪器, 不来自信号。

---
## 3 用户裁定索引
1. 20:5x SGT: 所有已知问题不等裁定、最严谨修复、每项提交链 + 报告 + 独立复审, 第一优先。
2. 14:13:19Z: main(全部修复, 含 P2 回放认证)完成后才开 secondary; secondary 以 L2 为首。
3. 15:0xZ: 复审 = main 完成后一次性合并包(覆盖实盘 / 全部管线 / 数据采集 / 评估 / 模型训练 / 未来研究 / 口径)。
4. 15:2xZ / 16:1xZ: 用量将尽时汇总进度与提交链, 交独立研究员接续。

---
## 4 逐项状态(✅ 已交付待复审 · 🔧 进行中 · ⏸ 暂停 · ⬜ 未开始)
### 4.1 实盘执行器(克隆, 未部署)
| 分支 / 负责 | 提交(旧→新) | 内容 | 报告 |
|---|---|---|---|
| `cc_tmp/fx_exec` `fix/known-issues-2026-09-13` / FX-EXEC 🔧 | 6294534 E2 · c28c0a7+82fcc16 E3 · 3a641c3 E4 · a21797d E9 | E2 GET 补查容量冲突合同 · E3 损坏事件日志具名 NOT OBSERVABLE · E4 已停名不进追单(裁定 (a) 保留 from_reject MARKET 转换)· E9 产物断言误报 | `REPORT_FX_EXEC.md`; 收据 3600d99e / 81e24fdd; diff `docs/receipts/fx_exec_E{2,3,4,9}.diff` |
| 同上, 队列 ⬜ | — | E10 公证器(FX-EXEC2 已发前缀一致提案)· ALM-03 · OPS-01b σ 阶梯读者 · E5 · E6(止损文案 / EXE-03 告警归因)· E7 · NEW-02 attempt_idx · gate_coverage 重复 · 全电池 | |
| `cc_tmp/fx_w6c` `fix/exe01-proportional-response` / FX-W6C 🔧 | f0d4eac · f99dc80 · b3c5fc2 EXE-01 · 933e7c5 ALM-02 · 3f85c0e M2-33 | EXE-01 比例响应(≤5 名且已知疑额 ≤2% target_gross 且无书级触发 ⇒ 只平具名名; 09-12 回放 LOCAL 2 名 0.65%; 09-09 仍全阶梯; 电池 b3c5fc2 135/136 仅 env_loading)· ALM-02 cond2 判日文本与触发数字 · M2-33 cond2 判最新有权益日, 未定价则 BLIND 不回退陈旧日 | `REPORT_FX_W6C.md`(EXE-01); ALM-02/M2-33 见 `FX_W6C/FACT_TABLE_ALM02.md`、`FACT_TABLE_FLOWDAY_M2-33.md`; diff `docs/receipts/fx_w6c.diff`(ef60f85..b3c5fc2 sha d4a6d103; 至 3f85c0e 待重生成) |
| 同上, 队列 ⬜ | — | **W6C-B13 全书读回缺失判盲**(先)· **W6C-I6 非计划运行暴露**(先测)· 平仓行 anchor_ts/submit_ts(NEW-01 / F-I5)· 3f85c0e 全电池(17:05Z 后, BATTERY.lock) | |
| `cc_tmp/fx_exec2` `fix/ledger-alarms-2026-09-13` / FX-EXEC2 🔧 | c46fb83 LED-02 · 7ca52ac LED-07 · 469c3f3 LED-08 · 8354c5a STA-02 · c2e9bdc ALM-01 · ec88424/d3d16ea/0d27a52 LED-01 · e05c45a LED-04 | 平仓按腿 mid_at_submit 计成本 · 干净逐锚序列 · 逐锚报告不折零 · 冷却到期改日报 · funding_span 告警 · fills 写入合同((symbol,trade_id) 键 + 隔离守卫 + 唯一读者; 冻结指标 44 日恒等 sha 4d00f6c7)· daily_nav 修前行按 guard_twin 收入账本修订记录读 | `REPORT_FX_EXEC2.md`(LED-04 段未到); 部分 diff 见 `FX_EXEC2/receipts/` |
| 同上, 队列 ⬜ | — | **LED-08 须补冻结参照窗漂移检查**(lead 退回)· LED-03/05(需凭据的回填由 lead 执行)· ALM-05 · ALM-06(guard_twin 非 git, 拷贝部署)· STA-03 · OPS-03(先设计)· CFG-02/07 · DOC-01 · 全电池 | |

### 4.2 生产者 / 模型服务(快照分支, 未部署; 部署 = 换装事件)
| 分支 / 负责 | 提交 | 内容 |
|---|---|---|
| `cc_tmp/fx_prod` `fix/train-serve-parity-2026-09-13`(基 b891748 = 在役快照)/ FX-PROD 🔧 | e4a1e84 / 1a2c1c1 / 633d44b P1 · e0e34ea P9 证据 · 4b996aa / 031707c / d7df9a5 P6′ · 41f3deb / 15921c0 P2 · c2cdfa7 / d620f6e 平价回放驱动与判官 · 69e8e22 P6-M/P9-M 离线精确修正 · 86a52e3 八月 zip 拉取装置 · 26b8dd8 / 76b4aed / 85e02ce P9 规则评估 v2–v4 · 3e4d78f / b90f1b8 P9 挂账路径精确重解 + v1 EMA 精确修正(混合 (a))+ 首行默认 · 38223d8 P1 迁移(v0 EMA 状态离线构建)· d49f1ef / 61a55bc / dfd3b0b 月 zip 对账 (c) | 报告 `REPORT_FX_PROD.md`; P9 真值表 `work/p9/…csv.gz` sha b797c85f(含八月 zip 新版 18Z 后) |
| 队列 ⬜ | — | **PROD-27 combo 静默跳过**(P6-M 后)· P5 席位播种 · 平价回放判官 (a)(b)(c) 读数 · 换装计划 |

**第 80 列口径裁定**(§6): 在役 = 服务改用训练定义 v0(P1/P2), 属缺陷修复不需重训; 重训 v0 / v1 属配方, FX-MODEL 预注册配对, 未判前十月保持 v0 一致。

### 4.3 生产路径回放认证(P2, 属 main)
- S1 七门(G2-B 原门 RED 保留)· G2-C-BIND ✅ lead 核验(ecd45655, `receipts/s2/G2C_BIND.json` c0aca587)· S2 六链已跑, 出表判词因 K2 作废待重出(书层数字不受影响)。
- ✅ 连续 combo 链残差归因**闭合**(17:0xZ): 装置缺陷(回放缓存窗口), **G2-C-ASOF PASS 41/41 恰 0.0**; Stage B 3eb958c1 · Stage C d4c4625b(去前 1,920 行复现 1.127e-4, 去 48/288 行 0.0)· Stage D 10b30695(恒等运行逐位复现 G2-C 链收据 41/41; 11,520 行窗 41/41 恰 0.0)· 最新 5f66eb83。
- ⬜ 第 3 项 G2-B 复判计划 AMENDMENT 9(7c0b1d0d, 未运行): R0 原门逐字复现收据 2 · R1 离线施 P6-M 于历史快照(预期仍 RED: 66 个冷启动名单独 1.15e-7)· R2 部署后实盘窗(约 09-26 05Z 前不可能合法转绿, 届时转绿是衰减非修复)。· AMENDMENT 10 把 D21 死合约加入 S2 偏差表(未重跑 S2)。
- **新发现交 FX-PROD**: 生产者 `state_H_f10` 文件在每锚 kc/fc 写出后约 2 分钟被再写, 09-12 08Z 与 combo 段自身计算差 2.63e-8(96 名)⇒ 疑似第二个进程重写; 在门外, 下一锚从生产者副本起步仍精确。
- ⬜ K2 采纳 AMENDMENT + 红测 → S2 重出表 · G2-B 在 P6-M 部署后复判计划 · D20 在生产路径上的诚实量(成员集已内嵌前视条件, P2 探针 f89f2fee)。

### 4.4 评估口径(K2, 研究仓)✅
adeda8e7 · efc2412a · f0cfe770 · d0b087db · 99a6cd27; `REPORT_FX_EVAL.md`; lead 复跑全部一致(legacy 红集 = 声明 19 格 · module 84/84 · AST · 变异 17/17 · 重标 347 行)。重标为提案, 待复审后由 K4 应用。

### 4.5 数据层 ⏸(FX-DATA, `FX_DATA/STATE_PAUSE.md`)
73b59ec0 TRD-01 SPEC 冻结(可交易 ⇔ (A−24h, A] 内 ≥1 成交 bar)· 8ab0d769 `common/tradability.py` + 构建器 · 30c635e6 / a0436bb0 / 468a6c1c 暂停与协调。构建器第 1 跑 rc=1(写出器把标量写成长度 1 数组, 自身重载检查抓到; 产物作废, 修复已提交未重跑); 交叉检验已过(与 T7 1h 成交计数 7,638,831 小时零分歧)。余: TRD-02/04 · FND-01/02/03(等 P9 八月新表)· HOL-01 面板重建(沙箱)· LIN-01 r6 构建器入 git · RET-02 · UNI-03 · EVL-01(33 个文件 CAL 缺省 simple)。

### 4.6 模型输入 ⏸(FX-MODEL, `FX_MODEL/STATE_PAUSE.md`)
74cb2e66 / a1c16b73 / 6b09524b / ff5e001e / ea44af7c / 126b369c。已确认 FEA-01 · TIM-01(5,838 锚 Spearman 中位 0.9865)· UNI-01(2026 非加密成员 7.26%)· P11 训练宇宙 829 vs 服务 450。TRN-06 预注册归 FX-MODEL。余: 事实表文档 → 旧构建器红测 → 新构建器(遗留设置逐位复现)→ 预注册 → 配对重训(GPU)。

### 4.7 十月重训链 ⏸(FX-TRAIN, `FX_TRAIN/STATE_PAUSE.md`; 期限 ≈10-01)
1e6d6122 事实表 · d591d65e **TRN-19 修复**(406/406)· 31305140 暂停。TRN-02 RAW 补丁覆盖门: pod2 真数据已过(九月 952/953 格, 余 1 格为 f16 舍入到界的真收益), 红格(09-10 缓存用九月补丁 ⇒ rc 3 点名 AKE/BULLA/WOO), 代码在 docs 下未入链目录。**待裁定**: 九月合同数据段需在九月运行目录写覆盖清单 —— lead 裁定先证无目录级哈希再写(§7.2)。余 TRN-01/03/14/15/16/17/18/20–27 · PROD-21 · AUG_IV.get 三处。

### 4.8 执行成本与实验 ✅(X-COST, `X_COST/`)
3eea1906 · 55aa2d3b · bcb3c0d5 · fdee4894 RESULT · 977962a4 CFG-04 / CFG-06 草案(未冻结)· 977eb46e 暂停。

### 4.9 知识库 ⏸(aud-kb)
`AUDIT_KB_PARTIAL.md` 248 行(721d1d44 / 0e88892f)+ M4 另 31 行在草稿区(`/Users/haosiyu/cc_tmp/claude-501/…/scratchpad/aud_kb/rows_M4.jsonl`)未并入。lead 已应用: STATE §1 回滚动词; 记忆 review_b0a573a1(运行树 / revert 作废)、k_window_180_live(在役 900 s)、chase_closed_at_39(09-01 起 50/50)。两个会话 cron(深查 41df7caa / 抛物线日志 4a2f33e3)约 09-16 00:24Z 过期, 替换提示词草稿在 PARTIAL 内。

### 4.10 运维 / 基建
OPS-01 · OPS-02 · 回滚动词双演练 · Mac 盘满清理 23 个陈旧克隆(`receipts/INFRA_disk_cleanup_20260913T143228Z.log`)· exec_w6 删除(`receipts/INFRA_delete_exec_w6_*.log`)· **pod2 配额 15:51Z 用尽**, 16:07Z 删 `uplift_2026-09-11/r2_sleeve/feat/*.npy` 11.4 GB(`receipts/INFRA_pod2_quota_relief_20260913T160702Z.log`)。L2 metrics 拉取与 P9 八月 zip 拉取在配额事件中停止(P9 已恢复缺失部分)。
**执行器电池规则**: tests_entrypoint_wiring 做无凭据公开行情 GET ⇒ 允许, 仅 N+65min..N+3h15m 启动、共用 `/Users/haosiyu/cc_tmp/BATTERY.lock`、断言无 .env 与 DRY_RUN、记请求权重、事后还原 state。

---
## 5 待用户裁定
1. **CFG-04**: 重建锚上是否继续随机追单((a) 全追 / (b) 维持 / (c) 仅复场锚全追)。
2. **CFG-06**: 无定论默认(回退 0.35 / 维持 0.50)· 窗 28 或 14 天 · 「停 behind」= eps 0 或 0.10; 另 lead 须核「09-05 后无人计算过分臂 placement 结果」声明(T3 / r17 / 锚日志可能读过)。
3. **转账日口径**(M2-33): 转账日为 day-loss 定价(事实表测了两种候选口径)还是维持 BLIND。
4. **EXE-01 范围**宽于 R-14 文字(按触发器作用域)—— 复审确认。
5. 是否把 EXE-01 + B13 + E4 + OPS-01/02 作为小包提前复审部署, 或随全部修复一次复审。
6. **账本公证器落点**(E10): 修后公证器在 launchd 下对桌面 iCloud 研究仓 git 被 TCC 拒绝且研究仓不在配置分支 ⇒ 部署后每日 HIGH 页报, 直到 (a) 公证仓移出桌面(独立小仓 + 远端, lead 倾向)/ (b) 解决 TCC 并让研究仓处于 multi-asset-v2 / (c) 改配置; 另 08-31..09-12 的 13 份 GENESIS 断链清单是否按原样提交(唯一时间戳将是提交日期)。

## 6 lead 自身错误与更正
- R2′ 原文「from_reject 以原限价 IOC 转换」不实(实为无价 MARKET reduce-only), 原句保留标假(§4.2)。
- 「全书不可读回会走全阶梯」不实(W6C-B13), 已登记为 P1 缺陷。
- 回滚动词第 1 次演练 3 s 读「未重生」结论错误(launchd 节流), 收据保留标错。
- 一次 .git 驱逐文件物化读取过慢被中止; 一次研究仓提交撞 ref 锁 rc 128 后重试成功。

## 7 在跑与接续要点(16:1xZ)
- 在跑工作者: FX-EXEC · FX-EXEC2 · FX-W6C · FX-PROD · P2(均已要求立即提交全部并报在飞状态)。暂停: FX-TRAIN · FX-DATA · FX-MODEL · aud-exec(X-COST 完成)· aud-kb。
- secondary 挂起: L2(重启核对清单 fb180666)· T7(S1 装置 1aec37c0 未运行)· T5d-R · L3 · L4 家族 3 · T6 §11 · T1 carry 更正。
- 估时(工作者小时, 约 5 并发): 执行器余项 6–10 h · 看门狗 B13/I6 3–5 h · 生产者 8–12 h · P2 残差 2–8 h · 账本告警余项 6–8 h · 知识库 3 h · 数据层 1–2 天 · 十月链 2–3 天 · 模型输入(含 GPU)2–3 天 · 书行为 P7/P8 1–2 天(P2 认证后)。**main 全部约 4–6 天。**

---
## 8 v3.1 增量(16:1xZ → 16:3xZ)
**分支头**(`receipts/HANDOFF_clone_heads_20260913T162850Z.txt`; 捆绑包已按新头重建): fx_exec **39a0055** · fx_exec2 **e808697** · fx_w6c **3f85c0e** · fx_prod **f289fc0**(`docs/receipts/fx_prod_stack.diff` = b891748..f289fc0, 17 文件 +2608/−0, sha 17a16f6e)。
- **FX-PROD 交接完成**(报告 `REPORT_FX_PROD.md` 全部段落, 研究仓 3a5cce44): P1 迁移干跑 PASS(525 名 0 冲突)· 平价 (a) 开关关 = 实盘逐位(链 41/41、快照 3/3)· (b) 只 king 第 76 列与 V2MAIN F82 第 80 列变 · (c) king Spearman 中位 0.9950、combo L1 中位 0.011 · V0P 门 PASS · P6′ 种子加载器(v3 bundle 在 ONG 08-25 08Z 拒绝)· P2 9/9 · P6-M 离线精确修正(正控 6.9e-18)· P9 H2 混合规则最终误标 1047→100、EMA >1% 格 73,484→8,205(31/31, 旧电池 65)· P5 装置已提交未运行 · 换装计划草稿 `FX_PROD/SWAP_PLAN_FX_PROD.md`(未干跑; 下一步 `migrations/swap_dryrun_frozen_20260913.sh` 于锚窗外, 约 30 min, 必须沙箱)· 八月 zip 832/832 完成于配额事件前, 680 文件 Mac 复核无需重拉 · PROD-27 未开始。
- **FX-EXEC2 新增**: ALM-05 63e116c(A7 保证金诊断改按外部书范围)· ALM-06 guard_twin 包 24b6e083(**lead 退回**: CUM 须保留独立收入账本输入告警)· LED-01 跟进 df57077(重冻结 pilot_metrics ⇒ 研究仓 vendored 副本须在部署同窗替换; lead 裁定照此)· STA-03 / CFG-02 / CFG-07 / DOC-01 文档项 · LED-04 e05c45a + 修订记录 250 条 + 应用装置 da1a9389(演练未跑)· OPS-03 设计 9add9bd5(**lead 裁定 A + C**: 滑动窗口权重限速同上限 + 更正 `_gross_mult_note` 的「速率风暴」错误归因; 不做分阶段重建)。
- **FX-W6C 新增**: ALM-02 933e7c5 · M2-33 3f85c0e(cond2 判最新有权益日, 未定价则 BLIND)· 队列: B13 → I6 → cond4 修前转账日定价(LED-04 裁定 (a))→ 平仓行时间戳 · 3f85c0e 电池未跑(17:05Z 后, BATTERY.lock)。
- **FX-EXEC 新增**: E10 公证器 6523440 · ALM-03 方案 A 裁定(新账本消费者 + 旧路径 RETIRED 保留断言逐字)· 头 39a0055(报告段待到)。
- **新登记 W6C-C4**(FIXPROGRAM §9): 看门狗 cond4 在修前转账日读低记 realised ⇒ §4-4 回撤低估 0.26 pp(−1.3136% vs −1.5749%)。
- **新增待用户裁定**: 无(转账日口径仍为 §5 第 3 项)。
- **FX-PROD 头更新 afd94a2**(捆绑包已重建): 换装干跑驱动加时间守卫(锚时 HH:15–HH:50 与 HH+1:05 之前拒跑)与 `~/wide_shadow/shadow_bundle*` 只读前后 mtime/size 核对(打印 LIVE_RO unchanged/CHANGED); 读码沙箱审计: 写全在 `work/swapdry`, 对 `~/wide_shadow` 只读, 无场所调用(ReplayFetcher 拒绝录制外请求), 无 launchctl, 不向在役 PID 发信号。**干跑未运行**; 接手者于 17:05Z 后、锚窗外在克隆内执行 `/bin/bash migrations/swap_dryrun_frozen_20260913.sh`, 日志 `work/swapdry/run_dry.log`, 结束后提交收据。
- **16:52Z lead 中止 FX-W6C 电池 `final2_3f85c0e`**(16:51:10Z 启动, 违反电池窗口 / 锁规则与「交接期不跑电池」指令, 且 16Z 实盘锚尚未 anchor done): 只杀电池驱动、run_acceptance 与其 python 子进程; 收据 `receipts/INFRA_stop_battery_in_anchor_window_20260913T165202Z.log`(第 1 次 kill 因 zsh 不分词未生效且进程树匹配到 lead 自身 shell, 已记入收据; 第 2 次按显式 PID 数组成功)。**fx_w6c 3f85c0e 的全电池仍未跑**, 接手者在 17:05–19:15Z 或 21:05–23:15Z 取锁运行。
- **17:0xZ 增量**: P2 链残差闭合(见 §2.1 第 5 条、§4.3)· FX-EXEC2 LED-03(八个旧平仓批费用: 离线代理 22.76 USDT + 0.14 BNB, 498/498 正控; 精确回填装置需凭据, 待复审后运行; **BNB 换算口径裁定 = BNBUSDT 现货 1m 收盘 `bnb_spot_1m_close_at_fill`**)· LED-04(250 条修订记录, 演练 PASS)· LED-05(09-09 12Z 崩溃锚 52 行重建订单, 两树演练 PASS, 看门狗条件变化均为愈合方向)—— **三项实盘写回本会话均未执行, 随复审包由接手者先 --rehearse 于实盘根再 --apply, 锚窗外**; 命令逐字在 `REPORT_FX_EXEC2.md`。16Z 实盘锚 anchor done rc=0(16:58:30Z)。
