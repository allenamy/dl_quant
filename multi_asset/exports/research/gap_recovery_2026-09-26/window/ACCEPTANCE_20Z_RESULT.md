> **创建:** 2026-09-26 21:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 20Z 恢复首锚的验收结果,按 `ACCEPTANCE_20Z_recovery.md`(6b238f24d,写于读数之前)逐条判 | **作废条件:** 不作废

# 20Z(1790452800)恢复首锚验收 — 结论:恢复正常;1 项对账缺口已具名并派修

| # | 判据 | 结果 | 依据 |
|---|---|---|---|
| 1 | 生产者 | **PASS**:signal OK,coverage 1.0,members 400,missing 0,无 anchor_error;按预期没有 08Z score 行;LR 未追加(文件 sha 仍为安装件 5a1ed5a0,k=0) | shadow_log;`first_anchor_1790452800_20Z_k0.txt` |
| 2 | combo | **PASS**:kc/fc 状态源都是 own,blend h_source=own,gross 0.8079,COMBO_LIVE rc=0,读者验收 ok。**预期偏差**:self_parity_maxdw 6.5e-3(weights/16Z 故意不写,已事先具名) | combo_live.log;target_combo/blend |
| 3 | 执行器 | **PASS**:20:24:49Z 首次尝试读到外部书 ok,TRADE,`anchor done rc=0`(20:56:45Z);inspect rc 0;VERSION_PROBE OK n=0;M3_SELFCHECK OK n=0;PARITY n_differing 0;B4_POOLED OK;watchdog 未触发;realized gross 213.7k 对目标 215.7k;venue net 0.14% | `nc_2026-09-23/receipts/anchor_accept_2026-09-25/ACCEPT_20Z_1790452800_recovery.txt` |
| 4a | daily_nav | **PASS**:有 20Z 行(nav 108,059.6);12Z/16Z 无行(预期) | daily_nav.jsonl |
| 4b | 资金费账本 | **具名缺口(不红)**:12Z 以前的结算都已写入;缺口期间 **545 笔结算没有可用的持仓回读,无法定价,因此未写行**(HIGH,按降噪规则只记录不推送)。NAV 本身来自交易所,不受影响;缺的是归因账本 M6 的行。**修复已派**:缺口期间没有任何成交,持仓不变,可用 08Z 回读的数量加 20Z 交易前回读证明不变,补写这些行。设备先在研究仓完成,由 lead 在静默窗安装;执行器侧的类修复另排进下一个包 | notify_audit 20:46Z |
| 4c | 持仓对账 | **与常态一致**:reconcile 采纳交易所真值的名 24 个(09-21..26 每锚 3–27 个,另有两次 88/109);12h 的价格位移并不异常 | notify_audit 历史 |
| 5 | 席位重播种 | **按冻结预期**:file UNDECIDED(k=0);w3_raw PASS(max 差 9.24e-6);w3_masked 逐位 PASS;目标层 CONSISTENT(Σ|dw| 0.0362,期望上限 0.0891)。00Z 为 k=1 首锚,届时三条全判 | `reseed_2026-09-26/receipts/first_anchor_1790452800_20Z_k0.txt` |
| 6 | comboparity | **PASS**:PARITY n_differing 0(快照含桥接的 16Z 状态) | parity.log |
| — | anchor_report | warn:fund_updates 1154(常态约 353)。这是 12h 缺口里累积的结算,属于预期 | anchor_report |
| — | 前向日志新鲜度 | RED:仓库里的 parabolic_onset_forward 长队列日志最后一行在 09-25 06:19Z,早于迁移。按 882a86576,它应迁到 ~/pof_long,但至今没有运行者。短队列(~/parabolic_onset_forward_short)FRESH。与实盘交易无关,已派 dlarch 查 | ACCEPT 文件末段 |
