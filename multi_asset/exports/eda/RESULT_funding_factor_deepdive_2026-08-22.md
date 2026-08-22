> **创建:** 2026-08-22 04:1xZ | **Session:** 6737834a-FF | **状态:** PREREG 冻结(本节 §P 先于任何数字入库; 结果段随后追加) | **作废条件:** 两书 funding 腿任一被重建/换装后由新日期文件取代并互链; 或 09-01 重训改 funding 口径; STATE.md §3 永远优先

# funding 因子深度重建(FF)· 现金流(carry)与价格反应(拥挤后果)拆开检验 —— 在役腿(空高费率收 carry)与宽书腿(多费率 EMA 走高付 carry)是不是同一个因子

**用户质询(原话):** "两个书关于最基础的 funding 腿完全是两种思路, 这是不是暴露了问题? 连基本腿的处理方式都没有收敛, 说明这个因子考虑的过于简单!"

**事实前提(受据 `kcurve_2026-08-21/RESULT_two_book_allocation_2026-08-21.md` §10)**: 在役 funding 腿 = `legs.py SIGNS funding=−1`, rank(funding_ema 修正口径) 取反, 8h 刷新 ⇒ 空高费率名, 精确归因下价格夏普 0.06、carry 收 0.19 bps/锚 @gross2 ⇒ **纯收费腿**; 宽书 fund 腿 = `+f_fund_ema_v1`(墙钟 HL3d, rate×8/iv normfix), 逐锚刷新 + EMA α0.1 ⇒ 多高费率 EMA 名, 价格 +1.38、付 carry 0.62 @gross2, 2022-24 夏普 0.2 / 2025-26 3.15。两腿 ρ −0.115。

---

## §P PREREG(判据先冻结, 2026-08-22 04:1xZ, 写于任何读数之前; 本节 SHA 以 git commit 为证)

### P0 口径(全部装置共用, 不得事后改)
- **收益口径**: 简单持有收益 `expm1(log close→close)`, 1h K 线, **实盘相位 [N, N+4h]**(名义锚 N ∈ {00,04,…,20}Z; 源 = `probe_artifacts/w2b_ret_cube.npz::R_wide` = log(close[N+4h]/close[N]) → expm1); 8h/24h 视界 = 相邻锚 4h 简单收益链乘 −1(缺锚 ⇒ NaN); 1h 视界(仅 140 宇宙)= 训练面板 `Y1[行 N−1h]` → expm1。
- **锚集**: 9,821 锚 2022-01-01 → 2026-06-29(与 W2/PH/SR 同锚族); 逐年 = 2022/23/24/25/26(2026 为 1-6 月)。
- **两个宇宙**: **140** = 在役面板 `MEMBER110[行 N−1h]`(实盘行); **400** = 宽书成员 `wide_fea_hist_meta::members[E_ts==N]` ∩ `qv4h ≥ 2.5e5`(与 `pod_stop_arms_v3` 书级 `sel` 同式)。
- **因子变量(全部信息 ≤ N, 宽书约定 fts ≤ N; 来源 `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz` 行 N, 两宇宙同源)**: `fund_now_nf` = 最近结算费率 × 8/iv(费率水平, 可比量纲); `ema_v1` = 墙钟 HL3d EMA(normfix) = **宽书腿变量**; `ema_v2` = 结算空间 EMA span=round(24/iv)(normfix) = **在役腿变量**(同构复现; 收据 R4 对在役面板通道); `chg` = `fund_now_nf − ema_v1`(费率相对其 EMA 的偏离 = "费率变化", 主定义); `d24_ema_v1` = ema_v1[N] − ema_v1[N−24h](次定义); `ema_v0` = 未归一 HL3d(zoo 原版, 仅作收据)。
- **在役信息集敏感性(仅 140)**: 实盘行 N−1h 的 funding 截至 N−1h ⇒ 对 4h 结算币每锚、8h 结算币在 00/08/16Z 锚比 "≤N" 旧一个结算; 构造 `*_stale` = 若 N 恰为结算时点则取行 N−4h 的值否则取行 N 的值; 报 IC 差。
- **carry(现金流)两口径**: **ex-post 精确** `carry_long[N] = Σ_{结算时点 s∈(N,N+4h]} rate_s`(按各币真实周期; 4h 网格法 = 若 N+4h 为该币结算时点则取 fund_now[行 N+4h]; iv∈{1,2}h 的罕见格按 ×4/iv 近似并计数; 收据 R3 用 140 币逐笔结算时间戳 `xvenue_funding_binance.npz` 对网格法逐格核) ; **ex-ante 代理** `fund_now[N]×4/iv[N]`(W2 归因约定, 决策时已知)。符号: `carry_long` 正 = 多头付出。腿 carry_paid = Σ w·carry_long(正 = 腿付出), **净 = 价格 − carry_paid − 成本**(与 W2 §10 同约定)。
- **成本**: 换手 × 4.137 bps(在役实测, 主)与 × 6.23(上界)。年化 √2190(锚级)。
- **IC** = 逐锚横截面 Spearman(因子按腿方向取号, 价格简单收益); 8h/24h 视界的 t 用 n_eff = n/2, n/6(重叠保守)。

### P1 装置 A(十分位 × regime; 两宇宙; 不做择时规则)
- 排序变量 ∈ {fund_now_nf, ema_v1, ema_v2, chg, d24_ema_v1}; 逐锚按宇宙内有限值分 10 等分; 报每分位 **价格**简单收益均值(1h/4h/8h/24h)与 **carry_long**(精确, 4h 窗)均值、**含 carry 总收益**(多头口径 = 价格 − carry_long); D10−D1 价差、carry 差、总差; 逐年 + 合并。
- 条件变量(逐锚状态, 全部 ≤N): BTC 7 日收益符号(`f_mom_7d[BTC]`); 全市场 7 日动量(宇宙中位 `f_mom_7d`)三分位; 费率水平 regime(宇宙中位 `ema_v1`)三分位; OI 24h 变化(140, `wide_metrics_ch::d_oi_24h` 宇宙中位)三分位; basis(140, `basis_premium_1h::PREM` 行 N−1h)逐名三分位(双排序)与 basis⟂funding 残差十分位。三分位阈值 = 全样本分位(描述性条件均值, 非择时; 事先声明)。
- **读法(冻结)**: "价格反应符号随 regime 翻转" 成立 ⇔ 某条件变量下 D10−D1 价差(4h 或 8h)在不同桶内**符号相反且两桶各自 |t|≥2**; 否则只记"幅度变化"。

### P2 装置 B(两腿同口径同宇宙同相位)
- 腿形态(主, 苹果对苹果): 纯 rank 书 `w ∝ rank_centered(score)`, Σ|w|=1, 逐锚刷新; IN: score = −ema_v2; WIDE: score = +ema_v1。次形态 = 各自部署节奏(IN 8h 持有 = 名义 00/08/16Z 刷新; WIDE 权重 EMA α0.1)。
- 逐年: IC(4h 价格)、价格 P&L、carry_paid、成本、净 @4.137 / @6.23、净夏普; 两腿同正年/互斥年; 两腿净额序列 ρ 与价格序列 ρ; 因子层 Spearman(ema_v1, ema_v2)、(fund_now_nf, ema_v1)、(chg, ema_v1) 逐锚均值。
- "同一因子的两个窗口 vs 两个现象" 判读(冻结): ① 若 ρ_xsec(ema_v1, ema_v2) ≥ 0.8 且两腿价格 IC 逐年同号反向(即同一排序两个符号)⇒ **同一因子, 分歧仅在符号/视界**; ② 若 chg 的价格 IC 与 ema_v1 的价格 IC 逐年符号/幅度明显分离(|Δ| ≥ 0.005 且 chg 逐年同号而 level 不同号, 或反之)⇒ **水平与变化是两个现象**; ③ 其他 ⇒ 记"混合", 写明证据。
- 视界拆解: 两腿变量对 1h(140)/4h/8h/24h 价格的 IC 逐年。

### P3 装置 C("收敛"候选, 只首读不裁定; 新腿提案, 走腿录取门, 不是结论)
- **C1 carry 腿(带状态闸)**: 持仓 = IN 纯 rank 书(空高 ema_v2, 收 carry); 闸 = 6 格状态(BTC 7 日符号 × 费率 regime 三分位); 因果: 在锚 N 用 ≤N−24h 的全部历史(扩张窗)算该格内【未闸腿的 价格−carry_paid 总额】均值, ≥60 锚且均值 >0 ⇒ 开(否则该格 <60 锚默认开); 报逐年净、Δ vs 未闸、开闸比例。
- **C2 动量腿**: score = +chg(主) / +d24_ema_v1(次); 纯 rank 书逐锚刷新。
- **S1 初筛(两宇宙)**: king 基线 = 140: `ph_preds::king_p3[行 N−1h]`(在役 king 实盘相位五折 OOS); 400: `slow_pred_hist_oos`(宽 king 逐年扩张 OOS)。ΔIC = IC(0.7·z(king)+0.3·z(cand)) − IC(z(king)) 对 4h 价格; **过 = 逐年均值 ≥ +0.003 且评估年全 ≥ 0**; 附 cand 对 king 残差(逐锚 rank OLS 残差)的 IC。
- **S2 初筛(单腿 sleeve 口径, 非整书 G 族终审)**: 净@4.137 日块自助 CI95 下界 >0 且 净@6.23 均值 ≥0 且 逐年净 >0 ≥4/5 年 且 净夏普 >0。**明确: 这是 sleeve 初筛, 正式 S2 = 加进在役/宽书的 Δ净 G 族(PREREG_leg_admission_v2), 本文不跑。**
- 预写死法: C1/C2 任一 S1 过而 S2 灭于换手 = "排序≠净额"第五例, 照记。

### P4 装置 D(四问 + 三选一, 事后只许在这三项里选)
- 四问: 口径 / 泄漏(全部信息 ≤N; carry 精确口径用的是 (N,N+4h] 内的结算 = 事后现金流, 只用于记账不进入任何决策) / 选择效应(条件变量阈值全样本分位, 已声明; C1 闸因果) / regime(逐年 + 2022-24 vs 2025-26)。
- 三选一: **(甲)** 两种思路互斥且必须二选一 / **(乙)** 两者是同一因子的不同窗口, 可并存(给并存条件) / **(丙)** 因子需要重建(给重建规格: carry 腿与价格反应腿分离的规格)。

### P5 收据(脚本断言, 非口头)
R1 面板/立方体 829 符号逐名对齐; R2 `f_fund_now[140]` 与 xvenue 逐笔 "fts≤N 最近费率" 逐格相等 ≥99%; R3 网格法精确 carry 与 xvenue 逐笔 (N,N+4h] 求和 逐格相等 ≥99%(含 iv 推断); R4 `ema_v2_stale[140]` 与在役训练面板 `CH[:,:,funding_ema][行 N−1h]` corr ≥0.99(在役因子同构 + 信息集同构双验; 不过则 140 宇宙在役变量改用面板通道并标注); R5 `expm1(R_wide)[140]` 与面板 `expm1(Y4[行 N−1h])` maxabs <1e-5; R6 zoo 认证复现: ema_v1 对 4h 价格 IC(400 宇宙 2023-26 合并)与 `zoo_scan.json::f_fund_ema.ic_wide400 +0.0237` 同号同量级(只报不断言, 宇宙定义不同)。

### P6 输入(只读)与输出
输入: jpline `pod_backup_2026-08-21/{wide_panel_4h_hist_v2.npz, wide_fea_hist_meta.npz, slow_pred_hist_oos.npy}`, `probe_artifacts/{w2b_ret_cube.npz, ph_preds_2026-08-22.npz, basis_premium_1h.npz}`, `quant_research_multi_asset/multi_asset/exports/{wide_dl_full_corrfund_causal_v1.npz(仅 Y1/Y4/MEMBER110/CH[funding_ema]), wide_metrics_ch.npz}`, `w3lane/xvenue_funding_binance.npz`; 全部 SHA256 入 JSON。
输出: `devices_2026-08-22/funding_factor_deepdive.py`(SHA256 入 JSON), `devices_2026-08-22/results/funding_factor_deepdive_2026-08-22.json` + `.log`, 本文。不碰 `~/dl_quant_live`, 不调交易 API, 不写训练目录。

---
