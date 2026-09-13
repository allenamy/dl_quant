> **创建:** 2026-09-13 ~09:55Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T8) | **状态:** 预注册, 冻结先于任何 T8 结果数字; sha256 与 UTC 冻结时刻记入 `receipts/PREREG_FREEZE_sha.txt`, 每个装置运行前断言 | **作废条件:** §2 任一输入文件 sha 变化; §7.1 任一前置门失败且无法以先于结果数字的定义性 AMENDMENT 补救; lead 或用户改问题
> **纲领:** `../PROGRAM_uplift_r2_2026-09-13.md` AMENDMENT 6 | **口径钉:** `uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`(记账元 y4 = Π(1+r)−1 RAW; 禁从 5m 缓存 `ret5` 通道重算收益, r18 RESULT §8 / E-0908-B) | **只读:** 全部既有研究产物只读; 本线不读 `~/wide_shadow` / `~/dl_quant_live`; 不调任何交易所 API | **本线不提出任何书行为改动**

# PREREG · T8 · 书层收益可感知门(多变量)

## §0 问题与本文冻结什么

**问题**: 锚 t 时可观测的状态, 能否在样本外预测 A0 回放书**下一个 4h 区间**的收益(净额)及其三分量(多头价格、空头价格、carry)的方向与幅度?
不能 ⇒ 建立在这组状态上的任何监控 / 调节层都是装饰。能 ⇒ 只获得为「非对称调节层」另立 S2 预注册的资格; 本线本身不产生书行为提案。

**冻结**: 目标与窗口与折(§2–§3)、特征集(§4, 24 列, 不增删)、模型家族与预处理(§5, 无搜索)、统计量(§6)、前置门与守卫(§7)、读法(§8)、事先声明的限制(§9)、装置与运行纪律(§10)。
**不冻结**: 任何结果数字。本文出现的数值只有阈值、窗口端点、文件 sha, 以及 §4.4 中**不涉任何收益或书**的数据覆盖计数(冻结前唯一算过的量)。

## §1 已看过的相关数字(申报: 它们可能影响了设计, 不能当作未见)

1. `adaptive_turnover_family_closed`(2026-08-11): corr(条件量_t, 当锚书毛) 离散度 +0.014 / 位移需求 +0.026 / 波动 +0.003(|corr| ≥ 0.03 门全不过); 波动对 |毛| +0.254; trailing-IC 择时 AR1 −0.13。
2. `vol_predictable_but_acting_loses`(2026-08-20): 目标「书未来 24h 净额 ≤ 10 分位」上 25 特征 LGBM 零增量, 仅 σ 排序 AUC 0.630; 波动目标化净额 −22%, 夏普 1.38 → 1.15。
3. `book_is_dominance_premium`(2026-08-21, 08-21 在役书, 非 v4 A0): 净额对同锚等权山寨−BTC 价差 β −0.249、r −0.767, 逐年 −0.22 ~ −0.30; 暴露约占收益 78%; 残差 alpha 0.29 bps/锚; 山寨季 7 日指数 lag42 自相关 −0.04; **AS_{t−1} → 下锚书收益 4/5 年为正**; 叠加对冲 h=0.25β 夏普 1.48 → 1.40。
4. `giveback_baserate_and_tail_levers_2026_09_06`: 大亏锚 70% 为空头侧被普涨挤压(空头侧均 −53 vs 多头 −10 bps, 市场等权 +41)。
5. `allweather_trackC_age_tilt_voltarget_refuted_2026_09_05`: 只降不升波动目标最差年夏普 −0.02 ~ −0.34。
6. `reweighting_cannot_close_the_sharpe_gap_2026_09_12`: SE(年化夏普) = √(2190/n) 算术。
7. T1 RESULT: 六个状态(DISP24 / BREADTH72 / BTC72 / SIGF / MUF / PUMP72)五分位 × 单元描述表; 「BREADTH72 第 4 五分位 × 空头价格」「BTC72 第 4 五分位 × 空头价格」三台仪器 CI 不含 0(数百格中挑出, 线索); 2026-08 落差在状态内而非状态移动; 近邻类比 1000 锚 g +3.58; W_ALPHA C0_s42 g +0.6342 / 价格 +1.2813 / carry +0.4797 / 成本 +0.1675; 逐月表 2025-01..2026-08。
8. r18 RESULT §4: W_FULL 逐年 g(C0 s42)2022 +0.005 / 2023 −0.649 / 2024 +0.486 / 2025 +0.677 / 2026 +3.091。
9. T2(κ* 路径; σ 臂时点敏感, 执行 24 分钟延迟下不可执行)、T5c(九月回放同亏, W_FULL 之外)、T6(家族 PBO / 选择折价)。

**本线尚未计算任何「T8 特征 × T8 目标」的统计量。** 第 8 条意味着目标水平逐年差异很大(2026 远高于其余年), 前推模型的截距跟不上 —— 故 §6 另报折内去均值的相关, §8 的 C2 用逐折相关防止「只靠水平」过门。

## §2 输入(pod2, 只读, 每个装置断言 sha256)

| 名 | 路径(pod2) | sha256 | 用途 |
|---|---|---|---|
| ARM_R18_s42 | `/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s42.npz` | `d6298deb8d89df54149d82df72d1fe606062cc74a2bfe6b93d0a27ffed3f5340` | `d30_n2_c42_rec`(10039×23)、`d30_n2_c42_W`(= 装置 `sm`, float32) |
| ARM_R18_s2027 | `/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s2027.npz` | `fa5ed19a546c4230d673c4d922ac1c98c1888bf032280fb4da1dbee1d1258f2b` | 同上 |
| ARM_T1_s42 | `/workspace/uplift_r2_2026-09-13/T1/arms/C0_s42.npz` | `93484e8186cabc7ab4d739b283665453542b4ea32eb00e9334be5c7879d0dd09` | `d30_n2_c42_T1AGG`(10039×6×4, 行 pnlL,pnlS,carL,carS,costL,costS; 列 king,rev24,fund,f10) |
| ARM_T1_s2027 | `/workspace/uplift_r2_2026-09-13/T1/arms/C0_s2027.npz` | `d23e4503dfcb44cccf4d9d0ae4ffa0fd1735fba5516d425b8d1b733f7901623c` | 同上 |
| META | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` | `0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3` | 记账元 `y4`(RAW Π(1+r)−1)、`qvk`、`E_ts`(10182 行, 2022-01-08 00Z 起); = A0 装置经 `pod_backup_2026-08-21/wide_fea_hist_meta.npz` 读的同一文件(`r18_foundation/receipts/RECEIPT_r18_drive_gateP.json` inputs) |
| PANEL | `/workspace/data/wide_panel_4h_v2ext.npz` | `5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116` | `f_fund_now`、`f_fund_iv`、`f_tbf_24h`、`ts`、`symbols`(A0 装置同一面板) |
| UMASK | `/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz` | `47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5` | 逐锚宇宙(UPIT: 每月首锚按此前 30 日成交额取前 449、上市 ≥ 30 日; ∧ underlyingType=COIN; 构建器 `health_check/build_umask.py` 自述严格因果) |

- **A0 = C0**: r18 GATE P 证明 `C0_s{42,2027}` 的 rec 与 W 逐位等于归档 A0; T1 GATE P 证明 T1 臂的 rec / W 逐位等于 r18 臂。装置再断言: 两个文件的 `d30_n2_c42_rec` 逐位相等; 臂 `config_json` 满足 CAL=log、PHI=0.45、LEGS=101、WRULE=msharpe、LOOK=900、UMASK_SCOPE=m1、FTRIM=zero、MEMBERS_TOPN=829、COSTB_JSON 以 `costb_PWR_G230k.json` 结尾、SLOW_NPY 以 `SLOW_v3_on_v4axis.npy` 结尾、R18_ELIG=0、R18_WARM=0、FSEED ∈ {42, 2027}。
- **CAL=log 的含义**(E-0826-C 旗标陷阱): 装置 `if CAL == "simple": expm1`; CAL=log = 不变换。v4 记账元的 y4 本身就是 Π(1+r)−1 简单复利收益(r18 RESULT §8), 所以 CAL=log 是 v4 正确口径, 不是对数口径。本线的特征也直接用该 y4, 不做任何变换。
- **不使用**: 5m 缓存任何通道的收益; 面板 `f_rev_*` / `Y4` / `Y24`(由 `ret5` 累加, 裁剪 ±0.30)。`f_tbf_24h` 来自缓存 `tbf` 通道(主动买入占比, 非收益), 其分母只用 `ret5` 的有限计数、不用其数值。

## §3 目标、对齐、窗口、折

### §3.1 目标(每个臂种子各一套; 单位 bps / 4h 锚 / 单位 gross)
对 rec 行 i(`gt_i = rec[i, gross_total]`):
- `NET_i = net_ex / gt`(主目标; 即纲领所说的 g)
- `LONG_i = Σ_{l=0..3} T1AGG[i, 0, l] / gt`(执行后持仓 `smr_n > 0` 的名的价格盈亏)
- `SHORT_i = Σ_l T1AGG[i, 1, l] / gt`(`smr_n < 0` 的名)
- `CARRY_i = carry_ex / gt`(正 = 付)
- 辅助(不作判决目标): `PRICE_i = pnl_ex / gt`, `COST_i = cost_ex / gt`
- 恒等: `NET = LONG + SHORT − CARRY − COST`(§7.1 G-T 断言)。
- **机械事实**: A0 装置里 `car_r = Σ smr·fnow·(4/iv)` 用锚 E_i 时的面板费率, `cbps_r = rate·|smr − HR|` 用锚 E_i 的交易 ⇒ **CARRY_i 与 COST_i 在锚 t 时已完全确定**, 只有 LONG / SHORT 依赖尚未实现的 y4。故 CARRY 在本线是**管线正控**(§7.1 PC), 不是可感知性证据; NET 另加 C4(§8), 防止 NET 仅靠已知的 carry 过门。

### §3.2 时间对齐(因果定义)
- rec 行 i: `ts_i = E_i`; 元行 `k(i) = i + 138`, 断言 `META.E_ts[k] == ts_i`; 面板 / 掩码行 `j(i) = i`, 断言 `PANEL.ts[j] == UMASK.ts[j] == ts_i`。
- 回放持仓 smr_i 在 E_i 定, 赚 `y4[k(i)]` = (E_i, E_i + 4h] 的 RAW 收益(构建器 `y4 = CS[E+48] − CS[E]` 同一 48 根 bar 的复利)。**纲领记号 g(t+1) = 本文 rec 行 i = t**(锚 t 定仓、t→t+1 实现)。
- 锚 t 的特征只用: 元行 ≤ k(i) − 1 的 y4(E_i 及之前已收盘的收益); 元行 k(i) 的 `qvk`(构建器为 E 之前 2016 根 5m bar 的均值); 面板 / 掩码行 j(i) − 41..j(i)(见 §4.2 列 11–16); 臂的 `W[i]`(E_i 定的持仓); rec 行 ≤ i − 1。
- 面板 `f_fund_now[j]` = fundingTime ≤ E_i 的最后一次结算费率, 超过 12h 置 NaN(`retrain_2026-09/pod_panel_ext.py` `searchsorted(side="right") − 1`); `f_tbf_24h[j]` = 截至 E_i 的 288 根 5m bar 均值。

### §3.3 窗口
- 轴 = rec 行(10039; 末行 2026-08-31 00Z 不入)。**W_FULL** = `ts_i ≤ 2026-08-30 20:00Z`, 行 0..10037, n = 10038(断言; = r18 PREREG §4 定义), 1673 个 UTC 日, 每日 6 锚(断言)。
- **样本外评估窗 = W_ALPHA** = W_FULL 行 900..10037 = 2022-06-30 00Z..2026-08-30 20Z, n = 9138(断言), 1523 个 UTC 日(每日 6 锚, 断言)。

### §3.4 嵌套前推折(扩张窗; 训练 = W_FULL 中 ts < 测试期起点的全部行)
| 折 | 测试期(UTC) | n_test(断言) | 训练行 |
|---|---|---|---|
| F1 | 2022-06-30 00Z..2022-12-31 20Z | 1110 | 行 0..899(2022-01-31 00Z..2022-06-29 20Z) |
| F2 | 2023-01-01 00Z..2023-12-31 20Z | 2190 | ts < 2023-01-01 |
| F3 | 2024 全年 | 2196 | ts < 2024-01-01 |
| F4 | 2025 全年 | 2190 | ts < 2025-01-01 |
| F5 | 2026-01-01 00Z..2026-08-30 20Z | 1452 | ts < 2026-01-01 |
Σ n_test = 9138 = W_ALPHA(断言)。

**对纲领「按日历年」的一处偏离(先于数字, 写明理由)**: 书收益在 2022-01-31 之前不存在 ⇒ 在 W_FULL 上严格「训练 < Y」只有 2023–2026 四个日历测试年, 而过门规则要求「≥ 4/5 年同号」需要 5 个测试期。F1 = 2022 年余下部分, 用 2022 年前 900 锚(回放暖机行)训练; 其测试起点恰为 W_ALPHA 起点, 因此样本外合并序列 = W_ALPHA 全窗(所有已发表 v4 逐年表的窗口)。
**不设 embargo**: 目标是互不重叠的 4h 区间, 全部特征按 §3.2 因果, 训练标签区间与测试标签区间不重叠。

## §4 特征(24 列; 全部锚 t 因果; 不增删)

### §4.1 记号与合格集
- `Y` = META `y4`(转 float64); 列序 = PANEL `symbols`(断言 ARM `symbols` == PANEL == UMASK; META 无符号数组, 其列序沿用装置的约定)。`U_j` = UMASK 行 j。`BTC` = `BTCUSDT` 列。
- 对元行 r 与名 n: `R4(r,n) = Y[r−1, n]`; `R24(r,n) = Π_{q=1..6}(1 + Y[r−q, n]) − 1`(6 个全有限, 否则 NaN); `R72(r,n) = Π_{q=1..18}(1 + Y[r−q, n]) − 1`(18 个全有限)。
- 合格集(行 i, k = k(i), j = j(i)): `A4_i = {n : U_j[n] ∧ isfinite R4(k,n)}`, `A24_i`、`A72_i` 同式。「山寨」= 集合 ∖ {BTC}。凡基于集合的列, 集合 < 50 名则该列为 NaN。
- `RN8(j,n) = f_fund_now[j,n] × 8 / IVf[j,n]`, `IVf = f_fund_iv` 若有限且 > 0, 否则 8(= A0 装置 `_IVf`)。
- 装置成员集 `m_i` = META `qvk[k]` 有限名(装置 MEMBERS_TOPN=829 重建: `nan→−1` 后 > −0.5, 按 qvk 降序取前 829)∩ `U_j`。
- `smr_i` = 臂 `W[i]` 的执行器重塑(装置公式, float32 转 float64): `nz = |W| > 1e-12`; `smr = W`; `smr[nz] −= mean(W[nz])`; 若 `Σ|smr| > 1e-9` 则 `smr ×= Σ|W| / Σ|smr|`。

### §4.2 列定义
| # | 名 | 定义 | 纲领条目 |
|---|---|---|---|
| 1 | BTC4 | `R4(k, BTC)` | BTC 4h |
| 2 | BTC24 | `R24(k, BTC)` | BTC 24h |
| 3 | BTC72 | `R72(k, BTC)` | BTC 72h |
| 4 | ALT4 | `mean_{n∈A4_i∖BTC} R4(k,n) − BTC4` | 山寨−BTC 等权价差 4h |
| 5 | ALT24 | `mean_{n∈A24_i∖BTC} R24(k,n) − BTC24` | 24h |
| 6 | ALT72 | `mean_{n∈A72_i∖BTC} R72(k,n) − BTC72` | 72h |
| 7 | BR4 | `mean_{n∈A4_i} 1[R4(k,n) > 0]` | 广度 4h |
| 8 | BR24 | `mean_{n∈A24_i} 1[R24(k,n) > 0]` | 广度 24h |
| 9 | DISP4 | `std_{n∈A4_i} R4(k,n)`(ddof 0) | 截面离散 |
| 10 | DISP24 | `std_{n∈A24_i} R24(k,n)` | 截面离散 |
| 11 | RVM24 | `sqrt(Σ_{q=0..5} MKT4_{i−q}²)`, `MKT4_{i'} = mean_{n∈A4_{i'}} R4(k(i'), n)`; 6 个须全有限(i' < 0 或其集合 < 50 ⇒ NaN) | 市场实现波动 24h |
| 12 | RVM168 | `sqrt(Σ_{q=0..41} MKT4_{i−q}²)`; 42 个须全有限 | 市场实现波动 7d |
| 13 | MUF | `1e4 × mean_{n∈F_j} RN8(j,n)`, `F_j = {n : U_j[n] ∧ isfinite f_fund_now[j,n]}` | 资金费水平 |
| 14 | SIGF | `1e4 × std_{n∈F_j} RN8(j,n)`(ddof 0) | 资金费离散 |
| 15 | DMUF24 | `MUF(j) − MUF(j−6)`(j < 6 ⇒ NaN) | 水平 24h 变化 |
| 16 | DSIGF24 | `SIGF(j) − SIGF(j−6)` | 离散 24h 变化 |
| 17 | TKR24 | `mean_{n∈A24_i ∧ isfinite f_tbf_24h[j,n]} (f_tbf_24h[j,n] − 0.5)` | 主动成交不平衡 |
| 18 | CSF | `1e4 × Σ_{n∈S⁻}|smr_n|·RN8(j,n) / Σ_{n∈S⁻}|smr_n|`, `S⁻ = {n∈m_i : smr_n < 0 ∧ isfinite RN8(j,n)}` | 书空头侧加权资金费 |
| 19 | CSR72 | `Σ_{n∈S⁻'}|smr_n|·R72(k,n) / Σ_{n∈S⁻'}|smr_n|`, `S⁻' = {n∈m_i : smr_n < 0 ∧ isfinite R72(k,n)}` | 书空头侧加权 3 日涨幅 |
| 20 | CLF | 同 CSF, `smr_n > 0` | 书多头侧加权资金费 |
| 21 | CLR72 | 同 CSR72, `smr_n > 0` | 书多头侧加权 3 日涨幅 |
| 22 | TR1 | `NET_{i−1}`(同种子) | 书自身近 1 锚 |
| 23 | TR6 | `mean(NET_{i−6..i−1})` | 近 6 锚 |
| 24 | TR42 | `mean(NET_{i−42..i−1})`(i < 42 ⇒ NaN) | 近 42 锚 |
- 列 1–17 两种子相同; 列 18–24 按种子。拥挤度加权集合总权重为 0 ⇒ NaN。
- 列 17 用 `A24_i` 而非 `U_j`: 面板构建器的 `wmean` 对 24h 内无 bar 的名给 0 而非 NaN, 要求 24h 价格有限可排除这类伪 0。

### §4.3 为什么没有聚合 OI(纲领条目「仅在覆盖允许时」)
- pod2 上唯一的 OI 文件 `/workspace/data/f12_l3_um.npz`: 59 名(110 名时代), 文件内无时间轴(`X_um` 379,585 × 59 × 6 根 5m bar), 覆盖不到 W_FULL 至 2026-08。
- 820 名 um 面板(`docs/DESIGN_um_features_2026-08-25.md` §0)在 jpline(不在本任务允许的计算主机内), 覆盖 2023-01 → 2026-08-22 ⇒ 缺整个 2022(F1 测试、F2 训练)与 W_FULL 末 8 天。
- 先验: 同文 §1 首行称「OI 象限择时(整书级 4h/日线)已判负 DNR」(二手引用, 底层收据本人未打开); 同文 RESULT §3-bis 在两种粒度上关闭 um 轴。
- 暂停中的研究员进程(PID 333197)的 OI 采集不是钉住的数据集, 且禁止触碰。
⇒ **OI: NOT MEASURED**。主动成交不平衡用面板 `f_tbf_24h`(覆盖见 §4.4)。

### §4.4 覆盖(冻结前算过; 只用 PANEL 与 UMASK, 不涉任何收益或书)
| 年 | UMASK 名数/锚 min / 中位 | `f_tbf_24h` 有限 ∩ U 占比 | `f_fund_now` 有限 ∩ U 占比 |
|---|---|---|---|
| 2022 | 136 / 141 | 100% | 99.2% |
| 2023 | 146 / 184 | 100% | 100% |
| 2024 | 236 / 264 | 100% | 99.97% |
| 2025 | 323 / 423 | 100% | 99.4% |
| 2026(面板行至 08-31 00Z) | 373 / 432 | 100% | 98.5% |
`BTCUSDT` 在每个面板行都 ∈ U。

## §5 模型家族(写死; 无搜索; 无特征筛选)

### §5.1 每折预处理(给定种子、目标 T、折 f)
- P1 训练行 `TR_f` = W_FULL 中 ts < 起点、且 24 列全有限的行(丢弃数入收据)。测试行 `TE_f` = 该折测试期全部行; 其中非有限的特征值以该特征在 `TR_f` 上的中位数替代(替代数入收据)。
- P2 每列 `lo, hi = np.quantile(训练值, [0.005, 0.995])`(numpy 默认 linear), 训练与测试都截断到 [lo, hi]。
- P3 以截断后训练均值与标准差(ddof 0)标准化; 训练标准差 < 1e-12 的列在训练与测试中都置 0(入收据)。
- P4 训练目标截断到 `np.quantile(T[TR_f], [0.005, 0.995])`; **测试目标永不截断**, 全部统计量用原始测试目标。

### §5.2 Ridge(R; 前置)
标准化 X(训练均值 0), `yc` = 截断后训练目标, `ȳ = mean(yc)`; `β = solve(XᵀX + αI, Xᵀ(yc − ȳ))`, **α = |TR_f|**(训练行数); `p_test = ȳ + X_test β`。numpy float64, 不用 sklearn。

### §5.3 LGBM(L; 唯一配方)
lightgbm 4.7.0(pod2 venv): `lgb.train(PARAMS, lgb.Dataset(X_train, yc), num_boost_round=300)`; `p_test = booster.predict(X_test)`。
`PARAMS = {objective: "regression", learning_rate: 0.02, num_leaves: 7, max_depth: 3, min_data_in_leaf: 200, feature_fraction: 0.8, bagging_fraction: 0.8, bagging_freq: 1, lambda_l2: 10.0, max_bin: 63, seed: 20260913, deterministic: True, force_row_wise: True, num_threads: 8, verbosity: -1}`。无早停、无验证切分、无种子平均。

### §5.4 家族大小(T6 教训: 写死)
- **判决格**: {R, L} × {NET, LONG, SHORT} = **6 个实质格**; {R, L} × {CARRY} = 2 个正控格(不能使 T8 过门)。每格在 2 个臂种子上**合取**读(种子是复本, 不是额外假设)。
- 观测拟合: 2 模型 × 4 目标 × 2 种子 × 5 折 = **80**。零分布重拟合(G1): 500 次置换 × 6 格 × 5 折 = **15,000**(只用 s42 特征; 其中 LGBM 7,500)。
- 本线不拟合、不报告任何其他模型、特征子集、窗口、折方案、超参或预处理变体。任何后续变体是新家族, 必须按新家族登记。

## §6 统计量(格 = 模型 × 目标 × 种子; 样本外序列 `p_i`, i ∈ W_ALPHA)
- `r_pool` = Pearson(p, T), W_ALPHA 全部 9138 锚; `ρ_pool` = Spearman。
- `r_f`、`ρ_f`: 逐折。`r_within`: p 与 T 各减所在折的均值后的合并 Pearson(描述, 去掉折间水平)。`r_2326`: 只用 F2–F5 行的合并 Pearson(描述)。
- **CI(UTC 日块自举)**: 日 `d_i = floor(ts_i / 86400)`, W_ALPHA 日升序, nd = 1523。主抽样 `D_b = default_rng([20260905, b]).integers(0, nd, nd)`, b = 0..1999(「k=0」); 复核抽样 `D9_b = default_rng([20260905, 9·2000 + b]).integers(0, nd, nd)`(「k=9」)—— 与 `uplift_2026-09-11/r18_foundation/devices/r18_judge.py` L65 / L74 的流约定逐字相同。每次抽样按抽中日(含重复)累加逐日充分统计量 (n, Σp, ΣT, Σp², ΣT², ΣpT) 算 Pearson。`CI95 = np.percentile(·, [2.5, 97.5])`。全部格共用同一组抽样。
- **幅度读数(描述)**: 样本外 R² = `1 − Σ(T − p)² / Σ(T − m_f)²`, `m_f` = 该折 `TR_f` 上原始目标均值; 校准斜率(T 对 p 的合并 OLS); 方向命中率 `mean(sign p == sign T)` 与基率 `max(mean(T>0), mean(T<0))`; 五分位表: 按预测五分位的 T 均值, 分位点取该折**训练内**预测的五分位; Ridge 逐折标准化系数; LGBM 逐折 gain 重要性。
- **C4 输入**(NET 格): `r_price` = Pearson(p_NET, PRICE), 同一组抽样给 CI。
- **主导率分解**(全部实质格): `S_i = mean_{n∈U_j ∧ isfinite Y[k,n], n≠BTC} Y[k,n] − Y[k,BTC]`(行 i 的**前向**区间; 只用于分解与 G2a, 永不作特征); `β_f` = 原始 T 对 S 在 `TR_f` 上的 OLS 斜率(含截距); `e_i = T_i − β_f·S_i`; `Share_S = Σ(p − p̄)(β_f S − mean(β_f S)) / Σ(p − p̄)(T − T̄)`(W_ALPHA); `r_S` = Pearson(p, S); `r_e` = Pearson(p, e) 及 CI(k=0 与 k=9)。
- **偏移谱**: `r(k)` = Pearson(p_i, T_{i+k}), i ∈ W_ALPHA 且 i+k ∈ W_FULL, k ∈ {−2, −1, 0, +1, +2, +3}。
- **未定义的相关**: 任何 Pearson 若一侧方差为 0(例如某折预测为常数), 记为未定义: `r_f` 未定义计为「非 > 0」; `r_pool` 未定义则 C1 不成立; 自举抽样中未定义的复制值按 0 计入百分位(保守)。

## §7 前置门与守卫

### §7.1 前置门(数据集级; 在任何模型拟合之前运行; 任一失败 ⇒ INVALID: 停下、不读任何判决、如实报告; 只能以先于结果数字冻结的 AMENDMENT 修正)
- **G-IN**: §2 全部 sha; config_json 断言; ARM_R18 与 ARM_T1 的 `d30_n2_c42_rec` 逐位相等(两种子); rec `ts` == PANEL `ts` == UMASK `ts`(10039 行); `META.E_ts[i+138] == ts_i`(全部 10039 行); §3.3 / §3.4 全部计数断言。
- **G-T(目标恒等)**: W_FULL 上 `max|LONG + SHORT − PRICE| ≤ 1e-8` 且 `max|PRICE − CARRY − COST − NET| ≤ 1e-8`(两种子); `gt > 0` 处处。
- **G-T2(多空拆分独立复算)**: 由 ARM_R18 的 W 与 META y4 独立算 `LONG'_i = Σ_{n∈m_i, smr'_n>0} smr'_n · nan→0(Y[k,n]) · 1e4 / gt_i`(smr' 按 §4.1 公式), SHORT' 同式: `max|LONG' − LONG| ≤ 1e-2` 且 `max|SHORT' − SHORT| ≤ 1e-2` bps(W 为 float32 的精度界; 两种子)。
- **G2a(对齐正控: 用已知的同期关系, 不涉预测)**: W_FULL 上, k ∈ {−2..+3}: `c_N(k) = corr(NET_i, S_{i+k})`, `c_L(k) = corr(LONG_i, MKT_{i+k})`, `c_S(k) = corr(SHORT_i, MKT_{i+k})`, `MKT_i = mean_{n∈U_j ∧ isfinite Y[k,n]} Y[k,n]`(前向)。通过 ⇔ `argmax_k |c_N| = 0` 且 `c_N(0) < 0`; `argmax_k |c_L| = 0` 且 `c_L(0) > 0`; `argmax_k |c_S| = 0` 且 `c_S(0) < 0`(两种子)。它证明 rec 行 i 的收益与元行 k(i) 的前向区间是同一段, 从而特征所用的 ≤ k(i) − 1 行严格在目标区间之前。
- **G3(shuffle-future)**: 行集 `default_rng([20260905, 10000]).choice(np.arange(42, 10038), 60, replace=False)`; 扰动值来自 `default_rng([20260905, 10001])`。对每个抽中的 i 制作扰动副本: Y 行 ≥ k(i) 全部格 ← N(0, 0.05²); META `qvk` 行 > k(i) ← 随机; PANEL `f_fund_now`、`f_fund_iv`、`f_tbf_24h` 行 > j(i) ← 随机; UMASK 行 > j(i) ← 随机布尔; W 行 > i ← N(0, 1e-3²); 全部目标数组(rec 派生量、T1AGG 派生量)行 ≥ i ← 随机。重算行 i 的 24 列, 必须与未扰动值**逐位相等**(两种子)。
  **G3-NEG(证明该门会红)**: 只扰动 Y 行 k(i) − 1 的 BTC 格 ⇒ BTC4 必变; 只扰动 NET 行 i − 1 ⇒ TR1 必变; 只扰动 PANEL `f_fund_now` 行 j(i) ⇒ MUF 必变 —— 60 行全部满足。
- **PC(管线正控)**: CARRY 格 `r_pool ≥ 0.5`, 两种子, R 与 L 分别判; 某模型不过 PC ⇒ 该模型全部格 INVALID(两个都不过 ⇒ T8 INVALID)。

### §7.2 每格守卫
- **G1(日块打乱目标的零分布; 族最大值)**: r = 0..499, `π_r = default_rng([20260905, 7·2000 + r]).permutation(1673)`(W_FULL 的 UTC 日); 置换后目标: 第 d 日的 6 行 ← 第 π_r(d) 日的 6 行(日内顺序不变), NET / LONG / SHORT 用同一置换; 特征不变; 按 §5 原样重拟合 6 个实质格(s42 特征)得 `r_pool^(r)`; `M_r` = 6 格最大值; `q95 = np.percentile(M, 95)`。G1 通过 ⇔ `r_pool > q95`(s2027 格用同一 q95)。另报逐格零分布分位与 `p = (1 + #{r : M_r ≥ r_pool}) / 501`。分块运行只是操作(任意划分), 合并后每个 r 恰出现一次(断言)。
- **G2b(偏移谱峰 @0)**: `argmax_{k∈{0,1,2,3}} r(k) = 0`。k ∈ {−2, −1} 只报不判, 理由先写: 特征含书自身上一锚收益(TR1 = NET_{i−1})与 E_i 收盘的 4h 市场收益(BTC4、ALT4、BR4 —— 与 T_{i−1} 同期, 且据 §1 第 3 条与 NET 同期 r ≈ −0.77), 后向峰是机械的, 不是泄漏; 对齐本身由 G-IN(时间戳相等)、G2a 与 G3 认证。

## §8 读法(冻结)

**格判据**:
- C1: `r_pool ≥ 0.03`
- C2: `r_f > 0` 的折 ≥ 4 / 5
- C3: `r_pool` 的 CI95 下界 > 0, k=0 与 k=9 两组抽样都成立
- C4(仅 NET 格): `r_price ≥ 0.03` 且其 CI95 下界 > 0(k=0 与 k=9)—— NET 的预测力必须到达价格部分
- G1、G2b 见 §7.2

`CORE = C1 ∧ C2 ∧ C3 ∧ G1 (∧ C4, 若 NET)`; `PASS_cell = CORE ∧ G2b`。
- **模型 × 目标**: PASS ⇔ 两种子 `PASS_cell`; UNDECIDED ⇔ 非 PASS 且(两种子 CORE, 或恰一个种子 `PASS_cell`); 否则 FAIL。
- **目标**: PASS-LINEAR ⇔ R PASS(Ridge 前置门通过); PASS-LGBM-ONLY ⇔ R 非 PASS 且 L PASS; UNDECIDED ⇔ 两者都非 PASS 且至少一个 UNDECIDED; 否则 FAIL。
- **T8 总判**: PASS ⇔ NET / LONG / SHORT 至少一个 PASS-*; UNDECIDED ⇔ 无 PASS 且至少一个 UNDECIDED; FAIL ⇔ 三个全 FAIL; INVALID 见 §7.1。

**后果(冻结)**: FAIL ⇒ 「在本分辨率下, 这组锚时状态(§4)与这个模型家族(§5)不能预测下一锚书收益; 建立在这组状态上的监控 / 调节层是装饰」—— 限定于本状态集、本家族、本分辨率, 不是普遍不可能。PASS ⇒ 只开 S2 预注册, 范围限于过门的目标; 不产生书行为提案; S2 必须处理 §9 第 1–2 条。UNDECIDED ⇒ 报告缺哪一条, 不开 S2。

**主导率分解标签**(全部实质格都报; 对 PASS / UNDECIDED 的目标随判决附上, 不改变判决): DOMINANCE-TIMING ⇔ 该判决模型两种子 `Share_S ≥ 0.5`; RESIDUAL ⇔ 两种子 `Share_S < 0.5` 且 `r_e ≥ 0.03` 且 `r_e` CI95 下界 > 0(k=0 与 k=9); 否则 MIXED。若为 DOMINANCE-TIMING, 须同时引用 §1 第 3 条(对冲主导率保费毁收益、山寨季状态不持久)。

**分辨率(先写)**: 独立近似下 `SE(r_pool) ≈ 1/√9138 ≈ 0.0105`, 日块下更大 ⇒ C1 的 0.03 与 C3 同时成立处在分辨率边缘; 真实 r = 0.03 时 C3 大约一半概率成立。这是冻结的门槛, 结果后不放宽。

## §9 事先声明的限制
1. **执行延迟**: 目标从 E_i 起记账; 实盘执行器约在 E_i + 24 分钟之后成交(T2 σ 臂先例)。若可感知性集中在 (E_i, E_i + 24m], 实盘拿不到。RAW 4h y4 分辨不出这一段, 而 5m `ret5` 通道禁用 ⇒ **NOT MEASURED**, S2 必须处理。
2. **C0 = A0 的 N2 合格规则**: 归档 A0 用前向 `isfinite(y4[i])` 判合格, 全史 15 格 / 12 锚受影响(r18 RESULT §1 第 2 条); W[i](拥挤度列)在这些格上继承它; G3 不能穿过回放扰动 W。有界、声明、不修(目标必须是归档 A0)。
3. **OI: NOT MEASURED**(§4.3)。
4. v2ext 面板 2026-08 的 API 尾行对结算间隔用拉取时的静态值(T1 §1 F6; T5b 口径更正针对 x0910); RN8 列与回放自身 carry 继承同一误差; W_FULL 止于 08-30, 九月误差不进入。
5. A0 的腿是 v3 谱系(king `SLOW_v3_on_v4axis`、F10 `f10_A0`; r15 §1 / T1 §10.5); 目标 = 归档 A0 原样。
6. 目标是单位 gross 收益; gross 缩放与复利不在 T8 范围。
7. 状态集 = 纲领所列; T8 FAIL 不排除其他信息源(如 T7 韩元溢价、盘口)。
8. 厚尾: Pearson 对极端锚敏感; 保护来自 C2(逐折同号)与 C3(日块 CI); Spearman 只报。

## §10 装置、环境、运行纪律
- 目录: pod2 `/workspace/uplift_r2_2026-09-13/T8/{devices,receipts,out}`; 仓库 `T8/{devices,receipts}`; Mac 端大件只放 `/Users/haosiyu/cc_tmp/t8/`。
- 装置: `t8_common.py`(目标与特征函数, 全部装置共用)· `t8_build.py`(§7.1 G-IN / G-T / G-T2 / G2a / G3 / G3-NEG; 产 `out/T8_data.npz` 与 `receipts/RECEIPT_T8_build.json`)· `t8_null.py <r_lo> <r_hi>`(G1 分块; `receipts/RECEIPT_T8_null_<r_lo>_<r_hi>.json`)· `t8_fit.py`(80 个观测拟合、§6 全部统计量、PC、分解、偏移谱; `out/T8_oos.npz` 与 `receipts/RECEIPT_T8_fit.json`)· `t8_judge.py`(§8 读法, 只读收据并断言各收据与装置 sha; `receipts/RECEIPT_T8_judge.json`)· `t8_tables.py`(Mac; 从收据渲染 `receipts/TABLES_T8.md`)。
- **顺序**: build → null(全部分块)→ fit → judge → tables。零分布阈值在任何观测拟合之前算完。
- 每个装置: 断言 `sha256(PREREG_T8.md)` 等于冻结值; 自报 self_sha256; 断言输入 sha; 环境白名单 {PATH, HOME, LC_CTYPE, OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS}(后三者值断言为 8), 出现口径旗标前缀即拒绝启动; 收据记 python / numpy / lightgbm 版本、`nvidia-smi` 前后(须 0 % / 2 MiB)、PID 333197 / 339489 的 `ps -o pid,stat` 前后(只读)、loadavg、墙钟。
- 启动(前台): `cd /workspace/uplift_r2_2026-09-13/T8 && env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/<装置> PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS [参数] > receipts/<装置>_stdout.log 2>&1; echo rc=$?`; rc 与装置末行摘要写入 `receipts/RC_<装置>[_参数].txt`。**缺 rc 或摘要行的运行视为未通过。**
- pod2 写入总量 < 500 MB(单个输出将超 500 MB 则装置先停); 不占 GPU; ≤ 8 核; 不向任何进程发信号; 不调交易所 API; 不写 T8 以外的目录。
- 提交: 本文 + 冻结收据(STEP 0); 装置在运行之前提交; 结果之后提交。均用显式 pathspec, 并核 `git show --name-only HEAD`。

## §11 修订规则
任何修改写成 `PREREG_AMENDMENT_<n>_T8.md`, 在受影响的结果数字产生之前冻结 sha 与 UTC 时刻, 原失败读数保留在收据; 结果之后的修改只能进 RESULT 的「偏离」节并标 POST-HOC。
