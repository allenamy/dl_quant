# PREREG · TRACK F · regime-conditional book (frozen BEFORE any per-regime number is seen)

> **创建:** 2026-09-11 | **Session:** session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 判据冻结, 数字未看 | **作废条件:** 书层装置 (pod_trackF_arms.py) 被证伪, 或 slow_pred_pinned 被证明非 walk-forward

## 0. 装置 (frozen)
`pod_trackF_arms.py` @pod2 — 书层 (不是分数层, 不是腿收益层)。每锚输出 (ts, gross_bps, carry_bps, cost_bps, gross_exp, turnover)。
net = gross - carry - cost。基底逐字继承 `pod_export_bundle_v3.py` L120-160 结构 (= `axisLEG_pod_book_track.py` 已复核过的同一装置)。
口径: y4 = Σ 5m 简单收益 (E-0904-F); carry = Σ sm·f_fund_now·(4/iv); cost = 三档 maker/taker 混合。
样本: king 腿仅 2024+ 有 OOS 预测 (slow_pred_pinned 逐年 walk-forward: 训 <YV, 预测 YV)。**主样本 = 2024-01 .. 2026-08。**

## 1. Regime 规则 (ex-ante, 参数冻结)
每个 regime 变量 v 在锚 t 的状态 = **v 在 t 之前 30 锚的均值**, 相对 **t 之前 4380 锚 (2年) 滚动分布** 的分位 p_t。
- 严格 trailing: 只用 ≤ t-1 的数据。窗口 30 / 4380 **直接沿用已部署 sigma_ladder 的预注册值** (PREREG_deploy_sigma_ladder_2026-09-04), 不调参。
- 分档: p<1/3 = LOW, 1/3≤p<2/3 = MID, p≥2/3 = HIGH。三档, 无自由阈值。
- 候选变量 (预先列全, 不事后增补): `fund_sd` (σ_fund), `fund_fracneg`, `disp_bps` (横截面收益离散), `comov` (|xs_mean|/disp, 对 BTC 的同涨同跌), `breadth_pos`, `turnover` (宇宙换手), `share_new90`, `realvol` (30 锚 disp 的均值), `vol_ts` (30锚disp均值 / 180锚disp均值, 波动期限结构)。

## 2. 军械库 (arms, 冻结)
flat / king / rev24 / fund / carry(=-xz(f_fund_now), 收 carry 的反向腿) / eq3 / kr(king+rev24) / kf / base(在役 msharpe900) / msh60 / msh190 / base_ftrim / king_ftrim / carry_ftrim / base_carryadj。
**每条 arm 的机制必须在报告中一句话写清; 无机制的 arm 不录取。**

## 3. 判据 (GATE, 冻结于看数字之前)
**主判据 (regime-conditional book 录取门):**
- G1 **样本外**: regime→arm 的映射只能用 t 之前的数据估计 (expanding walk-forward, 每月重估一次)。报告 OOS 与 IS 分开且并列。
- G2 **OOS 跨 regime Sharpe**: 2024-01..2026-08 全样本 OOS net Sharpe ≥ 2.0 且其 SE (=√(2190/N)) 被明写; 若 <3.0 必须明写"未达用户目标"。
- G3 **最坏 regime**: OOS 下每个 regime 档内 Sharpe ≥ 0 (点估计), 且最坏档 Sharpe ≥ base arm 同档 Sharpe。
- G4 **逐年同号**: 2024 / 2025 / 2026 三年 OOS net 均为正。
- G5 **换手成本已计价**: 切换 arm 产生的额外换手已在 cost_bps 中按同一三档成本模型计入; 不允许只报毛额。
- G6 **复杂度预算**: 规则参数数 ≤ 3 (1 个变量 + 2 个固定分位阈值 1/3, 2/3 已冻结 ⇒ 实际自由参数 = 1 个变量的选择)。**从 9 个候选变量里挑 1 个 = 9 重检验**, 报告必须给 Bonferroni/多重检验声明。
- G7 **反例检验**: 必须报告 regime 规则在"该 regime 里 base arm 本来是赢家"的子样本上是否把 alpha 关掉了。

**若 G2 的 OOS 跨 regime Sharpe < 3.0, 结论写"跨 regime Sharpe 上限 = X ± SE, 未达 3.0", 不得改判据。**

## 4. 泄漏分析 (预先声明必须回答的)
- L1 king 预测 slow_pred_pinned 是逐年 walk-forward (训 <YV) ⇒ 2024/2025/2026 折 OOS。**但特征面板 wide_fea_v2ext 的构建本身是否含前视, 本轨不重验, 引用既有受据 (panel_lookahead_betaadj_ret24 已知缺陷)。**
- L2 regime 分位用滚动 2 年 trailing 窗 ⇒ 无前视; 但前 4380 锚 (2022-01..2023-12) 无法给出分位 ⇒ 主样本 2024+ 恰好有完整参照窗。
- L3 arm 选择用 expanding 窗 ⇒ 无前视; 但**变量选择 (9 选 1) 是在全样本上看的 ⇒ 这一层是 IS**, 必须明写并用 hold-out 年 (2026) 单独报。
- L4 universe/members 冻结与否影响 turnover/share_new90 ⇒ 用同一 meta 计算, 不跨 lineage 拼。

## 5. 最廉价的证伪实验
把 regime 变量替换成**随机排列的同分布序列** (block-permute, 保留自相关), 重跑整条 walk-forward。若随机 regime 给出的 OOS Sharpe 分布覆盖了真 regime 的值, 则该 regime 条件化没有信息。**n=200 次 permutation, 报 p 值。**
