> **创建:** 2026-09-06 09:1xZ | **Session:** b9646a9e | **状态:** **已执行(用户字 09-06「按第一条修, 修完后 09-07 04Z 恢复建仓, 2x 杠杆」); 实盘仓提交 `c800690`, 电池 128/128 全绿; 恢复动作待 09-07 01:10Z 定时**| **用户字(触发本文):** 09-06 "最严谨的方式在下一锚恢复建仓, 2x 杠杆" | **受据:** 本次止损事件档(beeefc0 / STATE 9032ba6); 复场时点实测(43bfaa0) | **作废条件:** 用户否决; 或发现另有已设计的恢复路径

# PREREG(草案)· §4-2 单日止损的**恢复语义**修正: 判据从"日志中最差的一天"改为"最近一个已定价日"

## 0. 阻断事实(VERIFIED, 读码 + 隔离复现)
- `live/watchdog.py`: `days = PL.available_days(root)`(= pilot_log 里**全部**日目录, 无窗口上限, `pilot_log.py` L489–493)→ `per_day_loss` 逐日 → **`worst = min(_priced)`** → `hit = worst < DAY_LOSS_LIMIT_PCT(−4.0)`。
- `ops/resume_from_trip.sh` 步骤 1/4 是硬门: 把 pilot_log **整棵树复制**到临时目录重跑 `WD.run`, `ev["tripped"]` 为真即拒绝, 无覆盖旗标。
- ⇒ **2026-09-06 这一天的 −4.12% 会永久留在 `min()` 里, 恢复门将永远拒绝。**
- **隔离复现(只读, 临时目录, 未触碰实盘)**: ① 现状 → `tripped=True triggers=['§4-2 single-day loss -4.12% ...']`; ② 在副本里**新增一个持平的 20260907 日**(nav 不变, 实现/未实现 0)→ **仍然 `tripped=True`, 同一条 trigger**。⇒ 等待日切/新的一天**不能**解除。
- 性质: 这不是"某人写错了一行", 而是**同一个量被两处用作不同语义** —— 作为**触发器**"历史上最差的一天"与"今天在亏"在触发当日等价, 所以从未暴露; 作为**恢复门**它把一次性事件变成永久状态。§4-2 此前从未在实盘触发过(watchdog 自述 4.5 年 3 次且全在 2024), 所以这条路径是第一次被走到。

## 1. 改动(锁死; 仅 `live/watchdog.py` cond2 一处, 不动阈值、不动其它条款)
- `hit`(以及告警档 `_alert`)改用 **`recent = 最近一个已定价日的 per_day_loss`**, 而非 `min(全部)`; `worst_day_pct` 与 `worst_day` 作为**历史统计**照常上报(键名不变, 语义不变)。
- 新增上报键 `recent_day_pct` / `recent_day`(判据实际用的那个数), 使"判据用的量"与"上报的量"不再同名异义。
- 阈值 `DAY_LOSS_LIMIT_PCT = −4.0` 与 `DAY_LOSS_ALERT_PCT_OF_EQUITY = −2.68` **一字不改**。
- 触发语义不变: 事件当日, 最近已定价日就是当日, `hit` 与现行完全相同 ⇒ **本次触发不会被追溯抹掉**, 09-06 仍是一次真实触发。
- 恢复语义变为: **只要最近一个已定价日不再越线, 门就放行**。09-06 的行留在日志里作为历史事实。

## 2. 验证(先于任何实盘动作)
1. **逐位恒等**: 用 pilot_log 副本, 对**每一个历史日**跑改动前/后的 `WD.run`, 断言 `tripped` 与 `triggers` **逐日相同**(除 09-06 之后的恢复判定外)。特别断言: 09-06 当日两版都 `tripped=True`。
2. **新语义验证**: 副本里加一个持平的 20260907 → 改动后 `tripped=False` 且 `conditions_blind` 为空; 加一个 −4.5% 的 20260907 → 仍 `tripped=True`。
3. **盲区**: 若最近已定价日不存在(新树), 走既有 `blind` 路径 ⇒ 恢复门按现行规则拒绝(fail-closed 不变)。
4. **电池**: `ops/safe_commit.sh` 全绿(128/128), 含 watchdog 套件; 新增测试三条(恒等/新语义/盲区)并注册进 SUITES 与 gate_coverage。

## 3. 恢复执行(仅在 §2 全绿且用户给字后)
1. `LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check` → 必须 `RESUMABLE`。
2. `bash ops/resume_from_trip.sh "2026-09-06 §4-2 −4.12% 触发; 归因 = 多头极端正费率名连续崩跌(事件档 beeefc0), 非缺陷; 基率 1–2 天/年; 复场时点实测 43bfaa0 显示越早越好; 用户 09-06 裁定按 2.0× 恢复建仓"`。
3. 验 `state/live/watchdog/state.json` 已清(reduce_only / stage3_open_halted 不再为真), 证据已隔离归档。
4. **恢复锚**: 门放行后的**第一个锚**。执行器在锚内**先睡到 N+24 再读止损状态**(`anchor_loop.run_anchor` 先 `EXT.wait_for_slot` 后 0b), 所以清除只需在该锚的 **N+24 之前**完成, 有 24 分钟窗口, 不是竞态。
5. **杠杆维持 2.0×**(`sizing_policy constant_leverage_2.00` 不改; σ_fund 阶梯仍为撤回态 = g 1.0)。
6. **首锚验收(冻结)**: gross → 1.9–2.05×NAV; 名数 ≈ 240; 换手 ≈ 100%(从空仓重建, 一次性); maker 占比 ≥ 0.60(重建锚必然低于稳态 0.85, 因残差走补单); 费 ≤ 4.5 bps(若走 taker); 拒单率 < 40%; 无 429/−1003; phase C 三件齐; readback 非零名数 ≈ 目标名数; watchdog 当锚不再 tripped。任一不成立 ⇒ 记录并报用户(不自动回滚, 因为"回滚"= 再次平仓, 那是更大的动作)。

## 4. 不做的事
- 不删除、不移动、不改写 09-06 的 pilot_log(证据)。
- 不加覆盖旗标、不绕过硬门、不手改 `watchdog/state.json`。
- 不改任何阈值; 不改其它条款(cond1/3/4/5/6/7)。
- 不在同一批里做 N+6 Phase 2 换装(见 §5)。

## 5. 与在飞工程的关系
N+6 Phase 2 换装建议**顺延到恢复并跑满数锚之后**: 换装本身与书行为无关, 但在"刚复场 + 重建全书"的锚上做时点改动, 会让首锚验收失去正常交易的对照。沙箱三锚验证照常进行。

## 6. 执行收据(2026-09-06 10:0xZ)
- **实盘仓提交 `c800690`**(`ops/safe_commit.sh`, **ACCEPTANCE: ALL GREEN 128/128**), 改动文件三个: `live/watchdog.py`(cond2 判据取值 + 三个自报键)、`live/tests_watchdog.py`(新增 [2c] 七项断言)、`live/tests_threshold_roles.py`(源码文本守卫同步)。
- **§2.1 逐位恒等**: 逐日截断树 × 新旧两版, **37/37 天 `tripped` 与 `triggers` 完全相同**。中途出现的 `conditions_blind` 差异经判定为**测试装置假象**: 把**新版**放到同一临时目录跑, 同样出现 `cond4b_leverage` blind(该条款按模块位置解析配置路径), 与本次改动无关。
- **§2.2 新语义三例**: 现状仍 tripped(−4.12%, 同一 trigger)/ 追加持平次日 ⇒ 不再 tripped / 追加 −4.5% 次日 ⇒ 再次 tripped(报新那一天的数)。
- **§2.3 盲区**: `recent is None` ⇒ blind, 与旧版 `len(_priced)==0` 等价, fail-closed 不变。
- **§2.4 电池**: 第一次运行 **`tests_threshold_roles` 判红并拒绝提交** —— 该套件逐字断言 cond2 那两行的写法, 正是为了防止 halt/alert 两个常量的角色被对调; 它抓到了这次改名。按其意图同步变量名(引入 `_HALT_LINE`/`_ALERT_LINE` 常量), **[E] 红能力保留并通过**(把 LIMIT 换成 ALERT 常量后仍必须判红), 另加一条断言钉住"判据取最近已定价日"。第二次运行 128/128 全绿。
- **改动后即时核查**: `LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check` 仍打印 **NOT RESUMABLE**(最近已定价日 = 09-06 = −4.12%)⇒ **今天不可恢复, 与设计一致**; 09-07 的 NAV 行写出后(00Z 锚 phase C ≈ 00:44Z)门才会放行。
- **恢复动作**: 定时 `0b6c546e` 于 09-07 01:10Z 执行 §3 全部步骤(四项前置 → 只读核查必须 RESUMABLE → 唯一一次写操作 → 验证 → 记账 → 建 04Z 首锚验收定时)。杠杆维持 2.0×。
