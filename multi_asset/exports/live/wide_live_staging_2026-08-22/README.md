> **创建:** 2026-08-22 04:2xZ | **Session:** 6737834a (live-sys-eng 子会话, team-lead 派工 "External-book adapter patch") | **状态:** STAGING — 可审阅补丁包, **未应用到 ~/dl_quant_live, 未改运行中的 ~/wide_shadow/shadow_loop.py, 未调交易 API** | **作废条件:** 主线应用后以实盘仓 commit 为准; 或 DESIGN_wide_live_deployment_2026-08-22 作废

# 宽书实盘化(external book)适配器 — staging 包

基于: `docs/DESIGN_wide_live_deployment_2026-08-22.md` §1–§3-bis。实盘仓基线 commit **`ab569b8`**(`verify/PATCH_RECEIPT.json` 记录每个被改文件的原始 SHA-256 与补丁后 SHA-256); 影子基线 `~/wide_shadow/shadow_loop.py` SHA `445a9870…`。

## 0. 白话三句
1. **做了什么**: 实盘仓加一个 `book_source` 开关(默认 `internal` = 今天, 逐位不变); 设为 `external` 时, 锚的目标向量不再在进程内合成, 而是读影子 v2 每锚写的签名文件(`~/wide_shadow/state/target_live/<anchor_ts>.json` + `.sha256`), 校验(旁证 sha / schema / anchor_ts 等于本锚 / 新鲜度 / 宇宙与模型 sha 钉 / 权重合法)后按 `w/gross_norm × NAV × gross_mult` 换算名义, **跳过** compose_book/风险预算/EMA/中性带, **保留** 交易所门/非 COIN·非 ASCII 排除/2×minNotional 资格/撤名重整/clamp-flatten_only/逐名止损/执行层/看门狗。
2. **失败方向**: 任何校验不过 ⇒ 本锚保持现仓不下单 + HIGH `external_book_unavailable`(带原因), **绝不回退在役引擎**; 连续读不到按既有预注册阶梯(≥24h 减半 reduce-only, ≥48h 平仓; 可配 `hold` 永不升级); 配置写错 ⇒ `BLOCKED_CONFIG` + CRITICAL 零下单。
3. **验证了什么**: 新套件 `tests_external_book` 101 项(含 3 个会红变异体)全绿; 影子侧 `tests_target_live_output` 29 项在 py3.14(影子 venv)与 py3.9(实盘解释器)双绿, 且断言"生产方写出的文件被消费方接受"(配对检验); 在实盘仓**全量副本树**跑完整电池 → 见 §5。

## 1. 交付物(全部在本目录; 实盘仓文件按仓内相对路径放在 `live_repo/`)
| 路径 | 性质 | 说明 |
|---|---|---|
| `shadow/shadow_loop_v2.py` | 新文件(= 原 + 两段新增) | 每锚 npz 落盘后原子写签名目标 json + 旁证; try/except 包裹, 失败只记 `target_live_error` 行; 其余逐行不变(`shadow/shadow_loop_v2.diff`, 50 行新增 0 行删除; `tests_target_live_output [1]` 机器断言) |
| `shadow/tests_target_live_output.py` | 新测试 | 字段/原子性/sha/`shasum -c`/配对检验/变异体; 需 `DL_QUANT_LIVE_LIVE` 指向(补丁后的)实盘 `live/` |
| `live_repo/live/external_book.py` | **新模块** | 配置解析与校验 / 等槽 / 读取+校验 / 阶梯年龄 / 目标向量 / 两条保留过滤(纯函数) / 记录与告警文案 |
| `live_repo/scheduler/anchor_loop.py` + `anchor_loop.external.diff` | 补丁(全文副本 + unified diff) | 14 个 hunk, 见 §2; `diff -w` 后仅 173 行变动(613 原始行数中 ~440 行是把两段现有代码缩进进 `else:`) |
| `live_repo/live/per_name_stop.py` + `.diff` | 补丁 | `resolve_profile`(`active_profile`/`profiles` 覆盖; 未知名=基础值+告警, 条款不失明) |
| `live_repo/config/book.json` + `.diff` | 补丁 | 新键 `book_source`(internal) / `external_book` 块 / `per_name_stop.active_profile`+`profiles.wide` / `anchor_max_seconds` 1500→3000(带理由) |
| `live_repo/live/tests_external_book.py` | **新套件** | 101 检查, 见 §3 |
| `live_repo/ops/gate_coverage.py` + `.diff` | 补丁 | `tests_external_book` 边界自述(六个盲点) |
| `live_repo/run_acceptance.sh` + `.diff` | 补丁 | 显式注册(runner 对未注册 tests_*.py 会 REFUSE) |
| `live_repo/live/tests_imports.py` + `.diff` | 补丁 | PRODUCTION_MODULES += external_book(派生集合断言会红) |
| `live_repo/live/tests_entrypoint_wiring.py` + `.diff` | 补丁 | [D] 学会 external-HOLD 状态(真树 DRY 电池锚在 N+22 前读不到文件 ⇒ HOLD 无 plan, 旧断言 `n_planned>0` 会假红) |
| `live_repo/live/tests_anchor_skip_visible.py` + `.diff` | 补丁 | [E2] 碰撞窗半宽从 config `anchor_max_seconds` **推导**(原钉死 25 min = 1500/60; 套件自己的原则就是"derived, not a second number"); 首轮副本树电池唯一红 → 修后 28/28 |
| `docs/RUNBOOK_wide_live_2026-08-22.md`(研究仓 docs/) | 新文档 | 启动 L0/L1 / 升降级 / 停止 / 回滚 / 每锚核查 / 探针与影子交互 / 时序 |
| `verify/make_patches.py` | 生成器 | 从实盘仓**原件**按精确匹配重放所有 hunk(基线漂移 ⇒ 拒绝); 产出全文副本 + diff + `PATCH_RECEIPT.json` |
| `verify/build_scratch.sh` | 验证用 | rsync 实盘仓(去 .git)到 scratchpad 全量副本 + 覆盖 staged 文件 |
| `verify/l0_mirror_check.py` | 运维工具 | L0 镜像比对: 目标文件 vs orders.jsonl plan 行 target_w ⇒ max\|Δw\|、撤名单、重整位移 |
| `verify/RUN_*.txt` | 收据 | 见 §5 |

## 2. anchor_loop.py 逐 hunk(为什么)
| # | 位置 | 改动 | 为什么 |
|---|---|---|---|
| H1 | import | `import external_book as EXT` | 适配器单独成模块(纯函数可测), 与 `per_name_stop` 并列 |
| H1b | 模块常量 | `EXT_DUST_ALARM_FRAC = 0.10` | 2×minNotional 撤名质量超 10% gross 才告警(实测 L1 1× 撤 6.2%, L2 1.7%; 逐锚必记, 不逐锚刷屏); 政策数, 写明出处 |
| H2 | `run_anchor` 顶部 | `BC.load()`→`EXT.config`; INVALID ⇒ `BLOCKED_CONFIG` 返回; external ⇒ profile 一致性告警 + 非 DRY 等槽 `EXT.wait_for_slot`; `now_sched = now` | 书源一次解析, 早于一切读态; 配置打错不得选书; 等到生产方槽位(N+offset)再读态/下单; 调度判定用**入口时刻**(它就是计划内那次运行, 台账按进程起点计) |
| H3 | off-schedule 门 | `schedule_check(now_sched)` | 同上; internal 下 now_sched==now 逐位不变 |
| H4 | preds 新鲜度块 | external ⇒ `EXT.read_target`(非 DRY 轮询到 grace)→ 年龄 `EXT.age_anchors`(本文件/上次良好/目录最新已验) → `staleness_action`; 读失败 ⇒ 永不 TRADE, `hold`/年龄未知 ⇒ 钉 HOLD; HIGH 告警; 成功写 `state.external_last_good_anchor_ts` | 外部文件就是信号; 复用预注册阶梯而非新造一套; 年龄未知(冷启/状态重置)不许不可逆减仓 |
| H5 | `_trade(...)` 调用 | `external=ext` | 把已校验的书交给 `_trade`; internal 传 None |
| H6 | `_size_book` | 可选 `target_leverage`/`leverage_source`, 返回 `leverage_source` | external 的杠杆 = `gross_mult`(设计 target_gross=NAV×gross_mult), 死区/地板算术不变; 行里写明来源 |
| H7 | `_trade` 开头 | `_is_ext`; external ⇒ symbols 来自文件, 四道 DL preds 门(口径戳/冻结输入/列集/OOD)跳过并**写明跳过**; 原块整体进 `else:`(仅缩进, `diff -w` 可验) | 这四道门判的是 preds 文件, 不决定外部书; 跳过不伪装成通过 |
| H8 | universe 门之后 | external 非 DRY ⇒ `self.src._get(exchangeInfo)` → `EXT.venue_meta_exclusions` 并入 `_untradable`; 目标向量 `book={"target_w": EXT.target_vector}`; `_bw`/`_last_harvest_ema` 占位; 原 compose/EMA 块进 `else:`(缩进) | 设计保留"交易所过滤(COIN perp/非 ASCII/股票类)" = 探针 v2 规则; 生产方权重即目标, 不经 compose/风险预算/EMA |
| H9 | sizing | `_size_book(target_leverage=gross_mult, …)` | 同 H6 |
| H10 | floors 之后、止损置零之前 | `EXT.below_min_notional` ⇒ 并入 `_untradable`(未持有⇒pop 后重整; 持有⇒clamp reduce-only); 记录; >10% 告警 | 设计"最小名义额可达 ≥2×minNotional"; 走既有 withhold 通道, 零新执行形态 |
| H11 | 中性带 | external ⇒ 跳过(记录 skipped); 原带块进 `else:`(缩进) | 设计明令不经带(W2b) |
| H12 | `_anchor_ctx` | `factor_version`=external 戳(json: book_source/schema/booster/weights/universe sha/gross_mult); `panel_hash`=universe_sha; 新键 `book_source`/`external_book`(含两条过滤判决) | 账本必须说清这锚交易的是**哪本书**及每个被撤名的原因 |
| H13 | `finalize_anchor` anchors 行 | `row["book_source"]`, `row["external_book"]` | 下游(看门狗/IC 监视/guard_twin)读列, 不解析 factor_version; schema 允许额外键 |
| H14 | `_trade` 返回 | `book_source`, `external_filters` | phase_A 日志行可见 |

`per_name_stop.py`: `cfg()` 经 `resolve_profile`; `update_from_snapshot` 对 `_profile_error` 追加告警行。基础参数键**一字未改**(`tests_per_name_stop` W5 仍对原始 JSON 断言 −0.25/2/7)。

`config/book.json` 新值: `external_book.path=/Users/haosiyu/wide_shadow/state/target_live, max_age_min 10, anchor_offset_min 23, poll_grace_min 5, gross_mult 1.0, require_anchor_match true, universe_sha_pin null, booster_sha_pin null, min_notional_mult 2.0, on_unavailable ladder, schema wide_target_v1`; `anchor_max_seconds 3000`; `per_name_stop.active_profile null` + `profiles.wide {depth −0.30, 2, 7d, min_notional 20}`。

## 3. 测试(每条都有会红的对侧)
`live_repo/live/tests_external_book.py` — 101 检查: [C] 配置 (typo/缺块/gross 超杠杆政策/坏字段 ⇒ INVALID; 耦合谓词) · [W] 等槽纯计划(槽内等/槽外不等/env 关) · [R] 读取: 同生产方格式的 fixture **被接受**; 缺失/缺旁证/翻一字节/旁证错哈希/非 JSON/schema/anchor 不符/陈旧/未来/宇宙钉/模型钉/NaN/gross_norm 不符/全零/n_names 撒谎 各自被拒且原因准确; 轮询只重试可重试集 · [L] 环路 external DRY: **目标逐位 == w/gross_norm×NAV×gross_mult**(中性单位毛额二进制精确 fixture, 重整恒等); 带内持仓名**不被带住**; EMA 状态不落盘; 四道 DL 门写"跳过"; ctx/状态戳; gross_mult 2.0 算术 · [F] 2×minNotional 撤名+记录(+控制: mult 0 不撤); 场所 meta 纯函数六类 + **接线**(注入 src 的非 DRY 环路实际撤掉 EQUITY 名) · [H] 缺失 ⇒ HOLD 无 plan 零单 仓位不动 + HIGH 文案; 上次良好 7 锚 ⇒ DERISK(DRY 记账减半); `hold` 钉住; 陈旧 ⇒ HOLD; INVALID ⇒ BLOCKED_CONFIG; profile 不一致 ⇒ 交易但 HIGH · [I] internal 逐位: 读取器**零调用**、合成路径跑通(EMA 状态落盘)、ctx 戳 internal · [P] profile 解析/未知名告警/宽参数触发算术(−28%×2 不触, −31%×2 触) · [S] 静态接线次序/注册/自述/真配置自洽/`anchor_max_seconds` 覆盖等待+k · [M] 三变异体(副本上): 带重新施加 ⇒ L5 红; internal 下强制 external 分支 ⇒ I1 红; 缺文件回退 internal ⇒ H1 红。

`shadow/tests_target_live_output.py` — 29 检查: v2=原+新增(无删改行)/字段/npz sha/宇宙 sha 同配方/`shasum -c`/**配对: 实盘 `external_book.read_target` 接受生产方文件**/钉匹配/原子性(rename 失败零残留)/覆盖写/确定性/调用点 try-except/无钥匙仍拒/翻字节与缺旁证被拒。★ py3.14 `sum()` 是补偿求和, py3.9 不是 ⇒ gross_norm 末位可差 1 ulp; 读取器的 gross_norm 校验是相对 1e-6, 测试用容差。

## 4. 如何应用(主线; 全部在锚间静默窗; 落盘即上线)
```
LIVE=~/dl_quant_live; STG=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/wide_live_staging_2026-08-22
cd $LIVE && git status --short scheduler live config ops run_acceptance.sh     # 基线应干净; HEAD 应为 ab569b8(否则先 `python3 $STG/verify/make_patches.py` 重放 hunk 并重审 diff)
# 方式 A(推荐, 可审): git apply 八个 diff; 方式 B: cp 全文副本(基线已漂移时不要用 B)
for d in scheduler/anchor_loop.external.diff live/per_name_stop.py.diff config/book.json.diff ops/gate_coverage.py.diff run_acceptance.sh.diff live/tests_imports.py.diff live/tests_entrypoint_wiring.py.diff live/tests_anchor_skip_visible.py.diff; do git apply --check "$STG/live_repo/$d" || exit 1; done
for d in ...同上...; do git apply "$STG/live_repo/$d"; done
cp $STG/live_repo/live/external_book.py live/ ; cp $STG/live_repo/live/tests_external_book.py live/
shasum -a 256 scheduler/anchor_loop.py live/external_book.py config/book.json live/per_name_stop.py   # 对照 verify/PATCH_RECEIPT.json staged_sha256(external_book.py: cbbb4741…)
bash ops/safe_commit.sh "#wide-live external-book adapter (staging 2026-08-22): book_source switch (default internal, byte-identical) + external_book.py + tests_external_book (101) + per_name_stop profiles + gate_coverage/run_acceptance/tests_imports/tests_entrypoint_wiring" \
   scheduler/anchor_loop.py live/external_book.py live/per_name_stop.py live/tests_external_book.py live/tests_imports.py live/tests_entrypoint_wiring.py live/tests_anchor_skip_visible.py config/book.json ops/gate_coverage.py run_acceptance.sh
```
切换 external(另一次 safe_commit, 见 RUNBOOK §2.2): 同一编辑改 `book_source: "external"` + `per_name_stop.active_profile: "wide"`; `anchor_offset_min/poll_grace_min` 按 RUNBOOK §2.3 实测时序(现 23/5); 影子 v2 先于实盘切换起跑(RUNBOOK §2.1)。

## 5. 自检收据(`verify/`)
- `RUN_tests_external_book.txt` — **ALL PASS (101 checks)**, 在实盘仓全量副本树(scratchpad/live_scratch = rsync 去 .git + staged 9 文件)以 `/usr/bin/python3`(电池钉住的 3.9.6)运行。
- `RUN_tests_target_live_output_py314.txt` / `_py39.txt` — **ALL PASS (29)** ×2(影子 venv 3.14 / 实盘 3.9), `DL_QUANT_LIVE_LIVE` 指向副本树 `live/`。
- `RUN_full_battery_scratch.txt` — **首轮全量电池(122 套件, 副本树): 121 绿 / 1 红 = `tests_anchor_skip_visible`**, 红因 = 它把碰撞窗半宽钉成数字 25 min(=旧 cap 1500/60), 与本包 `anchor_max_seconds 3000` 冲突 → 补丁让它从 config 推导(见 §1 表)→ 单跑 `RUN_tests_anchor_skip_visible.txt` 28/28。**复跑全量电池** `RUN_full_battery_scratch_rerun.txt`: 见文件末 ACCEPTANCE 行(写 README 时在跑; 完成后本行追加读数)。受影响既有套件的逐份日志: `RUN_tests_neutral_band/per_name_stop/entrypoint_wiring/imports/static_names/gate_coverage/sizing_policy/signal_and_loop/k_window/harvest_ema/book_reshape/guard_reach/deadman_ping/guard_calibers/live_state_root/scoped_writes/guard_reach/acceptance_entrypoints.txt` — 全部 ALL PASS。
- `PATCH_RECEIPT.json` — 原件/补丁后 SHA-256, 基线 commit 匹配 `true`。
- 静态: 三份 Python 文件 `py_compile` 通过; pyflakes 对补丁后 anchor_loop 的两条发现(`target` unused @complete_anchor, `List` undefined)**与原件相同**(tests_static_names 已豁免的那两条), 无新增。

### 未能在 staging 验证(如实列)
1. **真树 safe_commit 电池**(只能在 ~/dl_quant_live 跑 — 我不写实盘仓); 副本树电池是最接近的替身, 差别: `.git` 缺席、launchd/plist 不在副本、`tests_entrypoint_wiring` 的真跑锚写的是副本 state。
2. **LIVE/TESTNET 真锚**: 等槽(N+offset 真空等)、`anchor_max_seconds 3000` 是否足够、真 NAV 下 2×minNotional 撤名比例(估 6.2%@1×)、真 exchangeInfo 的 underlyingType 字段形态 — 这些只有 L0-b(停开仓下的计划内锚)能给读数(RUNBOOK §2.4)。
3. 影子 v2 **未启动**(只读 v1; v2 是副本): 首个真 `target_live` 文件要等主线按 RUNBOOK §2.1 起 v2。
4. 设计 §3.3 guard_twin 目标一致性孪生、§1 IC 监视改读宽书分数、§3.4 MANIFEST 记 book_source — **不在本包**(见 RUNBOOK §6)。

## 6. 决策点(我做了选择, 主线可一行改回)
- **D1 时序**: 设计写影子 N+6 产出/N+8 读; **实测影子 SHADOW_OFFSET_MIN=16(进程 85661 env)+ 运行 5.5 min ⇒ 落盘 N+21.5**; 我把 staged 配置设为 `anchor_offset_min 23 / poll_grace_min 5`(且 `anchor_max_seconds` 3000)并写入 `_timing` 注释。若主线起 v2 时改回 offset 6(落盘 ≈N+12) ⇒ 实盘改 13/5 即可。**N+8 在任一影子 offset 下都不可行**(运行时间 5.5 min 大于 N+6→N+8 的 2 min)。
- **D2 读失败后的阶梯**: 设计只写"保持现仓不交易 + HIGH"; 我默认复用既有预注册阶梯(`on_unavailable: ladder`: 1–5 锚 HOLD, ≥6 DERISK 50/25% reduce-only, ≥12 FLATTEN, 年龄按最近一个校验通过的目标; 年龄未知 ⇒ 只 HOLD), 一键 `"hold"` 改为永远只 HOLD+告警。理由: 影子是 nohup 进程(非 launchd), 机器重启它不会自己回来; 阶梯是"没信号"的既有机制与文档。
- **D3 gross_mult 上限**: 配置层拒绝 `gross_mult > target_leverage`(§4-4b 以 target_leverage 为杠杆政策, 2.5× halt 线是它的倍数); L3 2.5 需同时把 target_leverage 提到 2.5 —— 让"杠杆上限沿用"成为一次显式编辑而不是一次触发。
- **D4 2×minNotional 的实现**: 作为"不可开"名并入既有 `_untradable`(未持有 pop+重整, 持有 clamp reduce-only), 而不是整锚拒绝或静默跳过; 撤名质量逐锚入记录, >10% gross 才告警。
- **D5 profile 耦合**: `book_source` 与 `per_name_stop.active_profile` 是两个键(各自可回滚、可见), 由谓词 `pns_profile_consistent` 守卫(不一致 ⇒ HIGH, 不阻断 — 阻断方向是止损失明)。
- **D6 等槽在环路内**: launchd 仍 N+0 起跑, 进程持锁空等到 N+offset(`external_wait` 记录), 调度门用入口时刻; 替代方案(改 plist 到 N+23 并放宽 `anchor_late_tolerance_min`)更干净但动安装仪式, 留给主线。

## 7. 顺手发现(非本包改动, 建议单独处理)
- ★ `anchors.jsonl.weights` 自 2026-08-10 中性带部署起记的是 **0.002(带宽)** 而不是混合权重 dict: `anchor_loop._trade` 里 `_bw = BC.weights()` 在中性带块被 `_bw = float(... no_trade_band_w ...)` 重绑, 而 `_anchor_ctx["weights"] = _bw` 在其后。实测 08-05 行 `weights={'king':0.595…}`, 08-22 行 `weights=0.002`。本包 external 分支不受影响(自设 `_bw` dict), internal 行为保持(不在本包修); 修法一行(带宽换名)。
- 探针 v2 的排除宇宙含 450(`exec_probe.py` 选币排除 live140 ∪ wide400/450 ∪ 持仓), 与设计 §3-bis ⑤ 一致; 探针现已 KILL(08-21 事故), L1 期间保持。

## 8. 批次 2(2026-08-22 04:5xZ): 电池与磁盘配置解耦 —— 切换是生产动作, 测试不得反向锁死它
**事故**: 批次 1 应用(实盘 `cf3fd9f`, 122/122)后, 按 RUNBOOK §2.2 把磁盘 config 切成 `book_source=external + per_name_stop.active_profile=wide`(offset 23/poll 5)的第二次 safe_commit 电池红了 3 套(batch 20260822T041458Z): `tests_signal_and_loop`(把磁盘 config 复制成夹具基线 ⇒ 内部路径用例全红, phase B `_pending` KeyError)、`tests_guard_calibers`(per_name_stop [F] 按 `PNS.cfg(磁盘)` 取参 ⇒ 宽 profile −30% 下 −26%/−25% 用例不触发)、`tests_external_book`(H10/I1: `book_with` 从磁盘起步 ⇒ external 基线污染; I1 HOLD 无 ctx ⇒ TypeError)。**根因同一个: 三套件把磁盘 config 当夹具基线; 而 book_source/active_profile 是操作员的生产开关 —— 开关一翻, 套件的"被测对象"跟着翻, 电池变红, 反过来把开关锁死(safe_commit 要求全绿)。**
**原则**: 测试的夹具必须**显式声明**自己的书源与 profile(internal 基线 / 指定 profile), 只取磁盘 config 里与被测对象无关的真值(时钟/容差/腿权重/口径戳); 只有明确"关于磁盘配置"的断言才读磁盘, 且必须在两种状态下都成立。
**改动**(三文件, diff + 全文在 `live_repo/live/`): ① `tests_signal_and_loop.py`: 新增 `_internal_baseline()`, 五处磁盘派生夹具(`_open_clock` / 时钟门块 `_REAL_INTERNAL` / `_mode_book` / `_probe_book` / `_bad`)全部钉 internal+profile null(时钟/容差仍为真值); ② `tests_guard_calibers.py`: `CFG = PNS.resolve_profile(dict(磁盘 per_name_stop, active_profile=None))`(显式基础 profile; 宽 profile 由 tests_external_book [P] 断言); ③ `tests_external_book.py`: `BASE_BOOK = _internal_baseline(REAL_BOOK)`, `book_with`/`pns_wide` 从 BASE 起步; I1/I2 对 `_anchor_ctx` None 防御(HOLD 无 ctx ⇒ 报告不抛); [S] 增 S9b(磁盘 book_source 合法名); 总 102 检查。其余文件**零改动**(`PATCH_RECEIPT.json files_unchanged_vs_base` 八项; 生成器改为基线感知: 已应用的 hunk 跳过, 基线 = 实盘 HEAD `cf3fd9f`)。
**收据**(两棵副本树: `live_scratch`=磁盘 internal, `live_scratch_ext`=磁盘 external+wide, `build_scratch.sh --external`): 三套件 ×2 树 = `RUN_tests_{signal_and_loop,guard_calibers,external_book}_disk{INTERNAL,EXTERNAL}.txt` **全部 ALL PASS**(external_book 102/102 ×2); 全量电池 ×2 树 = `RUN_full_battery_scratch_disk{INTERNAL,EXTERNAL}.txt`(写本节时后台在跑; 完成后在此行追加两份读数)。

## 9. 批次 3(2026-08-22 04:4xZ, 与批次 2 同一轮): 目标文件 = 宇宙内的书 —— 生产方 `universe` 列表 + 适配器 pop/归一 + 影子 v3(并入 WA a/b)
**事故/发现**(主线 + WA 审计): 影子 v2 首个签名文件(anchor 1787371200, 04:21Z)含 **746 个非零名, n_universe=450** ⇒ 296 个是"已出数据宇宙的冻结尾巴"(引导时从 829 名 pod 持仓带入, 影子只为 450 名拉数 ⇒ 目标恒 0 而 EMA 步长 < 带宽 ⇒ 永不交易、永不衰减、纸面记 0 盈亏; gross 0.25 = 总 gross 1.38 的 18%)。批次 1 的适配器只有交易所过滤 + 最小名义额, **会把这 296 个尾巴当目标交易**, 与"出宇宙即平"相反。
**改动**(同一 commit):
- **生产方 `shadow/shadow_loop_v3.py`**(生成器 `shadow/make_v3.py`, 基线 = 运行中 v2 SHA 019049584b; diff `shadow_loop_v3.diff` 134 行): v2 → WA (b) 出宇宙即平(`EXIT_ON_LEAVE=True`; **v3 置 `EXIT_NON_MEMBERS=True`** = 离开 K400 成员集的名也即平 ⇒ 纸面书 ≡ 可执行书; ★ **一处与 WA 原 hunk 的偏差, 已文档化**: WA 在 NON_MEMBERS 分支写 `keep[:] = False; keep[m] = True`(成员掩码**替换**宇宙掩码 ⇒ 宇宙外的成员会被保留 — 40 天引导缓存使非 live 名在 ~08-23 前仍可能成为成员), v3 改为 `keep &= member_mask`(宇宙内 ∧ 成员), 生成器 NOTE + `tests_target_live_output [8b]` 钉住) → WA (a) 记分补尾巴字段(score 行加 `tail_*`/`gross_bps_total`/`net_bps_total`, **原字段逐字不变**) → 目标文件加 **`universe: [450 名]`**(与 `universe_sha` 同一配方; `producer: shadow_loop_v3`)。生成器对 WA 两份 diff 的全部 `+` 行做交叉核对(除上述两行 v3 有意改动), 缺一即拒。
- **适配器 `external_book.py`**: 契约 v1 修订 — `universe` 列表**必填**(缺 ⇒ `schema` 拒; 列表 sha ≠ universe_sha ⇒ `universe_list_sha` 拒 ⇒ HOLD); 权重按列表**拆分**: `w`/`symbols` = 宇宙内书, `gross_in` = 宇宙内 Σ|w| 为归一分母(实盘 gross = NAV×gross_mult, 不被尾巴稀释), `w_outside`/`outside_names`/`n_outside_universe`/`gross_outside_frac` 进记录; `OUTSIDE_UNIVERSE_ALARM_FRAC = 0.25`(尾巴 gross 占比 > 25% 才 HIGH, 信息级); 新纯函数 `held_not_in_target`。
- **anchor_loop.py H15–H18**(对已应用基线 cf3fd9f 仅 +19 行): H15 尾巴 >25% 的 HIGH; H16 external 模式 `symbols = 宇宙内目标名 ∪ 持有名`, `self._ext_held_exit` = 持有但生产方不再给目标的名(出宇宙 / 出成员集 / 权重 0 / 在役残仓); H17 这些名并入 `_untradable` ⇒ 既有 clamp pass-2 ⇒ `flatten_only` ⇒ plan 生成 reduce-only 单(maker 优先, k 窗后强制补单) — **绝不走 universe 门的市价退出**(那条留给交易所状态非 TRADING 的退市名); H18 记录 `held_exit/n_held_exit` 进 ctx/anchors 行/phase_A `external_filters`。
- **测试**: `tests_external_book` → **114 检查**(新 [U]: 拆分/位归一/持有宇宙外名 reduce-only 退出/持有宇宙内未给目标名同样退出/记录字段/3% 不告警/33% HIGH 仍交易/列表 sha 不符 ⇒ HOLD/变异体 M4 "不拆分的读取器 ⇒ 宇宙外名进目标" 红; [R] 新增三条拒绝), 两态副本树各 114/114(`RUN_tests_external_book_disk{INTERNAL,EXTERNAL}.txt`); `tests_target_live_output`(v3)→ **45 检查**(v3 = v2 + 三块且只有五行被替换 / 契约含列表且 sha 同配方 / **配对: 读取器接受 v3 文件并正确拆分 S07 尾巴, 拒绝 v2 式无列表文件** / 原子性 / 调用点 / 无钥匙 / v3 开关 + WA T1/T2 在 v3 模块上复跑)两解释器 45/45; WA `test_shadow_tail_fix.py` 原样 14/14(`RUN_test_shadow_tail_fix.txt`)。`gate_coverage` 边界自述同步(七个盲点, 新增 (g) 宇宙列表只验 sha 不验"对不对")。
- **`verify/l0_mirror_check.py`**: 比对对象 = 宇宙内权重(按 gross_in 归一); 被撤名单按因归类(宇宙外尾巴 ∪ 交易所 meta ∪ 2×minNotional ∪ 止损/场所); plan-only 名必须 = `held_exit` 或 flatten 行; 旁证 sha 与列表 sha 都验。
**对影子 PASS 计时与成本(WA 提案 §1-2 + 主线裁定)**: 激活 (b) 的一次性成本 ≈ 0.25 gross × 4.7 bps ≈ **1.2 bps**, 纸面 gross **1.38 → 1.13**; 此后 `net_bps` 是真持有书的净额(不再有"持有但不记分"的仓位); **84 锚 PASS 计时按"一锚一变更"登记**(RESULT 分段报激活前后), 不重新起算; (a) 的 `tail_*` 字段只作过渡期采证, PASS 仍读 `net_bps`。目标文件里的权重 = 宇宙内成员书(生产方 (b) 保证)**与**适配器 pop+归一(消费方保证)= 双保险; 任一方失效另一方仍成立。
**操作**(RUNBOOK §2.1 已改为 v3): 主线一次重启: 杀 v2(按 PID) → `SHADOW_OFFSET_MIN=16 nohup ./venv/bin/python shadow_loop_v3.py run` → 首锚核 `target_live/<anchor>.json` 含 `universe`(450)且 `shasum -c` 过, `shadow_log` 的 `signal` 行有 `forced_exit_n/forced_exit_gross`(激活锚应 ≈296/0.25), `score` 行有 `tail_*`。实盘侧: 批次 3 的 `external_book.py`/`anchor_loop.py`/`tests_external_book.py`/`gate_coverage.py` 四文件 diff 对已应用基线 cf3fd9f 应用(`git apply --check`)+ safe_commit; **v2 文件(无 universe 列表)会被新适配器以 `schema` 拒 ⇒ HOLD**, 所以 v3 重启须先于实盘侧切 external(顺序: 应用适配器 → 重启 v3 → 切 external)。
**收据**: 上述单测 7 份 RUN; 两态全量电池 `RUN_full_battery_scratch_disk{INTERNAL,EXTERNAL}.txt`(批次 3 状态, 写本节时后台在跑; 完成后在此行追加读数)。
