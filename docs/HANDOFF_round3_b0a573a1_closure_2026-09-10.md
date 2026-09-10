# HANDOFF round 3 · 独立研究员复审 31fa3e4e 的修复收口(给研究员第三轮复核)

> **创建:** 2026-09-10 01:3xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** PIPELINE 节完成(研究分支); EXECUTOR 节由主研究员另补(实盘分支) | **作废条件:** 两条分支分别合并后降为历史记录; 若研究员第三轮再出 P1, 以其复核件为准
> **被复审对象**: 研究分支 `review/b0a573a1-pipeline` 自 fb98a8f9 之后的第三轮提交(见 §P0 表); 实盘分支 `review/b0a573a1-executor` 的第三轮提交(主研究员另填)。
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
5. **快照 16 件不在 pod2**(按设计, 快照只在归档), 清单按前缀归类为 SNAPSHOT 不计入 DIFFERS。

## §EXECUTOR(实盘分支 `review/b0a573a1-executor`)

(由主研究员填写: P1-1 absent 语义 / P1-2 请求身份 / P1-3 UNKNOWN 消费者合同与对账授权带 / P1-4 408·-1007·-1006 / cap P2 / income 同毫秒饱和 truncated / 12Z 52 行补件重建器折叠。)
