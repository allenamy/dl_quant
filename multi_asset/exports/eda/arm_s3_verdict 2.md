# ARM-S3 (168h 周级) — 0C 独立评分 verdict

> **创建:** 2026-07-14 JST | **Session:** fable multi-asset-v2 (0C scorer) | **状态:** final | **作废条件:** 若 S3 以不同频率/持仓层重做（把周级信号铺到日频以提 breadth）则重评
> 打分对象: `train/wideA_s3_y168_c1` (panel md5 `234bd318`, ts 与 king/S2 逐字节对齐, fold 分数 test-rows-only 严格 OOS, 5 fold te=2022-2026, ~52 周锚点/年 + 25 for 2026H1)

## 判词: **存档 S3 — 关 horizon 阶梯**（信号真实, 但不进书）

信号侧两道门全过（king-正交 + S2-正交增量都显著、五年全正）; **决定性的 book 门 (gate c) 未过** —— 周级频率让独立 Sharpe 仅 0.79（gross 1.16），无法对已接受的四腿书产生统计显著贡献。

## 门牌 scorecard

| 门 | 判据 | 结果 | 结论 |
|---|---|---|---|
| a (king-正交增量) | ≥+0.003 sign-consistent + CI 排除 0 | +0.0208 CI[0.0065,0.0353] 5/5 年正 | **PASS** |
| a' (S2-正交增量, 冗余检) | 同上 | +0.0149 CI[0.0015,0.0286] 5/5 年正 | **PASS** |
| b (pred-corr) | < 0.7 | king 0.098 / S2 0.152 | **PASS** |
| c (book margin, DECIDER) | 装配显著改善四腿书 | +0.06 Sh, bootstrap CI 含 0（各权重）; w>0.10 转负 | **FAIL** |
| #18 raw 专项 | fold0 raw−0.0084 是否危险 | metric-plumbing 假象, 真实 raw rank-IC +0.022 全年正 | **benign** |

## 1. #18 raw 专项 —— 判定: benign, 非危险信号（非 zoo-momentum 吃 raw）

`ensemble_raw_ic = −0.0084`(fold0) 是 harness 内部指标, **精确复现后坍缩到只有 18/52 周锚点**:
- 根因 = base-mask 退化: baseline-未覆盖资产(Yraw-valid 但 YR-NaN, 多为新/薄币, 34 个 asset-slot/年)携带 NaN 模型分数 → 触发 `_ensemble_ic` 的 `np.isfinite(col).all()` 全-有限 head 过滤 → 34/52 周被整行丢弃 → −0.0084 是 18 周非代表性子集的产物。
- 在完整 52 锚点的**可交易残差宇宙**(YR-valid): 2022 raw rank-IC = **+0.0223**(≈ resid +0.0234), Pearson raw +0.0175 —— 全正。
- corr(YR,Yraw) = 0.83–0.88(rank/Pearson) → 残差目标与 raw 收益高度同序; **S3 并非活在一层薄正交残差里**。"zoo momentum 吃掉 raw 分量"这个假设只弱成立(残差化保留了绝大部分排序)。
- Raw rank-IC 五年 [+.022/+.028/+.020/+.025/+.049] 全正、sign-consistent。无反转、无危险。

**给同门的话:** 若只看 harness 头条 `ensemble_raw_ic`, 会误以为周级 2022 信号反号。三路交叉验证(rank/Pearson/YR-限定 base)证明这是指标管道假象, 交易口径 raw 全年为正。这是本臂最需要审计的一处 —— 已审清。

## 2. 小样本统计力（~52 周锚/年）

Pooled per-ts + day-block bootstrap(3000×, 按周分块):
- king-正交增量 **+0.0208**, 95% CI **[0.0065, 0.0353]** —— 排除 0
- S2-正交增量 **+0.0149**, 95% CI **[0.0015, 0.0286]** —— 排除 0（边际但过）
两者都扛过诚实小样本门, 没被 52 锚点噪声骗。

## 3. king / S2 冗余（S3 与 S2 同为慢因子, 冗余风险在 S2）

- vs king: 增量 +0.021, pred-corr **0.098** —— 与 king 近乎正交(不同 horizon)。
- vs S2: 增量 +0.015, pred-corr **0.152** —— **冗余担忧未兑现**; S3 在信号层对 S2 有净增量。慢因子 ≠ 互相冗余。

## 4. 五腿分散 —— DECIDER

- S3 独立**周频 Sharpe: 0.79 净 / 1.16 GROSS(cost=0)** vs 四腿书 5.90（同周口径 √52）。
- 低 Sharpe **不是成本问题**(gross 仍 1.16), 而是 **breadth 饥饿**: 52 注/年 × IC 0.025 → Sharpe 天花板 ~1。周级换手 = 全书最便宜执行(换手 ~1/周, 正是它宣称的优势), 但同一低频把 Sharpe 也压死了。
- improve-rule Ss3 > ρ·S4 平凡为真(ρ −0.013≈0, 任何正 Sharpe 的不相关腿都过) —— 但当一腿 Sharpe 比书低 7× 时, 这个比值门无信息量。
- 混合增益: w0.05 **+0.059** / w0.10 **+0.049**(两者 bootstrap CI 含 0 = 不显著) / w0.15 −0.045 / w0.20 −0.232(稀释)。
- 两两 corr 全 ~0(s3↔king 0.02, s3↔s2 0.046, s3↔size 0.048) —— 分散是真的, 但 sleeve 太弱, 不 material。

## 判词 + horizon 阶梯收官

**存档 S3。** Horizon 阶梯完成, 呈现清晰的 Sharpe 甜点结构:

| 臂 | horizon | 信号(king-正交增量) | 独立 Sharpe | 执行 | 判 |
|---|---|---|---|---|---|
| S1 | 4h | ~0(king 已饱和该 horizon) | — | 同 king | 存档 |
| **S2** | **24h** | **+0.033** | **高(24h breadth)** | 中 | **进书 (w~0.10)** |
| S3 | 168h | +0.021 king-正交(真实, 双弱年正) | 0.79 净 / 1.16 gross | 最便宜(周级) | **存档** |

**核心 lesson:** horizon 阶梯有 Sharpe 甜点在 24h。**更快(4h)= king 已在那; 更慢(168h)= 每年注数太少, 无法把真实 IC 转成可入书的 Sharpe。便宜执行 ≠ book 价值; 是 breadth(频率×截面)把 IC 转成 Sharpe。** S3 的信号是真的(gate a/b 强过), 输在经济学不在统计学。部署书维持 4 腿(funding / king / size / S2-24h)。

若日后想榨出这层周级 alpha: 唯一路径是把 168h 信号铺到日频持仓层(每日重叠加权、非周级离散重平衡)以恢复 breadth —— 但那是执行工程, 不是本臂已证的东西。
