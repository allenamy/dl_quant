# FP3 D v4: 现金核账引擎按复审 R7-C1/C2 修正 —— 判词仍 PARTIAL, 门不再被日历替代量误绿 — 2026-09-18

> **创建:** 2026-09-18 02:3xZ | **Session:** b9646a9e(主研究员) | **状态:** 出数(引擎 v4 `FP3_devices/fp3_cash_recon.py` d311211f; v3 ae4bc7ea 原字节存 `FP3_devices/archive/fp3_cash_recon_v3_ae4bc7ea.py`) | **作废条件:** 账本回填(I v2)后重跑; 复审否决 v4 判据
> **受据**: `FP3_receipts/CASH_RECON_20260801_20260918_v4.json`; 测试 `FP3_devices/tests_fp3_cash_recon.py`(8/8, 含复审 a5bda8bf 的 7 个夹具原样移植 + 1 个时刻负控); 取代 `RESULT_FP3_D_cash_reconciliation_v3_2026-09-18.md` 的 §3 判词行(v3 文件原字节保留)。

## 1. 修了什么(逐条对应复审)
| 复审项 | v3 缺陷(复审反例) | v4 修法 | 夹具结果 |
|---|---|---|---|
| **R7-C1 P1** | 标准日窗把结束日 00Z 起的日历 FUNDING_FEE/COMMISSION 当窗内流量, 且 local/venue **任一**过就算 ok: 22Z 已知 −5 结算、NAV 未扣 ⇒ 正确残差 +5, 却判 RECONCILED | 日历量降为**诊断**字段 `diag_calendar_substitute`(带 `NOT_A_GATE: true`), 门只看 (t0, t1] 事件窗残差 | v3 RECONCILED → **v4 PARTIAL, residual +5** |
| **R7-C2 P2** | 每 symbol/锚留**最后**一条回读, 不绑定 nav_ts; 同锚更晚回读覆盖 NAV 时刻标记(110 → 100 ⇒ 残差 100) | 标记 = 与 NAV 行**同一调用**的快照(|read_ts − nav_ts| ≤ 60 s, 同快照内 10 s 分组); 无 ⇒ `UNAVAILABLE_TIMING`; 收据记 `snapshot_ts` 与 `snapshot_minus_nav_s`; 成交/资金费窗一律 (t0, t1], 快照与 NAV 行之间若有成交/结算事件 ⇒ 该窗 `UNAVAILABLE_TIMING` | v3 PARTIAL/100 → **v4 RECONCILED/0**; 新负控(唯一回读在 NAV 后 10 min)⇒ UNAVAILABLE |
| 测试可移植 | 引擎硬编码账本根 | `FP3_LEDGER_ROOT` 环境覆盖(只为夹具) | 原 4 例(R01/R02/R03/去重)与正控仍绿 |

## 2. 真实账本(08-01 → 09-18 00Z, 48 个 NAV 窗)
- **VERDICT PARTIAL**: 48 窗, ok **11**, bad 37, UNAVAILABLE 0。v3 是 47 窗 ok 13: 少的 2 个 = v3 只靠日历替代量过的三窗(08-24 −4.91 / 08-28 +2.15 / 09-01 −9.20, 替代量 −0.81 / +0.79 / −0.86)在 v4 按事件窗残差判, 其中两窗超容差。
- **同调用绑定在真实账本上恒成立**: 全部窗 `snapshot_minus_nav_s` = 0(实测 LIVE 的 NAV 行与 `fapi/v3/account@post_anchor` 回读同一调用, |Δ| ≤ 5 s, 且同 4h 桶内 NAV 行之后没有更晚回读)⇒ **R7-C2 在归档数据上没有改变任何残差**, 但门现在显式证明这一点而不是碰巧。
- **09-07 起 11 窗**(含 09-17 20:43Z → 09-18 00:43Z 的 4 h 窗): 位置缺口 0, 残差均值 −7.6, 总体 sd **20.6**(样本 sd 21.6), max |r| 55.1(09-14 窗), ok 2。与 v3 的 22.2 同量级——**残差不来自 R7-C1/C2 两类缺陷**(诊断列与事件窗残差在 9/11 窗相差 < 0.4 USDT; 09-08 窗相差 12 USDT = 本地资金费行与日历日的结算窗错位, 与 I-4 一致)。
- 成本表不变(不受两处修正影响): 09-07 起去两个保护性整桶 58 锚 2.60 bps、maker 79.9%、同人口滑点 −0.97 bps(覆盖 99.8%)、换手中位 5.21%。

## 3. 读法(收紧, 按复审 §5)
- 残差 sd ≈21 USDT/日仍**未归因**; 已排除: 资金费口径(诊断列)、BNB 余额(R² 0.08, 09-17)、回读覆盖(缺口 0)、快照时刻(Δ = 0)。剩余候选只能靠场所 income 逐笔(I v2 的 I-3/I-4/I-5)分辨; **在只读凭证到手前, 这个 sd 就是现金核账的已知不确定度**。
- 合成夹具金额(5 / 100 / 1100)不是历史实际误报; 归档上 v3→v4 的判词差只有 §2 第一条的两窗。

## 4. 与其它件的关系
L v3 表要等 I v2 取数后重做; 本件不改 L v2 的数字, 只改其读法行(见 `EVAL_FP3_L_unified_table_v2_2026-09-18.md` 追加)。
