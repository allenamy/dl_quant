# 第三次交付复审: R16R(独立复审第二轮)六条逐条修复 + 入口级/行为级证据 + 提交链

> **创建:** 2026-09-16 | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** 交付复审(§3.2 电池一节待 17:05Z 窗口结果回填) | **作废条件:** 下一轮复审意见的响应文档取代本文; 若任一提交被改写(amend/rebase), 本文所有 sha 作废

## 0. 一句话

R16R 指出的六条(E3 回归 / M1 读错键 / T1a 空记录通过 / T1b 豁免绕过 / E2 写入端未修 / E1 broker 吞 NaN)**全部按行为修复**, 每条带一个驱动真实入口或真实方法的测试, 修前对照**从 git 按缺陷形态取源**(不是固定祖先)并逐字复现复审者的反例; 上一轮「159/159 同退出码 = 零回归」的说法**撤回**——那只证明套件级无新红。本轮**不部署**任何东西(生产 `~/dl_quant_live` 仍 ef60f85), 不声称策略表现有任何变化(回放预期仍是 `HONEST_EXPECTATION_2026-09-16.md` v3 的 0.8–1.3)。

## 1. 提交链(两棵树, 均 `git commit -F <file> -- <显式路径>`, 无 amend)

**执行器叠加树**(`scratchpad/stack`, 分支 stacked): `ef60f85 → … → 4e997fb(R16-E1) → facdf24(R16-E2/E3) → `**`183915f`**
- 183915f: `live/binance_broker.py` `live/watchdog.py` `ops/daily_summary.py` `ops/gate_coverage.py` `run_acceptance.sh` + 新 `live/tests_daily_summary_entry.py` `live/tests_broker_nonfinite_positions.py`(7 文件, `state/` 零入库)
- 收据: `receipts/STACKED_ef60f85_to_183915f.diff`(24,720 行, sha8 0af97a0e) · `receipts/STACKED_R16R_facdf24_to_183915f.diff`(384 行, sha8 747a755d, 只触及上面 7 个文件)

**研究仓**(`research/book-uplift-2026-09-11`): `ba247021 → 1c00948b → 1f86f769 → fda1d3ef → ce9fdd16 → (本文与 §42 的提交)`
- 1c00948b: §41 受理 + LIVE_TRUTH/CODEREVIEW/HANDOFF_R16 的撤回横幅与措辞更正
- 1f86f769: R16R-M1 King 门 + `tests_fm_gate_b_repro_king_exit.py`
- fda1d3ef: R16R-E2 写入端 `led04_apply_amendments.py` C2b + `tests_led04_apply_identity.py`
- ce9fdd16: R16R-T1a/T1b `v4_gate_roll_paths.py` + `tests_pipeline_gates.py`(Q7/Q7b/Q7d + Q2/Q5 夹具) + 五条测试日志 + 两份 diff 收据

## 2. 逐条: 复审意见 → 根因(逐行) → 修复 → 证据(修前/修后同一输入)

### 2.1 E3 日报回归 101→11(P1)
- **根因**: `ops/daily_summary.py` main() 三处(`account_facts` / 同日增量两端)把 `root` 传给 `_LA.verify_record(rec, pilot_log_root)`, 校验器只认 `<plog>/<day>/daily_nav.jsonl`; 目录错一层 ⇒ 合法修订被判「原行不可核」⇒ 回退记录值并标不可靠。`tests_daily_summary` 两次 111/111 是因为它只调函数, 从不驱动 `main()`。
- **修复**: 三处一律传 `plog`(183915f)。
- **证据** `live/tests_daily_summary_entry.py` **5/5**: 驱动真实 `main()`(argv 解析、`state_root.paths_for` 按根重写整份字典、真实 state 布局的临时根)。修后渲染 `当日已实现   +101.0000 USDT   [口径: USDT, 修订记录(…)]`, 同日增量行 `已实现 +11.0000 → +101.0000`; **修前源(facdf24, 按「`pilot_log_root=root)`」形态取)同一布局渲染 `+12.0000 USDT [口径: 载体原数和…假定全 USDT]`** —— 复审者的反例在真实入口上复现。
- **自查(诚实项)**: 本测试第一版两臂都红而细节是 `count("101")=2` —— "101" 匹配到的是 2026-07-27 一条**真实告警**`101 name(s) had unreadable fills`: 夹具 nav_ts=1.0/2.0(1970)落在 `--since`(=过去 N 小时)窗外, 账户段根本没渲染; 临时根缺 `notify_audit.jsonl` 时 main() 回退到 `<repo>/state/` 的真实告警文件(670 行)。三处已改并写进测试 docstring; 新增断言 A2「渲染的是夹具(含 20260901, 不含 07-27/08-01)」。

### 2.2 M1 King 复现门读错键(P1)
- **根因**: `fm_gate_b_repro_king.py` L219 退出读 `rc.get("GATE_B_REPRO")`(DL 门的键), 本装置写 `GATE_B_REPRO_KING` ⇒ 永远 None ⇒ 真 PASS 退出 3。上一轮 AST 测试把错的键**手喂**给退出表达式(GEN-4 空洞对照)。
- **修复**: 读 `GATE_B_REPRO_KING`(1f86f769)。
- **证据** `tests_fm_gate_b_repro_king_exit.py` **5/5**: 注入合成 `lightgbm`, 跑**完整** `main()`: PASS(refit=1)→0; PARTIAL(REFIT=0)→3; INVALID(saved booster 偏 1.0)→3; 断言退出读的键==装置写的键; **修前源: 真 PASS 判词退出 3**(复现)。需 scipy, 缺则 UNAVAILABLE 3 不假造。

### 2.3 T1a 月份门空记录通过 / T1b 豁免绕过(P1)
- **根因**: P4 `rec if isinstance(rec, dict) else {}` ⇒ `{}`/`[]` 校验零文件 PASS rc 0; P6 对 `ROLL_ALLOW_OUTSIDE_ROOT` 里的键 `continue` ⇒ 别名符号链接 + ALLOW=CACHE 绕过 samefile。
- **修复**(ce9fdd16): P4 schema(非空 dict, 64-hex)+ coverage(上月全部已滚路径都在记录里)+ 缺文件 FAIL; 无 `ROLL_PREV_SHA_JSON` ⇒ ok=None/未评估 ⇒ 总判 **UNAVAILABLE rc 3**; P6 不再跳过 ALLOW 键(豁免位置, 不豁免身份); P3 realpath 包含。
- **证据** `tests_pipeline_gates.py` **475/475**: Q7 无记录→rc 3 UNAVAILABLE ok=None; 全覆盖→rc 0 n_checked=8; 移动一个→rc 3 点名; Q7b `{}`/`[]`→rc 3 schema_errors, 覆盖 1/8→`previous_rolled_paths_not_in_record` 长 7; Q7d 别名→上月 CACHE + ALLOW=CACHE→仍 rc 3, P6 samefile=True previous_key=CACHE。Q2/Q5 正向格改为对**合成上月+sha 记录**跑(三态下无记录不可能 rc 0; 对真实九月合同的 pod 路径本机不存在 ⇒ P4 不可评估, 有意语义)。
- **未动**: `v4_gate_common.finalize` 的 UNAVAILABLE 标签(冻结装置 24e813f1)仍待裁定, 本轮不改冻结装置。

### 2.4 E2 写入端准入未修(P1)
- **根因**: 上一轮只修了消费者 `ledger_amendments._row_sha_ok`; 准入 `led04_apply_amendments.checks()` 仍只核 line/sha ⇒ 两条 day/line/sha 各自正确、nav_ts 对调的记录 failures=[]。
- **修复**(fda1d3ef): C2b —— 记录自称的 nav_ts(有限数值相等, NaN≠NaN)与 day 必须等于被哈希原行所载。
- **证据** `tests_led04_apply_identity.py` **5/5**(子进程按操作员方式 check 模式驱动): 正确→CHECKS_PASS 0; 对调→REFUSE 2 + 两条 C2b 各自点名自称/所载; NaN→REFUSE; **修前源(fda1d3ef^): 对调记录被准入 exit 0**(复现)。

### 2.5 E1 broker 吞 NaN(P1)
- **根因**: `BinanceBroker.positions()` 用 `abs(float(x)) > 0` 过滤, NaN 为 False ⇒ 看门狗永远看不到 NaN(上一轮只修了 `_local_response`); `flatten_all` 对非有限数量照样构造订单; 梯子第一级把「NaN 账户→空书」读成已平。
- **修复**(183915f): `positions()` NaN/±inf 原样保留(未知≠零); `flatten_all` 非有限记 `flatten_skip_nonfinite` 跳过; `_degradation_ladder` 第一级非有限名字列入 `stage1_position_unknown_names`, 只对有限部分平仓, 有未知不置 ok, 平后复查同规矩。
- **证据** `live/tests_broker_nonfinite_positions.py` **8/8**: 真实 `positions()`/`flatten_all()`(只替换 `_request`, LIVE 模式——DRY_RUN 直接返回 {} 测不到解析), 梯子喂的是**本树 broker 对 NaN 账户的真实返回**。修后: NaN/inf 保留, `flatten_all` 0 单 2 条跳过记录、未触及提交路径, 链 `ok=False unknown=['NANUSDT']`, 有限书/空书行为不变。**修前(facdf24): NaN 被丢而 ±inf 被留(复审未点名的不一致); `flatten_all` 为非有限数量构造并发送 2 张订单(`BrokerUnavailable: order submission failed for 2/2`); NaN 账户→空书→stage1 `ok=True flat_on_reread=True`**(复审者的反例)。

## 3. 套件与电池

### 3.1 受影响既有套件(叠加树 183915f, `/usr/bin/python3`, 树内 `state/` = 08:24Z 拷入的实盘账本)
| 套件 | 结果 | 注 |
|---|---|---|
| tests_daily_summary | 111 ALL PASS(1 SKIP 声明) | |
| tests_daily_summary_entry(新) | 5/5 | 对照源 facdf24 |
| tests_broker_nonfinite_positions(新) | 8/8 | 对照源 facdf24 |
| tests_realised_amendment / tests_cond4_amended_transfer_day / tests_disposition_matrix(80) / tests_watchdog / tests_imports / tests_flatten_batch_identity | ALL PASS | |
| tests_proportional_response | 58/59 | **既有 B14**: 换回 facdf24 的 watchdog.py 同样 58/59; 纲领已登记归 FX-W6C(「修断言不修行为」, 须在合并电池前落地), 本轮不越界 |
| tests_env_loading | 9/15 + 6 UNAVAILABLE | 叠加树按规矩无 `.env`(既有) |
| tests_pipeline_gates(研究仓) | 475/475 | |

### 3.2 全量叠加电池(窗 17:05Z–19:15Z; 实跑 17:05:10Z→17:21:56Z, head 183915f, `/usr/bin/python3` 3.9.6)
收据 `receipts/STACKED_BATTERY_20260916T170510Z.log`。**155 绿 / 5 红 / 1 UNAVAILABLE, RC=1。**

红/UNAVAILABLE 集合与 13:48Z 基线(`STACKED_BATTERY_20260916T134811Z.log`)**逐套件完全一致**(diff 空):
`drift_gate`·`tests_drift_gate`(真漂移×2)·`tests_entrypoint_wiring`(本机 nosleep/电源)·`tests_ledger_notary`(公证 16 日断链, launchd TCC)·`tests_proportional_response`(B14, 58/59, 归 FX-W6C)·`tests_env_loading`(3=UNAVAILABLE, 叠加树无 .env)。**六条修复无一引入新红。**
绿 153→155, 新增的两格正是本轮两条测试 `tests_daily_summary_entry`、`tests_broker_nonfinite_positions`(均绿); `tests_daily_summary`、`tests_disposition_matrix`、`tests_realised_amendment`、`tests_cond4_amended_transfer_day` 等受影响既有套件全绿。

ENVRED-2 树外状态(开跑时现算): env 缺失、notify_audit 1986 行、pilot_log 47 天、watchdog_events 15 —— 账本事实与基线**逐项相同**, 只 audit 最新行年龄随钟从 3.64h 走到 12.32h(本轮刻意不重拷账本, 保同口径; 五条红均不依赖 audit 年龄)。

## 4. 本轮自查发现(不在复审清单内)
1. 修前 broker **丢 NaN 却留 ±inf** —— 同一过滤式对两种非有限数行为不同; 修后统一为未知。
2. E3 入口测试第一版三处静默改道(§2.1), 已写入记忆与测试 docstring。
3. 电池脚本的树外状态是静态拷贝(§3.2a)。
4. zsh 不分词让一整轮 `git commit -- $P` 落空(七个路径被当一个); 无半提交, 改数组后重做; 已追加进记忆。

## 5. 未做 / 待裁定(逐条不作完成声明)
- R16R §5: R16-D1(v2 后视中位数)、R16-D2 面板装置缺口、NOSLEEP-1 修复、`finalize` UNAVAILABLE 标签(冻结装置, 需裁定)、通用 CLOSE 资金费边界、月度重训/配对实验 —— **均未做**。
- B14(FX-W6C 名下)。
- 用户裁定: 十月 D1–D5、CFG-04/06、PROD-41、修后划转日 USDT 切片定价、F10_NP_EXPORT 治理、**部署批准**(本轮零部署)。

## 6. 复跑命令(逐字)
```
cd <scratchpad>/stack
/usr/bin/python3 live/tests_daily_summary_entry.py
/usr/bin/python3 live/tests_broker_nonfinite_positions.py
cd ~/Desktop/quant_research/docs/fixprogram_2026-09-13
/usr/bin/python3 FX_MODEL/devices/tests_fm_gate_b_repro_king_exit.py
/usr/bin/python3 FX_EXEC2/devices/tests_led04_apply_identity.py
cd ~/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09
/usr/bin/python3 tests_pipeline_gates.py
```
日志: `docs/fixprogram_2026-09-13/receipts/R16R_tests_20260916/`。
