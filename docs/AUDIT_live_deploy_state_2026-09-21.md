# AUDIT — 实盘部署状态单一真相表 (2026-09-21)

> **创建:** 2026-09-21 | **Session:** AUDIT-DEPLOY-0921 | **状态:** 现行 | **作废条件:** 执行器树离开 `409ea16`, 或生产者 `fea171/`、`shadow_loop_v3.py` 任一 sha 变化, 或本表任一 `[CODE]` 行被复测推翻

**这是状态审计, 不是处置建议。本文不建议合并、删除或部署任何东西。**

---

## §0 方法与边界

**只读。** 本审计没有修改、提交、检出或删除 `~/dl_quant_live` 与 `~/wide_shadow` 的任何内容, 没有运行执行器, 没有调用交易所。分支内容通过 `git archive <branch> | tar -x -C <scratchpad>` 取出 — 该命令不写仓库、不建 worktree。收工复核:

```
$ cd /Users/haosiyu/dl_quant_live && git rev-parse HEAD
409ea162746d0ba459db33c3f5c07865c24a7514
$ git status --porcelain=v1 | grep -v '^?? ' | grep -vcE '^\s*[MD]\s+state/'
0
```

**解释器身份(KB-73)。** 本文所有套件均以 `/usr/bin/python3` (`Python 3.9.6`) 运行, 与 `com.dlquant.live.anchor.plist` 的 `ProgramArguments[0]` 同。`run_acceptance.sh:28` 实测为 `PY="${ACCEPT_PY:-/usr/bin/python3}"` — 可覆盖缺省, 非硬钉, KB-73 原文成立。本文**不引用任何逐套件 N/M 计数作为通过证据**; 每条都给判词整行 + 退出码。

**行的来源标记 — 这是本表最重要的一列语义。**

| 标记 | 含义 |
|---|---|
| **`[CODE]`** | 我本人对 `409ea16` 的部署代码 / 磁盘配置 / 实盘台账直接复核过。这是本表唯一算数的证据等级。 |
| **`[DOC]`** | 只有文档受据, **我没有对代码复核**。状态是那份文档写作日的状态, **不是今天的状态**。 |

**为什么这个区分是本审计的主要产出:** 本轮有 **三条** `[DOC]` 状态被 `[CODE]` 复核推翻 (EXE-01、W6C-I6、OPS-01b — 文档说"未部署", 代码里在役)。凡 `[DOC]` 行, 按"可能已过期"读。

---

## §1 已核实的地基

| 事实 | 收据 |
|---|---|
| 执行器运行树 = 工作目录 `/Users/haosiyu/dl_quant_live`, 由 PID 17116 `scheduler/run_anchor.py` (启于 2026-09-21 00:00:00 +08) 执行 | `ps -Ao pid,ppid,lstart,command`; `launchctl list` → `17116 0 com.dlquant.live.anchor` |
| 该树代码 == `main` == `origin/main` == `409ea16`, 0 ahead / 0 behind | `git rev-list --left-right --count origin/main...HEAD` → `0	0` |
| **该树代码是干净的**: `state/` 之外零脏的已跟踪文件、零未跟踪文件 | 上方 §0 命令输出 `0`。(未跟踪目录 `rollback_*/`、`staging_batch1/`、`staging_s2gen/`、`.rollback_latest` 存在于 `state/` 之外, 但不在 `run_anchor.py` 的 import 路径上 — **未逐文件验证其内容**) |
| 本地分支共 **7** 条(含 main)。**4 条未并入** main: `blindspot-halted-book`、`queued-b7-cond3-thresholds`、`fp3/nosleep-asl-reader`、`fp3/nosleep-stat-unknown`。另 2 条 `volscale`(d997767)、`review/b0a573a1-executor`(b681ca5) **merge-base == 自身 HEAD ⇒ 已是 main 的祖先, 已并入** | `git for-each-ref refs/heads/`; `git merge-base main volscale` → `d9977675…`(== volscale HEAD); 同理 b681ca5 |
| 生产者 `~/wide_shadow` **不是 git 仓库** | `ls ~/wide_shadow/.git` → `No such file or directory`; `git rev-parse --show-toplevel` → `fatal: not a git repository` |

> lead 交付的地基我逐条复核: 运行树身份、0/0、远端、"4 条未并入"**全部成立**。`~/wide_shadow` 无 VCS 亦成立。

---

## §2 主表 — 每行一个已知实盘侧问题

### 2.1 三条被点名的"无修复"声明 — **三条全部未通过复核**

| 问题 | 存在的证据 | 修复在哪 | 已部署? | 若否, 为什么 | 留着的风险 |
|---|---|---|---|---|---|
| **EXE-01 看门狗比例响应** — 声称"任何触发仍整书平仓" | `docs/audit_pipeline_2026-09-13/AUDIT_EXEC.md:55` "Any watchdog trip still flattens 100% of the book; the proportional response W6(c) is not deployed" | **在役**: `live/watchdog.py:390-391` `PROPORTIONAL_MAX_NAMES = 5` / `PROPORTIONAL_MAX_FRAC_OF_GROSS = 0.02`; `:402` `def proportional_switch()`; 路由 `:2527`/`:2583`; 写入 `scheduler/anchor_loop.py:2960-2961` | **[CODE] 是。** 磁盘 `config/book.json:177-178` `"watchdog_proportional_response": {"enabled": true}`, 与 `409ea16` 树内同 | — | **声明本身是风险**: 见 2.5 "过期判词"行 |
| **DERISK 迟到参考规则** | `docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:1479` 规则全文, 结尾 "零部署" | **在役**: `scheduler/anchor_loop.py:3245` `_late = state.setdefault("stale_ref_late", {})`; `:3250` 写 `{"value":…, "frac_at_adoption": frac, …}`; docstring `:3201-3217` | **[CODE] 是**(代码在役)。⚠ 但 `STATE.md:117`(09-18, **晚于**部署)写"保持现版本…**随 Q6 影子验收后再部署**" — 库里两句未对账 | 未对账 | 低(见下"从未执行"); 但**台账与代码不一致本身是活口** |
| **I6 非计划运行平掉整本书** | `FIXPROGRAM_2026-09-13.md:354` §17.1 标题; `:361` `dev_frac 0.9639` / `flatten_all 105 单`; **机制我本人复核**: `com.dlquant.live.anchor.plist` 有 6 个 `StartCalendarInterval` 时刻且**无 `RunAtLoad`** | **在役**: `live/position_break.py:182` `BOOK_HELD_HALT_KINDS = ("proportional_local", "book_unobserved", "off_schedule")`; 写者 `scheduler/anchor_loop.py:2964-2965`; 套件 `live/tests_offschedule_held_book.py` 在树内 | **[CODE] 是。** | — | **残留**: caffeinate (`/usr/bin/caffeinate -ims` PID 815) 仍是唯一防线(`FIXPROGRAM…:369` "单点"); "非计划运行是否本就不该可能"(gate 0c)未触碰 |

> **结论: lead 的三条"无修复"声明, 零条存活。** 三条的修复都在 `409ea16` 里在役。来源是 09-13 的审计文档, 它早于 09-17 02:06Z 的 `6661ea3` 部署。

### 2.2 ★ 但"已部署"不等于"已生效" — 本审计最硬的一条新发现

`[CODE]` 闭合人口测量, 带正控:

```
LIVE 台账  state/live/pilot_log/*/anchors.jsonl : 51 文件 / 299 行
DRY_RUN    state/pilot_log/*/anchors.jsonl      : 518 行
  含 halt_kind 键的行(任意值, 两棵树合计)       : 0
  halt_kind=proportional_local                  : 0
  halt_kind=book_unobserved                     : 0
  halt_kind=off_schedule                        : 0
正控: 同一批行里 opening_halted=true             : 19   ← grep 有效
正控: 最近一行 LIVE 的键集里无 halt_kind, 有 opening_halted
```

```
state/anchor_runs.log (38,958 行 / 305 次 'anchor start mode=LIVE'):
  stale_ref_late / derisk_recovered / derisk_unknown / derisk_resolved_flat
  / QuantityNotFinite / flatten_skip_nonfinite  : 各 0
```

**⚠ 仪器更正(自查抓到)**: `halt_kind` 在 `anchor_runs.log` 里出现 **0** 次 — 那棵日志**根本不是这个字段的写入目标**, 拿它测会得到一个空洞的零。真正的写入目标是 `anchors.jsonl`。上表是改用正确仪器后的结果, 并带正控。

**但这个零不是缺陷证据。** 19 个 `opening_halted` 的 LIVE 锚, 换算成 UTC 后**最后一个是 `2026-09-13T08:24:02Z`** — 全部早于 `6661ea3` 部署 (09-17 02:06Z) 与 `409ea16` 部署 (09-18 02:46Z)。

| 问题 | 存在的证据 | 修复在哪 | 已部署? | 若否, 为什么 | 留着的风险 |
|---|---|---|---|---|---|
| **三条新防御路径生产可达性未经证实** | `[CODE]` 上方闭合人口: 部署后零次停机锚, 三个 halt_kind 与六个 derisk 动作在役台账中出现次数 = 0 | 不适用(是覆盖缺口, 非缺陷) | 代码已部署, **行为从未在生产中发生过一次** | 部署至今 4 天, 期间**零个**停机锚 ⇒ 零次机会。**不是写者坏了** | 与 `suite_certifies_a_state_production_cannot_construct`(10% 死区 272/272 锚从未生效)同形。首次真实触发即首次生产验证 |

### 2.3 四条未并入分支 — 逐条 `[CODE]` 裁决

**关键发现: 四条全部是已被取代的陈旧分支, 没有一条携带 main 所缺的待部署修复。** 两条 fp3 是 9 月的, 两条是 **7 月** 的(距今 7 周以上), 其 commit message 里的"未接线"描述的是**当时**的状态。

| 分支 | HEAD / 日期 | 代码改动(排除 state/log) | 内容在 main 里吗 | 干净抽取跑它自己的套件 | 裁决 |
|---|---|---|---|---|---|
| **`fp3/nosleep-stat-unknown`** | `30bec90` 2026-09-18 | `ops/check_nosleep.py`, `live/tests_nosleep.py` | **逐字节相同**: `ops/check_nosleep.py` blob `e8361e71…` == main; `live/tests_nosleep.py` blob `da02df22…` == main; `scheduler/run_anchor.py` blob `ef00c8ff…` == main | `ALL PASS` **rc=0** | **完全被取代。** main 就是它。`git cherry main` 标 `-`(已上游) |
| **`fp3/nosleep-asl-reader`** | `48ea820` 2026-09-18 | 同上三文件 | **严格落后 main**: main = 本分支 + R7-K1 (`+24 / −3` 行)。唯一差异见 `git diff 48ea820 main -- ops/check_nosleep.py`: `_asl_files` 对 stat 失败的文件由 `continue` 改为 `out.append(p)` | `ALL PASS` **rc=0**(但只 45 行判词 vs main 48 — 缺 A3b/A3c/A3d 三格正负控) | **被取代, 且是更弱的版本。** main 的祖先链 `58256ed → 81ea654 → d858c36 → 409ea16` 已含其内容 |
| **`queued-b7-cond3-thresholds`** | `8917959` **2026-07-30** | 7 commits; `live/watchdog.py`、`live/position_break.py`、`live/binance_broker.py`、`scheduler/run_anchor.py`、`ops/capture_halt_evidence.py`、`ops/gate_coverage.py`、`run_acceptance.sh` + 新增 `ops/ack_stuck_position.py` 与 6 个套件 | **语义已全部落在 main**: `ops/ack_stuck_position.py` 在 main(blob `6c33f976…`), 含 symbol+qty 钉 (`:22`) 与 TTL (`:60` "AN ACK EXPIRES (ruling 2026-07-30)"); "从不说话的告警档"= `watchdog_investigate`, 在 main 接线于 `scheduler/run_anchor.py:630,641`; `ops/capture_halt_evidence.py` **blob 与 main 逐字节相同** (`6342d59d…`); 6 个套件全在 main | 6 个套件全部 `ALL PASS` **rc=0**(20/`ALL PASS`/`ALL PASS`/15/16/19 检查) | **内容已落地, 分支陈旧。** main 的同名文件是这些文件的**后代**(blob 不同), 故 `git cherry` 标 `+` — patch-id 不同不等于内容缺席 |
| **`blindspot-halted-book`** | `f363621` **2026-07-28** | 新增 `live/position_break.py` (387 行) + 其套件。**merge-base `18bb9e33` 之后 main 已走 257 个 commit** | **语义已落在 main**: `halted_intent_flat` 状态 (`main:live/position_break.py:333` `"kind": "halted_intent_flat"`)、`flat_intent_legacy` 门 (`:853-854`)、1% 平意图限额 (`:836`)、ack 排除 (`:893-895`) 全在 main | **`FAILURES: ['★★ every one of them is CLEAN', '   their deviation is exactly zero — the book really was flat']  (31 checks)` rc=1**(连跑两次同 rc) | **被取代, 且它自己的套件在干净抽取下是红的** |

#### 2.3.1 `blindspot` 红的根因 — 一条独立的装置缺陷

该套件**不是自足的**: `live/tests_position_break_blindspot.py:45`

```python
LEDGER = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
```

它把断言钉在一个**树外的、会变的实盘 testnet 台账**上。7 月写下时那 14 个停机锚恰好全 CLEAN; 今天同一路径里多了一个 `07-31 12:00Z: BREAK`, 断言即破。失败输出逐字:

```
FAIL  ★★ every one of them is CLEAN  — {…, '07-31 12:00Z': 'BREAK', '08-01 00:01Z': 'CLEAN'}
FAIL     their deviation is exactly zero — the book really was flat  — [0.0, 0.0, 0.0, 0.0]
```

- 它 `:3` 自称 "READ-ONLY: opens state/testnet/pilot_log for reading and writes nothing anywhere" — 读这一点属实, 本次运行没有写任何东西。
- **这条红不证明 main 有问题**: main 里同名套件在同一台机器、同一抽取方式下 `ALL PASS (43 checks)` rc=0 —— 后续版本已经处理掉了这个非自足性。
- 这是 `textual_instrument_for_a_behavioural_property` / 非自足夹具一族: **夹具在被测对象之外且可变 ⇒ 该套件无论绿红都认证不了那个 commit。** 它在 7 月的绿, 认证的是 7 月那天的台账。

### 2.4 生产者侧 — "版本"在这里意味着什么

`~/wide_shadow` 无 VCS。**唯一的版本身份是文件 sha256**, 唯一的历史记录是三样东西: 带日期的备份件名、研究仓快照、以及 `docs/PRODUCTION_INTERVENTION_LEDGER.md`。

**在役文件现况 `[CODE]`**(`shasum -a 256` 前 16 位; mtime 为本机 +08):

| 文件 | sha256[:16] | mtime |
|---|---|---|
| `shadow_loop_v3.py`(PID 797 在跑) | **`e9c9837412130884`** | 2026-09-04 08:53 |
| `fea171/combo_stage.py` | **`3520d36394fbe7b9`** | 2026-09-17 21:09 |
| `fea171/sidecar_blend.py` | `6140790e55b70cff` | 2026-08-26 10:22 |
| `fea171/f8_higher_order_features.py` | `2c500c7ad2bb0f5d` | 2026-08-24 15:07 |
| `fea171/dlw_features.py` | `29ae6a985d891e56` | 2026-08-24 15:10 |
| `fea171/combo_live_daemon.sh` | `72f78d1e6be51b2b` | 2026-08-26 10:25 |
| `fea171/sidecar_daemon.sh` | `01d75619183da425` | 2026-08-24 18:48 |
| `fea171/combo_state_snapshot.sh` | `14da59a87a8492fd` | 2026-09-18 00:16 |
| `tests_target_live_output.py` | `b64fb36eb69ec2a6` | 2026-09-04 19:53 |

进程与装载(`launchctl list`): `com.hsy.shadowloop`(PID 797)、`com.hsy.combolive`(812)、`com.hsy.sidecar`(801)、`com.hsy.combosnap`、`com.hsy.comboparity`。

| 问题 | 存在的证据 | 修复在哪 | 已部署? | 若否, 为什么 | 留着的风险 |
|---|---|---|---|---|---|
| **FX-PROD 整包(PROD-27/41/42/43/46/47, P1/P2/P9)从未换入** | `[CODE]` 在役 `shadow_loop_v3.py` = `e9c98374` = 换装前 sha, mtime 停在 **2026-09-04** | 克隆 `b891748..bdb9e1f` | **否** | `[DOC]` `FX_PROD/SWAP_PLAN_FX_PROD.md:1` "DRAFT — not executed" | 见下逐条 |
| **PROD-42** 生产者曾整锚不产 king 文件(08-29 20Z), 守卫 `[ -f "$TL" ]` ⇒ 循环体不跑, 无页报, 执行器轮询 21 次 miss, 整锚 HOLD | `[DOC]` `FIXPROGRAM…:257` (P1) | FX-PROD 克隆 | **否** `[CODE]` sha 未变 | 同上 | 整锚冻结且无告警 |
| **PROD-43** combo 守护的**每一条**告警路径在生产中从未执行(125 锚 0 PAGE/0 skip/0 ABORT); `_page` 吞异常 ⇒ bail + 通道坏 = 端到端静默 | `[DOC]` `FIXPROGRAM…:258` (P1) | FX-PROD 克隆 | **否** | 同上 | 与 `gate_exists_but_its_verdict_does_not_control_the_write` 同族 |
| **PROD-27** combo 重写最坏只剩 9 s 余量; 生产者迟到即静默跳过重写 ⇒ 该锚按 king 形态交易且无页报 | `[DOC]` `FIXPROGRAM…:155`; 登记 `AUDIT_PROD.md:477` | FX-PROD 克隆 | **否** | 同上 | 书形态静默降级 |
| **PROD-46** 侧车 `LAST` 是内存 shell 变量 ⇒ 重启后重跑**过去**的锚并在数小时后覆写其链状态; 4 次实例, 其中 2 次把事后重写的状态喂给了随后的实盘锚 | `[DOC]` `FIXPROGRAM…:293` | FX-PROD, 排在 PROD-27 后 | **否** | 同上 | 实盘锚吃到被追溯改写的状态 |
| **PROD-41** 生产者门 G1/G2 仍按已退役的 N+23:00 标定, 执行器读 N+24:00 ⇒ G1 比首读早 85 s 关门 | `[DOC]` `STATE.md:280` | 待用户裁定(属书行为) | **否** | 待裁定 | ⚠ 后果句已被撤回: `CONCLUSION_dialectical_review_2026-09-16.md:31` "该门从未截断过一次本可以完成的运行" |
| **P1/P2 第 80 列 train-v0 / serve-v1** — 训练用逐结算原始 funding EMA, 服务用 8h 归一化 EMA ⇒ 4h 名 2×、1h 名 8×; 第 7 重要特征; 82% 在役 gross 落在非 8h 名上 | `[DOC]` `STATE.md:151` | FX-PROD 克隆 `fx_prod_P1.diff` | **否** `[CODE]` sha 未变 | 同上 | 在役模型的一个主要输入口径与训练不符 |
| **E-0907-B** combo 混合后不重施逐名帽: 20/20 锚有 2–10 个超帽名, 中位超 3.0% | `[DOC]` `ERROR_LEDGER…:501`; `[CODE]` 帽确实存在于 `combo_stage.py:85-86` (`capw` + `np.clip`) — **但我没有确立它相对混合步骤的先后**, 见 §4 | `[DOC]` "登记, 不修" | **否** | 混合后施帽 = 书行为改动, 需预注册 + 用户字 | 逐名集中度超设计值 |

**生产者干预台账的回填**: `docs/PRODUCTION_INTERVENTION_LEDGER.md` `[CODE]` 29 行, mtime 2026-09-18 16:56, 立于 2026-09-18。它**自己声明不完整**(末段): "上表**仍不完整**…九月还缺 09-01 模型换装的逐项受据与中间版本; 已补登的三行标「待逐项取证」的部分只写了已知锚位与来源文档, 不当作已取证。"

- **可回填的(证据尚存)**: 带日期+sha 的备份件 — `fea171/combo_stage.py.pre_fp2-6b_20260917T1259Z_b5c698f9`、`.pre_ftrim_20260902_backup`、`shadow_loop_v3.py.pre_m1_20260904_backup`、`.bak_predemeanfix`、`sidecar_blend.py.bak_preE0825A/.bak_prebtcv/.bak_predemeanfix`、`shadow_loop_v3_calfix_candidate.py.WITHDRAWN_wrong_caliber_20260904`; 研究仓快照 `multi_asset/exports/live/wide_shadow_snapshot*/`(含 `combo_stage_2026-09-01_pre_ftrim.py`、`combo_stage_2026-09-02_ftrim.py`、`combo_stage_2026-09-17_fp2-6b_f10sha.py`、`shadow_loop_v3.py.m1_20260904`); 以及 `state/snap/` 下 **166 个文件 / 26 个按锚 epoch 的目录**, 最早 `1789646400`。
- **不可复原的**: (a) `state/snap/` 归档**始于 2026-09-18**(最早目录 mtime 09-18 10:36), 此前滚动三件每锚整份重写 ⇒ **09-18 之前的逐锚生产者状态只能靠身份核对, 不能取回**; (b) 没有备份件对应的中间版本 — 任何"改了又改回"的编辑在 mtime 上不留痕, sha 也不留痕; (c) 09-01 模型换装的逐项受据(台账自述待取证)。
- **回填要做的事**: 对每个备份件与快照算 sha256, 与台账现有行对齐; 用 mtime 定"代码换入", 用 `shadow_log.jsonl` / `loop.out` / `combo_live_daemon.log` 的首现字段定"首锚产出"; 两者不一致时按台账末段的四事件语义(代码换入 / 状态播种 / 首锚产出 / 执行器消费)分别记。

### 2.5 执行器侧其余已知问题

`[CODE]` = 我复核过; `[DOC]` = 只有文档受据。

| 问题 | 存在的证据 | 修复在哪 | 已部署? | 若否, 为什么 | 留着的风险 |
|---|---|---|---|---|---|
| **OPS-01b σ_fund gross 梯子读取端** — 声称"读取端仍在, 任何人手写 g=0.5 文件即减半 gross" | `[DOC]` `FIXPROGRAM…:57` | **已修且在役**: `scheduler/anchor_loop.py:1965-1971` 注释 "WITHDRAWN, AND NO LONGER READ (OPS-01b)" … "No file sets exposure any more"; `:1976-1977` 硬写 `{"src":"sigma_ladder","g":1.0,"accepted":False,"reason":"retired_not_read"}`; `live/sigma_ladder.py` 留着但锚路径不 import | **[CODE] 是** | — | **文档过期** — 第三条被推翻的 `[DOC]` 状态 |
| **E-0918-P `reduce_only` 决定行为却不在订单台账里** | **[CODE] 我独立复测**: `state/live/pilot_log/*/orders.jsonl` 51 文件 / **97,787 行**, 含 `reduce_only` 的 **0 行**; **正控** 同批含 `reduceOnly`(驼峰) **311 行** ⇒ grep 有效。(文档当时数为 64,544 行 / 49 文件, 差额是新增天数) | `[DOC]` `ERROR_LEDGER…:761` "**只报不修** … **历史行补不回来**" | **否** | 修在执行器侧属实盘书, 按纪律不碰 | 事后无法从台账判定一笔单是否 reduce-only |
| **§4-4 是单向开关** — 触发后书被平成空仓 ⇒ 累计值永不回升 ⇒ `resume_from_trip.sh` 永久拒绝, 人的恢复决定无法执行 | `[DOC]` `docs/PREREG_s44_resume_reference_2026-09-21.md:9`; `[CODE]` §4-4 确在役: `live/watchdog.py:131` `DRAWDOWN_LIMIT_PCT = -25.0`, `:1853` 时间加权起始权益口径 | 预注册件; 用户裁定已给(2026-09-21) | **否** | `[DOC]` "实现落在分支, 不合 main, 不部署" | 触发即永久停机 |
| **§4-4 恢复链从未被执行过一次**; 实跑演练抓到演练装置自己空转(`--without-arm` 从未接上) | `[DOC]` `STATE.md:5` (E-0920-G) | 提案把空跑演练列为部署前门 #1 | **否** | 提案待裁定 | 唯一的恢复路径未经测试 |
| **§4-2 划转盲区** — 前一日最后一行 NAV 至 00:00Z 之间的划转不可见; `external_flow_usdt` 自然日累计且跨资产按数量相加 | `[DOC]` `docs/RULINGS_best_recommendation_2026-09-19.md:13` | 执行器克隆 `1c888279`, 分支 `fix/watchdog-flow-window-2026-09-19` | **否** | `[DOC]` `:50` "先交独立研究员复审这份改动, 通过后再按部署协议上线" | 日损守卫在划转日失明; 现行缓解是 20:40Z→00:00Z 不划转 |
| **EXE-01 比例门的 2% 分母取自被判锚** ⇒ 陈旧锚用更旧的 gross 定价 | `[DOC]` `FIXPROGRAM…:378` "已报告, 未重基, 数值 NOT CHECKED" | 无 | **否** | 未重基 | 比例门在陈旧锚上判据失准 |
| **EXE-03 / P8** 执行器去均值把生产者小空头翻成多头(109 个 combo 锚中 99 个) | `[DOC]` `AUDIT_EXEC.md:58`; `FIXPROGRAM…:159` | FX-BOOK **待派** | **否** | 书行为, 需回放配对 | 腿方向与生产者意图相反 |
| **EXE-04 / Q6** 逐窗对账 ⇒ 未解释余额一个锚后自行消失 | `[DOC]` `AUDIT_EXEC.md:59`; `FIXPROGRAM…:222` "数学已接受未落码" | 影子 v5 已建 | **否** | `[DOC]` `STATE.md:117` "批独立实现 + 副本影子验收, **不批改生产动作**; 部署另裁" | 对账可漏报 |
| **EXE-02 / E4** 止损与退出残差经 chase 臂用 **taker** 补单, 与 maker-only/no-chase 的止损条款矛盾 | `[DOC]` `AUDIT_EXEC.md:57` | 裁定 R2′(a) 保留 | 不适用 | 已裁定保留 | 成本口径与条款不符 |
| **E-0918-J** 保护性平仓腿的 `submit_ts` 记的是写入时刻 ⇒ 成交早于下单(1,732 行, 其中 1,692 行 >1 s) | `[DOC]` `ERROR_LEDGER…:696` | `[DOC]` `:700` "修在执行器侧, 需预注册与用户字" | **否** | 同上 | 时序归因不可用 |
| **E-0918-L** 一次平仓在本地台账里**订单与成交都没有**(08-21 16:23:09, 两个名) | `[DOC]` `ERROR_LEDGER…:709-711` | `[DOC]` `:712` "本轮只报不修" | **否** | 同上 | 台账不闭合 |
| **LED-02** 09-12 平仓 255 条订单行无费用无成交行, 读者标记全部未定价且回填后仍未定价 | `[DOC]` `AUDIT_EXEC.md:70` | FX-EXEC2 | **否** | 待裁定 | 成本不可归因 |
| **LED-03** 8 批更早的平仓(1,210 行 / 270,076 USDT)费用未测且不可归因 | `[DOC]` `AUDIT_EXEC.md:87` | 无 | **否** | — | 历史成本永久缺口 |
| **LED-04** `daily_nav` 分类已实现额 07-29 → 09-12 06:05Z 错(孪生收入行被 tranId 去重丢弃; BNB 费当 USDT 相加) | `[DOC]` `AUDIT_EXEC.md:71` "fixed going forward only" | FX-EXEC2 | 仅向前修 | 历史行未修订 | 历史 NAV 分解不可用 |
| **LED-06 / E10** 公证链自 08-31 起断裂 — 无有效哈希链、无第三方时间戳 | `[DOC]` `AUDIT_EXEC.md:72`; 根因 `FIXPROGRAM…:1091` (launchd 无法枚举 iCloud 桌面仓, TCC) | FX-EXEC | `[DOC]` 未说 | — | 台账不可事后证伪 |
| **LED-08** 逐锚 Telegram 报告把未知费用与成交折成**零**, 且用陈旧阈值 | `[DOC]` `AUDIT_EXEC.md:92` | 无 | **否** | — | "未知当零"一族 |
| **E-0825-I ③** 止损层与调仓层同进程耦合 ⇒ `arm()` 拒绝时两层一起停 | `[DOC]` `ERROR_LEDGER…:208` "结构性, 需单独设计" | 无(①② 已修并部署 `10063a6`) | **否** | 结构性 | 场所参数变更可同时停掉止损 |
| **E-05 杠杆死区 ±10% 在实盘 272/272 锚从未生效** | `[DOC]` `AUDIT_component_coverage…:74` | 不适用 | 配置声明存在但生产入口不可构造 | — | 声明与行为脱节 |
| **E-33** `reduce_only_reject.py` 喂的连败计数器**零读者** | `[DOC]` `AUDIT_component_coverage…:102` | 无 | 死接线 | — | 写者无读者一族 |
| **E-09** 场所 `maxNotionalValue` 截断在役但未建模, "≈0 at this NAV, 随 NAV 放大" | `[DOC]` `AUDIT_component_coverage…:78` | 无 | — | — | 随 NAV 增长而放大 |
| **E-21 / E-0920-A** 认证回放只实现 §4-2; §4-1/4-3/**4-4**/4-4b/4-5/4-6/4-7 全缺; 32/32 路径击穿 −25% | `[DOC]` `AUDIT_component_coverage…:90`; `ERROR_LEDGER…:993` | AMENDMENT 2 加并行 P 读数 | **不修** | — | 回放装不下实盘的停机与恢复 |
| **CFG-04 / CFG-06** chase 50/50 与 placement eps 0.50 在停止点前硬写在役; `_basis` 未更新 | `[DOC]` `AUDIT_EXEC.md:62,63` | 预注册修订 | 实验在跑 | 待停止点(≈10-01 / ≈10-14) | 已登记 |
| **停机后 8–20 小时不再平衡**: 19 个锚整锚被 `open_orders_halted` 拦下, 3,599 张单从未下达 | `[DOC]` `PREREG_october_decision_profile_2026-09-19.md:95`; `STATE.md:27`; **`[CODE]` 我独立复核 19 这个数**: LIVE 台账 299 行中 `opening_halted=true` 恰 **19** 行 | 不适用(是行为不是 bug) | — | — | 实盘 vs 回放对比必须单列这 19 锚 |
| **caffeinate 单点** — I6 的唯一防线 | `[DOC]` `FIXPROGRAM…:369`; `[CODE]` `/usr/bin/caffeinate -ims` PID 815, 启于 2026-09-14 23:45 | 无 | — | — | 该进程死掉 ⇒ I6 机制重新暴露(但 2.1 的 `off_schedule` halt_kind 已是第二道防线) |
| **过期判词仍在役文件里** — 在役逐锚深查提示词仍告诉代理"比例响应在克隆未部署" | `[DOC]` `docs/cron/ACTIVE_anchor_inspection_prompt_2026-09-19.txt:23` vs 同文件 `:29` 说树 = `409ea16`; 同句在 `docs/CRON_TEMPLATES_2026-09-04.md:61`、`docs/PREREG_s44_resume_reference_2026-09-21.md:9`(**今天写的**) | 无 | — | — | **每一次逐锚深查都会被喂一个错事实**; 与 `retraction_does_not_bind_the_retracted_document` 同形 |
| **DERISK 台账与代码不一致** | `RUNBOOK_deploy_executor_6661ea3_2026-09-17.md:62` "(未部署 → 已部署)" vs `STATE.md:117`(09-18)"随 Q6 影子验收后再部署" | 无(是对账缺口) | — | — | `STATE.md` 是起步必读的真相源, 它与代码不符 |

**表行数: 40**(2.1 三行 + 2.2 一行 + 2.3 四行 + 2.4 八行 + 2.5 二十四行)。

---

## §3 判词行与退出码(完整)

全部以 `/usr/bin/python3` (Python 3.9.6) 在 scratchpad 的干净 `git archive` 抽取上运行, cwd = `<extract>/live`, `env -u LIVE_MODE`。

| 抽取 | 套件 | 判词整行 | rc |
|---|---|---|---|
| `main` @409ea16 | `live/tests_nosleep.py` | `ALL PASS` | **0** |
| `main` @409ea16 | `live/tests_offschedule_held_book.py` | `ALL PASS`(前一行 `13/13 checks passed`) | **0** |
| `main` @409ea16 | `live/tests_proportional_response.py` | `ALL PASS`(前一行 `60/60 checks passed`) | **0** |
| `main` @409ea16 | `live/tests_position_break_blindspot.py` | `ALL PASS  (43 checks)` | **0** |
| `fp3/nosleep-asl-reader` @48ea820 | `live/tests_nosleep.py` | `ALL PASS` | **0** |
| `fp3/nosleep-stat-unknown` @30bec90 | `live/tests_nosleep.py` | `ALL PASS` | **0** |
| `blindspot-halted-book` @f363621 | `live/tests_position_break_blindspot.py` | `FAILURES: ['★★ every one of them is CLEAN', '   their deviation is exactly zero — the book really was flat']  (31 checks)` | **1** |
| `queued-b7…` @8917959 | `live/tests_position_break_blindspot.py` | `ALL PASS  (43 checks)` | **0** |
| `queued-b7…` @8917959 | `live/tests_stuck_position_ack.py` | `ALL PASS  (20 checks)` | **0** |
| `queued-b7…` @8917959 | `live/tests_halt_verdict_states.py` | `ALL PASS` | **0** |
| `queued-b7…` @8917959 | `live/tests_cond3_worst_selector.py` | `ALL PASS` | **0** |
| `queued-b7…` @8917959 | `live/tests_threshold_roles.py` | `ALL PASS  (15 checks)` | **0** |
| `queued-b7…` @8917959 | `live/tests_flatten_cancels_first.py` | `ALL PASS  (16 checks)` | **0** |
| `queued-b7…` @8917959 | `live/tests_halt_evidence.py` | `ALL PASS  (19 checks)` | **0** |

**全部 14 次运行都在干净抽取上, 不是脏工作树**(`green_in_a_dirty_tree_certifies_the_tree_not_the_commit`)。

**运行前的网络筛查**: 对每个待跑文件 grep `requests.|urllib|http.client|socket.|binance|fapi|curl|BinanceBroker(`。三处命中经逐行确认全部无害 — `tests_offschedule_held_book.py:57` 是 `import binance_executor`; `tests_flatten_cancels_first.py:21` 是 docstring 引用; `tests_halt_evidence.py:9` docstring、`:243` 读源码文本。`ops/resume_from_trip.sh` 内 grep `curl|wget|ping|nc |http|api.binance|fapi` **零命中** ⇒ `tests_proportional_response.py:26` 提到的 "public network probe" 在该套件中是**静态钉源码**而非执行。**本审计未产生任何交易所调用。**

---

## §4 UNVERIFIED — 我没能确立的, 以及我试过什么

1. **`rollback_*/`、`staging_batch1/`、`staging_s2gen/` 的内容**。它们是 `state/` 之外的未跟踪目录。我确认了它们不在 `scheduler/run_anchor.py` 的 import 路径上(该文件由 plist 以绝对路径直接调用, `sys.path` 不含这些目录), 但**未逐文件比对**其内容与在役代码的差异。
2. **E-0907-B 中"混合后不重施帽"的先后关系**。我确认 `fea171/combo_stage.py:85-86` 存在 `capw` + `np.clip(w,-capw,capw)`, 但**没有**通读该文件确立它相对 combo 混合步骤的位置。此行按 `[DOC]` 读。
3. **`watchdog_proportional_response` 之外的比例门运行时行为**。我确认了常量、开关函数、磁盘配置 `enabled: true` 与写入点, 但**没有**执行 `watchdog.run` 去观察真实触发 — 那需要跑执行器代码路径, 超出只读边界。生产可达性见 2.2: 至今 0 次。
4. **`STATE.md:117` 与 `RUNBOOK…:62` 关于 DERISK 的矛盾**。两句都读到了, **库里没有任何文档对账这两句**。我没有裁定哪句对 — 代码层面 `stale_ref_late` 在役是确定的, 但"用户 09-18 的裁定指的是哪一部分"无法从文本确立。
5. **`[DOC]` 行的今日真实状态**。2.5 中除 E-0918-P、OPS-01b、19 锚三项外, 其余 `[DOC]` 行我**没有**对 `409ea16` 代码复核。鉴于本轮已有三条 `[DOC]` 被推翻, **这些行的可信度应按"09-13/09-19 文档写作日的状态"折扣**, 不应直接引用为今日事实。
6. **生产者 09-18 之前的逐锚状态**。`state/snap/` 最早目录 `1789646400`(mtime 09-18 10:36)。此前滚动三件每锚整份重写, **不可复原**。

---

## §5 与既有受据的对账

- 记忆条目 `derisk_late_reference_rule_2026_09_17.md` 记"(09-17, 未部署)" — **与 `[CODE]` 不符**, `stale_ref_late` 在 `409ea16` 的 `scheduler/anchor_loop.py:3245` 在役。该记忆条目待更正。
- 记忆条目 `offschedule_run_flattens_the_whole_book_i6.md` 记"修复在克隆未部署" — **与 `[CODE]` 不符**, `off_schedule` 已在 `BOOK_HELD_HALT_KINDS`。待更正。
- `CLAUDE.md` 路由表 KB-73 关于 `run_acceptance.sh:28` 的表述 **`[CODE]` 复核成立**, 逐字为 `PY="${ACCEPT_PY:-/usr/bin/python3}"`。
- lead 交付的地基(运行树 = main = origin/main = 409ea16、0/0、四条分支未并入、`~/wide_shadow` 无 VCS)**逐条成立**。不成立的是三条"无修复"声明。
