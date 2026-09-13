> **创建:** 2026-09-13 ~10:45Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T8) | **状态:** 已判 —— 冻结读法 **T8 = FAIL**; 判据冻结于 `PREREG_T8.md` sha256 `53da0bcc…84f8a`(2026-09-13 09:59:27Z)+ `PREREG_AMENDMENT_1_T8.md` sha256 `d5928ee3…0be56`(10:20:22Z, 由 build 首跑 G2a 失败触发, 先于任何预测数字); 数字产生后未改阈值 / 窗口 / 读法; **未经 lead 复跑** | **作废条件:** r18 C0 臂、T1 C0 臂、v4 记账元、v2ext 面板或 UPIT_CRYPTO 掩码被替换; 预注册或修订 sha 变化
> **口径:** v4; 目标 = A0(= r18 `C0_s{42,2027}`, 逐位 = 归档 A0)逐锚 `net_ex/gross_total`, 及多头价格 / 空头价格(T1 臂 `T1AGG`)/ carry; bps / 4h 锚 / 单位 gross; 特征收益一律取记账元 RAW y4 = Π(1+r)−1, **未从 5m 缓存 `ret5` 或面板 `f_rev_*` 取任何收益**。全部数字由 `devices/t8_tables.py` 从收据渲染到 `receipts/TABLES_T8.md`, 本文数字都在那里有出处。
> **实盘零接触(VERIFIED):** 未读 `~/wide_shadow` / `~/dl_quant_live`; 无任何 API 调用。pod2 只用 CPU: 每次运行都在 `env -i` 白名单、`nice -n 10`、`taskset -c 40-47`(8 核)下前台运行, 装置断言亲和核 ≤ 8; `nvidia-smi` 前后 `0 %, 2 MiB`; PID 333197 / 339489 前后均为 `Tl`, 未触碰; pod2 写入共 14 MB。未写 P2 / T6 / T7 目录。
> **提交:** `844cd412`(预注册 + 冻结收据)· `de42037f`(装置, 运行前)· `7ef2786f`(AMENDMENT 1 + 装置更新, 运行前)· `1e3c01b1`(表格装置, 运行前)· 本文所在提交(结果、收据、校验和)

# RESULT · T8 · 书层收益可感知门(多变量)

## §0 一页

**回答: 不能。** 在冻结读法下, 下一个 4h 区间的 A0 书净额**不可从锚时状态预测**: 净额、多头价格、空头价格三个目标, Ridge 与 LGBM 两个模型, 两个臂种子, **全部 FAIL**。管线正控(carry)两个模型都通过, 前置门全部通过 ⇒ FAIL 是结果, 不是装置失灵。

| 目标 | Ridge r_pool(s42 / s2027) | LGBM r_pool(s42 / s2027) | 正折(R / L) | 决定 FAIL 的条件 | 判决 |
|---|---|---|---|---|---|
| **NET** | −0.0090 / −0.0062 | −0.0038 / −0.0067 | 2/5 · 2/5 | 全部: C1、C2、C3、C4、G1(族 p 0.95–0.99)、G2b | **FAIL** |
| LONG(多头价格) | +0.0212 / +0.0215 | **+0.0252 / +0.0288** | 4/5 · 5/5 | R: C1、C3、G1; **L: 只差 C1(< 0.03)** | **FAIL** |
| SHORT(空头价格) | +0.0054 / +0.0055 | +0.0190 / +0.0222 | 4/5 · 5/5 | R 与 L: C1、C3、G1 | **FAIL** |
| CARRY(正控) | +0.8091 / +0.8075 | +0.8664 / +0.8635 | 5/5 · 5/5 | — | 正控通过 |

- **净额没有任何预测力**: 合并相关 −0.009…−0.004, CI95 约 [−0.030, +0.016]; 5 折里只有 2 折为正; 2026 折最差(R −0.070 / −0.062, L −0.040 / −0.039); NET 预测对价格部分的相关 −0.008…−0.003(C4); 样本外 R² 全部为负; 方向命中率 0.503–0.508, 与基率 0.505–0.507 相同。零分布上 NET 格的族 p 为 0.95–0.99。
- **唯一接近过门的是 LGBM × 多头价格**: +0.025 / +0.029, 5/5 折为正, CI95 下界 > 0(k=0 与 k=9), 超过族最大值零分布 q95 0.02264(族 p 0.026 / 0.016), 偏移谱峰在 0 —— **只差 C1 的 0.03**(折内去均值的描述量 +0.029 / +0.033 也在门槛附近; 冻结判据用合并 r)。按冻结规则为 FAIL, 不开 S2。
- **这点预测力是市场方向, 不是残差 alpha**(主导率分解, 冻结规则下的标签): LONG 两个模型 Share_S = 1.00–1.09, 去掉价差后的残差相关 −0.004…+0.000(CI 约 [−0.026, +0.024]); SHORT 的 Share_S = 1.07–2.85, 残差相关 ≤ 0 ⇒ 两者标签都是 **DOMINANCE-TIMING**。多头价格 ≈ +0.5×市场、空头价格 ≈ −0.5×市场(G2a: 同期相关 +0.986 / −0.988), 所以两腿的微弱预测力是**同一个 4h 市场方向信号的正反两面**, 在净额里相互抵消(NET 与同期价差的相关只有 +0.05)。**[推断]** 若在 S2 里利用它, 实质是对单腿做方向性择时, 不是书收益感知门; 何况它本身没过冻结的门槛。
- **冻结后果**: 「在本分辨率下, 这组锚时状态(24 列)与这个模型家族(Ridge + 单一 LGBM 配方)不能预测下一锚书收益; 建立在这组状态上的监控 / 调节层是装饰」—— 限定于本状态集、本家族、本分辨率, 不是普遍不可能。**S2 不开; 无任何书行为提案。**

## §1 门与运行(`TABLES_T8.md` T0; 全部 VERIFIED)

| 门 | 读数 |
|---|---|
| 合成自检 `t8_selftest.py` | 8/8: 特征对逐名暴力循环相对差 1.1e-15、NaN 位置 0 不一致; 重塑与 A0 装置代码行逐位相同; 合成 shuffle-future 34/34 逐位不变, 且**植入的前视缺陷 17/17 被抓到**; 日块自举与直接重抽差 1.7e-16; Ridge 与 sklearn 预测差 1.7e-16; LightGBM 两次拟合逐位相同 |
| G-IN | 7 个输入 sha、臂 config_json、r18 与 T1 两臂 rec 逐位相等、rec / 面板 / 掩码 / 元 ts 逐行对齐、W_FULL 10038 / W_ALPHA 9138 / 折计数 |
| G-T | max\|LONG+SHORT−PRICE\| ≤ 5.5e-13; max\|PRICE−CARRY−COST−NET\| ≤ 5.7e-14(两种子) |
| G-T2 | 由 r18 臂 W(float32)与元 y4 独立复算多空拆分, 对 T1AGG max\|Δ\| LONG 7.8e-6、SHORT 1.2e-5 bps |
| G2a(修订 1 规则) | c_L(0) = +0.9858 / +0.9855, c_S(0) = −0.9881 / −0.9881, 相邻偏移 \|r\| ≤ 0.0104, argmax 全在 0 ⇒ **rec 行 i 的收益与元行 k(i) 的前向区间是同一段**; c_N 只报(见 §6) |
| G3 shuffle-future | 60 行 × 2 种子, 未来行全部替换后 24 列**逐位不变** 120/120 |
| G3-NEG | 只扰动已收盘的一格: BTC4 60/60 变、TR1 60/60 变、MUF 60/60 变(该门会红) |
| G1 零分布 | 500 次 UTC 日块置换全部完成(4 块, rc 全 0), 未定义值 0; 族最大值 q95 = 0.02264(分位 50 / 90 / 99 = 0.0075 / 0.0196 / 0.0298, 最大 0.0325) |
| PC | CARRY 合并相关 R +0.81 / +0.81, L +0.87 / +0.86(门 ≥ 0.5)|
| 数据可复现 | `out/T8_data.npz` sha `ff8d4e57…`, 首跑与修订后重跑**逐位相同** |
| 目标交叉核对 | F2–F5 逐折 NET 均值 = r18 RESULT §4 的 W_FULL 逐年 g: s42 −0.649 / +0.486 / +0.677 / +3.091, s2027 −0.612 / +0.460 / +0.759 / +3.101 |

## §2 逐年样本外表(Pearson; 括号内为 Spearman; `TABLES_T8.md` T2)

| 格(s42 / s2027) | F1 2022H2 | F2 2023 | F3 2024 | F4 2025 | F5 2026→08-30 | 合并 r [CI95 k=0] |
|---|---|---|---|---|---|---|
| R · NET | −0.009 / −0.009 | −0.025 / −0.025 | +0.009 / +0.007 | +0.028 / +0.031 | **−0.070 / −0.062** | −0.009 [−0.030, +0.011] / −0.006 [−0.027, +0.014] |
| L · NET | +0.010 / +0.010 | −0.018 / −0.015 | −0.012 / −0.021 | +0.045 / +0.050 | −0.040 / −0.039 | −0.004 [−0.024, +0.016] / −0.007 [−0.028, +0.013] |
| R · LONG | +0.079 / +0.079 | −0.021 / −0.020 | +0.060 / +0.060 | +0.032 / +0.032 | +0.007 / +0.005 | +0.021 [−0.003, +0.046] / +0.022 [−0.003, +0.046] |
| L · LONG | +0.050 / +0.050 | +0.019 / +0.019 | +0.028 / +0.038 | +0.030 / +0.036 | +0.036 / +0.031 | **+0.025 [+0.002, +0.048] / +0.029 [+0.005, +0.053]** |
| R · SHORT | +0.068 / +0.068 | −0.042 / −0.041 | +0.058 / +0.057 | +0.015 / +0.014 | +0.027 / +0.027 | +0.005 [−0.018, +0.029] / +0.006 [−0.018, +0.030] |
| L · SHORT | +0.060 / +0.060 | +0.012 / +0.012 | +0.033 / +0.040 | +0.026 / +0.031 | +0.015 / +0.022 | +0.019 [−0.003, +0.042] / +0.022 [−0.001, +0.045] |
| R · CARRY(正控) | +0.773 / +0.773 | +0.536 / +0.541 | +0.490 / +0.493 | +0.859 / +0.834 | +0.831 / +0.865 | +0.809 / +0.808 |
| L · CARRY(正控) | +0.599 / +0.599 | +0.741 / +0.752 | +0.724 / +0.725 | +0.882 / +0.874 | +0.902 / +0.904 | +0.866 / +0.864 |

- F1 两种子读数相同: F10 腿在 2023-01-01 前恒为 0(T1 RESULT §8 / r15 §1), 两种子的书在 2022 年相同 —— F1 的目标均值与全部 F1 相关在两种子上一致即此事实的读数。
- 合并 Spearman: NET +0.008…+0.012; LONG R +0.026 / L +0.041; SHORT R +0.004 / L +0.029–0.031。折内去均值合并 r: NET −0.009…−0.002; LONG +0.029–0.033; SHORT +0.019–0.031。只用 2023–26 行: NET −0.011…−0.005; LONG L +0.021 / +0.026。

## §3 守卫与分解(`TABLES_T8.md` T4–T7)

- **G1 零分布**: 6 个实质格的族最大值 q95 = 0.02264。过 G1 的只有 L · LONG(两种子); L · SHORT 的族 p 为 0.118 / 0.060; R · LONG 为 0.070 / 0.064; NET 各格 0.95–0.99。单格零分布 q95 为 0.0136–0.0181。
- **G2b 偏移谱**(前向 k ∈ {0..3} 峰须在 0): LONG、SHORT、CARRY 各格都在 0; **NET 四格前向峰都在 k = +1**, 但全部数值 ≤ +0.0083, 即没有可定位的峰(整条前向谱都在零附近)。后向 k = −2 / −1 为负(NET R −0.091 / −0.045…), 按预注册只报: 模型对 TR42 等书自身滞后收益加载为负(Ridge 系数 TR42 −0.56, 5/5 折同号), 后向相关是机械的。
- **G3**: 见 §1, 120/120 逐位不变, 负控 180/180 会红。
- **主导率分解**: 每折训练估计的 β(目标 bps / 价差收益): NET +454 / +261 / +413 / +298 / +147(s42); LONG ≈ +6300…+7000; SHORT ≈ −6000…−6600。Share_S 与残差相关见 §0; NET 格 Share_S 为负(−0.46…−0.83), 残差相关 −0.014…−0.007, 标签 MIXED(预测力本身为零, 标签无实质含义)。

## §4 幅度(方向与大小; `TABLES_T8.md` T3)
- 样本外 R²(对该折训练均值)**全部实质格为负**: NET −0.0025…−0.0145; LONG −0.0017…−0.0116; SHORT −0.0031…−0.0122 ⇒ **幅度不可预测**; 连方向的弱相关也换不来均方误差上的改进。
- 方向命中率: NET 0.503–0.508 对基率 0.505–0.507; LONG 0.510–0.518 对基率 0.534; SHORT 0.496–0.512 对基率 0.524 ⇒ **方向也不比「总猜多数方向」好**。
- 校准斜率: NET −0.19…−0.03(反向); LONG +0.18…+0.30; SHORT +0.08…+0.17(预测幅度被放大 3–12 倍)。
- 五分位表(描述): L · LONG 最高预测五分位的多头价格均值 +5.2 / +5.5 bps, 其余四档 −1.9…+0.9; 同样形状在 L · SHORT 上以镜像出现。NET 两模型的五分位均值无单调关系(L: +1.84 / +0.22 / −0.26 / +0.10 / +1.10)。

## §5 模型内部(描述, 不参与判决; `TABLES_T8.md` T8)
- Ridge · NET 最大的标准化系数: TR42 −0.56、BTC24 −0.37、BR24 −0.37、ALT4 +0.32、CLF −0.27、CSR72 +0.25(均 5/5 折同号)—— 在训练集里是「书近 7 日好 → 下一锚差」「BTC 与广度 24h 普涨 → 下一锚差」, 但样本外合并相关为 −0.009, 不成立。
- Ridge · LONG: ALT4 +1.93、BTC24 −1.53、RVM24 +1.44、TR42 +1.38、BR24 −1.22; SHORT 近似镜像。LGBM 在实质格上的 gain 分散, 没有占比 > 11% 的列(NET 最高 TR42 0.107; LONG 最高 RVM24 0.083; SHORT 最高 RVM24 0.086)。
- CARRY 正控按设计由 CSF / CLF 解释(LGBM gain 0.74 / 0.14), 确认拥挤度列与 W[i]、面板费率行对齐。

## §6 与既有受据的对账(引收据原文)
1. **与「主导率保费」记录方向相反(未裁定)。** 收据 `multi_asset/exports/eda/kcurve_2026-08-21/RESULT_event_calendar_and_wide_stop_2026-08-21.md` L209: 「书逐锚净额对"等权山寨 − BTC 同锚价差"的 β = **−0.249**, 相关 **−0.767**(r²=0.59), 逐年 −0.22/−0.28/−0.25/−0.24/−0.30 **五年稳定** … 该暴露贡献 … 书均值 1.122 的 78%」。本线在 A0 v4 上测得同期 corr(NET, 前向等权山寨−BTC 价差) = **+0.0506(s42)/ +0.0434(s2027)**, 逐折训练 β 为正(+131…+454 bps / 单位价差收益, 约 +0.013…+0.045 bps / bps)。**仪器不同**(读装置 `kcurve_2026-08-15/devices_2026-08-21/altspread_hedge_overlay.py` L9–22 核实): 该收据的书是 jpline `net_S1.npy`(08-21 在役书 S1, 9,821 锚)、收益是 `engine.replay_fullhist` 的 `src.Y4`、山寨集是引擎可交易名去 BTC 与 ETH; 本线是 A0(C0)、v4 RAW 记账元、UPIT_CRYPTO 去 BTC。**[推断]** 「78% 收益来自主导率暴露」不能迁移到 A0 v4 书。哪一个仪器对, 本线不裁定, 列为待对账。
2. **与 `adaptive_turnover_family_closed`(08-11)一致并扩展**: 该记录是 3 个条件量与书毛的同锚相关 < 0.03; 本线是 24 列多变量线性 + 非线性、按年嵌套前推、两种子, 净额样本外相关仍 ≈ 0。无矛盾。
3. **未复现 08-21 同一收据 L210 的「AS_{t−1} 五分位 → 下一锚净额 top−bottom 4/5 年为正」可用信号**: 本线特征含 ALT4 / ALT24 / ALT72, NET 仍只有 2/5 折为正。该收据本身写明「幅度 0.6~7 不稳, 不可入执行」, 统计量(样本内五分位差)与书也不同 ⇒ 不算矛盾, 与「不可入执行」一致。
4. **T1 的事后线索**「BREADTH72 第 4 五分位 × 空头价格为负」(T1 RESULT §2, 数百格中挑出): 本线 SHORT 目标含广度与拥挤度列, 样本外 SHORT 相关 CI 含 0 ⇒ 该描述性线索没有转化为稳健的样本外可预测性。T1 未作判决, 不算矛盾。

## §7 VERIFIED 与 INFERRED
**VERIFIED(本轮计算, 收据可复算)**: §1 全部门; §2–§5 全部数字; 目标对 r18 逐年表的复现; 数据文件在首跑与重跑间逐位相同; 收据拷回 Mac 后 31 个文件 sha 与 pod2 原件一致; 冻结规则下的判决 T8 = FAIL(`RECEIPT_T8_judge.json`)。
**INFERRED 或声明的边界**:
- LONG / SHORT 微弱预测力「是同一市场方向信号、在净额中抵消」: 由 Share_S ≈ 1、残差相关 ≈ 0、G2a ±0.99 与 NET 结果合读, 未单独检验。
- 与 08-21 主导率记录的方向相反: 事实已核, 原因未查。
- **执行延迟未测**(预注册 §9.1): 目标从 E_i 起记账, 实盘约 E_i + 24 分钟后成交; 因为本线在 E_i 就测不到可预测性, 这一条对 FAIL 没有影响。
- C0 的 N2 前向合格规则影响拥挤度列 15 格 / 12 锚(预注册 §9.2), 有界、未修。
- **OI: NOT MEASURED**(预注册 §4.3): Mac 与 pod2 上都没有宽覆盖 OI(已核); jpline 上有两份, 都不在允许的计算主机上, 覆盖也不够 —— 820 名 um 面板(2023-01 起)与 140 币 `wide_metrics_ch.npz`(见 §8 第 6 条)。
- 状态集限于纲领所列; FAIL 不排除其他信息源(T7 韩元溢价、盘口)。

## §8 偏离与事后项
1. **AMENDMENT 1**(`PREREG_AMENDMENT_1_T8.md`, 10:20:22Z, 先于 null 与 fit): build 首跑 G2a 在 `c_N(0) < 0` 上失败。我把一个取自另一台仪器的书性质先验写成了对齐门的硬条件, 是我的错误。修订后只由 c_L / c_S 认证对齐, c_N 只报。首跑收据原样保存在 `receipts/pod2/failed_first_runs/`。
2. **本机没有 `timeout` 命令**: 冻结前数次 `timeout 60 grep …` 检索实际没有运行, 因为 stderr 被重定向; 我把「无输出」读成了「无匹配」。修订前已用普通 grep 重跑, §4.3 的结论不变(记在 AMENDMENT 1 §E)。
3. 自检首跑的收据用的是修订前的 `t8_common.py`(sha `dbd20981…`, 当时 8/8 通过)。修订只改了 `check_prereg`, 修订后重跑仍 8/8; 旧收据留在 `failed_first_runs/`, 标 `_pre_amendment1`。
4. null 分块(0–40 / 40–190 / 190–340 / 340–500)是操作性划分, 用于满足前台 10 分钟上限; judge 断言 r = 0..499 各出现一次。
5. §0 与 §6 标 [推断] 的两处读法不参与判决。没有其他事后统计量; §4 与 §5 的描述量都在预注册 §6 中列过。
6. **事后发现(POST-HOC, 结果之后)**: 预注册 §4.3 列举 OI 数据时漏了一份资产 —— 记忆 `ma_v3_track2_oi_positioning_closed`(2026-07-13): 约 140 币的 data.binance.vision metrics 通道 `$M/multi_asset/exports/wide_metrics_ch.npz`(126 币到 2026-06), 其截面残差 IC 用法在 07-13 双门 FAIL 关闭。漏掉的原因: 我的重跑检索词是 `open_interest|f12_l3_um|um_panel|持仓量| OI `, 没有匹配到「OI/positioning」。核实: 该文件不在 Mac 仓库, 也不在 pod2(`/workspace/multi_asset/exports/`、`/workspace/` 均无); `$M` 是 jpline 的研究树(08-21 装置用同一前缀)。它也覆盖不到 W_FULL 末两个月和 2025–26 年 ≥ 400 名的宇宙。⇒ §4.3「OI 不可得」的结论不变, 但列举不完整; 本线**没有**补测 OI —— 那将是新家族成员。

## §9 家族大小(T6 教训)
判决格 = {Ridge, LGBM} × {NET, LONG, SHORT} = **6**, 另有 2 个 CARRY 正控格; 每格在 2 个臂种子上合取读。观测拟合 **80** 个(2 × 4 × 2 × 5); 零分布重拟合 **15,000** 个(500 × 6 × 5, s42)。没有拟合或报告任何其他模型、特征子集、窗口、折方案或超参。

## §10 复跑(逐字)
Mac(`uplift_r2_2026-09-13/T8` 目录)上传:
```
scp -q PREREG_T8.md PREREG_AMENDMENT_1_T8.md pod2:/workspace/uplift_r2_2026-09-13/T8/
scp -q receipts/PREREG_FREEZE_sha.txt pod2:/workspace/uplift_r2_2026-09-13/T8/receipts/
scp -q devices/t8_common.py devices/t8_build.py devices/t8_null.py devices/t8_fit.py devices/t8_judge.py devices/t8_selftest.py devices/run_t8.sh pod2:/workspace/uplift_r2_2026-09-13/T8/devices/
```
pod2(每行在 Mac 上以 `ssh pod2 'bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh <装置> [参数]; echo "wrapper_exit=$?"'` 前台调用):
```
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_selftest.py
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_build.py
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_null.py 0 40
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_null.py 40 190
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_null.py 190 340
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_null.py 340 500
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_fit.py
bash /workspace/uplift_r2_2026-09-13/T8/devices/run_t8.sh t8_judge.py
```
`run_t8.sh` 内部: `env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/<装置> PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS [参数]`, 输出 `receipts/<tag>_stdout.log` 与 `receipts/RC_<tag>.txt`。
Mac 取回并渲染:
```
scp -q -r 'pod2:/workspace/uplift_r2_2026-09-13/T8/receipts/*' receipts/pod2/ && rm -f receipts/pod2/PREREG_FREEZE_sha.txt
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 devices/t8_tables.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
```

## §11 产物
- 规格: `PREREG_T8.md`、`PREREG_AMENDMENT_1_T8.md`、`receipts/PREREG_FREEZE_sha.txt`
- 装置: `devices/t8_common.py`、`t8_selftest.py`、`t8_build.py`、`t8_null.py`、`t8_fit.py`、`t8_judge.py`、`t8_tables.py`、`run_t8.sh`
- 收据(pod2 原件的逐位拷贝): `receipts/pod2/RECEIPT_T8_{selftest,build,null_0_40,null_40_190,null_190_340,null_340_500,fit,judge}.json`、各 `*_stdout.log` 与 `RC_*.txt`、`receipts/pod2/failed_first_runs/`; 渲染表 `receipts/TABLES_T8.md`
- **只在 pod2**(不入库; Mac 副本在 `/Users/haosiyu/cc_tmp/t8/`): `out/T8_data.npz` sha256 `ff8d4e5779d6c7f96e95349582f3cf39371dbf3d1fcb53f03f4d6d3b3def9207`(4.5 MB, 目标与 24 列特征)、`out/T8_oos.npz` sha256 `fc0139137e81fa688d43621b846554822d5a2de4ccdf10605fe11ee112cbc0f3`(16 个格的样本外预测)
- 校验和: `SHA256SUMS.txt`
