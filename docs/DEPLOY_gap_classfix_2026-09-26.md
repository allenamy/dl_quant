> **创建:** 2026-09-26 18:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** DRAFT 发布手册, 交 lead 审; 窗口未定(lead 定; 建议 09-27 09:00–11:40Z, 须在 09-27 12Z 之前) | **作废条件:** §0 任一 sha 变动(生产 combo_stage 不再是 12a76de8、包或执行器 HEAD 变化), 或 lead / 用户裁定

# 发布手册: 缺锚类修复(gap class fix) —— 生产者 files-only 发布 + 执行器侧发布归档

验收线(lead): **下一次任意长度的缺锚, 不需要人即可被处理。** 判据: `multi_asset/exports/research/gap_classfix_2026-09-26/ACCEPTANCE_gap_classfix_2026-09-26.md`
(冻结 11bc3b4be; 修订 1 2a7567019、修订 2 483713a15, 都在读数之前)。
**这是书行为改动**: 只在出现缺锚(或状态文件损坏)时改变发布的书(原先是 ABORT → HOLD 约 5 锚 → 冷启动;改后是承接最近一份有效状态)。无缺锚时输出与现码字节相同(C0)。按 CLAUDE.md 约束 5, 需要用户裁定。

## 0. 组件与门(窗前实测)
| 组件 | 对象 | 状态(收据) |
|---|---|---|
| 生产者树 | tree GAP3 = `make_tree.py`(基于生产 combo_stage **12a76de8** 的逐处唯一替换)→ combo_stage **fa0c7466**,新增 prev_state **9729dafa**、members_rule **be691560**、tests_prev_state **1fcfe0e2** | receipts/TREE_GAP3_PATCH_RECEIPT.json |
| 生产者包 | `package_GAP3/INSTALL_CONTRACT.json` sha **bca5c63b**(nc_files_contract_v1:4 个文件、0 个归档移动、钉住 14 个不变文件) | `gap_package_files.py` |
| 真实 home 预检 | `nc_install_files.py preflight package_GAP3` → **PREFLIGHT_PASS** | receipts/PREFLIGHT_real_home_*.txt |
| 安装演练(机器布局副本) | TEST_GAP_INSTALL_FILES **13/13**(F0 预检;F1 装后状态零改动、生产者能加载、装上的单元测试过;F5 回滚逐字节还原;红控 F2/F3/F8/F9 各自拒绝) | receipts/TEST_GAP_INSTALL_FILES_run1.log |
| 单元测试 U | tests_prev_state **15/15**;旧谓词在 12/12 个有分辨力的用例上 RED;4/4 个变异被抓住 | receipts/U_tests_prev_state_stdout.txt |
| 沙箱重放(判官) | run 2 **GAP_FIX_JUDGE PASS 21/21**(run 1 为 FAIL 4,只有页报那一条;修的是代码,判官没动,见 RUN1_VERDICT_NOTE.md) | receipts/GAPFIX_JUDGE_run2.json(b14137400) |
| 成员规则 | V1 **13/13** 快照逐元素复现生产者成员集;V2 事后重算平均 Jaccard 0.9987,carry-forward 0.9914 ⇒ 用重算 | receipts/MEMBERS_V1V2.json |
| 发布边界测试 P | **作废**:20260922 那套测试在生产 12a76de8 上本身就 4/6 红。替代证据:发布 Try 节点的 AST 与现码完全相同 | receipts/P_publication_boundary.txt |
| 执行器侧 | 克隆 `~/cc_tmp/gapfix_exec_20260926T1807Z`,在 d01e35d 上本地提交 `ops/producer_release/20260927_gapfix/{INSTALL_CONTRACT.json,PATCH_RECEIPT.json}`(c78bcd0,**未推送**,origin 已指向无效路径);离线电池 **166/166 全绿** | §4 |
| 版本探针 | `gap_version_probe.py`(由 v2c 探针派生;钉更新为 d01e35d;新增 first-anchor 步)。控制:在当前(未安装)机器上跑 first-anchor → MISMATCH n=3,符合预期 | receipts/VERSION_PROBE_control_*.txt |

## 1. 修法(类形状)
1. **上一锚状态 = A 之前最近一份有效状态**(`prev_state.latest_state`)。四条状态都改:weights(生产者 H,L59)、f10(L237)、kc/fc(L310)。原先都恰好取 `A−14400`。
   - 有效的条件:可读;无 pickle;键齐;anchor 键 == 文件名锚;idx 为 1 维整数、落在 [0, NW)、不重复;val 有限且与 idx 等长。不满足的**具名跳过**,继续往前找。
   - 来源标签:`own`(与现码逐字同)/ `own_gap<m>` / `…_rejected<n>` / `…_beyond_bound`。标签写进 target_combo(`kc_state_source` 等)。只要不是 `own`,就另写 `state_lookup` 字段到 target_combo 和 combo_live_status。anchor_report 已有「kc/fc 状态断链」告警,对非 own 会响。
2. **界 = 6 锚(24h)**。界内:自动处理,不页报,只留记录。
3. **越界时怎么办**:照样承接最近一份有效状态并发布,另发 HIGH 页报。理由如下:
   - 执行器缺目标时按 `on_unavailable=hold` 一直持旧书(anchor_loop L1453),旧状态正是执行器手里拿着的书;
   - 冷启动从零出发,gross 约 0.07;而执行器不保留生产者的 gross(external_book L506-507 除以 gross_in,legs.py L199 归一,再乘 NAV×2.0)。所以冷启动书一旦过了 0.4 门,就会按满杠杆一次性换仓;
   - 如果改成 HOLD,旧书会无限期地越来越旧。
   唯一需要人的情形是「一份有效状态都没有」(全新安装或状态全毁)。这时保留原有具名回落(warmstart_live_H / warmstart_f10_H),另发 HIGH 页报;飞前 0.4 门仍会挡住零书。
4. **页报**:以下三种情况在发布之后发 HIGH:有被拒文件、越界、无有效状态。页报不占截止余量;页报失败不会把已发布的书变成中止;演练只记不发(与 M3 相同)。日志一事件一行。
5. **成员历史缺锚**:members_hist 里没有条目的窗口锚,用生产者成员规则现算(`members_rule.members_at`,即 shadow_loop L676-701 原文),fetch 名单取 A 时刻的;计数 `MH_RECOMPUTED` 写进日志和 target_combo。**本次实例**:09-26 12Z/16Z 没有成员历史,若不修,09-27 12Z/16Z 的 drank_*_1d 三列会全为 0。M 臂实测:现码 F10 分数 Spearman 0.9940,发布权重 L1 差 0.00126;补丁码与基线逐位相等。⇒ 本包在 09-27 12Z 之前装上,就**不需要**另做成员历史回填,也不改任何状态文件或 generation.json。
6. **不在本包**(设计选项 / 下一个包):
   - 生产者 LR 洞(shadow_loop L752):按 lead 对 news2 的裁定走路径 A,随十月重建处理,重播种构建加连续性门;量级 0.4–0.7pp,判为不实质。
   - 已中止锚的状态仍然写盘(L254/L323):有了 1,零状态不再出现,毒化链也就断了。「只承接已发布锚的状态」列为选项,不做。
   - 执行器侧:不信生产者 gross 的问题(建议加一个连续性字段或换手门),per_name_stop 按次数而非槽位计数。见 §5。

## 2. 窗 W = [N+1:00, N+3:40](lead 批准起算;每步报判词行和真实退出码)
- **W0 预检**:`venue_quiet_window.py` rc 0,剩余 ≥ 60 min;`df` 剩余 ≥ 15 GiB;执行器运行树 = d01e35d;`nc_install_files.py preflight package_GAP3` → PREFLIGHT_PASS(生产 combo_stage 仍是 12a76de8,14 个钉住的文件未变)。
- **W1 停生产者侧服务**:`com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity` 逐个 bootout。等周期作业自然结束,不按名字 kill;`ps` 里看不到它们的进程。(shadowloop 不 import 被改的文件,本包也可以不停它;为与既往协议一致,仍列入。)
- **W2** 无(没有上游补丁)。
- **W3 执行器候选**:在运行树 HEAD 上新建克隆,cherry-pick 归档提交(c78bcd0 的两个文件)→ rsync state(A4 排除项)→ `ops/safe_commit.sh`(全电池必须全绿,pathspec 只有这两个文件)→ 推送 → 在 anchor.lock 下执行 `ff_running_tree.py <NEWSHA>` → `gap_version_probe.py after-w3 <NEWSHA> <两个文件>` 末行必须 `OK n=0`(book.json 与 d01e35d 逐字节相同)。
- **W4 生产者 files-only 安装**:`~/wide_shadow/venv/bin/python nc_install_files.py apply package_GAP3 <BK>` → `installed_not_started`,state_manifest_diff == [] → `gap_version_probe.py after-w4 package_GAP3 <BK>/NC_FILES_INSTALL_RECEIPT.json` OK n=0。
- **W5 启动** 四个服务 → `gap_version_probe.py after-w5 …` OK n=0(运行路径的 combo_stage == fa0c7466)。
- **W6 首锚验收**(下一锚 N+30 之后):标准验收(inspect_anchor / VERSION_PROBE / M3_SELFCHECK / parity / B4_POOLED / report / watchdog)再加 `gap_version_probe.py first-anchor package_GAP3 <A>`。本修复特有的预期(冻结):
  - (a) 若 A 距上一份状态恰为 4h:kc/fc/f10 来源为 `own`,无 GAP_PAGE,combo_live_status 无 state_lookup。
  - (b) 约 11-05 之前(09-26 12Z/16Z 还在 239 锚 ≈ 39.8 天的窗内),每锚日志有 `MH_RECOMPUTED … 2 anchors [1790424000, 1790438400]`,target_combo 有 `members_recomputed`,errors 为 {}。
  - (c) comboparity 对该锚 PARITY(它重放的就是新代码)。
  - 任何一项不符 ⇒ 停,交 lead。

## 3. 回滚
`nc_install_files.py rollback package_GAP3 <BK>`:combo_stage 逐字节回到 12a76de8,三个新文件移到旁边,状态零改动(演练 F5 已验证)。执行器侧归档提交可以保留(它不影响行为),或 revert。
**回滚后的已知风险**:如果回滚之后又出现缺锚,就回到原缺陷(零回落 → ABORT)。那时仍需 lead 的 state-only 桥接(gap_recovery_2026-09-26/devices/combo_state_bridge.py)。

## 4. 执行器侧电池
克隆 `~/cc_tmp/gapfix_exec_20260926T1807Z`(d01e35d + c78bcd0,状态 rsync 自生产,56 个完成日全覆盖),用 `ops/run_acceptance_offline.sh` 跑(ACCEPT_PY 未设,解释器 /usr/bin/python3 3.9.6)。**ACCEPTANCE: ALL GREEN (166/166 suites exit 0), OFFLINE_ACCEPTANCE_EXIT 0**(receipts/BATTERY_gapfix_c78bcd0_20260926T1807Z.log)。本克隆**不推送**;窗内由 lead 按 W3 重做。

## 5. 全栈「上一锚」查找逐站点表(只读核查,2026-09-26;combo_stage 与 shadow_loop L752 之外)
| 站点 | 分类 | 缺锚后果 | 建议 |
|---|---|---|---|
| external_book.py L506-507 + legs.py L199 + _size_book | 放大 | 执行器丢弃生产者 gross,任何过了 0.4 门的低 gross 书都按 2.0×NAV 交易;执行器无换手或连续性检查 | 下一个执行器包:目标文件加「状态来源」字段,执行器对非 own 且 gross_norm 偏离近期中位的目标页报或拒绝(需判据) |
| combo_stage L167-176 → f8 L336-339(成员历史) | 静默降级 | 缺锚 +24h 的 drank 三列为 0 | **本包已修** |
| per_name_stop.py L131 | 静默降级 | 「连续 2 个终锚」按次数而非槽位,跨缺锚也照算;HOLD 期间不执行止损出场 | 下一个执行器包:计数器存锚时戳,缺锚即复位(或写明跨缺锚照算) |
| regime_dash.py L68 `prevA=A-14400` | 静默降级 | 缺锚后第一锚的已实现 IC 和 sleeve 归因为 None;缺锚区间的价格与资金费损益不进累计 | 取最近一次记录,并把缺锚区间具名成一行 |
| regime_weekly / regime_dash_ext `rows[-42:]` 等 | 标签失真 | 「7 天」「连续 12 锚」实为行数 | 改为按时间窗 |
| stop_overlay.py L80-88, L40, L95 | 静默降级 | NEED=2 和 42 锚冷却按处理过的文件计数;积压时一个价格快照被用于多个文件;另 `done[-500:]` 约 43 天后会重处理旧文件(与缺锚无关) | 证据收集器,低优先 |
| anchor_report.py L301 prev_row | 响亮降级 | 告警「上一锚持仓未知」 | 外观问题 |
| notarize_ledgers.py L196/L316 | 天粒度 | 若当日作业漏跑,该日不被公证,事后回补会因顺序检查被拒 | 与缺锚无关,记为另一个缺陷 |
| pilot_log.anchor_series、parity_summary、external_book.age_anchors、anchor_loop prev_nonzero、reconcile、M3 m3_overlay_last、watchdog、combo daemons、feature_cache_identity、nc_contract 衰减、beta_overlay_producer(k≤6)、dlw_features、depth_watch、backfill_markout | 安全 | 取「最近一次」、实耗时间,或具名缺槽 | — |
