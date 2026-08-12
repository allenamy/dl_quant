# champion_fixfunding 第三轨 — funding 量纲修复的样本外验证 (预注册判据)

> **创建:** 2026-07-25 JST | **Session:** multi-asset-v2 (0B) | **状态:** live (随 run_daily 每日跑)
> **作废条件:** 修复版因子被采纳为默认 (届时本轨并入 champion) 或被否决
> ⚠ **判据在见到任何影子数据之前冻结。见到结果后不得修改本文件的判据段。**

## 为什么需要这条轨

funding 因子有一个**结算周期量纲 bug**: `FUND_EMA` 存的是每结算周期费率, 而 4h 与 8h 结算的币共存。相同**年化** carry 的 4h 币, 每周期费率只有一半。引擎对 funding 做截面 rank-centring —— **rank-centring 洗掉个体尺度, 洗不掉组间位移** —— 于是 4h 队列被系统性推到一侧 (实测组间落差 −0.3745 rank 单位)。

修复: `rate × (8 / 该行的 interval_h)`, **逐结算点、EMA 之前**施加。

**但支持修复的证据 (配对 ΔIC t=+7.79, 0C 独立复现) 全部是样本内的。** 我们刚在 challenger 轨上学到这一课: 把冻结面板切片当作确认是循环论证。**样本内证据关不掉样本内缺口** —— 所以修复本身也要有自己的样本外时钟。

## 配置

| 轨 | 权重 | 面板 |
|---|---|---|
| champion | king .30 / s2 .10 / funding .30 / size .30 | `wide_dl_live.npz` (**错版** funding) |
| **champion_fixfunding** | **完全相同** | `wide_dl_live_fundfix.npz` (**修正版**) |

**只换因子, 权重不动** ⇒ 差异可完全归因于修复。与 challenger 轨**正交**:
- champion vs challenger = **权重**问题 (60 天时钟继续走, **不因本轨重置**)
- champion vs champion_fixfunding = **因子修复**问题 (新时钟)

## ★ 预注册判据 (冻结)

**(a) 整书 rank-IC 差** — `criterion_a_book_ic`
> 支持: ΔIC > 0 且 t > 2。反对: ΔIC < 0。

**(b) funding 腿 rank-IC 差** — `criterion_b_funding_leg_ic`
**这是最锐利的一条** —— 修复只动这条腿, 整书的差异被其他三条腿稀释。
> 支持: ΔIC > 0 且 t > 2。反对: ΔIC < 0。

**(c) 压力锚点表现** — `criterion_c_stress_anchors`
BTC rvol > 18bps/min 的锚点上的净值差。
> 检查修复没有把风险挪到尾部 —— 修复后若压力日反而更差, 需要解释。

**(d) 与回测预期同向** — `expected_direction_from_backtest`
回测预期 (纯价格口径): 整书 net Sharpe 12.21→12.37 (+0.16); funding 腿 IC −0.0093→−0.0035 (+0.0058)。0C 含 carry 口径: funding 腿净 +8.48%/yr, solo Sharpe 0.83。
> **影子应与之同向。量级会不同 (样本短且口径不同), 同向即可。反向则要查。**

**裁决**: (a)(b) 同向为正 + (c) 无恶化 + **≥60 个交易日**, 才提请把修正版因子设为默认。

## 口径 (必读)

- **本轨 P&L 是纯价格口径** (`Y4` 是前向价格收益, **carry 不计入**)。funding 腿本质是 carry 收割者, **所以纯价格口径系统性低估它**。0C 的 "+8.48%/yr、solo Sharpe 0.83" 是**含 carry 的完整经济口径**。**两个说法都对, 但绝不可混用 —— 引用时必须标口径。**
- 影子 paper 口径 (maker-fill 0.51 / 1.9·2.9bps), **不是基金净值**。两轨共用同一执行模型 ⇒ **有意义的是差值**。

## 纪律

- **加法实现**: 独立模块 + `run_daily.sh` 非致命步骤, 失败不影响 champion 主链, 也不影响 challenger 轨。
- **不改 canonical, 不改 pilot 默认权重, 不改默认因子版本** —— 修正版因子在本轨证明自己之前不上位。
- ⚠ **因子版本不可混用**: pilot 协议 §5 的常数是版本相关的。任何引用引擎数字的地方必须声明跑的是哪版因子。

## 已知遗留 caveat (lead + 0C 裁定: 不重训)

DL 的 `YR` 残差目标是对**错版** funding 残差化的 (`build_wide_dl.py::BASELINE` 含 `funding_ema`)。**不产生前视或泄漏** —— 只是 king/s2 的 "incremental-over-funding" 严格说是对一个略有偏差版本的增量。**已列入下次重训周期待办**, 修好的面板列已落盘 (`wide_dl_full_fundfix.npz`) 供未来重训使用。

## 产物

```
exports/live/fixfunding/
  positions/positions_YYYYMMDD_HH.json   修正版因子下的仓位 (带 factor_version 标记)
  pnl_daily.csv                          两轨逐日净值 + 累计
  compare.json                           四条判据的全部数字
  daily_report.md                        当日一页纸
```
