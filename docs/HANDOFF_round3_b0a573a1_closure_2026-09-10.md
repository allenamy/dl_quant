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
