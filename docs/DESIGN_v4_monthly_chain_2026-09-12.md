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
| `tests_pipeline_gates.py` | 新节 [P] 41 格(含 8 格突变红) | 151 旧格全绿 |
| `compare_gate_receipts.py` **新** | 门收据判决字段逐位对账(排除 utc/argv/sha 元数据) | — |
| `docs/RUNBOOK_monthly_retrain_2026-10.md` | §0★ 横幅 + 修订 3 | 历史不删 |

## §6 RESULT: 控制与收据(全部数字抄自收据; 收据目录 `v4_chain_2026-09-09/receipts/monthly_chain_2026-09-12/`)

### 6.1 本地自检(mac, `/usr/bin/python3 tests_pipeline_gates.py`)
- 修前基线: **ALL PASS (151 checks)**, exit 0(本会话开工时实测)。
- 修后: **ALL PASS (222 checks)**(= 151 旧格全绿 + 71 新格; 其中 [P] 节 41 格含 8 格突变红: MONTHS_ALL 越界、MONTHS ⊄、四键齐备时拒绝不触发、generation 齐备时拒绝不触发、malformed MONTHS_ALL、未批准门源码、无 DRYRUN 时 cache 阶段真跑、缺键合同)。中途两次红并修复: (a) 三脚本再生逐位([H]) — 生成器补齐, (b) [r4] 两格链场景 — 见 6.4。

### 6.2 pod2 正控: 九月路径 + 隔离根(`/workspace/w3_monthly_chain_2026-09-12/`, 运行副本 `/workspace/review_scratch` 零写入)
- 装置副本 = git 单源: **100 文件 sha 相等**(`pod2_root/device_sha256_pod2.txt` vs 本地; 唯一差异为期间本地再改的 `tests_pipeline_gates.py`, 已重传)。
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

## §7 仍开 / 未验证(诚实清单; 十月前必裁的标 ★)
- ★ (i) **STEP1/STEP2 门源码是九月专用且被合同冻结**: 内部写死 `/workspace/dlw_v4raw` 等路径与九月比对对象(hf3 vs hf2; v4 vs v2ext_clamp/v2ext; `n_first138 == 138`)。十月数据会让它们合法地红(新月尾部处处不同)。需要: 新门源码(env 定位 + 滚动参照的定义 = 预注册)→ 研究员复核 → 合同 `approved_source_sha256` 增补(用户字)。模板 `GATE_STEP1/2=TODO_…` 使 preflight 拒绝, 属有意。
- ★ (ii) **全链未在真数据上跑到底**: 九月数据 STEP1 字面 FAIL(AMENDMENT 3; 稳定 trend 候选待用户字)⇒ 正控到 gates 为止; king/legs 阶段 CPU 正控见 §6.5; mwf/refit/arms/judge/export 五阶段的接线只经: 语法、阶段守卫测试、与九月 `v4_commands.txt` 的 CMD 行逐 env 比对, **未经真跑**(GPU 禁用)。这是最大的未验证面; 十月首跑应在 `V4_STAGES` 分段推进并逐阶段读收据。
- (iii) CLIP 目标由 `pod_dlw_targets_raw.py` 无补丁产出; 与九月 `dlw_hf3`(sha `720f03a4…`)是否逐位相同**未验**(STEP1 A 部分会把两者绑住: 差异必须只在补丁窗)。
- (iv) 十月 `SIGNAL_RECEIPT` 须先由 `gate_signal_parity_v2.py` 为本月臂产出; `HC` 隔离副本须含合同钉死的 A0 基线书四件(preflight 查存在, 出口门查 sha); `LEGS_OLD` 指向哪代取决于届时在役代(STATE.md); `REF_META`/`build_dev_v4` 自检是九月专用参照(十月应指九月的 `meta_newprod_v4.npz`, 模板已写, 语义待定)。
- (v) 研究员 R2 的两项**未在本轮处理**(超出派工范围, 明写): 训练器 `_done` 复用已完成折时不核源码/legs 身份(FORCE=0); merge 只断言 F10_GATE 三 sha, 不比对逐折 self_sha/legs_sha 与本次 dispatch。
- (vi) `run_arm.sh`(health_check 内)自身 rc 语义未查; 若它恒 0, 逐 PID rc 只等价于 END 行计数。
- (vii) 崩溃型突变(preflight 自身 rc 1)只被通过条件覆盖, 没有专门测试格(我试过用坏解释器模拟, 但它先破坏 env 派生, 不构成证据)。
- (viii) refit 新字段(`trained_through_label_utc` 等)与导出器 `king_train_end_utc` 只在 §6.5 CPU 控中被真数据触发一次(refit 需 GPU, 未触发); 定义按索引构造, 见 §1 R1′/R4。
