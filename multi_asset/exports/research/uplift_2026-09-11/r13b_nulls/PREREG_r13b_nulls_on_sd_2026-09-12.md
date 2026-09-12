# PREREG — r13-B 零假设臂的 sd / 尾部读数(第十三轮活口的判决装置)

> **创建:** 2026-09-12 | **Session:** b9646a9e (research subagent, 分支 `research/book-uplift-2026-09-11`) | **状态:** FROZEN(本文 sha 被装置断言后才允许跑) | **作废条件:** 装置 `r13bn_device.py` 或其依赖 `r13b_core.py`(sha `54d98f8cf2ac16493387d767a1f614e9507cf09b5cf58fa9535ac95879b5a375`)任一改动; 或 `r13B_series.npz`(sha `f1b84e2796cf59d7036f229d6a9ba432daec53632f1b1570814391259bd68aa1`)被重写。

## 0. 问题(一句话)

第十三轮 T1(FORM B, 半区内沿估计 beta 轴重加权, 每半区美元和守恒)作为 alpha 臂**已被判负且不再复议**。唯一活口 = 「T1 把书的 W_ALPHA 波动压低 9.1%, 并把 W_TAIL 上 2.00× 的停机日 6→2, maxDD 0.4642→0.3743」。判决阶段自报: 六个换手匹配零假设**只打了 dg 分**, 没人记录零假设对 sd / 停机 / 回撤做了什么。本文冻结: **同一装置、同一次运行**, 六个零假设 + 真臂 + 基线, 记录 sd / 逐年方差分解 / 停机 / 最差日 / maxDD / P(1y maxDD≥25%), 并按下面的规则读。

## 1. 冻结时已知 vs 未知(诚实披露)

**已知(冻结前已从归档收据读到, 因此下面任何关于真臂本身的数字都不是盲测):**
`RECEIPT_r13B_full.json`(sha `c8614f7a…`)、`RECEIPT_r13B_tail.json`(`593b5f21…`)、`RECEIPT_r13_verdict.json`(`30a43c5d…`)中: 真臂 W_ALPHA sd 22.985→20.894(−9.098%, 配对 CI95 [−10.54%, −7.69%]); 逐年 sd 变化 2022 −1.8 / 2023 −5.1 / 2024 −11.1 / 2025 −11.9 / 2026 −7.8 (%); W_TAIL@2.00× 停机 6→2, alert 24→13, 最差日 −11.171%→−6.334%, maxDD_anchor 0.46418→0.37429, maxDD_daily 0.45986→0.37299, P(1y maxDD≥25%) 26.97%→20.78%; 判据最大杠杆 1.6072→1.6910(+5.2%); 逐年方差分解(A 解释 vs 残差); 六个零假设已归档的 KAPPA(3.25 / 3.1875 / 3.25 / 1.046875 / 1.1875 / 1.5)、dg、开火计数与 `Bhat_reduction_pct`(SHIFT101 **+93.3%**, SHIFT503 +87.7%, SHIFT1009 +66.9%, RELAB1-3 **−55.9 / −44.0 / −52.5%**)。

**未知(本文规则冻结在这些量上):** 六个零假设的 sd、逐年方差分解、停机/最差日/maxDD/P25; C1 附加臂的一切; BASE@L_sd 去杠杆对照的全部尾部指标; 杠杆余量的 bootstrap CI / 留出窗; beta 矩阵在滞后 101/503/1009 的截面秩自相关; 年固定效应后的 sd。

## 2. 臂(全部在 `r13b_core.py` 的函数上构建, 不重实现)

装置 `devices/r13bn_device.py` 以 `exec` 载入 `r13b_core.py` 从文件头到 `# --- S6 statistics` 之前的全部代码(与已归档 `r13b_chk.py` 同法), 因此 `load_book / static_rows / reshape_ex / overlay / account / BETA[250]` 全是归档代码; 装置断言 `r13b_core.py` sha 逐位等于上方值。

| 臂 | 定义 | KAPPA |
|---|---|---|
| BASE | `account(kappa=0, POST)` | 0 |
| REAL | `account(kappa=1.00, W=250, POST)`, seed s42 | 1.00 |
| NULL_RELAB1/2/3 | `bperm = default_rng([4242,k]).permutation(N)`, 每锚同一置换 | 二分重解 |
| NULL_SHIFT101/503/1009 | `bshift = k`(beta 矩阵整体前移 k 锚) | 二分重解 |
| **C1_VOL(附加, 非六零假设之一)** | 把 `b` 换成同窗 `σ_i(W=250)=sqrt(Syy/n − my²)`(同 pairwise-complete、同 ≥0.8 覆盖规则), 其余 overlay 机器一字不改 | 二分重解 |

**匹配(与 dg 零假设完全相同的算法, 逐字复用):** `lo=0, hi=8, ≤13 次二分, 命中 |Δturn − Δturn_REAL|/|Δturn_REAL| ≤ 1% 即停`; 目标 = REAL 的 W_ALPHA 边际匹配换手 `+0.003232648`(base 0.0540270 的 +5.81%)。**断言:** 六个零假设重解出的 KAPPA 与归档值逐位相等(这就是「同一次运行」的证明); 记录开火计数(目标 9131)与相对偏差。

**逐位复现门(GATE):** BASE 与 REAL 的 `g` 必须与 `r13B_series.npz` 的 `g_base / g_primary` 逐位相等(`np.array_equal`); 不等则装置 abort。

## 3. 记录的量(每臂)

- **W_ALPHA (n=9138):** `sd(g)`(ddof=1); 相对变化 `Δ = 1 − sd_arm/sd_BASE`; 配对 UTC 日块 bootstrap CI95(2000 次, `default_rng([20260905,k])`, 与 r13b_tail 同法); mean g; Sharpe_ann; **年固定效应后 sd**(逐年去均值后的 sd)与其 Δ; **年-月固定效应后 sd**; 逐年 sd 与 Δ; 逐年方差分解(OLS `g ~ A_ew(bps)`: beta, var_total, var_explained_by_A, var_resid; 与 `r13b_tail.py vardec` 同式); 逐年 mean g / dg。
- **W_TAIL (n=10038) @2.00×:** 日收益 `Π(1+2.0·g·1e-4)−1`; 停机日(≤−4.00%)、alert(≤−2.68%)、最差 UTC 日(日期+收益)、`maxDD_anchor`(与 build 同)、`maxDD_daily`(与 verdict 同)、`P(1y maxDD≥25%)`(1309 个重叠 365 日窗, 与 verdict 同)、中位 1y maxDD; 逐年: 停机、alert、最差日、年内 maxDD_anchor、日收益 sd。
- **机制诊断:** 300 个固定抽样锚(`default_rng([20260905,31])`)上每臂的 HHI=Σu² 与 **σ 加权毛额** Σ|u_i|σ_i(W250); beta 矩阵在滞后 101/503/1009 的截面 Spearman 自相关(每 10 锚抽一); 六零假设的 `mean|θ| / clipped / Bhat_reduction_pct` 与归档值对账。

## 4. 冻结的读数规则

设 `ΔREAL = 1 − sd_REAL/sd_BASE`(W_ALPHA, 点估计; 已知 ≈ 0.09098)。

**R1(sd, 主判据; 采纳判决阶段原提案, 不改):** 若六个零假设中**任一** `ΔNULL_j ≥ 0.70·ΔREAL` ⇒ **活口 CLOSED(sd 腿)**。
解释附则(冻结): RELAB 触发 ⇒ 波动压低是**一般性权重扰动收缩**; SHIFT 触发 ⇒ 波动压低**不需要及时的 beta**, 一个持久的名字属性即够(同时报该滞后的 beta 秩自相关)。两种触发都关闭「方向载荷覆盖层」这一命名下的活口。我知道 SHIFT101 保留了大部分 beta 信息(归档 Bhat_reduction 93%), 仍采纳 ANY 规则, 因为它保守——关闭比放行更容易——而这正是判决阶段自报的意图。

**R2(尾部):** 对每个零假设在 W_TAIL@2.00× 上算三项相对 BASE 的改善: 停机日移除数(REAL: 4)、maxDD_anchor 降幅(REAL: 0.08989)、P25 降幅(REAL: 6.188 pp)。若**任一**零假设在**≥2/3 项**上达到 REAL 改善的 ≥70%(即 停机 ≤3 日; maxDD_anchor ≤ 0.40126; P25 ≤ 22.635%)⇒ **活口 CLOSED(尾部腿)**。取「2/3」是因停机是 6 个整数上的计数, 单项极易被噪声打中。

**R3(去杠杆对照):** `L_sd = 2.00 × sd_REAL/sd_BASE`(W_ALPHA 锚级 sd; 同时报日级 sd 对应的 `L_sd_day`)。比较 BASE@L_sd 与 REAL@2.00 在 W_TAIL 四项 {停机数, 最差日收益, maxDD_anchor, P25}:
- BASE@L_sd 在 **≥3/4 项不劣于** REAL@2.00 ⇒ REAL 的尾部收益与单纯去杠杆不可区分 ⇒ **活口 CLOSED(R3)**(第十二轮以同一方式关闭锚内止损: "dominated at matched cost by a single leverage dial");
- REAL@2.00 在 **≥3/4 项严格优于** BASE@L_sd ⇒ R3 OPEN(REAL 携带超出波动缩放的尾部信息);
- 2:2 ⇒ R3 INDETERMINATE, 只报不关。
匹配 sd 下两臂均值不同(BASE@L_sd 损失 ~9% 均值, REAL 保住均值), 连 CI 一并报出, 但**不进 R3**: alpha 已判负, 活口是 vol/尾部主张。

**C1(附加 "costume" 臂, 与六零假设分开读):** 若 `ΔC1 ≥ 0.70·ΔREAL` ⇒ sd 收益在**纯波动轴**上即可复现 ⇒ **活口 CLOSED**, 理由 = 「逐名波动上限轴(2026-09-06 判负, DNR, `tail_aware_sizing_rejected_2026_09_06`)穿了 beta 的衣服」; 若 `ΔC1 < 0.70·ΔREAL` ⇒ beta 携带超出波动的 sd 信息, 只报。C1 同时过 R2 式尾部比较, 只报。**C1 不在 lead 指定的六零假设之列, 单列, 可被忽略而不影响 R1–R3。**

**R4(regime 相关性, 只读不判——因真臂逐年数在冻结前已知):** 逐年表(停机/最差日/maxDD/sd/mean, BASE vs REAL, 2022–2026 每年)。声明读法: 尾部腿的实盘相关性看 2025–2026; 若 REAL 在 2026 的停机/最差日/maxDD 均不优于 BASE, 尾部主张被改写为「2022 与 2025 事件」。

**H(+5.2% 杠杆余量):** `L_crit(arm) = max L: halt/yr ≤ 1.0 ∧ P(1y maxDD≥25%) ≤ 10%`(verdict 同法, 二分 [0.25, 6.0] 30 步)。不确定性: (a) **配对循环块 bootstrap**(日块长 30, 2000 次, `default_rng([20260905,k])`, 两臂同块), 对 `L_crit_REAL/L_crit_BASE − 1` 及两臂在各自 L_crit 上 W_ALPHA 年化收益之差给 CI95; (b) **对半留出**: 在 2022–23 日上解 L_crit, 在 2024–26 上验判据是否仍过(反向亦然); (c) 留一年出。**规则:** 若 (a) 的 CI95 含 0, 或 (b) 任一方向余量变号 ⇒ **+5.2% 的主张 WITHDRAWN**(改述为「不可分辨」); 否则保留并附 CI。

**总判决:** R1 ∨ R2 ∨ R3 ∨ C1 任一触发 ⇒ 活口 **CLOSED**; 全不触发 ⇒ **ESTABLISHED**, 并附 R4 与 H 的限定语。不偏好任一结果。

## 5. 口径与纪律

CALIBER PIN v4(`w10_sleeve.py` b88e35a46b93d712); 禁 v3 谱系(dlw_ext/_ext 缓存、pod_fea_ext、裁剪复利 E-0908-B、pod_legs_ext、shadow_bundle_v3、wide_fea_v2ext_meta、panel_source 默认脏面板、pod 5m 谱系 expm1)。装置只读 `pod_backup_2026-08-21` 面板、`umask_UPIT_CRYPTO.npz`、`causal_primitives_r12_v2.npz`、A0 书 `A0_PWR230k_s42.npz`(sha `352ac36f…`), 全部由 r13b_core 头部断言。W_ALPHA 仅用于均值/CI/Sharpe/sd/换手; W_TAIL 仅用于 maxDD/最差日/停机/P25。E-0826-D: 白名单以 argv[1] 传入、被断言、连 `env_actual` 写进收据。pod2 只用 CPU, 装置前后各记一次 `nvidia-smi`。实盘树零接触。
