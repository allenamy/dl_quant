> **创建:** 2026-09-12 | **Session:** W3(research-chain engineer, team-lead 派工; 复核对象 = 独立研究员 0dfc0d87 R1–R5)| **状态:** delivered, 待研究员复核 + 用户裁定十月门源码(§7 (i))| **作废条件:** 装置目录 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/` 任一被引文件 sha 改变 ⇒ 本文数字按新 sha 复核; 十月新门源码入合同后 §7 (i) 关闭

# DESIGN: v4 月度重训链可执行化 — `chain_v4_monthly.sh` + 月配置合同 `v4_month.env`

**一句话**: 十月重训以前不可照抄执行(研究员 R1–R5 全部成立), 现在是一条驱动 + 一份月合同 + 一个空根负控; 每处旧缺陷都有一个会红的测试。**未变**: 九月产物零改动(所有改动在 env 未设时走九月常量, 三个生成脚本从基底逐位再生), 合同冻结的门源码零改动(`v4_gate_step1/2.py`, `v4_gate_common.py`, `judge_v4.py`, `v4e_gate_export_v2.py`, `gate_signal_parity_v2.py`, `ELIGIBILITY_CONTRACT.json` 一字未动)。**仍开**: 十月的数据门需要新源码 + 合同批准(用户字), 见 §7。

## §1 事实表(先于代码; 每格可在发出时重算; 行号 = 修前的 09-11 归档版)

| # | 事实(修前) | 位置 | 后果 | 处置(本文) |
|---|---|---|---|---|
| R1 | refit 默认 `F10_DLW=/workspace/dlw_ext` `F10_OUT=/workspace/f8_ext` `BEST_EP_FIX=-1`(argmax) | `pod_f10_refit_v4.py` L5–8 | 裸调用读上代输入、选 argmax、覆盖 `f8_ext/models/f10_live_s42.pt`; launcher 子 shell 的 `BEST_EP_FIX=7` 不回传 | 四个 env 必填, 缺一在 `import torch` 之前拒绝 rc 2(`REFIT_REFUSED` 点名缺键) |
| R1′ | `trained_through = E_ts[tr_idx[-1]]` = 全池末锚 | 同文件 L122 | 被读作「模型看过的末条标签」; 实际优化器只见 tr1 的 TBPTT 窗 | 保留旧键 + `trained_through_meaning`; 新增 `trained_through_label_utc` = `E_ts[starts[-1]+WIN-1]`(最后一个进 loss 窗的锚)、`_label_end_utc`(+4h)、`tr1_end_utc`、`validation_span_utc`; 同内容写 json 侧车 |
| R2 | `ALL_MONTHS = 202501..202608` 源常量 | `pod_f10_train_monthly_v4.py` L298; `merge_mwf_v4b.py` L13 | 202609 被拒 / 合并缺月 | `v4_months.py`: MONTHS_ALL 由 env 声明或由目标轴推导(完整月), 越过数据末完整月 ⇒ 拒绝; `MONTHS ⊆ MONTHS_ALL` 断言 |
| R2′ | 四片 `SH0..SH3` 手写 | `chain_v4_gpu3.sh` L10, `chain_v4_post_export.sh` L20 | 新月不在任何片里 | `chain_lib.set_shards_from_months_all` 轮转生成; 九月常量 ⇒ 与手写四片逐位相同(测试 [P]) |
| R2″ | 训练器白名单 `DLW in ("/workspace/dlw_v4raw","/workspace/dlw_hf3") and OUT == "/workspace/f8_v4"` | 训练器 L283 | 隔离的十月根被白名单拒绝 | 白名单值来自 `V4_DLW_RAW/V4_DLW_CLIP/V4_F8`(env 未设 = 九月常量) |
| R3 | 链脚本 `R=/workspace/review_scratch` 写死; `dlw_v4raw` `dlw_hf3` `f8_v4` 写死 | `chain_v4_data.sh` L6–8, `chain_v4_gpu3.sh` L9, `launch_mwf_v4b.sh` L3–7, `merge_mwf_v4b.py` L10/14/34/42/48/50, `build_dev_v4.py` L7–8, `run_v4_arms.sh` L3–4 | 月不可隔离; 十月会覆盖九月 | 月合同 41 键(§3); `D`(装置目录)与 `R`(月根)分离; 每个旧脚本的默认 = 九月常量 |
| R3′ | 数据链不跑 STEP1/STEP2, 只 require 既存收据; 收据是 09-09 旧 schema(无 gate/self_sha) | `chain_v4_data.sh` 全文; pod `v4_gates/step1.json` | 加固后的 require 拒绝旧收据; 没有「跑门」这一步 | 驱动 `gates` 阶段先跑门再 require(`run_gate` + `require_gate`) |
| R3″ | legs 需 4 个必需 env 无人传; 用哪代 king PRED 未定; king 导出在 legs 之后 | `pod_legs_v4b.py` L8; RUNBOOK 步 3/5 顺序 | 裸调用 KeyError; 或用上代 PRED | 驱动顺序 king → legs, `LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy`; legs 阶段先查本根 `BUNDLE_DONE` |
| R3‴ | `run_v4_arms.sh` 裸 `wait; grep … | tail -4` | L11 | 读到旧 END 行当本次结果 | 逐 PID 收 rc + `ARMS_FAIL/ARMS_DONE`; 驱动只计新增 `END … rc=0` 行 |
| R4 | `"generation": "v3_2026-09"` 源常量; 只有 `built_utc` | `pod_export_bundle_v4.py` L241 | 任何月导出都自称九月; 构建日冒充训练截止 | `BUNDLE_GENERATION` 必填(缺 ⇒ 任何 import 前 rc 2); provenance 加 `king_train_end_utc`(标签年 <2026 拟合的最后训练锚)、`king_train_last_label_end_utc`、`king_train_rule`、`data_axis_end_utc`; `built_utc` 保留 |
| R4′ | `LIVE_PINS` env 被忽略(硬读 `/workspace/live_pins.json`) | 同文件 L22 | RUNBOOK 的 env 行是装饰 | 读 env(默认九月路径); `FUND_AUG`/`FUNDING_DIR` 同 |
| R5 | 旧步骤文字作废但可复制 | RUNBOOK §2–§4 | 误执行 | RUNBOOK §0★ 顶部横幅 + 修订 3: 十月只经驱动 |

## §2 设计原则(五条, 每条对应一个会红的测试)

1. **合同, 不是默认值**: 月配置是一份文件, 41 个键**全部必填**(`chain_lib.load_month_env` 缺键/空值/非 `KEY=value` 行/命令替换 ⇒ rc 4)。子程序仍保留九月常量作默认, 但**驱动从不依赖默认**——每个 env 由合同显式导出。
2. **装置 ≠ 月根**: `D` = 装置目录(脚本、门源码、合同), `R` = 月根(收据、日志、deps 钉)。旧驱动 `D == R`(九月布局)不变。驱动经 `CHAIN_DEVICE_DIR` 交接(普通名 `D` 可能被任何 shell 继承——本轮被咬一次, §6.4)。
3. **门先跑再要**: `run_gate`(门程序自己经 `finalize` 写收据)→ `require_gate`(gate= + 运行时 self_sha= + 合同批准 + 全注册输入 sha)。驱动不比门更绿: 九月数据上 STEP1 字面 FAIL ⇒ 驱动在 gates 停, rc 3(§6.2)。
4. **拒绝优先于默认**: refit 与导出器在任何重 import 之前检查 env, 缺则 rc 2 并点名; 因此拒绝路径在无 torch/无 zload 的机器上可测(测试 [P] 三格 + 两格突变红)。
5. **负控与正控同装置**: `chain_v4_monthly_dryrun.sh` 用同一驱动对空根跑, 通过条件 = **诚实的**拒绝(rc 3 + preflight 收据 PASS=false + 点名缺项 + 0 启动); 崩溃的 preflight(rc 1, 无收据)**不算通过**(§6.4 教训)。

## §3 月配置合同 `v4_month_<YYYY-MM>.env`(schema; 九月值 = `v4_month_2026-09.env`, 十月模板 = `v4_month_2026-10.env.template`)

格式: `KEY=value` 行 + `#` 注释; 值内禁 `; & | \` $(`; 后键可引用前键(`$R/...`)。**41 键, 全部必填**:

| 组 | 键 | 含义 |
|---|---|---|
| 身份 | `V4_MONTH` `R` `PY` | 月标签; 月根(收据/日志/deps); 解释器 |
| 缓存/面板 | `CACHE` `PANEL_SPLICE` `PANEL_KING` `RAW_PATCH` `HOLE_CELLS` | holefix2 正典缓存(滚动补月); DL 目标/fea82/导出用 splice 面板; king 特征 PANEL_IN; 原始收益补丁; 洞格 |
| DL 目录 | `DLW_RAW` `DLW_CLIP` `F8` `KING_FEA` `KING_META` | RAW 目标+fea82; CLIP 目标+fea82; fea89/legs/mwf/models; king 特征与 meta |
| 折/种子 | `MONTHS_ALL` `SEEDS` `MWF_ROOT` | 折月全集(驱动对目标轴断言); 种子(训练器白名单 {42,2027}); mwf 子树 |
| king 导出 | `BUNDLE_OUT` `BUNDLE_TAR` `BUNDLE_GENERATION` `BUNDLE_BASE` `EXPORT_PANEL` `EMA_STATE_JSON` `LIVE_PINS` `FUND_AUG` `FUNDING_DIR` | RUNBOOK 步 5 的 env 逐字 + 代次标签 |
| legs | `LEGS_OLD` `LEGS_PANEL` | 在役训练 legs(AMENDMENT 5 旧行逐位); legs 面板 |
| 上代 | `DLW_EXT` `F8_EXT` `PREV_BUNDLE` `PREV_META` `REF_META` | 年折在役代(merge 拼接 pre-2025 / A0 preds); 上代 bundle 与 meta(build_dev 对齐); 原始记账参照 meta |
| 书层 | `HC` `KING_DIR` `EXPORT_ARM` `SIGNAL_RECEIPT` | dev 树(masks/calib/run_arm.sh/A0 基线书四件); SLOW 文件目录; 本月臂; 本月臂的信号平价收据 |
| 外部 | `BUILDER_FEA82` `BUILDER_FEA89` `BASE_TRAINER` | 装置目录外的两个构建器与基底训练器(preflight 钉 sha) |
| 门 | `GATE_STEP1` `GATE_STEP2` | 装置目录内门源码文件名; sha 必须在合同 `approved_source_sha256` 中 |

## §4 驱动 `chain_v4_monthly.sh <env>` — 阶段与门(单一顺序; `V4_STAGES=` 子集只省工不省门; `V4_DRYRUN=1` 使 preflight 之后任何阶段在启动前 die rc 9)

| 阶段 | 做什么 | 停下的条件(rc≠0 + `FAIL_*`) | 收据/标记 |
|---|---|---|---|
| preflight | 合同全键; 月根存在; 21 个装置文件在 D 且 sha 钉入 deps; STEP1/STEP2/BUNDLE_export 三个门源码经 `v4_gate_common.py approved` 核为合同批准; 每个输入存在(含 HC 的 masks/calib/run_arm.sh + A0 基线书 4 件); MONTHS_ALL 格式; SEEDS ⊆ {42,2027} | 任一缺 ⇒ rc 3 | `v4_gates/preflight.json` `deps_preflight_device.json` |
| cache | `cache_coverage_gate_v2.py $CACHE` | rc≠0 | `v4_gates/cache_coverage.json`(rc + cache sha) |
| data | RAW 目标(+补丁)→ DLW_RAW; CLIP 目标(无补丁)→ DLW_CLIP; fea82 → DLW_CLIP, cp+cmp → DLW_RAW; fea89 → F8; king 特征(clamp); `F10_GATE_{RAW,CLIP}.json` | 任一 rc≠0 或产物缺 | `chain_v4_data.log` |
| gates | **跑** `$GATE_STEP1`→`step1.json`, `$GATE_STEP2`→`step2.json`; 然后 require 两者(gate= self_sha= 全注册输入) | 门红 / require 拒 | `v4_gates/step{1,2}.json` |
| king | require STEP2 收据(绑 KING_FEA/META); 导出器 env 逐字 + `BUNDLE_GENERATION`; 校验 config.provenance.generation == 合同 | rc≠0 / 无 `BUNDLE_DONE` / 有 `BUNDLE_FAIL` / generation 不符 | `export_v4.log`, bundle |
| legs | 本根 `BUNDLE_DONE`; `LEGS_PRED=$BUNDLE_OUT/slow_pred_pinned.npy`; 2023 king 席位 ≥ 0.4(AMENDMENT 5 全行重算缺陷的判据) | rc≠0 / 无 `LEGS_V4B_DONE` / 席位塌 | `legs_v4.log` |
| mwf | `v4_months.py check` 目标轴 vs MONTHS_ALL; SH0..SH3 轮转; require STEP1(v4 profile); legs 标记; `pin_deps`(训练器/launcher/merge/chain_lib/v4_months/基底训练器/legs/fea89/目标×2/fea82/F10_GATE/合同); RAW × SEEDS 逐 PID; merge rc + `MERGE_DONE` | 任一片 rc≠0 / merge 红 | `deps_v4_monthly_mwf.json`, `f8/logs/*` |
| refit | 每种子 `F10_DLW F10_OUT SEED BEST_EP_FIX=7 EMBARGO=1` 显式; 侧车 `best_ep_rule == fix7` 且 `env_given.BEST_EP_FIX == 7` | rc≠0 / 无 `REFIT_DONE` / 规则非 fix7 | `refit_s*.log`, `models/f10_live_s*.json` |
| arms | `build_dev_v4.py`(`DEV_V4_DONE`)→ `run_v4_arms.sh $EXPORT_ARM`(逐 PID rc; 新增 `END … rc=0` 行 ≥ 2×种子数) | 任一 rc≠0 | `arms_A1.log` |
| judge | `judge_v4.py`(JUDGE_HC=$HC) | rc≠0 / 无 `JUDGE_V4_DONE` | `v4_gates/JUDGE_v4.json` |
| export | v2 出口门 gate(rc 0)→ require(`REQUIRE_OK`)→ 用收据的 `inputs_path` 写 `JUDGE_ELIGIBILITY.json` → 判官带定位器重判 | 任一 rc≠0 | `BUNDLE_export_v2_A1.json` `REQUIRE_v2_A1.json` `JUDGE_v4_eligible.json` |
| 终点 | 全阶段 ⇒ `CHAIN_V4_MONTHLY_DONE` + `MONTHLY_DONE.json`; 子集 ⇒ `CHAIN_V4_MONTHLY_STAGES_DONE` + `MONTHLY_STAGES_DONE.json`(DONE=false) | — | — |

## §5 改动清单(装置目录; 每项「默认 = 九月」除非注明; sha 见 §6.6 与最终报文)

| 文件 | 改动 | 九月行为 |
|---|---|---|
| `v4_months.py` **新** | 月集合推导/声明/子集/轮转分片 + CLI(derive/check/shards); `LEGACY_*` 常量只供测试 | — |
| `chain_lib.sh` | `D=${CHAIN_DEVICE_DIR:-$R}`; `V4_MONTH_KEYS`(41); `load_month_env`; `run_gate`; `set_shards_from_months_all`; `gate_sha/require_gate/pin_deps/run_shards` 用 `$D`; `run_shards` 用 `eval` 取 `SH$k`(bash 3.2 无 nameref) | D==R; 旧驱动逐字可跑 |
| `chain_v4_monthly.sh` **新** / `chain_v4_monthly_dryrun.sh` **新** | §4 / §2.5 | — |
| `v4_month_2026-09.env` **新** / `v4_month_2026-10.env.template` **新** | §3 | 九月路径 / 十月 TODO |
| `pod_f10_train_monthly_v4.py` | L283 白名单 env 化; L287 `_BASE` env; env_given +7 键; L298–300 → `v4_months` | env 未设 = 常量 |
| `merge_mwf_v4b.py` | L10/14/34/42/48/50 路径 env 化; MONTHS 由 `v4_months`; HF2 信息块不可对齐时 skip(原 `assert` 在十月必炸); `/20` → `/len(MONTHS)` | 同上 |
| `launch_mwf_v4b.sh` | B/PY/DLW/F8 env 化; 转发 MONTHS_ALL/V4_*; 空 MONTHS 拒 | 同上 |
| `pod_f10_refit_v4.py` | 头部四键必填(torch 前); 尾部报告 + 侧车 json | **裸调用被拒**(有意) |
| `pod_export_bundle_v4.py` | 头部 `BUNDLE_GENERATION` 必填(import 前); LIVE_PINS/FUND_AUG/FUNDING_DIR env; 训练集末锚打印; provenance 扩展 | **缺 generation 被拒**(有意) |
| `pod_legs_v4b.py` | `LEGS_OLD`/`LEGS_PANEL` env; meta 记录 | 同九月 |
| `build_dev_v4.py` | 全部定位器 env 化(9 个九月默认); `locators` 入 BUILD.json | 同九月 |
| `run_v4_arms.sh` | 逐 PID rc; `V4_HC/V4_KING_DIR`; SLOW 文件存在检查 | 同九月(多了失败会红) |
| `make_v4_scripts.py` + `gen_*_2026-09-12.txt` ×4 | 生成器发出以上三脚本的全部改动; 片段文件 = 归档脚本原文切片 | 三脚本从基底**逐位再生**(测试 [H] 绿) |
| `tests_pipeline_gates.py` | 新节 [P] **47 格**(含 8 格突变红 + E-0912-B 后的沙箱 `run_sandboxed()` 三格 + 静态「裸真写手调用」格 + 缺 `BUNDLE_OUT` 拒绝格); 只改本节(行 863–~1040), 其余节为 W4([O]/[Q])/W7([R])所有 | 151 旧格全绿 |
| `compare_gate_receipts.py` **新** | 门收据判决字段逐位对账(排除 utc/argv/sha 元数据) | — |
| `docs/RUNBOOK_monthly_retrain_2026-10.md` | §0★ 横幅 + 修订 3 | 历史不删 |

## §6 RESULT: 控制与收据(全部数字抄自收据; 收据目录 `v4_chain_2026-09-09/receipts/monthly_chain_2026-09-12/`)

### 6.1 本地自检(mac, `/usr/bin/python3 tests_pipeline_gates.py`)
- 修前基线: **ALL PASS (151 checks)**, exit 0(本会话开工时实测)。
- 修后(共享文件同时被 W4 [O]/[Q] 与 W7 [R] 扩展, 计数随之增长): 本节相关的最终一次本地全跑 = **328 格 / 327 绿 / 1 红**, 唯一红 = W7 [R] G0 对其自己新文件 `v4_gate_step2_m.py` 的检查(非本任务文件); **[P] 47/47 绿**(151 旧格全绿; 突变红 8 格: MONTHS_ALL 越界、MONTHS ⊄、四键齐备时拒绝不触发、generation+BUNDLE_OUT 齐备时拒绝不触发、malformed MONTHS_ALL、未批准门源码、无 DRYRUN 时 cache 阶段真跑、缺键合同)。此前的中间全跑: 222/222(151 + W4 [O] 29 + 本节 42)两次(mac bash 3.2 + pod2)。中途红并修复: (a) 三脚本再生逐位([H]) — 生成器补齐; (b) [r4] 两格链场景 — 见 6.4; (c) E-0912-B 后本节改为沙箱 — 见 6.7。日志 `receipts/monthly_chain_2026-09-12/tests_pipeline_gates_mac_final_run9.log`。

### 6.2 pod2 正控: 九月路径 + 隔离根(`/workspace/w3_monthly_chain_2026-09-12/`, 运行副本 `/workspace/review_scratch` 零写入)
- 装置副本 = git 单源: **100 文件 sha 相等**(`pod2_root/device_sha256_pod2.txt` vs 本地; 唯一差异为期间本地再改的 `tests_pipeline_gates.py`, 已重传)。pod2 上的自检: 222/222(修前文件)两次; 沙箱版 [P] **47/47 绿**(`tests_pipeline_gates_pod2_final2.crashed.log`: 237 绿后在 W7 [R] 段因我副本缺其 `receipts/monthly_chain_2026-09-12/w7_gates/` 而崩, 非本节); 全目录重传后的再跑见 `tests_pipeline_gates_pod2_final3.log`(若存在)。
- 合同: `v4_month_2026-09.pod2ctrl.env` = 九月合同仅 `R` 改隔离根、`$R/` 引用展开为九月绝对路径(sha `266c2d0dfc56…`)。
- **preflight PASS**: 21 装置文件钉 sha, 30 输入在位, 三门源码合同批准 STEP1 `278fdce611e9` / STEP2 `db7ab3561f97` / BUNDLE_export `d63f4ec3f9e6`(`pod2_root/preflight.json`)。
- **gates**: STEP1 跑 37 s → **FAIL rc 3**(与 09-09 归档一致, AMENDMENT 3 的 trend_288 缺陷); STEP2 跑 21 s → **PASS rc 0**; require STEP1 拒(`REQUIRE_FAIL receipt says PASS=False`)⇒ 驱动 **rc 3 `FAIL_gate_require_step1`**(`pod2_root/v4_commands.txt`)。
- **收据对账**(`compare_gate_receipts.py`, 排除 utc/argv/sha 元数据): STEP1 **78 个判决字段全等, 0 差**(PASS=false 两边); STEP2 **31 个全等, 0 差**(PASS=true 两边)(`gate_receipt_parity_STEP{1,2}.json`)。新收据带 `gate`/`self_sha256`/10 与 6 个输入 sha(旧 09-09 收据无这些字段, 研究员 R3′)。
- GPU: `0 %, 2 MiB` 前/后; PID 333197/339489 状态 `Tl` 未动(`nvidia_before.txt` `nvidia_after_controls.txt` `paused_pids_before.txt`)。

### 6.3 负控(空根): 本地 + pod2
- pod2: `DRYRUN_PASS driver_rc=3 stopped_at=FAIL_preflight_rc_3 training_launched=0 gpu=0 %, 2 MiB`; preflight 收据 PASS=false, **33 项点名缺失**(全部在空根下); 驱动 sha `920d18faea7a…`(`pod2_dryrun/dryrun_receipt.json`)。本地同型(测试 [P] 每次运行都复跑一次)。
- 结构负控(测试 [P]): 全输入齐备的假根 ⇒ preflight PASS, `V4_DRYRUN=1` 下下一阶段 `FAIL_dryrun_guard_cache_would_launch` rc 9, `cache_coverage.log` 不存在; 去掉 DRYRUN ⇒ cache 阶段真跑并在假缓存上红(`FAIL_cache_coverage_rc_1`)。

### 6.4 本轮自己被咬的两处(入 ERROR_LEDGER 候选)
- **普通变量名当交接**: 我用 `D` 作装置目录并在驱动 `export D`; 测试环境里一个继承的 `D` 曾让 [r4] 两格链场景失败(实为 bash 3.2 `local -n` 失败 + 我新加的 launcher 空 MONTHS 拒绝的合成; 修法: `eval` 取片 + 交接改名 `CHAIN_DEVICE_DIR`)。
- **「停下了」≠「因为对的理由停下」**: 交接改名后 preflight 的 python 因读不到 `D` 崩溃(rc 1), 负控仍报 PASS(只看 `rc≠0` + `FAIL_preflight` 前缀)。修法: 通过条件加 rc==3 + preflight 收据 PASS=false + 点名缺项非空。这正是 memory「my_own_instruments_fail_at_the_extremes」的一例。

### 6.5 king + legs 阶段 CPU 正控(pod2, 九月数据, 输出全在隔离根 — 已完成, 收据 `pod2_king_legs/`)
`V4_STAGES=king,legs` 在 `v4_month_2026-09.pod2ctrl2.env`(= ctrl 合同再改 `F8/BUNDLE_OUT/BUNDLE_TAR/KING_DIR` 到隔离根; sha `850903461da2…`)上 11:00:08Z → 11:08:49Z(`v4_commands.txt`):
- king: 先 `REQUIRE_OK` STEP2 收据(self `db7ab3561f97` approved, 2 inputs verified); 导出 rc 0, `BUNDLE_DONE files 8 size 103MB`; 驱动校验 `provenance.generation == v3_2026-09`(合同声明值)。
- **与 09-09 归档 `bundle_v4_config.json` 逐字段**: generation / fold_ic_2024 **0.0544** / fold_ic_2025 **0.0609** / pinned_ic2026 **0.0573** / pinned_sharpe_full_b **2.3** / base_ic 全 EQUAL; params / keep_names / symbols_live(450)全等。MANIFEST 8 文件中 **6 个 sha 逐位相同**(`slow_pred_pinned.npy` `leg_returns.npz` `funding_ledger_seed.json` `fund_ema_v1_state.json` `cache_tail_40d.npz` `parity_signals_aug.json`); `config.json` 不同(新增 provenance 字段 + built_utc, 预期); `slow2026.txt` 不同(62 行, `tree_sizes` 若干项 ±1 字节的文本差, 预测 `slow_pred_pinned.npy` 逐位相同 — 不作解释, 记录为事实)。
- **新字段(R4)**: `king_train_end_utc = 2025-12-31T20:00:00Z`, `king_train_last_label_end_utc = 2026-01-01T00:00:00Z`, 训练集 **2,166,009 行 / 8,724 锚**; `data_axis_end_utc = 2026-08-31T20:00:00Z`(10,182 锚); `built_utc = 2026-09-12T11:08:26Z`。三者并列即研究员 R4 的论点: 面板多一个月, booster 的梯度截止不动。
- legs: `LEGS_PRED` = 本次导出的 PRED; rc 0, `LEGS_V4B_DONE`; 旧行逐位 **10206/10212**, 新行 6(2026-08-31 00–20Z); **2023 king 席位 0.5865**(判据 ≥ 0.4; AMENDMENT 5 期望 ≈0.59)。
- 终态 `CHAIN_V4_MONTHLY_STAGES_DONE stages=king,legs`(子集, DONE=false); GPU `0 %, 2 MiB` 前后(`nvidia_before_king.txt` / `nvidia_after_king_legs.txt`); PID 333197/339489 `Tl` 未动。九月运行副本 `/workspace/review_scratch`、`/workspace/shadow_bundle_v4`、`/workspace/f8_v4` 零写入(输出全在 `w3_monthly_chain_2026-09-12/root/`)。

### 6.6 sha256(创建/修改文件; 最终值见 W3 报文的清单, 由 `shasum -a 256` 实测)

### 6.7 ★ 事故(我的, 2026-09-12 11:16Z; W4 14:36Z 只读观察到并通报): 自检的「突变格」在 pod2 上跑了真导出, 改写了 `/workspace/shadow_bundle_v4/slow2026.txt`
- **事实(pod2 14:44Z 读盘)**: `slow2026.txt` mtime 11:16:59Z, sha `0a5adca16edb…` ≠ 归档 MANIFEST `f23657710f3a…`(**改**); `slow_pred_pinned.npy` mtime 11:18:22Z, sha `dde19142d017…` == 归档(**逐位相同地重写**); 其余 7 文件 + `/workspace/shadow_bundle_v4.tar.gz` 保持 09-09 mtime 与归档 sha(config.json provenance 仍 `v3_2026-09` / built 09-09)。
- **机制**: 测试格「MUTATION: with BUNDLE_GENERATION the refusal does NOT fire」只设了 `BUNDLE_GENERATION`, 依赖 `from zload import zload` 在 mac 上失败来终止; pod2 有 `/workspace/zload.py`, 导出器于是以**全部默认路径**真跑: booster 存到默认 `BUNDLE_OUT=/workspace/shadow_bundle_v4`, PRED 存盘, 然后在默认 `EXPORT_PANEL`(v2ext, 非 v3splice)上的守卫带前后停止(未写 leg_returns/config/MANIFEST/tar)。三次 pod2 套件运行中至少一次到达该格(日志 `.final.log` L245 / `_P.log` L245)。
- **后果**: r20 A1 v2 收据对该 bundle 失效(判官: `bundle/slow2026.txt changed since the receipt`), W4 的判官底 28 复核已看到。实盘/mac 零涉及; 我的 king 阶段控制只写隔离根(§6.5)。
- **修复(已落地)**: (a) 导出器 **`BUNDLE_OUT` 必填**(缺 ⇒ `BUNDLE_FAIL bundle_out_env_missing` rc 2), 代码里不再出现 `/workspace/shadow_bundle_v4` 字面, tar 默认跟随 `BUNDLE_OUT`; 生成器同步; (b) 测试: 每个真程序调用都给**不存在的输入路径 + 临时输出目录**, 并断言临时目录为空(测试必须在任何机器上都碰不到真数据); 新增「缺 BUNDLE_OUT 被拒」格。(c) 复原: 未动 09-09 tar 与 r20 `bundle_mut` 副本中的 `slow2026.txt` sha 均 == `f23657710f3a…`(两个独立来源); 复原 = 从 tar 抽出的副本覆盖回去 + sha 复核, 被改文件留作 `slow2026.txt.w3_overwritten_20260912` — **等 team-lead 字后执行**(§6.7 追记)。
- **教训(入 ERROR_LEDGER 候选)**: 「突变格必须红」的另一半是「突变格必须**不能**跑成功」——靠环境缺 import 来终止不是隔离; 隔离 = 不存在的输入 + 临时输出 + 空目录断言。与 §6.4 同族: 我的仪器在另一台机器上变成了写头。
- **复原(team-lead GO, E-0912-B; 收据 `receipts/monthly_chain_2026-09-12/e0912b/restore_run.log` + `restore_verify.json`; pod2 14:58:04–14:58:05Z)**: (a) 研究员 PID 333197/339489 `Tl` 未动; 我的模式匹配到的进程只有本人的 pod2 套件(pid 492897)与复原 shell 自身; 导出器进程 0。(b) 从**未动**的 09-09 tar(mtime 03:29:38Z)抽出 `slow2026.txt`(2,390,238 B, mtime 09-09 03:25:04Z), sha `f23657710f3a6d0068bca8a95082965d694de805195ef143be64951c0f2f203a` == 目录内 MANIFEST.json 值, **写入前核**。(c) 被改文件(2,390,235 B, 11:16:59Z, `0a5adca16edb…`)`mv` 为 `slow2026.txt.w3_overwritten_20260912`(保留); `cp -p` 抽出件; 在位 sha == MANIFEST(`RESTORE_SHA_OK`); stat 前后入日志。(d) 目录 8 文件逐个 vs MANIFEST.json: **8/8 EQUAL**(`slow_pred_pinned.npy` mtime 仍 11:18:22Z 但 sha == MANIFEST); 目录外多余文件仅 `.w3_overwritten_20260912`。GPU `0 %, 2 MiB` 前后。(e) **复原后的 v2 出口门重立资格**(`e0912b/BUNDLE_export_v2_A1_restored2.json` + `REQUIRE_v2_A1_restored2.json`; env = r20 `run_pod2_positive.sh` [1]/[2] 逐字, `V4CHAIN_DIR` = 装置副本(合同 `1188267adf42`, 门源码 `d63f4ec3f9e6`, 盘上 `v4_gate_common` `24e813f145c3`)): 第一次 gate **FAIL E1_manifest**(`unlisted_files: [slow2026.txt.w3_overwritten_20260912]` — 留档件放在 bundle 目录内破坏了闭包), 把留档件移到 `root/e0912b/`(仍保留, sha `0a5adca16edb…`)后重跑: **gate PASS**(15:01:44Z, arm A1, 28 inputs, E1 ok n_files 8, `bundle/slow2026.txt` = `f23657710f3a…`), **REQUIRE_OK identity=True, 28 inputs verified, registered floor 28, content_failed=[]**。GPU `0 %, 2 MiB` 前后。A1 的资格由这份新收据而非「字节已复原」重立。
- **追记 2 教训**: 「保留被改文件」与「bundle 闭包 = MANIFEST 列出的文件恰好是目录内容」冲突 —— 留档件必须放在 bundle 目录**外**。
- **ERROR_LEDGER E-0912-B 草案(供 lead 入账)**: 「2026-09-12 11:16Z, 研究基建(pod2), 无实盘影响。W3 在链自检里加的突变格『设 BUNDLE_GENERATION 则拒绝不触发』只设一个 env 就调用真导出器, 依赖 mac 缺 `zload` 模块中止; pod2 有 zload ⇒ 导出器以全部默认路径真跑, 把 booster `slow2026.txt`(文本不同, 预测逐位同)与 `slow_pred_pinned.npy`(同字节)写回 `/workspace/shadow_bundle_v4`(r20 A1 收据的对象), 在默认 v2ext 面板守卫带前停止, 其余 7 文件与 tar 未动。W4 于判官底 28 复核时观察到收据失效(`bundle/slow2026.txt changed since the receipt`)并通报。复原: 从未动 tar 抽出、sha 先核后写, 8/8 == MANIFEST, 被改件留档; 新 v2 门收据重立资格(追记 2)。修法: 导出器 `BUNDLE_OUT` 必填(与 generation 同律); 自检新增 `run_sandboxed()`(不存在输入 + 临时输出 + 空目录断言)与静态格(任何真写手调用不经沙箱 ⇒ 红)。形态: 『仪器在另一台机器上变成写头』—— 依赖环境缺失来终止 = 没有隔离(与 [[my_own_instruments_fail_at_the_extremes]] / [[shallow_error_masks_deep_error]] 同族)。」

## §7 仍开 / 未验证(诚实清单; 十月前必裁的标 ★)
- ★ (i) **STEP1/STEP2 门源码是九月专用且被合同冻结**: 内部写死 `/workspace/dlw_v4raw` 等路径与九月比对对象(hf3 vs hf2; v4 vs v2ext_clamp/v2ext; `n_first138 == 138`)。十月数据会让它们合法地红(新月尾部处处不同)。需要: 新门源码(env 定位 + 滚动参照的定义 = 预注册)→ 研究员复核 → 合同 `approved_source_sha256` 增补(用户字)。模板 `GATE_STEP1/2=TODO_…` 使 preflight 拒绝, 属有意。**承接方(2026-09-12 晚)**: W7 `docs/PREREG_v4_gates_monthly_2026-09-12.md`(`v4_gate_step1_m.py` / `v4_gate_step2_m.py`, 冻结门不动; 测试节 [R])— 落地后把两个文件名写进月合同 `GATE_STEP1/GATE_STEP2` 即接入本驱动, 驱动不需改动。
- ★ (ii) **全链未在真数据上跑到底**: 九月数据 STEP1 字面 FAIL(AMENDMENT 3; 稳定 trend 候选待用户字)⇒ 正控到 gates 为止; king/legs 阶段 CPU 正控见 §6.5; mwf/refit/arms/judge/export 五阶段的接线只经: 语法、阶段守卫测试、与九月 `v4_commands.txt` 的 CMD 行逐 env 比对, **未经真跑**(GPU 禁用)。这是最大的未验证面; 十月首跑应在 `V4_STAGES` 分段推进并逐阶段读收据。
- (iii) CLIP 目标由 `pod_dlw_targets_raw.py` 无补丁产出; 与九月 `dlw_hf3`(sha `720f03a4…`)是否逐位相同**未验**(STEP1 A 部分会把两者绑住: 差异必须只在补丁窗)。
- (iv) 十月 `SIGNAL_RECEIPT` 须先由 `gate_signal_parity_v2.py` 为本月臂产出; `HC` 隔离副本须含合同钉死的 A0 基线书四件(preflight 查存在, 出口门查 sha); `LEGS_OLD` 指向哪代取决于届时在役代(STATE.md); `REF_META`/`build_dev_v4` 自检是九月专用参照(十月应指九月的 `meta_newprod_v4.npz`, 模板已写, 语义待定)。
- (v) 研究员 R2 的两项**未在本轮处理**(超出派工范围, 明写): 训练器 `_done` 复用已完成折时不核源码/legs 身份(FORCE=0); merge 只断言 F10_GATE 三 sha, 不比对逐折 self_sha/legs_sha 与本次 dispatch。
- (vi) `run_arm.sh`(health_check 内)自身 rc 语义未查; 若它恒 0, 逐 PID rc 只等价于 END 行计数。
- (vii) 崩溃型突变(preflight 自身 rc 1)只被通过条件覆盖, 没有专门测试格(我试过用坏解释器模拟, 但它先破坏 env 派生, 不构成证据)。
- (viii) refit 新字段(`trained_through_label_utc` 等)与导出器 `king_train_end_utc` 只在 §6.5 CPU 控中被真数据触发一次(refit 需 GPU, 未触发); 定义按索引构造, 见 §1 R1′/R4。

## §8 RESULT 追加(2026-09-12, W7; 独立研究员 B-R1 / B-R3 / B-R4 / R5 收口; 全文 `docs/PREREG_v4_gates_monthly_2026-09-12.md` AMENDMENT 1 + §7.9)
- **§7 (i) 关闭到「待用户字」**: 月通用门 `v4_gate_step1_m.py` 79950786… / `v4_gate_step2_m.py` 0fe5ec55…(NONE 绑构建器身份 + 新尾质量 ≥ 0.90), 九月正控 STEP1 78/0(PASS=false 如归档)、STEP2 31 等 + 恰 1 差(`tail_quality`, 预注册); 合同 approved 增补 = 用户字。
- **B-R1 关闭(代码)**: `chain_v4_monthly.sh` 每阶段先 `prereq_*` 再 guard/dispatch(chain_lib 七个前置助手, `FAIL_<stage>_prereq_<name>` rc 3); 空根上 10 个阶段各停于 `_prereq_preflight`、preflight 后各停于下一缺件(自检 [S]); 研究员假解释器形态下 refit 0 次被调。
- **B-R3 关闭(代码)**: `load_month_env` 键须**在文件里**且先 `unset` 再 source(合同 46 键); 数据阶段五子进程 `env -i` + 白名单 + 逐变量显式, CLIP `DLWT_RAW_PATCH=` 空。§3 表「41 键」→ 46 键(+`PREV_DLW_CLIP PREV_F8 PREV_KING_FEA PREV_KING_FEA_UNCLAMPED PREV_CLAMP_BUILDER_SHA256`); §2 原则 1 的「41」同。
- **R5 关闭(物理)**: 五个旧链脚本首行 `V4_LEGACY_OK=1` 守卫, 否则 rc 64 `LEGACY_REFUSED` 什么也不做([S] 逐个验证 cwd 零写入); [J]/[K] 自检传 `V4_LEGACY_OK=1`。
- 自检 328 ALL PASS(`receipts/monthly_chain_2026-09-12/tests_pipeline_gates_w7.log` + `.SHA256SUMS`); `make_sha_manifest.py` rc 0; 研究员 13+8 探针复跑翻转 5 格(W7)+1 格(W4 并行), 见 `w7_gates/researcher_probes_live/README.md`。
- §7 (ii) 仍开: 真数据全链(mwf/refit/arms/judge/export)未跑; 前置只在合成根上验证。

## §9 ROUND 3(2026-09-13, W7b; 受据 = 独立研究员 `docs/REVIEW_code_and_research_2026-09-13.md` §3.D + `multi_asset/exports/research/codex_followup_code_review_2026-09-13/retrain/`)

研究员四项里三项改码、一项**只写字不动行为**。装置目录内每个改动都有一个**跑归档旧源就会红**的自检格(新节 [T]): 旧源以 `.r1_<sha8>` 存在装置目录里, [T] 每格**同时**跑旧的与新的 —— 红与绿在同一次运行里出现, 不靠文字声明。

### 9.1 D1 `prereq_refit_sidecar`: 证明了「有一份 JSON」, 没证明「这份 JSON 说的是谁」
- **旧行为(三个被接受的坏状态, 研究员夹具 rc 0)**: (a) 权重字节已改 + **删掉** `pt_sha256` 键 ⇒ 过(`elif m.get("pt_sha256") and …` 把缺键当成「没什么要查的」); (b) 四个声明输入缩成一个 ⇒ 过(循环只走侧车恰好列出的那些); (c) 完整的 **seed-42** 侧车放进 **seed-2027** 槽位 ⇒ 过(函数没有期望种子, 也不读 `m.seed` / `env_given.SEED` / `.pt` 路径; `name=refit_s2027` 只进日志)。此门在 **arms dispatch 之前**跑。
- **★ 影响边界(必须与结论同寿命地引用)**: **没有任何证据表明错误的 `.pt` 被用于真实预测。** arms 消费的是月度预测 `.npy`(`run_v4_arms.sh` L11–15), `build_dev_v4.py` 也不加载这个 `.pt`。所以这是一条**没兑现的 resume-gate 承诺**(报文里「refit 侧车/输入/weights 身份已验证」的保证过强), **不是**一次被证明的坏训练, 也不是「跳过了 refit 训练」。
- **新行为**(`chain_lib.sh` `prereq_refit_sidecar`, 7 个参数全必填): ① **期望种子**——`seed`、`env_given.SEED`、`.pt` 路径里的 `s<seed>`、侧车文件名 `f10_live_s<seed>.json` 四者都要等于驱动正在核的那个种子; ② **完整键集**——`seed/best_ep_rule/best_ep_kept/env_given/inputs/inputs_sha256/pt/pt_sha256/self_sha256` 与 `env_given` 的四键, **缺一即拒**, 永不「缺了就跳过」; ③ **期望路径**——四个输入必须是本月合同的 `$DLW_RAW/data/{dlw_targets,dlw_fea82}.npz`、`$F8/data/{f8_fea89,f10v2_legs}.npz`, `.pt` 必须是 `$F8/models/f10_live_s<seed>.pt`(逐字节相同但放在别的树下的副本 ⇒ 拒); ④ **实际工件 sha**——`.pt` 与每个声明输入都**当场重算**并比对, 记录值为空本身就是拒绝理由; ⑤ (超出 lead 点名的四项, 研究员建议)**哪个程序写的**——侧车 `self_sha256` 必须等于驱动这次调度的 `pod_f10_refit_v4.py` 现值, 与 `require_gate` 对门收据的 `self_sha=` 同律。参数本身也 fail-closed: 用旧的五参数形式调用 ⇒ rc 3 点名。
- **不漂移**: [T] 有一格静态断言「门现在要求的每个键与每条路径, 都是 `pod_f10_refit_v4.py` 真的会写的」——门不许要求写手从不产出的字段。另一格是**干预式**的: 把「refit 源」参数指向一个唯一语句是写标记文件的脚本, 门拒绝且标记文件**不存在** ⇒ 该参数只被 hash, 从不被执行。

### 9.2 D2 新尾成员索引 / 9.3 D3 合同值绑定
- D2 见 `docs/PREREG_v4_gates_monthly_2026-09-12.md` **AMENDMENT 2 + §3.7**(先结构后比例; 0.90 的射程 = 有限格门, 不是因果/预测有效性门)。
- D3 `load_month_env`: 46 键「在文件里」不等于「值来自文件」——`SEEDS=$UNLISTED_SEEDS` 是文件的一行, 但 `unset` 只清合同键, 于是 source 时由父环境填入(研究员实测 rc 0、SEEDS=2027)。新规则: **值里的变量引用只许指向本文件更早定义过的合同键**; 其余(非合同名、前向引用、`${...}` 指向外部名、裸 `$`)一律 rc 4 点名。**与 lead 字面指示的偏差(明写)**: lead 说「值里含 `$`/反引号/命令替换一律拒」; 直接照做会拒掉**两份已交付的合同**(九月 5 个 `$R/...`、十月模板 12 个), 所以取研究员给的窄规则。反引号与 `$(` 仍由 round-2 的行文法拒(rc 4 `month_env_malformed`), 两层互不依赖, [T] 各有一格。

### 9.4 D4 判官定位器: **本轮不动行为**, 只把闭合条件写死(待 lead 裁定)
- **机制(已复现)**: `v4_gate_common.py` L222–224 —— `for k in rec: if k in inputs: continue`。caller 已声明的名字**直接跳过**「从收据 `inputs_path` 定位」这一步, 之后只核 caller 给的路径。于是: 收据记 `femat=/fixture/femat.npy` 的旧 sha → 存一份同字节 backup → 改原 femat → caller 显式传 `femat=<backup>` ⇒ `eligibility.ok=true`, 而**实际会被读的那个文件已经变了**。省略 locator 或传原路径都已正确拒绝(round 8 已修)。
- **当前的真实射程**: 月度 export 路线**不受影响** —— 驱动 `chain_v4_monthly.sh` L299 把收据自己的**全量** `inputs_path` 原样写进 `JUDGE_ELIGIBILITY.json`, 所以 caller 路径 ≡ 收据路径。反例只在**手写 caller** 时成立, 而 `JUDGE_ELIGIBILITY` 本来就是受支持的研究入口, caller 本来就有定位文件的权限。**合法地把同字节工件整体迁到新路径不能一概算错。**
- **因此闭包的条件, 一句话**: 只有当**资格被绑到实际消费者读的那条路径**之后, 才能说「判官 ≡ standalone gate 的全闭包」; 在那之前, 正确的说法是「月度路线受保护, 手写 caller 的重定位未被约束」。
- **最小绑定提案(给 lead 裁定, 本轮不实施)**: 在 `require(recorded_extras=True)` 里, 对**每一个**收据记了 `inputs_path` 的名字, **无条件**核「收据路径的当前 sha == 收据记录的 sha」; caller 另给的路径**追加**核, 不是**替代**核。代价说清楚: 一次「搬走并删掉原件」的合法迁移会被拒(必须重开门写新收据)。之所以不选「原件还在就核、不在就放过」, 是因为那正是本轮在 D1 里刚拔掉的「absent ⇒ skip」——删掉原件就能过, 洞会原样长回来。**影响面**: 该行在 `v4_gate_common.py`(合同冻结族, 我不动); 改它要重新走批准。

### 9.5 本轮的 sha 与收据
| 文件 | 修前 sha256 | 修后 sha256 |
|---|---|---|
| `chain_lib.sh` | `3cd82956833e9c06…` | `a331f0351b3eca9ac2e64636e94a906045deb209f25888f38a8ab07e4d715a40` |
| `chain_v4_monthly.sh` | `c6ea34fa0131d3a0…` | `e8e688d58512a9395ac0b3d59b603be4b09c63ff08bc5d5d7b4726b8ab188d3b` |
| `v4_gate_step2_m.py` | `0fe5ec5573f34696…` | `b2f9cfd40b9e356536184a63e202aa9d2a48228be5145bcd81665fb5f7df24e9` |
| `tests_pipeline_gates.py` | `7181045d157758ae…` | `b56bdc60a86c5f0fde97efc83432a0e34c4b6cef07f2fe32ad902fbd85a79abb` |
| `w7_gates/v4_gate_step2_m.diff` | 88 行 | `833c9a420d0e5ed977aaa86a95d656d7a2493c69e70f82dcda0d29feb0e9c034`(105 行) |
| `chain_lib.r1_3cd82956.sh` **新** | — | `3cd82956833e9c06f0f241316e6fa210d3895df05aaf952fd41e6a4345805464`(红控) |
| `v4_gate_step2_m.r1_0fe5ec55.py` **新** | — | `0fe5ec5573f346969d9d3448c3e424f2ebc8b7c192cefe4313a05cdf84c09007`(红控) |

两个 `.r1_` 快照 = 研究员 `RESULT.md` 关键源表里的那两个 sha, 逐位; `v4_gate_step1_m.py` 不变(`79950786…`)。
- **冻结零改动(事前事后各实测一次)**: `v4_gate_step1.py` `278fdce6…`、`v4_gate_step2.py` `db7ab356…`、`ELIGIBILITY_CONTRACT.json` `1188267a…`、`v4e_gate_export_v2.py` `d63f4ec3…`、`v4_gate_common.py` `24e813f1…`、`judge_v4.py` `c2a81c48…`、`make_sha_manifest.py`、`tests_judge_dynamic_deps.py`。
- 收据: `receipts/round3_2026-09-13/`(自检修前/修后全跑日志、研究员 23+16 探针修前/修后结果与翻转表、被修正的正控、`SHA256SUMS`)。
- **未验(诚实)**: 本轮全部在 mac 本地合成夹具上; **pod2 未跑**, 真数据未跑; §7 (ii) 原样仍开。

> **勘误(2026-09-12 15:1xZ, lead)**: 本文 §3/§5 写的「41 键」是 W3 交付时的数; W7 随后加入 `PREV_DLW_CLIP / PREV_F8 / PREV_KING_FEA / PREV_KING_FEA_UNCLAMPED / PREV_CLAMP_BUILDER_SHA256` ⇒ 现为 **46 键**(`chain_lib.sh` V4_MONTH_KEYS; 自检 [P] 键数格已同步)。键的语义见 `docs/PREREG_v4_gates_monthly_2026-09-12.md` §2。
