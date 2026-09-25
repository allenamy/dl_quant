> **创建:** 2026-09-25 | **Session:** news2 / b9646a9e | **状态:** 现行注记(lead 2026-09-25 要求落在 `venue_quiet_window.py` 旁) | **作废条件:** `venue_quiet_window.py` 的锚日志路径或开放条件改变; 或团队改用别的窗口守卫

# `venue_quiet_window.py` 使用注记: 两个会咬人的地方

两条都是 2026-09-25 实测踩到的, 不是理论。守卫本身没有缺陷 —— 两条都是**用法**与**部署位置**的问题。

---

## 一、守卫在 pod2 上**永久返回关闭**, 而这是它正确

**实测**(同一时刻, N+65m, 本该开放):

| 机器 | 退出码 | `open` | `reason` |
|---|---|---|---|
| Mac | **0** | `true` | `open` |
| pod2 | **3** | `false` | `anchor log unreadable (FileNotFoundError) — unknown is not open` |

**原因**: 守卫的开放条件 ②③ 要读执行器的锚日志 `~/dl_quant_live/state/anchor_runs.log`。**那个文件在 Mac 上, pod2 上不存在**(`/root/dl_quant_live/state/anchor_runs.log: No such file or directory`)。守卫按自己写明的契约「**未知不是开放**」拒绝。

**危险不在守卫, 在顺手的修法**: 把守卫塞进 pod2 侧脚本会得到永久 closed, 然后很自然地去设 `VENUE_QUIET_WINDOW_OVERRIDE=<理由>` 绕过 —— **那一下就把所有 pod2 侧工作的窗口门整体关掉了**, 而且从收据上看像是「配置了一下」, 不像「门被拆了」。

**正确架构**: **门在它的证据可读的那台机器上判, 远端工作从那台机器驱动。**
- 判据端 = Mac(能读锚日志), 每个工作单元开跑前**重测一次**;
- 执行端 = pod2, 由 Mac 侧 `ssh` 逐单元调起。

实现参考: `news2_2026-09-23/devices/d10_pull_driver_mac.sh`(逐月重测窗口, 然后 ssh 到 pod2 跑那一个月; `remaining_min` 不足就停, 不硬撑)。

**不要**把 `open` 的判断写进叙述而不写进收据: 每次重测把 `now_utc / open / remaining_min / reason` 四个值落进该次动作的收据。我 2026-09-25 就因为按经过时间**推**了一句「现在已进入静默窗」, 而实测时钟还差 4 分钟 —— 没有造成实际越窗, 但发出的陈述是假的。

---

## 二、本地 `kill` 掉 ssh 驱动, **远端命令仍在跑**

`ssh host 'long_command'` 不分配 pty。本地把驱动进程 TERM 掉之后, **远端的 `long_command` 不会收到信号, 继续执行**。

2026-09-25 实测: TERM 掉 Mac 侧驱动 → 远端 puller 仍活着(PID 3080108 / 3080109), 直到我登上去按 PID 处置。

**后果**: 你以为停了, 于是改了输入 / 换了设计 / 报告「已停止」, 而远端还在写它的产物。这在共享主机上还会继续占别人的配额与请求速率。

**处置方式**(照团队纪律):
1. 停远端要**杀远端 PID**, 不是杀本地父进程;
2. **只按自己记录的 PID/PGID**, 禁止按名字 `pgrep`/扫杀(在案自伤: `pattern_kill_on_shared_host_killed_production_stage_2026_09_17`);
3. 发信号前**逐个核对该 PID 的命令行确实是自己的装置路径**。我 2026-09-25 就靠这一条拒绝了对一个 `bash -c` 包装发信号(命令行不匹配), 由它随子进程自然退出;
4. 更好的做法是**让远端自己可归属**: 远端脚本第一件事把自己的 PGID 写进一个文件, 这样无论被队列还是被手工 `ssh` 启动, 都不会出现「某个组无法归属」。参考 `ladder_engine_arm.sh` 开头那几行。

---

## 三、顺带: `data.binance.vision` 不需要这个守卫, 但仍受「本机重活只在静默窗」约束

守卫自己的 docstring 写明: **公开归档下载不走 fapi 权重, 不需要本守卫。** 但那是**场所权重**的事; 一个跨数小时的批量拉取仍然是本机/共享主机的重活, 因此**仍受 lead 的「本机重活只在静默窗 `[N+1:00, N+3:40]`」规则约束**。两条规则管的是两件不同的东西, 不要用前者豁免后者。

---

## 相关
- 装置: `venue_quiet_window.py`, 测试 `tests_venue_quiet_window.py`
- 记忆: `re_measure_a_blocker_before_reporting_it_2026_09_25`(含 2026-09-25 追加的镜像方向: 报「门已经开了」同样要在发出那一刻重测)
- 记忆: `pattern_kill_on_shared_host_killed_production_stage_2026_09_17`
