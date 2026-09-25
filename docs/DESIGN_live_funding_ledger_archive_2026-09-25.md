> **创建:** 2026-09-25 | **Session:** news2 / b9646a9e | **状态:** **设计稿, 交 lead 复核, 未部署**(lead: 部署等发布窗结束后再定) | **Owner:** news2 | **作废条件:** lead 否决; 或 `shadow_loop_v3.py` 改变 `ledger_tail` 的写法/保留长度; 或活账本改为落盘历史全量(届时本作业无必要)

# 设计: 只读的活账本归档作业(`funding_ledger_archive`)

## 0. 它要堵的盲区, 以及为什么两个月是硬上限

实测(2026-09-25): 在役活账本 `~/wide_shadow/state/aux.json` 的 `ledger_tail` 是**滚动 400 行/名**(`shadow_loop_v3.py:421`)。因为 2026 年很多名已在 1h/4h 间隔上, **400 行只有 17–67 天**, 不是我原先估的 133 天:

| 来源 | 最早一行(中位) | 覆盖 |
|---|---|---|
| 当前 `aux.json`(09-25) | 2026-07-21 | ~2 个月 |
| 唯一历史快照 `aux_pre_m1_20260904.json`(09-04) | 2026-07-07 | ~2 个月 |

⇒ **「在役账本当时有没有漏尖峰期的 1h 结算」对 2026-01..06 永久无法从留存状态回答**, 而且**窗口对尖峰活跃的名字最短** —— 与最需要审计的名字反向。这不是找不到, 是没有留存。

**本作业的唯一目的**: 每天把活账本的 `ledger_tail` 抄一份去重追加, 使**两个月之后任何一段历史都能对归档做切换窗审计**(与 `d10_live_ledger_vs_archive.py` 同一台仪器)。

## 1. 边界(不可违反)

- **只读实盘**: 只 `open(..., "rb"/"r")` 读 `~/wide_shadow/state/aux.json`。**不写、不移动、不删除 `~/wide_shadow` 下任何东西**, 不碰执行器, 不调交易所。
- **只写自己的目录**: `~/funding_ledger_archive/`。**不在 `~/Desktop` 下** —— 在案 `launchd_cannot_enumerate_icloud_desktop_repo_2026_09_16`: launchd 对 iCloud 桌面有 TCC 墙, **能 `stat` 不能枚举**, `glob` 吞错返回 `[]`, 结果公证链 16 天每份自称创建成功而实际为空。放 Desktop 之外是为了不重演这件事。
- **静默窗内运行**: 第一条命令调 `venue_quiet_window.py`, 把 `now/open/remaining_min/reason` 四个值写进该次运行的收据; 不在窗内**非零退出**, 不硬撑。门在证据可读的机器上判(Mac 能读执行器锚日志), 见 `common/README_venue_quiet_window.md`。

## 2. 数据契约

**输入**: `aux.json` 的 `ledger_tail`, 形状 `{symbol: [[ft_seconds, rate, iv], ...]}`(实测 09-25: 683 名, 每名 108–400 行)。

**去重键**: `(symbol, funding_time)`。**同键冲突的处理必须显式**: 若归档已有该键且 `rate`/`iv` 与新读到的不同 ⇒ **两份都留**, 记入 `conflicts.jsonl`(带两份取值与各自首见时间), **不静默覆盖也不静默丢弃**。生产者理论上不会改写既往结算, 所以冲突数应恒为 0; **它不是 0 就是一个发现**, 这正是要它可见的理由。

**归档格式**: 逐月分片 `~/funding_ledger_archive/YYYY-MM.jsonl`, 一行一事件 `{"s":symbol,"ft":int,"rate":float,"iv":float,"first_seen_utc":...}`。选 jsonl 而非 npz: 追加不需要重写整文件, 单行损坏不毁全月, 且可用 `wc -l` 廉价核对。
每月分片旁写 `YYYY-MM.sha256`(内容 sha), 以及全局 `MANIFEST.json`(逐月行数 + sha + 最后更新时间)。

## 3. 写入纪律(三条, 都来自在案错题)

1. **`write → fsync → 回读比对 → 由回读返回 sha`**。不允许「写完再独立重读文件算 sha」—— 在案 `receipt_sha_must_come_from_the_verified_write_2026_09_25`(E-0925-A)。
2. **禁用 `json.dump(x, open(p,"w"))` 这个写法** —— 磁盘满时它吞掉错误(在案 `disk_full_swallowed_by_json_dump_open_idiom_2026_09_25`)。一律 `with open(...) as f: ...; f.flush(); os.fsync(f.fileno())`, 追加用 `"a"` 且每次追加后 fsync。
3. **原子性依赖上游**: 生产者用 `atomic_json`(`os.replace`)写 `aux.json`, 所以读者只会拿到完整的旧版或新版, 不会读到撕裂的半份。**本作业仍要 `json.load` 成功才算读到** —— 解析失败 ⇒ 本次跳过并记 `READ_FAILED`, 不写任何东西, 下次再来(`ledger_tail` 有两个月冗余, 跳一次无损)。

## 4. 启动自检(必须能「列举」, 不是 `stat`)

按 `launchd_cannot_enumerate_icloud_desktop_repo_2026_09_16` 的教训, 自检的第一步是**枚举**:

```python
entries = os.listdir(ARCHIVE_DIR)          # 必须真的列出来, 不是 os.path.exists / os.stat
assert entries is not None
n_shards = len([e for e in entries if e.endswith(".jsonl")])
# 若目录不可枚举(TCC / 权限 / 路径错), listdir 会抛; 抛就退出非零, 绝不当成「目录是空的」
```

**判别线**: 「枚举抛异常」与「枚举返回空」必须走不同分支。返回空只在**首次运行**是合法的, 之后返回空 ⇒ 视为异常(归档不该凭空变空), 非零退出并具名告警。

自检还要断言: 归档目录**不在** `~/Desktop` 之下(路径字符串检查 + `realpath`), 且**不在** `~/wide_shadow` 之下(防止将来有人把它指到实盘目录里)。

## 5. 存活检查(挂到每锚验收, 与前向日志新鲜度同形)

**为什么要外部检查**: 在案 `silent_watcher_death` / `pod_quota_kills_jobs_silently_monitors_time_out` —— 一个自己报自己活着的作业, 死了就不报了。

**形状**(与集成代理的前向日志新鲜度同一形状): 每锚验收读 `MANIFEST.json` 的 `last_update_utc`, 与阈值比较。

**阈值必须从数据导出, 不能拍**: 允许的最长空窗 = **最短的那个名字的 `ledger_tail` 覆盖时长**, 因为超过它就开始真丢事件。实测最短 = 177 行 @ 1h ≈ **7.4 天**。所以:
- **告警阈值 3 天**(留 2× 余量);
- **硬失败阈值 7 天**(超过即确定开始丢事件)。
两个阈值都由自检**每次从当次读到的 `ledger_tail` 重算并写进收据**, 不写死常数 —— 若将来间隔普遍变短, 阈值自动收紧。

**必须区分「没跑」与「跑了但没写」**(在案 `new_mandatory_step_breaks_the_paths_early_exits`: 给恢复路径加必须步骤会让所有合法早退分支变成新的失败模式):
| 状态 | 含义 | 验收动作 |
|---|---|---|
| `SKIPPED_WINDOW_CLOSED` | 静默窗没开, 合法早退 | **不告警**, 但计入连续跳过次数 |
| `READ_FAILED` | `aux.json` 解析失败 | 记录; 连续 2 次以上告警 |
| `OK` + 0 新事件 | 跑了, 确实没有新结算 | **不告警**(夜间低活跃期合法) |
| 无本次记录 | 作业根本没启动 | **告警** —— 这是与上面三者都不同的一类 |
连续 `SKIPPED_WINDOW_CLOSED` 超过 3 天也要告警: 窗口不可能连关三天, 那说明门坏了而不是窗关着。

## 6. 逐次收据

`~/funding_ledger_archive/runs/RUN_<utc>.json`, 字段: 窗口四值 · `aux.json` 的 sha256 与 mtime · 读到的名数/行数 · 新增事件数 · 逐月分片的行数与回读 sha · `conflicts` 计数 · 自检枚举结果 · 两个导出的阈值 · 状态码。**收据里的每个 sha 都来自回读**, 不是事后独立重算。

## 7. 部署方式(**lead 2026-09-25 已裁定; 我的倾向被否, 理由我接受**)

**裁定**: **用独立的 launchd 用户级作业**, 形状同 `com.hsy.onsetfwd_short`(已实测按点自跑, 且其自检绑住消费者)。**存活检查挂在集成代理的每锚验收上。**

**我原先倾向「挂在集成代理已有的每锚链上做唯一执行者」, lead 否掉了, 理由逐字**:

> 集成代理的每锚验收由会话驱动, 会话结束它就停了, 不能做唯一的执行者。

**这个理由纠正了我的想法, 记下来**: 我当时的考虑是「少一个会静默死掉的独立作业」, 但我把**执行**与**监督**混成了一件事。正确的分工是 —— **执行要交给一个不依赖会话存在的东西(launchd), 监督交给一个会被人看的东西(每锚验收)**。把执行挂在会话驱动的链上, 不是减少了静默死亡点, 而是把执行本身变成了会话的函数: 没有会话的那些天它根本不跑, 而且不跑得无声无息。同族: [[silent_watcher_death]]。

**照抄 `com.hsy.onsetfwd_short` 的形状与它的两个关键细节**:

```xml
<key>ProgramArguments</key><array>
  <string>/usr/bin/python3</string><string>-B</string>
  <string>/Users/haosiyu/funding_ledger_archive/archive_live_ledger.py</string></array>
<key>WorkingDirectory</key><string>/Users/haosiyu/funding_ledger_archive</string>
<!-- 目标 09:30Z(在 08:00Z 锚的静默窗 09:00-11:40Z 内)。
     launchd 按 LOCAL 时间排程, 本机 +08 且无 DST ⇒ Hour 写 17 不是 9。 -->
<key>StartCalendarInterval</key><dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>30</integer></dict>
<key>RunAtLoad</key><false/>
<key>StandardOutPath</key><string>/Users/haosiyu/funding_ledger_archive/launchd.log</string>
<key>StandardErrorPath</key><string>/Users/haosiyu/funding_ledger_archive/launchd.err</string>
```
1. **`StartCalendarInterval` 是本地时间** —— 那份在案 plist 自己写了注释提醒(`07:22Z == 15:22 local`), 我照抄这个注释习惯, 把 UTC 目标与本地 Hour 同时写在 plist 里, 免得以后有人按 UTC 读它;
2. **`RunAtLoad` 为 false** —— 加载时不跑, 避免在非静默窗被一次 `launchctl load` 触发。

**launchd 触发 ≠ 窗口开着**: 固定本地时间只保证「大致在窗内」, 不保证守卫的条件 ②(上一锚已 done)成立。所以**脚本第一件事仍然调 `venue_quiet_window.py`**, 不在窗内就 `SKIPPED_WINDOW_CLOSED` 退出。两道都要。

**部署前必须实测一次的一项**(不能假定): launchd 下的进程能否**枚举** `~/wide_shadow/state/`。在案 `launchd_cannot_enumerate_icloud_desktop_repo_2026_09_16` 是 `~/Desktop` 的 TCC 墙; `~/wide_shadow` 不在 Desktop 下, 但**「不在 Desktop 下」不等于「launchd 能枚举」**, 必须在 launchd 上下文里真跑一次 `os.listdir` 并把结果写进收据。

## 7b. 部署前要交的控制(lead: 先交红控与正控的收据)

**正控制**(证明它真的在做该做的事):
- 跑一次后, 归档必须等于 `(跑前归档) ∪ (aux 的 ledger_tail)` 按 `(symbol, funding_time)` 去重的结果 —— 逐键比对, 不是只比计数;
- 每个被改动的月分片的 sha **由回读返回**, 并与 `MANIFEST.json` 里记的一致。

**红控制**(每条都必须能让它失败; 不能失败的控制不算控制):
| 控制 | 注入 | 必须的行为 |
|---|---|---|
| R1 不可枚举的目录 | 把归档目录指到一个不可 `listdir` 的路径 | **非零退出**; 绝不能报「目录是空的」然后当成首跑 |
| R2 幂等 | 对同一份 `aux.json` **连跑两次** | 第二次新增事件数 **恰好 0** |
| R3 同键冲突 | 手工把归档里某键的 `rate` 改一位 | 该键进 `conflicts.jsonl`, 归档**两份都留**, 不覆盖 |
| R4 窗口关闭 | 在非静默窗跑 | `SKIPPED_WINDOW_CLOSED`, **一个字节都不写** |
| R5 分片损坏 | 改掉某月分片的一行 | 下次启动自检按 sha **报红**, 不静默继续 |
| R6 非首跑空归档 | 清空归档目录后再跑 | **报红**(归档不该凭空变空), 不当成首跑 |
| R7 路径越界 | 把归档目录指到 `~/Desktop/...` 或 `~/wide_shadow/...` | 自检**拒绝启动** |

R2 与 R6 是一对: 一个证明「重复输入不会重复写」, 一个证明「输出消失会被发现」。**每条红控都要留一份失败时的收据**, 而不是只留通过时的。

**排期**: lead 裁定部署等**今天发布完成 + B7 两个锚之后**再排; 届时我按本设计实现并**先交 7b 的收据**, 再谈加载 plist。

## 8. 两个月后能做什么

归档积累两个月后, 对任意历史段可跑 `d10_live_ledger_vs_archive.py`(已在库, 本次 2026-08 用的就是它): 取交易所归档的间隔切换事件 ±24h, 逐事件比对活账本归档, 报缺失数/逐名/其中在当时书成员内的格数。**届时「在役当时有没有漏 1h 结算」就是一个可测问题, 而不是只能靠机制论证。**

## 9. 相关
- 装置: `news2_2026-09-23/devices/d10_live_ledger_vs_archive.py`(审计仪器, 已在库)
- 收据: `D10_LIVE_LEDGER_VS_ARCHIVE_2026-08.json`(2026-08 切换窗 305/305 零缺失)
- 注记: `common/README_venue_quiet_window.md`(门在证据可读的机器上判)
- 记忆: `launchd_cannot_enumerate_icloud_desktop_repo_2026_09_16` · `receipt_sha_must_come_from_the_verified_write_2026_09_25` · `disk_full_swallowed_by_json_dump_open_idiom_2026_09_25` · `new_mandatory_step_breaks_the_paths_early_exits`
