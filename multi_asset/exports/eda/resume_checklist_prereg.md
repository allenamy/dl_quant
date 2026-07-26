> **创建:** 2026-07-26 03:30Z (**在清除动作发生之前**) | **Session:** ma-v2 0C 独立审计 | **状态:** final (预注册, 清除后只填结果不改判据) | **作废条件:** 若清除在 04:30Z 后仍未执行, 重新核对 §0 的两条阻塞项是否仍成立

# resume 复核单 (预注册)

**角色分离 (team-lead 定):** 判据由 0C 定 · 执行由 team-lead 做 · 复核由 0C 做。**同一张单子, 两个人两个角色。** 本文件在清除发生**之前**定稿; 清除之后只允许填"实际观测", **不允许改判据**。

**resume 的总判据 (沿用本项目已定规则):** trip 的成因是**我方自身缺陷** (2× 敞口 + 取整方向), 不是外部状态 ⇒ **恢复条件 = 代码版本变更 + 该版本自己写出的、对真实数据的证据**。外部故障才用"外部状态改变"来解锁。

---

## §0 ★★ 两条阻塞项 —— 在按下清除之前必须先处置 (0C 03:2xZ 实测)

**这两条不是清单项, 是前提。若未处置, 下面 12 项无一可判。**

### 0-1 `ops/resume_from_trip.sh` 操作的是 **DRY_RUN 树**, 不是 trip 所在的 testnet 树

```
脚本第 26 行  STATE = $REPO/state/watchdog/state.json          ← DRY_RUN 树
脚本第 35 行  root  = $REPO/state/pilot_log                    ← DRY_RUN 树
真实 trip 在  state/testnet/watchdog/state.json  +  state/testnet/pilot_log/
```

**实测后果 (两个方向都错):**

| | 实测 |
|---|---|
| 硬门读 DRY_RUN 树 | `WD.run("state/pilot_log")` ⇒ **`tripped=False`** ⇒ **门放行** |
| 硬门读 testnet 树 | `WD.run("state/testnet/pilot_log")` ⇒ **`tripped=True`, `§4-5b … 47 name-anchors`** ⇒ 应拒绝 |
| 第 3 步删除的文件 | `state/watchdog/state.json`, 其 `tripped_at = None` —— **本来就没触发** |
| 真实 trip 文件 | `state/testnet/watchdog/state.json` (`tripped_at 2026-07-26T00:17:11Z`) —— **不会被动到** |

**⇒ 照现状执行, 脚本会: 通过一道空洞的门 → 隔离并删除一个未触发的文件 → 打印成功 —— 而系统仍然停着。** 这正是本项目已命名的形态: **诚实的数字指着一个不存在的对象**, 且比沉默更有说服力。

> **注: `state_root.py` 存在的全部理由就是把两棵树分开, 而这个脚本硬编码了路径没有用它。我自己今晚也踩过同一棵树的错 —— 所以这不是苛责, 是同一个坑的第二次踩中。**

### 0-2 即使路径修对, 硬门仍会 (正确地) 拒绝 —— §4-5b 至今仍然为真

`watchdog.evaluate` 的取数窗是 `PL.available_days(root)` = **磁盘上全部日期**。20260725/26 的 `position_readback` 行仍然记录着"实际持仓 = 下单量的 2 倍"⇒ **那 47 条异常不会因为代码修好而消失**, 它们是**历史事实的记录**。

- `12fe914` (2× 补单) 与 `e8039d9` (取整方向) 改的是**将来**的行为, 不是历史行数;
- 符号修复 (若落地) 只会把 16 条 `frac=1.0` 变成 `0.5`, **仍然 > 0.10 阈值** ⇒ 47 条一条不少。

**⇒ 结论: 在"日窗仍含 07-25/26"的前提下, 一道判据正确的硬门将永远拒绝恢复。⇒ 这不是 bug, 是判据与数据窗的交互, 必须由 team-lead 明确裁定走哪条路 (我不裁定, 只列出可判定的选项与各自代价):**

| 选项 | 代价 / 它把"恢复"证明成了什么 |
|---|---|
| **A. 把 07-25/26 的 testnet pilot_log 行隔离归档** | 与脚本对 `state.json` 的做法同构 (隔离不删除)。**但这会让 §2.5 的窗口失去这两天的执行记录**, 且下次谁读 `available_days` 都看不到它们 |
| **B. 给 watchdog 引入 resume epoch (只评估恢复标记之后的行)** | 判据从此带一个"起算点"。**我自己的规则说: 需要 epoch 通常意味着判据没被写进数据** —— 但 5b 的判据本质上是历史比对, 这里 epoch 是**正当**的 (旧行记录的是**已修复的缺陷**, 不是当前行为) |
| **C. 不清除, 让 08:00Z 首考在 reduce-only 下跑** | **零动作、零风险、零口径改动。** 代价: 首考只认证"止损跨进程持续生效", 不认证交易路径 —— 而这正是 `book.json` 第 4/7 条已经预先写下的处置 |

**⇒ 我的建议 (未经裁定): C。** 理由: A 和 B 都在**清除的当天改动判定口径**, 而口径改动与被判定的事件同日发生, 正是本项目反复拒绝的形状; C 什么都不改, 且已有预先写好的处置条款覆盖它。

---

## §1 清除**之前**必须成立 (前置条件, 逐条可判)

| # | 判据 | 数据源 | 通过条件 |
|---|---|---|---|
| 1-1 | 代码版本变更存在 | `git log` | `12fe914` (2026-07-26T00:30:16Z) + `e8039d9` (00:34:56Z) 均在 HEAD 祖先中 |
| 1-2 | **符号修复的处置已明确** | `live/watchdog.py:471-474` | **二选一, 必须写明走哪个**: (i) 已修复 ⇒ commit id 记入; (ii) **未修复 ⇒ 必须预注册"恢复后 5b 会在每个成交卖单名字上再次触发, 且那不是 2× 未修好的证据"** —— 否则下一次触发会被误读 |
| 1-3 | 该版本对真实数据的重放证据 | maker-leg 重放 85.9% + `oracle_5b_sign.py` 对账 | 重放报告存在且署明所用 commit; oracle `n=47` 对账一致 |
| 1-4 | **重放证据由修复后的版本产出** | 重放报告的时间戳 vs `12fe914`/`e8039d9` 的 commit 时刻 | **报告时刻晚于两个 commit** —— 否则是"用旧版本的证据为新版本背书"(第十形态) |
| 1-5 | 04:00Z halt 四项证据齐全 | **主要读 `state/testnet/pilot_log/<day>/orders.jsonl`, 不是 run log** (见下方 ★) | `action` 字段存在(phase_A) · **开仓单数 = 0** (全部开仓行 `terminal_reason == "blocked_by_halt"` 且 `submit_ts is None`) · phase_A 出现 `watchdog_halt` 块 · reduce-only 路径可达(有 reduce-only 单, 或明确记录无仓可减) |
| **1-5b** | **halt 重新施加**没有走失败分支 | `state/anchor_runs.log` 04:00Z 锚点 | **不出现** `could not re-apply the persisted watchdog halt` 这条 CRITICAL。**若出现 ⇒ 系统处于"已 trip 但未 halt"** —— 比 trip 本身更糟, 且它会让 1-5 的四项证据同时消失, 两者不可混为一谈 |
| 1-6 | §0-1 已处置 | `ops/resume_from_trip.sh` | 脚本指向 testnet 树 (或改用 `state_root` 绑定), **且改动本身有 commit** |
| 1-7 | §0-2 已裁定 | team-lead 明确选择 A/B/C | 裁定落在文字里, 含"它把恢复证明成了什么"这一句 |

> **★ 1-5 的读数口径修正 (0C 03:3xZ 实测, 写在使用之前):** `watchdog_halt` / `order_blocked_by_halt` / `halt_source` 三个词在 `anchor_runs.log` 的 **183 个锚点里出现 0 次**。原因不是日志缺陷 —— 而是**trip 之后一个 TESTNET 锚点都还没跑过** (两个 testnet 锚点在 21:51Z 与 00:00Z, trip 在 00:17Z; 其后全是手动 DRY_RUN 调用, 而 DRY_RUN 树未触发)。
> **⇒ 于是 04:00Z 将是 `anchor_loop.py:202-245`「从文件重新施加持久化 halt」这条路径的**史上第一次执行**。** launchd plist 里 `LIVE_MODE=TESTNET`, 所以计划内锚点会绑 testnet 树、读到已 trip 的 state。
> **⇒ 第一次执行的安全路径, 正是今晚所有缺陷的产地。所以 1-5b 是独立一条, 不并进 1-5。**
> **⇒ 并且这一条反过来加强 §0-1**: 计划内锚点在**各种意义上**都以 testnet 树为准, 而 `resume_from_trip.sh` 硬编码的是 DRY_RUN 树。

## §2 清除**过程**必须成立

| # | 判据 | 通过条件 |
|---|---|---|
| 2-1 | 走硬门, 不是手动 `rm` | 命令为 `bash ops/resume_from_trip.sh "<理由>"`; **run log / 终端记录留存** |
| 2-2 | 硬门**真的评估了 testnet 树** | 步骤 1/4 的输出里能看到它读的是 testnet root (修完 §0-1 后) |
| 2-3 | 证据被隔离而非删除 | `state/testnet/watchdog/quarantine/state_*_resumed.json` 存在, 含 `_resume_reason` |
| 2-4 | **trip 的历史记录原样存活** | `events.jsonl` / `ALARM.log` 里 00:17:11Z 那条**未被改写**(比对我此刻已留存的内容) |
| 2-5 | 理由/依据/时刻落在 run log | 三者齐, 且"依据"指向具体产物而非"已确认" |

## §3 清除**之后**必须成立

| # | 判据 | 通过条件 |
|---|---|---|
| 3-1 | state 干净 | `state/testnet/watchdog/state.json` 不存在, 或 `tripped_at = None` 且 `reduce_only = false` |
| 3-2 | **下一个锚点的看门狗未立即再触发** | 清除后第一个锚点 `watchdog: tripped=False` |
| 3-3 | **`open_orders_halted` 真的解除** | 下一个锚点 phase_A 无 `order_blocked_by_halt`; 若仍为 halt, 说明清了 state 但没解 halt (两个开关) |
| 3-4 | 08:00Z 前无意外交易 | 清除→08:00Z 之间的 `orders.jsonl` 新增行数 = 预期值 (若裁定为 C, 预期 = 0 开仓单) |
| 3-5 | **陈旧性检测器不因此变绿** | `anchor_timeline.py` 里 `watchdog:*` 各格仍按其自身证据时刻判 —— **清除不是证据** |

## §4 我复核时会另外做的两件事 (不需 team-lead 配合)

1. **重跑 §0-2 的那次评估** (throwaway state dir, 只读), 确认清除后 `tripped` 的读数与清除前的差异**能被解释**, 而不是"就是变了";
2. **对 `oracle_5b_sign.py` 重跑一次**, 确认 `n` 与分布相对清除前的变化**只来自已知原因** (行数增加 / 符号修复), 不是口径漂移。

---

## 未经单独检验的步骤清单 (本单)

0. **(已消解) 原第 2 条"我没有预先确认 04:00Z 锚点会写出那四个 halt 字段"** —— 已于 03:3xZ 查清: 三个字段在 run log 里 0 次, 因为 trip 后无 TESTNET 锚点; 判据已改为主要读 orders 表, 并新增 1-5b。**结论: 1-5 可判, 但读的不是原先写的那个产物。**
1. **§1-3 的"maker-leg 重放 85.9%"我没有独立复算** —— 该数字来自 team-lead 转述, 我只把"它必须晚于两个 commit"写成了判据;
2. **我未实测 `LIVE_MODE=TESTNET` 一定会被 04:00Z 那次 launchd 调用继承** —— 我只读到 plist 里有该键; 若该次调用因故走了手动路径(DRY_RUN), 1-5/1-5b 全部不可判, 应记 UNKNOWN 而非通过;
3. **§0-2 的三个选项我没有逐一验证可行性** —— B (resume epoch) 需要改 `watchdog.evaluate` 的取数窗, 我没有评估它对其余六条判据的连带影响;
4. **§3-3 的"两个开关"是我读代码推断的** (`state.json` 与 `open_orders_halted` 可能由不同路径设置), **未实测**。
