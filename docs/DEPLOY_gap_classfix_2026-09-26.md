> **创建:** 2026-09-26 18:1xZ(rev 2 19:2xZ: GAP4) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** 发布手册,交 lead 审;目标窗 **09-27 05:00–07:40Z**,备用窗 09:00–11:40Z(都在 12Z 之前) | **作废条件:** §0 任一 sha 变动(生产 combo_stage 不再是 12a76de8,或包、执行器 HEAD 变化),或 lead / 用户裁定

# 发布手册:缺锚类修复(gap class fix,tree GAP4)—— 生产者 files-only 发布 + 执行器侧发布归档

- 验收线(lead):**下一次任意长度的缺锚,不需要人即可被处理。**
- 判据:`multi_asset/exports/research/gap_classfix_2026-09-26/ACCEPTANCE_gap_classfix_2026-09-26.md`。冻结于 11bc3b4be;修订 1(2a7567019)、修订 2(483713a15)、修订 3(ffa978f27)都写在读数之前。
- **这是书行为改动**:只在出现缺锚、状态损坏,或(一份有效状态都没有的)冷启动时,才改变发布的书。无缺锚时输出与现码字节相同(C0)。按 CLAUDE.md 约束 5,需要用户裁定。

## 设计原则(lead 裁定 2026-09-26,含一处更正)
1. **承接最近一份有效状态**:不再恰好取 A−14400。来源具名为 `own` / `own_gap<m>` / `_rejected<n>` / `_beyond_bound`。
2. **越界(> 6 锚)**:照样承接、照样发布,另发 HIGH 页报。
   - **更正**:lead 早先写的是「越界 HOLD」。改为发布,依据是实测论证:执行器缺目标时一直持旧书(on_unavailable=hold),旧状态就是它手里拿着的书;HOLD 只会让旧书无限期变旧。
3. **冷启动的书绝不发布**。
   - 冷启动的定义:kc 或 fc 找不到任何有效状态,并且回落向量的 gross 低于 0.4。
   - 冷启动时,本锚不写任何 kc/fc 状态,COMBO_LIVE 中止并发 HIGH 页报,由人恢复状态。
   - 理由:执行器不保留生产者的 gross,会把冷启动书放大到满杠杆。旧码下,冷启动还会写出 ~0.1× 的状态,后续约 5 锚把它当作 own 承接,最终发布一本从零爬升的书。这已经发生过一次:08-30 04Z 以 gross 0.515 发布。
4. **退化状态不作前驱**:gross 低于 0.4(`MIN_STATE_GROSS`)的状态文件按「degenerate」具名拒绝。在留存的状态里,除 08-30 那段爬升外,kc/f10 的 gross 都 ≥ 0.78。
5. **成员历史缺锚**:在 combo 里用生产者成员规则现算,不改任何状态文件。

## 0. 组件与门(窗前实测)
| 组件 | 对象 | 状态(收据) |
|---|---|---|
| 生产者树 | tree GAP4:combo_stage **5eaabcdb**(基于 12a76de8,逐处唯一替换)+ prev_state **5150aeae** + members_rule **be691560** + tests_prev_state **eee8dcdc** | receipts/TREE_GAP4_PATCH_RECEIPT.json |
| 生产者包 | `package_GAP4/INSTALL_CONTRACT.json`,sha **27a0c493**:4 个文件,0 个归档移动,钉住 14 个不变文件 | `gap_package_files.py` |
| 真实 home 预检 | `nc_install_files.py preflight package_GAP4` → **PREFLIGHT_PASS** | receipts/PREFLIGHT_GAP4_real_home_*.txt |
| 安装演练 | TEST_GAP_INSTALL_FILES **13/13**(GAP4) | receipts/TEST_GAP_INSTALL_FILES_GAP4.log |
| 单元测试 U | **16/16**;旧谓词在 13/13 个有分辨力的用例上 RED | receipts/U_tests_prev_state_GAP4_stdout.txt |
| 沙箱重放 | run 3 **GAP_FIX_JUDGE PASS 25/25**:C0×3 字节同一、T×3、G1/G2/G6、gap7、X1–X3、cold、poison、M | receipts/GAPFIX_JUDGE_run3.json(99fd8f1c6) |
| 成员规则 | V1 **13/13** 快照逐元素复现;V2 事后重算平均 Jaccard 0.9987(carry-forward 0.9914) | receipts/MEMBERS_V1V2.json |
| 发布边界测试 P | 旧版在生产上本身就红(E-0926-H,测试漂移)。已修成 **v2**(fix-pkg-e 第 2 项):env 补 DIO/io,测试环境里的名字由 AST 从被测块推出,late_status 按 C 发布的合同;v2 在生产 12a76de8 与 GAP4 上都是 **7/7 OK**,并已作为 **W0 第 4 道门**跑在包的 combo_stage 上(W0 预演 ALL_PASS 4/4)。AST 同一性证据保留 | receipts/P_publication_boundary*.txt、receipts/W0_gates_dryrun_*.log、fixpkg_e_2026-09-27/receipts/PUBLICATION_V2_runs.txt |
| 执行器侧 | 克隆 `~/cc_tmp/gapfix4_exec_20260926T1911Z`:d01e35d + 201188d(`ops/producer_release/20260927_gapfix/` 下的契约与收据,**未推送**);离线电池 **166/166 全绿** | §4 |
| 版本探针 | `gap_version_probe.py`:钉 d01e35d,候选 sha 从包契约读(即 5eaabcdb);first-anchor 步检查来源必须为 own、不得有 GAP_PAGE | 在当前未安装机器上做控制:MISMATCH n=3,只差三个 sha,其余全 OK |
| release_gates | `gap_classfix_2026-09-26/window/gates_gapfix_{W0_pre,W4_install,W5_after_start,W6_first_anchor_*,RB_rollback}.json`(release_gates.py 格式,全部能正常加载) | — |

## 1. 修法要点(文件级)
- `prev_state.latest_state`:取最近一份有效状态,具名拒绝无效文件(读不出 / pickle / 缺键 / 错锚 / 越界 / 重复 / 非有限 / 退化)。界 6 锚,越界照样承接并标 `_beyond_bound`。
- combo_stage 的四处查找(weights L59、f10、kc、fc)都改用它;非 own 时,在 target_combo 和 combo_live_status 里写 `state_lookup` 字段。
- **页报**:有被拒文件、越界、无有效状态,都在**发布之后**发 HIGH;页报失败不影响已发布的书;演练只记不发;日志一事件一行。
- **冷启动**:见设计原则第 3 条。
- **成员历史**:`members_rule.members_at`(即 shadow_loop L676–701 原文)。在 10 月底前,每锚会重算 2 个锚(09-26 12Z/16Z),日志记 `MH_RECOMPUTED`,target_combo 记 `members_recomputed`。
- 生产者 LR 洞(shadow_loop L752)**不在本包**:按 lead 对 news2 的裁定走路径 A,随十月重建处理,重播种构建加连续性门。news2 的附加建议记为下一个生产者包的设计项:恢复锚追加的条数 k 必须等于实际经过的锚数,否则显式记 0 并写出洞的位置,不许静默。

## 2. 窗 W = [N+1:00, N+3:40](目标 09-27 05:00–07:40Z;每步报判词行和真实退出码)
- **W0 预检**:`/usr/bin/python3 release_gates.py window/gates_gapfix_W0_pre.json <LOG>`,内容是静默窗、真实 home 预检、包内单元测试、发布边界测试 v2(跑在包的 combo_stage 上)。另外人工确认:`df` 剩余 ≥ 15 GiB;执行器运行树 = d01e35d。
- **W1 停生产者侧服务**:`com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity` 逐个 bootout。等周期作业自然结束,不按名字 kill;`ps` 里看不到它们的进程。
- **W3 执行器候选**:
  1. 在运行树 HEAD 上新建克隆,cherry-pick 201188d 的两个文件;
  2. rsync state(A4 排除项);
  3. `ops/safe_commit.sh`,全电池必须全绿,pathspec 只有这两个文件;
  4. 推送 → 在 anchor.lock 下执行 `ff_running_tree.py <NEWSHA>`;
  5. `gap_version_probe.py after-w3 <NEWSHA> ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json`,末行必须 `OK n=0`。
- **W4 files-only 安装**:`release_gates.py window/gates_gapfix_W4_install.json <LOG>`。它执行 apply → `installed_not_started`,再跑 after-w4 探针(OK n=0)。BK = `~/cc_tmp/gapfix_install_BK_20260927`(必须不存在)。
- **W5 启动** 四个服务 → `release_gates.py window/gates_gapfix_W5_after_start.json <LOG>`:运行路径上的 combo_stage 必须是 5eaabcdb。
- **W6 首锚验收**(首锚 = 08Z 1790467200;备用窗时 = 12Z 1790481600):标准验收(inspect_anchor / VERSION_PROBE / M3_SELFCHECK / parity / B4_POOLED / report / watchdog),再加 `window/gates_gapfix_W6_first_anchor_<A>.json`。首锚判据(冻结):
  - (a) 正常锚:kc/fc/f10 来源**必须为 own**;本锚不得有 GAP_PAGE;combo_live_status ok 且 anchor = A。与现码字节相同的性质由 C0 负责,C0 已在沙箱 3 锚上验过。
  - (b) 日志有 `MH_RECOMPUTED … 2 anchors [1790424000, 1790438400]`,errors {};target_combo 有 `members_recomputed`。09-27 12Z/16Z 的 drank 三列因此恢复为按生产者规则计算的值。
  - (c) comboparity 对该锚 PARITY。
  - 任何一项不符 ⇒ 停,交 lead。

## 3. 回滚
- `release_gates.py window/gates_gapfix_RB_rollback.json <LOG>`:combo_stage 逐字节回到 12a76de8,三个新文件移到旁边,状态零改动(演练 F5 已验证)。执行器侧归档提交可以保留,它不影响行为。
- **回滚后的已知风险**:回到原缺陷。缺锚时仍需 state-only 桥接(`gap_recovery_2026-09-26/devices/combo_state_bridge.py`);如果当时在 12Z 之前,还需要成员历史回填(§6)。

## 4. 执行器侧电池
克隆 `~/cc_tmp/gapfix4_exec_20260926T1911Z`:d01e35d + 201188d,状态 rsync 自生产。用 `ops/run_acceptance_offline.sh` 跑,ACCEPT_PY 未设,解释器 /usr/bin/python3。结果:**ACCEPTANCE: ALL GREEN (166/166 suites exit 0), OFFLINE_ACCEPTANCE_EXIT 0**(receipts/BATTERY_gapfix4_201188d_20260926T1911Z.log)。前一版 GAP3 契约的同一电池已经 166/166 全绿(9ddc3d779)。

## 5. 缺锚影响量级(lead 项 (a);沙箱 A = 09-26 08Z,删掉 A−24h 的成员历史)
收据 receipts/M_READOUTS_run2.json、GAPFIX_JUDGE_run2/3.json 的 M 节。
| 量 | 现码 | 补丁码 |
|---|---|---|
| drank 三列在 A 行为 0 的比例 | 100%(基线 1.9%) | 1.9%(= 基线) |
| F10 分数与基线的 Spearman | 0.9940 | 1.0(逐位) |
| F10 书(state_H_f10)Σ\|dw\| | 0.0041(gross 0.78) | 0 |
| combo 的 F10 半本(state_H_fc)Σ\|dw\| | 0.0028 | 0 |
| combo 目标 Σ\|dw\| | 0.00126(gross 0.817,68 个名) | 0 |
训练分布(dlarch 实测,收据 360062c09 `receipts/f10full_2026-09-26/DRANK_ZERO_SHARE_live_F10_train_2026-09-26.json`):在役 F10 训练窗口 7,656 锚 / 201 万行里,逐格为 0 的比例是 0.61–0.62%,三列同时为 0 的行占 0.43%;**「全部名三列全 0」的锚一个都没有(0 / 7,656)**。⇒ 09-27 12Z/16Z 那种整锚全 0 的输入,在训练分布之外。模型在这种输入上的实际反应以上表的沙箱实测为准(Spearman 0.994,目标 Σ|dw| 0.00126)。

## 6. 备用:成员历史回填装置(只在本包未能在 12Z 前装上时使用)
- `devices/members_hist_backfill.py`,子命令 check / apply / verify / rollback。**只追加**,已有的锚不许改;generation.json 只重签 members_hist 的 sha。
- 判据 C1–C6 写在装置头部,入库在任何读数之前(首提 a0449c09a,rev 1 561433f28)。
- 沙箱测试 **13/13**(receipts/TEST_MEMBERS_HIST_BACKFILL_run.log):
  - 正控:把 04Z 删掉后回填,结果与删掉的真值**逐位相同**;
  - 红控:目标锚已存在 / 轴不对齐 / 目标不是缓存行 / 成员数不对 / 已记录的控制锚被改 / 生产者在运行 / 回滚时文件已被改,**各自拒绝**。
- 实盘只读 check(当前,09-26 19:0xZ):C1 红(shadowloop 在跑,**必须在 W1 停服务之后才能 apply**,否则生产者下次保存时会用内存里的旧历史覆盖文件);C4 红(12Z/16Z 晚于生产者最后一锚 08Z,20Z 那一锚跑完后才会变成缓存行)。控制锚 04Z/08Z 在实盘缓存上逐位复现。
- 用法:`~/wide_shadow/venv/bin/python devices/members_hist_backfill.py {check|apply|verify} --targets 1790424000,1790438400 --receipt <R>`,在服务停止的窗内执行。

## 7. 下一个执行器包(本包不含;按 lead 裁定列表)
| 站点 | 分类 | 缺锚后果 | 建议 |
|---|---|---|---|
| external_book.py L506-507 + legs.py L199 + _size_book | 放大 | 执行器丢弃生产者 gross,任何过了 0.4 门的低 gross 书都按 2.0×NAV 交易;执行器没有换手或连续性检查 | 目标文件加「状态来源」字段;执行器对非 own 且 gross_norm 偏离近期中位的目标页报或拒绝(需判据) |
| 20260922 发布边界测试 | 测试漂移(E-0926-H) | 在生产上 4/6 红 | env 从被测模块派生;late_status_error 改为 C 发布的合同;接进生产者发布门 |
| per_name_stop.py L131 | 静默降级 | 「连续 2 个终锚」按次数不按槽位,跨缺锚也照算 | **lead 裁定 (B),已在 fix-pkg-e 实现**(克隆提交 4e3fc6c):止损时机不变,计数器记锚时戳,跨缺锚触发时事件写明「跨缺锚 k 锚」并发 HIGH。(A) 缺锚复位 / (C) 缺锚后更早触发都会改变止损时机,需要用户裁定,本包不做 |
| **风险项(待向用户报)**:HOLD 期间止损出场暂停 | 风险 | 执行器 HOLD(缺目标或目标被拒)时不进入 `_trade`,已触发的逐名止损不会下出场单;HOLD 可以持续多个锚,止损也就失效同样长的时间 | 列入下一次向用户的风险报告;可能的修法(HOLD 期间只执行止损出场)属于书行为改动,需要用户裁定 |
| regime_dash.py L68 `prevA=A-14400` | 静默降级 | 缺锚后第一锚的已实现 IC 和 sleeve 归因为 None;缺锚区间的损益不进累计 | 取最近一次记录,并具名写出缺锚区间 |
| regime_weekly / regime_dash_ext `rows[-42:]` 等 | 标签失真 | 「7 天」「连续 12 锚」实为行数 | 改为按时间窗 |
| stop_overlay.py L80-88, L40, L95 | 静默降级 | NEED=2 和 42 锚冷却按文件计数;积压时共用一个价格快照;另 `done[-500:]` 约 43 天后会重处理旧文件 | 证据收集器,低优先 |
| anchor_report.py L301 prev_row | 响亮降级 | 告警「上一锚持仓未知」 | 外观问题 |
| notarize_ledgers.py L196/L316 | 天粒度 | 当日作业漏跑的那天不会被公证,事后回补会因顺序检查被拒 | 与缺锚无关,记为另一个缺陷 |
| 资金费账本 binance_funding.py(positions_at L270 + write_funding_rows L463) | 静默丢行(news2,7f08ff7cb / 515b3fb8c) | (a) 回读老于一个锚间隔就拒绝定价,缺口里的结算全部跳过;(b) 续跑点 = 盘上最新结算 + 1ms,被跳过的行不落盘,之后永不重试(09-26 实例 545 行,靠显式按窗口回填) | ① durable 待定价队列(交易所原始 income 行含 tranId,出口只有定价写入或 90 天具名永久缺口);② 跨缺口定价三条件(有 t 后回读 B;(A,t) 折叠 supersede 后成交为 0;qty(A)=qty(B)−净成交,容差半 stepSize),行记 pricing_rule;验收测试「明天再停机一次」(12h 无回读含 4h/1h 结算;注入成交/改 B 必留队;续跑点越过缺口后队列仍在;队列写失败=失败+告警;20260926 真实日文件回归 = 545 行;1788033600 / 1790006400 作正控) |
| 生产者 LR(shadow_loop L752) | 静默留洞 | 3 个洞,席位偏 0.4–0.7pp(news2) | 路径 A;恢复锚的追加条数必须等于经过的锚数,或显式记 0 |
| 安全站点(取「最近一次」、实耗时间或具名缺槽) | 安全 | — | pilot_log.anchor_series、parity_summary、external_book.age_anchors、anchor_loop prev_nonzero、reconcile、M3 m3_overlay_last、watchdog、combo daemons、feature_cache_identity、nc_contract、beta_overlay_producer、dlw_features、depth_watch、backfill_markout |
