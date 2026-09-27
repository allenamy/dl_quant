> **创建:** 2026-09-27 03:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 交接(用户迁移到新电脑;lead 暂停令) | **作废条件:** 下列任一件被 lead 重新派定

# 交接:fresh(2026-09-27 暂停时)

## 0. 在跑与已排:**无**
- pod2 与 Mac 上都没有我起的进程。我之前起的 master(PGID 3295973)已于 09-26 18:35Z 结束。
- 两个会话 cron(05:57Z / 06:41Z)已按暂停令取消,`CronList` 为空。
- 月度重训族与 `/dev/shm/mretrain_2026-09-26` 归 fresh2,我没有碰过。
- `~/shadow_ab` 不存在,即影子 A/B 没有安装。`~/shadow_ab_dryrun` 只是干跑产物(292 KB),可以删,收据已入库。

## 1. 前瞻影子 A/B —— 已设计、已冻结判据、**未安装**
- 设计 `docs/DESIGN_forward_shadow_ab_2026-09-27.md`(af77e86f5);判据(lead 冻结)`docs/DECISION_RULE_forward_shadow_ab_2026-09-27.md`(7f47461e6)。
- 装置 `multi_asset/exports/research/shadow_ab_2026-09-27/devices/`,SHA256SUMS 见 527c46e34。
  - 回放 `shadow_ab_replay.sh`:在役 `combo_parity_replay.sh` 7fa0881a 加 22 行差异,同一 sandbox-exec 隔离。
  - 沙箱副本 combo_stage 的挂钩 `ab_hook_block.py` 与 `shadow_ab_insert_hook.py`:插入点须唯一、18 个名字须用 AST 确认已绑定,否则 fail-closed。
  - 收集与恒等控制 `shadow_ab_collect.py`;纸面收益 `shadow_ab_pnl.py`;账本链检查 `shadow_ab_verify_ledger.py`。
  - launchd agent `shadow_ab_agent.sh` 与 `com.hsy.shadowab.plist`;配置模板 `config.sh.template`。
  - 读数装置 `shadow_ab_read.py`,三种模式 health / dispersion / final,先于任何读数入库。
  - 测试:`tests_shadow_ab.py` 18/18,`tests_shadow_ab_read.py` 4/4。
- 干跑(在役 combo_stage **12a76de8**,09-26 20Z 与 09-27 00Z 两锚):恒等控制 PASS(318 / 319 名逐位),臂状态接力 own,定价 48 行、0 未定价。收据 `receipts/dryrun_2026-09-27/`。

**安装前提(判据 §5)**:
1. GAP4(会更换 combo_stage)发布并通过首锚验收。GAP4 已推迟。
2. 对 GAP4 版 combo_stage:重新核对挂钩插入(`shadow_ab_insert_hook.py`,作用于副本),并做**一次两锚干跑**,写进新的 dry-run 目录。
   - 先用 GAP4 之前的两个快照:若 GAP4 不改变正常锚的输出,恒等控制应 PASS。
   - 不 PASS 就等 GAP4 自己产出的两个锚再干跑。
   - 只在 [N+1:00, N+3:40] 的 CPU 窗内跑,避开 M3 窗。
3. 干跑收据入库后交给 lead,由 lead 按设计 §6 的 7 步安装(START / END 锚写进 `config.sh`),并登记 registry。
4. **新电脑须知**:所有路径都写死在 `/Users/haosiyu/…`(plist、agent 的缺省值)。若新机的用户目录或 `~/wide_shadow`、`~/dl_quant_live` 位置不同,须先改 plist 与 `SHADOW_AB_HOME` / `WIDE_SHADOW_HOME` / `DL_QUANT_LIVE_ROOT`,再干跑。sandbox-exec 依赖 macOS。

**两条已知的量级事实(判据已经考虑)**:12 周的 MDE 约 7.9 bps/日(NOKING,σ 取自 R25-04 回撤期)。第 2 周只按离散度决定是否延长到 26 周。

## 2. G4 —— 中期版,终版待写
- `docs/RESULT_G4_why_fresh_underdelivers_2026-09-26.md`(中期版;最近一次追加是 a3845234d)。
- **终版依据(lead 裁定)**:King 根因的 3b 两个单条件格,加 King 改进族(KN / A1)的 IC 判词。两者都出来之后再写。
- 终版须吸收:
  - dlarch R1.4 REJECT(H-EP 不成立;F10 满窗在两段都为负);
  - EMA 通道 = 间隔规则的口径差(4e0e01862);
  - 月度重训族红控 FAIL(33abbad32,打乱 King 在 2026 反而 +4.29);
  - news2 按源普查(4aef8ef10):NEW_S / FRESH 两根全部是旧口径。

## 3. 其它已交付、可引用的(按时间)
| 事 | 提交 |
|---|---|
| 阶梯两端干净 RN8(G 约动 1%;只对 RN8 通道成立) | a44e62ac2 冻结,d7454281d 结果,838210c6a / 241be2200 更正 |
| EMA 通道归因 + NC EMA 为真值 | 3a01b0e91 冻结,4d3a26dad 结果 |
| 第二机制 = 间隔赋值规则(分叉) | a5ed7c60b 冻结,4e0e01862 结果,b34a4fcb6 六件更正 |
| 组合层三通道普查 | 28a6a2659 |
| G4 年龄检验(UNRESOLVED) | 91a8caf59 / cabacb68a 冻结,af37af9fa 结果 |
| 错题 E-0927-B(搬迁只改一个根常量 + 通知 8 小时未送达) | a839dc596 |

## 4. 给接手者的一条纪律
长跑任务的监督不要靠「后台任务完成通知」。要用定时唤醒去读执行进程自己的标记,并登记 registry(E-0926-J / E-0927-B)。

---
## 追加(2026-09-27 14:1xZ, fresh;lead 离线至 09-30,交独立研究员;上文原样保留)

### 在飞:**无**
- pod2 上我登记过的两项 `fresh_a1seat` 与 `fresh_a1seat_rerun` 都已用 `registry_edit.py` 关闭(a0ef5fa18 / 3bd3f5a92)。Mac 上没有我的进程;会话 cron 已清空。
- pod2 `/dev/shm/a1seat_2026-09-27` 与 `/workspace/a1seat_2026-09-27/mirror` 已删:删前逐文件对已入库的 PULL_SHA256SUMS 核过。`/workspace/a1seat_2026-09-27` 只剩 4 MB 现场(设备、LEAK_CLEARED、日志)。
- `~/shadow_ab_dryrun_arm64` 是干跑产物,不属于实验,可以删。

### 影子 A/B:待命(发布冻结中)
- **arm64 新机复验**(203d77cd2),针对在役 combo_stage 12a76de8:
  - 测试 18/18、读数装置 4/4,两个解释器都跑过;
  - 20Z / 00Z 两锚干跑,恒等控制 PASS;每锚 14/15 个存档文件与旧 Intel 机逐位相同;
  - agent 路径在 launchd 同款环境下跑通;新机路径不用改。
- **安装顺序**:GAP4 → M3 on → 影子 A/B,各占一个静默窗 [N+1:00, N+3:40],都在 16Z 首锚验收之后。按 HANDOFF_independent_researcher §7-6,开窗前须得到用户同意。
- **GAP4 会换 combo_stage**,所以装之前须:
  1. 对新版重跑 `shadow_ab_insert_hook.py`(作用于副本);
  2. 两锚干跑,写进新的干跑目录,只在静默窗内跑;
  3. 收据入库;
  4. 按设计 §6 的 7 步安装(START / END 锚写进 config.sh,用 `registry_edit.py` 登记)。
- 判据 7f47461e6 在换版后须由 lead 重新冻结(判据 §4 / 设计 §7)。

### G4:终版已出,并有四条追加
- 终版 `docs/RESULT_G4_why_fresh_underdelivers_2026-09-27.md`(bf503aa66)。四条追加依次是:
  - 泄漏审计(见 git log);
  - 撤回 L4c 保留,并撤回我自己 §3.5 的推理(318fb6fd8);
  - A1 席位拆分判词(239bace3d);
  - 勘误(e21763567)。
- **A1 席位/构成拆分**:
  - 判据 b41ac9985 + 修订 1 552475325;读数 dd68068dc;判词(lead)c381924f2。
  - pre-2026「未被支持」:构成通道 −2.08 扛了大部分,其中多付资金费 +0.85;席位 −1.01。
  - 2026「不可判」:交互项 1.20,FULL 为 1.23。
  - ⇒ G4 §3.3「经席位」在 A1 上未被支持,原因改为「机理未定」。
- **仍然有效的限定**:单成员;A1 的 IC 判词 FAIL(2026 年 16.9,门槛 20);L5 年龄混淆,以及「数据更新」与「数据更多」分不开。

### 给接手者的两条(本轮自犯,已在上面修正)
- 驱动的 mirror() 用了 `cp … 2>/dev/null; true`:不回读比对 sha,还会吞掉错误;而且它排在最后一行 DONE 之前执行。补救办法是终态后逐文件比 sha。以后的驱动应把「写 → 回读比对」放进镜像步骤本身。
- 等待循环第一版把 ssh 失败读成「PGID 已死」(空输出当 0),已换成把工具失败与作业状态分开判断的版本。
