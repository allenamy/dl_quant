> **创建:** 2026-08-22 04:1xZ | **Session:** 6737834a (live-sys-eng 子会话) | **状态:** 草案 — 随 `multi_asset/exports/live/wide_live_staging_2026-08-22/`(staging 包)交付, 主线审后生效; 上线前逐条打勾 | **作废条件:** DESIGN_wide_live_deployment_2026-08-22 作废, 或 external 适配器被替换/回滚

# RUNBOOK — 宽书实盘化(external book)启动 / 升级 / 降级 / 停止 / 回滚 / 每锚核查

依据: `docs/DESIGN_wide_live_deployment_2026-08-22.md` §1–§3-bis。代码: staging 包 `multi_asset/exports/live/wide_live_staging_2026-08-22/`(README 有逐 hunk 说明与应用步骤)。**本文只写动作与判据, 不重复设计理由。**

## 0. 白话总览(三句)
1. 宽书的权重由 `~/wide_shadow/shadow_loop_v2.py` 每锚算好并写成**签名文件** `~/wide_shadow/state/target_live/<anchor_ts>.json`(+ `.sha256`); 实盘仓的锚进程在 `external_book.anchor_offset_min` 分钟后读它, 校验通过 ⇒ 目标名义 = 权重/gross_norm × NAV × gross_mult, 进入原执行层(maker k=900s + 补单 + 看门狗 + 逐名止损)。
2. 读不到/校验不过 ⇒ **本锚保持现仓不下单 + HIGH 告警 `external_book_unavailable`**, 绝不回退在役引擎; 连续读不到按既有预注册阶梯(≥24h 减半 reduce-only, ≥48h 平仓)。
3. 分级上量 L0 镜像(零下单)→ L1 1× → L2 2× → L3 2.5×, 每级 ≥12 锚, 判据见 §3; 停止 = 停开仓(KILL 或 reduce-only), 不回 internal。

## 1. 前置收据(§3-bis 五条, 缺一不进 L1; 主线逐条贴 SHA/commit/读数)
| # | 条件 | 收据形式 | 状态 |
|---|---|---|---|
| ① | wide-full-audit 独立口径审计: 宽书显著优于在役(给 CI) | RESULT 文档 SHA | 待(审计在跑) |
| ② | 适配器 + 签名输出进实盘仓, safe_commit 电池全绿(含 `tests_external_book` + 边界自述) | `~/dl_quant_live` commit + `state/_safe_commit_acc.log` 末三行 | 待(staging 已在全量副本树跑电池, 见 README §5) |
| ③ | L0 镜像 ≥2 锚: 目标文件逐锚读到、名义额/过滤/清单与影子权重一致(\|Δw\|<1e-6)、无告警 | `verify/l0_mirror_check.py --anchor <ts>` 输出 `L0 MIRROR: PASS` ×2 + 两锚 phase_A 行 | 待 |
| ④ | 守卫全开(§4 看门狗、双账守卫、per_name_stop 宽参数、杠杆上限)且 profile 切换有测试 | `tests_external_book [P]` 绿 + `config/book.json per_name_stop.active_profile == "wide"` + guard_twin 在跑(launchd com.hsy.guardtwin) | 测试已绿; 配置待切 |
| ⑤ | 本 RUNBOOK §2 启动核查清单逐条打勾(含探针 v2 排除宇宙含 450、影子权重时序先于执行读取) | 本文 §2 勾选 + 时序实测行 | 待 |

## 2. 启动(顺序固定)

### 2.1 影子侧: 起 v3(签名输出 + universe 列表 + WA a/b 尾巴修法), 停 v2 —— 只动 ~/wide_shadow, 不动实盘仓
(历史: v2 = v1 + 签名输出, 主线 08-22 04:1xZ 已启动 PID 27185; **v3 = v2 + WA (b) 出宇宙即平[EXIT_NON_MEMBERS=True, keep = 宇宙∧成员] + WA (a) 记分尾巴字段 + 目标文件 `universe` 列表**; staging README §9。)
```
# (a) 把 v3 与其测试放进影子目录(v3 = v2 + 三块, 只有五行被替换; tests_target_live_output [1] 断言这一点)
cp multi_asset/exports/live/wide_live_staging_2026-08-22/shadow/shadow_loop_v3.py ~/wide_shadow/
cp multi_asset/exports/live/wide_live_staging_2026-08-22/shadow/tests_target_live_output.py ~/wide_shadow/
cd ~/wide_shadow && DL_QUANT_LIVE_LIVE=~/dl_quant_live/live ./venv/bin/python tests_target_live_output.py   # 45/45(实盘批次 3 补丁应用后跑; 应用前用 staging 的副本树路径)
# (b) 在锚间静默窗(避开 :16-:23)停 v2: 按 PID, 不用 pkill -f(协议 §9)
pgrep -f "shadow_loop_v2.py" ; kill <PID>                # 现 PID 27185(04:1xZ 起), env SHADOW_OFFSET_MIN=16
# (c) 起 v3 — ★ offset 决定(见 §2.3): 维持 16 ⇒ 落盘 ≈N+21.5, 实盘 anchor_offset_min=23/poll 5; 改 6 ⇒ 落盘 ≈N+12, 实盘改 13/5
cd ~/wide_shadow && SHADOW_OFFSET_MIN=16 nohup ./venv/bin/python shadow_loop_v3.py run > loop.out 2>&1 &
# (d) 首锚核: 文件含 universe(450) + 旁证 + 日志行(激活锚 forced_exit_n ≈296 / forced_exit_gross ≈0.25; score 行有 tail_*)
ls -la state/target_live/ ; (cd state/target_live && shasum -a 256 -c <anchor>.json.sha256) ; python3 -c "import json,sys; d=json.load(open('state/target_live/<anchor>.json')); print(d['producer'], len(d['universe']), d['n_names'])" ; grep '"e": "target_live\|forced_exit' shadow_log.jsonl | tail -3
```
- ★ v3 仍无钥匙(`assert_no_keys` 未动); **书行为变更一次**: 激活锚强制平掉宇宙外/非成员尾巴(一次性成本 ≈1.2 bps, 纸面 gross 1.38→1.13), 84 锚 PASS 计时按"一锚一变更"登记(RESULT 分段报), (a) 字段只采证, PASS 仍读 `net_bps`。
- ★ 顺序约束: **新适配器会把 v2 式文件(无 universe 列表)以 `schema` 拒 ⇒ HOLD**, 所以 (i) 应用实盘批次 3 补丁 → (ii) 重启 v3 → (iii) 切 external; 反过来会让首锚 HOLD(无害但浪费一锚)。
- ★ 回退 = 杀 v3 起 v2(v2 文件仍在; 但那时实盘适配器必须也回退到批次 2 的 external_book, 否则 HOLD)。

### 2.2 实盘仓: 应用补丁 + safe_commit(见 staging README §4 精确步骤)
- 应用后默认 **`book_source: "internal"`** —— 行为逐位不变(`tests_external_book [I]`), 电池必须全绿。
- **切换 external = 同一次编辑 config/book.json 三键**: `book_source: "external"` + `per_name_stop.active_profile: "wide"` + 确认 `anchor_max_seconds ≥ 3000`(staging 已设 3000); `external_book.gross_mult` 按级别(L0 见 §2.4, L1 1.0)。切换也走 safe_commit(电池全绿), 在锚间静默窗落盘(落盘即上线)。

### 2.2-bis ★ 实测(08-22 04:14Z): 切换提交的电池红 3 套 —— 套件耦合磁盘 config
- 适配器提交 `cf3fd9f` 122/122 绿(internal 默认)。随后按 §2.2 切 `external + wide profile + 23/5` 的 safe_commit 电池 **红 3 套**: `tests_signal_and_loop`(把磁盘 config 当夹具基线, 内部路径用例在 external 下红)、`tests_guard_calibers`(per_name_stop 用例写死基础 −25%, wide −30% 下不触发)、`tests_external_book`(H10/I1 依赖磁盘默认 internal; I1 处 `_anchor_ctx["external_book"]` None 的 TypeError)。**磁盘 config 已回退 internal**(实盘仓干净, 禁止未经电池的配置留在盘上)。
- 规则(新增): **测试必须与磁盘配置解耦**(显式注入夹具基线/profile); 切换是生产动作, 不能被测试反向锁死。修复在 staging(wide-live-staging 代理), 两种磁盘状态下全电池都要绿后再切。L0 顺延至修复落地后的下一计划内锚。

### 2.2-ter ★ 尾巴(宇宙外冻结名)处理 — 08-22 04:2xZ 决定
- 影子 v2 首文件(anchor 1787371200): 746 个非零名 vs 宇宙 450 ⇒ 296 个尾巴(gross 18%)。**目标文件 = 宇宙内的书**: 生产方改 v3(影子 `b_exit_on_leave` EXIT_NON_MEMBERS=on + 记分 `a_tail_scoring` + 目标文件附 `universe` 列表), 适配器 pop ∉ universe 的名并按宇宙内 Σ|w| 归一(双保险); 一次重启影子(08:16Z 前)。WA 提案 d013c87; 合并交付由 wide-live-staging。
- L0 镜像核对对象 = 宇宙内归一权重; 被撤名单 = 尾巴 ∪ 交易所过滤 ∪ 最小名义额。

### 2.2-quater ★ 落地记录(08-22 04:58Z)
- 适配器 `cf3fd9f` → 批次 2+3 `2652f95`(解耦 + 宇宙内书)→ **切换 `37186e6`**(external + wide profile + 23/5), 三次电池 122/122。影子 v3 04:46Z 起(PID 34330, SHADOW_OFFSET_MIN=16)。操作员停开仓(03:15Z)仍在 ⇒ 08:00Z/12:00Z 锚 = L0-b 镜像; 08:33Z 自动核对脚本已挂(l0_mirror_check + phase_A 字段 + 无告警 + 无订单)。L1 须用户一字。

### 2.2-quinquies ★ 红队上线前审阅(`docs/REDTEAM_wide_live_prelaunch_2026-08-22.md`, e31a61d)与处置(05:5xZ)
- **R1 (P0) 锚超时 3000s 对 N+23 相位只剩 2–5 min 余量**(影子晚 2–3 min ⇒ 锚在下单中途 os._exit 不撤挂单 ⇒ 下锚 §4-5b 整书平)⇒ `anchor_max_seconds` 3000→**3600**(config, safe_commit 在跑); 首个 L1 锚人盯 done < N+48。
- **R2 (P0) 探针 v2 仍在跑**(我的 00:52Z 重启使 RUNBOOK "已 KILL" 与事实不符)⇒ 05:52Z `KILL` 文件 + 进程 `killed` 事件 + launchd `com.hsy.execprobe2` 卸载 ✓(L1 期间保持停止; 重启须用户另裁)。
- **R3 (P1) 不可用阶梯**(24h DERISK/48h FLATTEN 是 staging 自选, 设计与预授权只写"保持现仓+告警")⇒ `on_unavailable` ladder→**hold**(config); 阶梯作为选项呈用户裁。
- **R4 (P1) 1× 粒度**: NAV 15.4k × 1× 摊到 ~300 名 ⇒ 60–87% 的调仓量 < minNotional(带宽 3.9U < 5U)⇒ L1 在 1× 下大部分名字调不动, ρ/净额判据失真 —— **需用户裁**: (a) L1 直接 2×(每名义额翻倍, 仍低于在役在役 2× 的风险因夏普更高)/ (b) 1× 但只作"管道+成交"验证, 不读 ρ / (c) 减名(top-K 200)/ (d) 加 NAV。
- **R5 (P1) 止损 20U 门槛对 175 名/14% gross 失明** ⇒ wide profile `min_notional_usdt` 20→**5**(config)。
- **R6 (P1) 一次性 autoresume launchd 仍挂载 RunAtLoad 且 --check 已 RESUMABLE**(重启机器会自动恢复书!)⇒ 05:52Z 已卸载并移走 plist ✓。
- **R14 (P1) L0 停开仓锚证明不了 L1 时序** ⇒ L1 首锚人盯(external_wait/age_s/done 时刻)。
- 红队结论: 修 R1/R2 + 裁 R3/R4/R5 + 卸 R6 + 首锚人盯后**可上**; L1 当执行探针读。

### 2.3 ★ 时序(必须实测后打勾, 不按设计文字)
- 设计: 影子 N+6 产出 / 执行 N+8 读。**实测(08-20..22 八锚 shadow_log `signal` 行): 影子以 SHADOW_OFFSET_MIN=16 起跑 + 运行 311–351 s ⇒ 权重落盘 N+21:12..N+21:51。** ⇒ N+8 读必然读到上一锚文件(anchor 不符 ⇒ HOLD)。
- 规则: `anchor_offset_min ≥ 影子落盘分钟 + 1`, `poll_grace_min ≥ 3`(N+offset 起每 15 s 重试), `max_age_min=10` 同时要求 written_utc 距读取 ≤10 min ⇒ offset 不得比落盘晚 >9 min。
- 实盘锚进程 launchd 在 N+0 起跑, 持锁**空等到 N+offset**(`external_wait` 记录), 再读文件、对账、下单; 相位 = 决策 N+offset, k=900s ⇒ phase B ≈ N+offset+16, 全程 ≈ N+offset+25 ⇒ `anchor_max_seconds=3000`(50 min)是 offset 23 的余量; 若 offset 改 13 可回 2400。
- 打勾项: [ ] v2 首锚 `target_live` 行 logged_utc = N+__:__ ; [ ] config `anchor_offset_min`/`poll_grace_min` = __/__ ; [ ] 首个 external 锚 phase_A `external_wait.slept_s` 与 `external_book.age_s`(应 < 600)。

### 2.4 L0 镜像(零下单, ≥2 锚)— 两种形态, 建议都做
- **L0-a DRY(电池级)**: 在任一 N+offset 之后手动 `LIVE_MODE=DRY_RUN LIVE_EXTERNAL_WAIT=0 /usr/bin/python3 scheduler/run_anchor.py`(off-schedule ⇒ 不开仓; DRY 无权益 ⇒ sizing blind gross=0 ⇒ 行全为 skipped_min_notional) —— 证明**读取/校验/过滤/规划链路在真树上走通**: phase_A 行 `book_source=external`, `external_book.ok=true`, `n_names`, `external_filters`。
- **L0-b LIVE-under-halt(真 NAV, 零下单)**: 在役已 08-22 03:15Z reduce-only 停开仓(watchdog 状态持久), 此时切 `book_source: external` 让 2 个**计划内**锚以 LIVE 跑: 开仓单全部 `blocked_by_halt`, 但 sizing 用真 NAV、filters 真、orders.jsonl 有全部 plan 行(target_w) ⇒ 可做镜像比对:
  `python3 multi_asset/exports/live/wide_live_staging_2026-08-22/verify/l0_mirror_check.py --anchor <nominal_ts> --mode LIVE` ⇒ `L0 MIRROR: PASS`(比对对象 = 文件**宇宙内**权重按宇宙内 Σ|w| 归一 vs plan 行 target_w; max|Δw−shift| < 1e-6; 被撤名单按因归类: 宇宙外尾巴 ∪ 交易所 meta ∪ 2×minNotional ∪ 止损/场所; plan-only 名必须 = `held_exit`(持有但生产方不再给目标 ⇒ reduce-only 退出)或 flatten 行)。
- L0 通过判据(设计 §2): 两锚文件逐锚读到、`|Δw|<1e-6`、电池全绿、**无 external_book_unavailable / 配置不一致 告警**。任一不符 ⇒ 不进 L1。

### 2.5 L1(真钱 1× NAV, 需用户一字 + §1 五收据)
- `external_book.gross_mult = 1.0`(已默认); 解除停开仓: `bash ops/resume_from_trip.sh "<reason>"`(先 `--check`); 首锚盯 phase_A/B + 看门狗行。
- ★ 探针 v2(com.hsy.execprobe2)已 KILL 且排除宇宙含 450(exec_probe.py 选币排除 live140 ∪ wide400/450 ∪ 持仓名); **L1 期间探针保持停止**(08-21 事故: 探针平掉书的 ATOM/SNX)。重开探针需用户另裁。

## 3. 升级 / 降级 / 停止判据(每级 ≥12 锚; 读数来源必须是真树)
| 级 | gross_mult | 升级判据(全部满足) | 降级/停止 |
|---|---|---|---|
| L1 | 1.0 | 对账零未授权残差(§4-5b/5e 无 unauth); maker 成交率 ≥60%(orders `filled`+`partial` 成交额/意图额); 逐锚净额对影子 score 差 \|均值\| ≤5 bps(shadow_log `score.net_bps` vs daily_nav 逐锚 equity_delta/NAV×1e4, 见 FIELD_CALIBERS); 看门狗零触发 | 看门狗任一触发 ⇒ 按阶梯; 连续 2 锚对账残差 ⇒ 停开仓 |
| L2 | 2.0 | 同上 + guard_twin 零分歧(★ guard_twin.py 的 DEPTH_LIMIT 仍写死 −0.25, 宽 profile −0.30 会制造假分歧 — 升 L2 前先改 guard_twin 读 profile, 否则此条不可读) | 同上 |
| L3 | 2.5(上限; 须同时把 `target_leverage` 提到 2.5, 否则 config 拒绝) | 用户裁 | — |
- 两周(84 锚)成功判据: 净额 ≥0 且与影子 score 逐锚 ρ ≥0.9 且与离线简单口径预期(≈1.5–1.8 bps/锚@2×)差在 CI 内; 否则回设计。
- 升级动作 = 改 `external_book.gross_mult`(safe_commit, 静默窗); 降级同键反向。`gross_mult` 变化由 `_size_book` 的 ±10% 死区自然重定尺寸(首锚会一次性调仓 ≈ Δgross 的换手)。

## 4. 停止 / 回滚(回滚 = 停开仓, **不回 internal**)
- **停开仓(温和)**: 写 watchdog reduce-only 状态(与现在 03:15Z 操作同一机制)⇒ 下锚起开仓单 `blocked_by_halt`, 减仓/平仓路径仍通; 恢复 = `resume_from_trip.sh`。
- **全停(急停)**: `bash ops/KILL.sh`(停调度 + halt + reduce-only 市价平仓 + 通知; 不接受参数)。
- **影子死了怎么办**: 锚自动 HOLD + HIGH 告警逐锚; ≥6 锚(24h)起按阶梯 DERISK 50%→25%(reduce-only), ≥12 锚 FLATTEN —— 若不想自动阶梯, 把 `external_book.on_unavailable` 改 `"hold"`(永远只 HOLD+告警)。修好影子 ⇒ 下锚自动恢复(无需人工 resume)。
- **回 internal**: 需用户一字 + 先核在役书链路(preds/模型/面板 08-22 后无人维护; `book_source: internal` 仅是开关, 不保证那条链还健康)。
- **配置写错**(book_source 拼错/块缺/gross 超杠杆政策): 锚 `BLOCKED_CONFIG` + CRITICAL, 零下单; 修 config 下锚生效。

## 5. 每锚核查清单(L0/L1 首周每锚; 之后每日)
1. `state/anchor_runs.log` phase_A: `book_source=external`, `action=TRADE`, `external_book.ok=true reason=null age_s<600 json_sha=...`, `external_wait.slept_s≈(offset−0.5)×60`, `sizing.leverage_source=external_book.gross_mult gross≈NAV×mult`, `external_book.n_outside_universe/gross_outside_frac`(v3 激活后应 ≈0; >25% 会 HIGH), `external_filters.n_held_exit`(持有但生产方不再给目标的名 ⇒ reduce-only 退出; 首锚 = 在役残仓 DEXE/JASMY/TAG 等)、`n_meta_excluded`/`below_min_notional.n` 与昨锚同量级(骤变=宇宙/NAV 事件)。
2. 影子侧: `shadow_log.jsonl` 本锚 `target_live` 行存在且 `json_sha` 与 phase_A 一致; `shasum -c` 过。
3. `anchors.jsonl` 新行: `book_source=external`, `factor_version` 含 booster/weights/universe sha, `panel_hash=universe_sha`, `realized_gross/target_gross` 比 ≥0.9(成交率), `net_over_gross` 在 ±3%。
4. 告警面: 无 `external_book_unavailable` / `profile 不一致` / `BLOCKED_CONFIG`; 看门狗 `tripped=false`; per_name_stop 状态 `stopped/cooldown` 名单合理(宽 profile −30%×2 锚)。
5. 周: `l0_mirror_check.py` 抽 2 锚; 净额 vs 影子 score 差; maker 成交率; 探针保持停止。

## 6. 已知未做 / 待裁(只列, 不决定)
- IC 监视(#55 ic_monitor)仍读在役口径的持仓书 IC(与宽书分数无关); 设计 §1"改读宽书分数"未在本包内。
- guard_twin 的 DEPTH_LIMIT −0.25 写死(见 §3 L2)。
- 影子 `SHADOW_OFFSET_MIN` 16 vs 设计 6(§2.3): 由主线裁; 两侧数字必须成对。
- MANIFEST 记 book_source/booster_sha(设计 §3.4): anchors 行已逐锚记 booster_sha/universe_sha/weights_sha; checkpoints/MANIFEST.json 未改(它描述 DL 模型, external 模式不消费)。
- `per_name_stop.profiles.wide.min_notional_usdt` 沿用 20(L1 1×NAV/300 名中位 ≈40 USDT, 20 以下小仓条款看不见)— 待裁。
- 发现(非本包改动): `anchors.jsonl.weights` 自 08-10 起记的是中性带宽 0.002 而非混合权重(anchor_loop `_bw` 被带宽重绑; 08-05 行还是 dict)— 建议单独一行修复 commit。
