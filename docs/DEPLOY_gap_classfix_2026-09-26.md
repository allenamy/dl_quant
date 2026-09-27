> **创建:** 2026-09-26 18:1xZ(rev 2 19:2xZ: GAP4) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** 发布手册 rev 3(09-27 05:xZ,arm64 新机复核 + 两处自身缺陷更正 + 改期,见 §rev 3),交 lead 审;目标窗 **09-27 09:00–11:40Z**(08Z 新机首锚验收之后,首锚 12Z 1790510400),备用窗 13:00–15:40Z(首锚 16Z 1790524800) | **作废条件:** §0 任一 sha 变动(生产 combo_stage 不再是 12a76de8,或包、执行器 HEAD 变化),或 lead / 用户裁定

# 发布手册:缺锚类修复(gap class fix,tree GAP4)—— 生产者 files-only 发布 + 执行器侧发布归档

## rev 3(2026-09-27 05:xZ,integ):arm64 新机复核、两处自身缺陷更正、改期
**这一节优先于下文。凡与下文冲突,以本节为准。**

### R3.1 新机复核结果
新机:arm64;生产者 venv 为 python 3.14.7 / numpy 2.5.2;执行器用 /usr/bin/python3 3.9.6。收据都在 `gap_classfix_2026-09-26/receipts/arm64_2026-09-27/`。

| 项 | 新机结果 | 与旧机(x86)比 |
|---|---|---|
| 安装演练 TEST_GAP_INSTALL_FILES | **13/13 PASS**(F0–F9 红控全部拒绝) | 判词相同。演练夹具契约的 sha 不同(6b0f87 对 7addd6):它把 built_utc 和工作目录路径写进了契约,每跑一次都会变。真实包契约 27a0c493 在真实 home 上预检 PREFLIGHT_PASS |
| release_gates W0 预演 | **ALL_PASS 4/4**(05:04:06Z) | 相同 |
| 回放判官 run 4:在新机上把 33 个臂×锚全部重跑,两套代码都重跑,不复用任何 x86 产物(`devices/run_arms4_arm64.sh`) | **GAP_FIX_JUDGE FAIL n_bad=3**:三条都是 C0 里的 `current_vs_archived` 子项,另外 22 条判词全部 PASS | 见 R3.2 |
| 跨机逐文件对比(`devices/cross_host_compare.py`,收据 `receipts/CROSS_HOST_x86_run3_vs_arm64_run4.json`) | 33 个臂×锚,共 208 个输出文件:**180 个逐位相同**;所有 state_H_{kc,fc,f10}、weights_combo、target_blend 都逐位相同;退出码 33/33 一致;文件有无 33/33 一致 | 其余 28 个见 R3.2 |
| 执行器侧电池(克隆 201188d) | **165/166**,唯一的红是 tests_nosleep A10 | 旧机 166/166 |

### R3.2 回放判官 FAIL 的来源:beta_overlay 差 1–2 ulp,属于容差,不是逐位
- C0 的核心性质在新机上**同机逐位成立**:每个锚上 current 与 patched 的权重、三份状态、target_combo 字节、target_blend 字节、weights_combo 全部相同,两边 rc 都是 0,T 也 PASS。
- 挂掉的是 C0 里的附属合理性检查:新机的 current 回放,对比旧机生产存档的 `target_live/<A>.json`。
  - 两边权重 319 / 318 / 318 个**逐位相同**;
  - 只有 `beta_overlay` 键不同:每个文件有 21–26 个名的 beta 差 ≤ 4.4e-16(1–2 ulp)。迁移收据在 00Z 已经记过同类现象(18/450,≤ 2.2e-16)。
- 28 个非逐位文件的构成:
  - 24 个是 target_live_PARITY:weights 逐位相同,只有 beta_overlay(≤ 4.4e-16)和 written_utc 不同;
  - 4 个是 target_combo:把沙箱根路径换成同一个占位符后完全相同,差别只在 state_lookup.rejected[].path 里嵌的沙箱路径。
- **判定**:回放判官的判词本身不改(它是冻结的)。照实报告:**权重、状态、书层逐位跨机一致;M3 的 beta 跨机差 1–2 ulp**。M3 仍是 shadow,beta 不进书。M3 开启后,对冲量相对差约 1e-16 量级。
- 新机上此后的存档都在新机上产生,同机平价不受影响。迁移收据里 00Z 的 parity 已是 319/319 逐位。

### R3.3 更正:我包里的两处缺陷(窗前发现,未造成任何后果)
1. **W6 首锚门的 epoch 标错了 8 小时**(UTC+8 换算错误):
   - `…_1790467200_08Z.json` 里的 1790467200 实际是 09-27 **00Z**;
   - `…_1790481600_12Z_backup.json` 里的 1790481600 实际是 **04Z**;
   - 下文 §2 W6 的「首锚 = 08Z 1790467200 / 12Z 1790481600」同样错了。
   - 两个旧文件已改名为 `*.VOID_epoch_is_00Z.json` / `*.VOID_epoch_is_04Z.json`。新门的文件名标签由生成脚本从 epoch 反算并断言。
2. **gap_version_probe after-w5 会崩**:它只按包里的候选文件取期望 sha,本包不含 shadow_loop_v3.py,于是抛 `KeyError`,W5 门必然 FAIL(而且是在服务已经启动之后)。
   - 另外,新机上根本没有 com.hsy.sidecar 的 plist,也就没有 disabled 覆盖项,旧谓词会把这台机器判为 BAD。
   - 探针 rev 1:
     - 期望 sha = 候选 ∪ 契约 unchanged 钉;两边都没钉的路径具名 BAD,不再崩;
     - sidecar 满足「被 disabled」或「launchd 找得到的地方都没有 plist」之一即可;
     - first-anchor 新增 `--expect-mh`,把 W6 (b) 从人工读日志改为机械核对。
   - 控制(未安装的本机):after-w5 只有 combo_stage 的 sha 一行 BAD;first-anchor 的 BAD 恰好是未安装的 3 个 sha 行和 members_recomputed 行;把字面量换成 3 锚时,「字面量 == 洞」一行也变 BAD(`VP_*control*.txt`)。

### R3.4 新机的发布前提(窗前必须成立)
- **P1 GitHub 凭据:已由 lead 修好。**
  - `~/.gitconfig` 两处 helper 改指 `/opt/homebrew/bin/gh`,备份在 `.gitconfig.bak_20260927`。
  - integ 于 05:31Z 复测:`GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/allenamy/dl_quant_live.git refs/heads/main` 返回 d01e35db…,与运行树一致。
  - 开窗前必须再实测一次。在修好之前,safe_commit 的 fetch / push、ff_running_tree 的 fetch,以及两个探针的「GitHub main」行都会失败。
- **P2 A10 修复:随 GAP4 的 W3 同一个提交走**(lead 裁定 09-27)。
  - 新机上任何电池都会停在 165/166,而 safe_commit 要求全绿,所以不带这个修复任何发布都会被拒。
  - 修复是 fix-pkg-e 克隆的提交 **cea1e15fa4051df1fb506a5989a3e582291ce95b**,只改测试 `live/tests_nosleep.py`,不碰生产代码。
  - 补丁留档在 `fixpkg_e_2026-09-27/receipts/arm64_2026-09-27/A10_fix_cea1e15.patch`,克隆丢了可以从这里重建。
- **P3**:08Z(1790496000)是新机上的第一个锚,必须先通过 lead 的验收,之后由 lead 发开窗信号。
- **P4**:运行树 HEAD 仍是 d01e35d;combo_stage 仍是 12a76de8;真实 home 预检仍是 PREFLIGHT_PASS。
- **P5 第 5 轮 C0,同主机参照**(lead 裁定):
  - 第 4 轮判官 FAIL(n_bad=3)原样入账,不改判据。原因是跨主机浮点差:beta_overlay 差 1–2 ulp,证据是 cross_host_compare。
  - 生产主机已换成 arm64,所以 C0 的参照物必须同主机。做法:08Z(1790496000)的生产产物落盘后,以它为参照只重跑 C0,判据一字不改,仍是逐位比较。
  - 装置见 R3.6。
  - **逐位相同 ⇒ 可以进窗;有任何差异 ⇒ 停下,不发布,交 lead。**

### R3.5 改期后的窗与步骤
- **主窗 09-27 09:00–11:40Z**,首锚为 **12Z = 1790510400**。
- **备用窗 13:00–15:40Z**,首锚为 **16Z = 1790524800**。
  - 走备用窗时,12Z 会用现码跑:members_hist 缺 09-26 12Z/16Z,F10 的 drank 三列在 12Z 输入为 0。§5 的沙箱量级是目标 Σ|dw| 0.00126。
  - 要避免这一点,只能在 12Z 前停服务、用 §6 的回填装置补上。由 lead 决定。
- **W3(一个提交,3 个文件)**:GAP4 执行器侧归档的两个文件,加 A10 修复。取代下文 §2 W3 的第 1–5 步。
  ```
  XC=~/cc_tmp/gapfix_release_$(date -u +%Y%m%dT%H%MZ); git clone ~/dl_quant_live $XC && git -C $XC remote set-url origin https://github.com/allenamy/dl_quant_live.git \
    && git -C $XC config user.name haosiyu && git -C $XC config user.email siyuhao0702@gmail.com
  git -C $XC rev-parse HEAD                      # 必须 == d01e35db56b4d7ed6abf0befd9f18452cd06c329
  G4=201188d652c69c2518be0d6457464940d24cca2e; A10=cea1e15fa4051df1fb506a5989a3e582291ce95b   # 完整 sha;短 sha 无法 fetch(已实测)
  git -C $XC fetch ~/cc_tmp/gapfix4_exec_20260926T1911Z $G4 && git -C $XC fetch ~/cc_tmp/fixpkg_e_exec $A10
  mkdir -p $XC/ops/producer_release/20260927_gapfix
  for p in ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json; do git -C $XC show $G4:$p > $XC/$p; done
  git -C $XC show $A10:live/tests_nosleep.py > $XC/live/tests_nosleep.py
  git -C $XC status --short --untracked-files=all -- ops live config   # 必须恰好这 3 个路径
  rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
  (cd $XC && bash ops/safe_commit.sh "producer release archive: gap class fix GAP4 (contract 27a0c493; files-only) + tests_nosleep A10 host-independent (arm64 host; test-only); quant_research DEPLOY_gap_classfix rev 3 W3" \
      ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json live/tests_nosleep.py); echo "rc=$?"   # 全电池必须 166/166
  NEWSHA=$(git -C $XC rev-parse HEAD); /usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA; echo "rc=$?"   # 在 anchor.lock 下
  /usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/gap_classfix_2026-09-26/devices/gap_version_probe.py after-w3 $NEWSHA \
      ops/producer_release/20260927_gapfix/INSTALL_CONTRACT.json ops/producer_release/20260927_gapfix/PATCH_RECEIPT.json live/tests_nosleep.py   # 末行必须 OK n=0
  ```
- **W5**:门文件不变,调用的探针已是 rev 1。
- **W6**:改用 `window/gates_gapfix_W6_first_anchor_1790510400_12Z.json`(备用窗用 `…_1790524800_16Z_backup.json`)。(b) 的期望改为 **3 个锚 [1790424000, 1790438400, 1790481600]**,即 09-26 12Z、09-26 16Z,再加 09-27 04Z(迁移中漏跑)。探针同时核对「字面量 == members_hist 在 A 之前的洞」,所以 08Z 若意外补上了 04Z,门会点名。**本条修订写于任何 GAP4 锚读数之前。**
- **窗前演练**(克隆,离线电池,新机,rsync 了完整 state):
  - d01e35d + A10:**ALL GREEN 166/166**(克隆 80ea0d5,收据 BATTERY_rehearse_T0_A10_80ea0d5.log);
  - d01e35d + GAP4 归档 + A10,**与本 W3 提交内容相同**:**ALL GREEN 166/166**(克隆 0d77784,收据 BATTERY_rehearse_T0_GAP4_0d77784.log);
  - 再加 M3 一行:**ALL GREEN 166/166**(克隆 527eec6,收据 `m3_on_2026-09-27/receipts/arm64_2026-09-27/BATTERY_rehearse_T0_GAP4_M3_527eec6.log`)。
  - 窗内的树内容与这些演练树相同,只有提交结构和 sha 不同。

### R3.6 第 5 轮 C0 装置(P5)
- `devices/gap_fix_judge_c0.py <root> <A> --out <json>`:从 `gap_fix_judge.py` 读出 C0 那一段源码原文(从 `# C0 ×3` 到 `A = GAP_A` 之前),只把 BASE_AS 换成 [A] 后执行。判据代码与冻结判官逐字节相同;装置启动时先断言这一段的 sha,把它和判官的 self_sha256 一起写进收据。
- 运行:`devices/run_c0_round5.sh <root> 1790496000 <receipt>`,依次重放 current base、patched base 各一次,再跑上面的判官。
- **前提**:08Z 的 snap COMPLETE、target_live_king 与 target_live 都已落盘(combo 写完之后)。放在 N+30(08:30Z)之后运行。它只有两次回放,约 20 秒,不是重 CPU。

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

## lead 审阅(2026-09-27 05:4xZ)
- rev 3 批准。P1(GitHub 凭据)lead 于 05:30Z 实测已成立:助手指向 `/opt/homebrew/bin/gh`,`ls-remote` 返回 d01e35db…,`fetch` rc=0。P4 实测:运行树 HEAD d01e35d,combo_stage 12a76de8。
- **追加一个开窗前提 P5**:回放判官第 4 轮的 FAIL(C0 current_vs_archived,beta_overlay 跨机 1–2 ulp)原样入账,判据不改。等 08Z(1790496000)在新机上的生产产物落盘后,拿它当同主机参照物,只重跑 C0 这一子项,作为第 5 轮。逐位相同才开窗;有任何差异就停,不发布。
- **备用窗的裁定**:主窗若没发成,改走备用窗,接受 12Z 用现码运行(drank 三列为 0,沙箱量级 Σ|dw| 0.00126)。不为此停服务回填,因为停服务回填本身引入的风险大于这点影响。
- **P5 澄清(05:5xZ,写于 08Z 读数之前)**:第 5 轮只重跑 C0 的 current_vs_archived 子项,不是整个 C0。原因:新机窗口里的 members_hist 有洞,约 40 天内不会出现无缺锚的锚,而在有洞的锚上 current 与 patched 不同本来就是 GAP4 要改的行为。第 5 轮判据:
  - (i) 08Z 上,新机 current 回放对新机生产存档,权重与 beta_overlay 逐位相同;
  - (ii) patched == current 引用 run 4 在 arm64 上 3 个无洞锚的逐位结果;
  - (iii) 08Z 上 patched ≠ current 的每一处差异,都要点名归因到 MH_RECOMPUTED 的 3 个锚 [1790424000, 1790438400, 1790481600]。有一处解释不了就停。
  - 否决 mhfill 臂:它是窗前新造的装置,新增出错面,换来的是重复证明。
