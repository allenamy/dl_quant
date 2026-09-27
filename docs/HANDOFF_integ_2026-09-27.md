> **创建:** 2026-09-27 14:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(integ) | **状态:** 交接件(lead 额度用尽,预计 09-30 回来;期间由独立研究员接手,见 `docs/HANDOFF_independent_researcher_2026-09-27.md` §7) | **作废条件:** 运行树不再是 d01e35d,或下文任何一个 sha 变动

# integ 交接(2026-09-27)

## 0. 一句话
- 我本机**没有在跑的作业**。
- 两个发布包 GAP4 和 M3 on 已在新机(arm64)上复核完,**发布冻结中,要等用户同意并重新开窗**。
- 恢复工具包已交付。实盘于 13:01Z 恢复。
- 16Z 首锚的账本侧核对由我做,结果见 §3。
- D10 候选生产者树**等研究员通知再开工**。
- 规矩:不开窗、不发布、不碰实盘凭据。

## 1. 发布包(都已在新机复核,都未发布)
| 包 | 候选 | 新机复核 | 手册 |
|---|---|---|---|
| GAP4(缺锚类修复,生产者 files-only + 执行器侧归档) | 包 `gap_classfix_2026-09-26/package_GAP4`(契约 27a0c493);执行器克隆 `~/cc_tmp/gapfix4_exec_20260926T1911Z` 的提交 201188d652c69c2518be0d6457464940d24cca2e | 安装演练 13/13;W0 预演 ALL_PASS 4/4;回放判官第 4 轮 FAIL n_bad=3,全是 C0 的 current_vs_archived 子项(beta_overlay 跨主机差 1–2 ulp,权重逐位相同;cross_host_compare:208 个文件中 180 个逐位相同,状态和书层全部逐位) | `docs/DEPLOY_gap_classfix_2026-09-26.md` rev 3(已由 lead 批准) |
| M3 on(`beta_overlay.mode` 由 shadow 改为 on,cap 2.5) | 克隆 `~/cc_tmp/m3on_exec_20260927T0059Z` 的提交 a6f8c21d658d19716e16c61d06229252e35b883a | 电池 165/166,唯一的红是 A10 | `docs/DEPLOY_m3_on_2026-09-27.md` rev 1(已由 lead 批准) |
| A10 修复(只改测试) | fix-pkg-e 克隆 `~/cc_tmp/fixpkg_e_exec` 的提交 cea1e15fa4051df1fb506a5989a3e582291ce95b(补丁留档:`fixpkg_e_2026-09-27/receipts/arm64_2026-09-27/A10_fix_cea1e15.patch`) | 变异阶梯 7/7;演练电池:d01e35d+A10 为 166/166,+GAP4 为 166/166,+M3 为 166/166;fix-pkg-e 为 168/168 | 按 lead 裁定**随 GAP4 的 W3 同一个提交走**(3 个路径),命令在 GAP4 手册 R3.5 |

**开窗前必须知道的几件事(都写进了手册):**
- **新机上旧 A10 必红,safe_commit 因此拒绝任何执行器提交**,除非 A10 修复在同一个提交里,或者已经在运行树上。若 GAP4 不发而要先发 M3,lead 的裁定是:先按 dbe522c4d 版 R3.5 单独发 T0(A10),OLDSHA 取 T0SHA,探针期望不改。
- **第 5 轮 C0(开窗前提 P5)还没跑**,原因是 08Z 验收失败(双执行器事故)。
  - 判据是 lead 的方案 B,原文入库在 `gap_classfix_2026-09-26/receipts/arm64_2026-09-27/RULING_round5_B_lead_2026-09-27.md`:
    - (i) 新机 current 回放对新机生产存档,逐位相同;
    - (ii) 引用 run 4;
    - (iii) patched≠current 的每一处差异都归因到 MH_RECOMPUTED 的锚。
  - 装置是 `devices/run_c0_round5.sh` 加 `c0_round5_attrib.py`,控制都已入库。
  - **参照锚要换**:08Z 不能再用,那个锚的存档里执行状态被事故打乱了。换用恢复之后的首个干净锚(例如 16Z 1790524800),同时要按那一锚在 A 之前的 members_hist 洞重新确定 EXPECT_MH(14:1xZ 实测 members_hist 的洞 = 09-26 12Z、09-26 16Z、09-27 04Z;08Z 与 12Z 的生产者都跑了)。这两个改动都要由接手人在读数之前写定。
- **W6 首锚门**:文件名标的时刻是从 epoch 反算并断言过的(旧门的 epoch 差了 8 小时,已作废)。开窗时间变了,就要为新的首锚重新生成门文件(`window/` 下已有 12Z 和 16Z 的两份;换锚照同样方式生成),`--expect-mh` 取当时的洞。
- M3 手册的首个 on 锚要跟着新窗口重新填。OLDSHA 等于当时运行树的 HEAD。
- 发布窗惯例:[N+1:00, N+3:40],上一次发布的首锚验收通过之前不叠新的发布。

## 2. 恢复工具包(已交付;实盘 13:01Z 恢复)
- 方案文件:`docs/PLAN_recovery_after_double_executor_2026-09-27.md`。§0–§6 是分析,§7 是最终步骤单,§8 是首锚加查清单。
- 装置在 `multi_asset/exports/research/recovery_2026-09-27/devices/`:

| 装置 | 做什么 |
|---|---|
| `venue_readonly.py q1q4 \| anchor` | 只读场所核验:只访问 GET 白名单,只打印密钥指纹,UNKNOWN 不算通过;离线测试 ALL PASS。**要加载实盘 .env,由研究员或 lead 跑** |
| `ledger_side_check.py <A>` | 离线账本侧核对:K2、K3 账本侧、K4、K5、K7 |
| `recheck_clone.sh` | 隔离克隆 + 沙箱里跑 `resume --check` |
| `gate_conditions.py` | 放行门的逐条件判词 |
| `rebuild_stats.py` | 历史重建的到位率和成本,合池 |

- 用户裁定:
  - 密钥暂时不换,旧指纹 88d264fe14;只读密钥 f952dbea01 不在轮换范围内。
  - **K1(外来 orderId = 0)只查 16Z、20Z、09-28 00Z 三锚。**
  - 三锚之后剩下的风险:旧机如果重新联网并启动作业,就没有哨兵了,唯一的防线是旧机保持停用、不开机。
- 待办(不阻塞,排在恢复之后):
  - Q5/Q6 取证:按 orderId 归属旧机的单,查它在 04Z/08Z 有没有也跑了正常锚;
  - 旧机账本证据入库;
  - 用 `RECONSTRUCTED_FROM_VENUE` 行补记外来成交;
  - §4 的类修法提案 a–d,在 09-30 08:47Z(§9-F7)之后预注册。

## 3. 16Z 首锚账本侧核对(结果)
(见本文件末尾的追加节;16:30Z 之后跑 `ledger_side_check.py 1790524800`,收据写到 `recovery_2026-09-27/receipts/LEDGER_SIDE_1790524800.json`。)

## 4. D10 候选生产者树(关键路径;等研究员通知再开工)
- 发布窗:用户已顺延到 **09-30 13:00Z 窗**(守住 F7 冷静期)。树的最晚完成时间:09-30 09:00Z(见研究员交接 §7)。
- 范围(runbook 1fa4e3be5,news2 终裁):
  - `nc_contract.ingest_settlements` L77 改用 `interval_d10`;
  - 声明间隔只用 `/fapi/v1/fundingInfo`,拿不到就 **只有 UNRESOLVED 一个分支**(没有默认 8h);
  - nc_prep、nc_seed_state、nc_derive_producer 同步修改;
  - 状态从**窗前钉住 sha 的归档快照**按毫秒键整体重新播种;
  - 回滚方式是按字节恢复切换前的快照。
- 树里带的 `common/funding_interval.py`,sha 必须等于 5d5bf20797ca41c0b83ce0d6d710acb9baf2c500c93c9b40b7084c23182afb3f(冻结于 2864babfd;我在 07:0xZ 实测相符)。
- King 的服务模型文件:`king_oct_2026-09-27/receipts/release_2026-09-27/served/king_2026.txt`,sha256 8534e56b…2b7182,2,386,470 字节,出自 e7181349d,我已实测。**只能用这个文件本身,不能用重训产物替代。** 顺序:dlarch 的 F10 书层格之后装包。
- 执行器电池:新机上约 12 分钟一次;每个执行器提交约 25 分钟墙钟(演练一次加 safe_commit 一次)。
- 开工第一步:**先冻结判据和测试(测到红),再写代码。**

## 5. 本会话的提交(integ,按时间)
- dbe522c4d:arm64 复核 + A10 + 两处自身缺陷(W6 epoch、after-w5 KeyError);
- ab8f2a814 / 其后:第 5 轮装置(mhfill 已按 lead 否决撤回)与控制;
- cb52106a4:方案 B 裁定原文 + 05:33Z 控制;
- 恢复方案:初版、rev 1(§7/§8 + venue_readonly + 测试)、§7 第 3 步更正、Q2 盲区注释、ledger_side_check。
- 全部按 pathspec 提交并核过 --stat。暂存区里别人的文件(例如 `loop_2026-09-26/inflight_status.py`)我没有碰。

## 6. 本机遗留(都属于我,都可以删;没有进程)
- `~/cc_tmp` 下:
  - 发布克隆:`gapfix4_exec_20260926T1911Z`、`m3on_exec_20260927T0059Z`、`fixpkg_e_exec`(**保留**,里面有未推送的候选提交);
  - 演练克隆:`rehearse_*_20260927T051*`;
  - 恢复核验克隆:`recovery_check_*`、`recovery_recheck_*`(其中 `recovery_recheck_20260927T130028Z` 是 lead 13:00Z 跑的)。
- scratchpad `integ/replay4_arm64`、`replay5_*`:回放根,需要复查时用。
- `/tmp/nonet.sb`:禁网沙箱配置。
