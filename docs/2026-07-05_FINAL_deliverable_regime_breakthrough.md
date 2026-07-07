> **创建:** 2026-07-05 18:10 UTC | **Session:** fable-regime-breakthrough (Fable 5) | **状态:** final | **作废条件:** 被后续 breakthrough 里程碑或盘外数据/事件时间采样的新证据取代
> **交叉引用:** `docs/2026-07-02_fable_regime_breakthrough.md`(滚动全记录) · `CLAUDE.md`(IC/β 铁律已固化) · memory `taker_tradeability_y600_2026_07_05` · `single_asset_y600_concluded_2026_05_20`(口径已修正)

# BTCUSDT perp y_600 — Regime Breakthrough 最终交付 (2026-07-05)

## 0. 一句话结论

**目标(全 regime per-month Pearson ≥0.08)在盘上数据里不可达 —— 已用样本外证据 + DL 测试穷尽验证。最佳可部署单模型 = Run1(bugfix),它真实、强显著、经济上明显胜生产,但是一个 maker-only 信号(仅好费率档 ≤0.76 bps/side),非 taker-可交易。全程无泄漏,关键结论皆双人独立验证。**

---

## 1. 模型侧结论

### 1.1 最佳单模型 = Run1 (bugfix)
- **Run1 = dual-book REG_arch 修两个 bug(regime-FiLM 吃 post-RevIN+batch-z / mask 泄漏)+ 严格无泄漏 walk-forward,不加 state/basis/新架构。**
- 7-月样本外 deploy 均值 **+0.0339**;穷尽验证下**没有任何更复杂方案稳健胜它**。

### 1.2 穷尽的路径(全部样本外证伪)
| 路径 | 结果 |
|---|---|
| 架构容量(深/宽/长上下文/multi-scale) | 6+ 次崩溃/阴性 |
| 因果 regime 路由(positioning tt-sign) | 样本外 +0.0019 vs always-Run1 = 不挣钱 |
| state/gain(Run2)、LoRA 换弹法 | 帮去杠杆/伤强月;样本外不稳健胜 Run1 |
| rank 输入归一(combo) | body-IC 转负(−0.024),叠 state 有害 |
| basis-dynamics + RevIN-skip(DL 重训) | drift +0.01 噪声地板 / 强月重挫 −0.037,净负,关闭 |
| 目标改造(align/aux)、选择器 | 干扰律/样本外缩水 |

### 1.3 核心机理事实
- **"帮难月"与"保强月峰值"是数据里不可调和的 trade-off** —— 没有冻结单模型处处最优(穷尽架构/特征/目标/优化四路)。
- **oracle 上界 +0.0629 vs always-Run1 +0.0479 = +0.015 真实可利用月间方差,但因果 tt-sign 路由只捕获 ~5%**(H4 月度概念漂移,静态符号跟不上逐月最优)。剩余上升空间在"更好的因果 regime 选择信号",而非更好的模型 —— 而那个信号可能不存在于可观测量里。
- 大多数月 cd 0.02-0.06,只强月近 0.08 → **0.08-全 regime 未达成。**

---

## 2. 可交易性结论(净成本回测,引擎+数据双人审计 CLEAN)

### 2.1 最终定论
**单资产 y_600 = maker-only 信号,且仅好费率档(maker ≤0.76 bps/side,高 VIP/返佣):**
- ❌ **非 taker-可交易** —— 无尾部截断(top-10/5/2/1/0.5%)过 taker 1.7 per-side;肥尾在 pooled/强月/drift 全 net-负;"看似正"的格子(cost-aware +1725、短尾 top-1%)全是 bootstrap 跨 0 / leave-one-month 死 / 换模型翻号的海市蜃楼。
- ❌ **非零售 maker(2 bps)** —— 水下 ~1.24 bps/side。
- ✅ **好费率档 maker 可交易**(break-even 0.76 bps/side)。

### 2.2 Run1 vs 生产(经济学证明 Run1 是真提升)
| | Run1 | 生产 |
|---|---|---|
| 盈亏平衡单边成本 | **0.760 bps** | 0.424 bps |
| maker@0.5 net | **+2117(正)** | −831(负) |
| gross 显著性 | z=8.62(强) | z=2.03(边际) |
- **Run1 扛成本高 ~80%、跨过 maker-可交易门槛,生产没跨。** 逐月强月最肥、drift 负,同 regime 指纹。

### 2.3 milestone 数修正(重要)
`single_asset_y600_concluded_2026_05_20` 的 **retail-maker Sharpe 4.4 / pure-taker 2.8 是灌水构造** = 强月 fold + clip±5σ + EMA-demean + 有利年化 + 低费。引擎只在强月 clip 口径复现(2025-10 clip taker Sharpe 6.17;raw 肥尾 net −62)。诚实 pooled 口径远更 sober。

---

## 3. 方法论修正(已固化到 CLAUDE.md)

### 3.1 IC 是 alpha,β 是量纲(核心铁律)
- **β = r·(σy/σŷ)**:β 是 IC 乘纯尺度比 → ŷ×c 则 IC 不变、β→β/c。**β 水平可任意 rescale,几乎不由模型质量决定。**
- **禁止**把 β 水平当质量门 / 把"β 改善"当 alpha。β 合法角色仅:塌缩监视(真守卫是 σŷ/σy)+ 跨-regime 稳定性(看方差非均值)。部署幅度用事后校准层,不训进模型(lambda_beta_calib 实测反向)。

### 3.2 deploy-demean 低估持续方向 alpha
- 1h-demean 预测会:① 把去 bias 折进 alpha 指标(错)② 强制多空对称,洗掉 H1 短尾。对单资产方向 taker,**去 bias 应在决策阈值层(慢中心 c),alpha 用 raw IC,策略用净成本回测。**
- 实证:deploy-demean 给 Run1-vs-生产 +0.0047,真实回测给 +0.336 bps/side → **cd +0.0137 侧更近经济真相,deploy 严重低估。**

---

## 4. 唯一正交真赢:日内自评部署层

- 用模型自身**上午的实际命中**因果地调下午仓位(同日 split;连续 trailing 形态证伪 = 同日效应跨隔夜洗没)。
- drift 下午 IC ~2.1×,自门控(近15d 均IC<0.05 且 近30d 上午→下午 rho>0)保强月零损,**全天 deploy +~0.009,叠加在任一模型之上。**

---

## 5. 已穷尽 vs 诚实前沿(下一步选项)

**已穷尽(有机理原因,勿再碰):** 架构容量、长上下文、加通道、特征族线性门槛、regime 目标改造、选择器、单模型统一、rank body、basis(DL 测过)、因果路由。

**诚实前沿(未验证,需用户拍板 + 大投入):**
1. **事件时间采样(volume/event bars)** —— 机理对症(信号住在成交爆发时刻,墙钟采样稀释),但需重建整条缓存管线。
2. **盘外正交数据**(更细 liquidations / 更高频 OI)—— 历史分析多次指向"0.06+ 需盘外数据"。

**注:** 两者都非"必胜",是真投入的赌注;on-disk 的 IC 杠杆已穷尽。

---

## 5b. Run1 生产预测 + 基础模型成绩单(2026-07-06, 双人验证)

**导出**: `exports/run1_production_preds_from_2025_08.csv`(130,698 行, 2025-08-10 起 walk-forward OOS 拼接, raw-y 口径)。**报告**: `docs/2026-07-06_run1_production_export_metrics.md`。
**pooled 成绩单(raw-y, per-day-CLEAN, Run1 vs 生产)**: Pearson cd **+0.0487 vs +0.0398(+22%, 赢 7/10 月)** | Spearman cd **+0.0572 vs +0.0391(+46%)** | DA|y|>σ 0.516 vs 0.510 | DA top-20%尾 0.536 vs 0.531 | corr-R² 0.0024 vs 0.0016 | bin-mono Spearman +0.552(4/9 上升步, regime-依赖) | long-short bias 近零。
**诚实**: R²~0(信号在 rank/sign 非方差消减, R²<1% 本就如此); DA 仅略高掷硬币(弱信号); DENSE-Pearson 生产略领先 = Run1 alpha 日内集中(跨日 level 稀释 pooled P, Spearman 反转) = 与 maker-可交易一致。
**★口径校正(2026-07-06, 0B 核对)**: 本成绩单 = **raw-y(诚实)**。之前 gate/轨迹表的 cd 是 **clipped(±5σ)口径,系统性压低绝对值尤其 drift 月**(2026-01 raw-y 0.0253 vs clipped 0.0175)。**arm-vs-arm ΔP 不受影响(两臂同 clip, 相消)→ 所有 gate 判定(basis/rank/combo/路由)仍成立; 仅绝对水平 raw-y 上修**。净: Run1 真实 OOS IC 比 clipped 数略高(尤其 drift), 强化(非削弱)"ship Run1"。唯一 caveat: 2025-08/09 仅 30%/26% raw-y 覆盖(生产 CSV 限制), 逐月指标在子集上。

## 6. 交付物清单
- 模型: `configs/d1gate/d1_*_run1.json`(Run1 bugfix,10 月 walk-forward preds 在 `experiments/d1gate/d1_*_run1/`)。
- 回测: `multi_asset/eval/taker_backtest.py`(引擎+battery,双人审计 CLEAN) + `tail_regime_split.py` + `exports/run1_backtest.csv`(共同-y)。
- 部署层: `multi_asset/eval/intraday_scaler.py`(日内自评,自门控)。
- 全记录: `docs/2026-07-02_fable_regime_breakthrough.md`。

## 7. 待用户决定
- **2025-H1 回补(~17h GPU)**: 把最终表扩到全 ~17 月 —— 只锐化"always-Run2 ≤ always-Run1",不改定论。默认**跳过**(HELD 可恢复)。
- **下一博**: 事件时间采样 / 盘外数据 —— 需拍板。
