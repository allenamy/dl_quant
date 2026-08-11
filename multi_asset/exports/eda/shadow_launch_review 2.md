> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 独立审计) | **状态:** final | **作废条件:** 信号环/P&L/监控口径变更, 或冠军/引擎 canonical 变更

# Live shadow 上线前快速终验 — 0C

**判词: GO (两条非阻断 follow-up)。** paper P&L 算术独立复算逐值吻合; 持仓-引擎对齐 0.9999 是真对齐 (修因=netting warmup, benign, 非 masking); 监控阈值合理。全部为**paper 影子** (无真金), 数值可信 = 可上线。

## 1. paper P&L 双轨口径 — **PASS (独立复算逐值吻合)**
0C 独立重实现 `net = 0.51·(gross − turnover·cost·1e-4)` 跑 102 锚:

| | 0C 复算 | pnl_summary | |
|--|--|--|--|
| A(3腿) cum_net | **0.035548** | 0.035548 | ✓ 逐值 |
| A worst_day | −0.001196 | −0.001196 | ✓ |
| B(4腿) cum_net | **0.035252** | 0.035252 | ✓ |
| B worst_day | −0.000774 | −0.000774 | ✓ |

- **(c2) 构成正确:** A = `funding=0.0` 三腿 (king0.30/s20.10/size0.30, open-month funding 本 feed 拉不到 → 丢); B = 四腿回填 (funding premium-proxy)。与 `_positions(drop_funding_open_month)` 一致, 照 (c2) 裁定。
- **成本/regime 正确:** cost 1.9(calm)/2.9(stress) by BTC rvol>18bps/min; 实测 **max BTC rvol 8.62 « 18 → stress_frac 0.0 正确** (本 17 天窗全 calm, stress-2.9 路径未被触发但代码逻辑正确)。
- **fill 0.51 保守:** `0.51·(gross−cost)` 把未成交 49% 记作 0 (而非持旧仓收益) → **低估 P&L, 保守**, 影子合适。手算 3 锚点算术核对通过 (如 07-01_00: gross−0.002426, turn1.0, net=0.51·(−0.002426−1.0·1.9e-4)=−0.001334 ✓)。
- **⚠️ 报告注记 (非缺陷):** daily_paper_sharpe 21.6 是 **17 天小样本 + 全 calm regime 的乐观读数**, **不可对标引擎 12.2 结构口径 (全史), 更非可部署净值**; summary note 已诚实标"NOT a fund net return / structural-caliber"。

## 2. 持仓 vs 引擎回放对齐 — **PASS (修因 benign)**
- dry-run: 99 锚, live-loop vs engine position corr **median 0.99995 / min 0.9999**, L1 median 0.0086 → PASS。
- **★ 0.9385→0.9999 修因 = netting warmup (benign, 非 masking).** dry-run 代码用 **40-锚 netting 预热** (`warm=frozen_anchors[-(n+40):]`, 注释"slow 24h legs need ~6 anchors to populate"): 旧版无预热 = **冷启动**, 慢-cadence 腿 (S2 24h / funding 8h) 未填充 → 头几锚位置偏离引擎 → 拖 min 到 0.9385。加预热使 netting 状态匹配引擎 (**生产环境本就 warm 运行**) → 0.9999。**是正确的状态初始化, 非掩盖**: 对比码诚实 (全-N-向量 corr, 不丢锚、不松 tol、不排除慢腿)。
- **follow-up (非阻断):** 修因 0B 未成文, 我从 dry-run 码 (warmup 注释+机理) 独立判为 benign; 建议 0B 一句话入档闭环。

## 3. 监控阈值 — **合理 (一条 regime-aware 精化建议)**
- `ICMonitor(window=60, decay_frac=0.5)`: rolling 60 锚 (~10 天) rank-IC, alert 当**满窗**且 roll < 0.5·baseline。decay_alarm_threshold **0.038 = 0.5×0.076** = 半基线 —— 业界标准"信号实质退化"门, 合理。current roll 0.0589, 0 告警。
- **★ 建议 (非阻断): baseline 0.076 是全史口径, 但 2026 是弱-IC regime (引擎 2026 replay rank-IC 0.062)。** live 0.0589 ≈ 2026-regime 水平 (**非退化**, 是 regime), 但"0.0589 vs 0.076"读起来偏悲观。建议 baseline 用 regime/年-appropriate 值 (~0.062 for 2026), 使健康读数反映现实 (0.0589≈0.95×regime-基线); 告警 0.038 (=半全史) 仍留足空间 (=61% of 2026-normal 0.062)。
- window=60 → rolling-IC SE ~0.019 (单窗有噪), 但满窗要求 + 目前 0 告警, 无碍。

## 判词
**GO。** 三项终验全过: P&L 算术独立逐值吻合、对齐 0.9999 真实 (warmup benign)、成本/fill/regime 正确、(c2) 构成正确、监控合理。**两条非阻断 follow-up: (i) 0B 把 warmup 修因入档; (ii) 监控 baseline 改 regime-aware (~0.062 for 2026)。** 均可上线后补, 不阻断。paper 影子无真金, 数值可信 → **上线 GO**。

---
**产物:** `exports/eda/pnl_check.py` (独立复算) · `/tmp/0c_pnl_check.json` · 本 review。
