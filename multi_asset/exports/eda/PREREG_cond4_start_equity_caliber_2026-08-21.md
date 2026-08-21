> **创建:** 2026-08-21 15:50Z | **Session:** 6737834a | **状态:** 预注册(用户已裁定语义, 补丁待电池) | **作废条件:** §4-4 语义被用户再次裁定改变, 或 daily_nav 字段语义改变(见 `docs/FIELD_CALIBERS_2026-08-19.md`)

# PREREG — §4-4 累计亏损停机线: 口径修复(B33)

## 0. 用户裁定(原文)
- 2026-08-21 我问"入金后起点重标定 vs 起始权益", 用户: **"按照起始权益金"**。
- 2026-08-10 方案 C 裁定(memory `deposit_option_c_ruled`): "TRANSFER 不入盈亏 ⇒ 停机线自动按新 NAV 标定; 84 锚为正 ⇒ 3× + 停机线 −50% 打包预授权"。本预注册是它的**精确化**, 不改变 −25% 数字, 不改变 2× 杠杆。

## 1. 缺陷(修复前, 已测量)
现行 `live/watchdog.py` cond4: `_c += (realised_d + unrealised_d)/nav_d` 逐日累加, 再取该累加曲线**自高水位**回撤。两处与规格不符:
1. `realised_d`(当日自日初已实现)+ `unrealised_d`(**水平**, 不是变化)—— 前日未实现已在前日权益里, 今日再加一次 = 双计(与 §4-2 12:16Z 误触发同族, 见 `docs/INCIDENT_daily_loss_trip_2026-08-21.md`)。
2. 注释写"从起始权益", 算法是"从累加曲线高水位(≥起点)" ⇒ 实际比规格更保守。

修复前读数(2026-08-21 15:40Z, 21 个 LIVE 日 08-01→08-21): 缺陷累加器 **−7.56%**; 真实 TWR 从起点 **+0.59%**; 自高水位最大回撤 −4.31%(08-21 日 −2.96%)。

## 2. 新口径(冻结)
- 日收益 r_d: 普通日 = nav_d/nav_{d−1} − 1; **转账日** = (realised_d + unrealised_d − unrealised_{d−1})/nav_{d−1}(盈亏按定义不含 TRANSFER; 转账**金额永不进公式**, 因入金日该字段金额不可靠, 错题集 B 族)。
- 截断日(收益账本翻页上限 ⇒ realised 为下界): **扣留**; 其 nav 仍精确, 链条用 nav 比跨过空洞; 空洞内若有转账 ⇒ 该跨度不可定价 ⇒ **BLIND**(命名之)。
- 累计 = Π(1+r_d) − 1, **起点 = LIVE 日志首日**(08-01), 入金**不重标定**; 触发: 累计 < −25%。
- 自高水位回撤同时报告(informational, 不触发)。
- 覆盖率 < 0.50 且未触发 ⇒ BLIND(沿用); 无可定价日 ⇒ None ⇒ BLIND。

## 3. 对在役守卫的效果(事前声明)
- **放松**: 从"高水位(≥起点)口径"改为"起点口径"(用户裁定); 常 gross 全史模拟(`RESULT_event_calendar_and_wide_stop_2026-08-21.md` §L/§M): 2× 下年触线 起点口径 7–17% vs 高水位 27–45%。
- 利润保护(高水位线)若要, 另起"回撤阶梯"预注册, 不塞进本线。

## 4. 验收(看数字前冻结)
1. `tests_watchdog [4]` 夹具: 6 日 × −6%/日 体现在 nav(0.94^5 = −26.6% < −25%)⇒ 触发; 空树 ⇒ None ⇒ blind。
2. `tests_numerator_honesty [B]/[C]`: 截断日扣留计数/覆盖率/blind 不变; 变异体 `cond4_ignores_truncation` 仍改变覆盖率(源码行 `_nav_use = [...]` 保留)。
3. 新增断言: 转账日读数来自盈亏不来自 nav 跳变(入金 +3810 的日子读 ≈ +1.45% 不是 +178%); 空洞含转账 ⇒ blind 并命名。
4. 电池全绿 → `safe_commit`; 提交后 `last_eval.json` cond4 读数应 ≈ +0.6%(起点)/−4.3%(高水位, info)。

## 5. 结果(提交后回填, 2026-08-21 15:53Z)
- 实盘仓 commit **`57cb180`**(电池全绿, 一次通过); 变更: `live/watchdog.py` cond4 块 + `live/tests_watchdog.py` [4](夹具亏损入 nav 6%/日 ⇒ −26.6% 触发; −22.6% 不触发; 入金日按盈亏 +1.77% 非 nav 跳变 +200%; 截断空洞含转账 ⇒ blind 并命名)。
- `tests_numerator_honesty` 变异体 `cond4_ignores_truncation` 仍有牙: "扣留"在代码里只定义一次(`_nav_use` 成员资格), 链条与覆盖率共用之。
- 新增 detail 键: `cum_return_from_start_pct`(判读数)/`max_drawdown_from_peak_pct_INFO`/`chain_broken`/`unpriced_flow_days`; 触发文案改为 "cumulative return from STARTING equity"。
- 首锚读数(16:00Z 看门狗)见 INCIDENT 文档 §R 追记。
- 注: `tests_production_signature` 依赖未移植的 `pilot_daily`, 是电池明文排除的既有红(run_acceptance.sh 头注 L12), 与本修复无关。
