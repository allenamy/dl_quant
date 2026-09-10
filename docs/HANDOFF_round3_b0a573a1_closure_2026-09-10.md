# HANDOFF round 3 · 独立研究员复审 31fa3e4e 的修复收口(给研究员第三轮复核)

> **创建:** 2026-09-10 01:3xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** PIPELINE 节 + EXECUTOR 节完成; 研究员第三轮复核已出(13 extra/collected 案例), 其 PIPELINE 侧发现已在 §PIPELINE 第四轮(本文末)收口, 待研究员第四轮复核 | **作废条件:** 两条分支分别合并后降为历史记录; 若研究员第三轮再出 P1, 以其复核件为准
> **被复审对象**: 研究分支 `review/b0a573a1-pipeline` 自 fb98a8f9 之后的第三轮提交(见 §P0 表); 实盘分支 `review/b0a573a1-executor` 的第三轮提交 **d73b1b0**(基 e1c4c87; 全电池 132/132 绿(第三次; 前两次分别被漂移门与静态名门拦下并修正); 见 §EXECUTOR)。
> **协议不变**: 修复在分支 → 研究员复核 → 分别合入 `multi-asset-v2` / `main` → 部署另裁; 本轮不改任何研究结论(G2 FAIL, v4e 无换装资格, 18 格 (C))。

---

## §PIPELINE(研究分支; 归档 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/` = A)

### P0 提交表(时间序, 每项一提交; 改动前版本先快照)

| 提交 | 内容 | 研究员发现(§ of pipeline/REVIEW.md) |
|---|---|---|
| 8cfc6822 | 改动前快照 `.r3_<sha8>`: judge_v4 (8b2c13b7) / v4e_gate_parity (c69b3322) / make_v4_scripts / v4_gate_common / chain_v4s_gpu / chain_v4_data | 判决装置与结论同寿命 |
| a922dfd7 | **r3-1** `v4_gate_common.require` 身份绑定: `gate=<期望门名>` 必填且须相符; `self_sha256` 须为真 64-hex 且非全零(可选 `self_sha=` 钉定); 依赖清单不得为空; 收据里 sha 为 null 的输入 ⇒ 拒 | §2 P1 |
| 320e36fa | **r3-2** 链驱动依赖全绑定: 按名 require(G2_closure / STEP1 / STEP2); v4s 链补 hole_cells、经 STEP1 收据绑定训练实际读的 RAW 目标与 fea82; `pin_deps` 记训练器/启动器/合并/legs/fea89/目标/fea82 sha → `v4_gates/deps_<stage>.json`; post_export 加 BUNDLE_FAIL 反标记; `chain_v4_data.sh` 每步与每次 cp 检查 + cmp 校验 | §2 P1(链)、data cp |
| f7623817 | **r3-3** 判官: A0p 双种子参照必需且 max\|Δ\| 有限; 冻结窗 = 精确时间集(3168 / 起点 / 严格 4h / 各臂同轴); 全有限性; `JUDGE_ALLOW_PARTIAL=1` ⇒ `exploratory:true` 且判决只写 EXPLORATORY; `JUDGE_EXPORT_GATE` 缺/FAIL ⇒ `eligibility:informational`, (A) 写为 INFO 永不 PROMOTE; 扩窗多出锚数改计算值 | §3 P1 |
| 744345d5 | **r3-4a** 生成器发出 `BUNDLE_GUARD_LO/HI` 行; 三份脚本自真基底再生**逐位相等**(exporter b5b6cd19 / trainer 2147a7dd / refit 2e9c999b) | §5 生成器 |
| f190eef8 | **r3-6** G1 平价门: 轴条款 (c) 成为布尔并折进 PASS(`v4e_parity_lib.axis_clause`), 六锚缺席 ⇒ FAIL; 允许集 `G1_ALLOWED_NEW_ANCHORS` 显式, 命中写进收据 | §6 / features §2 |
| 7c6f70ed | **r3-7** 文档: PREREG AMENDMENT 4 + AMD1/AMD2 读数/AMD3 措辞收窄与撤回; HANDOFF round2 72 CI / 121 锚; HANDOFF 0909 §4-5e 触发 = 逐名门 | features §1–7, RESULT 五项更正 |
| 739c8e80 | **r3-5** `make_sha_manifest.py` 逐文件清单(86 文件: MATCH_POD2 64 + 快照 r0 1 / r1 14 / r2 1 / r3 6; 0 DIFFERS, 0 NOT_ON_POD2); receipt_to_source 修正; pod2 收据 | §5 归档 |

### P1 每项改了什么 / 怎么证的

1. **require 身份**(`A/v4_gate_common.py`): 五条拒绝理由各有文案(`REQUIRE_FAIL …`), CLI 保留 `require <json> gate=<name> [self_sha=<sha>] name=path…`。`tests_pipeline_gates.py` [E] +10 项: 错门名 / 未声明门名 / self_sha 缺·全零·垃圾 / 钉定 sha 不符与相符 / 空依赖 / 手写 {PASS:true,gate} / 输入 sha 为 null。
2. **链**(`A/chain_lib.sh`, `chain_v4s_gpu.sh`, `chain_v4_gpu3.sh`, `chain_v4_post_export.sh`, `chain_v4_data.sh`): [J] 用研究员同形态的路径翻译夹具(私有根 + stub `venv/bin/python` 真跑 v4_gate_common)跑真实驱动: success ⇒ 8 训练/2 合并/DONE/deps 已钉; wrong_gate / wrong_source / changed_holes / changed_RAW / gate_fail / step1_fail / changed_explicit_input ⇒ rc 3、零派发、无 DONE; legs 缺 ⇒ rc 3; fail_shard1 ⇒ rc 1、4 派发、无合并; [K] `chain_v4_data.sh` fea82 产出缺失 ⇒ `FAIL_fea82_output_missing` rc 1 无 DATA_DONE; 全部产出齐 ⇒ DATA_DONE。
   - **边界(明写)**: `require` 只能核收据里**已哈希**的输入; RAW 目标/fea82 通过 STEP1 收据绑定, legs 与脚本 sha 由 `pin_deps` 记为**来源收据**(deps_<stage>.json), 不是「另一道门」—— 没有任何门在派发前批准过 legs/脚本本身, 这是登记的事实, 不是已闭合的门。
3. **判官**(`A/judge_v4.py`): [L] 12 项合成臂(28 书 + 2 参照, 3168 锚): full_valid rc 0 / 18 格 (C) / informational; 缺 s2027 参照 ⇒ 3; 重复锚(计数仍 3168)⇒ 2; 60 锚 ⇒ 2; A0p NaN ⇒ 3; A0p 偏 1 bps ⇒ 3; 缺臂 ⇒ 2; partial+promote ⇒ rc 0 但 `exploratory:true` 全 EXPLORATORY; 全窗 promote 无导出门 ⇒ `(A) INFO — export gate not PASS`; 导出门 PASS=false ⇒ 同; PASS=true ⇒ candidate 可 PROMOTE。
   - **消费导出门的方式**: 由 env `JUDGE_EXPORT_GATE` 指向 G2 导出收据; 未给 ⇒ informational(默认保守)。判官不猜文件名。
4. **生成器**(`A/make_v4_scripts.py`): 发出 `_GLO/_GHI` 三行(与归档 L162–164 逐字); 本地再生三份逐位相等(收据: tests [H] 三项 OK; sha 见 P0)。pod2 `review_scratch/pod_export_bundle_v4.py` 已由 23b1a5c7 同步为 b5b6cd19(备份 `.pre_r3_23b1a5c7`)。
5. **归档清单**(`A/make_sha_manifest.py` → `A/receipts/v4_scripts_sha_full.json`): 逐文件走目录, 计数由行派生; 状态 MATCH_POD2 / POD2_DIFFERS / NOT_ON_POD2 / SNAPSHOT_rN(按文件名前缀); `receipt_to_source` 修正(g3 s2027 → r2 判官; JUDGE_v4e_* → r3 判官快照; G1 收据 → r3 平价门快照); pod2 逐文件 sha 原件 `receipts/pod2_shas_2026-09-10T01xxZ.txt`。第三轮 18 件(12 改动 + 6 快照)已同步 pod2, 旧版 `.pre_r3` 备份。
6. **G1 轴条款**(`A/v4e_parity_lib.py`, `A/v4e_gate_parity.py`): [M] 10 项合成轴对(两早锚允许 / 第三早锚拒 / 尾差 1 允许 / 尾差 2 拒 / 旧轴内部缺锚拒 / 允许集为空则两早锚也拒 / 六锚缺席命名 / 门源码 PASS 表达式含 c 与 presence)。**未在 pod2 重跑数据门**(直接指示); 现有 G1 收据映射到改动前快照。
7. **文档**: 见 P0 7c6f70ed 行; AMENDMENT 4 全文在 `docs/PREREG_king_clock_E_2026-09-09.md`。

### P2 研究员 `audit_faults.py` 原样重跑(复制到 scratch, 未改其脚本; device/chain = 第三轮归档, device/pod_export_bundle_v3.py = c210bac6)

36 例全部执行完(`AUDIT_FAULTS_DONE 36`, 31 s)。场景 → rc(VERIFIED, scratch `audit_r3/faults/*/EXECUTION.json`):

| 场景组 | 第二轮(研究员观察) | 第三轮 |
|---|---|---|
| g2_identical / time_plus300 / reverse_symbols / both_axes_descending | 0 / 3 / 3 / 3 | 0 / 3 / 3 / 3(不变) |
| require_wrong_gate / wrong_self_sha / missing_self_sha / empty_dependency_list | **0 / 0 / 0 / 0** | **3 / 3 / 3 / 3** |
| require_hole_changed_but_omitted / _explicit | 0 / 3 | 3 / 3(未声明 gate= 亦拒) |
| generator_run: 再生 exporter 与归档相等 | **False**(20/21) | **True**(三份全等) |
| chain_wrong_gate / wrong_source / changed_holes / changed_RAW | **0, 8 训练 + 2 合并 + DONE** | **3, 0 派发, 无 DONE** |
| chain_gate_fail / changed_explicit_input / post_old_marker_FAIL | 3 | 3(不变) |
| chain_success / fail_shard0–3 / merge_fail / merge_missing_marker | 0 或 1(派发后) | **3, 0 派发** —— 见下注 |
| data_copy_failure | **0, DATA_DONE** | **1, 无 DATA_DONE**(`FAIL_fea82_output_missing`) |
| data_target_failure | 1 | 1(不变) |
| judge_full_valid | 0, (C) | 0, (C), `exploratory:false`, `eligibility:informational` |
| judge_short / missing_arm | 2 / 2 | 2 / 2 |
| judge_bad_repro | 3 | 3 |
| judge_missing_raw2027 | **0** | **3** |
| judge_duplicate_calendar | **0** | **2** |
| judge_nan_repro | **0** | **3** |
| judge_partial_short_promote | **0, 四个 (A) PROMOTE** | 0, 全部 `EXPLORATORY`, `exploratory:true` |
| judge_upstreamFAIL_full_promote | **0, PROMOTE** | 0, `(A) INFO — export gate not PASS`(研究员夹具未传 `JUDGE_EXPORT_GATE`, 判官按缺省保守读) |

**注(chain_success 与 shard/merge 组)**: 研究员夹具给所有链场景写的 `step1.json` 是 `PASS=False` 且无 `self_sha256`(它本是给 post_old_marker_FAIL 用的)。第三轮 v4s 链**新增**了对 STEP1 收据的 require(绑定训练实际读的 RAW 目标/fea82), 所以在该夹具下 success/fail_shard*/merge_* 全部在派发前被 STEP1 require 拒绝(rc 3, 0 派发)—— 这是加固的正确行为, 不是回归; 分片/合并阻断路径在我方 [J](STEP1 为 PASS + 真 self sha)下验证: success 8/2/DONE, fail_shard1 rc 1 / 4 派发 / 无合并。研究员若要在自己的夹具里继续测 shard/merge, 需把 step1.json 写成 PASS + 真 self_sha256。

### P3 收据

- 本地: `A/tests_pipeline_gates.py` **ALL PASS (65 checks)**(第二轮 21 → 第三轮 65; 新增 [E]+10 [J] 10 [K] 2 [L] 12 [M] 10)。
- pod2(新鲜归档副本 `/workspace/review_scratch/r3_check/v4_chain/`, exporter b5b6cd19 / judge 634ecce0 / common bd95aa93): `A/receipts/tests_pipeline_gates_pod2_r3.log` **ALL PASS (65 checks)**, 30.3 s。
- 归档 ↔ pod2: `A/receipts/v4_scripts_sha_full.json`(86 文件, 0 DIFFERS, 0 NOT_ON_POD2); pod2 sha 原件 `A/receipts/pod2_shas_2026-09-10T01xxZ.txt`。
- 生成器: 再生三份逐位相等(tests [H]; 研究员 audit `generator_run` regen_equal 三 True)。

### P4 未闭合 / 边界(明写)

1. **G1 数据门未重跑**: 轴条款代码已入, 现有 `G1_king_clock_parity.json` 是改动前门(r3_c69b3322)的产物, 其 PASS 只覆盖 (a)(b); (c) 的「将判 PASS」是按 AMENDMENT 4 允许集的推断(INFERRED), 重跑时以收据为准。
2. **legs / 脚本 sha 只有来源收据没有门**: `pin_deps` 记录不批准; 若研究员认为需要「legs 门」(由 pod_legs_v4b 写收据、链 require), 属新装置, 未做。
3. **G2 导出资格进判官靠 env 指路**: 判官不自动寻找导出收据; 链在调用判官时须传 `JUDGE_EXPORT_GATE`(chain_king_e.sh 尚未改为传它 —— 本轮未动 chain_king_e, 因其上一轮已跑完且不在复审五项内; 下次运行判官前补)。
4. **历史收据不重算**: JUDGE_v4e_* / G1 / G2 收据保持原样, 映射到产生它们的快照; 第三轮不改任何数字与判决。
5. **快照不在 pod2**(按设计, 快照只在归档), 清单按前缀归类为 SNAPSHOT 不计入 DIFFERS。第三轮此处写「16 件」是错的: 当时清单逐行实为 22 件(r0 1 / r1 14 / r2 1 / r3 6, 与上表 739c8e80 行一致); 第四轮加回 `v4e_gate_parity.r0_f0fac5e3.py` 后为 23 件(见 §PIPELINE 第四轮 第 5 项; 数字 VERIFIED 自 `receipts/v4_scripts_sha_full.json` 逐行)。

## §EXECUTOR · 实盘分支 `review/b0a573a1-executor` 第三轮(复审 31fa3e4e P1-1…P1-4 / cap P2 / A1–A3 收口)

> 提交: `d73b1b0`(基 e1c4c87 → d040c74; safe_commit 全电池 `132/132 绿(第三次; 前两次分别被漂移门与静态名门拦下并修正)`); 运行树 main 仍 d040c74, **未部署**。复审入口: 本节 + `live/tests_request_identity_unknown.py`(32 项) + 你自己的 `executor/fault_cases.py` / `consumer_followup.py`(我们在封闭副本上以 `python3 -O` 关闭断言重跑, 逐案观测见下表; 原件未改)。

### 改了什么(每条对应你的编号)

| 你的编号 | 修复 | 落点 | 证明 |
|---|---|---|---|
| P1-1 | `-2013×2` 不再是「未发」: `_settle_order_post` 置 `resolved="absent", ambiguous=True`(absent 是证据留在 `resolved`, 不是判决); 三个提交点(maker / 重挂 / 补单)把 `resolved=="absent"` 与 `ambiguous` 同待; 本锚对该意图**不再发任何单**; phase B 15 分钟后从 `allOrders` 结算(从未下达的单在那里就是不存在 ⇒ filled 0 ⇒ 补单, 非「本锚少一腿」外无代价) | `live/binance_broker.py` `_settle_order_post`; `live/binance_executor.py` L802/L988/L1550 三处 | 你的 case 1: live 0→**1**, 行 transport_error→**无行**, POST 1; consumer case「requote_absent_then_topup」: POST 2→**1**, rested 0→**1** |
| P1-2 | 每个场所请求唯一 client id: maker `-1`、重挂 `-2`、补单 `-3`、分块 `-3c1…`(`attempt_idx` 不变, id 是请求身份, attempt 是行经济学); `_resolve_ambiguous_order` 核对 `found.clientOrderId == cid`, 不符 ⇒ unknown; `submitted_order_legs` 拒绝同 orderId 的第二个 client id, 记 `last_leg_conflicts()`, 锚内 HIGH 页 | broker `_resolve_ambiguous_order`; executor 补单 id; `venue_fills.submitted_order_legs` | 你的 case 3: filled 10.0→**None / known 5 / unknown 5**, ids `[-2,-2]`→`[-3c1]`; case 4: 归属 topup_taker→**maker 保留**, 末行 `filled_amount_unknown` |
| P1-3 (i) | 补单 `except VenueError`: 若此前有不可读块(`_unknown`)⇒ 写 None / known / unknown, `filled_amount_unknown` | executor 补单 except 分支 | 你的 case 5: filled 0.0 known→**None / unk 10 / bounded** |
| P1-3 (ii) | `apply_commission_to_rows`: 行带 `filled_unknown_residual` 时**只抬 `filled_known_notional` 下界**, 不写 filled_notional, 不改终态, `out["unknown_kept"]` 计数; `book_after_anchor` 因 filled None 把该名列入 unknown 而不记 5 | executor L18xx | 你的 case 6 / consumer case 2: after 5.0 filled→**None / filled_amount_unknown / known 5**, book {HUSDT:5}→**{} + unknown [HUSDT/topup_taker]** |
| P1-3 (iii) | **UNKNOWN 有了消费者**: `reconcile._exec_qty` 新 kind `bounded`(known 部分入 expected, unknown 部分记为**签号授权带** USDT); `_between` 返回带; 残差落在带内同向 ⇒ 解释(`residual_qty` 0, 记 `residual_qty_raw` 与 `authorised_band_usdt`), 超带部分或反向 ⇒ 照旧异常。这样 UNKNOWN 不再被消费者抹掉, 也不会变成 §4-5b 的无条件异常(那会平仓) | `live/reconcile.py` | 新套件 [8]: venue +8 于 known 5 + 带 5 ⇒ 0 异常; +12 ⇒ 异常 2.0(raw 7); +2 ⇒ 异常 −3; 无带信息的纯 unknown 仍 `execution_of_unknown_size` |
| P1-3 (iv) | 未归属成交有声: n_unattributed>0 ⇒ INFO; 若本锚该名有 UNKNOWN 请求 ⇒ HIGH 并点名 | `scheduler/anchor_loop.py` 收费收集段 | 代码 + 新套件 wiring |
| P1-4 | `_execution_unknown`: HTTP 408 或 code ∈ {-1007, -1006} ⇒ 执行未知; -1008 等仍拒 | broker | 你的 case 2: GET 0 / venue_reject → **GET 1 / live 1**; 新套件 [3] 三组 + -1008 对照 |
| cap P2 | `clamp_venue_cap` 先校验 cap/target/held/margin 有限性(非有限 ⇒ 记 `invalid` 且该名不动), 临时映射算完后**原子应用**; `reduce_to_cap` 名进 `reduce_only_syms`, 计划器调用点并入 reduce-only; 非有限 ⇒ HIGH 页点名 | `scheduler/anchor_loop.py` | 你的 case 8a: 异常+GOOD 已改 → **无异常, GOOD 1960, BROKEN 原样, invalid 点名**; 8b: nan → **100.0 原样**; 8c: 你的调用传 `reduce_only_syms=set()` 绕过了接线, 故 plan.reduce_only 仍 False, 但 clamp 报告 `reduce_only_syms=[HUSDT]`, 真实调用点已并入(新套件 [9] 证 plan.reduce_only True) |
| A2 | `income_since`: 满页且游标无法前进(同毫秒饱和 / 无新行)⇒ `truncated=True`, `same_ms_saturated=True`; 页宽常量 `INCOME_PAGE_LIMIT`; 夹具 `_request` 按 `min(limit, self.page)` 真分页 | broker; `tests_income_twin_rows` [E][F] | 你的 A2 表: 1,001/2,001 行 ⇒ 1,000 行 **truncated True**(原 False); 页恰满且下一读无新行也 True; 短页 False |
| A3 | docstring 改闭区间 `[start_ms, end_ms]`(场所 endTime 含边界), 相邻窗口用 `end−1`; 返回加 `by_type_asset` 与 `non_usdt_assets`(不换算, 具名) | broker | 新套件 [G]: BNB 手续费行被具名并分桶 |
| A5 | **平仓单带我方 client id**: `flatten_all(..., client_prefix)` 每块 `F<yyyymmddHHMMSS>-<sym>-<i>`(≤36 字符不截断); 看门狗阶梯与陈旧信号阶梯两处以 broker 属性 `flatten_client_prefix` 传前缀(前缀 = 平仓时刻的 UTC 秒; 既有假 broker 的 `flatten_all(positions, reason)` 签名不受影响); 平仓 orders 行记 `client_id`。第一次电池因我改了字节冻结的 `pilot_metrics.py` 而红(漂移门), 第二次因阶梯作用域里引用了不存在的 `trip_key` 而红(静态名门), 均已修; 第三次 132/132 绿。**09-09 历史平仓**: 通用 `ops/backfill_fills.py` 因平仓单无 client id 正确拒绝(重建 0 腿); 专用工具 `pilot_journal/tools/backfill_flatten_fills_20260909.py` 按 **orderId 精确联接**(allOrders MARKET∧reduceOnly∧窗内 → userTrades.orderId): 243/243 名各识别平仓单, **3,095 笔 / Σ 232,756.969 = 243 张平仓行 Σfilled 逐名零差 / USDT 费 116.378476 = 子窗 income 3,094 行到分**(1 笔 BNB 计费 0 另列); 干跑收据在 pilot_journal; 写回等字 | `live/binance_broker.py`, `live/watchdog.py`, `scheduler/anchor_loop.py`; 研究主线工具 | 新套件 [11]; 干跑收据 `backfill_flatten_fills_20260909_dryrun.json`(reconciled=true 待重跑确认) |
| A1 | 结构化旗标 `reconstructed_from_venue`: `order_disposition.gaps` 排除; 重建工具写该列 + 费用/毛额对账门。**`pilot_metrics.py` 是字节冻结模块**(漂移清单 + metrics_freeze 2026-08-05, 电池第一次因我改它而红): 排除重建行是指标定义改动, 登记为「有意再封存」决定(需用户字), 不在本轮改; 在此之前 **52 行不能 apply**(重建行 target_w/prev_w None 会让 `m4_turnover` 抛错, 新套件 [10] 把这个门记成断言) | `live/order_disposition.py`; 研究主线工具 | 新套件 [10]; 工具离线复算 Σfee 0.50724168 = 折叠 fills 69 笔 |

### 你的 13 个反例在修复分支上的观测(封闭副本, `python3 -O`, 原脚本仅加 `rows_orders[-1]` 空表守卫)

| 案 | 你的观测(e1c4c87) | 修复后观测 |
|---|---|---|
| 1 two_absent_then_late_filled | live 0, 行 transport_error, filled 0 | live **1**, **无行**, POST 1 |
| 2 http408_backend_unknown | GET 0, venue_reject | GET **1**, live **1**, 无行 |
| 3 second_chunk_queries_first_terminal | filled 10.0, ids [-2, -2], orderIds [9001] | filled **None**, known **5**, unknown **5**, ids **[-3c1]**, orderIds [9001] |
| 4 requote_to_topup_id_alias | 归属 9101 → topup_taker, 末行 filled 5.0 | 归属 9101 **保留 maker**, 末行 `filled_amount_unknown`, unknown 5 |
| 5 unreadable_earlier_chunk_then_refusal | filled 0.0, reconcile known | filled **None**, unknown **10**, reconcile **bounded** |
| 6 known_subset_promotes_unknown_complete | after filled 5.0 `filled` | after **None** `filled_amount_unknown`, known 5, **bounded** |
| 7 cleanup_row_fault_closed | 已关闭 | 不变(same_error, 2 行, 1 页) |
| 8a cap_exception_is_partial_mutation | 异常且 GOOD 已改 1960 | **无异常**, GOOD 1960, BROKEN 原样(`invalid` 点名) |
| 8b cap_nan_injects_nan | nan | **100.0 原样** |
| 8c cap_reduce_not_tagged_reduceOnly | plan.reduce_only False | 你的调用绕过接线故仍 False; clamp 报 `reduce_only_syms=[HUSDT]`, 真实调用点并入(新套件 [9]) |
| C1 requote_absent_then_topup | POST 2, rested 0 | POST **1**, rested **1**, 无行 |
| C2 actual_attribution_and_book_after | after filled 5.0, book {HUSDT: 5}, known | after **None**, known 5, book **{}** + unknown [HUSDT/topup_taker], **bounded**, n_unattr 1 |
| C3 cap_reduction_during_opening_halt | blocked_by_halt | 不变 |

### 我方在第三轮里又抓到的自己的错
- 我 09-09 17:4xZ 写的「平仓手续费 3,049 笔 / −114.77U = 4.93 bps」是下界: 我的临时 income 查询用 `startTime=last+1` 翻页, 在页边界丢了 45 行 —— **正是你 A2 指出的饱和缺陷, 在我自己的查询里再现**。子窗 + 去重重查: 3,094 行 / −116.378476U = **5.00 bps**; 平仓总代价 ≈ 96 + 116 ≈ 212U ≈ 9.1 bps/gross(结论不变)。journal 已追加更正。
- 第一次全电池红: 我改了字节冻结的 `pilot_metrics.py`(漂移门抓到)。已还原, 排除逻辑改为登记再封存决定。

### 请复核(第三轮新问题, 我方自报)
1. **授权带的方向与标价**: 带以 `filled_unknown_residual`(USDT)/mark 转合约数, mark 取复读价; 若 unknown 请求以远离复读价成交, 带会略偏。是否可接受为「残差解释带」而非精确量?
2. **absent ⇒ 歧义**的代价面: 一条真正从未下达的 maker 现在要等 phase B 才补单(≤15 分钟), 与旧规则「立即当未发、下锚补」相比, 本锚不再少一腿但多了一个 k 窗等待。是否有我们没看到的第三种代价?
3. **client id 后缀读者**: 我们改了 `tests_signal_and_loop` 夹具(-3 / -3cN → orderId 202), 重建工具的 `rsplit("-",1)` 只服务历史 12Z(-1/-2); 请再扫一遍你能想到的其它读者。
4. **§4-5b 与 bounded**: 有带信息的 unknown 不再直接进 `execution_of_unknown_size`; 无带信息(旧行)仍进。这是有意的不对称: 旧行本来就是异常。请确认没有把真正的洞变小。
5. **未做**: 请求级持久化「未决列表」跨进程恢复(P1-1 的完整解); reduce-only 与库存变化的统一合同(cap 8c 的更深层); 同毫秒饱和的完整解法(页码/类型分区); asset 换算。均登记, 不在本轮。


---

## §PIPELINE 第四轮(研究分支 `review/b0a573a1-pipeline`, fd50007c → 本节末提交; 归档 A 同上; 研究员第三轮 `codex_round3_review_2026-09-10/pipeline/` 的 extra/collected 案例收口)

> 本轮只做研究分支半边; 实盘分支的第四轮另有节。不改任何研究结论(G2 FAIL / v4e 无换装资格 / 18 格 (C) 不变); 无训练、无 GPU、不动 `~/dl_quant_live*` `~/wide_shadow` 与研究主线。pod2 只在 `/workspace/review_scratch/` 同步与跑测试。数字标签: **VERIFIED** = 收据/日志逐位可查; **INFERRED** = 推断。

### R0 提交表(时间序, 每项一提交, 每项红路径 + 绿路径进 `A/tests_pipeline_gates.py`; 第三轮 65 项全部保留并全绿)
| 提交 | 项 | 改动 | 检查项 |
|---|---|---|---|
| dcb01bcb | **r4-1** | `judge_v4.py` 资格按臂绑定身份: `JUDGE_ELIGIBILITY`={arm:{receipt,gate,self_sha,inputs[,profile]}} 逐臂过 `v4_gate_common.require`; 绑定到 X 的 PASS 不能抬 Y; `JUDGE_EXPORT_GATE` 降为弃用别名(只记录 + WARNING, 永不产生资格) | 65 → 73 |
| da9be74a | **r4-2** | `require` 强制 `self_sha=`(缺/非 sha ⇒ rc 3); `chain_lib.sh` 新增 `gate_sha`; 三条链(v4s / gpu3 / post_export 含等待循环)在运行时从 `$R/v4_gate_{closure,step1,step2}.py` 算 sha 钉住门源码 | 73 → 90 |
| 4908080a | **r4-3** | `v4_gate_common.REQUIRED_INPUTS` 全依赖登记表(G2_closure 5 / STEP1 底 2 / STEP1@v4s 2 / STEP1@v4 4 / STEP2 2 / BUNDLE_export 7), `profile=<stage>` 选阶段子集, 漏报登记项 ⇒ rc 3(多报仍逐项核); 三条链显式报 profile | 90 → 104 |
| 08726802 | **r4-4** | `judge_v4.py`: RAW 参照先于复现验 schema + 全冻结轴(N_FROZEN 锚精确 4h 网格, 与 A0p 臂逐位相等)+ 有限(rc 2 / 非有限 rc 3); `load()` 验 NPZ schema(rec (n,23); cols==COLS; 书带 W (n,n_symbols); `JUDGE_REQUIRE_W=1` 强制 W)与整数秒时间戳(|x−round(x)|<1e-9)⇒ rc 2 | 104 → 117 |
| 0a6ee9a9 | **r4-5** | 自 git 8e7908e2 找回改前平价门 → `A/v4e_gate_parity.r0_f0fac5e3.py`(sha == G1 run-1 FAIL 收据 self_sha256, VERIFIED); `make_sha_manifest.py` 映射改指 r0 且**按 sha 核映射**(不符 ⇒ MANIFEST_REFUSED rc 2 不写); pod2 同步 8 文件(.pre_r4 备份)+ pod2 117 项收据 + 逐文件 sha; 清单重生成; 本文 P4.5 计数更正 | 117(pod2 117) |
| (本提交) | **r4-6** | 本节 + 研究员两套 harness 原样重跑收据 `A/receipts/researcher_round3_cases_rerun_after_r4.json` | — |

### R1 每项改了什么 / 怎么证的(对应研究员 REVIEW 的编号与 collected/extra 案例)
1. **资格是身份, 不是布尔**(REVIEW L34; extra `judge_minimal_PASS` / `judge_unrelated_stale_PASS` / `judge_A1e_gate_promotes_other_arm`): 第三轮判官读一个全局 `{"PASS": true}` 就把所有对比的 (A) 放成 PROMOTE。现在每个候选臂各自一条资格条目, 走与链派发**同一个** `require` 合同(门名 = / 门源码 sha = / PASS / 登记输入齐 / 每输入 sha = 盘上文件); 无绑定 PASS 的臂 (A) 读作 `(A) INFO — no bound export-gate PASS for arm X`; 输出新增 `eligibility_by_arm` / `eligible_arms` / `eligibility_error`。证: [L] 裸 `{PASS:true}` / 门名错 / 输入陈旧 / 绑定他臂(A1 +1 bps 而只有 A1e 有绑定 PASS ⇒ A1 六格 INFO, 零 PROMOTE)/ 无 self_sha / 漏登记输入 ⇒ 全部不合格; 绿: 正确绑定 A1e 收据 + A1e +1 bps ⇒ 恰好 A1e-A0/A1e-A1 两座四格 PROMOTE, 其余 (C); 内联 JSON 同效; 垃圾 env 忽略并记 `eligibility_error`。**边界**: 弃用别名 `JUDGE_EXPORT_GATE` 现在**永不**产生资格 —— 第三轮 [L] 「PASS=true ⇒ candidate」那条期望已改写为「仍 informational + WARNING」。
2. **门源码必须钉**(REVIEW L52; extra `require_valid_wrong_source_unpinned` / `chain_valid_wrong_gate_source`): 第三轮 `self_sha=` 可选而三条链都没传, 所以「用判官的真 sha 写 G2 收据」能让 v4s 链跑 8 训练 2 合并 DONE。现在 `require` 缺钉 ⇒ `caller did not pin the gate source` rc 3; 链用 `gate_sha` 在**运行时**从自己要调用的门脚本算 sha, 不是抄一个常数(测试断言成功跑的 require 行携带的 self = 翻译后门脚本实测 sha)。证: [E] 未钉 / 判官 sha 未钉 / 判官 sha 钉 closure ⇒ `caller trusts` / 空、非 sha、全零 ⇒ rc 3; [J] v4s: G2 由判官写 ⇒ rc 3 零训练(研究员案例逐字), STEP1 由 closure 门写(真门, 错门)⇒ rc 3, 门脚本缺 ⇒ `gate_source_unreadable` rc 3 先于任何 require; 新 [J2] gpu3 成功 16 训练 4 合并 DONE + STEP2 由判官写 / STEP1 由 closure 写 / RAW 变更 三红; post_export 成功 + 错源 STEP1 在等待循环永不通过 ⇒ `step1_receipt_timeout_2h` rc 3 零训练。
3. **全依赖是合同**(REVIEW §2 补; extra `require_correct_identity_dependency_subset`, faults `require_hole_changed_but_omitted`): 第三轮只核调用方自选子集, 漏报 hole_cells 且 holes 已变 ⇒ rc 0。`REQUIRED_INPUTS` 从链实际消费填: STEP1 分两个阶段子集 —— `@v4s`(chain_v4s_gpu: RAW targets + fea82; 它的 fea89 经 G2 fea_A 绑定)与 `@v4`(gpu3 / post_export: RAW+CLIP targets, fea82, fea89), 阶段子集是**显式登记的合同**, 未登记的 profile 被拒; `BUNDLE_export` 7 项 = `pod_export_bundle_v4.py` 读的 BUNDLE_FEA/META/BASE、EXPORT_PANEL、BUNDLE_CACHE、fund_aug.json.gz、live_pins.json, 供判官逐臂资格。证: [E] 漏 hole_cells rc 3 点名 / 研究员原案(变且漏)rc 3 / 变且申报 ⇒ `changed since the receipt`(两条路都看得见)/ STEP1@v4 只报 RAW 对 ⇒ rc 3 点名 CLIP+fea89 / 未登记 profile rc 3 / 登记表与三条链声明一致(源码 grep); [J] 链驱动被改成只报 4/5 ⇒ rc 3 零训练。**边界**: 未登记的门没有底(调用方非空声明仍逐项核), 通过语句带 `registered floor <key>=none` 便于审计; 要收紧为「未登记门一律拒」是一行改动, 未做(G1/G4 收据现在没有 require 调用方)。
4. **参照与 schema 先于数字**(REVIEW L66; extra `judge_both_raw_references_only60` / `judge_raw_duplicate_and_gap` / `judge_fractional_timestamp_plus025` / `judge_false_schema_no_W`): 第三轮 `np.intersect1d` 让「参照只剩 60 锚」在 60 个交集上「复现」, 「参照 r[100,0]=r[99,0]」被去重后照过; `astype(int64)` 把 +0.25 静默截断; 判官从不看 cols/symbols/W。现在参照两种子各自: 同 schema → `frozen_axis_check`(3168 锚精确 4h 网格)→ 与 A0p 臂冻结轴逐位相等 → 冻结窗有限, 任一坏 ⇒ rc 2(非有限 rc 3), 都在复现之前; `load()` 对臂与参照同样验 schema。**真数据不受影响(VERIFIED)**: `receipts/JUDGE_v4.json` / `JUDGE_v4e_hardened.json` / `JUDGE_v4e_informational.json` / `JUDGE_v4_g3_s2027.json` 的 A0p/A0 × s42/s2027 复现 `n` 均为 3168, 即真参照本就覆盖全冻结轴, 新门不改变任何已出判决; pod2 真 w10 NPZ 带 `cols`(23)/`symbols`(829)/`d30_n2_c42_W`(n,829), ts 整数(VERIFIED 抽样 A1e_dyn_s42 与 RAW s42)。证: [L] 四案例各 rc 2 点名原因; 1e-10 浮点 ts 放行; 对 cols 但无 W rc 2; W 形状错 rc 2; 全书 schema 绿; `JUDGE_REQUIRE_W=1` 对裸 rec 夹具 rc 2; 参照 NaN rc 3 先于复现; 参照缺 rec 数组 rc 2; PARTIAL + 分数 ts ⇒ 28 臂入 `schema_bad` 零判决; 缺参照仍走复现门 rc 3(第三轮行为不变)。**边界**: `JUDGE_REQUIRE_W` 默认关(合成夹具无 W); 下次真跑判官时应在调用处设 1。
5. **收据→源码映射按 sha 核**(研究员 `RECEIPT_SOURCE_CHECK.json`): G1 run-1 FAIL 收据(2026-09-09T16:33:30Z)self_sha256 = `f0fac5e3…`, 是 PREREG AMENDMENT 1 之前的门; 第三轮映射到 r3 快照 `c69b3322…` 是错的。自 git 8e7908e2 取回, sha256 逐位相等(VERIFIED), 存为 `A/v4e_gate_parity.r0_f0fac5e3.py`; `make_sha_manifest.py` 对每条带 self_sha256 的收据核映射文件 sha(4 条 VERIFIED: G1 两份 / G2 hardened / G4; 15 条旧 schema 收据无 self_sha, 映射只能靠提交史, 单列 `receipt_to_source_unverifiable_no_self_sha`), 不符 ⇒ `MANIFEST_REFUSED` rc 2 不写(用旧错映射实测被拒)。清单重生成: **87 文件 = MATCH_POD2 64 + SNAPSHOT r0 2 / r1 14 / r2 1 / r3 6; 0 DIFFERS, 0 NOT_ON_POD2**(VERIFIED, 计数由行派生)。本文 P4.5 「快照 16 件」已更正(当时 22, 现 23)。**本轮不再加 .r4 快照**: 第四轮改动前的 8 个文件(fd50007c 版)没有产生过任何归档收据(VERIFIED: 逐份收据 self_sha256 对照当前文件 sha, 命中的只有 v4_gate_closure / v4e_gate_quant / 两份平价门快照), 「判决装置与结论同寿命」不要求快照它们, 需要时 `git show fd50007c:<path>`。

### R2 研究员两套 harness 原样重跑(复制到 scratch, 未改其脚本, 未碰其 worktree; `device/chain` = 本轮归档 87 文件; 收据 `A/receipts/researcher_round3_cases_rerun_after_r4.json`, 含每案 rc 与拒绝语句)
**extra_checks.py(12 案)**: 10 翻转, 2 本来就对。
| 案例 | 第三轮 | 第四轮 | 拒绝处 |
|---|---|---|---|
| require_valid_wrong_source_unpinned | rc 0 | **rc 3** | `caller did not pin the gate source` |
| require_valid_wrong_source_pinned | rc 3 | rc 3 | `caller trusts 15a03d4a`(不变) |
| require_correct_identity_dependency_subset | rc 0 | **rc 3** | 其 harness 不钉源 ⇒ 先在钉源处被拒; 登记底的拒绝由我方 [E] 「变且漏报 ⇒ omitted registered input(s) ['hole_cells']」单独证 |
| require_correct_identity_all_dependencies | rc 3 | rc 3 | 同上先在钉源处被拒(第三轮是 changed since) |
| chain_valid_wrong_gate_source | rc 0, 8 训练 2 合并 DONE | **rc 3, 0 / 0 / 无 DONE** | `FAIL_gate_require_G2_closure_stable`(receipt was written by gate source <judge>, caller trusts <closure>) |
| judge_minimal_PASS | candidate, 4 PROMOTE | **informational, 0 PROMOTE** | WARNING 弃用别名; 其 harness 只会传 `JUDGE_EXPORT_GATE` |
| judge_unrelated_stale_PASS | candidate, 4 PROMOTE | **informational, 0** | 同上 |
| judge_A1e_gate_promotes_other_arm | candidate, A1 六格 PROMOTE | **informational, 0** | 同上; 按臂绑定的正面证明在我方 [L] |
| judge_both_raw_references_only60 | rc 0, 4 PROMOTE | **rc 2** | `reference axis: n=60 != 3168` |
| judge_raw_duplicate_and_gap | rc 0, 4 PROMOTE | **rc 2** | `not a strict 4h grid at index 99: diff 0 s` |
| judge_fractional_timestamp_plus025 | rc 0, 4 PROMOTE | **rc 2** | `timestamps are not integer seconds (row 0: 1740787200.25)` |
| judge_false_schema_no_W | rc 0, 4 PROMOTE | **rc 2** | `cols differ from the frozen COLS` |

**audit_faults.py(36 案)**: 35 与其第三轮记录逐字相同(含 chain_success 8/2/DONE、四 fail_shard、merge 两案、data 两案、judge 九案), 1 翻转: `require_hole_changed_but_omitted` rc 0 → **rc 3**(其 harness 不钉源, 先在钉源处被拒)。

### R3 收据
- 本地 `/usr/bin/python3 A/tests_pipeline_gates.py` ⇒ ALL PASS 117(每提交后跑; VERIFIED); pod2 `/workspace/venv/bin/python -B tests_pipeline_gates.py` @ `/workspace/review_scratch` ⇒ ALL PASS 117, `A/receipts/tests_pipeline_gates_pod2_r4.log`(VERIFIED)。
- pod2 同步: 8 文件(judge_v4 / v4_gate_common / chain_lib / 三条链 / tests / make_sha_manifest), 改前版 `<f>.pre_r4` 在 pod2; 逐文件 sha `A/receipts/pod2_shas_2026-09-10T0311Z.txt`(87 名, 17 MISSING = 全部快照, 按设计); 同步前 pod2 无链在跑、GPU 0%(VERIFIED 02:5xZ pgrep/nvidia-smi)。
- pod2 现存 `v4_gates/G2_closure_stable.json` / `step1.json` / `step2.json` 仍是旧 schema(无 gate/self_sha; step1 PASS=false)—— 第三轮起链就已拒派发, 本轮不改变这一状态, 也**未**重跑任何数据门(不在指示内)。
- 研究员重跑收据 `A/receipts/researcher_round3_cases_rerun_after_r4.json`(含其 harness 两文件 sha、本轮 device 8 文件 sha)。

### R4 未闭合 / 边界(明写)
1. **真判官今天仍拿不到资格条目**: 归档里没有写 `BUNDLE_export` 收据的门 —— `pod_export_bundle_v4.py` 只打印 guard PASS/FAIL、写 MANIFEST.json, 不走 `finalize`; `chain_king_e.sh` 也还没传 `JUDGE_ELIGIBILITY`(第三轮已记它没传 `JUDGE_EXPORT_GATE`)。后果是保守的: 任何真跑的判官都是 informational, 与「v4e 无换装资格」一致。补一个 `v4e_gate_export.py`(finalize 出 BUNDLE_export 收据, 输入 = REQUIRED_INPUTS 那 7 项)是新装置, 未做。
2. `REQUIRED_INPUTS["BUNDLE_export"]` 因此是对**尚不存在的门**的合同(INFERRED 自导出器读的文件); 门落地时名字须对齐。
3. 未登记的门无底(见 R1.3 边界); `JUDGE_REQUIRE_W` 默认关(见 R1.4 边界)。
4. 15 份旧 schema 收据(JUDGE_v4* / V3P_* / align / guard_decompose)无 self_sha, 映射不可 sha 核, 只能靠提交史; 不重算历史收据。
5. 本地测试 harness 在 macOS bash 3.2 下 `chain_lib.sh` 的 `local -n`(run_shards 月份表)不被支持, stderr 有 `local: -n: invalid option`, stub 不读月份所以计数不受影响; pod2 bash 5 无此问题, pod2 收据为准。第三轮已如此, 未改。
6. 研究员 harness 里的 `require_correct_identity_dependency_subset` / `_all_dependencies` 在第四轮都先被「未钉源」拦下, 其登记底那一层由我方测试单独证(R2 表注)。

### R5 我方自报(第四轮)
- pod2 同步时一条 ssh 参数引用错误(`"-p 55572 root@…"` 被当成一个参数)使 `.pre_r4` 备份那一步没先执行, 而 scp 已经覆盖了 pod2 上的 8 个文件。随即自 fd50007c 重建 8 个改前版, 与第三轮 pod2 sha 记录 `receipts/pod2_shas_2026-09-10T01xxZ.txt` 逐一相等后补上传为 `.pre_r4`; pod2 当时无链在跑。无损失, 但顺序错了: 备份该在覆盖之前得到收据, 不是之后重建。
- 第三轮 [L] 「export-gate PASS=true ⇒ candidate/PROMOTE」那条期望是第三轮设计本身的错(裸收据当许可), 本轮改写而非删除, 让翻转可见。

---

## §EXECUTOR 附录 A(2026-09-10 02:4xZ)· E-0910-A 熔断 + `reconstructed` 类型 + 账本写回状态 → 分支 3ff5e00

> 电池 132/132 全绿。与 §EXECUTOR 同一分支同一批复核。预注册: `docs/PREREG_venue_lock_breaker_E0910A_2026-09-10.md`(研究主线)。

### A1. E-0910-A 场所量化规则锁(-4400)熔断
- **事实**: 00Z 复场锚补单相 71 张 IOC 全部 -4400「only reduceOnly order is allowed」; `apiTradingStatus` ACCOUNT 指标 TMV isLocked, plannedRecoverTime 02:34:10Z; 书建到 67%, net/gross +5.23%。若锁落在首挂相, 191 张 GTX 全拒会以 `venue_reject` 灌满 §4-7 的失败率 —— 那才是真正的风险。
- **规则(冻结)**: 同一提交循环内首张 -4400 照旧记(首挂 `venue_reject` / 补单 `abandoned_max_attempts`); 其后**开仓**单不发, 记新终态 `skipped_venue_lock`(pilot_log TERMINAL_REASONS + order_disposition GAP 格, 矩阵一致性套件绿); **reduce-only 单照发**; 首挂/补单两相各自学习(不跨相传递, 15 分钟后重学一次代价一张单); `executor.venue_lock_report`; anchor_loop 两相各一条 HIGH 页, 含 `broker.api_trading_status()`(新只读方法, 仅供页面, 不参与决策)的锁指标与预计解锁时间。
- **不改**: 不读 apiTradingStatus 来决定发不发; 不动 reduce-only 语义; 不动 §4-7 分母(未发的单不是 `venue_reject`)。
- **证明**: 新套件 [13]: 首挂相 A 拒/B、D 未发/C(reduce-only)照发 ⇒ 2 POST; 补单相同构; 报告字段; 矩阵一致; -5022 循环不触发。
- **请复核**: (1) 是否存在 -4400 只针对单名而非账户的情形(我们按账户级处理, 单名锁会让其它名的开仓单被误跳过一相); (2) 首相位 -4400 计一张 `venue_reject` 对 §4-7 分母的影响可忽略(1/191)但请确认; (3) `api_trading_status()` 失败时页面只写「读取失败」, 不影响熔断。

### A2. `reconstructed` order_type(A1 的最终形状)
- pilot_log `ORDER_TYPES` 加法扩展 + 消费者普查(注释入码): m1/m3/m4 按类型排除(m4 在旧形状下对 target_w None 抛错, 副本实测), gaps 按终态(+旗标)不计, reconcile/book 按量计入(它们确实执行了)。`pilot_metrics.py` 字节冻结**不动**。
- 重建工具 `reconstruct_orders_12Z.py`: order_type=reconstructed, `leg_kind` 保留腿别(52 条全 maker), `DQL_ROOT` 指定校验树; 分支 pilot_log 52/52 过; Σfee 0.50724168。**写回等本分支部署**(现网 schema 会拒, 工具因而拒绝 —— 顺序正确)。
- **请复核**: 普查是否遗漏了按 order_type 分组且不容忍未知类型的读者(ops/anchor_report、daily_summary 等报表按类型分组, 我方读到的是「未知类型自成一组」)。

### A3. 账本写回状态
| 件 | 状态 | 证据 |
|---|---|---|
| 平仓 3,095 笔 fills | **已写回 02:16:00Z**(用户字「按最佳路径推动」) | 副本先过看门狗 tripped=False / 5b CLEAN; 3,095 行 Σ 232,756.969 = 平仓行 Σfilled 逐名零差; USDT 费 116.378476 = 子窗 income 3,094 行到分; 收据 `backfill_flatten_fills_20260909_dryrun.json` reconciled/applied true |
| 12Z 52 行 orders | 工具就绪, **等本分支部署** | 副本判官: 加入后 §4-5b 历史异常 15→6(12Z 的 9 个被解释), tripped False |
| E-0909-H | 在本分支(e1c4c87), 等复核→合并→部署 | — |

### A4. 我方自报
- 平仓 fills 对账门第一次误判「不对账」: 我把 userTrades 的正数手续费与 income 的负数直接相加; 改为比幅度后通过。门确实拦了一次不对的写回, 这是它该做的。
- ic_monitor #55 的处置文本此前从未写下(只有阈值), 已补预注册; 本次 DECIDE 用户裁定照常, 复核点 09-15 00Z。


---

## §EXECUTOR · 第四轮(复审 62ebf9f8: R1–R3 / 合同 §2 / E1–E4 / R7 / A4)→ 实盘分支 82e0cbf(a)+ 0d30095(b)

> 两次提交, 各自全电池(132/132 / 132/132), 已推送 `review/b0a573a1-executor`。运行树 `~/dl_quant_live` 仍 d040c74(本轮零接触)。处置文档(研究主线): `docs/REVIEW_ACCEPT_round3_codex_62ebf9f8_2026-09-10.md`。**你要求「按独立问题拆小提交」**: 电池一次 ≈25 分钟, 我把第四轮拆成 a(合同主体 + 身份)与 b(合同 §2.1/2.2 + 边界)两次; a 内部每个 hunk 的注释都带你的编号(R1/R2/R3/E1/E2/E3/E4/R7/A4), 下表给 hunk → 函数映射, 便于逐项审。

### 改了什么(对应你的编号)

| 你的编号 | 文件 / 函数 | 改动 | 证据(套件 `tests_request_identity_unknown.py`) |
|---|---|---|---|
| R1 · 合同 §2.3 | `binance_executor.topup` | 补单腿**逐请求账本** `request_ledger`: 每张真实请求(单发 `-3` 或分块 `-3cN`)一条 {client_id, qty(带号合约), notional_est(按数量比例), state ∈ not_sent→confirmed/unknown/rejected, order_id(按 **client id** 从 broker 提交记录取, 不取「最近一张」), confirmed_notional, confirmed_qty(b)}; `ledger_totals` 只把 **unknown** 请求计入上界 → 行列 `filled_unknown_qty`(合约)+ `filled_unknown_residual`(USDT 估计)+ `filled_known_notional`; 传输分支: 抛异常的那张请求 = 歧义/absent ⇒ unknown, 否则 not_sent; 拒绝分支: 被拒的那张 = rejected | [14] 50 未知 + 50 拒 ⇒ unknown_qty 50; 场所 +90 ⇒ anomaly 40 |
| R2 | `binance_executor._settle_leg_by_identity`(新, 从 `apply_commission_to_rows` 拆出) | 子成交按 orderId 联接到账本里的请求 ⇒ 该请求 confirmed(带号 Σ quote_qty × side); 旧行(无账本)走 `_sgn * max(|·|)` 保号 | [15] 卖 −50 已知 + 50 未知, 归属后 known **−50**; −80 解释 / +20 异常 |
| R3 | 同上 | unknown 集只按身份缩小; `uq == 0` 才写 `filled_notional` 并把 `filled_amount_unknown` 改 `filled`; 否则保持 UNKNOWN + 已知下界, `out["unknown_kept"]` | [16] 归属后 known 50 / unknown 50; +140 ⇒ anomaly 40; 全部结算 ⇒ filled 100 |
| 合同 §2(区间) | `reconcile._unknown_interval`(新) / `_between` / 残差环 | 买 [0, r] 卖 [−r, 0](合约; 优先 `filled_unknown_qty`, 旧行 USDT/自身价回退); 按名 **Minkowski 相加** [L, U]; e = (ΔQ−K) − clip(ΔQ−K, L, U), 之后乘 mark; 输出 `authorised_band_qty=[L,U]` 替代 `authorised_band_usdt`; 非有限数量/已知部分、side ∉{buy,sell}、非正价格 ⇒ `unquantifiable`(execution_of_unknown_size) | [17] 买 50 + 卖 50 ⇒ ±40 解释 ±60 异常; mark 1.1 持 100 解释 / 0.9 持 110 异常; NaN/Inf/side None/known NaN 全异常 |
| 合同 §2.1/2.2(b) | `ledger_known_qty` / `ledger_inconsistencies`(新); `_exec_qty` | 每请求 `confirmed_qty` = 该请求 notional/avgPrice(场所恒等式; 子成交结算时用逐笔 qty); 行列 `filled_known_qty` = Σ, reconcile 优先取它; 子成交超请求量或反号 ⇒ 行 `ledger_inconsistent`(命名请求)⇒ reconcile 不可测(异常), `out["ledger_inconsistent"]` | [20] 价 2 成 50U = 25 合约, 75 解释 / 100 异常; 60 合约对 50 请求 ⇒ inconsistent ⇒ 异常 |
| E1 | `venue_fills.fill_details_for` / `_scan_orders` / **`settle_ambiguous_legs`(新)** / `anchor_loop.complete_anchor` / `topup` | allOrders `limit` 500→**1000**(场所最大); `len(rows) ≥ 1000` ⇒ 该名满页(`last_full_pages()`); `_scan_orders` 记匹配到的 client id(`last_matched_cids()`); 阶段 B 对 `submit_ambiguous` 且 id 未见的计划: 满页 ⇒ UNKNOWN(不查); 否则 `GET /fapi/v1/order?origClientOrderId=cid`: 查到且 cid 相符 ⇒ 其事实(0 成交也是事实); **−2013 ⇒ 未下达(filled 0)**; 其它(传输/别的码/答非所问)⇒ UNKNOWN; 结算本身抛异常 ⇒ 全部歧义名 UNKNOWN; UNKNOWN 并入 `unknown_fills`; INFO/HIGH 页。`topup` 对 UNKNOWN 名(非 from_reject)写 **maker 行 `filled_amount_unknown`**, `filled_unknown_qty` = 所发数量, `request_ledger` 一条 unknown(order_id 按 cid 从提交记录取) | [18] 满页 ⇒ UNKNOWN 且 0 次 GET; 非满页 −2013 ⇒ absent 0; 查到 10 ⇒ 10; 查询失败 ⇒ UNKNOWN; 已匹配不重查; UNKNOWN 名 maker 行 `_exec_qty` = bounded |
| E2 | `binance_broker.flatten_all` | 进程内 `_flatten_seq` 计数(不随符号/重试重置)⇒ 同秒重试 id 不同 | [19] 同秒两次 ⇒ `-HUSDT-1` / `-HUSDT-2` |
| E3 | `venue_fills.submitted_order_legs` / `order_legs_from_venue` / `attribute_trades` | 键 (symbol, orderId); `attribute_trades` 按 (sym, oid) 联接; 冲突记录带 symbol; 三个既有套件(avgpx_backfill / fee_asset_detection / fill_backfill)夹具改键 | [19] BTC/ETH 同 77 ⇒ 两腿无冲突, ETH 费落 ETH topup |
| E4 | `binance_executor.client_id_for`(新) / `flatten_all` | 补单 id > 36 ⇒ **拒绝**(ValueError; 该名记 abandoned_max_attempts 不发, 循环继续); 平仓 id > 36 ⇒ 先试紧凑前缀, 仍超 ⇒ **弃 id** 记 `client_id_dropped`(保护动作不因记账阻塞; orderId 仍是联接键) | [19] 超长 ⇒ ValueError; 普通 id 不变 |
| EX-R3-4 表(b) | `venue_fills` 全部读者 | `startswith(RID + "-")`; 无 TIF 回退 `-1`/`-2` 皆 maker | [20] `RID1-…` 非我方; `-2` 为 maker |
| R7 | `anchor_loop._trade` cap 调用边界 | `invalid` 处理**移到 `plan()` 之前**: field=target 且 held 有限 ⇒ target := held(delta 0 ⇒ skip 行不发单); held 非有限 ⇒ 弹出; cap 非有限但 target 有限 ⇒ 仍不截断、只页(改成拒绝交易是书行为改动, 归用户); `_capd["invalid_disposition"]` 入锚工件 | [18] wiring 断言; tests_venue_cap_clamp 22 绿 |
| A4 | `anchor_loop` daily_nav / `ops/reprice_day.py` | 持久化 `realised_by_type_asset` + `realised_non_usdt_assets`(与混单位 `by_type` 并列; **换算未做**) | 电池 tests_reprice_day / numerator_honesty 绿 |

### 你的反例在修复分支上的观测

| 反例(你的分册) | 第三轮 | 第四轮 |
|---|---|---|
| risk R1: 买 50+50, 第一未知第二拒, 场所 +90 | CLEAN | **anomaly, residual_qty 40, band [0,50]**([14]) |
| risk R2: 卖 −50 已知 + 50 未决, 归属后; −80 / +20 | BREAK / CLEAN | **解释 / anomaly**([15]) |
| risk R3: 买 50+50 双未知, 第一回填; +140 | CLEAN | **anomaly 40**([16]) |
| risk 数值边界: mark 1→1.1 合法 100; 0.9 超量 110; 混方向; NaN/Inf/side None | 5e 触发 / CLEAN / 对消 / CLEAN | 解释 / 异常 / 区间 [−50,50] / 全异常([17]) |
| executor EX-R3-1: 满 500 页无本请求 → 0 → 再 POST 10 | filled 0, 2 POST | **UNKNOWN, 不补单, maker 行 bounded**([18]); 你的 `phase_b_clock_attempt02.py` 需把 allOrders mock 的 limit 从 500 改 1000(满页判据), 并为 `GET /fapi/v1/order` 加 mock, 否则新路径会因查询失败落 UNKNOWN(也是不补单, 但不是你想测的分支) |
| executor EX-R3-2: 同秒重试同 CID | 同 id | 不同 id([19]); 你的 `flatten_retry_chain.py` 断言应改为「两次 id 不同 且 第二次 resolver 不会命中 771」 |
| executor EX-R3-3: BTC/ETH 同 orderId 77 | 冲突 + ETH 费进 maker | 两腿, 费归位([19]) |
| executor EX-R3-4: 19 字符号两分块同 id | 同 id | 补单拒绝 / 平仓弃 id([19]) |
| risk R7: target NaN 进 planner | ValueError 整锚死 | target := held 或弹出, 页([18] wiring; 未构造完整 `_trade` 端到端, 你的 AST 提取脚本可直接对新源重跑) |

### 未闭合(明写, 不是「已披露即接受」)

1. **合同 §2.4 跨读数联合约束 / 跨进程未决账本**: 当前带只在含该行时间戳的窗口生效, 下一窗不再用(不会重复解释), 也**不会去结算**它 —— 晚到成交在下一窗读成未解释(fail-closed, 可能误触发), 旧 UNKNOWN 行永不关。需要: 未决请求落盘(`state/live/pending_requests.jsonl`)→ 下锚阶段 B 按 client id 查终态 → 追加修正行(orders 只追加: 修正行的形状、与原 UNKNOWN 行在 reconcile 的双计、m1/m3 消费者)→ 预注册。
2. **−2013 终局性**: 阶段 B 在 k 窗(≥15 分钟)后对我方 id 得 −2013, 现按「从未接受」处理并允许补单。场所在此时长后是否仍可能「稍后出现」该单, 我方无证据; 若你判断需二次查询/更长等待, 是参数不是结构。
3. **两进程同秒平仓**: `_flatten_seq` 是进程内计数; 看门狗阶梯是单进程, 但若将来两个进程同秒 flatten 同名, 前缀仍可撞。可加 pid 段但 36 字符会超(F14+sym14+seq3+分隔=34)。
4. **income 缺行恢复 / 币种换算**: 未做(A4 只到持久化)。
5. **cap 非有限但 target 有限**: 仍按未校验 cap 规划(只页)。改为拒绝交易该名需用户字。
6. **合同 §2.2 「均价同一子集」的旧行**: 无账本的历史行仍用 known_notional / avg_fill_px; 新行有 `filled_known_qty`。

### 我方在第四轮里承认的自己的错(见处置文档 §6)
意图当授权(R1) / 取绝对值丢号(R2) / docstring 里无证明的「absent ⇒ 0」(E1) / 「never truncates」注释与 `[:36]` 相反(E4) / 第三轮套件 [6] 把错误合同写成期望 / orderId 当全账户唯一(E3)。

### 请复核(第四轮新问题, 我方自报)
1. `settle_ambiguous_legs` 在 **非满页** + 查单 **−2013** 时判「未下达」并允许补单 —— 这是本轮唯一把 UNKNOWN 收敛成 0 的路径, 请专门打它(k 窗后场所是否可能仍返回 −2013 而后成交)。
2. `_unknown_interval` 对旧行(仅 USDT 上界)用行自身价格回退成数量 —— 旧行只在历史账本里, 但 reconcile 会读它们; 请判断回退是否应改为「旧行一律不可测」。
3. R7 的 target := held 会产生一条 `skip` 计划行(delta 0), 与「该名被弹出」在锚工件里可区分(`invalid_disposition`); 请看是否需要独立终态。
4. 分块 `notional_est` 按数量比例分摊整腿残差 —— 只用于 USDT 估计列与页文字, 不进风险合同(合同用 qty); 若你认为该列会误导, 可删。

---

## §PIPELINE 第五轮(研究分支 `review/b0a573a1-pipeline`, bc8b3772 → 本节末提交; 研究员第四轮 `codex_round4_review_2026-09-10/pipeline/` 的 P1/P1/P2 收口)

> 只做研究分支半边; 不改任何研究结论(G2 FAIL / v4e 无换装资格 / 18 格 (C) 不变); 无训练、无 GPU、不动 `~/dl_quant_live*` 与研究主线、不碰研究员 worktree。pod2 只在 `/workspace/review_scratch/` 备份→同步→跑测试。**VERIFIED** = 收据/日志可查; **INFERRED** = 推断。

### R0 提交表(每项一提交; 第四轮 117 项全部保留, 两条「调用者定标准」的期望改写并在断言文字里注明)
| 提交 | 项 | 改动 | 检查项 |
|---|---|---|---|
| f0c84502 | **r5-1** | 冻结资格合同 `A/ELIGIBILITY_CONTRACT.json` + `v4_gate_common.load_contract/approved_sources` + `require` 批准源检查 + 判官按合同推导标准(臂绑定 + 书绑定)+ 合同进 sha 清单 | 117 → 143 |
| 21a8bddd | **r5-2** | 判官严格书合同(cols/symbols 必在、W 有限、各臂 symbols 轴逐位相同)+ 任何模式下冻结窗 gross_total 有限且 > 0 | 143 → 151 |
| 10795c14 | **r5-3** | pod2 同步(.pre_r5 备份先列出再 scp)+ pod2 151 日志 + pod2 逐文件 sha + 清单 88 文件 + 研究员三套 harness 原样重跑收据 | 151(pod2 151) |
| (本提交) | **r5-4** | 本节 | — |

### R1 每项改了什么 / 怎么证的(对应研究员 REVIEW 的编号)
1. **[P1] 标准由谁定(REVIEW §2, `judge_actual_G2_not_export` / `actual_STEP1_downgraded_profile` / `actual_unknown_gate_one_input`)**: 第四轮 `JUDGE_ELIGIBILITY` 的 gate / self_sha / profile / inputs 全由调用者填, `require` 只核「调用者说的门与调用者给的数据自洽」, 所以真 G2 PASS、STEP1 降 profile、未登记门名都能让 A1e 四格 PROMOTE。现在: (a) 判官从**自己目录里的** `ELIGIBILITY_CONTRACT.json` 读标准(路径写死, 没有 env 能换合同; 换合同 = 换受审装置, 合同 sha 写进判官输出 `contract.sha256` 与 sha 清单); (b) 合同逐臂给 `candidacy_gate`(五个可晋级臂 A1/A1s/A1e/A2/A3 都是 `BUNDLE_export`)、profile、书绑定; 逐门给 `approved_source_sha256`(G2/STEP1/STEP2 = 归档门文件 sha; **BUNDLE_export = 空**: 物理导出门不存在, 空表 = 没有任何收据能授予候选); (c) `JUDGE_ELIGIBILITY` 只剩 `{arm: {receipt, inputs}}` 定位收据; 调用者若还报 gate/self_sha/profile 且与合同不一致 ⇒ `caller-supplied standard conflicts with the frozen contract` 不合格(一致则忽略); (d) 收据的 gate ≠ 合同门 ⇒ 不合格(「质量门的 PASS 不是导出候选」); 收据 self_sha256 ∉ 批准表 ⇒ 不合格。证: [N] 真 G2 PASS(归档 closure 门实跑写出)定位给 A1e ⇒ 0 PROMOTE; 调用者同时报 gate=G2_closure+真 sha ⇒ conflicts ⇒ 0; STEP1 PASS + profile=v4s ⇒ 0; 未登记门 ⇒ 0; 未登记臂 A9 ⇒ 不合格; 无合同的装置拷贝 ⇒ informational + WARNING; 畸形合同 ⇒ 同; **现网归档判官 + 现网合同 + 完整绑书的 A1e 收据 ⇒ 仍不合格**(`no approved gate source … physical gate is not built`); 正控(装置拷贝里的测试合同把归档导出器 sha 列为批准源)⇒ A1e 恰 4 PROMOTE 且输出记合同 sha/批准表。
2. **[P1] map key 不是经济工件绑定(REVIEW §3, `receipt_A1e_relabel_to_A1` / `book_replaced_after_receipt`)**: 现在 `receipt.arm` 必须等于被判臂; 并且**判官自己**把该臂四份被判书文件(`book_{dyn,fix}_s{42,2027}` = `<JUDGE_HC>/dev_v4/probe_artifacts/w10_…_<arm>_<seat>_s<seed>.npz`)加进声明输入, `REQUIRED_INPUTS["BUNDLE_export"]` 从 7 项变 11 项, 于是收据必须 hash 过这四份书且 sha 等于判官加载的文件。证: [N] A1e 收据放在 key A1 下 ⇒ `bound to arm 'A1e'`, 0 PROMOTE(第四轮 6); 收据 arm 字段伪造成 A1 但书 hash 是 A1e 的 ⇒ `book_dyn_s42 changed since the receipt`; 收据封好后改 A1e 经济序列 ⇒ 不合格(第四轮 4 PROMOTE); 收据没 hash 书 ⇒ `no sha for input book_dyn_s42`。
3. **[P1] 门源码「运行时 pin」≠「受审程序」(REVIEW §4 drift)**: `require` 在 pin 与收据相等之后再查 pin ∈ 合同批准表; 治理门(在 REQUIRED_INPUTS 里的)旁边没有合同 ⇒ 直接拒(`nothing can be required without the frozen research definition`); 未治理门(既未登记也不在合同)不受影响, 但它们映射不到任何臂, 授不出候选。新 CLI `v4_gate_common.py approved <gate> <sha>`。证: [E] 拷贝并改动 closure 门后实跑 ⇒ 自签收据 PASS; `require … self_sha=<改后 sha>` ⇒ rc 3 `not an APPROVED source`(第四轮 rc 0); [J] 新场景 `gate_edited_rerun`(链运行时 pin 到改后文件)⇒ rc 3 / 0 训练 / 无 DONE(研究员 `chain_runtime_gate_sha_accepts_changed_recipe`: rc 0 / 8 / DONE); 三条链成功路径在**带翻译后合同**的装置拷贝里仍 8/2/DONE、16/4/DONE。
4. **[P2] 严格书合同(REVIEW §5 七例)**: `JUDGE_REQUIRE_W=1`(别名 `JUDGE_STRICT_BOOK=1`)现在 = cols==COLS 且 symbols 必在、`d30_n2_c42_W` (n, n_symbols) **有限**、各臂 symbols 轴**逐位相同**(W 列按位置对齐, 一臂反序 ⇒ rc 2); **任何模式**下冻结窗 `gross_total` 必须有限且 > 0(−1 配分子翻号曾保持 g 并 4 PROMOTE, +inf 曾令 g=0 通过; 现 rc 2, 默认模式亦然)。默认模式其余仍是明写的 rec-only 窄合同(`rec_only_default` rc 0)。证: [N] 七例 + 正控(严格 + 测试合同 ⇒ 4 PROMOTE)+ 别名。
5. **合同进清单**: `make_sha_manifest.py` 把 `ELIGIBILITY_CONTRACT.json` 与 .py/.sh 同列; 清单 88 文件, MATCH_POD2 **65**(64 + 合同 `3299dc97…`), 快照 23(r0 2 / r1 14 / r2 1 / r3 6), 收据→源码 sha 核 4 / 旧 schema 15(VERIFIED, `receipts/v4_scripts_sha_full.json`)。

### R2 研究员第四轮三套 harness 原样重跑(拷贝到 scratch, 未改其脚本; device/chain = 本轮归档 87 文件 + 合同; `A/receipts/researcher_round4_cases_rerun_after_r5.json` 逐案给其记录与本轮结果)
| 类别 | 数 | 案例 |
|---|---|---|
| **意图翻转** | 11 | `judge_actual_G2_not_export` 4→**0** · `actual_STEP1_downgraded_profile` 4→**0** · `actual_unknown_gate_one_input` 4→**0** · `receipt_A1e_relabel_to_A1` 6→**0** · `book_replaced_after_receipt` 4→**0** · `negative_gross` rc 0/4→**rc 2** · `infinite_gross` rc 0→**rc 2** · `nonfinite_W` 4→**rc 2** · `symbols_order_reversed` 4→**rc 2** · `no_cols_strict` 4→**rc 2** · `no_symbols_strict` 4→**rc 2** |
| **按设计翻转** | 3 | `valid_strict_schema_positive` / `valid_new_eligibility_positive` / `rec_only_default` 4→**0 PROMOTE**: 现网合同 BUNDLE_export 批准表为空, 任何合成导出收据都不授候选; 允许路径由我方 [N] 正控(装置拷贝 + 测试合同)证明。研究员若要在自己 harness 里跑正控, 需在其 device/chain 旁放一份把其合成导出器 sha 列为批准源的合同 |
| **harness 拷贝无合同** | 7 (+1) | `chain_success` 8/2/DONE→rc 3/0, `chain_fail_shard0-3`, `chain_merge_fail`, `chain_merge_missing_marker`: 其 `chain_case` 只拷 .py/.sh 到翻译后的 root, 合同不在旁 ⇒ 治理门 fail-closed(`frozen contract missing`)。这是**新装置契约**: 装置拷贝必须带合同, 且路径翻译改变门字节 ⇒ 拷贝里的合同要重算批准 sha(我方 [J] harness 如此做, 8/2/DONE 保持)。`chain_runtime_gate_sha_accepts_changed_recipe`(drift retry)rc 0→**3** 方向对, 但其拷贝里的拒因是缺合同而非「未批准」; 「未批准」拒因由我方 [J]/[E] 在有合同时证明 |
| 逐字相同 | 42 | faults 其余 22(g2 4 / require 6 / generator / post_old_marker / data 2 / judge 9)、extra 其余 12(含 `chain_valid_wrong_gate_source` rc 3、四个 judge 0 PROMOTE、四个 rc 2)、trust `actual_G2_wrong_expected_gate` 0→0 |

### R3 收据
- 本地 `/usr/bin/python3 A/tests_pipeline_gates.py` ⇒ **ALL PASS 151**(r5-1 后 143, r5-2 后 151; VERIFIED); pod2 `/workspace/venv/bin/python -B tests_pipeline_gates.py` ⇒ **ALL PASS 151**, 2m04s, `A/receipts/tests_pipeline_gates_pod2_r5.log`(VERIFIED)。
- pod2 同步 5 文件(judge_v4 / v4_gate_common / tests / make_sha_manifest / 合同): **先** `cp -p f f.pre_r5` 并 `ls -la` + sha 列出四份备份(judge 9cf7853f = 第四轮 pod2 sha ✓)**再** scp; 同步后逐 sha 与本地相等; 同步前 GPU 0%、无链在跑(VERIFIED)。逐文件 sha `A/receipts/pod2_shas_2026-09-10T0544Z.txt`(88 名, 17 MISSING = 全部快照, 按设计)。
- 研究员 harness sha 与本轮 device 8 文件 sha 在重跑收据里。

### R4 未闭合 / 边界(明写)
1. **物理导出门仍不存在**: 合同 BUNDLE_export 批准表为空 ⇒ 任何真实判官运行都是 informational(与「v4e 无换装资格」一致)。`v4e_gate_export.py`(finalize `BUNDLE_export`, 输入 = 7 导出件 + 该臂 4 份被判书)是新装置, 未做; 落地后其受审 sha 写进合同才有第一条允许路径。
2. **合同本身可被有写权者改**: 程序门不能阻止(研究员亦如此判); 能做的是合同 = 受审文件(sha 清单 + git), 判官输出记合同 sha, 复核者据此核对。
3. **装置拷贝契约变了**: 拷贝必须带 `ELIGIBILITY_CONTRACT.json`, 路径翻译后须重算批准 sha; 研究员的 `audit_faults.py chain_case` / `trust_checks.py` 需相应更新(否则链场景全 fail-closed, 见 R2)。这是保守方向, 但会让旧 harness 的成功路径读不到。
4. 输入下限(`REQUIRED_INPUTS`)仍在代码里, 批准源与臂映射在合同里 —— 两处而非一处; 合同只引用门名。未治理门无下限无批准表(与第四轮同)。
5. 严格模式的 symbols 轴一致性只在**臂**之间检查, 不含 RAW 参照(参照是另一书系, 复现只比 g); 默认模式仍是 rec-only(gross > 0 除外)。
6. `JUDGE_HC`(书文件位置)仍是 env: 它定位工件, 不定义标准; 工件身份由书绑定 hash 核。
7. 15 份旧 schema 收据仍无 self_sha; pod2 现网 `v4_gates/*.json` 仍旧 schema(自第三轮起链已拒派发); 未重跑任何数据门。

### R5 我方自报(第五轮)
- 首次跑套件 2 红: (i) `r4_inline_json` 的条目在书夹具存在前生成 ⇒ 没绑到书(测试顺序错, 非产品); (ii) 「现网合同空批准表」一案的条目带了调用者 self_sha ⇒ 先撞冲突检查(结果同为不合格, 但拒因不是想证的那条)。两处只改测试, 产品源码未动。
- r5-1 / r5-2 的拆分是**事后**做的: 先在工作树里去掉严格合同的代码块与测试提交 r5-1, 再恢复最终文件提交 r5-2; 两个中间状态都编译通过, 最终文件与跑出 151 的版本逐字节相同(`cmp` VERIFIED), 但 r5-1 单独那一刻的 143 项没有单独跑过。
- 重跑收据第一版把研究员 trust14 记录读错(其 RESULT.json 里是 dict 不是 list)⇒ 14 案标成 ONLY_ONE_SIDE; 用其 `collected/trust/*/RESULT.json` 逐案重建后在推送前 amend 了 r5-3。


---

## §EXECUTOR · 第五轮(复审 cfaf1bbe: Q1–Q7 / E4-P1 / E4-P2A–C / A1)→ 实盘分支 b840ed9

> 全电池 132/132(首跑 2 红为电池自身缺陷, 修后重跑全绿), 已推送 `review/b0a573a1-executor`。运行树 d040c74 零接触。处置文档(研究主线): `docs/REVIEW_ACCEPT_round4_codex_cfaf1bbe_2026-09-10.md`; 跨读数合同预注册: `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md`(未落码)。你的五类阻断全部接受; 共因按你的诊断处理: 进入公式的请求状态/已知数量/账本行不完整或被另一口径替换 —— 所以第五轮的主体是**请求生命周期 + 单一读者**, 不是阈值。

### 改了什么(对应你的编号)

| 你的编号 | 文件 / 函数 | 改动 | 证据(`tests_request_identity_unknown.py`, 117/117) |
|---|---|---|---|
| Q1 | `binance_executor`: `ledger_row_columns` / `apply_ledger_to_plan`(新); topup 三条出口; `_settle_leg_by_identity`; `binance_broker.last_fill_details` | 每张请求记 `confirmed_qty` = 场所 **executedQty**(`last_fill_details` 新返回 `status` / `executed_qty` / `orig_qty`), 不再 名义/均价; 行的 `filled_qty`(腿关闭时 Σ)、`filled_known_qty`、`filled_unknown_qty`、`filled_known_notional`、`filled_notional`、`avg_fill_px`(同集合 Σ名义/Σ数量)**全部由一个读者产出, 成功/传输/拒绝/结算四条路径都过它** | [21] 50@1+50@2 ⇒ filled_qty 100 / avg 1.5; RC 100 CLEAN、75 异常 |
| Q2 | `request_remaining` / `ledger_totals` / `ledger_closed`(新语义); `_settle_leg_by_identity`; `apply_commission_to_rows` 门 | 请求状态 = (state, C, terminal): 子成交只抬 C, **不设终态**; 终态只由 status ∈ TERMINAL 或 C ≥ Q; 未读到回包的请求 terminal=False; 余量 = 0(拒绝/未发/终态) / |Q|(一无所知) / |Q|−|C|(仍开); 腿关闭 = 全部已发请求终态且名义已知且无矛盾; 有账本的行**每次归属都重跑结算** | [22] child 10 ⇒ known 10 / 带 90 仍 UNKNOWN; 10+70 ⇒ 80; 达 100 才关; PARTIALLY_FILLED 10/50 ⇒ 带 40+50 |
| Q3 | `reconcile._exec_qty`; `ledger_inconsistencies` | 矛盾检查在读者**第一行**(先于 filled_qty/bounded/structural); 生产者侧(回包 executedQty > origQty)与结算侧(超量 / 反向 / 非有限 qty·notional / quote≠qty×price)都记; 矛盾腿永不关闭 | [23] 60 关 50 ⇒ 不关、不可测; 回包 60/50 ⇒ 不写 110; child NaN / SELL 对 BUY ⇒ 矛盾 |
| Q4 | `_settle_leg_by_identity` | 每请求 `trade_qty{trade_id}` / `trade_quote{trade_id}` 集合; C = Σ 并集, 单调不降; 生产者读数大于子集时保留 | [24] [t1,t1,t2] ⇒ 40; 再给 [t1] ⇒ 40 |
| Q5 / R7 | `anchor_loop.clamp_venue_cap` + 调用方 | **先**校验全部名 target/held(raw None 亦无效)再 cap; held 无效的名弹出 | [27] 四组合 |
| Q7 | `_exec_qty` fn/avg 路径 | fn、px 有限且 px > 0, 否则不可测 | [17]/[23] |
| E4-P1 | `venue_fills._scan_orders` / `settle_ambiguous_legs`(重写) / `anchor_loop.complete_anchor` / `binance_executor.apply_fill_details` / topup UNKNOWN 分支 | `_scan_orders` 读 status: NEW/PARTIALLY_FILLED 记 `non_terminal`(0 成交也返回记录), 输出 `executed_qty`/`orig_qty`; `settle_ambiguous_legs` 遍历**全部** live 计划: 匹配且仍开 ⇒ `cancel_order` → 复查, 终态 ⇒ 事实 / 仍开或失败 ⇒ UNKNOWN; 未匹配 ⇒ 满页 UNKNOWN, 否则查单并核 **symbol / clientOrderId / orderId / side / origQty**, 非终态同上; 已确认单的 −2013 ⇒ UNKNOWN(只有 `submit_ambiguous` 的才判 absent, 且标明假设); 同名两计划 ⇒ UNKNOWN; `complete_anchor`: `unknown |= 仍开的名 − found |= cancels.unresolved`; UNKNOWN 名的 maker 行带 C(场所 executedQty)与余量 | [25] 七格 + wiring 断言 + `_scan_orders` NEW 0 返回记录 |
| A1 | `topup` 循环顺序 | UNKNOWN 名: maker 行 → (熔断 ? skipped_venue_lock : skipped_unknown_fill); 已知名: maker 行(filled/partial_expired)→ 熔断门 → 补单 | [26] 四断言 |
| E4-P2A | `venue_fills.flatten_exec_from_trades` | 键 (symbol, orderId) | [28] |
| E4-P2B | `binance_broker._FLATTEN_SEQ` | 模块级 `itertools.count`(进程级) | [28] |
| E4-P2C | `flatten_all` except 分支 / `watchdog._write_flatten_rows` / `submit_maker` 预检 | 传输失败 ⇒ `execution_unknown`(submitted, 非 rejected, order_id 不借前单); 行类 `filled_amount_unknown`; `client_id_dropped` 入行; `submit_maker` 开头对全部计划算最长 id(`-3c99`), 超 36 在任何 POST 前抛 ValueError(全有或全无) | [28] |

### 你的反例在修复分支上的观测

| 反例 | 第四轮 | 第五轮 |
|---|---|---|
| risk Q1 `all_confirmed_two_prices` | 75 张; 观察 75 CLEAN | filled_qty 100; 75 异常 25 |
| risk Q1 `last_close_switches_back_to_stale_avg` | 150 张 | 关闭时 filled_qty = Σ C = 100, avg 同集合 |
| risk Q2 `maker_partial10_then_child80` | 关腿 10, 80 不更新 ⇒ 残差 70 报警 | child 10 ⇒ known 10 / 带 90; 80 到来 ⇒ C 80; 场所 80 解释 |
| risk Q2 `positive_partial_submit_marked_confirmed` | known 10 + unknown 50(丢 40) | known 10 + 带 90 |
| risk Q3 `last_unknown_closes_over` / `all_confirmed_overquantity` / `..._nan_qty` | fn 110 / 110 / 100 CLEAN | 矛盾 ⇒ 不可测(异常), 腿不关 |
| risk Q4 重复 child / 较小子集 | 60 / 40→10 | 40 / 40 |
| risk Q5 四组合 | planner ValueError/TypeError | 全部 invalid, 不进 planner |
| executor E4-P1 五格(NEW 0 / PARTIALLY_FILLED 4 / matched NEW / matched PF / 满页含 NEW) | 补 10 / 6 / 10 / 6 / 10 | 撤后仍开 ⇒ UNKNOWN 不补; 撤成功且复查终态 ⇒ 其事实(正控 CANCELED 4 ⇒ 4) |
| executor E4-P2A/B/C | 漏恢复 / 同 id / submitted_rejected | 两名皆恢复 / 不同 id / execution_unknown |
| account A1 四格 | BUSDT maker 行 0 ⇒ BREAK | maker 行保留 ⇒ 残差 0 |

**你的脚本需改的地方**: `phase_b_full_chain_attempt02.py` 的 DELETE mock 现在会被 `settle_ambiguous_legs` 再调用一次(先撤后查), 且 GET 查单记录需带 `origQty`/`side`/`orderId`(否则按「非我方记录」落 UNKNOWN —— 也是不补单, 但不是你要测的分支); `risk_contract.py` 的 `all_confirmed_two_prices` 回包需带 `executedQty`(第五轮的数量来源), 缺 executedQty 时数量回退 名义/该请求均价(仍是同请求恒等式)。

### 未闭合(明写)
1. **Q6 / 合同 §2.4 跨读数**: 预注册已写(E_s 未解释余额 + P_s 未决请求跨窗延续, 只由可归属成交/显式记账/签字更正解决; 需 41 天账本副本回放 + 用户字), 未落码。我第四轮「只可能误报不会漏报」的说法撤回。
2. **−2013 终局性**: 仍是显式业务假设(仅 `submit_ambiguous` 计划, 非满页, k 窗后); 报告文字已标注。
3. **跨进程同秒平仓 id**: 进程级计数, 跨进程未解。
4. **M5 对 reconstructed 行的 TypeError**(同锚有 anchors 行时): 冻结模块再封存候选; 当前 12Z 无 anchors 行不触发。
5. income 缺行恢复 / 币种换算 / 物理 BUNDLE_export 门: 未做。
6. **maker/requote 的 `[:36]`** 仍在, 但预检保证不可达(最长 id 已在发单前拒绝)。

### 电池自身在第五轮里暴露的两处(非产品代码)
- `tests_notional_backfill` 的变异注入锚点随 `apply_commission_to_rows` 门重排失配(`if` → `elif`), 已更新锚点, 变异仍成立(旧行价格重建、金额不重建 ⇒ 不可测)。
- `tests_daily_summary` 的 Q2/跨日两条读**全日** nav 行数决定「是否可检」, 而工具渲染的是 `--since 24h` 窗; 状态副本超过 24h 后窗内只剩 1 行, 两条变成假红(06:1xZ 首现, 与第五轮改动无关, 第四轮 b 电池 03:1xZ 时窗内仍 ≥2 行)。改为按工具自报的窗内行数判, 不可检时打 NOT EXERCISED(不算过); 盲区自述已更新。**含义**: 在陈旧状态副本上的绿电池对这两条什么都没证明。

### 我方在第五轮里承认的自己的错(见处置文档 §6)
一个量两个读者 / 子成交当终态 + `filled_notional is not None` 屏蔽 / 矛盾检查藏分支 / 熔断先决定后记账 / 查单只核 cid、「−2013 唯一归零路径」表述不准 / 「只误报不漏报」撤回 / 夹具把非场所合同当真(改夹具不放宽规则)。

### 请复核(第五轮新问题, 我方自报)
1. `request_remaining` 对「终态但数量不可读」的已确认请求给 0 余量(它不会再成交), 其数量由名义/该请求均价回退 —— 请判断是否应改为不可测。
2. `settle_ambiguous_legs` 对仍开的单执行 `cancel_order`: 这是阶段 B 的第二次撤单(k-cancel 之后), 请看是否与 `stuck_orders` pin 语义冲突。
3. 一无所知(state unknown)的请求终态恒为 False, 即使 tif=IOC —— 保守方向, 但请确认与你的合同一致。
4. 预检以 `-3c99` 为最长 id 假设(≤ 99 块); 更大块数请指出。


---

## §EXECUTOR · 第六轮(复审 ce7b3cf4: R5-E1 / R5-QA / R5-QB–QE / R5-E2 / ID 边界)→ 实盘分支 07929ed

> 全电池 132/132, 已推送 `review/b0a573a1-executor`。运行树 d040c74 零接触。处置文档(研究主线): `docs/REVIEW_ACCEPT_round5_codex_ce7b3cf4_2026-09-10.md`; Q6 预注册修订 1: `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md`(累计恒等式 + 双时钟, 未落码)。两条承重项与全部边界项接受; 合同按你的 §4 实现: 数量先于计价, 终态且 C 可信 = [C, C], 金额缺失另报, C 未知不因终态归零。

### 改了什么(对应你的编号)

| 编号 | 文件 / 函数 | 改动 | 证据(`tests_request_identity_unknown.py`, 136/136) |
|---|---|---|---|
| R5-E1 | `anchor_loop.complete_anchor`; `binance_executor.apply_fill_details` / topup UNKNOWN 分支; `venue_fills._scan_orders` | `unknown |= (cancels.unresolved − found)`(按请求身份, 较新可靠终态覆盖旧未决); `found ∩ unresolved` 的名清 pin(`stuck_orders.clear(mode, [(symbol, cid)], reason)`, INFO 页; 失败 HIGH 页); `_scan_orders` 输出 `terminal`(我方匹配单全部终态), `apply_fill_details` 写 `venue_terminal`(partial 事实不算终态), UNKNOWN 路径 maker 行的请求 `terminal` 取自它 | [29] 终态 + C 4 ⇒ 带 None / filled_qty 4; 持仓 10 ⇒ 异常 6; 仍开 + C 4 ⇒ 带 6; wiring 断言 |
| R5-QA | `request_remaining` / `ledger_qty_closed`(新) / `ledger_row_columns` | C 可信 ⇒ 终态 0 否则 Q−|C|; C 未知 ⇒ |Q|(终态与否); `qty_closed`(全部已发请求终态且 C 可信)⇒ `filled_qty` = Σ C 与金额是否可读无关; `closed`(金额)仍单独决定 `filled_notional` | [30] 20(无金额)+50 ⇒ filled_qty 70 / 带 None; 100 ⇒ 异常 30; C=Q 金额未知 ⇒ 已知 100 |
| R5-QB | `binance_broker.last_fill_details` | 只有明确 `"0"` 是零; 缺失/null 落到同请求 cumQuote/avgPrice 推导(`executed_qty_source` 标记); 都不可读 ⇒ None | [31] |
| R5-QC | `ledger_row_columns`; `reconcile._exec_qty` | 均价只在每个已执行请求同时贡献金额与数量时写出; 账本行 `filled_qty` 为 None 时读者一律不可测(bounded 分支 known_qty 缺失亦然), 不回退到名义/均价 | [32] 150 / filled_qty None / avg None ⇒ 不可测 |
| R5-QD | `_exec_qty` bounded 分支 | 价格有限且 > 0 才除 | [33] |
| R5-QE | `_settle_leg_by_identity` | 同 trade id 不同 qty/quote ⇒ `inconsistent`, 首次读数保留 | [34] |
| R5-E2 | `venue_fills.settle_ambiguous_legs`(`_keep_partial`); `complete_anchor` | 撤单/复查失败或复查仍开时, 已读到的 executed_qty/金额作 `partial` 返回并并入 details(标 `partial: True`, 不算终态) ⇒ maker 行 known C / 带 Q−C | [35] 查单 PARTIAL 4 + 撤失败 ⇒ UNKNOWN 且 partial 4 ⇒ 行 known 4 / 带 6 |
| ID 边界 | `submit_maker` 预检 | 按每个计划的真实块数 `split_for_market(|qty|, mkt_max_qty, step)` 算最长 id; 不再假设 99 | [36] 100 块 + 长名 ⇒ POST 前拒; 1 块 ⇒ 过 |
| 夹具 | `tests_transport_resilience._CB.last_fill_details` | 回包形状改为真实(带 executedQty/status): 第五轮「终态但 C 未知归零」的特例条款删除后, 旧夹具的「已知 5 未知 5」期望在真实形状下成立 | transport 92 绿 |

### 你的反例在修复分支上的观测

| 反例 | 第五轮 | 第六轮 |
|---|---|---|
| R5-E1 撤失败 → PF4 → 撤成功 CANCELED/4 | known 4 / 带 6 / pin 留 / 持仓 10 CLEAN | known 4 / 带 0 / pin 清 / 持仓 10 异常 6; 合法补 6 照旧 |
| R5-QA EXPIRED20(无金额)+FILLED50 | known 70 / 带 30 / 持仓 100 CLEAN | filled_qty 70 / 带 0 / 持仓 100 异常 30 |
| R5-QA 反向 C=Q=50 金额未知 | 不可测 | filled_qty 已知 |
| R5-QB 缺 executedQty + 100/2 | 总量 50 | 同请求推导 50 + 50 = 100(标源) |
| R5-QC 金额 100 无数量 + 50@1 | RC 150 | 不可测 |
| R5-QD 旧行 avg NaN | NaN 两门 CLEAN | 不可测(异常) |
| R5-QE 同 id 20→50 | 覆盖 | 矛盾 |
| R5-E2 查单 PF4 + 撤失败 | known 0 / 带 10 | known 4 / 带 6 |
| 100 块 | maker 已发 1 才拒 | POST 前拒 |

**你的脚本需改的地方**: `phase_b_full_chain_attempt02.py` 的 `cancels.unresolved` 夹具 —— 第二轮撤单成功后请断言 pin 被清(`stuck_orders.load(mode)` 为空)且 maker 行 `filled_unknown_qty is None`; `quantity_boundary` 的 `original_broker_missing_ex` 现在应读到 `executed_qty 50` 与 `executed_qty_source`。

### 未闭合(明写)
1. **Q6**: 修订 1 已写(累计恒等式 + 双时钟), 未落码; 请先复核修订 1 的数学, 再谈 41 天回放。
2. **−2013 终局性**: 仍是显式业务假设。
3. **跨进程同秒平仓 id**; **M5 对 reconstructed 行的再封存**; **income 缺行 / 币种换算**; **物理 BUNDLE_export 门**: 未做。
4. **终态但 C 未知**: 现按 |Q| 带 + 读者不可测(你的第 3 点); 若你认为应区分「终态 + 金额可读 + 均价可读」(同请求可推 C)与「都不可读」—— 前者已在生产者推 C, 后者不可测。

### 我方在第六轮里承认的自己的错(见处置文档 §5)
按请求身份结算只做了一半(`_still_open` 做了, `unresolved` 和 pin 没做)/ 数量授权绑在金额可读上 / `-3c99` 是假设 / 读者侧仍留名义回退 / 「预检保证全锚原子」超出范围。

### 请复核(第六轮新问题, 我方自报)
1. 清 pin 用的是 `found ∩ unresolved` 的名对应计划的 cid(`{rid}-{sym}-{attempt_idx}`); 若 pin 的 cid 是 `-2` 重挂而 found 的是 `-1`(同名两请求), 清错; 同名两计划本轮已 ⇒ UNKNOWN, 但 pin 键仍请复核。
2. `_keep_partial` 只在查单记录通过 `_valid` 时记录; 若记录部分损坏(缺 origQty)则不记 —— 保守方向。
3. `venue_terminal` 对 partial 事实恒为 False; 对 `absent`(−2013 判未下达)的 updates 为 True(non_terminal 空)—— 与 −2013 假设同寿命。


---

## §EXECUTOR · 第七轮(复审 a99c447e: R6-§2 / R6-§3 / R6-QB / R6-P2)→ 实盘分支 5dc120a · 方法改为「先写事实表」

> 全电池 132/132(首跑 tests_alarm_digest 因陈旧副本红, 刷新副本后重跑), 已推送 `review/b0a573a1-executor`。运行树 d040c74 零接触。处置(研究主线): `docs/REVIEW_ACCEPT_round6_codex_a99c447e_2026-09-10.md`; **事实表**: `docs/DESIGN_request_fact_model_2026-09-10.md`(事实 × 来源 × 出口, 每格期望; 第七轮按表实现); Q6 修订 2: `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md` §1b(D1–D4)。你六轮的方法我这轮照做了三件: 原链端到端([37][38] 用未改的 `complete_anchor` 跑真实 broker + FakeNet 到 reconcile), 同夹具正反两向(拒单 × 持仓不变 = CLEAN; CANCELED 4 × 持仓 10 = 异常), 结构性保证(读者在行发出时最后重算, 分支不能改列)。

### 改了什么

| 编号 | 文件 / 函数 | 改动 | 证据(`tests_request_identity_unknown.py`, 155/155) |
|---|---|---|---|
| R6-§2 | `venue_fills._scan_orders` | 执行数量 / 金额 / 价格三种可读性: `exec_unreadable`(数量)、`unreadable`(金额)、`inconsistent`(负数 / NaN / 显式 0 伴正金额)各自成列; 缺 executedQty 由同请求 cumQuote/avgPrice 推导并列入 `executed_qty_derived`; `executed_qty` 只在数量不可读时为 None | [40]; **[37] 原链**: CANCELED 4 无金额 ⇒ maker 行 filled_qty 4 / 带 None / 金额 UNKNOWN / 0 补单; 持仓 4 CLEAN、10 异常 6 |
| R6-§3 | `binance_executor._order_row`; 两个「未发」出口 | `_order_row` 看到 `request_ledger` 就用 `ledger_row_columns` **覆盖六列**(known_notional / known_qty / unknown_qty / unknown_residual / filled_qty / filled_notional(若调用方未标 UNKNOWN)); 分支手写的列一律被推翻; 出口不再手写列; 标签 `filled` 而账本未关闭 ⇒ `ledger_label_mismatch` | [42]; **[38] 原链**: −2019 / −4400 / −1008 × 持仓 0 / 1 ⇒ 行 filled_qty 0.0, reconcile 无异常, 1 POST; EXPIRED 0 正控 filled 0 CLEAN |
| R6-QB | `binance_broker.last_fill_details`; 请求账本 | 负数 / NaN / 显式 0 伴正 cumQuote ⇒ `inconsistent`(不返回任何数); 请求记 `inconsistent` ⇒ 腿不可测 | [39] |
| R6-P2 | `venue_fills.settle_ambiguous_legs`; `anchor_loop.complete_anchor` | 匹配且终态的请求进 `terminal_matched`; `found_all = found ∪ terminal_matched` 用于 unresolved 覆盖与清 pin | [41] |
| 折叠矛盾 → 计划 | `apply_fill_details` / UNKNOWN maker 行 | `venue_inconsistent` 传到计划, 请求 `inconsistent` | [40] |

### 你的反例在修复分支上的观测

| 反例 | 第六轮 | 第七轮 |
|---|---|---|
| §2 CANCELED 4 金额不可读, 持仓 10 | known 0 / 带 0–10 / CLEAN | filled_qty 4 / 带 0 / 异常 6(原链) |
| §3 三种拒单 × 持仓 0/1 | 6 格 WD tripped | 6 格 CLEAN(原链); R5 同夹具本来 CLEAN ⇒ 版本配对恢复 |
| QB 负 executedQty / 显式 0 伴正金额 | 真零, 腿 50 通过 | 矛盾 ⇒ 不可测 |
| P2 allOrders 终态不进 found | pin 留、补单抑制 | terminal_matched ⇒ 覆盖 unresolved、清 pin, 补单照旧 |

**版本配对(上一轮期望被改的格)**: 无(第六轮所有 136 项原样保留; 新增 19 项)。

### 未闭合(明写)
1. **Q6**: 修订 2 已写(联合轨迹 / 两种余量 / 终态 C 未知 / 同截面重启, 验收 5b–5e), 未落码; 请复核数学, 特别是逐锚区间传播对 ≤3 张同名请求是否与你的联合枚举一致。
2. **R6-MARK**(数量已知无 mark 时 5b PARTIAL / 5e CLEAN): 未改; 动作合同需单独预注册(不擅改阈值)。
3. −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行 / 币种换算; 物理 BUNDLE_export 门。
4. 原链端到端测试到 reconcile 为止(未跑 phase C / watchdog 本体); 你的 RC/PB/WD 三段链仍是更完整的证据。

### 电池环境(非产品代码)
- 复审工作树的 `state/` 是陈旧副本; `tests_alarm_digest` 按其设计在 24h 窗内可读告警 < 8 时判「不可观测 = 红」(第七轮首跑因此红), 从运行树刷新 `notify_audit.jsonl` 副本(只读审计日志)后重跑全绿。规则已写入处置文档 §5-5: 跑电池前刷新副本并写明副本时间。

### 我方在第七轮里承认的自己的错(见处置文档 §5)
折叠里数量与金额共用一个 `unreadable` / 只测漏报方向、没测良性格 / 「终态 C 未知一律不可测」说过头 / decoder `<= 0` 把负数与矛盾当零。

### 请复核(第七轮新问题, 我方自报)
1. `_order_row` 的账本覆盖对 `filled_notional` 的处理: 账本已关闭 ⇒ 取账本 Σ; 未关闭而调用方未标 UNKNOWN ⇒ 保留调用方值并标 `ledger_label_mismatch`(不改标签)—— 是否应改为直接置 None?
2. `_scan_orders` 对「executedQty 缺失且 cumQuote/avgPrice 可读」的推导现在也用于 allOrders 页(不只 decoder); 推导值进入 `executed_qty` 与 `executed_qty_derived` —— 若你认为 allOrders 页的推导应降为下界而非可信 C, 请指出。
3. 端到端夹具把行时间戳统一放进回读窗(fixture 的 updateTime 2000 ms 不是被测对象); 窗口语义由既有 reconcile 套件覆盖。


---

## §EXECUTOR · 第八轮(复审 82cbe018: A 来源合并 / B 可靠终态门 / C 矛盾 ⇒ UNKNOWN / #1 读者写金额)→ 实盘分支 2381030

> 全电池 132/132, 已推送 `review/b0a573a1-executor`。运行树 d040c74 零接触。处置(研究主线): `docs/REVIEW_ACCEPT_round7_codex_82cbe018_2026-09-10.md`; 事实表补格: `docs/DESIGN_request_fact_model_2026-09-10.md` §3b / §4.3(来源合并是表里漏掉的一列, 本轮补上); Q6 修订 3: `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md` §1c(撤回「≤3 精确」, 联合可行集为对象)。

### 改了什么

| 编号 | 文件 / 函数 | 改动 | 证据(`tests_request_identity_unknown.py`, 173/173) |
|---|---|---|---|
| A | `binance_broker.merge_order_records`(新)/ `last_fill_details` | 提交回包与金额补查逐字段合并: 可读的 executedQty 不被缺字段撤销; 累计量不减(后读 < 先读 = 矛盾); 终态吸收(终态后 NEW = 矛盾); 显式 0 + 终态 = 测得零(任一入口); 金额/价格取可读者(后读优先); 负数 / NaN / 0 伴正金额 = 矛盾 | [43] 四格 + merge 单元; [44] 补单腿两链: 20(无金额)+50 ⇒ 70 / 持仓 100 异常 30; ACK+GET 0 + 50 ⇒ 50 / 持仓 100 异常 50 |
| B | `venue_fills._scan_orders` / `settle_ambiguous_legs`; `anchor_loop.complete_anchor` | 折叠保留匹配记录 `last_matched_rows()`; 匹配的请求: 记录缺 status ⇒ 按未匹配走查单; 身份不符(symbol / side / origQty / orderId)⇒ UNKNOWN; 只有显式终态且身份相符才 `terminal_matched`(覆盖 unresolved、清 pin) | [45] 无 status ⇒ 查单失败 ⇒ UNKNOWN(不清 pin 不补单); origQty 5 vs 10 ⇒ UNKNOWN; 显式 CANCELED + 身份 ⇒ terminal_matched |
| C | `anchor_loop.complete_anchor` | details 带 `inconsistent` 的名 ⇒ UNKNOWN(不入 filled, 不补单); UNKNOWN maker 行带 `inconsistent` ⇒ 读者不可测 | [46] 原链: 查单 C=0/N=4 ⇒ maker 行 inconsistent, 0 次补单, reconcile 任何持仓皆异常; 正控 CANCELED 0 ⇒ 补 10 成交 |
| #1 | `binance_executor._order_row` | 有账本: `filled_notional` = 读者(未关闭 ⇒ None, 标签改 `filled_amount_unknown` + `ledger_label_mismatch`); `avg_fill_px` = 读者同集合均价或 None; 不再回退分支值 | [47] |

### 你的反例在修复分支上的观测

| 反例 | 第七轮 | 第八轮 |
|---|---|---|
| A `known20_then_missing_C_and_N` | known 50 + 带 50, 持仓 100 CLEAN | filled_qty 70 / 带 0, 持仓 100 异常 30 |
| A `terminal_zero_after_ACK` | known 50 + 带 50 | filled_qty 50 / filled 50, 持仓 100 异常 50 |
| B allOrders 缺 status + 撤失败 | 清 pin, 补 10 | UNKNOWN, 不清 pin, 不补 |
| B allOrders origQty 5 vs Q 10 | 补 6 | UNKNOWN |
| C 查单 / allOrders C=0/N=4, C=−1/N=4 | 写 0, 补 10 | maker 行 inconsistent, 不补, 不可测 |
| #1 999/123 夹具 | 回退分支值 | None / 读者值 |

**版本配对(上一轮期望被改的格)**: [18]「匹配即不重查」、[41]「匹配且终态即 terminal_matched」改为带记录(显式终态 + 身份)才成立; `tests_signal_and_loop` 三处场所夹具行补 `symbol` / `origQty` / `orderId`(真实 allOrders 行必有; 身份门需要)。

### 未闭合(明写)
1. **Q6**: 修订 3(联合可行集为对象, 精确可满足性, 联合 checkpoint, 预测集, 证据/推断下界分离, 合同统一)未落码; 验收改为你的 8 组 40 条断言与网格解集原样重跑。
2. R6-MARK 不可定价数量动作合同; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行 / 币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。
3. 撤单回包(k-cancel 的 DELETE 响应带 executedQty)尚未进入 `merge_order_records` 的合并(它只合并提交回包与补查); allOrders 与查单记录之间的合并在 settle 里按「较新可靠终态覆盖」处理, 不是逐字段合并 —— 登记为下一格。

### 我方在第八轮里承认的自己的错(见处置文档 §4)
`terminal_matched` 把「没看到 open」当「证明了终态」且没过身份门(第七轮新增放行域)/「六列都被推翻」说过头 / 事实表漏了「同一请求多条记录如何合并」这一列 / Q6「≤3 精确」无证明。

### 请复核(第八轮新问题, 我方自报)
1. `merge_order_records` 把「后读 executedQty 小于先读」判矛盾 —— 若场所在撤单竞态下可能短暂回退(文档未见), 请指出; 我方按累计量单调处理。
2. 身份门对 allOrders 记录要求 `origQty` 与我方 Q 相符(1e-6 相对), 对被场所改量(如 -2027 截断后的接受量)的记录会判不符 ⇒ UNKNOWN(保守方向); 请判断是否有合法改量的情形。
3. 折叠矛盾 ⇒ 整名 UNKNOWN: 同名若有多条我方记录(-1 与 -2), 一条矛盾使另一条也 UNKNOWN(保守方向)。
