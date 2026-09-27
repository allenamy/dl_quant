> **创建:** 2026-09-27(`date -u` 11:36:55Z 定稿) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(alloc,受 lead 派) | **状态:** 操作手册草稿·通用版(**只是给操作人的流程,不改执行器代码,不设任何判据**;以 integ `PLAN_recovery_after_double_executor_2026-09-27.md` §7、§8 为第一版底本) | **作废条件:** 执行器的 halt / 恢复语义或 `ops/resume_from_trip.sh` 的接口改变;或 09-30 08:47Z 之后的协议化版本取代本文

# 手册(通用版):看门狗跳闸之后,怎样判断、取证、恢复

**⚠ 地位**:这是分析与流程,**不是协议 v2 草稿**(§9-F7,冷静期到 2026-09-30 08:47Z)。
- 文中的「目标时限」是给操作人的**建议**,不是判据。
- 任何判据、预注册或代码改动,都在冷静期之后按流程起草(lead 09-27 裁定)。
- 机制出处:`docs/DESIGN_post_flatten_halt_2026-09-27.md` §1(只读 d01e35d 克隆)。

## 0. 先认清你面对的是哪一种停机(第一件事,只读)

读 `~/dl_quant_live/state/live/watchdog/state.json`,只读,不要编辑,也不要删除:

| 字段 | 取值 | 含义 |
|---|---|---|
| `kind` 缺省或为 trip,且 `book_flattened: true` | **(A) 整书已平** | 书是空的;代价是空仓期间的期望收益(量级约 1.3 bps NAV / 锚) |
| `kind: proportional_local` | **(B) 局部响应,书仍持有** | **优先级更高**:书被冻住,普通减仓也被拦,只剩 staleness 梯子与宇宙出场能减仓 |
| 文件读不出,或模式戳不符 | **(C) fail-closed** | 执行器按「已跳闸」处理。**修文件,不要删文件**;交 lead |
| `_seeded_by_rehearsal` | 演练植入 | 用 `ops/unseed_rehearsal_halt.py`,**不要用** resume 脚本 |
| 存在 `state/KILL_SWITCH.json` | 急停 | 连出场都拒。不在本手册范围;按 `ops/KILL.sh` 的说明 |

**再判原因类别**,依据 `trip_receipt.json` 的触发原文与 `ALARM.log`:

| 类 | 例 | 恢复之前**必须**先做的 |
|---|---|---|
| R1 真实风险触发 | 09-06 §4-2 单日止损 | 冷静期规则照常;恢复当天全天冻结合约钱包划转(§4-2 划转缺陷,按未修处理) |
| R2 我方仪器假阳性 | E-0909-G 账本缺行、E-0912-A reduce-only 截量、I6 非计划运行 | 先写一句成因,并附证据行号;不要在没弄清之前「跑到绿」 |
| R3 外来执行者 | 09-27 双执行器 | **轮换密钥**,并通过场所核验 Q1–Q4(integ §3、§7 第 1–4 步),两者都做完才谈恢复 |
| R4 未知 | 看不懂触发原文 | 交 lead;不恢复 |

## 1. 取证(任何恢复动作之前;不改状态)

1. 用 `ops/capture_halt_evidence.py` 取停机锚的四项证据:action、已经上场的开仓单数(应为 0)、blocked_by_halt 行数(应 > 0,和上一项成对才有意义)、reduce-only 可达性(书为空时如实写 NOT_OBSERVABLE)。
2. 复制 `state/live/watchdog/{state.json, trip_receipt.json, events.jsonl}` 与当日的 `pilot_log/<YYYYMMDD>/` 作证据。只拷贝,不移动。
3. **归因只用身份**,也就是订单或成交 id,不用「事件 ± 常数」的时间窗(记忆 `event_window_attribution_misses_flatten_start`)。
4. 读成交表时,走属主的读取函数(`pilot_log.read_fills`,已经 collapse_supersedes)。盲态纪律照旧:只报合池。

## 2. 判能否恢复(只读、隔离)

1. 在**隔离克隆**上跑 `LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check`:克隆 = 运行树 + state 的完整拷贝,沙箱禁网、生产目录不可读;integ 的 `recheck_clone.sh` 与 `offline_clone.sb` 可以直接复用。
   - ⚠ `--check` 是唯一的预览方式,**不认识的旗标会被拒绝**。不要用 `--dry-run` 之类,它们不是预览。
   - ⚠ 必须带 `LIVE_MODE=LIVE`,否则默认 DRY_RUN,会被拒绝并点名 LIVE。
   - 期望:`RESUMABLE`,tripped 为 False,没有 blind,5b 与 5e 都是 CLEAN。
2. **门看不到的前提**,由人确认:
   - 只有一台机器在跑执行器。R3 类必须有密钥轮换和 Q1–Q4 的收据。
   - 恢复当天全天冻结合约钱包划转。
   - `git status` 认领研究仓里的非预期改动(iCloud 同步的机器可能写入)。
3. **用户字**:以原参数恢复。原因写成一句话,里面含证据与时刻。

## 3. 执行恢复

```
cd ~/dl_quant_live && LIVE_MODE=LIVE bash ops/resume_from_trip.sh "<一句话原因:类别 + 证据 + 时刻>"
```

- 期望依次出现 1/4 到 4/4 的 ✓,最后一行 `✓ resumed`,rc 0。
- (A) 类会删除 harvest_ema.json,下一锚从原始目标开始重建;(B) 类保留 EMA 记忆。
- **任何一步 ✗,脚本会自己拒绝,不改状态 ⇒ 交 lead,不要改参数重跑到绿。**
- 执行时刻不要落在 N+24 到 N+30,即执行器下单的窗口。

## 4. 恢复后的首锚与第二锚

- 首锚:标准首锚验收,即 lead 那一套 inspect_anchor、VERSION_PROBE 等。另加:
  - `blocked_by_halt` 行 = 0;
  - watchdog 没有再次跳闸;
  - (A) 类的建仓到位率 ≥ 0.60(参照 0.62–0.97);
  - R3 类用 integ 的 `venue_readonly.py anchor` 核对外来 orderId = 0。
- 第二锚:(A) 类的到位率 ≥ 0.95(参照三次历史 ≥ 0.98)。
- 成本只作描述:参照 5.1–12.4 bps(integ §2)。

## 5. 目标时限(建议,给操作人;**不是判据**)

以跳闸时刻 T 与跳闸所在的锚 N 计:

| 阶段 | (A) 整书已平 | (B) 书仍持有 |
|---|---|---|
| 页报被人确认 | 当个静默窗之内(N+3:40 之前) | 同左 |
| 判出类别 R1–R4 | 下一锚之前(N+4h) | **同一个静默窗之内** |
| 恢复或不恢复的决定(含用户字) | R1 / R2:2 个锚之内;R3:密钥轮换与 Q1–Q4 做完之后;R4:交 lead | R1 / R2:**1 个锚之内**;否则明确选择「保持冻结」或「人工整书平仓」,不能默认拖着 |
| 超过目标时限 | 再次页报,在页报里写明「已超过建议时限 X 锚,理由 …」 | 同左 |

- **理由**:按 `DESIGN_post_flatten_halt` §2 的量级,(A) 类每停一个锚,期望只损失约 1.3 bps NAV,所以时限可以宽一些,**宁可弄清原因再恢复**。
- (B) 类的书在冻结期间持续偏离目标,而且减仓也被拦,所以要尽快作出明确选择。
- 这些时限在冷静期之后是否写入协议,由 lead 决定。

## 6. 本手册不做的事(明确排除)

- 不改执行器代码:reduce_only 的标注、halt 的语义、自动恢复,都不在本手册里。
- 候选 H1(自动恢复)已挂起,等 integ 的 §4a(迁机轮换密钥)与 §4b(锚前外来活动预检)落地。
- 候选 H3((B) 类允许朝目标减仓)是代码改动,冷静期之后按预注册处理。
