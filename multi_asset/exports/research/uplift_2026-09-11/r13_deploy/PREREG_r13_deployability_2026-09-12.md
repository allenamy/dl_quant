# PREREG r13 · T1 可表达性裁定(FORM A / FORM B)+ 逐名 β 可估性

> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结, 先于任何数字 | **作废条件:** 执行器 `signal/legs.py::reshape_after_withhold` 或 `scheduler/anchor_loop.py::apply_withhold_and_reshape` 的语义改变
> **口径锁:** CALIBER_PIN_v4_2026-09-11.md。装置 `w10_sleeve.py` sha16 `b88e35a46b93d712`。
> **实盘零接触:** `~/dl_quant_live` / `~/wide_shadow` 只读 import / 只读 open。不写、不重启、不下单、不调任何账户 API。pod2 只跑 CPU。

## §0 K 与首要统计量

**K = 14** 条预注册检验(S1–S6 结构 6 · A1–A3 FORM A 3 · B1–B3 FORM B 3 · E1–E2 β 2)。

**首要统计量(裁定用的就是这三个, 其余是支撑):**
1. `S_A(d) = (gL−gS)_after_reshape / d` —— 意图中的半区美元倾斜 `d` 在 reshape 之后的**存活比**。
2. `S_B = max_i |w_out,i − w_in,i| × sizing_gross` (USDT) —— reshape 施加在一本 FORM B 书上的**畸变**。
3. `ρ_OOS` = 逐名 `β̂`(尾随窗 W)与**下一个不重叠窗**实现 β 的截面 Spearman。

**本轮不产出任何收益统计量。** 因此换手匹配零假设电池(SHIFT101/503/1009, RELAB1-3)**不被调用** —— 它约束的是 r14 要建的臂。逐锚置换 placebo 已知有缺陷, 不使用。r14 的零假设必须同时匹配**换手**与**开火次数**(firing count), 此处一并声明。

## §1 三个窗, 绝不混用

| 窗 | 定义 | n | 用途 |
|---|---|---|---|
| **W_ALPHA** | 丢前 900 (E-0911-A) ∧ ts ≤ 2026-08-30 20Z (E-0911-D) | 9138 | E1/E2 的一切均值/CI/离散度/自相关 |
| **W_TAIL** | ts ≤ 2026-08-30 20Z, 不丢暖 | 10038 | 本轮**不使用**(无 maxDD/最坏日/停机数字) |
| **W_LIVE_DEPLOY** | 实盘 combo 换装后的锚: 2026-08-26 08Z … 2026-09-12 04Z, 取 `anchors.jsonl` 中带 `reshape` 报告的行 | 待测(≥30) | **只**用于可表达性的结构事实(净额/毛额/逐名位移/存活比)。**不在其上计算任何收益、Sharpe、maxDD。** |

W_LIVE_DEPLOY 既不属于 W_ALPHA 也不属于 W_TAIL。它承载的全部是**确定性代数与账本读数**, 不是收益推断 —— 这是它可以单独存在的理由, 并在此显式声明, 而不是悄悄使用。

## §2 结构检验 S1–S6(实盘账本 + 部署中的函数本体)

被检对象逐字: `~/dl_quant_live/signal/legs.py` L124-198 `reshape_after_withhold`; `~/dl_quant_live/scheduler/anchor_loop.py` L287-380 `apply_withhold_and_reshape`, 调用点 L1664; `~/wide_shadow/fea171/combo_stage.py` L198-206 `exec_reshape`, 写者 L345-356。

| 号 | 命题 | 阈值(先于数字) |
|---|---|---|
| S1 | reshape 把 net 精确打到 0 | 每个 W_LIVE_DEPLOY 锚 `|net_after| / sizing_gross ≤ 1e-12` |
| S2 | reshape 把 gross 精确还原到 sizing_gross | 每锚 `|gross_after − sizing_gross| / sizing_gross ≤ 1e-9` |
| S3 | reshape 是**全局仿射**映射 `w ↦ (w − mean w)/‖w − mean w‖₁` | 我方独立重实现与**部署中的函数本体**逐位: 每锚 `max|Δw| ≤ 1e-15` |
| S4 | reshape **无条件**运行, 不以"有 pop"为门 | 若存在 `n_popped == 0` 且 `net_before ≠ net_after` 的锚 ⇒ 无条件成立; 若**所有** `n_popped==0` 锚都满足 `net_before==net_after` ⇒ 判 pop-gated |
| S5 | 次序 = pop → reshape → clamp → (外部书跳过中性带) → plan | 源码字节序断言 `i_reshape < i_band < i_plan`; 且账本存在 `clamped_after_reshape` ⇒ clamp 在 reshape 之后 |
| S6 | 生产者写进 `target_live` 的是 **`combo_raw`(reshape 前)**, 所以执行器那一次 redemean 是**唯一生效**的 | ≥30 个锚满足 `|Σw_file| / Σ|w_file| > 1e-3` |

**平价门 P0(先于 A/B 任何注入):** 我方从 `~/wide_shadow/state/target_live/{A}.json` + 账本 `popped_names` + `sizing_gross` 重建的 `net_before` / `gross_before`, 与账本 `reshape` 字段相对误差 ≤ 1e-6 的锚数 ≥ 30。**P0 不过 ⇒ A/B 的注入实验作废, 只报 S1–S6 与账本读数。**

## §3 FORM A(半区缩放)A1–A3

FORM A 定义: `w_L ← w_L(1+d)`, `w_S ← w_S(1−d)`, 毛额守恒(单位毛额下 Σ|w| 仍为 1, 净额变为 d)。
注入点 = 生产者文件权重(执行器上游唯一可控点), 然后跑**部署中的函数本体**。

| 号 | 统计量 | 阈值 |
|---|---|---|
| A1 | `S_A(d)`, d ∈ {0.01, 0.05, 0.10, 0.20} | **可表达** iff `median S_A(0.05) ≥ 0.50`; **不可表达** iff `median S_A(0.05) ≤ 0.01`; 之间 ⇒ ONLY_WITH_EXECUTOR_CHANGE |
| A2 | 实际存活下来的是什么: `max_i |w_A,out,i − w_base,out,i|` (pp) 及其占典型名权重的比例 | 只报, 无阈值(用于说明"被执行的不是你要的那本书") |
| A3 | 是否存在**任何**别的通道让"逐名权重比"活下来 | 仿射不变量检验: `(w_i−w_j)/(w_k−w_l)` 在 reshape 前后相对变化 ≤ 1e-12 ⇒ 结论"只有仿射不变泛函能通过" |

## §4 FORM B(半区内重配)B1–B3

FORM B 定义: 每个半区的**美元和精确不变**, 权重只在半区内部从高 β 名移向低 β 名(空头半区反向), 毛额精确不变。
⇒ 构造上 Σw = 0 且 Σ|w| 不变 ⇒ redemean 减 0, rescale 除 1。

| 号 | 统计量 | 阈值 |
|---|---|---|
| B1 | `S_B = max_i |w_out,i − w_in,i| × sizing_gross` (USDT) | **可表达** iff 每个锚 `S_B ≤ 1e-6` USDT |
| B2 | 意图中的 β 缺口变动是否逐位保留 | `|Δ(β_L−β_S)_after − Δ(β_L−β_S)_intended| / |intended| ≤ 1e-9` |
| B3 | FORM B 叠加层的**增量换手**与成本 | 报**匹配口径** `Δturnover/gross_total`;按 fitted 模型 `costb_PWR_G230k.json` `book_avg_bps_per_unit_turnover = 2.9537` 定价;并报 **×3.2167 重定价下的符号**。参照: A0 匹配换手 = **0.0540270**(mean gross_total 0.6956);生收据字段 0.03032 **未归一**, 混用 = 1.4375× 错误 |

**成本争议声明(必须随每个加换手的臂重复):** 实现成本是否 ≈ 模型的 3.2 倍, 在我方两台仪器之间**有争议且未解决**。r12 已证明它决定每个加换手臂的**符号**。B3 因此同时报 fitted 与 ×3.2167 两个读数。

## §5 β 可估性 E1–E2(pod2, CPU, W_ALPHA)

基准 `A_t` = 在册成员的**等权截面 4h 收益**(与 r12 `A_ew` 同定义, 逐字复用 `causal_primitives_r12_v2.npz` 的构造)。
`β̂_i(t; W) = cov(y_i, A)/var(A)`, 尾随 W 个锚, 要求窗内有限观测 ≥ 0.8W。W ∈ {30, 60, 120, 250}。

| 号 | 统计量 | 阈值(裁定) |
|---|---|---|
| E1 | (i) 分半信度 `ρ_SB`(窗内奇/偶观测各估一次, 截面 Spearman 后 Spearman-Brown 修正); (ii) `ρ_OOS` = β̂(尾随 W) vs **下一个不重叠 W 窗**的实现 β, 截面 Spearman; (iii) 半区价差存活比 = 按 β̂ 分五分位, 下一窗实现 β 的 Q5−Q1 ÷ 事前 β̂ 的 Q5−Q1 | **KILL** iff 最优窗下 `ρ_SB < 0.30` **或** `ρ_OOS < 0.30` **或** 存活比 < 0.20。**GO** iff `ρ_OOS ≥ 0.30` ∧ 存活比 ≥ 0.40 ∧ `ρ_SB ≥ 0.30`。之间 ⇒ USABLE_WITH_SHRINKAGE |
| E2 | 截面离散度 `sd_cs(β̂)`、IQR;秩自相关 lag-1(机械, 窗重叠 ⇒ 必然高, 只报)与 lag-W(不重叠, 有信息) | 只报, 但 lag-W 秩自相关 < 0.20 单独构成 KILL 的佐证 |

**收缩:** 报隐含 Vasicek/James-Stein 收缩系数 = 信度 `ρ_SB`。任何 β 目标叠加层的可实现 β 缺口缩减 ≈ 存活比, 不是 1。

## §6 ENV 白名单(E-0826-D)

全部本地装置以 `env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu` 启动。
**白名单(枚举, 非空):** `PATH`, `HOME`, `PWD`, `SHLVL`, `_`, `LC_CTYPE`, `__CF_USER_TEXT_ENCODING`。
**断言集(必须为空):** 任何以 `CAL/JUDGE/UPLIFT/PANEL/LOOK/WRULE/LEGS/PHI/FSEED/W3FIX/FTRIM/UMASK/SLOW/FPRED/MEMBERS_TOPN/COSTB/SLEEVE/KMOD/SEAT/RNSM/LTRIM/CDAMP/FUNDSCALE/FEMAT/TRADE_TOPN/REF_SKIP/PYTHON/OMP/MKL` 开头的变量。
pod2 装置以 `env -i PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root` 启动, 白名单 `PATH HOME PWD SHLVL _ LANG LC_ALL`(实测枚举写进收据), 同一断言集必须为空。
**每台装置把实测 `env_actual` 全量写进自己的收据 JSON。**

## §7 冻结前已看过的东西(诚实声明)

冻结前只做了**代码阅读**与**两行 schema 探查**(`20260909/anchors.jsonl` 的 2 行 `reshape` 字段, 目的是学结构)。这两行同样计入 W_LIVE_DEPLOY 的全量统计, 不剔除。除此之外没有计算过任何本预注册中的统计量。

## §8 裁定映射

- `form_A_expressible` ∈ {YES, NO, ONLY_WITH_EXECUTOR_CHANGE} ← A1 阈值。
- `form_B_expressible` 同上 ← B1 阈值。
- `go_nogo` ∈ {GO_BOTH, GO_A_ONLY, GO_B_ONLY, NO_GO}: A/B 各自可表达 **且** E1 非 KILL ⇒ 该形态 GO。E1 判 KILL ⇒ 无论可表达性如何, 依赖逐名 β 的形态一律 NO_GO(可表达 ≠ 有信号)。
