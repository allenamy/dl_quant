# 引擎 v1 复核 (funding z→rank + isotonic 接入 P&L) — 0C 独立复核

> **创建:** 2026-07-15 JST | **Session:** fable multi-asset-v2 (0C) | **状态:** final | **作废条件:** 引擎组件/权重变更
> 复核对象: engine v1 (`signal_chain.py`/`netting.py`/`replay_fullhist.py`, funding_mode=rank + shaping 接入 P&L)。独立重算 `engine_v1_review.py`(自实现 rank+L1+cadence 净额+walk-forward isotonic+cap+renorm P&L; 并用 0B 自身 run_replay 交叉确认)。

## 判词: **两改动**判然不同 —— **rank 切换 = 真·结构 Sharpe 增益, 加冕; isotonic ≠ +1.3, 实为 −1.3(0B 归因错误), 是部署-sizing 层非 alpha 层。canonical 应报 rank+cap ≈ 12.2(结构口径), 不是 rank+iso 10.84。**

## Task 1 — funding z→rank

**(a) 2×2 复算:** 复现。rank C5on==C5off **逐格 bit-identical**(C5 在 rank 下完全 inert: winsor±4 对 rank∈[−1,1] no-op; name_cap 0.15 对 rank-L1 max 0.049 no-op; disp-gate 被 L1-renorm 抵消)。单名集中 0.049(z 是 0.49), FTX 尾天然 1.0, 2022 分散尖峰年 6.34/6.92(z)→9.64(rank)。**rank 切换是真实修复。**

**(b) rank-funding 是否 = book_assembly megacap-raw+rank?→ 否, 不是回归我原口径。** engine rank-funding 腿 vs book_assembly megacap-raw funding 腿**日收益 corr 仅 0.213**(n=1641)。二者不同因子: engine=funding_ema(24h-EMA)110-宽, book_assembly=raw funding 14-megacap; rank 操作不改底层信号/宇宙。**故 rank 的"上移"是对引擎自身 funding_ema 腿的真实改进**(把 z+L1 的离群集中 0.49 换成 rank 的天然有界 0.049), **不是修 bug/revert 到我口径 —— 是新东西, 且比 C5-winsor 更干净**(rank-noshape 12.33 > z-C5on-shaping 9.24, 因为 rank 全有界, winsor 仍留残余集中)。

**(c) 腿间 corr / 尾部共险在 rank 版是否成立?→ 成立。** rank engine 四腿: 全样本平均两两 corr **−0.023**; 危机日(BTC 最差 5%)平均 corr **−0.117**, 组合当日均值 **+0.52**(正), 组合正天占比 0.84; 最差 10%: corr −0.098, 组合 +0.44。**crash-beneficiary 属性在 rank 版完全保留**(与我 tail_corisk 结论一致, 尽管那是另一面板)。

## Task 2 — isotonic 接入 P&L ★ 关键更正

**walk-forward 因果性: 干净, 无前视。** calib[y] fit 于 year y−1 anchors, 应用于 year y(net.run 逐年 swap); 首年 2022 → prior 2021 无 anchors → identity。已核实。

**★★ 但 isotonic 不是 +1.3, 是 −1.3。** 消融(我重算 + 0B 自身 run_replay 双证):

| rank 配置 | avg net Sharpe | 逐年 |
|---|---|---|
| rank no-shape (无 iso 无 cap) | **12.33** | [9.27/11.97/12.79/16.09/11.54] |
| rank cap-only (无 iso) | 12.21 | [9.64/11.77/12.55/16.04/11.05] |
| **rank iso-WF + cap (=出货 canonical)** | **10.84** | [9.64/9.98/10.93/15.57/8.07] |
| rank iso-ORACLE(同年 fit, 前视上界) | 11.69 | — |

- **isotonic(walk-forward) = −1.27**(cap-only 12.21 → iso-WF 10.94 in my recompute; 0B run_replay: rank shaping-OFF 12.33 → ON 10.84 = −1.49, 其中 cap −0.12 iso −1.27)。**shaping 在 rank 下净负。**
- **甚至前视-ORACLE isotonic(11.69)< cap-only(12.21)** → 不是 walk-forward 漂移问题, **isotonic 重塑本身净负**(不是 val-fitting; 反向 —— 若是 val-fit, in-sample oracle 应 inflate, 结果 oracle 也输 cap-only)。
- **机制:** isotonic 阶梯函数在稀疏尾部饱和 → **压平高信念尾仓**(最大 per-unit alpha 处)→ 砍 numerator 多于 denominator(日波动几乎不变 0.0033→0.0032, 但均值降)→ Sharpe 降。**rank-IC 近不变(0.0746→0.0714, 仅 tie-flatten)→ 不是丢信号, 是 mis-sizing。**
- **★ 0B "+1.3" 的来源 = 误归因:** 那 +1.3 是 **z-mode 的 99% pos-CAP 削 funding z+L1 离群集中**(z shaping-OFF 5.31 → ON 9.24 = +3.93, 主要是 cap 干 C5 的活)。在 rank mode(离群已被 rank 消除)cap 近乎免费(−0.12), isotonic 净负。**"+1.3 isotonic" 应更正为 "z-mode-cap 削离群 +3.9(rank 已替代), isotonic 本身 −1.3"。**

## Task 3 — canonical 裁定

- **★ 加冕 rank 切换(真实结构增益)。结构口径 canonical headline = rank + cap-only ≈ 12.2**(逐年 [9.64/11.77/12.55/16.04/11.05]; 或 no-shape 12.33)。**不是 rank+iso 10.84 —— 出货管线因 isotonic 白丢 ~1.3-1.5 Sharpe。**
- **不加冕 isotonic 为 +Sharpe。** 更正叙事: **isotonic 是部署 magnitude-校准层(Kelly/net-cost 门需要真实 E[bps]), 代价 −1.3 结构 Sharpe; 其价值在部署/净成本口径(结构表不度量), 不在结构 Sharpe。** 若为部署保留 isotonic, 把 10.84 作"可部署-已校准"变体单列, 与 12.2"结构-信号"headline 区分, 明示 −1.3 代价。
- **"重度依赖 C5" 正式改写为:** **"rank 加权下 C5 完全 inert(winsor/name_cap/disp-gate 三件套在 rank 上全 no-op 或被 L1-renorm 抵消), 保留为 z-mode 保险"。** 确认。
- **定位判词不变:** 12.2 仍是**结构口径**(日频×√365, 市场中性, 仅 1.9bps 显性, 无 maker-fill 栈), 信号质量上界非部署净值; 部署要叠 maker-fill 折损。

## Task 4 — disp-gate 零作用(归档 C5-owner 待办)

确认 0B 发现: **dispersion 门在 rank(且 z)下对 P&L 零作用 —— 因为它把整条 funding 腿乘 0.3× 均匀 shrink, 而下游 `_l1` 归一化把这个标量抵消掉了。** 要让它咬合, 必须作用于 **book 权重 / 总 exposure**(在 combine 之后、renorm 之前), 而非 L1-归一化的腿内。归档为 C5-owner 待办(当前 122 天 gate 计数只是日志, 无 P&L 效果)。

## 一句话给汇报

rank 切换真金(7.86→~12.2, 修 funding_ema 离群集中, 非回归旧口径, 尾部属性保留); isotonic 不是收益是 −1.3 代价的部署-sizing 层(0B 的 +1.3 是 z-mode-cap 的误记); **建议 canonical 报 rank+cap ≈ 12.2 结构口径, isotonic 单列为可部署变体 10.84**; C5 rank 下 inert(z 保险); disp-gate 需改作用于 book 权重。
