> **创建:** 2026-09-12 10:10 UTC | **Session:** W1(team, lead=main; 隔离克隆 `/Users/haosiyu/cc_tmp/exec_w1`, 分支 `fix/ic-monitor-contract`, 基线 918559f=origin/main) | **状态:** FINAL r3 2026-09-13 01:5xZ(§8: 复审 REVIEW_2026-09-13 §3.B 两条缺陷已闭, 单跑 94/94, 修前源逐格红, 研究员探针四条缺陷断言全翻红; 代码仍只在克隆, **未部署**) | r2 15:55Z — 第一轮 §1-§5(10:10Z 事实表先于码; 单跑 52/52; 电池 131/132) + 第二轮 §7(独立复审 W1-R1/R2/R3 修正: 14:30Z 事实表先于码; 单跑 76/76; 老码 918559f 与修前 8b2c218c 皆红; 最终树电池 131/132, 唯一红 = 克隆无 .env 的 tests_env_loading); 代码只在克隆, **未部署**(lead 经 safe_commit 落地) | **作废条件:** `ops/ic_monitor.py` 再改; 或阈值按在役形态重标(生产者平价回放 Phase 2)落地; 或 launchd 调度/数据源变更

# #55 实现 rank-IC 监视器 — 告警合同修正(设计 + 事实表 + 收据)

**一句话:** 监视器的数学不动(统计量、阈值常量、判读窗起点全部原样), 改的是它**对人说的话**(对象/标定身份写进每页与状态文件)、**它何时说话**(恢复通知; 判窗不完整时不判并告知缺哪些锚)、以及 **`--check` 必须零副作用**。

**硬边界(任务作废条件):** 运行树 `~/dl_quant_live` 与生产者 `~/wide_shadow` 只读; 不跑 `safe_commit.sh`; 不部署; 不调交易所/Telegram API; 不上 pod2/GPU; 研究仓不提交不推送。所有改动只在克隆。

---

## §0 事实基线(独立复核 + lead 给定, 本文照单接受, 不重新论证)

来源: `/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_system_status_review_2026-09-12/monitoring/RESULT.md`(独立研究员 09-12 09:19Z, 全部 VERIFIED 项)+ lead 任务书。克隆内 `ops/ic_monitor.py` sha256 `ba89bf68…9162f` 与审计 pin 逐位相同(§4 R0)。

## §1 事实表(每条: 事实 · 出处 · 我如何核)

| # | 事实 | 出处(克隆内路径:行) | 核法 |
|---|---|---|---|
| F1 | 统计对象 = spearman(场所回读**实持仓有符号名义** @t0, **p(t1)/p(t0)−1**), p=\|notional\|/\|qty\|(不是订单簿 mid, 是场所 notional/qty 隐含价) | `ops/ic_monitor.py:86-103`(loader 只读 `venue_position_notional/qty/anchor_ts`), `:119-122,141` | 读源; 与审计 VERIFIED 1-5 一致 |
| F2 | 它**不是**模型分数 IC, **不是**扣费净收益: 无 target_live/分数输入, 无费用/资金费/成交现金流 | 同上; 审计 VERIFIED 4 | 读源 |
| F3 | 阈值常量 ALERT r24<−0.02277; DECIDE r24<−0.04425 或 r48<−0.01656; 标定 = α=0.05/band=0.002 离线书, 2026-08-10, 9821 锚 | `ops/ic_monitor.py:11-17,45-51` | 读源 |
| F4 | 在役书 α=0.1/band=0.00025(combo, 去 rev24) ⇒ 5%/1% 概率含义对在役形态**不成立**; 源码无按形态换阈值机制 | 审计 VERIFIED「阈值身份不匹配」(读 `~/wide_shadow/shadow_bundle/config.json` + `fea171/combo_stage.py:90`); lead 任务书 | 只读树, 本人未开; 照审计+lead 接受 |
| F5 | 最新评估 2026-09-12 01:30:02Z: **OK**, r24 +0.00472, r48 −0.01104, n=176; 前三日 01:30Z 均 DECIDE(09-09 −0.03483/−0.02373; 09-10 −0.02705/−0.02667; 09-11 −0.02788/−0.02178) | 克隆 `state/icmonitor_out.log` 末 8 行 | 读文件 |
| F6 | 状态文件当前 = `{"last_ALERT": 1788744602.806 (=09-07 01:30:02Z), "last_DECIDE": 1789003803.968 (=09-10 01:30:03Z)}`; **无「最后投递级别」字段** | 克隆 `state/live/ic_monitor_state.json`(sha `2e690e1f…`) | 读文件 |
| F7 | 手机最后一页 = 09-10 DECIDE; 09-11 DECIDE 未投(距上次成功投递 86,398.51 s < 严格 24h 冷却); 09-12 OK 时 `deliver()` 对非 ALERT/DECIDE **直接 return**, 恢复零通知 | `ops/ic_monitor.py:192-203`; 审计 INFERRED(冷却)+VERIFIED(无恢复路径) | 读源 |
| F8 | `--check` **不是**只读: import 期 L33-37 无条件加载 `.env`; main L251 对任何模式都调 `deliver()`, 它 import `telegram_notify` 并构造 notifier(即使 NOT_CONFIGURED 也**写** `state/notify_audit.jsonl` 一行) | `ops/ic_monitor.py:31-38,209-222,242-251`; `live/telegram_notify.py:206-212,239-248` | 读源 |
| F9 | 统计量 = 账本**最后 24/48 行**均值, 行只在「相邻网格间隔 ≤6h 且共持 ≥30 名」时产生 ⇒ 缺锚被**跳过而拉长窗口**, 无新鲜度门, `check()` 不知现在时钟 | `ops/ic_monitor.py:112-116,124,178-181` | 读源 + 本人在冻结账本上量: 09-12 运行的最后 24 行跨 **112h**(理想 96h), 48 行跨 **228h**(理想 192h) |
| F10 | 冻结账本 post-window 176 行(08-10 12Z → 09-11 20Z), 网格期望 195 点, **缺 19**: 08-21 20Z…08-22 08Z(4), 08-25 12/16Z, 08-26 12/16Z, 09-01 20Z, 09-02 00Z, **09-06 08Z→09-07 00Z(5, 首次单日止损平仓 E-0906)**, **09-09 08Z→20Z(4, 看门狗账本缺口平仓 E-0909-G)** | 克隆 `state/live/ic_monitor.jsonl`(sha `fd62e6b7…`) | 本人脚本 census(§4 R2 同码复算) |
| F11 | **按任务书门(r24 缺>2 / r48 缺>4)在冻结账本上逐日回放** — 前沿 = floor((run−4h−1h)/4h)·4h: | 本人脚本(§4 R2 以正式代码复算并留收据) | 计算 |
|  | 09-07 01:30Z(实投 ALERT): r24 缺 4 [09-06 08/12/16/20Z] · r48 缺 6 ⇒ **INCOMPLETE** | | |
|  | 09-09 01:30Z(实投 DECIDE): r24 缺 5 · r48 缺 7 ⇒ **INCOMPLETE** | | |
|  | 09-10 01:30Z(实投 DECIDE, 由 r48 门触发): r24 缺 9 · r48 缺 10 ⇒ **INCOMPLETE**(当日最近可评分起点仅 09-09 04Z, 前沿 09-09 20Z) | | |
|  | 09-11 01:30Z(DECIDE 未投): r24 缺 5 · r48 缺 9 ⇒ **INCOMPLETE** | | |
|  | 09-12 01:30Z(OK): r24 缺 4 [09-09 08/12/16/20Z] · r48 缺 9 ⇒ **INCOMPLETE** | | |
|  | ⇒ **本轮全部四次判级(3 页实投 + 1 次 OK)都落在跨越平仓洞的拉长窗上; 门按任务书参数会把它们全部标 INCOMPLETE。** 这是任务书参数的直接后果, 本文如实呈报, 不擅改参数(常量集中一处 `MAX_MISSING`, lead 可裁) | | |
| F12 | `tests_env_loading` 的**总体是算出来的**: 正则 `TelegramNotifier\s*\(` 扫 ops/scheduler/live/signal 非 tests_ 模块, 每个成员在子进程 import 后必须已填 TELEGRAM_*(不看 argv) ⇒ `ic_monitor.py` 是成员; **删 import 期加载 = 该安全套件红; 改写法躲开正则 = 把监视器从安全总体里悄悄除名**(更糟) | `live/tests_env_loading.py:59-75,84-105` | 读源 |
| F13 | `alarm_policy` 只按**正文文字**分级: 无规则命中 ⇒ UNRECOGNISED ⇒ tier A ⇒ PUSH; 命中 MEASURE 规则(如 `coverage\|覆盖率\|measurement_complete`, `weight`, `net/gross`)⇒ RECORD **永不推送**; 命中 EXPECTED(如 `redeliver`, `门槛` 组合)⇒ DAILY 不推送; 同正文 24h 内已投 ⇒ 抑制。严重度 INFO/HIGH/CRITICAL **不参与**分级 | `live/alarm_policy.py:39-113,116-141,147-178` | 读源 |
| F14 | 现役正文只打印 r24 的两个阈值, 不打印触发 09-10 DECIDE 的 R48_P1; 不写数据前沿 | `ops/ic_monitor.py:205-208`; 审计 VERIFIED | 读源 |
| F15 | 电池: `run_acceptance.sh` SUITES 数组注册, `tests_ic_monitor` 在 L222; 每个 `live/tests_*.py` 必须注册否则拒跑; 解释器 `/usr/bin/python3`(3.9.6); `ops/pyenv.sh` 关字节码写+私有缓存 | `run_acceptance.sh:26-28,39-…,222,244-256` | 读源 |
| F16 | `ops/gate_coverage.SUITE_SCOPE` 每套件必有条目(verify 只查**键存在**, 不查文字); `tests_ic_monitor` 条目盲区 (b)「投递未测」(c)「阈值正确性全靠离线标定, 无人注意形态漂移」在本改动后**部分失真**, 需改文字 | `ops/gate_coverage.py:150,339-371` | 读源 |
| F17 | launchd: `/usr/bin/python3 /Users/haosiyu/dl_quant_live/ops/ic_monitor.py` **无参数**(=append 模式), 每日 09:30 SGT=01:30Z; stdout→`state/icmonitor_out.log`; runs=14, last exit 0(审计 09:09:58Z `launchctl print`) | `~/Library/LaunchAgents/com.dlquant.live.icmonitor.plist`(只读) | 读文件 |
| F18 | `ic_monitor.jsonl` 每行被 `main()` 当锚行解析(`known.add(r["anchor_ts"])`), 非锚行会进 `rows` 再在 `check()` KeyError ⇒ **评估/普查记录不能写进这个 jsonl** | `ops/ic_monitor.py:232-239,166-168` | 读源 |
| F19 | `tests_imports` 不 import `ic_monitor`(不在 run_anchor 可达图), 只正则扫 ops 文件的 `"/fapi/v…"` 字串 | `live/tests_imports.py:300-320` | 读源 |
| F20 | 克隆: HEAD 918559f=origin/main; **无 `.env`**(故意; 无任何凭据) ⇒ `tests_env_loading` [B] 在克隆对总体每个成员必红 — **已知克隆伪影, 唯一允许的红** | `git -C clone log -1`; `ls clone/.env` 不存在 | 命令 |
| F21 | 克隆快照回读网格 237 个, 最后 09-12 08Z; 账本最后行 09-11 20Z(09-12 00/04Z 行要等 09-13 01:30Z 运行追加) | 本人 census | 计算 |

## §2 设计决策(每条: 规则 · 被拒替代 · 可调常量)

**D1 对象与标定身份 = 常量, 进每一页与状态文件。** 两个字串**逐字**取 lead 任务书:
- `OBJECT = "书级实现 rank-IC = 场所实持仓名义排序 vs 下锚 mid 收益排序; 不是模型分数 IC, 不是扣费净收益"`
- `CALIB_IDENTITY = "阈值标定: α=0.05/band=0.002 离线书(2026-08-10, 9821 锚); 在役 α=0.1/band=0.00025 — 阈值未按在役形态重标, 5%/1% 概率含义不适用"`
- 每页(ALERT/DECIDE/RECOVERED/INCOMPLETE)正文尾部两行原样附上; `contract()` 块 = {object, calibration, thresholds{ALERT_r24_lt, DECIDE_r24_lt, DECIDE_r48_lt}, calib_src, statistic, freshness_gate} 写入 `ic_monitor_state.json["contract"]`、每条评估记录、以及 `check()` 输出(进 launchd stdout 日志)。
- 顺带补 F14: 正文打印 R48_P1, 写明**哪扇门触发**, 写数据前沿与两窗普查。

**D2 恢复通知 = 状态机上的一次性转移。**
- 新状态键 `last_delivered_level ∈ {ALERT, DECIDE, OK}`, 只在**成功离机**(`delivered_offbox`)时更新: ALERT/DECIDE 页成功 ⇒ 记该级; RECOVERED 页成功 ⇒ 记 OK。
- **遗留状态迁移(部署首日就要对):** 无 `last_delivered_level` 时, 取 `last_ALERT/last_DECIDE` 中时间戳更大者为「最后投递级别」(F6 ⇒ DECIDE)。这是账本事实(09-10 DECIDE 确有 message_id), 不是猜测。
- 转移规则: 本次 `level == "OK"` 且 `judged` 且 `last_delivered_level ∈ {ALERT, DECIDE}` ⇒ 投**一页 INFO** `RECOVERED: 24/48 锚均值回到所用阈值以上 — 不等于 alpha 恢复` + r24/r48 数值 + 若 r48<0 明写「r48 仍 <0」+ 若 r48 窗未判明写。OK 持续 ⇒ last=OK ⇒ 不再发。投递失败 ⇒ last 不变 ⇒ 次日重试(=「恰好一页**送达**」)。
- INCOMPLETE 不改 `last_delivered_level`(它不是判级)。ALERT/DECIDE 同级冷却与升级逻辑**原样**。
- 被拒替代: 「等两窗都完整才 RECOVERED」— 任务书写的是 level 转移; 保留任务书语义, 正文把未判窗写明; 若 lead 要更严, 改一处条件。

**D3 新鲜度门 = 网格期望 vs 实有, 不动统计量。**
- 前沿 `frontier = floor((now − GRID_S − MATURE_LAG_S)/GRID_S)·GRID_S`, `MATURE_LAG_S = 3600`(回读 read_ts−E 观测 15.8–47.1 分钟, 取 1h 余量; 01:30Z 运行 ⇒ 前沿 = 前日 20Z, 与账本实际前沿一致 F11)。
- 期望点 = `{frontier − i·GRID_S | i<24 (48)} ∩ [WINDOW_START_TS, ∞)`; 实有 = 期望点中账本有 `rank_ic≠None` 行者; 缺 = 期望 − 实有。
- `MAX_MISSING = {"r24": 2, "r48": 4}`(任务书); 缺 > 上限 ⇒ 该窗 `complete=False`, **不在该窗上判** ALERT/DECIDE; 两窗都不可判 ⇒ `level="INCOMPLETE"`; 一窗可判 ⇒ 只按可判窗判级, `judged_windows` 写明。
- r24/r48 **数值照旧算**(最后 24/48 行均值)并照旧输出——只是不据以判级; 阈值常量、WINDOW_START_TS、`compute_rows` 一字不动。
- 普查 `census` 进 `check()` 输出、状态文件 `last_eval`、评估账本 `state/live/ic_monitor_evals.jsonl`(新文件, 只 append 模式写, 与锚行账本分离 — F18)。
- 任一窗不完整 ⇒ 24h 内至多一页 INFO `INCOMPLETE`, 列出缺的锚(ISO), 状态键 `last_INCOMPLETE`。
- **后果(F11)如实报**: 冻结账本上本轮四次判级均 INCOMPLETE; 若此后每个网格锚都有行(无新洞), r24 于 **09-14 01:30Z** 运行(前沿 09-13 20Z, 09-09 洞滑出 24 窗, 缺 0)恢复可判, r48 于 **09-16 01:30Z** 运行(前沿 09-15 20Z, 缺 4 = 恰在上限)恢复可判, **09-18** 起两窗缺 0 — §4 R2 用正式代码复算(10:10Z 初稿误写 09-18, 以 R2 为准)。
- 新鲜度**同时**覆盖「账本冻死」: 前沿随 now 前进而行不进 ⇒ 缺数上升 ⇒ INCOMPLETE(审计「固定旧 ledger 可永久 OK/DECIDE」的洞由此关上)。

**D4 `--check` 严格只读; `--dry` = `--check` + 投递预演。**
- import 期 `.env` 加载改为 **argv 门控**: `sys.argv[1:]` 含 `--check`/`--dry` ⇒ 不加载; 否则照旧加载(launchd 无参数 ⇒ 加载; `tests_env_loading` 子进程 `python3 -c` ⇒ argv=['-c'] ⇒ 加载 ⇒ 该套件语义不变, 监视器仍在安全总体内 — F12)。
- `--check`: 不写 LEDGER/STATE/EVALS, 不调 `deliver`, 不 import `telegram_notify`; 只打印 verdict(含 census+contract)。
- `--dry`: 同 `--check`, 另打印 `plan_delivery()` 结果(会发什么页、给谁级别、正文)— **不构造 notifier**, 纯计算。
- 被拒替代: 把 `TelegramNotifier(` 挪到别处/改写法 — 会让监视器逃出 F12 的安全总体; 拒。

**D5 正文用词避开 alarm_policy 的 B/C 层规则(F13)**: 不用 coverage/覆盖率/weight/net-gross/门槛/REGRESSION/停机/无法判定 等; 用「判窗不完整」「缺」「阈值」「不判」。测试 T11 直接调 `alarm_policy.decide(body)` 断言四种正文都是 PUSH(否则 INFO 页会被静默记档而永不上手机 — 这正是恢复通知最怕的失败形态)。

**D6 不动的东西(明列, 免误读):** 阈值三常量; 统计量; `compute_rows`(β 因果、n≥30、6h 间隔); WINDOW_START_TS; 同级严格 24h 冷却(F7 的 86,398 s 伪抑制是**已知开口**, §6 列出, 不在本单)。

**D7 测试纪律:** 测试文件顶部、import 模块前置 `LIVE_ALARM_SUPPRESS=1` + `LIVE_NOTIFY_AUDIT=<tmp>`(即便某路径构造了 notifier 也只会 SUPPRESSED 且审计落 tmp); 投递用注入的 `sender` 桩; 突变体写到 tmp 目录用 importlib 按路径加载(不碰 ops/ 树); 子进程测试用临时 `.env` 路径**猴补 `envfile.ENV_PATH`**(克隆内不创建 `.env`)。

## §3 测试矩阵(行为 → 绿断言 → 红能力)

| 行为 | 绿断言(新 T#) | 突变(必须红) |
|---|---|---|
| D1 对象/标定 | T7a 两常量逐字等于任务书; T7b 四种正文都含两串; T7c `contract()` 的 object/calibration/thresholds 与常量/阈值相等; T7d 正文含 R48_P1 与触发门 | M7: 正文去掉 OBJECT ⇒ T7b 红 |
| D2 恢复 | T8a DECIDE→OK 恰一页 INFO RECOVERED, state last=OK; T8b OK→OK 零页; T8c 从未投递→OK 零页; T8d **真实遗留状态字典(F6)**→OK ⇒ RECOVERED; T8e 投递未离机 ⇒ last 不变(次日重试); T8f r48<0 ⇒ 正文含「r48 仍 <0」 | M8: 删转移分支 ⇒ T8a/T8d 红 |
| D3 新鲜度 | T9a 24 窗挖 4 锚 ⇒ r24 不完整、缺锚列表逐位相等、level INCOMPLETE; T9b 挖 2 锚 ⇒ 完整、照判; T9c 账本冻死(now 前进 3 天)⇒ INCOMPLETE; T9d INCOMPLETE INFO 页 24h 内恰一次; T9e r24 完整/r48 不完整 ⇒ 只按 r24 判, r48 越线不触发 DECIDE; T9f 统计量不变: r24 数值 = 最后 24 行均值(不论洞); **T9g 冻结真实账本回放 09-12 01:30:02Z ⇒ r24=+0.00472, r48=−0.01104 复现, r24 缺 [09-09 08/12/16/20Z], r48 缺 9** | M9: `MAX_MISSING` 置 10^9 ⇒ T9a/T9c 红 |
| D4 只读 | T10a 子进程 argv `--check` + 临时 fake .env ⇒ TELEGRAM_BOT_TOKEN 未填; T10b 无旗标 ⇒ 已填(加载器仍在, F12 性质保住); T10c `main(--check)`/`main(--dry)` 在克隆真实回读上跑, LEDGER/STATE/EVALS 三文件 sha 前后相等, `telegram_notify∉sys.modules`, `urllib.request.urlopen` 陷阱未触发 | M10: 删 argv 门 ⇒ T10a 红 |
| D5 分级 | T11 四种正文 `alarm_policy.decide()` 均 action=PUSH | (M7 的正文变体仍 PUSH; 此项是合同守卫非突变对象) |
| 既有 | T1–T6 全保留; T3 各调用补 `now=`(签名新增参数, 夹具语义不变: 前沿 = 夹具最后锚) | — |

## §4 收据

全部收据文件在 `/Users/haosiyu/Desktop/quant_research/docs/receipts/`(研究仓, **未提交**); 代码只在克隆 `/Users/haosiyu/cc_tmp/exec_w1`(分支 `fix/ic-monitor-contract`, **未提交未推送**, 运行树未动)。

**R0 基线.** 克隆 HEAD `918559f` = origin/main; 修前 `ops/ic_monitor.py` sha256 `ba89bf68ba5a7d28d60fabc031f2fee85aed529048bbfa18430a091c6709162f`(= 审计 pin, 逐位同); 修前 `live/tests_ic_monitor.py` `15e4722c…c6a584c`; 快照 `state/live/ic_monitor.jsonl` `fd62e6b7…5fd47af0`(= 审计 pin), `ic_monitor_state.json` `2e690e1f…27d3b8`。克隆无 `.env`(`ls` 不存在)。

**R1 套件单跑(克隆, `/usr/bin/python3`, pyenv.sh 生效).** 文件 `w1_ic_monitor_suite_standalone.log`: **52 项全 PASS**(`grep -c "  PASS "` = 52; T1a-d, T2a-c, T3a-e, T4, T5a-b, T6 = 16 项既有/微调; T7a-e 5 + T8a-i 9 + T9a-g(含 T9d') 8 + T10a/a'/b/c 4 + T11/T11' 2 = 28 项新; M7/M8/M9/M10 各「注入点恰一次」+「突变红」= 8 项), 6.6 s。逐行复跑命令(逐字):
```
cd /Users/haosiyu/cc_tmp/exec_w1/live && . ../ops/pyenv.sh && /usr/bin/python3 tests_ic_monitor.py
```

**R2 冻结账本回放(正式代码).** 文件 `w1_ic_monitor_replay_and_projection.txt`。五次历史运行(行 = `computed_at ≤ run+5`, now = run): 09-07 ALERT/09-09 DECIDE/09-10 DECIDE/09-11 DECIDE(未投)/09-12 OK 的 r24/r48/n **逐位等于** `icmonitor_out.log` 与审计表(−0.02372/−0.00964 n151; −0.03483/−0.02373 n162; −0.02705/−0.02667 n164; −0.02788/−0.02178 n170; +0.00472/−0.01104 n176); 新门下五次全部 **INCOMPLETE**(r24 缺 4/5/9/5/4, r48 缺 6/7/10/9/9)。填平投影(09-11 20Z 后每锚补一行): 09-13 缺 4/9 ⇒ INCOMPLETE; **09-14 缺 0/9 ⇒ r24 可判**; 09-15 缺 0/5; **09-16 缺 0/4 ⇒ 两窗可判**; 09-18 起缺 0/0。

**R3 红能力.** (i) 突变体 M7/M8/M9/M10(R1 内, 各自红); (ii) 新套件跑在 **origin/main 旧码** 上: 文件 `w1_ic_monitor_suite_on_OLD_code_918559f.log`, exit=1(T1-T2 过后在首个新签名调用处 AttributeError: MATURE_LAG_S 缺 — 旧码不可能过新套件)。

**R4 电池(克隆, 代码 = R5 的 sha, 运行 2026-09-12 10:36:02Z → 10:51:28Z, 避开 HH:20–HH:35 与锚小时).** 文件 `w1_battery_20260912T1036Z_summary.log`(runner stdout 原表, 逐字抄转录命令: `cd /Users/haosiyu/cc_tmp/exec_w1 && bash run_acceptance.sh`); 逐套件日志在克隆 `state/acceptance/20260912T103603Z_*.log`(132 个)。

| 计 | 数 |
|---|---|
| 套件总数 | 132 |
| exit 0 | 131 |
| exit ≠ 0 | **1: `tests_env_loading`**(exit 1) |
| runner 终判 | `ACCEPTANCE: NOT GREEN — at least one suite failed` |

**唯一红的解剖**(文件 `w1_battery_20260912T1036Z_tests_env_loading_RED.log`): 14 项中 10 过、**4 败, 全部是 [B]「X populates TELEGRAM_* on import」**, X = ops/ic_monitor.py, ops/redeliver_alarms.py, ops/unseed_rehearsal_halt.py, scheduler/run_anchor.py —— 即安全总体的**全部四个成员**同败, 原因单一: 克隆无 `.env`(F20, 故意不拷贝凭据), `envfile.load()` 报 exists=False。[A] 总体计算、[C] 加载器语义、[D] 有/无加载器的投递回执、[E] 突变 M1 全过。**本模块的 argv 门不是原因**: T10b 用临时假 `.env` 证明无旗标 import 仍加载(`tok: True`); 且另外三个未改动的成员同败。在运行树(有 `.env`)该套件应绿 —— 由 lead 落地时的电池证实, 本文不声称。

`tests_ic_monitor` 在电池内: exit 0, 52 PASS, 日志 `w1_battery_20260912T1036Z_tests_ic_monitor.log` sha `9e06dfd0…` **与单跑日志逐字节相同**(确定性输出)。`gate_coverage` exit 0(条目文字改后 verify 通过)。`tests_static_names`(pyflakes)exit 0。

**R5 diff 与文件 sha.**
- diff(**只含三个代码文件**; 克隆 `state/` 的 rsync 差异不在其中): `w1_ic_monitor_contract.diff`, 978 行, 3 个 `diff --git`(live/tests_ic_monitor.py, ops/gate_coverage.py, ops/ic_monitor.py), sha256 `ad2f6dba97be0b28c48ee793d0495ba1f098eafc789ca5194c458f5a98711477`。生成命令(逐字): `git -C /Users/haosiyu/cc_tmp/exec_w1 diff origin/main -- ops/ic_monitor.py live/tests_ic_monitor.py ops/gate_coverage.py`。
- 克隆代码(修后):
  - `ops/ic_monitor.py` `8b2c218c7270a7bb1629c2affa35fdaa5e2c11d4784fb0b1ff947c072d33776f`(修前 `ba89bf68…`)
  - `live/tests_ic_monitor.py` `0b1f2b6eca8ba2c2e3718ea96d20b8b21c3ad1066fdca1deaab86166517ce9bf`(修前 `15e4722c…`)
  - `ops/gate_coverage.py` `591cb8ff2eb58f87efdc626cb44c134b2631d032f89d2b0e109d996985e07684`
- 研究仓收据(`docs/receipts/`, 未提交):
  - `w1_ic_monitor_suite_standalone.log` `9e06dfd0318351b456c292126b2d090d739b123f2ab0e8108bd5dc9fd3726510`
  - `w1_ic_monitor_suite_on_OLD_code_918559f.log` `cd28c25a1263b36b32239ba39dceedc4395742d0374a59b4aeaefa5c8d51d6a5`
  - `w1_ic_monitor_replay_and_projection.txt` `07b281b257c40368c963267ae91ef1384cd9dcf7502cbc60af04e71da2303269`
  - `w1_battery_20260912T1036Z_summary.log` `e4bad4f616bd979b38b9a89c0b9b76869226933f8d9d3dfa9ac0ef2a103ff69a`
  - `w1_battery_20260912T1036Z_tests_env_loading_RED.log` `61c3df91ad36bff0fb264e0292c2bd6b2f53ffb2504131303e67035bf74fd52f`
  - `w1_battery_20260912T1036Z_tests_ic_monitor.log` `9e06dfd0318351b456c292126b2d090d739b123f2ab0e8108bd5dc9fd3726510`
- 本文档自身的 sha 在最终报告里给(写入后才能算)。
- **未做**: 研究仓不提交; 克隆不提交不推送; 运行树/生产者零写入; 零 API 调用(T10c 的 urlopen 陷阱在只读门下未触发; 电池里 `tests_telegram_notify` 等套件按其自身设计用桩)。

## §5 RESULT

**改了什么(克隆 `ops/ic_monitor.py`, 525 行; 修前 255 行):**
- L1-41 模块文档: 对象/非对象、标定身份、合同四条、只读门、用法。
- L49-64 `_readonly_invocation()` + **argv 门控**的 import 期 `.env` 加载(D4; F12 的安全总体成员身份不变)。
- L70 `EVALS` 评估账本路径; L74 `COOLDOWN_S`; L85-88 `OBJECT`/`CALIB_IDENTITY`; L92-93 `MATURE_LAG_S`/`MAX_MISSING`; L96-112 `contract()`。
- L115-225 `_rankdata/_corr/_spear/load_anchors/compute_rows` **逐字不动**(T4 静态序检查仍过)。
- L228-254 `iso/frontier_ts/census`; L257-305 `check(ledger_rows, now=None)`: 统计量不变, 加普查、`judged_windows/incomplete_windows/trigger`, 两窗都不可判 ⇒ `level="INCOMPLETE"`。
- L308-370 正文: `body_breach`(触发门 + 三阈值 + 前沿 + 两窗普查 + 两行合同)/`body_recovered`/`body_incomplete`。
- L373-404 `load_state/save_state/last_delivered_level`(遗留迁移); L406-424 `plan_delivery`(纯函数状态机); L427-432 `_telegram_sender`; L435-467 `deliver(verdict, now, state_path, sender, persist)`: 只有离机成功才推进状态; 状态文件总带 `contract` + `last_eval`; L470-478 `append_eval`。
- L481-521 `main(argv)`: `--check`/`--dry` 不写三文件、不调 deliver; append 模式 = 原行为 + deliver + evals。
- `live/tests_ic_monitor.py`(490 行; 修前 75 行): T1-T6 保留(T3 调用补 `now=`); 新 T7-T11 + M7-M10(§3)。
- `ops/gate_coverage.py` L150: `tests_ic_monitor` 条目文字重写(覆盖 + 四个盲区 a-d 更新; verify 仍 exit 0)。

**每个测试证明什么:** 见 §3 矩阵; 要点 — T7 证两行**逐字**在每页与 contract 块(M7 证「少一行」会红); T8a/d/e 证恢复是「最后**送达**级别」上的一次性转移且遗留 state 迁移到 DECIDE(部署后首个可判 OK 会发 RECOVERED)(M8 证删转移会红); T9a/c/e/g 证门在洞、冻死、部分窗三种形态下都拒判且**真实 09-12 评估在门下是 INCOMPLETE**(M9 证关门会红); T10a/b/c 证 `--check`/`--dry` 在真实回读上零副作用且无参数调用仍加载 `.env`(M10 证删门会红); T11 证四种正文不会被 alarm_policy 静默降级。

**行为后果(lead 必读):** ① 部署后下一次 01:30Z 运行(09-13)在冻结账本 + 正常追加下 = **INCOMPLETE**(r24 缺 09-09 四锚), 发一页 INFO 列缺锚, **不发 RECOVERED**; 若无新洞, 09-14 r24 可判 —— 若 OK 则发 RECOVERED(正文注明 r48 窗未判、r48 数值与符号); 09-16 两窗可判。② 本轮已投的三页(09-07/09-09/09-10)在门下都会被扣住 —— 门参数是任务书的, 若 lead 认为过严, 只改 `MAX_MISSING` 一处并重跑 R2。③ 遗留 state 迁移: 现状态文件按 `last_DECIDE` 迁为 DECIDE, 与手机最后一页一致。

**未关(明列, 见 §6):** 阈值按在役形态重标 = OUT OF SCOPE(生产者平价回放 Phase 2); 24h 严格冷却的秒级抖动; 「mid」命名; launchd 触发断言。

## §6 未关(明列)

- **阈值按在役形态(α=0.1/band=0.00025, combo)重标 — 明确 OUT OF SCOPE**, 需生产者平价回放 Phase 2 产出在役书逐锚 IC 分布再盖章。本改动只把「未重标」写进每页与状态。
- 同级严格 24h 冷却 vs 每日 01:30Z 调度的秒级抖动(F7: 86,398.51 s 抑制了 09-11 DECIDE)— 行为改动, 需 lead 裁(一行: 冷却 24h → 23h)。
- 「mid」命名(F1: 实为 notional/qty 隐含价)— 正文按任务书用「下锚 mid 收益」字面; 状态 `contract.statistic` 里写明 p 的定义。
- launchd 实际每日触发无断言(gate_coverage 盲区 d)— 新鲜度门是间接覆盖(停跑 ⇒ 账本冻 ⇒ INCOMPLETE 页), 但页本身也靠同一 job 发; 真正的 off-box 死人开关不在本单。

---

## §7 第二轮: 独立复审 W1-R1/R2/R3 修正(14:30Z 事实表先于码)

复审来源: `/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_batch_incident_review_2026-09-12/monitoring/RESULT.md`(14:06Z, 冻结克隆 `ops/ic_monitor.py` sha `8b2c218c…776f` = §4 R5 修后 sha)。复审 VERIFIED 的正面项照单接受: 五个数值函数与线上 AST 相同; 阈值/WINDOW_START 不变; 精确 `--check`/`--dry`/`--backfill --check` 零副作用; 遗留迁移/失败重试/OK 不重发。

### §7.1 事实表(第二轮)

| # | 事实 | 出处 | 核法 |
|---|---|---|---|
| F22 | **R1 反例**: 60 时点, r48 窗缺 6、r24 无缺 ⇒ r24=+0.01000 可判, r48=−0.09500 不判(< R48_P1 但缺失>4); 上次投递 DECIDE 时 `plan_delivery` 产 INCOMPLETE + RECOVERED, RECOVERED 标题「24/48 锚均值回到所用阈值以上」, 且 `last_delivered_level` 写成 OK | 复审 R1; 克隆 L406-424 | 本人读源确认: 恢复条件只看 `level=="OK"`, 不看**触发窗**是否重新可判 |
| F23 | **R2 反例**: t0 投 DECIDE → t0+1h 投 RECOVERED(state=OK) → t0+2h 再 DECIDE ⇒ **零投递**, 因 L416 冷却键 = 旧 `last_DECIDE`(t0), 与事件是否已恢复无关 | 复审 R2; 克隆 L415-418 | 读源确认 |
| F24 | **R3 反例**: argparse 默认 `allow_abbrev=True` ⇒ `--che` 解析为 check; 但 import 门 L49-52 只比较完整字串 ⇒ `--che` 先尝试 `import envfile`(复审陷阱截获)再进入只读路径 | 复审 R3 + `cli_probe_receipts.json` | 读源确认: 门在 L60, 解析在 L482, 顺序倒置且规则不一致 |
| F25 | OBJECT 说「下锚 mid 收益」, `contract.statistic` 说 p=\|notional\|/\|qty\| 隐含价 —— 同一页两种说法 | 复审 §2 | 读源 |
| F26 | `check()` 在 `len(post)<24` 提前 return, **无 census / 无 INCOMPLETE 页** ⇒ 空账本或 <24 行的冻死账本永远「OK 只记不判」 | 复审 §2 + probe `short` | 读源 L268-270 |
| F27 | 复审 §4 指出 eval 缺「实际最新已评分锚」字段(census 只有期望前沿) | 复审 §4-2 | 读源 |
| F28 | 三份「老码红」参照: 本轮修前克隆源 sha `8b2c218c…`(已快照到 scratch `prefix_r2/`), 用于证明每条新测试在修前为红 | 本人 | 命令 |

### §7.2 设计决策(第二轮)

**D9 事件模型(修 R1+R2).** 状态文件新增 `event` 块 = 一次越线**事件**: `{open, level, trigger_windows, opened_at, delivered:{ALERT:ts, DECIDE:ts}, closed_at, legacy}`。
- **开**: 一页 ALERT/DECIDE **成功离机**时开(或在已开事件内更新 level/并入触发窗/记该级投递时刻)。触发窗 = 本次 verdict `trigger` 里的窗(`r24<…`⇒r24, `r48<…`⇒r48), 事件内取并集。
- **恢复(R1)**: 仅当 `level=="OK"` 且 **事件的每个触发窗都在本次 `judged_windows` 内**(重新可判且未越线)才投 RECOVERED 并关事件(`open=False, closed_at`), `last_delivered_level` 才变 OK。触发窗未判 ⇒ **不恢复、不降级**; 此时若有 INCOMPLETE 页, 正文写「可判窗口未越线, 其余窗口未判; 事件 X(触发窗 …)仍开, 未恢复」— 只许这句, 不许「24/48 都恢复」。
- **RECOVERED 标题按窗**: 两窗皆判 ⇒ 「24/48 锚均值回到所用阈值以上」; 否则 ⇒ 「触发窗 {W} 重新可判且回到所用阈值以上; 其余窗口未判」。仍附「不等于 alpha 恢复」、r24/r48 数值、r48<0 明写、事件起止。
- **冷却限定在同一事件内(R2)**: 无开事件 ⇒ 越线 = **新事件, 立即投**(不看旧 `last_<LEVEL>`); 事件内同级 ⇒ 24h 冷却(键 = `event.delivered[level]`); 事件内升级/降级到另一级 ⇒ 按该级自身冷却。恢复后同级复发 = 新事件 ⇒ 投。R-10 秒级抖动(86,398 s)在**事件内**同级仍存在, 保留为已知开口。
- **遗留迁移**: 无 `event` 键但有 `last_ALERT/last_DECIDE` ⇒ 合成开事件: level = 时间戳更大者(现状态 ⇒ DECIDE), `trigger_windows = LEGACY_TRIGGER_WINDOWS = ["r48"]`(**lead 裁定 16:20Z, 事实依据**: icmonitor_out.log 09-09 01:30Z DECIDE r24=−0.03483/r48=−0.02373, 09-10 01:30Z DECIDE r24=−0.02705/r48=−0.02667 —— 两次 r24 都在 DECIDE 线 −0.04425 之上, r48 都在 R48_P1=−0.01656 之下 ⇒ 两次遗留 DECIDE 均由 r48 门触发; 14:30Z 初稿曾保守取两窗), `legacy=True`, `delivered` 取遗留时刻。首次 deliver 时物化进 `state["event"]`。
- 兼容: `last_ALERT/last_DECIDE/last_delivered_level` 键继续写(只读用途), 不再作冷却键。

**D10 只读门先于一切凭据加载(R3).** 解析器 `build_parser()` 定义在模块顶部, `allow_abbrev=False`; import 期门 `_readonly_invocation()` 用 `parse_known_args` 判: `--check`/`--dry` ⇒ 只读; **任何无法识别的参数(含 `--che` 缩写)⇒ 也按只读处理(不加载凭据)**, 随后 `main()` 的严格 `parse_args` 以 exit 2 拒绝它。`parse_known_args` 若自身 SystemExit ⇒ 视为只读。launchd 无参数 / `python3 -c` import ⇒ 不只读 ⇒ 照旧加载(tests_env_loading 总体语义不变)。

**D11 OBJECT 措辞统一(F25).** OBJECT 改为「书级实现 rank-IC = 场所实持仓名义排序 vs 下锚场所隐含价(\|notional\|/\|qty\|, 源码旧称 mid)收益排序; 不是模型分数 IC, 不是扣费净收益」; `contract.statistic` 已是隐含价, 一致。`load_anchors` 的 docstring 属 AST, **不动**(保持与线上 5/5 相同)。测试 OBJECT_SPEC 同步。

**D12 <24 行也普查(F26).** `check()` 的 insufficient 分支也算 census: 任一窗不完整 ⇒ `level="INCOMPLETE"`, `incomplete=True`, 会有 INCOMPLETE 页(24h 一次); 两窗完整(年轻部署: 期望被 WINDOW_START 截短)⇒ 维持「OK 只记不判」。空账本 ⇒ INCOMPLETE(不再静默 OK)。

**D13 census 加实际前沿(F27).** `census.newest_row_anchor(_ts)` = post 行里最大 anchor_ts(实际最新已评分锚), 与期望前沿 `frontier` 分列, 供 W5 读。

### §7.3 测试矩阵(第二轮; 每条先在修前源 8b2c218c 上红, 再在修后绿)

| 行为 | 绿断言 | 红能力 |
|---|---|---|
| D9 恢复按触发窗 | T12a 复审 R1 夹具 + 开事件 DECIDE(触发 r48): 计划只有 INCOMPLETE, 无 RECOVERED, last 仍 DECIDE, INCOMPLETE 正文含「可判窗口未越线, 其余窗口未判」与「未恢复」; T12b 其后 r48 重新可判且 OK ⇒ RECOVERED, 标题「24/48…」; T12c 事件触发 r24(ALERT) + r48 不完整 ⇒ RECOVERED 但标题为「触发窗 r24 …其余窗口未判」, 不含「24/48 锚均值回到所用阈值以上」 | M12: `_event_recoverable` ⇒ `return True` ⇒ T12a/T12c 红 |
| D9 冷却限事件 | T13a DECIDE(t0)→RECOVERED(t0+1h)→DECIDE(t0+2h) ⇒ 第三步投 DECIDE, 新事件 opened_at=t0+2h; T13b 事件内 ALERT→DECIDE 升级即投; T13c 事件内同级 +1h 不投(T8h 保留) | M13: 新事件分支改回旧键 `last_<LEVEL>` ⇒ T13a 红 |
| D10 只读门 | T14 子进程复刻复审陷阱(禁 import envfile/telegram_notify/binance_broker、禁 socket、禁写 open、禁 os.mkdir/… ), 对 `--check`/`--dry`/`--backfill --check` ⇒ 零事件、READ-ONLY 尾行、无异常; `--che` ⇒ **零事件且 SystemExit 2**(拒绝) | M14a 去 `allow_abbrev=False` ⇒ `--che` 被接受为 check 正常返回 ⇒ 红; M14b 门忽略 unknown ⇒ `--che` 尝试 import envfile ⇒ 红 |
| D11 措辞 | T16 OBJECT 含「隐含价」与「\|notional\|/\|qty\|」, 不含孤立「mid 收益」; contract.statistic 同源 | 修前源 OBJECT 不同 ⇒ 老码红 |
| D12 <24 普查 | T15a 23 行 + 时钟前进 3 天 ⇒ INCOMPLETE 且带 census; T15b 10 行年轻部署 ⇒ OK 不判且 census 完整; T15c 空账本 ⇒ INCOMPLETE | M15: insufficient 分支删 census ⇒ T15a/T15c 红 |
| D13 | T15d census 含 newest_row_anchor = 最后一行 | — |
| 既有 | T8a/T8d 断言改为含「24/48 锚均值回到所用阈值以上」(两窗皆判) + RECOVERED; M8 目标行更新为新恢复分支 | — |

### §7.4 收据(第二轮, 回填)

**R6 套件单跑(修后, 克隆).** 文件 `docs/receipts/w1_r2_ic_monitor_suite_standalone.log`(sha `01ab7e01…3f75`): **76 项全 PASS**(`grep -c "  PASS "` = 76 = 第一轮 52 + 第二轮 24: T12a-c 3 · T13a-d 4 · T14 1 · T15a-e 5 · T16 1 · M12/M13/M14a/M14b/M15 各「注入点恰一次」+「红」10), 19.7 s。命令逐字: `cd /Users/haosiyu/cc_tmp/exec_w1/live && . ../ops/pyenv.sh && /usr/bin/python3 tests_ic_monitor.py`。
- 过程中被测试抓到并修掉的**本人缺陷**: 首版 `deliver()` 在事件更新之前写 `last_<LEVEL>`, 使首次投递把自己派生成「遗留事件」(T13b 红 ⇒ 改为事件先于遗留键 ⇒ 绿); 另一次 T13b 红是夹具错(−0.05 全序列同时越 r24/r48 门, 触发窗并集本应两窗)—— 改夹具为只越 r24 门。
- T14 = 复审陷阱形状的子进程复刻(按 `__main__` 执行源码字节; 禁 import envfile/telegram_notify/binance_broker、禁 socket、禁写 open、禁 os.mkdir/makedirs/remove/unlink/replace/rename、禁开 .env): `--check`/`--dry`/`--backfill --check` ⇒ events=[] · error=None · READ-ONLY 尾行; `--che` ⇒ events=[] · `SystemExit:2`。M14b 的红收据显示旧门形态正是复审所见: events=['import:envfile']。

**R7 老码红.** (a) 复审冻结的第一轮克隆源(sha `8b2c218c…776f`, 快照于 scratch `prefix_r2/`)跑新套件: exit 1 — T7a 红(OBJECT 措辞)后在 `body_breach(v, event)` 处 TypeError(旧签名), 文件 `w1_r2_suite_on_PREFIX_code_8b2c218c.log`(sha `75d50540…72be`); (b) origin/main 918559f: exit 1(MATURE_LAG_S 缺), 文件 `w1_r2_suite_on_OLD_code_918559f.log`(sha `b632dc7e…4a48`)。逐行为的红能力由 M12–M15 给出(R6)。

**R8 冻结账本回放(重生成, 正式修后代码).** 文件 `w1_ic_monitor_replay_and_projection.txt`(sha `d80223f5…d32e`): 五次历史运行 r24/r48/n 与第一轮**逐位相同**(数值函数未动), 判级仍全 INCOMPLETE; 新列 `newest_row`(实际最新已评分锚)与期望前沿分列(09-07 运行: 前沿 09-06 20Z, 实际最新 09-06 04Z; 09-10 运行: 前沿 09-09 20Z, 实际最新 09-09 04Z)。填平投影「遗留事件(触发窗 r48)可恢复?」列(16:21Z 按裁定重生成, sha `5b218e53…d509c`): 09-13 否(r24 缺 4/r48 缺 9), 09-14/15 否(r48 缺 9/5, **r48 是触发窗, 未判则不恢复**), **09-16 起 是**(r48 缺 4 ≤ 4)。⇒ 部署后若无新洞, RECOVERED 最早在 09-16 01:30Z 运行, 标题「24/48 …」(两窗皆判); 09-13..15 每日一页 INFO INCOMPLETE 写「可判窗口未越线, 其余窗口未判; 事件 DECIDE(触发窗 r48) 仍开, 未恢复」(09-14/15)或「无可判窗口」(09-13)。**更正**: 本人在第二轮报告第 11 条曾称「改为 r48 可把最早 RECOVERED 提前到 09-14」—— 错; r48 是绑定窗, 两窗与仅 r48 的最早日期同为 09-16, 只有 ["r24"] 才会是 09-14, 而那不是事实。

**R9 电池(最终树, 引用的那次).** 运行 2026-09-12 15:36:00Z → 15:51:37Z(避开 HH:20–HH:35 与锚小时; 树 = R10 的三个 sha), 命令逐字 `cd /Users/haosiyu/cc_tmp/exec_w1 && bash run_acceptance.sh`; runner stdout 原表 `w1_r2_battery_20260912T153600Z_summary.log`(sha `3fe45177…1a439`), 逐套件日志克隆 `state/acceptance/20260912T153600Z_*.log`(132 个)。**132 套件: 131 exit 0, 1 exit 1 = `tests_env_loading`**; runner 终判 NOT GREEN 即此一套件。解剖(`w1_r2_battery_20260912T153600Z_tests_env_loading_RED.log`, sha `d9b1fc0d…c74dc`): 10/14 过, 4 败全是 [B]「X populates TELEGRAM_* on import」, X = ops/ic_monitor.py, ops/redeliver_alarms.py, ops/unseed_rehearsal_halt.py, scheduler/run_anchor.py(安全总体四成员同败), 单一原因 = 克隆无 `.env`(F20; 其中三个是未改动模块; T10b 用临时假 .env 证明本模块无旗标 import 仍加载)。`tests_ic_monitor` 在电池内 exit 0, 76 PASS, 日志 sha `01ab7e01…3f75` **与单跑 R6 逐字节相同**。`gate_coverage`/`tests_static_names` exit 0。早期信号电池(14:40:56Z → 14:57:29Z, gate_coverage 文字改动前的混合树)同样 131/132 且唯一红同为 tests_env_loading — 仅作旁证, 不引用。

**R10 diff 与 sha(最终树).** `w1_ic_monitor_contract.diff` 1372 行, 3 个 `diff --git`, sha `9e362e7ab9780a752a46a1ecf4022f8959f467f538b80a0e2c0b11470b82085b`(只含 ops/ic_monitor.py, live/tests_ic_monitor.py, ops/gate_coverage.py; 克隆 state/ 的 rsync 差异不在其中)。克隆代码: `ops/ic_monitor.py` `abac2fdf2568b5258d1883470e900f0421311ad1e1f871dd7a8ab4b72474e76a`(638 行) · `live/tests_ic_monitor.py` `cc9e67fb2d83952a8830a878447623f56d29eef61d390bfe1d1071dbd16e7909`(768 行) · `ops/gate_coverage.py` `2d9b2157496d3ae98077f66468ec899b437127c1ff0652ea0cc4ba8bcefa49c7`。

### §7.5 RESULT(第二轮)

**改了什么(`ops/ic_monitor.py`, 第一轮 525 → 638 行):**
- L54-75 `build_parser()`(`allow_abbrev=False`)+ `_readonly_invocation()`: `parse_known_args` 在 import 期、任何凭据加载之前判门; 精确 `--check`/`--dry` **或任何未知参数**(含 `--che`)⇒ 不加载 .env; L83 门不变形。L600-… `main()` 用同一解析器严格解析 ⇒ `--che` exit 2。(R3)
- L108-109 OBJECT 改为「下锚场所隐含价(|notional|/|qty|, 源码旧称 mid)收益排序」, 与 `contract.statistic` 一致; `load_anchors` 不动(AST 与线上相同)。
- L260-282 `census()` 加 `newest_row_anchor(_ts)`(实际最新已评分锚, 与期望前沿分列)。
- L284-… `check()` 的 <24 行分支也普查: 缺锚 ⇒ `level=INCOMPLETE`(空账本/冻死账本不再静默 OK); 年轻窗口(期望被 WINDOW_START 截短且无缺)⇒ 维持 OK 不判。
- L371-438 正文: `_event_line`; `body_breach(v, event)` 写事件新开/已开; `body_recovered(v, event)` 标题**按窗**(两窗皆判才「24/48」, 否则「触发窗 W 重新可判且回到所用阈值以上; 其余窗口未判」), 写事件起止; `body_incomplete(v, event)` 写「可判窗口未越线, 其余窗口未判」+「事件 X(触发窗 …) 仍开, 未恢复」+ 实际最新已评分锚。
- L457-520 事件模型: `_trigger_windows` · `open_event`(含遗留合成: level=时间戳更大者, 触发窗保守两窗, legacy=True)· `last_delivered_level`(开事件 ⇒ 其级; 关 ⇒ OK; 无 ⇒ None)· `_event_recoverable`(事件每个触发窗 ∈ judged_windows)· `plan_delivery`: 越线时 **无开事件 ⇒ 立即投**, 事件内同级按 `event.delivered[level]` 冷却 24h; OK 且事件可恢复才 RECOVERED。(R1+R2)
- L530-588 `deliver()`: 事件先于遗留键更新; 越线页成功离机 ⇒ 开/更新事件; RECOVERED 成功 ⇒ 关事件(`closed_at`, `recovered_with`); `last_eval` 带 `event`。
- `live/tests_ic_monitor.py` 490 → 768 行: T12–T16 + M12–M15(§7.3); T8f/T8g 传事件; bodies() 覆盖九种页形态(含事件变体)全部过 T7b 两行合同与 T11 PUSH。
- `ops/gate_coverage.py` L150 条目文字同步(事件模型、按窗恢复、缩写拒绝、短账本普查、九个突变)。

**复审三反例的关闭证据:** R1 → T12a(复审同一夹具 + 开事件 DECIDE/r48 ⇒ 只 INCOMPLETE, last 仍 DECIDE)+ T12c(标题按窗)+ M12 红; R2 → T13a(t0 DECIDE → t0+1h RECOVERED → t0+2h DECIDE **投**, 新事件)+ M13 红; R3 → T14(复审陷阱形状, `--che` 零事件 + exit 2)+ M14a/M14b 红。其余: T16(措辞)、T15a-e(短账本普查)+ M15 红。

**未关(明列):** 阈值按在役形态重标 OUT OF SCOPE(Phase 2); 事件内同级 24h 严格冷却 vs 01:30Z 秒级抖动(R-10)保留为已知开口(事件模型已让「恢复后复发」不再被它吞掉); 遗留事件触发窗已按 lead 裁定改为 ["r48"](§7.6), 现开事件的 RECOVERED 最早仍是 09-16(r48 为绑定窗); launchd 触发无断言; 数学路径的口径保留项(下一快照有仓才入样、显式零仓丢弃、隐含价非固定 E 时刻、无费用/资金费)不在本单, 不宣布关闭。

### §7.6 lead 裁定后的收口(16:20Z)

- **裁定 (1)** `LEGACY_TRIGGER_WINDOWS = ["r48"]`(`ops/ic_monitor.py` 常量, 注释引两条日志事实; `open_event` 用之; `_event_line` 遗留标注改为「09-09/09-10 DECIDE 皆由 r48 门触发」); T13c 改为断言常量 = ["r48"] 且四个数值事实相对阈值成立(−0.03483 > R24_P1, −0.02705 > R24_P1, −0.02373 < R48_P1, −0.02667 < R48_P1); T13d 语义不变(r48 是触发窗且未判 ⇒ 不恢复)。
- **裁定 (2)** `MAX_MISSING = {"r24": 2, "r48": 4}` 保持(= 用户裁定 R-11, 推荐 A), 代码注释标明。
- **收据**: 单跑 **76/76**(`w1_r2_ic_monitor_suite_standalone.log` 重生成, sha `06427458…fd949`); gate_coverage verify exit 0; diff 重生成 `w1_ic_monitor_contract.diff` 1383 行 3 文件, sha `636327fb639e840b998a91c8bb1088eb00e4dd90f0219b3decca7d56ff131c80`; 克隆 `ops/ic_monitor.py` `00921bc754e4927b333c20b663e2d819a146496867d68a76a17ab13ec4cf1f00`(645 行), `live/tests_ic_monitor.py` `c917cd93c24c9890252cc93a1b4924103a5bf80a230bbe060d0bcd438ccb6d23`(772 行), `ops/gate_coverage.py` 不变 `2d9b2157…49c7`。
- **最早 RECOVERED 日期**: 09-16 01:30Z 运行(不是本人第二轮第 11 条所说的 09-14 —— 该说法错, 见 R8 更正)。
- 全电池未重跑(lead: 落地时在新克隆跑 W6→W2→W1 叠加电池); 本轮改动 = 一个常量 + 两处注释/文字 + 一条测试断言, 无行为面之外的改动。
- **16:26Z 补丁(lead: 新克隆叠加落地测试 T9g 红)**: T9g 依赖运行树的真实账本 `state/live/ic_monitor.jsonl`(state/ 不入库, 新克隆无此文件)—— 与 `.env` 同类的环境依赖, 非代码缺陷。改为: 账本缺失时打印一行 `  SKIP T9g SKIPPED: no real ledger in this tree (clone) — passes only in the run tree (expected <path>)`, 不计 FAIL; 账本在时断言原样。收据: 有账本 76 PASS / 0 SKIP / exit 0(单跑日志 sha 不变 `06427458…fd949`); 无账本(scratch 复刻新克隆形状) 75 PASS / 1 SKIP / 0 FAIL / exit 0。`live/tests_ic_monitor.py` sha `44662f02775d59d7a3e6aa429549687e43d96745c74960b57aed4a7ca31c2cf9`(774 行); `ops/ic_monitor.py` 不变 `00921bc7…1f00`; diff 重生成 1385 行 sha `863244656db370c542ac12a8695dece95d5d24269895f592e0a1b6eea9aa7449`。

---

## §8 第三轮: 独立复审 REVIEW_2026-09-13 §3.B 的两条缺陷(01:25Z 事实表先于码)

复审来源: `/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/docs/REVIEW_code_and_research_2026-09-13.md` §3.B(裁定「未关闭」)+ 专项
`.../multi_asset/exports/research/codex_followup_code_review_2026-09-13/monitoring/RESULT.md` §3(W1-N1/N2/N3)。
执行人 = W1b(接手 W1, 后者触模型用量上限)。克隆 `/Users/haosiyu/cc_tmp/exec_w1` 分支 `fix/ic-monitor-contract`, 基线 918559f, **未部署**。

**本轮不重标阈值。** `R24_P5/R24_P1/R48_P1` 与 `WINDOW_START_TS` 仍是 **α=0.05/band=0.002 的旧标定对象**(2026-08-10, 9821 锚离线书);
在役书 α=0.1/band=0.00025。每一页仍逐字打印 `CALIB_IDENTITY` 说明这一错配。重标依旧是 OUT OF SCOPE(生产者平价回放 Phase 2)。

### §8.1 事实表(第三轮; 每条: 事实 · 出处 · 我如何核)

| # | 事实 | 出处(逐位路径:行) | 核法 |
|---|---|---|---|
| F29 | 研究员冻结的 W1 快照 `private/inputs/w1/ops/ic_monitor.py` sha256 `00921bc7…1f00` 与克隆工作树**逐位相同**(= §7.6 第二轮终版) ⇒ 复审读的就是我要改的那份码 | `shasum -a 256` 两路径 | 命令 |
| F30 | 复审点名的两处在克隆里的**实际行号**: 冷却门 `ops/ic_monitor.py:518`(复审写 519), 触发窗并入 `:563`(复审写 570); 恢复条件 `:501`/`:522`; None 过滤 `:295`; 普查 present 集合 `:272` | 克隆源 | `grep -n` |
| F31 | **N1 复现(修前码, 研究员输入集 A `initial(-1.08,-.72,-.6)`)**: ① now: r24=−0.045 r48=−0.015 ⇒ DECIDE(触发 r24), 投, event.tw=['r24'] ② now+4h(追加 ic=0 一行): r24=−0.020 r48=−0.01708 ⇒ DECIDE(**触发 r48**), 同级冷却**零投递**, **event.tw 仍 ['r24']** ③ now+8h(下一锚缺): r24 缺1可判且健康, r48 缺5不判 ⇒ **投 INCOMPLETE + RECOVERED**, 事件关闭, last=OK | 本人脚本 `scratchpad/w1r3/repro_before.py` 跑克隆修前码 | 计算(数值与专项 §3 W1-N1 表逐位相同) |
| F32 | **N2 复现(输入集 B `initial(-.504,-.816,.1)`)**: ① r24=−0.021 r48=−0.017 ⇒ DECIDE(触发 r48), 投 ② now+8h(锚 60 缺, 追加 ic=−0.1): r24=−0.02933 可判 ALERT, r48=−0.02117 缺5**不可判** ⇒ 投 INCOMPLETE+ALERT, **event.level 被覆写成 ALERT**(原触发窗 r48 尚未重新可判) ③ now+12h(追加 ic=−1.0): r24=−0.06991 ⇒ DECIDE, **零投递**(旧 DECIDE 时钟 12h<24h), event.level 仍 ALERT | 同上 | 计算(与专项 §3 W1-N2 表逐位相同) |
| F33 | **N3 复现**: 60 行 `rank_ic=NaN` 的新鲜网格 ⇒ `check()` 给 level=OK, judged=True, judged_windows=['r24','r48'], r24=r48=**nan**, 普查缺 0 ⇒ 在已开 DECIDE(r48)事件上**投 RECOVERED**, last=OK。根因: `:295` 只排除 None; `:272` 把 NaN 行算作实有; NaN 与阈值的一切比较为 False ⇒ 「健康」是从「所有越线比较都不成立」**推**出来的 | 同上 | 计算 |
| F34 | 修前码的两个概念**共用一个更新条件**: `deliver()` 只在 `delivered_offbox` 为真时才 `:563` 并入触发窗、`:565` 覆写 `event.level`。于是「越线发生过」这件事实被「页发出去了没有」门控 —— 正是复审 §3.B 的一句话根因 | 克隆 `:555-570` | 读源 |
| F35 | 冻结真实账本 `state/live/ic_monitor.jsonl` 225 行: `rank_ic` **None 0 个, 非有限 0 个**; `value_ic`/`rank_ic_beta_resid` 同为 0 ⇒ **有限值门对真实数据零改动**(不改任何已发布数字) | 本人扫描 | 计算 |
| F36 | 研究员探针 `probe_causal_events.py` 读的是**冻结快照** `OUT/private/inputs/w1/ops/ic_monitor.py`(`probe_followup.py:18` `W1=OUT/'private/inputs/w1'`), **不是**克隆工作树 ⇒ 逐字重跑它只能证明「研究员的冻结证据没被我动过」, 不能测我的修改。且它的三条 assert **断言缺陷存在**(`a[1]['state']['event']['trigger_windows']==['r24']`、`a[2]` 投 `['INCOMPLETE','RECOVERED']`、`b[1]...['level']=='ALERT' and b[2]['deliveries']==[]`) ⇒ 指向修后码时**必须**在这些 assert 上失败, 这就是它的红能力 | `probe_followup.py:14-18`; `probe_causal_events.py` 末段 | 读源 |
| F37 | `probe_followup.py:15-17` 断言 `OUT` 在 codex worktree 内且该 worktree 当前分支 = `agent/codex/QNT-2026-0907/onboarding-audit` ⇒ 探针**只能在原地跑**, 不能整目录搬到 scratch | `probe_followup.py:15-17` | 读源 |
| F38 | 既有 76 格里被本轮改动波及的: M13 的注入靶行(冷却门原文)会消失 ⇒ 必须重新指靶, 否则「注入点恰一次」为 0 而红。其余 75 格的断言不需要改(T13c 的遗留事件精确字典**不加新键**即可保持) | 克隆测试 `live/tests_ic_monitor.py:733-736` | 读源 + 设计 |

### §8.2 设计决策(第三轮)

**D14 观测与投递分离(修 N1 + N2 的事实面).** 新纯函数 `observed_event(st, verdict, now)`: 本次 verdict 若 level ∈ {ALERT, DECIDE},
把**已观测的越线事实**写进事件 —— 触发窗取并集、`observed[level]=now`、必要时开新事件 —— **与页发没发出去无关**。
`plan_delivery` 与 `deliver` 都以它为准(前者只读不落盘, 保持纯函数; 后者把结果落 `st["event"]`)。
于是 N1 的第②步: 页被冷却扣住, 但 r48 进了 `trigger_windows`; 第③步 `_event_recoverable` 见 r48 ∉ judged_windows ⇒ **不恢复**。
- 被拒替代: 「冷却时也发页」—— 复审明写「这不要求实际多发消息」; 拒。
- 被拒替代: 「把 trigger_windows 的并集挪进 `plan_delivery`」—— 它是纯函数不落盘, 事实会在下一次 `open_event` 时丢失; 拒。

**D15 风险级别单调, 只由恢复降级(修 N2 的降级面).** 事件的 `level` = **当前未恢复的【已观测】风险级别**, 事件内**只升不降**;
唯一的下降路径是每个触发窗重新可判且未越线 ⇒ RECOVERED 关事件。旧码在每次成功投递时 `ev["level"] = p["kind"]`, 于是
「r48 未判、r24 只到 ALERT」被写成事件降级到 ALERT。新码在 `observed_event` 里按 `_rank`(OK0/ALERT1/DECIDE2)取 max。

**D16 冷却按「最后送达的级别」判升级(修 N2 的吞没面).** 新增 `delivered_level_of(ev)` = `ev["delivered"]` 里**时刻最大**的级别
(不落新字段 ⇒ 遗留事件/旧盘面状态逐位兼容, T13c 的精确字典不变)。`_breach_due(ev, level, now)`:
① 事件内还没有任何一页成功离机(新事件, 或上次投递失败)⇒ 投; ② `_rank(level) > _rank(delivered_level_of(ev))` ⇒ **相对手机上最后那页是升级** ⇒ 投, **不受旧的更高级别时钟约束**; ③ 否则按**本级自己的**送达时钟 24h。
- N2 第③步: 手机最后一页是 ALERT, 现在是 DECIDE ⇒ ②命中 ⇒ **投**。同级复发仍被 ③ 扣住(T8h/T13a 第四步不变)。
- 页数上界不变坏: 每级每 24h 至多一页 ⇒ 一个事件 24h 内至多 ALERT+DECIDE 两页。
- R-10(86,398 s 秒级抖动)仍是**同级**的已知开口, 本轮不动。

**D17 NaN/±Inf = 不可测, 不是健康(修 N3).** 新谓词 `_measurable(x)` = 有限实数(`bool` 排除)。
① `check()` 的行过滤由 `is not None` 改为 `_measurable` ⇒ 非有限行**不进 post**, 于是自动进普查的「缺」⇒ 缺超上限即该窗不判;
② 窗均值本身再过一道 `_measurable` 作纵深(`j24/j48`); ③ `r24_beta_resid` 同。
- 后果: 全 NaN 账本 ⇒ post 空 ⇒ `len(post)<24` 分支 ⇒ **INCOMPLETE**(不再 OK, 不再 RECOVERED)。
- 真实数据零改动(F35)。已知性质(明列, 非缺陷): 一行 NaN 会因 `known_ts` 幂等而**永不重算**, 成为永久普查洞 ⇒ 持续 INCOMPLETE —— 这是**响亮**的失败模式, 优于静默健康。
- 顺带闭一个**我自己这轮引入**的口: 观测会在投递失败/被冷却时也开事件, 于是可能出现「从未成功投出过任何页」的事件; 它若恢复, 旧逻辑会发一页 RECOVERED 给**从没听说过这次越线**的操作员。规则: RECOVERED 页要求 `delivered_level_of(ev) is not None`; 不满足则**静默关闭**事件(`closed_silently`), 不留僵尸。

**D18 不动的东西(明列):** 三个阈值常量、`WINDOW_START_TS`、`MAX_MISSING`、`LEGACY_TRIGGER_WINDOWS`、`COOLDOWN_S`、
`GRID_S`/`MATURE_LAG_S`; 五个数值函数 `_rankdata/_corr/_spear/load_anchors/compute_rows`(与线上 AST 相同, 一字不动);
统计量定义(最后 24/48 个**可用**行的均值 —— 「可用」的含义由 None 扩到「非有限」, 真实数据上是同一集合)。

### §8.3 测试矩阵(第三轮; 每条先红后绿 + 突变再红)

| 行为 | 绿断言(新格) | 突变(必须红) |
|---|---|---|
| D14 观测入事件 | T17a 研究员输入集 A 三步全跑 `deliver`: ①投 DECIDE/tw=['r24'] ②**零投递**但 **tw 变 ['r24','r48']** ③只投 INCOMPLETE、**无 RECOVERED**、事件仍开、last 仍 DECIDE; 数值逐位 (−0.045/−0.015, −0.020/−0.01708) | M16 `observed_event` 不并入本次触发窗 ⇒ T17a 红 |
| D14/D15/D16 | T18a 输入集 B 三步: ①投 DECIDE(r48) ②投 ALERT 但 **event.level 仍 DECIDE** ③ **投 DECIDE**(不被旧时钟吞), 数值逐位 (−0.021/−0.017, −0.02933/−0.02117, −0.06991) | M17 级别改回无条件覆写 ⇒ T18a 的 level 断言红; M18 去掉「相对最后送达级别升级」分支 ⇒ T18a 的第③步投递断言红 |
| D17 NaN | T19a 全 NaN 新鲜网格 ⇒ INCOMPLETE 且 judged=False(修前: OK/judged/两窗可判); T19b 同一夹具 + 已开 DECIDE(r48)事件 ⇒ **零 RECOVERED**; T19c 尾 24 里 3 行 NaN ⇒ r24 窗缺 3>2 不判, 且 r24 = 最后 24 个**有限**行的均值; T19d ±Inf 同 | M19 `_measurable` 退回 `x is not None` ⇒ T19a/T19b 红 |
| D17 附带口 | T20 观测开的事件(投递失败, 从未送达)恢复时 **不发 RECOVERED** 且事件被静默关闭 | M20 去掉 `delivered_level_of(ev) is not None` 前提 ⇒ T20 红 |
| 输入集自证 | T17b 两组输入集满足专项声明的合同: 4h 网格、逐步只追加(历史行逐位不变)、IC ∈ [−1,1] | — |
| 既有 76 格 | 全保留; **只改 M13 的注入靶**(靶行被 D16 改写, 语义不变: 冷却回旧全局键 `last_<LEVEL>` ⇒ T13a 红) | — |

### §8.4 收据(第三轮, 回填 01:5xZ)

**R11 修前复现(红).** 装置 `docs/receipts/w1_r3_repro_device.py`(sha `b48abd4a…6ff8`): 以研究员输入集
A/B + NaN 夹具跑**修前**克隆码, 逐位得到 §8.1 F31/F32/F33 的三张表 —— 与专项 RESULT.md §3 的
W1-N1/N2/N3 表**数值全同**(−0.045/−0.015 · −0.020/−0.01708 · −0.021/−0.017 · −0.02933/−0.02117 · −0.06991)。

**R12 套件单跑(修后).** `docs/receipts/w1_r3_ic_monitor_suite_standalone.log`(sha `f61ff692…9b6c`):
**94 项全 PASS / 0 FAIL / 0 SKIP**, exit 0(= 第二轮 76 + 第三轮 18: T17a/T17b/T18a/T19a-d/T20 共 8 绿格 +
M16-M20 各「注入点恰一次」+「突变红」共 10)。命令逐字:
```
cd /Users/haosiyu/cc_tmp/exec_w1/live && . ../ops/pyenv.sh && /usr/bin/python3 tests_ic_monitor.py
```

**R13 逐格红能力(修前源).** 装置 `docs/receipts/w1_r3_red_runner_device.py`(sha `3455bd5e…bfd3`): 把测试文件
每一处 `check(...)` 包进 try/except(崩溃也记 FAIL 而不中断), 再以**镜像树**(符号链接 live/state, 只换
`ops/ic_monitor.py`)跑整套 —— 克隆一个字节没动。
- 修前源 = 研究员冻结快照 `private/inputs/w1/ops/ic_monitor.py` sha `00921bc7…1f00`(与克隆修前逐位同, F29):
  日志 `w1_r3_suite_on_PREFIX_code_00921bc7.log`(sha `e82f50d6…d7dc`), **75 PASS / 13 FAIL**。
  13 红 = **7 个新绿格全红**(T17a · T18a · T19a · T19b · T19c · T19d · T20「CRASHED: KeyError: 'event'」)
  + 6 个突变注入靶 count=0(M13 靶行被本轮改写; M16-M20 的靶是本轮新码)。
  **T17b 在两侧都绿** —— 它断言的是研究员输入集自身的性质(4h 网格 / 只追加 / IC∈[−1,1]), 不是我的码, 应当如此。
- origin/main `918559f`(`ops/ic_monitor.py` sha `ba89bf68…162f`): 日志 `w1_r3_suite_on_OLD_code_918559f.log`
  (sha `854cde61…cb8d`), 7 PASS 后在 `tests_ic_monitor.py:90` 崩 `AttributeError: MATURE_LAG_S` —— 旧码连新格都到不了。

**R14 研究员探针(他们的装置, 他们的输入集).**
- **逐字重跑(在原地, 未改一字节)**: `cd <monitoring> && /usr/bin/python3 -B probe_causal_events.py` ⇒ **exit 0**;
  日志 `w1_r3_researcher_probe_verbatim.log`(sha `b7509455…ac98`)。运行前后该目录 6 个 json 收据
  **sha 逐位不变**(`causal_event_receipt.json` 被确定性重写为同样字节)。
  ★ 注意(F36): 它读的是**冻结快照** `private/inputs/w1/`, **不是**克隆工作树 —— 所以 exit 0 只证明
  「研究员的冻结证据没被我动过」, **不**证明我的修改。
- **指向修后树**: 同一探针只改两行路径(`newpath` → 克隆工作树; 收据写到 scratch), 其余逐字节不动 ⇒ **exit 1**,
  在 `assert a[1]['state']['event']['trigger_windows']==['r24']` 上失败 —— 这正是它编码 N1 的那一行。
- **逐条断言矩阵**(装置 `w1_r3_probe_assertion_matrix_device.py` sha `20cd9250…5c54`; 日志
  `w1_r3_researcher_probe_assertion_matrix.log` sha `6e24c150…e263`):

| 探针里的断言 | 冻结 round-2 `00921bc7` | 修后 `a085d471` |
|---|---|---|
| A1 `trigger==['r24<R24_P1']` (非缺陷断言) | HOLDS | HOLDS |
| A2 `trigger==['r48<R48_P1']` (非缺陷断言) | HOLDS | HOLDS |
| A2 `deliveries==[]` 同级冷却仍扣住页 (非缺陷断言) | HOLDS | HOLDS |
| A2 `event.trigger_windows==['r24']` **★N1** | HOLDS | **FAILS** → 实际 `['r24','r48']` |
| A3 `deliveries==['INCOMPLETE','RECOVERED']` **★N1** | HOLDS | **FAILS** → 实际 `['INCOMPLETE']` |
| B2 `event.level=='ALERT'` **★N2** | HOLDS | **FAILS** → 实际 `DECIDE` |
| B3 `verdict.level=='DECIDE'` (非缺陷断言) | HOLDS | HOLDS |
| B3 `deliveries==[]` 升级被旧时钟吞 **★N2** | HOLDS | **FAILS** → 实际 `['DECIDE']` |

⇒ **四条缺陷断言全部翻红, 四条非缺陷断言全部不动**(统计量、触发门、同级冷却对页的抑制都原样)。

**R15 不动量的直接复核.**
- 五个数值函数 `_rankdata/_corr/_spear/load_anchors/compute_rows` 与**运行树** `~/dl_quant_live/ops/ic_monitor.py`
  (sha `ba89bf68…162f`, 只读打开)**逐个 `ast.dump` 相等**: 5/5 True。
- 阈值三常量、`WINDOW_START_TS=1786363200.0`、`MAX_MISSING`、`LEGACY_TRIGGER_WINDOWS`、`COOLDOWN_S`、
  `GRID_S`、`MATURE_LAG_S` 一字未动(T1d/T9/T13c 在套件内钉)。
- 冻结真实账本 225 行 `rank_ic` 非有限 **0 个**(F35)⇒ 有限值门在真实数据上是恒等变换; T9g(09-12 01:30Z
  回放 r24=+0.00472/r48=−0.01104/n=176)**仍绿**。
- `ops/gate_coverage.py verify` exit 0; `tests_static_names`(pyflakes)exit 0。
- 只读门未退化: T10a/T10b/T10c/T14 全绿; 另在克隆真实回读上直跑 `ops/ic_monitor.py --check` ⇒
  账本/状态 sha 前后相等, evals 文件从未创建, 输出 `INCOMPLETE`(克隆快照前沿 09-12 20Z vs 实际最新行
  09-12 04Z, 缺 8/13 —— 这是**克隆快照**的陈旧度, 不是对在役状态的陈述)。

**R16 diff 与 sha(第三轮最终树).**
- `docs/receipts/w1_ic_monitor_contract.diff`: **1701 行, 3 个 `diff --git`**(只含 `ops/ic_monitor.py`、
  `live/tests_ic_monitor.py`、`ops/gate_coverage.py`), sha256
  **`62a3032e1b9c9d80e0a799e06bae925c3e416b56e2cd701b5cd280db45808392`**。生成命令逐字:
  `git -C /Users/haosiyu/cc_tmp/exec_w1 diff origin/main -- ops/ic_monitor.py live/tests_ic_monitor.py ops/gate_coverage.py`
- 克隆代码(第三轮修后): `ops/ic_monitor.py` `a085d47182f5033c54f38e7471433c35250b94bba4e9db20a9b2c14d47e32589`(748 行,
  第二轮 645)· `live/tests_ic_monitor.py` `983726eccc5a77be177786a32724a542a5c570d750d80bf756e12816f68b9493`(986 行,
  第二轮 774)· `ops/gate_coverage.py` `dc60d57e2b3f3d4fc4c858d495135f56cfaec3d61e4fa0ff903ff4593862dd33`(401 行)。
- **未做**: 全电池未跑(lead: 落地时跑叠加电池); 克隆不提交不推送; 运行树 `~/dl_quant_live` 与生产者
  `~/wide_shadow` **零写入**(只 `ast` 读过运行树那一个文件); 零网络/Telegram/.env; 研究仓只写
  `docs/DESIGN_…md` 与 `docs/receipts/`(均未提交)。

### §8.5 RESULT(第三轮)

**改了什么(`ops/ic_monitor.py` 645 → 748 行):**
- `_measurable()` / `_rank()` 两个新谓词, 置于五个数值函数**之前**(那五个一字未动)。
- `check()`: 行过滤 `is not None` → `_measurable`; `resid` 同; `j24/j48` 增加「窗均值本身可测」一道纵深。
- `observed_event(st, verdict, now)`(纯函数): 把**本次观测到的越线**记进事件 —— 触发窗并集、`observed[级]=now`、
  必要时开新事件; 风险级别取 `max`(事件内只升不降)。`plan_delivery` 与 `deliver` 都以它为准。
- `delivered_level_of(ev)`: 最后一次成功离机的级别 = `delivered` 表里时刻最大者(**不落新字段**, 遗留/旧盘面兼容)。
  `last_delivered_level(st)` 改用它 —— 与 `event["level"]` 正式分家。
- `_breach_due(ev, level, now)`: ①事件内未送达过 ⇒ 投 ②相对**最后送达级别**升级 ⇒ 投(不受旧高级别时钟约束)
  ③否则本级自己的 24h 时钟。`plan_delivery` 的冷却门改调它。
- `plan_delivery` 的 RECOVERED 分支加前提「该事件确实送达过页」; `deliver` 对「从未送达过」的事件在恢复条件
  成立时**静默关闭**(`closed_silently`), 不发页也不留僵尸。
- `deliver`: 观测**先于**计划并落盘; 成功离机**只**推进 `delivered[级]` 时钟(不再覆写 level/并触发窗)。
- `_event_line(event, now)` / `body_breach(v, event, now)`: 新开事件说「新开」, 否则多打「最后送达级别」与
  「已观测 {级} 于 {时刻}」—— 被冷却扣住的越线在页面上**看得见**。
- 模块 docstring 的告警合同段按上述重写。

**每条缺陷的关闭证据(红→绿→再红):**
| 缺陷 | 绿格 | 修前红 | 突变再红 |
|---|---|---|---|
| N1 冷却中的新触发窗丢失 ⇒ 误恢复 | T17a(输入集 A 三步全跑 deliver) | PREFIX 日志 T17a FAIL | M16(观测不并入本次触发窗) |
| N2 触发窗未判仍降级 | T18a(输入集 B, `event.level` 断言) | PREFIX 日志 T18a FAIL | M17(级别无条件覆写) |
| N2 再升级被旧时钟吞 | T18a(第③步投递断言) | 同上 | M18(去掉「相对最后送达级别升级」) |
| N3 NaN 当新鲜可判并发恢复 | T19a/T19b/T19c/T19d | PREFIX 日志四格全 FAIL | M19(可测性退回 `is not None`) |
| (本轮自带口)从未送达的事件发 RECOVERED | T20 | PREFIX 崩 `KeyError: 'event'` | M20(去掉「送达过」前提) |

**阈值声明(lead 点名要写明):** 本轮**没有**重标阈值。`R24_P5/R24_P1/R48_P1` 仍是 **α=0.05/band=0.002 的旧标定对象**
(2026-08-10, 9821 锚离线书), 在役书是 α=0.1/band=0.00025; 每页仍逐字打印这一错配。重标 = OUT OF SCOPE,
等生产者平价回放 Phase 2。

**未关(明列):** ① 事件内**同级** 24h 严格冷却 vs 01:30Z 秒级抖动(R-10)仍是已知开口 —— 本轮只让「相对最后
送达级别的升级」不再被吞; ② 一行 NaN 会因 `known_ts` 幂等而永不重算, 成为永久普查洞 ⇒ 持续 INCOMPLETE
(响亮失败, 非静默健康 —— 明列为**性质**而非缺陷); ③ launchd 实际每日触发无断言; ④ 数学路径的口径保留项
(下一快照有仓才入样、显式零仓丢弃、隐含价非固定 E 时刻、无费用/资金费)不在本单, 不宣布关闭;
⑤ 复审 §3.B 末句「本次没有证实线上真实发过这两组序列」—— 我也**没有**证实; 两组都是合成可达序列。
